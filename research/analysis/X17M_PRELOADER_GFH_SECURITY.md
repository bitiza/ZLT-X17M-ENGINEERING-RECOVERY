# X17M 20250327 Preloader GFH/security metadata

Input: `zlt x17m dumps/mmcblk0boot0.bin`, GFH container beginning at file
offset `0x800`. All integers below are little-endian.

The public structure references used are MediaTek/U-Boot `tools/mtk_image.h`
and the Kaitai `mediatek_preloader.ksy` GFH definitions. The public sources
define GFH_BROM_CFG version 3; this image carries version 4 and a larger
`0xcc` record, so only the common/version-3-compatible prefix is assigned
semantics. The remaining version-4 tail is reported as unknown/zero, not
silently assigned names.

## GFH_FILE_INFO (type 0, file offset 0x800, size 0x38)

| offset | raw/value | field | meaning |
|---|---|---|---|
| 0x800 | `4d 4d 4d 01` | magic/version | `MMM`, GFH version 1 |
| 0x804 | `38 00` = 0x38 | size | 56-byte record |
| 0x806 | `00 00` = 0 | type | `GFH_FILE_INFO` |
| 0x808 | `FILE_INFO\0\0\0` | identifier | file-info identifier |
| 0x814 | `01 00 00 00` = 1 | file_ver | file-info version |
| 0x818 | `01 00` = 1 | file_type | ARM bootloader |
| 0x81a | `02` | flash_dev | NAND enum value 2 in public definitions; wrapper is nevertheless an eMMC boot-region image |
| 0x81b | `05` | sig_type | value 5; signature format is generation-specific and not the public SHA-256 enum |
| 0x81c | `a0 0e 20 00` = 0x00200ea0 | load_addr | GFH load address |
| 0x820 | `38 bc 03 00` = 0x3bc38 | file_len | total GFH/image length |
| 0x824 | `00 00 08 00` = 0x800 | max_size | maximum size field |
| 0x828 | `60 01 00 00` = 0x160 | content_offset | executable content offset |
| 0x82c | `6c 06 00 00` = 0x66c | sig_len | signature extent |
| 0x830 | `60 01 00 00` = 0x160 | jump_offset | entry offset |
| 0x834 | `01 00 60 c2` = 0xc2600001 | attr | image attributes; only known bit assignments are version/tool dependent |

## GFH_BL_INFO (type 1, file offset 0x838, size 0x0c)

Raw record: `4d 4d 4d 01 0c 00 01 00 01 00 00 00`.

`0x840` is `01 00 00 00`. Under the public `gfh_bl_info` definition this is
`bl_attr`; bit 0 is `bl_attr_load_by_bootrom`, so this record requests loading
by BootROM. No other bit is assigned by the public definition.

## GFH_BROM_CFG (type 7, file offset 0x844, size 0xcc)

Header bytes at `0x844..0x84b`:

```text
4d 4d 4d 04 cc 00 07 00
```

This is GFH version 4, record size 204. The version-3-compatible field prefix
decodes as follows:

| offset | raw bytes | field | decoded value/meaning |
|---|---|---|---|
| 0x84c | `92 21 09 13` | cfg_bits | `0x13092192`; public named masks `0x02`, `0x10`, `0x80`, `0x100` are all set |
| 0x850 | `88 13 00 00` | usbdl_by_auto_detect_timeout_ms | 5000 ms |
| 0x854..0x893 | all zero | usbdl_abnormal_timeout_string | empty/NUL string |
| 0x894 | `00` | reserved0 | zero |
| 0x895 | `00` | usbdl_bulk_com_support | disabled/zero under the Kaitai field definition |
| 0x896 | `00` | reserved1 | zero |
| 0x897 | `00` | brom_cmd_via_uart1_disable_magic | no `R` magic (`0x52`) present |
| 0x898 | `00` | brom_cmd_via_usb_disable_magic | no `U` magic (`0x55`) present |
| 0x899 | `00` | boot_aarch64_magic | not the required `0x64` |
| 0x89a | `00` | usbdl_hs_en | zero |
| 0x89b | `00` | reserved3 | zero |
| 0x89c | `88 13 00 00` | usbdl_by_kcol0_timeout_ms | 5000 ms |
| 0x8a0 | `88 13 00 00` | usbdl_by_flag_timeout_ms | 5000 ms |
| 0x8a4 | `00 00` | usbdl_vid | zero/default |
| 0x8a6 | `00 00` | usbdl_pid | zero/default |
| 0x8a8..0x90f | all zero | version-4 extension/tail | no public field definition; retained as unknown zero bytes |

Public U-Boot macros assign these low masks as:

```text
0x02  GFH_BROM_CFG_USBDL_BY_AUTO_DETECT_TIMEOUT_EN
0x10  GFH_BROM_CFG_USBDL_AUTO_DETECT_DIS
0x80  GFH_BROM_CFG_USBDL_BY_KCOL0_TIMEOUT_EN
0x100 GFH_BROM_CFG_USBDL_BY_FLAG_TIMEOUT_EN
```

