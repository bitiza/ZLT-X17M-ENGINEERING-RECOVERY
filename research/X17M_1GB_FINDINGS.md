# ZLT X17M 1 GB Model — Findings

This note records the current findings about the small-storage X17M, the known-good 1 GB reference router, and what remains unknown about the suspect unit.

## Hardware and storage

The 1 GB and approximately 8 GB X17M variants use different storage architectures. The 1 GB model has 1 GiB raw NAND with MediaTek NANDX, MTD, and PMT. The larger model uses eMMC, MMC block devices, and GPT. The 1 GB model has SquashFS on MTD and a separate JFFS2 `rootfs_data` overlay; do not transfer images between variants based only on matching partition names. Both have A/B firmware slots.

The working 1 GB router reports NAND model `NM4888KSPAXAI`, ID `76 26 91 a3 98`, capacity `0x40000000` (1 GiB), eraseblock `0x40000` (256 KiB), page `0x1000` (4096 bytes), sector `0x200` (512 bytes), OOB `0x40` (64 bytes/page), and ECC level `0x0c` (12). Linux driver: `mtk-nand`; device-tree compatible: `mediatek,mt6880-nfc`.

The known-good unit reports six factory bad blocks (1536, 1537, 1672, 1674, 3584, 3585) and zero worn bad blocks. NAND reads showed corrected ECC bitflips but no uncorrectable ECC errors, and repeated logical dumps had stable hashes.

## Recovered MTD map

All 52 partitions:

| MTD | Name | Size | MTD | Name | Size |
|---:|---|---:|---:|---|---:|
| 0 | `preloader` | 4 MiB | 26 | `tee_a` | 1 MiB |
| 1 | `preloader_backup` | 2 MiB | 27 | `boot_a` | 32 MiB |
| 2 | `proinfo` | 1 MiB | 28 | `rootfs_sig_a` | 1 MiB |
| 3 | `misc` | 1 MiB | 29 | `rootfs_a` | 64 MiB |
| 4 | `para` | 1 MiB | 30 | `rootfs_data` | 18 MiB |
| 5 | `expdb` | 20 MiB | 31 | `md1img_b` | 80 MiB |
| 6 | `nvcfg` | 32 MiB | 32 | `md1dsp_b` | 10 MiB |
| 7 | `nvdata` | 32 MiB | 33 | `spmfw_b` | 1 MiB |
| 8 | `protect1` | 8 MiB | 34 | `pi_img_b` | 1 MiB |
| 9 | `protect2` | 8 MiB | 35 | `dpm_b` | 1 MiB |
| 10 | `mcf1_a` | 8 MiB | 36 | `medmcu_b` | 1 MiB |
| 11 | `mcf2_a` | 8 MiB | 37 | `sspm_b` | 2 MiB |
| 12 | `mcf1_b` | 8 MiB | 38 | `mcupm_b` | 2 MiB |
| 13 | `mcf2_b` | 8 MiB | 39 | `lk_b` | 2 MiB |
| 14 | `seccfg` | 1 MiB | 40 | `tee_b` | 1 MiB |
| 15 | `boot_para` | 2 MiB | 41 | `boot_b` | 32 MiB |
| 16 | `nvram` | 32 MiB | 42 | `rootfs_sig_b` | 1 MiB |
| 17 | `md1img_a` | 80 MiB | 43 | `rootfs_b` | 64 MiB |
| 18 | `md1dsp_a` | 10 MiB | 44 | `loader_ext_a` | 1 MiB |
| 19 | `spmfw_a` | 1 MiB | 45 | `loader_ext_b` | 1 MiB |
| 20 | `pi_img_a` | 1 MiB | 46 | `fibo_para` | 4 MiB |
| 21 | `dpm_a` | 1 MiB | 47 | `user_config` | 20 MiB |
| 22 | `medmcu_a` | 1 MiB | 48 | `productinfo` | 4 MiB |
| 23 | `sspm_a` | 2 MiB | 49 | `fibonv` | 32 MiB |
| 24 | `mcupm_a` | 2 MiB | 50 | `user_data` | 388.5 MiB |
| 25 | `lk_a` | 2 MiB | 51 | `pmt` | 512 KiB |

