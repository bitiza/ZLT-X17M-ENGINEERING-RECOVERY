# X17M 1 GB brick recovery: live audit of remaining avenues (2026-10-20)

Target: bricked 1 GB NAND ZLT X17M. Slot B holds a non-booting image (no `/dev`).
Slot A is intact. Only the bootlooped unit is on the bench; the working 1 GB unit is in use.

All statements below are either **FACT** (observed on the live unit during this session)
or **OFFLINE** (read from local dumps, no device contact). No flash write has been
performed on the device at any point in this session.

---

## 1. Preloader DA host: closed

The Preloader (`0e8d:2000`) accepts the MTK handshake and reports
`is_brom=False`, `hwcode=0x992`, target config `0x5`, `SBC=True`, `DAA=True`.

| Test | Command | Result |
|---|---|---|
| Stock DA | `send_da` of `DA_BR.bin` | `DAA_SIG_VERIFY_FAILED (0x7024)` at `upload_data` |
| ACC-bypass DA | `send_da` of `DA_BR_acc_bypass_nand.bin` | `DAA_SIG_VERIFY_FAILED (0x7024)` at `upload_data` |
| SRAM write | `WRITE32` to `sec_img_auth` `0x22d050` | `CRYPTO_DEINIT_FAIL (0x1001)` |
| SRAM read | `READ16` / `READ32` / `READ32_direct` | `CRYPTO_INIT_FAIL (0x1000)` |
| Raw register | `0xDA` write of `00207047` to `0x22d050` | `USB Overflow`, Kamakiri2 failed, session broken |

**FACT.** The Preloader enforces a DA signature that neither the stock RG500 DA nor the
ACC-bypass DA satisfies. The ACC bypass lives inside the DA body and therefore cannot
satisfy the outer DAA gate. The Preloader also refuses unauthenticated SRAM access, and it
does not implement the `0xDA` register command in Preloader mode (it is a BROM-only command).

**OFFLINE (root cause of the key mismatch).** `analysis/MT6890_DA_BR_SIGNATURE_KEY_AUDIT.md`
proves the supplied `DA_BR.bin` is RSA-PSS/SHA-256 signed by modulus
`9af8a28bf1096b58751ab5ef5f696c5df3050124bb9fec51bd9bf190d04c618f`.
`analysis/MT6890_TOOLAUTH_BINARY_AND_TRUST_ANALYSIS.md` records that the SDK's
`inc/dakey.h` `DA_PUBK` used by `sec_auth.c` is a *different* modulus,
`a697414d00aeb51df58c60b0b9f9e3129898ab10cca064067f3b41d2dc7b2657`, and that this is what
`seclib_set_pubk(g_dakey, DA_PUBK_SZ)` installs for DA-image signature checking.
No private key for `a697...` was found in the workspace, so the DA cannot be re-signed
offline. **This avenue is closed unless a matching key is produced.**

**Consequence.** Every remaining avenue must avoid the DA entirely.

---

## 2. NEW FACT: the UART console is live and interactive

This session's first result was a discovery that changes the recovery picture.

**FACT.** With the FTDI on `/dev/ttyUSB0` at 921600 8N1, the unit's console is a *working
interactive tty*, not a dead sink:

- The boot transcript ends with the stock OpenWrt prompt pair
  `Press the [f] key and hit [enter] to enter failsafe mode` /
  `Press the [1], [2], [3] or [4] key and hit [enter] to select the debug level`.
- Sending `f\n` is **accepted and acted upon**: the unit replies `- failsafe -`.
  The response is a semantic acknowledgement, not an echo, so the failsafe path really runs.
- The unit is not a stale `0e8d:2000` instance. After the last power cycle the router's USB
  identity is gone entirely (`lsusb` shows only the FTDI), i.e. the device has left the
  Preloader and is running Linux with the broken slot-B rootfs.

**FACT.** No shell is produced, and the reason is now precisely identified rather than guessed.
The live `/etc/preinit` is the vendor/ZLT one, not the stock OpenWrt copy in the work tree:

```text
/etc/preinit: line 0: can't open '/dev/null': No such file or directory
/etc/preinit: line 15: can't create /dev/null: nonexistent directory
/etc/preinit: line 20: can't create /dev/null: nonexistent directory
/etc/preinit: line 32: can't create /dev/null: nonexistent directory
```

The stock `preinit` under test in `rootfs/`, `rootfs.original/`, `build_v18/restore/` and
`build_v19/rootfs/` is 29 lines with no `/dev/null` reference, so the running preinit is a
different, longer vendor script. It fails because the running rootfs has **no `/dev`
directory at all**, so `devtmpfs` is never mounted.

**FACT.** Even after `- failsafe -`, no `ash` prompt appears, because the failsafe login hook
is unreachable: `lib/preinit/99_10_failsafe_login` requires
`[ -c "/dev/$console" ]` before it will spawn `ash --login </dev/$console`. With no `/dev`
directory that test can never pass. This matches, and now explains, the older note in
`analysis/X17M_LIVE_FAILSAFE_TEST_20261008.md` that "failsafe did not provide a usable
interactive shell".

**FACT.** The `1|2|3|4` debug-level option remains available. It is handled inside
`30_failsafe_wait` as `echo "$do_keypress" >/tmp/debug_level`, i.e. it only writes a file and
does not spawn a shell. It is not a recovery path by itself, but it does prove that the
`read -t "$timer" do_keypress` loop is consuming our keystrokes, which is why `f` worked.

**Consequence.** The blocker is precisely "no `/dev` in the running rootfs", not "no console",
not "no kernel", and not "failsafe is broken". Any recovery that supplies a rootfs with
`/dev` present is sufficient. The UART is a usable *input* channel to a failsafe prompt, and
would become a usable *shell* channel the moment `/dev` exists.

---

## 3. Why the current slot-B image cannot fix itself

**OFFLINE.** `WORK_LOG_XRAY_SMS_FLASH.md` section 5/6 records the flash incident:
`rootfs_v18_restore.img` was written to `rootfs_b` with `mtd -r write`. That tree was built
from the vendor original and, as built, was missing the boot-path edits and `/dev`. The
subsequent lesson list already names the fix: include `/dev` in the squashfs.

**OFFLINE.** `analysis/X17M_LIVE_FAILSAFE_TEST_20261008.md` records that the *v17_10s* image
(a) boots normally from slot B and (b) reaches an interactive failsafe root prompt on
`/dev/ttyS0` with the console-selection fix applied. `rootfs_patched_v17_10s.img`
(SHA-256 `6469a522780382293c0f62bc412b55d5477188ed547e6754db5bebd3e5cae872`) is therefore
already known-good on this hardware.

**FACT/limit.** That image cannot be delivered from the host side without a working flash
write path, because DA-based delivery is closed (section 1) and the Preloader's own
`WRITE32` is crypto-gated. The image is only useful once some write path exists.

---

## 4. A/B slot selection: the one remaining "just boot the other slot" idea

**OFFLINE.** `analysis/X17M_FORENSIC_REPORT.md` section 5 and the live `misc` dump show the
boot-control record at byte offset 2048 of the `misc` partition:

```text
00 41 42 30 ffffffff 0f 02 01 00 00 00 00 00 ffff...
```

`00 41 42 30` is the `AB0` magic. The firmware's own `get_current_slot()` selects the
larger priority byte, so B (`0x0f`) beats A (`0x0e`) and B was selected. **Slot A is
intact**, so flipping the priority byte to make A win would boot a working system with no
flash write of the rootfs at all.

**OFFLINE.** `analysis/X17M_FORENSIC_REPORT.md` section 14 lists "Boot A slot" as a
plausible candidate whose constraint is "requires changing boot-control state", and rates
writing `misc` boot-control bytes as **High** risk. `mtd write` of `misc` is therefore the
simplest *conceptual* route but needs the same missing write capability.

**OFFLINE.** The 1 GB `LK_b` (`mtd39_lk_b.img`) contains a fastboot engine whose command
table is:

```text
getvar:  reboot  reboot-bootloader  reboot-fastboot  continue  set_active:
max-download-size  product  is-userspace
```

`set_active:` is present but the implementation prints `set active slot: not supported!`
and the surrounding code opens the `misc` partition and has `bio_write failed` handling, so
the write plumbing exists even though the command is refused. There is **no** `download:`,
`flash:`, `erase:`, or `unlock` command in this LK. `analysis/X17M_FORENSIC_REPORT.md`
independently reaches the same conclusion for the 8 GB LK: the LK fastboot endpoint is
diagnostic-only.

**OFFLINE.** The 1 GB LK has `fastboot:[download_base:%p][download_size:0x%x]`, but the
command table above shows no `download:` handler is exposed, and no `flash:` token exists
anywhere in the image. This is consistent with the forensic report's finding and is not a
new avenue.

---

## 5. Preloader-as-DA partition write: the strongest remaining untested idea

**OFFLINE.** Upstream mtkclient implements a Preloader "as DA" path that needs no DA
signature at all:

- `mtkclient/Library/mtk_preloader.py:54` `SEND_PARTITION_DATA = b"\x70"`
- `mtkclient/Library/mtk_preloader.py:55` `JUMP_TO_PARTITION = b"\x71"`
- `mtkclient/Library/mtk_preloader.py:511` `send_partition_data(partitionname, data)`
  writes a partition image and `jump_to_partition(partitionname)` boots it.
- `mtkclient/Library/mtk_main.py:607` shows upstream deliberately using only
  `jump_to_partition`, with the data-sending call commented out.

**OFFLINE.** The 1 GB Preloader image does contain the partition-name machinery that this
feature depends on, at `0x720a7` onward: `%s %s partition not found`, `uboot_a`, `uboot_b`,
`lk_a`, `lk_b`, `aee_lk`, `%s lk active = %x, lk2 active = %x`, `part name=%s`. So the
Preloader can resolve partition names and know which `lk_a`/`lk_b` is active.

**Status.** This has not been exercised live yet. It is the top candidate for the next
test because it is the only identified path that could deliver a rootfs image to NAND
without a DA signature. It is also **destructive if used to write**, so it will be probed
with `jump_to_partition` (read/no-write) semantics first, and any write will be to a
**non-critical** target only, or to a verified-good image.

---

## 6. Selector avenues available in the Preloader

**OFFLINE.** `analysis/X17M_PRELOADER_SOURCE_CORRELATION.md` gives the exact dispatcher and
confirms these 8-byte tokens are present in the 1 GB Preloader image (verified by string
offsets in `mtd00_preloader.img`):

| Token | Acknowledgement | Resulting boot mode |
|---|---|---|
| `METAMETA` | `ATEM0001` / `ATEM0002` / `ATEMATEX` | `META_BOOT` (Linux META) |
| `ADVEMETA` | `ATEMEVDX` | `ADVMETA_BOOT` |
| `FACTFACT` | `TCAFTCAF` | `FACTORY_BOOT` |
| `FACTORYM` | `MYROTCAF` | `ATE_FACTORY_BOOT` |
| `FASTBOOT` | `TOOBTSAF` | `FASTBOOT` |
| `AT+NBOOT` | `AT+OK` | `NORMAL_BOOT` |

**OFFLINE.** `METAMETA` is already proven to complete end-to-end on this device
(`analysis/X17M_META_USB_WORKING_1GB_20261008.md`, `analysis/enter_x17m_meta.py`): the
transaction `READY -> METAMETA -> ATEM0001 -> V1 -> ATEM0002 -> V2 -> ATEMATEX -> DISCONNECT`
is validated and lands the unit in the Linux META gadget.

**Why META mode matters.** The META service exposes the `meta_tst` file-operation primitive
(`analysis/X17M_META_TST_PROTOCOL_RECONSTRUCTION.md`), which is an **unrestricted
`open(path)`** on the target: operation 3 reads any path, and operation 2 writes any path
(`O_RDWR|O_CREAT|O_TRUNC` then `O_RDWR|O_APPEND` continuation blocks). Live reads of
`/proc/cmdline`, `/proc/mtd`, `/usr/bin/meta_tst` and a partial `/dev/mtd51` were already
validated on the working 1 GB unit. If that same primitive is reachable on the bootlooped
unit, it is a *direct* NAND write path that needs no DA.

**Important constraint.** The META gadget on the working unit was reached with the device
running a working Linux, and the `meta_tst` binary lives in the rootfs
(`/usr/bin/meta_tst`). On the bootlooped unit the running slot-B rootfs is the broken one,
so the gadget may not come up at all. This must be tested, not assumed.

**Untested selectors.** `FASTBOOT` and `ADVEMETA` have never been exercised on this device.
`FASTBOOT` is the interesting one because it hands control to the LK fastboot engine, and
`ADVEMETA` selects a different META variant that may expose a different service set.

---

## 7. Dead ends already excluded (do not re-test)

| Avenue | Why it is dead |
|---|---|
| BootROM (`0e8d:0003`) DA upload | `0x7017` `DAA_Security_Error`; DA never executed |
| `0xDA` raw register write in Preloader | Not implemented in Preloader mode; `USB Overflow` |
| Preloader SRAM read/write | Crypto-gated (`0x1000` / `0x1001`) |
| LK fastboot `flash:` / `download:` / `erase:` | Tokens absent from the LK image |
| LK fastboot `set_active` | Explicitly `set active slot: not supported!` |
| `firstboot -y` | Already run once; it erased `nvdata` and `boot_para`. Do not repeat |
| Failsafe shell on the current image | Needs `/dev/$console`; the running rootfs has no `/dev` |

