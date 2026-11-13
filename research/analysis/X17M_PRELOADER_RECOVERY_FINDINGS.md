# X17M Preloader / loader_ext recovery findings

Date: 2026-09-17

## Scope and answer

This investigation combined static analysis with a read-only passive USB
observation. No target command, DA transfer, memory access, storage access,
slot operation, or reset was performed.

The narrow answer is:

> **No Preloader-native external eMMC readback interface has been identified on
> the X17M. For the conventional MediaTek flashing protocol on hardware code
> `0x0992`, storage read/write commands live in an executed XFLASH Download
> Agent, and the X17M's BootROM DAA currently blocks the available X28 DA. The
> earliest stage with concrete X17M-specific evidence of host-facing storage
> operations that do not themselves require a BootROM DA is Linux META mode.**

That Linux META result has an important qualification: the X17M rootfs and LK
implementation are **CONFIRMED** statically, and the exact Preloader has now
been observed emitting its `READY` preamble. Acceptance of the subsequent
`METAMETA` selector remains **BLOCKED for the tested selector path**; the
single controlled attempt produced no acknowledgement or META transition. It is a
factory/diagnostic service with NVRAM,
`proinfo`, and file operations, not evidence of unrestricted raw eMMC
readback.

`loader_ext` is not a DA. It is a signed, Preloader-loaded DRAM extension with
no identified USB stack, command dispatcher, storage driver, partition API,
or recovery/download mode.

## Classification vocabulary

- **CONFIRMED**: directly observed on X17M, or unambiguously present in an
  X17M artifact.
- **PLAUSIBLE**: supported by a coherent X17M evidence chain plus upstream
  implementation, but not exercised on this target.
- **BLOCKED**: a relevant route is prevented by an observed security boundary,
  is contradicted as a recovery candidate, or falls outside the authorized
  non-destructive scope.
- **UNKNOWN**: the available artifacts do not establish whether the target
  implements or accepts it.

## 1. Evidence inventory

### Actual X17M Preloader evidence

The real `preloader_a`/`preloader_b` executables are **not present**. They live
in eMMC boot0/boot1, while `ZLT_X17M_FULL_BACKUP.img` and the individual
partition images cover only the eMMC user area.

The following nevertheless constitute direct evidence about the executing
X17M Preloader:

| Evidence | What it establishes | Status |
|---|---|---|
| `CoolTerm Capture 2026-06-07 16-42-57.txt` | Preloader USB tool enumeration, listen timeout, and normal continuation | **CONFIRMED** |
| `zlt x17m dumps/2.expdb.img` | Preserved complete Preloader logs, eMMC initialization, secure policy, active `loader_ext_b`, and USB handshake ordering | **CONFIRMED** |
| Passive USB captures | BootROM `0e8d:0003` followed by MT65xx Preloader `0e8d:2000`, both CDC ACM | **CONFIRMED** |
| Prior minimal BootROM query | HW code `0x0992`; target config `0x000000e5` (SBC, DAA, memory-read auth, memory-write auth, and blocked `0xC8`) | **CONFIRMED** |
| Prior authentication-only DA attempt | Transfer/checksum completed; X28 DA rejected with `0x7017` before any jump | **CONFIRMED / BLOCKED** |

The preserved log in `2.expdb.img` is especially valuable. In boot order it
records:

1. `[SD0] Initialized, eMMC45` and `[PLFM] Init Boot Device: OK(0)`.
2. Reading and validating `seccfg`; secure lock state is set.
3. Selecting `loader_ext_b`, requiring image authentication, verifying its
   certificate and image, and loading `loader_ext_b_dram`.
4. Matching Preloader and loader_ext build time `20251203-025510`.
5. DRAM work and `store_switch_to_dram`.
6. `#T#before bldr_handshake=1`, `#T#seclib_brom_meta_mode=0`, and
   `[BLDR] Tool connection is unlocked`.
7. The USB tool listen/handshake window.
8. Secure image verification and normal boot continuation.

This proves that eMMC is initialized and used internally before the external
Preloader tool window. It does **not** prove that any host command exposed in
that window can read eMMC.

