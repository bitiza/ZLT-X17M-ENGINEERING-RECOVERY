# Boza X17M recovery and RNDIS port

Built a separate candidate from `/home/kali/Desktop/bozax17/rootfs_a_mod.img`
for the previously working 1 GB X17M. The source tree was the extracted
`/home/kali/Desktop/bozax17/squashfs-root-new`; existing Boza files and normal
USB profile logic were retained. This avoids replacing that tree with the
different rootfs used for the recovery unit's tested image.

## Ported changes

- 10-second failsafe key window and the serial-console-first root shell.
- Lock-free failsafe wait/hook flow. The banner warns against `firstboot`,
  which this firmware was observed erasing `nvdata` and `boot_para`.
- META USB profile with three ACM functions and no mass-storage function;
  `restart_usb.sh` no longer repeatedly reinitializes the gadget in META mode.
- The supplied patched v6.10.9 dialer at `/usr/bin/dialer`.
- Procd-managed RNDIS bridge watcher plus the idempotent tether helper.

The existing normal-mode USB profile logic from `rootfs_a_mod.img` was kept.

## Candidate metadata

| Property | Value |
|---|---|
| Image | `rootfs_bozax17_v17_10s_meta_rndis_dialer_auto.img` |
| Size | 48,054,272 bytes |
| SHA-256 | `19bea120810ed8302146ff46b37fa3488c6e61625e9cf66aa1c6b6825425c864` |
| Source image | `/home/kali/Desktop/bozax17/rootfs_a_mod.img` |
| Source image SHA-256 | `0b124e28bd8091344a6022d1a466dd2855ee3b026816c74f77b9e7cbf1dacbb7` |
| Dialer SHA-256 | `0a46af6d4a4b089ebb03db1e2ab694f675ff9eb529e2228219e7c6049bd2f5b7` |
| Rootfs target capacity | 67,108,864 bytes (64 MiB) |

The user flashed this image to `rootfs_b` with `mtd -r write` and reports that
the router rebooted successfully. However, after reboot the boot-control
record still reads A=`0f020100`, B=`00000000`, and `get_current_slot` returns
`_a`. The user then confirmed `/proc/cmdline` has
`root=/dev/mtdblock29` and `bootslot=a`, so the successful boot was from A;
the new B image has not yet been boot-tested. The user also observed this
router boots faster than their other router, independent of which slot booted.
The individual failsafe, META USB, RNDIS, and dialer behaviors remain
unverified on this router.

The user also observed `-ash: fgrep: not found` after login. This is consistent
with the existing Boza rootfs source lacking the `/bin/fgrep` alias; the port
preserved that base behavior. Preserve an off-device NAND backup. Do not
change misc boot-control bytes by hand based only on this note.
