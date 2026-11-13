# Other ZLT MTK firmware archives: findings

Date: 2026-09-21  
Scope: read-only inspection of `/home/kali/Desktop/x17m/Other_zlt_mtk_firmwares`. No
router, image, or archive was modified.

## Contents

The directory contains three RAR5 firmware bundles:

| Archive | Firmware root | Notes |
|---|---|---|
| `1.5.13-openssh.rar` | `1.5.13/` | RG500L/MT6890 NAND package |
| `8.5.4.3-openssh.rar` | `8.5.4.3/` | Same platform package |
| `8.5.5.1-openssh.rar` | `Pro-8.5.5.1/` | Same platform, later Pro build |

Each contains `boot.img`, `lk.img`, `ubi-rootfs.ubi`, a NAND Preloader,
`MT6890_openwrt_scatter.xml`, and a Download Agent directory.

## Cross-version identity

The following files are identical across all three archives:

| Component | SHA-256 |
|---|---|
| `preloader_evb6890v1_64_cpe_nand.bin` | `e2ae79dd585c0ac7e19324fe8182e2d4a374452c1c9f5ed446e1b9e0ba4fae06` |
| `DA_BR.bin` | `c3d9058aeb56373eaadc5868ce93198fb99a9cbf876a30f876714e9007d66d56` |
| `DA_BR_unsign.bin` | `9133e91fd2dd4e5871a84d1709f2cac33a973025ca69f14f007a4a9f1223cfc1` |
| `MT6890_openwrt_scatter.xml` | `a70d6afe1f756fcf12dfe2a08ba483b3a9ece6f788fdb363f0606f4ca92b6530` |
| `download_agent/flash.xml` | `a5cb22d2cae6e0bd43bdbf3ebfd53c40aeb7967cd524950f66c5dc209b7887ce` |

The 1.5.13 and 8.5.4.3 bundles also share identical `lk.img` and `boot.img`:

* LK: `051f661144df7f12ff8721198f8ebd356953bae8dd1764283c29979011483c50`
* boot: `9c539434d37fa591bf0a093d8b65d724a6cef95c6ddb5aec08ea43c2c9e67358`

The 8.5.5.1 Pro bundle has different LK, boot, and UBI rootfs payloads. All
three rootfs UBI images differ.

## Relationship to the exact X17M backup

The exact working-router Preloader is a 4 MiB logical MTD image with build
string `20250909-103520`. The archive Preloader is only 237,612 bytes and has
build string `20230628-041024`; its SHA-256 is different, and its first bytes
do not match the exact dumped Preloader. Therefore the archive Preloader must
not be flashed to an X17M merely because the project and partition map match.

The archive Preloader is still useful as a comparison specimen. It contains
the same source path and A/B strings (`platform/common/bootctrl/2.0/ab_bootcheck.c`)
seen in the exact image, but the exact 2025 image additionally contains the
`[AB] restore the misc partition` string and newer security/bootloader code.

## Partition map confirmation

The archive scatter confirms the layout already recovered from the working
router:

* NAND erase block: `0x40000`
* `preloader`: base `0x000000`, size `0x400000`
* `preloader_backup`: base `0x400000`, size `0x200000`
* `proinfo`: base `0x600000`, size `0x100000`
* `misc`: base `0x700000`, size `0x100000`
* `para`: base `0x800000`, size `0x100000`

The archive scatter’s partition geometry therefore independently supports the
offsets documented in `X17M_1GB_PRELOADER_AB_STATE_MACHINE.md`.

## Download Agent and security implications

The stock archive DA is the same across all three bundles. Its strings expose
host-facing XML commands including `READ-PARTITION`, `READ-FLASH`,
`ERASE-PARTITION`, `WRITE-PARTITION`, and `READ-PARTITION-TABLE`, plus NAND/BMT
support. This confirms that a DA, once accepted and loaded, has the low-level
storage operations needed for partition recovery.

However, this does **not** show that the stock DA will load on the failed
routers. The current investigation already encountered DAA/security rejection.
The archive DA is a stock 2023 DA; it is not evidence of a bypass for the
newer 2025 Preloader/security policy.

There is a separate local artifact,
`/home/kali/Desktop/x17m/zlt-dump/lib/da/DA_BR_acc_bypass_nand.bin`, with
SHA-256 `b207028741fd66c458ea4d86a06b06c9c6679b82cf24e607ad4eb3b24af9264e`.
Its strings explicitly mention `NAND-BMT`, ACC/HACC handling, and partition
read/write/erase commands. The repository README describes it as a patched
ACC-bypass DA for MT6890 NAND dumping. It is not byte-identical to the archive
DA (different size and binary layout), so it should be treated as a separate,
already-patched tool artifact—not as an archive firmware component.

The bypass DA is potentially more relevant to the DA route than these RARs,
but loading it on a failed unit remains an external, live operation and was
not attempted during this inspection.

## Recovery value

Useful:

1. Independent confirmation of the X17M/MT6890 NAND partition geometry.
2. Older Preloader/LK specimens for static comparison of boot modes, A/B code,
   and DA protocol strings.
3. Stock DA protocol strings showing that partition-level read/write/erase are
   implemented below the Android/Linux META layer.
4. Version-specific rootfs/boot/LK payloads for identifying which firmware
   generation a recovered device may contain.

Not established:

* The old Preloader is safe or compatible to flash onto the 2025 X17M.
* The stock DA bypasses DAA on either failed router.
* Any archive rootfs is the correct unit-specific image; identity/NVRAM data is
  not supplied by these generic firmware bundles.
* A DA write operation should be attempted before a device-specific full backup
  and target-image verification.

## Reproducibility

The inspection used `unrar`/`sha256sum`, `strings`, and read-only XML/text
inspection. Temporary extraction directories were under `/tmp`; the source
archives and router backups were not changed.
