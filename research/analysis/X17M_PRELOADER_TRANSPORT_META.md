# X17M 20250327 Preloader transport and META transaction

Static analysis of the exact A-side 20250327 Preloader. No live target
communication was required or performed.

## Confirmed parser/receive relationship

The selector handler is `0x002188f0..0x00218c70`. Before the named selectors,
it checks the input against the three-byte prefix at runtime `0x230dfd`:

```text
0x2188f6  load relative offset
0x2188fe  add PC -> 0x230dfd = "AT+"
0x218906  r0 = "AT+"
0x21890a  strlen("AT+")
0x218924  bounded compare(input, "AT+", min(lengths))
0x21892c  nonzero -> continue with the selector cases
```

This is **CONFIRMED** evidence that the parser has an AT-command family path
and a separate non-AT path. `METAMETA` is tested in the latter path, so its
absence of an `AT+` prefix is intentional rather than an automatic reject.

## Receive helper

`0x00218888` is a concrete receive helper:

```text
0x218894  buffer = sp + 4
0x218896  clear(buffer, 0, 10)
0x2188a2  callback = [r5]
0x2188a4  callback(buffer, 10, 0x3e8)
0x2188ae  status = (uint8_t)return_value
```

The requested maximum is therefore 10 bytes and the timeout argument is
`0x3e8` (1000). This is **CONFIRMED**. The callback is indirect; its USB/UART
identity is **UNKNOWN**.

The helper then compares/logs transport status strings around
`0x230dd2..0x230de7` (`timeout`, `DISCONNECT`, `OK`). It is called from the
selector actions at `0x218ad4` and `0x218b84`, proving that selector handling
can re-enter a bounded receive operation.

## Indirect object layout

At dispatcher entry:

| field | instruction | use | status |
|---|---|---|---|
| `r0 + 4` | `0x2188fc` | loaded to `r7`; later called at `0x218a24`, `0x218b36`, `0x218be4` | **CONFIRMED**, implementation **UNKNOWN** |
| `r1 + 0` | `0x218902` | input pointer | **CONFIRMED** |
| `r1 + 4` | `0x21890e` | input length | **CONFIRMED** |
| `r2 + 8` | `0x218900` | loaded to `r4` | **CONFIRMED** |
| `[*r2+8]` | `0x218950` | callback used at `0x218966` | **CONFIRMED**, implementation **UNKNOWN** |
| `[*r2+8 + 4]` | `0x2189f6` via `r4+4` | 12-byte META/state operation | **CONFIRMED**, implementation **UNKNOWN** |

No direct call, absolute pointer, MOVW/MOVT pair, ADR, or ordinary PC-relative
literal reference to `0x2188f0` was found. Registration is therefore through
an indirect table or runtime-created object. The concrete registration table
remains the smallest unresolved object.

## METAMETA transaction

The equality path begins at `0x2189ac` when the bounded comparison returns
zero. Confirmed operations:

```text
0x2189b0..0x2189c8  clear 12-byte and 16-byte stack structures
0x2189cc..0x2189e2  update context/global state at structure-relative 0x608f8/0x608f9
0x2189f6            indirect callback(stack_buffer, 12, 0x7d0)
0x218a14            construct 0x230e36 = "ATEM0001"
0x218a1a            strlen("ATEM0001")
0x218a24            indirect callback("ATEM0001", length)
0x218a42/0x218a4e   construct/log md_type[0]/md_type[1]
0x218ad4            invoke receive helper
```

The byte direction of the two indirect callbacks cannot be proven without the
object implementation. Therefore the following wire interpretation is only
**PLAUSIBLE**, not confirmed:

```text
HOST -> parser: METAMETA
TARGET: state setup at 0x2189b0..0x2189e2
TARGET -> callback: 12-byte META/state record (0x2189f6)
TARGET -> callback: ATEM0001 (0x218a24)
HOST -> receive helper: up to 10 bytes, timeout 1000 (0x2188a4)
```

No static evidence proves that `ATEM0002` or `ATEMATEX` is emitted on the
successful METAMETA path. Their strings are constructed in later selector
branches, but the callback identity and state transitions are unresolved.

## READY producer and repeated READY

`READY` is runtime `0x2306c0`. Static searches found no direct materialization
in the dispatcher, no direct caller of `0x2188f0`, and no fixed transport call.
The READY producer is therefore **UNKNOWN** and is likely reached through the
same unresolved transport object or a separate registration record.

The observed sequence has these classifications:

| hypothesis | classification | evidence |
|---|---|---|
| METAMETA rejected by selector | **IMPOSSIBLE** for a correctly framed prefix-free input; `0x2189ac` is a real equality path | dispatcher structure |
| accepted, next handshake incomplete | **PLAUSIBLE** | `0x2189f6` state callback followed by receive at `0x218ad4` |
| transport timeout/parser restart | **PLAUSIBLE** | receive timeout argument `0x3e8`, status handling in `0x2188b0..0x2188d0` |
| secure/policy callback rejection | **UNKNOWN** | indirect callback implementation unavailable |
| USB disconnect/re-enumeration/new instance | **UNKNOWN** | disconnect strings exist, but no USB primitive reached |
| unexpected framing/length | **PLAUSIBLE** | comparator uses `min(selector_length,input_length)` and receive max is 10 |

The exact `READY -> receive -> READY` loop is not proven. A second READY could
be emitted by parser re-entry after the receive helper returns, but the READY
call site itself remains unresolved.

## Security state

Within the statically recovered METAMETA equality path, no direct call or data
reference to `seclib_brom_meta_mode`, SLA, DAA, or META authentication was
identified. This is **UNKNOWN**, not evidence of a bypass: those checks may be
inside the unresolved indirect callback at `0x2189f6` or a later state handler.

## State diagram

```text
external registration/object (unresolved)
          |
          v
0x2188f0 selector dispatcher
          |
          +-- AT+ prefix path ---------------------> AT command branches
          |
          +-- METAMETA compare == 0 (0x2189ac)
                  |
                  +--> state/context setup 0x2189b0..0x2189e2
                  |
                  +--> indirect 12-byte callback 0x2189f6
                  |
                  +--> indirect ATEM0001 callback 0x218a24
                  |
                  +--> receive(buffer,10,1000) 0x2188a4
                              |
                              +--> status/timeout handling
                              |
                              +--> parser re-entry possible, READY source unknown
```

The remaining requirement for complete resolution is the registration/object
table that supplies `[r0+4]`, `[r2+8]`, and the receive callback `[r5]`.

## Stronger callback-role result

The `[r4]` field of the METAMETA object is the same callback reached by the
receive helper:

```text
0x218ad4  r0 = r4
0x218ad4  bl 0x218888
0x2188a2  r3 = [r5]        // therefore r3 = [r4]
0x2188ac  blx r3           // receive(buffer,10,1000)
```

The same field is invoked after constructing `ATEM0001`:

```text
0x218a10  construct ATEM0001
0x218a1a  strlen(ATEM0001)
0x218a24  blx r7            // r7 = [r4]
```

Thus `[r4]` is **STRONGLY SUPPORTED** as a bidirectional transport callback
whose ABI supports both `(buffer, length, timeout)` receive calls and
`(buffer, length, ...)` output calls. Its concrete backend (USB CDC, UART, or
another abstraction) remains **UNKNOWN** because the object itself is not
statically registered in this image.

The `[r4+4]` field is separate and is called only with the 12-byte stack
record at `0x2189f6`; it is therefore **STRONGLY SUPPORTED** as a META/state
service rather than the byte transport. No downstream implementation proving
SLA, `seclib_brom_meta_mode`, or boot-mode mutation was found.
