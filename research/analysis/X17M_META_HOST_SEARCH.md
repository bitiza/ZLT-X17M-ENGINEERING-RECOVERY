# META host-client artifact search

Read-only search; no target communication was performed.

## Search scope

Searched:

* the extracted RG500/T750 MT6890 and MT6880 SDK source;
* all files under `/home/kali/Desktop/x17m`;
* bundled Feature Tool and preloader utilities;
* the local `analysis/tools/mtkclient_upstream` source tree.

The exact identifiers `METAUtility`, `SPMeta`, `MetaMode`, `META_DLL`,
and `bldr_send_para` were not found in the RG500 SDK or Feature Tool source.
The SDK contains only the Preloader-side definitions already documented in
`platform/mt6890/src/core/inc/meta.h`.

## Important host-side implementation found

A complete host implementation exists in the local upstream mtkclient source:

`analysis/tools/mtkclient_upstream/mtkclient/Library/meta.py:37--112`.

This is not proof that it is the OEM X17M client, but it is an executable
host-side implementation of the same MediaTek handshake vocabulary. It:

1. waits for USB PID `0x2000`;
2. waits for `READY`;
3. sends the selected eight-byte selector;
4. waits for the response;
5. when it receives `ATEM0001`, sends:
   `040000000100000003000000`;
6. when it receives `ATEM0002`, sends:
   `06000000010000000300000001000000`;
7. when it receives `ATEMATEX`, sends ASCII `DISCONNECT`.

The exact code is:

```python
if resp == b"ATEM0001":
    ep_out(bytes.fromhex("040000000100000003000000"))
    resp = bytearray(ep_in(maxinsize))
    if resp == b"ATEM0002":
        ep_out(bytes.fromhex("06000000010000000300000001000000"))
        resp = bytearray(ep_in(maxinsize))
        if resp == b"ATEMATEX":
            ep_out(b"DISCONNECT")
```

The same file sends alternative records for the non-world-phone
`ATEMATEM` path, including a 12-byte record and a 16-byte record, but those
are not the X17M's `ATEMATEX` path.

## Decoding the host records

### v1 record

Host bytes:

```text
04 00 00 00 01 00 00 00 03 00 00 00
```

Using the SDK's little-endian `para_v1_t` layout:

| Offset | Bytes | Decoded |
|---:|---|---|
| 0x00 | `04 00 00 00` | `len = 4` |
| 0x04 | `01 00 00 00` | `ver = 1` |
| 0x08 | `03` | `usb_type = 3` |
| 0x09 | `00` | `usb_num = 0` |
| 0x0a | `00` | `md0_type = 0` |
| 0x0b | `00` | `md1_type = 0` |

### v2 record

Host bytes:

```text
06 00 00 00 01 00 00 00 03 00 00 00 01 00 00 00
```

Using the SDK's `para_v2_t` layout:

| Offset | Bytes | Decoded |
|---:|---|---|
| 0x00 | `06 00 00 00` | `len = 6` |
| 0x04 | `01 00 00 00` | `ver = 1` |
| 0x08 | `03` | `usb_type = 3` |
| 0x09 | `00` | `usb_num = 0` |
| 0x0a | `00` | `md0_type = 0` |
| 0x0b | `00` | `md1_type = 0` |
| 0x0c | `01` | `meta_log_disable = 1` |
| 0x0d--0x0f | `00 00 00` | alignment/padding |

## Critical discrepancy

The SDK comment for `usb_type` says only:

* 0 = single-interface device;
* 1 = composite device.

The host implementation sends `usb_type = 3`. Neither the SDK nor the
host source defines an enum explaining value 3. Therefore:

* the byte sequence is **confirmed as a real host implementation's record**;
* `usb_type = 3` is **not source-defined as semantically valid by the supplied
  RG500 SDK**;
* it may be a broader META client/ELT-port identifier, a product-specific
  extension, or a stale SDK comment.

The host source also establishes `len=4`, `ver=1`, and v2 `len=6`, but the
Preloader source never validates these fields. The length values therefore
cannot be independently derived from the C definitions alone.

## Handshake ordering relative to the initial 12-byte receive

The host implementation does **not** send a record immediately after
`METAMETA`. It waits for the Preloader response. This fits the matching
Preloader source:

* X17M first performs `recv(v1,12,2000)` and ignores the return status;
* after that it sends `ATEM0001`;
* the host then sends the 12-byte v1 record above;
* the Preloader sends `ATEM0002`;
* the host sends the 16-byte v2 record above;
* the Preloader sends `ATEMATEX`;
* the host sends `DISCONNECT`.

Thus the “initial” v1 record relevant to a normal host is the one sent after
`ATEM0001`; the first compatibility receive may simply time out.

## Other search results

* `meta_com` and `g_meta_com_id): found only in Preloader source and boot-tag
  plumbing; no host serializer in the RG500 SDK.
* `para_v1_t`, `para_v2_t`, `ATEM0001/2`, `ATEMATEX): found in MT6890
  and MT6880 Preloader source plus the local mtkclient host implementation.
* `METAUtility`, `SPMeta`, `META_DLL`, `bldr_send_para`: not found.
* FeatureTool is an ELF executable with debug information, but its strings and
  symbols do not expose this META parameter protocol.
* mtkclient's `MetaMode` support is mode selection; its host transaction is
  implemented in `Library/meta.py`.

## Safety conclusion

The best evidence-backed client records currently available are:

```text
v1: 040000000100000003000000
v2: 06000000010000000300000001000000
```

They are **host-observed/source-code-confirmed for mtkclient**, not yet
X17M/OEM-confirmed. Because `usb_type=3` conflicts with the supplied SDK
comment, these bytes should not be described as semantically validated for the
X17M without an additional product-specific source or a controlled test.

The v1 send itself only supplies values consumed into Preloader RAM globals and
boot arguments. It does not inherently invoke eMMC/NVRAM access; later META
Linux behavior remains a separate question.

