# X17M Linux META failure analysis

Scope: static analysis of the exact extracted X17M `rootfs.original` and the
captured META UART evidence. The RG500/T750 SDK is used only as comparative
source. No target communication or firmware modification was performed for
this report.

## Executive result

**Live-test update:** this static report predates the working 1 GB META test of
2026-10-08. That test confirms the META PID is selected and the UDC initially
binds; after the ADB retry loop is bypassed, the UDC remains bound but Windows
and Kali still fail to obtain a usable USB identity. The earlier unbacked-LUN
bind-failure hypothesis is therefore not the observed failure in this run.
See [the dated live-test report](X17M_META_USB_WORKING_1GB_20261008.md) for
the current evidence and unresolved descriptor-enumeration failure.

The X17M rootfs does explicitly implement a Linux META USB profile. For boot
mode `0001`, `/etc/init.d/usb.init` selects VID:PID `0e8d:202d`, configuration
`dualacm`, and links one mass-storage function plus three ACM functions. This
is not merely an RG500 inference.

The most important static defect is that the X17M script creates and links
`functions/mass_storage.usb0`, but never writes a backing file to its
`lun.0/file` attribute. Consequently the UDC bind may fail when the mass-
storage function is included. The script does not check any of the configfs,
function creation, symlink, or UDC-write exit statuses. This is the earliest
likely explanation for the absence of `0e8d:202d`, but the actual kernel error
is not present in the captured UART, so it remains an inference rather than a
confirmed runtime failure.

## 1. META boot-mode propagation

### FACT

The live capture is conclusive through the Linux handoff:

* LK printed `lk boot mode = 1` and `lk finished --> jump to linux`.
* The kernel command line retained `root=/dev/mmcblk0p41` and `bootslot=b`.
* Subsequent UART output included `/bin/board_detect` messages, proving that
  Linux userspace ran.

Thus META mode did not alter the selected root partition or A/B slot.

### SOURCE-CORRELATED

The exact rootfs consumers all read the FDT node
`/proc/device-tree/chosen/atag,boot`:

* `usb.init:83` reads the value with `hexdump` and uses field 6 as
  `boot_mode`.
* `fibo_rndis.init:12-16` exits for `0001`.
* `mipc_wan.init:105-109` exits for `0001`.
* `meta_tst` contains the same path as a string.

The comparative MediaTek META source defines the structure as four 32-bit
words (`size`, `tag`, `bootmode`, `boottype`) and returns word 2. Its constants
are `NORMAL_BOOT=0` and `META_BOOT=1`. The X17M `meta_tst` binary contains the
matching path, messages (`not meta mode boot`, `Meta mode boot`), and mode
value strings. This strongly supports the path `LK boot mode -> FDT
atag,boot[2] -> userspace`, although the X17M LK/FDT writer itself is not
recovered in this report.

## 2. Exact X17M USB setup

### FACT

The complete execution order in `rootfs.original/etc/init.d/usb.init` is:

1. At rcS priority `S30usb.init`, force USB device mode by writing `3` to
   `/sys/devices/platform/11201000.usb/mode` (`usb.init:26-29`).
2. Read `devinfo 102020`, load `/etc/config/usb`, and obtain serial/config
   values (`31-38`).
3. Mount configfs at `/config` and create gadget `g1` (`40-47`).
4. Set VID `0x0e8d`, bcdDevice `0x0223`, bcdUSB `0x0200`, manufacturer
   `Mediatek`, product `mt6890` (`48-54`).
5. Create `acm.gs0`, `acm.gs1`, `acm.gs2`, `rndis.gs4`, and
   `mass_storage.usb0` plus configuration `b.1` (`56-69`).
6. For non-`usr` firmware only, create/mount FunctionFS ADB and start
   `adbd_usb` (`74-80`).
7. Read `atag,boot` (`82-85`).
8. For `0001`, set configuration string `dualacm`, PID `0x202D`, and link:

   * `f1 -> mass_storage.usb0`
   * `f2 -> acm.gs0`
   * `f3 -> acm.gs1`
   * `f4 -> acm.gs2`

   (`118-125`).
9. Start `/etc/restart_usb.sh` through procd (`128-130`).
10. `restart_usb.sh` sleeps two seconds, writes
    `11201000.usb` to `g1/UDC`, then repeats once per second if
    `/dev/usb-ffs/adb/ep1` is absent (`restart_usb.sh:3-16`).

Therefore the expected X17M META descriptor is:

* VID:PID: `0e8d:202d`
* configuration: `dualacm`
* functions: mass storage, ACM `gs0`, ACM `gs1`, ACM `gs2`
* expected META application serial endpoint: `/dev/ttyGS0`

The exact X17M `meta_tst` binary contains `/dev/ttyGS0`, and its comparative
source implementation uses that path for the non-AP-only build.

### STRONGLY SUPPORTED failure point: unbacked mass storage

