# X17M work log: xray stack, SMS investigation, and the failed flash

Router: X17M 1 GB, OpenWrt 21.02.7, kernel 5.4.238, aarch64. LAN 192.168.0.1.
Dates are 2026-10-10 to 2026-10-13.

Status at the end of this log: **rootfs_b holds a non-booting image. The device stops in
failsafe with no shell and no network. Recovery needs a verified DA or a NAND programmer.**
See "Incident" below.

---

## 1. Usage meter removed

- Stopped the daemon, the busybox httpd on 8085, the `X17M_USAGE` iptables chain and its FORWARD
  jump, the two rc.local lines, and `/data/usage`.
- Backup of `/data/usage` and rc.local kept in the session scratchpad (temporary).
- Local folder `x17m-usage/` deleted. Its rc.local lines were also removed from the v17 rootfs.

## 2. xray stack

### Core
- Router shipped xray 1.7.5 (2023). Replaced by **xray 26.7.11** from the Passwall ipk, at
  `/data/xray/xray` (musl aarch64, depends on libc only).
- The old 1.7.5 binary is kept at `/data/xray/xray-1.7.5` on the router.
- `/usr/bin/xray` was a symlink to `/data/xray/xray` on the router. In the rebuilt image the xray
  init script creates that symlink at boot if `/data/xray/xray` exists.

### Protocol tests (live, through the router)

| Config | Result | Exit IP |
|---|---|---|
| Shadowsocks `156.146.38.170:443` aes-128-gcm | Works (1.7.5 and 26.7.11) | 156.146.38.170 |
| VMess `REDACTED1.example.com:443`, ws `/REDACTED`, TLS | Works | 203.0.113.10 |
| VMess same host, no TLS | Fails (server needs TLS) | - |
| VLESS `REDACTED2.example.com:443`, ws `/REDACTED`, TLS | Works | 203.0.113.11 |
| VLESS `REDACTED2.example.com:10004`, ws, no TLS | Works | 203.0.113.11 |
| Trojan `REDACTED2.example.com:4443`, TLS, with and without SNI | Works | 203.0.113.11 |
| Trojan `51.195.235.71:443` (old saved config) | Fails. Server returns the Traefik default cert for the SNI, no backend | - |
| SSH over TLS `techno1.gretongers.my.id:443`, SNI `myaccount.telkom.co.ke` | Worked (tunnel exit 103.151.141.66). Later refused TLS from the server side | - |

Credentials supplied in chat are only in the router's UCI config and `/etc/sshtun/password`, mode 600.
Those are plaintext.

### Generator, probe, watchdog
- `/usr/bin/xray-generate-config` writes one outbound for the selected protocol plus the transparent
  inbound (`192.168.0.1:12345`), the local SOCKS inbound (`127.0.0.1:10808`) and routing. It validates
  with `xray run -test` before replacing the live file.
- It installs only when the output differs (`unchanged` otherwise), so Save & Apply no longer restarts
  xray for an unchanged config.
- `sshtls` is a SOCKS hop to `127.0.0.1:1080`, served by `/usr/bin/sshtun` and `sshtun-proxy`.
- `/usr/bin/xray-probe <proto>` tests one server on spare ports without touching the live proxy.
- `/usr/bin/xray-watchdog` (procd): checks the live path every 30 s. After two failures it restarts
  xray if the active server still passes a probe, or else moves to the next server in
  `failover_order`. It returns to the `preferred` server every 300 s if that passes a probe.
- Manual Stop is recorded as `xray.general.service=0`. The watchdog and the init script respect it.
  Start and Restart clear it.

### LuCI
- Overview page: active outbound with live exit IP, server list with radio buttons, automatic failover
  card with event log, service controls.
- Servers page: one section per server. No protocol dropdown. Save & Apply regenerates only the
  active server's config.
- Verified: both pages return 200, selection and Stop/Start work through the page endpoints.
- Not verified: how the page looks in a browser.

### Limits known
- Only TCP is redirected. UDP and DNS from the LAN are not proxied.
- REALITY is not supported. The generator would silently produce a plain config. Not fixed.
- Switching servers restarts xray and interrupts open connections.
- The health check depends on `connectivitycheck.gstatic.com`.

## 3. SMS and USSD investigation

Findings (not a fix):

- No SMS/USSD binary is missing from the rootfs compared with the vendor original. The 1,035 missing
  files are Valgrind, Bluetooth, ALSA, DDNS, zoneinfo, TR-069/USP/ONENET data and the SLIC voice driver.
- Modem path works (live): `AT+CPIN?` READY, `AT+CREG?` 2,1 (registered), `AT+CSCA?` set,
  `AT+CUSD=?` supported, `AT+CMGL` runs. Read-only commands only. No USSD code was sent.
- `sms_mgr` runs, `mdlcfg SYS_SMS_SW=1`, and its log shows init completed.
- The web SMS/USSD pages call `/cgi-bin/http.cgi`. In the **patched image** that file was missing
  (renamed to `httpx17m_nand1gb.cgi`, original kept as `http.cgi.orig`). On the router it is a modified
  copy (247 bytes differ from vendor, same strings, changed code and data around `0x3fd98`,
  `0x338xx`, `0xa6cd8`, `0xcc2a8`). Its changes are documented in
  `/home/kali/Desktop/x17u-docs/superadmin-login-trace/` and `x17m_http_cgi.md`. They change
  superadmin/admin/root login levels. They do not touch SMS.
- Web SMS was **not** confirmed working. The web login returned a next-login time of about 9,400 s,
  and I did not attempt a login.
- Not identified: which earlier edit or deletion broke SMS. Edited areas include 74 `tzscript` files
  (about 13 of them stubbed, several with "Disabled for ODU" comments), `etc/inittab`, and
  `lib/preinit/*`.

## 4. Flash layout (corrected from earlier mistakes)

Live `/proc/mtd` and mounts:
- `rootfs_a` mtd29 = 64 MiB, `rootfs_b` mtd42 = 64 MiB. Kernel boots slot b (`bootslot=b`,
  `root=/dev/mtdblock42`).
- `rootfs_data` mtd43 = 0xAC0000 (10,752 KiB, JFFS2), mounted at `/overlay`.

Read from the live `mtd42`:
- SquashFS ends at byte 55,737,791.
- From byte **55,836,672** (= 67,108,864 - 0xAC0000) to the end of the slot is a JFFS2 copy of the
  overlay, byte-identical to the live `mtd43` (first 1 MiB compared).

So the usable squashfs size is **55,836,672 bytes**, not the full 64 MiB. Writing a larger image
overwrites that overlay copy. The overlay size equals whatever the squashfs does not use, rounded to
the erase block, so a smaller image gives a larger overlay.

There is no dm-verity on the X17M root. `rootfs_sig_b` is not referenced on the command line. The
bootloader log (UART) prints `[SECLIB_IMG_VERIFY] Partition [rootfs_sig] is not exist`, then
`ROOTFS_SIG_VFY Fail: 100008`, then `ROOTFS_SIG_VFY Success` on the retry. It did not stop the boot.

## 5. Image build

- Tool: `mksquashfs <dir> <img> -comp xz -b 262144 -noappend -all-root -no-xattrs`. Pad to the
  intended size with `truncate`.
- Original tree packs to 58.65 MB. That is too large for the 55,836,672-byte limit.
- Removing Valgrind (19 files in `usr/lib/valgrind` and `usr/bin/valgrind*`, `usr/bin/vgdb`)
  brings the restore tree to 51.6 MB. Padded to 55,836,672. `build_v18/images/rootfs_v18_restore.img`.
- Deletions were not forced by the old 58 MB estimate. That number was wrong.

Images in `build_v18/images/`:
- `rootfs_v18_restore.img` (55,836,672 bytes). Built from the vendor original, plus x17m additions,
  plus the device config files, `dialer`, `http.cgi` and the xray init. **Missing: boot-path edits
  (preinit, inittab, init.d/system, tzproc, rc.local, S30usb.init) and `/dev`.** The `/dev` problem was
  found after the flash and fixed in the file, but the flashed copy did not have it.
- `rootfs_patched_v18_xray_candidate.img` (55,738,368 bytes). Built from the edited v17 tree with
  deletions and stubs kept. Not recommended.
- `rootfs_v18_restore_candidate_TOO_LARGE_DO_NOT_FLASH.img` (67,108,864 bytes). Over the limit. Do not use.

Trees:
- `rootfs.original/`: vendor, untouched.
- `rootfs_patched_v17_10s_meta_rndis_dialer_auto/`: edited v17. Restored to its pre-build contents
  (CGI backup, `geosite.dat` and generated `config.json` put back).
- `build_v18/restore/`: clean build tree (original plus additions, Valgrind removed).

## 6. Incident: flashed image, device not recovered

What was flashed:
- `rootfs_v18_restore.img` (the version without `/dev`) written with
  `mtd -r write /data/rootfs_v18_restore.img rootfs_b` on the active slot.

What happened (UART log):
1. Bootloader verifies the kernel and DTB. `rootfs_sig` check fails once, then passes on retry.
2. Kernel boots from `/dev/mtdblock42`.
3. `/etc/board.d/99-default_network` cannot read `/mnt/vendor/nvcfg/mac0` and `mac1`.
4. Preinit prints `Press the [f] key ... failsafe mode`.
5. `/etc/preinit: can't open '/dev/null'`. The image has no `/dev` directory, so devtmpfs is not
   mounted. The failsafe path then cannot create `/dev/null`.
6. Typed commands (`mount -t devtmpfs devtmpfs /dev`, `ls`, `hexdump`) are echoed by the tty but
   produce no output. No prompt appeared after Enter or Ctrl-C. No shell is running.

Final state:
- No shell on UART. No network. No verified DA. No direct flash-write capability on our side.
- `rootfs_b` holds the bad image. The v17 image (`rootfs_patched_v17_10s_meta_rndis_dialer_auto.img`)
  and `rootfs_b.img` in the project root (64 MiB) are the candidates for restoring it. Verify
  `rootfs_b.img` against the v17 image before use.

Remember: the UART capture notes in the project record that attaching a UART adapter to a known-good
unit caused the same NAND init failures. Check wiring and logic level before connecting it again.

## 7. Lessons

1. **Write to the inactive slot, or keep a verified backup of the active one, before any flash.**
   A flash to the running slot has no fallback here.
2. **Build the image from the tree that was tested, and diff it against the tested image before
   flashing.** Our restore tree was built from the vendor original, so it dropped the boot-path edits
   that the device needed.
3. **Include `/dev` in the squashfs** (`dev/console c 600 0 0 5 1` as a pseudo-file entry, or a real
   root-owned build). An empty `dev` directory is not enough for the kernel to populate it.
4. **Check the slot layout from the live device, not from notes.** The overlay copy at the slot tail
   sets the real size limit.
5. **Don't assume the device ran a command.** Commands typed on UART were ours, and the device did
   not run them.
6. **Keep the edited and original trees apart,** and build each new image in its own folder.
7. **Read the safety reasons when a command is blocked,** and don't route around them.

## 8. Next steps (if the device is ever recovered)

- Write `/dev` and the boot-path edits into a new tree, then diff the tree against the tested
  `rootfs_patched_v17_10s_meta_rndis_dialer_auto` before building.
- Confirm the squashfs size against 55,836,672 bytes.
- Test SMS and USSD on the tested image before adding more changes.
- Re-check the `/dev/null` failure mode on the console first, before trusting any new image.

