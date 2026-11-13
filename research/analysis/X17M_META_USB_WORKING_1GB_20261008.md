# Working 1 GB X17M META USB live test

Date: 2026-10-08  
Target: known-working 1 GB X17M, not the bootlooped unit.  
Scope: Preloader META selector, passive UART evidence, Linux configfs/UDC
inspection, and a temporary runtime edit to the USB retry script. No flash
partition was changed.

## Result

The complete META selector succeeds. Preloader reports `BOOT_MODE: 1` and LK
hands Linux `lk boot mode = 1`. Linux selects the expected META USB PID
`0x202d` and creates the configured gadget. Disabling the retry condition in
`/etc/restart_usb.sh` leaves the gadget bound. An initial Windows enumeration
failed with “Invalid Configuration Descriptor,” and Kali logged an attach
without a VID:PID. A later Windows USBDeview screenshot shows the same META
gadget enumerated successfully as `0e8d:202d` with COM264–266. USBDeview also
shows `K:`, but later router checks show mass storage is absent in the current
configuration, so that drive-letter field may be historical.

Therefore two distinct issues have now been observed:

1. The original retry loop re-ran `usb.init` because META mode has no ADB
   FunctionFS `ep1`; this cleared the configuration and unbound the gadget.
2. After bypassing that loop, one host enumeration failed on the configuration
   descriptor, followed by a later successful enumeration of the full gadget.

The transient invalid-descriptor event remains unexplained. Current evidence
shows the full META gadget can enumerate successfully; the event's trigger has
not been isolated.

## Selector and boot evidence

Evidence directory: `live_meta_usbdiag_1gb/20261008T111708Z/`.

The recorded USB transaction completed:

```text
READY
METAMETA
ATEM0001
12-byte V1 record
ATEM0002
16-byte V2 record
ATEMATEX
DISCONNECT
```

The corresponding UART text included:

```text
[BLDR] 'METAMETA' received!
BOOT_MODE: 1
META_COM TYPE: 2
META_COM ID: 3
META_COM PORT: 285220864
set_fdt_atag_meta: meta com type = 2
set_fdt_atag_meta: meta com id = 3
set_fdt_atag_meta: meta uart port = 285220864
boot_linux_fdt:671: lk boot mode = 1
```

The USB/UART logger's UART thread failed because the serial device disconnected
or was already in use; `uart_raw.bin` in this run is not a valid boot capture.
The pasted serial-console output is the evidence for the UART findings.

## Linux gadget observations

On the working router, read-only checks returned:

```text
/proc/device-tree/chosen/atag,boot: boot mode field is 1
devinfo 102020: usr
/config/usb_gadget/g1/idProduct: 0x202d
/config/usb_gadget/g1/UDC: initially empty after teardown
```

After manually starting the META USB profile, configfs showed links:

```text
f1 -> functions/mass_storage.usb0
f2 -> functions/acm.gs0
f3 -> functions/acm.gs1
f4 -> functions/acm.gs2
```

The `UDC` file then contained `11201000.usb`, and `restart_usb.sh` was running.
The `/dev/usb-ffs/adb` directory was empty, as expected for the META
configuration. The configfs listing showed no configuration function links
after the earlier service teardown; the `usb.init restart` recreated them.

Kernel messages after that start showed:

```text
configfs-gadget gadget: acm ttyGS0: super speed ...
configfs-gadget gadget: acm ttyGS1: super speed ...
configfs-gadget gadget: acm ttyGS2: super speed ...
mtu3_gadget_pullup (on) for active device
USB3_EN = 1
gadget (super-speed) pullup D+
```

Later kernel messages showed repeated `gadget RESET` and `gadget SUSPEND` events.
There was no later `mtu3_gadget_pullup (off)` in the captured post-edit log.
This is consistent with the host attempting enumeration while the gadget
remained bound.

## Temporary retry-loop workaround

The router backup was created in volatile storage and the condition was
changed from:

```sh
if [ ! -f /dev/usb-ffs/adb/ep1 ]
```

to:

```sh
if false
```

The router then ran `/etc/init.d/usb.init restart`. Its first `Stop USB` phase
printed `write error: No such device` and `Command failed: Not found`, after
which the start phase selected `BootMode: 0001` and created/bound the META
configuration. The edit was made only on the working 1 GB router. The saved
backup path was `/tmp/restart_usb.sh.orig`; `/tmp` is volatile and may be lost
at reboot. The running script should be restored after this test, and the
normal boot should be used to leave META mode.

## Host enumeration evidence

### Windows USBView follow-up

