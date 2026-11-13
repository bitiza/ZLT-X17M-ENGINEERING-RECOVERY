# X17M 8 GB BusyBox state-transition analysis

## Scope and state vocabulary

Read-only analysis of the exact p41 backup filesystem, the separately supplied BusyBox candidate, and the preserved failed-router UART capture. No router communication, firmware/image modification, journal replay, writable mount, filesystem repair, or repair recommendation was performed. The binaries were invoked only offline under QEMU with harmless missing-argument probes; no target was involved.

This report uses **BACKUP STATE**, **CURRENT FAILED RUNTIME STATE**, and **USER-RECALLED POSSIBLE OPERATION**. It does not classify the backup as pre- or post-modification. The complete p41 and rootfs_data identities/hashes are documented in [the p41 provenance audit](X17M_P41_ROOTFSDATA_PROVENANCE_AUDIT.md). The inspected p41 SHA-256 is `eb651ffc5492b994beef02beb3aa6e366dbe793308dbe4089af21235b2abbbfa`; its embedded rootfs_data SHA-256 is `54443567d65477838ea0131ab236a91bc0f59c2c34ca9b7e4b1827137c89acbc`.

## 1. Binary identities and offline behavior

| State/artifact | Path | SHA-256 | Size | Version | Format |
|---|---|---|---:|---|---|
| BACKUP STATE canonical BusyBox | p41 SquashFS `/bin/busybox` | `45859c936774dc1939f44ede157081452217722b69a2e30c2dbafa76336369b4` | 595,744 | BusyBox v1.36.0, build `2025-12-03 01:38:30 UTC`; package metadata 1.36.0-1 | ELF64 AArch64 PIE, dynamically linked to `/lib/ld-musl-aarch64.so.1` |
| BACKUP STATE full BusyBox | p41 SquashFS `/usr/bin/busybox_full` | `43db2f47d9ea4e6ccf02a261a0ab00afb4490eed2d89730e089eacd65dea2273` | 1,975,064 | BusyBox v1.37.0 (Debian `1:1.37.0-6+b7`) | ELF64 AArch64, static, non-PIE |
| Supplied candidate | `/home/kali/Desktop/x17m/rootfs/bin/busybox_full` | `43db2f47d9ea4e6ccf02a261a0ab00afb4490eed2d89730e089eacd65dea2273` | 1,975,064 | Same Debian BusyBox v1.37.0 build | ELF64 AArch64, static, non-PIE |

**FACT:** p41 `/usr/bin/busybox_full` and the supplied candidate are byte-for-byte identical (equal size and SHA-256). This proves candidate identity, not when or why it entered the backup state.

Offline QEMU probes, from the backup binaries:

```text
BACKUP /bin/busybox invoked as lock:
Usage: lock [-suw] <filename>
        -s      Use shared locking
        -u      Unlock
        -w      Wait for the lock to become free, don't acquire lock
        -n      Don't wait for the lock to become free. Fail with exit code
EXIT=1

BACKUP /bin/busybox invoked as netmsg:
usage: netmsg <ip> "<message>"
EXIT=1

BACKUP /usr/bin/busybox_full invoked as lock:
lock: applet not found
EXIT=127

BACKUP /usr/bin/busybox_full invoked as netmsg:
netmsg: applet not found
EXIT=127
```

The first two exit 1 only because required operands were intentionally omitted. They establish that those applets exist. The candidate’s exit-127 diagnostics reproduce the failed-UART wording exactly.

### Applet inventory qualification

The candidate’s own `--list` produces 272 compiled applet names. The vendor BusyBox 1.36 binary does not implement a working `--list`/`--help` query under QEMU (`-list: applet not found`, exit 127). Its complete **installed/callable alias inventory** is recoverable from the exact p41 filesystem: 129 symlinks target `/bin/busybox`, matching the BusyBox package file list. This is the complete installed alias set, not a claim that the binary contains no additional unlinked applets.

BACKUP STATE installed applet-alias inventory (129 unique names):

