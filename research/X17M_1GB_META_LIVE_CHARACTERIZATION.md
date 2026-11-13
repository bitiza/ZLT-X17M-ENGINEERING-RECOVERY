# X17M 1 GiB META live characterization

Date: 2026-09-21

## Scope

This was a controlled live USB experiment against the known-good 1 GiB NAND
router, after its complete backup was captured. It sent only the documented
Preloader META selector transaction. It sent no DA, memory, storage, erase,
flash, slot, reboot, fastboot, or post-META service command.

Evidence directory:

`live_meta_usbdiag_1gb/20260921T111339Z`

All evidence-file SHA-256 checks passed.

## Exact transaction

The USB timeline observed the normal MediaTek boot stages:

| UTC time | USB state |
|---|---|
| 11:14:50.057912 | `0e8d:0003` BootROM |
| 11:14:53.592365 | BootROM disconnect |
| 11:14:56.392243 | `0e8d:2000` MediaTek MT65xx Preloader |
| 11:14:58.629764 | Preloader disconnect |

The probe preserved the active configuration, selected CDC interface 1,
alternate setting 0, and discovered bulk IN `0x81` and OUT `0x01` from that
interface. It received an exact `READY`, then completed this exchange:

```text
11:14:56.439564  TARGET -> READY
11:14:56.440083  HOST   -> METAMETA
11:14:58.460794  TARGET -> ATEM0001
11:14:58.461936  HOST   -> v1 (12 bytes)
11:14:58.466126  TARGET -> ATEM0002
11:14:58.466570  HOST   -> v2 (16 bytes)
11:14:58.470092  TARGET -> ATEMATEX
11:14:58.470447  HOST   -> DISCONNECT
```

The roughly two-second gap between `METAMETA` and `ATEM0001` is consistent
with the source-correlated initial compatibility receive timeout. It confirms
that the exact September 2025 NAND Preloader accepts the selector and proceeds
through its complete META handshake.

## Post-META USB result

The Preloader disappeared 159 ms after `DISCONNECT`. During the following
90-second passive USB observation, Kali saw no `0e8d:202d`, Android gadget,
ADB USB identity, diagnostic port, mass-storage interface, or any other new
USB device.

The UART adapter was not attached, so this run has no UART handoff trace.

## Post-handoff router state

The existing network ADB connection remained reachable after the experiment.
Read-only checks found normal Linux command-line state:

```text
root=/dev/mtdblock29
bootslot=a
```

The router had been up approximately three minutes at the check, consistent
with a normal boot after the META handoff. Its services and watchdog were
running. This confirms that the experiment did not leave the working router
in a stuck Preloader state.

## Conclusions

1. META selection is implemented and accepted by the exact 1 GiB NAND
   Preloader.
2. The full selector exchange itself does not expose a USB META endpoint on
   this product. The expected Linux META PID `0e8d:202d` did not appear.
3. The router subsequently returned to normal A-slot Linux, so this route is
   currently a boot-mode/handoff mechanism rather than a demonstrated host
   recovery service.
4. No evidence from this run connects META USB input to NAND readback,
   `partition_read`, `raw_read`, or another storage protocol.

The next useful work remains static tracing of the post-META Preloader/LK
handoff and Linux META startup, then a passive no-interference UART capture of
the failed router once the 1.8 V adapter is available.
