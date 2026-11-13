# META file read and sender disassembly — 2026-10-08

## Scope and identity

Local static analysis of `rootfs.original/usr/bin/meta_tst`, AArch64 ELF,
219128 bytes, SHA256
`1dcb212082889f5332792d0a48a828079fcd65e6fdf569aafeb8b2d92fe62c37`.
Addresses below are ELF virtual addresses, not runtime PIE addresses.
Selected instructions are saved in `meta_tst_read_sender_disassembly.txt`.
Indirect calls were resolved using ELF relocations and C++ virtual tables.
No router commands or live requests were sent during this analysis.

## What operation 3 expects

The handler at `0x103a0` passes request path at local offset 8 and a response
structure to the file-read function at `0xff30` (GOT `0x440b8`). It does not
pass a requested byte count, starting offset, or chunk size.

`0xff6c–0xff7c` calls `open(path, 0)` (`O_RDONLY`). It allocates a fixed
`0x5000` (20480-byte) buffer and calls `read(fd, buffer, 0x5000)` at
`0x1001c–0x1002c`. Each positive read is immediately sent as a response
(`0x10100–0x1011c`); the byte offset advances by the file read count.
It clears the start flag and loops directly back to `read()` at `0x10158`.
Zero bytes read causes the EOF response at `0x10068–0x1008c`.

**There is no per-block acknowledgment, host credit, or retransmission in
this operation.** One request starts a whole-file stream. Request size/stage
fields cannot be assumed to limit this read; the traced operation does not
use them. Closing the host COM port is not a protocol cancellation command.

Conceptual reconstruction (not original source):

```c
fd = open(path, O_RDONLY);
offset = 0;
flags = START;
while ((n = read(fd, buffer, 20480)) > 0) {
    flags |= DATA;
    reply.offset = offset;
    send_reply(reply, buffer, n);  // result not checked here
    offset += n;
    flags &= ~START;
}
// Normal n == 0 path sends final offset with EOF; errors have a separate path.
```

## USB transport and short writes

The PC transport instance is created using `/dev/ttyGS0` at `0x174c4`.
Its constructor at `0x15098` selects the UsbPort virtual table: type
information at `0x436e8` names `UsbPort`, and the write entry at `0x43860`
points to `0x13b08`. That wrapper invokes the shared writer `0xc528`
through GOT `0x440c8`.

The shared writer takes a mutex and repeatedly calls imported `write()`:

- `0xc580–0xc58c`: write the remaining bytes.
- `0xc610`: subtract the actual returned count from the remaining count.
- `0xc614`: advance the buffer pointer by that actual count.
- `0xc620`: continue until all bytes are accepted.
- A negative result logs the error, unlocks, and returns an error.
- A zero result makes no progress and repeats; this is a potential stall.
- This writer does not retry `EINTR`/`EAGAIN` explicitly. A different CCCI
  writer at `0x138e8` does retry `EAGAIN`; it is not this UsbPort entry.

**Positive short writes are handled correctly.** The claim that this
binary simply discards every short-write tail is not supported.

## Send failures are not propagated

`FTMuxPrimitiveData` at `0x17824` constructs the complete frame, calculates
the XOR checksum and applies the target-direction escapes. At `0x17a34–0x17a4c`
it invokes the transport writer. The returned value is not compared with the
frame length or used to retry the frame; the buffers are subsequently freed.
The wrapper at `0x17be4–0x17c08` returns success after the encoder call, and
the file-read loop likewise ignores the send result.

Therefore an error after part of a frame has been accepted can leave an
incomplete frame followed by later responses. That is a real robustness
weakness, but **it does not establish the cause of the observed 1024-byte
deletion in the middle of a frame whose trailing checksum was received**.
Kernel USB/gadget loss and host USB/serial receive loss remain candidates.

## Serial settings

The serial setup at `0x14664` configures raw-like input/output settings and
sets both speeds to `0x1007` (Linux termios `B921600`). It clears input
software flow-control bits `IXON`, `IXOFF`, and `IXANY` via the mask at
`0x14704–0x14714`. It sets `CS8`, `CREAD`, and `CLOCAL`.
The cflag mask does not explicitly clear inherited `CRTSCTS`, so the code
alone is not proof of its runtime hardware-flow-control state.

921600 is the device-side line coding setting; its presence does not prove
that changing the Windows baud setting will fix USB ACM data loss. The
existing 115200 host configuration already completed small reads.

## Consequences for the captured failures

The successful small reads show that the request format is accepted. Missing
host acknowledgments do not explain the large-read failures: this handler
does not wait for any. The nonzero starting offsets on subsequent requests
are consistent with continued output from an earlier whole-file stream.
Reusing token 1 across requests makes that old output harder to distinguish.