```text
[ [[ arp arping ash awk basename brctl bunzip2 bzcat cat chgrp chmod chown chroot
clear cmp cp crond crontab cut date dd df dirname dmesg du echo egrep env expr false
fgrep find flock free fsync ftpget grep gunzip gzip halt head hexdump hwclock id
ifconfig kill killall less ln logger lock login ls lsof lspci md5sum mkdir mke2fs
mkfifo mknod mkswap mktemp mount mv netmsg netstat nice nohup ntpd passwd pgrep
pidof ping ping6 pivot_root pmap poweroff printf ps pstree pwd readlink reboot reset
rm rmdir route sed seq sh sha256sum sleep sort start-stop-daemon strings swapoff
swapon switch_root sync sysctl tail tar tcpsvd tee test time top touch tr traceroute
traceroute6 true udhcpc udhcpd umount uname uniq unzip uptime vconfig vi watch wc
which xargs yes zcat
```

The candidate’s complete compiled applet inventory from its `--list` is:

```text
[ [[ acpid adjtimex ar arch arp arping ascii ash awk base64 basename bc blkdiscard
blockdev brctl bunzip2 busybox bzcat bzip2 cal cat chgrp chmod chown chroot chvt clear
cmp cp cpio crc32 crond crontab cttyhack cut date dc dd deallocvt depmod devmem df diff
dirname dmesg dnsdomainname dos2unix dpkg dpkg-deb du dumpkmap dumpleases echo ed egrep
env expand expr factor fallocate false fatattr fdisk fgrep find findfs fold free
freeramdisk fsfreeze fstrim ftpget ftpput getfattr getopt getty grep groups gunzip gzip
halt head hexdump hostid hostname httpd hwclock i2cdetect i2cdump i2cget i2cset
i2ctransfer id ifconfig ifdown ifup init insmod install ionice ip ipcalc kill killall
klogd last less link linux32 linux64 linuxrc ln loadfont loadkmap logger login logname
logread losetup ls lsmod lsscsi lzcat lzma lzop md5sum mdev microcom mim mkdir mkdosfs
mke2fs mkfifo mknod mkpasswd mkswap mktemp modinfo modprobe more mount mt mv nameif
nbd-client nc netstat nl nologin nproc nsenter nslookup nuke od openvt partprobe passwd
paste patch pidof ping ping6 pivot_root poweroff printf ps pwd rdate readlink realpath
reboot renice reset resume rev rm rmdir rmmod route rpm rpm2cpio run-init run-parts sed
seq setkeycodes setpriv setsid sh sha1sum sha256sum sha3sum sha512sum shred shuf sleep
sort ssl_client start-stop-daemon stat strings stty su sulogin svc svok swapoff swapon
switch_root sync sysctl syslogd tac tail tar taskset tc tee telnet telnetd test tftp time
timeout top touch tr traceroute traceroute6 true truncate ts tty tunctl ubirename udhcpc
udhcpc6 udhcpd uevent umount uname uncompress unexpand uniq unix2dos unlink unlzma
unshare unxz unzip uptime usleep uudecode uuencode vconfig vi w watch watchdog wc wget
which who whoami xargs xxd xz xzcat yes zcat
```

For the vendor binary, the authoritative complete *installed alias inventory* is the 129 symlink paths under p41 that target BusyBox. A complete internal applet table cannot be queried from that binary with its supported interface; therefore the report does not falsely equate installed aliases with every possibly compiled but unlinked function. The p41 alias set and direct target checks are the evidence for path analysis; neither binary’s inventory was inferred from its version string.

## 2. BACKUP STATE effective namespace

| Requested path | BACKUP STATE result | Dispatch consequence |
|---|---|---|
| `/bin/busybox` | Regular p41 lower-layer file, BusyBox 1.36.0 above; no `/upper/bin` directory | Canonical `/bin` applet dispatcher is the original 1.36.0 binary |
| `/bin/lock` | Lower-layer symlink `lock -> busybox` | Dispatches to canonical `/bin/busybox`; works |
| `/bin/netmsg` | Lower-layer symlink `netmsg -> busybox` | Dispatches to canonical `/bin/busybox`; works |
| `/usr/bin/busybox` | Allocated p41 upper symlink `-> /usr/bin/busybox_full` | Explicit `/usr/bin/busybox` selects candidate 1.37.0 |
| `/usr/bin/busybox_full` | Regular p41 lower-layer file, same hash as supplied candidate | Candidate is reachable in the merged view |
| `/usr/bin/lock` | Absent in lower and upper trees | PATH lookup does not shadow `/bin/lock` |
| `/usr/bin/netmsg` | Absent in lower and upper trees | PATH lookup does not shadow `/bin/netmsg` |

