# ZLT X17M eMMC Unbrick — Full Analysis
**Date:** 2026-09-26  
**Device:** ZLT X17M, 8 GB eMMC variant  
**SoC:** MediaTek MT6890 (hwcode 0x992)  
**Working directory:** `/home/kali/Desktop/x17m`

---

## 1. Device State

| Field | Value |
|-------|-------|
| Storage | eMMC 8 GB (JEDEC name `33BGAX`, manfid `0x0b`) |
| Active boot slot | B (`root=/dev/mmcblk0p41 bootslot=b`) |
| Boot state | Hard bootloop — reboots ~30 s after power-on |
| UART output (1.8 V) | `lock: applet not found` × 2, `netmsg × 2`, silence, reboot |
| BootROM security | SBC = enabled, DAA = enabled, SLA = disabled |

---

## 2. Root Cause

`/bin/busybox` in the **rootfs_b overlay** was replaced by a Debian BusyBox 1.37.0 static build.

| Property | Original (vendor) | Replacement (broken) |
|----------|-------------------|----------------------|
| Size | 595 744 bytes | 1 975 064 bytes |
| SHA-256 | `45859c93…` | `43db2f47…` |
| Build | musl dynamic, BusyBox 1.36.0 | glibc static, BusyBox 1.37.0 |
| Missing applets | — | `lock`, `netmsg`, `flock` |

### Why it bootloops

The OpenWRT preinit failsafe wait script (`/lib/preinit/30_failsafe_wait`) calls
`lock -w /tmp/.failsafe` in a tight loop. With `lock` gone, the call fails immediately
and loops forever. The failsafe shell (`/bin/ash`) is never reached.

### Init chain blocking meta_tst

```
kernel → /etc/preinit (pid 1, no PREINIT env) → exec /sbin/init
/sbin/init → fork /etc/preinit (PREINIT=1) → waits for /tmp/.preinit
preinit (fork) → stuck in lock loop → /tmp/.preinit never created
/sbin/init → never starts procd → meta_tst never runs
```

Even without the lock issue, the inittab has the getty line commented out
(`# console::respawn:/sbin/getty -L ttyS0 921600 …`), so no login shell
would appear on UART after a clean boot.

---

## 3. Partition Layout

50 GPT partitions on the main eMMC (`/dev/mmcblk0`):

| Partition | Node | Size | Notes |
|-----------|------|------|-------|
| misc | mmcblk0p1 | 512 KiB | A/B boot control record at +0x800 |
| rootfs_a | mmcblk0p28 | 512 MiB | Presumed intact factory image |
| rootfs_b | mmcblk0p41 | 512 MiB | **Active broken slot** |
| user_data | mmcblk0p49 | 5.6 GiB | — |

Hardware boot partitions (`/dev/mmcblk0boot0`, `mmcblk0boot1`) each 4 MiB,
hold the Preloader.

### rootfs_b internal layout

```
+0x00000000   SquashFS 4.0/xz  (read-only base, ~58 MB)
+0x03880000   ext4 overlay     (upper dir, writable, contains broken busybox)
```

---

## 4. A/B Boot Control

32-byte record at `misc (mmcblk0p1) + 0x800`:

```
+0x00  magic      \0AB0
+0x04  major ver
+0x05  minor ver
+0x08  A priority (0=unbootable, max 15)
+0x09  A retry count
+0x0A  A successful-boot flag
+0x0C  B priority / retry / successful
+0x10  CRC area (not validated by this LK)
```

Currently: **slot B has higher priority than slot A** → LK boots slot B.
`reduce_retry_count()` is compiled out — no automatic rollback after failed boots.

LK fallback: if the `\0AB0` magic is invalid or misc is unreadable, LK likely
defaults to slot A. However, writing misc requires DA auth (circular dependency).

---

## 5. Delivery Mechanisms — Status

### 5.1 DA Authentication (USB BootROM download mode)

**Status: BLOCKED**

