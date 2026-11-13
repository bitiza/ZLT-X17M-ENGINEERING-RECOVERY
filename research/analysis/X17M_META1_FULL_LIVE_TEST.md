# X17M META-1 and full META live tests

Date: 2026-09-18. Authorized live communication only.

## META-1

Sequence:

```text
TARGET -> READY
HOST   -> METAMETA
TARGET -> ATEM0001
HOST   -> 040000000100000003000000
TARGET -> ATEM0002
STOP
```

Raw result:

```text
READY
ATEM0001
ATEM0002
```

The V1 packet was accepted by the exact X17M Preloader.

## Full META

Fresh Preloader enumeration on bulk IN `0x81`, bulk OUT `0x01`.

Sent and received:

```text
HOST   -> METAMETA
TARGET -> READY
TARGET -> ATEM0001

HOST   -> 040000000100000003000000
TARGET -> ATEM0002

HOST   -> 06000000010000000300000001000000
TARGET -> ATEMATEX

HOST   -> DISCONNECT
```

The post-handshake USB observation saw `0e8d:2000` still present during the
short observation window. No DA, memory, storage, reset, or additional command
was sent.

## Conclusions

* The mtkclient V1 record is accepted by the X17M Preloader.
* The V2 record is accepted and elicits `ATEMATEX`.
* The full source-correlated META negotiation is live-confirmed through the
  disconnect stage.
* This still does not prove Linux META enumeration or host-facing storage
  functionality.

