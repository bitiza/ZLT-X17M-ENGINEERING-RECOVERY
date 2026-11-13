# MT6890 SEND_AUTH live result — 2026-09-22

## Test scope

The dedicated `send_auth_only.py` runner sent exactly one generated `customer_da.auth` object to the detected BootROM. It did not upload a DA, run a bypass, reset, read NAND, write NAND, erase NAND, or issue any storage command.

## Observed result

```text
auth_size=2256
auth_sha256=9fbcb7caf402119b0499200a3ca7b5629400f53cca7a69226911c235eeece37
handshake=PASS
send_auth_echo=PASS cmd=e2
echoed_length=0x000008d0
initial_status=0x0000
transport_checksum=0xfe50
final_status=0x7009
stopped_without_da_upload=PASS
```

## Facts

- `0x8d0` is 2256 bytes, so BootROM echoed the complete authentication-object length.
- `initial_status=0x0000` means the SEND_AUTH upload phase was accepted and the object was received.
- `final_status=0x7009` was returned after BootROM processed the object.
- The runner stopped immediately; no DA bytes or NAND operation followed.
- The transport checksum is not the RSA authorization result. It only covers the transferred payload according to the SEND_AUTH transport protocol.

## Interpretation

The production BootROM did not complete authorization from the auth object alone. This crosses the transport/protocol gate but does not establish a fused-root mismatch.

The local mtkclient status tables do not define `0x7009`. Based on the MTK DAA interpretation supplied for this platform, `0x7009` is a DA-hash/DA-association failure: SEND_AUTH was processed without a staged/associated DA payload whose expected hash could be checked. That interpretation fits this deliberately auth-only test. It is not evidence that the DA signature was checked, and it is not sufficient evidence of a production trust-anchor mismatch, because no DA was uploaded.

## Safety conclusion

No persistent state was changed. Do not proceed to DA upload or `printgpt` with this authorization result. Preserve the raw console output and generated auth hash.

## Next safe investigation

1. Stop repeated SEND_AUTH attempts on this unit.
2. Treat the next experiment as a paired transaction: send the verified auth, then upload the exact matching signed `DA_BR.bin` in the same session, with no NAND command afterward unless separately approved.
3. Record whether the status changes from `0x7009` to authorization success or to a DA-signature/key error. That distinction is the meaningful live test of the auth/DA association.
4. Keep the auth-only result as a transport and DA-hash-baseline result; it does not prove that the production BootROM trusts or rejects the SDK root by itself.

## Matching DA artifact

The matching DA is the existing stock signed artifact; it should not be re-signed:

`zlt x17m dumps/RG500LEUACR04A06M8G_OCPU_30.202.30.202/RG500LEUACR04A06M8G_OCPU_30.202.30.202/download_agent/DA_BR.bin`

SHA-256: `c3d9058aeb56373eaadc5868ce93198fb99a9cbf876a30f876714e9007d66d56`

Its two DA signature regions were already verified offline against the matching SDK DAA key. The similarly named `DA_BR_acc_bypass_nand.bin` is not this artifact and must not be substituted.

## Follow-up mtkclient attempt

The correctly parsed invocation reached:

```text
Preloader - Send auth error:Unknown: 0x7009
DaHandler - Device is protected.
DaHandler - Device is in BROM-Mode. Bypassing security.
```

This confirms the auth was sent and rejected at the same auth-stage status. Because the CLI automatically fell back to its Kamakiri path, the matching `DA_BR.bin` was **not** uploaded. The result is therefore not yet a paired auth-plus-DA test. The bypass attempt failed before any DA/storage operation.

## Paired stage-1 upload result

The no-jump runner then sent the verified stage-1 slice (`DA_BR.bin[0xBC:0x2F6CC]`, 194064 bytes) after the auth transaction:

```text
auth_final_status=0x7009
sending_verified_da_to_ram_only
upload_data failed with error: DAA_Security_Error (0x7017)
da_upload=FAIL
jump_da_sent=False storage_command_sent=False
```

This is the first live result reaching DA signature/security verification. The device did not execute the DA and no NAND command was sent. `0x7017` means the submitted stage-1 representation was not accepted by the DA authorization verifier; it does not by itself distinguish a wrong stage framing/region from a key or policy mismatch. Do not retry live until the exact BootROM stage-1 framing is reconciled offline with the DA GFH region metadata.
