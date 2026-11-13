# X17M 20250327 Preloader selector parser

Static-only analysis of `zlt x17m dumps/mmcblk0boot0.bin`. No target
communication or binary modification was performed.

## Executive result

The selector dispatcher is **CONFIRMED** at runtime `0x002188f0` through
`0x00218c70`. It does not use flat string references. It loads signed
image-relative offsets from literal pools, adds the Thumb PC, computes the
candidate string address, obtains the candidate length, and compares it with
an input descriptor.

The dispatcher receives:

```text
r1 -> input descriptor: [r1] = input pointer, [r1+4] = input length
r2 -> context containing a callback/object at [r2+8]
r0 -> object containing a function pointer at [r0+4]
```

The exact callers that prepare this descriptor, and the function that emits
`READY`, remain unresolved. Consequently the observed `READY -> METAMETA ->
READY` sequence cannot yet be assigned uniquely to rejection, restart, or a
successful intermediate state.

## PC-relative selector recovery

For PC-relative literal loads, Thumb uses `Align(current_instruction+4,4)`.
For the 16-bit register form `ADD reg,PC` used here, the effective PC is
`current_instruction+4` (without the literal-load alignment step). The
following are direct, instruction-backed constructions; the literal value is an
image-relative offset and the result is the runtime address.

| instruction | literal address/value | PC used | computed object |
|---|---|---:|---|
| `0x21892e: ldr r7,[pc,#...]`; `0x218930: add r7,pc` | `0x218c80 = 0x184cd` | `0x218934` | `0x230e01` `AT+NBOOT` |
| `0x218956: ldr sb,[pc,#...]`; `0x21895a: add sb,pc` | `0x218c88 = 0x184ac` | `0x21895e` | `0x230e0a` `AT+OK` |
| `0x218972: ldr r5,[pc,#...]`; `0x218974: add r5,pc` | `0x218c94 = 0x18498` | `0x218978` | `0x230e10` `AT+UNKONWN` |
| `0x218984: ldr sl,[pc,#...]`; `0x218988: add sl,pc` | `0x218c98 = 0x1848f` | `0x21898c` | `0x230e1b` `METAMETA` |
| `0x218a10: ldr r2,[pc,#...]`; `0x218a14: add r2,pc` | `0x218cac = 0x1841e` | `0x218a18` | `0x230e36` `ATEM0001` |
| `0x218abe: ldr r7,[pc,#...]`; `0x218ac4: add r7,pc` | `0x218cc8 = 0x183bb` | `0x218ac8` | `0x230e83` `ATEMATEX` |
| `0x218ae0: ldr sl,[pc,#...]`; `0x218ae8: add sl,pc` | `0x218ccc = 0x183a0` | `0x218aec` | `0x230e8c` `FACTFACT` |
| `0x218b40: ldr sl,[pc,#...]`; `0x218b48: add sl,pc` | `0x218cd8 = 0x18352` | `0x218b4c` | `0x230e9e` `ADVEMETA` |
| `0x218b6e: ldr r7,[pc,#...]`; `0x218b74: add r7,pc` | `0x218ce0 = 0x1832f` | `0x218b78` | `0x230ea7` `ATEMEVDX` |
| `0x218b90: ldr sl,[pc,#...]`; `0x218b98: add sl,pc` | `0x218ce4 = 0x18314` | `0x218b9c` | `0x230eb0` `FACTORYM` |
| `0x218bee: ldr r7,[pc,#...]`; `0x218bf4: add r7,pc` | `0x218cf0 = 0x182ca` | `0x218bf8` | `0x230ec2` `FASTBOOT` |
| `0x218c4e: ldr r4,[pc,#...]`; `0x218c50: add r4,pc` | `0x218d0c = 0x182b5` | `0x218c54` | `0x230f09` `METAFORB` |

These are genuine uses, not merely algebraic matches: each resulting pointer
is passed to `strlen` (`0x2276f8`), to the comparison helper (`0x227722`), or
to a callback after a successful branch.

`READY` at runtime `0x2306c0` was not found in this dispatcher. Its producer
is therefore a separate caller/transport path and remains **UNKNOWN**.