`[BLDR] Tool connection is unlocked` is evidence that the tool handshake is
not globally disabled. It is not evidence that DAA, image authentication, or
storage authorization is bypassed.

### X17M user-area firmware evidence

| Artifact | Relevant contents | Evidentiary role |
|---|---|---|
| `41.loader_ext_a.img`, `42.loader_ext_b.img` | Signed `loader_ext_dram` payloads | Direct loader_ext evidence, not actual Preloader |
| `23.lk_a.img`, `36.lk_b.img` | META boot-argument propagation; AEE/MRDUMP diagnostic fastboot | Later-stage evidence |
| `25.boot_a.img`, `38.boot_b.img` | Kernel/DT strings including `mode-meta` and `mode-download` | Mode definitions only; no entry mechanism established |
| `rootfs/usr/bin/meta_tst` | MTK factory META protocol service | Direct Linux-stage implementation evidence |
| `rootfs/etc/init.d/usb.init` | META-mode USB gadget configuration, PID `0x202d`, ACM ports | Direct Linux-stage transport evidence |
| `rootfs/etc/init.d/meta_tst` | Starts `meta_tst` as a service | Direct Linux-stage service wiring |
| `rootfs/lib/upgrade/platform.sh` | Linux eMMC update path, including boot0 handling | Linux-only update evidence, not a Preloader protocol |
| `zlt-dump/` | X25/X28 tool using an executed ACC-bypass DA | Comparison only; not a no-DA route |

### Upstream/reference inference

The pinned source examined is `analysis/tools/mtkclient_upstream` at commit
`cd25cf9c1ff6d36e82697ac2c798e69e9cfb78c3` (2026-09-12). Its command enum is
a cross-generation superset, so an enum entry is not proof that the X17M
Preloader implements it.

The X28 scatter and DA under `zlt-dump/` are also inference only. Their
geometry is not the X17M geometry, and the DA route necessarily executes a DA.
The exact bundled X28 eMMC DA was already rejected at the X17M's DAA gate.

## 2. The `0e8d:2000` Preloader protocol surface

Upstream `mtk_preloader.py` groups the following command families in one
BootROM/Preloader client (`Library/mtk_preloader.py:52-121`). Their normal
roles are:

| Family | Representative operations | Meaning | X17M conclusion |
|---|---|---|---|
| Identification/capability | `GET_BL_VER`, `GET_VERSION`, `GET_HW_CODE`, `GET_HW_SW_VER`, `GET_TARGET_CONFIG`, `GET_PL_CAP`, MEID, SOCID, logs | Identify stage/SoC/security/capability; no storage | **PLAUSIBLE** at Preloader; BootROM subset already **CONFIRMED** |
| Register/memory | `READ16/32`, `WRITE16/32`, register access, PWR/I2C | SoC address-space or peripheral access; not a block-storage protocol | **BLOCKED** by stated scope; target config also reports memory read/write authentication |
| DA loading | `SEND_DA`, `JUMP_DA`, `JUMP_DA64`, environment preparation | Transfer and execute a DA | **BLOCKED** by DAA; X28 DA returned `0x7017` |
| Control transfer | `JUMP_BL` | Continue/jump to bootloader | **BLOCKED** by scope; no storage readback |
| Conditional Preloader-as-DA | `SEND_PARTITION_DATA` (`0x70`), `JUMP_TO_PARTITION` (`0x71`) | Host-to-target data feed and jump, only under `CFG_PRELOADER_AS_DA` | **UNKNOWN** on X17M; no read command and no evidence the flag is enabled |
| META/factory selector | ASCII `READY` followed by `METAMETA`, `ADVEMETA`, `FACTFACT`, `FACTORYM`, `FASTBOOT`, or `AT+NBOOT` | Select a subsequent boot/factory mode | **PLAUSIBLE** generically; this X17M's tested `METAMETA` path was not accepted |

### Identification only

Identification commands reveal stage, chip, security flags, capabilities, or
identifiers. They do not expose a sector/LBA, eMMC region, GPT, PMT, or
partition read operation. They are candidates for a future strictly bounded
Preloader probe, but none was sent during this investigation.

