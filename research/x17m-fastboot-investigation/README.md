# ZLT X17M Fastboot investigation

Date: 2026-10-20. Completed offline capability assessment; live entry remains unverified.

**CONFIRMED:** the verified 1 GiB NAND LK A/B backup contains executable Fastboot command registration in both normal LK and its embedded AEE LK. The AEE image includes a USB transport configured for `0e8d:201c`, interface `ff/42/03`. **UNKNOWN:** a successful entry mechanism and a live compatible endpoint on the current router. **NOT SUPPORTED:** conventional Fastboot firmware flashing in these analyzed images.

No router was contacted, rebooted, reset, switched, patched, or flashed during this investigation. All new writes are host research artifacts in this directory. Existing scripts that send selectors, probe memory, or start MTKClient were inspected, never executed.

## Reports

1. [Bootloader identification](bootloader-identification.md)
2. [Static Fastboot evidence](fastboot-static-analysis.md)
3. [Boot-mode entry points](boot-mode-entry-points.md)
4. [USB protocols](usb-protocol-analysis.md)
5. [Security restrictions](security-restrictions.md)
6. [Proposed safe verification](safe-verification-plan.md)
7. [Recovery risks](recovery-risk-assessment.md)
8. [Final verdict: ten explicit answers](final-verdict.md)

## Scope and provenance

The requested feasibility project was located at `/home/kali/Desktop/bozax17/openwrt-port-feasibility/`; all four requested reports were read. Their snapshots and selected earlier research are in [evidence/prior-reports](evidence/prior-reports/). The verified NAND artifacts are under `/home/kali/Desktop/bozax17/backups/x17m-1gb-20260921-061524/logical/`. Full paths, sizes and recomputed hashes are in [artifact-manifest.json](evidence/artifact-manifest.json).

**Do not merge hardware/build identities:** the September backup's preloader says `20250909-103520`; recent bench UART logs say `20251203-032240`. Historical 8 GB eMMC images are a third evidence set. No current-bench LK readback was obtained. A recent log demonstrating an app startup does not establish a byte-for-byte match to the backed-up LK.

Confidence labels used for major claims:

- **CONFIRMED** — direct bytes, decoded instructions, configuration, or preserved device observation; scope identified.
- **PROBABLE** — source correlation or a strongly indicated incomplete path.
- **UNKNOWN** — insufficient evidence; includes untested reachability.
- **NOT SUPPORTED** — evidence against the specified functionality in the bounded artifacts, not a universal claim about every X17M revision.

## Reproduction and evidence

From `/home/kali/Desktop/x17m`, run `python3 x17m-fastboot-investigation/scripts/analyze.py`. It reads host files only and regenerates strings, term scans, container map, candidate cross-references, disassembly, and DTB/DTS. Requires Python 3, Capstone, binutils and `dtc`. It uses explicit local backup paths. Offsets in this report are hexadecimal **file offsets in the whole LK partition**, unless explicitly marked VA.

[evidence/source-manifest.json](evidence/source-manifest.json) identifies snapshots of earlier reports, logs and extracted userspace files. These are prior-session evidence, not newly collected live observations. `thumb-string-xrefs.tsv` contains automated candidates; conclusions use the separately preserved instruction ranges and data structures. The scanner is not a complete decompiler or proof of reachability. `readelf`/`objdump` rejecting raw LK containers is expected; see `tool-output.txt`.

[evidence/SHA256SUMS](evidence/SHA256SUMS) covers deliverables and evidence at completion. No firmware images were altered. The original research is preserved; disagreements and later superseding observations are documented explicitly.