---

## 9. Ported the xray + SSH-over-TLS stack into the boza tree (2026-10-17)

Source: `rootfs_patched_v17_10s_meta_rndis_dialer_auto` (tested).
Target: `rootfs_bozax17_v17_10s_meta_rndis_dialer_auto`.
Additive only. boza's own `dialer` and its system libs were left untouched. No image was built or flashed.

Copied into boza:
- Core + data: `/usr/bin/xray` (1.7.5 fallback), `/usr/share/xray/geoip.dat`, `geosite.dat`.
- Scripts: `xray-generate-config`, `xray-probe`, `xray-watchdog`, `xray-check-status`, `xray-import-link`,
  `sshtun`, `sshtun-proxy`.
- Init + enablement: `/etc/init.d/{xray,xray-watchdog,sshtun}` and the six `rc.d` symlinks
  (`S99xray`, `K10xray`, `S99xray-watchdog`, `K10xray-watchdog`, `S60sshtun`, `K10sshtun`).
- Config: `/etc/config/xray`, `/etc/xray/` (runtime config.json dir), `/etc/sshtun/{sshtun.conf,known_hosts,password}` (password 600).
- LuCI: `controller/xray.lua`, `model/cbi/xray/settings.lua`, `view/xray/{status.htm,nav.htm}` (menu: admin/services/xray).

Dependencies boza was missing, also added:
- SSH VPN path: `/usr/libexec/ssh-openssh` + `/usr/bin/ssh` symlink + `/usr/bin/sshpass` (boza had only dropbear).
  ssh-openssh links libcrypto.so.1.1/libc/libgcc_s/libz.so.1 — all already in boza.
- `curl`: boza's system `libcurl.so.4` is an **OpenSSL** build (used by boza's collectd/nettest) and must not be
  replaced. The tested `curl` is a **wolfSSL** build. Installed it privately in `/usr/lib/xray-deps/`
  (`curl.real` + libwolfssl + its own libcurl/libnghttp2) behind a wrapper `/usr/bin/curl` that sets
  `LD_LIBRARY_PATH=/usr/lib/xray-deps`. No system library was overwritten.

One change from the tested scripts:
- `xray-generate-config` no longer hardcodes `"listen": "192.168.0.1"` for the transparent inbound. boza has no
  UCI `network` file, so the listen address is now detected at runtime: br0's IPv4 -> `uci network.lan.ipaddr`
  -> `192.168.0.1` fallback. (`$XRAY_LISTEN` override still honoured.)

Verified on disk: all files/perms/symlinks present, `bash -n` clean on the patched generator, curl.real's
NEEDED libs all resolve under xray-deps, boza dialer + boza system libcurl unchanged.

Device-side, still required (not part of the rootfs):
- The newer core `xray 26.7.11` lives on the persistent `/data` partition, not in the rootfs. The init symlinks
  `/usr/bin/xray -> /data/xray/xray` at boot when present; otherwise the shipped 1.7.5 is used (enough for
  shadowsocks/vmess/vless/trojan). To use 26.7.11 on boza, extract it from
  `passwall_packages_ipk_aarch64_cortex-a53/xray-core_26.7.11-r1_aarch64_cortex-a53.ipk` to `/data/xray/xray` on the device.
- Confirm boza's real LAN IP matches what the transparent proxy expects (auto-detected now, but verify br0).
- iptables hook `prerouting_mdl_chain` exists in boza's `/etc/iptables_config`; confirm it is actually created at runtime.

---

## 10. Live staging + test on the boza unit (2026-10-17)

Device booted OpenWrt 21.02.7, **slot A** (`bootslot=a`, root=/dev/mtdblock29, rootfs_a mtd29 = 64 MiB).
Transport: telnet 192.168.0.1 (root). ICMP ping is dropped by the router but TCP works; PC on LAN via DHCP
(192.168.0.128). ssh:22 refused (no server). curl absent live; wget present (full, HTTPS).

Live flash layout here differs from the earlier X17M notes:
- `/overlay` = mtd30 (`/dev/mtdblock30`), ~18 MiB, only ~17 MiB free. overlayfs on /.
- `/data` = `/dev/ubi1_1`, UBIFS, 347 MiB, ~279 MiB free.