### Register and memory access

The `READ16/32` and `WRITE16/32` methods operate on a caller-supplied SoC
address (`mtk_preloader.py:388-448`). `brom_register_access` similarly moves
bytes to/from an address (`mtk_preloader.py:884-921`). These are not eMMC
readback commands. Attempting to synthesize controller operations with them
would be arbitrary target memory/register access and is explicitly excluded.

The observed target configuration has both memory-read-auth and
memory-write-auth bits set. Even absent the scope restriction, those bits are
evidence that this is not an open recovery route.

### DA loading and where storage commands begin

For HW code `0x0992`, upstream maps the chip to `DAmodes.XFLASH`
(`config/brom_config.py:506-520`). In the XFLASH flow:

1. Stage 1 is obtained from the selected DA container.
2. The host calls Preloader `send_da`.
3. The host calls `jump_da`.
4. Only after DA synchronization and hardware setup does the XFLASH command
   loop become available (`DA/xflash/xflash_lib.py:952-1000`).
5. The actual eMMC/NAND/UFS read command is implemented by XFLASH
   `cmd_read_data`/`readflash` (`xflash_lib.py:690-735`).

The generic `DAloader.readflash`, `writeflash`, and `formatflash` calls are
delegations to that selected DA implementation
(`DA/mtk_daloader.py:315-334`), not Preloader primitives.

The XML/v6 path has the same boundary: `send_da` and `jump_da` occur at
`DA/xmlflash/xml_lib.py:271-321`; `CMD:READ-FLASH` is issued later by the
running DA (`xml_lib.py:918-941`).

Therefore, for the conventional MediaTek readback/download workflow on this
generation, **storage access requires an executing DA**. The source contains
no corresponding Preloader `READ_PARTITION` or `READ_FLASH` command.

### Conditional `CFG_PRELOADER_AS_DA`

Upstream explicitly labels commands `0x70` and `0x71` as conditional on
`CFG_PRELOADER_AS_DA` (`mtk_preloader.py:53-55`). The host implementation
sends a named partition plus data for `0x70`, then can jump to a named
partition for `0x71` (`mtk_preloader.py:501-530`). It has no receive/readback
operation.

No X17M artifact contains `CFG_PRELOADER_AS_DA`, `SEND_PARTITION_DATA`, or a
target-specific handler. Because the real Preloader binaries are missing,
support is **UNKNOWN**. Even if present, these methods do not establish raw
storage reading; they look like a host-to-target boot/data route.

### META/factory mode selection

Upstream's separate META handshake watches PID `0x2000`, waits for `READY`,
and sends a mode token (`Library/meta.py:12-64`). It selects a later mode; it
does not implement eMMC reads or writes.

The X17M-specific evidence chain is unusually strong but incomplete:

- Preloader logs contain `seclib_brom_meta_mode`, a tool handshake, and an
  unlocked tool connection.
- Preloader/LK boot data contains `META_COM TYPE`, `META_COM ID`, and
  `FAST META GPIO`.
- LK contains `app/gem_boot/meta.c`, `atag,meta`, and code passing META
  communication fields into the kernel DT.
- The rootfs explicitly recognizes boot mode `0001` as META mode.
- In that mode `usb.init` exposes MediaTek USB PID `0x202d`, mass-storage plus
  three ACM functions, while normal networking is suppressed.
- `meta_tst` opens `/dev/ttyGS0` and implements the MTK META framing/service.

The first half of that gap is now closed by a passive live capture. On
2026-09-17 at approximately 10:39 local Kali time, udev identified the ACM
device as `ID_VENDOR_ID=0e8d`, `ID_MODEL_ID=2000`; kernel logs identified the
same device as `MediaTek MT65xx Preloader`. The read-only capture received
repeated ASCII `READY` bytes (`52 45 41 44 59`). No host payload was written:
in particular, no `METAMETA`, selector, DA, memory, or storage command was
sent. The earlier `0e8d:0003` capture was kept separate and is not used as
Preloader evidence.

