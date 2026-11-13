# MT6890 tool-auth binary, key, trust-anchor, and `SEND_AUTH` analysis

Date: 2026-09-21  
Scope: offline inspection only. No USB device was opened, contacted, or
modified. The analysis used the extracted T750 SDK, its Python 2 bytecode
libraries, the supplied MT6890 NAND Preloader image, and local mtkclient
source.

## Executive result

The SDK can generate a complete `customer_da.auth`/`auth_sv5.auth` object. The
generated PSS artifact is 2,256 bytes:

```text
0x0000..0x07cf  GFH tool-auth object (0x7d0 bytes)
0x07d0..0x08cf  one 2048-bit RSA-PSS signature (0x100 bytes)
```

The outer signature is made with `keys/toolauth/root_prvk.pem`. The embedded
DAA public key is made from `keys/toolauth/da_prvk.pem`; in this SDK those two
keys are identical. The embedded SLA key is `sla_prvk.pem` and is different.

Most importantly, the MT6890 Preloader source contains `OEM_PUBK` equal to the
root/DA modulus, and the supplied exact NAND Preloader image contains that same
256-byte modulus at file offset `0x39ae0`. This is substantially stronger than
the earlier conclusion that the SDK key was merely a development key.

It still does not prove that every production router has this key: the device's
BootROM/eFuse state is authoritative, and the supplied image must actually be
the image flashed on the target. But the SDK, Preloader source, and supplied
Preloader image are internally consistent with the tool-auth key.

## Inputs and generation path

Relevant SDK root:

```text
/home/kali/Desktop/x17m/zlt x17m dumps/RG500LEUACR04A06M8G_OCPU_30.202.30.202/T750
```

`mtk/tools/common/security/secure_chip_tools/toolauth.py` performs this exact
sequence:

1. Load the GFH INI into `gfh.ImageGFH`.
2. Call `ImageGFH.finalize(0, toolauth_key.ini)`.
3. Pack the GFH bytes as `tbs_toolauth.bin`.
4. Create a `cert.SigSingle` signer using the GFH pad type (`pss`).
5. Sign the packed GFH and concatenate GFH followed by the signature.

`quectel/common/security/1.generate_key.sh` invokes the same generator as:

```text
python2.7 toolauth.py \
  -i settings/toolauth/toolauth_key.ini \
  -g settings/toolauth/toolauth_gfh_config_pss.ini \
  out/toolauth/customer_da.auth
```

`usage/toolauth_usage.txt` documents the equivalent output name
`out/toolauth/auth_sv5.auth`.

An offline run completed successfully and produced a 2,256-byte artifact. The
signature is randomized, so its whole-file SHA-256 changes on each run.
One run used for layout verification had:

```text
customer_da.auth SHA-256 = 31b3093ca4081d674c0dde23a55c528efccb83659e748cdea357e6cdb11d961c
tbs_toolauth.bin SHA-256 = b124bcd41c928e982711417b3a6db599eb41445ee0005e14d2d42ffb63c40c2c
signature SHA-256       = 4f6199e598559fd7499bfc0a04bcc4d870afe4df7861e1a03ca367581b36ab39
```

## Exact GFH layout

All integer fields below are little-endian. The GFH header is:

```c
struct gfh_header {
    uint32_t magic_version; /* 0x014d4d4d: version 1, magic "MMM" */
    uint16_t size;
    uint16_t type;
};
```

### GFH_FILE_INFO, offset `0x000`, size `0x38`

The generated PSS artifact has:

| Offset | Size | Value | Meaning |
|---:|---:|---|---|
| `0x00` | 4 | `0x014d4d4d` | GFH version/magic |
| `0x04` | 2 | `0x0038` | structure size |
| `0x06` | 2 | `0x0000` | `GFH_FILE_INFO` |
| `0x08` | 12 | `FILE_INFO\0\0\0` | identifier |
| `0x14` | 4 | `1` | file version |
| `0x18` | 2 | `5` | file type |
| `0x1a` | 1 | `5` | `emmc` storage code from the INI |
| `0x1b` | 1 | `2` | `SINGLE` signature code |
| `0x1c` | 4 | `0x00200830` | computed load address |
| `0x20` | 4 | `0x000008d0` | complete file length, 2,256 |
| `0x24` | 4 | `0x00040000` | maximum size |
| `0x28` | 4 | `0x000007d0` | content/signature offset |
| `0x2c` | 4 | `0x00000100` | signature length |
| `0x30` | 4 | `0` | jump offset |
| `0x34` | 4 | `0xc2606000` | combined PSS attribute bits |

