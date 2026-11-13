# X17M 8 GB normal-boot reconstruction through S30

## Scope and conclusion

This read-only report correlates the newly observed explicit-failsafe run with the earlier complete META boot capture, then reconstructs the expected p41 init path through `S30usb.init`. No router communication occurred in this analysis. The full backup, its partitions, and the captured evidence were not modified; p41 SquashFS and p49 user_data were inspected through temporary copies under `/tmp`, without mounting or replaying either filesystem journal.

The explicit-failsafe loop is real and has a distinctive UART signature. That signature is absent from the normal META capture. Thus the normal META boot is **strongly inconsistent with having entered that same repeating failsafe hook**, but the quiet UART tail does not prove that preinit returned or that procd/rcS ran. The highest-value deterministic downstream marker is `Restore nothing`, written by `S001restore` to `/dev/kmsg`; it is absent from the normal capture. On available evidence, the runtime is confirmed only through the preinit failsafe-wait messages. The later stages remain unconfirmed.

## Evidence identity and method

The backup source is the ZIP member `ZLT_X17M_FULL_BACKUP.img` in `ZLT_X17M_FULL_BACKUP.zip` (7,818,182,656 decompressed bytes; whole-image SHA-256 `0f746cfa55f9853cb48d47e505f83c3d6cdf5cc358c28d4ebfbdc30b6eed55f5`). The verified p41 `rootfs_b` starts at byte offset `0x3afa0000`, is `0x20000000` bytes, and has SHA-256 `eb651ffc5492b994beef02beb3aa6e366dbe793308dbe4089af21235b2abbbfa`.

The p41 SquashFS ends at the embedded rootfs_data boundary `p41 + 0x03880000`. Its superblock reports creation/last append `2026-03-23 04:10:23` and filesystem size 59,192,372 bytes. Exact p41 scripts and binaries below were read from this SquashFS slice, not from the separate extracted rootfs tree.

The full backup's p49 `user_data` begins at byte offset `1,595,965,440` (sector 3,117,120) and is 6,205,407,232 bytes. The exact slice was inspected as ext4 using `debugfs` and Sleuth Kit only. Its temporary-copy SHA-256 is `592a4d3d47e48275da7b90279774d4897e5565b01827ed5b0bca382d000f857a`. The ext4 metadata says its last mountpoint is `/data`; `S000mount_all`'s p41 `/etc/fstab` maps `/dev/block/user_data` to `/data` as ext4.

Normal-META runtime evidence is [the complete `20260918T142003Z` capture](live_meta_usbdiag/20260918T142003Z/). The raw UART SHA-256 is `2fb8a5bd7963dcd242461d719a48743cf5ee6bb9d6a7004f39433a78b4b96975`. The USB log records `DISCONNECT` at `2026-09-18T14:20:15.257932Z` and observation through `14:21:46.269210Z`, about 91 seconds later. Its raw stream, not only the printable derivative, was scanned.

## 1. Explicit failsafe signature versus normal META capture

### Explicit failsafe test — FACT

In [the failsafe-entry report](X17M_FAILSAFE_ENTRY_REPORT.md), the UART prompt was seen and the host sent exactly `f\n` once. UART then printed `- failsafe -`, followed by 23,760 `lock: applet not found` diagnostics over the approximately 60-second post-selector interval. No shell prompt appeared. There was no observed reset, panic, watchdog, or reboot.

This matches exact p41 `/lib/preinit/40_run_failsafe_hook`: when `FAILSAFE=true`, it calls the failsafe hooks, then executes `while [ ! -e /tmp/sysupgrade ]; do lock -w /tmp/.failsafe; done`. With the active BusyBox unable to dispatch `lock`, the wait returns immediately and the shell loops, producing the repeated diagnostic. The `- failsafe -` marker and sustained lock-error flood therefore identify this branch far more specifically than the ordinary failsafe-key prompt does.

### Normal META capture — FACT

Raw-byte search of `live_meta_usbdiag/20260918T142003Z/uart_raw.bin` finds:

| Raw offset (decimal) | Bytes decoded as text |
|---:|---|
| 140250 | `lock: applet not found` |
| 140274 | `Press the [f] key and hit [enter] to enter failsafe mode` |
| 140410 | `netmsg: applet not found` |
| 140436 | `netmsg: applet not found` |
| 140462 | `lock: applet not found` |
| 140486 | `lock: applet not found` |

