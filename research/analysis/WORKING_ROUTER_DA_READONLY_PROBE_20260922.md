# Working-router DA read-only probe — 2026-09-22

Script:

```text
analysis/probe_da_nand_readonly.py
```

Requested operation was `printgpt` only. The wrapper explicitly forbade
partition reads, writes, erase, reset, and flash operations. No NAND command
completed and no device write was requested.

## Observed sequence

### Initial BROM state

```text
HW code              0x0992
HW subcode           0x8a00
HW version           0xca01
SW version           0x1
ME_ID                7D2DEDE9B6C0D14B8A055B3238F43ACA
Target config        0x05
SBC                  enabled
SLA                  disabled
DAA                  enabled
SWJTAG               enabled
Root cert required   false
Mem read auth        true
Mem write auth       true
Cmd 0xC8 blocked     true
```

The supplied `DA_BR_acc_bypass_nand.bin` could not be uploaded because the
device required an authentication file. The first Kamakiri/generic-patcher
attempt also failed before any DA execution.

### Transient regular-mode state after the crash attempt

The tool then observed a temporary regular/preloader state:

```text
Target config        0xe5
SBC                  enabled
SLA                  disabled
DAA                  enabled
SWJTAG               enabled
Root cert required   false
Mem read auth        false
Mem write auth       false
Cmd 0xC8 blocked     false
```

Despite the relaxed memory-command flags, DA upload failed with:

```text
DAA_SIG_VERIFY_FAILED (0x7024)
```

The device subsequently returned to BROM and again reported target config
`0xe5`, with `Mem read auth=true`, `Mem write auth=true`, and `Cmd 0xC8
blocked=true`; it again requested an auth file.

## Facts

1. The working router's BootROM reports SBC and DAA enabled. This independently
   confirms the BROM/Preloader report and should not be inferred from the Linux
   devinfo word at NVMEM offset `0x7c`.
2. SLA is disabled, but that does not disable DAA authentication.
3. The ACC-bypass DA did not pass DAA signature verification.
4. `printgpt` did not reach NAND partition discovery. No GPT/PMT data was
   returned by this run.
5. The repeated ME_ID is a device identifier and is not a public-key hash.

## Interpretation

The result localizes the blocker to authenticated DA admission, not NAND
access or PMT parsing. The transient `0xe5` state changes memory-command policy,
but the BootROM still verifies the DA signature and rejects the supplied binary.
The earlier SDK/tool-auth analysis therefore remains relevant: an accepted DA
requires the production DAA trust chain, and the available bypass binary is not
accepted by this unit.

The target-config transition should not be treated as a writable security
state. It was observed during the tool's crash/reconnect sequence, and the
probe performed no explicit write or erase operation.

## Unresolved

* Whether the transient `0xe5` state is a normal Preloader handoff state or a
  side effect of the failed crash attempt.
* Whether an OEM-signed DA/auth pair exists in the supplied SDK packages that
  matches this production unit.
* Whether `0x11ec0060`'s Linux devinfo/API snapshot differs from the live BROM
  target-config register because of stage, unit, or register-representation
  differences.

