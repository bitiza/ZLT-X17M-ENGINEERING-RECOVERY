# A/B boot control

## Record format

The NAND build stores redundant A/B metadata beginning at `misc + 0x800`.

The 32-byte record contains:

```text
+0x00  magic "\0AB0"
+0x04  version/reserved
+0x08  A: priority, retry, successful_boot, up_type
+0x0c  B: priority, retry, successful_boot, up_type
+0x10  reserved / CRC area
```

Priority zero means unbootable. The greater valid priority wins; a tie selects A.

## NAND redundancy

With the 256 KiB erase size and reference `misc` base `0x700000`:

```text
copy 0: eraseblock 0x700000, record 0x700800
copy 1: eraseblock 0x740000, record 0x740800
copy 2: eraseblock 0x780000, record 0x780800
copy 3: eraseblock 0x7c0000, record 0x7c0800
```

The normal metadata writer is eraseblock-aware and updates redundant copies.

## Reference working unit

Observed state:

```text
A: priority 15, retry 2, successful_boot 1, up_type 0
B: priority  0, retry 0, successful_boot 0, up_type 0
```

B was therefore not a valid boot candidate on that particular NAND unit despite containing a factory-looking rootfs. This must not be generalized to another router.

## eMMC observation

A separately observed eMMC X17M has the same logical record at `/dev/mmcblk0p1 + 0x800`:

```text
00 41 42 30 00 00 00 00 0f 02 01 00 00 00 00 00
```

This parses to A = priority 15, retry 2, successful_boot 1, up_type 0; B = all zero. The vendor boot-done service independently reported `FLASH_TYPE=emmc`, `is_ab_partition=1`, and `current_slot=_a`.

This is evidence that the observed NAND and eMMC builds share the logical A/B record format. It is **not** evidence that their physical metadata-writing procedures are interchangeable.

## Rollback behavior

Source-correlated behavior shows:

- higher valid priority wins;
- priority zero is invalid;
- invalid metadata initializes an A-oriented default;
- rollback can promote the opposite slot;
- an abnormal-boot condition can suppress switching.

The exact production retry-counter lifecycle remains unresolved.

## Safety

Do not treat `misc` as a one-byte slot flag. On NAND it is redundant metadata with eraseblock-aware update behavior. On the observed eMMC unit the record is in GPT partition `misc` at offset `0x800`; NAND write procedures must not be transferred to eMMC.

## UNRESOLVED

- Exact retry-counter update path in the 2025 Preloader.
- Exact caller/meaning of the production-only `restore the misc partition` path.
- Whether a legitimate reset/boot condition can select an existing valid opposite slot without an external metadata write.