The rootfs_data upper tree has 227 `/upper/usr/bin/<applet>` symlinks to `/usr/bin/busybox_full`, and an upper `/usr/bin/busybox` symlink to that same binary. It has no `/upper/bin`. Crucially, it does **not** contain upper aliases for the 13 applets missing from the candidate. Their lower-layer aliases remain links to `../../bin/busybox` or `busybox`; they therefore continue to dispatch to the original canonical BusyBox in BACKUP STATE. This split namespace is why “the backup contains `busybox_full`” does not mean that its `/bin/lock` and `/bin/netmsg` use it.

## 3. Hypothetical canonical replacement: exact path effect

Model only: overwrite the bytes of `/bin/busybox` with the candidate bytes, leaving every existing link and overlay entry unchanged. No such operation was performed.

Candidate applet inventory has 272 names. The exact BACKUP-installed aliases absent from that inventory are:

| Applet | BACKUP path(s) still pointing at canonical `/bin/busybox` | Use/effect if canonical file is replaced |
|---|---|---|
| `flock` | `/usr/bin/flock` | Procd service-wrapper lock; hotplug, MIPC/WAN, CLAT, and VoIP locking. Several call sites handle failure non-fatally; packet-steering hotplug explicitly exits. |
| `fsync` | `/bin/fsync` | Called by Wi-Fi profile-save Lua after writing a profile; `os.execute()` result is ignored. Persistent profile flush may fail. Not a preinit/service-start command. |
| `lock` | `/bin/lock` | Preinit failsafe wait and, if failsafe is actually entered, a `lock -w` loop; also account/config locks, luci reload, sysupgrade. |
| `lsof` | `/usr/bin/lsof` | Installed alias; no shell-script executable call found in the searched boot/service trees. `lsof_LineNum` in TR-069 data is a model/API label, not proof of command execution. |
| `lspci` | `/usr/bin/lspci` | Called by `/usr/bin/mtk_netdiag.sh` diagnostics; not init/USB startup. |
| `netmsg` | `/bin/netmsg` | Conditional preinit network/failsafe announcements; failure status is ignored. |
| `nice` | `/bin/nice` | Installed alias; `procd_set_param nice` in service code is a procd parameter, not execution of the BusyBox `nice` applet. No boot-time `nice` command invocation was found. |
| `nohup` | `/usr/bin/nohup` | Installed alias; no invocation found in searched scripts/configuration. |
| `ntpd` | `/usr/sbin/ntpd` | `sysntpd` service can configure this executable; its S-start link is absent in this backup’s `/etc/rc.d`, so no automatic rcS launch is established. Explicit service start would fail to exec the applet. |
| `pgrep` | `/usr/bin/pgrep` | Used by dynamic-DNS cleanup trap to enumerate child processes; command-substitution status is not checked. Not a boot-dispatch gate. |
| `pmap` | `/usr/bin/pmap` | Installed alias; no invocation found in searched scripts/configuration. |
| `pstree` | `/usr/bin/pstree` | Installed alias; no invocation found in searched scripts/configuration. |
| `tcpsvd` | `/usr/bin/tcpsvd` | Installed alias; no invocation found in searched scripts/configuration. |

**Only four of the 53 direct `/bin` symlink aliases become unavailable:** `/bin/fsync`, `/bin/lock`, `/bin/netmsg`, and `/bin/nice`. The other nine original-only aliases live under `/usr/bin` or `/usr/sbin`, but their lower symlink targets also resolve to `/bin/busybox`; those paths fail under the hypothetical as well. The additional `/usr/bin/busybox` upper symlink continues to point to the already-existing `busybox_full` candidate and is unaffected by changing `/bin/busybox`.

