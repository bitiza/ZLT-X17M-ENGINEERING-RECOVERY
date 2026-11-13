# Research report archive

Verbatim mirror of the local investigation workspace (`/home/kali/Desktop/x17m`),
covering reports that were not yet distilled into the numbered `docs/` chapters.
Reports keep their original names, wording, and provenance. Only mechanical
redaction was applied before upload:

- live VPN server names, account strings, and resolved exit IPs in the work log → placeholders
- real device MAC addresses (Tozed `D8:42:F7::*`, and others) → `REDACTED-MAC-nn`
- identifiers in the forensic report were already masked by the author (`8613*********77`)

Binaries, firmware dumps, archives, PDFs, third-party tool docs, and the external
`Tozed-ZLT-Firmware-Dump` clone are intentionally excluded.

## Layout

| Path | Contents |
|------|----------|
| `analysis/` | 56 investigation reports: BootROM/DAA chain, preloader META, LK, eMMC unbrick, 8 GB busybox failure reconstruction, forensic report, other ZLT firmware findings |
| `x17m-fastboot-investigation/` | 2026-10-20 static fastboot capability assessment of the LK A/B backup (9 reports + text evidence + analysis script). Key verdict: fastboot command registration exists in both LK containers, but no confirmed live entry/flash path |
| `work/BENCH.md` | Bench manual for one-test-per-power-cycle USB/boot-mode probing |
| `diff-x17m-info/` | Identity/OpenWrt info captured from three other X17M variants (2/4/5) plus dmesg, for cross-variant comparison |
| `X17M_1GB_*.md` | Early 1 GiB findings: factory META boot chain, preloader/LK recovery surface, live META characterization |
| `WORK_LOG_XRAY_SMS_FLASH.md` | 2026-11-06 work log: XRAY proxy failover testing, SMS flash/root behavior, xray 26.7.11 upgrade (sanitized) |

## Relationship to `docs/`

- `docs/08-lk-meta-fastboot.md` predates the 2026-10-20 fastboot investigation;
  the reports under `x17m-fastboot-investigation/` supersede it and should be folded
  into a future revision.
- `analysis/X17M_RECOVERY_AUDIT_20261020.md` is the master live audit of the bricked
  1 GiB NAND unit and complements `docs/09-recovery-decision-tree.md`.
- The Oct-08 dialer replacement / RNDIS bridge / failsafe reports extend
  `docs/12-cellular-modem-and-ccci.md` observations.
- The 8 GB busybox failure reports provide the eMMC-side counterpoint to
  `docs/11-nand-variant.md`.
