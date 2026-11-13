# ZLT X17M read-only forensic report

Date: 2026-09-17  
Scope: offline, read-only analysis of supplied artifacts. No source artifact or block device was written, no filesystem was mounted, and no repair/flash/erase operation was run.

## 1. Executive summary

### FACTS

- `ZLT_X17M_FULL_BACKUP.img` is a 7,818,182,656-byte image of the eMMC user area with a protective MBR, valid primary and backup GPT, 512-byte sectors, and 50 GPT partitions. `sgdisk -v` reports no GPT problem.
- `/dev/mmcblk0p41` is exactly GPT partition 41, `rootfs_b`, at sectors 1,932,352–2,980,927 (512 MiB). It is a hybrid container: an xz-compressed SquashFS created 2026-03-23 followed by an embedded ext4 `rootfs_data` filesystem.
- The supplied 64 MiB `rootfs_b.img` is a different SquashFS, created 2025-12-03. It differs from partition 41 beginning at byte 5 and is not a partition-41 dump.
- The backup's boot-control record selects B: B priority is `0x0f`, A is `0x0e`; both success bytes are `1`. Both available UART boots also say `bootslot=b` and `root=/dev/mmcblk0p41`. Separately supplied live evidence proves another 8 GB unit/state booted A with `bootslot=a root=/dev/mmcblk0p28`.
- Every captured A/B GPT pair differs byte-for-byte across its full extent. This does not by itself mean either copy is corrupt; several pairs contain different signed builds or slot-specific metadata.
- GPT numbering and `/proc/mtd` numbering are distinct naming layers: for example, GPT p28/p41 are rootfs A/B while the vendor MTD view calls them mtd29/mtd42. The MTD table is not a one-to-one physical GPT map.
- Both 512 MiB GPT rootfs containers have an exact tail-sized ext4 `rootfs_data`: A begins at relative `0x036d0000`; B begins at `0x03880000`. This directly explains the approximately 430.8 MiB loop-backed overlay.
- Live `nvcfg` and the `nvcfg.img` stored inside `user_data` both contain `e2p` but no `mac0` or `mac1`. Device identity still exists in `productinfo` (MAC, IMEI, and serial files) and modem calibration/IMEI databases exist in `nvdata`, `nvram`, and `protect*`.
- The two supplied UART files show substantially the same B-slot boot, reaching LK, ATF, the 64-bit kernel handoff, `/etc/preinit`, and early userspace. The earliest networking-related symptom printed is `rai0`/`ra0` lacking private ioctls, followed by missing `mac0`/`mac1` during `board_detect`.
- The firmware's `network` init script intentionally exits after printing `Tozed not run netifd`; absence of netifd is therefore vendor design, not automatically a failure.
- `/sbin/firstboot` cannot restore `mac0`/`mac1`: on eMMC it erases `nvdata` and `boot_para`, then runs `jffs2reset`; it does not rebuild `nvcfg`. Repeating it risks additional loss of modem state.

### INFERENCES

- The missing `mac0`/`mac1` files are a real compatibility/configuration defect, but are unlikely to be the sole root cause of all networking because they are absent even in this reportedly functional backup and because the `ra0`/`rai0` ioctl failures occur first.
- A version/layout mismatch is plausible: the older extracted firmware tree does not read `nvcfg/mac0` or `mac1`, while the later tree does; the active B rootfs is newer than A and all A/B components differ.
- The best next phase is additional read-only collection from a booted unit and controlled discovery of bootloader interfaces. Restoring persistent/NVRAM partitions is not an appropriate first experiment.

### UNRESOLVED QUESTIONS

- The requested March UART capture is absent, so the evidence does not establish two distinct physical units or permit a genuine good-unit/bad-unit comparison. The newly supplied A-slot shell output is also not yet tied to a uniquely identified unit.
- Static analysis now identifies LK's fastboot code as the separate AEE/MRDUMP USB transport, not a conventional flashing implementation. Both LK slots omit `download:`, `flash:`, `erase:`, boot-image, and unlock commands; the exact safe entry trigger remains unproven. A compatible authenticated MediaTek Download Agent is still unavailable.
- The supplied image excludes eMMC boot0/boot1, so neither preloader copy is present for comparison or recovery planning.

## 2. Evidence inventory

### FACTS

| Artifact | Exact bytes | SHA-256 | Identification |
|---|---:|---|---|
| `ZLT_X17M_FULL_BACKUP.img` | 7,818,182,656 | `0f746cfa55f9853cb48d47e505f83c3d6cdf5cc358c28d4ebfbdc30b6eed55f5` | Protective MBR + GPT disk image |
| `rootfs_b.img` | 67,108,864 | `baec6707b37fc7945a5a810de19e5b058665f78a5101a25eeed8c1ef0437dcd5` | SquashFS 4.0, xz |
| `CoolTerm Capture 2026-06-07 16-40-12.txt` | 63,271 | `3e798ceb0333e2cfdf5bd26c6f37ecc10f6e48e376c78be30c74bb3ef5c31bef` | UART capture/data |
| `CoolTerm Capture 2026-06-07 16-42-57.txt` | 64,287 | `f1d804fe83dd524583e7b1741c79627de21981575ba8a76d8029515b0ac0e796` | UART capture/data |

Deterministic directory-manifest digests are recorded in [evidence_inventory.txt](evidence_inventory.txt). The requested `CoolTerm Capture 2026-03-12 20-18-45.txt` is not present. `16-40-12.txt` is present in addition to the named `16-42-57.txt`.

