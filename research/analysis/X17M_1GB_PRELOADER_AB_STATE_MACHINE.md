# X17M 1 GiB NAND Preloader A/B state machine

Date: 2026-09-21  
Scope: read-only analysis of the working-router NAND backup and the matching
MT6890 SDK source. No router was contacted, and no image or device was changed.

## Evidence and confidence

The backup images are:

| Image | SHA-256 |
|---|---|
| `logical/mtd00_preloader.img` | `5152173ee3f604dcd65edaa199812703f97acd391cb7a0d9c27ab9a5568567f5` |
| `logical/mtd25_lk_a.img` | `a757f40b3c7da58167c56cde10728768196f42e53a8c10c49e6de97fd9ef1b5e` |
| `logical/mtd39_lk_b.img` | `a757f40b3c7da58167c56cde10728768196f42e53a8c10c49e6de97fd9ef1b5e` |

LK A and B are byte-identical. The Preloader contains the source path
`platform/common/bootctrl/2.0/ab_bootcheck.c` and the distinctive A/B log
strings used by the SDK implementation. The source is from the 2023 MT6890
RG500 SDK, not the exact September 2025 X17M source release. Its correspondence
to the dumped binary is strong, but it is not an instruction-for-instruction
proof of every branch in that binary. In particular, an extra exact-binary
message, `restore the misc partition`, has not yet been tied to a precise
branch, and the retry-update call site remains unresolved.

## Boot-control record

The MediaTek/AVB metadata record begins at `misc + 0x800` and is 32 bytes.
Fields are serialized as bytes:

| Record offset | Field | Meaning used by A/B code |
|---:|---|---|
| `+0x00..03` | magic | `\0AB0`; checked by `get_suffix()` |
| `+0x04` | major version | Not checked by the matching selection code |
| `+0x05` | minor version | Not checked by the matching selection code |
| `+0x06..07` | reserved | Not used by the matching selection code |
| `+0x08` | A priority | 0 means unbootable; maximum 15 |
| `+0x09` | A retry count | Compared with threshold 5 by Preloader |
| `+0x0a` | A successful-boot flag | Read and logged, but not used in the fallback branch |
| `+0x0b` | A `up_type` | NAND Preloader-maintenance state |
| `+0x0c` | B priority | Same semantics as A |
| `+0x0d` | B retry count | Same semantics as A |
| `+0x0e` | B successful-boot flag | Same semantics as A |
| `+0x0f` | B `up_type` | Same semantics as A |
| `+0x10..1f` | reserved / CRC area | CRC is not validated by the matching selection code |

There is no separate unbootable flag: priority zero is the unbootable value.
`check_valid_slot()` reports a valid A/B set if either slot has priority above
zero. It does not check `successful_boot` or retry count.

The captured working-router record at `misc + 0x800` is:

```text
00 41 42 30 ff ff ff ff 0f 02 01 00 00 00 00 00
```

It has valid magic, A priority 15 / retry 2 / successful 1 / `up_type` 0, and B
priority 0 / retry 0 / successful 0 / `up_type` 0. This is consistent with the
known-good router booting A. It does not reveal either failed router's state.

## Suffix selection and fallback

The source-correlated flow is:

1. `get_suffix()` reads the metadata from `misc + 0x800`.
2. If magic is valid, the larger priority wins; a tie selects A. Retry and
   successful-boot fields do not select the slot.
3. If magic is invalid, `ab_metadata_init("_a")` initializes A to priority 15,
   successful 1, retry 0, `up_type` 0; B to priority 0, successful 1, retry 0,
   `up_type` 0. It then writes the record copies described below.
4. `ab_ota_boot_check()` reads the selected suffix's retry count, success flag,
   and NAND `up_type`. The success flag is logged. Its conditional is commented
   out in the correlated source.
5. If either slot has nonzero priority and selected retry count is at most 5,
   the routine normally returns and continues booting the selected slot.
6. If retry count is above 5, `ram_console_is_abnormal_boot()` is checked. An
   abnormal result logs `skip switch for abnormal in while boot failed` and
   returns without changing slot metadata.
7. Otherwise `rollback_slot()` raises the opposite slot's priority to 15. If
   the current slot also had priority 15, it is lowered to 14. Retry,
   successful-boot, and `up_type` values are otherwise left unchanged.
   `ab_set_boot_part()` is a no-op for NAND; the updated metadata controls the
   suffix selected by later boot-image loading. Ordinary NAND fallback does
   not request a reset in this code path.
8. If both priorities are zero, the routine sets `g_boot_mode` to
   `RECOVERY_BOOT` and logs `no valid slot`; it does not choose the other slot.

For NAND, `mark_slot_invalid()` is excluded from this path by the source's
compile-time conditional. The matching source's non-NAND path does call it;
that helper sets priority and successful-boot to zero.