`pmt` is MediaTek PMT metadata, not GPT.

## Filesystems and firmware slots

The running system reports:

```text
/dev/root       /rom       squashfs   ro
/dev/mtdblock30 /overlay   jffs2      rw
overlayfs       /          overlay
```

Thus `mtd29/rootfs_a` is read-only SquashFS and `mtd30/rootfs_data` is the writable JFFS2 overlay. `user_data` is UBI-managed and mounted at `/data`, with about 347 MiB usable. YAFFS2 is used for `nvcfg`, `nvdata`, `nvram`, `protect1`, `protect2`, `user_config`, `productinfo`, and `fibonv`; JFFS2 for `mcf1_a/b`, `mcf2_a/b`, and `rootfs_data`; UBI/UBIFS for `user_data`.

The duplicated A/B chain includes `md1img`, `md1dsp`, `spmfw`, `pi_img`, `dpm`, `medmcu`, `sspm`, `mcupm`, `lk`, `tee`, `boot`, `rootfs_sig`, `rootfs`, and `loader_ext`. The reference reports `bootslot=a` and `root=/dev/mtdblock29`; another unit could legitimately be running B.

The reference runs Linux 5.4.238, aarch64, OpenWrt 21.02.7 (`r16847-f8282da11e`), target `gem6xxx/evb6890v1_64_cpe`. Kernel build timestamp: Tue Sep 9 08:22:52 2025.

## Factory and modified rootfs recovery

Inactive B (`mtd43/rootfs_b`) is 67,108,864 bytes, SHA-256 `77d13d3cc0e172d23c10b18ae717db03b766bff29c813b249e5ac7e1b0f706f1`. Its XZ SquashFS was created Sep 9 2025, is 58,382,709 bytes with 6,556 inodes, and is byte-for-byte identical to the historical original `rootfs_a.img` SquashFS. It is a known-good factory reference.

Active A (`mtd29/rootfs_a`) is 67,108,864 bytes, SHA-256 `446815265d9f391c89feceab47d4d0d416404502c80587b860414aed0784cd`. `cmp -n 48050176 rootfs_a_mod.img nand_reference/rootfs_a.img` returned `rc=0`, proving the active image begins with the known modified image built in August 2026.

The modification kept factory `/bin/busybox` (595,744 bytes; SHA-256 `37791178b0508bad0b66e470ba7a6454d3467f92bb9e08ec80332958df2b9c65`) and added `/bin/busybox_full` (1,975,064 bytes; SHA-256 `43db2f47d9ea4e6ccf02a261a0ab00afb4490eed2d89730e089eacd65dea2273`). It also added a patched dialer (factory 583,800 bytes, hash prefix `2f68afca45975c32`; patched 588,568 bytes, prefix `888aab780312ebb...`) and patched `/tzwww/cgi-bin/http.cgi` (factory prefix `02e528a3f8ad...`; patched prefix `b8bb0248cb460...`).

The image restored more OpenWrt components, including opkg, uclient-fetch, wget/SSL support, CA certificates, LuCI package management/themes, GNU awk/grep components, and Lua dependencies. LuCI/uhttpd configuration and startup were changed. Valgrind and other nonessential debugging/audio material were removed to make room. Comparison: original 5,813 files; modified 6,029; 266 added, 50 removed, 9 changed.

The historical `rootfs_a.img` also contains JFFS2 history after the factory SquashFS. At offset `0x038C0000`, bytes `85 19` mark JFFS2 nodes; extracting that region identifies as little-endian JFFS2. Strings include `cron.update`, `root.new`, `.network.uci-...`, `/data/busybox`, and `overlay.opaque`. Current factory B has erased (`FF`) bytes at that offset. Preserve this historical data.

