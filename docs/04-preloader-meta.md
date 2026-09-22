# Preloader META

## Key result

Preloader META is a **boot-mode selector**, not a persistent host command service.

The source-correlated transaction is:

```text
READY -> METAMETA
          |
          +-- receive 12-byte compatibility record
          +-- send ATEM0001
          +-- receive 12-byte parameter record
          +-- send ATEM0002
          +-- receive 16-byte parameter record
          +-- send ATEMATEX
          +-- receive up to 10 bytes (expected DISCONNECT)
          +-- set g_boot_mode = META_BOOT
          \-- return from selector
```

## Recognized selector tokens

| Host token | Result |
|---|---|
| `METAMETA` | collect META parameters and select META boot |
| `ADVEMETA` | select advanced META |
| `FACTFACT` | select factory boot |
| `FACTORYM` | select ATE factory boot |
| `FASTBOOT` | select fastboot boot mode |
| `AT+NBOOT` | select normal boot |

The parameter records configure META USB/modem/log fields passed forward as boot arguments. They are not arbitrary operation codes, addresses, partition names, lengths or function pointers.

## What the selector does not expose

No correlated selector branch calls:

- `blkdev_read`
- `partition_read`
- `raw_read`
- NANDX erase/write
- A/B metadata writers
- image-upload routines

Appending an undocumented command after `ATEMATEX` therefore does not expose the internal storage helpers.

## Separate download dispatcher

The familiar low-level download dispatcher is separate from the META selector. It contains memory access, SEND_DA/JUMP_DA and related commands, and belongs to the DAA-protected path already investigated.

Entering META does not transition into this dispatcher.

## FACTS

- Failed routers complete the Preloader META selector through `ATEMATEX`.
- This proves Preloader execution and the selector's USB transport.
- It does not prove LK or Linux success.
- It does not create a NAND repair channel.

## Recovery value

Preloader META remains useful for establishing boot progress and selecting boot modes. It is not itself a partition read/write service.
