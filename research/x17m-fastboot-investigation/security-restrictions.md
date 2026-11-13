# Security restrictions

## Confirmed restrictions, with stage attribution

| Evidence | Conclusion | Scope |
|---|---|---|
| Prior BROM target config `0x000000e5`, hwcode `0x0992` | **CONFIRMED:** SBC and DAA enabled; SLA clear; memory-read/write authorization flags set | Historical sampled units; `X17M_USB_ENUMERATION_FINDINGS.md` and its raw JSON paths |
| DA upload returns `0x7017` after transfer checksum matches | **CONFIRMED:** submitted DA rejected by BROM security stage before execution | Tested candidate, not every signed DA |
| Recent audit reports preloader config `0x5`, DAA/SBC set; DA rejection `0x7024` | **CONFIRMED as recorded prior observation:** preloader DA signature gate rejects tested uploads | December-preloader bench session; independent raw upload trace not reacquired here |
| Prior UART `lk ... cert vfy`, `tee ... atf vfy` | **CONFIRMED:** boot-image certificate verification executed in that captured boot | Recent log/build, not proof of every trust-policy detail |
| LK includes certificate containers | **CONFIRMED:** signed-container structure present | Does not alone establish enforced fuses |
| Normal LK `set_active:` refusal stub, no flash/download registrations | **CONFIRMED:** restricted compiled command surface | Absence of command support is not evidence of a locked Android unlock state |

The different target-config words `0xe5` and `0x5` must not be treated as contradictory fuse reports: they were returned in different stages/contexts. Preserve the raw value and stage. SLA disabled does not mean DAA disabled or unrestricted memory access.

## Fastboot-specific authorization

**UNKNOWN:** Android-style bootloader lock state (`locked/unlocked`), a Fastboot authentication requirement, and any exact event-gating security policy. No live Fastboot getvar or authorization exchange was captured. The normal registration sequence contains no obvious per-command lock argument or unlock registration, but that does not rule out checks elsewhere.

**NOT SUPPORTED:** the claim that DAA explains the absence of a Fastboot endpoint. DAA verifies Download Agents at the MTK ROM/preloader transport stage; it is not automatically a gate on LK's USB initialization or getvar dispatcher.

**PROBABLE:** vendor build selection and boot-mode/event conditions account for at least part of the limited Fastboot exposure. **UNKNOWN:** whether board-specific USB initialization, security mode, crash-state checks, or a missing normal-LK transport block entry on a particular unit.

**CONFIRMED, source correlation:** the related preloader dispatcher checks a communication-forbidden attribute on META/factory paths; the FASTBOOT case in that source does not perform the same check. **UNKNOWN:** identical policy in the exact September NAND or December bench preloader. Do not transplant a permissive source branch into a confirmed runtime authorization claim.

## Interpretation of historical authentication work

The prior auth-only status `0x7009` was not defined in the local MTKClient table and its DA-association interpretation remains a hypothesis. Later paired upload rejection still does not isolate key mismatch from framing/policy solely by status. `X17M_RECOVERY_AUDIT_20261020.md` makes stronger key-mismatch claims; this investigation relies on the confirmed rejection, not an unproven universal explanation.

**CONFIRMED:** patched code inside a DA cannot execute before its outer DA signature gate passes. **UNKNOWN:** availability of a vendor-authorized matching DA and full NAND restore workflow. No authorization bypass, signature patch, security-state change or exploit was attempted. No private key material is included in these deliverables.