The supplied `zlt-dump/` package was also inventoried. Its eMMC DA identifies MT6890/T750 internally, but it was not executed; its scatter geometry diverges materially from this X17M image after the start of `rootfs_a`. Exact hashes are in [evidence_inventory.txt](evidence_inventory.txt).

Two new analysis-only extractions were made with Sleuth Kit from files already stored in `user_data`:

| Analysis copy | Bytes | SHA-256 |
|---|---:|---|
| `extracted/nvcfg_from_userdata.img` | 33,554,432 | `3b9ae4a9c016b5fdef3dec0b5195cfc382705725b95c09cf6b72d1314e462907` |
| `extracted/nvdata_from_userdata.img` | 33,554,432 | `890a374d651f4fbe9ad17ebe93ad25f4ab947607a30bfe4f525305c93536d811` |

### UNRESOLVED QUESTIONS

- Provenance of `rootfs.original/`, `squashfs-root/`, `rootfs/`, and `ubifs-root/` was not supplied. Key hashes show `rootfs.original` and `rootfs` are closely related, while `squashfs-root` is a different/older firmware tree. They were treated as supporting artifacts, not automatically as exact extracts of partition 41.

## 3. Hardware/SoC observations

### FACTS

- Kernel command line: `androidboot.hardware=mt6890`, 64-bit kernel, 1 GiB DRAM (`Total DRAM = 0x40000000`).
- Storage is eMMC. The user-area GPT is exposed as `/dev/mmcblk0pN`. A separate vendor MTD compatibility view uses different ordinal numbers and smaller logical regions; `/dev/block` symlinks provide the authoritative name-to-GPT mapping for the observed live system.
- The preloader copies are `/dev/mmcblk0boot0` and `/dev/mmcblk0boot1`, not GPT partitions. The full backup begins at the eMMC user area and does not contain either boot hardware region.
- MediaTek signed-image magic `88 16 88 58` appears on the modem, tinysys, LK, TEE, signature, and loader-ext partitions.
- UART reports secure boot state `sboot_state = 0x1`, lock state `0x4`, and `img_auth_required = 1`.

### INFERENCES

- The `mt6890` string is the board/kernel hardware identifier; it should not be used alone to claim the retail SoC part number.

## 4. Complete GPT partition map

### FACTS

All entries use type GUID `EBD0A0A2-B9E5-4433-87C0-68B6B72699C7` (Microsoft basic data); this generic type does not describe actual content. The disk GUID is all-zero, but each partition has a nonzero unique GUID. The complete authoritative map, including unique GUIDs, byte offsets, and byte sizes, follows.

