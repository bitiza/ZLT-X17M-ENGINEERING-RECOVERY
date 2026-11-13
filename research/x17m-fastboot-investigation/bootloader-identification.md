# Bootloader identification

## Evidence-backed chain

**CONFIRMED, platform identity:** historical device evidence reports MT6890 (`mediatek,mt6890`, `evb6890v1_64_cpe`, gem6xxx), four Cortex-A55 cores, Linux 5.4.238 AArch64, vendor OpenWrt 21.02.7 userspace. The USB hardware code is `0x0992`; that is not a second SoC identification. Sources: feasibility hardware report; `analysis/X17M_USB_ENUMERATION_FINDINGS.md` (snapshots in `evidence/prior-reports/`).

**CONFIRMED, captured stages:** prior UART records show MediaTek preloader loading/verifying `tee_b` ATF and `lk_b`, then ATF and LK, then Linux. This strengthens the earlier feasibility report's partition-based inference. `evidence/uart_combined.log` has `tee_b ... atf`, `lk_b ... cert vfy`, load to physical `0x44000000`, and LK application starts. It reports a December build; it must not be treated as an execution trace of the September backup.

```text
SoC BootROM -> MediaTek preloader -> trusted platform firmware/ATF
                                  -> normal Little Kernel -> Linux boot image -> preinit/procd
                                  -> embedded aee_lk (exception path; exact trigger unresolved)
```

**CONFIRMED, September artifact:** 32-bit ARM startup instructions and Thumb-2 bodies occur in normal and AEE LK. Linux is 64-bit; that does not make LK AArch64. Normal LK uses virtual addresses around `0x84000000`; AEE uses `0x83000000`. Normal startup performs relocation to physical `0x44000000`. Preloader analyses identify ARM Thumb code and MT6890 source paths. **NOT SUPPORTED:** U-Boot as the executable OS bootloader in the analyzed LK partition. `uboot_a/b` strings in preloader are generic partition aliases, not evidence of an installed U-Boot command shell.

## Verified NAND artifacts

| Region | Size | SHA-256 |
|---|---:|---|
| preloader | 4 MiB | `5152173ee3f604dcd65edaa199812703f97acd391cb7a0d9c27ab9a5568567f5` |
| preloader_backup | 2 MiB | `d74f5ea5ce12b4d8a4cd211a0e917deadd77ccf9bc363965f12b3d5581722fa5` |
| lk_a and lk_b | 2 MiB each | `a757f40b3c7da58167c56cde10728768196f42e53a8c10c49e6de97fd9ef1b5e` |

Recomputed hashes confirm identical LK banks. The earlier recovery-surface report says preloader payloads match with physical-header fields differing; differing full-partition sizes/hashes alone do not imply different code.

**CONFIRMED:** LK has MediaTek container headers, not ELF headers. [lk-containers.json](evidence/lk-containers.json) records:

| Name | Header offset | Payload start | Payload size |
|---|---:|---:|---:|
| lk | `0x0` | `0x200` | `0x449e8` |
| aee_lk | `0x45a70` | `0x45c70` | `0x40078` |
| lk_main_dtb | `0x86b70` | `0x86d70` | `0x1997a` |

Certificates follow the executable payloads and DTB. Their presence is not by itself evidence that the SoC enforces them. The DTB magic begins at `0x86db0`, after a 64-byte wrapper. Build source strings identify `app/fastboot/fastboot_entry.c`, `app/gem_boot/meta.c`, and platform AEE code. **UNKNOWN:** exact LK commit, toolchain, and complete build configuration. The preloader build time must not be attributed to LK.

## Banks and boot modes

**CONFIRMED:** vendor `bootctrl.sh` uses `misc` offset `0x800` and per-slot priority/retry/success/update bytes. Its selector helper compares priorities. LK contains boot-control/storage machinery. **PROBABLE:** this metadata drives the product's boot-bank selection. **UNKNOWN:** complete deployed LK retry/fallback state machine across reset causes. Bank selection and Fastboot mode are separate concerns.

**CONFIRMED:** the extracted LK DT declares reboot reasons in WDT/syscon offset `0x24`, mask `0x0f`: recovery `2`, bootloader `3`, meta `7`, download `9`, pcie `10`. These register reason values are not necessarily the same enum values as LK boot mode. **UNKNOWN:** whether every declared mode works on this board and kernel build.

**CONFIRMED:** META userspace consumes `chosen/atag,boot`; it does not inherently select a separate recovery rootfs. Linux has normal and META USB profiles. **UNKNOWN:** an independent Android recovery system or general bootloader menu. No recovery partition or reset-button sequence has been established as a usable independent rescue channel.

The eMMC comparison in [8gb-comparison.json](evidence/8gb-comparison.json) has different LK hashes and offsets. Its A/B images are not identical. No cross-variant bootloader compatibility is inferred.