The apparent `emmc` value is literal: `toolauth_gfh_config_pss.ini` says
`flash_dev = "emmc"`, even though this router uses NAND. The generator does not
silently change it.

### GFH_TOOL_AUTH, offset `0x38`, size `0x798`

The second GFH has type `5` and is packed as:

```c
/* after the 8-byte gfh_header */
struct gfh_tool_auth_body {
    char     customer_name[32];  /* "MTK", NUL padded */
    uint32_t attr;                /* 0xc2606000 */
    uint32_t brom_verified_num;  /* 0 */
    uint32_t da_hash_num;        /* 0 */
    uint8_t  reserved[320];      /* zero in this artifact */
    struct ct_ce_key sbc_key;    /* absolute 0x1ac..0x3b7 */
    struct ct_ce_key sla_key;    /* absolute 0x3b8..0x5c3 */
    struct ct_ce_key daa_key;    /* absolute 0x5c4..0x7cf */
};
```

The absolute offsets are:

| Offset | Size | Value |
|---:|---:|---|
| `0x38` | 4 | `0x014d4d4d` |
| `0x3c` | 2 | `0x0798` |
| `0x3e` | 2 | `0x0005` (`GFH_TOOL_AUTH`) |
| `0x40` | 32 | `MTK` plus NUL padding |
| `0x60` | 4 | `0xc2606000` |
| `0x64` | 4 | `0` |
| `0x68` | 4 | `0` |
| `0x6c` | 320 | zero padding |
| `0x1ac` | 524 | SBC/root public key |
| `0x3b8` | 524 | SLA public key |
| `0x5c4` | 524 | DAA public key |

Each `ct_ce_key` is exactly:

```c
struct ct_ce_key {
    uint32_t exponent_length; /* 3 */
    uint32_t modulus_length;  /* 256 */
    uint32_t reserved;        /* 0 */
    uint8_t  exponent[256];   /* little-endian, 01 00 01 then zeroes */
    uint8_t  modulus[256];    /* little-endian modulus */
};
```

The three public-key blocks therefore occupy `3 * 524 = 0x624` bytes. The GFH
size is `0x38 + 0x798 = 0x7d0`.

### Signature, offset `0x7d0`, size `0x100`

The final 256 bytes are the raw RSA signature produced by `SigSingle.pack()`.
There is no certificate wrapper, trailer, terminator, or additional length
field after it.

The direct private-key path in `hsm_hook.pyc` does:

```text
openssl dgst -sha256 -binary       -> tbs_toolauth.bin.sha256
openssl pkeyutl -sign
    -pkeyopt digest:sha256
    -pkeyopt rsa_padding_mode:pss
    -pkeyopt rsa_pss_saltlen:32
```

Thus the implementation hashes the 0x7d0-byte GFH once to a 32-byte input and
`pkeyutl` applies SHA-256 again before RSA-PSS. Offline verification of the
generated artifact succeeds when the verifier is given the first SHA-256 digest
as the input to `pkeyutl` with `digest:sha256`; this confirms the effective
double-SHA-256/PSS-32 behavior of this SDK implementation.

If an HSM public key is supplied instead of a private PEM, the code delegates
to `hsm.py`; the checked-in test HSM maps public keys back to its local test
private keys. The generated artifact here used the private PEM path.

## Which keys are used

`toolauth_key.ini` names `rootkey`, `imgkey`, and `ac_key`. In this generator,
`imgkey` is not used by the tool-auth signing path; `SigSingle.parse_ini()` only
consumes `rootkey`. The referenced `keys/toolauth/img_prvk.pem` is absent from
the extracted `keys/toolauth` directory. The GFH tool-auth INI directly names
`sla_prvk.pem` and `da_prvk.pem`.