`usb.init` creates `functions/mass_storage.usb0` and links it into the META
configuration, but there is no command anywhere in the extracted rootfs that
writes `.../functions/mass_storage.usb0/lun.0/file`. The script also does not
set a read-only flag or a block/file path. A mass-storage configfs function
normally requires a backing file or block device before a gadget containing it
can bind to a UDC. If this kernel enforces that requirement (the normal
f_mass_storage behavior), the `echo 11201000.usb > .../UDC` bind fails and no
`0e8d:202d` enumeration occurs.

This is an X17M-confirmed configuration omission; the resulting kernel error
is not captured, so the bind failure itself is STRONGLY SUPPORTED rather than
FACT.

### POSSIBLE additional USB failures

* `configfs` mount or any `mkdir` can fail; no status is checked.
* The UDC name can be absent/not ready; the UDC write is unchecked.
* `DI_SYS_FWVERSION_TYPE=usr` suppresses ADB creation, while
  `restart_usb.sh` nevertheless tests for `ep1` and repeatedly re-runs
  `usb.init`. The actual `devinfo 102020` value is not in the image, so the
  condition is possible, not confirmed.
* The script only binds after a two-second delay. A reboot before that point
  would prevent enumeration.
* A pre-existing `g1` skips creation of functions and assumes the old gadget
  state is compatible; this is relevant after restarts but not proven here.
* No X17M rootfs script assigns a different META PID. `0e8d:202d` is therefore
  the expected value for this image, not a comparative-only guess.

## 3. `meta_tst` startup and device

### FACT

The init link is `S98meta_tst`; the script starts `/usr/bin/meta_tst`
unconditionally (`/etc/init.d/meta_tst:3-15`). There is no shell-level boot-mode
guard. `meta_tst` itself is an AArch64 PIE executable and requires:

`libccci.so`, `libmipc_msg.so`, `libnvram.so`, `libfile_op.so`,
`libubox.so.20210516`, `libstdc++.so.6`, `libgcc_s.so.1`, and libc.

Its embedded strings include:

* `/proc/device-tree/chosen/atag,boot`
* `/dev/ttyGS0`
* `Meta mode boot!`, `not meta mode boot!`, and `Enter meta_tst init fail`
* `/dev/ccci_ioctl4`
* `/dev/block/platform/bootdevice/by-name/proinfo`
* `/dev/block/platform/bootdevice/by-name/para`
* `/data/nvram/AllFile`, `/data/nvram/AllMap`, and
  `/mnt/vendor/nvdata/AllFile`

### SOURCE-CORRELATED control flow

The matching SDK source (`tst_main.cpp`) performs:

1. log `Enter meta_tst init flow`;
2. read `atag,boot`; return immediately with `not meta mode boot!` unless
   mode is 1;
3. create the serial port (`/dev/ttyGS0` in this build);
4. start its asynchronous receive pump;
5. create modem threads;
6. remain in an infinite sleep loop.

The X17M binary has the same strings, imports, and device paths. Exact X17M
instruction-level equivalence is not claimed because it is stripped.

`meta_tst` does not itself create the USB gadget. It depends on `usb.init` and
the kernel ACM gadget to create `/dev/ttyGS0`. If that device is absent,
`createSerPort()` can fail; the main program logs `Enter meta_tst init fail`
but then still proceeds to its infinite loop. The init script has no respawn
parameter and no reboot action.

## 4. Init ordering and observed boundary

### FACT

Relevant rcS order is:

| Order | Link | Effect |
|---:|---|---|
| 00 | `S000mount_all` | creates/mounts vendor, data, product and NVRAM paths |
| 00 | `S001nvram_daemon`, `S002ccci_fsd`, `S003ccci_mdinit` | NVRAM/modem foundations |
| 10 | `S10boot` | root/config setup and kmodloader |
| 30 | `S30mipc_wan.init` | exits on META mode |
| 30 | `S30usb.init` | creates/selects gadget and launches UDC binder |
| 53 | `S53scd` | modem/AP service under procd |
| 95 | `S95aee_aed` | crash-dump daemon if DT enables AEE |
| 96 | `S96atcid`, `S96atci_service` | AT services |
| 98 | `S98meta_tst` | META daemon, unconditionally launched |
| 99 | `S99fibo_rndis.init` | exits on META mode |
| 99 | `S99zmtk_boot_done` | boot profiling, boot-control bookkeeping, LVTS reboot setting |

The exact UART capture proves Preloader, LK, ATF, kernel handoff, and at least
userspace `board_detect`. It does not contain an unambiguous `Start USB`,
`BootMode: 0001`, `usb.init done`, `start meta_tst`, or `Meta mode boot!` line.
Accordingly, the last directly confirmed userspace stage is `board_detect`,
not successful `usb.init` or `meta_tst` initialization.

### SOURCE-CORRELATED META differences from normal boot

* Normal mode (`0000`) selects PID `0x2028` and an RNDIS/ADB/ACM profile,
  subject to the `usr` condition.
* META mode (`0001`) skips `mipc_wan.init` and `fibo_rndis.init`, so normal
  APN/RNDIS setup is deliberately suppressed.
* META mode still runs the common rcS sequence, including `usb.init`, modem
  daemons, AEE, AT services, `meta_tst`, and `zmtk_boot_done`.