A separately authorized, single-shot live selector test was then performed.
The host waited for the same `0e8d:2000` identity and a `READY` sequence,
sent exactly the eight ASCII bytes `METAMETA`, and performed no other write.
The only post-selector response was another `READY`; there was no `METASLA`,
META acknowledgement, `0x202d` gadget, or other META-mode USB identity before
the Preloader disconnected. The router continued its normal BootROM/Preloader
loop. This is a negative live result for this attempt, not proof that every
possible vendor handshake is impossible.

Consequently:

- X17M Linux META implementation: **CONFIRMED**.
- X17M Preloader `READY` preamble: **CONFIRMED**.
- Preloader acceptance of `METAMETA` and transition into Linux META:
  **BLOCKED for the tested selector path**; no acknowledgement or META-mode
  transition followed the exact documented token.
- Any authentication or authorization applied to that entry path: **UNKNOWN**.
- Preloader-stage raw eMMC access through META: **not identified**.

The DT values `mode-meta`/`mode-download` do not by themselves identify the
software that consumes an arbitrary numeric write. They are not a basis for
trying unvalidated reboot-mode values.

## 3. OEM recovery and factory mechanisms

### Linux META service

`rootfs/usr/bin/meta_tst` is an AArch64 MediaTek META service, started by
`rootfs/etc/init.d/meta_tst`. It checks
`/proc/device-tree/chosen/atag,boot`, distinguishes normal and META mode, and
uses `/dev/ttyGS0` for its USB transport.

Static strings and imports establish the following modules:

- NVRAM backup, restore, reset, read, and write;
- general file list/send/receive operations;
- AP database and modem diagnostic operations;
- product-info query/set using
  `/dev/block/platform/bootdevice/by-name/proinfo` (with `/dev/mtd/proinfo`
  and `/dev/block/proinfo` fallbacks);
- modem CCCI and AT diagnostic control;
- target log collection, clock, reboot, and power-off operations.

This is concrete externally controlled access to named eMMC-backed data once
Linux META is running. It is **not** evidence that the host may request an
arbitrary raw LBA or safely recover every partition. Some modules are
state-changing and remain out of scope.

The META-mode USB config also links a mass-storage function. No backing file or
block device assignment was found in the rootfs scripts, so usable host mass
storage is **UNKNOWN** and must not be treated as a recovery path.

### Linux upgrade path

`rootfs/lib/upgrade/platform.sh` knows how to update Preloader, loader_ext,
LK, TEE, boot, rootfs, and other partitions. On eMMC it accesses boot0 and
user-area block devices directly. This confirms that a running privileged
Linux system can service the storage, but it is a local upgrade mechanism,
not a Preloader protocol and not useful when Linux/root access is unavailable.

### zlt-dump and bundled MediaTek DA

`zlt-dump` invokes mtkclient with a bundled MT6890/T750 DA. The DA itself
contains the eMMC controller and `CMD:READ-FLASH`/`CMD:READ-PARTITION`
implementations. This supports, rather than weakens, the DA boundary.

The tool was designed for X25/X28 configurations that its documentation
describes as open or differently protected. Its eMMC scatter is not the X17M
partition geometry. On X17M, the DA transfer was already rejected with
`0x7017` before execution. It is **BLOCKED**, not an alternate Preloader-only
readback interface.

### Other searched mechanisms

No X17M user-area artifact established an OEM SP Flash Tool wrapper, SN Writer
server, emergency raw-storage service, Preloader readback command, or Tozed-
specific unauthenticated storage protocol.

`macwriter`, `configloader`, `tz_upgrade_client`, `upgraded`, factory-mode
scripts, and modem tooling are Linux services/utilities. Their presence does
not move the storage boundary earlier than Linux.

MRDUMP/AEE remains diagnostic. The prior LK analysis found a restricted AEE
fastboot endpoint, not conventional flash/readback fastboot. The proposed
read-only `mrdump_tool` queries remain useful when a root-accessible unit is
available, but they cannot be collected now and do not change the Preloader
conclusion.

## 4. loader_ext reverse analysis

### Container and slot relationship

