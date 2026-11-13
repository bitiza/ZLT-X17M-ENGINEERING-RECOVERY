# X17M META para_v1_t analysis

Static-only analysis. No target communication was performed.

Source compared:

`/tmp/rg500_preloader.WXZxxE/T750/mtk/package/boot/preloader/platform/mt6890/src`

The same definitions also occur in the MT6880 comparative tree. The X17M
binary remains authoritative.

## 1. Exact definition

The exact definition is `core/inc/meta.h:78--95`:

```c
typedef struct {
    unsigned int len;
    unsigned int ver;
} para_header_t;

typedef struct {
    para_header_t header;
    unsigned char usb_type;
    unsigned char usb_num;
    unsigned char md0_type;
    unsigned char md1_type;
} para_v1_t;

typedef union {
    para_header_t header;
    para_v1_t     v0001;
} para_t;
```

On the 32-bit ARM build, the field offsets and size are:

| Offset | Size | Field |
|---:|---:|---|
| 0x00 | 4 | `header.len` |
| 0x04 | 4 | `header.ver` |
| 0x08 | 1 | `usb_type` |
| 0x09 | 1 | `usb_num` |
| 0x0a | 1 | `md0_type` |
| 0x0b | 1 | `md1_type` |

`sizeof(para_v1_t) = 12` is directly implied by the source layout and by
the X17M receive length at `0x002189f6`.

## 2. Field meanings and supported values

### `len`

Type: unsigned 32-bit integer. It is described only as the parameter length
through the `para_header_t` field name. No enum, constant, assignment,
range check, or comparison for `header.len` exists in the SDK source.

**Supported conclusion:** semantic role is “record length”; the normal numeric
value is **not recoverable from this SDK**.

### `ver`

Type: unsigned 32-bit integer. It is described only as the parameter version.
No enum, constant, assignment, range check, or comparison for `header.ver`
exists in the SDK source.

**Supported conclusion:** semantic role is “record version”; the normal
numeric value is **not recoverable from this SDK**.

The protocol token `ATEM0001` is a selector/acknowledgement string; it is not
a source-defined numeric value for `para_header_t.ver`.

### `usb_type`

Source comment: `0: single interface device, 1: composite device`
(`core/inc/meta.h:86`).

Supported values:

| Value | Meaning |
|---:|---|
| 0 | single-interface USB device |
| 1 | composite USB device |

The handler uses this byte as `g_meta_com_id` for the META/ELT port
(`core/main.c:1149--1151`). It is not the separate `meta_com_t` enum
(`META_UNKNOWN_COM=0`, `META_UART_COM=1`, `META_USB_COM=2`) in
`drivers/inc/platform.h:187--191`.

### `usb_num`

Source comment: “usb com port number” (`meta.h:87`). The SDK contains no
enum, range definition, default assignment, or use in `bldr_cmd_handler()`.
It is copied as part of the received record but is not consumed by the
Preloader selector.

**Supported conclusion:** a port-number byte exists; its normal value is
unknown from this SDK.

### `md0_type`, `md1_type`

Source comments identify these as modem-image type bytes
(`meta.h:88--89`; the comments themselves say “md image type for md1”).
No enum or symbolic value table for either byte exists in the SDK. The only
Preloader consumer is:

```c
bootarg.md_type[0] = param.v0001.md0_type;
bootarg.md_type[1] = param.v0001.md1_type;
```

