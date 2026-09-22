# eMMC X17M variant

Status: partial characterization. Large rootfs images have not yet been transferred into the evidence set.

## FACTS

### Storage identity

- Device: `mmcblk0`
- User area: 15,269,888 sectors × 512 bytes = 7,818,182,656 bytes
- Logical/physical sector size: 512 bytes
- Hardware boot0: 8,192 sectors = 4 MiB
- Hardware boot1: 8,192 sectors = 4 MiB
- boot0/boot1 were exposed read-only with `force_ro=1`
- eMMC name: `33BGAX`, type `MMC`, manufacturer ID `0x00000b`, OEM ID `0x0d00`, date `10/2025`
- Running root: `/dev/mmcblk0p28`, `bootslot=a`

Vendor boot-done output:

```text
FLASH_TYPE=emmc
bootctrl=00414230000000000f02010000000000
is_ab_partition=1
current_slot=_a
```

### GPT layout

The live kernel exposes 50 named GPT partitions. Geometry matches the previously observed large-storage X17M map:

```text
 1 misc          512 KiB       26 boot_a        32 MiB
 2 para          512 KiB       27 rootfs_sig_a  512 KiB
 3 expdb          20 MiB       28 rootfs_a      512 MiB
 4 nvcfg          32 MiB       29 md1img_b       80 MiB
 5 nvdata         32 MiB       30 md1dsp_b       10 MiB
 6 protect1        8 MiB       31 spmfw_b         1 MiB
 7 protect2        8 MiB       32 pi_img_b        1 MiB
 8 mcf1_a          8 MiB       33 dpm_b           1 MiB
 9 mcf2_a          8 MiB       34 medmcu_b        1 MiB
10 mcf1_b          8 MiB       35 sspm_b          1 MiB
11 mcf2_b          8 MiB       36 mcupm_b         1 MiB
12 seccfg        512 KiB       37 lk_b            1 MiB
13 boot_para       2 MiB       38 tee_b           1 MiB
14 proinfo         3 MiB       39 boot_b          32 MiB
15 nvram          32 MiB       40 rootfs_sig_b  512 KiB
16 md1img_a       80 MiB       41 rootfs_b       512 MiB
17 md1dsp_a       10 MiB       42 loader_ext_a   256 KiB
18 spmfw_a         1 MiB       43 loader_ext_b   256 KiB
19 pi_img_a        1 MiB       44 logo             8 MiB
20 dpm_a           1 MiB       45 fibo_para        2 MiB
21 medmcu_a        1 MiB       46 fibonv          32 MiB
22 sspm_a          1 MiB       47 user_config     20 MiB
23 mcupm_a         1 MiB       48 productinfo      4 MiB
24 lk_a            1 MiB       49 user_data    5,918 MiB
25 tee_a           1 MiB       50 flashinfo       16 MiB
```

Critical starts: `rootfs_a` sector 616512; `rootfs_b` sector 1932352.

### Filesystem organization

`/dev/root` is read-only SquashFS at `/rom`. `/dev/loop0` is ext4 at `/overlay`, with overlayfs providing `/`. Persistent nvcfg, nvdata, protect1/2, active mcf1/mcf2, user_config, productinfo, user_data and fibonv are mounted as ext4. This differs materially from the raw-NAND unit's MTD/JFFS2/UBI handling.

### A/B headers and hashes

Header inspection identifies LK containers (`lk`), TEE/ATF containers (`atf`), Android boot images (`mt6890`), rootfs signature containers (`cert1`), SquashFS rootfs images (`hsqs`), and loader extension containers (`loader_ext_dram`).

| Pair | SHA-256 A | SHA-256 B | Result |
|---|---|---|---|
| boot | `c1815e7a90776088c79831c5a94c724dd339cd86c79d55179af60de683e03c7f` | same | identical |
| rootfs_sig | `e393a0daed018f9cc1dc85e8461e07fbda091edeb20bf1edfc7d317187c75890` | same | identical |
| rootfs | `1bd78f94e63ed5eeaf980f80fb5323680c01e39be4cd7549f2833c09a0e8e9df` | `0c66578f825ab6687f472ee642e204ad7d69ce6a7ba1598028e4e76543ac3f60` | different |
| LK | `f3d4b3f83c463c6483de0fc1a904abc67017edb74b8f5c9d7f0af4b2bf0ae9a7` | same | identical |
| TEE/ATF | `cec2a8064c61e0bd8c14e02dbed5e9015a23130a3add2f2aefb24758980b2aa4` | same | identical |
| loader_ext | `4baba1fe20434ba67c07c18b847aa2c8dc34a969cc9a7b0b1f19e77d083fd3ed` | same | identical |

The differing complete rootfs hashes prove the two 512 MiB partitions are not byte-identical, although their observed SquashFS headers match. Full images are pending backup/transfer.

### Boot control

`misc` SHA-256:

```text
dbc5f8ce28f3c193210f6fda0280448bf3142efbe9a5f3c5e084823d3ede2ffc
```

At `misc + 0x800`:

```text
00 41 42 30 00 00 00 00 0f 02 01 00 00 00 00 00
```

Parsed state:

```text
A: priority 15, retry 2, successful_boot 1, up_type 0
B: priority  0, retry 0, successful_boot 0, up_type 0
```

This agrees with the vendor runtime `current_slot=_a` report. B is not currently a valid boot candidate despite the presence of B firmware partitions.

## INFERENCES

- This sample is architecturally very close to the previously characterized large-storage X17M at the GPT level.
- The same logical A/B record layout appears on the observed NAND and eMMC units, but physical persistence/write procedures are storage-specific.
- Identical A/B bootloader hashes do not imply B is selectable when its boot-control priority is zero.

## UNRESOLVED

- Structural reason for the complete `rootfs_a` versus `rootfs_b` hash difference.
- Exact Preloader content/version in this sample's eMMC hardware boot areas.
- Whether other eMMC production revisions use the same bootloader hashes.
- Whether additional eMMC boot-control copies exist outside the observed `misc + 0x800` record.
- Full comparison with the older raw eMMC backup.

## Safety

Do not transplant `nvcfg`, `nvdata`, `nvram`, `protect1`, `protect2`, `proinfo`, `productinfo`, `fibonv`, `seccfg`, or other identity/calibration/security state between physical routers. Do not apply raw-NAND erase/write procedures to eMMC merely because partition names correspond.