| Property | `loader_ext_a` | `loader_ext_b` |
|---|---:|---:|
| GPT partition | 42 | 43 |
| User-area offset | `0x5af88000` | `0x5afc8000` |
| Partition size | 262,144 bytes | 262,144 bytes |
| SHA-256 | `077efd468d62156190949a3367fad47b047b463565c99bd6e50bb12cb0b64c6c` | `9fbf5d0b3e8dd7d5096b9e6ccd87daf346ad2f7a8ed3c1905180821da16ab312` |
| Embedded build time | `20250327-080226` | `20251203-025510` |

Both begin with MediaTek magic `0x58881688`, declared object size `0x8060`,
and name `loader_ext_dram`. A 0x200-byte header is followed by a `0x8060`-byte
payload at file offset `0x200`, ending at `0x8260`. Signed `cert1` and `cert2`
objects follow at `0x8260` and `0x8b10`; DER certificates begin at `0x8460`
and `0x8d10`.

The A/B headers are identical. Across the executable payload there are only
nine differing bytes, all within the ASCII build timestamp. Code is otherwise
identical; certificate/signature areas differ as expected.

The preserved Preloader log confirms that the active B-side Preloader chose
`loader_ext_b`, required authentication, verified both certificate and image,
and checked the exact matching build time. This is direct proof of its
relationship to Preloader.

### Code and entry information

The payload is ARM Thumb-2. Valid code begins at payload offset zero (file
offset `0x200`) with low-level register configuration and absolute MMIO
references. The image also makes PC-relative calls outside its own small
payload, consistent with a tightly coupled extension using routines supplied
by the parent Preloader.

The container does not expose an independently validated absolute runtime load
address in the examined header, and the Preloader log prints no address for
loader_ext. Therefore:

- payload start / probable implicit entry: file `0x200`, payload offset `0` —
  **PLAUSIBLE**;
- absolute runtime load address: **UNKNOWN**;
- a standalone boot-stage entry point: not established.

Treating a PC-relative branch target as an absolute address without the
missing link/load base would be unsound.

### Functionality

Operational strings are confined to DRAM/DDR setup: DRAM type, frequency
groups, AC timing, p2s ratio, MR8 density, DDR PHY frequency measurement,
reserve mode, DRAMC timeouts, LPDDR5 mode-register writes, and
`DramcFetchGlobalMR`. It also prints both the Preloader and loader_ext build
times.

No strings, imports, or recognizable tables were found for:

- USB or ACM transport;
- command parsing or host command handlers;
- eMMC, MSDC, UFS, generic storage, GPT/PMT, or partitions;
- flash/readback/backup/restore;
- META, factory, fastboot, or MRDUMP;
- host authentication, SLA, DAA, or authorization.

The security relationship is external: Preloader authenticates the signed
loader_ext container before invoking it. No loader_ext host-authentication
surface was identified.

**Conclusion:** loader_ext recovery/download is **BLOCKED as a candidate by
the static evidence**. It is a signed DRAM extension, not a DA and not an
independent externally controlled recovery stage.

## 5. Recovery boundary

### Interface classification

| Proposed interface | Classification | Storage consequence |
|---|---|---|
| BootROM identification/config query | **CONFIRMED** | Identification only; no eMMC readback |
| Preloader USB tool window at `0e8d:2000` | **CONFIRMED** | Transport/listen window exists; accepted target-specific commands remain partly unknown |
| Preloader identification/capability commands | **PLAUSIBLE** | No storage access |
| Preloader register/arbitrary-memory commands | **BLOCKED** | Not a storage API; auth bits set; excluded by scope |
| Preloader `SEND_DA`/`JUMP_DA` to XFLASH DA | **BLOCKED** | Required conventional storage route; DAA rejected X28 DA with `0x7017` |
| `CFG_PRELOADER_AS_DA` commands `0x70`/`0x71` | **UNKNOWN** | Conditional, no X17M evidence, host-to-target only, no readback command |
| Preloader `READY` preamble | **CONFIRMED** | Exact X17M `0e8d:2000` emitted repeated `READY` during a read-only capture |
| Preloader `METAMETA` mode selection | **BLOCKED for tested path** | Exact token elicited only another `READY`; no acknowledgement or META-mode USB identity |
| Linux `meta_tst` over USB ACM | **CONFIRMED** statically | Named NVRAM, `proinfo`, and file operations; unrestricted raw eMMC readback not established |
| META-mode USB mass storage | **UNKNOWN** | Function is linked, but no backing block device is configured in the artifacts |
| loader_ext | **BLOCKED** as recovery candidate | DRAM extension only; no external/storage command surface identified |
| LK AEE fastboot/MRDUMP | **CONFIRMED** diagnostic endpoint | No conventional flash/readback surface identified |
| Privileged normal Linux (`sysupgrade`, block devices) | **CONFIRMED** | Full local storage access, but requires a booted/root-accessible system |
| X28 `zlt-dump` DA | **BLOCKED** | Requires DA execution; rejected by X17M DAA; geometry also mismatches |
| Tozed-specific Preloader readback protocol | **UNKNOWN** | No evidence found |

