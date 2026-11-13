# X17M 1 GB variant — USB observation

Capture: `analysis/live_usb/x17m-usb-20260917-060434/`  
Scope: passive host observation; no MTK protocol bytes were sent.

The separately connected smaller-capacity (reported “1 GB”) bootlooped unit
enumerated with the same two MediaTek identities seen on the 8 GB unit:

- `0e8d:0003` — BootROM-compatible identity, CDC ACM interface, no USB strings.
- `0e8d:2000` — `MediaTek / MT65xx Preloader`, CDC ACM interface.

The capture recorded 12 BootROM product events and 24 preloader product events
across repeated connect/disconnect cycles. Kernel logs show the device reaching
`0e8d:0003` at 06:04:49 and then `0e8d:2000` at 06:04:55; a later preloader-only
appearance occurred at 06:06:33. No storage or reset operation was performed.

## FACTS

The 1 GB unit exposes the same apparent BootROM/preloader USB recovery path as
the 8 GB unit. This establishes interface similarity only; hardware code,
target-security bits, eMMC size, GPT geometry, and DA policy remain unqueried.

## BootROM target-config result

On reconnect, the reviewed minimal client connected to `0e8d:0003` and sent
only `a0 0a 50 05 fd d8`. The unit returned hardware code `0x0992`, target
configuration `0x000000e5`, and status `0x0000`.

Decoded flags are identical to the tested 8 GB unit: SBC enabled, SLA disabled,
DAA enabled, root-certificate-required bit clear, memory-read authentication
enabled, memory-write authentication enabled, and command `0xC8` blocked.
No DA, payload, memory, storage, reset, or slot command was sent.

Evidence: `analysis/live_usb/x17m-target-config-20260917-061413.json`, SHA-256
`fe0bef7ce9a1d4c4622478f0016ddd511ea1a72fd45dd6f9e5181c6e393d68a2`.

## NEXT SAFE TEST

Do not upload the X28 DA to this unit: its matching DAA policy and the earlier
8 GB rejection make unsigned-DA compatibility unlikely. Any future recovery
work must first locate an OEM-authenticated DA or a specifically validated
0x0992 preloader/BROM method.
