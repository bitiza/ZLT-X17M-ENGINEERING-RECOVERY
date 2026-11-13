# 8 GB UART debug-level attempt

Source: `CoolTerm Capture 2026-10-09 00-48-26.txt` (filename uses host-local
time; no per-line timestamps establish the capture duration).

Size: 133611 bytes. SHA-256: `3651f8d3913e815d42c9a869586d810a54e6ae80e899fba8abf24a80ff83c7f3`.
Source preserved unchanged.

## Observations

- One `lk boot mode = 1` handoff, slot B, root `/dev/mmcblk0p41 rootwait`.
- Linux userspace reaches board_detect and the failsafe/debug prompt.
- Three `lock: applet not found` messages, two `netmsg: applet not found`
  messages, and one `/etc/preinit: line 18: uci: Structure needs cleaning`.
- A standalone 4 is present before the prompt; further 4 lines and one 44
  appear afterward. These are not an acknowledgment that debug level was set:
  terminal/device echo and queued input are not command results.
- No `- failsafe -`, `Restore nothing`, `Start USB`, `Check BootMode`,
  `procd`, or `meta_tst` strings; no second LK mode-1 handoff in the capture.

## Interpretation

This attempt did not reveal additional downstream startup output or an
interactive shell. Debug-level acceptance is unconfirmed. Normal preinit
completion, procd startup, and USB/META service execution remain unconfirmed.
The finite three-lock-error pattern differs from the previously recorded
explicit failsafe lock flood. Do not diagnose the normal boot as that loop.
The uci error is a filesystem-related clue; its affected object and cause
remain unknown. Lack of a timed second boot does not establish that the
device will never reset. No storage changes or live host communication were
performed in this analysis.

## Practical outcome

No new recovery entry point was demonstrated. Further repetitions of f/4
without additional instrumentation are unlikely to resolve startup location.
Preserve this evidence; next offline work is correlating the exact 8 GB
preinit/overlay state with the uci failure and startup before USB setup.