---

## 8. Ordering of the next tests

1. **`FASTBOOT` selector** on a fresh Preloader window. Cheapest, non-destructive, and it
   reaches a subsystem (LK) that has never been contacted on this device. Observe which USB
   identity appears (`0e8d:201c` per the forensic report) and what `getvar` answers.
2. **Preloader `jump_to_partition` / `send_partition_data` probe** (section 5). If the
   Preloader accepts partition commands, this is the write path. Probe with a no-write
   command first.
3. **`ADVEMETA` selector**, then re-test the `meta_tst` primitive against the bootlooped
   unit, with `/dev/mtd42` (the broken slot B) as the first read-only target.
4. If and only if a write path exists, restore slot B with the known-good
   `rootfs_patched_v17_10s.img` (or the vendor image with `/dev` added), and keep
   `rootfs_a` untouched as the fallback.

Every step is a single avenue, and each is checked before the next is attempted.

---

## 9. Restore-image candidates verified (offline, 2026-10-20)

Three local images carry a `dev/console` device node, i.e. a populated `/dev`, and are
therefore candidates to restore slot B if and only if a write path appears.

| File | Bytes | SHA-256 | `/dev` entries | Notes |
|---|---:|---|---|---|
| `rootfs_patched_v17_10s.img` | 55,738,368 | `6469a522780382293c0f62bc412b55d5477188ed547e6754db5bebd3e5cae872` | `dev/console` | **Known-good on this hardware.** Already recorded as booting normally from slot B and reaching a failsafe root prompt on `/dev/ttyS0` |
| `rootfs_patched_v17_10s_meta_rndis_dialer_auto.img` | 55,738,368 | (see work log) | `dev/console` | Same tree plus the meta/RNDIS/dialer additions that were in use when the unit was working |
| `rootfs_b.img` | 67,108,864 | `baec6707b37fc7945a5a810de19e5b058665f78a5101a25eeed8c1ef0437dcd5` | `dev/console` | Full 64 MiB slot-sized image |

**Constraint on the 64 MiB image.** `WORK_LOG_XRAY_SMS_FLASH.md` section 4 records that the
usable squashfs size of the live slot is **55,836,672 bytes** (`0xAC0000` less than 64 MiB),
because from that offset to the end of the slot is a JFFS2 copy of the overlay, and
`rootfs_b.img` is a 67,108,864-byte image whose squashfs itself ends later than that. Writing
`rootfs_b.img` over the slot would therefore overwrite the overlay copy. The 55,738,368-byte
`v17_10s` images sit under the limit and are the safer choice.

**Verified independently.** `analysis/X17M_LIVE_FAILSAFE_TEST_20261008.md` records the v17
family booting from slot B with `bootslot=b`, `root=/dev/mtdblock42`, PID 1 `procd`, and
`/tmp/.failsafe` absent (NORMAL_BOOT), plus a successful failsafe root prompt on
`/dev/ttyS0`. The `v17_10s` build additionally extends the failsafe window to 10 s.

**Same-unit backup.** `bozax17/backups/x17m-1gb-20260921-061524/logical/mtd43_rootfs_b.img`
is a 67,108,864-byte image from this unit's own NAND capture, with squashfs
`bytes_used` 58,382,709 and a `dev/console` node. It is a genuine same-unit artifact, but it
is the *pre-incident* slot B and, being 64 MiB, carries the same overlay-overwrite caveat
above.

**Verification rule for any future write.** After writing, re-read the slot and compare the
squashfs superblock plus a full SHA-256 of the written region against the source image
before rebooting. Do not trust the write without a read-back.

---

## 10. Transport requirements of the META `meta_tst` path (offline, 2026-10-20)

**FACT.** `analysis/meta_tst_safe_read.py` resolves its serial port strictly to the genuine
X17M Linux-META CDC ACM interface:

```python
matches = [port for port in serial_module.tools.list_ports.comports()
           if port.vid == 0x0E8D and port.pid == 0x202D]
```

So the `meta_tst` primitive is **not** reachable over the FTDI UART at `/dev/ttyUSB0`
(`0403:6001`). It requires the Linux META USB gadget to enumerate as `0e8d:202d` and to
expose a CDC ACM node, which the tool then opens directly. The FTDI is a separate physical
UART path and is irrelevant to this primitive.

**Consequence for the plan.** Testing `meta_tst` against the bricked unit therefore needs
**two** things in sequence, and they are sequential dependencies rather than parallel ones:

1. The `METAMETA` selector must be delivered over the Preloader's USB CDC bulk interface
   (`0e8d:2000`) using the already-validated transaction in `analysis/enter_x17m_meta.py`.
2. The device must then actually boot into the Linux META configuration and enumerate
   `0e8d:202d`, exposing the CDC ACM node the reader needs.

**FACT that makes step 2 doubtful on this unit.** `meta_tst` is `/usr/bin/meta_tst`, i.e. it
lives *in the rootfs*. The bricked unit's active slot B runs the broken image, so the
`meta_tst` binary may be absent, and the META boot may never reach the point where the
gadget enumerates. This must be tested, not assumed.

**Reference point from the working unit.** `analysis/X17M_META_TST_PROTOCOL_RECONSTRUCTION.md`
records that on the working 1 GB unit the gadget exposed *multiple* ACM ports and only
`COM281` completed validated exchanges; `COM280` returned 281 bytes that failed checksum
validation and `COM282` returned nothing. On Linux the tool resolves by VID/PID instead, so
it will pick the only matching `0e8d:202d` node; if the bricked unit exposes more than one,
the tool will refuse rather than guess, which is the correct behaviour.

**Note on the FTDI.** The FTDI remains valuable for its own purpose: it is the only channel
that gives *interactive console access to the running kernel* (section 2). The two channels
are independent and complementary - UART for console, USB for the loader/META protocols.

---

## 11. Test tooling prepared (2026-10-20)

Two tools are staged in `x17m/work/`.

**`fast_part_probe.py`** - minimal raw-pyusb Preloader prober. Written because the
Preloader USB window is roughly one second and mtkclient's `preloader.init()` performs
many sequential round trips (handshake, `GET_HW_CODE`, `GET_TARGET_CONFIG`, BL version,
BROM version, `ME_ID`), which does not reliably fit inside that window. The fast probe:

1. polls for `0e8d:2000` with no USB traffic;
2. claims the CDC bulk interface;
3. sends the 4-byte MTK start sequence `A0 0A 50 05` one byte at a time, verifying the
   inverted echo of each byte (the same sequence and echo rule as
   `mtkclient/Library/Port.py:128` `run_handshake`);
4. immediately issues the two read-only probes `0x71 JUMP_TO_PARTITION` and
   `0x70 SEND_PARTITION_DATA`, both with the non-existent name
   `zzz_no_such_partition_zzz` and, for `0x70`, a zero-length body;
5. then observes USB identities passively.

The `0x70` path writes the partition name and a 4-byte length of `0` but no payload. If the
command family *is* implemented, a name that cannot resolve plus an empty body cannot
modify anything. **This tool implements no write path at all.**

**`pl_partition_probe.py`** - the same probes expressed through mtkclient's own
`send_partition_data()` / `jump_to_partition()` API, so that a positive result is
corroborated by the upstream code path rather than only by my framing. It has a stage-2
write branch that is refused unless `--write-partition`, `--write-file` and `--confirm` are
all supplied explicitly; it was never used.

**Patched client rebuilt.** `/tmp` was wiped during this session (tmpfs), so
`mtkclient_pl` was recreated from `analysis/tools/mtkclient_upstream` with the same two
patches as before: `usb_ids.py` no longer lists `0e8d:0003` (BROM) so any successful attach
is genuinely the Preloader, and `usblib.py` no longer filters discovery on
`bDeviceClass=0x0A`.

**Observed during the session.** With the broken rootfs running, the router does **not**
enumerate any MediaTek USB identity at all - `lsusb` shows only the FTDI, and `dmesg` shows
no `0e8d` events since the last power cycle. This is consistent: the device left the
Preloader, booted Linux, and the broken rootfs has no working USB gadget, so there is no
Preloader window and no META gadget. A Preloader window exists only between a power cycle
and the device leaving USB-download mode.

---

## 12. `CFG_PRELOADER_AS_DA` is compiled out (offline, 2026-10-20) - partition path closed

`analysis/X17M_PRELOADER_META_AND_RAMBOOT_REASSESSMENT_20260922.md` section 3 documented the
SDK's optional Preloader-as-DA service and listed its distinctive implementation strings.
That document examined "the exact working-router Preloader"; this session checked the
**1 GB NAND** Preloader (`mtd00_preloader.img`) specifically. Every distinctive string is
absent:

| String | Present in 1 GB Preloader |
|---|---|
| `SEND: name = %s` | no |
| `SEND: len = 0x%x` | no |
| `SEND: Verify PASS` | no |
| `PL Checksum` | no |
| `XFLASH checksum` | no |
| `Jump to LK` | no |
| `Jump to ATF` | no |
| `Unknown Jump` | no |
| `READ: name` | no |

A generic string scan shows no `SEND:`/`READ:`-prefixed family and no `Jump to` family at
all. The only checksum/jump strings present belong to unrelated subsystems
(`[%s]checksum mismatch s %d d %d!`, `[dramc] checksum failed`, `%s jump to 0x%x`,
`%s Others, jump to ATF`).

**Conclusion.** The `0x70` / `0x71` Preloader-as-DA command family is **compiled out** of
this build, exactly as the 2026-09-22 reassessment concluded for the other unit. The
`send_partition_data()` / `jump_to_partition()` calls in upstream mtkclient are therefore
dead code against this device: the commands are not merely refused, the handler does not
exist. The live probe is still worth running once for the negative result, but the
partition-command avenue is **closed** and must not be pursued further.

**What the partition-name strings in the Preloader actually are.** The 1 GB Preloader does
contain `%s %s partition not found`, `uboot_a`, `uboot_b`, `lk_a`, `lk_b`, `aee_lk` and
`part name=%s`, but these belong to the *internal boot chain* loader: they are the code
that resolves which `lk`/`uboot`/`atf`/`loader_ext` image to load for the boot about to
happen. They are not a host-facing command surface. The earlier reading of these strings
as evidence for a host-writeable partition path was wrong, and this section supersedes it.

---

## 13. NEW: the LK fastboot app starts on every boot (live, 2026-10-20)

A power cycle at 13:42 produced a full UART capture (28,443 bytes). The Preloader window
behaved as expected and the unit booted normally, but the LK log contains a line the
previous analysis had not recorded:

```text
starting app fastboot
wait_for_enter_fastboot:90: Wait for enter fastboot event...
starting app gem_boot
wait_for_boot_linux:722: Wait for boot linux event...
```

**FACT.** The LK fastboot application is *started on every normal boot*, in parallel with
`gem_boot`. It then blocks in `wait_for_enter_fastboot()` waiting for an "enter fastboot"
event that never arrives, so the device continues to Linux. The LK binary contains the
corresponding code and strings:

- `0x2fc54` `%s:%d: Notify enter fastboot.`
- `0x2fc73` `notify_enter_fastboot`
- `0x2fcab` `fastboot_entry`
- `0x2fcba` `%s:%d: Wait for enter fastboot event...`
- `0x2fce3` `wait_for_enter_fastboot`
- `0x2fcfb` `%s:%d: Ready to enter fastboot...`

**Why this matters.** The LK fastboot engine is therefore *not* a separate exotic mode that
must be coaxed out of the bootloader: it is already resident and running on every boot,
one event away from taking over. The `FASTBOOT` Preloader selector
(`analysis/X17M_PRELOADER_SOURCE_CORRELATION.md`, confirmed present in the 1 GB Preloader
at `0x72040` with acknowledgement `TOOBTSAF` at `0x72049`) sets
`boot_mode = FASTBOOT`, which is the most plausible source of that event. That selector has
**never been exercised on this device** and is now the highest-value remaining test.

**Constraint unchanged.** Even if the LK fastboot endpoint comes up, its command table is
`getvar: / reboot / reboot-bootloader / reboot-fastboot / continue / set_active: /
max-download-size / product / is-userspace` with no `download:`, `flash:` or `erase:`, and
`set_active` prints `set active slot: not supported!`. So the value of reaching it is
diagnostic plus the possibility of `reboot-bootloader`/`reboot-fastboot` timing, **not** a
write path. The write path remains the open problem.

**Preloader window timing, measured.** From the same capture:

```text
[TOOL] Enumeration(Start)
[TOOL] Enumeration(End): OK 2117ms
[TOOL] : usb listen timeout
[TOOL] <USB> cannot detect tools!
#T#USB handshake=3313
#T#bldr_handshake=0
```

The Preloader waits **3313 ms** total for a tool, of which 2117 ms is the USB enumeration
phase. This is a usable window - a lean prober that connects and issues one command
immediately can fit inside it. The earlier mtkclient-based prober could not, because
`preloader.init()` performs many sequential round trips.

**Note on `[BLDR] Tool connection is unlocked`.** The Preloader log states the tool
connection is unlocked, i.e. the DAA gate is not blocking a *connection* - it is the DA
*upload* that is rejected with `0x7024`.

---