Therefore the image explicitly disables auto-detect while enabling the
KCOL0/flag timeout controls, each with a 5-second value. The remaining set
bits (`0x13092100` after removing those four public masks) have no authoritative
meaning in the public version-3 structure and are **UNKNOWN**, not DA/META
permissions.

This record contains no public field for DA authentication, SLA, arbitrary
memory read/write, jump-DA authorization, META, factory mode, or eMMC access.

## GFH type 0x0002: GFH_ANTI_CLONE

Record at `0x910`, size `0x14`:

```text
4d 4d 4d 01 14 00 02 00
00 00 00 00 10 00 00 00 80 00 00 00
```

| offset | field | value |
|---|---|---|
| 0x918 | `ac_b2k` | 0 |
| 0x919 | `ac_b2c` | 0 |
| 0x91a..0x91b | pad | 0 |
| 0x91c | `ac_offset` | 0x10 |
| 0x920 | `ac_len` | 0x80 |

This is the public `gfh_anti_clone` / Kaitai `gfh_anti_clone_v1` structure.
The zero mode bytes do not prove anti-clone is globally disabled; they only
describe this GFH record.

## GFH type 0x0008: GFH_BROM_SEC_CFG

Record at `0x924`, size `0x30`:

```text
4d 4d 4d 01 30 00 08 00
00 00 00 00
00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
00 00 00 00
```

Under public `gfh_brom_sec_cfg_v1`:

| offset | field | value |
|---|---|---|
| 0x92c | flags/cfg_bits | 0 |
| 0x930..0x94f | customer_name[0x20] | empty |
| 0x950 | brom_magic_cmd_mode_permanent_dis | 0 (magic not present) |

The public flags define `debug_en` and `jtag_en` in the low byte; both are
zero here. The separate public U-Boot alias `BROM_SEC_CFG_UART_EN` is also not
set. This is BootROM security-configuration metadata, not a Preloader META
policy switch.

No GFH type 3 (`GFH_BL_SEC_KEY`) record is present in this chain.

## Correlation with exact-image code

The exact image contains these strings at the following file offsets:

```text
0x2e15f  usbdl_vfy_da:disabled
0x2e176  usbdl_send_da: clean invalid da
0x2e1c4  usbdl_jump_da: %x
0x30b88  img_auth_required=%x
0x30d5a  seclib_brom_meta_mode
0x3304f  img_auth_required = %x
0x34d90  [SEC_POLICY] sboot_state = 0x%x
0x34db1  [SEC_POLICY] lock_state = 0x%x
0x34dd1  [SEC_POLICY] lock_state(default) = 0x%x
```

These are Preloader code/log/policy artifacts. Their presence does not mean
GFH_BROM_CFG disables BootROM DAA. In particular:

- `usbdl_vfy_da:disabled` is a Preloader DA-verification path/log string;
- `usbdl_send_da` and `usbdl_jump_da` describe Preloader download/jump code;
- `img_auth_required`, `sboot_state`, and `lock_state` are later security-policy
  state and are not GFH_BROM_CFG fields;
- `seclib_brom_meta_mode` is a Preloader security-library state variable and
  is not present in the GFH records.

The previously observed X17M state (`sboot_state=0x1`, `lock_state=0x4`, and
`img_auth_required=1`) therefore belongs to runtime security state, not to a
GFH bitfield. The exact GFH chain provides no proof that an unauthenticated DA
would be accepted.

## Comparison with BootROM TARGET_CONFIG

The live BootROM report gave HW code `0x0992` and `TARGET_CONFIG=0x000000e5`.
That value is returned by the BootROM/SoC security boundary and reflects
hardware/eFuse/BootROM policy. It is not stored in the decoded GFH records.

The separation is:

```text
BootROM/eFuse TARGET_CONFIG  -> DAA/SLA and BootROM command policy
GFH_BROM_CFG                 -> BootROM download timing/mode metadata
GFH_ANTI_CLONE               -> anti-clone metadata region descriptor
GFH_BROM_SEC_CFG             -> BootROM debug/JTAG/UART metadata
Preloader security code      -> img_auth_required, sboot_state,
                                lock_state, seclib_brom_meta_mode,
                                usbdl_vfy/send/jump behavior
```

Nothing in this GFH chain is evidence that the image can override
`TARGET_CONFIG=0xe5` or bypass BootROM DAA. The correct classification for
GFH-mediated arbitrary memory/storage access is **NOT ESTABLISHED**.

## New RG500 artifact

The added RG500 package contains MT6890-related build artifacts, including
`preloader_evb6890v1_64_cpe_nand.bin`, `aee_lk.elf`, `lk.elf`, and a complete
SDK source tree with `T750/.../preloader`, security tools, and MT6890 eFuse
definitions. It is valuable as a comparative source tree and preloader/GFH
reference, but it is not evidence that its security configuration is the
X17M's configuration. The package was not used to overwrite or modify any
X17M image.
