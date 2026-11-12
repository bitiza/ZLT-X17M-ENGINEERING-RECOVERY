# Cellular Modem and MediaTek CCCI Architecture

Status: Characterization complete. Cellular baseband IPC constraints, daemon interactions, and recovery limits proven on live NAND hardware.

## FACTS

### Modem and Baseband Hardware Identity

- **Baseband SoC:** MediaTek MT6890 / T750 (octa-core ARM64 AP integrated with multi-mode 5G NR / LTE Sub-6 GHz baseband modem).
- **Module Subsystem:** Fibocom FG360-EAU integration.
- **Kernel Interface:** Cross-Core Communication Interface (CCCI) driver subsystem:
  - Device nodes: `/dev/ccci_ctrl`, `/dev/ccci_sys`, `/dev/ccci_ipc*`, `/dev/atci-service`, `/dev/ttyCCCI*`.
  - Virtual Network Devices: `ccmni0` through `ccmni20`. Active cellular data session binds to `ccmni1`.
  - Kernel workers: `[ccci_fsm1]`, `[ccci_poll1]`, `[ccci_sys]`, `[ccci_ctrl]`, `[ccci_rpc_k]`, `[ccmni1_rx_q_wor]`, `[ccci_dpmaif_rx0]`, `[md1_tx0_worker]`.
- **User-space Cellular Stack:**
  - `/usr/bin/dialer`: Proprietary Fibocom/MTK user-space dialer daemon. Implements CCCI PDU state machine, negotiates carrier APN, monitors network registration (CREG/CGREG/CEREG), and generates `/tmp/.tmp_dialer_sh` upon session establishment.
  - `/usr/bin/atcid` & `/usr/bin/atci_service`: AT command interface daemons attached to `/dev/atci-service`.
  - `/usr/bin/mipc_wan_cli`: Command-line tool communicating with TRM (Terminal Radio Manager) IPC for querying radio states, signal metrics, and SIM status.
  - `/usr/bin/atcmd`: Low-level AT command sender over `/dev/atci-service`.

### Established Operational Constraints

1. **CCCI Mailbox State Machine Inviolability:**
   - The T750 CCCI protocol relies on synchronous shared-memory queues between the Cortex-A55 AP kernel and the modem DSP core (`md1img` / `md1dsp`).
   - If `/usr/bin/dialer` is terminated via `SIGTERM` or `SIGKILL` while a cellular PDU session is active, or if asynchronous AT resets (`AT+CFUN=1`, `AT+CGATT=1`) are injected during an unexpected carrier drop, the user-space and kernel CCCI queues desynchronize.
   - Once desynchronized, `/usr/bin/dialer` repeatedly encounters IPC timeouts or failure to re-allocate CID (`mipc_msg_init MIPC_DATA_ACT_CALL_REQ failed`).
2. **The `x17m-iface-watch` Race Condition:**
   - The vendor environment runs `/usr/bin/x17m-iface-watch` polling every 2 seconds via `ubus call network.interface.wan renew`.
   - If OpenWrt's `netifd` protocol handler (`/lib/netifd/proto/x17m_external.sh`) blocks or attempts active recovery commands on interface teardown/setup, `x17m-iface-watch` continuously fires `renew` calls in a tight loop.
   - This creates a continuous restart storm that starves the cellular baseband of the 10–15 seconds of quiet time required to negotiate cell acquisition, attach, and PDU assignment.
3. **Thermal Throttling Interaction:**
   - The vendor thermal manager controls 5G NR secondary carrier groups via cooling device 7 (`/sys/class/thermal/cooling_device7`, type `scg-off-pa2`).
   - In high thermal events (>= 105°C), the script `/etc/tzscript/temperature_control.sh` executes `AT+EGMC=1,"endc_deactivation",2,1,0` and writes `1` to `cooling_device7/cur_state` to drop 5G NR.
   - If dropped, the modem falls back to LTE-A. When cooling occurs, user-space attempts to restore NR via state `0`.

## INFERENCES

1. **Recovery Boundary:** Standard OpenWrt WAN interface recovery (`ifup wan`, `ifdown wan`, or LuCI "Connect" / "Restart" buttons) cannot safely reboot or re-initialize the MediaTek T750 CCCI baseband once the hardware session drops.
2. **Netifd Protocol Role:** The netifd protocol handler for `ccmni1` (`x17m_external.sh`) must remain strictly passive: it should only reflect kernel device state and IP addresses into OpenWrt's ubus object model.
3. **Hardware Reset Requirement:** When the baseband modem loses sync or shuts down permanently, a full SoC reset (via OpenWrt `reboot` or LuCI System -> Reboot) is the only reliable recovery mechanism, as the bootloader (`preloader` / `lk`) cleanly re-initializes the CCCI mailbox and re-authenticates the modem firmware (`md1img`).

## UNRESOLVED

- Whether a specific proprietary `sockmsg_send` command exists that instructs the running `/usr/bin/dialer` to trigger a clean carrier detach/reattach without killing the CCCI process context.
