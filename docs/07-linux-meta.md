# Linux META

## Role

Linux META is a later-stage AP diagnostic/recovery environment. It exists only after the kernel and enough userspace have started.

On the factory X17M, META mode configures a USB gadget and starts `meta_tst`.

## USB configuration

The factory META branch uses:

```text
VID 0x0e8d
PID 0x202d
configuration: dualacm
```

A manually reconstructed single-ACM configuration on the healthy reference router enumerated successfully under Windows. This established that the physical USB path, gadget controller and generic serial transport worked.

## meta_tst

Static and live analysis showed that `meta_tst` implements a framed AP-side META protocol and contains both read- and write-capable handlers.

A constrained read-only file-operation request was successfully used to retrieve:

- `/proc/cmdline`
- `/proc/mtd`

from a healthy unit over CDC ACM.

This proved an end-to-end path:

```text
host COM port
 -> USB CDC ACM
 -> /dev/ttyGS0
 -> meta_tst
 -> AP META handler
 -> open/read
 -> framed response
```

## Why this does not recover the current early bootloops

Both failed routers complete the Preloader META selector, but neither subsequently enumerates as the expected Linux META `0e8d:202d` gadget.

Therefore Linux META is not presently an entry point for those units.

## Where Linux META is valuable

It can be highly useful for a router that boots sufficiently far but has:

- broken networking;
- inaccessible web UI;
- no Telnet;
- no ADB;
- damaged network configuration;
- failed vendor network services.

That is a different recovery class from an early rootfs/kernel boot failure.

## Safety

`meta_tst` contains real write-capable handlers. Unknown commands should not be fuzzed against a valuable device. Read-only probes should use strict operation/path allowlists and bounded transactions.
