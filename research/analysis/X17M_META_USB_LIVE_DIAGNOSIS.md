# X17M META USB live diagnosis

Evidence set: `analysis/live_meta_usbdiag/20260918T142003Z`

Analysis date: 2026-09-18. This report uses only the completed RX-only UART,
USB-handshake, and passive `lsusb` evidence. No new target communication was
performed.

## Evidence integrity

| File | SHA-256 |
|---|---|
| `host_metadata.txt` | `4fc13dc169c5d9fba78134dad387b0c747ca0a7c2e22a944b5a334b6c83549e3` |
| `start_time.txt` | `4f9ec382f3d25c1feaabf49f4fc94b1b37c9e90b448222eb51b3088e36f124e1` |
| `uart_events.log` | `d21275fbb130f1747563b338dbf2d178adc4943c12689ea2963fd3e3626da9b3` |
| `uart_raw.bin` | `2fb8a5bd7963dcd242461d719a48743cf5ee6bb9d6a7004f39433a78b4b96975` |
| `usb_handshake.log` | `9ed61a482ee9280a13d1838c03c6d9795a4bcb7ed5ba53113dc7636f51ebedd4` |
| `usb_timeline.log` | `36474fce2c24e0647eb1c431896602bfa673d1335d79a0b73c37a70b804317b8` |

The raw UART is 140,514 bytes. UART event timestamps describe completion of
host `read()` calls, so a line mapped to a read chunk occurred no later than
that chunk timestamp; they are not target-generated per-line timestamps.

## Correlated timeline — FACT

All times are UTC.

| Time | Delta from `DISCONNECT_COMPLETE` | Evidence |
|---|---:|---|
| 14:20:13.217872 | -2.041286 s | Exact `READY` received |
| 14:20:13.242999 | -2.016159 s | Host sent `METAMETA` |
| 14:20:13.248656 | -2.010502 s | Target sent another exact `READY` |
| 14:20:15.249671 | -0.009487 s | `ATEM0001` after 2.001015 s compatibility wait |
| 14:20:15.250559 | -0.008599 s | V1 sent |
| 14:20:15.254548 | -0.004610 s | `ATEM0002` received |
| 14:20:15.255062 | -0.004096 s | V2 sent |
| 14:20:15.257499 | -0.001659 s | `ATEMATEX` received |
| 14:20:15.257932 | -0.001226 s | `DISCONNECT` sent |
| 14:20:15.259158 | 0 | Handshake logged complete |
| 14:20:15.276661 | +0.017503 s | UART chunk contains META parameters and `[BLDR] DISCON...OK` |
| 14:20:15.331628 | +0.072470 s | First passive USB snapshot without `0e8d:2000` |
| 14:20:19.487400 | +4.228242 s | UART chunk contains `booting linux` and `lk boot mode = 1` |
| 14:20:26.761174 | +11.502016 s | First post-ATF userspace output (`rai0`/`ra0`) |
| 14:20:26.861557 | +11.602399 s | `board_detect` errors and preinit prompt output |
| 14:20:30.932855 | +15.673697 s | Last substantive UART message: `lock: applet not found` |
| 14:21:46.269210 | +91.010052 s | RX-only UART capture closed |

### Preloader completion context

The following contiguous UART text begins at raw offset `0x1a3b9` (decimal
107,449) and was delivered in the read ending at 14:20:15.276661:

```text
meta_com_id = 0
meta_com_id = 3
md_type[0] = 0
md_type[1] = 0
meta_com_id = 3
meta_log_disable = 1
[BLDR] DISCON...OK
[BLDR] 'METAMETA' received!
#T#USB handshake=6304
#T#bldr_handshake=0
```

This confirms the entire Preloader transaction, including the V1/V2 state,
on configuration 1, interface 1, alternate setting 0, bulk IN `0x81`, bulk
OUT `0x01`.

### LK and kernel handoff context

The read ending at 14:20:19.487400 contains raw offsets 139,029 through
139,993:

```text
dump_cmdline:71: cmdline len=461, str="console=tty0 console=ttyS0,921600n1
    init=/etc/preinit root=/dev/mmcblk0p41 rootwait ..."
[ver]bypass update
boot_linux_fdt:670: booting linux @ 0x40080000, dtb @ 42f00000 (133861)
boot_linux_fdt:671: lk boot mode = 1
...
NOTICE: [ATF](0)[12.955533]Kernel is 64Bit
NOTICE: [ATF] BL3-1: Preparing for EL3 exit to normal world, Kernel
INFO: [ATF] BL3-1: Next image address = 0x40080000
INFO: [ATF] BL3-1: Next image spsr = 0x3c9
INFO: [ATF](0)[12.959026]el3_exit
```

