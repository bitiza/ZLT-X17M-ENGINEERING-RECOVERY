# Bootlooped X17M USB enumeration findings

Date: 2026-09-17  
Scope: passive host observation only; no MTK handshake, DA, payload, flash read,
write, erase, slot operation, or device reset command was issued.

## FACTS

- The device appeared on VMware's USB bus as MediaTek vendor ID `0e8d`.
- Cycle 1:
  - `0e8d:0003`: enumeration began at kernel monotonic time `155340.952390`;
    descriptors were logged at `155341.448400`; disconnect at `155344.335975`.
  - `0e8d:2000`: enumeration began at `155346.852582`; descriptors at
    `155347.335413`; disconnect at `155348.461514`.
- Cycle 2:
  - `0e8d:0003`: enumeration began at `155384.317514`; descriptors at
    `155384.820583`; disconnect at `155385.943015`.
  - `0e8d:2000`: enumeration began at `155388.475397`; descriptors at
    `155388.983861`; disconnect at `155390.112527`.
- `0e8d:0003` supplied no manufacturer, product, or serial strings.
- `0e8d:2000` identified as manufacturer `MediaTek`, product `MT65xx
  Preloader`, with no serial string.
- Both identities exposed CDC ACM and briefly produced `/dev/ttyACM0`.
- The interval between the starts of the two observed `0003` stages was about
  43.365 seconds. The `0003` disconnect-to-`2000` enumeration gap was about
  2.52 seconds in each cycle.

Evidence directories:

- `analysis/live_usb/x17m-usb-20260917-052136/`
- `analysis/live_usb/x17m-usb-20260917-052152/`

## INFERENCES

- `0e8d:0003` is consistent with the MediaTek BootROM-facing USB stage.
- `0e8d:2000` is explicitly the preloader stage.
- The bootlooped router exposes both recovery windows without a UART
  connection or test-point intervention.
- The short dwell times explain why ordinary one-shot `lsusb` checks can miss
  both identities.

## UNRESOLVED QUESTIONS

- Whether a host handshake can hold either window open safely.
- Whether the 8 GB and smaller-capacity X17M revisions expose the same sequence.
- Whether LK offers fastboot or another USB identity after a different key/reset
  condition.

## Tool audit

- The supplied `zlt-dump/dump.py` invokes mtkclient `printgpt` with `--da`; it
  is not suitable for passive security discovery.
- Upstream mtkclient was cloned under `analysis/tools/mtkclient_upstream` for
  source inspection only at commit
  `cd25cf9c1ff6d36e82697ac2c798e69e9cfb78c3`.
- Its `gettargetconfig` command calls the full preloader initialization path,
  not merely command `0xD8`. That path includes transient register operations,
  so it was not executed during this passive phase.

## Approved minimal target-config query

After the passive stage, explicit approval was given for a non-storage security
query. `analysis/mtk_minimal_target_config.py` connected only to `0e8d:0003` and
hard-limited outbound bytes to:

```text
a0 0a 50 05 fd d8
```

The first four bytes are the MTK synchronization sequence; `fd` is
`GET_HW_CODE`; `d8` is `GET_TARGET_CONFIG`. The exchange returned:

```text
handshake reply: 5f f5 af fa
hardware raw:    09920000
hardware code:   0x0992
target config:   0x000000e5
status:          0x0000
```

Decoded target flags:

- SBC enabled
- SLA disabled
- DAA enabled
- EPP parameter bit clear
- root-certificate-required bit clear
- memory-read authentication enabled
- memory-write authentication enabled
- command `0xC8` blocked

The exact JSON result is
`analysis/live_usb/x17m-target-config-20260917-053510.json`, SHA-256
`151d668697c1455011b8909bc661bce1d39c2c46ae8d383c2158036fa05f73e1`.

The separately connected reported 1 GB unit produced the same result on
2026-09-17 06:14:13: hardware code `0x0992`, target configuration
`0x000000e5`, status `0x0000`, with identical SBC/SLA/DAA and authenticated
memory flags. Its evidence is
`analysis/live_usb/x17m-target-config-20260917-061413.json` (SHA-256
`fe0bef7ce9a1d4c4622478f0016ddd511ea1a72fd45dd6f9e5181c6e393d68a2`). No DA,
payload, memory, storage, reset, or slot command was sent.

DAA is demonstrably enabled on this X17M. This proves that the X28's open
unsigned-DA behavior cannot be assumed here. A later, explicitly approved
non-executing upload test confirmed that this particular X28 DA is rejected;
see below.

## Bundled X28 DA authentication assessment

Both bundled DA files are MTK DA v6 containers for hardware code `0x0992` and
declare 256-byte signature tails for each executable region. This means the
files retain DA signature fields; it does not prove that those signatures
remain valid after patching.

For the eMMC DA, the explicit `*** PATCHED: ACC bypass active ***` marker is at
file offset `0x2a4da`, inside region 1's declared signed-data extent
`[0x000000bc, 0x000356fc)`. Its signature tail is
`[0x000356fc, 0x000357fc)`. A content modification inside the signed extent
normally invalidates the retained signature unless it was re-signed with an
accepted key. No evidence of such re-signing is supplied.

The DA's ACC/security-policy bypass code executes only after the DA has been
accepted and launched. It therefore should not be confused with a BootROM DAA
bypass. A separate mtkclient BootROM/preloader exploit path might potentially
avoid or neutralize DAA, but that has not been tested on this X17M.

## Controlled DA authentication result (no execution)

With separate explicit approval, `analysis/mtk_da_auth_upload_nojump.py`
submitted only region 1 of the bundled X28 eMMC DA to BootROM using `SEND_DA`
(`0xD7`). The test was intentionally incapable of sending `JUMP_DA` (`0xD5`)
and issued no memory, storage, reset, or slot command.

Facts:

- BootROM accepted the `SEND_DA` header with initial status `0x0000`.
- All 218,944 stage bytes were transmitted to volatile load address
  `0x00200000`.
- BootROM returned XOR16 checksum `0x9a21`, exactly matching the locally
  calculated checksum. USB transfer integrity is therefore established.
- BootROM then returned final status `0x7017`, which the upstream MediaTek
  status table identifies as `DAA_Security_Error`.
- `JUMP_DA` was not sent, so the rejected stage was never executed.

The exact result is
`analysis/live_usb/x17m-da-auth-nojump-20260917-054232.json`, SHA-256
`e0a8ca6741bc9345e5fa1e4db33e1725a068281be475fa88dc1e3fc532fcce89`.

This is a specific negative compatibility result: the supplied patched X28 DA
does not pass this X17M's BootROM DAA check. It does not prove that no signed DA
or independently validated exploit path can work. Upstream mtkclient explicitly
lists `mt0992` in `mtkclient/config/missing_brom.txt`; its chip profile lacks the
complete known BootROM exploit parameters used by its turnkey bypass paths.

## UART status

The attached CH341 adapter appeared as `/dev/ttyUSB0` and was read at 921600
8N1 without transmitting. A 55-second capture contained only 40 bytes of
framing noise and no valid boot text. TX/RX/GND, voltage level, or signal
quality should be checked before using this capture diagnostically.
