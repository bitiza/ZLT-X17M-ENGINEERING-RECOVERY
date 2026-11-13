# X17M 20250327 Preloader / RG500 SDK source correlation

Status: static, read-only comparison. No target communication was performed.

The comparison source is the RG500/T750 SDK archive
`MTK01R04A06_BNX_C_SDK_L.tar.gz`, extracted under
`/tmp/rg500_preloader.WXZxxE/T750/mtk/package/boot/preloader/platform/mt6890`.
The X17M 20250327 Preloader remains authoritative; the SDK is not evidence
that the RG500 build configuration is identical.

## Executive result

The SDK contains the source implementation corresponding to the X17M selector
dispatcher. `core/main.c:bldr_cmd_handler()` (source lines 1100--1240) is an
**EXACT/NEAR-EXACT MATCH** to the recovered X17M function at runtime
`0x002188f0..0x00218c70`:

* the AT+ prefix and `AT+NBOOT`/`AT+OK` path occur in the same order;
* `METAMETA`, `FACTFACT`, `ADVEMETA`, `FACTORYM`, and `FASTBOOT` occur in the same order;
* the X17M has the source's 12-byte first parameter receive, `ATEM0001`, 12-byte parameter receive, `ATEM0002`, 16-byte V2 receive, `ATEMATEX`, and ten-byte disconnect receive;
* X17M contains `ATEMATEX`, not the non-world-phone `ATEMATEM`, strongly supporting `CFG_WORLD_PHONE_SUPPORT` for this image;
* the X17M immediate timeouts match the source: 2000, 5000, 5000, and 1000 ms.

This is source correlation, not a claim that every RG500 security option is
enabled in X17M.

## 1. Source search

The exact selector strings are defined together in
`core/inc/meta.h:42--77` and consumed by `core/main.c:1118--1239`.

| Strings | Source | Function/range | Conditional context |
|---|---|---|---|
| `READY`, `DISCONNECT` | `core/inc/meta.h:42--44` | constants | always defined |
| `METAMETA`, `ATEM0001`, `ATEM0002`, `ATEMATEX`, `ATEMATEM`, `METAFORB` | `core/inc/meta.h:46--57` | constants | ACK selected by `CFG_WORLD_PHONE_SUPPORT` |
| `ADVEMETA`, `ATEMEVDX` | `core/inc/meta.h:59--60` | constants | selector handler |
| `FACTFACT`, `TCAFTCAF` | `core/inc/meta.h:62--63` | constants | selector handler |
| `FACTORYM`, `MYROTCAF` | `core/inc/meta.h:65--66` | constants | selector handler |
| `AT+NBOOT`, `AT+OK`, `AT+UNKONWN` | `core/inc/meta.h:70--74` | constants | selector handler |
| `FASTBOOT`, `TOOBTSAF` | `core/inc/meta.h:76--77` | constants | selector handler |
| all selectors | `core/main.c:1100--1240` | `bldr_cmd_handler` | `SWITCHMD` is an additional `CFG_DT_MD_DOWNLOAD`-guarded case |

The surrounding implementation is a command callback, not a BootROM DA
command dispatcher. It receives one eight-byte handshake token and then uses
the selected command to send acknowledgements, receive META parameters, or set
`g_boot_mode`.

## 2. X17M argument and callback structures

The matching source declarations are in `drivers/inc/platform.h`:

```c
struct comport_ops { int (*send)(u8 *, u32); int (*recv)(u8 *, u32, u32); };
struct bldr_comport { u32 type; u32 tmo; struct comport_ops *ops; };
struct bldr_command { u8 *data; u32 len; };
struct bldr_command_handler { void *priv; u32 attr; bldr_cmd_handler_t cb; };
```

The correct X17M register mapping is therefore:

| X17M use | Source field | Meaning | Status |
|---|---|---|---|
| `r0+4` loaded at `0x2188fc`, tested before META/factory cases | `handler->attr` | `CMD_HNDL_ATTR_COM_FORBIDDEN` bit | X17M binary confirmed; source-correlated |
| `r1+0`, `r1+4` at `0x218902`, `0x21890e` | `cmd->data`, `cmd->len` | token pointer and length | X17M binary confirmed |
| `r2+8` at `0x218900` | `comport->ops` | callback table | X17M binary confirmed |
| `r4+0` | `comport->ops->send` | target-to-host callback | source-correlated; indirect implementation unresolved |
| `r4+4` | `comport->ops->recv` | host-to-target callback | source-correlated; indirect implementation unresolved |

