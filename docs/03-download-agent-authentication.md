# Download Agent authentication

## SDK model

The MT6890 SDK describes a chain conceptually equivalent to:

```text
BootROM OEM/fused trust
          |
          v
tool-auth root
          |
          v
customer_da.auth
          |
          +-- authorized SLA key
          \-- authorized DAA key
                       |
                       v
                 signed DA_BR
```

`customer_da.auth` is an authorization object, not the Download Agent itself.

## Exact DA audit

Analyzed DA:

```text
DA_BR.bin
SHA-256
c3d9058aeb56373eaadc5868ce93198fb99a9cbf876a30f876714e9007d66d56
```

Two RSA-2048 signature regions were identified:

| Region | Signature offset | Signed range |
|---|---:|---|
| stage 1 | `0x2f5cc` | `0xbc:0x2f5cc` |
| stage 2 | `0x5d1dc` | `0x2f6cc:0x5d1dc` |

Both verify using RSA-PSS, SHA-256, MGF1-SHA256, salt length 32, with DAA public-key modulus fingerprint:

```text
9af8a28bf1096b58751ab5ef5f696c5df3050124bb9fec51bd9bf190d04c618f
```

## Generated authorization object

A fresh SDK-generated authorization artifact was independently checked:

```text
size: 2256 bytes
SHA-256:
9fbcb7caf402119b0499200a3ca7b5629400f53cca7a69226911c235eeece37d
```

It contained a 2000-byte GFH/tool-auth structure followed by a 256-byte RSA signature. The embedded DAA key matched the public key that verifies both exact DA signature regions.

This establishes **offline cryptographic coherence** between the generated authorization object and the analyzed DA.

## Live result

A constrained SEND_AUTH-only test completed the transport exchange but returned `0x7009`. A subsequent staged SEND_DA test, using the corrected exact descriptor/load region, still ended in `0x7017` before execution.

Therefore the investigation did not produce a working DAA bypass.

## FACTS

- The auth structure is valid offline.
- Its DAA key matches the exact DA signer.
- Both exact DA signatures verify offline.
- Production BootROM still does not execute the DA.

## INFERENCES

The unresolved boundary is no longer ordinary DA framing/address/signature mismatch. Production authorization or session policy remains the likely boundary.

## Publication note

Public-key fingerprints, offsets, protocol structures and verification results are sufficient to reproduce the analysis. Private SDK signing-key material is intentionally not published.
