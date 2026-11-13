# Read-only DA test plan for a bootlooped X17M

Date: 2026-09-21  
Scope: one live connection/PMT probe using the existing
`DA_BR_acc_bypass_nand.bin`. No write, erase, reset, or partition dump is part
of this first test.

## Why this is the right first test

The current Linux USB bus has no attached `0e8d` device, so no live attempt was
run from this environment. The attached firmware archives contain a stock DA,
but the local `zlt-dump` package contains a separate ACC-bypass NAND DA that was
specifically prepared for MT6890 NAND PMT access:

```text
/home/kali/Desktop/x17m/zlt-dump/lib/da/DA_BR_acc_bypass_nand.bin
SHA-256: b207028741fd66c458ea4d86a06b06c9c6679b82cf24e607ad4eb3b24af9264e
```

The first useful question is whether the failed router accepts the DA and lets
it initialize NAND/return the PMT. A successful PMT response proves more than
Preloader META enumeration, while keeping the flash untouched.

## Command

With one bootlooped router powered off and connected so that it appears as
MediaTek `0e8d` Preloader/BROM, run:

```bash
python3 /home/kali/Desktop/x17m/analysis/probe_da_nand_readonly.py --timeout 120
```

The wrapper bootstraps/uses the patched local mtkclient, selects the NAND DA,
and invokes exactly:

```text
mtkclient --da DA_BR_acc_bypass_nand.bin printgpt
```

For this patched NAND path, `printgpt` is the PMT/partition-table discovery
operation. It does not request a partition payload and does not issue a write,
erase, or reset command.

The wrapper prints `safety=READ_ONLY`, the selected DA, the exact operation, and
the mtkclient output/return code. A failed connection or DAA rejection is still
useful evidence; it does not imply that any flash operation was attempted.

## What to capture

Save the complete terminal output. The important outcomes are:

* DA accepted and NAND initialized; PMT entries returned.
* DA accepted but PMT/storage initialization failed.
* DAA/SLA/authentication rejection before DA execution.
* No `0e8d` device observed / timeout.

Do not proceed directly to `w`, `wf`, `wo`, `e`, `es`, `ess`, `reset`, or a full
dump based only on a successful connection. If PMT discovery succeeds, the next
read-only step should be a deliberately narrow read of `misc` (or another
non-identity diagnostic partition), with its output and device-specific
geometry reviewed first.

## Safety boundary

The probe wrapper contains no call to mtkclient's read-partition, write,
erase, reset, or flash commands. It may write only local mtkclient bootstrap
files/logs. It does not modify the router or any firmware image.

## Live result (2026-09-21)

The probe was run against a bootlooped router. It reached the device and
obtained the target configuration, but the DA was not accepted or executed:

```text
HW code:              0x0992 (MT6880/MT6890 family)
TARGET_CONFIG:        0x000000e5
SBC enabled:          True
SLA enabled:          False
DAA enabled:          True
Root cert required:   False
Mem read auth:        True
Mem write auth:       True
Cmd 0xC8 blocked:     True
Auth file required
generic_patcher_payload.bin: Error on sending payload
return_code=1
```

The tool briefly lost and then rediscovered the device in regular Preloader
mode while retrying its protected-device path. It never reached DA execution,
PMT access, or a NAND command. The ACC-bypass DA therefore did **not** bypass
this router's BootROM DAA boundary.

This result is consistent with the earlier authentication-only evidence and
does not indicate a bad NAND or bad PMT. It establishes that the next DA route
would require an OEM-authorized/authenticated DA or a separately validated
authorization mechanism. Repeating the generic patcher attempt is not useful
without a new hypothesis.