```text
ZLT X17M GPT partition map
Disk bytes: 7818182656
Logical/physical sector: 512/512 bytes
Sectors: 15269888 (LBA 0..15269887)
Protective MBR: present at LBA 0 (type EE, signature 55 AA)
Primary GPT: header LBA 1, entries LBA 2..33
Backup GPT: entries LBA 15269855..15269886, header LBA 15269887
Disk GUID: 00000000-0000-0000-0000-000000000000
GPT verification: sgdisk -v reports no problems
All partitions use type GUID EBD0A0A2-B9E5-4433-87C0-68B6B72699C7 (Microsoft basic data); detected content is independent of that generic type.

#   NAME                START        END    SECTORS   BYTE_OFFSET     BYTE_SIZE UNIQUE_GUID                            DETECTED_CONTENT
1   misc                   64       1087       1024         32768        524288 F57AD330-39C2-4488-9BB0-00CB43C9CCD4   raw/vendor data
2   para                 1088       2111       1024        557056        524288 FE686D97-3544-4A41-BE21-167E25B61B6F   raw/vendor data
3   expdb                2112      43071      40960       1081344      20971520 1CB143A8-B1A8-4B57-B251-945C5119E8FE   raw/vendor data
4   nvcfg               43072     108607      65536      22052864      33554432 3B9E343B-CDC8-4D7F-9FA6-B6812E50AB62   ext4 filesystem
5   nvdata             108608     174143      65536      55607296      33554432 5F6A2C79-6617-4B85-AC02-C2975A14D2D7   ext4 filesystem
6   protect1           174144     190527      16384      89161728       8388608 4AE2050B-5DB5-4FF7-AAD3-5730534BE63D   ext4 filesystem
7   protect2           190528     206911      16384      97550336       8388608 1F9B0939-E16B-4BC9-A5BC-DC2EE969D801   ext4 filesystem
8   mcf1_a             206912     223295      16384     105938944       8388608 D722C721-0DEE-4CB8-8A83-2C63CD1393C7   ext4 filesystem
9   mcf2_a             223296     239679      16384     114327552       8388608 E02179A8-CEB5-48A9-8831-4F1C9C5A8695   ext4 filesystem
10  mcf1_b             239680     256063      16384     122716160       8388608 84B09A81-FAD2-41AC-890E-407C24975E74   ext4 filesystem
11  mcf2_b             256064     272447      16384     131104768       8388608 E8F0A5EF-8D1B-42EA-9C2A-835CD77DE363   ext4 filesystem
12  seccfg             272448     273471       1024     139493376        524288 D5F0E175-A6E1-4DB7-94C0-F82AD032950B   raw security configuration
13  boot_para          273472     277567       4096     140017664       2097152 1D9056E1-E139-4FCA-8C0B-B75FD74D81C6   raw/vendor data
14  proinfo            277568     283711       6144     142114816       3145728 7792210B-B6A8-45D5-AD91-3361ED14C608   raw/vendor data
15  nvram              283712     349247      65536     145260544      33554432 138A6DB9-1032-451D-91E9-0FA38FF94FBB   raw MediaTek NVRAM image/catalog
16  md1img_a           349248     513087     163840     178814976      83886080 756D934C-50E3-4C91-AF46-02D824169CA7   MediaTek signed md1rom/modem firmware
17  md1dsp_a           513088     533567      20480     262701056      10485760 A3F3C267-5521-42DD-A724-3BDEC20C7C6F   MediaTek signed md1dsp firmware
18  spmfw_a            533568     535615       2048     273186816       1048576 8C68CD2A-CCC9-4C5D-8B57-34AE9B2DD481   MediaTek signed spmfw firmware
19  pi_img_a           535616     537663       2048     274235392       1048576 6A5CEBF8-54A7-4B89-8D1D-C5EB140B095B   MediaTek signed pi_img firmware
20  dpm_a              537664     539711       2048     275283968       1048576 A0D65BF8-E8DE-4107-9434-1D318C843D37   MediaTek signed dpm firmware
21  medmcu_a           539712     541759       2048     276332544       1048576 46F0C0BB-F227-4EB6-B82F-66408E13E36D   MediaTek signed medmcu/tinysys firmware
22  sspm_a             541760     543807       2048     277381120       1048576 FBC2C131-6392-4217-B51E-548A6EDB03D0   MediaTek signed sspm/tinysys firmware
23  mcupm_a            543808     545855       2048     278429696       1048576 E195A981-E285-4734-8025-EC323E9589D9   MediaTek signed mcupm/tinysys firmware
24  lk_a               545856     547903       2048     279478272       1048576 E29052F8-5D3A-4E97-ADB5-5F312CE6610A   MediaTek signed LK image
25  tee_a              547904     549951       2048     280526848       1048576 9C3CABD7-A35D-4B45-8C57-B80775426B35   MediaTek signed ATF/TEE image
26  boot_a             549952     615487      65536     281575424      33554432 E7099731-95A6-45A6-A1E5-1B6ABA032CF1   Android boot image (kernel+DTB)
27  rootfs_sig_a       615488     616511       1024     315129856        524288 8273E1AB-846F-4468-B999-EE2EA8E50A16   MediaTek signed cert/rootfs signature blob
28  rootfs_a           616512    1665087    1048576     315654144     536870912 D26472F1-9EBC-421D-BA14-311296457C90   hybrid: SquashFS 4.0/xz + ext4 rootfs_data at +0x036d0000
29  md1img_b          1665088    1828927     163840     852525056      83886080 B72CCBE9-2055-46F4-A167-4A069C201738   MediaTek signed md1rom/modem firmware
30  md1dsp_b          1828928    1849407      20480     936411136      10485760 9C1520F3-C2C5-4B89-8242-FE4C61208A9E   MediaTek signed md1dsp firmware
31  spmfw_b           1849408    1851455       2048     946896896       1048576 902D5F3F-434A-4DE7-8988-321E88C9B8AA   MediaTek signed spmfw firmware
32  pi_img_b          1851456    1853503       2048     947945472       1048576 BECE74C8-D8E2-4863-9BFE-5B0B66BB920F   MediaTek signed pi_img firmware
33  dpm_b             1853504    1855551       2048     948994048       1048576 FF1342CF-B7BE-44D5-A25E-A435ADDD2702   MediaTek signed dpm firmware
34  medmcu_b          1855552    1857599       2048     950042624       1048576 A4DA8F1B-FE07-433B-95CB-84A5F23E477B   MediaTek signed medmcu/tinysys firmware
35  sspm_b            1857600    1859647       2048     951091200       1048576 C2635E15-61AA-454E-9C40-EBE1BDF19B9B   MediaTek signed sspm/tinysys firmware
36  mcupm_b           1859648    1861695       2048     952139776       1048576 4D2D1290-36A3-4F5D-AFB4-319F8AB6DCD8   MediaTek signed mcupm/tinysys firmware
37  lk_b              1861696    1863743       2048     953188352       1048576 FDCE12F0-A7EB-40F7-8350-960972E6CB57   MediaTek signed LK image
38  tee_b             1863744    1865791       2048     954236928       1048576 0FBBAFA2-4AA9-4490-8983-5329328505FD   MediaTek signed ATF/TEE image
39  boot_b            1865792    1931327      65536     955285504      33554432 A76E4B2F-31CB-40BA-826A-C0CB0B73C856   Android boot image (kernel+DTB)
40  rootfs_sig_b      1931328    1932351       1024     988839936        524288 F54AC030-7004-4D02-9481-BBF982036807   MediaTek signed cert/rootfs signature blob
41  rootfs_b          1932352    2980927    1048576     989364224     536870912 C4C310E2-4A7E-77D3-4818-61E2D8BB5E86   hybrid: SquashFS 4.0/xz + ext4 rootfs_data at +0x03880000
42  loader_ext_a      2980928    2981439        512    1526235136        262144 3734710F-0F13-1AB9-734C-12A08EC50837   MediaTek signed loader_ext image
43  loader_ext_b      2981440    2981951        512    1526497280        262144 85A5B02F-3773-18B3-1049-718CDE95107E   MediaTek signed loader_ext image
44  logo              2981952    2998335      16384    1526759424       8388608 6FCE83A6-5273-4748-1145-C205EBB4B8AD   raw/vendor data
45  fibo_para         2998336    3002431       4096    1535148032       2097152 3645E6A3-A7E3-19B2-4941-172C10190EEF   raw/vendor data
46  fibonv            3002432    3067967      65536    1537245184      33554432 F60B92B4-0E2F-91B6-FB4A-2D0B643BAB4B   ext4 filesystem
47  user_config       3067968    3108927      40960    1570799616      20971520 D05CEDFE-20B7-68B3-59F2-4FE25317F2FC   ext4 filesystem
48  productinfo       3108928    3117119       8192    1591771136       4194304 54060B67-FA74-5C82-6116-44821E54DCED   ext4 filesystem
49  user_data         3117120   15237055   12119936    1595965440    6205407232 C0A128FB-59D1-0A9E-F0E8-EA3D36A9D658   ext4 filesystem
50  flashinfo        15237056   15269823      32768    7801372672      16777216 F5F5A7F8-F8EC-3BA1-CBC9-4E2A7CBC7D07   raw/vendor data
```