The later Windows USBDeview screenshot
`/home/kali/Desktop/Screenshot 2026-10-08 150624.png` shows both the earlier
failed instance and a later successful instance. The invalid-configuration
entry (`VID_0000&PID_0006`, port `#0003`) is disconnected. A later connected
device is listed as `Linux File-CD Gadget USB Device`, VID `0e8d`, PID `202d`,
with drive letter `K:` and serial `0123456789ABCDEF`. Three connected child
serial functions appear as COM264, COM265, and COM266, also under `0e8d:202d`.

This is direct evidence that Windows successfully enumerated the META gadget
and all three ACM serial functions at the time of the screenshot. The user
reports the intervening action sequence was:

1. unbind UDC;
2. remove config link `f1` (mass storage);
3. rebind UDC;
4. disconnect and reconnect the USB cable.

The invalid-descriptor state cleared after this sequence. A later router
check confirmed that the UDC is bound to `11201000.usb`, config link `f1` is
absent, and `functions/mass_storage.usb0/lun.0/file` is empty. Thus the current
gadget is ACM-only, and the successful enumeration followed removal of the
mass-storage function (plus a physical disconnect/reconnect). This strongly
implicates the mass-storage function/link in the invalid configuration, though
the unbind/rebind and cable reconnection were part of the same experiment and
were not isolated separately.

USBDeview still displays drive letter `K:` for the saved gadget record. Since
the router currently has no `f1` link and the mass-storage backing file is
empty, that field is not evidence that mass storage is part of the current
enumerated configuration; it may be retained device-history metadata. Confirm
in Windows Explorer/Disk Management before treating `K:` as a live volume.

This Windows evidence supersedes the earlier statement below that no usable
VID:PID was available as the current state. It remains a valid description of
the failed enumeration attempt immediately before the unbind/rebind and cable
reconnection sequence.

Kali's host kernel recorded a new high-speed attach at `usb 3-2.1`, but the
provided log excerpt had no subsequent `New USB device found` line and `lsusb`
listed no `0e8d:202d` or other replacement identity. Windows separately showed
an “Unknown USB Device (Invalid Configuration Descriptor)” entry. Its
instance path was `USB\VID_0000&PID_0006\...`, with `usb.inf` and
`BADDEVICE.Dev.NT`. This is more specific than a generic unknown-device popup:
Windows is reporting that it rejected the configuration descriptor. Kali's
log still shows only an attach and no usable VID:PID. This raises the
configuration/function descriptor composition as the leading area to inspect;
the exact malformed field has not yet been captured. Cable, controller, and VM
forwarding issues are less consistent with this specific Windows diagnosis,
but cannot be fully excluded without a descriptor or bus trace.

The router's successful ACM bind and pullup messages show that configfs
accepted the functions and the UDC was asked to connect. Later Windows
enumeration proves successful host descriptor handling for the ACM-only
configuration. Removing the mass-storage link is strongly associated with
recovery from the invalid-configuration error, though the accompanying UDC
cycle and cable reconnection were not independently controlled.

## Boza X17 comparison

The reviewed paths under `/home/kali/Desktop/bozax17` contain no notes recording
a USB descriptor workaround. The old and new extracted trees have byte-identical
hashes for:

| File | SHA-256 |
|---|---|
| `etc/init.d/usb.init` | `21077ebe11877101ba41be6eab15d7159fa91b50b30d8a9b08648c9b406df6d7` |
| `etc/restart_usb.sh` | `b5ac7df120332004f887dbfca0aff43b3e171d28a1c0993fc48204c05917e7d5` |
| `etc/start_usb.sh` | `ffed6e60126a4d6c188b661c521cdde18071f0d2abe8abbc238585b01186ff7b` |

Those `usb.init` and `restart_usb.sh` hashes also match the factory copies
recorded in `X17M_1GB_FACTORY_META_BOOT_CHAIN.md`. The Boza `start_usb.sh`
waits for `/sys/module/mtu3/parameters/aplog_usb_port` to equal `1 0`, then
waits ten seconds before binding the UDC. This is an initialization timing
script, not evidence of a descriptor fix. No prior Boza edit explaining the
current Windows “unknown device” symptom was found in its tracked notes or
extracted USB scripts.

## Current interpretation and next evidence

### Kali host follow-up

The later Kali `dmesg` capture records successful enumeration in the current
ACM-only state:

```text
New USB device found, idVendor=0e8d, idProduct=202d, bcdDevice=2.23
Product: mt6890
Manufacturer: Mediatek
SerialNumber: 0123456789ABCDEF
cdc_acm ... ttyACM0
cdc_acm ... ttyACM1
cdc_acm ... ttyACM2
USB disconnect, device number 31
```

