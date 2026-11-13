# X17M 8GB BusyBox Failure: Read-Only Causal Analysis

## Scope and provenance

This report treats the complete 8GB backup as the **pre-modification baseline**, the supplied `rootfs/bin/busybox_full` as the later replacement candidate, and the UART capture as current failed-router runtime evidence. It does not use the extracted 1GB model rootfs as evidence about the 8GB filesystem. No router communication or image modification was performed.

The 8GB backup is `ZLT_X17M_FULL_BACKUP.zip`, containing `ZLT_X17M_FULL_BACKUP.img`. The p41 partition map places `rootfs_b` at byte offset `989,364,224` (`0x3afa0000`) and gives it a size of `536,870,912` bytes. The extracted baseline partition SHA-256 is `eb651ffc5492b994beef02beb3aa6e366dbe793308dbe4089af21235b2abbbfa`.

The baseline p41 is a hybrid image: SquashFS 4.0/xz lower filesystem followed at partition-relative `+0x03880000` by ext4 `rootfs_data`. The lower filesystem reports 59,192,372 bytes of SquashFS data and a creation time of 2026-03-23 04:10:23. The ext4 overlay image is 477,626,368 bytes, UUID `cf51bad6-6518-4941-9585-8628e62c71b0`; it was inspected with `debugfs` without mounting it or replaying/repairing its journal. Its metadata indicated recovery-needed state, so conclusions about it are limited to directory/file metadata readable from the backup.

In this pre-modification overlay, `/upper/bin`, `/upper/sbin`, `/upper/lib/preinit`, `/upper/etc/preinit`, and `/upper/etc/init.d` are absent. `/upper/etc` contains configuration/state files, not an init-script override. Thus the baseline effective BusyBox, its `/bin` aliases, and preinit scripts are from the SquashFS lower layer. This does **not** establish the exact current failed router's full overlay contents; its original extracted filesystem was deleted.

## BusyBox artifacts

| Property | Original effective 8GB baseline | Supplied replacement candidate |
|---|---|---|
| Path | p41 SquashFS `/bin/busybox` | `/home/kali/Desktop/x17m/rootfs/bin/busybox_full` |
| SHA-256 | `45859c936774dc1939f44ede157081452217722b69a2e30c2dbafa76336369b4` | `43db2f47d9ea4e6ccf02a261a0ab00afb4490eed2d89730e089eacd65dea2273` |
| Size | 595,744 bytes | 1,975,064 bytes |
| Version | BusyBox 1.36.0; binary reports `BusyBox v1.36.0 (2025-12-03 01:38:30 UTC)` | BusyBox 1.37.0; reports Debian `1:1.37.0-6+b7` |
| Architecture | ELF64 AArch64, PIE, dynamically linked to musl (`/lib/ld-musl-aarch64.so.1`) | ELF64 AArch64, non-PIE, statically linked |
| Package metadata | Baseline `busybox.control`: version `1.36.0-1`, architecture `aarch64_cortex-a55_neon-vfpv4` | Debian build identity is in its BusyBox version banner |

The baseline binary was run offline under QEMU with libraries taken from the **same baseline SquashFS**. The replacement was run offline under QEMU. Invoking the candidate with argv[0] `lock` and `netmsg` reproduces exactly:

```text
lock: applet not found
netmsg: applet not found
```

Both replacement invocations return 127. The baseline binary recognizes both aliases: `lock` prints its own usage when called without a filename (exit 1), and `netmsg` prints `usage: netmsg <ip> "<message>"` when called without arguments (exit 1). This demonstrates the capability difference; it does not by itself prove which exact binary image was installed on the failed unit.

### Baseline links and applet inventory

The baseline SquashFS has a regular executable `/bin/busybox` and these exact aliases:

```text
/bin/lock   -> busybox
/bin/netmsg -> busybox
```

The 129 names below are the **complete installed BusyBox symlink/applet set** extracted from the baseline filesystem. Because this vendor binary does not implement the `--list` interface, this is not a claim that no additional compiled-in but unlinked applets exist.