## 5. A/B slot architecture

### FACTS

| Component | A partition | B partition | Size each | Full-extent comparison |
|---|---:|---:|---:|---|
| preloader | eMMC boot0 | eMMC boot1 | not captured | unavailable |
| mcf1 | 8 | 10 | 8 MiB | different |
| mcf2 | 9 | 11 | 8 MiB | different |
| md1img | 16 | 29 | 80 MiB | different |
| md1dsp | 17 | 30 | 10 MiB | different |
| spmfw | 18 | 31 | 1 MiB | different |
| pi_img | 19 | 32 | 1 MiB | different |
| dpm | 20 | 33 | 1 MiB | different |
| medmcu | 21 | 34 | 1 MiB | different |
| sspm | 22 | 35 | 1 MiB | different |
| mcupm | 23 | 36 | 1 MiB | different |
| lk | 24 | 37 | 1 MiB | different |
| tee/ATF | 25 | 38 | 1 MiB | different |
| boot | 26 | 39 | 32 MiB | different |
| rootfs_sig | 27 | 40 | 512 KiB | different |
| rootfs | 28 | 41 | 512 MiB | different |
| loader_ext | 42 | 43 | 256 KiB | different |

The `misc` partition at byte offset 2,048 contains magic `00 41 42 30` and bytes:

```text
A: priority=0e tries=02 successful=01 update_type=01
B: priority=0f tries=02 successful=01 update_type=01
```

The firmware's own `get_current_slot()` selects the larger priority, so B was selected when this backup was taken. Both UART captures independently confirm B. A separate live command line, `bootslot=a root=/dev/mmcblk0p28`, and symlink `rootfs_a -> /dev/mmcblk0p28` prove that another 8 GB unit or state legitimately booted A.

### INFERENCES

- In the imaged unit, A appears to be an older fallback set: `rootfs_a` was built 2025-03-27; `rootfs_b` was built 2026-03-23. The live A-slot evidence shows that A boot is viable on at least one similar unit/state, but does not prove this backup's complete A set is mutually compatible or safe to select.

### UNRESOLVED QUESTIONS

- No preloader A/B comparison is possible without separate read-only boot0 and boot1 dumps.
- The exact semantics of `tries=02` on this LK build are not documented in the supplied evidence.

## 6. Filesystem map

### FACTS

- ext4: partitions 4–11 and 46–49. Sleuth Kit reports them unmounted cleanly but with the ext4 `needs recovery` incompatibility flag, consistent with an image captured without replaying the journal. No repair was attempted.
- Hybrid rootfs containers: partitions 28 and 41 begin with SquashFS 4.0/xz and contain an embedded ext4 `rootfs_data` in the aligned remainder. The standalone `rootfs_b.img` is only a 64 MiB SquashFS image.
- Android boot image: partitions 26 and 39. Both start with `ANDROID!`, page size 2,048, kernel load address `0x40080000`, and include a DTB.
- Raw/signed MediaTek containers: partitions 16–25, 27, 29–40, 42, and 43.
- Raw/vendor data: misc, para, expdb, seccfg, boot_para, proinfo, nvram, logo, fibo_para, and flashinfo.
- No F2FS, UBI/UBIFS, or JFFS2 signature was detected in the eMMC image outside the identified filesystems. `ubifs-root/` is a supplied directory whose single regular file is not evidence that the full image contains UBIFS.
- Although `/etc/fstab` says `yaffs2` and scripts use MTD/UBI commands, the imaged on-disk persistent partitions are ext4. This is a vendor compatibility/configuration mismatch, not detection of YAFFS2 in the image.

SquashFS comparison:

| Source | Container bytes | SquashFS used bytes | Inodes | Build time | SHA-256/relationship |
|---|---:|---:|---:|---|---|
| partition 28 `rootfs_a` | 536,870,912 | 57,410,288 | 6,599 | 2025-03-27 | differs from B |
| partition 41 `rootfs_b` | 536,870,912 | 59,192,372 | 6,551 | 2026-03-23 | full hash `eb651f…bbfa` |
| standalone `rootfs_b.img` | 67,108,864 | 58,463,666 | 6,566 | 2025-12-03 | `baec67…dcd5`; differs at byte 5 |

The SHA-256 of partition 41's first 64 MiB is `721cca4420ee762d726256e963629302cf3942bb1437a2651e62fbcd6174148e`, which does not match the standalone image.

Embedded overlay map:

