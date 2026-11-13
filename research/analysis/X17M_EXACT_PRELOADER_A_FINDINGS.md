# X17M exact working-unit-A Preloader findings

Date: 2026-09-18

## Scope and conclusion

This is a static, read-only analysis of the complete eMMC boot-region dump
from a working A-slot ZLT X17M. No router was contacted and no protocol
command, DA, memory access, storage access, reset, or image modification was
performed.

The files are direct evidence of a 2025-03-27 X17M Preloader, not merely a
generic MT6890 sample. They contain a MediaTek boot container and an ARM32
Preloader image with the same build timestamp as `loader_ext_a`.

The image definitely contains Preloader-side USB/META/download code and
internal eMMC/partition code. It does **not** by itself establish a host
command that reads arbitrary eMMC without a Download Agent. The only
host-facing DA path identifiable from static evidence is the usual
`usbdl_send_da`/`usbdl_jump_da` path, whose security policy and the previously
observed X17M BootROM DAA boundary remain relevant.

The selector vocabulary is strongly consistent with the upstream MediaTek
Preloader META implementation. Exact branch conditions, lengths, timeout
values, and destinations cannot be claimed from flat file offsets alone:
the MMM payload is a multi-stage relocated ARM image, not an ELF, and the
first-stage loader must be rebased before reliable function-level xrefs can be
made.

## Classification

- **CONFIRMED**: directly present in this exact image or proved by its
  container metadata.
- **PLAUSIBLE**: supported by this image plus the upstream implementation,
  but not executed on this unit.
- **BLOCKED**: prevented by an observed security boundary or contradicted as
  an unrestricted recovery path.
- **UNKNOWN**: not determined by the available static evidence.

## 1. Provenance and identity

The two supplied files are byte-for-byte identical:

| file | size | SHA-256 |
|---|---:|---|
| `zlt x17m dumps/mmcblk0boot0.bin` | 4,194,304 | `68a999377a7631125f3408bec6da15221f0882f58f4c337424d8ffdae20ed66b` |
| `zlt x17m dumps/mmcblk0boot1.bin` | 4,194,304 | `68a999377a7631125f3408bec6da15221f0882f58f4c337424d8ffdae20ed66b` |

`cmp` returned exit status 0. This establishes that this unit does not have
different binaries in the two eMMC boot hardware regions.

The image contains:

```
Build Time: 20250327-080226
preloader_evb6890v1_64_cpe_emmc.bin
platform/mt6890/src/...
```

The build timestamp exactly matches the recovered `loader_ext_a` timestamp.
The running unit was reported as `bootslot=a`, `root=/dev/mmcblk0p28`.
This is therefore labelled **working-unit A / 20250327**, not a universal
X17M Preloader. It is not the separate bootloop specimen whose preserved log
reported a 2025-12-03 Preloader.

## 2. Complete eMMC boot-region layout

The file is a complete MediaTek boot-region container, not a flat executable.
Important offsets in `mmcblk0boot0.bin` are:

| offset | observation | status |
|---:|---|---|
| `0x000` | `EMMC_BOOT` | **CONFIRMED** |
| `0x200` | `BRLYT` | **CONFIRMED** |
| `0x208` | BRLYT fields point to `0x800` | **CONFIRMED** |
| `0x800` | `MMM` / `FILE_INFO` image container | **CONFIRMED** |
| `0x820` | little-endian image length `0x3bc38` | **CONFIRMED** |
| `0x800..0x3c437` | declared MMM payload | **CONFIRMED** |
| `0x3c438..0x3fffff` | erased/padding area (the last nonzero content is at `0x3c437`; the remainder is zero/FF padding) | **CONFIRMED** |
| `0xb8c` | `AND_ROMINFO_v`, `MT6752`, `CUST`, `AND_SECCTRL_v`, `AND_SECRO_v` metadata | **CONFIRMED** |
| `0x3b8db` | embedded filename and `MTK_BIN` metadata | **CONFIRMED** |

The payload SHA-256 for bytes `0x800..0x3c437` inclusive is
`f191862f7c9abb67ceabeafbc290f78b25942f5dfb2217d9aee085ff48621cd4`.
The `MT6752` text is a legacy/generic ROM-info marker inside the MediaTek
container; it is not evidence that this X17M is an MT6752 device.

The upstream `preloader_emu_mmc.py` parser independently confirms the same
layout rule: read the BRLYT start field, expect `MMM`, then read the image
length at MMM+`0x20`. This is why extracting from `0x800` is justified; the
original 4 MiB files remain untouched.

## 3. What the ARM image establishes

The MMM payload begins with ARM32 code rather than an ELF header. A first-stage
disassembly at file offset `0x960` shows relocation/initialisation logic and
literal load addresses including `0x201000`, `0x109000`, `0x11755c`,
`0x200000`, and `0x237efc`, followed by a branch/copy sequence. This confirms
that the payload contains a loader plus subsequent image regions and must be
rebased by load segment before code-to-string xrefs are meaningful.