Therefore the generated object contains:

* SBC/root block: `root_prvk.pem` public key;
* SLA block: `sla_prvk.pem` public key;
* DAA block: `da_prvk.pem` public key;
* outer signature: `root_prvk.pem` private key.

`root_prvk.pem` and `da_prvk.pem` are byte-distinct PEM files but contain the
same RSA modulus and exponent. `epp_prvk.pem` is present in the directory but is
not referenced by this tool-auth PSS configuration.

### Public-key fingerprints

All keys are RSA-2048 with exponent `65537` (`0x010001`). `mod_be` is the
usual 256-byte big-endian integer; `mod_le` is the exact little-endian byte
order used in each GFH `ct_ce_key`. `ctce_sha256` is SHA-256 of the complete
524-byte packed key block. The DER fingerprints are included to avoid ambiguity
about key serialization.

| Logical key | SDK PEM(s) | SHA-256 `mod_be` | SHA-256 `mod_le` | SHA-256 packed CT-CE | SHA-256 SPKI DER | SHA-256 PKCS#1 DER |
|---|---|---|---|---|---|---|
| root / DAA | `toolauth/root_prvk.pem`, `toolauth/da_prvk.pem`, `resignda/da_prvk.pem`, `pbp/root_prvk.pem`, `hsm_test_keys/root_prvk.pem` | `9af8a28bf1096b58751ab5ef5f696c5df3050124bb9fec51bd9bf190d04c618f` | `90ca058019b26129f3af845b750235c063d36d89e76a2f742686e4cd34609fb4` | `ece9eb1cc9425823dc3a0d23a345d8e04eac4313931eb09527f8960e05ad1063` | `edf343d880317d38c6cd9ba2ab77505156045024cd6cfdb0a7addda997bebe68` | `64b6430136cd4afcee97bab6f1bd7cf3231692986447422257e6d73d149a0ae1` |
| SLA | `toolauth/sla_prvk.pem` | `1a89bd533b633a5b6e5c8ad908790f2dce3284f70525a7570a1101870096176b` | `8a2f1e980f7dff1c9d5529197e95d59e4df78aef4796a71b63a55bba16cafbe1` | `320fa97aa22e4ead752aea8c18bfdcef3251812670a2c92a95a4939c776d8cb5` | `73ef77c5ff7442e48376cdda31ac81c326b26f5d29e8fc79f06b047d3c567d4a` | `db82ef71f2a5e32bbf124bf9512d8f2195d7f70e3a4d10c887bdfd75f28c5fa6` |
| EPP / image | `toolauth/epp_prvk.pem`, `resignda/epp_prvk.pem`, `pbp/img_prvk.pem`, `hsm_test_keys/img_prvk.pem` | `952a0d4b2ce11a057b3da1ba63105da1e4b5e52efab0cb16557ed267370e9506` | `56c92c243278cc0474ff5ec50f17e8fefbd649b9bffeca4c65b4d755468807a9` | `d2dc374268df9a519b50b060b76926d2c1f24601d26ab42011bd643666773178` | `051e3c5a1d927b9c756a339e62ed04124d9e3f54246c66fb3202ecffeae26a87` | `b940751ec08d4e15cfc505341f6e64e3f243eef8f4fb368468096e404b42d925` |

For reference, the root/DA modulus in conventional big-endian hex is:

```text
9bb734774443d77557a76e24b10733787750d90d09c869cd606d54f28978ea6220dc9948b3c9e89284f8551d6166f3754b6a3b890ac9cda9e37dfaa0c1317e351ce5107c4273795949c6cce638314ab1a345385d7642cb8d055a1f410c7d7e24a6f0a2aab8184e773d21b3754a947541680f2c1a8d6ba5befd3b6e1fc28ec0b61d55b1454383f2c3e8bd27170a25978608f6788b90a2fc34f0ce35056bf7520795c8c60232cbbc0b0399367af937869ca45cf737a8a066127893e93166c433298dd6fd009e6790e743b3392aca8ea99f61dfc77bd99416dda4b8a9d7e4da24217427f3584119a4932016f1735cc63b12650fddda73c8fcfbc79e058f36219d3d
```