The exact text `lk finished --> jump to linux` is absent. Its absence does not
negate the handoff: `boot_linux_fdt`, ATF `el3_exit`, and subsequent userspace
output independently prove progression through the kernel.

### Linux preinit/userspace context

The first output after ATF appears at raw offset 140,005. The relevant tail is:

```text
rai0      no private ioctls.
ra0       no private ioctls.
/bin/board_detect: /etc/board.d/99-default_network: line 5:
    can't open /mnt/vendor/nvcfg/mac0: no such file
/bin/board_detect: 6: can't open /mnt/vendor/nvcfg/mac1: no such file
lock: applet not found
Press the [f] key and hit [enter] to enter failsafe mode
Press the [1], [2], [3] or [4] key and hit [enter] to select the debug level
netmsg: applet not found
netmsg: applet not found
lock: applet not found
lock: applet not found
```

After the last line, the capture contains only three isolated NUL bytes at
14:20:31.033257, 14:20:36.718773, and 14:21:31.578096. There is no later
printable boot, USB, panic, or restart message.

This proves Linux preinit/userspace execution. It also records concrete early
userspace abnormalities (missing `mac0`/`mac1` files and missing `lock` and
`netmsg` applets). The evidence does not prove that these abnormalities caused
the boot to stop before rcS.

## Passive USB timeline — FACT

The timeline contains only three states:

1. 14:20:03.734986: no MediaTek device.
2. 14:20:13.279316: `0e8d:2000 MediaTek Inc. MT65xx Preloader` present.
3. 14:20:15.331628: the Preloader absent; no replacement USB identity.

The change-based logger does not record every poll, so 14:20:15.331628 is the
first confirmed absence rather than an exact physical disconnect timestamp.
No additional USB change was logged during the remaining observation window.

| VID:PID after DISCONNECT | Result |
|---|---|
| `0e8d:202d` | **NOT OBSERVED** at any sample |
| `0e8d:2000` | Gone by +0.072470 s; did not reappear |
| `0e8d:0003` | **NOT OBSERVED** |
| Any other new VID:PID | **NOT OBSERVED** |

Because no `202d` sample exists, no first/last timestamp or positive duration
can be assigned. An enumeration shorter than the approximately 100 ms polling
interval cannot be absolutely excluded, but no host evidence supports one.

## Complete marker audit — FACT

The complete raw UART stream was decoded and inspected, including context
before and after every case-insensitive keyword match.

Present:

* `lk boot mode = 1`
* `booting linux`, ATF kernel handoff, and Linux userspace output
* two benign early Preloader RTC lines containing `reboot`, explicitly stating
  that two-second reboot is not enabled
* two image-authentication timing messages reporting successful loading, not
  authentication failure
* `aee_lk` only as a reserved-memory name
* `udc support : 0x00000000` only in the modem image header; this is not a
  Linux USB gadget UDC bind message

Absent:

```text
lk finished --> jump to linux
Start USB
Check BootMode
BootMode: 0001
usb.init done
configfs
gadget
11201000
mass_storage / mass storage
lun
ACM
ttyGS / ttyGS0
FunctionFS
failed / error
EINVAL / ENODEV / EBUSY
start meta_tst
Enter meta_tst init flow
Meta mode boot
not meta mode boot
Enter meta_tst init fail
panic
watchdog
reset
fatal
authentication failure
```

## USB.INIT questions

### FACT

The exact rootfs `S30usb.init` prints `Force on usb device mode` and `Start
USB` before configfs construction, then `Check BootMode` and `BootMode: ...`
before its mode switch. `restart_usb.sh` prints `usb.init done` immediately
after attempting the UDC write.

None of these unconditional progress markers appears in this capture. No
`0e8d:202d` device appears on the host.

### INFERENCE

The strongest evidence-based interpretation is that the captured boot did not
reach observable execution of `S30usb.init` before UART output ceased. This is
consistent with the last visible stage being OpenWrt preinit/failsafe setup,
which precedes rcS service priority 30.

### UNKNOWN

Absence of a UART line is not instruction-level proof that a script never ran.
Accordingly:

1. S30usb.init reached: **UNKNOWN / NOT OBSERVED**.
2. BootMode `0001` read by usb.init: **UNKNOWN / NOT OBSERVED**.
3. PID `202D` selected: **UNKNOWN at target; not enumerated on host**.
4. Configfs construction attempted: **UNKNOWN / NOT OBSERVED**.
5. `mass_storage.usb0` linked: **UNKNOWN at runtime**.
6. Missing backing store: **CONFIRMED in the exact static rootfs; no runtime
   evidence in this capture**.
