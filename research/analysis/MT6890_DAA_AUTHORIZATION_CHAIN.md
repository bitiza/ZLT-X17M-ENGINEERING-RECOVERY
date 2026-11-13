# MT6890 DAA authorization chain

## Scope

This is separate from PBP/Preloader image authentication. It covers BootROM `SEND_AUTH` (`0xe2`), `customer_da.auth`, and Download Agent authorization.

## SDK-defined chain

The SDK flow is `quectel/common/security/1.generate_key.sh` followed by `3.CopyAndresign.sh`.

`toolauth.py` creates a GFH containing `GFH_TOOL_AUTH`, then appends one RSA-PSS signature over that GFH. `toolauth_gfh_config_pss.ini` embeds the SLA public key and DAA public key, while `toolauth_key.ini` names the root signer.

```text
BootROM trust anchor / fused OEM authorization
                    ↓ authenticates
tool-auth root public key
                    ↓ verifies customer_da.auth
GFH_TOOL_AUTH: authorized DAA public key + SLA public key
                    ↓ authorizes
DA_BR signatures made with the DAA private key
```

The exact BootROM implementation is not in the SDK, so “trust anchor” means the public-key hash/key slot against which BootROM validates the tool-auth root. It is not the Preloader PBP root key.

The relevant configuration is:

```text
toolauth_key.ini:
  rootkey = keys/toolauth/root_prvk.pem
  imgkey  = keys/toolauth/img_prvk.pem

toolauth_gfh_config_pss.ini:
  sig_type = SINGLE
  pad_type = pss
  sla_public_key = keys/toolauth/sla_prvk.pem
  sla_pad_type = pkcs1
  daa_public_key = keys/toolauth/da_prvk.pem
  daa_pad_type = pss
```

## Key identities in the shipped `quectel` tree

Hashes below are SHA-256 over the 256-byte big-endian RSA modulus.

| role | file | modulus SHA-256 |
|---|---|---|
| tool-auth root signer | `keys/toolauth/root_prvk.pem` | `a13aa886f512c56bd3b87730f9f80fd1482005963d3cd4e8a23e4a0400f8ee06` |
| embedded DAA key | `keys/toolauth/da_prvk.pem` | `59c617688a2f49eb2a40a71f03249fb341fb47a070d8a9b5c55d08f1cb9c6408` |
| embedded SLA key | `keys/toolauth/sla_prvk.pem` | `1a89bd533b633a5b6e5c8ad908790f2dce3284f70525a7570a1101870096176b` |
| DA signing key | `keys/resignda/da_prvk.pem` | `59c617688a2f49eb2a40a71f03249fb341fb47a070d8a9b5c55d08f1cb9c6408` |
| EPP signing key | `keys/resignda/epp_prvk.pem` | `59c617688a2f49eb2a40a71f03249fb341fb47a070d8a9b5c55d08f1cb9c6408` |

The critical equality is `toolauth/da_prvk.pem == resignda/da_prvk.pem`.

## DA signing and upload

`3.CopyAndresign.sh` copies `customer_da.auth`, moves the original DA to `DA_BR_unsign.bin`, and invokes `resign_da.py ... MT6890 ... bbchips_pss.ini`. For MT6890 the configuration declares PSS signatures for DA load regions and uses `keys/resignda/da_prvk.pem`.

The examined signed/unsigned DA pair differs in two 256-byte signature regions, confirming that signatures are inserted into the DA rather than transported separately.

`dakey.h` is the Preloader-side compiled DA public-key header. `1.generate_key.sh` regenerates it from `da_pubk.der` and copies the same generated DA private key into both `toolauth` and `resignda`. Thus a freshly generated customer build makes `dakey.h`, the embedded DAA key, and the DA signing key identical. The checked-in `quectel` `dakey.h` currently hashes to `a697414d00aeb51df58c60b0b9f9e3129898ab10cca064067f3b41d2dc7b2657`, not the shipped `toolauth/da_prvk.pem` hash; this indicates stale/default material in the repository snapshot.

## mtkclient behavior

`mtk_preloader.py::send_auth()` sends command `0xe2`, the byte length, and the authentication bytes unchanged. It does not parse or re-sign the GFH. It only computes a 16-bit upload checksum, sends an empty USB packet, and reads status.

`send_da()` separates the final `sig_len` bytes only to calculate the transport checksum; it uploads the complete DA payload and signatures unchanged.

Relevant status names include:

- `0x1775` `DAA_FAIL`
- `0x178d` `SEND_AUTH_FAIL`
- `0x1d15` `DA_SIG_LEN_IS_ZERO_AND_DAA_ACTIVE`
- `0x1d17` `DA_BLOCKS_INCONSISTENT_WITH_TOOL_AUTH`
- `0x2000` `AUTH_IMAGE_VERIFY_FAIL`
- `0x7015` `DAA_Security_Error_Signature`
- `0x7017` `DAA_Security_Error`
- `0x7024` `DAA_SIG_VERIFY_FAILED`

## Key-domain distinction

| domain | purpose |
|---|---|
| OEM/tool-auth root | signs `customer_da.auth`; BootROM trust-anchor domain |
| embedded tool-auth DAA key | authorized by `GFH_TOOL_AUTH`; verifies DA signatures |
| `dakey.h` | compiled Preloader DA verification key; should equal generated DAA key |
| DA_BR signing key | signs DA load regions; same key as embedded DAA key in generated flow |
| PBP/Preloader production root/image keys | authenticate Preloader image; independent of DAA |

## FACTS

- `customer_da.auth` is GFH plus one RSA-PSS signature, not a DA image.
- The DAA public key is embedded in the GFH and authorized by the tool-auth-root signature.
- The DA is separately signed with the DAA/resignda key.
- `send_auth()` and `send_da()` do not cryptographically transform their inputs.
- SDK generation intentionally copies one generated DA key into tool-auth, resignda, and `dakey.h`.

## INFERENCES

- A freshly generated `customer_da.auth` and freshly resigned `DA_BR.bin` are cryptographically coherent even when the device's PBP/Preloader keys differ.
- The 2025 production Preloader certificate mismatch does not itself invalidate DAA: BootROM DAA authorization is a separate earlier chain.
- Observed `0x7024` indicates a DA authorization/signature/package mismatch, not proof that the PBP certificate chain is wrong.

## UNRESOLVED QUESTIONS

- The exact fused MT6890 BootROM tool-auth root hash/key slot is not exposed by the SDK or Linux devinfo dump.
- The checked-in `dakey.h`/`toolauth/da_prvk.pem` mismatch must be resolved by identifying the generated-key set belonging to the tested DA package.
- Exact DA signed-byte ranges and PSS salt/hash parameters require the proprietary verifier or a successful BootROM acceptance; mtkclient only transports the bytes.
