# Static Fastboot analysis

All findings below apply to the hashed September 2025 NAND LK unless stated otherwise. Offsets refer to its entire 2 MiB partition. See [tool outputs](evidence/tool-output.txt), [strings](evidence/mtd25_lk_a.img.strings.txt), [term scan](evidence/term-scan.txt), [candidate cross-references](evidence/thumb-string-xrefs.tsv), and [disassembly](evidence/lk-main-disassembly.txt).

## Executable registrations, not just strings

**CONFIRMED:** normal LK has a real Fastboot dispatcher. File `0x2ca4` allocates a 16-byte linked-list record, stores the command pointer at +4, its length at +8, and its handler at +12. It is called with these arguments:

| Registration call offset | Command string offset | Token | Handler file offset |
|---:|---:|---|---:|
| `0x33e2` | `0x2fd1e` | `getvar:` | `0x354a` |
| `0x33f6` | `0x2fd26` | `reboot` | `0x35ce` |
| `0x340a` | `0x2fd2d` | `reboot-bootloader` | `0x35f2` |
| `0x341e` | `0x2fd3f` | `reboot-fastboot` | `0x361c` |
| `0x3432` | `0x2fd4f` | `continue` | `0x36e4` |
| `0x3446` | `0x2fd58` | `set_active:` | `0x36d8` |

The Thumb function pointer has bit 0 set; the table above gives the aligned file offset. Example:

```text
0x33d2 movw r0,#0xfb1e
0x33d6 movw r1,#0x334b
0x33da movt r0,#0x8402      ; command VA 0x8402fb1e -> file 0x2fd1e
0x33de movt r1,#0x8400      ; handler VA 0x8400334b -> file 0x354a, Thumb
0x33e2 bl   0x2ca4         ; registration routine
```

**CONFIRMED:** the `set_active:` handler at `0x36d8` loads the refusal string at `0x2fe4f` and branches to the failure-response routine. Its implementation is a stub, not a proven slot switch. Adjacent `misc`/`bio_write` strings and the separate reboot-fastboot handler do not change that result.

**CONFIRMED:** variable publishing calls at `0x349c..0x34e4` register version `0.5`, max-download-size, product `evb6890v1_64_cpe`, serialno, and is-userspace. These are published metadata, not independent commands. `max-download-size` and `download_base` are not evidence of a data-download command.

**NOT SUPPORTED:** `download:`, `flash:`, `erase:`, `upload:`, `fetch:`, and standard `flashing unlock`/`oem unlock` commands. Their tokens are absent from both NAND LK copies, and the recovered registration sequence has no such handlers. This is strong bounded evidence against standard firmware flashing, not a mathematical proof that every opaque or dynamically generated vendor command is impossible.

## Activation and reachability

**CONFIRMED, static:** the normal entry path at `0x3360` prints the wait message, waits on an event object at VA `0x84040bb0`, then reaches command registration and the transport dispatcher. `0x339c` loads the ready message. Registration occurs after the event wait, not merely because the app was started.

**CONFIRMED, prior live log:** `evidence/uart_fastprobe.log` records:

```text
starting app fastboot
wait_for_enter_fastboot:90: Wait for enter fastboot event...
starting app gem_boot
...
boot_linux_fdt:671: lk boot mode = 0
```

The recent December-preloader bench boot therefore starts the Fastboot app and continues to Linux while it waits. **UNKNOWN:** whether that boot's LK bytes match the September artifact, which precise deployed caller signals the event, and whether a FASTBOOT mode handoff signals it on this board. A waiting task is not an active USB service.

**CONFIRMED:** normal LK's default transport selector returns string `usb` (`0x2c7a`, string at `0x2fa6b`). The framework searches registered controllers and invokes their methods indirectly. **UNKNOWN:** a complete normal-LK USB-controller registration and operational enumeration path. The distinctive USB Fastboot controller initialization name and the decoded VID/PID/interface structure below belong to **AEE LK**. Do not assign AEE's USB identity automatically to the normal app.

## Embedded AEE Fastboot

**CONFIRMED:** AEE has a second Fastboot command-registration sequence (`0x4e6b0` onward; [disassembly](evidence/lk-aee-disassembly.txt)). It also contains `oem mrdump` at `0x74b65`. At file `0x82814`, the command extension table points to that string (VA `0x8302eef5`), with a following Thumb handler pointer `0x830070f9`. This establishes a linked diagnostic extension, not arbitrary storage access.

**CONFIRMED:** the AEE image includes UDC initialization and Fastboot transport state. Its USB structures and bulk endpoint creation are decoded in [USB analysis](usb-protocol-analysis.md). This is substantially stronger than a lone Fastboot string, but still does not establish a safe runtime route into AEE.

The older research describing Fastboot as exclusively AEE/MRDUMP was too broad for this NAND artifact: **normal LK also contains a command engine**. The AEE transport is the directly decoded USB implementation; normal transport reachability remains unresolved.

## Cross-variant and method limits

The separately supplied 8 GB eMMC ZIP contains non-identical `23.lk_a.img` and `36.lk_b.img`. Both have `getvar:` and `oem mrdump`, and neither has `download:`, `flash:`, or `erase:`; [comparison](evidence/8gb-comparison.json) records hashes and offsets. This is corroboration of a diagnostic design, not proof that eMMC and NAND activation paths are identical.

`file`, `readelf`, and `objdump` were run on the raw container. Capstone was used for instruction analysis; Ghidra is installed but no new Ghidra/Binary Ninja project was required. Automated MOVW/MOVT scanning can generate false candidate references across register clobbers or data. The decisive registrations, stub, event wait, syscall and USB structures were inspected directly. Full control-flow recovery of all boot/security paths remains outstanding.

For comparison, a public MediaTek LK implementation explicitly registers download, flash and erase handlers in its `fastboot_init`; those registrations cannot be imported into X17M conclusions. [Public LK source](https://github.com/dguidipc/gemini-lk/blob/master/lk/app/mt_boot/fastboot.c). The exact MT6890 selector source correlation is preserved in `evidence/prior-reports/X17M_PRELOADER_SOURCE_CORRELATION.md`; it concerns a related SDK, not a matching X17M build.