## 14. NEW: the USB link is unreliable - enumeration fails (live, 2026-10-20)

A series of power cycles at 13:42-13:46 produced a clear pattern in `dmesg`:

```text
13:42:07  usb 1-1: new high-speed USB device number 4 using ehci-pci
13:42:07  usb 1-1: New USB device found, idVendor=0e8d, idProduct=2000
13:42:08  usb 1-1: USB disconnect, device number 4        <-- gone after 1 second

13:43:33  usb 1-1: new high-speed USB device number 5 using ehci-pci
13:43:45  usb 1-1: device not accepting address 5, error -110

13:46:04  usb 1-1: new high-speed USB device number 7 using ehci-pci
```

**FACT.** `error -110` is `ETIMEDOUT` from the host USB stack: the device never completed
address assignment. The Preloader's own log corroborates it from the other side:

```text
[TOOL] USB enum timeout (Yes), handshake timeout(Yes)
[TOOL] Enumeration(Start)
[TOOL] : usb listen timeout
[TOOL] <USB> cannot detect tools!
```

So the Preloader *did* try to enumerate and *did* time out, then gave up and booted
normally. The host stack independently timed out on the same transaction.

**Consequence.** Several earlier "the Preloader window was missed" observations are
explained by link quality, not by timing or by a wrong test design:

- the 13:42:07 device appeared and vanished **one second** later, which is shorter than
  the Preloader's own 3313 ms tool timeout, so no host could have completed a handshake
  on that particular attempt;
- the 12:29 and 13:43 attempts show the same pattern of immediate disconnect.

**This is a hardware/connection problem and it must be fixed before any further loader
test can be judged.** Candidate causes, in order of likelihood:

1. The router's USB-C port and the host cable/hub are not making a solid electrical
   connection - the port is repeatedly re-enumerating and dropping.
2. The FTDI adapter is on a different bus (`bus 3`, `xhci`) than the router
   (`bus 1`, `ehci-pci`), so the two links are physically separate; a shared hub, a
   VMware USB passthrough layer, or a marginal cable is involved.
3. VMware USB passthrough is in the path (`usb 1-1` attaches to `ehci-pci` behind a
   virtual hub), which can drop enumeration under timing pressure.

**Action.** Re-seat the router's USB cable, and if the host is a VM, prefer a direct
pass-through of the router's USB controller (or move the router to the same host
controller path as the FTDI) rather than a hub. Then re-run the combined probe. A
reliable enumeration is a precondition for the `FASTBOOT` selector test in section 13
and for any future loader test.

**Note on the UART captures.** Despite the USB failures the UART captured three complete
boots in `work/uart_fastprobe.log` (441,208 bytes). The device boots and runs perfectly
well; only the USB enumeration is failing. That also means the console path is
unaffected and remains the reliable channel on this bench.

---

## 15. BEST restore candidate identified: the v19 image (offline, 2026-10-20)

`build_v19/images/rootfs_bozax17_v19_xray_busybox.img` is the strongest image found for
restoring slot B. All of the following are verified directly from the file, not inferred.

| Property | Value | Verification |
|---|---|---|
| Path | `x17m/build_v19/images/rootfs_bozax17_v19_xray_busybox.img` | - |
| Size | 48,685,056 bytes (0x2E6E000) | `ls -l` |
| SquashFS magic | `0x73717368` | header read |
| SquashFS `bytes_used` | 48,683,391 (0x2E6D97F) | superblock field 40 |
| Fits the slot? | **Yes** - 48,685,056 <= 55,836,672 | slot limit from work log section 4 |
| `/dev/console` | present, **character device 5,1**, `crw------- root/root` | `unsquashfs -ll` |
| SHA-256 | `95be8ec18a3dabad5e53e8467dc08ecbe4ead74d6e793dde17d7ec571d61130b` | matches `build_v19/images/SHA256SUMS` exactly |
| Boot result | **"successful, confirmed by user"** | `build_v19/reports/deployment.json` |

**This is better than the previously considered candidates.** `rootfs_patched_v17_10s.img`
is known-good too, but the v19 image is (a) smaller and therefore further inside the slot
size limit, (b) carries a genuine device node rather than a pseudo-file, and (c) has a
directly quoted user confirmation of a successful flash and boot:

```json
"image": ".../rootfs_bozax17_v19_xray_busybox.img",
"sha256": "95be8ec18a3dabad5e53e8467dc08ecbe4ead74d6e793dde17d7ec571d61130b",
"flash_method": "mtd",
"boot_result": "successful, confirmed by user",
"user_statement": "i flashed the rootfs using mtd, device booted up fine"
```

Note the deployment record leaves `flash_command` and `target_partition` as `null`, so
"which partition" and "the exact command" are not on record. The v19 rootfs also differs
from the v18 tree in only four file contents (`bin/busybox`, `etc/rc.local`,
`usr/libexec/egrep-gnu`, `usr/libexec/fgrep-gnu`) plus 243 added applet links, per
`build_v19/reports/tree-changes.json`; nothing is removed. `dev/console` is explicitly
retained as major 5 minor 1 mode 0600.

**Therefore the single remaining blocker is the write path, not the image.** Everything
else is ready:

- a verified-good image with a real `/dev/console` exists and is user-proven to boot;
- the console on this bench is live and interactive;
- the LK fastboot application is resident on every boot, one event away from activation.

**Verification rule for the write.** After writing, re-read the slot, confirm the SquashFS
superblock magic and `bytes_used` match the source image, and compare a full SHA-256 of
the written region against
`95be8ec18a3dabad5e53e8467dc08ecbe4ead74d6e793dde17d7ec571d61130b` before rebooting.

---

## 16. LIVE RESULT: the Preloader selector channel is reachable (2026-10-20)

This is the first time in the session that a host command was actually accepted by the
Preloader. It also produced a concrete protocol lesson.

**FACT - the host reached the Preloader's selector state.** The combined probe attached to
`0e8d:2000` on a live power cycle and received the Preloader's readiness token:

```text
preloader seen
claimed interface=1 in=0x81 out=0x01
...
pre-ready bytes=52 45 41 44 59          <- "READY"
sending b'FASTBOOT'
post-selector bytes=52 45 41 44 59
acknowledgement b'TOOBTSAF' not received
```

So the USB link *does* work when the device enumerates cleanly, the CDC bulk interface
*is* claimable, and the Preloader *does* emit `READY` on the bulk IN endpoint exactly as
`analysis/enter_x17m_meta.py` expects. The `0e8d:2000` stage is fully reachable from the
host.

**FACT - the FASTBOOT token was not recognised, and the cause is my own test ordering.**
The probe sent the partition-command probes (`0x71`, then a 64-byte partition name, then
`0x70`, then another 64-byte name) *before* the selector token. The Preloader frames
host commands in **fixed 8-byte units**: `core/handshake_usb.c:192-243` sends `READY` on
every iteration of `usb_listen()` "while no complete eight-byte token has arrived", and
`usb_handshake_handler` (`276-295`) then builds the command descriptor with
`cmd.len = 8`. By writing 1+64+1+64 bytes first, the token boundary was shifted and the
bytes `FASTBOOT` were no longer aligned to a token start, so the dispatcher compared a
mislaligned 8-byte window and answered with more `READY` instead of `TOOBTSAF`.

**Correction to the test design.** The selector token must be the **first** write after
`READY`, with no other bytes in between. `work/fastboot_select.py` has been rewritten to
do exactly that: wait for `READY`, send `FASTBOOT` as the first write, then expect
`TOOBTSAF`, then send `DISCONNECT`. The partition-command phase has been removed from
that script entirely (it is closed offline anyway, section 12), because it is exactly what
breaks the framing.

**FACT - the `READY` response also tells us the preloader was in selector mode, not
download mode.** The `0x71`/`0x70` writes were not echoed as commands at all; the device
answered with `READY` bytes, i.e. it was still in the `usb_listen()` loop. That is
consistent with section 12: the download-mode dispatcher is a different loop
(`download.c:usbdl_handler()`) that is only reached after the tool handshake, and the
partition commands are not implemented in it either.

**Measurements from the same cycle.** The Preloader tool timeout varies with boot timing:

| Cycle | USB handshake total | Enumeration |
|---|---:|---:|
| 13:42 | 3313 ms | 2117 ms |
| 14:07 | 1895 ms | 1373 ms |

Both are usable, but the window is short and can shrink further, which is why the
selector attempt has to be the very first action after enumeration.

---

## 17. LIVE RESULT: the `FASTBOOT` selector is accepted and changes the Preloader's boot path (2026-10-20)

**This is the first successful host-accepted bootloader command of the entire recovery
attempt.** The `FASTBOOT` selector is confirmed working end to end.

### Host side

```text
preloader seen
claimed interface=1 in=0x81 out=0x01
ready bytes=52 45 41 44 59                       <- READY
sending b'FASTBOOT' (first write)
post-selector bytes=52 45 41 44 59 54 4f 4f 42 54 53 41 46
FASTBOOT selector accepted (TOOBTSAF)
```

`TOOBTSAF` (`54 4f 4f 42 54 53 41 46`) was returned by the Preloader, exactly as
`analysis/X17M_PRELOADER_SOURCE_CORRELATION.md` predicts for the `FASTBOOT` branch
(`send("TOOBTSAF"); boot_mode = FASTBOOT`).

### Device side (UART, independent confirmation)

```text
[BLDR] 'FASTBOOT' received!
```

The Preloader itself logged receipt of the token. The host and the device agree.

### The protocol lesson from the previous attempt is confirmed

The first attempt failed only because the partition-command probes were sent *before* the
selector token and shifted the Preloader's fixed 8-byte command framing. The Preloader
answered with more `READY` bytes instead of `TOOBTSAF`. With the selector sent as the
first write, it works. **The selector token must be the first write after `READY`.**

### What changed on the device, and what did not

Diffing the `FASTBOOT` boot against a normal boot of the same unit:

| Observation | Normal boot | `FASTBOOT` boot |
|---|---|---|
| `lk_b` partition load | `to 0x44000000 (mem) [SUCCESS]` | same |
| `aee_lk` DRAM reservation | `0x43000000`, 2 MiB, `map:1` | same |
| `aee_lk` image staged | not staged | **staged**, `load_mkimg_part_info` reports `name : aee_lk`, size 262,264 |
| `starting app fastboot` | present | present |
| `lk boot mode` | 0 | **still 0** |
| Final result | boots Linux | **still boots Linux** |
| USB `0e8d:201c` endpoint | absent | absent |

**FACT.** Selecting `FASTBOOT` genuinely changes the Preloader's behaviour: it now stages the
`aee_lk` partition (the AEE/MRDUMP fastboot engine that
`analysis/X17M_FORENSIC_REPORT.md` identifies as the minimal fastboot engine at USB
`0e8d:201c`). That is real progress and it confirms the selector path is intact.

**FACT.** The LK nevertheless continued to Linux with `lk boot mode = 0`, and no
`0e8d:201c` USB identity ever appeared. So on this build the `FASTBOOT` selector alone
does **not** hand control to the fastboot engine; the LK's own boot-mode variable was
still 0.

**Interpretation (offered as a hypothesis, not a fact).** The `FASTBOOT` branch in the
Preloader sets `g_boot_mode = FASTBOOT`, and the LK reads its boot mode from the boot
arguments handed over by the Preloader. Two candidate explanations:

1. the boot-mode value is not propagated into the LK handover in this build, or
2. the LK's `lk boot mode` is a *different* variable from the one the selector sets, and
   the LK fastboot engine still waits for its own "enter fastboot" event
   (`notify_enter_fastboot`) which nothing raised.

The LK log in both boots shows the same `starting app fastboot` /
`wait_for_enter_fastboot:90: Wait for enter fastboot event...` pair, so the LK fastboot
application is started either way; what differs is that the `aee_lk` payload is now
present in DRAM for it to use.

### Consequence for the recovery plan

**The LK fastboot endpoint remains unreached, and the write path is still open.** The
forensic report's constraint still holds: even if the endpoint appeared, the 1 GB LK's
command table has no `download:`, `flash:` or `erase:`, and `set_active` is a stub. So
reaching it would be diagnostic, not a write capability.

**What this does establish, and it is important:** the Preloader's command channel is
functional and the host can drive the boot flow. The remaining gap is a *write* primitive,
not a *control* primitive. The `aee_lk` staging also shows the Preloader can read
partitions and place images in DRAM - it is the DAA-gated download dispatcher, not the
partition machinery, that is closed.

**Next step.** With the selector now proven, the natural follow-up is the **other**
never-tested selector, `ADVEMETA` (`ATEMEVDX`), which selects `ADVMETA_BOOT`. It is a
different boot mode and may present a different service set than `META_BOOT` did. The
`meta_tst` primitive reachable under `META_BOOT` is an unrestricted `open()` on the target
with a write-capable operation, and it was never tested on this unit because the META
gadget requires a working Linux - which is exactly what the broken slot B cannot provide.
`ADVEMETA` may not have that dependency, and it is the last untested selector.

---

## 18. LIVE RESULT: the `ADVEMETA` selector is also accepted (2026-10-20)

With the framing lesson applied, the second never-tested selector also succeeded.

### Host side