```text
[ [[ arp arping ash awk basename brctl bunzip2 bzcat cat chgrp chmod chown
chroot clear cmp cp crond crontab cut date dd df dirname dmesg du echo egrep
env expr false fgrep find free ftpget grep gunzip gzip halt head hexdump hwclock
id ifconfig kill killall less ln logger login ls md5sum mkdir mke2fs mkfifo
mknod mkswap mktemp mount mv netstat passwd pidof ping ping6 pivot_root
poweroff printf ps pwd readlink reboot reset rm rmdir route sed seq sh sha256sum
sleep sort start-stop-daemon strings swapoff swapon switch_root sync sysctl tail
tar tee test time top touch tr traceroute traceroute6 true udhcpc udhcpd umount
uname uniq unzip uptime vconfig vi watch wc which xargs yes zcat
```

The replacement's `--list` reported 272 applets. The exact set comparison is against baseline-installed symlink names (129), not against a guessed internal applet table:

**ORIGINAL_ONLY (13)**

```text
flock fsync lock lsof lspci netmsg nice nohup ntpd pgrep pmap pstree tcpsvd
```

**COMMON (116)**

```text
[ [[ arp arping ash awk basename brctl bunzip2 bzcat cat chgrp chmod chown
chroot clear cmp cp crond crontab cut date dd df dirname dmesg du echo egrep
env expr false fgrep find free ftpget grep gunzip gzip halt head hexdump hwclock
id ifconfig kill killall less ln logger login ls md5sum mkdir mke2fs mkfifo
mknod mkswap mktemp mount mv netstat passwd pidof ping ping6 pivot_root
poweroff printf ps pwd readlink reboot reset rm rmdir route sed seq sh sha256sum
sleep sort start-stop-daemon strings swapoff swapon switch_root sync sysctl tail
tar tee test time top touch tr traceroute traceroute6 true udhcpc udhcpd umount
uname uniq unzip uptime vconfig vi watch wc which xargs yes zcat
```

**REPLACEMENT_ONLY (156)**

```text
acpid adjtimex ar arch ascii base64 bc blkdiscard blockdev busybox bzip2 cal
chvt cpio crc32 cttyhack dc deallocvt depmod devmem diff dnsdomainname dos2unix
dpkg dpkg-deb dumpkmap dumpleases ed expand factor fallocate fatattr fdisk findfs
fold freeramdisk fsfreeze fstrim ftpput getfattr getopt getty groups hostid
hostname httpd i2cdetect i2cdump i2cget i2cset i2ctransfer ifdown ifup init insmod
install ionice ip ipcalc klogd last link linux32 linux64 linuxrc loadfont
loadkmap logname logread losetup lsmod lsscsi lzcat lzma lzop mdev microcom mim
mkdosfs mkpasswd modinfo modprobe more mt nameif nbd-client nc nl nologin nproc
nsenter nslookup nuke od openvt partprobe paste patch rdate realpath renice resume
rev rmmod rpm rpm2cpio run-init run-parts setkeycodes setpriv setsid sha1sum
sha3sum sha512sum shred shuf ssl_client stat stty su sulogin svc svok syslogd tac
taskset tc telnet telnetd tftp timeout truncate ts tty tunctl ubirename udhcpc6
uevent uncompress unexpand unix2dos unlink unlzma unshare unxz usleep uudecode
uuencode w watchdog wget who whoami xxd xz xzcat
```

Every `ORIGINAL_ONLY` item is an installed baseline alias whose name is not in the replacement's applet list. In particular, the existing `/bin/lock` and `/bin/netmsg` symlinks still dispatch through the replacement binary but fail because those applets are absent. Other original-only applets are not all necessarily needed during early boot; some are nevertheless used in later baseline scripts. For example, baseline `/lib/functions/procd.sh` invokes `flock` for service locking, and several `/etc/tzscript/*` scripts use `flock` for VoIP-related critical sections. This makes later effects from the missing applet set plausible, not established for the failed boot.

## Exact baseline preinit path and lock/netmsg behavior

The following describes the 8GB **baseline** source, not the 1GB extraction. All listed shell scripts have no `set -e`; simple command return statuses are not used as a global abort condition.

