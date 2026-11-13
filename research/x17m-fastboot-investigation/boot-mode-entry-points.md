# Boot-mode entry points

No entry method was exercised during this investigation.

| Candidate | Evidence/status | Boundary |
|---|---|---|
| Preloader `FASTBOOT` selector | **PROBABLE** entry candidate; exact NAND strings and older eMMC instruction/source correlation | Changes boot flow; requires separate approval |
| ADB `reboot bootloader` | **CONFIRMED** daemon accepts reboot service; **PROBABLE** reboot-reason route; final LK destination **UNKNOWN** | Reboots and may update retained reason state |
| ADB `reboot fastboot` | **CONFIRMED** generic target-string forwarding; Fastboot-specific destination **UNKNOWN** | Reboots; no evidence of userspace fastbootd |
| Reset held during power-up | **UNKNOWN** | May reset configuration or select crash behavior |
| UART LK command/menu | **UNKNOWN**; existing interactive prompt is Linux preinit/failsafe | Do not send keys as a discovery technique |
| MRDUMP key/reset interrupt | **CONFIRMED** DT/code machinery; physical mapping and conditions **UNKNOWN** | Can trigger crash/reset; not a safe entry procedure |
| misc/environment flags | **CONFIRMED** slot metadata and reboot-fastboot misc-write machinery; safe mode-setting API **UNKNOWN** | Persistent modifications prohibited |

## Preloader selector

**CONFIRMED, NAND bytes:** `FASTBOOT` at `0x72040`, acknowledgment `TOOBTSAF` at `0x72049` in the verified preloader; see term scan. **CONFIRMED, older eMMC analysis:** dispatcher at runtime `0x002188f0..0x00218c70` compares selectors, and the source-correlated FASTBOOT case sends the acknowledgment and assigns a boot-mode value. The source match is described in `X17M_PRELOADER_SOURCE_CORRELATION.md`; that address must not be reused as a NAND address.

**PROBABLE:** the NAND selector implements the same RAM boot-mode assignment. **UNKNOWN:** successful FASTBOOT selection on any reviewed live capture, subsequent normal/AEE LK choice, and USB enumeration after it.

The reviewed `work/fastprobe.log` reports no preloader in its observation window; `fastprobe2.log` and `combined.log` only show waiting. No successful `TOOBTSAF` transaction is preserved there. Script existence and comments claiming RAM-only behavior are not experimental proof.

A proposed selector transaction must be reviewed against the exact preloader build:

```text
existing natural/authorized boot -> 0e8d:2000 -> receive READY
host sends exactly FASTBOOT (8 bytes)
target acknowledgment TOOBTSAF
then observe UART and USB only
```

**Important correction:** the related SDK FASTBOOT branch does not call the META `wait_for_discon()` helper. Existing local scripts append `DISCONNECT`, copied from META. That extra transfer is not justified for FASTBOOT and should not be used without exact-build evidence. No selector script was run or edited here.

## ADB path traced in the extracted vendor daemon

**CONFIRMED:** `rootfs.original/sbin/adbd_usb` is stripped AArch64 ELF. `reboot:` occurs at file `0x13a98`. At `0xe658..0xe66c`, service dispatch compares the seven-byte prefix. At `0xe928`, it takes the suffix `name+7`, duplicates it, and selects callback `0xd848` through GOT entry `0x28e70` (ELF RELATIVE relocation).

**CONFIRMED:** callback `0xd848` invokes syscall 142 with Linux reboot magic values, command `0xa1b2c3d4` for a nonempty suffix, and that suffix as argument. Thus `bootloader` and `fastboot` are passed to Linux as restart targets. This daemon path does not prove an Android property service or init-based powerctl flow. [Disassembly](evidence/adbd-reboot-disassembly.txt).

**CONFIRMED:** LK DT has `mode-bootloader=3`, and has no `mode-fastboot` property. **PROBABLE:** a matching Linux syscon reboot-mode driver can encode the bootloader reason. The upstream driver writes the mapped value through regmap; it does not establish the vendor kernel's exact behavior. [Linux source](https://raw.githubusercontent.com/torvalds/linux/master/drivers/power/reset/syscon-reboot-mode.c). **UNKNOWN:** the currently running daemon binary, bound kernel reboot-mode driver and final bootloader interpretation. A target string without a configured mapping can fall back to an ordinary restart.

## Buttons, persistent flags and recovery

**CONFIRMED:** the LK DT includes an enabled `mrdump_ext_rst` interrupt node and code supports MRDUMP key configuration. **UNKNOWN:** physical GPIO/pad mapping, whether it is the case reset button, its polarity/timing, and safe use. No board photograph with an established Fastboot pad mapping was located in the reviewed research. No pin identification is inferred from EINT0 alone.

**UNKNOWN:** an interactive LK shell, diagnostic menu or Fastboot UART command. `starting app` and OpenWrt `Press [f]` are not LK command prompts. Recent logs show Linux failsafe acknowledgment but no shell on a rootfs missing `/dev`; this supersedes older blanket claims that UART never accepts input, without establishing bootloader control.

**CONFIRMED:** `reboot-fastboot`'s LK handler has misc access/write machinery; it must not be treated as read-only because of its name. No `setenv`, `fw_setenv`, devmem, misc writer or boot-control helper should be invoked. A/B priorities at misc+`0x800` select banks, not proof of a Fastboot flag. No persistent flag edit is proposed.