### Retry semantics and boot failure

The source has a `reduce_retry_count()` helper that decrements a positive value,
but the call in `ab_ota_boot_check()` is under `#if 0`. The matching routine
itself therefore does not decrement the counter after a Linux failure. The
optional `ql_increase_boot_retry_count()` helper increments the selected slot's
counter under `MTK_AB_OTA_UPDATER` on NAND; its unique log string is absent from
the exact Preloader, so this helper's inclusion/call site is not established
for this build. The exact Preloader does contain the A/B retry-threshold and
abnormal-boot messages.

The A/B routine does not observe Linux reaching userspace. Its apparent failure
criterion is stored retry count greater than 5, with a watchdog/abnormal-reset
gate that suppresses automatic switching. `successful_boot=1` does not exempt a
slot from that threshold in the matching routine. The exact small-NAND
Preloader's complete retry-counter lifecycle remains unproven until the
counter-update call site is tied to its binary control flow.

The abnormal-boot check is the only identified reset-state input to this
fallback path. Preloader strings mention watchdog status in its abnormal-boot
diagnostics. In this routine that state prevents switching; it does not itself
select the alternate suffix.

## `misc` copies, repair, and NAND write targets

For NAND, the matching `read_write_partition_info()` logic reads up to four
copies of the 32-byte metadata, separated by the NAND erase size. When a later
copy has valid magic after an invalid earlier copy, it repairs the immediately
preceding copy by erasing that copy's full eraseblock and writing the 32-byte
record at offset `+0x800` in that block. If every copy has invalid magic,
`get_suffix()` initializes default A metadata.

Metadata writes erase and program all four copies. The working router's NAND
erase size is `0x40000`; its `misc` partition base is logical offset `0x700000`.
The resulting logical offsets are:

| Copy | Full eraseblock erased | 32-byte record programmed |
|---:|---:|---:|
| 0 | `misc + 0x00000` = `0x700000` | `misc + 0x00800` = `0x700800` |
| 1 | `misc + 0x40000` = `0x740000` | `misc + 0x40800` = `0x740800` |
| 2 | `misc + 0x80000` = `0x780000` | `misc + 0x80800` = `0x780800` |
| 3 | `misc + 0xc0000` = `0x7c0000` | `misc + 0xc0800` = `0x7c0800` |

The same relative layout applies if lookup falls back to `para`, whose base in
this backup is `0x800000`. `para` is used only when `misc` partition lookup (or
the early SRAM address lookup) fails. It is not selected merely because a
readable `misc` record has invalid contents. `para` is distinct from the
`boot_para` MTD partition.

Other writes/erases represented by the matching NAND A/B source:

* `rollback_slot()`, default metadata initialization, and `up_type_set()` use
  the four-copy metadata writer above.
* `reduce_retry_count()` would use that writer if called; the correlated
  `ab_ota_boot_check()` decrement call is compiled out.
* The optional retry-increment helper would use that writer if it is present
  and called; the exact binary call site is unresolved.
* The NAND `up_type` maintenance path can erase one `0x40000` block at
  `preloader + 0x40000` (logical NAND offset `0x40000`). In the working layout,
  this is the second eraseblock of MTD `preloader`. The correlated source
  associates `up_type=4` with erasing it, changing `up_type` to 1, then reset;
  an `up_type=1` retry/rollback path can erase it before rollback and reset.

These offsets describe logical NAND/partition offsets passed to the NAND
driver; physical bad-block remapping remains the driver's responsibility.
No device or image was written during this analysis.

The exact binary's string `restore the misc partition` is not present in the
near-matching SDK source at that exact wording. The redundant-copy repair above
is a plausible corresponding operation, but the string's exact caller/branch
is not yet established.

## Volatile overrides

No suffix override was found in the source-correlated A/B routine for META
arguments, keys, RTC, watchdog reason, or command line. `METAMETA` selects META
boot mode; it does not change the A/B record. The watchdog/abnormal flag gates
fallback as described above. A/B command-line arguments are downstream of
Preloader selection, and no command-line-dependent suffix override was found.
When neither slot is bootable by priority, the routine requests recovery mode
rather than temporarily selecting the opposite slot.

This is negative evidence from the matching source plus exact-binary strings,
not a proof that no unrelated undocumented path exists elsewhere in the exact
Preloader.

## Artifacts

* Exact NAND Preloader/LK recovery surface: `X17M_1GB_PRELOADER_LK_RECOVERY_SURFACE.md`.
* Exact backup inventory and limitations: `/home/kali/Desktop/bozax17/backups/x17m-1gb-20260921-061524/README.md`.
* Partition physical ranges: `/home/kali/Desktop/bozax17/backups/x17m-1gb-20260921-061524/metadata/physical-ranges.json`.
