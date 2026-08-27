# Microarchitecture specification

**Document:** SPEC-MICRO 1.0

## MICRO-1 RTL organization

### MICRO-1.1 Synthesizable hierarchy

The public-reference RTL hierarchy is frozen conceptually as follows. Module names
may acquire a version suffix only through change control; their responsibilities
shall not migrate without traceability review.

```text
ot_stage_top
├── ot_cmd_frontend
│   ├── ot_cmd_crc_version_check
│   ├── ot_session_table
│   └── ot_admission_controller
├── ot_stage_controller
├── ot_schedule_controller
│   ├── ot_schedule_store (active/shadow)
│   └── ot_static_switch / ot_static_mesh_endpoint
├── ot_tile_array
│   └── ot_tile
│       ├── ot_route_mask
│       ├── ot_rom_wrapper
│       ├── ot_format_decode
│       ├── ot_mac_array
│       ├── ot_reduction_tree
│       └── ot_tile_ras
├── ot_hbm_frontend
├── ot_stage_link_endpoint
├── ot_repair_controller
├── ot_ras_controller
├── ot_power_reset_controller
├── ot_csr_block
└── ot_dft_controller
```

Generic library blocks include `ot_sync_bits`, `ot_async_fifo`, `ot_skid_buffer`,
`ot_crc16_ccitt`, `ot_crc32c`, `ot_secded_64_8`, `ot_counter_sat`, and protocol
assertion bind modules. Macro wrappers are a distinct directory and never contain
silent functional fallbacks in a synthesis configuration.

### MICRO-1.2 Parameters and legality

Widths and maxima come from `parameters.json`. The synthesizable public default is
16 experts, top-6, 16 arithmetic lanes, 64 words per expert, 8-bit activations,
4-bit weights, and 32-bit accumulators. This reduced default exists for fast DV.

Elaboration-time checks shall reject:

- zero dimensions;
- experts above 1,024, top-k above 16, or top-k above expert count;
- a field width unable to encode its configured maximum;
- nonpositive FIFO/schedule sizes or schedule length above 256;
- accumulation width smaller than the selected numerical profile requires;
- macro latency inconsistent with the configured alignment pipeline;
- unsupported numeric mode or a target-format build missing its decoder;
- inconsistent CRC/ECC enablement at an architectural boundary.

Non-power-of-two expert, word, port, and queue counts are legal. Range checks must
not rely on unused binary encodings wrapping into valid storage.

### MICRO-1.3 Coding semantics

Synthesizable state uses `always_ff`; combinational decode uses `always_comb` with
complete assignment. Sequential pipelines use nonblocking assignment. Every module
declares time unit/precision for simulation, though synthesizable behavior is
cycle based. Signedness is explicit at module boundaries and before arithmetic.

There are no inferred latches, implicit nets, unsized arithmetic constants in
width-sensitive expressions, combinational ready-to-valid paths across module
boundaries, or initialization-only functional state outside macro models. Reset
values, invalid payload behavior, and unused/reserved bits are specified.

## MICRO-2 Data and control planes

### MICRO-2.1 Decode decomposition

The stage controller executes a manifest microprogram for each owned layer. The
microprogram opcode set is deliberately small:

| Opcode | Responsibility |
|---|---|
| `KV_READ` | issue tagged state/cache reads and wait for declared beats |
| `VECTOR` | invoke an abstract qualified vector/attention operation |
| `ROUTE` | consume/validate top-k expert IDs and broadcast route context |
| `ROM_MATMUL` | issue immutable matrix words and tagged activations |
| `REDUCE` | execute the certified static collective |
| `KV_PREPARE` | write nonarchitectural next-state records |
| `COMMIT` | atomically publish prepared state for the layer/transaction |
| `STAGE_SEND` | packetize final activation for the next stage |
| `COMPLETE` | retire terminal output/response |

The microprogram is immutable or manifest-bound configuration; it cannot address
outside the stage-owned layer/tensor regions. The public reference may implement
`VECTOR` through a deterministic functional macro. All surrounding ordering,
buffer, numeric-mode, poison, state-commit, and RAS semantics remain synthesizable.

### MICRO-2.2 Control separation

The always-on configuration plane owns CSRs, boot, schedule/repair shadow loading,
telemetry drain, and power control. The core service plane owns sessions in flight,
NoC slots, tiles, HBM requests, and stage transactions. Configuration changes cross
through closed-loop handshakes and become visible only at specified quiescent epoch
boundaries.