This corrects the earlier tentative interpretation: `r0` is the command
handler, `r1` is the command descriptor, and `r2` is the comport object.

## 3. Selector control flow

The source-backed pseudocode is:

```text
handler(handler, cmd, comport):
    comm = comport->ops
    if cmd begins "AT+":
        if cmd == "AT+NBOOT": send("AT+OK"); boot_mode = NORMAL_BOOT
        else: send("AT+UNKONWN"); return false
    else if cmd == "METAMETA":
        if forbidden: send("METAFORB"); return false
        zero v1 and v2; clear md types
        recv(v1, 12, 2000)                         // backward-compatible record
        meta_com_id = v1.usb_type
        send("ATEM0001")
        if recv(v1, 12, 5000) == 0: save usb/md types
        send("ATEM0002")
        if recv(v2, sizeof(v2), 5000) == 0: save usb type/log-disable
        send("ATEMATEX")
        wait_for_discon(comm, 1000)                 // world-phone build
        boot_mode = META_BOOT
    else if cmd == "FACTFACT":
        if forbidden: METAFORB/false
        recv(v1, 12, 5); save usb type; send("TCAFTCAF")
        boot_mode = FACTORY_BOOT
    else if cmd == "ADVEMETA":
        if forbidden: METAFORB/false
        send("ATEMEVDX"); wait_for_discon(comm, 1000)
        boot_mode = ADVMETA_BOOT
    else if cmd == "FACTORYM":
        if forbidden: METAFORB/false
        recv(v1, 12, 5); save usb type; send("MYROTCAF")
        boot_mode = ATE_FACTORY_BOOT
    else if cmd == "FASTBOOT":
        send("TOOBTSAF"); boot_mode = FASTBOOT
    else: unknown/false
```

The X17M instruction-backed portions are the dispatcher range above, the
`METAMETA` equality branch at `0x2189ac`, the first 12-byte callback at
`0x2189f6`, `ATEM0001` transmission at `0x218a24`, the ten-byte receive
helper at `0x218888`/`0x2188a4`, and subsequent selector branches through
`0x218c70`. The source's `strlen`/bounded-comparison behavior corresponds to
the X17M helpers at `0x002276f8` and `0x00227722`.

## 4. META wire transaction

For the world-phone build supported by the X17M string set:

```text
TARGET -> HOST:  READY                         (USB listen loop)
HOST   -> TARGET: METAMETA                     (exactly 8 bytes)
HOST   -> TARGET: v1 record, 12 bytes          (initial compatibility receive)
TARGET -> HOST:  ATEM0001                     (8 bytes)
HOST   -> TARGET: v1 record, 12 bytes          (5-second receive)
TARGET -> HOST:  ATEM0002                     (8 bytes)
HOST   -> TARGET: v2 record, sizeof(v2) bytes  (normally 16 bytes)
TARGET -> HOST:  ATEMATEX                     (8 bytes)
HOST   -> TARGET: DISCONNECT                   (10 bytes, 1-second receive)
TARGET:            boot_mode = META_BOOT
```

`para_v1_t` is 8-byte `{len,ver}` followed by four bytes:
`usb_type`, `usb_num`, `md0_type`, `md1_type`, for a total of 12 bytes.
`para_v2_t` adds `meta_log_disable`; normal 32-bit alignment makes its size
16 bytes. The source does not validate the record header fields before using
the selected byte fields. The initial 12-byte receive return value is ignored;
the later 12/16-byte receives are accepted only when the callback returns zero.

`wait_for_discon()` clears a ten-byte buffer, calls `recv(buffer,10,1000)`,
and compares it with literal `DISCONNECT` (`main.c:261--279`). A timeout or
different ten bytes is logged, but the function still returns and the caller
sets `META_BOOT`.

## 5. READY and the observed repeated READY

`core/handshake_usb.c:192--243` sends `READY` on every iteration of
`usb_listen()` while no complete eight-byte token has arrived. It polls the
USB CDC queue and sleeps 20 ms between iterations. `usb_handshake_handler`
(`276--295`) then constructs the command descriptor with `cmd.len = 8` and
calls the registered handler.

`usb_handshake()` (`301--365`) returns false if enumeration/listening or the
callback fails, and shuts down the USB service. The normal boot path then also
tries UART (`main.c:1259--1287`).

Therefore `READY -> METAMETA -> READY` is **not** the normal in-function META
sequence: after the equality branch the X17M must first receive the 12-byte
compatibility record, then emit `ATEM0001`. A second `READY` is most naturally
explained by a restarted/new USB listen invocation after a failed callback,
USB teardown/re-enumeration, or a different Preloader instance. A timeout in
the subsequent META receive is also possible, but this source path does not
itself transmit `READY` while blocked in `bldr_cmd_handler`.

