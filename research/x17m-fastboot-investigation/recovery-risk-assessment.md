# Recovery risk assessment

## Preserved findings

**CONFIRMED, prior feasibility assessment:** A/B selection exists but B is not a proven independent recovery mechanism. The captured A rootfs occupies a 64 MiB region whose JFFS2 overlay is carved from its tail; current snapshot overlay starts 46.5 MiB into A and occupies 17.5 MiB. This split can move with SquashFS length. It is not safe to treat rootfs and overlay as unrelated storage or apply fixed geometry across images.

**CONFIRMED, prior backup provenance:** the NAND acquisition was non-atomic, contained unreadable expdb pages, did not cover a generic raw NAND/OOB restore process, and is not a validated complete restore kit. Correct hashes prove artifact consistency, not recoverability or originally correct NAND data.

**CONFIRMED, recent recorded bench state:** Linux can reach preinit/failsafe acknowledgment but its rootfs lacks `/dev`, preventing the expected shell. This is a runtime Linux failure, not proof of a bootloader failure. **UNKNOWN:** independently verified current bytes or health of either rootfs bank. The recent audit asserts that A is intact; that assertion does not establish a safe reachable switch back to A.

**UNKNOWN:** a complete independent unbrick procedure for this exact board/build. Fastboot query support does not fill that gap. The analyzed Fastboot implementation lacks conventional firmware flash commands and refuses set_active.

## Risks of proposed observations

| Operation | Principal risks | Safeguard |
|---|---|---|
| Existing ADB state reads | Load, output containing identifiers, selecting wrong unit; vendor sysfs access behavior | Explicit serial; known state files only; host-side logs |
| Host USB descriptors/listing | Control-read timeouts, VM visibility failures, wrong device attribution | Capture bus/interface details; no reconfiguration/detach; bounded observation |
| UART receive | Wrong voltage, ground/power connection, adapter DTR/RTS/break interference | Verify electrical compatibility first; no power wire/TX/control lines; use existing proven setup |
| Fastboot getvar on an existing endpoint | Firmware bugs, idle timer or watchdog reset, query mistaken for action | Explicit device, small allowlist, bounded host timeout, no OEM commands |
| Selector or reboot entry | WAN interruption, stalled boot, watchdog, retained reason or automatic metadata updates, no tested exit | Separate approval and exact-build review; no automatic fallback/actions |
| Reset-button discovery | Factory reset, configuration erase, crash or unexpected boot mode | Do not attempt without documented reviewed behavior |

**PROBABLE:** a verified preloader selector may avoid intentional flash modification. **UNKNOWN:** all automatic writes or reset side effects after that transition. “RAM-only token” is not sufficient to guarantee unchanged persistent storage across the ensuing boot. Likewise, an authorized normal boot can update counters without any explicit host flash command.

## Requirements before bootloader changes

No modification is recommended by this assessment. Before a future proposal could be reviewed, establish:

1. Exact board/storage/DRAM revision and deployed preloader/LK/kernel hashes, including which stage chooses the bank.
2. Vendor-supported recovery independent of Linux, tested on matching sacrificial hardware with an accepted authorized loader/tool.
3. Complete per-device partition/calibration/security backups, NAND geometry, OOB/ECC/bad-block handling and a verified restoration process.
4. Secure-boot and signature-chain requirements, valid signing/authorization process, supported image container and version/rollback rules.
5. Exact proposed changed bytes/source/configuration, why a change is needed, validation plan, deterministic entry/exit and rollback route.
6. Explicit authorization for the concrete operation and its failure consequences.

Until those exist, do not flash/erase/unlock, change slots or misc, patch/replace bootloaders, change security, write raw memory, or reset the configuration. Existing host backups and a second partition name do not reduce these prerequisites.