The host emitted `Device not responding to setup address` once, then read the
device identity and registered all three ACM interfaces. It logged disconnect
about 7 ms after the final ACM registration. Earlier in the same excerpt the
guest xHCI path repeatedly reported `Cannot enable`, followed by `unable to
enumerate USB device`, and `urb submitted to disabled ep`. Thus the current
configuration is descriptor-valid when enumeration succeeds, but the capture
does not show a stable connection. These messages fit a connect/disconnect or
host-controller/passthrough problem; they do not prove the router initiated
the disconnect.

A subsequent Kali capture shows a longer stable interval: the same
`0e8d:202d` identity and three ACM ports were present at monotonic time
28891.38, then Kali logged `USB disconnect` at 29032.879 (about 141.5 seconds
later). The user confirmed this was a deliberate unplug. Thus no spontaneous
disconnect is established by this interval. After the cable was reconnected,
enumeration attempts produced repeated `Cannot enable` and `unable to enumerate
USB device` messages, along with `urb submitted to disabled ep` warnings. The
reconnect enumeration failure remains unexplained and points to the host/USB
link path for further diagnosis.

Confirmed:

* Preloader accepts META and LK passes mode 1 to Linux.
* Linux chooses PID `0x202d` and configures three ACM functions plus mass
  storage.
* The original ADB-endpoint retry loop caused repeated reinitialization and
  teardown; bypassing the condition keeps the UDC bound.
* After the reported UDC unbind, `f1` removal, UDC rebind, and cable
  reconnection, Windows enumerated `0e8d:202d` and exposed three ACM serial
  ports as COM264–COM266.
* A subsequent router check confirmed UDC `11201000.usb`, no `f1` link, and an
  empty mass-storage backing-file attribute. The current gadget is ACM-only.
* Kali successfully enumerated `0e8d:202d` and registered `ttyACM0` through
  `ttyACM2`, then logged a disconnect.
* The user confirms the disconnect after about 141 seconds was manual. The
  subsequent reconnect attempts failed at port enable/enumeration.
* An earlier enumeration attempt on the same date failed as
  “Invalid Configuration Descriptor”; it is now a transient failure rather
  than the current state.

Not confirmed:

* Whether removal of `f1` alone clears the invalid-descriptor condition; the
  test also unbound/rebound the UDC and reconnected the cable.
* Whether the router, physical USB link, host controller, or VMware USB
  forwarding caused the rapid disconnect.
* Any specific Boza X17 descriptor edit. The inspected Boza USB scripts match
  the factory files byte-for-byte.

If desired, re-add `f1` while the UDC is unbound and rebind to test whether the
invalid-descriptor error returns; this is a reversible runtime-only comparison.
If it recurs, capture the descriptor request and response with
USBPcap/Wireshark and compare it with the successful ACM-only enumeration.

## Bootlooped 1GB target: META selector test (2026-10-08)

Evidence is in `live_meta_usbdiag_1gb/20261008T133745Z/`. Unlike the earlier
working-router USB-gadget tests, this run was performed on the bootlooped
device. The host detected the MediaTek preloader (`0e8d:2000`, interface 1,
bulk IN `0x81`, bulk OUT `0x01`) and completed the selector exchange:

```text
INITIAL_READY → METAMETA → ATEM0001 → V1 → ATEM0002 → V2 → ATEMATEX → DISCONNECT
```

This confirms the bootlooped target's preloader accepts the same META selector
sequence. It does not yet prove that LK or Linux booted afterward: the run's
USB timeline does not record a subsequent Linux gadget identity, and UART
capture did not start. `uart_events.log` reports that opening `/dev/ttyUSB0`
failed with `Errno 2` (path absent); `uart_raw.bin` is empty. This is a Kali
host/VM adapter visibility issue, not evidence of a UART failure on the router.

Next action: pass the FT232R adapter through to the Kali guest, verify its
actual `/dev/ttyUSB*` path, close any other serial terminal, and rerun the
capture during a bootlooped-device power cycle. Keep the capture passive; do
not transmit on UART. Capture both UART and USB identity changes to determine
whether META mode proceeds into LK/Linux on this target.

## UART console log: OpenWrt failsafe reached (2026-10-08)

A later pasted UART excerpt shows the device booting LK in normal mode
(`lk boot mode = 0`), handing off to the Linux kernel, and reaching the OpenWrt
failsafe shell. The kernel command line selects `root=/dev/mtdblock42` and
`bootslot=b`. The failsafe banner and interactive `~ #` prompt confirm that
this is not a preloader/LK-only failure; at least this boot reached Linux and
failsafe userspace. The excerpt also shows the root filesystem is read-only
while in failsafe (`mkdir: can't create directory '/var/': Read-only file
system`), which is consistent with a constrained recovery environment.