1. `/etc/preinit` line 5 immediately `exec`s `/sbin/init` when `PREINIT` is empty. In the preinit invocation, it sets `PATH`, sources `/lib/functions.sh`, `/lib/functions/preinit.sh`, and `/lib/functions/system.sh`, initializes hook stacks, sources every `/lib/preinit/*` file, then executes `preinit_essential` and `preinit_main` hooks. The files are sourced in glob (lexical filename) order.
2. `/lib/preinit/10_indicate_preinit` registers `preinit_ip` and `pi_indicate_preinit`. `preinit_ip` can call `/bin/board_detect /tmp/board.json`; `preinit_config_board` also calls it. UART messages about `/etc/board.d/99-default_network` are consistent with this early preinit call. `preinit_net_echo()` runs `netmsg $pi_broadcast "$1"` only when `pi_ifname` exists in `/proc/net/dev` and the relevant normal/failsafe network-message flag is set. Its `netmsg` status is not tested; failure loses that network announcement but does not abort the shell function.
3. `/lib/preinit/30_failsafe_wait` registers `failsafe_wait`. Its default timeout from `/lib/preinit/00_preinit.conf` is two seconds. It creates three temp markers, installs INT/USR1 traps, calls `lock $keypress_wait` at line 30, and starts a background countdown. The background invokes `preinit_net_echo` (which may emit `netmsg`), sleeps one second per tick, then calls `lock -u $keypress_wait` at line 39 and removes the wait marker. The foreground prints the failsafe prompt, polls stdin with `read -t`, then calls `lock -u` at line 67 if a recognized key is entered. After the wait loop it calls `lock -w $keypress_wait` at line 72, reads the key marker, deletes its temp files, and returns whether the failsafe key was pressed.
4. No `set -e` means missing `lock` at lines 30, 39, 67, or 72 emits an error but does not itself abort the function. None of those lock return statuses is tested; the calls are ordinary foreground/background commands (except the trap body), and later statements run after a nonzero result. The `lock` command is meant to coordinate the foreground and background around the wait-file marker. When it is missing, that mutual exclusion is gone: the background can remove the marker while the foreground is checking it, and the final `lock -w` no longer waits for a lock holder. The loop still has its timeout, and the marker-removal, `read -t`, and cleanup operations remain. Thus a race or altered key-detection behavior is possible; an indefinite wait is not implied by this ordinary two-second path.
5. `/lib/preinit/40_run_failsafe_hook` returns unless `FAILSAFE=true`. When failsafe is true, it calls `lock /tmp/.failsafe`, runs failsafe hooks, then loops while `/tmp/sysupgrade` is absent, invoking `lock -w /tmp/.failsafe`. With `lock` missing, this explicit failsafe path can become a fast loop rather than a blocking lock wait. This is a concrete disruption mechanism, but current UART evidence does not prove the failsafe flag was set.
6. If the key was not pressed and no `failsafe=` cmdline/button condition set `FAILSAFE`, hooks continue: `run_failsafe_hook` returns; regular-preinit network notice/state hooks run; the initramfs test and root-mount hooks run; then final preinit IP deconfiguration runs. The final `lock -w` itself is not followed by `exit` or a status-checked branch.
7. **Important baseline-path limitation:** baseline `/etc/inittab` contains `::sysinit:/etc/init.d/rcS S boot`, but neither the baseline SquashFS nor baseline `rootfs_data/upper` contains `/etc/init.d/rcS`. This means the exact baseline image alone does not provide the rcS dispatcher implementation needed to prove the transition from the inittab entry into service startup. The baseline does contain `/etc/rc.common`, `/etc/init.d/usb.init`, and `/etc/rc.d/S30usb.init -> ../init.d/usb.init`; `usb.init` declares `START=30`. If the rcS dispatcher runs those links, S30usb.init follows earlier startup links such as S000mount_all and S10boot. But the missing dispatcher must not be silently filled in from the 1GB rootfs or generic OpenWrt assumptions. The current failed router may have a changed overlay that provides additional files, but that deleted tree is unavailable here.

### What happens after the last observed lock error?

The live UART event log's last `lock: applet not found` is in the final group at approximately 14:20:30.932855Z (read-chunk completion timestamp; this is not a per-character UART timestamp). In baseline source, the two errors following the pair of `netmsg` errors align most naturally with the background `lock -u $keypress_wait` at `30_failsafe_wait:39` and foreground `lock -w $keypress_wait` at line 72. The exact process/thread attribution is inference because the raw UART stream does not label shell PIDs.

After line 72, the source sets `keypressed=1`, tests the marker, removes the three temp files, and returns. With no `f` key marker, `failsafe_wait` does not set `FAILSAFE=true`. The next normal hook, `run_failsafe_hook`, returns if that flag is empty; later preinit hooks proceed to root-mount and final cleanup. This source path contains no immediate fatal branch after the final lock error. Therefore the applet error alone does not explain why the later normal init/service path was not observed. A failsafe condition, downstream script failure, the missing rcS dispatcher in baseline, or another changed/current-overlay issue remains relevant and unresolved.

