# X17M p41 rootfs_data provenance audit

Scope: read-only examination of the 8 GB backup, p41 (`rootfs_b`), and its embedded ext4 `rootfs_data`. No router communication, image modification, journal replay, repair, or writable mount was performed. The target BusyBox file's contents were not read, executed, or hashed.

## FACT — artifact identity and offsets

The archive on disk is `ZLT_X17M_FULL_BACKUP.zip`; it contains one entry named `ZLT_X17M_FULL_BACKUP.img`, length 7,818,182,656 bytes. The uncompressed `.img` was not separately materialized. SHA-256 was computed on the decompressed image stream.

| Object | Identity / extent | SHA-256 |
|---|---|---|
| Full backup image stream | ZIP entry `ZLT_X17M_FULL_BACKUP.img`, 7,818,182,656 bytes | `0f746cfa55f9853cb48d47e505f83c3d6cdf5cc358c28d4ebfbdc30b6eed55f5` |
| p41 / `rootfs_b` | LBA 1,932,352; byte offset `0x3afa0000`; size `0x20000000` (536,870,912 bytes) | `eb651ffc5492b994beef02beb3aa6e366dbe793308dbe4089af21235b2abbbfa` |
| Embedded p41 `rootfs_data` | p41 + `0x03880000` (59,244,544 bytes; LBA-relative sector 115,712); size `0x1c780000` (477,626,368 bytes) | `54443567d65477838ea0131ab236a91bc0f59c2c34ca9b7e4b1827137c89acbc` |

The p41 hash matches the exact 512 MiB slice streamed from the named ZIP entry at byte offset `0x3afa0000`. The `rootfs_data` hash matches the exact tail slice of that verified p41 extraction. Thus the inspected ext4 file is not a similarly named rootfs from another extraction. The full-image hash is the hash of the ZIP member's decompressed bytes, not the ZIP container.

The ext4 image identifies as label `rootfs_data`, UUID `cf51bad6-6518-4941-9585-8628e62c71b0`. The extracted p41 SquashFS and ext4 tail were separately identified from this p41 container; no `rootfs_a` or 1 GB-model tree was used for this audit.

## FACT — directory traversal and contradictory claim

Read-only `debugfs` traversal of the exact verified ext4 image:

1. `ls -l /upper` lists inode 65595 as `usr`; it does not list `bin`.
2. `stat /upper/bin` returns `File not found by ext2_lookup`.
3. `ls -l /upper/usr` lists `bin`, inode 65596, a directory.
4. `stat /upper/usr/bin` confirms inode 65596, directory mode 0755, uid/gid 0/0, size 5120, ctime/mtime 2026-03-23 04:13:14.
5. `ls -l /upper/usr/bin` lists 227 symlink entries. They are allocated directory entries (not deleted entries): the directory references their inodes, and representative inode 65610 (`busybox`) is marked in-use and resolves by `ncheck` to `/upper/usr/bin/busybox`.

Therefore the earlier narrow statement “`/upper/bin` is absent” was correct. The broader inference that the p41 overlay has no BusyBox-related content was incorrect: it resulted from stopping at `/upper` instead of traversing `/upper/usr/bin`.

All 227 entries below have full path `/upper/usr/bin/<name>`, file type symlink, mode 0777 (`120777`), uid/gid 0/0, size 21, one link, and ctime/mtime `2026-03-23 04:13:14`. `debugfs stat /upper/usr/bin/busybox` reports fast-link target `/usr/bin/busybox_full`. A read-only `rdump /upper` enumeration independently found that all 227 symlinks have that same target. For each name, the allocated ext4 inode is shown:

```text
acpid=65597 adjtimex=65598 ar=65599 arch=65600 arp=65601 arping=65602 ascii=65603 ash=65604
base64=65605 bc=65606 blkdiscard=65607 blockdev=65608 brctl=65609 busybox=65610 bzip2=65611
cal=65612 cat=65613 chgrp=65614 chmod=65615 chown=65616 chroot=65617 chvt=65618 cp=65619
cpio=65620 crc32=65621 crond=65622 cttyhack=65623 date=65624 dc=65625 dd=65626 deallocvt=65627
depmod=65628 devmem=65629 df=65630 diff=65631 dmesg=65632 dnsdomainname=65633 dos2unix=65634
dpkg=65635 dpkg-deb=65636 dumpkmap=65637 dumpleases=65638 echo=65639 ed=65640 egrep=65641
expand=65642 factor=65643 fallocate=65644 false=65645 fatattr=65646 fdisk=65647 fgrep=65648
findfs=65649 fold=65650 freeramdisk=65651 fsfreeze=65652 fstrim=65653 ftpput=65654 getfattr=65655
getopt=65656 getty=65657 grep=65658 groups=65659 gunzip=65660 gzip=65661 halt=65662 hostid=65663
hostname=65664 httpd=65665 hwclock=65666 i2cdetect=65667 i2cdump=65668 i2cget=65669 i2cset=65670
i2ctransfer=65671 ifconfig=65672 ifdown=65673 ifup=65674 init=65675 insmod=65676 install=65677
ionice=65678 ip=65679 ipcalc=65680 kill=65681 klogd=65682 last=65683 link=65684 linux32=65685
linux64=65686 linuxrc=65687 ln=65688 loadfont=65689 loadkmap=65690 login=65691 logname=65692
logread=65693 losetup=65694 ls=65695 lsmod=65696 lsscsi=65697 lzcat=65698 lzma=65699 lzop=65700
mdev=65701 microcom=65702 mim=65703 mkdir=65704 mkdosfs=65705 mke2fs=65706 mknod=65707
mkpasswd=65708 mkswap=65709 mktemp=65710 modinfo=65711 modprobe=65712 more=65713 mount=65714
mt=65715 mv=65716 nameif=65717 nbd-client=65718 nc=65719 netstat=65720 nl=65721 nologin=65722
nproc=65723 nsenter=65724 nslookup=65725 nuke=65726 od=65727 openvt=65728 partprobe=65729
passwd=65730 paste=65731 patch=65732 pidof=65733 ping=65734 ping6=65735 pivot_root=65736
poweroff=65737 ps=65738 pwd=65739 rdate=65740 realpath=65741 reboot=65742 renice=65743
resume=65744 rev=65745 rm=65746 rmdir=65747 rmmod=65748 route=65749 rpm=65750 rpm2cpio=65751
run-init=65752 run-parts=65753 sed=65754 setkeycodes=65755 setpriv=65756 setsid=65757 sh=65758
sha1sum=65759 sha3sum=65760 sha512sum=65761 shred=65762 shuf=65763 sleep=65764 ssl_client=65765
start-stop-daemon=65766 stat=65767 stty=65768 su=65769 sulogin=65770 svc=65771 svok=65772
swapoff=65773 swapon=65774 switch_root=65775 sync=65776 sysctl=65777 syslogd=65778 tac=65779
tar=65780 taskset=65781 tc=65782 telnet=65783 telnetd=65784 tftp=65785 timeout=65786 touch=65787
traceroute=65788 traceroute6=65789 true=65790 truncate=65791 ts=65792 tty=65793 tunctl=65794
ubirename=65795 udhcpc=65796 udhcpc6=65797 udhcpd=65798 uevent=65799 umount=65800 uname=65801
uncompress=65802 unexpand=65803 unix2dos=65804 unlink=65805 unlzma=65806 unshare=65807 unxz=65808
usleep=65809 uudecode=65810 uuencode=65811 vconfig=65812 vi=65813 w=65814 watch=65815
watchdog=65816 wget=65817 who=65818 whoami=65819 xxd=65820 xz=65821 xzcat=65822 zcat=65823
```

The regular target file is in the p41 SquashFS lower filesystem at `/usr/bin/busybox_full` (mode 0755, size 1,975,064 bytes, SquashFS timestamp 2026-03-23 04:08). This is metadata-only identification; its bytes were not examined. There is no ext4 upper entry `/upper/usr/bin/busybox_full`: the upper symlink targets the lower path. Consequently `/usr/bin/busybox` in the merged overlay namespace resolves through the allocated upper symlink to that lower regular file. No claim is made here that this lower file is byte-identical to the separately supplied replacement BusyBox.

### Requested namespace checks

| Path in ext4 upper tree | Result |
|---|---|
| `/upper/bin` | Absent |
| `/upper/bin/busybox` | Absent |
| `/upper/bin/busybox_full` | Absent |
| `/upper/bin/lock` | Absent |
| `/upper/bin/netmsg` | Absent |
| `/upper/usr/bin/busybox` | Allocated symlink inode 65610 → `/usr/bin/busybox_full` |
| `/upper/usr/bin/busybox_full` | Absent; target is in lower SquashFS |
| `/upper/usr/bin/lock` | Absent |
| `/upper/usr/bin/netmsg` | Absent |

