# USB identification and protocols

## Observed identities versus compiled configurations

| Identity | Meaning and evidence | Status |
|---|---|---|
| `0e8d:0003` | BootROM-facing MTK stage in prior USB timelines; CDC ACM observed | **CONFIRMED** historical enumeration; stage assignment corroborated by MTKClient source |
| `0e8d:2000` | `MediaTek / MT65xx Preloader`; CDC communication/data interfaces | **CONFIRMED** historical enumeration and selector transfers |
| `0e8d:201c` | AEE LK's compiled Android Fastboot USB identity | **CONFIRMED** static configuration; live exposure **UNKNOWN** |
| `0e8d:202d` | Vendor Linux META composite gadget | **CONFIRMED** script profile; early Sept 21 test did not enumerate it; later research documents Linux META access |
| `0e8d:2028` | Linux RNDIS/ADB/ACM profile, conditional on vendor configuration | **CONFIRMED** extracted script; exposure on a specific unit must be observed |
| `0e8d:202f` | Alternate Linux ADB/ACM profile | **CONFIRMED** extracted script; current exposure **UNKNOWN** |

A VID/PID is not sufficient to prove protocol compatibility. Standard Fastboot needs a vendor interface with class/subclass/protocol `ff/42/03` and bulk IN/OUT endpoints. [Android USB protocol requirement](https://android.git.googlesource.com/platform/bootable/libbootloader/+/9bb23ceb380d4b73068151ddd16b32cef267f4f0/gbl/docs/GBL_EFI_FASTBOOT_USB_PROTOCOL.md). MTKClient's own device list associates `0003` with BROM and `2000` with preloader; it does not identify these as Fastboot. [MTKClient source](https://raw.githubusercontent.com/bkerler/mtkclient/main/mtkclient/config/usb_ids.py).

## AEE transport decoded

**CONFIRMED:** data at parent file `0x82ba4` begins:

```text
8d 0e 1c 20 00 01 ...       # little-endian vendor 0e8d, product 201c
```

AEE function at `0x4eb9c` loads this structure via VA `0x8303cf34`, logs VID/PID, and passes it to UDC initialization at file `0x568b2`. At `0x4ebf6..0x4ec12`, it requests endpoints `0x82` and `0x02`, packet size `0x200` (512 bytes). Related gadget/interface structure at `0x82bc4` starts `ff 42 03 02`: Fastboot interface class, subclass, protocol, two endpoints. See [raw structures](evidence/usb-structures.txt) and [USB disassembly](evidence/usb-init-disassembly.txt).

**CONFIRMED:** the image also contains `usb_register_fastboot_controller_interface` in a linked initialization record at `0x828b0`. **UNKNOWN:** exact invocation order and all conditions for loading/starting this AEE image on the present hardware. The normal LK engine selects the `usb` controller name, but no complete normal-image controller path was recovered.

A scan for literal 18-byte USB device descriptors and 9-byte interface descriptors found no qualifying complete serialized descriptor. This does not contradict the structures above: LK builds descriptors from internal structures at runtime. The empty `usb-descriptor-candidates.txt` is a bounded negative result, not proof that USB support is absent.

## Other protocols and stages

- **BootROM mode — CONFIRMED:** immutable SoC-stage MTK transport for hardware/security discovery and DA authorization. It is distinct from Fastboot and does not itself establish authorized NAND access.
- **Preloader mode — CONFIRMED:** flash-resident initialization stage; CDC tool handshake, boot selectors, and DA transfer/authorization services. `FASTBOOT` here is an eight-byte selector, not the Fastboot USB command protocol.
- **LK mode — CONFIRMED:** ARM/Thumb bootloader runtime with gem_boot and Fastboot application framework; AEE LK is a separate payload. Being in LK does not imply active Fastboot.
- **Fastboot mode — CONFIRMED compiled capability; runtime UNKNOWN:** command transport with `getvar:` and response framing. [AOSP protocol](https://android.googlesource.com/platform/system/core/+/master/fastboot/README.md).
- **Recovery mode — UNKNOWN as independent rescue:** a declared reboot reason and Linux failsafe are not proof of a standalone recovery image.
- **Vendor download — CONFIRMED code/previous transfers:** MTK DA upload/jump path is the lower-level download route, with tested DA rejection. **UNKNOWN:** a matching authorized DA/storage implementation and usable full restore.
- **Linux META — CONFIRMED historical service:** ACM-based `meta_tst` protocol, dependent on working Linux, rootfs and gadget configuration. Its reconstructed file operations include writes; it must not be used casually as a read-only rescue tool.

The September 21 no-META-enumeration result and October META success concern different experimental states. Preserve both; do not repeat the earlier failure as proof that META never works. The recent broken rootfs lacks `/dev` and cannot be assumed to expose a Linux gadget.

## USB observation limitations

**CONFIRMED, prior logs/reports:** short preloader windows, disconnects and host `-110` address-assignment timeouts occur. **PROBABLE:** cable/controller/VM passthrough or timing issues contribute. **UNKNOWN:** exact electrical cause. A missed endpoint under those conditions cannot distinguish disabled Fastboot from failed enumeration.

The CDC data interface is class `0x0a`; the device descriptor must not be filtered to class 10. A previous script did that and missed a VID/PID that `lsusb` could see. Reviewed successful META evidence used interface 1, alt 0, IN `0x81`, OUT `0x01`; those endpoints belong to preloader, not LK Fastboot. No new descriptor requests were sent in this investigation.