Debug/test override is a third mode, mutually exclusive with service enable. Test
mode forces command ready low, drains or resets response state per entry sequence,
and prevents test clocks from reaching active HBM/stage links unless their BIST
mode is selected.

## MICRO-3 Commands, sessions, and state

### MICRO-3.1 Command frontend and admission

The command frontend contains eight accepted-command entries, eight response
entries, and sixteen fatal/uncorrectable telemetry entries in the public default.
Depths are parameters but never below two. The frontend checks CRC, ABI, opcode,
reserved bits, field ranges, image/epoch, layer ownership, session range, batch
range, and operating state before allocating a transaction ID.

A command describes a homogeneous batch of consecutive session IDs beginning at
`session_id`, with a common image, context, position, numeric mode, and layer
interval. `activation_address_64b_units` names the first packed activation; lane
`i` begins after one manifest-defined hidden-vector stride. The range
`session_id .. session_id + batch_size - 1` may not overflow 24 bits. A heterogeneous
production batcher may decompose work into homogeneous commands; no implicit
descriptor DMA format is hidden from the ICD.

Admission atomically reserves:

- every addressed session and generation;
- prepared-state space on each stage;
- required HBM request tags and response buffering;
- static-NoC sink transaction credits;
- stage-link packet/retry entries where applicable;
- one response entry.

Failure reserves nothing and returns `NO_CREDIT`, `CAPACITY_ERROR`, or the relevant
legality error. Credit accounting uses widened counters and formal conservation
properties.

### MICRO-3.2 Session table

`session_id` is split into a low configurable table index and high generation tag.
The public default has 256 physical entries; a product configuration sizes the
table from verified local capacity. Each entry stores:

- full session ID and valid/busy/poison flags;
- image slot, numeric mode, context length, and expected position;
- stage-local KV base, limit, allocation generation, and prepared-state pointer;
- last retired epoch/transaction and sticky session error class.

Configure is legal only for an invalid entry. Release is legal only after drain or
explicit abort. A late response must match the full session ID, allocation
generation, epoch, and transaction before it can update state. The table uses
SECDED and treats an uncorrectable entry as a session-contained fatal error.

### MICRO-3.3 Transaction state machine

The stage transaction states are:

```text
FREE → VALIDATE → RESERVE → FETCH → EXECUTE_LAYER ↔ WAIT_SERVICE
     → PREPARE → COMMIT → NEXT_LAYER → STAGE_SEND/COMPLETE → RETIRE → FREE
```

Any pre-commit error transitions to `POISON_DRAIN`; post-commit errors attach to
the following layer boundary and may require session abort. `POISON_DRAIN` consumes
and discards all already-launched beats, releases every credit once, emits one
terminal response, and transitions to `FREE`. Watchdog expiration follows the same
path and enters system SAFE if drain cannot complete within its bound.

QUIESCE blocks `RESERVE` but lets allocated transactions retire. ABORT marks the
specified transaction poisoned and prevents subsequent COMMIT. Warm reset first
requests quiesce; on timeout it aborts, records the reset cause, and only then
clears nonretained architectural state.

### MICRO-3.4 State atomicity and poison

KV/state writes target a prepared generation not visible to later decode. COMMIT
atomically advances the session pointer and expected position after every required
beat, CRC/ECC result, tile result, and stage result is known good. Whole-batch
commands are atomic: any lane poison prevents every lane in that command from
committing. This is conservative and deterministic.

Poison is sticky within a transaction. It accompanies NoC flits, tile results,
HBM tag state, stage packets, and completion. Logic may omit data calculation for
a poisoned transaction but must preserve drain, credit, ordering, counter, and
terminal-response behavior.

## MICRO-4 Tile pipeline

### MICRO-4.1 Route context

`ot_route_mask` receives one `IF-TILE-ROUTE` record before the first activation
beat for its transaction. It checks record CRC, epoch, layer, top-k count, reserved
bits, and every expert ID. IDs at or above configured expert count poison the
transaction. Duplicate legal IDs are suppressed while retaining the first
appearance order for diagnostic reporting.

The route context is held in a two-entry tagged FIFO. It expands to a logical
expert mask for reduced configurations; product-scale synthesis may use a decoded
bank-select tree rather than a 1,024-bit high-fanout vector, provided the visible
selection semantics and timing contract remain identical.

### MICRO-4.2 ROM issue and repair