## FACT / UNKNOWN — allocated versus historical evidence

The 227 references were observed in the allocated `/upper/usr/bin` directory in the current raw ext4 image view. They are not merely strings, deleted directory entries, orphaned inodes, journal-only remnants, `lost+found` items, or unrelated backup paths. The direct `debugfs` traversal and the read-only extracted namespace agree. No deleted-inode or journal-carving search was needed to establish these live directory references; this audit does not claim that no unrelated historical remnants exist anywhere in the filesystem.

The ext4 superblock reports filesystem state `clean`, while its feature flags include `needs_recovery` and `has_journal`; journal sequence is `0x1ab`, start is 1. Nothing was mounted read-write and no journal replay occurred. A later kernel mount/replay could change the post-recovery view if the journal contains pending metadata, but that possibility is not evidence that it would remove these currently allocated directory entries. The earlier discrepancy is sufficiently explained by incomplete directory traversal; there is no evidence here that journal state caused it.

## FACT / INFERENCE / UNKNOWN — chronology and provenance conclusion

* SquashFS creation/append timestamp: 2026-03-23 04:10:23. This is an image metadata timestamp, not a backup capture timestamp.
* ext4 creation/check timestamp: 2026-03-23 04:13:07; upper symlink directory/inode times: 2026-03-23 04:13:14. These filesystem times describe metadata in the image but do not prove when the raw backup was captured or whether the entries came from the factory image, a prior boot, or a later modification.
* ZIP member timestamp: 2026-03-24 10:19. Host ZIP-file mtime is 2026-03-30; neither establishes when the backup was acquired from the router.
* User recollection says the complete backup predates BusyBox/rootfs changes. The backup contains the allocated symlink fan-out described above, so it is not safe to interpret this artifact as a pristine namespace with no BusyBox indirection. That fact does not, by itself, disprove the recollection: the links may be part of the shipped filesystem, or the chronology/identity of the claimed later modification may differ. The replacement binary's identity/content and the creation history of these entries remain unknown.

The provenance discrepancy is resolved at the filesystem/path level: prior `/upper/bin` absence was accurate but did not establish absence of BusyBox-related upper entries; `/upper/usr/bin` contains them. Chronology is **not** resolved. Under the user's stop condition, this is a positive finding of currently allocated, reachable BusyBox references, so broader boot-impact analysis must pause here pending review. Do not infer that the backup is post-modification or that the candidate replacement caused the failure from this audit alone.

## Required summary

```text
FULL IMAGE SHA256: 0f746cfa55f9853cb48d47e505f83c3d6cdf5cc358c28d4ebfbdc30b6eed55f5
P41 SHA256: eb651ffc5492b994beef02beb3aa6e366dbe793308dbe4089af21235b2abbbfa
ROOTFSDATA SHA256: 54443567d65477838ea0131ab236a91bc0f59c2c34ca9b7e4b1827137c89acbc
CORRECT SOURCE ARTIFACT VERIFIED: YES — p41 slice and p41 rootfs_data tail both hash-match the named backup ZIP member
/UPPER/BIN REACHABLE: NO
BUSYBOX_FULL REFERENCES FOUND: YES — 227 upper symlinks in /upper/usr/bin; target /usr/bin/busybox_full
REFERENCES ALLOCATED: YES — live directory entries and in-use inode targets
REFERENCES REACHABLE: YES — /usr/bin/busybox and 226 other applet aliases resolve via upper symlinks to the lower busybox_full path
REFERENCES DELETED/ORPHANED: NONE among the 227 reported references; no claim about unrelated historical remnants
PREVIOUS /UPPER/BIN ABSENT CLAIM: CORRECT; prior no-BusyBox-override conclusion was incomplete
EFFECTIVE OVERLAY CONTAINS BUSYBOX MODIFICATION: UNKNOWN as a chronology/causation claim; FACT: it contains an allocated symlink fan-out to lower /usr/bin/busybox_full
BACKUP DEFINITELY PRE-MODIFICATION: UNKNOWN from filesystem evidence; user recollection noted but not treated as proof
PROVENANCE CONFLICT RESOLVED: YES for exact path/allocation and enumeration discrepancy; NO for chronology or binary identity
SAFE TO CONTINUE BOOT-IMPACT ANALYSIS: NO — stop for user review because the reachable BusyBox reference is present
```
