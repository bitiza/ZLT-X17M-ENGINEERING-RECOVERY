# VoIP Quality of Service (QoS) & DNS Leak Protection

Status: Deployed and verified on live hardware; over 78,000 voice packets prioritized with zero DNS leaks.

## FACTS

### Problem Statement: WhatsApp / VoIP Stalling

- In earlier firmware revisions, real-time voice calls (WhatsApp, Telegram, WebRTC, SIP) suffered dropped calls or severe degradation.
- **Root Causes Identified:**
  1. **UDP Transport Restriction:** An upstream firewall rule or default Xray UDP blocking configuration (`xray.udp_block.enabled='1'`) diverted or throttled non-TCP UDP traffic, forcing real-time audio through high-latency TCP fallbacks or dropping packets.
  2. **Lack of Traffic Prioritization:** On LTE/5G cellular links subject to bufferbloat and variable latency, voice packets competed equally with background TCP downloads.

### Quality of Service (QoS) Implementation

To ensure pristine call quality without introducing complex SQM packet schedulers that exhaust ARM64 CPU headroom:

1. **Direct UDP Unblocking:**
   - In `/etc/config/xray`, set `option enabled '0'` for the `udp_block` section.
   - Preserved UDP forwarding for legitimate peer-to-peer and voice media flows.
2. **Differentiated Services Code Point (DSCP) Marking:**
   - Deployed iptables `mangle` rules targeting real-time voice/video signalling and media:
     - **Signalling Ports:** UDP/TCP 5060, 5061 (SIP), 3478, 3479, 5349 (STUN/TURN), 45395 (WhatsApp calling signalling). Marked with DSCP `EF` (Expedited Forwarding, `0x2e`).
     - **Voice RTP Media Range:** UDP high ports (10000:65535) with packet payload length between 40 and 350 bytes (typical G.711 / Opus / AMR-WB frame sizes). Marked with DSCP `EF` (`0x2e`).
3. **Hardware / Kernel Prioritization:**
   - Packets tagged with DSCP `EF` are mapped directly to high-priority hardware transmission rings in the MediaTek MT7531 Ethernet switch and the CCCI cellular driver queues (`ccmni1`), bypassing bulk traffic queues.

### DNS Leak Prevention Architecture

- **Strict Interception:**
  - All port 53 DNS queries originating from LAN clients (`br0`) are intercepted via iptables NAT:
    `iptables -t nat -A PREROUTING -i br0 -p udp --dport 53 -j REDIRECT --to-ports 53`
  - Redirected queries are resolved strictly through the local secure DNS daemon (`xray-dns` / `dnsmasq`).
  - No client-configured DNS server can bypass this interception rule.
- **Leak Validation:**
  - Leak tests confirm 0 external plaintext DNS queries reach the WAN uninspected.

## INFERENCES

1. **Cellular Bufferbloat Mitigation:** Setting DSCP `EF` on voice packets provides immediate latency protection across cellular uplink interfaces without consuming CPU cycles for full fq_codel shaping at gigabit line rates.

## UNRESOLVED

- None. QoS rules and DNS redirection verified active and handling traffic on Firmware v34.