* The root partition and slot are the same in the captured normal and META
  command lines (`mmcblk0p41`, slot B); this is not an A/B difference.

## 5. Reboot analysis

### FACT

The later USB timeline returned to `0e8d:0003` and `0e8d:2000`, showing that
the unit restarted through BootROM/Preloader. The UART capture does not show a
conclusive panic, watchdog, authentication failure, or explicit userspace
`reboot` message at the transition.

### NOT SUPPORTED as an automatic `meta_tst` reboot

The exact init script does not set `respawn`, and the matching main loop is an
infinite sleep. `meta_tst` imports `reboot` and contains reboot/power command
strings, but those are command handlers reached through a later host META
protocol request; no automatic reboot follows initial startup. No such host
request was sent in the observational test.

### POSSIBLE / UNKNOWN causes

* A kernel panic could reboot after the configured `kernel.panic=3` in
  `/etc/sysctl.d/10-default.conf`, but no panic trace was captured.
* A watchdog or modem/AP supervisor could reset the system; no concrete call
  chain to this restart is established.
* USB setup failure alone does not call `reboot` in the extracted scripts.

Therefore `POST-META REBOOT CAUSE` is UNKNOWN from current evidence.

## 6. META capabilities and recovery value

### SOURCE-CORRELATED, with X17M binary corroboration

The X17M binary imports NVRAM and file-operation APIs and contains paths and
messages for:

* NVRAM file backup/restore and reset;
* product-info (`proinfo`) query and write;
* modem/CCCI diagnostics and AT-mediated modem mode changes;
* file transfer and clock/query operations;
* reboot, power-off, and recovery handlers.

The comparative source implements these as later META command modules. They
are not exposed by the Preloader selector itself.

### RAW EMMC ACCESS VIA `meta_tst`

No arbitrary raw-LBA/eMMC interface is established. The binary has no
`/dev/mmcblk*` string and no demonstrated raw block command. It does access
named `proinfo`, `para`, and NVRAM/file-operation paths, which are persistent
configuration storage and can include writes when corresponding META commands
are used. A mass-storage gadget could expose a backing block/file only if one
were configured, but this X17M script does not configure one.

## 7. Classification of leading hypotheses

| Hypothesis | Classification | Evidence |
|---|---|---|
| META mode was rejected before Linux | IMPOSSIBLE | LK mode 1 and userspace output are live-confirmed |
| Linux boot mode was not propagated | IMPOSSIBLE/NOT SUPPORTED | LK mode 1; exact consumers read `atag,boot`; userspace reached |
| `usb.init` selected wrong X17M PID | NOT SUPPORTED | Exact script selects `0x202D` for `0001` |
| Configfs/function/UDC bind failed | STRONGLY SUPPORTED | unchecked setup plus unbacked mass-storage function |
| `meta_tst` absent or never launched | UNKNOWN | rcS link and binary exist; no clear UART startup line |
| `meta_tst` could not open `/dev/ttyGS0` | POSSIBLE | binary requires `/dev/ttyGS0`; gadget was not observed |
| `meta_tst` deliberately rebooted | NOT SUPPORTED | no automatic reboot path in startup/main loop |
| kernel panic/watchdog caused later restart | POSSIBLE/UNKNOWN | reboot observed, cause markers absent |

## 8. Safest next live observation

Do not send any new META or Linux command. Repeat the already validated
handshake only while capturing RX-only UART and the host's USB event stream,
then inspect for these exact lines in order:

1. `Start USB`
2. `Check BootMode`
3. `BootMode: 0001`
4. `usb.init done`
5. `start meta_tst`
6. `[Meta] Meta mode boot!`
7. `[Meta] ... ttyGS0 ...` / `Open ... success` or an init-failure message

Also preserve kernel log output for configfs/UDC errors. This observation
distinguishes “userspace never reached USB init” from “META branch selected but
UDC bind failed” without opening or writing to any new interface.

## Final status

EXPECTED X17M META USB VID:PID: `0e8d:202d` (FACT)

EXPECTED USB FUNCTIONS: `mass_storage.usb0`, `acm.gs0`, `acm.gs1`, `acm.gs2`
under `dualacm` (FACT)

EXPECTED META_TST DEVICE: `/dev/ttyGS0` (X17M binary string; source-correlated
device selection)

META_TST START CONDITION: launched unconditionally by `S98meta_tst`; binary
continues only when `atag,boot[2] == 1` (SOURCE-CORRELATED)

LAST CONFIRMED USERSPACE STAGE: Linux userspace `/bin/board_detect` (FACT)

EARLIEST LIKELY META FAILURE: configfs/UDC binding in `usb.init`, especially
the linked but unbacked mass-storage function (STRONGLY SUPPORTED)

POST-META REBOOT CAUSE: UNKNOWN

RAW EMMC ACCESS VIA META_TST: not established; named NVRAM/proinfo/para and
file operations exist, arbitrary raw-LBA access does not (FACT / UNKNOWN for
unseen command handlers)

NEXT SAFEST LIVE OBSERVATION: RX-only UART plus passive USB event capture of
`Start USB` through `meta_tst` startup and kernel UDC/configfs errors; no new
protocol writes.
