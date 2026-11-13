# X17M DA authentication-only test

Date: 2026-09-17  
Device: bootlooped X17M used for the preceding `0e8d:0003` security query  
Scope: volatile stage transfer only; no execution and no storage operation

## FACTS

- BootROM hardware code: `0x0992`.
- Target configuration: `0x000000e5` (SBC and DAA enabled; SLA disabled;
  memory-read and memory-write authentication enabled).
- Candidate: `zlt-dump/lib/da/DA_BR_acc_bypass_emmc.bin`, SHA-256
  `90250ef6ae3ce671d810a30ec0b8f5f4e708def678a5e9a4baa2756f9bbac0a6`.
- Region 1: file offset `0xbc`, 218,944 bytes, volatile load address
  `0x00200000`, SHA-256
  `e7421ad34ed26a131e8b83ff463ca42b5b671e75ef90de263446f04d9990a54a`.
- `SEND_DA` initial status: `0x0000`.
- Bytes transmitted: 218,944.
- Expected and returned XOR16 checksum: `0x9a21`.
- Final BootROM status: `0x7017` (`DAA_Security_Error`).
- `JUMP_DA` was not sent; the DA did not execute.
- No memory, storage, reset, flash, erase, format, repair, or slot command was
  sent.

Evidence: `analysis/live_usb/x17m-da-auth-nojump-20260917-054232.json`, SHA-256
`e0a8ca6741bc9345e5fa1e4db33e1725a068281be475fa88dc1e3fc532fcce89`.

## INFERENCE

The exact checksum match rules out an incomplete/corrupt USB transfer. The
candidate X28 DA reached BootROM intact and was rejected by the DAA gate before
execution. Its embedded ACC-bypass patch cannot help at this point because
that code would run only after authentication and a subsequent jump.

## UNRESOLVED QUESTIONS

- Whether an OEM-authenticated DA can be located.
- Whether the preloader stage reports the same security configuration or
  supports a separately validated, non-storage diagnostic route.
- Whether the smaller-capacity X17M uses the same hardware code and policy.
- Whether a new 0x0992-specific method exists; the preserved upstream
  mtkclient revision lists `mt0992` as missing a complete BootROM profile.
