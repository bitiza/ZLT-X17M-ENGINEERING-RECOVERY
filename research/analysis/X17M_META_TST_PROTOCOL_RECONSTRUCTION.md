# X17M `meta_tst` protocol reconstruction

Binary analyzed: `/usr/bin/meta_tst`, 219128 bytes, AArch64 PIE

SHA-256: `c66ac91fb7490037f680f68da898ba2415e476f5266e237f0fdfc1c0b0a96bc0`

All addresses below are ELF-relative virtual addresses (subtract Ghidra's `0x100000` image base).

## Confirmed file-operation primitive

The constructor at `0x0f704` calls the base module constructor with primitive ID
`0x00a3`. Its virtual handler is at `0x101b0` (`FtModFileOperation`). The reply
copies the request token and uses request primitive ID plus one, so replies use
primitive ID `0x00a4`.

The local request begins:

```text
offset  size  field
0x000   u16   token
0x002   u16   primitive_id = 0x00a3
0x004   u32   operation
0x008   ...   operation-specific data
```

The handler recognizes four operations:

| Operation | Behavior | Safety |
|---:|---|---|
| 0 | Enumerate a supplied directory, optionally filtering entry names by substring | Read-only filesystem metadata |
| 1 | Return one entry from the enumeration cached by operation 0 | Read-only |
| 2 | Write supplied peer data to a supplied path | **Write-capable; do not probe** |
| 3 | Open a supplied path with `O_RDONLY` and return its contents | Read-only at the `open(2)` level; some special device nodes may still block or have read side effects |

## Arbitrary-path behavior is confirmed

Operation 3 passes the NUL-terminated string at request offset `0x008` directly
to `open(path, O_RDONLY)` at `0x0ff30`. There is no path whitelist or prefix
validation in this executable. Successful reads are emitted in peer-data blocks
of at most `0x5000` bytes until EOF.

This proves that regular files such as `/proc/cmdline` and `/proc/mtd` are
reachable through this primitive, subject to process permissions and namespace.
It also means Linux-visible block/MTD paths may be accepted, but reading those
has not been live-tested and should not be the first protocol test.

Operation 2 is equally unrestricted and opens the supplied path with either
`O_RDWR|O_CREAT|O_TRUNC` (`0x242`) for a start block or `O_RDWR|O_APPEND`
(`0x402`) for a continuation block. It then calls `write(2)`. A malformed or
misidentified operation can therefore be destructive.

## Operation 3 reply block

The reply's local data is `0x114` bytes. Fields established by the code are:

```text
offset  size  field
0x000   u16   request token
0x002   u16   0x00a4
0x004   u32   operation = 3
0x008   u32   byte offset/cumulative byte count
0x00c   u8    block flags
0x110   u8    status (zeroed on the normal path)
```

Observed flag bits:

```text
bit 0 (0x01)  start-of-file / initial block
bit 1 (0x02)  data block (`BLK_WRITE` in vendor logging)
bit 2 (0x04)  end-of-file (`BLK_EOF`) or read failure
```

Non-empty peer data begins with an eight-byte, zero-initialized
`peer_buff_struct` header. File bytes follow that header, so an outer peer
length of `N + 8` represents `N` bytes read from the file. The byte offset in
the local reply counts only file bytes, not this transport header.

The code emits a final EOF reply with no peer bytes after a normal zero-length
`read(2)`. It retains the data bit from the preceding block and ORs in the EOF
bit, so the observed normal final flags are `0x06`, not `0x04`.

The first controlled live read of `/proc/cmdline` confirmed this layout:

```text
data reply: peer length 461 = 8-byte peer header + 453 file bytes; flags 0x03
EOF reply:  offset 453, peer length 0; flags 0x06
capture:    1031 bytes, SHA-256 ad08b3954d49ba75111559cc750be61007b3c419492d841e45aeccf23e3aed60
```

## Outer USB/RS232 envelope

The decoded logical envelope is:

```text
offset  size  field
0x00    u8    sync = 0x55
0x01    u16   big-endian frame length
0x03    u8    frame type
0x04    u16   little-endian local length
0x06    u16   little-endian peer length
0x08    ...   local data followed by peer data
end     u8    XOR checksum of all preceding decoded frame bytes
```

For frames emitted by `FTMuxPrimitiveData` at `0x17824`, frame length is
`local_len + peer_len + 5`, and the emitted frame type is `0x60`. Incoming
AP-injected frames are selected by type `0x66` in the parser at `0x165c0`.

The incoming parser treats `0x5a` as an escape marker: `5a 01` decodes to
`0x55`, and `5a 5a` decodes to `0x5a`. The outgoing encoder at `0x17824` is
directionally asymmetric: it escapes `0xa5` as `5a 01` and `0x5a` as `5a 5a`.
This asymmetry is present in the machine code and must be preserved rather than
"corrected" speculatively.

## Safest progression

1. Capture COM262 without transmitting and confirm whether the target sends an
   unsolicited frame.
2. Implement an offline decoder for both directional escape rules and validate
   it against any captured target bytes.
3. Only then build a single operation-3 request for `/proc/cmdline` (or
   `/proc/mtd`). Verify every decoded field, total length, primitive ID, operation,
   and XOR checksum before allowing a serial write.
4. Keep operation 2 absent from any host utility. Do not test block or MTD nodes
   until regular-file reads and complete EOF handling are proven.

No bytes were transmitted to COM262 during this analysis.

## Offline request builder

`analysis/meta_tst_frame_decoder.py` now has a single-purpose `--build-read`
mode. It has no serial-port code and exposes no generic operation selector.
Operation 3 is compiled into the builder; verification explicitly rejects
operation 2 and every operation other than 3.

```sh
python3 analysis/meta_tst_frame_decoder.py --build-read /proc/cmdline
```

For `/proc/cmdline` with token 1, the verified fields are:

```text
frame type      0x66
primitive ID    0x00a3
operation       3
local length    269 (0x10d)
peer length     0
frame length    274 (0x112)
XOR checksum    0xe7
```

The `0x10d`-byte local request consists of the 8-byte META request header,
the 256-byte NUL-terminated path field, a zeroed 4-byte file-size field, and a
zeroed 1-byte block-stage field. The tool prints logical and wire-escaped hex,
decodes the wire bytes using host-to-target escape rules, and aborts unless all
fields, padding, lengths, path termination, operation, and checksum match.

## Additional live read tests (2026-10-08)

The user ran the safe reader from Windows against a working 1 GB NAND X17M in
Linux META mode. The confirmed serial port was `COM281` (the gadget exposed
multiple ACM COM ports; `COM280` and `COM282` were not successful test ports).
No write operation was sent.

* `/proc/cmdline`: PASS. One operation-3 request returned a valid data frame
  containing 453 bytes, followed by a valid EOF frame. The response identified
  `bootslot=b` and `root=/dev/mtdblock42` at that test boot. Raw capture:
  `meta_tst_proc_cmdline_20261008T195600Z.bin`.
* `/proc/mtd`: PASS. One operation-3 request returned a valid data frame
  containing 1,861 bytes, followed by a valid EOF frame. The table identifies
  `mtd29` as `rootfs_a`, `mtd42` as `rootfs_b`, and `mtd51` as the 512 KiB
  `pmt` partition. Raw capture: `meta_tst_proc_mtd_20261008T195857Z.bin`.
* COM280 returned 281 bytes that failed frame checksum validation; COM282
  returned no data. These outcomes establish only that COM281 completed the
  validated exchanges, not why the other ports failed.

This confirms end-to-end Linux META request/reply handling for two regular
procfs files, including EOF validation. It does not yet demonstrate raw flash
transfer, access to the 8 GB eMMC device, or any ability to modify the target.
The next bounded test is the reader's allowlisted `/dev/mtd51` read (512 KiB),
which also validates multi-frame binary transfer and compares the result to
the reader's pre-recorded size and SHA-256. Keep its generated
`mtd51_meta.img` and the raw response capture as evidence. Do not treat a
matching 1 GB NAND test as proof that the bootlooped eMMC unit exposes the same
paths or META service.

### `/dev/mtd51` partial transfer result (2026-10-08)

The user ran the allowlisted raw read on `COM281`. The tool transmitted the
verified 278-byte operation-3 request once. It validated the first response:
offset 0, peer length 20,488 (8-byte peer header plus 20,480 file bytes),
flags `0x03`. It then aborted at raw capture offset 20,773 because the next
frame failed checksum validation (`calculated f3, received ff`). The capture
contains 45,056 raw bytes and is saved on the Windows host as
`meta_tst_dev_mtd51_20261008T200024Z.bin`.

Status: **partial only; no EOF, no complete 512 KiB image, and no validated
SHA-256**. The utility aborts before creating `mtd51_meta.img`. Preserve the
raw capture and inspect the failing frame/escape handling before retrying the
raw-device read or expanding the test to any larger partition. The successful
procfs reads remain fully validated and unaffected.

The supplied capture was inspected locally. Its SHA-256 is
`7d034f900c197605f62f2d33927a8f9987715c3a001cb8b84adc31d0318a1076`.
Offline replay reproduces the same failure. Frame 0 is valid, including its
XOR checksum (`0x7b`), and reports offset 0 with 20,480 file bytes. Frame 1
starts at raw offset 20,773 and has a structurally plausible reply header for
offset 20,480, flags `0x02`, and peer length 20,488, but its checksum is
`0xff` while the XOR over the advertised frame is `0xf3`. The capture contains
a frame-shaped sequence at raw offset 40,522 whose local reply offset is
40,960, 1,024 raw bytes before the prior frame's advertised end at 41,546.
Because the file payload can contain unescaped `0x55` bytes, that sequence
alone does not prove a frame boundary; it does show why the capture needs
careful framing analysis. The robust conclusion remains that the second frame
is not validated and no complete image can be reconstructed from this run.

### Next isolation read prepared

To distinguish a raw-MTD-specific issue from generic multi-frame transfer,
`analysis/meta_tst_safe_read.py` now has one additional fixed, read-only
allowlist target: `/usr/bin/meta_tst`, capped at its known 219,128-byte size.
It writes the recovered file only after receiving a valid complete EOF and
exact size; the resulting SHA-256 can be compared with the known image copies.
Offline preflight passes 17/17 checks. The live test has not yet been run with
this updated script. Use an extended timeout because the file spans many
20 KiB frames.

The user subsequently ran this test on `COM281` with a 120-second timeout.
The request was transmitted once, but the first accepted response had file
offset 102,400 when offset 0 was expected. The reader safely aborted after
capturing 32,768 raw bytes. The capture is saved on Windows as
`meta_tst_usr_bin_meta_tst_20261008T200741Z.bin`. No complete file, EOF, or
SHA-256 was validated, and `meta_tst_binary.bin` was not produced. This is
not a validated response to the `/usr/bin/meta_tst` request.

The user supplied the capture and offline decoding reproduced the abort. Its
SHA-256 is
`7d66d253723d5171290b36701a35fbd8e605810ec84f4ffb132d22ec6155634d`. It has
10,533 leading `0xff` bytes, then a valid META reply frame at raw offset 10,533
with operation 3 and file offset 102,400; a second, incomplete frame begins at
raw offset 31,306 and reports offset 122,880. These sequential offsets and the
erased-flash-looking `0xff` stream strongly indicate that COM281 delivered a
tail of the earlier `/dev/mtd51` response after that test aborted, rather
than the new regular-file response. This is strong evidence of stale/queued
META output or a sender left blocked mid-transfer, but does not prove exactly
where it was buffered. No bytes from `/usr/bin/meta_tst` were validated, and
the router received only the read request; no device write was performed.

Before any further request, clear this stale transfer state (for example,
reboot the working unit and re-enter Linux META), then verify a fresh small
`/proc/cmdline` read on COM281. Do not start another large read until the
channel is synchronized and a response begins at offset 0.

### Follow-up after META reboot and large-file retry (2026-10-08)

The user rebooted/re-entered META and ran `/proc/cmdline`. The first attempt
captured 518 bytes but no validated EOF; the next attempt passed with a
453-byte file response and EOF. The following `/usr/bin/meta_tst` read began
at offset 0 and validated its first 20,480-byte data block, but the next
frame failed checksum (`calculated 04, received f9`) at raw offset 20,795.
Raw capture: `meta_tst_usr_bin_meta_tst_20261008T201655Z.bin` (45,056 bytes).

After that abort, immediate `/proc/cmdline` attempts failed checksum, then
one received a valid reply at offset 163,840 instead of 0. This offset is
consistent with a later chunk of the still-running `/usr/bin/meta_tst` read.
Two subsequent `/proc/cmdline` attempts then passed at offset 0 with valid
EOF. Together, these results strongly support that closing the host COM port
after a client-side validation abort does not stop the device-side META file
transfer; later requests can first receive leftover response frames. The
small reads succeeding after the tail drained indicate the channel recovered.

The large read itself remains incomplete, and the second-frame checksum
failure still needs raw-capture analysis. Preserve and inspect the 20:16:55
capture before retrying the large read. For future runs, do not issue another
META request after an abort until the outstanding stream has been drained or
the device has been rebooted/re-entered into META.

The supplied 20:16:55 capture was inspected locally. SHA-256:
`ad34fdbcdf055a3feeba11d9d7c7065c720f1ce6c98a69ebdb46d6f4732220d8`.
Offline replay confirms frame 0 is valid at offset 0 with 20,480 file bytes.
Frame 1 starts at raw offset 20,795 and advertises offset 20,480 plus a
20,488-byte peer buffer, but its checksum is `0xf9` instead of calculated
`0x04`. A frame-shaped sequence at raw offset 40,554 reports offset 40,960;
this is 1,024 raw bytes before frame 1's advertised end at 41,578. The
`/dev/mtd51` capture showed the same 1,024-byte discrepancy (third-frame-like
header at 40,522 versus advertised end 41,546). These two independent binary
reads therefore show a repeatable 1,024-byte loss/truncation pattern around
the second data frame, although the partial third frames prevent checksum
validation of those headers as complete frames. This is not fixed by choosing
a different 5a-escape decode value. Treat multi-frame binary reads as
unreliable until the USB/TTY sender or host receive path is isolated.

Further byte comparison against the local `rootfs.original/usr/bin/meta_tst`
shows the second block is not merely a parser-escape mismatch. After decoding
the target escape sequences, the captured 19,456 file bytes equal the expected
20,480-byte block with exactly 1,024 bytes omitted at block-relative offsets
11,995 through 13,018 (file offsets 32,475 through 33,498). The stream then
contains a frame-shaped response at offset 40,960. Reconstructing the intended
full second frame from the local file yields XOR checksum `0xa5`, which equals
the final checksum byte at the captured truncated frame boundary. Thus the
source-side frame checksum corresponds to the complete intended data, while
1,024 payload bytes are missing in the captured stream. This locates the fault
after frame construction, somewhere in the device TTY write/USB path or the
host USB/COM receive path; this capture alone cannot distinguish those sides.
## Sender disassembly follow-up (2026-10-08)

See [X17M_META_TST_READ_SENDER_ANALYSIS.md](X17M_META_TST_READ_SENDER_ANALYSIS.md)
for the exact original-binary hash, instruction addresses and selected
disassembly. Operation 3 streams the entire file in fixed 20480-byte reads
without host acknowledgments. The UsbPort writer correctly retries positive
short writes, but send errors are not propagated through the frame encoder
and file-read loop. This does not yet locate the observed 1024-byte stream
loss. Continuous host capture and USB-level comparison are the next useful
diagnostics; an acknowledgment packet is not required by this read handler.

