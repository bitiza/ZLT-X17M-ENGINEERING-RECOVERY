# MT6890 MTK DAA auth offline validation

## Generated artifact

Using the SDK's `mtk` key set and the supplied `toolauth.py` generator, a fresh artifact was generated read-only at:

`analysis/generated_auth_check_20260922/customer_da.auth`

SHA-256: `9fbcb7caf402119b0499200a3ca7b5629400f53cca7a69226911c235eeece37d`

Size: **2256 bytes**.

The artifact is 2000 bytes of GFH/tool-auth data followed by a 256-byte RSA signature. Its GFH begins with the expected MediaTek `MMM\x01` records, includes `FILE_INFO` and `GFH_TOOL_AUTH`, and reports MTK as the customer name.

## Embedded keys

The generated GFH contains:

| field | offset | modulus SHA-256 |
|---|---:|---|
| root/SBC key | `0x2b8` / data offset 696 | `9af8a28bf1096b58751ab5ef5f696c5df3050124bb9fec51bd9bf190d04c618f` |
| SLA key | data offset 1220 | `1a89bd533b633a5b6e5c8ad908790f2dce3284f70525a7570a1101870096176b` |
| DAA key | data offset 696 | `9af8a28bf1096b58751ab5ef5f696c5df3050124bb9fec51bd9bf190d04c618f` |

The root and DAA keys are intentionally the same modulus in this SDK key set.

## Signature validation

The final 256 bytes verify over the preceding 2000 bytes with:

```text
RSA-2048 PSS
hash = SHA-256
MGF1 = SHA-256
salt length = 32
signing modulus = 9af8a28b...
```

The same `9af8a28b...` modulus verifies both signatures in the exact X17M `DA_BR.bin`:

| DA region | signature offset | signed range | verification |
|---:|---:|---|---|
| 0/1 descriptor pair | `0x2f5cc` | `0xbc:0x2f5cc` | PASS, PSS-SHA256, salt 32 |
| 2 | `0x5d1dc` | `0x2f6cc:0x5d1dc` | PASS, PSS-SHA256, salt 32 |

Thus the offline relationship is:

```text
generated customer_da.auth
  ├─ root signature PASS with 9af8...
  ├─ embeds DAA key 9af8...
  └─ DAA key verifies both DA_BR regions
```

## Supplied example auth

`auth_sv5 (1).auth` is also 2256 bytes and has the same broad GFH layout, but its embedded key hashes are different:

- first/root/DAA-looking key block: `a13ed7b7f399882f00e71ed34e140af7956ea863c56d26b9bc99265737a1e19f`
- SLA block: `7f9f5f563b4e685e85088d589297b7cd7eefe4489fc46bad7a5e5d02d5b2b1df`

It is not the generated MTK auth for the X17M DA, and its originating device cannot be identified from the file alone.

## FACTS

- The generated auth passed structural validation and root RSA-PSS verification.
- Its embedded DAA modulus exactly matches the modulus that verifies both X17M DA signatures.
- No device was contacted and no DA was uploaded.

## INFERENCE

- The SDK `mtk` customer-auth/DA pair is cryptographically coherent offline.

## STILL UNKNOWN

- Whether the target MT6890 BootROM's fused trust anchor accepts the `9af8...` tool-auth root remains a live-device question. The offline artifacts cannot establish that fuse relationship.
