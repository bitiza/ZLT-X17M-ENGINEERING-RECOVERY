# Windows META entry and immediate read

## Purpose

`enter_meta_windows_read.py` ports the exact successful Kali Preloader
selector exchange to Windows COM transport. This avoids moving USB ownership
from Kali to Windows after boot, which can miss a short-lived Linux META port.
Windows selection and a complete read are verified on the working NAND unit.
Recovery of the stock bootlooped 8 GB unit remains unverified.

The sequence is:

1. Wait for a serial port with USB identity `0e8d:2000`.
2. Receive `READY`, send `METAMETA`.
3. Receive `ATEM0001`, send `040000000100000003000000`.
4. Receive `ATEM0002`, send `06000000010000000300000001000000`.
5. Receive `ATEMATEX`, send `DISCONNECT` and close the Preloader COM port.
6. Immediately poll for `0e8d:202d` serial ports and launch small reads on
   up to three ACM ports concurrently, or only the selected `--meta-port`.
   Completed small reads with no response can be retried within the readiness
   window; uncertain writes stop that port. Reads target `/proc/cmdline`,
   or `/proc/mtd` if explicitly selected.

The wrong ACM ports may return garbage or no data; only a reply passing the
existing strict checksum, token, offset, status and EOF checks counts as success.
All expected Preloader acknowledgments are required before advancing.
Fragmented COM acknowledgments and repeated READY messages are handled.
This does not include flash writes, erase, arbitrary commands, or a DA loader.

## Files and use

Keep these three files together on Windows:

- `enter_meta_windows_read.py`
- `meta_tst_safe_read.py`
- `meta_tst_frame_decoder.py`

The archive `windows_meta_entry_read.zip` contains them and these instructions.
Use the existing MediaTek Preloader VCOM driver and META ACM drivers first.
No WinUSB driver replacement is required by this COM-based implementation.
The user's installed VCOM driver carried the raw selector exchange successfully.

```powershell
py -m pip install pyserial
py .\enter_meta_windows_read.py
py .\enter_meta_windows_read.py --enter
```

The first script invocation is an offline dry-run. The second waits for a
power-cycle, enters META and performs the immediate small read probes.
Keep the router USB attached to Windows, disable VM USB auto-capture for it,
and close other programs using its COM ports. Start with the working NAND
unit before attempting the bootlooped 8 GB unit. Disconnect an existing META
session before starting: the tool rejects a pre-existing `0e8d:202d` identity
to avoid probing a different unit.

If multiple Preloaders are attached, select one with
`--preloader-port COMxxx`. The port must still enumerate as `0e8d:2000`.
Each invocation creates a new `windows_meta_*` directory with timestamped
handshake/port events and raw read captures plus JSON token metadata.
Provide the whole directory if the attempt fails.

If a port disappears while being read, the receiver preserves captured bytes
but may report a transport failure before parsing. Such a capture can be
decoded offline with the token from its JSON sidecar:

```powershell
py .\meta_tst_safe_read.py --decode-capture .\windows_meta_DIRECTORY\meta_COMxxx.bin --target /proc/cmdline --token 0xTOKEN
```

## Current limitations

No local tests or hardware execution were performed for this new entry tool.
Its COM baud setting is 115200 with software and hardware flow control disabled,
and DTR/RTS asserted during the Preloader handshake. Compatibility with the
specific Windows Preloader driver must be established on the healthy device.
Windows driver enumeration/open latency can still exceed the stock firmware's
META window. The tool cannot keep a service alive if firmware tears it down,
nor can it create a Linux META service that never starts.

Previously verified: the healthy NAND unit accepts the Kali bulk-USB selector,
and the Windows META reader successfully retrieves the complete 219128-byte
binary and 524288-byte PMT image with matching hashes. Those tests did not
verify Windows Preloader selection or recovery of the 8 GB unit.

## Windows live result and COM open retry update — 2026-10-08

The user completed the exact selector exchange on Windows COM278
(`0e8d:2000`), including all acknowledgments and `DISCONNECT` at
20:43:59 UTC. Windows Preloader COM transport is now hardware verified on
this working unit. META ports first appeared around 20:44:38 UTC, roughly
39.4 seconds later. All three immediate opens failed with FileNotFoundError,
before any operation-3 request was sent. The original orchestration marked
each port as attempted and exited after those failures.

