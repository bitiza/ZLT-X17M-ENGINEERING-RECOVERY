# Preloader recovery surfaces

## Internal capability is not host reachability

The exact Preloader contains partition, raw-NAND, NANDX and A/B maintenance routines used internally by the boot chain.

Finding `partition_read`, `raw_read`, NAND write/erase, or boot-control routines in the binary does **not** establish that a USB host can invoke them.

## Optional Preloader-as-DA service

The matching SDK contains an optional service:

| Command | Function | Behavior |
|---:|---|---|
| `0x70` | `usbdl_send_image()` | receive a whitelisted LK/logo/boot/ATF image into RAM |
| `0x71` | `usbdl_boot_image()` | jump to uploaded LK or ATF |

This is close to an ideal RAM-recovery architecture, but the code is conditional on `CFG_PRELOADER_AS_DA`.

Distinctive implementation strings such as `SEND: name = %s`, `SEND: Verify PASS`, `Jump to LK`, and `Jump to ATF` are absent from the exact 2025 X17M Preloader. Current evidence therefore classifies these commands as compiled out/not exposed in this build.

## LK handoff

The exact LK contains normal boot-image and ramdisk loading code. Its currently mapped fastboot surface, however, lacks a host image-transfer path.

## FACTS

- Preloader contains the storage machinery needed to boot and maintain NAND.
- The META selector does not dispatch to it.
- The SDK's optional RAM-image service appears absent from the production X17M Preloader.
- No proven Preloader/LK host command currently accepts a temporary recovery image.

## Recovery consequence

Internal storage capability cannot be used for recovery until a host-controlled path reaches it.