The raw binary contains exactly three `lock` diagnostics and two `netmsg` diagnostics. It contains no `- failsafe -` and no rapid repeated lock stream. After the last readable preinit error, the capture continued for more than 90 seconds after USB `DISCONNECT`; its only later UART bytes were three isolated NULs. The test program was doing RX-only UART capture; it did not send `f` over UART.

The raw file was scanned both for exact byte strings (`grep -aobF`, which finds strings adjacent to NULs) and with `strings -a` so that printable text separated from other binary data was not overlooked. Neither scan finds `- failsafe -`, any repeated lock sequence, procd/rcS markers, restore markers, or `S30usb.init`/USB-init markers. The six strings above are the only failsafe/lock/netmsg matches in the printable-string scan.

### Assessment

**STRONGLY SUPPORTED:** the normal META capture did not enter the same explicit `40_run_failsafe_hook` missing-lock loop observed in the controlled failsafe test. Had that loop been active and serial capture functioning, its many-thousands-of-errors signature should have been unmistakable; the normal capture instead has only the finite ordinary failsafe-wait diagnostics.

This does **not** establish that normal preinit completed. A different hang, failure, console/log-routing change, or an early exit could also yield silence. In particular, absence of UART output is not evidence that a later stage succeeded.

## 2. Exact backup `/data` and S001restore result

### p49 directory evidence — FACT

The full-image partition map identifies p49 as ext4 `user_data`, and the filesystem superblock's last mountpoint is `/data`. Read-only `debugfs` root listing showed `/upgrade`, logs, backup directories, and stored firmware/partition images. Recursive allocated-entry enumeration did **not** find `sysupgrade.tgz`; direct `debugfs stat /sysupgrade.tgz` returned `File not found by ext2_lookup`. No journal replay or recovery was performed. A deleted/unallocated historical object would not satisfy the runtime shell test `-f /data/sysupgrade.tgz` and is not part of the effective namespace.

### S000mount_all — exact p41 source

`/etc/fstab` maps `/dev/block/user_data` to `/data` as ext4. `/etc/init.d/0mount_all` first runs `/etc/setup_link.sh`, creates mountpoints, checks filesystem types with `/usr/sbin/blkid`, runs `mount -a`, then performs vendor setup. It has no unconditional successful-completion message. Most commands are quiet on success; errors from mount/setup commands may appear on stderr or kernel logs, but their absence is not a positive marker that the script completed.

Important safety qualification: the exact script has `mkfs.ext4` fallback commands if `blkid` reports a filesystem type other than `ext4`. The backup p49 is ext4, so the intended branch for the correctly resolved `/dev/block/user_data` does not format it. The script was only inspected, never executed against the router or any image.

### S001restore — exact p41 source

The p41 `/etc/init.d/1restore` is:

```sh
CONFIG_FILE_TAR=/data/sysupgrade.tgz
if [ -f $CONFIG_FILE_TAR ]; then
    echo "Restore $CONFIG_FILE_TAR" > /dev/kmsg
    cd /
    tar -xzf $CONFIG_FILE_TAR
    rm -f $CONFIG_FILE_TAR
else
    echo "Restore nothing" > /dev/kmsg
fi
```

The p41 rc entry is `S001restore`; it follows `S001nvram_daemon` in the rc filename order. In the exact backup state, `/data/sysupgrade.tgz` is absent, so if `S001restore` runs with the backed-up user_data mounted, it takes the `Restore nothing` branch. No archive is extracted, no rootfs file is changed by this script, and the script contains no explicit wait, loop, fatal exit, or return-status gate that would stop rcS. In a state where that archive exists, its intended action is to extract paths under `/`—and could alter rootfs files—then remove the archive; that is not what the inspected backup's allocated namespace contains.

The boot command line captured for this unit includes `console=ttyS0,921600n1` and `loglevel=8`. Because S001restore writes its status directly to `/dev/kmsg`, `Restore nothing` (or `Restore /data/sysupgrade.tgz` in the other branch) is the strongest naturally emitted serial marker for this phase. Both strings are absent from the normal META raw UART. This absence weighs against S001restore having run, assuming the live user_data matches the backup and the normal kernel console configuration remained in effect; it does not prove non-execution because runtime state/console routing could differ.

## 3. Static expected boot sequence

The exact p41 state supports this path:

```text
kernel init=/etc/preinit
  -> /etc/preinit's preinit hooks
       -> failsafe_wait (ordinary timed key window)
       -> run_failsafe_hook (only loops if FAILSAFE=true)
       -> remaining preinit hooks/cleanup
  -> /sbin/init wrapper returns from preinit and execs /sbin/procd
  -> /etc/inittab sysinit entry: /etc/init.d/rcS S boot
       -> procd's internal rcS/runrc dispatcher scans /etc/rc.d/S*
       -> S000mount_all
       -> S001nvram_daemon
       -> S001restore
       -> S30usb.init
       -> ...
       -> S98meta_tst
```

There is no standalone `/etc/init.d/rcS` in the image; p41 `/sbin/procd` contains its inittab/rcS dispatcher strings, and the installed `S*` links provide the run list. The internal-procd explanation is corroborated by its binary strings and prior source-correlation; the source-correlation is not being substituted for the X17M runtime.

The normal capture confirms only the failsafe-wait stage. `S000mount_all`, `S001nvram_daemon`, and `S001restore` are statically ordered before `S30usb.init`; none was directly confirmed at runtime.

## 4. Natural marker audit and UART value

| Stage/source | Exact marker(s) available in p41 | Output route | UART absence value in the normal META capture |
|---|---|---|---|
| `/sbin/init` wrapper | `Console is alive`, `Exec to real procd now`, `- preinit -`, `Launched preinit instance, pid=%d` | The first two are confirmed by AArch64 instructions to call imported `ulog` (the `Exec` call is debug-level gated); they are not direct `printf`/`write` to `ttyS0`. The binary also contains `/dev/console` redirection strings. | **Not meaningful by itself.** ULOG routing/level may not place the line on UART. Raw scan finds none of these strings. |
| `/sbin/procd` | `Parsing inittab - %s`, `valid format is rcS <S|K> <param>`, `running %s/%s%s %s`, service lifecycle strings | Binary logging strings; procd imports `ulog`. No instruction-backed evidence here that these are written directly to serial rather than the logging path. | **Not meaningful by itself.** Raw scan finds no such markers, but logging route is not a reliable serial witness. |
| `S000mount_all` | No unconditional success message. Errors from `blkid`, `mkfs.ext4`, `mount -a`, or setup helpers are possible. | Shell stdout/stderr and kernel messages, depending on command and procd child descriptors. | **Not meaningful.** A successful run is normally quiet. |
| `S001nvram_daemon` | `start nvram_daemon` | Script stdout; the init wrapper has a console setup path, but the exact procd run-script fd route to `ttyS0` is not proven by the strings alone. The spawned service requests stdout/stderr forwarding with `procd_set_param stdout 1` and `stderr 1`. | **Weak/non-conclusive.** It is a possible marker, not a guaranteed one. Raw scan finds none. |
| `S001restore` | `Restore nothing` (archive absent) or `Restore /data/sysupgrade.tgz` (archive present) | Written directly to `/dev/kmsg`; kernel console is `ttyS0` with `loglevel=8`. | **Most meaningful missing marker.** Under the exact backup state and unchanged console, absence moderately/strongly weighs against this script running, but runtime filesystem/console differences remain possible. Raw scan finds neither branch string. |
| `S30usb.init` | `Force on usb device mode`, `Start USB`, `Check BootMode`, `BootMode: <value>`; for META it sets product ID 202D and links mass-storage plus three ACM functions. | Shell `echo` to stdout. Likely visible if procd's script child inherits console, but exact fd routing is not fully established here. | **Suggestive, not proof.** Raw scan contains none. No `0e8d:202d` was observed on passive USB. Could be not reached, or reached with output/bind failure. |
| `/etc/restart_usb.sh` started by S30 | `usb.init done` after the delayed UDC write | Shell stdout, after `sleep 2`; script repeats usb.init/UDC attempts while `/dev/usb-ffs/adb/ep1` is absent. | **Suggestive, not proof.** No marker or 202D device in capture. A failed bind does not itself stop the script from printing `usb.init done`. |

The raw-byte marker scan also checks the intact binary stream around NULs; it is not limited to a line-oriented transcript. The only matching printable strings from the failwait/lock search are the finite errors and prompt listed above. Exact p41 string/sequence markers from init, procd, restore, and usb.init are absent.

## 5. What S001restore can and cannot explain

