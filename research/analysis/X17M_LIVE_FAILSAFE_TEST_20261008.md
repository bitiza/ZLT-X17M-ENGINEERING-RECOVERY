# X17M live failsafe and rootfs copy observations

Date: 2026-10-08

## Device state and access

ADB to `192.168.0.1:5555` succeeds while the router is running. `adb shell`
returns a BusyBox `ash` prompt, and `id` reports `uid=0(root)`. Thus root access
is available in the currently booted state; the earlier statement that root
was unavailable was temporary.

The live `/proc/cmdline` reports:

```text
root=/dev/mtdblock42 bootslot=b
```

The live MTD map reported on this unit differs from the saved reference map.
For the relevant partitions it is:

| MTD | Live name | Size |
|---:|---|---:|
| 29 | `rootfs_a` | 64 MiB |
| 41 | `rootfs_sig_b` | 1 MiB |
| 42 | `rootfs_b` | 64 MiB |
| 43 | `rootfs_data` | 8.25 MiB |

The mount table shows `/dev/root` mounted read-only at `/rom` as SquashFS,
`/dev/mtdblock43` mounted read-write at `/overlay` as JFFS2, and the overlay
mounted as `/`. Vendor filesystems and `/data` are also mounted. This is a
running Linux system with the normal writable overlay.

## Rootfs copy command and verification limit

The command reported by the user was:

```sh
dd if=/dev/mtd29 of=/dev/mtdblock42 bs=64k
```

On the live map above, this copies from `rootfs_a` to `rootfs_b`, matching the
currently selected B slot. `dd` reported 64 MiB read and written. This does not
by itself establish that the NAND contents are byte-identical or that the
rootfs signature for B matches the copied image.

The subsequent command was:

```sh
cmp -n 67108864 /dev/mtd29 /dev/mtd42
```

It returned `/bin/ash: cmp: I/O error`. It compares the MTD character device
`/dev/mtd42`, whereas the copy destination was the block interface
`/dev/mtdblock42`. The failed comparison is not a successful verification and
does not establish the current contents of either partition.

The saved 1 GiB reference map previously found in the backup has different
numbering around the B-slot rootfs (`mtd42=rootfs_sig_b`, `mtd43=rootfs_b`). Do
not use that older mapping for this device; always use its live `/proc/mtd`.

## Boot output and failsafe test

Captured serial output includes normal-world handoff from ATF to the 64-bit
kernel at `0x40080000`, followed by:

```text
/bin/board_detect: /etc/board.d/99-default_network: line 5: can't open /mnt/vendor/nvcfg/mac0: no such file
/bin/board_detect: /etc/board.d/99-default_network: line 6: can't open /mnt/vendor/nvcfg/mac1: no such file
Press the [f] key and hit [enter] to enter failsafe mode
Press the [1], [2], [3] or [4] key and hit [enter] to select the debug level
```

The same prompt is the last serial output on normal boot; therefore silence
after the prompt alone does not show that boot stalled. ADB access and mounted
filesystems independently confirm Linux reached a usable state.

During an attempted failsafe entry, the console showed `- failsafe -`, then
echoed typed `f`, `id`, and other input, with repeated/garbled characters and
no visible command results. This is evidence that failsafe did not provide a
usable interactive shell through the tested console path. It supports the
working concern that the device's failsafe path is not a dependable recovery
method when normal userspace is broken. It does not prove the router is
unrecoverable in every failure state or rule out a console configuration,
terminal, timing, or input-path issue.

The missing `mac0` and `mac1` messages are board-detection warnings. Their
presence does not alone identify the cause of the bootloop or prove NAND
damage.

## Offline rootfs directory comparison

`squashfs-root` and `rootfs.original` differ substantially. Relevant observed
differences include:

The user confirms that `rootfs.original` is a copy of this same physical
device's root filesystem, and that the files in this project directory came
from this device except for a few files. The exceptions have not yet been
identified. Treat `rootfs.original` as device-specific evidence, while
retaining that provenance caveat for the unspecified files.

- `/etc/preinit`, `/etc/rc.button/failsafe`, and the files under
  `/lib/preinit` appear unchanged in the recursive comparison / targeted
  checks.
- `squashfs-root/etc/diag.sh` comments out the `preinit` and
  `preinit_regular` LED indications.
- `squashfs-root/etc/inittab` is a much longer customized file with additional
  mounts, a second `rcS` invocation, and shutdown actions. These differences
  may change startup behavior, but do not by themselves explain the observed
  lack of an interactive failsafe shell.