The exponent is `010001` (65537). The exact SLA and EPP moduli are preserved
by the fingerprints above and by the packed generated artifact. Their complete
big-endian public moduli are:

```text
SLA:
c43469a95b143cdc63ce318fe32bad35b9554a136244fa74d13947425a32949ee6dc808cdebf4121687a570b83c51e657303c925ec280b420c757e5a63ad3ec6980aad5b6ca6d1bbdc50db793d2fddc0d0361c06163cff9757c07f96559a2186322f7abf1ffc7765f396673a48a4e8e3296427bc5510d0f97f54e5ca1bd7a93ade3f6a625056426bdfe77b3b502c68a18f08b470da23b0a2fae13b8d4db3746255371f43306582c74794d1491e97fde504f0b1ecac9ddef282d674b817b7ffa8522672cf6281790910378febfa7dc6c2b0af9da03a58509d60aa1ad6f9bfdc84537cd0959b8735fe0bb9b471104b458a38df846366926993097222f90628528f

EPP/image:
e6b4fcfd7a5aac156c97f0146cc12bec3e95a46ca37564d0870081d33c4ca245b3a8205292d0b75876e4d1b18330e7ea7b0ae0c76e85409f1ed66c031a93820ea9f4f19e4ff0ac3080410594110077e44a279bd8289bfbe1b567ddad050642a1f4424d677b8d567e48d9d2ba8e634f4f859c266ddbe6f89e49c36de8118f6d6130d8eb430eefb3ffa0084d575dc780eddfb5b3adf25f9327237f56a1e10938c8379b63a6be3ee9e9de60a58e0b23e034066a7b3b89c6baf0f221c2bb76bc8f3378ed6db001acc462a62477aa7da4e8a071aaad4433d4b910773cba4a1770f7e85981a014e79a8cb8803d65592da988e11a064db764e52b1238083a50020d525f
```

No private-key material is reproduced in this report.

## Preloader and eFuse trust-material search

### Embedded OEM key: positive match

The NAND Preloader source contains:

```text
mtk/package/boot/preloader/custom/evb6890v1_64_cpe_nand/inc/oemkey.h
```

Its `OEM_PUBK` bytes are exactly the root/DA modulus above. The corresponding
MT6890 source calls `seclib_set_oemkey(g_oemkey, OEM_PUBK_SZ)` from
`platform/mt6890/src/security/cust_init.c`, and the security code includes
`oemkey.h`.

The supplied firmware Preloader:

```text
.../RG500LEUACR04A06M8G_OCPU_30.202.30.202/preloader_evb6890v1_64_cpe_nand.bin
```

has SHA-256:

```text
e2ae79dd585c0ac7e19324fe8182e2d4a374452c1c9f5ed446e1b9e0ba4fae06
```

and contains the exact 256-byte OEM modulus at file offset `0x39ae0`; the
extracted modulus SHA-256 is `9af8a28bf1096b58751ab5ef5f696c5df3050124bb9fec51bd9bf190d04c618f`.

This is an embedded trust-material match, not merely a matching configuration
filename.

### DA public key is separate

`inc/dakey.h` contains a different 256-byte `DA_PUBK` (modulus SHA-256
`a697414d00aeb51df58c60b0b9f9e3129898ab10cca064067f3b41d2dc7b2657`). It is
used by `platform/mt6890/src/security/auth/sec_auth.c` via
`seclib_set_pubk(g_dakey, DA_PUBK_SZ)` for DA-image signature checking. It is
not the `OEM_PUBK`/tool-auth root modulus. The exact supplied Preloader image did
not contain this source `DA_PUBK` as a contiguous byte string, so the compiled
image may use another representation, another build variant, or protected
material.

### eFuse configuration

The checked-in NAND `security/efuse/input.xml` is a template with:

```text
Enable_DAA="false"
Enable_SBC="false"
<pub-key-e></pub-key-e>
<pub-key-n></pub-key-n>
sbc_pubk_hash_lock="false"
```

That template is intentionally mutable. `1.generate_key.sh` changes
`Enable_DAA` to true while producing the full-function eFuse image and creates
key-only/full-function variants. Therefore the template alone is not the
production fuse state. The Preloader's compiled `OEM_PUBK` is the stronger
available source-side indication.