| Slot/GPT | SquashFS used | ext4 relative offset | ext4 absolute byte/sector | ext4 bytes | Evidence |
|---|---:|---:|---:|---:|---|
| A / p28 | 57,410,288 | `0x036d0000` (57,475,072) | 373,129,216 / 728,768 | 479,395,840 | ext4 label `rootfs_data`; exact remainder; 91 `fls` entries |
| B / p41 | 59,192,372 | `0x03880000` (59,244,544) | 1,048,608,768 / 2,048,064 | 477,626,368 | ext4 label `rootfs_data`; exact remainder; 959 `fls` entries |

The offsets are 256 KiB-aligned and each ext4 size plus its relative offset equals 536,870,912 bytes exactly. Vendor `libfstools` contains root-disk loop/overlay logic. This proves that `/dev/loop0` is the embedded tail exposed as `/overlay`; filesystem overhead explains why `df` reports about 430.8 MiB rather than the raw 455.5 MiB B-side tail. Partition 41's ext4 has the `needs recovery` feature flag, but no journal replay or repair was attempted.

The separately reported `/dev/mtdblock43 /overlay jffs2` line and 8 MiB MTD `rootfs_data` cannot yet be assigned to this same unit/state. They describe a vendor compatibility view or another layout; they must not be conflated with the directly proven loop-backed ext4 layout.

## 7. Boot-chain reconstruction

### FACTS

1. BootROM executes preloader from eMMC boot0/boot1. These regions are not in the GPT image.
2. Preloader initializes PMIC/DRAM/eMMC, offers a USB tool handshake, enforces secure-boot policy, and loads the selected B-side trusted components. The observed USB-listen timeout is followed by normal boot.
3. `loader_ext_b` (GPT 43) extends the loader path; its exact division of labor with preloader is not fully printed in these captures.
4. `lk_b` (GPT 37) selects slot B, authenticates/loads `sspm_b`, modem/tinysys components, `tee_b`, and `boot_b`, constructs the kernel command line, and hands off.
5. `tee_b` (GPT 38) supplies the signed ATF/TEE payload. ATF identifies BL31 v1.6 and transitions from EL3 to the normal-world 64-bit kernel.
6. `boot_b` (GPT 39) supplies the kernel and DTB. LK boots kernel at `0x40080000`, DTB at `0x42f00000`.
7. `rootfs_b` (GPT 41) is mounted as `/` because LK passes `root=/dev/mmcblk0p41 rootwait init=/etc/preinit bootslot=b`. The kernel/vendor fstools expose the ext4 tail inside that same GPT container through a loop device as the writable overlay.
8. `/etc/preinit` runs OpenWrt preinit hooks, then `/sbin/init`; `S000mount_all` creates device aliases and mounts persistent storage before vendor networking services.

### INFERENCES

- Authentication and kernel handoff are successful in both captures. The observed fault is after the trusted boot chain, in early userspace/network initialization.

### UNRESOLVED QUESTIONS

- The captures do not show explicit successful authentication lines for every named component; some facts about loader-ext/LK/TEE authentication come from the supplied known information rather than a complete UART transcript.

## 8. Persistent-storage analysis

### FACTS

| Partition | Findings | Sensitivity |
|---|---|---|
| nvcfg (4) | ext4, mounted historically at `/mnt/vendor/nvcfg`; only `lost+found` and 655,360-byte `e2p`; no `mac0`/`mac1` | Wi-Fi calibration, high |
| nvdata (5) | ext4; extensive `md/NVRAM/NVD_IMEI` and `CALIBRAT` tree | modem identity/calibration, very high |
| protect1/2 (6/7) | ext4; modem-protection records | very high |
| seccfg (12) | raw security configuration | critical |
| boot_para (13) | raw/mostly zero in string scan; erased by `firstboot` | boot state, high |
| proinfo (14) | raw duplicated device identifiers and firmware strings | identity, high |
| nvram (15) | raw MediaTek NVRAM catalog/data referencing nvdata records | modem/calibration, very high |
| fibonv (46) | ext4; SIM-lock and vendor-NV files | high |
| user_config (47) | ext4; APN/config/SMS state and calibration flag | medium/high |
| productinfo (48) | ext4; IMEI, MAC, serial, credentials, flags | identity/credentials, very high |
| user_data (49) | ext4; logs, backup images, modified rootfs artifacts | mixed, high |

Sensitive identifiers are present and were masked. Examples: IMEI `8613*********77`, MAC prefix `FC:3F:FC:**:**:**`, serial `X17***77`. No full identifier is reproduced here.

The live nvcfg hash is `187fc963…4e5f`; its `user_data/nvcfg.img` backup hash is `3b9ae4a9…2907`. They differ at the filesystem-image level but expose the same allocated directory contents and the same filesystem UUID. The same pattern holds for live and backed-up nvdata. This is consistent with journal/free-space differences and is not evidence that one is a good copy.

`productinfo` also contains `disable_macwriter`, meaning the vendor MAC programming daemon deliberately refuses to run. A later script, `wifi_calibrate_check.sh`, can read `/productinfo/mac` and call `mac_update` only when `ra0` is already visible with a specific default MAC.

The two slot overlays are not equivalent: the A-side ext4 tail has 91 allocated `fls` entries, while B has 959 and includes extensive `/etc` and wireless overrides. This is slot-local mutable state embedded inside each 512 MiB rootfs GPT container.

### INFERENCES

- `productinfo/mac` is the surviving authoritative base MAC candidate. It is not safe to assume that copying it verbatim to both `mac0` and `mac1` is correct; interface-specific derivation rules are not established.
- The backup was not a pristine factory state: `user_data` includes rootfs images/modifications and `productinfo` includes a `backdoor.sh`. This does not invalidate it, but affects provenance.