## 6. Newly supplied Preloader images

The directory `/home/kali/Desktop/x17m/preloaders` contains four MTK images:

| File | Size | Embedded build time | Embedded image name / storage flavor |
|---|---:|---|---|
| `mtd0_preloader.bin` | 4 MiB | `20230525-123940` | `preloader_evb6890v1_64_cpe_nand.bin`, `MTK_BIN` count 5 |
| `preloader_evb6890v1_64_cpe_nand.bin` | 2 MiB | `20231217-172204` | NAND image, `MTK_BIN` count 6 |
| `preloader_backup` | 2 MiB | `20250214-012103` | `preloader_evb6890v1_64_cpe.bin` name in metadata, `MTK_BIN` count 6 |
| `preloader_evb6890v1_64_cpe.bin` | 242,972 bytes | `20231222-051658` | CPE/eMMC-oriented image, `MTK_BIN` count 5 |

All four identify the MT6890 platform and contain the same family of META
strings, USB download strings, and DRAM QVL material. They are **CONFIRMED as
MT6890/T750-family Preloader images**, but **not confirmed as the exact X17M
boot0/boot1 images**. The strongest disqualifier is the live X17M Preloader
record in `2.expdb.img`, whose active Preloader and `loader_ext` build time is
`20251203-025510`; none of these four images has that build time. Their older
timestamps indicate reference, backup, or earlier product-build artifacts.

### Selector parser recovered from the images

The selector block is present in all four images. The strings occur in this
order, with the corresponding response strings:

| Host selector | Parser response / follow-up | Interpretation |
|---|---|---|
| `AT+NBOOT` | `AT+OK` or `AT+UNKONWN` | AT-style normal-boot command; exact argument grammar is not recoverable from strings alone |
| `METAMETA` | `ATEM0001`, `ATEM0002`, `ATEMATEX` | META negotiation sequence; may require a follow-up framed exchange |
| `FACTFACT` | `TCAFTCAF` | Factory-menu selector/acknowledgement |
| `ADVEMETA` | `ATEMEVDX` | Advanced META selector/acknowledgement |
| `FACTORYM` | `MYROTCAF` | Factory/ATE selector/acknowledgement |
| `FASTBOOT` | `TOOBTSAF` | Fastboot selector/acknowledgement |
| `METAFORB` | `'%s' is forbidden!` diagnostic | Rejection marker, not a usable mode selector |

`READY` is the pre-selector idle preamble. These response names match the
upstream META implementation’s handling of `ATEM0001/2`, `ATEMATEX`,
`TCAFTCAF`, `ATEMEVDX`, `MYROTCAF`, and `TOOBTSAF`. This is strong evidence
that the images contain the standard MTK selector parser, but because they are
not proven to be the 2025 X17M build, it does not prove every selector is
enabled on the live router.

### Conditions and authentication

The images show several distinct gates:

- The parser is reached through the Preloader USB handshake; the images log
  `before bldr_handshake`, `USB handshake`, and `bldr_handshake`.
