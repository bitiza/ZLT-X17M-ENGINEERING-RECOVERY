# ZLT X17M Engineering Recovery

Engineering notes, protocol analysis, and recovery research for the MediaTek MT6890-based ZLT X17M.

This repository documents a read-only-first investigation of recovery paths for devices that still reach BootROM/Preloader/LK but have damaged Linux rootfs, overlay, or networking/userspace. The emphasis is on separating **proven behavior** from **inference**, and on avoiding destructive operations until the boot/storage state is understood.

> **Status:** work in progress. The LK fastboot static phase is complete (2026-10-20); live entry/activation remains the open item.

## Scope

Two storage variants are now directly characterized and must be treated separately:

- **NAND reference:** MediaTek MT6890 family, 1 GiB raw NAND, 4 KiB page / 256 KiB eraseblock, MTD/UBI/JFFS2.
- **eMMC reference:** MediaTek MT6890 family, 7,818,182,656-byte user area (15,269,888 × 512-byte sectors), 50 GPT partitions, plus separate 4 MiB boot0 and boot1 hardware areas.

Both use A/B firmware naming and OpenWrt-based userspace, but offsets, sizes, storage semantics, and recovery procedures must not be assumed interchangeable. The characterized eMMC sample reports model `33BGAX` and boots slot A from `/dev/mmcblk0p28`.

## Recovery model

```text
BootROM
   |
   +-- Download Agent path
   |      \-- DAA protected
   |
   v
Preloader
   |
   +-- META boot selector
   +-- A/B boot control
   +-- authenticated image loading
   |
   v
LK
   |
   +-- META / boot-mode handling      <-- static analysis done; live entry unverified
   +-- AEE / MRDUMP
   \-- limited fastboot
   |
   v
Linux
   |
   +-- normal boot
   \-- Linux META / meta_tst
```

The central recovery question is:

> What software-accessible recovery primitive remains available when Linux is broken but BootROM, Preloader, or LK still execute?

## Established findings

- BootROM DAA and Preloader/rootfs image authentication are separate trust domains.
- The MTK SDK can generate a structurally valid `customer_da.auth`.
- The exact X17M `DA_BR.bin` contains two RSA-PSS signatures whose signing relationship was verified offline.
- A generated auth can embed the same DAA public key that verifies the DA.
- Live production BootROM still rejects the DA path before execution; no DA storage command has executed.
- Preloader META is a **boot-mode selector**, not a persistent command service.
- The SDK contains optional Preloader-as-DA `SEND_IMAGE` / `BOOT_IMAGE` commands, but the exact 2025 X17M Preloader appears to have them compiled out.
- LK contains internal image-loading code, but the currently identified fastboot endpoint lacks upload/boot/flash/erase commands.
- Linux META exposes a powerful `meta_tst` framework on a sufficiently healthy boot, but is unavailable when userspace never reaches the USB gadget stage.
- UART on the NAND platform is a **1.8 V logic domain**. An electrically unsuitable UART adapter reproduced false NAND-initialization failures on a known-good router.
- **CCCI Baseband IPC Inviolability:** Unilateral user-space restarts of `/usr/bin/dialer` or AT injection desynchronize MediaTek T750 CCCI shared-memory queues; `x17m_external.sh` must remain a passive state reflector and modem recovery requires a full SoC reset.
- **TR-069 & TR-369 Stacks:** Completely removable (45 files, ~7.25 MiB raw pruned) without impacting cellular baseband operation or carrier APN negotiation, fully remediating CVE-2026-2035703.
- **Vendor Script Remnants:** Vendor rootfs contains multi-generational artifacts (hardcoded Linux 4.4 modules in `sip_alg.sh`, missing `/usr/bin/cron_master`, missing `thermal_intf`, and dormant JD Logistics `jingdongwuliu` services).
- **VoIP Quality of Service:** WhatsApp and real-time voice calls require unblocked UDP forwarding and DSCP `EF` (`0x2e`) prioritization in `mangle` to bypass cellular bufferbloat while retaining strict `XRAY_DNS` redirection.

## Documentation

1. [Boot chain overview](docs/01-boot-chain.md)
2. [BootROM and DAA](docs/02-bootrom-daa.md)
3. [Download Agent authentication](docs/03-download-agent-authentication.md)
4. [Preloader META](docs/04-preloader-meta.md)
5. [A/B boot control](docs/05-ab-boot-control.md)
6. [Preloader recovery surfaces](docs/06-preloader-recovery-surfaces.md)
7. [Linux META](docs/07-linux-meta.md)
8. [LK / META / fastboot](docs/08-lk-meta-fastboot.md) — revised 2026-11-13
9. [Recovery decision tree](docs/09-recovery-decision-tree.md)
10. [eMMC variant notes](docs/10-emmc-variant.md)
11. [Raw-NAND variant notes](docs/11-nand-variant.md)
12. [Cellular modem and CCCI architecture](docs/12-cellular-modem-and-ccci.md)
13. [TR-069 & TR-369 remediation (CVE-2026-2035703)](docs/13-tr069-tr369-remediation.md)
14. [Vendor scripts and middleware audit](docs/14-vendor-scripts-and-middleware-audit.md)
15. [VoIP QoS and DNS hardening](docs/15-voip-qos-and-dns-hardening.md)
16. [NAND firmware repacking and flashing](docs/16-nand-firmware-repacking-and-flashing.md)

Supplementary: [Research report archive](research/README.md) — verbatim workspace reports (recovery audit, fastboot investigation, 8 GB/eMMC failure analysis, work log, variant comparison) not yet distilled into the numbered chapters.

## Safety model

The research uses a conservative workflow:

1. identify storage type and geometry before assuming a layout;
2. dump and hash before writing;
3. keep physical routers and storage variants separated;
4. preserve device-specific calibration and identity partitions;
5. distinguish BootROM, Preloader, LK, and Linux recovery surfaces;
6. never infer NAND failure from logs captured with electrically unsafe instrumentation;
7. do not treat a successful transport handshake as proof that a write-capable recovery path exists.

Do not transplant device-specific partitions such as `nvcfg`, `nvdata`, `nvram`, `protect*`, `proinfo`, `productinfo`, `fibonv`, or security metadata between physical routers.

## Evidence convention

Technical notes distinguish:

- **FACTS** — directly observed or statically verified.
- **INFERENCES** — conclusions supported by those facts but not directly observed.
- **UNRESOLVED** — questions that still require evidence.

This is an engineering/recovery reference, not a generic one-command flashing guide.

## Current status

The DA/BootROM and Preloader META investigations are mature enough to document. The LK fastboot static phase is now complete: limited fastboot is compiled into both LK engines (diagnostics only, no flash/download), but live entry and USB endpoint exposure remain unverified — that is the open item for devices that reach LK or early Linux but have no usable network, ADB, Telnet, or web interface.

The eMMC reference now includes live GPT, boot-control, filesystem and A/B hash characterization across multiple observed production builds; full `rootfs_a` and `rootfs_b` images are still pending transfer. The raw-NAND reference now includes NAND-aware A/B acquisition results, ECC/bad-block behavior, modem-image comparison, and the experimentally reproduced 1.8 V UART instrumentation failure.
