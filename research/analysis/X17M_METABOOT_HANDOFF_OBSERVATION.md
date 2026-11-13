# X17M META_BOOT handoff observation

Date: 2026-09-18

## Test

The validated sequence was completed:

```text
METAMETA
ATEM0001
040000000100000003000000
ATEM0002
06000000010000000300000001000000
ATEMATEX
DISCONNECT
```

After `DISCONNECT`, the host performed no USB protocol reads or writes to any
new interface. It only passively polled `lsusb` for 60 seconds.

## Result

The device was initially still visible as:

```text
0e8d:2000  MediaTek MT65xx Preloader
```

It then disappeared. No new MediaTek, Android, Linux-gadget, CDC, ADB, or
expected META Linux PID (including `0e8d:202d`) appeared during the
observation window.

## Conclusion

META negotiation is live-confirmed through `ATEMATEX` and `DISCONNECT`.
LK/Linux META_BOOT USB enumeration was **not observed**. The result is
consistent with the unit resetting or failing before a Linux USB gadget is
enumerated; it does not show rejection of the META negotiation itself.

No DA, memory, storage, reset, or new-interface command was sent after the
handoff point.