The tile reserves a result-buffer entry before issuing a fixed-latency ROM read.
Logical `{region,tensor,word,expert}` addresses pass through range and repair
translation. Dense regions ignore routed IDs and use their manifest enable mask.
Routed regions issue only selected logical experts. The ROM and scale-ROM responses
carry the transaction tag, word sequence, macro syndrome, and block-CRC state.

No downstream backpressure may stop a read after issue. Alignment delay equals the
macro's declared read latency and is statically checked. An invalid repair entry,
macro fault, block CRC mismatch, or response/tag misalignment poisons the reserved
result entry.

### MICRO-4.3 Numeric and reduction pipeline

The target pipeline stages are:

1. unpack canonical nibbles/bytes and classify exceptional encodings;
2. combine block scales and align exponents;
3. multiply activation/weight lanes;
4. accumulate within the frozen block order;
5. round at the declared block boundary;
6. reduce ascending lane IDs;
7. emit tagged tile partial sum and status.

The integer DV mode uses signed operands and a widened exact product accumulator,
then the same configured saturation and reduction order. Target and DV modes use
different manifest/numeric mode IDs. Pipeline latency is a parameter exported in
capabilities; throughput is one admitted word per cycle after fill when no macro
or result-buffer constraint stalls admission.

### MICRO-4.4 Tile buffering and backpressure

Route, activation, and result boundaries use two-entry skid/elastic buffers. The
tile may deassert activation ready before issue. Once a word is issued, all
internal fixed-latency stages advance every enabled core clock; result capacity was
pre-reserved. Legal clock gating freezes every aligned state element together and
never gates only data or only valid/tag state.

Invalid cycles drive architecturally ignored payload and preserve no secret
assumption about zero. Assertions check stable stalled payload, tag continuity,
one result per issue, no result without issue, and poison monotonicity.

## MICRO-5 Static network

### MICRO-5.1 Switch datapath

Each output reads one active-bank schedule entry per slot. An entry contains source
port ID, expected-valid class, route/sequence check bits, and idle encoding. The
selected input flit is CRC/epoch checked, registered, and emitted on the reserved
physical output. There is no output arbiter and no link ready.

An expected idle source emitting valid, an expected-valid source missing a flit,
an out-of-range source, or a flit with wrong epoch/transaction/sequence records a
schedule violation and poisons that transaction. Schedule violation never causes
the flit to slip into a later slot.

### MICRO-5.2 Schedule control

Active and shadow memories each hold at most 256 slots. Shadow writes occur only
from the always-on plane while shadow is not pending commit. A streaming CRC covers
the exact stored entry bits. Hardware checks source ranges, reserved bits, enabled
ports, length, and expected manifest CRC. The compiler's certificate hash is
stored alongside but global proof is checked in software/CI.

Commit handshake sequence is `request → service quiescent → epoch boundary → bank
select toggle → acknowledge`. Reset selects bank zero, epoch zero, slot zero, and
service disabled; boot must validate bank zero before enabling slots.

### MICRO-5.3 Credits and egress

Each certified route names all terminal egress queues. Admission decrements one
transaction credit at each terminal through an atomic reservation vector. Egress
buffers hold a complete maximum packet or one transaction's certified maximum
flits. A credit is returned after terminal consumption or complete poison drain,
never on intermediate forwarding.

Counters have an additional overflow bit. Assertions prove no decrement at zero,
no increment above configured depth, and `free + reserved + occupied = depth`.
Backpressure at HBM, tile, stage-link, or host boundaries can consume credits and
stop admission but cannot block a launched static path.

### MICRO-5.4 Reduction endpoint

The reduction endpoint groups partials by epoch, transaction, layer, word sequence,
and numeric mode. It accepts each expected source exactly once, rejects unexpected
or duplicate sources, and reduces in ascending certified source order even when
physical arrival is earlier. Completion requires the expected-source bitmap and
terminal marker. Any poisoned/missing/bad-CRC source poisons the group.

Reduced configurations implement the bitmap directly. Product-scale implementations
may use hierarchical bitmaps, but the proof-visible expected count and duplicate
detection remain exact.

## MICRO-6 HBM frontend and stage link

### MICRO-6.1 HBM request machinery

The HBM frontend has a 4,096-entry architectural tag namespace and a configurable
smaller physical outstanding table. A tag entry records operation, session and
allocation generations, address range, expected beats, received bitmap/count,
prepared-state destination, and poison/error state. Beats are in order within one
tag; different tags may interleave.

