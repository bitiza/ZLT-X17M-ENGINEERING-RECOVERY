# Raw-NAND X17M variant

Status: working-unit storage characterization is mature. Full rootfs image comparison is pending transfer into the offline evidence set.

## FACTS

### Platform and storage identity

The characterized raw-NAND unit reports:

- OpenWrt 21.02.7
- target `gem6xxx/evb6890v1_64_cpe`
- Linux 5.4.238, September 9 2025 build
- MediaTek MT6890 platform
- active root `/dev/mtdblock29`, `bootslot=a`
- NAND `NM4888KSPAXAI`
- NAND ID `76 26 91 a3 98`
- physical capacity 1 GiB
- page size 4 KiB
- eraseblock size 256 KiB
- OOB size 64 bytes/page
- ECC strength reported as 12
- six factory bad blocks and no observed worn bad blocks on the reference unit

The live kernel exposes 52 MTD partitions. This layout is not interchangeable with the 50-partition eMMC GPT layout.

### MTD layout

```text
 0 preloader          4 MiB       26 tee_a             1 MiB
 1 preloader_backup   2 MiB       27 boot_a           32 MiB
 2 proinfo            1 MiB       28 rootfs_sig_a      1 MiB
 3 misc               1 MiB       29 rootfs_a         64 MiB
 4 para               1 MiB       30 rootfs_data    0x00840000
 5 expdb             20 MiB       31 md1img_b         80 MiB
 6 nvcfg             32 MiB       32 md1dsp_b         10 MiB
 7 nvdata            32 MiB       33 spmfw_b           1 MiB
 8 protect1           8 MiB       34 pi_img_b          1 MiB
 9 protect2           8 MiB       35 dpm_b             1 MiB
10 mcf1_a             8 MiB       36 medmcu_b          1 MiB
11 mcf2_a             8 MiB       37 sspm_b            2 MiB
12 mcf1_b             8 MiB       38 mcupm_b           2 MiB
13 mcf2_b             8 MiB       39 lk_b              2 MiB
14 seccfg             1 MiB       40 tee_b             1 MiB
15 boot_para          2 MiB       41 boot_b            32 MiB
16 nvram             32 MiB       42 rootfs_sig_b      1 MiB
17 md1img_a          80 MiB       43 rootfs_b          64 MiB
18 md1dsp_a          10 MiB       44 loader_ext_a       1 MiB
19 spmfw_a            1 MiB       45 loader_ext_b       1 MiB
20 pi_img_a           1 MiB       46 fibo_para          4 MiB
21 dpm_a              1 MiB       47 user_config       20 MiB
22 medmcu_a           1 MiB       48 productinfo        4 MiB
23 sspm_a             2 MiB       49 fibonv            32 MiB
24 mcupm_a            2 MiB       50 user_data      0x18480000
25 lk_a               2 MiB       51 pmt              512 KiB
```

The current live unit reports `rootfs_data` as `0x00840000` bytes (8.25 MiB). Earlier evidence from another acquisition described a different apparent rootfs-data extent. Until PMT start-address evidence is reconciled, do not generalize the exact overlap/extent across all NAND units.

### Filesystem organization

The active root is SquashFS and the writable overlay is JFFS2. Persistent configuration uses a mixture of YAFFS2/JFFS2, while `user_data` is UBI/UBIFS. This differs materially from the eMMC unit's ext4/loop-overlay organization.

### NAND-aware acquisition

For raw NAND, `nanddump --bb=padbad --omitoob` is the canonical logical acquisition method used in this investigation.

Direct reads through `/dev/mtdblockN` can fail on partitions containing bad blocks even when NAND-aware acquisition succeeds with zero uncorrectable ECC errors. Therefore an `mtdblock` I/O error is not, by itself, evidence that a firmware partition is corrupt.

A current `rootfs_a` acquisition completed the full 64 MiB range with:

```text
ECC failed: 0
ECC corrected: 1136
Number of bad blocks: 0
Number of bbt blocks: 0
```

Corrected ECC events are not equivalent to uncorrectable data loss.