## Correlation with current failed-router UART

The analyzed capture is `analysis/live_meta_usbdiag/20260918T142003Z/uart_raw.bin` (SHA-256 `2fb8a5bd7963dcd242461d719a48743cf5ee6bb9d6a7004f39433a78b4b96975`). Associated timestamped chunk log: `uart_events.log` (SHA-256 `d21275fbb130f1747563b338dbf2d178adc4943c12689ea2963fd3e3626da9b3`). UART was opened RX-only at 921600 8N1. The text order in the raw capture is:

```text
rai0      no private ioctls.
ra0       no private ioctls.
/bin/board_detect: /etc/board.d/99-default_network: line 5: can't open /mnt/vendor/nvcfg/mac0: no such file
/bin/board_detect: 6: can't open /mnt/vendor/nvcfg/mac1: no such file
lock: applet not found
Press the [f] key and hit [enter] to enter failsafe mode
Press the [1], [2], [3] or [4] key and hit [enter] to select the debug level
netmsg: applet not found
netmsg: applet not found
lock: applet not found
lock: applet not found
```

The first lock error is consistent with `lock $keypress_wait` at line 30, before the prompt. The two netmsg errors are consistent with `preinit_net_echo` calls from the two-second background failsafe countdown, conditional on `pi_ifname` and network-message flags. The final two lock errors are consistent with the background unlock and foreground wait calls above. The order therefore matches a preinit failsafe wait that advances through its normal timeout with broken lock/netmsg applets; it is not evidence by itself that preinit stopped at those errors.

The available capture does not show a later `Welcome to Preloader`, panic, watchdog, reset, reboot, or a positive `/sbin/init`/rcS/S30usb marker after these messages. It also does not record an explicit shell prompt/input or identify the state of `FAILSAFE`, `/tmp/failsafe_button`, or `/tmp/sysupgrade`. UART silence is not proof that `/sbin/init` did or did not execute.

## Causal assessment

| Claim | Classification | Basis |
|---|---|---|
| A. Replacement BusyBox was active on the failed router | **STRONGLY SUPPORTED** | Current UART errors exactly match offline replacement alias behavior, and the user identifies this candidate as the installed binary. The deleted current filesystem prevents hash-level confirmation of the exact installed file. |
| B. Replacement explains `lock`/`netmsg` errors | **PROVEN** (capability); **STRONGLY SUPPORTED** (live attribution) | Candidate lacks both applets and reproduces the exact diagnostic; baseline binary has both aliases. The current device's precise BusyBox bytes are unavailable. |
| C. Missing `lock`/`netmsg` can disrupt preinit | **PROVEN** | Preinit uses `lock` for timeout synchronization/failsafe exclusion and `netmsg` for network announcements. Missing applets remove those semantics. `netmsg` failure is non-fatal in this source; missing `lock` affects synchronization and can spin in explicit failsafe mode. |
| D. Missing `lock`/`netmsg` alone explains observed boot failure | **NOT SUPPORTED** | Ordinary failsafe wait is timed and has no `set -e`; source continues after final lock call. Capture does not show a fatal/exit branch at that point. It remains possible that a race or an active explicit failsafe path changes behavior, but those conditions are unobserved. |
| E. Other missing replacement applets could affect later boot | **STRONGLY SUPPORTED** (availability difference); **POSSIBLE** (boot impact) | 13 original installed aliases are absent. `flock` is directly used by procd service handling and VoIP scripts; whether it blocks this boot path is unknown. |
| F. Missing `/mnt/vendor/nvcfg/mac0` and `mac1` is causal | **NOT SUPPORTED** | `board_detect` prints missing-file diagnostics. Available source does not establish that these messages terminate preinit; they precede the failsafe prompt and subsequent hooks. They may affect MAC configuration, not proven boot progression. |
| G. Wi-Fi private-ioctl errors are causal | **NOT SUPPORTED** | `rai0`/`ra0` diagnostics precede board-detect/failsafe output; no fatal consequence is shown. |

## Minimum theoretical repair target (analysis only)

For the **specific missing `lock`/`netmsg` applet symptoms**, the minimum file-level difference in the baseline layout is the BusyBox executable itself: both aliases already point to `busybox`, so restoring a BusyBox binary that implements the baseline applets would make those links dispatch again. The broader exact applet-set regression includes 11 other baseline aliases, and `/bin/busybox` compatibility alone would not establish whether the current writable overlay, symlinks, ownership/mode, libraries, or unrelated modified files also differ. Since the current 8GB rootfs tree was deleted and the failed router was not accessed, the evidence cannot determine whether a one-file target would restore boot, whether multiple files changed, or whether an entire filesystem partition was altered. This is a theoretical scope statement, not a repair recommendation.