The SDK contains no literal root/DA modulus or public-key hash in the eFuse XML
because the key fields are generated/populated during provisioning. No source
artifact exposes the device's actual fused hash. The key match in the supplied
Preloader is strong evidence for that firmware build, but only a device eFuse
read or a successful BootROM authorization would prove the live unit's state.

## `SEND_AUTH` behavior in mtkclient

`mtkclient/Library/mtk_preloader.py` defines `SEND_AUTH = b"\\xe2"` and its
`send_auth()` implementation does the following:

1. Calls `prepare_data(auth, sigdata=b"", maxsize=len(auth))`.
2. Sends command `0xe2` and a 32-bit big-endian byte length.
3. Requires BootROM to echo the same length.
4. Sends the bytes in endpoint-sized chunks, followed by a zero-length USB
   packet and a short delay.
5. Reads a checksum word and then a final status word.

For the generated 2,256-byte artifact, `prepare_data` performs no mutation:
the length is even, `sigdata` is empty, and the complete GFH+signature object is
sent unchanged. The helper computes an XOR16 upload checksum for comparison but
does not rewrite the auth bytes.

The success condition is a final status in `0x00..0xff`. `0x1d0c` is reported
as `NO_AUTH_NEEDED`. Relevant failure statuses include:

```text
0x1771  SLA_WRONG_AUTH_FILE
0x1772  SLA_INVALID_AUTH_FILE
0x178d  SEND_AUTH_FAIL
0x6000  SBC_KEY_NOT_FOUND
0x6004  ERR_PSS_CHK_FAIL
0x6005  ERR_SIG_CHK_FAIL
0x7015  DAA_Security_Error_Signature
0x7017  DAA_Security_Error
0x7024  DAA_SIG_VERIFY_FAILED
```

The prior X17M authentication-only experiment reached `0x7017` after transfer,
which means the BootROM rejected authorization before DA execution; it does not
identify whether the cause was the wrong key, wrong certificate fields, or
another DAA policy mismatch.

## Final determination

The SDK provides enough information to reconstruct and sign the exact tool-auth
container, and the supplied MT6890 NAND Preloader contains the same OEM public
modulus as the SDK's root/DA key. This establishes a source/preloader trust
chain for the supplied firmware family.

It still cannot establish, offline, that a particular production router has the
same fused key hash. The decisive trust anchor is the BootROM/eFuse state. The
safe conclusion is therefore:

```text
SDK generator:                 YES, fully reconstructable
Binary layout/signature:       YES, verified offline
Preloader OEM key match:       YES, exact modulus match
Device fuse match:             NOT provable from files alone
SEND_AUTH transformation:     none for this even-length artifact
Device contacted in analysis:  NO
```

## Comparison with the exact September working-router Preloader dump

The requested file was found at:

```text
/home/kali/Desktop/bozax17/backups/x17m-1gb-20260921-061524/logical/mtd00_preloader.img
```

Its size and SHA-256 were independently verified:

```text
size   = 4,194,304 bytes
SHA256 = 5152173ee3f604dcd65edaa199812703f97acd391cb7a0d9c27ab9a5568567f5
```

### Key search result

The complete 4-MiB logical dump was searched for each of the following for the
root/DA, SLA, and EPP keys:

* 256-byte big-endian modulus;
* 256-byte little-endian modulus;
* common 32-bit/word-reversed modulus encodings;
* SHA-256 of the big- and little-endian modulus;
* complete 524-byte packed CT-CE key (`<III` plus 256-byte exponent and
  256-byte modulus);
* SHA-256 of that packed CT-CE representation.

Every search returned zero matches. In particular, the root/DA modulus
fingerprints from this report (`9af8…09fb4`, `90ca…09fb4`, and
`ece9…1063`) are absent from the exact working-router dump.

This is different from the supplied 2023 NAND Preloader image, which contains
the SDK OEM modulus at offset `0x39ae0`. The older archive Preloader therefore
matches the SDK key; the exact September working-router dump does not expose
that key as a contiguous or straightforward transformed value.

### Security structures present in the working dump

