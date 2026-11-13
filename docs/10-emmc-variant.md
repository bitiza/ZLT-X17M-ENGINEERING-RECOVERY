# eMMC X17M variant

Revised 2026-11-13. Two eMMC references are now characterized: a **working
production sample** (storage identity and GPT below) and a **bootlooped 8 GB
unit** analyzed on 2026-09-26
([`research/analysis/ZLT_X17M_EMMC_UNBRICK_ANALYSIS_20260926.md`](../research/analysis/ZLT_X17M_EMMC_UNBRICK_ANALYSIS_20260926.md)),
cross-checked against the BusyBox failure reconstruction
([`research/analysis/X17M_8GB_BUSYBOX_FAILURE_CAUSAL_ANALYSIS.md`](../research/analysis/X17M_8GB_BUSYBOX_FAILURE_CAUSAL_ANALYSIS.md)).
Full rootfs images from the working sample are still pending transfer.

## FACTS

### Storage identity (working sample)

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
16 md1img_a       80 MiB       41 rootfs_b      512 MiB
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

### rootfs slot layout (8 GB unit)

The 8 GB unit's `rootfs_b` (p41) is a hybrid image:

```text
+0x00000000   SquashFS 4.0/xz read-only base (~59 MB of data, built 2026-03-23)
+0x03880000   ext4 overlay image (~477 MB), mounted as /upper
```

The pre-modification overlay contains configuration/state only — no
`/upper/bin`, `/upper/sbin`, `/upper/etc/preinit`, or `/upper/etc/init.d`
overrides — so the effective init binaries come from the SquashFS lower layer.

### Broken-unit root cause: BusyBox replacement

The 8 GB unit's bootloop root cause was identified by QEMU execution of both
binaries with libraries from the same baseline SquashFS:

| Property | Vendor baseline | Replacement (broken) |
|---|---|---|
| BusyBox | 1.36.0, musl dynamic, 595,744 B | 1.37.0 Debian static, 1,975,064 B |
| SHA-256 | `45859c93…` | `43db2f47…` |
| `lock` / `netmsg` applets | present | **absent** (`applet not found`, exit 127) |

OpenWrt's `/lib/preinit/30_failsafe_wait` calls `lock -w /tmp/.failsafe` in a
tight loop; without the applet the call fails immediately and loops forever.
The init chain stalls as:

```text
/sbin/init → forks preinit (PREINIT=1) → waits for /tmp/.preinit
preinit → stuck in lock loop → /tmp/.preinit never created
/sbin/init → procd never starts → meta_tst never runs → watchdog reboot (~30 s)
```

Additionally, the inittab getty line is commented out, so no UART login shell
would appear even after a clean boot.

### Delivery mechanisms measured on the 8 GB unit

| Mechanism | Status |
|---|---|
| BootROM DA | **BLOCKED** — DAA `0x7024` (ACC-bypass DA); `0x7017` root-caused as **trust-anchor mismatch**: the production eMMC Preloader and `rootfs_sig_a` cert carry `b5ed982c…`/`c4daa020…` keys while the SDK DA carries `9af8…`; `0x7009` is the auth-only (no paired DA) status |
| LK fastboot | **BLOCKED** — surface is `oem mrdump`, `set_active:` stub, limited `getvar:`; no `download:`/`flash:`/`erase:` in this 1 MiB ARM32 LK |
| USB META | **BLOCKED** — `usb.init` creates `mass_storage.usb0` without a backing file so the `0x202d` UDC bind fails silently; and `meta_tst` never starts because procd never starts |
| UART META trigger | **TRIGGER WORKS** — `METAMETA`→`ATEM0001` accepted during the ~50 ms Preloader window, boot mode reaches Linux, but preinit still fails at `lock`; the mode does not bypass preinit |
| UART shell | **BLOCKED** — preinit has no stdin attached to the console; LK UART is output-only in this build |
| UART firstboot injection | **BLOCKED** — `firstboot` cannot execute without a working BusyBox; if it could run, `jffs2reset -y` (which calls `overlay_delete()` on the ext4 overlay) would restore the factory SquashFS BusyBox and fix the unit |

