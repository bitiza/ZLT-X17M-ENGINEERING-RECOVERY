# X17M bench manual — one test at a time

Everything is driven by a single script so that a run is never a chain of competing
tests. Run **one test per power cycle**.

```bash
cd /home/kali/Desktop/x17m/work
```

## The three commands

### 1. `status` — see what the host sees

```bash
python3 x17m_bench.py status
```

Reports every USB identity, whether a Preloader window (`0e8d:2000`) is open right now,
and whether any enumeration is stuck.

### 2. `select` — send one boot-mode selector

```bash
python3 x17m_bench.py select --selector factorym --wait 900 --observe 120
```

Selectors available:

| name | token | expects | SDK boot mode |
|---|---|---|---|
| `metameta` | `METAMETA` | `ATEMATEX` | 1 (`META_BOOT`) |
| `fastboot` | `FASTBOOT` | `TOOBTSAF` | 99 |
| `advemeta` | `ADVEMETA` | `ATEMEVDX` | 5 |
| `factfact` | `FACTFACT` | `TCAFTCAF` | 4 (`FACTORY_BOOT`) |
| `factorym` | `FACTORYM` | `MYROTCAF` | 6 (`ATE_FACTORY_BOOT`) |

The command **waits** for the Preloader to appear, sends the token as the very first
write, and reports one of:

* `RESULT: ACCEPTED - device replied <ACK>` — the selector was accepted
* `RESULT: no 0e8d:2000 seen within the wait window` — no window opened
* `RESULT: READY never arrived` / `acknowledgement ... not received` — the channel was
  open but the device did not accept the token

After a successful selector it watches USB identities **passively** for `--observe`
seconds. It never sends traffic to any endpoint it discovers.

### 3. `uart` — capture the console

```bash
python3 x17m_bench.py uart --seconds 900 --out uart.log
```

**This is the important one.** The router and the FTDI share one physical USB
controller, so a router power cycle also drops the FTDI. A plain `cat /dev/ttyUSB0`
holds a dead file descriptor and records nothing exactly when it matters. This logger
re-resolves the port by VID:PID and reopens it whenever it disappears, so it keeps
recording across power cycles.

Each reopen is marked in the log:

```
=== [uart_watch] (re)opened /dev/ttyUSB0 attempt 1 ===
```

Those markers are the boot boundaries.

### 4. `summarise` — read a capture

```bash
python3 x17m_bench.py summarise uart.log
```

Prints boot boundaries, the selector acknowledgements, `BOOT_MODE` / `lk boot mode`
values, and the PMIC reset flag for each boot.

## Reading the PMIC reset flag — this is the key diagnostic

Every boot prints one of:

```text
[pmic_check_rst] UVLO_RSTB     <- good: the supply collapsed, a real power-off
[pmic_check_rst] DDLO_RSTB     <- bad: brown-out, a warm reboot
```

* **`UVLO_RSTB`** — a genuine full power-off. The Preloader enumerates properly and
  serves USB. The host can attach.
* **`DDLO_RSTB`** — the supply sagged instead of collapsing (short power cycle, or a
  reset button press). The Preloader's USB session is disturbed: the log then shows
  `Enumeration(End): OK` repeating, and `READY` is never emitted, so no host
  transaction can start.

If a boot shows `DDLO_RSTB`, the host cannot attach no matter what the host software
does. **Leave the power adapter unplugged for 30 s or more** so the PMIC rail
discharges fully, then reconnect.

## Why the window is so short

Measured Preloader tool timeouts on this unit:

| cycle | `Enumeration(End)` | verdict |
|---|---:|---|
| 13:42 | 3313 ms | usable |
| 14:07 | 1895 ms | usable |
| 15:35 | 835 ms | **too short for the host to attach** |

The window depends on boot timing and shrinks when the supply is not fully collapsed.
That is why a test can be "running" and still miss the device.

## Recommended sequence for a test

1. Terminal A: `python3 x17m_bench.py uart --seconds 900 --out uart.log`
2. Terminal B: `python3 x17m_bench.py select --selector <name> --wait 900 --observe 120`
3. **Power-cycle the router**: unplug the power adapter, unplug USB, wait **30 s+**,
   plug USB in, plug power in.
4. Terminal B reports the result.
5. Terminal A: stop with Ctrl-C, then `python3 x17m_bench.py summarise uart.log`

To confirm the boot was healthy, check that the summary shows `UVLO_RSTB` and that
`lk boot mode` has the expected value.

## Current state of the investigation

