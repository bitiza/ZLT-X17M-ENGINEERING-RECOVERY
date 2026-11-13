# MT6890 DAA policy/protocol reconciliation

## FACTS

1. The SDK `toolauth.py` creates only a GFH tool-auth object plus its RSA-PSS signature. It has no input for a DA filename or DA digest.
2. The SDK PSS GFH configuration contains `GFH_TOOL_AUTH` with `daa_public_key`, `sla_public_key`, and no DA-hash list. The generated object has `da_hash_num = 0`.
3. mtkclient's normal order is SEND_AUTH followed by SEND_DA. Its `send_auth()` returns the final status but does not itself transform the auth object.
4. The exact X17M DA descriptor table gives region 1 as:
   - file buffer `0xBC`
   - length `0x2F610`
   - load address `0x00200000`
   - signature offset `0x2F5CC`
   - signature length `0x100`
5. The transmitted stage-1 slice exactly matches that descriptor and its offline RSA-PSS signature verifies with the SDK DAA modulus `9af8...`.
6. Live behavior with that exact auth and stage is:
   - SEND_AUTH final status `0x7009`
   - SEND_DA status `0x7017`
   - no jump and no storage command

## INFERENCES

- `0x7009` during auth-only is compatible with the expected “no DA hash/DA association yet” state; it is not a standalone proof that the root key is untrusted.
- Because the exact descriptor address, stage boundary, and offline DA signature are now correct, the subsequent `0x7017` is no longer explained by the earlier address or full-container framing mistake.
- The remaining live rejection is therefore either a production policy/trust decision (the device does not accept the generated tool-auth chain or embedded DAA key) or an undocumented BootROM session binding not represented in the public SDK flow.

## UNRESOLVED QUESTIONS

- Whether production BootROM accepts the SDK's `9af8...` tool-auth root/DAA key pair.
- Whether MT6890 requires an OEM-generated auth object with a nonzero DA-hash association despite the SDK generator emitting `da_hash_num=0`.
- Whether an additional SEND_CERT, target-config query, or DA container command is required between auth and stage upload on this exact BootROM revision.

## Conclusion

Offline artifacts are internally coherent, and the DA upload parameters now agree with the DA GFH. The remaining distinction cannot be resolved from the SDK files alone because the decisive trust anchor and any undocumented session policy reside in BootROM/device state. Further live testing should be limited to one explicitly instrumented protocol variant at a time.