No other existing `/bin` aliases are lost: comparison of all 53 lower `/bin` symlink basenames against the candidate’s actual 272-name `--list` found exactly those four. `/sbin` BusyBox links and the remaining installed aliases are supported by the candidate.

## 4. Call-site and phase audit of all 13

The following is a source-level call-site audit of the exact p41 SquashFS plus reachable p41 upper tree. “No `set -e`” means the affected script/function does not enable errexit; explicit conditionals are noted. Textual searches cannot prove that no opaque vendor binary invokes an applet by a dynamically assembled name.

### Preinit and lock/netmsg

* `/lib/preinit/30_failsafe_wait`, lines 30, 39, 67, 72: `lock $keypress_wait`, then `lock -u` in the countdown/key paths, then `lock -w $keypress_wait`. Foreground except the line-39 countdown in a background group; no return value is tested; no `set -e`. In the normal two-second wait, missing lock removes synchronization but the countdown, marker tests, and cleanup continue. If `FAILSAFE=true`, `/lib/preinit/40_run_failsafe_hook` calls `lock /tmp/.failsafe`, then loops while `/tmp/sysupgrade` is absent and calls `lock -w`; a missing applet makes that a fast repeating loop. The UART prompt alone does not prove `FAILSAFE=true`.
* `/lib/preinit/10_indicate_preinit:154`: `netmsg $pi_broadcast "$1"`, conditional on the selected preinit interface and message flags. Foreground; status ignored; no `set -e`; lost announcement only in this source path.
* `/lib/functions.sh:321,323,351,353,373,376`: `lock`/`lock -u` around group/password database edits. Foreground and unchecked; affects account/config mutation, not normal boot dispatch.
* `/sbin/luci-reload:36,45`: acquire/release around a reload operation; no evidence this is on the boot chain.
* `/sbin/sysupgrade:424`: unlocks `/tmp/.failsafe` during an upgrade path; not ordinary boot.

The observed UART order—board-detect output, one `lock: applet not found`, failsafe prompt, two `netmsg: applet not found`, then two more lock diagnostics—matches the baseline countdown call pattern. It is **OBSERVED** in `analysis/live_meta_usbdiag/20260918T142003Z/uart_raw.bin` (SHA-256 `2fb8a5bd7963dcd242461d719a48743cf5ee6bb9d6a7004f39433a78b4b96975`). It does not identify the exact binary or prove that the process entered the explicit failsafe hook.

### `flock` call sites

* `/lib/functions/procd.sh:48-57`: `procd_lock` tries `flock -n 1000` with stderr suppressed. On failure it opens a per-service lock file, tries `flock 1000`, and if that fails logs a warning. It does not `exit`, return an error that gates the wrapper, or use `set -e`; `_procd_wrapper` then defines the service API wrappers. A missing flock therefore loses mutual exclusion and emits a warning, but does not by itself prevent `service_start`, `procd_open_instance`, `procd_close_instance`, or the init script from continuing. It is reached when a `USE_PROCD=1` script loads the helper (including S001nvram_daemon, S30usb.init, and S98meta_tst).
* `/etc/hotplug.d/net/20-smp-packet-steering:40-41`: opens fd 512, then `flock 512 || exit 1`. Failure is tested and terminates this network hotplug hook, so CPU packet steering tuning is skipped. It does not terminate procd or rcS.
* `/lib/netifd/proto/mipc.sh:38-45,338`: `pdn_lock` tries nonblocking then blocking flock, logs a warning if both fail, and returns without a fatal guard; later APN provisioning continues without the intended lock. This can allow races in MIPC WAN provisioning, not block the USB init script directly.
* `/usr/bin/clat.sh:54,125,127`: initial lock/unlock statuses are ignored. A later background prefix-detection subshell uses `flock -n 2 || exit`; missing flock ends that optional prefix-detection task, while the surrounding CLAT setup proceeds.
* `/usr/bin/setup_clat.sh:22`: missing flock is unchecked; script continues, with synchronization lost.
* `/etc/tzscript/start_tzphone:33,60`, `start_voice:69,95`, `start_voipclient:76,102`, and `stop_voipclient:8,56`: blocking lock/unlock around telephony operations. Statuses are not tested; missing flock removes serialization but these are VoIP service paths, not boot-dispatch gates.