At offset `0x40000`, the working dump begins a GFH chain:

| Offset | GFH type | Size | Interpretation |
|---:|---:|---:|---|
| `0x40000` | `0` | `0x38` | `GFH_FILE_INFO` |
| `0x40038` | `1` | `0x0c` | `GFH_BL_INFO` |
| `0x40044` | `7` | `0xcc` | anti-clone/security material |
| `0x40110` | `2` | `0x14` | `GFH_BL_SEC_KEY` |
| `0x40124` | `8` | `0x30` | `GFH_BROM_SEC_CFG` |

The first file-info record decodes as:

```text
file_type       = 1
flash_dev       = 5 (emmc code in this GFH implementation)
sig_type        = 5 (CERT_CHAIN)
load_addr       = 0x00200ea0
file_len        = 0x0003ed4c
max_size        = 0x00080000
content_offset  = 0x00000160
sig_len         = 0x0000066c
jump_offset     = 0x00000160
attr            = 0xc2606001
```

The dump also contains these useful strings near its compiled code:

```text
platform/mt6890/src/security/...
platform/mt6890/src/core/...
img_auth_required=%x
seclib_brom_meta_mode
BR META BOOT
```

It also contains `MT6752` inside an older `AND_ROMINFO`-style metadata record.
That string is not sufficient to reclassify the compiled image; the source-path
and MT6890 boot/security strings show that this is an MT6890-family Preloader
build with legacy metadata embedded.

### Provenance conclusion

The new comparison weakens the claim that the SDK root key can be assumed to be
the key used by the known-good router. The strongest defensible chain is now:

```text
SDK tool-auth private key
    ↓ exact modulus match
2023 supplied NAND Preloader OEM_PUBK
    ↓ no match found in the exact September working-router dump
2025/September working-router Preloader trust material
    = not identified from this dump
```

There are several possible explanations for the negative result—different
production key, key material held only in protected/eFuse state, a different
security build, or a compiled/encoded representation not covered by the tested
forms. The dump alone does not distinguish them. It does establish that the
working router's Preloader contains a valid signed/security GFH chain, but it
does not provide the OEM modulus needed to prove that the SDK-generated auth
object is accepted by that unit.

## Live Linux devinfo/eFuse capture (2026-09-22)

The working router exposes a read-only MediaTek devinfo NVMEM device:

```text
/sys/bus/nvmem/devices/mtk-devinfo0/nvmem
size   = 800 bytes (0x320)
sha256 = 9cd7f9a458842e20a7565b6b2f96d437b6688e0ead2656ee3e744d6ff36c47a7
```

The bootloader also exports an `atag,devinfo` copy:

```text
/sys/firmware/devicetree/base/chosen/atag,devinfo
size   = 804 bytes
sha256 = a06fe7bc3bf25ae1c580bc1971391a637f1dc2a369f57da22f743447854f89d0
```

Byte-for-byte comparison establishes the exact relationship: `atag,devinfo`
is a four-byte little-endian `0x000000c8` header followed by the complete
800-byte NVMEM payload. Thus `atag-devinfo.bin[4:]` equals
`mtk-devinfo0.nvmem.bin` exactly. The raw files should still be preserved;
`od -tx4` reverses the byte order within each displayed 32-bit word.

### Confirmed values

The NVMEM dump visibly contains identifiers associated with the target:

```text
word 20          0x00000992 (the source does not name this index; the platform
                 `chip_info.xml` independently declares hardware code `0x0992`)
hardware version  0xca01
```

It also contains several opaque 32-byte regions. Those regions are not
identified as an SBC public-key hash from the current word-oriented dump, and
no write was performed. The read-only sysfs permissions and the successful
800-byte read demonstrate access to the Linux devinfo exposure, not access to
the BootROM trust anchor.

### Why this is not yet the fused SBC key

The SDK's `MT6890/efuse/efuse_definition.xml` describes a generated eFuse
writer image, not the Linux `mtk-devinfo0` register dump. In that writer format:

* `SBC_PUBK_HASH` is 64 bytes (512 bits), represented in eight-byte chunks at
  writer offsets `0x44` through `0x83`;
