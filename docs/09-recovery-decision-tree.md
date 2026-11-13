# Recovery decision tree

Revised 2026-11-13 from the live audit of the bricked 1 GiB NAND unit
(2026-10-20, [`research/analysis/X17M_RECOVERY_AUDIT_20261020.md`](../research/analysis/X17M_RECOVERY_AUDIT_20261020.md))
and the eMMC unbrick analysis
([`research/analysis/ZLT_X17M_EMMC_UNBRICK_ANALYSIS_20260926.md`](../research/analysis/ZLT_X17M_EMMC_UNBRICK_ANALYSIS_20260926.md)).
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
Preloader runs?  (0e8d:2000 window: ~1.9-3.6 s after power-on)
     | unknown
     |--> receive-only 1.8 V UART diagnosis; verify PMIC reset flag first
     |
    yes
     |
     +--> BootROM DA
     |      \-- CLOSED: production DAA rejects stock, ACC-bypass, unsigned,
     |           and community (X25) DAs; SDK key != device trust anchor
     |
     +--> Preloader boot-mode selectors  <-- LIVE-PROVEN reachable
     |      +-- METAMETA -> BOOT_MODE 1 -> lk boot mode = 1  (only mode LK acts on)
     |      +-- FASTBOOT -> BOOT_MODE 99 -> lk boot mode = 0 (aee_lk staged)
     |      +-- ADVEMETA -> BOOT_MODE 5  -> lk boot mode = 0
     |      \-- FACTFACT -> BOOT_MODE 4  -> lk boot mode = 0 (no write service)
     |
     v
LK reached?  (fastboot app starts on every boot and waits)
     | unknown
     |--> safe UART / USB-mode observation
     |
    yes
     |
     +--> LK fastboot endpoint
     |      \-- never enumerated (0e8d:201c); no download:/flash:/erase:
     |
     v
Linux reaches META userspace?  (needs a rootfs with /dev)
     | yes
     |--> meta_tst provides a powerful diagnostic/write surface (0x202d gadget)
     |
     no
     |--> Linux META unavailable even with lk boot mode = 1
     |     if the rootfs cannot mount devtmpfs
     |
     v
Existing alternate A/B image valid?
     |
     +--> slot selection: LK acts only on META_BOOT; set_active: is a stub;
     |    writing misc requires DA auth (circular dependency)
     |
     \--> trusted write-capable environment still required
          (signed DA from a same-trust-anchor unit, or physical NAND access)
```

## Current boundaries

### BootROM DA — CLOSED

The architecture is capable of NAND/eMMC access after a DA executes, but
production authorization blocks every tested agent: stock, ACC-bypass, unsigned,
and the community X25-package DA (all rejected at the DAA gate). The device
trust anchor differs from the SDK/DA public key; the only acceptable DA would be
signed with the device's own key modulus.

### Preloader boot-mode selectors — LIVE-PROVEN, but not write-capable

The selector channel works end to end on the failed unit: `READY` → selector →
acknowledgment (`TOOBTSAF`/`ATEMATEX`/`TCAFTCAF`), with device-side
`[BLDR] '<selector>' received!` confirmation over UART. The full measured matrix:

| Selector | ACK | Preloader `BOOT_MODE` | LK `lk boot mode` | Outcome |
|---|---|---:|---:|---|
| `METAMETA` | `ATEMATEX` | 1 | **1** | Linux boots in META mode; gadget blocked by broken rootfs |
| `FASTBOOT` | `TOOBTSAF` | 99 | 0 | `aee_lk` staged; LK boots Linux |
| `ADVEMETA` | `ATEMEVDX` | 5 | 0 | META params changed; LK boots Linux |
| `FACTFACT` | `TCAFTCAF` | 4 | 0 | No factory endpoint or write service observed |

The LK acts **only** on the `META_BOOT` value; three non-META modes (4, 5, 99)
are accepted and recorded by the Preloader and ignored by the LK. Selectors are
a control surface, not a repair surface.

### LK — statically characterized; endpoint never enumerates

The LK fastboot app starts on every boot and waits on an event; the `0e8d:201c`
endpoint was never observed even with `FASTBOOT` selected. The command table has
no `download:`/`flash:`/`erase:` and `set_active:` is a refusal stub — see
[docs/08](08-lk-meta-fastboot.md).

### Linux META — requires a rootfs with `/dev`

`meta_tst` and the `0x202d` gadget are userspace components. On the failed NAND
unit, even a successful `METAMETA` handoff (`lk boot mode = 1`) does not produce
the gadget, because the running rootfs cannot mount `devtmpfs` — preinit fails
with `can't open '/dev/null'` and procd never starts.