This makes a META-mode flash unnecessary for the immediate next diagnostic
step if this log came from the bootlooped unit: use failsafe to inspect the
active slot, mounts, MTD partition table, and boot configuration before any
repair. The source unit is not independently identified in the pasted excerpt,
so do not treat it as proof that the bootlooped unit has already been
recovered. Do not run `firstboot -y`, erase partitions, or write firmware as
part of this inspection; those actions can destroy configuration or worsen
recovery prospects.

Follow-up UART commands succeeded after opening the console with picocom.
`/proc/mtd` confirms `mtd42` is exactly `rootfs_b` (size 64 MiB), matching
both `root=/dev/mtdblock42` and `bootslot=b`. The table also shows the paired
`rootfs_a` at mtd29, `rootfs_sig_b` at mtd41, and `rootfs_data` at mtd43.
This establishes that the captured boot selected the B root filesystem; it
does not by itself establish why normal startup enters failsafe or whether
the same capture came from the bootlooped unit. Next gather mount state and
boot errors read-only before considering repair.

Failsafe diagnostics received: `/dev/root` is SquashFS mounted read-only at
`/`; `/dev/root` reports 50.5 MiB used of 50.5 MiB, which is the compressed,
read-only root image and is not evidence of a full writable flash filesystem.
No overlay or `/dev/mtdblock43` (`rootfs_data`) is mounted in this failsafe
mount namespace. `/tmp` is a writable 301 MiB tmpfs. `logread` returns
`Failed to connect to ubus`, expected in this minimal failsafe environment.
The attempted quoted `dmesg | grep` commands were interrupted while the shell
was waiting for a closing quote, so no filtered kernel-error output was
collected. Next use a simple unquoted `dmesg | tail -n 40` and inspect
`/overlay` and `/dev/mtdblock*` without mounting or writing anything.

Those follow-up checks returned: `/overlay` exists but is empty; all
`/dev/mtdblock0` through `/dev/mtdblock51` device nodes exist. The last 40
kernel-log lines are mostly watchdog/SoC idle messages, with one UART console
input-overrun notice; they do not expose an earlier rootfs/overlay failure.
The captured boot transcript contains repeated literal `f` input immediately
before the failsafe banner. Because the failsafe prompt is explicitly
activated by pressing `f` during a short boot window, unintended UART RX data
(or a deliberate keypress) could explain this failsafe entry. This is a
hypothesis, not yet confirmed as the cause of the reported bootloop. Next
repeat a cold boot with the serial adapter receive-only (router TX -> adapter
RX and GND connected; adapter TX disconnected) to prevent UART input from
selecting failsafe, while observing whether the router boots normally or
reproduces the issue. Avoid filesystem/flash writes until this distinction is
resolved.

## Subsequent boot trace: slot B reaches Linux handoff

A subsequent serial trace shows slot B selected (`ab_suffix: _b`), with
`ab_retry: 2` and `ab_boot_success: 1`. Secure-boot verification succeeds for
the B-side SSPM, MCUPM, TEE/ATF, LK, modem, and `boot_b` images; LK logs
`boot_b cert chain vfy pass`, `image mt6890 auth pass`, then hands off to the
kernel with `root=/dev/mtdblock42`, `bootslot=b`, and `lk boot mode = 0`.
The trace reaches the Linux early userspace board-detect messages and the
two-second failsafe prompt, but the excerpt does not show a failsafe-active
banner or confirm that normal userspace/network startup completed. It also
contains no evidence here of a secure-boot rejection or failure loading the B
kernel. The source identity and whether the UART adapter TX line was
disconnected during this specific capture are not explicit. Recheck normal
boot completion with adapter TX disconnected, without pressing keys; regard
this as successful Linux handoff, not yet verified full recovery.

Correction from user comparison: UART output also normally stops after the
failsafe prompt on a working router. Therefore, the lack of further serial
output after that prompt is not evidence of a hang and must not be used to
distinguish working from failed units. The meaningful symptom remains that the
unworking unit does not provide network service and has only the power LED
(network LED briefly lights then goes dark). Compare this unit's failsafe
state and writable-overlay/startup configuration against the working 1 GB
unit; do not infer failure solely from the quiet UART console.

Latest failsafe check reconfirmed `/dev/root` as read-only SquashFS and an
empty `/overlay`. This is the normal OpenWrt failsafe arrangement: writable
`rootfs_data` is deliberately not mounted there, so this result alone does
not indicate overlay corruption. The documented next diagnostic is
`mount_root`, then inspect the mounted overlay/configuration; do not use
`firstboot`, `jffs2reset`, `mtd erase`, or raw `dd` writes. Reference:
OpenWrt's [failsafe and factory reset guide](https://openwrt.org/docs/guide-user/troubleshooting/failsafe_and_factory_reset).

