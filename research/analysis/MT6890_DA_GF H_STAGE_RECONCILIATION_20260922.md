# MT6890 DA GFH/stage reconciliation

Input: the exact X17M `DA_BR.bin`, SHA-256 `c3d9058aeb56373eaadc5868ce93198fb99a9cbf876a30f876714e9007d66d56`.

## GFH descriptors

The descriptor table begins at file offset `0x60`. The relevant little-endian region records are:

| region | `m_buf` file offset | `m_len` | `m_start_addr` | signature offset | signature length |
|---:|---:|---:|---:|---:|---:|
| 1 | `0xBC` | `0x2F610` | `0x00200000` | `0x2F5CC` | `0x100` |
| 2 | `0x2F6CC` | `0x2DC10` | `0x40000000` | `0x5D1DC` | `0x100` |

The first two descriptor records are duplicates of region 1. Region 1 therefore consists of bytes `DA_BR[0xBC:0x2F6CC]`, including its final 256-byte signature. Its SHA-256 is `4c52749940cffb9bec14ab3fd226102198b5ea4b59a368d671a8ccc729b4fef2`.

## Why the previous upload failed

The runner initially used the generic mtkclient workspace address `0x00201000`. That is not the region-1 `m_start_addr`; the DA GFH says `0x00200000`. The stage bytes and signature boundary were correct, but the load address was off by `0x1000`. The resulting `0x7017` cannot be used to conclude that the RSA key was wrong.

The full 381,660-byte container was also incorrect as a single SEND_DA stage: it contains both regions and the outer GFH/container bytes, exceeding the region-1 descriptor length.

## Corrected no-jump test parameters

- Auth: verified 2256-byte object, SHA-256 `9fbcb7caf402119b0499200a3ca7b5629400f53cca7a69226911c235eeece37d`
- DA source: exact stock signed `DA_BR.bin`
- Stage: `DA_BR[0xBC:0x2F6CC]`
- Stage length: `0x2F610` (194064 bytes)
- Stage signature: final `0x100` bytes
- DA load address: `0x00200000`
- No `JUMP_DA`, reset, or storage command

The runner was corrected to use `0x00200000`. No new signing or image modification was performed.

## Remaining validation

The corrected upload was tested live with the descriptor address `0x00200000`; BootROM still returned `0x7017` after the auth `0x7009`. Therefore the earlier address error was not the sole cause. The stage bytes, descriptor boundaries, and offline RSA-PSS verification are correct as reconstructed, but the production authorization path still rejects the DA. Do not perform another live attempt until the auth/DA policy binding and BootROM-specific stage protocol are resolved.