### UART — NEW: console is live and interactive

**FACT.** With a proper 1.8 V FTDI at 921600 8N1, the failed unit's console is a
working interactive tty: sending `f\n` at the OpenWrt failsafe prompt is accepted
and answered with `- failsafe -`. No shell follows because
`lib/preinit/99_10_failsafe_login` requires `-c /dev/console`, which cannot pass
in a rootfs with no `/dev`. The `1|2|3|4` debug-level keys are handled by the
preinit read loop and prove keystrokes are consumed. **Any recovery that supplies
a rootfs with `/dev` present is sufficient to turn this input channel into a
shell channel.**

UART remains diagnostic rather than a repair primitive, but it is the primary
instrument for establishing the real failure layer, active suffix, image
verification result, and kernel/rootfs progress. Three electrical/operational
rules now apply:

1. The NAND platform UART is a 1.8 V logic domain; an unsuitable adapter
   reproduced false NAND-initialization failures on a known-good router. Start
   receive-only; never connect a 3.3 V TX to the router RX pad.
2. **Warm reset vs full power-off is decisive for USB attachment.** The PMIC
   reset flag discriminates: `UVLO_RSTB` (undervoltage reset, clean supply
   collapse) → Preloader serves USB; `DDLO_RSTB` (brown-out latch from a warm
   reset or too-short power cycle) → USB never settles. Unplug the power adapter
   long enough for the rail to discharge and confirm `UVLO_RSTB` in the boot log
   before expecting the host to attach. Holding the power key during power-up
   separately skips USB enumeration.
3. **Do not share one host USB controller between the FTDI and the router** if it
   can be avoided, and use reconnect-aware capture: a power cycle re-enumerates
   the FTDI, killing a plain `cat /dev/ttyUSB0` descriptor, which silently
   produces zero-byte captures for exactly the window that matters.

### Direct NAND — last resort, now the fallback write path

Physical NAND access remains a last resort, but with all three software
flash-write paths closed (DAA gate, compiled-out Preloader-as-DA, LK's absent
flash commands), a physical write to the failed slot's rootfs partition is now
the highest-value hardware option. Raw recovery must account for ECC, bad
blocks, BMT/translation, OOB/in-band metadata and device-specific persistent
data.

## Ranked recovery options (2026-10-20 state)

1. **Obtain a DA the Preloader's DAA accepts** — from a same-family working unit
   whose Preloader demonstrably accepts a DA (highest-value remaining action;
   needs explicit authorization since the working unit is in service).
2. **Physical NAND write** to the failed slot's rootfs — bypasses every software
   gate; the restore image is already built and verified.
3. **Unsigned/community DA probes** — cheap, expected to fail with `0x7024`;
   a different status would still be informative.
4. **Factory selectors (`FACTORYM`)** — not recommended without a full verified
   backup: factory modes commonly expose write-enabled paths that erase
   partitions on entry, and no verified backup of the failed unit exists.

## Restore image prepared

`build_v19/images/rootfs_bozax17_v19_xray_busybox.img` — SHA-256
`95be8ec18a3dabad5e53e8467dc08ecbe4ead74d6e793dde17d7ec571d61130b`,
48,685,056 bytes (inside the 55,836,672-byte usable slot size), containing a
real `/dev/console` character device node (5,1), and user-confirmed to boot.
It is ready for whichever write path becomes available; the image is not the
gap — the write path is.