### A/B boot-chain comparison

On the September reference unit, NAND-aware/readable comparisons show the following A/B pairs identical:

- `md1dsp`
- `spmfw`
- `pi_img`
- `dpm`
- `medmcu`
- `sspm`
- `mcupm`
- `lk`
- `tee`
- `boot`
- `rootfs_sig`
- `loader_ext`

The complete `rootfs_a` and `rootfs_b` images differ. Structural comparison is pending transfer of the current images.

#### md1img

The two 80 MiB modem images are not byte-identical.

The first 10 MiB are exactly identical:

```text
SHA-256(first 10 MiB):
944b4e178ff11d52584bead178779d7d94c6920d89ba9fed3f0403fd6bddaef8
```

The first differing byte is at zero-based offset `0x00A00000` (10 MiB). Both images contain substantial programmed data after this point; a small erased region in B immediately at the boundary must not be mistaken for the end of B's image.

At 1 MiB resolution:

- A contains programmed data through the 60-61 MiB region and is all `0xff` from 61 MiB through 80 MiB.
- B contains programmed data through part of the 61-62 MiB region and is all `0xff` from 62 MiB through 80 MiB.

Whole-image SHA-256:

```text
md1img_a:
b5d098fa165f5bb00337e8a597cab32267d3a084af41d0b72ec25365faf7fcde

md1img_b:
52a9b87b820d85ce925a5ee7582ba5a8f2a6e64680be8983ebefb8565abfc184
```

The observed structure is not evidence, by itself, that B is damaged. Offline parsing of the modem-image container is still required.

### Boot control

The NAND `misc` record at `+0x800` uses the same logical `\0AB0` structure observed on eMMC.

Observed state:

```text
A: priority 15, retry 2, successful_boot 1, up_type 0
B: priority  0, retry 0, successful_boot 0, up_type 0
```

The NAND copy uses erased `0xff` bytes in reserved fields where an observed eMMC record used zeroes. B firmware being present does not make B selectable when its priority is zero.

### UART electrical finding

The NAND X17M UART pads were measured around 1.8 V logic levels. An older UART adapter reproduced the same apparent NAND initialization failure on a known-good router that otherwise boots normally.

With the unsuitable adapter attached, Preloader read a bogus/perturbed NAND identity and failed NANDX initialization, after which A/B and secure-boot errors cascaded because no boot device existed.

Therefore UART-captured NAND initialization failure from that setup is an instrumentation artifact and cannot be used as evidence of NAND failure.

Safe future UART testing should begin receive-only:

```text
router GND -> adapter GND
router TX  -> 1.8 V-compatible adapter RX
router RX  disconnected
adapter VCC disconnected
```

Do not connect a 3.3 V TX signal directly to the router RX pad.

## INFERENCES

- The raw-NAND and eMMC products share much of the logical A/B firmware architecture while using materially different physical storage and filesystem stacks.
- The exact 10 MiB common prefix in `md1img_a/b`, followed by structured differences and later erased padding, is more consistent with intentional image/container differences than random NAND damage. The internal format still needs offline parsing.
- A/B population and A/B selectability are separate questions: the observed factory-like state has populated B partitions while B priority is zero.

## UNRESOLVED

- Exact internal structure responsible for the `md1img` divergence at `0x00A00000`.
- Exact payload-level difference between current `rootfs_a` and `rootfs_b`.
- Reconciliation of the current 8.25 MiB `rootfs_data` report with the earlier apparent larger extent/overlap.
- Trustworthy boot-stage diagnosis of the failed NAND units using a proper 1.8 V UART interface.
- Whether the failed units can autonomously transition to another valid A/B state without a trusted storage write.

## Safety

Do not use ordinary block-device read failures as definitive NAND-integrity tests. Do not erase, refresh, unlock, or write MTD while collecting evidence. Preserve per-device `nvcfg`, `nvdata`, `nvram`, `protect*`, `proinfo`, `productinfo`, `fibonv`, `seccfg`, calibration, identity, and security state.
