# Vendor Scripts, Startup Architecture & Middleware Audit

Status: Complete audit of 228 vendor shell scripts and daemons across `/etc/init.d/`, `/etc/tzscript/`, and `/usr/libexec/`.

## FACTS

### Startup Architecture: `S99tzproc`

The vendor implements system startup via a monolithic procd wrapper: `/etc/init.d/tzproc` (executed at boot via `/etc/rc.d/S99tzproc`). Rather than utilizing standard OpenWrt modular init order, `tzproc` sequences over 35 distinct vendor daemons, background polling scripts, and configuration scripts.

### Identified Vendor Script Defects & Typos

1. **`power_daemon` Typo:**
   - **Path:** `/etc/init.d/power_daemon`
   - **Defect:** Vendor SDK declared `PROG=/usr/bin/power_deamon` and invoked `/usr/bin/power_deamon`. The compiled binary on disk was `/usr/bin/power_daemon`.
   - **Symptom:** Boot failure logged: `/etc/rc.common: line 11: /usr/bin/power_deamon: not found`.
   - **Correction:** Fixed binary path to `power_daemon` and guarded autosleep sysfs write.
2. **Missing `cron_master`:**
   - **Path:** `/etc/init.d/tzproc` lines 44 & 154
   - **Defect:** Unconditionally invoked `/etc/init.d/cron_master start` and `stop`. The binary `/usr/bin/cron_master` was never compiled or shipped for this hardware platform (only `/usr/bin/cron_controller` exists).
   - **Correction:** Guarded start/stop with `[ -x /usr/bin/cron_master ]`.
3. **Hardcoded Linux 4.4 Kernel Modules in `sip_alg.sh`:**
   - **Path:** `/etc/tzscript/sip_alg.sh`
   - **Defect:** Hardcoded `insmod /lib/modules/4.4.83/kernel/net/netfilter/nf_conntrack_sip.ko` (copied from an older Linux 4.4 MediaTek platform). The running kernel is Linux 5.4.238, rendering module loading completely inoperative. In addition, `/usr/sbin/siproxd` was launched without checking existence.
   - **Correction:** Replaced with dynamic `modprobe nf_conntrack_sip` and `modprobe nf_nat_sip 2>/dev/null`, and guarded `/usr/sbin/siproxd`.
4. **Missing `thermal_intf` Binary:**
   - **Paths:** `/etc/tzscript/start_temp_mode.sh` and `/etc/tzscript/temperature_control.sh`
   - **Defect:** Scripts unconditionally executed `/usr/bin/thermal_intf apply ...`, but the binary does not exist in the rootfs.
   - **Correction:** Guarded invocations with `[ -x /usr/bin/thermal_intf ]`.
5. **Dead Enterprise / Carrier Scripts:**
   - **/etc/init.d/jingdongwuliu:** References `/usr/bin/jingdongwuliu` (JD Logistics enterprise daemon). The binary does not exist on this device. The wrapper in `/etc/tzscript/start_codplatform.sh` checks `[ -f /usr/bin/jingdongwuliu ]` and remains dormant.
   - **/etc/tzscript/remote_start.sh:** Legacy SHCL03 customer script for TR-069 direct web portal access.
   - **/etc/tzscript/tz_set_l2tp_5_static_ip.sh:** Legacy SA0343 EBU customer static IP workaround.
6. **Shell Syntax and Bashisms:**
   - Multiple `#!/bin/sh` scripts used bashisms (`function name()` syntax and unquoted variables `[ ${var} -eq 1 ]`).
   - Cleaned and converted to POSIX standard in `temperature_control.sh`, `start_voice.sh`, `utnd_sw.sh`, and `dropbear_sw.sh`.
7. **Procd Service Deletion Warnings:**
   - Wrappers `/etc/tzscript/modem_log_sw.sh`, `routemanger_start.sh`, and `fota_start.sh` called `/etc/init.d/<svc> stop` when features were disabled, emitting `Command failed: Not found`.
   - Corrected with `2>/dev/null` redirection.
8. **Upstream `ddns-scripts` Exit Error Spam:**
   - OpenWrt upstream generic `ddns-scripts` ran hourly at `/etc/rc.d/S95ddns` with dummy placeholder `yourhost.example.com`, failing repeatedly. Disabled in `/etc/config/ddns` and removed boot links.

## INFERENCES

1. **Vendor Code Provenance:** The vendor codebase contains layers of copy-pasted legacy scripts accumulated across multiple router hardware generations (Linux 4.4 kernel platforms, MT7621/MT7628 boards, and custom Chinese enterprise deployments such as JD Logistics).
2. **Runtime Resilience:** Guarding missing binaries and silencing spurious deletion errors prevents procd from thrashing during boot and eliminates persistent syslog pollution.

## UNRESOLVED

- None. All audited scripts pass `sh -n` syntax checks and execute cleanly on Firmware v34.