### A/B boot control (both samples)

Header inspection identifies LK containers (`lk`), TEE/ATF containers (`atf`),
Android boot images (`mt6890`), rootfs signature containers (`cert1`), SquashFS
rootfs images (`hsqs`), and loader extension containers (`loader_ext_dram`).

Working-sample A/B SHA-256 pairs:

| Pair | SHA-256 A | SHA-256 B | Result |
|---|---|---|---|
| boot | `c1815e7a…` | same | identical |
| rootfs_sig | `e393a0da…` | same | identical |
| rootfs | `1bd78f94…` | `0c66578f…` | different |
| LK | `f3d4b3f8…` | same | identical |
| TEE/ATF | `cec2a806…` | same | identical |
| loader_ext | `4baba1fe…` | same | identical |

The differing complete rootfs hashes prove the two 512 MiB partitions are not
byte-identical, although their observed SquashFS headers match.

`misc` (working sample) SHA-256
`dbc5f8ce28f3c193210f6fda0280448bf3142efbe9a5f3c5e084823d3ede2ffc`;
at `misc + 0x800` the `\0AB0` record reads:

```text
A: priority 15, retry 2, successful_boot 1, up_type 0
B: priority  0, retry 0, successful_boot 0, up_type 0
```

On the 8 GB bootlooped unit the same record had **slot B at higher priority**
(`root=/dev/mmcblk0p41 bootslot=b`), which is why LK kept selecting the broken
slot. The A/B magic layout is shared with NAND; `reduce_retry_count()` is
compiled out of this LK — **no automatic rollback after failed boots**. If the
`\0AB0` magic is invalid, LK falls back to slot A, but writing `misc` requires
DA authorization — a circular dependency.

## INFERENCES

- This sample is architecturally very close to the previously characterized large-storage X17M at the GPT level.
- The same logical A/B record layout appears on the observed NAND and eMMC units, but physical persistence/write procedures are storage-specific.
- Identical A/B bootloader hashes do not imply B is selectable when its boot-control priority is zero — and on the 8 GB unit the inverse held: B's higher priority kept a broken image selected with no automatic retry-count rollback.
- The eMMC recovery decisive fix is small: either restore the vendor BusyBox (or any BusyBox with `lock`/`netmsg`) into the effective init path, or point the boot record at the intact slot — both currently require a write path that software does not provide.

## UNRESOLVED

- Structural reason for the complete `rootfs_a` versus `rootfs_b` hash difference on the working sample.
- Exact Preloader content/version in this sample's eMMC hardware boot areas.
- Whether other eMMC production revisions use the same bootloader hashes.
- Whether additional eMMC boot-control copies exist outside the observed `misc + 0x800` record.
- Full comparison with the older raw eMMC backup.
- Whether the eMMC trust-anchor keys (`b5ed982c…`/`c4daa020…`) match the NAND unit's anchor — the two storage variants were analyzed at different times with different tooling; do not assume one shared key.

## Recovery paths (8 GB unit, ranked)

1. **OEM DA** — request an eMMC-specific signed DA / restore tool from ZLT/Quectel; the required public keys are in the `rootfs_sig_a` cert chain.
2. **Physical eMMC access** — BGA153/169 socket programmer; deterministic and unauthenticated: write a fixed `misc` record (slot A priority = 15) or a repaired `rootfs_b` overlay.
3. **1.8 V UART** — observe the ~50 ms Preloader window; `METAMETA` reaches Linux META mode but does not bypass preinit on a BusyBox-broken rootfs.
4. **Misc-write exploit** (speculative) — invalidating the A/B magic would make LK fall back to slot A; no tool path is currently identified.

## Safety

Do not transplant `nvcfg`, `nvdata`, `nvram`, `protect1`, `protect2`, `proinfo`, `productinfo`, `fibonv`, `seccfg`, or other identity/calibration/security state between physical routers. Do not apply raw-NAND erase/write procedures to eMMC merely because partition names correspond. Do not `dd` over `nvdata`/`boot_para` (`firstboot` would) without understanding that it is a destructive reset of persistent state.
