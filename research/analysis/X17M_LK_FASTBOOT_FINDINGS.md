# X17M LK / fastboot static findings

Date: 2026-09-17

## Conclusion

The fastboot implementation in both X17M LK partitions belongs to the separate
`aee_lk` crash-dump payload. It is not a conventional Android flashing
fastboot implementation. Static evidence supports a small query/reboot/MRDUMP
command surface, with no compiled-in `download:`, `flash:`, `erase:`,
boot-image, or unlock command tokens.

LK fastboot remains worth a controlled, read-only enumeration test, but it is
unlikely to provide partition read/write or slot switching. Its useful roles
are identifying the AEE entry route, collecting safe `getvar` results, and
confirming whether the OEM left the MRDUMP USB path reachable.

## Image layout

The GPT contains two 1 MiB signed LK containers:

- `lk_a`, partition 24, SHA-256
  `c19d64b7e41766aeee05ae394436a4537197e4876f5aba28e257bc7325050baf`
- `lk_b`, partition 37, SHA-256
  `fc8b60a9c1b4f46b97876d8d44c7f07c94811c2faba713e4152f0088cfcd512c`

Each container has signed subimages for normal `lk`, certificate objects,
`aee_lk`, and `lk_main_dtb`. In slot A, normal `lk` starts at
`0x00000000` (payload size `0x48f88`), `aee_lk` starts at
`0x0004a010` (payload size `0x45738`, load address `0x43000000`), and
`lk_main_dtb` starts at `0x000907d0`.

The fastboot strings and command table occur only in `aee_lk`. Normal LK
contains MRDUMP setup and reserves `aee_lk`, but does not contain the
fastboot command engine.

UART independently confirms the separation. Normal boots reserve
`0x43000000`–`0x431fffff` as `aee_lk`, while ATF transfers ordinary boot
to LK at `0x44000000`. Both captures report `abnormal_boot: 0x0` and later
`lk boot mode = 0`, then boot Linux normally.

## Command surface

Both slot images contain these fastboot command tokens:

- `getvar:`
- `reboot`
- `reboot-bootloader`
- `reboot-fastboot`
- `continue`
- `set_active:`
- `oem mrdump`

`set_active:` is a stub whose response is exactly
`set active slot: not supported!`.

Both complete images lack `download:`, `flash:`, `erase:`,
`flashing unlock`, `flashing lock`, `oem unlock`, and `oem lock`.
The engine logs a `download_base` and advertises `max-download-size`, but
that is generic fastboot framework state, not evidence of a registered
download or flash handler.

Visible `getvar` names are `max-download-size`, `product`
(`evb6890v1_64_cpe_emmc`), `serialno`, `is-userspace`, and `all`.
No fastboot lock-state gate is relevant because no storage-writing fastboot
command is present. Secure boot still governs normal image loading, but this
endpoint is limited by its command surface before lock policy matters.

## USB identity and entry path

The AEE payload contains USB VID:PID `0e8d:201c`, with manufacturer/product
strings `MediaTek` and `Android`. A passive capture should watch for this
identity, distinct from the observed BootROM/preloader identities
`0e8d:0003` and `0e8d:2000`.

The fastboot thread blocks in `wait_for_enter_fastboot()` until
`notify_enter_fastboot()` signals it. That signal is associated with the
MRDUMP USB output path, not ordinary boot selection. Nearby AEE code contains
`mrdump_detection`, `mrdump_run`, `mrdump_usb_output`, `oem mrdump`,
and MRDUMP exception types including `KERNEL-PANIC`, `MANUALDUMP`,
`MRDUMP_KEY`, and hang-detect.

The embedded DTB supplies a reboot-mode register at `0x10007024` with
`mode-bootloader = 3`, `mode-recovery = 2`, and `mode-download = 9`.
It also enables `mrdump_ext_rst` on interrupt 8 / GPIO 0. Tozed GPIO keys on
GPIO 7 and GPIO 20 belong to the Linux `tz_gpio_keys` driver; there is no
static evidence that either key selects LK fastboot.

The root filesystem includes MediaTek's `mrdump_tool`. Its read-only queries
are:

```text
mrdump_tool is-supported
mrdump_tool status-get
mrdump_tool status-log
mrdump_tool output-get
mrdump_tool dump-type-get
mrdump_tool mrdump-key-get
mrdump_tool dram-info
```

It can also mutate MRDUMP configuration with `output-set usb`,
`mrdump-key-set enable`, and `timeout-set`. Those commands were not run.

## Safe next experiment

On a booted unit, first run only the read-only `mrdump_tool` queries above
and preserve UART output. Do not run `status-clear`, `output-set`,
`mrdump-key-set`, `timeout-set`, or a crash trigger.

If a non-mutating OEM entry route is later proven, monitor USB and UART for
`0e8d:201c`. Once enumerated, limit the host to:

```text
fastboot devices
fastboot getvar product
fastboot getvar serialno
fastboot getvar is-userspace
fastboot getvar max-download-size
fastboot getvar all
```

Do not send `oem mrdump`, reboot commands, `continue`, or `set_active`
during initial characterization. The expected outcome is a diagnostic AEE
endpoint, not a recovery flashing interface.