Staging strategy (overlay is tiny): big files on /data, small scripts on the overlay, symlinks bridge them.
- `/data/xray/xray` = xray 26.7.11 (from passwall ipk; needs only libc + libgcc_s). `/usr/bin/xray` -> it.
- `/data/xray/assets/{geoip,geosite}.dat`; UCI `xray.config.datadir=/data/xray/assets`.
- `/data/xray-stack/ssh-openssh` ; `/usr/bin/ssh` -> it.
- `/data/xray-stack/curl-libs/` (wolfSSL curl + libs); `/usr/lib/xray-deps` -> it; `/usr/bin/curl` wrapper.
- Overlay: the xray* / sshtun* scripts, sshpass, /etc/config/xray, /etc/sshtun/*, /etc/init.d/*, LuCI pages.
- Files pushed with a PC HTTP server + wget. rc.d autostart NOT enabled yet (manual control during test).

Test results (non-invasive; no iptables added):
- `xray version` -> Xray 26.7.11 (go1.26.5 linux/arm64).
- `xray-generate-config` -> OK (shadowsocks); `xray run -test` -> Configuration OK.
- transparent inbound listen auto-detected as 192.168.0.1 (correct for this unit).
- `xray-probe shadowsocks` -> rc=0.
- Manual listen-only run: direct exit IP 196.202.223.252 (router HAS upstream internet),
  proxied exit IP 156.146.38.170 (through xray). Stack works end to end.

Not yet done: enabling the live transparent redirect (service start + iptables), autostart on boot,
and any image build/flash. The router's own internet works, so the PC-tethering failure is a LAN->WAN
forward/NAT issue, independent of xray.

---

## 11. LuCI web UI fix on boza (2026-10-17)

Symptom: http://192.168.0.1:4153/cgi-bin/luci/ unreachable (connection refused).
Cause: rc.local starts `uhttpd ... -L /usr/lib/lua/luci/sgi/uhttpd.lua` for LuCI, but boza was missing the
uhttpd Lua plugin: `Could not open plugin uhttpd_lua.so`. uhttpd never bound 4153. (boza's vendor UI is
mini_httpd on :80/:443; LuCI is the add-on on 4153.)

Fix: ported `/usr/lib/uhttpd_lua.so` (12,370 B, from the v17 tree; needs liblua.so.5.1.5 + libc + libgcc_s,
all already on boza; same OpenWrt 21.02.7 build so plugin ABI matches). Added to the boza tree and pushed to
the live overlay. Restarted uhttpd.

Result: 4153 UP. `/cgi-bin/luci/` returns the LuCI login page (403 + X-LuCI-Login-Required is normal for an
unauthenticated root; the body is the full login form, theme CSS 200). Logged in as root; the ported Xray
page at admin/services/xray returns HTTP 200 and renders (Overview / Servers / failover / Exit IP).

Persistence: the .so lives on the overlay, so on reboot rc.local's existing uhttpd line starts LuCI
automatically — no extra autostart config needed.

---

## 12. Image build for boza + flashing blocker (2026-10-17)

Built a flashable rootfs from the LIVE known-good slot A (not the empty-/dev on-disk tree):
1. `dd if=/dev/mtd29` dumped over uhttpd:8081 to PC, sha256 verified (b4bd2d7f...).
2. unsquashfs under fakeroot (preserves the single /dev/console node, root ownership).
3. Baked in the stack ADD-ONLY: xray* / sshtun* scripts, curl wrapper, sshpass, /etc/config/xray
   (datadir -> /data/xray/assets), /etc/sshtun/*, /etc/init.d/* + /etc/rc.d autostart symlinks,
   LuCI pages, uhttpd_lua.so, and symlinks /usr/bin/xray|ssh and /usr/lib/xray-deps into /data.
   Big binaries (26.7.11, geo, ssh-openssh, curl libs) stay on /data (separate UBI, survives reflash).
4. Repacked: `mksquashfs ... -comp xz -b 262144 -noappend -all-root` (matches the original superblock).

Artifacts in build_v18/images/:
- `rootfs_bozax17_v18_xray.img`  48,078,864 B / 45.9 MiB (limit 67,108,864; 18.1 MiB headroom).
  sha256 a20bb03ce4b36af6413d2ca4ec7e663ca0a694ffca48167f2448e8bbcc8bb574
- `rootfs_bozax17_slotA_KNOWNGOOD_backup.img`  64 MiB raw dump of slot A. sha256 b4bd2d7f...
Verified: valid squashfs v4/xz/256K, /dev/console present, 0 files removed vs original, stack present.

FLASHING NOT DONE - blocker:
- rootfs slots are 64 MiB each (rootfs_a mtd29 / rootfs_b mtd43); overlay (rootfs_data mtd30, 18 MiB) is
  SHARED by both slots. So the X17M 55.8 MiB limit does NOT apply here; 64 MiB is the budget.
- Slot is chosen by the LK bootloader (cmdline bootslot=a). boot_para (mtd15) is erased (0xFF); the slot
  flag location is unconfirmed (likely misc/BCB mtd3). setup_link.sh only reads the slot, never sets it.
- Vendor A/B tooling exists: /sbin/sysupgrade, /sbin/upgraded, /usr/bin/tz_upgrade_client - the safe path
  to write the inactive slot and flip the pointer. Must be understood before any write.
- A blind `mtd write rootfs_b` risks a no-boot (wrong/again-missing slot flag) and gains little, since the
  overlay + /data already persist the whole stack across reboots.
Next: study tz_upgrade_client/sysupgrade + confirm the slot flag, OR leave the image as a staged artifact.

---

## 13. Post-reboot recovery: boot NAT race + self-healing keeper (2026-10-17)

**Symptom:** after a router restart, the WiFi phone had no internet, though LuCI ping
tests passed. (Ping passed because those are router-sourced; LAN-client TCP died.)

**Access:** Kali was off the router LAN (RNDIS gave a carrier IP via passthrough this
boot). Reached the router through the **Samsung phone as a jump host**: Kali --USB/adb-->
phone --WiFi(wlan0 192.168.0.161)--> router telnet. Helpers added in scratchpad:
`rr.sh` (paced adb->nc->telnet short command), `rputx.exp` (expect file upload via
quoted heredoc). Note: router busybox lacks base64/nslookup/timeout; full applets at
`/bin/busybox_full` (`export PATH=/usr/local/bin:$PATH`).

**Root cause:** the MTK cellular dialer firewall layer came up late/incomplete:
- POSTROUTING had **no MASQUERADE** for ccmni1 (clients left with private src, no return).
- vendor chain **`prerouting_mdl_chain` absent**, so `/etc/init.d/xray`'s
  `setup_xray_iptables` (which hooks the `XRAY` chain into `prerouting_mdl_chain`) could
  not attach the transparent redirect. xray(26.7.11) + REDACTED VLESS outbound were
  healthy (proxied exit 203.0.113.11 vs direct 196.202.223.195).

**Fix (live; persists via overlay, NOT in the image artifact):**
- `/usr/bin/xray-natfix` — 30s idempotent loop: ensure `POSTROUTING -o <defroute-if>
  -j MASQUERADE` and `PREROUTING -i br0 -j XRAY` (direct hook, bypassing absent vendor chain).
- `/etc/init.d/xray-natfix` — procd service, START=97, enabled (`S97xray-natfix`).

**Verified:** HOOK_PRESENT + MASQ_PRESENT held by keeper; phone exit IP = 203.0.113.11
(VPN). User chose to restore the VPN transparent proxy (vs direct). If the image is ever
flashed, add these two files to the tree.

---

## 14. Protocol sweep + allowInsecure migration (2026-10-17)

**Trigger:** selecting vmess in LuCI failed with "Generated configuration is invalid!"
-> Xray 26.7.11 removed `allowInsecure` (migrated to `pinnedPeerCertSha256`/
`verifyPeerCertByName`). `xray-generate-config` still emitted `allowInsecure`, so every
TLS profile regenerated after the 26.7.11 upgrade failed validation. (Live vless kept
working only because its config predated the regen.)

**Fix:** `stream_json()` now takes a 7th arg (real server address). For allow_insecure=1
(bug-host spoofed SNI) it emits `verifyPeerCertByName:<address>` (verifies the real cert
while SNI stays spoofed); for allow_insecure=0 it omits the field (default verifies against
serverName). Callers trojan/vmess/vless pass "$ADDR". Applied live
(/usr/bin/xray-generate-config, .bak kept) and to the tree (.pre-vcn.bak kept).

**Automated sweep results (direct/carrier exit 196.202.223.214):**
- trojan      OK   exit 203.0.113.11 (REDACTED2.example.com)
- vmess       FAIL no proxy exit (config now valid; REDACTED1.example.com server/account dead)
- vless       OK   exit 203.0.113.11 (proves the verifyPeerCertByName migration works
                   with spoofed SNI myaccount.telkom.co.ke)
- shadowsocks OK   exit 156.146.38.170
- sshtls      FAIL: (1) stale pinned SSH host key (ECDSA changed) -> cleared
                   /etc/sshtun/known_hosts (accept-new re-pins); (2) then banner-exchange
                   timeout -> techno1.gretongers.my.id SSH-over-TLS server dead/unreachable.

**Left live on vless** (working). vmess + sshtls need fresh server accounts; not code issues.

**Update 2026-10-18:** user confirmed sshtls works end-to-end with a NEW SSH-over-TLS
account — confirming the earlier sshtls failure was purely the dead techno1 account, and
that the generate-config fix + known_hosts clearing (accept-new re-pin) are correct. All
five protocols now functional with live credentials (vmess still needs a fresh account).

---

## 15. Recovery audit and preloader DA closure (2026-10-20)

Full audit: `analysis/X17M_RECOVERY_AUDIT_20261020.md`. Summary of what changed in this
session.

### Preloader DA host is closed

The Preloader (`0e8d:2000`) is reachable and completes the MTK handshake
(`is_brom=False`, `hwcode=0x992`, target config `0x5`, `SBC=True`, `DAA=True`), but:

- stock `DA_BR.bin` -> `DAA_SIG_VERIFY_FAILED (0x7024)` at `upload_data`
- `DA_BR_acc_bypass_nand.bin` -> same `0x7024`
- Preloader `WRITE32` to `sec_img_auth` -> `CRYPTO_DEINIT_FAIL (0x1001)`
- Preloader `READ16/READ32/READ32_direct` -> `CRYPTO_INIT_FAIL (0x1000)`
- raw `0xDA` register write -> `USB Overflow`, Kamakiri2 failed (not implemented in
  Preloader mode; it is a BROM-only command)

The `0x7024` root cause is documented in `analysis/MT6890_DA_BR_SIGNATURE_KEY_AUDIT.md` and
`analysis/MT6890_TOOLAUTH_BINARY_AND_TRUST_ANALYSIS.md`: the supplied DA is signed by
modulus `9af8...`, while the SDK's `inc/dakey.h` `DA_PUBK` that the Preloader's DA-image
checker installs is `a697...`. The ACC bypass sits inside the signed DA body, so it cannot
satisfy the outer DAA gate. No private key for `a697...` is in the workspace, so the DA
cannot be re-signed offline.

### New fact: the UART console is live and interactive

This is the significant finding of the session and it was not previously known.

- The console at `/dev/ttyUSB0` 921600 8N1 is a working tty. The boot transcript ends with
  the stock OpenWrt prompt pair, and sending `f\n` is **accepted**: the unit replies
  `- failsafe -`. That is a semantic acknowledgement, not an echo, so the failsafe path
  really executes.
- The unit is not a stale `0e8d:2000` instance. After the last power cycle the router USB
  identity is gone entirely and only the FTDI remains, i.e. the device left the Preloader
  and is running Linux with the broken slot-B rootfs.
- **No shell appears, and the reason is now exact rather than inferred.** The running
  `/etc/preinit` is a vendor script, not the 29-line stock copy under test in
  `rootfs/`, `rootfs.original/`, `build_v18/restore/`, `build_v19/rootfs/`. It reports
  `can't create /dev/null: nonexistent directory` at lines 15/20/32, and the running
  rootfs has no `/dev` directory at all, so `devtmpfs` is never mounted.
- Consequently the failsafe login hook can never fire: `lib/preinit/99_10_failsafe_login`
  requires `[ -c "/dev/$console" ]` before spawning `ash --login </dev/$console`. With no
  `/dev` that test can never pass. This explains the older observation in
  `analysis/X17M_LIVE_FAILSAFE_TEST_20261008.md` that failsafe gave no usable shell.

**The blocker is precisely "no `/dev` in the running rootfs"** - not a dead console, not a
failed kernel, not a broken failsafe. The UART is a usable input channel today and would
become a usable shell channel the moment a rootfs containing `/dev` is running.

### New offline finding: LK fastboot is confirmed diagnostic-only

The 1 GB `LK_b` (`mtd39_lk_b.img`) fastboot command table is exactly:
`getvar:`, `reboot`, `reboot-bootloader`, `reboot-fastboot`, `continue`, `set_active:`,
`max-download-size`, `product`, `is-userspace`.

A byte-exact search of the whole image finds **no** `download:`, `flash:`, `erase:`, or
`flash_part` token. `set_active:` is present but prints `set active slot: not supported!`.
This matches `analysis/X17M_FORENSIC_REPORT.md` for the 8 GB LK. The `fastboot:
[download_base:%p][download_size:0x%x]` string is a log format, not a command handler.

So the LK fastboot endpoint cannot be used to write a rootfs, and `set_active` cannot flip
the slot. The A/B route is blocked by the same missing capability as everything else.

### Next tests, in order (one avenue at a time)

1. `FASTBOOT` selector on a fresh Preloader window - never tested on this device, and it is
   the only selector that reaches a subsystem (LK) not yet contacted. Non-destructive: it
   only changes a RAM boot_mode.
2. Preloader `jump_to_partition` / `send_partition_data` (CMD `0x71` / `0x70`,
   `mtk_preloader.py:501,511`). This is the only identified path that could deliver a
   rootfs to NAND **without** a DA signature. The 1 GB Preloader does contain the
   partition-name machinery it needs (`%s %s partition not found`, `uboot_a`, `uboot_b`,
   `lk_a`, `lk_b`, `aee_lk`, `part name=%s` at `0x720a7`+). Probe with a no-write command
   first; any write must target a non-critical partition or a verified-good image.
3. `ADVEMETA` selector, then re-test the `meta_tst` primitive against this unit, using
   `/dev/mtd42` (the broken slot B) as the first read-only target. The primitive is an
   unrestricted `open(path)` on the target and its operation 2 is write-capable, so it
   would be a direct NAND path. Caveat: `meta_tst` lives in the rootfs, and this unit's
   running rootfs is the broken one, so the gadget may not come up at all. Test, do not
   assume.

If and only if a write path appears, restore slot B with the known-good
`rootfs_patched_v17_10s.img` (SHA-256 `6469a522780382293c0f62bc412b55d5477188ed547e6754db5bebd3e5cae872`),
which is already recorded as booting normally from slot B and reaching a failsafe root
prompt on `/dev/ttyS0`. Leave `rootfs_a` untouched as the fallback.

Do not repeat `firstboot -y`; it already erased `nvdata` and `boot_para` once.

### Tooling staged for the next test

`x17m/work/fast_part_probe.py` - a minimal raw-pyusb Preloader prober, written because the
Preloader USB window is about one second and mtkclient's `preloader.init()` does too many
round trips to fit inside it. It handshakes with the MTK start sequence `A0 0A 50 05`
(inverted echo per byte) and then immediately issues two **read-only** probes: `0x71
JUMP_TO_PARTITION` and `0x70 SEND_PARTITION_DATA`, both with the non-existent partition
name `zzz_no_such_partition_zzz` and, for `0x70`, a zero-length body. It contains no write
path at all.

`x17m/work/pl_partition_probe.py` - the same two probes through mtkclient's own
`send_partition_data()` / `jump_to_partition()` API, so a positive result would be
corroborated by upstream code rather than only by my framing. Its stage-2 write branch is
refused unless `--write-partition`, `--write-file` and `--confirm` are all given
explicitly; it was never used.

`/tmp` was wiped mid-session, so the patched mtkclient was rebuilt at
`x17m/work/mtkclient_pl` from `analysis/tools/mtkclient_upstream` with the same two patches
(`usb_ids.py` no longer lists `0e8d:0003`, and `usblib.py` no longer filters discovery on
`bDeviceClass=0x0A`).

### Device state during the broken rootfs

With the broken slot-B image running, the router enumerates **no** MediaTek USB identity:
`lsusb` shows only the FTDI, and `dmesg` has shown no `0e8d` event since the last power
cycle. The device left the Preloader, booted Linux, and the broken rootfs brings up no
working USB gadget, so there is neither a Preloader window nor a META gadget while it sits
in this state. A Preloader window exists only between a power cycle and the device leaving
USB-download mode, which is why every Preloader test needs a fresh power cycle.

### Restore images, verified

Three local images contain a `dev/console` node and are candidates for restoring slot B if
a write path ever appears:

- `rootfs_patched_v17_10s.img` - 55,738,368 bytes, SHA-256
  `6469a522780382293c0f62bc412b55d5477188ed547e6754db5bebd3e5cae872`. Known-good on this
  hardware: recorded as booting normally from slot B and reaching a failsafe root prompt on
  `/dev/ttyS0`.
- `rootfs_patched_v17_10s_meta_rndis_dialer_auto.img` - same size, same `/dev`, plus the
  meta/RNDIS/dialer additions that were in use when the unit was working.
- `rootfs_b.img` - 67,108,864 bytes, SHA-256
  `baec6707b37fc7945a5a810de19e5b058665f78a5101a25eeed8c1ef0437dcd5`. Full slot-sized, but
  see the size caveat below.

**Size caveat.** The usable squashfs size of the live slot is **55,836,672 bytes**, because
from that offset to the end of the slot is a JFFS2 copy of the overlay (section 4). The two
55,738,368-byte images sit under that limit and are the safer choice; the 64 MiB
`rootfs_b.img` would overwrite the overlay copy. After any write, re-read the slot and
compare the squashfs superblock plus a full SHA-256 of the written region against the
source image before rebooting. Do not trust a write without a read-back.

### The USB link is unreliable and must be fixed before further loader tests (2026-10-20)

Power cycles at 13:42-13:46 produced this host-side pattern:

```
13:42:07  usb 1-1: new high-speed USB device number 4 using ehci-pci
13:42:07  usb 1-1: New USB device found, idVendor=0e8d, idProduct=2000
13:42:08  usb 1-1: USB disconnect, device number 4        <-- gone after 1 second
13:43:33  usb 1-1: new high-speed USB device number 5 using ehci-pci
13:43:45  usb 1-1: device not accepting address 5, error -110
```

`error -110` is ETIMEDOUT from the host USB stack: the device never finished address
assignment. The Preloader's own log shows the same failure from its side:

```
[TOOL] USB enum timeout (Yes), handshake timeout(Yes)
[TOOL] Enumeration(Start)
[TOOL] : usb listen timeout
[TOOL] <USB> cannot detect tools!
```

So the earlier "the Preloader window was missed" observations were **link quality**, not
bad test design or bad timing - one attempt lasted a single second, shorter than the
Preloader's own 3313 ms tool timeout, so no host could have finished a handshake on it.

The FTDI is on `bus 3` (xhci) and the router on `bus 1` (ehci-pci, behind a VMware
virtual hub), so the two are physically separate paths. Re-seat the router's USB cable,
and if this is a VM, prefer a direct pass-through of the router's USB controller instead of
a hub. A reliable enumeration is a precondition for the `FASTBOOT` selector test.

The UART is unaffected and captured three complete boots in the same window
(441,208 bytes), so the device boots and runs fine - only USB enumeration is failing.

### LK fastboot app is resident on every boot

From the live UART of a normal boot:

```
starting app fastboot
wait_for_enter_fastboot:90: Wait for enter fastboot event...
starting app gem_boot
wait_for_boot_linux:722: Wait for boot linux event...
```

The LK fastboot application is started on every normal boot and blocks waiting for an
"enter fastboot" event that never arrives. The `FASTBOOT` Preloader selector sets
`boot_mode = FASTBOOT` and is the most plausible source of that event; it has never been
tested on this device. `work/combined_probe.py` performs that test (plus the
now-closed partition-command probe) in a single Preloader window.

### Preloader-as-DA partition commands are compiled out

`analysis/X17M_RECOVERY_AUDIT_20261020.md` section 12 confirms, against the exact 1 GB
Preloader, that all the distinctive `CFG_PRELOADER_AS_DA` strings are absent
(`SEND: name = %s`, `SEND: len = 0x%x`, `SEND: Verify PASS`, `PL Checksum`,
`XFLASH checksum`, `Jump to LK`, `Jump to ATF`, `Unknown Jump`, `READ: name`). The
`0x70`/`0x71` command family does not exist in this build, so upstream mtkclient's
`send_partition_data()`/`jump_to_partition()` are dead code against this device. The
partition-name strings that *are* present (`%s %s partition not found`, `uboot_a`, `lk_a`,
`aee_lk`, `part name=%s`) belong to the internal boot-chain loader, not to a host-facing
command surface.

### Best restore candidate: the v19 image (verified)

`build_v19/images/rootfs_bozax17_v19_xray_busybox.img`

| Property | Value |
|---|---|
| Size | 48,685,056 bytes |
| SquashFS `bytes_used` | 48,683,391 |
| Fits the slot | Yes - under the 55,836,672 limit with ~7 MiB to spare |
| `/dev/console` | present, real character device 5,1, `crw------- root/root` |
| SHA-256 | `95be8ec18a3dabad5e53e8467dc08ecbe4ead74d6e793dde17d7ec571d61130b` (matches `build_v19/images/SHA256SUMS`) |
| Boot result | "successful, confirmed by user" - `build_v19/reports/deployment.json` |

This is better than `rootfs_patched_v17_10s.img`: smaller and further inside the slot size
limit, a genuine device node rather than a pseudo-file, and a directly quoted user
confirmation of a successful flash and boot ("i flashed the rootfs using mtd, device booted
up fine"). The deployment record leaves `flash_command` and `target_partition` as null, so
the exact command and partition are not on record.

The v19 tree differs from the v18 tree in only four file contents (`bin/busybox`,
`etc/rc.local`, `usr/libexec/egrep-gnu`, `usr/libexec/fgrep-gnu`) plus 243 added applet
links; nothing is removed, and `dev/console` is explicitly retained as major 5 minor 1
mode 0600.

**The image is not the blocker any more - the write path is.** Everything else is ready: a
verified-good image with a real `/dev/console` that the user has already booted
successfully, a live interactive console on this bench, and an LK fastboot application
that is resident on every boot waiting for an enter event.

After any write: re-read the slot, check the SquashFS superblock magic and `bytes_used`
against the source, and compare a full SHA-256 of the written region against
`95be8ec18a3dabad5e53e8467dc08ecbe4ead74d6e793dde17d7ec571d61130b` before rebooting.

### The Preloader selector channel is reachable (2026-10-20)

First successful host-to-Preloader transaction of the session:

```text
preloader seen
claimed interface=1 in=0x81 out=0x01
pre-ready bytes=52 45 41 44 59          <- "READY"
```

The `0e8d:2000` USB link works, the CDC bulk interface is claimable, and the Preloader
emits `READY` on bulk IN exactly as `analysis/enter_x17m_meta.py` expects. The selector
channel is reachable from the host.

The FASTBOOT token was not acknowledged, and the cause was the test's own ordering: the
probe sent the partition probes (`0x71` + 64-byte name, `0x70` + 64-byte name) before the
selector token. The Preloader frames host commands in **fixed 8-byte units**
(`core/handshake_usb.c:192-243` sends `READY` "while no complete eight-byte token has
arrived"; `usb_handshake_handler` at `276-295` builds the descriptor with `cmd.len = 8`).
Those 130 bytes shifted the token boundary, so `FASTBOOT` was no longer aligned and the
dispatcher answered with more `READY` instead of `TOOBTSAF`.

Fixed: `work/fastboot_select.py` now sends `FASTBOOT` as the **first** write after
`READY`, with nothing in between, and the partition phase has been removed from that
script (it is closed offline anyway - `CFG_PRELOADER_AS_DA` is compiled out).

Useful measurement - the Preloader tool window varies with boot timing:

| Cycle | USB handshake total | Enumeration |
|---|---:|---:|
| 13:42 | 3313 ms | 2117 ms |
| 14:07 | 1895 ms | 1373 ms |

Both are usable, but the window can shrink, so the selector has to be the first action
after enumeration.

### The `FASTBOOT` selector WORKS (2026-10-20) - first accepted bootloader command

Host side:

```text
preloader seen
claimed interface=1 in=0x81 out=0x01
ready bytes=52 45 41 44 59                       <- READY
sending b'FASTBOOT' (first write)
post-selector bytes=52 45 41 44 59 54 4f 4f 42 54 53 41 46
FASTBOOT selector accepted (TOOBTSAF)
```

Device side, independently:

```text
[BLDR] 'FASTBOOT' received!
```

**Protocol lesson (confirmed).** The first attempt failed only because the partition-command
probes were sent *before* the selector token and shifted the Preloader's fixed 8-byte
command framing (`core/handshake_usb.c:192-243` sends `READY` "while no complete eight-byte
token has arrived"; `usb_handshake_handler` at `276-295` uses `cmd.len = 8`). The
Preloader answered with more `READY` instead of `TOOBTSAF`. With the selector as the first
write, it is accepted. **The selector token must be the first write after `READY`.**

**What changed on the device**, diffed against a normal boot of the same unit:

| Observation | Normal | `FASTBOOT` |
|---|---|---|
| `lk_b` load to `0x44000000` | SUCCESS | SUCCESS |
| `aee_lk` DRAM reservation at `0x43000000` | 2 MiB | 2 MiB |
| `aee_lk` image staged | no | **yes**, size 262,264 |
| `lk boot mode` | 0 | **still 0** |
| Outcome | boots Linux | **still boots Linux** |
| USB `0e8d:201c` | absent | absent |

So the selector genuinely changes the Preloader's behaviour - it now stages `aee_lk`, the
AEE/MRDUMP fastboot engine that `analysis/X17M_FORENSIC_REPORT.md` identifies at USB
`0e8d:201c`. But the LK still booted Linux with `lk boot mode = 0` and the endpoint never
appeared. Two hypotheses, neither proven: the boot-mode value is not propagated into the
LK handover in this build, or the LK's boot mode is a different variable from the one the
selector sets and the LK fastboot app still waits for its own `notify_enter_fastboot`
event.

**Consequence.** The LK fastboot endpoint is still unreached, and it would only be
diagnostic anyway (no `download:`/`flash:`/`erase:`, `set_active` is a stub). But this
establishes that the **Preloader command channel works and the host can drive the boot
flow**. The remaining gap is a *write* primitive, not a *control* primitive. The `aee_lk`
staging also shows the Preloader can read partitions and place images in DRAM - it is the
DAA-gated download dispatcher that is closed, not the partition machinery.

**Next test, now armed:** the `ADVEMETA` selector (`ATEMEVDX`), the last never-exercised
selector. It selects `ADVMETA_BOOT`, a different mode from `META_BOOT`, and may expose a
different service set - notably the `meta_tst` file-operation primitive, which is an
unrestricted `open()` on the target with a write-capable operation. It was never tested on
this unit because the META gadget needs a working Linux, which the broken slot B cannot
provide; `ADVEMETA` may not have that dependency.

### The `ADVEMETA` selector also works (2026-10-20)

```text
ready bytes=52 45 41 44 59
sending b'ADVEMETA' (first write)
post-selector bytes=52 45 41 44 59 41 54 45 4d 45 56 44 58
ADVEMETA selector accepted (ATEMEVDX)
sent DISCONNECT
```

`ATEMEVDX` is the acknowledgement the source correlation predicts for the `ADVEMETA`
branch, and this time `DISCONNECT` also wrote successfully (matching the source's
`wait_for_discon`). On the device side the META parameter block differs from a normal
boot - `META_COM TYPE: 2` and `META_COLOG_COM EN: 1`, versus `META_COM TYPE: 0` in a
normal boot - so the mode genuinely changes the META configuration rather than just being
acknowledged. The LK again continued to Linux and no `0e8d:202d` gadget appeared.

**All four non-factory selectors are now exercised live** on this unit:

| Selector | ACK | Result |
|---|---|---|
| `METAMETA` | `ATEM0001`/`ATEM0002`/`ATEMATEX` | accepted; META gadget seen on the *working* unit |
| `FASTBOOT` | `TOOBTSAF` | accepted; stages `aee_lk`; LK still boots Linux |
| `ADVEMETA` | `ATEMEVDX` | accepted; META params change; LK still boots Linux |
| `AT+NBOOT` | `AT+OK` | not tested; equivalent to a normal boot |
| `FACTFACT` / `FACTORYM` | `TCAFTCAF` / `MYROTCAF` | not tested; **factory modes are the highest-risk untested option and are not recommended** without a verified image |

The `CMD_HNDL_ATTR_COM_FORBIDDEN` gate did not trigger for `FASTBOOT` or `ADVEMETA` - no
`METAFORB` was returned.

**Where this leaves the recovery.** The control surface is now proven end to end: the host
can drive the Preloader's boot-mode dispatcher, and the Preloader can read partitions and
stage images into DRAM (`aee_lk`). The gap is a single flash-write primitive, and it is
blocked three independent ways - the DAA gate on the download dispatcher, the missing
`CFG_PRELOADER_AS_DA` `0x70`/`0x71` commands, and the LK's absent `download:`/`flash:`.

Practical options now that the image is ready:

1. a DA signed with the `a697...` key, or any DA the Preloader's DAA accepts;
2. a hardware/physical NAND write path for the slot-B rootfs partition;
3. **use the working 1 GB unit** - it boots normally, so its Preloader accepts some DA and
   its `mtd` tooling works. If a DA that the working unit accepts can be obtained, the
   same tooling can write the bricked unit's slot B, whose image is already prepared and
   verified.

### Consolidated status (2026-10-20)

**Proven working:** host <-> Preloader USB CDC bulk channel (READY received, `TOOBTSAF` and
`ATEMEVDX` acknowledged, device-side `[BLDR] 'FASTBOOT' received!` confirmed); the
Preloader boot-mode selector dispatcher; Preloader partition reads and DRAM staging
(`aee_lk`, 262,264 bytes); the interactive UART console.

**Proven closed:** DA upload (stock / ACC-bypass / unsigned - DAA signature, `9af8...` vs
`a697...`); Preloader SRAM read/write (crypto-gated); Preloader `0xDA` register access (not
implemented in Preloader mode); Preloader-as-DA `0x70`/`0x71` (`CFG_PRELOADER_AS_DA`
compiled out); LK fastboot `download:`/`flash:`/`erase:` (tokens absent); LK fastboot
`set_active` (stub); the LK fastboot endpoint (never enumerated even with `FASTBOOT`
selected); the `meta_tst` primitive on this unit (needs a working Linux); the failsafe
shell on the current image (no `/dev`); BROM Kamakiri (`mt0992` has no exploit parameters).

**The one remaining gap: a flash-write primitive.** Three independent paths would provide
it and all three are closed - the DAA gate, the compiled-out Preloader-as-DA commands, and
the LK's absent `download:`/`flash:`. The control surface around them works, so the gap is
now precisely characterised.

**Image side is fully prepared:** `build_v19/images/rootfs_bozax17_v19_xray_busybox.img`,
SHA-256 `95be8ec18a3dabad5e53e8467dc08ecbe4ead74d6e793dde17d7ec571d61130b`, 48,685,056
bytes, real `/dev/console` device 5,1, user-confirmed to boot.

**Options in order of expected value:**

1. **Obtain a DA the Preloader's DAA accepts.** Only a DA signed with `a697...` would
   qualify. The **working 1 GB unit** boots normally, so its Preloader accepts *some* DA.
   If that DA can be obtained, the same `mtkclient` flow that works on it will write the
   bricked unit's slot B. Highest value; needs the user's go-ahead since that unit is in
   service.
2. **A physical NAND write** of the slot-B rootfs partition - bypasses every software
   gate. The image is built and verified; only the transfer is missing.
3. **The unsigned DA** - one cheap test, armed now. Expected to fail with the same
   `0x7024`; a *different* status would still be informative.
4. **Factory boot modes** (`FACTFACT`, `FACTORYM`) - **not recommended.** A factory-mode
   device commonly exposes a write-enabled path that erases partitions on entry. With no
   verified backup of the bricked unit's own NAND and no working read path, an accidental
   erase would be unrecoverable. Only consider this if 1-3 are exhausted *and* a full
   verified backup of the bricked unit exists.

### Factory-mode selectors authorised and staged (2026-10-20)

The user has put every option on the table, including `FACTFACT` and `FACTORYM`. Protocol
per the source-correlated dispatcher:

```text
TARGET -> HOST: READY
HOST   -> TARGET: FACTFACT            (exactly 8 bytes, MUST be the first write)
HOST   -> TARGET: v1 record, 12 bytes
TARGET -> HOST: TCAFTCAF              (or MYROTCAF for FACTORYM)
```

The v1 record is the already-validated 12-byte `para_v1_t` used successfully by
`analysis/enter_x17m_meta.py` on this device:
`04 00 00 00 01 00 00 00 03 00 00 00`.

Why they are worth trying: `FASTBOOT` and `ADVEMETA` were both accepted but the LK
overrode them (`lk boot mode = 0`), so the LK ignored them. A factory mode is a
different LK/rootfs consumer, and factory images on this platform commonly expose a
download/flash service that ordinary boot paths do not.

**Risk position.** The selector transaction itself sends no flash command - it is a
RAM-only `g_boot_mode` change and a power cycle restores normal boot. The risk is in what
the device does *after* entering factory mode: a factory endpoint may offer an erase or
reformat, and this unit has no verified backup of its own NAND and no working read path,
so an erase would be unrecoverable.

**Mitigation.** `work/factory_select.py` is observation-only after the selector: token,
v1 record, `DISCONNECT`, then 120 s of passive USB polling. It sends no DA, no download
and no write command, and does not speak to whatever appears. If an endpoint enumerates,
the next step is to identify it and read its capabilities first. If it offers a write
path, the only acceptable target is the verified v19 image to only the slot-B rootfs
partition, with a re-read and SHA-256 check before rebooting. A whole-device erase or
reformat command is not acceptable without a verified full backup of the bricked unit.

Order: unsigned DA first (no mode change, cannot alter the device), then `FACTFACT`, then
`FACTORYM`.

**Status update (2026-10-20, later in the session).** The chained runner was stopped
before the `FACTFACT` stage ever reached a Preloader - `work/seq.log` ends at
`=== attempt 1/25 waiting for 0e8d:2000 ===` with no `TCAFTCAF`. So **neither factory
selector has been tested**: there is no `TCAFTCAF` or `MYROTCAF` acknowledgement anywhere
in the session logs. `work/factory_select.py` is written and validated but has never
completed a live transaction.

Meanwhile the unsigned-DA stage was also never actually exercised, because mtkclient
speaks the BROM download handshake rather than this Preloader's selector handshake (see
the "mtkclient cannot attach" note below).

### CORRECTED: the failed handshakes were a host-side client bug, not the reset button (2026-10-20)

I first attributed the failures to the router's reset button. The user confirmed they had
**not** pressed reset in any test, so that was wrong. Two separate things were going on,
and both are recorded below.

| | successful boot (`FASTBOOT` accepted) | failed boot (DA attempt) |
|---|---|---|
| `Enumeration(End): OK` count | **1** | **5616** (repeating) |
| `READY` seen on the wire | yes | **never** |
| host result | `TOOBTSAF` received | "Handshake failed, retrying..." x17 |

The Preloader reached `Enumeration(End): OK` and then re-ran the whole enumeration sequence
thousands of times without ever emitting `READY`. That is a Preloader stuck in a loop, not
a slow host.

The PMIC difference gives the cause:

```text
successful:  [PMIC]TOP_RST_STATUS[0x13C]=0x48     failed:  [PMIC]TOP_RST_STATUS[0x13C]=0x0
successful:  [PMIC]POFFSTS[0xE]=0x1                failed:  [PMIC]POFFSTS[0xE]=0x0
successful:  [pmic_check_rst] UVLO_RSTB            failed:  (absent)
successful:  [pmic_check_rst] PORSTB              failed:  (absent)
```

The successful boot had a genuine power-on reset (`UVLO_RSTB` and `PORSTB` both reported,
watchdog configured). The failed boot reported **no reset flag at all**, no watchdog setup,
and its SPMI reads returned `addr=0x0, data=0x0, cmd=0` - the PMIC was not answering the
Preloader's init traffic.

The Preloader binary contains the decisive string, next to `Enumeration(Start)`:

```text
%s Enumeration(Skip): powerkey pressed
```

The Preloader **skips USB enumeration when the power key is held**. The reset button is
wired to that key, so pressing it during power-up means the device never enumerates as
`0e8d:2000`, never emits `READY`, and no selector or download transaction can begin. That
also explains the earlier `error -110` (ETIMEDOUT) enumerations: the device was
half-enumerating on a bus the Preloader was not driving properly.

**Rule for the rest of this recovery: power-cycle only, never press reset.**

- Correct: unplug power adapter, unplug USB, wait 10 s, plug USB in, plug power in.
- Wrong: pressing/holding reset selects the "powerkey pressed" path, which skips USB
  enumeration, so every host-side loader test silently fails.

This is a test-harness artefact, not a device fault. The unsigned-DA test at 14:24/14:28
did not fail on its merits - it never got a Preloader to talk to. It should be re-run after
a clean power cycle, as should the `FACTFACT` / `FACTORYM` selectors, which remain
untested.

**1. Device side - that boot was degraded, not a different protocol.** The failed boot
differed from the successful one in the PMIC state:

```text
successful:  [PMIC]TOP_RST_STATUS[0x13C]=0x48     failed:  [PMIC]TOP_RST_STATUS[0x13C]=0x0
successful:  [PMIC]POFFSTS[0xE]=0x1                failed:  [PMIC]POFFSTS[0xE]=0x0
successful:  [pmic_check_rst] UVLO_RSTB            failed:  (absent)
successful:  [pmic_check_rst] PORSTB              failed:  (absent)
successful:  [pmic_wdt_set] TOP_RST_MISC1=0x25     failed:  (absent)
```

and its early SPMI reads all returned `addr=0x0, data=0x0, cmd=0`. The Preloader never
completed a power-on reset on that cycle: no `PORSTB`, no `UVLO_RSTB`, no watchdog setup, and
an SPMI bus that answered with zeros. Correspondingly, `Enumeration(End): OK` repeated
**5616 times** instead of once, `READY` never appeared on the wire, and the host reported
"Handshake failed, retrying..." 17 times. The device was in a degraded state that boot.

**2. Host side - a real bug in the rebuilt mtkclient.** `/tmp` was wiped mid-session, so
the patched client was rebuilt from upstream. Upstream discovers devices with
`usb.core.find(find_all=True, bDeviceClass=devclass, ...)`; that filter had to be relaxed
because this Preloader enumerates as a composite CDC device whose `bDeviceClass` is not 10
and was therefore never found. The first rebuild replaced it with an *unrestricted* search
over all `0x0E8D` devices, which lets the client latch onto the wrong product - including
the `0x0E8D:0x0003` BROM stage that the `usb_ids.py` patch exists to exclude. Fixed: keep
the `0x0E8D` vendor restriction and require the device to expose a CDC data interface,
instead of accepting every MediaTek device on the bus.

**Still true, just not the cause here:** the Preloader contains
`%s Enumeration(Skip): powerkey pressed`, so holding the power key during power-up makes
it skip USB enumeration and no host transaction can begin. Useful to know; not what
happened.

**Next:** the unsigned-DA test and the `FACTFACT` / `FACTORYM` selectors were never
actually exercised against a healthy Preloader - re-run them. If the `Enumeration(End)`
loop and the missing `PORSTB`/`UVLO_RSTB` reappear, that is a device-side condition of
that boot; try a different power source or leave it unpowered longer so the PMIC rail
fully discharges.

### Sequencing lesson: one test per power cycle (2026-10-20)

Chaining several tests into one script that runs them back to back was the wrong design
and the user called it out. Each stage needs its own Preloader window, so a chained
runner desynchronises as soon as one stage misses its window - the remaining stages then
consume power cycles that were meant for earlier tests. One armed test, one power cycle,
one unambiguous result.

### The three power cycles at 14:42 were all healthy - and the host still missed them

The UART capture of those three boots shows each one was in good shape:

| boot | `Enumeration(End)` count | reset flag reported |
|---|---:|---|
| 1 | 1 | `PORSTB` |
| 2 | 1 | `UVLO_RSTB` |
| 3 | 1 | `UVLO_RSTB` |

So the device was fine, and the earlier degraded-boot symptoms did not recur. The host
side, however, reported "Handshake failed, retrying..." and never logged "Device
detected".

**Why mtkclient cannot attach to this Preloader.** Upstream mtkclient's handshake
(`Library/Port.py:128` `run_handshake`) sends the 4-byte BROM download start sequence
`A0 0A 50 05` and expects the inverted echo `5F F5 AF FA`. That belongs to the **BROM
download dispatcher** (`download.c:usbdl_handler`). This Preloader's USB service is the
**selector dispatcher** (`core/main.c:bldr_cmd_handler`), whose `usb_listen()` loop emits
`READY` repeatedly and waits for an 8-byte token - it does not answer `A0 0A 50 05` at
all. That is why the raw-pyusb selector probes worked and the mtkclient DA probe never
attached.

This also means the whole family of mtkclient-based tests in this session
(`pl_da_only.py`, `pl_da_unsign.py`) were driving the wrong protocol for this device.
The unsigned-DA test is therefore **not yet actually exercised**; it needs a client that
speaks the selector/download handshake the Preloader really implements.

### The important new finding: the Preloader does set the mode, the LK just does not use it

Comparing our boots with the working 1 GB unit's META capture
(`analysis/live_meta_uart/20260918T122836Z_attempt3/uart_printable.txt`):

| selector | `BOOT_MODE` in the Preloader boot tag | `lk boot mode` reported |
|---|---:|---:|
| `FASTBOOT` | **99** | 0 |
| `ADVEMETA` | **5** | 0 |
| normal | 0 | 0 |

`99` and `5` are exactly the SDK values for `FASTBOOT` and `ADVMETA_BOOT`
(`analysis/X17M_PRELOADER_SOURCE_CORRELATION.md` section 7). **The selector works and the
Preloader records the mode correctly** - it is lost on the way to the LK, which is handed
control via ATAG at `0x42B00000`.

The working unit's capture contains **no `BOOT_MODE` line at all** yet the LK still
reported `lk boot mode = 1` in its META boot. So the LK takes the mode from a different
handover than the Preloader's boot-tag field, and on the working unit that handover
carried it.

**Consequence.** `METAMETA` is the mode worth testing, because it is the only one the
working unit demonstrably propagated all the way to Linux: `lk boot mode = 1` -> the
`0x202d` Linux META gadget -> the `meta_tst` primitive, which is an unrestricted `open()`
on the target with a write-capable operation and **no DAA gate**. `METAMETA` has never
been tested on this unit.

`work/meta_select.py` implements the exact transaction already validated on the working
unit:

```text
READY -> METAMETA -> ATEM0001 -> V1(12) -> ATEM0002 -> V2(16) -> ATEMATEX -> DISCONNECT
V1 = 04 00 00 00 01 00 00 00 03 00 00 00
V2 = 06 00 00 00 01 00 00 00 03 00 00 00 01 00 00 00
```

It is armed now, alone, and observes USB identities passively afterwards so that a newly
appearing endpoint can be identified before anything is sent to it.

### Host stability: the USB polling was too aggressive (2026-10-20)

Kali froze and needed a hard reboot for the second time during this session. Both freezes
happened while a probe was polling USB in a tight loop, so the polling was made
substantially gentler:

- `usb.core.find()` polling interval raised from **5 ms to 100 ms**. A Preloader window is
  1895-3563 ms, so 100 ms still gives 20-35 polls per window - ample to catch it - while
  cutting the libusb/VMware-passthrough traffic by 20x.
- The passive USB-observation loop raised from 50 ms to 250 ms.
- A 2 s pause was added after any exception in the attempt loop, so a transient USB error
  cannot turn into a tight retry loop.

All probes in `work/` (`meta_select.py`, `factory_select.py`, `fastboot_select.py`,
`advemeta_select.py`, `fast_part_probe.py`, `handshake_probe.py`) were updated
consistently.

**Also changed: one test at a time.** The chained runner `run_all.sh` was removed in favour
of arming a single test per power cycle. Chaining desynchronises as soon as one stage
misses its window, and each stage needs its own Preloader window anyway.

Note the USB topology changed after the reboot: the FTDI now enumerates on `bus 2`
(`xhci_hcd`) rather than `bus 3`, and the router's passthrough controller is not currently
enumerating at all.

### Refined procedure: the PMIC reset flag is the discriminator (2026-10-20)

A boot captured after the second host crash isolates the last variable. Comparing the
boot where the host attached successfully with the boot where it never saw `0e8d:2000`:

| | successful | failed |
|---|---|---|
| `pmic_check_rst` | **UVLO_RSTB** | **DDLO_RSTB** |
| `[PMIC]TOP_RST_STATUS[0x13C]` | `0x48` | `0x40` |
| `[PMIC]POFFSTS[0xE]` | `0x1` | `0x201` |
| `[PMIC]POWER_HOLD` | `0x1` | `0x1` |
| `powerkey_flag` / `powerkey_val` | `0` / `0` | `0` / `0` |
| host saw `0e8d:2000` | **yes** | **no** |

**The power-key state is identical in both boots**, which independently confirms the
reset button was not what was pressed in the failed case. The discriminator is the PMIC
reset flag:

- `UVLO_RSTB` - undervoltage reset, the supply actually collapsed. This is a **full
  power-off**. The good boot had it, with `TOP_RST_STATUS` bit 3 set (`0x48` vs `0x40`) and
  `POFFSTS = 0x1`.
- `DDLO_RSTB` - digital brown-out low, a **drooping supply during a warm reboot**. The
  failed boot had it, with `POFFSTS = 0x201` (brown-out latch) and bit 3 clear.

**So the requirement is stricter than "don't press reset": unplug the power adapter and
leave it unplugged long enough for the PMIC rail to discharge fully.** The bootloader log
gives the check directly - look for `pmic_check_rst] UVLO_RSTB` (good, the host can
attach) rather than `DDLO_RSTB` (brown-out, the host cannot attach).

This also explains the earlier degraded boot, where `Enumeration(End): OK 2296ms` repeated
5616 times: with a browned-out supply the Preloader re-ran enumeration indefinitely and
never completed a clean one, so `READY` was never emitted and no host transaction could
start.

The power key remains a *separate* hazard - holding it during power-up makes the
Preloader take the `Enumeration(Skip): powerkey pressed` path and skip USB enumeration
entirely - but it was not what happened in these boots.

### METAMETA accepted on this unit, and it reaches Linux (2026-10-20)

Host side:

```text
ready bytes=52 45 41 44 59
sending b'METAMETA' (first write)
ack1 = ATEM0001 / ack2 = ATEM0002 / ackf = ATEMATEX
METAMETA selector accepted (ATEMATEX)
sent DISCONNECT
METAMETA_SELECTED=YES
```

Device side:

```text
[BLDR] 'METAMETA' received!
BOOT_MODE: 1
META_COM TYPE: 2
META_COM ID: 3
boot_linux_fdt:671: lk boot mode = 1
```

**This is the first mode that has propagated all the way into Linux on this unit**, and
it settles the question from the `FASTBOOT`/`ADVEMETA` runs. Those two set the
Preloader's `BOOT_MODE` to 99 and 5, but the LK still reported `lk boot mode = 0`.
`METAMETA` sets `BOOT_MODE: 1` **and** the LK reports `lk boot mode = 1` - the same value
the working unit only ever showed in its META boot. So the LK acts specifically on
`META_BOOT`; it does not act on a generic boot-mode field.

**The `0x202d` META gadget still did not appear.** The kernel booted in META mode, ran to
userspace, and stopped exactly as always:

```text
/etc/preinit: line 0: can't open '/dev/null': No such file or directory
```

A scan of the 1.4 MB capture finds no `202d`, `usb gadget`, `g_dnl` or `configfs` at all.

**Reason:** the `0x202d` gadget and the `meta_tst` service are both *userspace*
components - `/etc/restart_usb.sh` creates the gadget and `/usr/bin/meta_tst` is the
service, both inside the rootfs. The broken slot-B rootfs has no `/dev`, so devtmpfs never
mounts and that userspace cannot run. The kernel is in META mode, but there is nothing
userspace-side to act on it.

**That closes the META route on this unit:** the mode reaches the kernel correctly, and
the mode alone is not enough - it needs a rootfs with `/dev`, which is the very thing
being installed. The circularity is now explicit, which is why a write primitive (not a
mode) is what is needed.

**Status of the selector surface, all now tested except the factory pair:**

| Selector | ACK | `BOOT_MODE` | `lk boot mode` |
|---|---|---:|---:|
| `METAMETA` | ATEMATEX | 1 | **1** |
| `FASTBOOT` | TOOBTSAF | 99 | 0 |
| `ADVEMETA` | ATEMEVDX | 5 | 0 |
| `FACTFACT` | - | not tested | not tested |
| `FACTORYM` | - | not tested | not tested |

The two factory modes are the last untested boot modes and are the only ones that might
expose a write-enabled service the three above did not. `work/factory_select.py` is ready
for them, observation-only after the selector.

### An `auth_sv5.auth` artifact exists on disk - supersedes an earlier audit conclusion (2026-10-20)

`analysis/MT6890_DA_BR_SIGNATURE_KEY_AUDIT.md` says: *"No `customer_da.auth` or
`auth_sv5.auth` file exists in the extracted workspace, so an embedded-auth blob could not
be parsed or matched directly."*

**That is now superseded.** There is one at `/home/kali/Desktop/x17m/auth_sv5 (1).auth` -
2256 bytes, mode 0600, dated 2026-09-22 01:28, i.e. created during the earlier DAA
investigation. The earlier audit only searched inside the extracted SDK/firmware workspace
and missed it.

Parsed against the documented GFH layout it is a structurally valid tool-auth object:
GFH magic `0x014d4d4d`, identifier `FILE_INFO`, `GFH_TOOL_AUTH` type 5 size `0x798` at
`0x38`, GFH total `0x7d0`, then a 256-byte signature at `0x7d0`. All three `ct_ce_key`
blocks are well formed.

**Its keys are a surprise - a third key set:**

| Block | modulus SHA-256 |
|---|---|
| SBC/root | `660774dea40fba0a8fb532a8bb2c941cc4b1812bb3372dd6cf64374bb19473ac` |
| SLA | `8964c8a8a8dc97a16577cec8021f193f0e5924c8962c49e69c04f78858e494ac` |
| DAA | `660774de...` (same as SBC) |

The DAA key here is **neither** `9af8a28b...` (which signs our `DA_BR.bin`) **nor**
`a697414d...` (the `dakey.h` `DA_PUBK` the Preloader's checker installs). So the DAA key
is **customer-provisioned**, not the SDK development key - which is consistent with the
forensic report's caution that the device's BootROM/eFuse state is authoritative.

The 256-byte signature does **not** verify against either embedded key, under PSS/MGF1-
SHA256 (salt 32 and MAX_LENGTH), PSS/MGF1-SHA1, or PKCS#1 v1.5, over the raw GFH or a
pre-hashed digest. So it is either a template, generated for a different key set, or signed
over a different GFH encoding.

**Worth one cheap live test.** The Preloader exposes `SEND_AUTH` (`0xE2`) and `SEND_CERT`
(`0xE0`). Sending this artifact asks the device to evaluate an authorization; a status
*other than* `0x7009` ("no DA staged / association failure") would be a completely new
result. Neither outcome writes to flash. It must go through the handshake this Preloader
actually implements (the selector/download path), not mtkclient's `A0 0A 50 05`.

**This does not unlock the DA.** Three different DAA keys are now in play and we hold no
private half of any of them, so "find the right key" is a *provisioning* question - what
was this unit's BootROM/eFuse provisioned with - rather than an SDK-key question.

### `FACTFACT` accepted - `BOOT_MODE: 4` - and the LK ignored it too (2026-10-20)

Full transaction completed:

```text
ready bytes=52 45 41 44 59
sending b'FACTFACT' (first write)
sending v1 record 04 00 00 00 01 00 00 00 03 00 00 00
post-selector bytes=52 45 41 44 59 54 43 41 46 54 43 41 46
selector accepted (b'TCAFTCAF')
SELECTOR_ACCEPTED=YES mode=FACTORY_BOOT
```

Device side:

```text
[BLDR] 'FACTFACT' received!
BOOT_MODE: 4
boot_linux_fdt:671: lk boot mode = 0
```

`BOOT_MODE: 4` is the SDK value for `FACTORY_BOOT`, so the Preloader consumed the v1
record and recorded the mode correctly. But the LK then reported `lk boot mode = 0` and
booted Linux normally, exactly as with `FASTBOOT` and `ADVEMETA`. No factory endpoint, no
`0x201c`, no `0x202d`, and no download/flash/erase activity in the 349 KB capture.

**The complete selector matrix, all measured on this device:**

| Selector | ACK | `BOOT_MODE` | `lk boot mode` | Outcome |
|---|---|---:|---:|---|
| `METAMETA` | ATEMATEX | 1 | **1** | Linux in META mode; gadget blocked by the broken rootfs |
| `FASTBOOT` | TOOBTSAF | 99 | 0 | `aee_lk` staged; LK booted Linux |
| `ADVEMETA` | ATEMEVDX | 5 | 0 | META params changed; LK booted Linux |
| `FACTFACT` | TCAFTCAF | 4 | 0 | **LK booted Linux** |
| `FACTORYM` | - | (6) | ? | not yet tested |

**Only `META_BOOT` is acted on by the LK.** Three different non-META modes (4, 5, 99) are
accepted and recorded by the Preloader and the LK ignores every one of them. That is now
a measured property of the device rather than an inference.

**The factory mode exposed no write service here** - which was the specific reason for
testing it, and the answer is negative. Whatever `FACTORY_BOOT` does on this platform, it
is not reachable through the selector path on this unit, in the same way `FASTBOOT` did
not reach the LK's fastboot engine.

Only `FACTORYM` remains untested among the factory pair. It is the ATE variant of the
same mode (`BOOT_MODE: 6`), with the same `recv(v1, 12, 5); save usb type; send(...)`
structure and a different acknowledgement (`MYROTCAF`), so the prior is that the LK will
ignore it too - but it is worth one cycle for completeness.

### ROOT CAUSE of the "missed windows": the FTDI and the router share one USB controller (2026-10-20)

The user observed that the power cycle is only detected *after* the UART adapter is
disconnected. That turned out to be the key to the whole "the host never attaches"
pattern, and `dmesg` confirms it.

**The router and the FTDI are on the same physical USB controller**, so a router power
cycle also drops the FTDI's USB link:

```text
15:33:15  usb 1-1: USB disconnect, device number 8        <- router (bus 1, ehci-pci)
15:33:57  usb 2-1.3: USB disconnect, device number 10     <- FTDI   (bus 2, xhci)
15:34:00  usb 1-1: new high-speed USB device number 9     <- router back
15:34:01  usb 2-1.3: new full-speed USB device number 11  <- FTDI back
```

They come and go **together**, and the host USB stack is busy re-enumerating one while the
other is supposed to be talking to it.

**This silently broke the UART capture.** A plain `cat /dev/ttyUSB0` opens the port once
and holds that descriptor. When the FTDI re-enumerates, `/dev/ttyUSB0` is recreated and the
old descriptor is dead, so the capture records **nothing** for the whole window that
matters. That is the `device reports readiness to read but returned no data (device
disconnected or multiple access on port)` error seen earlier, and the reason some
captures were exactly 0 bytes precisely while a test was running.

**It also explains the host-side handshake failures.** If the host is speaking to the
router's Preloader at the moment the FTDI is re-enumerating on the same controller, the
router's session is disturbed. The `Enumeration(End): OK` repetition and the differing PMIC
reset flags in section 22 are consistent with this - the router's USB session was being
disturbed by the FTDI's re-enumeration, not failing on its own.

**Fix applied.** `work/uart_watch.py` replaces the plain `cat`:

- re-resolves the port by **VID:PID** (`0403:6001`) rather than by device name;
- reopens it automatically whenever it disappears;
- appends to one log with a `=== [uart_watch] (re)opened ... ===` marker at each open, so
  boot boundaries are unambiguous in the capture.

**Better fix if the hardware allows.** Put the FTDI on a different USB controller or power
domain from the router - a USB isolator, or a hub with its own supply for the FTDI. The
host already shows the router on bus 1 (`ehci-pci`) and the FTDI on bus 2 (`xhci_hcd`), but
they are evidently on the same physical hub or power domain, since one goes down with the
other.

**Bench sequence from now on:** plug in the FTDI and confirm `ttyUSB0` exists; start the
host test and `uart_watch.py`; power-cycle the router; expect the FTDI to drop and return -
the capture now reconnects and keeps recording.

### Manual bench workflow, and the real reason the window is missed (2026-10-20)

Chaining is gone. The bench is now one script, `work/x17m_bench.py`, run one test per
power cycle, with the operator guide in `work/BENCH.md`:

```bash
cd /home/kali/Desktop/x17m/work

python3 x17m_bench.py status                              # what does the host see?
python3 x17m_bench.py select --selector factorym         # send ONE selector
python3 x17m_bench.py uart --seconds 900 --out uart.log  # resilient console capture
python3 x17m_bench.py summarise uart.log                  # read the capture
```

`select` polls at 50 ms, claims the device the instant it appears, and reports one of
four unambiguous outcomes (ACCEPTED with the ACK / no 0e8d:2000 seen / READY never
arrived / ACK not received). After a successful selector it watches USB identities
passively and never speaks to anything it finds.

**The Preloader window is much shorter than I had assumed.** The two cycles captured by
the resilient logger at 15:35 and 15:46 show:

```text
15:35:  [TOOL] Enumeration(End): OK 835 ms
15:46:  [pmic_check_rst] UVLO_RSTB
        [TOOL] Enumeration(End): OK 835 ms
```

**835 ms**, not the 1900-3600 ms measured earlier. Both shortest observations coincide
with the router enumerating and the host failing to attach - which is exactly what
happened on the 15:46 cycle: the probe was running, the device enumerated at 15:46:33, and
the window closed before the host could claim it. A host application needs to find and
claim the device in well under a second.

This also confirms the earlier 15:46 boot was a *good* one (`UVLO_RSTB`, a real power-off)
- so the miss was timing, not device state.

**A phantom enumeration was also observed.** At 15:46:33 the host logged
`usb 1-1: new high-speed USB device number 12` with no `New USB device found`, no
disconnect, and no `1-1` entry in sysfs. The device took a bus number but never completed
enumeration, so it is invisible to `lsusb` and pyusb while still occupying a slot in the
host USB stack. `x17m_bench.py status` reports this case explicitly, because it also
explains a probe that sees nothing at all.

**Sequencing that works:** terminal A runs `uart`, terminal B runs `select`, then
power-cycle with the adapter unplugged for 30 s+ (so the PMIC rail fully discharges and
the boot reports `UVLO_RSTB` rather than `DDLO_RSTB`), then read the result from
terminal B and summarise from terminal A.

## 16. Community repo evaluation sprint (2026-11-03)

- Evaluated `armarchindo/advan-v6-flasher` (not applicable), `mralinp/zlt-x28-openwrt`
  (proven read/write tooling on hwcode 0x992; end-game playbook), and the whole
  `mt6890-cpe-recovery` ecosystem (7 SPFT packages downloaded and mined).
- Every community DA resolves to the already-rejected `c3d9058a…` (2023-06-28), except
  the X25 package's `MTK_DA_v6_2023-12-28` (`c873d21d…`) - saved as
  `work/dax28/DA_X25_20231228.bin`, the only never-tested live candidate.
- External confirmation of our exact failure class: mtkclient#88 "silent update that
  the DA files won't work anymore" (Lucas-Liam) and the unanswered
  `safuapy/zlt-x28-unbrick#1` "DA file for the new zlt x28 pro or zlt x17m".
- Offline findings: neither 2025 preloader stores any known DA key plaintext;
  `MTKKEYDERIVATION` string shows the locked generation derives keys; X25-DA vs ~65k
  preloader key-region windows: no verification; both 2025 preloaders share cert-chain
  structure but have different key-cert moduli (ours `c16649a5…`, X25 `00d1fd5c…`).
- Wrote `work/pl_da_x25.py` (same driver as validated `pl_da_unsign.py`, pointing at
  the X25 DA). Awaiting the operator's power-cycle run; non-destructive DAA probe only.

## 17. X25-DA live verdict + F0/F3 lines explained (2026-11-03, second cycle)

- Operator ran `work/pl_da_x25.py`: clean attach (hwcode 0x992, config 0x5, SBC+DAA),
  then `DAA_SIG_VERIFY_FAILED (0x7024)` on the X25 2023-12-28 DA. Every public DA is
  now conclusively rejected. Unit continued boot normally after the window closed.
- New datum: bricked unit `ME_ID AD2E009BFAC7B8BF397ADDD7370986D4` (per-unit; the
  working unit's is `7D2DEDE9…` per the September probe). Citable for vendor
  provisioning of DA+auth.
- Build divergence discovered: bricked unit Preloader `20251203-032240` (all
  captures), working unit `20250909-103520` (dump). The working unit's preloader dump
  is family-level ground truth only, not unit-level.
- The post-test `F0: 102B … / F3: 1001 … / Jump to BL` lines are the Preloader's
  standard hand-off index log, routed to the tool during a session; the plain UART
  capture of the follow-up boot shows the usual preloader→LK hand-off without that
  block. Benign; no persistent device change.


## 18. SSH-over-TLS transport repair (2026-11-06)

On the working BOZAX17 router, incoming SSH port 22 is refused because the image has client/tunnel support rather than an SSH server. Telnet root login works; vendor HTTP is :80, LuCI is :4153. Initial screenshot showed Shadowsocks selected and `xray.general.service=0`, explaining absent Xray listeners.

The intended outgoing SSH-over-TLS endpoint, `ip.crispdev.online:443`, expects SSH directly inside TLS. The legacy proxy sent an HTTP Upgrade request first, causing `Bad packet length 1231976033` and an SSH MAC error. A standalone direct-TLS test authenticated and returned exit IP `172.235.157.43`.

An initial PROXY_CMD override in /etc/sshtun/sshtun.conf was overwritten by xray-generate-config when the profile was selected in LuCI. The durable live correction modifies /usr/bin/sshtun-proxy to read `xray.sshtls.transport` (or SSHTUN_TRANSPORT). `tls` executes the TLS relay directly; other/unset values preserve legacy HTTP Upgrade. Set and committed `xray.sshtls.transport=tls`. Original script is backed up as /usr/bin/sshtun-proxy.before-transport-20261106.

The page's actual xray-check-status returned CONNECTED through Xray and SSH, exit IP 172.235.157.43, 1520 ms. After config regeneration and sshtun restart, an immediate check timed out during reconnection; the subsequent check returned CONNECTED at 980 ms. Left Xray running on sshtls. No reboot or LAN-client coverage test performed. Firmware build artifacts remain unchanged; include the repair in the next build.

Detailed operating commands, rollback, verification limits, and proposed improvements: [SSH TLS repair notes](../bozax17/XRAY_SSH_TLS_FIX_20261106.md). No credentials included in these notes.


## 19. Transport/UI/probe improvements (2026-11-06)

Implemented transport selector, bounded Connecting state, SSH-aware probes and watchdog integration, isolated generator temporary files, shell-profile quoting, Xray/SSH lifecycle coordination, HTTPS-time label and TCP-only coverage notice. Used live scripts to preserve fixes missing from v19 sources.

Final end-to-end status CONNECTED, exit IP 172.235.157.43, HTTPS time 860 ms. Active and isolated SSH probes pass; invalid transport rejected; Lua/template and shell checks pass; 11 deployed files verified by checksum. Automatic failover remains off. Source overlay, backups, manifest and build instructions: [firmware-next](../bozax17/firmware-next/README.md). No firmware built/flashed; reboot and LAN coverage remain untested.

## 20. Connection log panel (2026-11-06)

Added live filtered connection logs to Xray overview, with refresh/pause, source selection and follow-latest. Authenticated endpoint is bounded, redacts saved credentials and URI links, and disables caching. Pinned /sbin/logread to avoid PATH selecting incompatible BusyBox logread. Live HTTP checks pass, unauthorized access denied, VPN remains CONNECTED. Firmware-next overlay and manifest updated; no image built/flashed.

## 21. SSH connection-load investigation (2026-11-06)

SSH reached 1,010/1,024 descriptors; forwarded load concentrated on 192.168.0.163. User stopped Netch. Without restarting services, SSH descriptor use drained to 92 and CLOSE_WAIT to 46; HTTPS check CONNECTED at 850 ms. Strong evidence of client workload exceeding SSH capacity, not a persistent leak. Read-only findings: [investigation](../bozax17/firmware-next/CONNECTION_LOAD_INVESTIGATION.md). No limits or firmware changed.

## 22. Netch guard proposal and refreshed X28 review (2026-11-06)

Reviewed both user-supplied X28 repositories. mralinp now documents custom TPROXY modules/Passwall2 TCP+UDP+IPv6 on vendor 4.19.205; this is useful design evidence, not binary compatibility with our 5.4.238 kernel. Recovery tools have moved to a currently private repository according to its README. Proposed SSH soft-limit headroom plus per-client admission controls/monitoring, not deployed. Details: [review](../bozax17/firmware-next/NETCH_GUARDS_AND_X28_REVIEW.md).

## 23. Netch connection guards deployed (2026-11-06)

After user reduced Netch entries, applied SSH nofile 4096, IPv4 transparent-proxy admission caps (512/client, 2048 overall) and 40 NEW SYN attempts/client/second. Added LuCI settings and load/reject counters. Matching kernel modules present. Isolated loopback cap/rate tests passed; final live VPN CONNECTED, 1040 ms, 277 accepted/0 rejected attempts. Firmware-next overlay, boot defaults and manifest updated; no firmware build/flash or reboot. Details: [connection guards](../bozax17/firmware-next/CONNECTION_GUARDS.md).

## 24. X28 kernel-module source investigation (2026-11-06)

Traced custom modules, missing-UDP-export shim, CRC workaround and guarded loader. Live X17M 5.4.238 configuration reconfirmed; offline kernel export-reference candidates support a similar wrapper gap. Upstream 5.4 loader behavior raises an additional no-version-section acceptance constraint with force-load disabled. Exact BSP/ABI records remain missing; no modules installed/loaded or firmware changed. [Report](../bozax17/openwrt-port-feasibility/x28-module-study/REPORT.md).

## 25. DNS tunneling implemented (2026-11-06)

Separate Xray DNS listener on LAN :1053 converts ordinary IPv4 LAN UDP/TCP DNS to TCP upstream via main Xray SOCKS :10808 and selected SSH/VPN. Preserved vendor DHCP and direct router bootstrap DNS. Enabled service, interception keeper and Servers toggle; verified A/AAAA/TXT/local names, TCP requests, direct-upstream-block test and listener-outage/recovery. Main VPN remains CONNECTED. General UDP/IPv6/encrypted-DNS coverage is unchanged. [Details](../bozax17/firmware-next/DNS_TUNNEL.md). No firmware build/flash.

## 26. UDP-in-TCP/TUN investigation (2026-11-06)

Validated installed Xray TUN configuration and short-lived device creation without automatic/default routes; lab device removed and carrier default preserved. Investigated matching Hev UDP-in-TCP endpoints, BadVPN UDP gateway and sshuttle requirements. Current SSH -D alone remains insufficient: a remote UDP-aware relay/profile or executable session is required. No remote shell or production UDP routing change performed. [Detailed plan](../bozax17/openwrt-port-feasibility/udp-tunnel-study/REPORT.md).

## 27. Systemwide direct UDP block (2026-11-06)

Enabled IPv4/IPv6 OUTPUT/FORWARD UDP rejection with local-service exceptions. Added TCP bootstrap DNS instance/OUTPUT local redirect to preserve SSH resolution without public UDP DNS. Verified bootstrap and LAN VPN DNS, reject counters and VPN connectivity. Cleared existing LAN UDP conntrack states. Sources, boot defaults, UI toggle and notes staged. No reboot/flash; vendor hardware-cache and reset windows documented in [UDP_BLOCK.md](../bozax17/firmware-next/UDP_BLOCK.md).

## 28. Clock consistency and forwarding guard (2026-11-06)

Found correct UTC clock but conflicting UTC/UTC+3/UTC+8 display settings. User chose Nairobi; aligned vendor storage, UCI and zone files. Added two-source verified HTTPS time service, daily last-good checkpoint and Overview clock panel; blocked UDP NTP disabled. Vendor GUI manual field uses browser time; device field uses backend systime. Web login unverified. Added IPv4/IPv6 LAN forwarding rejection, early startup and iface repair hooks; software rejects observed and VPN remains connected. Management hardening skipped. [Full report](../bozax17/firmware-next/CLOCK_AND_FORWARDING.md). No firmware build/reboot/flash; reset/offload assurance still needs controlled testing.

## 29. Vendor firewall reload validation (2026-11-06)

Identified vendor firewalltools ownership; fw3 boot disabled. Discovery --help unexpectedly launched an extra worker; stopped only extra PID and restored/check policy, documented incident. Added shared priority-aware policy restore and mangle reload gate/completion hooks to full/NAT vendor scripts. Two full applies, NAT apply, temporary enabled admission-cap test and failed-completion gate retention/recovery passed. Restored user guard.enabled=0 preference; DNS/UDP blocking remain on. Final VPN CONNECTED at 910 ms; DNS/LuCI available. Six hashes verified; source/snapshots/logs saved. [Report](../bozax17/firmware-next/FIREWALL_RELOAD_VALIDATION.md). Hardware/daemon/reboot assurance remains separate; no image built/flashed.

## 30. v20 rootfs candidate built and fully verified (2026-11-06)

User confirmed earlier BOZA working tree rootfs_bozax17_v17_10s_meta_rndis_dialer_auto. Compared it with v19: nine changed shared contents; remaining BOZA dialer/META/RNDIS files match. Used verified v19 image for fresh fakeroot extraction/device metadata, merged tested firmware-next overlay and ten current private configuration/account/trust inputs; preserved dialer/rc.local and /data symlinks. Baked service startup links. Full pack/re-extraction content and metadata match; no removed paths; console character 5:1 preserved.

Output: /home/kali/Desktop/bozax17/firmware-next/build-v20-20261106/images/rootfs_bozax17_v20_vpn_guard_dns_clock.img
SHA-256: 64a1445bea677a8c19e4d2dd757d32f7ac3d42e4280b7521f688cebdbd89e2d4
Size 48,697,344 bytes; headroom 18,411,520 bytes in 64 MiB rootfs budget. Private candidate contains current credentials and needs existing /data assets. No flash/reboot. Reports/source/comparison/checksums stored beside image. Build validation is not boot validation; overlay/partition/recovery review remains before flashing.

## 31. VPN disable regression fixed; v20 withdrawn (2026-11-06)

User reported network stuck after disabling Xray. Found unconditional forwarding guard plus stale enable/settings lifecycle and missing independent bootstrap resolver. Unified effective VPN state; explicit disable restores direct forwarding/DNS, enabled outage remains protected, independent UDP-block setting preserved. Actual LuCI Stop/Start and checkbox/state tests passed; current Shadowsocks profile/settings restored. Twelve hashes verified. Prior v20 image withdrawn and renamed .img.superseded, not flashed; corrected overlay needs rebuild. [Details](../bozax17/firmware-next/TOGGLE_FIX.md).

## 32. Corrected v21 with v14 Simple Adblock (2026-11-06)

Deleted superseded v20 image/checksum as requested. Inspected v14 image aed4e1be985aec9d9c238bb018607e5c553323ea4e6bb4e93105c119310f83e8 plus historical rootfs_changes.txt and data/adblock orchestration. Restored Simple Adblock 1.8.8-1/LuCI/feed/custom policy, normalized 175,193 cached rules plus 21 provider domains. Added dedicated DNS-only frontend on :1056, preserving vendor DHCP and current VPN/direct TCP DNS. Avoided old global dnsmasq/lan_mgr kills. Verified cache start, allowed/blocked/local resolution, VPN stop/start, tunneled DNS, adblock toggle, controlled downloader fixture and firewall reload; settings restored. Bootstrap resolver works with adblock independently of UDP-block state.

Final v21 image: /home/kali/Desktop/bozax17/firmware-next/build-v21-20261106/images/rootfs_bozax17_v21_corrected_simple_adblock.img
SHA-256: 936c40765190946b9e9c6bfbff6f09ece6a27daa4e09d48ae27c1603ba164cca
Bytes: 49,881,088; headroom 17,227,776 in 64 MiB budget. Complete extraction/metadata match and checksum verification passed; BOZA dialer/startup/console preserved. Requires /data assets and contains private credentials. No flash/reboot. [Integration](../bozax17/firmware-next/SIMPLE_ADBLOCK_V21.md).

## 33. Recovery readiness and X28 cross-reference (2026-11-06)

Read-only current-unit check: slot A, rootfs_a mtd29/rootfs_b mtd43, JFFS2 overlay and UBIFS /data; preloader hash matches working September-2025 reference. Serial-preference failsafe hook and console nodes present; earlier v17 UART-shell success is historical, not a new current-unit test. Reviewed both user-supplied X28 projects plus safuapy unbrick; mralinp guarded USB workflow is a useful design but flasher repo inaccessible (404), and DA/layout compatibility remains unproven. Do not transfer all-public-DA-failed result from the separate December-2025 bricked unit. Corrected shared-overlay assumption: active rootfs split can move with new image size. [Readiness report](../bozax17/openwrt-port-feasibility/reports/recovery-readiness-20261106.md). No writes/reboots/DA operations.