7. Final UDC bind attempted: **UNKNOWN / NOT OBSERVED**.
8. UDC bind result: **UNKNOWN**.
9. `/dev/ttyGS0` created: **UNKNOWN / NOT OBSERVED**.

## META_TST questions

The exact rootfs launches `/usr/bin/meta_tst` from `S98meta_tst`, much later
than `S30usb.init`. The capture contains none of its launcher or binary
messages.

1. S98meta_tst reached: **UNKNOWN / NOT OBSERVED**.
2. `/usr/bin/meta_tst` executed: **UNKNOWN / NOT OBSERVED**.
3. META mode recognized: **UNKNOWN**.
4. `createSerPort()`/open `/dev/ttyGS0`: **UNKNOWN**.
5. Init failure logged: **NO; no such log is present**.
6. Remained alive or disappeared: **UNKNOWN**.

The evidence is more consistent with execution not yet reaching S98 than with
a proven `ttyGS0` open failure, but it cannot distinguish those cases.

## Leading mass-storage hypothesis

### FACT — static image

The exact X17M `usb.init` creates and links `mass_storage.usb0` for mode
`0001`, but the extracted rootfs contains no assignment to
`mass_storage.usb0/lun.0/file`.

### UNKNOWN — this live run

There is no live `Start USB`, mode-selection, configfs, mass-storage, UDC, or
kernel error evidence. Therefore the proposition that an unbacked mass-storage
function caused the UDC bind to fail remains **STRONGLY SUPPORTED STATICALLY
BUT UNKNOWN AT RUNTIME**. This run neither confirms nor disproves it.

The absence of `202d` is necessary but not sufficient evidence for that
specific failure: the captured execution may not have reached the binder.

## Restart analysis

No post-META restart is observed during the 91.010-second UART window:

* no second `Welcome to Preloader`;
* no new BootROM or Preloader UART sequence;
* no `0e8d:0003` or reappearing `0e8d:2000`;
* no panic, watchdog, reset, reboot, fatal, AEE-event, or authentication-
  failure message.

The last substantive UART message is `lock: applet not found` at or before
14:20:30.932855. Since no restart occurred, an elapsed time from DISCONNECT to
restart and a restart cause do not exist for this evidence set.

## Final status

```text
PRELOADER META HANDSHAKE: PASS
LIVE USB CONFIGURATION: 1
LIVE PRELOADER INTERFACE: 1, alternate setting 0, bulk IN 0x81, bulk OUT 0x01
META_BOOT REACHED LK: YES — lk boot mode = 1
META_BOOT REACHED KERNEL: KERNEL EXECUTION YES; KERNEL-SIDE MODE VALUE NOT DIRECTLY LOGGED
USB.INIT REACHED: UNKNOWN / NOT OBSERVED
USB.INIT BOOTMODE: UNKNOWN / NO BootMode LINE
PID 202D SELECTED: UNKNOWN AT TARGET; NOT OBSERVED ON HOST
MASS_STORAGE FUNCTION CREATED: UNKNOWN AT RUNTIME
MASS_STORAGE BACKING STORE: ABSENT IN STATIC ROOTFS; RUNTIME STATE UNKNOWN
UDC BIND ATTEMPT: UNKNOWN / NOT OBSERVED
UDC BIND RESULT: UNKNOWN
0E8D:202D ENUMERATED: NO OBSERVATION DURING 91.010-SECOND WINDOW
TTYGS0 CREATED: UNKNOWN / NOT OBSERVED
META_TST STARTED: UNKNOWN / NOT OBSERVED
META_TST RECOGNIZED META: UNKNOWN
META_TST SERIAL RESULT: UNKNOWN; NO OPEN OR INIT-FAILURE MESSAGE
FIRST CONFIRMED META USB FAILURE: NO 0E8D:202D ENUMERATION; INTERNAL FAILURE POINT UNKNOWN
POST-META RESTART: NO, NOT DURING THIS CAPTURE
POST-META RESTART CAUSE: NOT APPLICABLE / NO RESTART OBSERVED
NEXT SAFEST STEP: STATICALLY EXPLAIN THE CAPTURED PREINIT STOP/QUIET POINT AND WHETHER ITS MISSING NVCFG/LOCK/NETMSG CONDITIONS CAN PREVENT TRANSITION TO /sbin/init AND S30usb.init; NO ADDITIONAL LIVE RUN.
```