### Remaining applets

* `fsync`: `/usr/bin/wifi_config_save` calls `os.execute("fsync "..path)` after saving a wireless profile. Return value is not checked; no boot/service invocation found.
* `lspci`: `/usr/bin/mtk_netdiag.sh` runs `run_cmd "lspci"` in its diagnostic collection; not the init path.
* `ntpd`: `/etc/init.d/sysntpd` prepares `/usr/sbin/ntpd` as the procd command. The backup has no enabled `S*sysntpd` symlink; explicit start could fail to execute it and affect time service, not system init. The service definition uses procd respawn only for some configuration branches.
* `pgrep`: `/usr/lib/ddns/dynamic_dns_functions.sh:1244` captures `pgrep -P $$` in a cleanup trap and loops over returned PIDs. No status branch/errexit; failed pgrep yields an empty PID list and may leave children.
* `nice`: `/lib/functions/procd.sh` treats the token `nice` as a procd parameter type; `/etc/init.d/collectd` sets that parameter. This is not an external `nice` applet invocation.
* `lsof`, `nohup`, `pmap`, `pstree`, `tcpsvd`: installed aliases but no command invocation was found in the searched shell, init, hotplug, or service sources. Their use by a closed-source binary or generated command remains unknown; the direct aliases would still fail if `/bin/busybox` were replaced.

## 5. Init/rcS/S30/S98 path; correction to prior report

The prior report’s statement that a missing `/etc/init.d/rcS` left the sysinit-to-service path unproven was too conservative and should be superseded. The absence is real in both p41 layers, but this is the expected procd design: **procd supplies rcS dispatch internally; `/etc/init.d/rcS` need not exist.**

