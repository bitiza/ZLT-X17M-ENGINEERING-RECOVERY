# Firmware images

## `rootfs_bozax17_v35_pruned_optimized.img`

Build v35 (2026-11-12) — image not yet published; build metadata only:

| File | Contents |
|------|----------|
| `build-v35/source-manifest.json` | Per-file SHA-256/mode manifest of the source rootfs |
| `build-v35/pruning-plan.json` | Packages and paths removed from the vendor rootfs |
| `build-v35/image-deletions.json` | Exact paths deleted when composing the image |
| `build-v35/image-boot-links.json` | Sysvinit boot links created in `etc/rc.d/` |
| `build-v35/service-cleanup-policy.json` | Boot services intentionally disabled |
| `build-v35/source-live-differences.json` | Files whose contents diverge from the live device source |
| `build-v35/reports/build-manifest.json` | Final image hash, size, partition limit, and headroom |
| `build-v35/reports/pruning-validation.json` | 20-point post-build validation checklist (all passed) |
| `build-v35/reports/package-dependencies.json` | Tool/package dependency check (dnsmasq 2.89-2, simple-adblock 1.8.8-1) |
| `build-v35/reports/expected-inventory.json` | Per-file metadata inventory of all 7,244 image files |

Per `reports/build-manifest.json`: image SHA-256 `37ddd143308be78af940b0a14deeb7cf95e08a31f19709cdd6aeed61560bb35e`, 47,738,880 bytes, 64 MiB partition limit, ~18.5 MiB headroom. `router_modified: false`, `flashed: false`.

## `rootfs_bozax17_v34_pruned_vendor_fixes_sanitized.img`

Companion build metadata for this image lives in [`build-v34/`](build-v34/):

| File | Contents |
|------|----------|
| `source-manifest.json` | Per-file SHA-256/mode manifest of the source rootfs |
| `pruning-plan.json` | Packages and paths removed from the vendor rootfs |
| `image-deletions.json` | Exact paths deleted when composing the image |
| `image-boot-links.json` | Sysvinit boot links created in `etc/rc.d/` |
| `service-cleanup-policy.json` | Boot services intentionally disabled |
| `source-live-differences.json` | Files whose contents diverge from the live device source |

Custom-built rootfs for the ZLT X17M (MT6890, NAND variant), derived from build v34
(`rootfs_bozax17_v34_pruned_vendor_fixes`, 2026-11-12). SquashFS 4.0, xz compressed,
262144-byte blocks, all-root.

**This image is sanitized.** The following were replaced with placeholders before upload:

| Item | Sanitization |
|------|--------------|
| `/etc/config/xray` | VPN server addresses, passwords, UUIDs, and import link replaced with `REDACTED*` placeholders |
| `/etc/xray/config.json` | Shadowsocks server address/password replaced with `0.0.0.0` / `REDACTED` |
| `/etc/shadow` | `root` and `admin` password hashes removed (accounts locked) |
| `/etc/mini_httpd.pem` | Replaced with a fresh generic self-signed certificate (`CN=x17m-recovery`) |
| `/etc/sshtun/` | Tunnel host/user redacted, password file blanked, `known_hosts` hostname redacted |
| `/etc/config/dhcp` and `/etc/x17m-dhcp-candidate/dhcp` | DHCP option 125 device MAC and serial zeroed |

Functional behavior (boot, layout, services, XRAY_DNS redirection structure) is preserved;
proxy credentials are placeholders and must be re-entered by the device operator.

### Integrity

```
1365fbbafaa3523dfc8460d888cbb45691aab488b93857fe1a69a651447cc924  rootfs_bozax17_v34_pruned_vendor_fixes_sanitized.img
```

Size: 47,738,880 bytes (47.7 MiB) — identical footprint to the unsanitized build.

### Warning

Flashing this image replaces the entire rootfs partition. Follow the recovery
decision tree (`docs/09-recovery-decision-tree.md`) and the NAND flashing notes
(`docs/16-nand-firmware-repacking-and-flashing.md`) before any write. Do not
transplant device-specific partitions (`nvcfg`, `nvdata`, `nvram`, `proinfo`, ...)
between routers.
