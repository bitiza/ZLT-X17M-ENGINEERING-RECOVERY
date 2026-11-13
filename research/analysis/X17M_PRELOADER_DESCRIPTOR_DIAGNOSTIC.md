# X17M Preloader descriptor-only diagnostic

This is a pre-run static review. No diagnostic was executed and no router was
contacted.

## Discovery correction

`analysis/run_meta_usb_diag.py::find_preloader()` now searches strictly for:

```python
usb.core.find(idVendor=0x0e8d, idProduct=0x2000, backend=backend)
```

It no longer supplies `bDeviceClass` to `usb.core.find()`.

The class-10 filter was introduced by copying
`mtkclient/Library/Connection/usblib.py:305`, where `UsbClass.connect()` passes
its `devclass` into device discovery. `Port.py:34` constructs that class with
`devclass=10`. That source conflates the desired CDC Data interface class with
the device descriptor class. Applying it to X17M discovery was not supported
by the preserved live descriptors and caused PyUSB to discard `0e8d:2000`
before VID:PID inspection.

The corrected separation is:

1. discover the USB device solely by VID:PID;
2. obtain the already-active configuration without changing it;
3. enumerate every interface and alternate setting;
4. only then identify class-10 transport candidates.

## Descriptor-only program

`analysis/dump_preloader_usb_descriptors.py`:

* starts RX-only UART capture at 921600 8N1;
* waits for `0e8d:2000` without a class filter;
* calls only `get_active_configuration()` for configuration selection;
* never calls `set_configuration()`;
* never claims an interface;
* never detaches a kernel driver;
* never reads an endpoint;
* never writes an endpoint or device payload;
* enumerates every active interface/alternate setting and endpoint;
* identifies the first interface-class-10 candidate used by the mtkclient
  selection rule, without claiming it;
* exits after preserving descriptor and UART evidence.

Strict USB terminology qualification: obtaining descriptors can cause libusb
to issue standard read-only `GET_DESCRIPTOR`/configuration control requests if
they are not already cached by the host. The program sends zero vendor
protocol payloads, zero endpoint writes, and zero configuration/interface
state-changing requests. A literal zero-USB-packet program could not acquire
the requested descriptors.

## Current report before the descriptor run

DEVICE `bDeviceClass`: **UNKNOWN** — not preserved numerically in earlier
evidence. It is demonstrably not safe to assume it is class 10.

CONFIGURATION: **UNKNOWN numerically** — earlier reports did not preserve
`bConfigurationValue`.

INTERFACES: **PARTIALLY CONFIRMED** — earlier descriptor observations reported
CDC ACM communication/data interfaces, but did not preserve all interface,
alternate-setting, subclass, and protocol fields.

CDC/DATA INTERFACE: **CONFIRMED PRESENT; NUMBER UNKNOWN**.

BULK IN: **0x81 CONFIRMED** by successful META evidence.

BULK OUT: **0x01 CONFIRMED** by successful META evidence.

WHY OLD `find_preloader()` MISSED IT: **CONFIRMED CODE REGRESSION** — it
required `bDeviceClass == 10` during device lookup. `lsusb` independently saw
`0e8d:2000`, while PyUSB returned no match through that filtered query. The
exact non-10 device-class value remains for the descriptor-only run to record.

No attempt is made here to invent the missing descriptor values from the
interface description or endpoint addresses.