at `core/main.c:1158--1164), and those assignments occur only after the
later `ATEM0001` receive, not after the initial compatibility receive.

The handler initializes the RAM boot-argument values to zero at
`main.c:1137--1140` and, for the BROM META boot case, again at
`main.c:1300--1302`.

**Supported conclusion:** these are modem-image selector bytes; their normal
numeric values are not defined in the SDK.

## 3. Every source location constructing or sending para_v1_t

No host-side construction or transmission implementation was found in the
SDK tree.

Preloader declarations/receives:

1. MT6890 `core/main.c:1135`: local `para_t param` for METAMETA.
2. MT6890 `core/main.c:1147`: initial
   `comm->recv((u8*)&param.v0001, sizeof(param.v0001), 2000)`.
3. MT6890 `core/main.c:1156`: second
   `comm->recv(... sizeof(param.v0001), 5000)` after sending `ATEM0001`.
4. MT6890 `core/main.c:1183`, `1189`: FACTFACT local and 12-byte receive.
5. MT6890 `core/main.c:1207`, `1213`: FACTORYM local and 12-byte receive.
6. The same implementation is duplicated in the MT6880 comparative tree at
   corresponding `core/main.c` locations.
7. `core/inc/meta.h:78--95`: only type definition.

The archive contains no Feature Tool, META host daemon, modem factory tool,
Python host implementation, or other source that fills and sends
`para_v1_t`. The only matching host-adjacent artifact is a preloader tool
binary directory; it contains no source-level para_v1 construction.

## 4. Normal host-side values

**No normal host-side implementation exists in the supplied SDK source tree.**
Consequently the following are not source-supported:

* numeric `len`;
* numeric `ver`;
* default `usb_num`;
* default `md0_type` or `md1_type`;
* whether ordinary X17M META uses single or composite USB in this particular
  product configuration.

The only normal values explicitly supported by source are
`usb_type = 0` or `usb_type = 1`.

The X17M binary confirms the 12-byte receive and subsequent use of the
`usb_type` byte, but it cannot recover the absent host's intended header
values.

## 5. What the handler validates

For the initial METAMETA parameter receive
(`main.c:1147`, X17M `0x002189f6`):

* receive size is fixed at 12 bytes;
* timeout is 2000 ms;
* the return status is ignored;
* no `len` validation;
* no `ver` validation;
* no `usb_type` range validation;
* no `usb_num` validation;
* no modem-byte validation;
* only `param.v0001.usb_type` is copied to RAM global `g_meta_com_id`.

After `ATEM0001` (`main.c:1154--1164`), a second 12-byte record is
received with a 5000 ms timeout. Only a zero return status gates consumption;
then `usb_type`, `md0_type`, and `md1_type` are copied into RAM state.
Even this second path does not validate the header or enum ranges.

## 6. Safest semantically valid initial record

A fully source-supported 12-byte hex record cannot be provided without
guessing `len`, `ver`, `usb_num`, and the modem-type values. Per the
request, this report therefore intentionally does **not** provide a 12-byte
hex string.

The strongest semantically supported constraints for an ordinary USB META
record are only:

* `usb_type = 0` means single interface, or `usb_type = 1` means composite;
* the remaining fields must be supplied by the actual matching META host
  implementation, which is absent from this SDK;
* the Preloader itself accepts any byte values because it performs no field
  validation.

Thus choosing zeroes for unknown fields would be an unverified experiment, not
a source-derived “normal” record.

## 7. Persistence and security effects

Receiving the first 12-byte record does not call any storage routine. In the
matching source path it performs only:

```text
USB/UART recv -> stack-local para_v1_t
             -> g_meta_com_id = param.v0001.usb_type
```

At this point it does **not**:

* call `blkdev_read`, `blkdev_write`, erase, or partition APIs;
* write eMMC boot/user areas;
* write NVRAM, proinfo, or persistent configuration;
* change the active slot;
* change `g_boot_mode`;
* alter `sboot_state`, SLA, DAA, lock state, or authentication state.

`g_meta_com_id` is RAM global state. Later, if the complete META exchange
succeeds, `platform.c:386--392` copies META state into a boot tag for the
next boot stage, and `platform.c:449` copies modem types into boot tags.
That is still handoff metadata in RAM, not persistent storage.

The first record therefore has a **RAM-only effect**: it can set the in-memory
META communication identifier byte. It does not itself establish a storage
readback path or bypass BootROM DAA.

## Final classification

* Exact structure definition: **CONFIRMED**.
* `usb_type` values 0/1: **CONFIRMED**.
* Numeric values for `len`, `ver`, `usb_num`, `md0_type`, `md1_type`:
  **UNKNOWN / absent from supplied SDK**.
* Host-side normal record: **NOT FOUND**.
* Initial-record side effects: **CONFIRMED RAM-only**.
* A source-supported final 12-byte hex record: **NOT AVAILABLE WITHOUT GUESSING**.