* the security-control word is at writer offset `0x7c` (SBC, DAA, SLA and
  related bits);
* the security-lock word is at writer offset `0x8c`.

The live NVMEM object is 800 bytes and its visible word layout does not match
that writer-image layout. Treating NVMEM offset `0x7c` as the XML security
control offset would produce values inconsistent with the already observed
BootROM state (`DAA enabled`), so that direct mapping is invalid. A driver or
device-tree-specific translation is required before any 64-byte key hash can be
identified.

### Current trust conclusion

This capture confirms a useful, read-only path for collecting device security
metadata, but it neither proves nor disproves that the SDK tool-auth key is the
production key fused into this router. The exact September Preloader dump still
contains no match for the SDK modulus in the tested encodings, and the Linux
devinfo dump has not yet yielded a labeled 64-byte `SBC_PUBK_HASH`.

The next safe step is byte-oriented capture and device-tree metadata inspection
only (no writes):

```sh
od -Ax -tx1 -v /tmp/efuse-readonly/mtk-devinfo0.nvmem.bin
od -Ax -tx1 -v /tmp/efuse-readonly/atag-devinfo.bin

for d in /sys/firmware/devicetree/base/efuse@11ec0000 \
         /sys/firmware/devicetree/base/efuse@11ec0000/*; do
    [ -d "$d" ] || continue
    echo "=== $d ==="
    find "$d" -maxdepth 1 -type f -print
    for f in "$d"/*; do
        [ -f "$f" ] || continue
        printf '%s: ' "$f"
        od -Ax -tx1 -v "$f"
    done
done
```

These commands establish the NVMEM/device-tree field mapping without any write
or device-modifying operation.

## Exact ATAG/NVMEM and MT6890 source mapping

The SDK includes the relevant source, which resolves the wrapper exactly:

* `lk/platform/mediatek/common/devinfo/efuse.c:118-153` defines
  `ptr[0] = ATAG_DEVINFO_DATA_SIZE` and copies
  `get_devinfo_with_index(i)` into `ptr[1+i]`.
* `lk/platform/mediatek/mt6890/devinfo/include/platform/sec_devinfo.h:57`
  sets `ATAG_DEVINFO_DATA_SIZE` to `200`.
* `drivers/nvmem/mtk-devinfo.c:43-78` reads the `data_size` header, copies
  `tags->data`, and exposes it as a read-only 32-bit-stride NVMEM provider.

Therefore:

```text
atag-devinfo.bin[0:4]   = little-endian 200 (0x000000c8)
atag-devinfo.bin[4:]    = 200 little-endian 32-bit words
nvmem offset 4*n        = word n
```

This is an ATAG snapshot of the values returned by the MT6890 `get_devinfo`
API. It is not a raw dump of a contiguous 0x320-byte eFuse address range.

### FACTS

The exact MT6890 source exposes the following security reads in the preloader
`platform/mt6890/lib/libdevinfo.a` object `efuse.o`:

```text
seclib_sbc_enabled():  read MMIO 0x11ec0060, extract bit 1
seclib_daa_enabled():  read MMIO 0x11ec0060, extract bit 2
seclib_sla_enabled():  read MMIO 0x11ec0060, extract bit 3
```

The disassembly is an exact source-independent record of the compiled MT6890
implementation (`ubfx #1`, `ubfx #2`, and `ubfx #3`). The source tree does not
provide a C field-name table that maps all 200 ATAG words to these MMIO
registers. `internal_seclib_get_devinfo_with_index()` is limited to indices
`0..0x34` and uses an internal address table; the remaining ATAG words are
still exported, but their semantic names are not present in the supplied
source.

The exact address table recovered from `efuse.o` includes:

```text
index 0..7   -> 0x11ec0020, 0x11ec0038, 0x11ec0030, 0x11ec0040,
               0x11ec0044, 0x11ec0048, 0x11ec004c, 0x11ec0050
index 8..9   -> 0x11ec0800, 0x11ec0800
index 13..16 -> 0x11ec0140, 0x11ec0144, 0x11ec0148, 0x11ec014c
index 17..28 -> 0x11ec07a0 through 0x11ec07cc (step 4)
index 31     -> 0x11ec0060
index 32     -> 0x11ec0130
index 34     -> 0x11ec0120
index 35..36 -> 0x11ec0260, 0x11ec0264
index 37..38 -> 0x11ec0268, 0x11ec0664
index 39     -> 0x11ec0668
index 52     -> 0x11ec0580
```