After `mount_root`, the actual mounts show `/dev/root` on `/rom` (SquashFS,
read-only), while the writable `/` overlay is `overlayfs:/tmp/root` backed by
`tmpfs` (301 MiB). `df` confirms `/tmp/root` is empty. The persistent MTD
partition `rootfs_data` (mtd43) was therefore not mounted; `mount_root` has
provided a volatile failsafe overlay. Any file edits now would be RAM-only
and lost at reboot. This is the documented temporary-tmpfs fallback when the
JFFS2 overlay is not available/ready; it raises a concrete investigation of
why the rootfs_data filesystem is not mounted but does not, alone, prove
hardware or filesystem corruption. Next collect read-only JFFS2/overlay kernel
messages and filesystem support before attempting repair. Do not use
`firstboot`, `jffs2reset`, erase, or raw writes.

## Persistent META recovery candidate (built, not flashed)

A separate candidate was built from the verified ten-second failsafe tree,
leaving `rootfs_patched_v17_10s` and its image unchanged. The source tree is
`rootfs_patched_v17_10s_meta`; the image is
`rootfs_patched_v17_10s_meta.img`.

The candidate changes only the Linux USB setup for META recovery:

- `etc/init.d/usb.init` reads `/proc/device-tree/chosen/atag,boot` before
  starting ADB FunctionFS. When the boot mode is `0001` (META), it does not
  mount ADB FunctionFS or start `adbd_usb`.
- The META USB configuration retains VID `0e8d`, PID `202d`, and three ACM
  functions (`gs0`–`gs2`), and omits the mass-storage function link. The
  mass-storage function directory remains available for the unchanged normal
  profile; it is not part of the META configuration.
- `etc/restart_usb.sh` recognizes META mode and keeps the UDC-bound ACM gadget
  alive without retrying `usb.init` due to the intentionally absent ADB
  endpoint. Normal mode retains its existing retry behavior.

The existing selector path remains on-demand: Preloader receives the META
selector sequence, LK passes mode 1, and Linux selects this USB profile. This
candidate does not force META mode or modify boot selection. This is important
because the user reports `firstboot -y` erased `nvdata` and `boot_para`; do not
repeat that command or change `boot_para` as part of this recovery work.

Candidate metadata:

| Property | Value |
|---|---|
| Size | 55,738,368 bytes |
| SHA-256 | `8452ae84d77172ac9f77695321678d0372cee87ee6fe1ec7d91ab8a88dfa45e5` |
| Base image SHA-256 | `6469a522780382293c0f62bc412b55d5477188ed547e6754db5bebd3e5cae872` |
| Build | SquashFS 4.0, XZ, 262144-byte blocks; includes the `/dev/console` pseudo entry |

This candidate has been built but has not been flashed or live-tested. The
successful prior META selector and ACM enumeration tests were on the separate
known-working 1 GB X17M, not proof that this candidate works on the recovery
target. Keep the verified `rootfs_patched_v17_10s.img` as the known-good
failsafe fallback.

## META candidate flashed: brief ACM enumeration observed

The user reports flashing `rootfs_patched_v17_10s_meta.img` to `rootfs_b`
and rebooting with the Preloader META selector. The pasted LK trace confirms
`lk boot mode = 1`, and Linux begins. Kali's USB log then records a successful
read of VID `0e8d`, PID `202d`, product `mt6890`, manufacturer `Mediatek`, and
serial `0123456789ABCDEF`; the kernel registers all three interfaces as
`ttyACM0`, `ttyACM1`, and `ttyACM2`. This confirms that the flashed image
reaches Linux in META mode and that the host can enumerate the intended
ACM-only gadget at least briefly.

The same capture records `USB disconnect` immediately after ACM registration,
followed by repeated xHCI `Cannot enable`, `unable to enumerate USB device`,
`urb submitted to disabled ep`, and one `error -71` sequence. The log does not
show whether the router unbound/reset its UDC or the host/VM USB path lost the
device. Therefore the candidate's META profile has achieved brief enumeration,
but stable USB access is not yet verified. The host errors are consistent
with the previously observed xHCI/passthrough instability and do not by
themselves identify a router-side cause.

The attached USBDeview screenshot shows an older failed META instance
(`VID_0000&PID_0006`) and a connected `0e8d:202d` instance with three COM ports
(COM264–COM266). Its registry timestamps precede or overlap the user's latest
flash report, so it is retained as corroborating host history, not attributed
specifically to the newly flashed candidate. The latest Kali `dmesg` is the
direct evidence for the candidate's brief enumeration.

