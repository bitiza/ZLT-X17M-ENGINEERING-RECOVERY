# MT6890 DA_BR signature-key audit

## Input

Exact X17M package examined read-only:

`RG500LEUACR04A06M8G_OCPU_30.202.30.202/download_agent/DA_BR.bin`

SHA-256: `c3d9058aeb56373eaadc5868ce93198fb99a9cbf876a30f876714e9007d66d56`

The matching unsigned copy is `DA_BR_unsign.bin`, SHA-256 `9133e91fd2dd4e5871a84d1709f2cac33a973025ca69f14f007a4a9f1223cfc1`.

## DA header and regions

The v6 DA descriptor begins at file offset `0x60`. Its region records identify two distinct 256-byte signatures:

| region | payload start | signature offset | signature length | signed bytes |
|---:|---:|---:|---:|---:|
| 0/1 descriptor pair | `0xbc` | `0x2f5cc` | `0x100` | `DA_BR[0xbc:0x2f5cc]` |
| 2 | `0x2f6cc` | `0x5d1dc` | `0x100` | `DA_BR[0x2f6cc:0x5d1dc]` |

The first two descriptor entries are identical; the actual distinct signature blocks are the two rows above. The signed DA contains nonzero 256-byte blocks at those offsets; the unsigned copy contains zero bytes at both locations.

## Offline verification

Every RSA public key discovered under the extracted SDK/firmware workspace was tested, including PEM private/public keys, DER public keys, all `dakey.h` arrays, tool-auth DAA keys, resignda keys, and DA-related public keys. Verification tried the SDK-declared RSA-PSS/SHA-256 form (MGF1-SHA256, salt length 32), plus PSS maximum/zero salt and SHA-1/MD5 fallbacks.

Both regions verify with the same modulus:

| DA SHA-256 | region | signature offset | verifying modulus SHA-256 | representative candidate | result |
|---|---:|---:|---|---|---|
| `c3d9058aeb56373eaadc5868ce93198fb99a9cbf876a30f876714e9007d66d56` | 0 | `0x2f5cc` | `9af8a28bf1096b58751ab5ef5f696c5df3050124bb9fec51bd9bf190d04c618f` | `mtk/.../secure_chip_tools/keys/resignda/da_prvk.pem` | **PASS, RSA-PSS SHA-256, salt=32** |
| same | 2 | `0x5d1dc` | same | same | **PASS, RSA-PSS SHA-256, salt=32** |

The same modulus also appears in the available `mtk` tree's `toolauth/da_prvk.pem`, `resignda/da_prvk.pem`, and the corresponding public/private copies. Since RSA verification depends on the modulus/exponent, all files containing that exact key are equivalent candidates. No `quectel` DAA key (`59c617...`) verified either region.

## Customer-auth relationship

No `customer_da.auth` or `auth_sv5.auth` file exists in the extracted workspace, so an embedded-auth blob could not be parsed or matched directly.

The exact DA signer is nevertheless established cryptographically as the modulus with SHA-256:

`9af8a28bf1096b58751ab5ef5f696c5df3050124bb9fec51bd9bf190d04c618f`

The matching SDK DAA private/public material is in the `mtk` tree's `secure_chip_tools/keys/toolauth/da_prvk.pem` and `keys/resignda/da_prvk.pem`. A customer auth generated from that same `mtk` key set would embed this exact DAA public key. The `quectel` tree's DAA key is different and cannot authorize this DA.

The root signer for such an `mtk`-tree customer auth is the corresponding `mtk/.../keys/toolauth/root_prvk.pem`, whose modulus hash is also `9af8...` in this SDK snapshot. However, because the actual auth file is absent, the root signature over a concrete customer-auth artifact was not independently verified.

## FACTS

- The package DA has two distinct 256-byte RSA-PSS signatures.
- Both signatures verify offline with the exact `9af8...` modulus, SHA-256, MGF1-SHA256, and 32-byte salt.
- No other candidate modulus verified either region.
- The available `quectel` DAA key does not verify this DA.
- No customer auth artifact is present to inspect directly.

## INFERENCES

- The intended DAA public key for this exact DA is the `9af8...` key, regardless of whether a file is labelled `root_prvk.pem` or `da_prvk.pem`.
- The matching customer auth must be generated from the `mtk` key set, not the `quectel` key set.
- The build scripts' intended relationship is confirmed for the DA signer, but the absent auth prevents direct proof of the auth file's root signature.

## STILL UNKNOWN

- The production BootROM fused trust anchor that authenticates the tool-auth root is not present in these files.
- The SDK does not provide the actual X17M customer auth artifact, so its embedded key and root signature cannot be directly inspected.
- This offline result does not prove that the `9af8...` SDK root is accepted by a particular device's BootROM fuses.
