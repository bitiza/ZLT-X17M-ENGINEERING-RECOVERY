# X17M META-0 live observation

Date: 2026-09-18
Target communication: authorized, one bounded test only.

## Procedure

1. Waited for USB `0e8d:2000` (MediaTek MT65xx Preloader).
2. Selected the discovered bulk interface:
   * bulk IN: endpoint `0x81`, max packet 512;
   * bulk OUT: endpoint `0x01`, max packet 512.
3. Sent exactly eight bytes:
   `4d 45 54 41 4d 45 54 41` (`METAMETA`).
4. Sent no parameter record, no `ATEM0001` response, and no other payload.
5. Read for three seconds, stopping after the observation window.

## Raw result

```text
RX +0.017 s: 52 45 41 44 59              READY
RX +2.018 s: 41 54 45 4d 30 30 30 31      ATEM0001
```

No disconnect or re-enumeration occurred during the three-second read window.

## Interpretation

This is strong live confirmation of the correlated X17M META state machine:

```text
TARGET -> READY
HOST   -> METAMETA
TARGET waits approximately 2000 ms for compatibility v1 record
TARGET -> ATEM0001
```

The second response arrived approximately 2.001 seconds after `READY` was
observed and was produced without the host sending any parameter bytes. This
matches the source behavior where the first 12-byte receive has a 2000 ms
timeout and its return value is ignored, after which `ATEM0001` is sent.

The test stopped before sending any v1/v2 structure. No `ATEM0002`,
`ATEMATEX`, `DISCONNECT`, DA command, memory command, storage command, or
reset command was issued.

## State/effect boundary

The test confirms selector acceptance and entry into the META negotiation path.
It does not establish that the later parameter records are accepted, that
Linux META boots, or that any host-facing storage operation exists.