The BootROM (DAA-enabled) requires a Preloader-signed Download Agent before
any flash operation. All attempts failed:

| Attempt | Error | Reason |
|---------|-------|--------|
| ACC-bypass DA (`DA_BR_acc_bypass_nand.bin`) | `0x7024` DAA_SIG_VERIFY_FAILED | DAA signature rejected |
| `customer_da.auth` (SDK, `9af8…` key) | `0x7009` hash association failure | Normal — no paired DA |
| `DA_BR.bin` (Quectel NAND, `9af8…` key) | `0x7017` DA signature security error | **Trust anchor mismatch** |

#### Root cause of 0x7017 — RESOLVED

The production eMMC Preloader (`mmcblk0boot0.img`, SHA `844a4ed5…`) was
extracted from a working eMMC X17M device. Key search results:

| Key | Present in eMMC Preloader | Offsets |
|-----|--------------------------|---------|
| `9af8a28b…` (open-source SDK / MTK tree) | **NO** | — |
| `a697414d…` (`dakey.h` in NAND Preloader source) | **NO** | — |
| `b5ed982c…` (cert key 1, from `rootfs_sig_a.img`) | **YES** | 0x3aa08, 0x3beec |
| `c4daa020…` (cert key 2, from `rootfs_sig_a.img`) | **YES** | 0x3c0f8 |

The Preloader trusts `b5ed982c…` / `c4daa020…` — OEM keys embedded in the
`rootfs_sig_a.img` certificate partition. The SDK-generated auth blob uses
the wrong root. **Fix requires the OEM private key from ZLT/Quectel**, or an
eMMC-specific DA already signed with one of these keys.

#### rootfs_sig_a.img certificate structure

Format: custom MTK ASN.1 (not standard X.509). OID namespace `2.16.886.2454.*`
(MediaTek, Taiwan).

```
SEQUENCE (1709 bytes)            ← outer cert
  SEQUENCE (1368 bytes)          ← main cert body
    Algorithm: sha256WithRSAEncryption
    Subject:   C=AU, ST=Some-State, O=Mediatek
    Validity:  2015-06-04 → 2035-06-04
    SubjectPublicKeyInfo (RSA-2048)
      Modulus: b5ed982c2bd789c2...  ← Key 1
    OID 2.16.886.2454.1.2
      SubjectPublicKeyInfo (RSA-2048)
        Modulus: c4daa0203cf63f2c...  ← Key 2
    OID 2.16.886.2454.1.1
      BIT STRING (525 bytes)     ← signature over cert
```

### 5.2 Fastboot (LK level)

**Status: BLOCKED**

LK (`lk_a.img`, ARM32, 1 MiB) exposes only:

```
oem mrdump          → triggers AEE/MRDUMP crash dump
set_active:         → "set active slot: not supported!"
getvar:             → limited variable set, no slot variables
```

No `download:`, `flash:`, or `erase:` handlers exist in this LK build.

### 5.3 META mode (USB)

**Status: BLOCKED on bootlooped device**

`meta_tst` reads from `/dev/ttyGS0` (USB gadget, VID `0e8d` PID `202d`).
The USB gadget never appears because `usb.init` creates `mass_storage.usb0`
without a backing file — the UDC binding fails silently. Additionally, even
if USB appeared, `meta_tst` never starts because procd never launches
(preinit is stuck; see §2).

### 5.4 UART META mode (UART trigger)

**Status: TRIGGER WORKS, STILL BLOCKED BY PREINIT**

The Preloader contains a UART META detection handshake:

```
Host sends:      METAMETA  (8 bytes, during Preloader execution window ~50 ms)
Preloader ACKs:  ATEM0001  (8 bytes)
Boot mode set:   META_BOOT ATAG → passed to LK → kernel cmdline
```

Other Preloader-level mode triggers found: `ADVEMETA`, `FACTFACT`, `FASTBOOT`.

