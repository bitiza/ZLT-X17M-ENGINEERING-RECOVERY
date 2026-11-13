# X17M full META handoff retry with passive descriptors/logs

Date: 2026-09-18

## Handshake

The exact validated sequence completed:

```text
METAMETA
ATEM0001
040000000100000003000000
ATEM0002
06000000010000000300000001000000
ATEMATEX
DISCONNECT
```

Responses matched at every stage.

## Passive post-handoff observation

After `DISCONNECT`, no protocol commands or endpoint payloads were sent.
Only `lsusb`, USB descriptor enumeration, and kernel log snapshots were
collected.

Observed cycle:

```text
0e8d:2000  MT65xx Preloader
<disconnect>
0e8d:0003  MT6227 phone
<disconnect>
0e8d:2000  MT65xx Preloader
<disconnect>
0e8d:0003  MT6227 phone
<disconnect>
0e8d:2000  MT65xx Preloader
```

The `0e8d:0003` descriptor exposed:

* Communications class / Abstract modem / AT-command protocol;
* CDC Data interface;
* bulk IN endpoint `0x81`, bulk OUT endpoint `0x01).

The `0e8d:2000` descriptor exposed:

* manufacturer: MediaTek;
* product: MT65xx Preloader;
* CDC ACM communication/data interfaces;
* bulk IN `0x81`, bulk OUT `0x01`.

No `0e8d:202d`, Android gadget, ADB, Linux META CDC identity, or other
Linux-stage USB interface appeared during the observation.

## Conclusion

The full META transaction is repeatedly accepted through `DISCONNECT`, but
this unit then resets through BootROM/Preloader rather than presenting an
observable LK/Linux META gadget. The failure boundary is after the Preloader
META negotiation and before (or during) the subsequent boot-stage handoff.

No DA, memory, storage, reset, or command was sent after `DISCONNECT`.

