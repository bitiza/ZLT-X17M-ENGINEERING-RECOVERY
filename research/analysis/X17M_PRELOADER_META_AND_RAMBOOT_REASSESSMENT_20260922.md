# X17M Preloader META and RAM-boot reassessment

Date: 2026-09-22  
Scope: offline, read-only analysis of the exact 2025 NAND Preloader/LK and the matching MT6890 SDK source. No device was contacted.

## Outcome

Preloader META is a boot-mode selector, not a persistent command service. In the source-correlated implementation, the only host-controlled bytes consumed after `METAMETA` are the fixed META parameter records and the optional ten-byte `DISCONNECT`. After that, Preloader sets `g_boot_mode = META_BOOT`, exits the handshake, and continues the normal authenticated boot chain. No post-`ATEMATEX` dispatcher remains listening for partition, NAND, memory, or boot commands.

The SDK also contains a potentially valuable Preloader-as-DA RAM-image service (`0x70 SEND_IMAGE`, `0x71 BOOT_IMAGE`), but it is conditional on `CFG_PRELOADER_AS_DA`. Its unique implementation strings are absent from the exact 2025 X17M Preloader, strongly indicating that this feature is compiled out.

## 1. Complete host input surface after META selection

The exact-binary/source-correlated transaction is:

```text
READY -> METAMETA
          |
          +-- receive 12-byte para_v1 compatibility record
          +-- send ATEM0001
          +-- receive 12-byte para_v1 record
          +-- send ATEM0002
          +-- receive 16-byte para_v2 record
          +-- send ATEMATEX
          +-- receive up to 10 bytes, expected DISCONNECT
          +-- g_boot_mode = META_BOOT
          `-- return from selector/handshake
```

The parameter records control META USB/modem/log fields. They are copied into boot arguments. They are not interpreted as operation codes, addresses, lengths, partition names, or function pointers.

The selector's complete recognized eight-byte command set is:

| Host token | Result |
|---|---|
| `METAMETA` | collect META parameters, select `META_BOOT` |
| `ADVEMETA` | acknowledge and select advanced META boot |
| `FACTFACT` | collect small parameter record and select factory boot |
| `FACTORYM` | collect small parameter record and select ATE factory boot |
| `FASTBOOT` | acknowledge and select fastboot boot mode |
| `AT+NBOOT` | select normal boot |

No selector branch calls `blkdev_read`, `partition_read`, `raw_read`, NANDX erase/write, A/B metadata writers, or an image-upload routine. Those storage functions belong to internal boot/image loading and A/B maintenance paths.

## 2. Separate BootROM/Preloader download dispatcher

`download.c:usbdl_handler()` is a different command loop from `bldr_cmd_handler()`. It provides the familiar low-level commands (`READ16/32`, `WRITE16/32`, `SEND_DA`, `JUMP_DA`, target configuration, etc.). It is the DAA-protected path already tested; entering META does not transition into this dispatcher.

Consequently, internal storage helpers cannot be reached merely by appending another command after `ATEMATEX`. At that point the USB handshake service is being torn down for boot handoff.

## 3. Preloader-as-DA RAM-image service

The SDK source contains an optional service:

| Command | Function | Behavior |
|---:|---|---|
| `0x70` | `usbdl_send_image()` | receive a whitelisted `lk`, `logo`, `boot`, or `atf` image into its configured RAM buffer |
| `0x71` | `usbdl_boot_image()` | jump only to uploaded `lk` or `atf` |

This is exactly the architecture desired for a RAM recovery environment, but both definitions and dispatcher cases are under `#if CFG_PRELOADER_AS_DA`.

The exact working-router Preloader lacks all distinctive strings from these functions, including `SEND: name = %s`, `SEND: len = 0x%x`, `SEND: Verify PASS`, `PL Checksum`, `XFLASH checksum`, `Jump to LK`, `Jump to ATF`, and `Unknown Jump`. The evidence therefore classifies `CMD_SEND_IMAGE/CMD_BOOT_IMAGE` as **compiled out / not exposed** in this X17M build.

## 4. LK RAM-boot surface

The exact LK contains ordinary NAND boot-image and ramdisk loading code, plus the AEE/MRDUMP fastboot framework. Its exposed fastboot command set does not include `download:`, `boot`, `flash:`, or `erase:`. `set_active:` is present only as a not-supported stub. LK therefore has internal RAM-loading capability but no identified host command that supplies a temporary kernel/initramfs.

The `FASTBOOT` Preloader selector may still enter the minimal LK/AEE endpoint, but that endpoint currently offers diagnostics/query/reboot behavior, not image upload or slot repair.

## 5. A/B implications

META parameters do not override the selected suffix. The A/B selector reads redundant metadata at `misc + 0x800`; no volatile META, key, RTC, watchdog, or command-line suffix override was found. A legitimate slot change still requires either:

- the normal Preloader rollback state machine to select the opposite slot; or
- a write to boot-control metadata through an authorized storage-capable environment.

The latter remains unavailable through the proven META selector and minimal LK fastboot surface.

## FACTS

- Failed routers reach the complete Preloader META selector transaction through `ATEMATEX`.
- The selector consumes only fixed META records and `DISCONNECT`, then returns to boot.
- Storage routines are not reachable from the selector command table.
- The SDK's `0x70/0x71` RAM-image commands are conditional.
- Exact X17M Preloader lacks their unique code strings.
- Exact LK lacks a fastboot download/boot/flash handler.

## INFERENCES

- Sending undocumented data after `ATEMATEX` will not expose a hidden Preloader META service; it will either be consumed as `DISCONNECT` input or ignored during teardown/handoff.
- The most promising selector-side experiment is `FASTBOOT`, but its known downstream endpoint is diagnostic and does not currently solve recovery.
- A signed factory kernel/initramfs cannot presently be injected through any proven Preloader/LK host command.

## UNRESOLVED

- Whether the exact X17M has a separate OEM-only command registered outside the source-correlated selector and download dispatchers; none has been found in the exact binary.
- Whether a reset-reason/boot-control condition can cause LK to use an existing alternate boot/rootfs combination without writing metadata.
- Whether an OEM production auth artifact can unlock the existing DAA download path.

## Recovery consequence

Preloader META remains valuable because it proves execution and sets boot mode, but it is not itself a storage repair channel. The remaining non-physical recovery candidates are narrowed to: automatic/controlled A/B rollback using existing signed NAND images; an OEM-authenticated DA; or an as-yet-unidentified signed OEM recovery mode. UART evidence will determine which existing image fails, but it does not create the repair primitive.