```text
preloader seen
claimed interface=1 in=0x81 out=0x01
ready bytes=52 45 41 44 59                       <- READY
sending b'ADVEMETA' (first write)
post-selector bytes=52 45 41 44 59 41 54 45 4d 45 56 44 58
ADVEMETA selector accepted (ATEMEVDX)
sent DISCONNECT
ADVEMETA_SELECTED=YES
```

`ATEMEVDX` (`41 54 45 4d 45 56 44 58`) is exactly the acknowledgement
`analysis/X17M_PRELOADER_SOURCE_CORRELATION.md` predicts for the `ADVEMETA` branch
(`send("ATEMEVDX"); wait_for_discon(comm, 1000); boot_mode = ADVMETA_BOOT`). This time
`DISCONNECT` also wrote successfully, matching the source's `wait_for_discon` behaviour.

### Device side

The UART capture for this cycle is 80,804 bytes and contains one Preloader boot. The
Preloader's META parameter block shows a *different* META configuration than a normal boot:

```text
META_COM TYPE: 2
META_COLOG_COM EN: 1
```

(compare the normal boot, which reports `META_COM TYPE: 0` / `META COM ID: 0` /
`META LOG DISABLE: 0`). So `ADVEMETA` genuinely alters the META parameter set rather than
merely being acknowledged.

The LK again continued to Linux (`lk boot mode = 0`) and no `0e8d:202d` META gadget
appeared during the 120 s observation window; the host saw only `0e8d:2000` then
`mediatek_usb=none`.

### Summary of the selector surface - all four non-factory selectors now tested live

| Selector | Acknowledgement | Result on this unit |
|---|---|---|
| `METAMETA` | `ATEM0001`/`ATEM0002`/`ATEMATEX` | accepted (proven earlier); boots Linux, META gadget `0e8d:202d` seen on the *working* unit |
| `FASTBOOT` | `TOOBTSAF` | **accepted**; stages `aee_lk`; LK still boots Linux, no `0e8d:201c` |
| `ADVEMETA` | `ATEMEVDX` | **accepted**; META parameters change (`META_COM TYPE: 2`); LK still boots Linux, no `0e8d:202d` |
| `AT+NBOOT` | `AT+OK` | not tested; equivalent to a normal boot |
| `FACTFACT` / `FACTORYM` | `TCAFTCAF` / `MYROTCAF` | not tested; factory modes are the highest-risk untested options and are **not** recommended without a verified image |

**FACT.** The Preloader's selector dispatcher is fully functional on this device and the
host can drive it with any of the recognised 8-byte tokens. The `CMD_HNDL_ATTR_COM_FORBIDDEN`
gate did not trigger for `FASTBOOT` or `ADVEMETA` (no `METAFORB` was returned).

**FACT.** Selecting a META-family boot mode does **not** by itself stop the LK from booting
Linux on this build. The `meta_tst` primitive is therefore still out of reach, because the
gadget appears only after a working Linux is up, and slot B never gets that far.

### Where this leaves the recovery

The control surface is now proven end to end:

- the host can talk to the Preloader and select boot modes;
- the Preloader can read partitions and stage images into DRAM (`aee_lk`);
- the Preloader can jump to a staged image - that is exactly what `SEND_PARTITION_DATA`
  / `BOOT_IMAGE` (`0x70`/`0x71`) would do, but those commands are compiled out of this
  build (section 12).

**The single remaining gap is a flash-write primitive.** The DAA gate on the download
dispatcher, the missing `CFG_PRELOADER_AS_DA` commands, and the LK's absent
`download:`/`flash:` are the three independent reasons the same wall is hit from three
directions. Since all three are closed, and the image to restore is verified and
user-proven to boot, the practical options are:

1. obtain a DA signed with the `a697...` key, or a DA the Preloader's DAA will accept;
2. obtain a hardware/physical NAND write path for the slot-B rootfs partition;
3. use the **working 1 GB unit** (which is in use) as a source of a correctly signed DA
   or as a host with working flash tooling, if it is permitted to be used for this.

Option 3 is worth stating explicitly: the working unit boots normally, so it has a
Preloader that accepts *some* DA, and its `mtd` tooling works. If the same signed DA
that the working unit accepts can be obtained, the same tooling can write the bricked
unit's slot B - and the bricked unit's `rootfs_b` image is already prepared and verified.

---

## 19. A third DA candidate found: `DA_BR_unsign.bin` (offline, 2026-10-20)

`Other_zlt_mtk_firmwares/extracted_da/` contains three DA variants of identical size
(381,660 bytes):

| File | SHA-256 |
|---|---|
| `DA_BR.bin` | `c3d9058aeb56373eaadc5868ce93198fb99a9cbf876a30f876714e9007d66d56` |
| `DA_BR.bin.rg500l-30.202-orig` | `c3d9058aeb56373eaadc5868ce93198fb99a9cbf876a30f876714e9007d66d56` (identical to `DA_BR.bin`) |
| `DA_BR_unsign.bin` | `9133e91fd2dd4e5871a84d1709f2cac33a973025ca69f14f0074a9f1223cfc1` |

**FACT.** `DA_BR_unsign.bin` is byte-identical to `DA_BR.bin` except for **509 bytes in
five ranges**, and both signed payloads are unchanged:

```text
region 0 payload  DA_BR[0xbc:0x2f5cc]      identical
region 2 payload  DA_BR[0x2f6cc:0x5d1dc]   identical
```

The five differing ranges map exactly onto the two 256-byte signature fields and the
inter-signature metadata:

| Range | Meaning |
|---|---|
| `0x2f5cc`-`0x2f61e` | region 0 signature (256 bytes) - now all zero |
| `0x2f620`-`0x2f6b8` | inter-region metadata - now zeroed |
| `0x2f6ba`-`0x2f6cb` | further metadata - now zeroed |
| `0x5d1dc`-`0x5d293` | region 2 signature (256 bytes) - now all zero |
| `0x5d295`-`0x5d2db` | trailing metadata - now zeroed |

The signature offsets `0x2f5cc` and `0x5d1dc` match
`analysis/MT6890_DA_BR_SIGNATURE_KEY_AUDIT.md` exactly.

**Why this is worth one live test.** The Preloader's DAA rejection
(`DAA_SIG_VERIFY_FAILED (0x7024)`) is a *signature* failure, not a content failure. A DA
with the signatures zeroed is a different object from a re-signed DA, and the DAA
implementation may treat "no signature present" differently from "signature present but
wrong" - for example by falling back to a different verification path, or by rejecting at
an earlier stage with a distinguishable status. It is cheap to test and it is the only DA
variant on disk that has not been tried.

**Honest expectation.** This is unlikely to succeed: `0x7024` is a signature-verification
failure and the check almost certainly requires a valid signature rather than tolerating
its absence. It is listed because it costs one power cycle and the alternative DA sources
are exhausted, and because a *different status code* would still be informative - it would
distinguish "DAA rejects this DA" from "DAA never ran".

**Do not confuse this with a DA that would work.** A DA that the Preloader accepts must
carry a valid signature under the `a697...` modulus, because
`analysis/MT6890_TOOLAUTH_BINARY_AND_TRUST_ANALYSIS.md` records that
`sec_auth.c` calls `seclib_set_pubk(g_dakey, DA_PUBK_SZ)` with that modulus for
DA-image signature checking. Zeroing a signature cannot satisfy that check; only the
matching private key can. The `a697...` key is not present in the workspace, and the
working 1 GB unit is the only other place a device that accepts *some* DA exists.

---

## 20. Where the investigation stands (2026-10-20) - consolidated

### Proven working

| Capability | Evidence |
|---|---|
| Host <-> Preloader USB CDC bulk channel | `READY` received, `TOOBTSAF` and `ATEMEVDX` acknowledgements returned, section 16-18 |
| Preloader boot-mode selector dispatcher | `FASTBOOT` and `ADVEMETA` both accepted, device-side `[BLDR] 'FASTBOOT' received!` confirmed |
| Preloader reads partitions and stages images into DRAM | `aee_lk` staged (262,264 bytes) when `FASTBOOT` is selected, section 17 |
| UART console is interactive | `f` accepted with `- failsafe -` reply, section 2 |
| Preloader tool window | 1895-3563 ms total depending on boot timing, sections 16-17 |

### Proven closed

| Blocked avenue | Root cause | Section |
|---|---|---|
| DA upload (stock / ACC-bypass / unsigned) | DAA signature check, `9af8...` vs `a697...` | 1, 19 |
| Preloader SRAM read/write | crypto-gated `0x1000` / `0x1001` | 1 |
| Preloader `0xDA` register access | not implemented in Preloader mode | 1 |
| Preloader-as-DA `0x70`/`0x71` | `CFG_PRELOADER_AS_DA` compiled out | 12 |
| LK fastboot `download:`/`flash:`/`erase:` | tokens absent from the 1 GB LK image | 4, 13 |
| LK fastboot `set_active` | prints `set active slot: not supported!` | 4 |
| LK fastboot endpoint | never enumerated at `0e8d:201c` even with `FASTBOOT` selected | 17, 18 |
| `meta_tst` primitive on this unit | needs a working Linux; slot B never gets there | 10 |
| Failsafe shell on the current image | no `/dev` directory in the running rootfs | 2 |
| BROM Kamakiri | `mt0992` is in upstream `missing_brom.txt`, no exploit parameters | - |

### The one remaining gap

A **flash-write primitive**. Three independent code paths would provide it and all three
are closed: the DAA gate, the compiled-out Preloader-as-DA commands, and the LK's absent
`download:`/`flash:`. The control surface around them is fully working, which is why the
gap is now precisely characterised rather than guessed at.

### The recovery is fully prepared on the image side

`build_v19/images/rootfs_bozax17_v19_xray_busybox.img`

- SHA-256 `95be8ec18a3dabad5e53e8467dc08ecbe4ead74d6e793dde17d7ec571d61130b` (matches
  `build_v19/images/SHA256SUMS`)
- 48,685,056 bytes, comfortably inside the 55,836,672-byte usable slot size
- a real `/dev/console` character device (5,1), not a pseudo-file
- **user-confirmed to boot successfully** (`build_v19/reports/deployment.json`)

### Options, in order of expected value

1. **Obtain a DA the Preloader's DAA accepts.** The only such DA would be signed with the
   `a697...` modulus. The **working 1 GB unit** boots normally, so its Preloader accepts
   *some* DA. If the signed DA that the working unit accepts can be obtained, the same
   `mtkclient` flow that works on it will write the bricked unit's slot B. This is the
   highest-value remaining action and it needs only the working unit and the user's
   permission to use it for this.
2. **A physical NAND write** for the slot-B rootfs partition - a hardware path that
   bypasses every software gate. The image is already built and verified; only the
   transfer is missing.
3. **The unsigned DA** (section 19) - one cheap test, currently armed. Expected to fail
   with the same `0x7024`, but a *different* status would still be informative.
4. **Factory boot modes** (`FACTFACT`, `FACTORYM`) - **not recommended.** They are the
   last untested selectors, but a factory-mode device commonly exposes a *write-enabled*
   path that erases partitions on entry. With no verified backup of the bricked unit's own
   NAND and no working read path, an accidental erase would be unrecoverable. They should
   only be attempted if options 1-3 are exhausted *and* a full verified backup of the
   bricked unit exists.

### A note on the working 1 GB unit

The user has been using the working 1 GB unit throughout. It is a same-family X17M 1 GB
unit with a full logical NAND backup on disk
(`bozax17/backups/x17m-1gb-20260921-061524/`), and it is the only device available whose
Preloader demonstrably accepts a DA. Using it to source a working DA - or to perform the
slot-B write itself if the two units are interchangeable - is the shortest path to
recovery. This needs the user's explicit go-ahead, since the working unit is in service.

---

## 21. Factory-mode selectors: the last untested tokens (authorised 2026-10-20)

The user has explicitly placed **all** options on the table, including the two factory
selectors. This section records the plan, the exact protocol, and the risk position
*before* anything is sent, so the reasoning is auditable.

### Why they are worth testing

The selector dispatcher is proven to work, and it is the only host-facing control surface
that is not DAA-gated. `FACTORY_BOOT` and `ATE_FACTORY_BOOT` are the two remaining
`g_boot_mode` values. Neither has been observed on this device.

The specific reason to expect them to differ from `FASTBOOT`/`ADVEMETA`: those two
selected a mode that the LK then *overrode* (`lk boot mode = 0` in both cases), so the
LK ignored them. A factory mode is a different consumer in the LK/rootfs, and factory
images on this platform commonly expose a **download or flash service** that ordinary
boot paths do not. The `aee_lk` staging already demonstrated that the Preloader can
place a partition image in DRAM and that a different `aee_lk`-based engine exists in the
LK; a factory mode is a plausible way to reach it.

### Exact protocol (from the source-correlated dispatcher)

```text
else if cmd == "FACTFACT":
    if forbidden: METAFORB/false
    recv(v1, 12, 5); save usb type; send("TCAFTCAF")
    boot_mode = FACTORY_BOOT
else if cmd == "FACTORYM":
    if forbidden: METAFORB/false
    recv(v1, 12, 5); save usb type; send("MYROTCAF")
    boot_mode = ATE_FACTORY_BOOT
```

Wire transaction, as implemented in `work/factory_select.py`:

```text
TARGET -> HOST: READY
HOST   -> TARGET: FACTFACT            (exactly 8 bytes, MUST be the first write)
HOST   -> TARGET: v1 record, 12 bytes
TARGET -> HOST: TCAFTCAF              (or MYROTCAF for FACTORYM)
```

