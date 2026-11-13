# Raw-NAND X17M variant

Revised 2026-11-13. Working-unit storage characterization is mature, and the
bricked 1 GiB unit has now been live-audited end to end
([`research/analysis/X17M_RECOVERY_AUDIT_20261020.md`](../research/analysis/X17M_RECOVERY_AUDIT_20261020.md)),
including live-tested Preloader selectors and a root-caused host-instrumentation
story. Full rootfs image comparison is still pending transfer into the offline
evidence set.

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

- `md1dsp`, `spmfw`, `pi_img`, `dpm`, `medmcu`, `sspm`, `mcupm`, `lk`, `tee`, `boot`, `rootfs_sig`, `loader_ext`

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
md1img_a: b5d098fa165f5bb00337e8a597cab32267d3a084af41d0b72ec25365faf7fcde
md1img_b: 52a9b87b820d85ce925a5ee7582ba5a8f2a6e64680be8983ebefb8565abfc184
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

### Live audit of the bricked unit (2026-10-20)

The failed 1 GiB NAND unit (slot B non-booting, slot A intact) was live-audited
without any flash write:

- **The UART console is live and interactive.** With a proper 1.8 V FTDI at
  921600 8N1, the OpenWrt failsafe prompt is reached; sending `f\n` is accepted
  and answered with `- failsafe -`. No shell follows because
  `lib/preinit/99_10_failsafe_login` requires `-c /dev/console` and the running
  rootfs has **no `/dev` directory at all** (preinit fails with
  `can't open '/dev/null'`). The `1|2|3|4` debug keys work, proving the preinit
  read loop consumes keystrokes.
- **The Preloader selector channel works end to end.** Full `READY` → selector →
  ACK transactions were completed live, with device-side UART confirmation. The
  measured matrix on this unit:

| Selector | ACK | Preloader `BOOT_MODE` | LK `lk boot mode` | Outcome |
|---|---|---:|---:|---|
| `METAMETA` | `ATEMATEX` | 1 | **1** | Linux boots in META mode; `0x202d` gadget blocked by the broken rootfs |
| `FASTBOOT` | `TOOBTSAF` | 99 | 0 | `aee_lk` staged into DRAM; LK boots Linux |
| `ADVEMETA` | `ATEMEVDX` | 5 | 0 | META params changed; LK boots Linux |
| `FACTFACT` | `TCAFTCAF` | 4 | 0 | No factory endpoint or write service observed |

- **The LK acts only on `META_BOOT`.** Three non-META modes (4, 5, 99) are
  accepted and recorded by the Preloader and ignored by the LK (`lk boot mode = 0`
  in every case; `METAMETA` alone yields `lk boot mode = 1`). Even with
  `lk boot mode = 1`, no META gadget appears because the userspace that would
  configure it cannot run on a rootfs without `/dev`.
- **The LK fastboot app starts on every boot** (`wait_for_enter_fastboot` in the
  live log) and its endpoint never enumerates — consistent with the static
  analysis in [docs/08](08-lk-meta-fastboot.md).
- **Preloader tool window measured: 1895–3563 ms** after power-on, depending on
  boot timing.
- **DA candidates exhausted:** stock, ACC-bypass, unsigned, and the community
  X25-package DA are all rejected at the DAA gate; Preloader-as-DA
  (`0x70`/`0x71`) is compiled out; Preloader SRAM read/write is crypto-gated;
  BROM Kamakiri is unavailable (`mt0992` in upstream `missing_brom.txt`).

### Instrumentation findings (root-caused)

Three measurement artifacts were identified that previously looked like device
behavior:

1. **Shared host USB controller.** The FTDI UART adapter and the router were on
   the same physical host controller, so a router power cycle also dropped the
   FTDI's link; a plain `cat /dev/ttyUSB0` descriptor died on re-enumeration and
   captured zero bytes for exactly the window that mattered. Use separate
   controllers where possible and reconnect-aware capture.
2. **Warm reset vs full power-off.** The PMIC reset flag discriminates:
   `UVLO_RSTB` (clean undervoltage reset from a full power-off) → the Preloader
   serves USB normally; `DDLO_RSTB` (brown-out latch from a warm reset or
   too-short power cycle) → the USB stack never settles and the host sees
   nothing. Unplug the power adapter long enough for the rail to fully discharge
   and confirm `UVLO_RSTB` in the boot log before expecting host attachment.
   Holding the power key during power-up separately skips USB enumeration
   (`Enumeration(Skip): powerkey pressed`).
3. **1.8 V logic domain.** An unsuitable (3.3 V-domain) UART adapter reproduced
   the same apparent NAND-initialization failure on a known-good router that
   boots normally: Preloader read a bogus/perturbed NAND identity and failed
   NANDX initialization, after which A/B and secure-boot errors cascaded
   because no boot device existed. UART-captured NAND-init failure from that
   setup is an instrumentation artifact and cannot be evidence of NAND failure.

Safe UART testing begins receive-only:

```text
router GND -> adapter GND
router TX  -> 1.8 V-compatible adapter RX
router RX  disconnected
adapter VCC disconnected
```

### Restore image prepared

`build_v19/images/rootfs_bozax17_v19_xray_busybox.img` — SHA-256
`95be8ec18a3dabad5e53e8467dc08ecbe4ead74d6e793dde17d7ec571d61130b`,
48,685,056 bytes (inside the 55,836,672-byte usable slot size), containing a
real `/dev/console` character device (5,1), and user-confirmed to boot. The
missing piece for this unit is a trusted flash-write path, not an image.

## INFERENCES

- The raw-NAND and eMMC products share much of the logical A/B firmware architecture while using materially different physical storage and filesystem stacks.
- The exact 10 MiB common prefix in `md1img_a/b`, followed by structured differences and later erased padding, is more consistent with intentional image/container differences than random NAND damage. The internal format still needs offline parsing.
- A/B population and A/B selectability are separate questions: the observed factory-like state has populated B partitions while B priority is zero.
- The failed unit's blocker is precisely "no `/dev` in the running rootfs" — not a dead console, not a dead kernel, and not broken failsafe. Any delivered rootfs with `/dev` present converts the proven-interactive UART failsafe prompt into a usable shell.

## UNRESOLVED

- Exact internal structure responsible for the `md1img` divergence at `0x00A00000`.
- Exact payload-level difference between current `rootfs_a` and `rootfs_b`.
- Reconciliation of the current 8.25 MiB `rootfs_data` report with the earlier apparent larger extent/overlap.
- Whether a DA signed with the device's own trust-anchor modulus can be obtained from a working same-family unit (the highest-value remaining action).
- Whether `FACTORYM` (the one untested selector) behaves like `FACTFACT` — expected, but untested.
- Whether the failed units can autonomously transition to another valid A/B state without a trusted storage write.

## Safety

Do not use ordinary block-device read failures as definitive NAND-integrity tests. Do not erase, refresh, unlock, or write MTD while collecting evidence. Preserve per-device `nvcfg`, `nvdata`, `nvram`, `protect*`, `proinfo`, `productinfo`, `fibonv`, `seccfg`, calibration, identity, and security state. Confirm the PMIC reset flag (`UVLO_RSTB`) before interpreting any failed USB attachment, and never diagnose NAND failure from a capture taken with a 3.3 V-domain UART adapter attached.