## 9. UART log analysis — Unit A / capture `16-40-12`

### FACTS

Timeline:

1. Power-key boot; RTC says no two-second reboot and WDT status is zero.
2. PMIC/DRAM/eMMC initialize.
3. USB tool enumeration completes, then times out because no PC tool is detected; boot continues.
4. Secure boot is enabled; selected partition names have `_b` suffix.
5. ATF/TEE and LK initialize; signed modem images authenticate and modem execution is triggered.
6. LK passes slot B and `/dev/mmcblk0p41`, then jumps to a 64-bit kernel.
7. Early userspace prints `ra0 no private ioctls`, missing `nvcfg/mac0`, missing `nvcfg/mac1`, missing BusyBox applets `netmsg`/`lock`, and a failsafe prompt.

No kernel panic, filesystem corruption message, partition-read error, authentication failure, modem-load failure, or watchdog reboot is present. The USB tool timeout is not causal because normal boot continues.

## 10. UART log analysis — Unit B / capture `16-42-57`

### FACTS

The file begins with the tail of a previous early-userspace session (`rai0`, `ra0`, missing MAC files), then records another power-key boot. The second boot repeats the same chain and timings within small variation: USB handshake timeout, B slot, successful modem loading, ATF handoff, and the same userspace warnings.

The end of the capture includes text resembling incomplete `dd if=/dev/zero of=/dev/mmcblk0p...` shell input. The transcript does not show a completed target, command result, or proof that any such command executed. It is therefore evidence of risky console input, not proof of erasure.

### UNRESOLVED QUESTIONS

- File continuity and timestamps strongly suggest these are two captures/boots of one device, not logs from two labeled units. Physical-unit attribution must be supplied externally.

## 11. Comparison of the failures

### FACTS

- Both complete boots are effectively the same: B-slot selection, power-key/WDT state, signed component loading, kernel handoff, and early network warnings.
- Capture B additionally starts with leftover lines from a preceding boot and shows `rai0` as well as `ra0` private-ioctl failure.
- There is no evidence in either available file of one healthy networking boot.

### INFERENCES

- The evidence supports reproducibility of one failure, not a differential diagnosis between a working and failed unit.

## 12. Networking initialization analysis

### FACTS

Observed/static dependency chain:

```text
S000mount_all -> setup_link/update_setup_link -> persistent mounts
              -> board_detect -> /etc/board.d/99-default_network
                 -> reads nvcfg/mac0 and mac1 -> writes board.json/UCI defaults
              -> vendor Wi-Fi/lan_mgr/tzproc
                 -> ra0/rai0 + e2p calibration + optional productinfo/mac update
              -> mtk_netagent / mipc_wan / ccmni modem data path
              -> vendor LAN/WAN services and dnsmasq
```

- `nvcfg` is the partition intended to supply `/mnt/vendor/nvcfg`; its ext4 superblock records that mount point.
- `board_detect` only reads `mac0`/`mac1` to set eth0/eth1 LAN/WAN MACs. Empty values skip those assignments; this script does not create `ra0`, `rai0`, `br0`, or `ccmni*`.
- The log prints Wi-Fi private-ioctl failures before `board_detect` reports the missing files.
- `network` deliberately exits before starting `/sbin/netifd`; vendor processes are expected to own network setup.
- `mipc_wan.init` has `check_sim` commented out and returns early in the supplied tree, so lack of normal OpenWrt netifd/APN behavior may be intentional for this build.
- The UART captures end too early to show dnsmasq, `br0`, ccmni state, SIM registration, DHCP, or the vendor daemons' final status.

### INFERENCES

- Earliest meaningful observed failure: the Wi-Fi interface/driver control path is not ready (`rai0`/`ra0 no private ioctls`). Missing legacy nvcfg MAC files are the next failure and can disrupt deterministic Ethernet MAC assignment, but do not explain creation failure of radio interfaces.
- A rootfs/persistent-layout mismatch could cause both symptoms: the active newer B rootfs expects files absent from both the live and backed-up nvcfg, while the older firmware tree did not expect those files. B also carries a far more populated slot-local overlay, including wireless configuration overrides, so overlay state is an additional differential to inspect.

### UNRESOLVED QUESTIONS

- Whether nvcfg actually mounted during the failed boot; absence of `mac0` is not equivalent to a mount failure because the offline filesystem itself lacks the files.
- Kernel module load status, `dmesg` Wi-Fi probe errors, actual `ip link` output, and vendor daemon process/log state.
- Whether `productinfo/mac` should generate two Ethernet addresses and the precise vendor increment/derivation rule.

## 13. Most likely failure mechanisms

Ranked hypotheses:

1. **Wi-Fi driver/vendor initialization failure or build mismatch — moderate/high confidence.** It is the earliest network symptom and precedes MAC-file reads.
2. **Rootfs B versus persistent-data schema mismatch — moderate confidence.** B is a newer build; all slot pairs differ; newer board defaults expect files not present in either nvcfg copy.
3. **Missing nvcfg `mac0`/`mac1` — high confidence as a defect, low/moderate as sole cause.** It directly breaks LAN/WAN MAC injection but is also true in the reportedly functional backup.
4. **Vendor network-daemon/configuration state failure — moderate confidence.** netifd is intentionally disabled, making the vendor control plane a single dependency; the available logs end before it can be assessed.
5. **Persistent filesystem corruption — low confidence from current evidence.** Journal replay is pending in raw images, but no UART filesystem error is shown and directories are readable offline.
6. **Secure-boot/boot-chain failure — low confidence.** Boot reaches userspace and authenticated stages report success.