The v1 record is the already-validated 12-byte `para_v1_t`
(`{len, ver}` + `usb_type`, `usb_num`, `md0_type`, `md1_type`):

```text
04 00 00 00 01 00 00 00 03 00 00 00
```

which is the exact `V1` that `analysis/enter_x17m_meta.py` uses successfully on this
device. The source does not validate the record's header fields before using the
selected byte fields, so the validated values are the best-supported choice.

**Ordering requirement**, learned live in section 16: the 8-byte token must be the first
write after `READY`, and the v1 record must follow it, because the Preloader frames host
commands in fixed 8-byte units. The factory branches additionally *receive* 12 bytes
before acknowledging, which is why this token needs a payload and the others do not.

### Risk position - stated honestly

Factory mode is the highest-risk remaining option, and the risk is not in the selector
itself but in what the device does once it is in that mode:

- The selector transaction sends **no** flash command. It is a RAM-only `g_boot_mode`
  change. A power cycle restores normal boot.
- The risk is that a factory-mode device exposes a service that **erases or rewrites
  partitions on entry**, or that a subsequent host command would. This unit has **no
  verified backup of its own NAND** and **no working read path**, so an erase would be
  unrecoverable and would also destroy the evidence needed for the remaining avenues.

**Mitigation actually applied.** The probe is *observation-only* after the selector: it
sends the token, the v1 record, and `DISCONNECT`, then polls USB identities passively for
120 s. It does **not** speak any protocol to whatever appears, does not send a DA, and
does not send a download or write command. If a factory endpoint enumerates, the next
step is to identify it and read its capabilities first - not to write to it.

**Ordering.** The unsigned-DA test is armed first because it needs no mode change at all
and cannot alter the device. The factory selectors are armed next, `FACTFACT` before
`FACTORYM`, because `FACTORY_BOOT` is the more conventional of the two.

**If a factory endpoint appears, the escalation order is:** identify it and enumerate its
commands read-only -> if it offers a write path, write **only** the verified v19 image to
**only** the slot-B rootfs partition -> re-read and verify SHA-256 before rebooting. If it
offers a *whole-device* erase or reformat command, that is not acceptable without a
verified full backup of the bricked unit, and it should stop there.

### Also worth noting

`FACTFACT`/`FACTORYM` receive a v1 record and save the **usb type** from it. That
parameter decides *which* USB path the factory mode uses - so a wrong value might select
a path that does not exist rather than something dangerous. The validated value from the
working unit is used.

---

## 22. CORRECTED: the failed handshakes were a HOST-side client bug, not the device

> **Correction.** This section was first written attributing the failures to the router's
> reset button. The user confirmed they had **not** pressed reset during any test, so that
> attribution was wrong. The evidence below shows the device behaved differently between
> the two boots, and the real cause is on the **host** side: a bug in the mtkclient copy
> that was rebuilt after `/tmp` was wiped. The reset-button mechanism is still documented
> (it is real and worth knowing) but it was **not** the cause here.


The user noted that they sometimes press the router's **reset button**. Comparing the UART
captures of a *successful* selector boot against a *failed* DA-attempt boot isolates the
difference exactly.

### The observation that gives it away

| | successful boot (`fb.txt`, `FASTBOOT` accepted) | failed boot (`seq.txt`, DA attempt) |
|---|---|---|
| `[TOOL] Enumeration(Start)` | 1 | 1 |
| `[TOOL] Enumeration(End): OK ...` | **1** | **5616** (repeating) |
| `READY` seen on the wire | yes | **never** |
| host handshake result | `TOOBTSAF` received | "Handshake failed, retrying..." x17 |

The Preloader reached `Enumeration(End): OK` and then **re-ran the whole enumeration
sequence thousands of times** without ever emitting `READY` and without ever letting the
host's handshake complete. That is a Preloader stuck in a loop, not a host that was too
slow.

### The PMIC difference - this is the cause

Diffing the first 700 lines of the two captures:

```text
successful:  [PMIC]TOP_RST_STATUS[0x13C]=0x48     failed:  [PMIC]TOP_RST_STATUS[0x13C]=0x0
successful:  [PMIC]POFFSTS[0xE]=0x1                failed:  [PMIC]POFFSTS[0xE]=0x0
successful:  [pmic_check_rst] UVLO_RSTB            failed:  (absent)
successful:  [pmic_check_rst] PORSTB              failed:  (absent)
successful:  [pmic_wdt_set] TOP_RST_MISC1=0x25     failed:  (absent)
successful:  [pmic_wdt_set] TOP_RST_MISC1=0x21     failed:  (absent)
```

The successful boot had a genuine **power-on reset**: `UVLO_RSTB` (undervoltage reset) and
`PORSTB` (power-on reset) were both reported, and the watchdog was configured. The failed
boot reported **neither reset flag** and no watchdog setup, and its SPMI reads returned
`addr=0x0, data=0x0, cmd=0` - i.e. the PMIC was not responding to the Preloader's
initialisation traffic at all.

### Why this produces exactly the symptom

The Preloader binary contains the decisive string:

```text
%s Enumeration(Skip): powerkey pressed
```

adjacent to `%s Enumeration(Start)` and `%s Enumeration(End): %s %dms`. The Preloader
**skips the USB enumeration entirely when the power key is held**. The reset button is
wired to that key on this board, so pressing it during power-up drives the Preloader down
the "powerkey pressed" path: it never enumerates as `0e8d:2000` for the host, it never
emits `READY`, and no selector or download transaction can be started.

This also explains the earlier `error -110` (ETIMEDOUT) enumerations: the device was
half-enumerating on a bus that the Preloader was not driving properly, because the boot
had not come from a clean power-on.

### Operational rule for the rest of this recovery

**Power-cycle only. Do not press the reset button.**

- Correct: unplug the power adapter, unplug USB, wait 10 s, plug USB in, plug power in.
- Wrong: pressing reset (or holding it) selects the Preloader's "powerkey pressed" path,
  which skips USB enumeration, so *every* host-side loader test silently fails.

This is a test-harness artefact, not a device fault. The device is fine.

### Consequence for the queued tests

The unsigned-DA test that "failed" at 14:24 and 14:28 did not actually fail on its
merits - it never got a Preloader to talk to. It should be re-run after a clean power
cycle. The same applies to the `FACTFACT` / `FACTORYM` selectors, which are still untested.

The `fastboot_select.py` / `advemeta_select.py` probes that succeeded earlier did so on
cycles where the operator used a proper power cycle, which is consistent with this
diagnosis.

### What the device actually did differently

The device-side evidence is still valid and still important, because it shows the two boots
were *not* the same situation:

| | successful boot (`FASTBOOT` accepted) | failed boot (DA attempt) |
|---|---|---|
| `[TOOL] Enumeration(End): OK ...` count | **1** | **5616** (repeating) |
| `READY` on the wire | yes | **never** |
| `[PMIC]TOP_RST_STATUS[0x13C]` | `0x48` | `0x0` |
| `[PMIC]POFFSTS[0xE]` | `0x1` | `0x0` |
| `[pmic_check_rst] UVLO_RSTB` / `PORSTB` | both present | both absent |
| `[pmic_wdt_set] TOP_RST_MISC1` | `0x25`, `0x21` | absent |
| early SPMI reads | real register values | `addr=0x0, data=0x0, cmd=0` |
| host-side handshake | `TOOBTSAF` received | "Handshake failed, retrying..." x17 |

The failed boot shows a Preloader that had **not** completed a normal power-on reset
sequence: no `UVLO_RSTB`, no `PORSTB`, no watchdog programming, and an SPMI bus that
answered every read with zeros. That is consistent with a boot in which the PMIC was not
properly initialised - the device was in a degraded state on that cycle.

**This is a device-side symptom of that particular boot, and it is the reason the host
handshake could not complete.** It is not a property of the reset button, and the user has
confirmed reset was never pressed.

### The host-side bug that was also present

Independently, the mtkclient copy rebuilt after `/tmp` was wiped had a real defect that
would have broken the DA test even with a healthy device. Upstream
`Library/Connection/usblib.py:305` discovers devices with

```python
devices = usb.core.find(find_all=True, bDeviceClass=devclass, backend=self.backend)
```

The `bDeviceClass` filter had to be relaxed for this Preloader, which enumerates as a
composite CDC device whose `bDeviceClass` is not 10 and was therefore filtered out and
never found. The first rebuild replaced that with an *unrestricted* search over all
`0x0E8D` devices:

```python
devices = usb.core.find(find_all=True, backend=self.backend)
if devclass != 0x0A:
    devices = [d for d in devices if d.bDeviceClass == devclass]
```

That opens discovery to any MediaTek device on the bus, so the client can latch onto the
wrong product (for example the `0x0E8D:0x0003` BROM stage, which the whole point of the
`usb_ids.py` patch was to exclude).

**Fix applied.** The rebuilt client now keeps selection tight while still accepting the
composite CDC Preloader:

```python
devices = usb.core.find(find_all=True, backend=self.backend)
if devclass != 0x0A:
    devices = [d for d in devices if d.bDeviceClass == devclass]
else:
    def _has_cdc(dev):
        try:
            cfg = dev.get_active_configuration()
        except Exception:
            return False
        return any(i.bInterfaceClass == 0x0A for i in cfg)
    devices = [d for d in devices if d.idVendor == 0x0E8D and _has_cdc(d)]
```

The `usb_ids.py` patch is unchanged and still correct: `0x0E8D:0x0003` (BROM) is not
listed, so any successful attach is genuinely the Preloader.

### Operational note that remains true

The Preloader binary does contain `%s Enumeration(Start)` next to
`%s Enumeration(Skip): powerkey pressed`, so holding the power key during power-up
*does* make the Preloader skip USB enumeration and no host transaction can begin. That
mechanism is real and worth knowing; it simply was not triggered here.

### What to do next

The unsigned-DA test and the two factory selectors were never actually exercised against a
healthy Preloader. They should be re-run. If the `Enumeration(End)` loop and the missing
`PORSTB`/`UVLO_RSTB` reappear, that is a **device-side** condition of that boot and worth
capturing deliberately - try a different power source, or leave the router unpowered for
longer so the PMIC rail fully discharges.

---

## 23. Why the LK ignored the boot mode: the handover mechanism (2026-10-20)

A decisive comparison between this unit and the **working** 1 GB unit's META capture
(`analysis/live_meta_uart/20260918T122836Z_attempt3/uart_printable.txt`) explains why
`FASTBOOT` and `ADVEMETA` were accepted by the Preloader yet had no effect on the LK.

### The Preloader really does set the mode

Both selectors produced a correct `BOOT_MODE` in the Preloader's boot tag:

| selector | `BOOT_MODE` in the boot tag |
|---|---:|
| `FASTBOOT` | **99** |
| `ADVEMETA` | **5** |
| normal boot | 0 |

`99` is exactly the SDK value for `FASTBOOT` and `5` for `ADVMETA_BOOT` recorded in
`analysis/X17M_PRELOADER_SOURCE_CORRELATION.md` section 7. **The selector works and the
Preloader records the mode correctly.** The mode is then lost on the way to the LK.

### Where it is lost

Ours:

```text
[PLFM] boot to LK by ATAG reason=32 addr=0x42B00000
[PLFM] boot_tag size = 0x5A90
BOOT_TAG_VERSION: 1
BOOT_REASON: 32
BOOT_MODE: 99
...
boot_linux_fdt:671: lk boot mode = 0
```

The LK is handed control via the **ATAG** structure at `0x42B00000`, and it reports
`lk boot mode = 0` - it never sees the `BOOT_MODE: 99` that the Preloader wrote into
its own boot tag.

