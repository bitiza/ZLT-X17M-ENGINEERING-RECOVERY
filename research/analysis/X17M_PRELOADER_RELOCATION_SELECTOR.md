# X17M Preloader relocation and selector analysis

Date: 2026-09-18

## Result

The MMM relocation blocker is resolved for the executable Preloader content.
The GFH header gives an explicit load address and entry offset:

```
GFH start/file offset       0x00000800
GFH load_addr               0x00200ea0
GFH content_offset          0x00000160
GFH jump_offset             0x00000160
content file offset         0x00000960
content runtime entry       0x00201000
```

Therefore, for bytes in this image's loaded GFH address space:

```
runtime_address = file_offset + 0x002006a0
file_offset     = runtime_address - 0x002006a0
```

This is **CONFIRMED** by the header and **STRONGLY SUPPORTED** by independent
code validation: the entry offset maps exactly to `0x201000`; Thumb-2 branch
targets and function prologues are coherent under this base; PC-relative
literal calculations resolve to real strings/data; and the resulting code
contains a large internally consistent Thumb-2 function region.

The remaining limitation is not the load map. It is selector-string reference
encoding: the compiler frequently materialises string addresses through
`ADD <reg>,PC` plus signed/relative literal tables, which generic flat `axt`
does not fully resolve. The selector parser can therefore be bounded and
partly disassembled, but every requested string xref is not yet safe to label
as a direct code reference.

No target communication was performed.

## 1. GFH / MMM header decoding

The MediaTek eMMC container points to the GFH chain at `0x800`. The relevant
raw bytes are:

```
00000800: 4d 4d 4d 01 38 00 00 00 46 49 4c 45 5f 49 4e 46
00000810: 4f 00 00 00 01 00 00 00 01 00 02 05 a0 0e 20 00
00000820: 38 bc 03 00 00 08 00 00 60 01 00 00 6c 06 00 00
00000830: 60 01 00 00 c2 60 00 01 4d 4d 4d 01 0c 00 01 00
00000840: 01 00 00 00 4d 4d 4d 04 cc 00 07 00 13 09 21 92
00000850: 88 13 00 00 ...
```

### GFH_FILE_INFO at 0x800

| field | raw offset | value | interpretation | status |
|---|---:|---:|---|---|
| magic/version | `0x800` | `MMM\x01` | GFH version 1 | **CONFIRMED** |
| header size | `0x804` | `0x38` | 56-byte FILE_INFO header | **CONFIRMED** |
| GFH type | `0x806` | `0x0000` | FILE_INFO | **CONFIRMED** |
| identifier | `0x808` | `FILE_INFO\0\0\0` | FILE_INFO record | **CONFIRMED** |
| file version | `0x814` | `1` | image file version | **CONFIRMED** |
| file type | `0x818` low 16 | `0x0001` | ARM bootloader (`arm_bl`) | **CONFIRMED** |
| flash device | `0x81a` | `2` | NAND sequential encoding in GFH; container itself is eMMC boot | **CONFIRMED; semantic caveat** |
| signature type | `0x81b` | `5` | MediaTek signature format 5 | **CONFIRMED** |
| load address | `0x81c` | `0x00200ea0` | address of GFH start in memory | **CONFIRMED** |
| file length | `0x820` | `0x0003bc38` | bytes from GFH start through signature | **CONFIRMED** |
| max size | `0x824` | `0x00000800` | GFH max-size field; not the actual image span | **CONFIRMED** |
| content offset | `0x828` | `0x00000160` | executable content begins 0x160 bytes after GFH start | **CONFIRMED** |
| signature length | `0x82c` | `0x0000066c` | 0x66c-byte tail signature region | **CONFIRMED** |
| jump offset | `0x830` | `0x00000160` | entry = load address + 0x160 | **CONFIRMED** |
| attributes | `0x834` | `0x016000c2` | packed GFH attributes | **CONFIRMED; individual flags not all assigned** |

The GFH content is therefore:

```
file:    [0x960, 0x3bdcc)
runtime: [0x201000, 0x23bf0c)
```

The signature region is:

```
file:    [0x3bdcc, 0x3c438)
length:  0x66c
```

This explains why the earlier “last nonzero byte” and the MMM end coincide at
`0x3c437`, while the executable content itself ends earlier at `0x3bdcb`.