## 14. Recovery mechanisms available

No mechanism below was executed.

| Candidate | Evidence | Feasibility | Main constraint |
|---|---|---|---|
| Boot A slot | Complete A GPT set exists; both slots marked successful | plausible diagnostic | requires changing boot-control state; A is older and untested |
| AEE LK fastboot | `aee_lk` contains a minimal MRDUMP fastboot engine at USB `0e8d:201c` | plausible diagnostic endpoint; entry unproven | no `download:`, `flash:`, `erase:`, boot-image, or unlock commands; `set_active` explicitly unsupported |
| UART bootloader command | UART works through LK/Linux | unproven | no LK command prompt or interrupt sequence observed |
| Preloader USB download mode | preloader performs PC-tool USB enumeration/handshake | plausible | secure boot; likely requires compatible authenticated DA/tool |
| BootROM mode | MediaTek platform necessarily has BootROM | theoretical | physical entry method, authorization, and safe read protocol unknown |
| Supplied `zlt-dump` DA | X28 comparison tooling; internal strings identify MT6890/T750 and ACC-bypass patch | rejected by this X17M BootROM before execution | intact transfer followed by `0x7017` (`DAA_Security_Error`); do not execute or reuse absent a new validated hypothesis |
| Restore boot/rootfs slot set | Exact partition map and same-unit backup exist | technically possible after interface validation | boot, rootfs_sig, rootfs and signed companions must remain compatible |
| Restore individual persistent partition | exact same-unit data exists for some partitions | technically possible | device identity/calibration loss or cross-unit contamination |

The supplied `zlt-dump` package originated with X28 recovery work, where the tested routers did not require a signed DA. That is comparison evidence only: signed firmware-image enforcement and DA authentication are separate controls, so the X17M's `img_auth_required=1` does not prove either acceptance or rejection of an unsigned DA. Conversely, X28 acceptance does not establish the X17M's SLA/DAA state.

The package is not safe to use as-is for named X17M reads. Its eMMC scatter matches offsets through the start of `rootfs_a` (`0x12d08000`) but assigns rootfs A only 64 MiB and places `md1img_b` at `0x16d08000`; this X17M image assigns rootfs A 512 MiB and places `md1img_b` at `0x32d08000`. `dump.py` trusts scatter names/sizes and its mismatch check does not detect a same-name/different-size target. Its initial `printgpt` invocation also passes `--da`, so it is a DA-upload test rather than passive USB enumeration. Any later adaptation must derive geometry from the live GPT and enforce exact returned lengths. No DA was run in this phase.

Passive observation of the bootlooped X17M established a repeatable USB sequence: `0e8d:0003` (no USB strings) followed about 2.5 seconds after disconnection by `0e8d:2000` (`MediaTek`, `MT65xx Preloader`). Both stages exposed CDC ACM and briefly created `/dev/ttyACM0`. Two observed cycles began about 43.4 seconds apart. No MTK handshake, payload, DA, storage command, or slot command was sent.

Upstream mtkclient has a `gettargetconfig` command intended to report SBC, SLA, DAA, root-certificate, memory-read-auth, and memory-write-auth bits. Static audit shows that this command calls the full preloader initialization path, which also reads identifiers and can write a transient SoC register. It was not used. With explicit approval, a purpose-built client sent only the MTK four-byte synchronization sequence, `GET_HW_CODE` (`0xFD`), and `GET_TARGET_CONFIG` (`0xD8`) to the `0e8d:0003` stage. It uploaded no DA or payload and contained no memory/storage/reset command.

The query succeeded with hardware code `0x0992`, target configuration `0x000000e5`, and status `0x0000`. Decoded flags are: SBC enabled, SLA disabled, DAA enabled, root-certificate-required bit clear, memory-read authentication enabled, memory-write authentication enabled, and command `0xC8` blocked. Upstream identifies `0x0992` as the MT6880/MT6890 modem family. DAA being enabled means the X28's unsigned-DA behavior cannot be transferred to this X17M: an accepted authentication, signature, or separately validated bypass path is required before a DA can be assumed executable.

The reported 1 GB X17M was then queried independently through its own
`0e8d:0003` window. It returned the identical hardware code `0x0992`, target
configuration `0x000000e5`, and all decoded security flags. This is strong
evidence that the capacity variant does not expose a weaker BootROM DAA policy;
it does not yet establish that its GPT geometry or eMMC sector count matches
the 8 GB layout.

The bundled DAs are v6 containers for hardware code `0x0992` and retain 256-byte signature fields, but the eMMC DA's explicit ACC-bypass patch marker lies inside its declared signed stage-1 data. The retained signature therefore cannot be presumed valid after patching. The ACC bypass is code inside the DA and would act after execution; by itself it does not bypass BootROM's DAA gate.

With separate explicit approval, a purpose-built authentication-only client
then issued `SEND_DA` for the eMMC DA's stage 1 but contained no DA-jump path.
BootROM accepted the header (`0x0000`), received all 218,944 bytes at the
volatile load address `0x00200000`, and returned checksum `0x9a21`, exactly
matching the local XOR16 value. It then returned `0x7017`, identified by the
upstream MediaTek status table as `DAA_Security_Error`. No `JUMP_DA`, memory,
storage, reset, or slot command was sent. Thus the result is not a transport
failure: the supplied patched X28 DA was rejected by this X17M's BootROM
authentication gate and never executed. The preserved JSON is
`analysis/live_usb/x17m-da-auth-nojump-20260917-054232.json` (SHA-256
`e0a8ca6741bc9345e5fa1e4db33e1725a068281be475fa88dc1e3fc532fcce89`).

