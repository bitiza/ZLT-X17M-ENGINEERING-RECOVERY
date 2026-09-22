# Boot chain overview

## NAND X17M path

```text
BootROM
  -> Preloader
  -> LK
  -> Linux kernel
  -> SquashFS rootfs
  -> JFFS2 overlay
  -> vendor userspace
```

The NAND X17M uses an A/B image layout on raw NAND/MTD. BootROM, Preloader, LK, Linux, and Linux META expose different interfaces and must be treated as separate recovery layers.

## Why layer separation matters

A device can complete the BootROM handshake but fail DA authorization; complete Preloader META selection but fail before Linux; reach LK while exposing only diagnostic fastboot; or boot Linux far enough for USB META while normal networking is broken.

| Layer | Known host surface | Current recovery value |
|---|---|---|
| BootROM | handshake, SEND_AUTH, SEND_DA | DAA protected |
| Preloader | META selector, download dispatcher | mode selection; download path protected |
| LK | AEE/MRDUMP/limited fastboot | investigation ongoing |
| Linux | shell/network services | useful when userspace boots |
| Linux META | CDC ACM + meta_tst | powerful on sufficiently healthy boots |

## FACTS

- Preloader META and the BootROM/download command path are different dispatchers.
- The Preloader META selector returns into the normal authenticated boot path.
- Linux META is implemented later and depends on Linux/userspace progress.

## UNRESOLVED

- Whether the exact LK build exposes useful META-specific recovery functionality not yet mapped.
