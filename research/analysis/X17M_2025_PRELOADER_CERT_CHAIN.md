# Exact 2025 X17M Preloader certificate chain

## Scope and evidence

This note analyzes the exact working-router Preloader dump:

`backups/x17m-1gb-20260921-061524/logical/mtd00_preloader.img`

SHA-256: `5152173ee3f604dcd65edaa199812703f97acd391cb7a0d9c27ab9a5568567f5`.

The GFH file-info record at `0x40000` reports `sig_len = 0x66c`, `file_len = 0x3ed4c`, and certificate-chain signature type 5. Therefore the complete signature object is at file offset `0x7e6e0`, length `0x66c`. Its SHA-256 is `cc72bd8305ff3f9ca4d1b1eb027acb36d8d179cba63a98365a7d9f6c25e3a24d`.

## Confirmed binary layout

The first four bytes are a little-endian chain count/version:

```
02 00 00 00
```

Two proprietary MediaTek certificate records follow. They are not X.509 DER certificates; `openssl asn1parse` is therefore not a valid parser for this object.

| chain offset | size | interpretation |
|---:|---:|---|
| `0x000` | 4 | chain version/count = 2 |
| `0x004` | `0x52c` | key certificate |
| `0x530` | `0x13c` | content certificate |

The common certificate header is 28 bytes:

```
magic       0xe291f358
version     0x00010000
size        0x52c or 0x13c
type        0x00010100 (key) or 0x00020100 (content)
key_count   1
reserved    0, 0
```

The key certificate has two RSA-2048 public-key records. The exact key layout is corroborated by the SDK's `prebuilt/pbp/key_cert.bin` and `settings/pbp/pl_key.ini`, whose fields are `rootkey` then `imgkey`.

| key | chain-relative offset | size | exponent | SHA-256 of modulus bytes |
|---|---:|---:|---:|---|
| root key | `0x11c` | 256 | 65537 | `9c1eb2433f7a064b6b9a31d464a0c04802b5c66f1760c52f91ac246e100a79bb` |
| image/content key | `0x328` | 256 | 65537 | `f7599dad94554ebe0f0cb6b4a3697f4b9eace9c357b75c5303016c4fc69f5ec3` |

The first modulus begins at absolute signature offset `0x120`; the second begins at absolute offset `0x32c`. Both are raw big-endian RSA modulus encodings in the certificate record. No ECC key is present.

The content certificate begins at `0x530`. Its 20-byte digest field is at `0x54c`:

```
33 d4 98 f6 52 9d 73 33 25 57 fb ff 36 27 a2 c6 be e9 31 8d
```

The remainder is a proprietary content-signature record; it is not an X.509 issuer/subject structure. The certificate record does not encode human-readable issuer or subject names. The matching SDK configuration is `settings/pbp/pl_content.ini`, which names `keys/pbp/img_prvk.pem` as the content signer, while `settings/pbp/pl_key.ini` names the two key roles `rootkey` then `imgkey`. The exact Preloader GFH configuration also says `pad_type = "pss"`; therefore the intended RSA signature scheme is RSA-PSS (the digest/hash salt parameters are not encoded as an X.509 algorithm identifier in this blob).

## Independent rootfs certificate corroboration

Both logical `rootfs_sig_a` and `rootfs_sig_b` contain the exact first Preloader modulus byte-for-byte at offset `0x2d6` (inside their `cert1` public-key structure). They also contain the exact second Preloader modulus at offset `0x411`.

Thus the signed rootfs metadata and the 2025 Preloader use the same two production RSA public keys. This is a strong chain relationship, but it does not identify the external trust anchor that signed those keys.

## Comparisons

The SDK `prebuilt/pbp/key_cert.bin` has the same format and two modulus hashes:

| SDK field | SHA-256 |
|---|---|
| SDK `rootkey` modulus | `9af8a28bf1096b58751ab5ef5f696c5df3050124bb9fec51bd9bf190d04c618f` |
| SDK `imgkey` modulus | `952a0d4b2ce11a057b3da1ba63105da1e4b5e52efab0cb16557ed267370e9506` |

Neither SDK modulus equals either 2025 Preloader modulus. The same applies to the SDK tool-auth root/DA, SLA, and EPP/image keys (their hashes are documented in `MT6890_TOOLAUTH_BINARY_AND_TRUST_ANALYSIS.md`). The 2023 `OEM_PUBK`/`DA_PUBK` material likewise does not match these two 2025 production moduli.

The working-router Preloader therefore does **not** carry the SDK development certificate keys. It carries a production root/content-key pair that is reused by the rootfs signature metadata.

No matching modulus was found in the available `DA_BR.bin` variants. Those files contain their own Download Agent authentication material and are not the Preloader certificate chain.

## FACTS

- The exact 2025 chain is a proprietary two-record MediaTek CertChainV2 object, total `0x66c` bytes.
- It contains two RSA-2048 public moduli, exponent 65537, in rootkey/imgkey order.
- Both moduli are also present in both A/B rootfs signature partitions.
- Neither modulus matches the SDK root/DA, SDK SLA, SDK EPP/image, or 2023 OEM/DA public keys examined.
- No ECC public key, X.509 issuer, X.509 subject, or PEM certificate is embedded in this object.

## INFERENCES

- The first key is the production root key for this signed-image domain; the second is the production image/content key. The content certificate is intended to be signed with the image key, and the key certificate is intended to bind the image key below the root key. This follows the SDK field order and signing configuration, but the external root-of-trust certificate is not included in the Preloader blob.
- BootROM/Preloader authentication must trust a production key or key hash provisioned outside this certificate object (for example BootROM/eFuse state or an OEM signing service). The blob alone cannot prove which external key signed/authenticated it.
- The matching rootfs key pair shows that Preloader and rootfs verification are provisioned as one production signing domain, not that they descend from the SDK private keys.

## UNRESOLVED QUESTIONS

- The exact RSA padding/hash used by BootROM to authenticate the key certificate and by Preloader to authenticate the content certificate still requires the proprietary `cert.py` implementation or a successful cryptographic verification against the production root key.
- The external production root public key/hash and its certificate issuer are not present in the analyzed files; they may exist only in BootROM/eFuse or an OEM signing database.
- `DA_BR.bin` authorization is a separate BootROM Download-Agent chain; absence of a modulus match here does not by itself explain DAA authorization failures.