For the next observation, preserve the router's current META boot and avoid
reflashing. If the USB link drops again, capture the router-side state through
the serial ACM ports or UART: boot mode, `cat /config/usb_gadget/g1/UDC`, the
three config links under `configs/b.1`, and recent `dmesg` lines containing
`mtu3`, `gadget`, `USB`, or `acm`. On Kali, correlate `dmesg -w` timestamps
with the router output. If the router remains bound while Kali reports
`Cannot enable`, focus next on host-controller/VM passthrough and cable/port
behavior; if the router UDC becomes empty or its init script restarts, inspect
the router-side USB service.

## Router-side META gadget state after candidate flash

After the candidate flash, the user confirmed shell access over UART and
network/telnet access. The boot-mode property returned:

```text
0000000 0003 0000 0802 4100 0001 0000 0002 0000
```

This agrees with LK's `lk boot mode = 1` and confirms META mode. Router-side
USB checks then showed:

```text
/config/usb_gadget/g1/UDC: 11201000.usb
configs/b.1/f1 -> functions/acm.gs0
configs/b.1/f2 -> functions/acm.gs1
configs/b.1/f3 -> functions/acm.gs2
```

No mass-storage link is present. The UDC remained bound and all three
ACM-only configuration links remained in place while the host had reported a
USB disconnect. This makes a router-side gadget teardown less likely for that
particular disconnect and shifts the next investigation toward the host/VM USB
path or link stability, while not ruling out a transient controller-side
reset. Router `dmesg` repeatedly printed `mtu3 ... === U2COMM[200] ===` during
this interval; that log line alone does not establish the disconnect cause.

Current result: the flashed candidate boots in META mode, supplies network
and UART shell access, and maintains its expected bound ACM-only gadget. Kali
has successfully enumerated the gadget and three ACM interfaces at least once,
but the host-side USB connection was not stable in the supplied capture.

## Live NAND A/B boot-control record read

The user sourced the firmware's `/lib/upgrade/platform.sh` and
`/lib/upgrade/bootctrl.sh` and ran only the read helpers. They reported:

```text
FLASH_TYPE=nand
BOOTCTRL_DEV=/dev/mtd/misc
get_bootctrl 2048 16: 00414230ffffffff0e0201010f020101
get_bootctrl 2056 4: 0e020101
get_bootctrl 2060 4: 0f020101
get_current_slot: _b
```

The boot-control magic is `00414230`. At the helper's documented offsets,
slot A has priority/retry/success/update-type bytes `0e 02 01 01`, while B has
`0f 02 01 01`. Thus B has higher priority and the firmware helper selects B,
matching the observed `bootslot=b` and `root=/dev/mtdblock42`. This also shows
the record in `misc` remains readable; the earlier `firstboot` output named
erasures of `nvdata` and `boot_para`, not `misc`.

This confirms that the router is not simply locked to A or B: its Linux OTA
code contains NAND boot-control read/write routines and uses the per-slot
priority bytes. However, LK's separate fastboot `set_active` command is a stub
(`set active slot: not supported!`), so there is no supported standard-fastboot
slot switch. No boot-control bytes have been changed in this live check.

The record alone does not prove why the original bootloop stayed on B. A/B
boot selection and Linux recovery are distinct: this device's firmware can
select a slot by priority, but an intact priority record does not demonstrate
that Preloader/LK will detect a failure occurring later in rootfs/userspace and
fall back. The present log shows B was selected; further interpretation of the
failure policy requires the corresponding LK/boot-control trace. Do not test a
manual priority write until there is a verified backup and the A-side image set
has been checked for compatibility.

## RNDIS internet-sharing path found in firmware

The Windows USBDeview entry for VID:PID `0e8d:2028` shows that the normal USB
profile enumerated an RNDIS interface and Windows bound its built-in RNDIS6
driver. This proves USB function enumeration/driver binding; it does not prove
that DHCP, routing, or Internet forwarding is working.

Static inspection of the flashed candidate's normal-mode scripts shows:

- `/etc/init.d/usb.init` selects PID `0x2028` for normal boot mode `0000` and
  links `rndis.gs4` into the USB configuration. META mode `0001` instead uses
  the tested ACM-only profile with PID `0x202d`.
- `/etc/init.d/fibo_rndis.init` explicitly exits in META mode. In normal mode,
  when `/data/startup_option` is `1` (the default if absent), it runs
  `/usr/bin/mtk_usb_tether_on.sh`.