1. Kernel command line uses `init=/etc/preinit`. `/etc/preinit` initially execs `/sbin/init` when `PREINIT` is unset. The p41 `/sbin/init` is a small AArch64 wrapper (18,376 bytes, distinct hash from `/sbin/procd`); its strings include `/etc/preinit`, `PREINIT`, `/sbin/procd`, and “Exec to real procd now”. It starts the preinit shell with `PREINIT=1`, then transitions to `/sbin/procd` after the script returns.
2. `/etc/preinit` sets `PATH=/usr/sbin:/usr/bin:/sbin:/bin`, sources functions and `/lib/preinit/*`, then executes essential/main hooks. The final failed-UART messages are from the failsafe-wait hook. The normal return path continues through the later preinit hooks and back to the init wrapper unless an explicit failsafe condition changes control flow.
3. `/etc/inittab` contains `::sysinit:/etc/init.d/rcS S boot` and a shutdown entry. p41 `/sbin/procd` contains the strings `Parsing inittab`, `valid format is rcS <S|K> <param>`, `/etc/rc.d`, `/etc/init.d`, and `running %s/%s%s %s`.
4. In procd, the sysinit handler is the internal `runrc` callback, which invokes internal `rcS("S", "boot", ...)`; that dispatcher scans `/etc/rc.d/S*` in order. The comparative upstream implementation shows this same model: [`inittab.c`](https://raw.githubusercontent.com/openwrt/procd/master/inittab.c) routes `sysinit` to `runrc`, and [`rcS.c`](https://raw.githubusercontent.com/openwrt/procd/master/rcS.c) enumerates and serially runs `/etc/rc.d/S*`. These are source-correlation, not a claim that the SDK/current upstream source is byte-identical to this vendor binary; the exact p41 binary’s strings and installed rc links independently support the same path.
5. The p41 rc links include `S000mount_all -> ../init.d/0mount_all`, `S001nvram_daemon -> ../init.d/1nvram_daemon`, `S001restore -> ../init.d/1restore`, `S30usb.init -> ../init.d/usb.init`, and `S98meta_tst -> ../init.d/meta_tst`. Procd’s rcS runqueue serializes the S scripts. **No standalone `/etc/init.d/rcS` file is required.**
6. `S000mount_all` is a non-procd script and runs first. `S001nvram_daemon` is the first listed `USE_PROCD=1` service in lexical rc order. Under the hypothetical canonical replacement, sourcing its procd helpers is the first normal post-preinit operation that encounters missing `flock`; procd logs the failure/warning but continues. `S001restore` follows; it conditionally extracts `/data/sysupgrade.tgz`. Whether that archive exists in the backup’s separate mounted user-data partition and whether it changes rootfs files is not established by the p41 filesystem audit.
7. `S30usb.init` is enabled and declares START=30/USE_PROCD. Its script performs the static META boot-mode selection and PID 202D configuration already documented in the earlier exact-rootfs analysis. Missing `flock` in the procd helper is not an explicit abort. If run, `S98meta_tst` follows S30 and starts `/usr/bin/meta_tst` through procd.

Thus the first canonical-replacement applet failure after a normal preinit return is expected to be `flock` during procd service-wrapper setup at S001nvram_daemon, not an applet in S30usb.init itself. The source handles it non-fatally. If `FAILSAFE=true`, a different earlier post-wait path exists: `40_run_failsafe_hook` can repeatedly call missing `lock -w` while waiting for `/tmp/sysupgrade`. The captured UART has only the finite failsafe-wait lock messages, not a repeated stream from that loop; the capture does not establish the `FAILSAFE` variable, so that branch remains a conditional possibility, not an observed cause.

## 6. Current failed runtime correlation and hypotheses

| Proposition | Assessment | Evidence / limit |
|---|---|---|
| A. BACKUP STATE already contains `busybox_full` | **PROVEN** | p41 lower file SHA-256 equals the supplied candidate; upper `/usr/bin/busybox` points to it. |
| B. CURRENT FAILED RUNTIME used a BusyBox lacking `lock` and `netmsg` | **PROVEN at applet-lookup behavior level; exact binary UNKNOWN** | UART reports `lock: applet not found` and `netmsg: applet not found`; the supplied BusyBox candidate reproduces these exact messages, while backup canonical BusyBox implements both. This proves the active applet dispatcher could not provide these applets. It does not identify the exact binary or prove it was `busybox_full`. |
| C. `/bin/busybox` specifically overwritten with BACKUP `/usr/bin/busybox_full` | **HYPOTHESIS / UNKNOWN** | This operation predicts both UART diagnostics exactly, but no current failed-rootfs image/hash or independent record of the write survives. |

Other arrangements can produce the same UART text: `/bin/lock` and `/bin/netmsg` could have been retargeted to the candidate; a different canonical BusyBox could lack those applets; another PATH-preceding alias could dispatch to a reduced BusyBox; or a different replacement binary could have the same applet omissions. The discriminating evidence would be an exact image or filesystem copy from the failed router (including upper/lower path resolution), or a trustworthy pre-failure hash/log of `/bin/busybox` and both symlink targets. None is available in this static audit.

### Does the hypothetical explain no 0e8d:202d?

**Not by itself on the source evidence.** The hypothetical explains `lock`/`netmsg` diagnostics and makes all 13 aliases fail. Yet the ordinary preinit wait does not abort on those statuses. Missing `flock` in procd service setup is logged and handled without returning before wrapper/service setup. The S30usb.init source’s required shell utilities (`sh`, `echo`, `cat`, `mkdir`, `ln`, etc.) are present in the candidate; no direct missing-app-let gate before USB configuration was found. The MIPC/packet-steering paths can lose synchronization or tuning, but their failure is not a direct S30 skip. If S30 executes with META boot mode 0001, its static branch selects PID 202D; if it is not executed, some earlier condition/changed runtime filesystem is needed.

A conditional exception is explicit failsafe mode: the failed `lock -w` loop can prevent procd handoff while `/tmp/sysupgrade` is absent. However the preserved UART has a bounded cluster of lock messages and then silence, rather than a continuously repeated lock diagnostic; it does not prove that the loop ran. Separately, a missing UDC backing store and unverified gadget bind remain possible downstream causes if S30 is reached. Therefore the replacement hypothesis is **consistent with the applet errors**, but **not sufficient to explain the missing USB PID from available evidence**.

## 7. Facts, inferences, remaining unknowns

**FACT:** The exact backup p41 includes a lower BusyBox 1.36.0 and a distinct `busybox_full` that hashes identically to the supplied static 1.37.0 candidate. The upper `/usr/bin/busybox` selects the candidate, while `/bin/busybox` remains the original. `/bin/lock` and `/bin/netmsg` still point to `/bin/busybox`; `/usr/bin/lock` and `/usr/bin/netmsg` are absent. The 13 applets missing from the candidate remain lower aliases to `/bin/busybox` in BACKUP STATE. The offline output and exit codes are recorded above. The failed UART diagnostics match candidate behavior. The p41 inittab and rc links plus procd binary strings establish a procd internal rcS dispatch model; no rcS script file is present or required.

**INFERENCE:** A user-recalled operation replacing canonical `/bin/busybox` bytes with `busybox_full` would make all 13 original-only aliases fail, including the four direct `/bin` links and nine aliases in `/usr/bin`/`/usr/sbin`. This is a strong fit for the failed UART wording, not proof the operation happened. Under ordinary boot, missing applets do not appear to stop rcS/S30 directly; explicit failsafe looping or another changed filesystem/runtime condition would be needed to explain no 202D.

**USER RECOLLECTION:** The backup may have been made after flashing a rootfs with `busybox_full`; the canonical BusyBox may possibly have been replaced just before bootlooping. These are uncertain recollections and were not used as filesystem facts.

**UNKNOWN:** Exact BusyBox bytes and symlinks in the current failed runtime; whether the candidate was copied over `/bin/busybox`; whether `/tmp/sysupgrade`/FAILSAFE state activated the possible spin loop; whether `/data/sysupgrade.tgz` is present and changes the live namespace; whether the init scripts reached S30 or what happened at UDC bind; and whether any closed-source binary uses aliases with no textual call site.

## Required summary

```text
BACKUP /BIN/BUSYBOX SHA256: 45859c936774dc1939f44ede157081452217722b69a2e30c2dbafa76336369b4
BACKUP /USR/BIN/BUSYBOX_FULL SHA256: 43db2f47d9ea4e6ccf02a261a0ab00afb4490eed2d89730e089eacd65dea2273
SUPPLIED CANDIDATE SHA256: 43db2f47d9ea4e6ccf02a261a0ab00afb4490eed2d89730e089eacd65dea2273
BUSYBOX_FULL BYTE-IDENTICAL: YES
BACKUP /BIN/LOCK WORKS: YES (applet present; no-argument probe exits 1 after usage)
BACKUP /BIN/NETMSG WORKS: YES (applet present; no-argument probe exits 1 after usage)
BUSYBOX_FULL LOCK: NO — "lock: applet not found", exit 127
BUSYBOX_FULL NETMSG: NO — "netmsg: applet not found", exit 127
FAILED UART MATCHES HYPOTHETICAL REPLACEMENT: YES, exact diagnostic text; attribution to this exact binary remains unproved
CURRENT FAILED RUNTIME BUSYBOX LACKS LOCK/NETMSG: PROVEN at the reported applet-lookup behavior level; exact executable hash UNKNOWN
FAILED ROUTER DEFINITELY USED BUSYBOX_FULL: NO — strongly supported behaviorally, exact file unknown
/BIN/BUSYBOX OVERWRITE PROVEN: NO — hypothesis only
FIRST POST-PREINIT FAILURE UNDER HYPOTHESIS: missing flock while S001nvram_daemon loads procd helpers; warning/error handled non-fatally. Conditional earlier lock spin only if FAILSAFE=true.
CAN HYPOTHESIS EXPLAIN ABSENCE OF USB 202D: NOT SUFFICIENT BY ITSELF on available source; possible only with an additional condition such as explicit failsafe loop or unrelated S30/UDC failure.
MINIMUM THEORETICAL STATE DIFFERENCE: candidate bytes at canonical /bin/busybox with existing symlinks unchanged; this would break 13 installed aliases, including /bin/{fsync,lock,netmsg,nice}.
NEXT SAFEST STEP: preserve/obtain an exact failed-runtime filesystem image or file/hash evidence offline; do not infer or repair from the backup alone.
```