- META-related boot data includes `META_COM TYPE/ID/PORT`, `FAST META GPIO`,
  `seclib_brom_meta_mode`, and `UART META Connected`. The X17M expdb records
  `seclib_brom_meta_mode=0`, consistent with the live selector test not
  advancing after `METAMETA`.
- Download mode has separate conditions: `Force download mode`, key detection
  (`download keys are pressed`), and `emergency download mode(timeout:%ds)`.
  These are boot/policy paths, not evidence that an arbitrary USB selector can
  enter storage download.
- The Preloader contains `img_auth_required`, secure-policy `lock_state` and
  `sboot_state` handling, plus `img_auth fail/ok` and `pubk auth fail` paths.
  `usbdl_vfy_da:disabled` is a Preloader log/config string; it does not erase
  the X17M BootROM DAA gate, which rejected the X28 DA with `0x7017`.

### Host-facing storage functionality

These images contain substantial internal storage code: eMMC/NAND drivers,
partition lookup, `blkdev_read`/`blkdev_write`, `raw_read`/`raw_write`,
Preloader rawdata push/pop, seccfg access, boot metadata, and the
`usbdl_send_da`/`usbdl_jump_da` path. That explains how Preloader reads its own
boot media and loads the next stage. It does **not** expose a confirmed
host-issued raw-LBA or partition-read command. The only clearly host-facing
download operation is DA transfer/jump, which requires execution of a DA and
remains behind the existing authentication boundary.

Classifications from these files:

- Standard selector parser: **CONFIRMED in supplied images; UNKNOWN for the
  exact 2025 X17M binary**.
- Factory/advanced META/fastboot selector strings: **CONFIRMED in supplied
  images; live reachability on X17M UNKNOWN**.
- X17M `METAMETA` path: **BLOCKED for the tested token**, since the live device
  returned only another `READY` and never exposed META USB PID `0x202d`.
- Preloader-native host storage readback: **not identified**.
- DA loading/jump: **CONFIRMED as code**, but execution remains **BLOCKED** by
  BootROM DAA for the available X28 DA.

### Earliest stage conclusion

The answer to:

> "On this X17M, what is the earliest boot stage that can access eMMC storage
> through an externally controllable interface without first passing BootROM
> DAA?"

is:

> **Linux META is the earliest positively evidenced stage. The static
> Preloader mode-selection route is plausible in general, but the tested
> X17M `METAMETA` path did not transition. No Preloader- or loader_ext-native
> external eMMC readback interface has been identified.**

More precisely:

- Preloader internal eMMC access before USB handshake: **CONFIRMED**.
- Preloader external raw eMMC access without DA: **not identified**.
- loader_ext external storage access: **BLOCKED as a hypothesis by its code and
  observed role**.
- Linux META named storage/data operations: **CONFIRMED statically**.
- X17M `READY` preamble: **CONFIRMED** by live passive capture.
- Live X17M entry into Linux META using `METAMETA`: **BLOCKED for the tested
  path**; the controlled token test produced no transition.
- Unrestricted raw eMMC recovery without authenticated DA: **UNKNOWN / not
  demonstrated**.

## 7. Safe next evidence, when a working device exists

No action below was performed in this investigation.

1. Collect the seven previously selected read-only MRDUMP queries from a
   root-accessible X17M.
2. Preserve eMMC boot0 and boot1 through an already trusted, read-only Linux
   path. Those images would permit target-specific Preloader handler analysis.
3. The passive `0e8d:2000` capture is complete: it emitted repeated `READY`
   and no host response was sent.
4. If later separately authorized, test only the documented, non-storage
   Preloader identification/capability commands before considering a META
   selector. Do not use generic mtkclient initialization if it performs
   watchdog or register writes.
5. If META entry is eventually validated, inventory USB descriptors and issue
   only a META alive/version/capability query first. Do not invoke NVRAM,
   product-info, file-write, reboot, or power operations.

If the META selector is absent or authenticated, the recovery problem reduces
to the already stated narrow alternatives: locate an OEM-authenticated
X17M/MT6890 DA, or separately validate a specific `0x0992` authentication path.
The current evidence does not justify arbitrary boot-mode values, another DA
upload, or further LK fastboot work.