Classification against the exact binary:

| Explanation | Classification |
|---|---|
| METAMETA rejected solely by selector comparison | **IMPOSSIBLE** for an exact 8-byte token reaching `0x2189ac` |
| accepted, but host did not send the first 12-byte record | **STRONGLY SUPPORTED** |
| timeout/restart then another USB listen emits READY | **STRONGLY SUPPORTED** |
| security/SLA rejection | **PLAUSIBLE**, if handler attr has forbidden bit; would send `METAFORB` |
| USB disconnect/re-enumeration/new instance | **PLAUSIBLE** |
| CR/LF framing included in the eight-byte command | **PLAUSIBLE**; command length is fixed at 8, so extra bytes belong to the next receive |

## 6. Security and META policy

`bldr_handshake()` calls `seclib_brom_meta_mode()` and
`seclib_sla_enabled()` (`main.c:1248--1253`). In `NORMAL_BOOT`, an enabled
SLA sets `handler->attr |= CMD_HNDL_ATTR_COM_FORBIDDEN`
(`1260--1267`). The selector then emits `METAFORB` for META, factory, and
advanced-META branches (`1143--1144`, `1186--1187`, `1198--1199`,
`1210--1211`, `1236--1239`). `FASTBOOT` has no corresponding forbidden
check in this source function.

This is Preloader command policy. It is not BootROM DAA. The SDK's download
code separately contains `usbdl_vfy_da:disabled/forbidden` logging and image
verification policy (`core/download.c:475--500`), while image loading uses
`blkdev_read` and `sec_img_auth` in the loader path. Nothing in the selector
handler exposes those storage reads to a host.

## 7. Mode destinations

The SDK enum (`drivers/inc/platform.h:157--166`) is:

| Selector | Source state | Value in SDK | X17M status |
|---|---|---:|---|
| `AT+NBOOT` | `NORMAL_BOOT` | 0 | control flow matched; value not independently proven |
| `METAMETA` | `META_BOOT` | 1 | control flow matched; value not independently proven |
| `FACTFACT` | `FACTORY_BOOT` | 4 | source-correlated only |
| `ADVEMETA` | `ADVMETA_BOOT` | 5 | source-correlated only |
| `FACTORYM` | `ATE_FACTORY_BOOT` | 6 | source-correlated only |
| `FASTBOOT` | `FASTBOOT` | 99 | source-correlated; not conventional Android fastboot proof |

The X17M LK/rootfs mode consumers previously identified are consistent with
these being boot-mode selectors, but the SDK enum alone must not be used to
assert X17M numeric values.

## 8. Storage conclusion

The source reveals no host-facing raw storage operation before DA execution.
The selector callback only sends acknowledgements, receives small META
records, updates boot arguments, waits for disconnect, and changes
`g_boot_mode`. `blkdev_read()` appears in the internal image-loading path,
not as a handler reachable through `METAMETA` or the other selectors. Thus the
SDK strengthens the META/recovery hypothesis but does not establish eMMC
readback, partition access, or a DA-free storage protocol.

## 9. Remaining differences / unresolved items

1. The concrete X17M `send` and `recv` function bodies behind the runtime
   callback table remain unresolved; the source proves their types and wire
   direction, not their exact implementation.
2. The X17M compile-time security configuration (`CFG_USB_*`, SLA/factory-lock
   state, timeout enables) is not recoverable solely from RG500 source.
3. The X17M numeric boot-mode values and downstream Linux META implementation
   need binary confirmation; source enum values are RG500-only.
4. Source `wait_for_discon()` explains the ten-byte receive, but a live
   capture is required to distinguish parser restart from USB re-enumeration
   in the prior observation. No such test was performed here.

## Final classifications

* Selector implementation: **X17M BINARY CONFIRMED / EXACT SOURCE-CORRELATED**.
* META record sizes, strings, ordering, and timeouts: **X17M BINARY CONFIRMED**
  where the corresponding instruction and literal were recovered; field names
  and meanings are **SOURCE-CORRELATED**.
* READY loop and `DISCONNECT` semantics: **STRONGLY SUPPORTED** by exact source
  behavior and matching X17M constants.
* SLA/META forbidden behavior: **SOURCE-CORRELATED**, with X17M `METAFORB`
  string and forbidden branch confirmed but the live security state unknown.
* DA-free host storage: **NOT FOUND / UNKNOWN**, with no evidence in the
  matching selector source.

