# Firmware images

## `rootfs_bozax17_v34_pruned_vendor_fixes_sanitized.img`

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