## Comparison helpers

`0x002276f8` is **CONFIRMED** `strlen`:

```text
r0 = string
while ([r0] != 0) r0++
return r0 - original_string
```

`0x00227722` is **CONFIRMED** a bounded byte comparison equivalent to a
`strncmp`-style routine. The caller supplies input pointer in `r0`, selector
pointer in `r1`, and a byte count in `r2`; it returns zero on equality.

Each selector case first computes `strlen(selector)`, compares that length
with `[input_descriptor+4]`, and passes the smaller length to `0x227722`.
Thus the dispatcher compares a common prefix rather than independently
proving equal lengths. The exact descriptor producer must be recovered before
claiming whether the transport layer always supplies exact lengths.

## Dispatcher structure

The first selector comparisons are:

```text
0x21892e..0x218924  AT+NBOOT, compare at 0x218924
0x218956..0x21894c  AT+OK,    compare at 0x21894c
0x218972..0x218964  AT+UNKONWN, compare at 0x2189a4 path
0x218984..0x2189a4  METAMETA, compare at 0x2189a4
```

The exact control-flow labels are compiler-generated and interleave several
subsequent cases, but the comparison result is tested with `CBNZ` at:

```text
0x21892c, 0x218954, 0x218982, 0x2189ac,
0x218b08, 0x218b68, 0x218bb8, 0x218c14
```

The later cases are similarly direct:

```text
ATEMATEX  0x218ac4 / comparison preceding 0x218ad0
FACTFACT  0x218ae8 / comparison preceding 0x218b04
ADVEMETA  0x218b48 / comparison preceding 0x218b64
ATEMEVDX  0x218b74 / comparison preceding 0x218bb4
FACTORYM  0x218b98 / comparison preceding 0x218c10
FASTBOOT  0x218bf4 / comparison preceding 0x218c10
```

## METAMETA path

The equality path is **CONFIRMED** to begin at `0x2189ac` (comparison result
zero) and continue through `0x218a6a`.

Instruction-backed effects include:

```text
0x2189b0..0x2189c8  zero 12-byte and 16-byte stack structures
0x2189cc..0x2189e2  access a context/global object and update two bytes at
                     a structure-relative offset 0x608f8/0x608f9
0x2189f6            indirect call through [r4+4], arguments include
                     stack buffer, length 12, timeout/value 0x7d0
0x218a14            construct 0x230e36 = ATEM0001
0x218a1a            strlen(ATEM0001)
0x218a24            indirect call through [r7] with ATEM0001 and its length
0x218a42/0x218a4e   construct and log md_type[0] / md_type[1] strings
0x218a72            continue into the next state/case block
```

This proves that METAMETA performs state/context setup and invokes an
indirect callback with `ATEM0001`. It does **not** yet prove that the callback
is USB transmit, UART transmit, or a log sink; that depends on the unresolved
object/vtable construction. No direct `seclib_brom_meta_mode` reference was
identified in this path.

## METAFORB and rejection behavior

`METAFORB` is not a normal comparison case in this function. At
`0x218c4c..0x218c5c`, the dispatcher constructs `0x230f09`, computes its
length, and passes it to the indirect callback. The same block then constructs
the diagnostic strings around `0x230ef6`/`0x230eed` and calls the formatter at
`0x2249b4`.

This is **STRONGLY SUPPORTED** as a forbidden/rejection response path. It is
not evidence that the host should send the literal `METAFORB` selector.

## READY / transport status

The dispatcher itself contains no proven construction of `READY` at
`0x2306c0`, no direct USB CDC register access, and no direct UART register
access. Its transport operations are indirect through function pointers:

```text
[r0+4] and [r2+8] are loaded as callback/object tables
[r4] / [r4+4] and related registers are invoked with selector buffers,
lengths, and state structures
```

Therefore:

- selector comparison and state machine: **CONFIRMED**;
- callback identity (USB, UART, logging, or META service): **UNKNOWN**;
- READY transmission point: **UNKNOWN**;
- receive buffer allocation and exact upstream transport read length:
  **UNKNOWN**;
