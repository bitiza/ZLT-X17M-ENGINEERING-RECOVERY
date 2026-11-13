# LK / META / fastboot

> **Status: static phase substantially complete (2026-10-20 revision). The LK fastboot
> capability is now statically characterized from the verified NAND A/B backup and
> corroborated on the eMMC variant; live entry/activation remains unverified.**
> Primary evidence: [`research/x17m-fastboot-investigation/`](../research/x17m-fastboot-investigation/README.md).

## Established so far

### Two fastboot engines in the NAND LK partition

**FACT — normal LK contains an executable fastboot dispatcher.** The verified
September 2025 NAND LK (2 MiB partition, offsets below are file offsets) registers
commands through a real linked-list registration routine at `0x2ca4` (command
pointer, length, handler), not through unused string vocabulary:

| Registration call | Command | Handler |
|---:|---|---:|
| `0x33e2` | `getvar:` | `0x354a` |
| `0x33f6` | `reboot` | `0x35ce` |
| `0x340a` | `reboot-bootloader` | `0x35f2` |
| `0x341e` | `reboot-fastboot` | `0x361c` |
| `0x3432` | `continue` | `0x36e4` |
| `0x3446` | `set_active:` | `0x36d8` |

It also publishes fastboot variables (version `0.5`, `max-download-size`,
product `evb6890v1_64_cpe`, `serialno`, `is-userspace`). These are published
metadata; `max-download-size` and `download_base` are **not** evidence of a
data-download command.

**FACT — `set_active:` is a refusal stub.** Its handler loads a failure string
and branches to the failure response. It is not a working slot switch.

**FACT — no firmware-flashing command surface.** `download:`, `flash:`,
`erase:`, `upload:`, `fetch:`, and `flashing unlock`/`oem unlock` tokens are
absent from both NAND LK copies, and the recovered registration sequence has no
such handlers. This is strong bounded evidence against standard fastboot
flashing, not a proof that every opaque vendor command is impossible. For
contrast, a public MediaTek LK explicitly registers download/flash/erase in its
`fastboot_init`; those registrations cannot be imported into X17M conclusions.

**FACT — AEE LK is a second fastboot engine.** The embedded AEE image contains a
second command-registration sequence, an `oem mrdump` diagnostic extension, and
the only fully decoded USB transport:

- compiled USB identity `0e8d:201c`, interface class/subclass/protocol `ff/42/03`;
- bulk endpoints `0x82`/`0x02`, 512-byte packets, UDC initialization code present;
- `usb_register_fastboot_controller_interface` in a linked init record.

The older claim that fastboot in this device is exclusively AEE/MRDUMP was **too
broad**: normal LK also contains a command engine. The AEE transport is the only
directly decoded USB implementation; normal-LK transport reachability is
unresolved.

**FACT — eMMC variant corroborates.** The 8 GB eMMC ZIP's `lk_a`/`lk_b` are
non-identical, both contain `getvar:` and `oem mrdump`, and neither has
`download:`/`flash:`/`erase:`.

### Activation and reachability

**FACT — the fastboot app waits, then Linux boots.** The normal entry path
prints a wait message, waits on an event object, and only then performs command
registration and transport dispatch. A prior live UART capture records:

```text
starting app fastboot
wait_for_enter_fastboot:90: Wait for enter fastboot event...
starting app gem_boot
...
boot_linux_fdt:671: lk boot mode = 0
```

A waiting task is not an active USB service. No reviewed log shows an active
fastboot endpoint or a successful event handoff.

**FACT — preloader `FASTBOOT` selector exists.** The verified NAND preloader
contains the eight-byte selector `FASTBOOT` with acknowledgment `TOOBTSAF`.
No live capture shows a completed transaction. The leading candidate transaction
is `0e8d:2000 → READY → FASTBOOT (8 bytes) → TOOBTSAF → observe`. **Correction to
local tooling:** the related SDK FASTBOOT branch does *not* send the META
`DISCONNECT` transfer; existing probe scripts that append it are unjustified for
FASTBOOT.

**FACT — an ADB reboot path exists.** The extracted vendor `adbd_usb` forwards
`reboot bootloader`/`reboot fastboot` suffixes to the Linux reboot syscall; the
LK device tree declares `mode-bootloader=3` and has no `mode-fastboot` property.
The final LK interpretation is unobserved, and a target string without a
configured mapping can fall back to an ordinary restart.

### Security attribution

**FACT — boot/download security is separate from fastboot gating.** SBC/DAA and
the observed DA rejections (`0x7017` BROM, `0x7024` preloader) and boot-image
certificate verification operate at other stages. DAA does **not** explain the
absence of a fastboot endpoint, and absence of flash/download support is a
compiled capability limit, not evidence of an Android lock state.

**UNRESOLVED —** Android-style lock state, any fastboot-specific authentication,
and the exact event-gating policy.

### META and MRDUMP inside LK

**FACT —** AEE LK links an `oem mrdump` command extension (diagnostic dispatch,
not arbitrary storage access), and the LK device tree includes an enabled
`mrdump_ext_rst` interrupt node with MRDUMP key-configuration support. The
physical key/pad mapping and safe trigger conditions are unknown. No interactive
LK shell or UART command menu has been established; `starting app` and OpenWrt
`Press [f]` prompts belong to other stages.

## Why LK still matters

For a device that reaches LK but has no usable Linux network/ADB/Telnet/web UI,
an LK fastboot or `oem mrdump` path would be the last software recovery surface
before the BootROM/Preloader DA domain. Current evidence limits what it could
offer even if entered: diagnostics and reboot control, **not** image flashing.

## Investigation goals (remaining)

1. Demonstrate or refute a live entry path (preloader `FASTBOOT` selector,
   ADB reboot reason, MRDUMP key) end to end;
2. Resolve the normal-LK USB transport/controller path (or its absence);
3. Determine whether `0e8d:201c` ever enumerates on this hardware;
4. Map `oem mrdump` handler capabilities in detail;
5. Confirm whether the December bench build's LK matches the September artifact
   whose static analysis is summarized here.

The proposed lowest-risk live step is passive current-state inspection
(`adb devices -l`, `lsusb -t`, `fastboot devices -l`, descriptor reads, bounded
ADB state reads) — see [`safe-verification-plan.md`](../research/x17m-fastboot-investigation/safe-verification-plan.md).
Any selector, reboot, or reset test requires separate approval and a tested
rollback plan.

## Evidence rule

An internal load/read/write function is not a recovery interface by itself. A
recovery surface is established only when a host-controlled path to that
function is demonstrated or statically proven. A confirmed command registration
is a capability statement, not a recovery path.

## UNRESOLVED

Live entry, live endpoint exposure, normal-LK transport, and the December-build
artifact match remain open. The static investigation is complete enough to state:
**limited fastboot is compiled in, wait-state activated, diagnostics-oriented,
and not a firmware-flashing recovery surface in either storage variant.**