- The two `/etc/board.d/99-default_network` versions differ. The original
  version reads `mac0`/`mac1`; the `squashfs-root` version omits those reads.

No causal link between these `squashfs-root` versus `rootfs.original`
differences and the failed interactive failsafe test was established by that
comparison. The v15 image was inspected separately below and exposes a likely
serial-console selection bug.

## Failsafe console code-level finding

Inspection of the v15 image found a likely explanation for the UART behavior.
Its `/proc/cmdline` on this unit lists `console=tty0` before
`console=ttyS0,921600n1`. The v15 `lib/preinit/99_10_failsafe_login` selects
the first `console=` token, so its background failsafe shell is attached to
`/dev/tty0` instead of the serial UART. The v15
`lib/preinit/40_run_failsafe_hook` also starts another ash on `/dev/console`,
creating a second shell/input path. This combination is consistent with the
observed failsafe marker and echoed/garbled input without usable command
results. It is a code-level diagnosis, not yet confirmed by a repeat UART
test with corrected code.

The first PDF's suggestion to add yet another ash loop to
`40_run_failsafe_hook` would compound the duplicate-shell issue. Its suggested
OpenSSH failsafe hook also edits `/etc/shadow` to allow empty-password root
login; that change was not used. The candidate below fixes serial-console
selection and avoids simultaneous input readers.

## Current conclusion

The router boots Linux on slot B and is reachable as root over ADB. The A-to-B
`dd` was aimed at the correct B rootfs partition according to this unit's live
map. Copy integrity remains unverified. v15 was previously tested by the user;
v18 was the first version associated with a bootloop. The v17 UART transcript
below confirms the failsafe serial shell works after the console-selection
fix.

## Candidate v15 image (not yet flashed)

The user plans to restore `rootfs_patched_v15.img`; the bootlooped v18 image was
deleted. The user clarifies that earlier versions were tested before advancing
to the next version, and the bootloop first occurred with v18. This makes v15
a previously tested version. Local inspection found:

| Property | Value |
|---|---|
| File size | 55,738,368 bytes (reported by `ls` as 54 MiB; SquashFS filesystem size is 55,736,015 bytes) |
| SHA-256 | `f4162c15204fc9116c638cd54302f6da853c77e84e59b8e998f3bf1765247267` |
| Filesystem | SquashFS 4.0, XZ, block size 262144, 6329 inodes |
| Creation time | 2026-08-08 18:51:49 (from image superblock) |
| OpenWrt target | `gem6xxx/evb6890v1_64_cpe` |
| OpenWrt release | 21.02.7; embedded revision `r0-f27a03f3`; description `r16847-f8282da11e` |

The target string matches the live NAND X17M target, and the 53.15 MiB
SquashFS payload fits within the live 64 MiB `rootfs_b` partition. It is a
plausible image for this device. It is a standalone SquashFS image; it does
not include the separate 1 MiB `rootfs_sig_b` partition. The user confirms
that this router does not use dm-verity. No evidence in this inspection
establishes that `rootfs_sig_b` is involved in mounting or verifying this
SquashFS. This inspection did not establish whether v15 was previously
boot-tested on this exact unit. No flash operation was performed as part of
this inspection.

## v16 failsafe candidate

`rootfs_patched_v16` was extracted from the local v15 image, retaining v15 as
the baseline. The failsafe changes are limited to:

1. `lib/preinit/99_10_failsafe_login` now prefers serial consoles such as
   `ttyS0` over `tty0`, reports which device it selected, and respawns the
   failsafe shell on that device.
2. `lib/preinit/40_run_failsafe_hook` no longer starts a second ash on
   `/dev/console`; it leaves the single console shell to the failsafe hook and
   waits for the existing sysupgrade signal.

The SquashFS candidate `rootfs_patched_v16.img` was built from that tree with
XZ compression and 262144-byte blocks. It is 55,738,368 bytes, contains one
device node (the `/dev/console` node restored using the accompanying pseudo
definition), and has SHA-256
`fccf7dc222fd62ba545a54178be6bc5a185b0216ecd6277df76cbf5dc63852e6`.
The image was flashed and booted, as recorded below.

The user flashed v16 to `rootfs_b` with:

```sh
mtd -r write /tmp/rootfs_patched_v16.img rootfs_b
```