- timeout/retry around READY: **UNKNOWN**;
- USB and UART sharing this parser: **UNKNOWN**;
- `seclib_brom_meta_mode` participation: **UNKNOWN**;
- eMMC/storage access from this path: **UNKNOWN**.

## Current interpretation of READY → METAMETA → READY

The static evidence now proves that a METAMETA input can enter a real
METAMETA equality path and cause state setup plus an indirect `ATEM0001`
callback. It does not prove that a second READY is rejection. The second READY
could still be produced by:

1. a caller-level parser restart after the callback returns;
2. a transport reinitialization;
3. a policy failure in an indirect callback;
4. a separate enumeration/stage using the same string; or
5. an input-length/prefix mismatch before this function is reached.

The smallest unresolved object is the caller that constructs the `r1` input
descriptor and the vtable/object behind `[r0+4]`/`[r2+8]`. Recovering that
object construction is required to identify READY emission and distinguish a
successful intermediate META transition from a restart.

## Follow-up negative results

Additional static scans were performed for the exact runtime address
`0x2306c0` (`READY`):

- no literal `LDR` directly loads `0x2306c0`;
- no nearby `LDR` + `ADD reg,PC` pair in the executable image resolves to it;
- no `MOVW/MOVT` pair materializes it;
- no direct branch to `0x2188f0` was found in the Thumb image.

These negatives are useful constraints, not proof that READY is unused. They
indicate that READY is probably reached through an indirect callback, a
descriptor/table lookup, or a separate parser/transport function. The next
smallest static target is therefore the object/table construction feeding the
indirect calls at `0x218966`, `0x218a24`, `0x218ad0`, `0x218b36`, and
`0x218be4`.

## Callback-resolution follow-up

The dispatcher loads callback-bearing objects rather than calling fixed
transport routines:

```text
0x2188fc  r7 = [r0 + 4]
0x218900  r4 = [r2 + 8]
0x218950  r4 = [r4]
0x218966  blx r4
0x218a24  blx r7
0x218ad0  blx sb
0x218b36  blx r7
0x218be4  blx r7
```

The image contains no direct `BL`/`BLX immediate` caller of `0x2188f0` and no
plain absolute pointer to that function. This is **CONFIRMED** evidence that
the dispatcher is registered or reached through an indirect table outside the
ordinary direct-call graph. The callback identity therefore cannot be safely
named USB, UART, or logging from this image alone.

The most specific unresolved object is now:

```text
caller-supplied r0 object -> [r0+4]
caller-supplied r2 object -> [r2+8] -> [0] / [4]
```

Resolving it requires finding the registration site or a complete relocation-
aware data-reference analysis of the object table; guessing a transport from
the indirect-call shape would be **UNKNOWN**, not a conclusion.

## Concrete receive helper

Function `0x00218888` is a directly evidenced receive-side helper and is
called from selector handling at `0x218ad4` and `0x218b84`.

Instruction-backed behavior:

```text
0x21888e  r4 = sp + 4
0x218894  r0 = r4; r1 = 0; r2 = 10
0x218896  bl 0x227748          // clear ten-byte receive buffer
0x2188a2  r3 = [r5]
0x2188a4  r0 = r4; r1 = 10; r2 = 0x3e8
0x2188ac  blx r3               // receive(buffer, 10, 1000)
0x2188ae  uxtb r5, r0          // status/result byte
0x2188b0  cbz r5, 0x2188b8
```

The nonzero-result path formats/logs the disconnect diagnostic around
`0x230dbf`; the zero-result path compares the ten-byte buffer against the
`DISCONNECT`/`OK` status strings around `0x230dc8..0x230de7` and logs timeout or
disconnect outcomes. This establishes a real receive callback with a fixed
10-byte request and a 1000 timeout, but the callback remains indirect through
`[r5]`, so its physical USB/UART implementation is still **UNKNOWN**.

This helper materially narrows the repeated-READY problem: the parser is not
reading an unbounded line at this point. A short, malformed, or transport-
status-prefixed input can return through the receive helper and re-enter the
selector state machine. The exact re-entry edge and READY transmit call are
still not proven.