Even after a successful `METAMETA` trigger, the Linux boot sequence still runs
`/etc/preinit`, which still fails at `lock`, and procd/meta_tst still never
start. The UART META path does not bypass preinit.

### 5.5 UART shell (1.8 V adapter, Linux level)

**Status: BLOCKED**

UART TX reaches the device console. preinit is running but has no stdin
attached to the console device — characters sent over UART are not received
by any process. The failsafe never produces a `/bin/ash` shell.

LK UART is output-only — no `uart_getc` / interactive input in this LK build.

### 5.6 UART firstboot injection

**Status: BLOCKED**

`firstboot` (SHA `d0a5164…`, 2410 bytes) is a shell script beginning with
`#!/bin/sh`. Cannot execute without a working busybox. If it could run, it
would call `jffs2reset -y`:

```sh
# eMMC path in firstboot:
dd if=/dev/zero of=/dev/block/nvdata  bs=1M
dd if=/dev/zero of=/dev/block/boot_para bs=1M
/sbin/jffs2reset -y
```

`jffs2reset` (9976-byte standalone ELF, dynamically linked to `libfstools.so`)
calls `overlay_delete()` which would wipe the ext4 overlay and restore the
factory SquashFS busybox on next boot. **If callable directly, this would fix
the device.** Blocked by the no-shell problem.

---

## 6. Boot Chain Summary

```
eMMC boot0/boot1
  └─ Preloader (244 792 bytes, load addr 0x00200EA0)
       GFH FILE_INFO + GFH BL_INFO only — no BL_SEC_KEY header
       Trust anchors: b5ed982c… / c4daa020…
       UART META trigger: METAMETA→ATEM0001
       └─ LK (ARM32, 299 912 bytes)
            A/B slot select from misc (mmcblk0p1 + 0x800)
            Fallback: default to slot A if magic invalid
            fastboot surface: oem mrdump only
            UART: output only
            └─ Kernel (boot_b.img, cmdline patched by LK)
                 init=/etc/preinit  root=/dev/mmcblk0p41  bootslot=b
                 └─ /sbin/init (custom binary)
                      forks /etc/preinit (PREINIT=1)
                      waits for /tmp/.preinit
                      └─ preinit (fork)
                           runs lock -w /tmp/.failsafe → FAIL
                           infinite loop → watchdog reboot
                           /tmp/.preinit NEVER CREATED
```

---

## 7. Available Images

| File | Size | Notes |
|------|------|-------|
| `ZLT_X17M_FULL_BACKUP.img` | 7.8 GiB | Full eMMC dump, taken AFTER break (broken state) |
| `rootfs_b.img` | ~512 MiB | Factory slot B SquashFS + ext4 overlay |
| `rootfs_patched_v15–v18.img` | ~512 MiB | Patched rootfs with fixed busybox (unflashtable) |
| `emmc_rar_extracted/mmcblk0boot0.img` | 4 MiB | Preloader from working eMMC device |
| `emmc_rar_extracted/lk_a.img` | 1 MiB | LK from working eMMC device |
| `emmc_rar_extracted/boot_a.img` | 32 MiB | Kernel + initrd, slot A, from working device |
| `emmc_rar_extracted/rootfs_sig_a.img` | 512 KiB | OEM cert chain (contains b5ed982c…/c4daa020… keys) |

Patched rootfs images are ready to flash but cannot be delivered without
an authenticated DA.

---

## 8. Variant Device Comparison

| Property | Bootlooped eMMC (target) | Working eMMC (variant1/4) | NAND 1GB (reference) |
|----------|--------------------------|---------------------------|----------------------|
| Target | `gem6xxx/evb6890v1_64_cpe_emmc` | same | `gem6xxx/evb6890v1_64_cpe` |
| Kernel | 5.4.238 | 5.4.238 | 5.4.238 |
| Active slot | B (broken) | A | A |
| Overlay FS | ext4 loop | ext4 loop | jffs2 |
| busybox SHA | `43db2f47…` (broken) | `19c2b391…` | `37791178…` |
| meta_tst SHA | `c66ac91f…` | `c7d734b5…` | `c66ac91f…` |
| firstboot SHA | `d0a5164…` | `d0a5164…` | `d0a5164…` |