## Validated NAND dump method

`nanddump --bb=padbad --omitoob` against `/dev/mtd29` produced a 64 MiB logical image. Comparing it to `/dev/mtdblock29` returned `rc=0`, validating this method as equivalent to the ECC-corrected logical data exposed by mtdblock on this router. Corrected bitflips occurred in A/B dumps; no uncorrectable ECC errors were seen, and logical data was stable.

## UART incident and unresolved suspect router

The suspect unit initially appeared to fail NAND initialization over UART (`device scan fail`, ONFI/Jedec detection failures, `nand chip init fail`, `nandx init error (-14)`), followed by boot-device, A/B-slot, security, and watchdog errors.

Connecting the exact same UART adapter and wiring to the known-good router reproduced essentially the same NAND failure. With UART disconnected, it boots normally. The strange NAND ID `98 D3 91 26 76 16 08 00` was also reproduced on the known-good router. This means the old UART log is not evidence of NAND failure in the suspect unit; later errors are cascading after Preloader loses the boot device.

With the problematic adapter disconnected, the router pads measured TX about 1.75 V and RX about 1.58 V, strongly suggesting a 1.8 V logic interface. A 3.3 V adapter TX could overdrive the router RX domain or cause clamp/back-powering/loading. This fits the observations but remains a hypothesis. The old adapter is retired.

First replacement-adapter test: 1.8 V receive-only, with router GND to adapter GND and router TX to adapter RX. Leave router RX to adapter TX disconnected, and leave both VCC pins disconnected.

Still unknown until that safe boot capture: whether the suspect NAND initializes normally, its NAND model/ID, whether it reaches Linux, its selected slot, whether A/B firmware is intact, whether the issue is rootfs/overlay or boot-control related, or whether failure occurs later in networking/userspace.

## Recovery safety

Treat `proinfo`, `nvcfg`, `nvdata`, `protect1`, `protect2`, `nvram`, `seccfg`, `fibonv`, `productinfo`, and `user_config` as device-specific. They may contain calibration, modem state, IMEI/identity, MAC addresses, security configuration, or other per-device data. Recover them from the failed physical unit wherever possible; do not transplant them from the reference router.

## Current position

We have a working physical reference, factory rootfs reference, known-working modified rootfs, exact partition map, NAND geometry, PMT/Preloader dumps, and a validated dump procedure. The suspect router's actual fault is undiagnosed because the old UART setup itself disrupted NAND initialization on the known-good router. The next useful observation is a boot capture with a 1.8 V receive-only UART connection.

## Correction from live backup acquisition (2026-09-21)

Sysfs offsets show that `mtd30/rootfs_data` is an overlapping MTD view of the final 18 MiB of `mtd29/rootfs_a`, rather than a disjoint physical partition. `rootfs_a` spans `[0x13600000, 0x17600000)`; `rootfs_data` spans `[0x16400000, 0x17600000)`. The separate JFFS2 mount remains correct, but the earlier description of its physical arrangement was incomplete. All exposed MTD ranges together cover the first 1023 MiB of the 1 GiB NAND; the last 1 MiB is not exposed by those partitions.

## Broader NAND read result (2026-09-21)

The all-partition acquisition found uncorrectable ECC reports in `mtd5/expdb`, at relative offsets `[0x01200000, 0x013c0000)`: 448 pages (1.75 MiB), reported in both ECC-enabled passes. One page differed between the returned data from the two passes. Earlier rootfs-only tests with no uncorrectable errors therefore did not establish that every partition reads cleanly. Both expdb captures and an additional no-ECC/OOB capture of the affected range were preserved. `nanddump` returned zero despite these reports; transfer hashes do not prove source readability. No hardware-wear diagnosis is established by this observation.
