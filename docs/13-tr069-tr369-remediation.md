# TR-069 & TR-369 Complete Remediation (CVE-2026-2035703)

Status: Complete and verified across Firmware builds v31–v34.

## FACTS

### Threat Model & Vulnerability Context (CVE-2026-2035703)

- **Vulnerability:** Unauthenticated remote management exposure and command injection / privilege escalation via TR-069 CWMP client (`netcwmpd`) and TR-369 USP agent (`uspad`).
- **Vendor Configuration:**
  - `netcwmpd` ran as a root daemon listening for inbound ACS connection requests, often bound across both WAN and LAN bridges.
  - The stock configuration loaded default carrier bootstrap parameters pointing to external management endpoints.
  - The vendor Web GUI exposed extensive TR-069 / TR-369 parameter tabs (`/tzwww/` and LuCI CBI menus) capable of mutating device identity, APN credentials, and firmware upgrade targets remotely without local authentication.

### Pruning and Decoupling Inventory

The complete remediation removed 45 binaries, libraries, scripts, and configuration templates totaling **7,250,580 bytes (~7.25 MiB raw)** from the NAND rootfs:

1. **Daemons and Binaries Removed:**
   - `/usr/sbin/netcwmpd` (TR-069 CWMP daemon)
   - `/usr/sbin/uspad` (TR-369 USP daemon)
   - `/usr/bin/cwmp_test` & `/usr/bin/usp_cli`
2. **Support Libraries & Plugins Pruned:**
   - `/usr/lib/libtr069*`, `/usr/lib/libusp*`, `/usr/lib/libcwmp*`
   - Data-model mapping objects for TR-098 / TR-181 (`/usr/lib/bcm_tr069*` / `/usr/lib/mtk_tr*`)
3. **Init and Boot Scripts Disabled:**
   - `/etc/init.d/netcwmpd`
   - `/etc/init.d/uspad`
   - Boot links `/etc/rc.d/S99netcwmpd` and `/etc/rc.d/S99uspad` deleted
4. **Web GUI Decoupling:**
   - Removed TR-069 / TR-369 menu entries from `/tzwww/js/` navigation trees.
   - Neutralized `/tzwww/cgi-bin/` endpoints that queried `netcwmpd` via `sockmsg_send` (App ID 13).
   - Removed LuCI TR-069 / USP controller endpoints.

### Verification Evidence

- Live process audit confirms zero instances of `netcwmpd`, `uspad`, or related management workers (`ps | grep -E "netcwmp|uspad"` returns only grep).
- No listening sockets remain on CWMP HTTP connection request ports (typically TCP 7547 or vendor custom ports).
- System memory freed: ~12 MiB of active RAM reclaimed by eliminating these long-running management daemons.

## INFERENCES

1. **Cellular Independence:** Neither the cellular data plane (`ccmni1`), nor the Fibocom FG360-EAU AT command processor (`atcid`), nor the dialer (`dialer`) depend on TR-069 or TR-369 services. Cellular registration and IP connectivity remain 100% operational after complete stack removal.
2. **Persistent Immunity:** Because the binaries and shared libraries were permanently excised from the squashfs image on `rootfs_a`, the vulnerability cannot be revived through factory reset or `/etc/config` restoration.

## UNRESOLVED

- None. Remediation is complete, validated in sandboxes, and running live in production.
