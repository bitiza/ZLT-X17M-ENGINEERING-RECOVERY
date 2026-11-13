# X17M dialer replacement candidate

Prepared a separate rootfs candidate using the supplied patched dialer. The
active router was not flashed or rebooted as part of this change.

| Property | Value |
|---|---|
| Source | `/home/kali/Desktop/Dialer_Ng/dialer_6.10.9_X17M.patched` |
| Source SHA-256 | `0a46af6d4a4b089ebb03db1e2ab694f675ff9eb529e2228219e7c6049bd2f5b7` |
| Rootfs path replaced | `/usr/bin/dialer` |
| Package | `apptzproc` |
| Candidate tree | `rootfs_patched_v17_10s_meta_rndis_dialer/` |
| Candidate image | `rootfs_patched_v17_10s_meta_rndis_dialer.img` |
| Image size | 55,738,368 bytes |
| Image SHA-256 | `0a3ac94a71f66099743c3f799b343604aa328bcc99b585fe39bc18f6b3bca9e2` |

The source and installed executable are both AArch64 PIE binaries using the
rootfs musl loader, and both are 588,568 bytes. The replacement retains mode
0755. The package manifest identifies `/usr/bin/dialer`; no package checksum
manifest exists in the extracted rootfs. This image is built but has not been
flashed or runtime-validated. Its base is the separate
`rootfs_patched_v17_10s_meta_rndis` candidate; the tested META and ten-second
failsafe images remain unchanged.