A later manual read at 20:45:59 UTC succeeded on COM281: 453 bytes, two
validated responses including EOF, rootfs B. This establishes Windows META
entry and subsequent Linux META reads in one host session on the healthy
unit. The evidence is consistent with COM publication preceding port-open
readiness; it does not precisely establish when the port became usable.

Updated the shared reader with an optional open-retry period. The entry tool
now retries each of the three COM opens every 20 ms for up to 15 seconds.
It retries only failures before the port opens; after opening, each worker
still performs exactly one read-request write. It does not retry a failed
write or resend a request. Existing standalone reader behavior retains a
zero-second open-retry default. Output reports the number of open attempts.
This retry update has not yet been tested. The 8 GB unit's short-lived META
service remains unverified.

## COM opens succeeded but initial reads were silent — 20:49 UTC

The second Windows attempt again completed the selector on COM278 at
20:48:57 UTC. META ports appeared at 20:49:37 UTC. The retry change opened
COM281 after 10 attempts, COM280 after 7 and COM282 after 6. Each accepted
one 278-byte request, but all captured zero reply bytes over 15 seconds.
Another manual COM281 request at 20:50:09 also captured zero bytes; the
20:50:37 request succeeded with 453 bytes and normal EOF.

Port-open success is therefore not proof that the Linux META read handler
is ready. Delayed service readiness is a hypothesis; the log does not
identify the cause of the silence or rule out another startup/transport state.
The success occurred around 100 seconds after selector completion and about
60 seconds after initial port enumeration.

Updated the entry tool to retry only its allow-listed small read requests
after zero-byte captures. Each attempt gets a fresh token and its own raw
capture and JSON metadata. The default receive timeout is 3 seconds per
attempt, with a 250 ms pause, within a 90-second readiness window measured
from each port's first appearance (`--ready-seconds`). A validated reply
stops further attempts; nonempty invalid output stops that port for analysis.
In-flight workers may finish after another port succeeds. Open retries remain
limited to the pre-transmission stage. This behavior deliberately sends
multiple read-only requests when previous attempts receive zero bytes;
it does not resend large transfers or introduce write operations.

The new readiness loop is not yet tested. Windows has entered META twice;
automatic immediate reads have not yet succeeded. Stock 8 GB behavior must
still be measured separately. The tool cannot extend a device-side teardown
window merely by retrying requests.

## Automatic Windows selection and read succeeded — 21:07 UTC

The user's run `windows_meta_20261008T210552533451Z` completed the selector
at 21:05:59.878 UTC, discovered META ports at 21:06:39.350, and validated a
453-byte `/proc/cmdline` read on COM281 attempt 34 at 21:07:42.333.
The read reported rootfs B and normal EOF. This verifies the combined
Windows entry-and-read workflow on the working NAND unit. The log shows
about 99 seconds from selection to the successful request and 102 seconds
to validation; this is an observed timing, not a required protocol delay.

COM281's successful capture contained 1549 raw bytes, compared with 1031 in
previous clean runs. Only two matching replies were collected. The raw
capture is needed to identify the extra bytes; it has not been supplied
or analyzed locally. COM282 produced 8528013 raw bytes with decoding failure;
COM280 produced 280 invalid bytes. Their contents/roles are not established
by these log messages.

Attempts 4–33 repeatedly encountered write timeouts. The readiness-loop
implementation incorrectly retried these based only on zero received bytes.
A write timeout leaves transmission uncertain; zero receive bytes are not
proof of an unsent request. Corrected the reader to record `write_started`
and `write_completed` in metadata and the entry tool to stop the affected
port after an uncertain write. It may still retry a completed small request
that receives zero bytes. This correction may stop earlier than the
successful run did; the next step is transport/service diagnosis if so,
not assuming timeout retries were harmless or necessary.

Added `--meta-port COM281` to restrict probes to the proven interface on
this unit. Use it for the next working-unit run to avoid simultaneous probes
of other ACM functions. COM numbers must be rediscovered on another unit.
See the subsequent run below for timeout-guard behavior.

## Coalesced READY parser failure and timeout guard — 21:17–21:18 UTC