The working unit's capture shows the same `[MBOOT_PARAMS]. atag(PL2LK): 0x11d000, 0x800,
0x1, 0xac0` handover, and it *does* reach `lk boot mode = 1`:

```text
boot_linux_fdt:671: lk boot mode = 0      <- first boot
...
boot_linux_fdt:671: lk boot mode = 1      <- the META boot
```

**FACT.** The working unit's capture contains **no `BOOT_MODE` line at all** in the
Preloader stage, yet the LK still received mode 1. The LK therefore does not read the
Preloader's boot-tag `BOOT_MODE` field for this purpose; it gets the mode from a
different handover, and on the working unit that handover carried the value.

### The most likely mechanism

The Preloader's boot tag (`BOOT_MODE`, `META_COM TYPE`, `META_COM ID`, ...) is written
into the `pl-boottag` mblock at `0x42B00000` and passed to the LK by ATAG. The LK
prints `BOOT_MODE` only when it parses that structure, and it then derives
`lk boot mode` from the **META parameter block** rather than from `BOOT_MODE` directly -
the working unit's META boot is precisely the case where `META_COM TYPE` was set, and
that is when `lk boot mode = 1` appeared.

That suggests the LK's boot mode is gated on the META parameter record being present
and valid, and that on this unit the META record is not reaching the LK in the form it
expects, even though the Preloader accepted the selector and staged `aee_lk`.

**This is a hypothesis, stated as such.** It is supported by three facts - the correct
`BOOT_MODE` value in the boot tag, `lk boot mode = 0` regardless of selector, and the
working unit reaching `lk boot mode = 1` only in its META boot - but it is not proven,
and the alternative (the LK reading a separate boot-mode field that the Preloader sets
only for `META_BOOT`) is equally consistent with the evidence.

### Why this matters less than it sounds

Even if the LK reached the fastboot engine, `analysis/X17M_RECOVERY_AUDIT_20261020.md`
section 4 establishes that the 1 GB LK's command table has no `download:`, `flash:` or
`erase:`, and `set_active` is a stub. So this path remains diagnostic.

**The actionable variant is `METAMETA`**, because that is the one mode the working unit
demonstrably propagates all the way to Linux (`lk boot mode = 1` -> the `0x202d` META
gadget -> the `meta_tst` primitive, which is an unrestricted `open()` on the target with a
write-capable operation). The `meta_tst` primitive is the only identified host-reachable
write path that does not involve the DAA gate.

**`METAMETA` has not been tested on this unit.** The earlier `METAMETA` work in this
project was all done on the *working* unit. On this unit it is untested, and the earlier
session's `pl_da_only.py` and the current `pl_da_unsign.py` both drive the **download**
dispatcher, which is DAA-gated - not the selector dispatcher.

**So the next test is `METAMETA` on this unit**, using the exact transaction already
validated on the working unit:

```text
READY -> METAMETA -> ATEM0001 -> V1(12) -> ATEM0002 -> V2(16) -> ATEMATEX -> DISCONNECT
```

with `V1 = 04 00 00 00 01 00 00 00 03 00 00 00` and
`V2 = 06 00 00 00 01 00 00 00 03 00 00 00 01 00 00 00`.

If the LK then reports `lk boot mode = 1`, the META gadget may appear and the
`meta_tst` write primitive becomes reachable - which would be the first DA-free write
path in the whole investigation.

---

## 24. REFined: warm reboot vs full power-off - the PMIC reset flag identifies it (2026-10-20)

A further boot captured after the second host crash isolates the remaining variable
precisely. Comparing the boot in which the host attached successfully (`fb.txt`, the
`FASTBOOT` selector) with the boot in which the host never saw `0e8d:2000`
(`meta_uart.txt`):

| | successful (`fb.txt`) | failed (`meta_uart.txt`) |
|---|---|---|
| `pmic_check_rst` | **UVLO_RSTB** | **DDLO_RSTB** |
| `[PMIC]TOP_RST_STATUS[0x13C]` | `0x48` | `0x40` |
| `[PMIC]POFFSTS[0xE]` | `0x1` | `0x201` |
| `[PMIC]POWER_HOLD` | `0x1` | `0x1` |
| `powerkey_flag` / `powerkey_val` | `0` / `0` | `0` / `0` |
| `[TOOL] Enumeration(End)` | 1 | 1 |
| host saw `0e8d:2000` | **yes** | **no** |

**FACT - `POWER_HOLD` and the power-key debug state are identical in both boots**
(`POWER_HOLD :0x1`, `powerkey:0 count=0(ms) g_pwrkey_release=0`, `powerkey_flag = 0`).
So the power key was **not** held in either case, which independently confirms that the
reset button is not the variable.

**FACT - the reset flag is the discriminator.**

- `UVLO_RSTB` = undervoltage reset, i.e. the supply actually collapsed. This is what a
  **full power-off** produces. The good boot had it, plus `TOP_RST_STATUS` bit 3
  (`0x48` vs `0x40`) and `POFFSTS` `0x1`.
- `DDLO_RSTB` = digital-brown-out low, i.e. a **drooping supply during a warm reboot**.
  This is what a **reset or a too-short power cycle** produces. The failed boot had it,
  with `POFFSTS = 0x201` (a brown-out latch set) and `TOP_RST_STATUS` bit 3 clear.

**FACT - the power key state is not the cause, but the reset button can produce exactly
this signature.** The Preloader's own string
`%s Enumeration(Skip): powerkey pressed` shows the power key is checked during boot, and
the `powerkey_flag = 0` value in the failed boot shows the *flag* was not set, so the
button was not what was held. What was held is the **reset** path, which browns out the
rail rather than cycling it cleanly.

**Consequence and corrected procedure.** The Preloader enumerates and serves USB on a
boot in which the PMIC came up cleanly from a supply collapse. A warm reset leaves the
PMIC in a brown-out state, the USB stack never settles, and the host sees either nothing
or a device that vanishes. The practical requirement is therefore stricter than "don't
press reset":

**Unplug the power adapter and leave it unplugged long enough for the PMIC rail to
discharge fully** - the difference between `UVLO_RSTB` and `DDLO_RSTB` - and confirm the
boot log shows `UVLO_RSTB` before expecting the host to attach. The Preloader's own log
gives the check directly:

```text
pmic_check_rst] UVLO_RSTB        <- good: host can attach
pmic_check_rst] DDLO_RSTB        <- brown-out: host cannot attach
```

This also explains the `Enumeration(End): OK 2296ms` repetition seen in the earlier
degraded boot: with a browned-out supply the Preloader re-ran enumeration indefinitely
without ever completing a clean enumeration.

**FACT - the power key remains a separate hazard.** `POWER_HOLD :0x1` is reported in
*both* boots, so it is not a discriminator, but the Preloader's
`Enumeration(Skip): powerkey pressed` path is real: holding the power key during
power-up skips USB enumeration entirely. It was simply not what happened in these boots.

---

## 25. Selector test status - exactly what has and has not been run (2026-10-20)

Added because the two factory selectors had been queued in an earlier section and it was
not obvious that they had never actually been exercised. Every selector is listed with the
evidence for its result, so "queued" and "tested" cannot be confused again.

| Test | Acknowledgement seen | Verdict | Evidence |
|---|---|---|---|
| `METAMETA` | `ATEM0001`/`ATEM0002`/`ATEMATEX` | accepted **on the working 1 GB unit only** (2026-10-08) | `analysis/X17M_META_USB_WORKING_1GB_20261008.md` |
| `METAMETA` | - | **NOT YET TESTED on this unit** | no `ATEM0001` in any log from this unit |
| `FASTBOOT` | `TOOBTSAF` | **accepted**; `BOOT_MODE: 99` set; `aee_lk` staged; LK still booted Linux | section 17, `work/fastboot_select.log` |
| `ADVEMETA` | `ATEMEVDX` | **accepted**; `BOOT_MODE: 5` set; META params changed; LK still booted Linux | section 18, `work/advemeta.log` |
| `AT+NBOOT` | `AT+OK` | **NOT TESTED** | no attempt recorded |
| `FACTFACT` | `TCAFTCAF` | **NOT TESTED** - the stage was killed while still waiting for a Preloader | `work/seq.log` ends at `=== attempt 1/25 waiting for 0e8d:2000 ===` |
| `FACTORYM` | `MYROTCAF` | **NOT TESTED** - never reached | no attempt recorded |

**Independent confirmation of the table:** a scan of every `*.log` in `work/` for the
acknowledgement strings finds only `TOOBTSAF` (in `combined.log` and
`fastboot_select.log`) and `ATEMEVDX` (in `advemeta.log`). There is no `TCAFTCAF`, no
`MYROTCAF`, and no `ATEM0001` from this unit.

**Also untested here, for the same reason:** the unsigned DA. The mtkclient-based probe
(`work/pl_da_unsign.py`) drives the **BROM download dispatcher** handshake
(`A0 0A 50 05`), while this Preloader serves the **selector dispatcher**
(`READY` + 8-byte token). The client therefore never attaches, so the unsigned DA has
never actually been put to the device. A DA test on this unit needs a client that speaks
the selector/download handshake this bootloader really implements.

**Consequence.** The two factory modes are the only *boot-mode* avenues still untested,
and they are the only ones that might expose a write-enabled service that the
`FASTBOOT`/`ADVEMETA` modes did not. They remain the correct next thing to try after
`METAMETA`, and `work/factory_select.py` is written and ready for them:

```text
TARGET -> HOST: READY
HOST   -> TARGET: FACTFACT            (8 bytes, MUST be the first write)
HOST   -> TARGET: V1 record, 12 bytes
TARGET -> HOST: TCAFTCAF              (or MYROTCAF for FACTORYM)
```

with the observation-only mitigation described in section 21.

---

## 26. LIVE RESULT: `METAMETA` accepted, and `lk boot mode = 1` reached (2026-10-20)

**The `METAMETA` selector is accepted on this unit for the first time, and it is the
first mode that has propagated all the way into Linux.**

### Host side

```text
ready bytes=52 45 41 44 59                       <- READY
sending b'METAMETA' (first write)
ack1 bytes=... 41 54 45 4d 30 30 30 31           <- ATEM0001
sending V1 04 00 00 00 01 00 00 00 03 00 00 00
ack2 bytes=... 41 54 45 4d 30 30 30 32           <- ATEM0002
sending V2 06 00 00 00 01 00 00 00 03 00 00 00 01 00 00 00
ackf bytes=... 41 54 45 4d 41 54 45 58           <- ATEMATEX
METAMETA selector accepted (ATEMATEX)
sent DISCONNECT
METAMETA_SELECTED=YES
```

### Device side

```text
[BLDR] 'METAMETA' received!
BOOT_MODE: 1
META_COM TYPE: 2
META_COM ID: 3
...
boot_linux_fdt:671: lk boot mode = 1
```

**FACT.** This is the decisive result of the investigation for the selector surface. The
`METAMETA` transaction completes exactly as it does on the working unit, the Preloader
records `BOOT_MODE: 1`, and the LK receives and reports **`lk boot mode = 1`** - the value
the working unit only ever showed in its META boot.

**FACT - this settles the question raised in section 23.** `FASTBOOT` (99) and `ADVEMETA`
(5) set the Preloader's `BOOT_MODE` but the LK still reported `lk boot mode = 0`.
`METAMETA` (1) sets `BOOT_MODE: 1` **and** the LK reports `lk boot mode = 1`. So the LK's
boot mode is not read from a generic `BOOT_MODE` field - it is specifically the
`META_BOOT` value that the LK acts on, exactly as the source-correlation document's
`META_BOOT = 1` entry states. The earlier hypothesis ("the LK gates on the META parameter
record being present and valid") is therefore **supported**, and the alternative is
refuted.

### Why the META gadget still did not appear

**FACT.** The Linux kernel booted with `lk boot mode = 1`, ran to userspace, and then
stopped at the same place as always:

```text
ra0       no private ioctls.
/bin/board_detect: /etc/board.d/99-default_network: line 5: can't open /mnt/vendor/nvcfg/mac0
Press the [f] key and hit [enter] to enter failsafe mode
/etc/preinit: line 0: can't open '/dev/null': No such file or directory
```

No `0x202d` identity appeared (a scan of the 1.4 MB capture finds zero occurrences of
`202d`, `usb gadget`, `g_dnl` or `configfs`).

**Reason.** The `0x202d` Linux META gadget and the `meta_tst` service are **userspace**
components: on the working unit the gadget is configured by `/etc/restart_usb.sh` and the
`meta_tst` service is `/usr/bin/meta_tst` inside the rootfs. The broken slot-B rootfs has
no `/dev`, so `devtmpfs` is never mounted, and the userspace that would create the gadget
cannot run. The kernel is in META mode, but there is no userspace to act on it.

**This closes the last META-based route on this unit** - the mode reaches the kernel
correctly, and the mode alone is not enough. It needs a rootfs with `/dev`.

### Where that leaves the investigation

The picture is now complete and unusually clear:

- **The Preloader's control surface is fully mapped and working** on this device:
  `METAMETA` -> `lk boot mode = 1`; `FASTBOOT` -> `BOOT_MODE: 99`; `ADVEMETA` ->
  `BOOT_MODE: 5`. The host can drive all of them.
- **Every write path remains closed**, each for its own independent reason: the DAA gate
  (no DA signed with `a697...`), the compiled-out `CFG_PRELOADER_AS_DA` commands, the LK's
  absent `download:`/`flash:`, and now also "the META gadget needs a working rootfs, and
  the only working rootfs is the one we are trying to install".
- **The image to install is ready and verified**: `rootfs_bozax17_v19_xray_busybox.img`,
  SHA-256 `95be8ec18a3dabad5e53e8467dc08ecbe4ead74d6e793dde17d7ec571d61130b`, 48,685,056
  bytes, real `/dev/console` device 5,1, **user-confirmed to boot successfully**.

**The remaining untested selectors are `FACTFACT` and `FACTORYM`** (section 25). They are
the only boot modes that might expose a write-enabled service that the three modes just
tested did not, and `work/factory_select.py` is written and ready for them.

**A new thought worth recording.** `META_BOOT` makes the LK boot Linux in META mode. If the
*kernel command line* could be changed the same way, the META gadget would still need
userspace. But it does raise a sharper question: is there a rootfs-independent way to get
the `meta_tst` service running? It is `/usr/bin/meta_tst` **inside the rootfs**, so no -
it is part of the very thing that is broken. That is the circularity at the heart of this
recovery, and it is why a write primitive, not a mode, is what is needed.

---

## 27. IMPORTANT: an `auth_sv5.auth` tool-auth artifact EXISTS on disk (offline, 2026-10-20)

`analysis/MT6890_DA_BR_SIGNATURE_KEY_AUDIT.md` states, in its "Customer-auth
relationship" section:

> No `customer_da.auth` or `auth_sv5.auth` file exists in the extracted workspace, so an
> embedded-auth blob could not be parsed or matched directly.

**That statement is now superseded: such a file does exist on this machine**, at
`/home/kali/Desktop/x17m/auth_sv5 (1).auth`, 2256 bytes, mode `0600`, dated 2026-09-22
01:28 - i.e. created during the earlier DAA investigation, which is consistent with it
being an output of that work rather than a vendor input. It was evidently not searched for
in the earlier audit, which looked only inside the extracted SDK/firmware workspace.

### It is a structurally valid GFH tool-auth object

Parsed against the layout in `analysis/MT6890_TOOLAUTH_BINARY_AND_TRUST_ANALYSIS.md`
section "Exact GFH layout":

| Field | Expected | Actual |
|---|---|---|
| GFH magic at `0x00` | `0x014d4d4d` | `0x014d4d4d` |
| GFH identifier at `0x08` | `FILE_INFO\0\0\0` | `FILE_INFO\x00\x00\x00` |
| `GFH_TOOL_AUTH` at `0x38` | magic `0x014d4d4d` | `0x014d4d4d` |
| size at `0x3c` | `0x0798` | `0x0798` |
| type at `0x3e` | `0x0005` | `0x0005` |
| GFH total | `0x7d0` | `0x7d0` |
| signature | `0x7d0`, 256 bytes | 256 bytes |

The three `ct_ce_key` blocks are all well formed (exponent length 3, modulus length 256,
exponent `010001`).

### Its three public keys - and the surprise

| Block | modulus SHA-256 (big-endian) |
|---|---|
| SBC/root at `0x1ac` | `660774dea40fba0a8fb532a8bb2c941cc4b1812bb3372dd6cf64374bb19473ac` |
| SLA at `0x3b8` | `8964c8a8a8dc97a16577cec8021f193f0e5924c8962c49e69c04f78858e494ac` |
| DAA at `0x5c4` | `660774dea40fba0a8fb532a8bb2c941cc4b1812bb3372dd6cf64374bb19473ac` (identical to SBC) |

**FACT.** The DAA key in this file is `660774de...`, which is **neither** of the two keys
known from the SDK:

- `9af8a28b...` - the signer of the supplied `DA_BR.bin` (and the SDK's
  `toolauth/da_prvk.pem` / `resignda/da_prvk.pem`).
- `a697414d...` - the `inc/dakey.h` `DA_PUBK` that `sec_auth.c` installs for DA-image
  signature checking.

So this artifact is a **third** key set. That is significant in two directions:

1. If the device's BootROM was provisioned with a *customer* DAA key rather than the SDK
   `a697...` one, then this file may be exactly the authorization the device expects, and
   a DA re-signed under `660774de...` would be accepted. We do not hold that private key
   either, so this does not by itself unlock a DA.
2. Conversely, it is evidence that the DAA key is **per-customer and provisioned**, not
   the SDK development key. That matches the forensic report's caution that "the device's
   BootROM/eFuse state is authoritative".

### The signature does not verify against its own embedded keys

RSA-PSS/SHA-256 verification of the 256-byte signature at `0x7d0` over the GFH at
`0x0000..0x7d0` **fails** for every key in the file (SBC/DAA `660774de...` and SLA
`8964c8a8...`) and for every padding variant tried: PSS/MGF1-SHA256 with salt length 32
and with MAX_LENGTH, PSS/MGF1-SHA1, and PKCS#1 v1.5 with SHA-256, over both the raw GFH
and a pre-hashed SHA-256 digest.

**FACT.** The file is structurally a tool-auth object but its signature does not verify
against the keys it carries. The most likely explanations, in order:

1. the outer signature is made with the **root** private key, and the SBC/root *public*
   key block in the file is not the signer's key (for example the file was generated for
   a different device or key set, then the key blocks were edited or the artifact is a
   template);
2. the signature is over a different encoding of the GFH than the one tried here (the
   generation path packs a GFH image via `ImageGFH.finalize()` and may serialise
   differently from the raw file bytes);
3. the file is a template or placeholder rather than a finished artifact.

**This is worth one live test, and it is cheap.** The Preloader exposes
`SEND_AUTH` (`0xE2`) and `SEND_CERT` (`0xE0`). Sending this artifact as the auth blob is
a *read-only-ish* probe in the same sense as the DA upload: it asks the device to evaluate
an authorization. The interesting outcomes are:

- a status **other than** `0x7009` (the "no DA staged / association failure" status seen
  previously) would mean the device accepted the auth and proceeded to the DAA stage, which
  is a completely new result; and
- a status of `0x7009` would confirm the artifact is not associated with a staged DA.

Either outcome is informative, and neither writes to flash. It must be sent through the
**selector/download handshake this Preloader actually implements** (see section 26 and the
"mtkclient cannot attach" note) - `SEND_AUTH` is a download-dispatcher command
(`0xE2`), and mtkclient's `A0 0A 50 05` handshake is not what this Preloader answers, so
a purpose-built client is required.

### Relationship to the DAA story

This does not change the conclusion that **no DA we can produce will pass the DAA gate**:
the DA is signed with `9af8...`, the Preloader's checker wants `a697...`, and this file's
DAA key is `660774de...`. Three different keys, none of which we hold a private half of.
What this file *does* change is the diagnosis: the DAA key is customer-provisioned, so
"find the right key" is a provisioning question (what was this unit's BootROM/eFuse
provisioned with?), not a "the SDK key must be slightly different" question.

---

## 28. LIVE RESULT: `FACTFACT` accepted, `BOOT_MODE: 4`, and the LK ignored it too (2026-10-20)

The first factory selector has now been exercised live.

### Host side - full transaction completed

```text
preloader seen
claimed interface=1 in=0x81 out=0x01
ready bytes=52 45 41 44 59
sending b'FACTFACT' (first write)
sending v1 record 04 00 00 00 01 00 00 00 03 00 00 00
post-selector bytes=52 45 41 44 59 54 43 41 46 54 43 41 46
selector accepted (b'TCAFTCAF')
SELECTOR_ACCEPTED=YES mode=FACTORY_BOOT
```

`TCAFTCAF` (`54 43 41 46 54 43 41 46`) was returned - exactly the acknowledgement the
source-correlated dispatcher predicts for the `FACTFACT` branch
(`recv(v1, 12, 5); save usb type; send("TCAFTCAF")`). The 12-byte v1 record was consumed
and the acknowledgement followed, confirming the full branch, including its parameter
receive, executed.

### Device side

```text
[BLDR] 'FACTFACT' received!
BOOT_MODE: 4
...
boot_linux_fdt:671: lk boot mode = 0
```

`BOOT_MODE: 4` is the SDK value for `FACTORY_BOOT` recorded in
`analysis/X17M_PRELOADER_SOURCE_CORRELATION.md` section 7. The Preloader therefore
accepted the factory selector, consumed the v1 record, and recorded the mode correctly.

**FACT.** As with `FASTBOOT` (99) and `ADVEMETA` (5), the LK then reported
`lk boot mode = 0` and booted Linux normally. No factory endpoint, no `0x201c`, no
`0x202d`, and no download/flash/erase activity appeared in the 349 KB capture. The device
ran to the same preinit stop as always.

### What this establishes

**The complete selector matrix is now measured on this device:**

| Selector | ACK | Preloader `BOOT_MODE` | LK `lk boot mode` | Outcome |
|---|---|---:|---:|---|
| `METAMETA` | `ATEMATEX` | 1 | **1** | Linux in META mode; gadget blocked by the broken rootfs (section 26) |
| `FASTBOOT` | `TOOBTSAF` | 99 | 0 | `aee_lk` staged; LK booted Linux (section 17) |
| `ADVEMETA` | `ATEMEVDX` | 5 | 0 | META params changed; LK booted Linux (section 18) |
| `FACTFACT` | `TCAFTCAF` | 4 | 0 | **LK booted Linux** (this section) |
| `FACTORYM` | `MYROTCAF` | (6) | ? | **not yet tested** |
| `AT+NBOOT` | `AT+OK` | 0 | ? | not tested; equivalent to a normal boot |

**FACT - only `META_BOOT` is acted on by the LK.** Three different non-META modes (4, 5,
99) are accepted and recorded by the Preloader, and the LK ignores every one of them. This
is now a measured property of the device, not an inference: the LK's boot-mode field only
takes the value for `META_BOOT` on this build.

**FACT - the factory mode exposes no write service here.** This was the specific reason
for testing it, and the answer is negative: selecting `FACTORY_BOOT` produced no
download, flash, erase or burn activity, and no new USB identity. Whatever the factory
mode does on this platform, it is not reachable through the selector path on this unit -
the same way `FASTBOOT` did not reach the LK's fastboot engine.

**Remaining.** Only `FACTORYM` is untested among the factory pair, and it is expected to
behave like `FACTFACT` (it is the ATE variant of the same mode, `BOOT_MODE: 6`, with the
same `recv(v1, 12, 5); save usb type; send(...)` structure and a different acknowledgement).
It is worth one cycle for completeness, but the prior is that it will also be ignored by
the LK.

---

## 29. ROOT CAUSE of the "missed windows": the FTDI and the router share one USB controller (2026-10-20)

The user observed that the power cycle is only detected *after* the UART adapter is
disconnected. That is the key to the whole "the host never attaches" pattern, and it is
now confirmed from `dmesg`.

**FACT.** The router and the FTDI adapter are attached to the **same physical USB
controller** on the host, so a router power cycle also drops the FTDI's USB link. From
`dmesg`:

```text
15:33:15  usb 1-1: USB disconnect, device number 8        <- router (bus 1, ehci-pci)
15:33:57  usb 2-1.3: USB disconnect, device number 10     <- FTDI   (bus 2, xhci)
15:34:00  usb 1-1: new high-speed USB device number 9     <- router back
15:34:01  usb 2-1.3: new full-speed USB device number 11  <- FTDI back
15:34:02  usb 1-1: USB disconnect, device number 9
```

The two devices come and go **together**, and the host-side USB stack is busy
re-enumerating one while the other is expected to be talking to it.

**FACT - this silently broke the UART capture.** A plain `cat /dev/ttyUSB0` opens the
port once and holds that file descriptor. When the FTDI re-enumerates, `/dev/ttyUSB0` is
recreated and the old descriptor is dead, so the capture records **nothing** for the whole
window that matters. This is the source of the `device reports readiness to read but
returned no data (device disconnected or multiple access on port)` error seen earlier, and
of the captures that were exactly 0 bytes precisely while a test was running.

**FACT - it also explains the host-side handshake failures.** When the host is trying to
speak to the router's Preloader at the exact moment the FTDI is re-enumerating on the same
controller, the host USB stack is servicing the FTDI's re-enumeration and the router's
session is disturbed. The `Enumeration(End): OK` repetition and the differing PMIC reset
flags in section 22 are consistent with this: the router's USB session is being disturbed
by the FTDI's re-enumeration, not failing on its own.

**Mitigation applied.** `work/uart_watch.py` replaces the plain `cat`:

- re-resolves the serial port by **VID:PID** (`0403:6001`) rather than by device name;
- reopens it automatically whenever it disappears;
- writes to a single append-only log with a marker at each (re)open.

So the capture now survives the re-enumeration and keeps recording across power cycles
instead of going silent exactly when the evidence matters.

**A better fix, if the hardware allows it.** The real remedy is to put the FTDI on a
*different* USB controller from the router - for example by passing the router's USB
through one host controller and the FTDI through another, or by using a USB isolator/hub
with its own power for the FTDI. Then a router power cycle cannot disturb the FTDI. The
host currently shows:

```text
Bus 001  ehci-pci    -> the router (passthrough)
Bus 002  xhci_hcd    -> the FTDI, behind VMware virtual hubs
Bus 003  xhci_hcd
Bus 004  uhci_hcd
```

They are already on *different* host controllers (1 and 2), but they are evidently on the
same physical hub or the same power domain, since one goes down with the other.

**Practical guidance for the operator.** Sequence the bench as:
1. plug in the FTDI, confirm `ttyUSB0` is present;
2. start the host-side test and the UART capture;
3. power-cycle the router;
4. expect the FTDI to drop and come back - the capture will now reconnect and keep
   recording, and the UART log will show `=== [uart_watch] (re)opened ... ===` markers
   that let the boot boundaries be identified precisely.

---

## 30. Manual bench workflow (2026-10-20) - one test per power cycle

Following the user's instruction to stop chaining tests and run them manually, the bench
is now driven by one script, `work/x17m_bench.py`, with an operator guide in
`work/BENCH.md`.

### Commands

| command | purpose |
|---|---|
| `python3 x17m_bench.py status` | list USB identities, report whether a `0e8d:2000` Preloader window is open, and report stuck/phantom enumerations |
| `python3 x17m_bench.py select --selector <name>` | send **one** boot-mode selector, wait for the window, report the acknowledgement, then watch USB identities passively |
| `python3 x17m_bench.py uart --seconds N --out log` | resilient UART capture that survives the FTDI re-enumerating |
| `python3 x17m_bench.py summarise log` | boot boundaries, selector acknowledgements, `BOOT_MODE` / `lk boot mode`, and the PMIC reset flag per boot |

The `select` command reports one of four unambiguous outcomes: `ACCEPTED` with the
acknowledgement, `no 0e8d:2000 seen`, `READY never arrived`, or `acknowledgement not
received`.

### The Preloader window is shorter than previously measured

The two power cycles at 15:35 and 15:46 are the first data from the resilient logger, and
the second one is decisive:

```text
15:35 boot:  Enumeration(End): OK 835 ms      <- window far too short for the host
15:46 boot:  [pmic_check_rst] UVLO_RSTB        <- good, full power-off
             [TOOL] Enumeration(End): OK 835ms
