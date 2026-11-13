# X17M recovery strategy

## Current assessment

The likely fault is corrupted rootfs or rootfs_data, but that remains a hypothesis until boot-stage evidence is available. The old UART adapter was electrically unsuitable, so previous UART conclusions are not reliable. The replacement 1.8-V UART is useful evidence, but recovery must not depend on it.

## Priority order

### 1. Preserve and use the replacement UART when available

Use it to identify the last successful stage (Preloader, LK, kernel, mount, or userspace) and the active A/B suffix. Treat this as diagnosis, not as the recovery mechanism.

### 2. Continue investigating software recovery through authorized DA

The exact signed DA is internally valid and its GFH extraction is understood. The remaining blocker is BootROM authorization: the generated SDK auth produced `0x7009`, and the following exact stage-1 DA produced `0x7017`. No NAND state was changed. An OEM production auth artifact, or a resolved MT6890 auth/session policy, could still enable RAM DA access and therefore Linux-aware NAND operations without external NAND instrumentation.

### 3. A/B recovery

If either slot is intact, the minimum repair may be selecting the opposite slot or resetting boot-control metadata. Do not write `misc`, `boot_para`, or slot metadata blindly. First establish the active suffix and boot-control record layout from the working-router dump and, if possible, failed-router UART output. Any slot change should be a separately verified, narrow operation.

### 4. Linux META

Linux META is confirmed useful on a healthy router (`/proc/cmdline`, `/proc/mtd`, and device-node reads), but neither failed router currently reaches `0e8d:202d`. It is therefore a conditional recovery path only if the failed unit can be made to boot an intact slot.

### 5. Physical NAND intervention

This remains the last resort and is not currently recommended. No direct NAND instrumentation should be attempted while the DA authorization and A/B alternatives remain unresolved.

## Practical consequence

The next high-value work is not another blind live DA retry. It is:

1. finish offline comparison of the production auth/session requirements;
2. search for an OEM auth artifact matching this exact MT6890/X17M package;
3. map the working unit's boot-control records and determine whether a volatile or authorized slot-selection mechanism exists;
4. use UART when available to confirm which recovery branch applies.