Next useful work is a host capture path that reads continuously into a larger
receive buffer, parses separately, and continues preserving/draining raw
output after a validation error. Keep checksum/offset validation strict and
use a distinct token per request. Compare its capture with USB traffic to
locate the loss. These are proposed changes, not implemented or verified here.
Do not treat an incomplete or checksum-invalid capture as a flash backup.

These results concern the local healthy NAND firmware. They do not establish
that the bootlooped 8 GB unit starts this service or accepts the same request
before its META interface disappears.

## Host reader update

Updated `meta_tst_safe_read.py` to capture before parsing, request a 1 MiB
Windows receive buffer where supported, and read in batches up to 65536 bytes.
It captures until three seconds of receive silence, the selected timeout,
or a 16 MiB capture bound. A decoding error therefore cannot stop reception
mid-transfer. A timeout or size bound can still interrupt an ongoing stream.
The device receives exactly one read request, with a random nonzero 16-bit
token in live mode. The raw capture has a JSON sidecar recording that token.
Offline decoding defaults to the historic token 1; use `--token` to match a
new capture. Checksum, offset, size and EOF validation remain mandatory.

This update has not been run against hardware or tested locally. First use
a fresh META session and read `/proc/cmdline`; then read `/usr/bin/meta_tst`
with `--timeout 120`. Preserve both `.bin` and `.bin.json` files if it fails.
This change is diagnostic and is not yet a verified fix for the data loss.

## Successful live transfer with updated reader — 20:33 UTC

The user ran the updated reader on Windows COM281 and supplied the captures
under `analysis/meta_tst_reads/`.

- `/proc/cmdline`, token `0xc9bd`: 1031 raw bytes, 453 recovered bytes,
  data response and validated EOF.
- `/usr/bin/meta_tst`, token `0x4858`: 222777 raw bytes, 219128 recovered
  bytes, 11 contiguous data responses and validated EOF (12 replies total).
  Ten data chunks contain 20480 bytes each, the last contains 14328 bytes.
- The Windows receive-buffer request was 1048576 bytes. Both captures
  ended after three seconds of receive silence, not the timeout.
- Local SHA256 comparison of the supplied `meta_tst_binary.bin` and
  `rootfs.original/usr/bin/meta_tst` confirms both equal
  `1dcb212082889f5332792d0a48a828079fcd65e6fdf569aafeb8b2d92fe62c37`.

This verifies a complete, byte-identical binary transfer on the healthy
NAND unit using the revised host reader. It strongly implicates the earlier
host reception/capture behavior, but buffer size, capture-before-parsing,
read batch size and token handling changed together, so the individual
cause has not been isolated. No target-side protocol acknowledgment was
added or required. This is one successful large-file run, not evidence that
the 8 GB unit's early META window is usable or that flash writes work.

Next read-only experiment: repeat the 512 KiB `/dev/mtd51` transfer on this
same healthy unit and compare the expected digest. Its MTD numbering must
not be carried over to the 8 GB device.

## Successful partition transfer — 20:35 UTC

The next Windows COM281 run read `/dev/mtd51` with token `0x41ef`.
The user supplied the raw capture, JSON metadata and recovered image under
`analysis/meta_tst_reads/`.

- Raw capture: `meta_tst_dev_mtd51_20261008T203546Z.bin`, 532191 bytes.
- Recovered image: `mtd51_meta.img`, exactly 524288 bytes (512 KiB).
- 25 data replies of 20480 bytes, one data reply of 12288 bytes, then EOF
  at offset 524288: 27 validated replies total.
- The script reported valid checksums, contiguous offsets, normal EOF and
  the expected SHA256. Local hashing independently confirms image SHA256
  `0449e9b33269c7cd3a956b490b295a9482b852265a521aeb29d1ff2e9377960c`.
- Receive buffer request: 1 MiB; capture ended on three seconds of silence.

This establishes complete, digest-matching raw MTD partition reading over
Linux META on the healthy NAND device. It does not test NAND OOB capture,
bad-block restoration, writes, command execution, or the 8 GB eMMC unit.
The earlier large-read failures are no longer reproduced by these two
successful revised-reader transfers; their precise cause remains unisolated.

Recovery work should now establish whether the bootlooped 8 GB unit's stock
Linux META service can answer a small read before USB teardown. Identify its
current ports and capture `/proc/cmdline` first; establish its own storage
layout before requesting any raw device. The patched healthy firmware's
stable META session cannot be assumed to exist on the bootlooped firmware.