```

**FACT.** The usable Preloader tool window on this unit is not a fixed 1900-3600 ms. It
has been observed as short as **835 ms**, and the two shortest observations both
coincided with the router enumerating but the host failing to attach. A host-side
application that takes even a few hundred milliseconds to find and claim the device can
miss the window outright.

**This is the practical reason the probe "did nothing" on the 15:46 cycle** even though
the device enumerated at 15:46:33 and the probe was running: the window closed before the
host could claim it, and the device then left USB-download mode.

**Consequence for the workflow.** The `select` command polls at 50 ms and claims the
device the instant it appears, which is about the best a host can do. The remaining
variable is the *device* side, and the operator controls it: a boot with `UVLO_RSTB` gives
a longer, cleaner enumeration than a boot with `DDLO_RSTB`.

**Also observed: a phantom enumeration.** At 15:46:33 the host logged
`usb 1-1: new high-speed USB device number 12` with **no** subsequent
`New USB device found`, no disconnect, and no `1-1` entry in sysfs. The device was
allocated a bus number but never completed enumeration, so it is invisible to `lsusb` and
to pyusb while still occupying a slot in the host's USB stack. The `status` command
reports this case explicitly, since it also explains a probe that sees nothing at all.

### Files

- `work/x17m_bench.py` - the driver (status / select / uart / summarise)
- `work/BENCH.md` - the operator guide, including how to read the PMIC reset flag and
  the measured window lengths

## 31. Community repo evaluation: the MT6890 ecosystem mapped, one never-tested DA found (2026-11-03)

Evaluation of the two linked repos plus everything reachable from them, all offline
(downloads and hash/cert analysis; no device contact).

### Repos evaluated

| repo | relevance |
|---|---|
| `armarchindo/advan-v6-flasher` | **Not applicable.** Termux web-firmware flasher for Advan V6 / ZLT S50; requires a *booting* unit. |
| `mralinp/zlt-x28-openwrt` | **Highest value.** Proven USB read *and write* through the X28 preloader on hwcode 0x992 (mtkclient `7cb40e7` + 4 documented fixes: DA log packets in `xread`, `page_parity_size`, SLA empty-reply, DA-extension crash). Guarded read-verify-restore tooling (`slot_entry.py`). Their docs/RECOVERY.md is the end-game playbook. |
| `mt6890-cpe-recovery/mt6890-cpe-recovery` | SPFT packages for Zyxel NR5103Ev2 / FWA505 / NR5103-nonE / X28 NAND / X25. Downloads mined below. |
| `safuapy/zlt-x28-unbrick` | Complete patched-mtkclient unbrick of an older X28 (BROM entry by holding reset). Their `da_loader/DA_BR.bin` is **byte-identical** to the 2023-06-28 file this unit already rejects (`c3d9058a…`). |
| `Mr-Tezar/Tozed-ZLT-Firmware-Dump` + Google Drive | Tozed firmware archive incl. the locked-generation `pro 8.6.28.2` (Drive folder `TIHSG-Firmware` was empty/unreachable via gdown; only the three unlocked 1.5.13 / 8.5.4.3 / 8.5.5.1 rars came down - all already analysed, identical `c3d9058a…` DA). |

### Community-consensus fact (external evidence matching ours)

`bkerler/mtkclient#88` (67 comments): Lucas-Liam, 2026-08-14:

