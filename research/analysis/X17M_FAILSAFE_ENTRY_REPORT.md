# X17M failsafe-entry observation

## Result

The failsafe selector was accepted far enough for UART to print `- failsafe -`, but the device did **not** reach an observed interactive failsafe shell. Immediately after the selector, UART began a sustained `lock: applet not found` loop. This is consistent with the known missing `lock` BusyBox applet disrupting the failsafe hook. No command was entered at a shell prompt, no USB protocol traffic occurred, and no storage or configuration changes were made.

## Procedure and evidence

The capture used `/dev/ttyUSB0` at 921600 baud, 8N1, with software/hardware flow control disabled. It recorded UART bytes before the router was power-cycled and passively sampled `lsusb`. The script waited for the exact failsafe prompt; on seeing it, it transmitted only the two bytes `66 0a` (`f\n`) once, then returned to RX-only mode for 60 seconds. The script did not send any shell command or USB packet.

Evidence is preserved under [`analysis/live_failsafe/20260919T071926Z/`](live_failsafe/20260919T071926Z/):

| File | SHA-256 |
|---|---|
| `uart_raw.bin` | `aa1288e5d9e0c308aa0b6d0127fc01a91fd2e15e0751c2399e665dcbf711ee1e` |
| `uart_printable.txt` | `2918752e1a91813993392359ec034dc1a8152f0a38631f9db34e784a3586c67e` |
| `events.log` | `bcf2c6506283eef208646c02e6a28ac4eab979f18253ae478722f6ebaf5d3db7` |
| `usb_timeline.log` | `c5082d36dac2adb9be71c5a15ea7c99c85c849aa64f2a815570271dda521bbf5` |
| `host_metadata.txt` | `af0a8f534416e79d11f01586683f4875d9d2361fb95b24e9f95b82ab9bce099d` |

The raw stream is 607,924 bytes. `uart_printable.txt` is a derived decoding; the raw binary remains unmodified. `events.log` timestamps RX chunks, selector transmission, and capture close.

## Observed sequence (UTC)

- `07:19:27.121106` — UART capture opened RX-only.
- `07:19:39.409754` — first boot UART bytes received.
- `07:19:54.513510` — UART chunk containing the failsafe prompt was received. The prompt occurs at raw offset 37,474:

  ```text
  Press the [f] key and hit [enter] to enter failsafe mode
  ```

- `07:19:54.531347` — one UART transmission, `f\n` (`66 0a`). The raw stream contains the first `lock: applet not found` before this transmission and 23,760 occurrences after it.
- The stream then contains `- failsafe -` (raw offset 37,700), followed by the repeating error. The final occurrence is at raw offset 607,884. The errors occur throughout the rest of the capture, until UART capture closed at `07:20:54.652115`.
- No second boot banner, reset, panic, watchdog, or reboot message was identified in the capture.

The event log timestamps reads in chunks rather than timestamping each UART byte. Therefore the exact instant of the `- failsafe -` text cannot be assigned more precisely than its position in the post-selector stream.

## USB observation

The passive USB timeline recorded the host's static device list, including the CH341 UART adapter. It showed no MediaTek router VID:PID during the capture. No USB interface was opened or written to.

## Interpretation

**FACT:** The boot reached Linux preinit and printed the failsafe-key prompt. The host sent only `f\n` in response. The UART stream then printed `- failsafe -` and produced 23,760 subsequent `lock: applet not found` messages in approximately 60 seconds. No interactive shell prompt was observed.

**STRONGLY SUPPORTED:** The failsafe selection entered the failsafe hook, and the repeated missing-applet diagnostic is the hook's `lock -w` wait path failing immediately and looping. This matches the exact 8GB backup preinit analysis: in explicit failsafe, the hook waits for `/tmp/sysupgrade` while invoking `lock -w`; if the active BusyBox lacks `lock`, each call returns with “applet not found” instead of waiting. The repeated output is direct runtime evidence of that failure mode.

**UNKNOWN:** Whether the hook would eventually expose a shell if `lock` worked; whether another failsafe hook also ran; whether the device would progress to normal init absent this loop. The observed capture does not establish a hardware reset or reboot cause.

## Outcome

Failsafe mode was selected, but the result was **not a usable failsafe shell**. The device became stuck in a rapid missing-`lock` diagnostic loop during failsafe startup. No further interaction should be attempted at that console as part of this capture; no repair was performed.