Flat `r2` xrefs from the file offset to the selector strings produce no valid
references. That is a limitation of the current mapping, not evidence that the
strings are dead. A complete function-level reconstruction remains
**UNKNOWN** pending segment-aware rebasing and disassembly of the later
stages.

## 4. Selector surface present in this exact Preloader

The selector and response strings occur contiguously in the protocol area at
`0x30761..0x3082b`, with diagnostic text immediately following:

| request | response/next token present | static interpretation | status |
|---|---|---|---|
| `AT+NBOOT` | `AT+OK`, `AT+UNKONWN` | normal boot selector/ack or unknown response | **PLAUSIBLE** |
| `METAMETA` | `ATEM0001`, `ATEM0002`, `ATEMATEX` | META negotiation sequence | **PLAUSIBLE** |
| `FACTFACT` | `TCAFTCAF` | factory-menu acknowledgement | **PLAUSIBLE** |
| `ADVEMETA` | `ATEMEVDX` | advanced META acknowledgement | **PLAUSIBLE** |
| `FACTORYM` | `MYROTCAF` | ATE/factory acknowledgement | **PLAUSIBLE** |
| `FASTBOOT` | `TOOBTSAF` | Preloader fastboot-mode acknowledgement | **PLAUSIBLE** |
| any other token | `unknown received: '%s'` | rejected/diagnostic path | **CONFIRMED string; branch UNKNOWN** |
| `METAFORB` | `'%s' is forbidden` | forbidden META diagnostic | **CONFIRMED string; triggering condition UNKNOWN** |

The exact image also contains `READY` at `0x30020`, and logging/configuration
strings for `meta_com_id`, `meta_log_disable`, `META_COM TYPE/ID/PORT`, and
`seclib_brom_meta_mode`. The upstream implementation waits for a `READY`
packet on the Preloader CDC endpoint, sends one of the eight-byte selectors,
then expects the reverse acknowledgements listed above. It performs the
additional META handshake (`ATEM0001` and `ATEM0002` payloads, then
`ATEMATEX`) only after receiving a `METASLA` challenge in the authenticated
META path.

For precision, the upstream wire sizes are: `READY` 5 bytes; each primary
selector and reverse acknowledgement 8 bytes; `ATEM0001` followed by a
12-byte little-endian payload (`04 00 00 00 01 00 00 00 03 00 00 00`);
`ATEM0002` followed by a 16-byte payload
(`06 00 00 00 01 00 00 00 03 00 00 00 01 00 00 00`); and `ATEMATEX`
followed by disconnect. Those lengths are **CONFIRMED for the upstream
implementation** and **PLAUSIBLE, not yet function-level-confirmed**, for
this relocated X17M image. A `METASLA` response additionally invokes a
challenge/secret exchange in that implementation; no `METASLA` string was
found in this image's selector block, so whether that challenge is compiled
or reached here is **UNKNOWN**.

That upstream sequence is a **PLAUSIBLE model**, not proof that every branch
is enabled on this X17M. The exact comparison length, retry count, timeout,
and whether a selector is accepted over USB CDC, UART META, or both are
**UNKNOWN** until the relocated functions are disassembled or observed on
this exact unit.

A literal `METAMETA` therefore cannot be assumed to imply unrestricted META:
the image contains policy/logging checks, and the separate 2025-12 bootloop
experiment produced another `READY` rather than a META transition. That live
negative result is useful context but is not a test of this 2025-03-27 image.

## 5. Boot/mode conditions and security policy

The exact image contains the following ordering and policy evidence:

- `part_init`, `store_switch_to_dram`, and `rpmb` occur before the loader
  handshake strings.
- `before bldr_handshake`, `seclib_brom_meta_mode`, `USB handshake`,
  `BR META BOOT`, `BR FACTORY BOOT`, `BR ADVMETA BOOT`, and
  `BR ATE FACTORY BOOT` are present together.
- `img_auth_required=%x` appears in both loader/partition diagnostics.
- Security-policy strings expose `sboot_state`, `lock_state`, and a default
  policy fallback.
- `seclib_img_auth_load_sig`, `img auth fail`, `img auth ok`, and `pubk auth
  fail` are present.
- `usbdl_vfy_da:disabled`, `usbdl_send_da: clean invalid da`, and
  `usbdl_jump_da` are present in the download module.

These facts establish that Preloader has an image-authentication/policy layer
and mode-selection logic. They do **not** establish that `usbdl_vfy_da:disabled`
means all DA authentication is disabled: it may be a diagnostic/configuration
print for a particular path. The previously observed X17M BootROM (HW code
`0x0992`) rejected the available X28 DA during DAA before execution; that is a
BootROM boundary, distinct from any later Preloader image-authentication check.

The relationship between `seclib_brom_meta_mode`, the selector state machine,
and whether a secure-boot/lock state suppresses a mode is **UNKNOWN** from the
currently rebased evidence. It is not safe to infer that a selector bypasses
BootROM DAA merely because its string is present.

## 6. FASTBOOT, factory and META destinations

