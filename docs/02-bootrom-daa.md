# BootROM and Download Agent Authorization

## Purpose

MediaTek Download Agent Authorization (DAA) controls whether BootROM will accept and execute a Download Agent. It must not be conflated with the later certificate chain used for authenticated firmware images.

## Observed production state

On the working NAND X17M, BootROM reported:

```text
HW code      0x0992
HW subcode   0x8a00
HW version   0xca01
SBC          enabled
SLA          disabled
DAA          enabled
root cert    false
```

Memory-command policy was observed to vary across reconnect/preloader states, but DAA remained active.

## Separate trust domains

```text
PBP / firmware-image authentication
             !=
BootROM tool authentication
             !=
DA image authentication
```

A certificate/key observation in the Preloader or rootfs-signature domain therefore does not by itself explain BootROM DA acceptance.

## Live boundary

Generic/bypass attempts and later exact-artifact tests did not result in DA execution. Observed DAA-related statuses included `0x7009`, `0x7017`, and `0x7024` in different controlled tests.

The critical result is that these failures occurred **before DA execution and before any DA NAND/PMT operation**.

## FACTS

- DAA is enabled on production hardware.
- Successful BootROM USB handshake does not imply DA authorization.
- Relaxed memory-command flags do not imply DAA is disabled.
- No tested DA reached execution on the target.

## INFERENCES

After correcting DA descriptor, load-address and signature assumptions, the remaining rejection is consistent with a production trust/policy boundary or an undocumented session requirement.

## UNRESOLVED

- The production fused tool-auth trust anchor.
- Whether an OEM production authorization artifact exists for this device family.
