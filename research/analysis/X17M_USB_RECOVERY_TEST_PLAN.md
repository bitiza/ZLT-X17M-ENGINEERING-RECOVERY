# X17M read-only USB recovery-interface test plan

## Safety boundary

This stage is host-side observation only. Do not run `zlt-dump`, `mtk.py
printgpt`, or any command with a DA argument: the supplied script's `printgpt`
path uploads a DA before it can query storage.

Do not send download-protocol commands, change slots, reboot through a protocol,
or read/write/erase storage until the observed USB stages and authorization
policy have been reviewed separately.

## Passive capture

1. Attach the physical X17M USB device to the Kali VMware guest.
2. Run `analysis/capture_x17m_usb_enumeration.sh 180`.
3. During the capture, power-cycle the bootlooped X17M normally. Do not hold test
   points or force BootROM yet.
4. Preserve the generated `analysis/live_usb/x17m-usb-*` directory.
5. Repeat with the known-good 8 GB and smaller-capacity units, labeling which is
   which.

The evidence sought is the full VID:PID sequence and dwell time for BootROM,
preloader/download, LK/fastboot, kernel gadget, and disconnect/reboot events.
MediaTek commonly uses vendor ID `0e8d`, but specific product IDs must be
observed rather than assumed.

## Decision gate after enumeration

- A stable preloader/download VID:PID permits descriptor-only characterization.
- A transient stage may require a host listener to hold it, but that is active
  protocol interaction and needs a separately reviewed command.
- `zlt-dump` cannot serve as the passive listener because it invokes mtkclient
  with `--da` even for `printgpt`.
- X28 unsigned-DA acceptance is not evidence of X17M DA acceptance. Firmware
  image authentication and BootROM/preloader SLA/DAA must be evaluated
  independently.

## First bootlooped-X17M observation

Two passive cycles showed this sequence:

1. `0e8d:0003`, no manufacturer/product strings, CDC ACM `/dev/ttyACM0`.
2. Disconnect.
3. About 2.5 seconds later, `0e8d:2000`, manufacturer `MediaTek`, product
   `MT65xx Preloader`, CDC ACM `/dev/ttyACM0`.
4. Disconnect after about 1.1 seconds at the identified stage.

Cycle starts were approximately 43.4 seconds apart. This identifies accessible
BootROM-facing and preloader-facing windows, but does not reveal SLA or DAA.

Upstream mtkclient commit `cd25cf9c1ff6d36e82697ac2c798e69e9cfb78c3`
provides `gettargetconfig`, but its implementation calls full preloader
initialization, including transient register operations. It was therefore not
used. A reviewed minimal client subsequently sent only the synchronization
sequence, `GET_HW_CODE` (`0xFD`), and `GET_TARGET_CONFIG` (`0xD8`).

The result was:

| Field | Value |
|---|---|
| hardware code | `0x0992` |
| target configuration | `0x000000e5` |
| status | `0x0000` |
| SBC | enabled |
| SLA | disabled |
| DAA | enabled |
| root-certificate-required bit | clear |
| memory-read authentication | enabled |
| memory-write authentication | enabled |
| command `0xC8` | blocked |

No DA/payload was uploaded and no memory, storage, reset, or slot command was
sent. The next decision is therefore not whether generic MTK USB access exists;
it does. The decision is how DAA can be satisfied without risking storage.

## Completed authentication-only DA test

After separate explicit approval, the X28 eMMC DA's 218,944-byte stage 1 was
sent to volatile RAM with `SEND_DA`, but deliberately not executed. BootROM
reported the correct transfer checksum (`0x9a21`) and then rejected the stage
with `0x7017` (`DAA_Security_Error`). No `JUMP_DA`, memory command, storage
command, reset, or slot command was sent. This rules out using that supplied DA
directly through the tested X17M BootROM path.

Upstream mtkclient also lists `mt0992` in `config/missing_brom.txt`; a complete
turnkey BootROM exploit profile is not present. The X28 patch's preloader
payload address is implementation evidence for a possible preloader route, not
evidence that it bypasses this X17M's DAA policy.
