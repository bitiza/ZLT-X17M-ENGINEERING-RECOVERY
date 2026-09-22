# Recovery decision tree

This is an engineering decision tree rather than a generic flashing recipe.

```text
Device powers on
     |
     v
BootROM reachable?
     | no
     |--> hardware-level diagnosis
     |
    yes
     |
     v
Preloader runs?
     | unknown
     |--> safe 1.8 V UART diagnosis
     |
    yes
     |
     +--> BootROM DA
     |      \-- currently blocked by production DAA
     |
     +--> Preloader META
     |      \-- boot-mode selector only
     |
     v
LK reached?
     | unknown
     |--> safe UART / USB-mode observation
     |
    yes
     |
     +--> AEE / limited fastboot
     |      \-- LK/META investigation ongoing
     |
     v
Linux reaches META userspace?
     | yes
     |--> meta_tst can provide a powerful diagnostic/recovery surface
     |
     no
     |--> Linux META unavailable
     |
     v
Existing alternate A/B image valid?
     |
     +--> investigate legitimate rollback/selection path
     |
     \--> trusted write-capable environment still required
```

## Current boundaries

### BootROM DA

The architecture is capable of NAND access after a DA executes, but production authorization remains the blocker.

### Preloader META

Reachable on the failed units but not a persistent storage-command interface.

### LK

Still under investigation, particularly for devices that reach LK/early Linux but lose normal management access.

### Linux META

Powerful once userspace reaches it; unavailable for sufficiently early boot failures.

### UART

UART is diagnostic rather than a repair primitive. It remains critical because it can establish the real failure layer, active suffix, image verification result and kernel/rootfs progress.

The NAND X17M uses approximately 1.8 V UART logic. An unsuitable adapter was experimentally shown to disturb NAND initialization on a known-good router. Start receive-only with a proper 1.8 V interface and do not connect a 3.3 V TX signal directly to the router RX pad.

### Direct NAND

Physical NAND access is a last resort. Raw recovery must account for ECC, bad blocks, BMT/translation, OOB/in-band metadata and device-specific persistent data.
