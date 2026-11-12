# NAND Firmware Repacking, Headroom Budgeting & In-Field Flashing

Status: Fully characterized and validated across Firmware builds v28 through v35.

## FACTS

### Storage Geometry & Partition Constraints

- **Platform:** ZLT X17M (Raw-NAND variant, 1 GiB capacity).
- **Target Partition:** `rootfs_a` (MTD 29) / `rootfs_b` (MTD 43).
- **Partition Capacity Ceiling:** Exactly **67,108,864 bytes (64.0 MiB)**.
- **Critical Safety Constraint:** Writing an image exceeding 64 MiB overwrites adjacent MTD partitions (`rootfs_data` on slot A, `loader_ext_a` on slot B), causing catastrophic unrecoverable bricking.

### Firmware Budgeting History (v30–v35)

| Build | Raw Size (Bytes) | Size (MiB) | Headroom Below 64 MiB | Key Changes |
| :--- | :--- | :--- | :--- | :--- |
| **v30** | 49,033,216 | 46.76 MiB | 18,075,648 bytes (17.24 MiB) | Initial logging daemon & script guards |
| **v31** | 47,738,880 | 45.53 MiB | 19,369,984 bytes (18.47 MiB) | TR-069 & TR-369 stacks purged (-7.25 MiB raw) |
| **v32** | 47,738,880 | 45.53 MiB | 19,369,984 bytes (18.47 MiB) | WhatsApp/VoIP UDP unblocked, QoS deployed |
| **v33** | 47,738,880 | 45.53 MiB | 19,369,984 bytes (18.47 MiB) | Script error silencing & vendor typo fixes |
| **v34** | 47,738,880 | 45.53 MiB | 19,369,984 bytes (18.47 MiB) | Full vendor script audit, cron_master & sip_alg fixes (Flashed live) |
| **v35** | 47,738,880 | 45.53 MiB | 19,369,984 bytes (18.47 MiB) | Dormant code pruned, 100% POSIX compliance, TCP Fast Open, DNS cache 4k (Ready) |

### Build and Repacking Toolchain

The build pipeline enforces deterministic, fakeroot-isolated generation:

1. **`prepare_sources.py`:** Merges validated source overlays, evaluates `service-cleanup-policy.json`, generates `image-deletions.json`, and records SHA-256 digests in `source-manifest.json`.
2. **`build.py` (executed under `fakeroot`):**
   - Extracts baseline squashfs into a staging rootfs.
   - Applies deletions specified in `image-deletions.json`.
   - Copies modified overlay files with correct permissions (UID 0, GID 0).
   - Generates SquashFS using `mksquashfs4` with parameters matching vendor kernel expectations:
     `mksquashfs <rootfs> <image> -comp xz -b 262144 -noappend -always-use-fragments`
   - Verifies the output image size is strictly below 67,108,864 bytes.
3. **`validate_pruning.py`:**
   - Mounts / extracts the generated image in an isolated verification workspace.
   - Executes 16 automated checks covering ELF dynamic linking, syntax, menu decoupling, and service presence.

### In-Field Flashing Workflow

To flash an updated rootfs candidate without bootloader-level JTAG/UART:

1. Transfer image to RAM:
   ```bash
   scp rootfs_bozax17_vXX_*.img root@192.168.0.1:/tmp/
   ```
2. Verify SHA-256 on device:
   ```bash
   sha256sum /tmp/rootfs_bozax17_vXX_*.img
   ```
3. Flash target slot and reboot:
   ```bash
   mtd -r write /tmp/rootfs_bozax17_vXX_*.img rootfs_a
   ```
   *Note: OpenWrt's `mtd` utility automatically unlocks the flash partition, writes eraseblocks sequentially, and triggers an immediate reboot (`-r`).*

## INFERENCES

1. **A/B Slot Redundancy:** By targeting `rootfs_a` while keeping `rootfs_b` untouched, recovery remains feasible via bootloader slot switching if an untested image fails to boot.
2. **Safety Margin:** Maintaining ~18.47 MiB of unallocated headroom inside the 64 MiB partition guarantees flash endurance and provides ample room for future kernel or security updates.

## UNRESOLVED

- None. Workflow proven across multiple live flash cycles on the reference hardware.