The captured API word at index 31 (NVMEM offset `0x7c`) is `0x00000000`.
Because the compiled address table maps index 31 to `0x11ec0060`, this
particular Linux snapshot reports all three extracted bits as zero:

```text
SBC bit 1 = 0
DAA bit 2 = 0
SLA bit 3 = 0
```

That is a result for this working-router Linux/ATAG snapshot only. It conflicts
with the separate BROM/Preloader target-configuration report from the
bootlooped-router probe (`SBC enabled`, `DAA enabled`), so those reports cannot
be silently merged; they may refer to different units, stages, or security
register snapshots.

There are special cases: index `29` conditionally selects an address based on
bits `0xc0000000` of `0x11ec07a0`, index `30` returns the low byte of
`0x11ec0050`, and index `10` is a constant. Consequently, the number `0x992`
in captured word 20 must not be called a security flag or trust hash. The
firmware's `chip_info.xml` independently identifies `0x0992` as the MT6890
hardware code, but the supplied source does not prove that word 20 is that
field. The LK model code uses index 7 for segment and index 29 for project
code; the devinfo API is primarily informational silicon/device data.

The two highlighted regions are exactly:

```text
NVMEM offsets 0x140..0x15f = words 80..87
NVMEM offsets 0x300..0x31f = words 192..199
```

The supplied MT6890 source assigns no public symbol, SBC field, DAA field, or
key-hash name to either range. They must remain classified as opaque devinfo
fields, not security hashes.

### Key-hash comparison

The SDK provisioning path is precise about the *writer image*:

* `efuse_definition.xml:179-202` places the 64 hexadecimal characters from
  `SBC_PUBK_HASH` at writer offsets `0x44..0x60`, in eight 4-byte output words;
* `efuse_bingen_v2.py:520-552` reads exactly 64 hex characters from
  `keyhash.txt`, uppercases them, validates hexadecimal syntax, and passes the
  string as external data;
* the generated writer image is 512 bytes, while Linux exports 200 API words.

The source therefore establishes the expected hash as the 32-byte binary
value represented by the key-hash text, with writer-image byte ordering defined
by the generator's `reverseEndian()` handling. It does **not** establish that
the Linux ATAG word array is that writer image or that any particular ATAG
range is `SBC_PUBK_HASH`.

Comparing the SDK modulus hash
`9af8a28bf1096b58751ab5ef5f696c5df3050124bb9fec51bd9bf190d04c618f` against
the captured words in raw-byte, per-word-little-endian, and reversed-word forms
does not produce a source-established match. The two 32-byte ranges at 0x140
and 0x300 are not matches under those transformations.

### INFERENCES

The BootROM/Preloader security state is read from the dedicated MMIO security
register at `0x11ec0060`, not from a documented Linux-readable “key record.”
The DAA/SBC trust anchor is therefore likely consumed internally by the
security implementation or BootROM, while Linux devinfo exposes only selected
device-information words.

The fact that the 200-word ATAG snapshot contains no labeled key-hash field is
consistent with the trust anchor being protected eFuse/BootROM state, but this
is an inference—not proof that the hash is physically absent from all readable
registers.

### UNRESOLVED QUESTIONS

1. The supplied tree contains the MT6890 API and compiled devinfo library, but
   not the proprietary implementation that names every `E_AREA` and maps all
   200 exported words. Exact semantic names for words 0..199 therefore remain
   unavailable from this SDK.
2. We cannot equate MMIO `0x11ec0060` with NVMEM word 31 merely from the
   address-table entry: the ATAG values are an API snapshot and may apply
   transformations or alternate register sources.
3. The actual production `SBC_PUBK_HASH` expected by BootROM remains
   unconfirmed. The SDK writer hash and the live Linux devinfo snapshot are
   different representations until a vendor mapping or a matching Preloader
   implementation proves otherwise.