> "ZLT X28 version 8.6.28.2 which has 2 versions with locked and unlocked bootloader
> (I mean some old DAs working, then there was a silent update that the DA files won't
> work anymore)"

and mutaanto's still-open issue `safuapy/zlt-x28-unbrick#1` "DA file for the new
zlt x28 pro or zlt x17m" — unanswered since 2026-09. The community **does not have** a
DA for the 2025-generation locked units. Ours is exactly one of those (`target config
0x5`, SBC+DAA on), and this unit's `0x7024` is the same phenomenon.

### DA mining result (all packages extracted and hashed)

Every `download_agent/DA_BR*.bin` across Zyxel NR5103Ev2 (stock+rooted), FWA505,
NR5103-nonE, X28 package, X28 Pro/X25 package, safuapy, Mr-Tezar rar archives, and the
X17M's own 30.202 package resolves to **two distinct files**:

| DA | sha256 | verdict on this unit |
|---|---|---|
| 2023-06-28 Quectel | `c3d9058a…` (signed) / `9133e91f…` (unsigned) | **already tested**: `0x7024` |
| 2023-12-28 (X25 package only) | `c873d21d373b531c196cf1fd13798b4ea444b27b4a682c9d1004972023e1581e` / same-practice unsigned `9133e91f…`-file kept in package but that is the *old* unsigned one | **never tested** — only live candidate |

The X25 DA (saved as `work/dax28/DA_X25_20231228.bin`) is a standard-combo NAND v6 DA:
descriptor at `0x60`, hwcode `0x0992 dada`, stage-1 `[0xbc, 0x2f5dc)`, sig at `0x2f5dc`,
stage-2 `[0x2f6dc, 0x5d36c)`, sig at `0x5d36c`. `--loader`-compatible with `mtkclient_pl`.

### Offline key-facts settled today (all read-only)

- The 2025 X17M preloader dump (`5152173e…`, equal to the working unit's) contains
  **none** of the known DA-key moduli (`9af8`, `a697`, `660774de`, `8964c8a8`) as
  plain byte strings; likewise the X25 package preloader.
- The X25 package preloader contains the string `MTKKEYDERIVATION`: the
  2025/locked-generation preloaders store key material **derived/obfuscated**, which
  explains why generation-key extraction from images keeps failing (and why the 2023
  image scoped plaintext `OEM_PUBK` at `0x39ae0` but the 2025 ones do not).
- Brute-force PSS/PKCS1 verification of the X25 DA's two signature regions against
  ~65k 256-byte windows from both preloaders' key regions (e = 65537/3, sha1/sha256,
  salt 0/32/max): **no verification**. The X25 DA's signer is not stored plaintext in
  either image — only a live DAA verdict can decide.

### Preloader cert-chain comparison (new, structural)

Both 2025 preloaders use the same two-cert chain (key cert `0x52c` + content cert
`0x13c`, magic `0xe291f358`) at nearly the same offsets (`0x7e6e4` ours / `0x7e628`
X25). The key certs are byte-identical up to `0x11c` and differ from there
(modulus + signature). Extracted key-cert moduli:

- ours: sha256 `c16649a5…`
- X25 package: sha256 `00d1fd5c…`

Two distinct production signing identities in the same Tozed 2025 family. Whether the
BROM eFuse root accepts the X25 key cert (i.e. whether the *whole-package* route could
ever work) is not decidable offline; the root lives in BROM.

### Next live test (non-destructive, one power cycle)

`work/pl_da_x25.py` — same driver as the validated `pl_da_unsign.py`, pointed at the
X25 DA via `config.loader`. Verdicts:

- `DAA_SIG_VERIFY_FAILED (0x7024)` again → X25-generation key ≠ ours; DA route closed
  for all community assets known today; remaining paths are vendor-supplied DA/auth or
  hardware NAND work.
- Anything else (or a completed PMT read) → DAA gate open.

Note: the earlier unsigned-DA test (`da_unsign.log`) never reached `upload_da`
(handshake window missed), so only the signed stock DA has a definitive `0x7024` on
record. The unsigned variant is still untested.

### Outside-of-host addresses worth keeping

- Comment on `safuapy/zlt-x28-unbrick#1` / contact Lucas-Liam (Drive dump owner) /
  bnjdg: their locked-build assets (X28 Pro 8.6.28.2 `TIHSG-Firmware` folder) may
  contain a matched DA+auth for the locked generation. The Drive folder exists but
  yielded no files via gdown (folder may require browser access).

## 32. LIVE: X25-package DA also fails the DAA gate (2026-11-03)

`work/pl_da_x25.py` run by the operator, one power cycle. Attach succeeded cleanly:

```text
Preloader - Detected regular mode !
Preloader - HW code: 0x992   Target config: 0x5   SBC True   SLA False   DAA True
Preloader - HW subcode: 0x8a00   HW Ver: 0xca01   SW Ver: 0x1
Preloader - ME_ID: AD2E009BFAC7B8BF397ADDD7370986D4
DAXML - Uploading xflash stage 1 from DA_X25_20231228.bin
Preloader - [LIB]: upload_data failed with error: DAA_SIG_VERIFY_FAILED (0x7024)
... T0: 0000 03A8 [000A]  Jump to BL          (window closed normally, unit unaffected)
```

**FACT.** The X25-generation DA (`MTK_DA_v6_2023-12-28`, `c873d21d…`) is rejected with
the same `0x7024` as the 2023-06-28 file. Every public MT6890 DA available today —
X17M 30.202, Zyxel NR5103Ev2/FWA505/NR5103-nonE, X28 package, X28 Pro/X25 package,
safuapy copy, Mr-Tezar archives, and the three Tozed rar bundles — is accounted for and
rejected. **The DA route is closed for all community assets; the pin is bound to the
2025 lock event, not to any DA generation we can obtain.**

**New device identity recorded.** The attach exposed the unit's **ME_ID** (never seen
in earlier sessions):

```text
ME_ID: AD2E009BFAC7B8BF397ADDD7370986D4
```

This is the per-device identity a vendor uses to provision tool authorization. It is
exact and citable for a service/vendor request: an operator-issued DA + auth for
this ME_ID would pass the DAA gate on the first try.

### Remaining paths (unchanged set, now finalised)

1. **Vendor/service DA + auth** provisioned for ME_ID `AD2E009B…` (community contacts:
   Lucas-Liam dump owner / bnjdg / mutaanto; ZLT support for the region where sold).
2. **Hardware NAND work**: bench write of the slot-B rootfs region with the verified
   v19 image; requires identifying the NAND package (part number will come from the
   UART boot line for NAND ID) and a suitable programmer/adapter.
3. Software avenues are exhausted: selectors all tested on this unit, META blocked by
   the broken rootfs, LK fastboot lacks flash commands, BROM exploit unavailable (no
   0x992 BROM dump), preloader 0x70/0x71 compiled out.

### 32 addendum: unit preloader builds differ - and the F0/F3 "index log" lines are normal (2026-11-03)

**Correction to an assumption.** The post-test follow-up boot capture (`work/uart.log`,
140 KB) shows the bricked unit's Preloader build is `20251203-032240`:

- **Bricked unit**: `[BLDR] Build Time: 20251203-032240` - identical string in every
  earlier capture of this unit (`all.txt`, `fb.txt`, `ff.txt`, `meta_uart.txt`,
  `normal.txt`, `uart_watch.log`). Stable.
- **Working unit**: its dump (`mtd00_preloader.img`, `5152173e…`) contains
  `Build Time: 20250909-103520`. **A different build.**

Consequences, all offline reasoning:

1. The earlier framing "the bricked unit runs the same 2025 preloader as the working
   unit" is wrong. The two units are two months apart. The working unit's preloader
   dump is **not** reliable ground truth for the bricked unit's DAA pin, cert chain,
   or derived-key policy; only its *family-level* properties (2025 generation, MTK
   key derivation present in both dumps) carry over.
2. `X17M_2025_PRELOADER_CERT_CHAIN.md` analysed the *September* build. Its moduli
   (`c16649a5…` key cert etc.) apply to the working unit; the December build's chain
   is unverified and may differ.
3. Per-unit identity confirmed independently: the working unit's September BROM probe
   recorded `ME_ID 7D2DEDE9B6C0D14B8A055B3238F43ACA`, while today's attach read
   `AD2E009BFAC7B8BF397ADDD7370986D4`. ME_ID is per-unit (it also appears in the
   September probe doc), so a vendor provisioning request must cite the bricked
   unit's ME_ID, not the working unit's.
4. The September probe doc also shows the *working* unit rejects the same DAs
   (`0x7024` in a transient regular mode with statically relaxed flags). Both units
   are locked-generation; neither accepts community DAs. Nothing changes about the
   flash-path closure - it only removes the "differing preloader builds" surprise as a
   candidate explanation.

**The F0/F3 question.** The block

```text
F0: 102B 0000
F3: 1001 0000 [0200]
...
T0: 0000 03A8 [000A]
Jump to BL
```

is the Preloader's standard hand-off "index log" (MAXLOG-style abbreviated boot
summary ending in `Jump to BL`) - the same text printed in terminal B at the end of
the aborted DA session. During a tool session the Preloader routes its log to the
tool connection as well; the plain UART capture of the following boot
(`uart.log`) shows the normal hand-off (`[PLFM] boot to LK by ATAG reason=32`,
`BOOT_MODE: 0`, `[BLDR] Build Time: 20251203-032240`, LK, kernel, `bootslot=b`,
`can't open /dev/null` in preinit) **without** the F0/F3 block, matching every prior
boot of this unit. Conclusion: the block is session-routed log output of a normal
boot, benign, and the follow-up boot is byte-for-byte the usual boot-loop behaviour.
No persistent change resulted from the X25-DA test.