## Facts / inference / unknown

**FACT:** The pre-modification 8GB baseline contains a 595,744-byte BusyBox 1.36.0 AArch64 dynamically linked to musl, plus `/bin/lock -> busybox` and `/bin/netmsg -> busybox`. Both names are among 13 baseline-installed aliases absent from the supplied static BusyBox 1.37.0 candidate. The candidate reproduces both live UART error strings offline. Baseline preinit calls these applets exactly as described, without `set -e`; the normal failsafe wait is two seconds. Baseline rootfs_data has no BusyBox/preinit/rcS override. The baseline `inittab` references rcS but the rcS dispatcher is absent from both baseline layers.

**INFERENCE:** The failed unit likely ran the replacement or another BusyBox with the same omitted applets. The observed `lock`, `netmsg`, `lock`, `lock` sequence matches the baseline two-second failsafe wait's call order. Missing synchronization can perturb preinit, but the ordinary path is designed to continue after those command errors.

**UNKNOWN:** Exact BusyBox hash installed on the current router; exact current overlay contents; whether failsafe was entered/forced; whether the background and foreground lock calls interleaved exactly as inferred; whether `/sbin/init`, the rcS path, or any later service ran after the last UART error; whether other changes account for the boot failure; and whether restoring only BusyBox would restore boot.

## Requested summary

BASELINE BACKUP PREDATES MODIFICATION: YES

BASELINE 8GB BUSYBOX: SHA-256 `45859c936774dc1939f44ede157081452217722b69a2e30c2dbafa76336369b4`, 595,744 bytes, BusyBox 1.36.0-1, AArch64 PIE/dynamic musl; 129 installed aliases listed above.

REPLACEMENT BUSYBOX: SHA-256 `43db2f47d9ea4e6ccf02a261a0ab00afb4490eed2d89730e089eacd65dea2273`, 1,975,064 bytes, BusyBox 1.37.0 Debian build, AArch64 static; 272 `--list` applets.

ORIGINAL LOCK APPLET: PRESENT (symlink `/bin/lock -> busybox`; baseline recognizes it)

REPLACEMENT LOCK APPLET: ABSENT (`lock: applet not found`, exit 127)

ORIGINAL NETMSG APPLET: PRESENT (symlink `/bin/netmsg -> busybox`; baseline recognizes it)

REPLACEMENT NETMSG APPLET: ABSENT (`netmsg: applet not found`, exit 127)

LIVE FAILED ROUTER USED INCOMPATIBLE BUSYBOX: STRONGLY SUPPORTED; exact installed bytes unknown

LOCK/NETMSG ERRORS EXPLAINED: YES for the supplied candidate's capability mismatch; live attribution strongly supported

PREINIT STALL EXPLAINED: NO; applet failures disrupt intended semantics, but source shows a timed continuation path and no immediate fatal branch

OTHER MISSING APPLETS RELEVANT: YES; 11 additional baseline aliases absent, including `flock` used by service/runtime scripts; their role in this boot failure is unknown

LAST LIVE PREINIT LOCATION: Failsafe wait, consistent with `/lib/preinit/30_failsafe_wait` lines 39 and 72; exact process attribution is inferred from UART ordering

EXPECTED NEXT PREINIT ACTION: After line 72, inspect marker, remove temporary files, return from `failsafe_wait`; with no failsafe trigger, continue to later hooks, mount-root/final cleanup. The exact handoff into rcS cannot be proven from baseline because `/etc/init.d/rcS` is missing there despite the inittab reference.

MINIMUM THEORETICAL REPAIR TARGET: `/bin/busybox` is the minimum file that would restore both aliases if links and all other files are intact; not established as sufficient for boot recovery.

REMAINING UNCERTAINTY: Current rootfs/overlay state is deleted; no hash for installed BusyBox; failsafe state and post-preinit progression are unobserved; baseline rcS dispatcher is absent.

NEXT SAFEST STEP: Preserve and inspect any surviving exact modified rootfs image or filesystem copy offline; absent that, compare the current UART against a fresh RX-only capture only if separately authorized. No repair or target access is recommended by this analysis.