### Subsequent GFH records

At `0x838` is `MMM\x01`, size `0x0c`, type `0x0001` (`GFH_BL_INFO`), with
body word `1`. At `0x844` is `MMM\x04`, size `0xcc`, type `0x0007`
(`GFH_BROM_CFG` in the standard GFH type table). Its body begins with the
configuration words at `0x84c`. These records are part of the GFH chain before
the executable content; they are not additional loadable code segments.

At `0x910` and `0x924` are additional `MMM` records with types `0x0002` and
`0x0008` and sizes `0x14` and `0x30`. They are metadata records inside the
FILE_INFO header area, not a second executable image. No internal segment table
or alternate executable load address was found.

## 2. Early ARM32/Thumb entry and relocation behaviour

The first code bytes are at file offset `0x960`, runtime `0x201000`:

```
file 0x964 / runtime 0x201004: EA000003    B       0x201018
file 0x978 / runtime 0x201018: LDR     r6,[pc,#0xb0]   ; 0x00201000
file 0x97c / runtime 0x20101c: STR     r4,[r6]
```

The early routine is ARM state. It performs memory-pattern initialisation,
not a file-to-DRAM memcpy:

| file instructions | operation | runtime range/value | status |
|---|---|---|---|
| `0xA58..0xA78` | word loop: store `0` and increment by 4 | `[0x109000, 0x11755c)` | **CONFIRMED** |
| `0xA7C..0xA78` | word loop: store `0xDEADBEFF` and increment by 4 | `[0x200000, 0x237efc)` | **CONFIRMED** |
| `0xAA4..0xAAC` | load entry literal and `MOV PC,r0` | branch to `0x201000` | **CONFIRMED** |

The values `0x109000`, `0x11755c`, `0x200000`, `0x237efc`, and
`0x201000` are literal runtime addresses. They are not inferred from nearby
file positions. The first two are scratch/initialisation bounds; the latter
three are the Preloader image/runtime region and handoff address. The early
routine is an ARM-mode bootstrap; the main content at `0x201000` and later
functions is Thumb-2.

There is no evidence in this routine of decompression or copying a second
embedded executable. The apparent self-overlap of the pattern-fill range is a
hardware/bootstrap detail (the early code executes from the BootROM-provided
mapping while preparing the later runtime region), not evidence for a second
file segment. A complete cache/MMU alias explanation is outside the selector
question and remains **UNKNOWN**.

## 3. Runtime image map

The best-supported single-image map is:

| file range | runtime range | mode/purpose | confidence |
|---|---|---|---|
| `0x800..0x95f` | `0x200ea0..0x200fff` | GFH chain/header metadata, not ordinary code | **CONFIRMED** |
| `0x960..0xb4f` | `0x201000..0x2017ef` | ARM bootstrap, literal pool, MMU/cache/bootstrap handoff | **CONFIRMED** |
| `0xb50..0x3bdcb` | `0x2017f0..0x23bf0b` | loaded Preloader content: Thumb-2 code, tables, data, strings | **STRONGLY SUPPORTED** |
| `0x3bdcc..0x3c437` | `0x23bf0c..0x23c577` | signature/certificate tail | **CONFIRMED** |

Independent checks:

1. `file 0x960 + 0x2006a0 = runtime 0x201000`, exactly the GFH entry.
2. ARM bootstrap literals and branch targets resolve to the explicit runtime
   addresses above.
3. Under the same base, file `0x16f94` becomes runtime `0x217634`, where a
   coherent Thumb-2 function prologue, calls, literal pools, and control flow
   are present.
4. A Thumb `ADD r2,PC` at runtime `0x217654` plus literal `0x18f99` resolves
   to runtime `0x2305f1`, file `0x2ff51`, the real `"No"` diagnostic string.
   This is a concrete PC-relative data validation independent of the GFH
   arithmetic.
5. The selector block maps to runtime addresses `0x230e01..0x230f09`, and
   the surrounding relocated code uses the same Thumb-2 PC-relative data
   model.

## 4. Selector string runtime addresses

Using `runtime = file + 0x2006a0`:

| string | file offset | runtime address | state |
|---|---:|---:|---|
| `READY` | `0x30020` | `0x2306c0` | **CONFIRMED address** |
| `AT+NBOOT` | `0x30761` | `0x230e01` | **CONFIRMED address** |
| `AT+OK` | `0x3076a` | `0x230e0a` | **CONFIRMED address** |
| `AT+UNKONWN` | `0x30770` | `0x230e10` | **CONFIRMED address** |
| `METAMETA` | `0x3077b` | `0x230e1b` | **CONFIRMED address** |
| `ATEM0001` | `0x30796` | `0x230e36` | **CONFIRMED address** |
| `ATEM0002` | `0x307c3` | `0x230e63` | **CONFIRMED address** |
| `ATEMATEX` | `0x307e3` | `0x230e83` | **CONFIRMED address** |
| `FACTFACT` | `0x307ec` | `0x230e8c` | **CONFIRMED address** |
| `TCAFTCAF` | `0x307f5` | `0x230e95` | **CONFIRMED address** |
| `ADVEMETA` | `0x307fe` | `0x230e9e` | **CONFIRMED address** |
| `ATEMEVDX` | `0x30807` | `0x230ea7` | **CONFIRMED address** |
| `FACTORYM` | `0x30810` | `0x230eb0` | **CONFIRMED address** |
| `MYROTCAF` | `0x30819` | `0x230eb9` | **CONFIRMED address** |
| `FASTBOOT` | `0x30822` | `0x230ec2` | **CONFIRMED address** |
| `TOOBTSAF` | `0x3082b` | `0x230ecb` | **CONFIRMED address** |
| `unknown received` | `0x30837` | `0x230ed7` | **CONFIRMED address** |
| `METAFORB` | `0x30869` | `0x230f09` | **CONFIRMED address** |

## 5. What is and is not a genuine selector xref

The relocated image contains real Thumb-2 functions that materialise data
addresses with sequences such as:

```
LDR   rN,[literal-pool]
ADD   rN,PC
LDR/BL/compare using rN
```

Consequently, a simple `axt @ string_address` misses most references. The
`READY` query produces one apparent data xref at runtime `0x21779e`, but it is
an `ADD r3,PC` inside a table-building path and is not, by itself, proof of the
READY transmit call. It is classified **UNKNOWN**, not promoted to a selector
xref.

The strongest selector-related code region is the relocated Thumb-2 region
around `0x217e00..0x219fxx`, where repeated PC-relative table materialisation,
byte-buffer construction, comparisons, and calls occur. Several relative
literal values in this region resolve algebraically to the selector-string
addresses. However, the current generic disassembler does not preserve the
compiler's table provenance well enough to distinguish a true selector use
from coincidental equal relative values in shared data tables.

Therefore the following are **not yet claimed** as exact xrefs:

- an instruction address for each selector;
- containing selector-parser function address;
- whether each reference is a comparison operand, a log format, or an ACK;
- ARM versus Thumb for each individual string use (the surrounding region is
  Thumb-2, but table entries can be consumed by helper functions);
- a direct `READY` transmit call.

This is a narrower and more accurate unresolved point than the former
relocation uncertainty.

## 6. Selector parser reconstruction status

### Established

- The code and strings share one validated runtime mapping.
- `READY` and all requested selector/ack strings are in the same relocated
  data region.
- The relocated code contains byte-buffer construction and comparison-like
  loops, not merely dead string data.
- The runtime image is predominantly Thumb-2 after the ARM bootstrap.

### Strongly supported

- The parser is in the Thumb-2 code/table region around `0x217e00..0x219fxx`.
- It uses PC-relative tables to obtain selector and response strings.
- The repeated `ADD PC`/literal-table pattern explains why a flat string-xref
  search failed.

### Unknown

- exact receive function and buffer;
- exact requested length after `READY`;
- comparison helper and comparison order;
- `METAMETA` and `METAFORB` branch destinations;
- retry/timeout loop and cause of a repeated `READY`;
- `seclib_brom_meta_mode` gating;
- USB-versus-UART parser sharing;
- successful-selector handoff.

## 7. No live test was required

The load address, entry address, and file-to-runtime transform are explicit in
the image header and validated by code/data references. Connecting the
bootlooped router would not resolve the remaining static ambiguity without
sending a selector, which is outside this phase. No live communication was
performed.

