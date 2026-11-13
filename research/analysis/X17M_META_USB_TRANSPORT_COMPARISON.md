# X17M META USB transport comparison

Static/repository-only review. The corrected program was not executed and no
target was contacted.

> Correction after descriptor-discovery review: copying mtkclient's
> `bDeviceClass=devclass` device lookup was inappropriate for this X17M. Device
> discovery must use VID:PID only; class 10 is evaluated later against
> interface descriptors. See `X17M_PRELOADER_DESCRIPTOR_DIAGNOSTIC.md`.

## Reference implementation

No separate custom script that generated the preserved successful runs is
present in the project tree. The exact reusable implementation is the local
upstream mtkclient code used for the successful META-0/META-1/full-META
procedure:

* `analysis/tools/mtkclient_upstream/mtkclient/Library/meta.py:37-109`
  implements the selector/ACK state machine.
* `analysis/tools/mtkclient_upstream/mtkclient/Library/Connection/usblib.py:298-385`
  implements USB setup.
* `analysis/tools/mtkclient_upstream/mtkclient/Library/Port.py:24-35` creates
  `UsbClass(..., devclass=10)`, i.e. CDC-class interface selection.
* `analysis/tools/mtkclient_upstream/mtkclient/config/usb_ids.py:2-7` maps
  `0e8d:2000` to interface `-1`, meaning dynamic selection.

The preserved successful evidence independently records the resulting bulk
endpoints as IN `0x81`, OUT `0x01`, max packet 512
(`analysis/live_meta_uart/20260918T122836Z_attempt3/meta_handshake.log:2`).
There is no preserved successful descriptor dump recording a separate
configuration number or alternate-setting number.

## Required comparison

| Item | Successful reference | Failed `run_meta_usb_diag.py` before this patch |
|---|---|---|
| Script/source | `meta.py:37-109` plus `usblib.py:298-385` | `analysis/run_meta_usb_diag.py:67-149` |
| Interface | Port mapping `-1`; first interface whose class is 10 (`usblib.py:328-337`) | Guesses/iterates active interface numbers, then always claims 0 (`:111-124`) |
| Altsetting | No explicit alternate-setting selection; descriptor returned by `find_descriptor` on the active configuration (`usblib.py:345`) | No interface descriptor or alternate setting selected |
| Bulk IN | Discovered from selected interface (`usblib.py:378-383`); successful run recorded `0x81`, 512 bytes | Hard-coded device endpoint `0x81`, size 512 (`:79`) |
| Bulk OUT | Discovered from selected interface (`usblib.py:372-377`); successful run recorded `0x01` | Hard-coded device endpoint `0x01` (`:94`) |
| Kernel driver | Detach interface 0 and selected CDC interface; expected compatibility exceptions are handled (`usblib.py:347-368`) | Detaches guessed interfaces; suppresses all errors (`:116-121`) |
| Configuration | Reads active configuration; calls `set_configuration()` only for `Configuration not set` (`usblib.py:316-321`) | Unconditionally calls `set_configuration()` after detaching (`:122`) |
| READY read | Reads one packet of `EP_IN.wMaxPacketSize`; exact equality `resp == b"READY"` (`meta.py:52-63`) | Reads arbitrary 512-byte chunks, concatenates them, and searches for a substring (`:75-89`) |
| Timing | Connect and read the selected endpoint immediately; source retries on disconnect | Waits up to five seconds on a guessed endpoint, while the observed PID window was about one second |
| Failure policy | No selector write until exact READY | Sends METAMETA after READY timeout (`:127-130`) |

The successful state-machine source sends the selector after exact READY
(`meta.py:57-63`). The preserved successful log has a logging-order anomaly
(`SEND METAMETA` is logged before its subsequent READY read), but the source
implementation and the live packet sequence establish the required gate.

## Root cause assessment

The failed program did not reproduce the successful USB path. It changed the
active configuration, did not select the CDC interface by class, did not use
that interface's endpoint descriptors, and treated arbitrary endpoint data as
a token stream. Consequently, data such as `CDC ACM Data Interface` and
`MediaTek` can be a valid 512-byte transfer from a different interface or from
the disturbed configuration; it is not evidence of a Preloader READY packet.

The evidence strongly supports a combined setup/selection failure. The exact
successful descriptor capture proves only the resulting addresses `0x81/0x01`,
not that those addresses are valid on every interface. Therefore it would be
incorrect to identify one of wrong-interface, wrong-altsetting, or
unconditional reconfiguration as uniquely sufficient from the failed log
alone. The unconditional `set_configuration()` is independently a concrete
deviation and can invalidate the short-lived active Preloader state. The
five-second wait is also inconsistent with the observed approximately
one-second enumeration window.

There is no evidence that endpoint data was an intentional alternate setting;
the successful implementation never explicitly chooses one. The failed code
also never discovered an alternate setting. A timing-only explanation is
insufficient because the failed reader did receive data, just not the exact
READY packet, and it attempted a write after the device had disappeared.

## Corrected USB setup/handshake

Only the USB section of `analysis/run_meta_usb_diag.py` was replaced. UART
capture, passive `lsusb` monitoring, evidence directories, and SHA-256
collection remain unchanged. The relevant corrected source is:

```python
cfg, intf, ep_in, ep_out = setup_reference_usb(dev)
print(f'CONFIGURATION={cfg.bConfigurationValue}', flush=True)
print(f'INTERFACE={intf.bInterfaceNumber}', flush=True)
print(f'ALTSETTING={intf.bAlternateSetting}', flush=True)
print(f'BULK_IN=0x{ep_in.bEndpointAddress:02x}', flush=True)
print(f'BULK_OUT=0x{ep_out.bEndpointAddress:02x}', flush=True)

print('WAITING_FOR READY', flush=True)
if wait_exact(ep_in, b'READY', 'INITIAL_READY', timeout=0.8) is None:
    print('READY_TIMEOUT', flush=True)
    print('HANDSHAKE_ABORTED_AT=READY', flush=True)
else:
    print('READY_RECEIVED', flush=True)
    send_only(ep_out, b'METAMETA', 'METAMETA')
    if wait_exact(ep_in, b'ATEM0001', 'ATEM0001', timeout=2.5,
                  allow_ready=True) is None:
        usb_log('HANDSHAKE_ABORTED_AT=ATEM0001')
    else:
        send_only(ep_out, bytes.fromhex('040000000100000003000000'), 'V1')
        if wait_exact(ep_in, b'ATEM0002', 'ATEM0002', timeout=2.5) is None:
            usb_log('HANDSHAKE_ABORTED_AT=ATEM0002')
        else:
            send_only(ep_out,
                      bytes.fromhex('06000000010000000300000001000000'),
                      'V2')
            if wait_exact(ep_in, b'ATEMATEX', 'ATEMATEX', timeout=2.5) is None:
                usb_log('HANDSHAKE_ABORTED_AT=ATEMATEX')
            else:
                send_only(ep_out, b'DISCONNECT', 'DISCONNECT')
```

`setup_reference_usb()` preserves an active configuration, selects class 10,
logs (rather than hides) expected detach/claim exceptions, fails on selected
interface/endpoint errors, and discovers endpoints from the selected
interface. `receive_packet()` logs every libusb exception. The state machine
cannot send METAMETA without the exact `READY_RECEIVED` branch.

The file was not executed or syntax-run as part of this review, per the
no-execution requirement.
