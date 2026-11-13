# Evidence guide

Artifacts were analyzed on the host on 2026-10-20. No live-device probe was performed.

- `artifact-manifest.json`: full absolute paths, recomputed SHA-256 and sizes for four verified NAND bootloader regions and other local preloader candidates. The verified NAND LK copies match.
- `source-manifest.json`: hashes and original paths for snapshots of prior reports, prior-session logs and extracted vendor userspace. A saved log is evidence of its contents, not proof that all observations used the same router/build.
- `lk-containers.json`: decoded header offsets, names and sizes. Headers with magic `88 16 88 58` contain 32-byte names and payload size at +4; payload starts after a 512-byte header.
- `*.strings.txt`: printable ASCII runs of at least four characters with hexadecimal file offsets. This is a reproducible Python equivalent of an offset-bearing strings scan, not a symbol table.
- `term-scan.txt`: bytewise case-insensitive scan; negative results explicitly say ABSENT.
- `thumb-string-xrefs.tsv`: candidate MOVW/MOVT constructions and relative references. An automated candidate can cross a clobber/data boundary; inspect instructions before treating it as a genuine use. File coordinates make relative references relocation-independent.
- `lk-main-disassembly.txt`: registration helper, event wait, direct command registrations and set_active stub. Normal VA = `0x84000000 + file_offset - 0x200`.
- `lk-aee-disassembly.txt`: AEE entry/registration sequence. AEE VA = `0x83000000 + file_offset - 0x45c70`.
- `usb-init-disassembly.txt` and `usb-structures.txt`: AEE UDC initialization and vendor/product/interface/extension table bytes. A complete serialized descriptor scan is empty because internal gadget structures are used.
- `adbd-reboot-disassembly.txt` and `adbd-elf.txt`: reboot-service dispatch, callback and ELF relocations. Code segment file offsets equal ELF relative virtual addresses here. Syscall 142 is AArch64 reboot; `0xfee1dead`, `0x28121969` are the reboot magic values and `0xa1b2c3d4` is RESTART2.
- `lk-main.dtb/.dts`: extracted embedded DTB at parent file `0x86db0`, total size `0x1993a`; DT compiler warnings are retained separately. Warnings about unrelated bus bindings do not make this a deployable device tree.
- `8gb-comparison.json`: hashes and bounded string scan from the supplied eMMC ZIP, distinct from NAND. It was read directly through Python zipfile; no archive was written back or firmware flashed.
- `prior-reports/`: requested feasibility reports and selected older research. Original locations remain unchanged.
- `uart_*.log`, `fastprobe*.log`, `combined.log`: snapshots of pre-existing work files, not experiments by this investigation.

Reproduction: from `/home/kali/Desktop/x17m`, run `python3 x17m-fastboot-investigation/scripts/analyze.py`. It regenerates the static analysis outputs, not historical report/log snapshots. Snapshot provenance is in `source-manifest.json`. The eMMC ZIP comparison can be reproduced by opening the named ZIP members, SHA-256 hashing their uncompressed contents and finding the literal terms enumerated in its JSON. No need to extract the 7.8 GB full-disk backup: equivalent boot-stage partitions are available and named/hash-identified.

Historical full backup ZIP and other vendor images were inventoried but not expanded indiscriminately. Earlier preloader disassembly/source work and MTKClient live experiments were reviewed rather than repeated. Public SDK source paths under old `/tmp` extraction locations are historical references; their availability today is not assumed.

External primary references checked on 2026-10-20:

- [AOSP Fastboot protocol](https://android.googlesource.com/platform/system/core/+/master/fastboot/README.md): protocol/transport distinctions, getvar semantics.
- [Android Fastboot USB interface requirements](https://android.git.googlesource.com/platform/bootable/libbootloader/+/9bb23ceb380d4b73068151ddd16b32cef267f4f0/gbl/docs/GBL_EFI_FASTBOOT_USB_PROTOCOL.md): class/subclass/protocol; indexed excerpt available, full-page fetch timed out.
- [MTKClient USB IDs](https://raw.githubusercontent.com/bkerler/mtkclient/main/mtkclient/config/usb_ids.py): BROM/preloader VID/PID interpretation. This is tool-maintainer source, not a MediaTek specification.
- [Linux syscon reboot-mode driver](https://raw.githubusercontent.com/torvalds/linux/master/drivers/power/reset/syscon-reboot-mode.c): generic register-based reason encoding, not proof of the vendor kernel's binding.
- [Public MediaTek LK implementation](https://github.com/dguidipc/gemini-lk/blob/master/lk/app/mt_boot/fastboot.c): contrast with explicit flash/erase/download registrations. Different device/generation; no compatibility inference. The source is the implementation repository, not an X17M vendor release.

`SHA256SUMS` covers reports, scripts and evidence except itself and transient Python bytecode. Regenerating outputs requires regenerating the checksum file. Paths in the checksum file are relative to the research directory.
