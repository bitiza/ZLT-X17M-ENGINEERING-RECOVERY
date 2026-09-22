# LK / META / fastboot

> **Status: active investigation — do not treat this chapter as complete.**

## Established so far

The exact LK contains:

- normal NAND boot-image loading;
- ramdisk handling;
- AEE/MRDUMP support;
- a limited fastboot framework.

The currently identified endpoint does not expose the usual full-fastboot recovery surface:

- no identified `download:` handler;
- no identified `boot` command;
- no identified `flash:` command;
- no identified `erase:` command;
- `set_active:` is present only as unsupported behavior.

## Why LK remains important

LK may still matter for a device that:

```text
BootROM     OK
Preloader   OK
LK          OK
kernel      possibly OK
network     failed
ADB/Telnet  unavailable
web UI      unavailable
```

Such a device does not necessarily require a BootROM DA recovery if LK/META exposes a useful OEM diagnostic path.

## Investigation goals

The remaining work should map:

1. META boot-mode handling inside LK;
2. USB functions/endpoints registered in META/factory/fastboot modes;
3. AEE/MRDUMP command dispatch;
4. OEM commands outside the obvious fastboot table;
5. existing-image boot overrides that do not require modifying A/B metadata;
6. any safe memory/log/storage read surface useful for diagnosis or recovery.

## Evidence rule

An internal load/read/write function is not a recovery interface by itself. A recovery surface is considered established only when a host-controlled path to that function is demonstrated or statically proven.

## UNRESOLVED

This document will be expanded as the LK/META investigation continues.
