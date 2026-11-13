# X17M 1 GiB factory META boot-chain analysis

Scope: offline analysis of the exact NAND factory slot-B SquashFS, boot/LK
partitions from the verified 1 GiB backup, and the already-recorded META USB
experiment on the known-good router. No router was contacted and no firmware
was modified.

## Finding

The artifacts do **not** indicate that META is supposed to select another
Linux image or another A/B slot. META is a boot-mode value carried alongside
the ordinary Linux handoff. Linux should still boot the selected slot, then
change its service behavior based on `/proc/device-tree/chosen/atag,boot`.
Thus seeing A-slot Linux and `bootslot=a` is compatible with a successful META
handoff; it does not by itself mean that the mode was lost.

The factory userspace has an explicit META USB profile (`0e8d:202d`) and starts
the META daemon, so the product was designed to expose a Linux META gadget.
The profile links a mass-storage function but never assigns it a backing file
or block device. That proves the profile cannot export useful mass storage;
it does **not**, by itself, prove that Linux refuses to bind the composite
gadget or explain the complete absence of USB. The META daemon independently
expects `/dev/ttyGS0`, which depends on the ACM function. The artifacts do not
identify why no USB device appeared; a lost mode tag or UDC/configfs failure
remains possible, and kernel errors are needed to discriminate these paths.

## Exact artifacts checked

* Factory rootfs: backup `backups/x17m-1gb-20260921-061524/logical/mtd43_rootfs_b.img`, SHA-256
  `77d13d3cc0e172d23c10b18ae717db03b766bff29c813b249e5ac7e1b0f706f1`.
  It is the September 9, 2025 factory SquashFS extracted to
  `/tmp/x17m_nand_factory_B`.
* Exact factory `/etc/init.d/usb.init` SHA-256
  `21077ebe11877101ba41be6eab15d7159fa91b50b30d8a9b08648c9b406df6d7`.
* Exact factory `/etc/restart_usb.sh` SHA-256
  `b5ac7df120332004f887dbfca0aff43b3e171d28a1c0993fc48204c05917e7d5`.
* Exact factory `/usr/bin/meta_tst` SHA-256
  `c66ac91fb7490037f680f68da898ba2415e476f5266e237f0fdfc1c0b0a96bc0`.
* `mtd25_lk_a.img` and `mtd39_lk_b.img` are byte-identical,
  SHA-256 `a757f40b3c7da58167c56cde10728768196f42e53a8c10c49e6de97fd9ef1b5e`.
* `mtd27_boot_a.img` and `mtd41_boot_b.img` are byte-identical,
  SHA-256 `491b86624981d3314b9c99e90d5632bb0242165cae97a10c612a0f742ec145cb`.
* The USB and META init scripts in the known-good router's modified A rootfs
  have the same hashes as the exact factory B copies listed above. The live
  USB result therefore exercised the same relevant startup scripts.

## Reconstructed path

1. **Preloader selector.** The recorded USB exchange completed the full
   `METAMETA` transaction (`ATEM0001`, 12-byte record, `ATEM0002`, 16-byte
   record, `ATEMATEX`, host disconnect). Exact Preloader strings and the
   correlated selector implementation support that this changes the boot
   mode to META after the host disconnect. The selector is not a Linux boot
   image selector or a storage-read command.

2. **LK handoff.** The exact NAND LK contains `atag,boot`,
   `set_fdt_atag_boot`, `lk boot mode = %d`, `app/gem_boot/meta.c`,
   `atag,meta`, and `set_fdt_atag_meta`. This supports LK passing the boot
   mode and META communication parameters in the device tree while continuing
   its ordinary Linux handoff. A complete exact-image instruction-level trace
   of the FDT writer was not recovered, so this is binary-supported rather
   than a captured runtime fact for the 1 GiB experiment.

3. **Linux startup.** Factory `/etc/inittab` runs the ordinary OpenWrt `rcS`
   boot sequence. Its rc links start `S30mipc_wan.init` and `S30usb.init`,
   followed later by `S98meta_tst` and `S99fibo_rndis.init`. The MIPC WAN and
   RNDIS network scripts read the same `atag,boot` property and exit when its
   value is `0001`; META therefore suppresses normal modem-WAN/RNDIS startup,
   but does not change rootfs or prevent other Linux services from running.