**FACT:** The inspected full-backup p49 has no allocated `/data/sysupgrade.tgz`. In backup state, S001restore therefore does not invoke `tar`, does not remove a restore archive, and does not make an overlay/rootfs change. It would issue only `Restore nothing` to the kernel log.

**FACT:** If a `sysupgrade.tgz` existed in a different runtime state, the script would extract it under `/` and remove it. Thus a populated archive could change the effective root filesystem. The exact p41 script does not test `tar` success or explicitly abort rcS after the command; a pathological archive/tool failure is not evidenced here.

**INFERENCE:** S001restore is not a plausible cause of the normal META capture's silence based on this backup: the file is absent, so its normal branch is quick and non-blocking. The missing expected kmsg marker is evidence that the run may not have advanced as far as S001restore, but is not conclusive.

## 6. Reassessment and stage classifications

| Question | Assessment | Basis / limits |
|---|---|---|
| NORMAL BOOT ENTERS FAILSAFE LOOP | **NOT SUPPORTED; strongly contradicted** | Normal META raw has three finite lock errors, two netmsg errors, no `- failsafe -`, and no flood for >90 seconds. Explicit selector capture's 23,760-error loop is unmistakably different. Silence alone does not prove later progress. |
| NORMAL PREINIT LIKELY COMPLETES | **STRONGLY SUPPORTED, not proven** | Ordinary failwait path is timed; the observed diagnostics match its finite countdown/unlock calls; the explicit loop signature is absent. No later preinit-completion or init marker is present. |
| PROCD REACHED | **UNKNOWN** | No raw UART procd marker. p41 init/procd strings use ULOG and do not guarantee serial visibility. No independent runtime evidence shows the exec/handoff. |
| S000MOUNT_ALL REACHED | **UNKNOWN** | It is first in static rc order but has no unconditional success marker; successful mount commands are quiet. |
| S001RESTORE REACHED | **UNKNOWN; expected marker absent** | The backup has no sysupgrade archive, so `Restore nothing` should be sent to kmsg if the script runs. It is absent from raw UART; live filesystem and printk visibility are assumptions, so this is not proof. |
| S30USB.INIT REACHED | **UNKNOWN / NOT OBSERVED** | No `Start USB`, `Check BootMode`, `BootMode: 0001`, `usb.init done`, or 0e8d:202d device. Console routing and UDC failure still prevent an absolute conclusion from absence. |

The one proven control-flow distinction is: **explicit failsafe selection causes the missing-lock loop; the normal META run does not exhibit its UART signature.** The normal run's furthest confirmed point remains Linux preinit's failsafe wait, not procd.

## 7. Next marker interpretation (static only)

No further live action is included in this report. If existing UART evidence is later collected without changing the router, `Restore nothing` is the earliest strong expected serial marker after `S001restore` starts, while the earlier init/procd messages are ULOG or have uncertain forwarding. `Start USB` / `Check BootMode` would indicate S30 script execution if visible; `usb.init done` indicates restart_usb reached its delayed bind attempt, not that the bind succeeded. Passive 202D enumeration would independently demonstrate successful gadget binding/enumeration. None of these is present in the existing normal capture.

## Required summary

```text
NORMAL BOOT ENTERS FAILSAFE LOOP: NOT SUPPORTED; strongly contradicted by direct signature comparison
NORMAL PREINIT LIKELY COMPLETES: STRONGLY SUPPORTED, not proven
PROCD REACHED: UNKNOWN
S000MOUNT_ALL REACHED: UNKNOWN
S001RESTORE REACHED: UNKNOWN; expected Restore nothing marker absent
S30USB.INIT REACHED: UNKNOWN / NOT OBSERVED
P49 /data/sysupgrade.tgz: ABSENT from allocated backup namespace
S001RESTORE ACTION IN BACKUP STATE: no tar extraction; emits Restore nothing to /dev/kmsg
CAN S001RESTORE ALTER ROOTFS: yes, only if a runtime /data/sysupgrade.tgz exists; none is in this backup
EARLIEST HIGH-VALUE POST-INIT UART MARKER: Restore nothing (S001restore -> /dev/kmsg)
NORMAL META UART EVIDENCE ENDS AT: preinit failsafe-wait diagnostics; no direct procd/rcS marker
S30 CAUSAL STATUS: not established; no runtime marker, and no 0e8d:202d enumeration
NEXT SAFE STEP: interpret only already-preserved evidence; no additional target interaction performed
```
