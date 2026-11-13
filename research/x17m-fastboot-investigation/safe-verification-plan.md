# Proposed safe live verification

**Status: proposal only. No commands in this document were run against hardware.** Stage 1 inspects an already running device; stage 2 observes an already existing boot loop if available. Any reboot, power cycle, mode selection, service reconfiguration or UART transmission requires separate explicit authorization.

## 1. Lowest-risk next experiment: current-state snapshot

Use the already configured connection and an explicit serial/transport selection. Do not run `adb connect`, restart adbd, configure the gadget or change USB mode to make a missing connection appear. `adb devices -l` can start the host ADB server and communicate with existing transports, but it is not a router reboot request.

On the host, capture outputs to host files:

```sh
adb devices -l
lsusb
lsusb -t
fastboot devices -l
```

If a specific USB device is already visible, use its observed bus/device number:

```sh
lsusb -v -s BUS:DEVICE
```

This performs USB descriptor/control reads; it is not electrically passive, but it sends no vendor flashing command. Permission errors are evidence, not justification to detach drivers or reconfigure interfaces. Do not infer absence from `fastboot devices` alone: verify permissions, interface descriptors, tool version, and visibility to the host/VM.

For a router already reachable through existing ADB, replace SERIAL with its exact `adb devices -l` identifier. Run bounded separate shell commands:

```sh
adb -s SERIAL shell 'uname -a; cat /proc/cmdline; cat /proc/mtd'
adb -s SERIAL shell 'if test -r /proc/bootbank; then cat /proc/bootbank; fi'
adb -s SERIAL shell 'if test -r /proc/bootslot; then cat /proc/bootslot; fi'
adb -s SERIAL shell 'if command -v getprop >/dev/null 2>&1; then getprop; fi'
adb -s SERIAL shell 'ls -l /sys/class/udc; ls -l /sys/bus/platform/drivers/syscon-reboot-mode'
adb -s SERIAL shell 'cat /proc/mounts; cat /proc/uptime'
adb -s SERIAL shell 'if test -r /proc/device-tree/chosen/atag,boot; then hexdump -C /proc/device-tree/chosen/atag,boot; fi'
adb -s SERIAL shell 'cat /etc/openwrt_release; cat /etc/init.d/usb.init; cat /etc/restart_usb.sh'
adb -s SERIAL shell 'ls -l /sbin/adbd*; cat /sys/devices/platform/11201000.usb/mode'
adb -s SERIAL shell 'cat /config/usb_gadget/g1/idVendor; cat /config/usb_gadget/g1/idProduct; cat /config/usb_gadget/g1/UDC'
adb -s SERIAL shell 'ls -l /config/usb_gadget/g1/configs/b.1; dmesg'
```

These inspect state. Missing files/tools are expected on OpenWrt; record errors. `/proc/bootbank` and Android properties are not assumed. Avoid running vendor `get_bootctrl` helpers: some create temporary target files and rely on NAND-specific behavior. Do not run arbitrary debugfs, procfs action nodes or `devmem` reads. The files above are bounded known state/configuration sources.

If already accessible, read DT `.../reboot-mode/mode-bootloader`, its `compatible`, `offset`, and `mask` under the observed `/proc/device-tree` path with `hexdump -C`; locate directories using `find /proc/device-tree -type d -name reboot-mode`. Hash `/sbin/adbd_usb` with an installed hash utility or pull only that ordinary file to the host. This distinguishes the analyzed vendor daemon from the actual running one. No restart test follows automatically.

**Decision:** if Linux is unavailable, stop trying shell commands. That is not permission to reboot, start META, or launch a DA.

## 2. Passive observation of an existing boot loop

Record host USB kernel events and descriptors without cycling power. An established electrically safe UART setup may receive only; no keystrokes, break signal, modem-control toggling or reset line. Historical guidance calls for proper 1.8 V level compatibility, router TX -> adapter RX and common GND, no adapter power lead. Verify the exact board electrical level before attaching anything. Do not change pins/straps or short test points.

Capture build banners, selected partitions, LK app starts, LK boot mode and any `Notify/Ready to enter fastboot`, UDC-init or authentication messages. Timestamp against USB transitions. Observe a bounded interval and preserve failures. Repeating a natural loop is observation, but initiating a new power cycle is an authorized test boundary.

## 3. Only if Fastboot is already present

After matching descriptor `ff/42/03` and the correct router serial/USB path, the first protocol probe may be:

```sh
fastboot -s SERIAL getvar version
fastboot -s SERIAL getvar product
fastboot -s SERIAL getvar is-userspace
```

Use a host timeout if it hangs; terminating a host process does not authorize a device reset. Record stdout and stderr (Fastboot commonly prints getvar on stderr). A response `OKAY`, `FAIL`, or `INFO` establishes protocol behavior; `FAIL` on an unsupported variable is not proof of no Fastboot. Start with individual getvars, not OEM commands or an automatic command sweep. Observe the compiled idle-reboot timer: even read-only queries can affect timing; absence of a host write command does not guarantee the bootloader never writes its own metadata.

## 4. Separate future entry experiment, not authorized here

Prerequisites: establish exact unit/build; stabilize USB enumeration/VM visibility; recover the event-signaling path and preloader FASTBOOT case; review timer, reason-register and misc side effects; identify how a failed entry can be ended safely; accept that independent unbrick is not validated.

A single selector exchange during an already occurring preloader window is the leading bootloader-independent candidate. Prefer it over editing persistent flags, but do not call it proven RAM-only on the current build. Use exactly `FASTBOOT`, require `TOOBTSAF`, then only observe. Do not inherit META's `DISCONNECT`. Stop on any unexpected bytes/identity; no fallback to MTKClient, DA or exploitation. This operation can halt normal startup, lose WAN service, hit a watchdog or require a later separately authorized restart.

`adb reboot bootloader` is a separate reboot experiment only after the deployed daemon/kernel reason handler is identified. `adb reboot fastboot` is lower priority because the decoded DT lacks that mode name. Neither is included in stage 1.

## Command classes

| Class | Examples | Execution status |
|---|---|---|
| Inspect state | lsusb/descriptors, existing ADB shell reads, fastboot devices, selected getvars if already exposed | Proposed; no hardware contact made here |
| Restart/change boot flow | adb reboot variants, fastboot reboot/continue, preloader FASTBOOT selector, power/reset button | Explicit separate approval required |
| Persistent configuration or reset | misc writers, bootctl/set_active, fw_setenv, UCI mode changes, firstboot/reset helpers, gadget reconfiguration | Prohibited in this investigation |
| Firmware/memory/security operations | fastboot flash/erase/boot/unlock, mtd write, DA upload/jump, raw memory writes, security patches | Prohibited in this investigation |

`fastboot boot` may avoid a flash write but still executes an untrusted image and changes boot flow; it is not a read-only probe. `oem mrdump` can trigger diagnostic transfer/reset behavior and is outside the query allowlist.