| selector | acknowledgement | `BOOT_MODE` | `lk boot mode` | result |
|---|---|---:|---:|---|
| `METAMETA` | `ATEMATEX` | 1 | **1** | accepted; Linux in META mode; the `0x202d` gadget needs a working rootfs, which is what is broken |
| `FASTBOOT` | `TOOBTSAF` | 99 | 0 | accepted; `aee_lk` staged; LK booted Linux |
| `ADVEMETA` | `ATEMEVDX` | 5 | 0 | accepted; META params changed; LK booted Linux |
| `FACTFACT` | `TCAFTCAF` | 4 | 0 | accepted; LK booted Linux; no write service |
| `FACTORYM` | `MYROTCAF` | 6 | 0 | accepted; LK booted normal Linux; no ATE factory USB service |
| `AT+NBOOT` | `AT+OK` | 0 | ? | not tested; equivalent to a normal boot |

Only `META_BOOT` is acted on by the LK. Every write path is closed for an independent
reason (DAA gate, compiled-out `CFG_PRELOADER_AS_DA`, absent LK `download:`/`flash:`,
and now "the META gadget needs the very rootfs we are trying to install").

### Why modes 4, 5, and 6 fall back to normal boot

The November 3 live UART capture `factorym_new.log` contains two full cold boots.
`FACTORYM` produced `BOOT_MODE: 6` and `ADVEMETA` produced `BOOT_MODE: 5`; in both
cases LK reported `lk boot mode = 0` and booted normal Linux. Earlier captures
show `FACTFACT` with `BOOT_MODE: 4` / LK mode 0 and `METAMETA` with `BOOT_MODE: 1` /
LK mode 1. The preloader accepted the selectors and recorded the requested modes.

Read-only disassembly of the archived September 2025 X17M NAND LK image
`/home/kali/Desktop/bozax17/backups/x17m-1gb-20260921-061524/logical/mtd25_lk_a.img`
(SHA-256 `a757f40b3c7da58167c56cde10728768196f42e53a8c10c49e6de97fd9ef1b5e`)
explains the pattern. Thumb file offsets `0x0a0a` and `0x0a18` save and read the
preloader boot-mode tag. At `0x3afe..0x3b18`, LK compares the tag to **1** and
sets its own mode byte at `0x84051734` to **1** only on equality. There is no
assignment for 4, 5, or 6 in that function. `boot_linux_fdt` calls the getter
at `0x4c3c` immediately before printing `lk boot mode = %d`. The mode setter is
called at `0x4ed4` in the LK boot path. This is direct evidence for the archived
LK; the live unit's LK image has not been dumped or byte-compared, so identical
code on that unit is an inference supported by its matching UART behavior.

The preloader security-forbidden branch in the source-correlated selector
handler sends `METAFORB` and logs that the token is forbidden. Neither occurred
in these captures. The observed normal boot does not establish a fuse or
`sec_cfg` rejection; the archived LK's explicit mode-1-only assignment is the
stronger explanation.

The image to install is ready and verified:
`build_v19/images/rootfs_bozax17_v19_xray_busybox.img`, SHA-256
`95be8ec18a3dabad5e53e8467dc08ecbe4ead74d6e793dde17d7ec571d61130b`, 48,685,056 bytes,
real `/dev/console` device 5,1, user-confirmed to boot successfully.

## If the host still cannot attach

1. `python3 x17m_bench.py status` — is `0e8d:2000` present right now?
2. Check the UART summary for `UVLO_RSTB` vs `DDLO_RSTB` on the most recent boot.
3. Try a longer power-off (60 s) and a different USB port or cable.
4. If the FTDI and the router are on the same physical hub, the router's power cycle
   disturbs the host's USB stack. Moving the FTDI to a different port or powering it
   from a separate supply removes that coupling.

## X25-DA DAA gate test (one power cycle, non-destructive)

Candidate: the only untested download agent in the public ecosystem —
`work/dax28/DA_X25_20231228.bin` (X25 SPFT package, `MTK_DA_v6_2023-12-28`,
sha256 `c873d21d…`). No write/erase/path besides the DA upload itself.

1. Terminal A: `python3 x17m_bench.py uart --seconds 900 --out uart.log`
2. Terminal B: `python3 pl_da_x25.py` (it polls 900 s for the preloader window)
3. Power-cycle (adapter + USB unplugged ≥30 s, USB in, then power); never press reset.
4. Verdict in terminal B:
   - `DAA_SIG_VERIFY_FAILED (0x7024)` → X25-generation key mismatches ours; DA route
     closed for everything public. Report and move on.
   - anything else, esp. a completed partition-table read → **stop, save the output,
     and report before anything else happens.** No further commands — no write, no
     erase, no boot sequence from the DA.
5. `summarise` in terminal A afterwards.