Two filtered runs failed before transmitting METAMETA. Their received chunks
combined multiple READY messages: `READYREADYREADY` and `READYREADY`.
The parser incorrectly rejected bytes remaining after the first acknowledgment.
This failure occurred before META port filtering was used and does not implicate
`--meta-port COM281`.

Fixed acknowledgment parsing to retain a shared pending buffer across handshake
stages. A matched acknowledgment is consumed; duplicate READY messages and
fragmented trailing acknowledgments are processed at the following stage.
Unexpected bytes still abort. This parser change has not been tested.

The unfiltered run `windows_meta_20261008T211754419587Z` completed selection at
21:18:01.035 UTC; META appeared at 21:18:40.532. All three ports accepted three
278-byte requests without returning bytes. Attempt 4 encountered write timeouts
and each worker stopped with `request transmission uncertain; no resend`.
This verifies the timeout guard's observed behavior, with no validated read in
this run. It does not establish whether the cause is service startup, USB
transport, or another device-side condition. No raw captures from this run have
been inspected locally. A filtered run is still needed to isolate COM281.

## Filtered healthy and bootlooped eMMC runs — 21:26–21:35 UTC

Healthy run `windows_meta_20261008T212612533774Z`: selection completed at
21:26:19.653; COM281 appeared at 21:26:59.076. Three completed requests
received no bytes, and attempt 4 stopped on write timeout at 21:27:10.513.
A manual read at 21:27:57 also timed out on write. The next manual read at
21:28:03 recovered 453 bytes with validated EOF (1031 raw bytes). Thus
COM281 alone reproduces the startup failure; simultaneous probes on other
interfaces are not necessary for it. Later usability is confirmed but its
cause remains unresolved. Duplicate READY messages were handled successfully.

Bootlooped 8 GB run `windows_meta_20261008T213403627774Z`: selection completed
at 21:34:11.824, but the COM281-filtered watcher found no matching port in
90 seconds. This does NOT establish that no META serial interface appeared:
other COM numbers were silently filtered in this version. Added logging of
filtered META ports for subsequent runs; this logging change is untested.

The supplied UART log shows `lk boot mode = 1`, slot B,
`root=/dev/mmcblk0p41 rootwait`, and execution reaching preinit. It reports
`lock: applet not found`, `netmsg: applet not found`, and
`/etc/preinit: line 18: uci: Structure needs cleaning`. These are observed
preinit/tool/filesystem errors, not proof of the exact damaged file, storage
hardware failure, or a running META service. UART echoes of id/whoami do not
prove a shell executed them. Next: repeat Windows entry without the healthy
unit's COM filter and retain USB enumeration and UART evidence together.

### User clarification: no post-selection USB on Windows

The user explicitly confirmed that the bootlooped 8 GB unit exposes no USB
device at all on Windows after META selection. This observation goes beyond
the filtered script's `ports: []`: a different COM assignment is not the
current explanation. Windows USB event captures have not been supplied for
local inspection. Preloader selection and LK mode 1 are confirmed, but Linux
USB gadget enumeration and META service readiness are not. Further COM read
retries cannot address an absent USB transport. Investigate whether preinit
reaches init/procd and the USB/META startup scripts; missing applets and the
uci filesystem error are relevant clues, not yet a proven causal chain.

## Planned bounded UART diagnostic before further recovery work

Reviewed prior explicit failsafe evidence: f was already accepted on the
8 GB unit, followed by a sustained missing-lock loop with no usable UART
shell. Repeating that alone adds little. Earlier exact p41 reconstruction
places S001restore before S30usb.init and S98meta_tst; normal preinit
completion remains unproven. Missing lock alone does not prove normal
preinit is stuck: earlier normal traces had finite lock errors.

Next user-run diagnostic: enter META as before; at the UART debug prompt
send exactly 4 followed by Enter (no f), retain the entire UART capture for
90 seconds. The inspected failsafe wait code recognizes 1–4 and writes
/tmp/debug_level. Whether this image consumes that value to expose more
logs is not established; a quiet result is inconclusive. Look for restore,
procd, USB initialization, mount-root and uci errors, and repeat boot banners.
No outcome has yet been reported. No host-side live test was run here.
