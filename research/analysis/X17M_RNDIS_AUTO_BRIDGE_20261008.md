# X17M persistent RNDIS bridge candidate

Built after the user confirmed that manually attaching `rndis0` to `br0`
restored PC Internet access. This candidate adds an enabled procd service and
watcher that repeatedly brings `rndis0` up and attaches it to `br0` (or
`br-lan` if `br0` is absent). The watcher handles the interface appearing
after boot or returning after USB re-enumeration. It only bridges RNDIS; it
does not change the router's cellular default route.

| Property | Value |
|---|---|
| Base | `rootfs_patched_v17_10s_meta_rndis_dialer.img` source tree |
| Candidate tree | `rootfs_patched_v17_10s_meta_rndis_dialer_auto/` |
| Candidate image | `rootfs_patched_v17_10s_meta_rndis_dialer_auto.img` |
| Image size | 55,738,368 bytes |
| Image SHA-256 | `58b8ed39efa3feb43966733d18bd07fbda1fc65e8f173bafca8bc7a49fe92c2e` |
| Dialer | Supplied `dialer_6.10.9_X17M.patched` at `/usr/bin/dialer` |
| Dialer SHA-256 | `0a46af6d4a4b089ebb03db1e2ab694f675ff9eb529e2228219e7c6049bd2f5b7` |

The startup service is `/etc/init.d/rndis_bridge_watch`, enabled by
`/etc/rc.d/S98rndis_bridge_watch`; it runs
`/usr/bin/rndis_bridge_watch.sh` under procd. The helper checks every two
seconds for `rndis0` and a LAN bridge, brings the interface up, and adds it to
the bridge if needed.

The user reports flashing this image to the active B slot, running firstboot,
rebooting, and verifying that RNDIS comes up after boot. Earlier, the user
confirmed that the manual bridge restored PC Internet access; this later
report verifies the automatic startup behavior. Slot A is being left intact
as a separate fallback. The dialer replacement is present in the tested
image, but its specific patched reboot behavior has not yet been reported as
tested.