The router rebooted and ADB returned. Subsequent checks show `bootslot=b`,
`root=/dev/mtdblock42`, PID 1 is `procd`, and `/tmp/.failsafe` is absent
(`NORMAL_BOOT`). This confirms v16 boots normally from B. A first UART failsafe
attempt did not show failsafe-entry markers and was inconclusive. On a
subsequent attempt, the user sent `f` during the displayed two-second prompt
window. The user clarifies that this successful transcript is from v17, not
v16. The UART output showed, in order:

```text
- failsafe -
Failsafe shell on /dev/ttyS0; enter a command and press Enter.
BusyBox v1.36.0 (2025-12-03 01:38:30 UTC) built-in shell (ash)
/bin/ash: can't access tty; job control turned off
... FAILSAFE MODE active ...
root@(none):~#
```

This positively confirms v17 enters failsafe, selects the serial UART shell,
and reaches an interactive root prompt. The `can't access tty; job control
turned off` message is present, but the shell accepted commands and displayed
the failsafe banner. The `FAILSAFE MODE ACTIVE` banner is printed after the
shell starts because the failsafe shell hook runs in the background. The
successful entry validates the console-selection fix. The displayed prompt
still said `Timeout: 2s`; investigation of the v17 build source found why the
planned timeout extension did not take effect.

## v17 failsafe result and timeout override

The user reports the successful failsafe transcript is from v17. Although
`lib/preinit/30_failsafe_wait` changed its fallback default from two to ten
seconds, `lib/preinit/00_preinit.conf` explicitly sets
`fs_failsafe_wait_timeout=2`. Since the script honors that variable, the
actual prompt remained two seconds. Thus v17 validates failsafe entry and the
serial shell fix, but did not yet provide the intended ten-second window.

The candidate `rootfs_patched_v17.img` is 55,738,368 bytes and has SHA-256
`30948908d65e3c3edfff800864c77aab87e0a59c1c32ce9b0eef41d5f37f8c88`.
The user reports this v17 image is flashed; its normal boot and failsafe UART
shell are confirmed. The timeout was still two seconds because of the explicit
configuration override, as explained below.

## Corrected ten-second timeout image

The explicit `fs_failsafe_wait_timeout=2` in
`rootfs_patched_v17/lib/preinit/00_preinit.conf` was the reason the previous
v17 image still displayed a two-second prompt. A separate source tree,
`rootfs_patched_v17_10s`, changes that setting to 10. Its image,
`rootfs_patched_v17_10s.img`, is 55,738,368 bytes and has SHA-256
`6469a522780382293c0f62bc412b55d5477188ed547e6754db5bebd3e5cae872`.
The user subsequently flashed it to `rootfs_b` using `mtd -r write`. Its boot
log displayed `Timeout: 10s`; sending `f` entered failsafe, selected
`/dev/ttyS0`, and reached the root prompt. This validates both the ten-second
window and UART shell on this device.

After confirming failsafe, the user ran `firstboot -y && reboot`. The captured
output shows this device-specific implementation does more than reset the
overlay:

```text
FLASH_TYPE=nand, IS_UBIFS=1
Erasing nvdata partition
yaffs2
mtd erase nvdata success
Erasing boot_para partition
mtd erase boot_para success
reboot
```

Thus `firstboot -y` erased `nvdata` and `boot_para` before reboot. `nvdata` is
device-specific; `boot_para` contains boot parameters/metadata. Do not repeat
`firstboot` on this device. The reboot after those erases is in progress;
post-reboot ADB, slot, overlay, and modem state have not yet been reported.
Preserve remaining per-device partitions and use read-only checks until state
is assessed.

## Review of additional failsafe suggestions

The user supplied additional Gemini-generated suggestions concerning
`30_failsafe_wait` and `40_run_failsafe_hook`. The effective ten-second timeout
is implemented in `v17_10s`. A direct `read -t` already existed in v15/v16; the claim
that console log output necessarily corrupts or clobbers that input is not
established by the observed evidence. `/tmp` is mounted as tmpfs on this
device, so `mktemp`/lock files there are RAM-backed rather than flash writes;
the alleged flash wear or read-only overlay failure is not a demonstrated
cause here.

The `40_run_failsafe_hook` wait loop is intentional: while in failsafe, normal
startup is held so the failsafe shell remains available. v16 removed the
additional ash loop from that hook because the failsafe chain already starts a
shell; the primary identified issue was the shell selecting `tty0` instead of
`ttyS0`. The suggestions to start another shell and to remove all waiting
logic were not adopted. Claims that network recovery will always expose
`192.168.1.1` or telnet are also not established for this device.