---

## 9. Remaining Recovery Paths

### Path A — OEM DA (recommended first attempt)
Contact ZLT/Quectel and request either:
- An eMMC-specific signed Download Agent for MT6890 eMMC variant
- A firmware restoration tool for the X17M eMMC model

The keys required (`b5ed982c…` / `c4daa020…`) are embedded in the `rootfs_sig_a.img`
cert from a working device. ZLT/Quectel hold the private keys for these.

### Path B — Physical eMMC chip access
Desolder or clip the eMMC (`33BGAX`) and program it directly with a
BGA153/169 eMMC socket adapter and PCIe/USB programmer. Write either:
- A modified `misc` partition that sets slot A priority = 15
- A fixed `rootfs_b` overlay that restores the original busybox

This requires no authentication and is deterministic.

### Path C — 1.8 V UART adapter (when available)
1. Observe LK and Preloader serial output for any timing windows
2. Attempt `METAMETA` trigger during Preloader window (~50 ms after power-on)
3. If META mode boots: observe whether a different init path is taken
   (low probability — preinit still runs)
4. Confirm slot selection messages in LK output

### Path D — Misc partition corruption via tool exploit (speculative)
If any fastboot extension or BootROM-level command can write raw blocks to
eMMC without DA auth, zero out `mmcblk0p1 + 0x800` (32 bytes) to invalidate
the A/B magic → LK falls back to slot A. No such tool path has been
identified yet.

---

## 10. Key Artifacts

| Artifact | Location | SHA-256 (first 8 hex) |
|----------|----------|-----------------------|
| customer_da.auth | `x17m/` | `9fbcb7ca…` |
| DA_BR.bin (Quectel NAND) | `extracted_da/` | `c3d905…` |
| mmcblk0boot0.img (working eMMC Preloader) | `emmc_rar_extracted/` | `844a4ed5…` |
| rootfs_sig_a.img (OEM cert chain) | `emmc_rar_extracted/` | — |
| rootfs_patched_v18.img (latest patch) | `rootfs images/` | — |
| preloader_evb6890v1_64_cpe.bin (local eMMC PL) | `preloaders/` | `a49724d7…` |

---

## 11. Analysis Documents in `x17m/analysis/`

| File | Contents |
|------|----------|
| `MT6890_DA_GFH_STAGE_RECONCILIATION_20260922.md` | GFH framing analysis; corrected load address 0x00200000 |
| `MT6890_DAA_POLICY_OFFLINE_RECONCILIATION_20260922.md` | Confirms framing correct; 0x7017 is policy/trust rejection |
| `MT6890_DA_BR_SIGNATURE_KEY_AUDIT.md` | DA signed with `9af8…`; two RSA-PSS SHA-256 regions |
| `MT6890_TOOLAUTH_BINARY_AND_TRUST_ANALYSIS.md` | Preloader dakey.h = `a697…`; 2025 Preloader has no `9af8…` |
| `MT6890_MTK_AUTH_OFFLINE_VALIDATION.md` | customer_da.auth offline chain: PASS (but wrong key for device) |
| `X17M_META_TST_PROTOCOL_RECONSTRUCTION.md` | meta_tst frame format, op 3 = file read, op 2 = file write |
| `X17M_META_USB_LIVE_DIAGNOSIS.md` | Live META test on eMMC device: USB never appeared |
| `X17M_LINUX_META_FAILURE_ANALYSIS.md` | Root cause: usb.init unbacked mass_storage → no USB gadget |
| `X17M_1GB_PRELOADER_AB_STATE_MACHINE.md` | A/B boot control record format and rollback logic |
| `ZLT_X17M_EMMC_UNBRICK_ANALYSIS_20260926.md` | **This document** |