Upstream mtkclient explicitly lists `mt0992` in its `missing_brom.txt`; its
0x0992 chip entry lacks the complete known BootROM exploit parameters used by
the turnkey bypass paths. This does not prove exploitation impossible, but it
means there is no supported upstream one-command BROM bypass to treat as a
safe recovery mechanism. The X28 patch's preloader payload address is relevant
implementation evidence for a possible preloader-stage route, not proof of an
X17M DAA bypass.

The X17U route is not directly reusable. X17U evidence describes a Unisoc/Spreadtrum `SPRD4:AutoD` downloader and U-Boot protocol; X17M is MediaTek with preloader/LK and signed-image authentication. Reusable lessons are procedural only: establish a read path first, back up exact current state, identify geometry, require immediate full read-back verification, and never transplant device-specific calibration casually.

## 15. Risk assessment

| Risk | Operations |
|---|---|
| Low/read-only | UART capture; enumerate USB IDs; `fastboot devices/getvar` if already in fastboot; read `/proc/cmdline`, `/proc/mtd`, mounts, `ip link`, processes, dmesg; hash/read partitions without changing them |
| Moderate | One-time alternate-slot boot through a proven vendor-supported volatile mechanism; bootloader reboot to an already supported mode |
| High | Writing `misc` boot-control bytes; flashing boot/rootfs/LK/TEE/loader components; executing an unvalidated DA/auth bypass; restoring `user_config`/`user_data` |
| Critical | Writing preloader boot0/boot1, GPT, `seccfg`, `nvram`, `nvdata`, `nvcfg`, `protect*`, `proinfo`, `productinfo`, `fibonv`, or another unit's persistent data |

Secure boot raises the risk of mixing images: a file may parse correctly yet fail authentication or be incompatible with its signature/companion partitions. Device-specific partitions must be preserved per physical unit.

## 16. Recommended next diagnostic steps

All steps below are read-only unless a later, separately approved phase explicitly changes scope.

1. Obtain the missing March capture and label every UART file with physical unit, firmware version, and whether the unit had working Ethernet, Wi-Fi, and cellular service.
2. From the Linux shell, capture without changing state: `/proc/cmdline`, `/proc/mtd`, `/proc/partitions`, `/proc/mounts`, `dmesg`, `ip -details link`, `iwconfig`/`iwpriv` status, `lsmod`, `ps`, and vendor logs under `/tmp/logs` and `/data/log*`.
3. Verify mounts and files only: record `findmnt`/`mount` for nvcfg, nvdata, productinfo; list file metadata for `nvcfg/e2p`, `nvcfg/mac0`, `nvcfg/mac1`, and `productinfo/mac`; do not create missing files.
4. Capture module/probe ordering around mt791x/ra0/rai0 and compare a working unit. This is the shortest path to explaining the first observed ioctl failure.
5. Read and preserve eMMC boot0 and boot1 using a verified read-only method before any bootloader experiment. Hash them separately; they are missing from the current backup.
6. Discover boot modes non-destructively: USB VID/PID during BootROM/preloader/LK windows, LK key/UART behavior, and fastboot enumeration. Limit fastboot to non-mutating queries.
7. If a healthy X17M donor exists, collect only hashes, partition metadata, directory listings, masked identifiers, and UART/network-state logs first. Do not copy its NVRAM/calibration partitions.
8. Before proposing an alternate-slot test, validate A-side signed headers and determine a reversible, vendor-supported slot-selection method. LK's standard fastboot `set_active` is not supported by this build.
9. Do not run `firstboot` again: its static code erases `nvdata` and `boot_para` and cannot recreate the missing nvcfg MAC files.
10. For the smaller-capacity model, collect the physical sector count and live layout before comparing geometry: `/sys/block/mmcblk0/size`, logical block size, `/proc/partitions`, `/proc/mtd`, `/dev/block` symlinks, mounts, `df`, and read-only `fdisk -l /dev/mmcblk0`. The “1 GB” label cannot be treated as literal physical capacity until sector count is known.
11. Treat `zlt-dump` only as protocol/DA research evidence. Do not use its supplied scatter against X17M; first establish whether the DA is accepted using a separately approved, non-writing discovery phase, then obtain geometry from the device's own GPT rather than the legacy XML.
12. Repeat the passive USB capture with each labeled X17M variant. The bootlooped unit has already shown `0e8d:0003` followed by `0e8d:2000`; compare VID:PID order and dwell times before assuming the 8 GB and smaller-capacity models share identical recovery policy.
13. Preserve the target-config and authentication-only results as the recovery-interface baseline. The supplied X28 DA has now been transferred without execution and rejected with `0x7017` (`DAA_Security_Error`); do not execute it or repeat the upload absent a new hypothesis.
14. The smaller-capacity unit has now been tested separately. Its USB sequence and target configuration match the 8 GB unit (`0x0992`/`0x000000e5`, DAA enabled). Do not upload the rejected X28 DA; next collect physical sector count/GPT geometry and pursue only an OEM-authenticated DA or validated 0x0992-specific path.

### Final unresolved decision gate

No write recovery should be designed until the current failed unit has its own complete user-area, boot0, and boot1 backups; the missing UART evidence is obtained; the Wi-Fi driver failure is captured in Linux logs; and a bootloader/download interface has been proven with read-only queries.