The exact image proves the presence of selector/ack vocabulary and boot-mode
logging, but not the final destination of each branch:

- `FASTBOOT` -> `TOOBTSAF` is **PLAUSIBLE** as Preloader mode selection.
  It is not evidence of conventional Android fastboot flashing. The separate
  LK AEE/MRDUMP fastboot endpoint is diagnostic-only and must not be conflated
  with this selector.
- `FACTFACT` -> `TCAFTCAF`, `FACTORYM` -> `MYROTCAF`, and `ADVEMETA` ->
  `ATEMEVDX` are **PLAUSIBLE** factory/META transitions. The strings
  `Loading LK/LK2`, `Loading Uboot/Uboot2`, and partition-not-found errors show
  that normal boot images are loaded around this code, but do not identify the
  destination branch.
- Whether any branch boots the X17M Linux factory/META environment, exposes
  PID `0x202d`, or instead falls back to ordinary LK is **UNKNOWN** for this
  binary.

## 7. Preloader USB/download dispatcher

The exact binary contains a real Preloader CDC path (`USB CDC ACM for
preloader`), USB enumeration/listen timeout diagnostics, and the DA functions
`usbdl_send_da` and `usbdl_jump_da`. It also contains internal eMMC services:

```
part_load fail: blkdev_read / blkdev_write
partition_read fail / partition_write fail
raw_read fail / raw_erase fail
read_config_emmc / write_config_emmc
mmc_switch_part, mmc_switch, msdc_cmd
MSDC erase/read-card/switch-part diagnostics
```

This classifies the **internal** capabilities as follows:

| capability | finding |
|---|---|
| identification/USB handshake | **CONFIRMED** |
| eMMC/MMC initialisation and partition reads | **CONFIRMED internally** |
| DA transfer/jump | **CONFIRMED by code and diagnostics** |
| image/signature authentication | **CONFIRMED by code and diagnostics** |
| host-facing raw eMMC readback before DA execution | **UNKNOWN; no handler proven** |
| host-facing partition readback before DA execution | **UNKNOWN; no handler proven** |
| arbitrary register/memory access | **UNKNOWN in this exact Preloader** |
| erase/write through an unauthenticated host command | **NOT IDENTIFIED / BLOCKED by scope** |
| reset/mode selection | **PLAUSIBLE** from selector and boot-mode code |

The presence of `blkdev_read`, `partition_read`, and `raw_read` strings is not
enough to call them externally controllable. They are used by Preloader's own
boot, DRAM-calibration, partition, and logging paths. No statically rebased
USB command handler has yet been shown to call one of those functions without
first entering a DA or an authenticated service. Therefore a Preloader-native
eMMC readback route is **not identified**.

## 8. Comparison with older supplied Preloaders

The older 2023-05 and 2025-02 MT6890-family samples contain the same selector
vocabulary (`READY`, `METAMETA`, `ATEM0001/2`, `ATEMATEX`, `FACTFACT`,
`ADVEMETA`, `FACTORYM`, `FASTBOOT`) and analogous `usbdl_send_da` strings.
Their selector offsets differ because the builds/layouts differ. This exact
2025-03-27 image therefore confirms continuity of the MediaTek implementation,
but does not prove byte-identical control flow or policy.

A code-level difference report between the 2025-03-27 image and those samples
requires segment-aware rebasing. Until that is done, claims that this build
accepts a selector rejected by an older sample are **UNKNOWN**.

## 9. Recovery boundary

For this exact working-unit-A artifact:

1. Preloader can initialise eMMC and use partition/raw-read functions
   internally: **CONFIRMED**.
2. Preloader exposes a USB CDC handshake and a DA loading/jump path:
   **CONFIRMED**.
3. A host-facing, arbitrary eMMC readback command that bypasses DA execution:
   **UNKNOWN / not identified**.
4. The available X17M DA route is constrained by the observed BootROM DAA
   rejection of the X28 DA: **BLOCKED**.
5. META/factory selectors may lead to a vendor diagnostic environment:
   **PLAUSIBLE**, but acceptance and storage scope on this exact build are
   untested.

Accordingly, the earliest stage with a **concrete, proven external eMMC
readback interface without first passing BootROM DAA remains none identified**.
The static evidence supports investigating the selector state machine and
the OEM-authenticated DA, but does not justify sending selectors or treating
internal Preloader storage calls as a host readback API.

## 10. Unresolved questions

- Segment/load-address map needed for complete ARM function recovery and xrefs.
- Exact selector input lengths, timeout/retry behaviour, and transport choice.
- Whether `seclib_brom_meta_mode` or secure/lock state gates each selector.
- Final destinations of FASTBOOT, FACTORYM, FACTFACT, and ADVEMETA.
- Whether this build emits `METASLA` and implements the authenticated META
  challenge sequence on USB CDC.
- Whether any Preloader USB command reaches `partition_read`/`raw_read`
  before DA execution.
- Code-level differences from the 2025-12 bootloop Preloader, which is a
  different build and was not supplied here.
