# X17M 1 GiB NAND Preloader and LK recovery surface

Date: 2026-09-21

## Scope

This is a static, read-only review of the actual 1 GiB NAND router backup captured on 2026-09-21. It replaces assumptions drawn from older eMMC X17M artifacts where the storage medium, partition layout, or build differs. No router command, flash operation, slot operation, reset, or image change was performed for this review.

| Image | SHA-256 | Finding |
|---|---|---|
| `logical/mtd00_preloader.img` | `5152173ee3f604dcd65edaa199812703f97acd391cb7a0d9c27ab9a5568567f5` | Primary NAND Preloader region, 4 MiB |
| `logical/mtd01_preloader_backup.img` | `d74f5ea5ce12b4d8a4cd211a0e917deadd77ccf9bc363965f12b3d5581722fa5` | Backup Preloader region, 2 MiB |
| `logical/mtd25_lk_a.img` | `a757f40b3c7da58167c56cde10728768196f42e53a8c10c49e6de97fd9ef1b5e` | LK A, 2 MiB |
| `logical/mtd39_lk_b.img` | `a757f40b3c7da58167c56cde10728768196f42e53a8c10c49e6de97fd9ef1b5e` | LK B, 2 MiB |

The two LK slots are byte-identical. The Preloader payload is also the same in primary and backup copies: only four bytes in the BootROM header's physical-location fields differ, accounting for different partition locations.

## Exact NAND Preloader identity

Both Preloader partitions contain the same content through file offset `0x7ed4b`; the remaining partition space is padding. The primary/backup header locations are `0x00000000` and `0x00400000`. MediaTek boot structures occur at offsets `0x0`, `0x100`, and `0x1000`.

The exact payload reports:

```text
Build Time: 20250909-103520
preloader_evb6890v1_64_cpe.bin
platform/mt6890/src/...
```

This is a NAND Preloader even though its historical filename lacks a `_nand` suffix.

## Confirmed Preloader services

The live NAND Preloader contains these strings:

```text
USB CDC ACM for preloader
READY
METAMETA / ATEM0001 / ATEM0002 / ATEMATEX
FACTFACT / ADVEMETA / FACTORYM / FASTBOOT / METAFORB
META_COM TYPE / ID / PORT / META LOG DISABLE / FAST META GPIO
usbdl_send_da / usbdl_jump_da / usbdl_vfy_da:disabled
blkdev_read / partition_read / raw_read
nand_write / blkdev_erase / blkdev_write
nandx init error / nand chip init fail / NAND BBT diagnostics
```

This confirms USB CDC selector handling, the normal Download Agent transfer/jump path, and internal NANDX partition/raw-read/erase/write/BBT services. Internal storage calls are not a host-facing raw NAND protocol. No static evidence has shown a Preloader USB command that dispatches to `raw_read`, `partition_read`, or `blkdev_read`. The conventional storage command loop begins only after a DA runs; the earlier BootROM DAA result remains a boundary.

## META is the leading recovery-vector candidate

The exact selector vocabulary matches the source-correlated MT6890 Preloader handler documented in `analysis/X17M_PRELOADER_SOURCE_CORRELATION.md`:

```text
TARGET -> HOST  READY
HOST   -> TARGET METAMETA                  (8 bytes)
HOST   -> TARGET v1 record                 (12 bytes)
TARGET -> HOST  ATEM0001
HOST   -> TARGET v1 record                 (12 bytes)
TARGET -> HOST  ATEM0002
HOST   -> TARGET v2 record                 (16 bytes)
TARGET -> HOST  ATEMATEX
HOST   -> TARGET DISCONNECT                (10 bytes)
TARGET             META boot mode
```

`METAMETA` is only the first selector. The handler then waits for an initial 12-byte record before it can return `ATEM0001`. Thus a historical `READY -> METAMETA -> READY` observation is consistent with a timeout and fresh listener; it does not establish selector rejection.

`METAFORB` is compiled in. Runtime policy is still unknown, so the safe UART capture must come first for the failed router. The known-good NAND router can validate the complete selector transaction only through a separately reviewed active experiment.

## FASTBOOT and LK result

The identical NAND LK A/B image contains the AEE/MRDUMP fastboot framework:

```text
getvar:
reboot / reboot-fastboot / continue
set_active:
oem mrdump
max-download-size / product / serialno / is-userspace
set active slot: not supported!
```

It does not contain `download:`, `flash:`, `erase:`, `upload:`, `fetch:`, `flashing unlock`, or `flashing lock`. Its `download_base` diagnostic is generic framework state, not a registered handler. It is a diagnostic AEE/MRDUMP endpoint, not a NAND recovery reader or writer.

LK also contains NAND-specific MRDUMP support, including `kedump: nand device`, NANDX/BBT diagnostics, and `mrdump_read_expdb`. Those are crash-dump internals, not arbitrary partition services. The useful next use is passive observation of an AEE endpoint, followed only by read-only fastboot `getvar` queries if it enumerates as `0e8d:201c`.

## Recovery-vector ranking

| Vector | Evidence | Status |
|---|---|---|
| Safe UART capture on failed router | Establishes actual boot progression without the old 3.3 V interference | Highest priority after the 1.8 V RX-only adapter arrives |
| Preloader META boot selector | Exact NAND Preloader has the full handler vocabulary and source-matched protocol | Strong candidate; live policy and failed-unit behavior unknown |
| BootROM/Preloader DA | Compiled transfer/jump support; earlier available DA rejected by DAA | Blocked for tested DA |
| LK AEE/MRDUMP fastboot | Query/MRDUMP support, no flash/read handlers | Secondary diagnostic route |
| Direct Preloader raw NAND read | Internal NANDX reads exist | Not identified as host-facing |

## Recommended next work

Keep the failed-device investigation passive until the 1.8 V adapter arrives: router GND to adapter GND and router TX to adapter RX only. Capture its full undisturbed boot and correlate USB identities without transmitting a USB protocol command. Use this September 2025 NAND Preloader as the reference to distinguish actual NANDX failure from slot, authentication, rootfs/overlay, modem, or userspace failure.

Reserve active META or fastboot characterization until after that passive capture. This analysis establishes neither a restore procedure, a Preloader-native NAND read command, a DAA bypass, nor a transferable firmware image.