- That helper adds `rndis0` and `ecm0` to `network.@device[0].ports`, commits
  UCI, and cycles the LAN interface. Thus the intended router-to-host path is
  to bridge the USB network function into LAN; internet service then also
  depends on normal DHCP, WAN connectivity, and firewall forwarding.

The user has since clarified that they rebooted from META back into normal
mode. Therefore the RNDIS profile should now be active; the earlier observation
that META disables tethering applies only while booted with mode `0001`. The
Windows `0e8d:2028` entry is consistent with normal-mode enumeration. The
desired traffic direction (router Internet to PC, or PC Internet to router)
remains to be confirmed before choosing a network repair.

## Normal-mode RNDIS tether diagnostics from router

The user clarified the router had rebooted back to normal mode. In that state,
Windows showed the `0e8d:2028` RNDIS6 interface. Router-side output reported:

```text
uci get network.@device[0].ports: eth0 rndis0 ecm0
ip link show rndis0: state DOWN, no UP/LOWER_UP flags
brctl show: bridge br0 contains eth1 only
cat /data/startup_option: file does not exist
ubus call network.interface.lan status: Command failed: Not found
ubus call network.interface.wan status: Command failed: Not found
```

This separates USB enumeration from network forwarding: the USB interface is
created and listed in UCI, but it is down and absent from the runtime `br0`
bridge shown by `brctl`. The missing `ubus` interface objects also mean the
usual OpenWrt `network.interface.lan/wan` status query is not useful on this
running vendor image. The absent `/data/startup_option` may cause the init
script to fall back to its default, but we need the `/etc/startup_option`
source and service log to confirm the service actually ran. Do not add
`rndis0` to `br0` yet: the live `/etc/config/network` is needed to establish
which bridge is the LAN bridge and how this vendor image configures routing.

## Follow-up: normal-mode bridge and upstream route findings

The user confirms normal boot and prefers router Internet to the PC. Additional
router output shows UCI's configured LAN device is `br-lan` with ports `eth0`,
`rndis0`, and `ecm0`, and LAN IP `192.168.1.1/24`. However, runtime
`ifconfig`/`brctl` show only `br0` at `192.168.0.1/24`, with `eth1` as its sole
bridge member; there is no runtime `br-lan`. `rndis0` is present but DOWN with
zero RX/TX counters. `ip route show` contains only the connected
`192.168.0.0/24` route and no default route. Thus neither the configured bridge
nor an upstream Internet route is currently available in the runtime state.

The normal-mode tether hook did execute. Its log records failure to copy the
missing `/etc/startup_option`, then defaults to option `1` and invokes
`mtk_usb_tether_on.sh`. That helper exits immediately because UCI already lists
`rndis0`, printing `'rndis0' existed, no need to up again`; consequently it
never reaches its `ifdown lan` / `ifup lan` reload. USB configfs itself is
bound to `11201000.usb`, and config `b.1` has the RNDIS function linked at f1
plus ADB/ACM functions. Kernel logs show RNDIS setup, but no data packets.

Before any bridge change, inspect the actual WAN/modem status and network
manager processes. The no-default-route state means even a successful RNDIS
bridge cannot currently deliver Internet from this router. Do not apply a
blind `brctl addif` to `br0` or repeatedly run the tether helper until the
vendor runtime bridge/WAN mapping is understood; the saved UCI device name and
runtime bridge name disagree.

## Network-manager correction and SIM/WAN state

The user clarifies that the device does not use the usual OpenWrt network
management binaries. This matches the live results: `ubus call
network.interface.* status` returns Not found, and `ps` showed no `netifd`
process (only `dnsmasq.real`). Treat UCI values as vendor configuration state,
not proof that Linux runtime networking has applied them; use the vendor's own
manager/scripts and live interfaces for diagnosis.

After the user inserted a SIM, `mipc_wan_cli --show_sim_status` returned
`MIPC_SIM_STATUS_COMPLETE_READY`, but `ccmni0` remained down with zero packet
counters and `ip route show` still had no default route. Thus the SIM is
recognized, but a cellular data session is not established. The pasted
multi-command terminal echo appears interleaved; the apparent `network.wan`
values (`proto=dhcp`, `device=eth1`) should be re-read one command at a time
before relying on them.

The firmware includes vendor script `/usr/bin/mtk_wan_mipc.sh`, which reads
APN provisioning from `mipc_wan_cli --apn_provision_by_sim`, sets WAN proto to
`mipc` and device to `ccmni`, commits UCI, and restarts the vendor network
service. This is an available intended configuration path, not yet run in this
session. The current state needs both an established cellular WAN/default
route and a live RNDIS-to-LAN bridge before the PC can get router Internet.

