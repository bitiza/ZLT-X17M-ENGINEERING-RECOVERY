# X17M META_BOOT UART report

Date: 2026-09-18. Evidence: `analysis/live_meta_uart/20260918T122836Z_attempt3/`.

## Result

A synchronized RX-only UART capture and validated USB META handshake completed.
UART was `/dev/ttyUSB0`, CH341, 921600 8N1, no flow control. The descriptor
was opened `O_RDONLY|O_NOCTTY|O_NONBLOCK`; no UART write occurred.

The validated exchange timestamps were:

```text
12:36:56.660736  HOST -> METAMETA
12:36:56.670444  TARGET -> READY
12:36:58.671206  TARGET -> ATEM0001
12:36:58.671395  HOST -> 040000000100000003000000
12:36:58.674650  TARGET -> ATEM0002
12:36:58.675163  HOST -> 06000000010000000300000001000000
12:36:58.679264  TARGET -> ATEMATEX
12:36:58.679406  HOST -> DISCONNECT
12:36:58.682218  handshake complete
```

UART independently logged:

```text
meta_com_id = 0
meta_com_id = 3
meta_com_id = 3
meta_log_disable = 1
[BLDR] DISCON...OK
[BLDR] 'METAMETA' received!
#T#USB handshake=3704
```

## META-to-LK/kernel evidence

After the handshake, UART printed a new Linux command line containing:

```text
root=/dev/mmcblk0p41
bootslot=b
```

and then:

```text
boot_linux_fdt:671: lk boot mode = 1
boot_linux_fdt:673: lk finished --> jump to linux
```

ATF kernel-entry output and userspace messages followed, including
`/bin/board_detect`, failsafe prompt text, and service messages.

This proves META_BOOT propagated through Preloader, LK, and kernel to userspace.

The preceding normal cycle showed the same root/slot but:

```text
lk boot mode = 0
```

Later cycles returned to normal `lk boot mode = 0`.

## Passive USB timeline

After `DISCONNECT`, no USB protocol writes or new-interface commands were
made. Only passive enumeration listing was collected:

```text
12:36:58.741  0e8d:2000
12:36:59.354  none
12:37:21.249  0e8d:2000
12:37:22.396  none
12:37:47.435  0e8d:0003
12:37:50.300  none
12:37:52.715  0e8d:2000
12:37:53.859  none
12:38:05.350  0e8d:0003
```

No `0e8d:202d`, ADB, or distinct Linux META gadget appeared.

## Security/reset evidence

UART printed:

```text
sboot_state = 0x1
lock_state(default) = 0x4
img_auth_required = 1
```

Authenticated modem-image loading completed. No panic, oops, watchdog-failure,
or authentication-failure message was observed at the META-to-LK transition.
A later restart/boot cycle is confirmed by fresh Preloader logs, but its exact
mechanism is unknown.

## Classification

```text
FURTHEST CONFIRMED EXECUTION STAGE:
  Linux userspace after LK META boot mode.

FIRST CONFIRMED FAILURE/ABNORMALITY:
  No expected META Linux USB gadget/PID; later reboot cycle.

META_BOOT PROPAGATED TO LK: YES
META_BOOT PROPAGATED TO KERNEL: YES
LINUX META USERSPACE REACHED: YES
POST-META RESET OBSERVED: YES; mechanism UNKNOWN
NEXT SAFEST INVESTIGATION STEP:
  Static analysis of the META-mode Linux/userspace gadget and meta_tst startup.
  If testing again, remain UART RX-only and USB-passive until a stable Linux
  interface appears.
```

## Facts, inferences, unresolved questions

Facts: the exact META exchange was accepted; Preloader logged the records and
disconnect; LK reported mode 1; kernel/userspace ran; slot/root stayed B/p41;
no 202d gadget appeared; no post-handoff protocol command was sent.

Inference: META selection and propagation are not the failure point. The
missing gadget is product-specific, userspace-related, or followed by a later
reboot.

Unresolved: whether another META PID is used, whether `meta_tst` starts and
fails before enumeration, and whether the later restart is watchdog,
intentional reboot, or userspace failure.

## Hashes

Complete hashes are in
`analysis/live_meta_uart/20260918T122836Z_attempt3/SHA256SUMS.final`.

Raw UART SHA-256:

```text
bf23e560e8b937ceb967535ed908896707b0e873f0a9f94125a956f5a3b741f1
```