4. **USB selection.** `usb.init` sets the controller to device mode, creates
   configfs gadget `g1` (VID `0e8d`, product string `mt6890`), and reads field
   six of the `hexdump` of `atag,boot`. For `0001` it selects product `202d`,
   configuration `dualacm`, and links:

   ```text
   f1 -> mass_storage.usb0
   f2 -> acm.gs0
   f3 -> acm.gs1
   f4 -> acm.gs2
   ```

   It does not start USB ADB in this branch. The tree-wide search found no
   assignment to `functions/mass_storage.usb0/lun.0/file` (nor any mass-storage
   backing assignment in another factory script). No disk image or block
   device is exported by this profile. This is not proof of UDC bind failure: a
   mass-storage LUN may enumerate without media. The kernel config does include
   configfs, ACM and mass-storage gadget support, so this is not simply a
   missing compiled gadget function.

5. **Bind and daemon.** The service starts `/etc/restart_usb.sh`, which waits
   two seconds and writes `11201000.usb` to the gadget's UDC file. It does not
   check or log the write result. It then loops and retries `usb.init` whenever
   `/dev/usb-ffs/adb/ep1` is absent. In META mode ADB was not configured, so
   that condition may remain true and cause repeated setup attempts; this is a
   script logic bug candidate, not a proven cause of non-enumeration.

   `S98meta_tst` starts the AArch64 `/usr/bin/meta_tst` unconditionally. The
   binary contains the exact `atag,boot` path and normal/META mode messages,
   depends on vendor modem libraries, and contains `/dev/ttyGS0` plus META UART
   discovery strings. It is a META protocol/modem service, not the gadget
   creator. If USB ACM does not bind, its expected serial endpoint is missing.

## What the live test establishes

After the full Preloader selector exchange, the Preloader USB device
disappeared and no Linux device, including the expected `0e8d:202d`, appeared
during the following 90-second observation. Network ADB remained reachable;
read-only checks showed `root=/dev/mtdblock29`, `bootslot=a`, and a running
Linux system. There was no UART attached, so the test did not capture LK's
printed boot mode or the kernel's FDT tag.

The result proves that the selector did not expose a useful host service before
Linux and that the router returned to A-slot Linux. It does **not** establish
that the kernel lost META mode: ordinary A-slot Linux and ADB/network services
are compatible with the factory META design. The same factory startup scripts
are present in the modified A image used for this live test.

## What is and is not diagnosed

1. **Confirmed defect — no mass-storage backing.** This explains why the
   advertised mass-storage function cannot provide useful storage. It may
   still enumerate as an empty LUN, so this does not explain the missing
   composite USB identity on its own.
2. **Unresolved — the META boot tag may not reach Linux or may be misread.** The
   factory consumers and LK strings show the intended path, but the 1 GiB test
   lacks a UART capture of LK's `lk boot mode` and the Linux FDT property. A
   wrong tag would select the ordinary USB profile instead of `202d`.
3. **Unresolved — configfs/UDC bind or sequencing failure.** The shell ignores
   configuration and UDC write errors. If `devinfo 102020` reports `usr`, it
   skips ADB setup, while the restart loop still waits for an ADB FunctionFS
   endpoint. This is a retry-loop bug candidate, but the image alone does not
   reveal the runtime devinfo value or actual kernel errors.

No offline evidence supports an automatic fallback from META into a separate
normal A image. The observed root slot is the same slot expected to boot under
META. The unresolved points are whether `atag,boot=1` reached Linux and, if it
did, whether the `202d` profile was selected and which configfs/UDC operation
(if any) failed. The factory image gives no basis for claiming that the
unbacked mass-storage LUN itself prevents enumeration.

## Evidence needed to decide conclusively

A passive UART capture on a later META boot should record: LK's boot-mode
print; `/proc/device-tree/chosen/atag,boot`; `devinfo 102020`; `usb.init` and
`meta_tst` output; the configfs function attributes including
`mass_storage.usb0/lun.0/file`; and the kernel response from writing
`11201000.usb` to UDC. This will distinguish mode loss from Linux META with a
failed gadget without issuing any storage or write/erase commands.