## Cellular WAN provisioning versus data-call activation

The user ran `/usr/bin/mtk_wan_mipc.sh`. It provisioned APN `telkom`, PLMN
`63907`, IP type `1`, RAT type `21`, and set `network.wan.proto=mipc` with
`network.wan.device=ccmni`. It did not create a route; `ccmni0` remained down.

Static inspection explains why its network restart did not start the WAN:
`/etc/init.d/network` has a `start_service()` that prints `Tozed not run
netifd` and exits before the stock netifd launch. The APN helper therefore
persists settings and returns, but `restart` is not an active interface bringup
on this vendor build.

The firmware includes vendor binaries `mtk_act_data_call` and
`mtk_deact_data_call`. Its bundled `/usr/bin/nettest.sh` calls the former to
activate a data call, tests connectivity, then calls the latter; however, that
test script repeats 1001 cycles and is unsuitable for a one-time connection
attempt. The current next step is a single explicit `mtk_act_data_call` after
checking mobile network registration, then inspect `ccmni0`, the default route,
and connectivity. The action has not yet been run.

## Cellular antenna state

The user identified that the router antennas had been disconnected during UART
access and is reconnecting them. This plausibly explains why the inserted SIM
reported `MIPC_SIM_STATUS_COMPLETE_READY` while `ccmni0` remained down and no
WAN route existed: SIM readiness does not establish cellular network
registration or a packet-data session. Recheck `mipc_wan_cli --check_nw_status`
after the antennas are reconnected; then start one data call if registered.

## Cellular route appears after antenna reconnection

The user subsequently reported:

```text
default dev ccmni1 scope link
10.64.157.80/30 dev ccmni1 proto kernel scope link src 10.64.157.82
192.168.0.0/24 dev br0 proto kernel scope link src 192.168.0.1
```

This shows the modem has now installed an IPv4 cellular default route through
`ccmni1` with address `10.64.157.82`. The earlier `ccmni0` down state does not
contradict this: the active data session is on `ccmni1`. Router-to-Internet
reachability still needs a ping/DNS check, and PC sharing still needs the
RNDIS interface brought up and attached to the actual runtime LAN bridge.

## Router cellular Internet confirmed

The user successfully pinged both `8.8.8.8` and `google.com` from the router,
with no packet loss. The cellular uplink, IP routing, and DNS are therefore
working. The remaining objective is sharing that working connection over the
normal-mode RNDIS USB interface to the PC. The previously observed RNDIS
interface was down and absent from the live `br0` bridge.

## RNDIS runtime bridge test succeeded; persistent candidate built

The user ran:

```sh
ifconfig rndis0 up
brctl addif br0 rndis0
```

`brctl show` then listed `rndis0` under `br0`. The Windows RNDIS adapter
received DHCP address `192.168.0.138`, gateway and DHCP/DNS server
`192.168.0.1`, and Windows displayed Internet access on the RNDIS adapter.
This confirms the immediate PC-sharing failure was the missing runtime bridge
membership; with the router's cellular route active, the temporary bridge
change successfully passes internet to the PC.

A separate persistent candidate was built from the tested META/failsafe image.
It changes `/usr/bin/mtk_usb_tether_on.sh` so it no longer exits just because
UCI already lists `rndis0`. The script ensures saved UCI membership when needed,
selects an existing `br-lan` bridge or falls back to the observed vendor bridge
`br0`, brings available `rndis0`/`ecm0` interfaces up, and attaches them to the
runtime bridge. It avoids `ifdown`/`ifup`, which cannot apply bridge state here
because `/etc/init.d/network` explicitly does not run netifd. The normal-mode
`fibo_rndis.init` continues to skip this path in META mode.

Persistent candidate metadata:

| Property | Value |
|---|---|
| Image | `rootfs_patched_v17_10s_meta_rndis.img` |
| Size | 55,738,368 bytes |
| SHA-256 | `0a592ac93ec08b4d0af4cb246e04251fc7db2db66d38e22c3043fdc7d9019980` |
| Base | `rootfs_patched_v17_10s_meta.img` |

This candidate was later used as the base for
`rootfs_patched_v17_10s_meta_rndis_dialer.img`, which was flashed along with
the patched dialer on 2026-10-08. After reboot, `rndis0` existed but was down
and absent from `br0`, so the candidate's startup change did not attach it
automatically. Running `ifconfig rndis0 up` followed by `brctl addif br0
rndis0` attached it; the PC then regained Internet access through the router.
Automatic attachment after boot remains unresolved. The earlier META and
ten-second failsafe images remain unchanged.