Address-plus-length overflow, session-limit violation, misalignment, duplicate
beat, early/late `last`, bad CRC, or memory error terminates the tag as poisoned.
Write acknowledgement is required before COMMIT. The behavioral model can insert
latency, reordering across tags, correctable/uncorrectable errors, and backpressure.

### MICRO-6.2 Stage-link endpoint

The sender packetizes NoC flits, retains a two-packet retry window per virtual
channel, adds CRC32C, and consumes remote packet credit. The receiver checks image,
epoch, transaction, sequence, length, flit CRC, and packet CRC. A recoverable CRC
failure sends negative acknowledgement; timeout or a third failed transmission
poisons the transaction.

Acknowledgements are idempotent. Retry cannot duplicate a state commit because the
receiver tracks the last accepted `{epoch,transaction,packet_sequence}` until the
transaction retires. Link reset withdraws credits and requires a resynchronization
handshake before service resumes.

## MICRO-7 CSR, telemetry, and counters

### MICRO-7.1 CSR behavior

The 4 KiB CSR block implements the exact map in `interfaces.json`. Unsupported
addresses return `BAD_FIELD`. Misaligned or unsupported-size accesses return an
error without side effects. Partial writes obey byte strobes only on RW fields.
RO and reserved fields ignore writes but report a bad-field status when the write
attempt is nonzero. RW1C clears only bits written as one.

Schedule and repair windows target shadow state. Writes are rejected while commit
is pending or test/service ownership conflicts. Image identity registers are tied
to mask/macro identity inputs and cannot be overridden by configuration.

The AON-to-core schedule adapter permits one outstanding operation. It transfers
the complete write/commit record through a stable-payload acknowledged mailbox,
emits a single-cycle core request exactly once, waits through a blocked quiescent
commit, and returns a typed acknowledgement or error. An invalid write is rejected
without mutating or permanently poisoning the shadow bank, so corrected firmware
may retry. Commit error is a per-request response pulse; sticky diagnostic history
is maintained by RAS/CSR state rather than overloaded onto the transaction signal.

### MICRO-7.2 Error and telemetry queues

First error captures atomically on the earliest event by core timestamp; ties use
fixed ascending source ID. Correctable events increment saturating counters and may
be coalesced. Fatal/uncorrectable events reserve telemetry storage before affected
service is enabled. If the telemetry sink stalls, new inference admission stops;
existing events are never overwritten.

Interrupts are level sensitive summaries of unmasked sticky classes. Masking an
interrupt does not suppress capture, counters, poison, or safe-state behavior.

## MICRO-8 Integrity storage

### MICRO-8.1 SRAM and FIFO ECC

Every architectural 64-bit SRAM word uses SECDED with eight check bits or a macro
code at least as strong. Narrow records are packed with independent ownership so
a corrected word cannot mix update domains. Read correction is combinational or
one fixed pipeline stage and increments a counter; writeback scrub is scheduled
without changing transaction order. Double-bit detection poisons every record in
the affected ownership word.

Small flops may use parity plus replay/abort if their contents are reconstructible.
Control state whose corruption can cause an unsafe commit uses duplication/parity
or SECDED and fail-safe decode. The exact protection allocation is machine checked
against the RTL inventory before verification closure.

### MICRO-8.2 CRC engines

CRC engines accept one parameterized data beat per cycle and produce deterministic
little-endian bit traversal as defined by the ICD. They support known-answer test
mode and have no hidden reflection option. CRC state is reset at record start and
latched with the same transaction tag; an interrupted record cannot reuse prior
state.

## MICRO-9 Macro wrappers and synthesis configurations

### MICRO-9.1 Required wrappers

Each external macro wrapper has three configurations:

1. **behavioral DV** — deterministic contents/latency plus injectable faults;
2. **generic synthesis** — synthesizable or black-box declaration with timing and
   area constraints, never an accidentally inferred giant implementation;
3. **target integration** — external macro pins and signoff views under a later
   target-node baseline.

Build manifests name the chosen configuration. Synthesis fails if a behavioral
model is selected for a product-like hierarchy or if a black box lacks declared
clock, reset, latency, test, integrity, and constraint metadata.

### MICRO-9.2 Public proxy scope

The public proxy synthesizes command/control, route mask, representative numeric
lanes, reductions, static switches, repair translation, CRC/ECC, FIFOs, counters,
power FSM, and macro wrappers at reduced parameters. ROM depth, tile count, HBM,
and physical links may be black-boxed or sampled. PPA reports must separate logic,
inferred memory, black boxes, and scaled hypotheses; no single linear scaling from
the proxy to a leading-node wafer is permitted.
