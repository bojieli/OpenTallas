# S81 fixed-cycle command plane

`dsfd_stage_seq_static_c` is a new RTL successor using the real S81 sequencer external bus widths and context packing. It includes all thirteen engine command/done/status faces, including HC projection engine 11. It does not instantiate the predecessor's completion-driven scheduler or asynchronous credit FIFOs.

The core has 128 shared 76-bit program rows and two context slots. Each row stores `{done24,issue24,engine4,arg24}`. Three PW36 writes load 26, 26 and 24 bits; a fourth page selects BEGIN/SEAL configuration with length, stage and reset-relative start phase. All rows must be loaded before SEAL. A fixed 128-edge boot scan validates one row per stream edge; the first permitted sampled START is SEAL +129 stream edges. The scan never waits for data or changes runtime issue times. The four-row wrapper test uses the corresponding five-edge arm boundary. Native commands are `{slot,user10,pos21,token21,arg24,op7}` on the actual 85-bit valid/data engine face. Each engine has a parallel one-hot operand reduction and fixed output registers; command selection has no variable 84-bit slice priority chain. Engine 14 is a fixed KIT return and engine 15 is fixed END. Command pin cycle zero is one stream edge after sampled core `job_v`.

Every issue, KIT and END comes from the stored cycle comparison. Engine status, availability and completion pins detect errors; they never choose or delay an issue. Program mutation during execution, unsupported engines, bad phase, occupied context, missing pages, late/missing/bad-tag completions and unavailable engines raise sticky faults. On execution faults, the configured calendar continues, including its fixed END. Fault handling outside this block must discard that failed result. The compiler owns all context launch times and rejects cross-context command/completion collisions or live-slot overwrite.

The wrapper retains the real serial START/PW and stream command clock domains. Fixed alternating mailbox banks carry START/PW and KIT return data; no ready or credit enters issue timing. The compiler must establish source spacing and a bounded physical clock/reset/launch epoch. The included ideal 3:4 clock test proves only component transport behavior. The physical 3.6 GHz source, reset epoch delivery, clock/pin timing and command/completion relays remain unqualified. Existing phase candidate tables are not physical evidence.

`program.py:emit_native` consumes the actual native operand/service compiler. Missing native producers, native boot/constant ownership, command ABI integration, stream pin-to-pin timing, immutable context launch cycles or qualified physical clock evidence return an empty dispatch image. Serial endpoints need actual fixed-phase command adapters. Merely copying the mixed fixture programs into PW memory does not satisfy these checks. Every one of the existing 59 physical stage programs is tested to reject absent native owner bindings.

Validation uses `python3 -m unittest discover -s tools/s81_static_control -p 'test_*.py'`. The RTL gate runs through `ot-run ... -- bash tools/s81_static_control/component_gate.sh`; it exercises all 128 program rows, 252 nonzero native commands across two contexts, adjacent and simultaneous issues, KIT/END, nine fault witnesses, and timing/context mutants. Its command data are opaque component patterns; this is not numerical model execution or a native-token pass. A separate wrapper test sends consecutive PW words over modeled 3:4 clocks, checks both native contexts and KIT token returns, and checks sticky engine status outside an issue edge.

The actual PQ producer is now `ot_s81_pq_command_endpoint`. It accepts the
sequencer's real `c_cmd[84:0]`, returns `c_done[8:0]` and `c_st[1:0]`, and drives
`dsfd_sp_pq_n.f_iss[91:0]` from an independently sealed PW36 descriptor image.
The native fields are stored; the bench never supplies `f_iss`. Four explicitly
selected native tags may overlap. Each descriptor contains native fields90,
command-sample-to-observed-retire edges24, and native tag2 (116 bits total).
There are 64 descriptors under one clock root, with 7,424 data-storage flops.
`pq_descriptors.py` writes five24-bit pages per descriptor. Page7/address0 BEGIN
or SEAL carries the length8; bit24 distinguishes SEAL. A fixed64-edge scan arms
the selected image. Reset revokes it. Runtime availability and retire events
only fault; they cannot move a programmed GO or completion edge. The static
controller's `t_iss[36]` is the explicit calendar retire pulse and `[38:37]` its
tag. Global idle does not gate another native tag. The older dynamic core's
last-stream event does not establish this retire contract.

`ot_s81_pq_calendar_rom` instantiates two real `ot_rom_4096x72_m8` mask-ROMs.
Their combined row144 is `{reserved48,timestamp24,action72}`. The native action
ABI in `pq_calendar.py` matches the static controller's exact VM, ROM, config,
launch and retire fields. Four rows are prefetched at a fixed boot edge before
`stage_start`. A stage start sampled at E0 produces timestamp0 at the action
pin at E1; the receiving controller samples that pin at E2. The issuer emits
rowissue R at command pin R+1, the endpoint emits GO at R+2, and calendar
ACCEPT timestamp R+1 reaches the action pin at R+2. Both are captured by the
native controller at R+3. Prime/phase/source gaps fault and never cause waits.
The compiler must bind the actual boot-prime and stage-start producers before
native dispatch; component stimulus does not satisfy those obligations.

The admitted component gates (`pq_endpoint_gate.sh`, `pq_calendar_gate.sh`,
`pq_count_lifetime_gate.sh`) cover 252 hardware-produced commands across four
tags, real paired-ROM consecutive/sparse events, and the actual 12 count leaves
with their 15/2/15 partition. Live reaches the farthest leaf12 edges after the
source pin; a root reaches GA after4 and Q2F after5. The compiler additionally
needs the static controller's last-count-consume timing and its actual live/tag
producer. Endpoint status and calendar stimulus remain declared component
boundaries. Production phase-ROM addresses, operand producers, full native
VM service calendars, physical phases/slots and layer throughput remain
unqualified. The compiler refuses absent bindings; no production calendar is
created from random phase fixtures or historical252-command opaque patterns.

The Markov embedding successor `ot_dsrom_markov_embed_static` replaces its old
PP lookup's runtime credits/FIFO with sixteen fixed reads and responses. Its
253 real paired masters instantiate506 actual4096x274 mask ROMs; each preserves
256 payload bits per word and the released129280x256 BF16 Etable. The upper18
ROM bits remain unused. The physical pair and group clocks are explicit270
entries. No runtime input changes a read or response edge. Prefix token and
caller identity are captured at the real request; invalid token/overlap/missing
pair output faults are diagnostic and never shift the output slots.

`markov_static_image.py` copies the entire66,191,360-byte released tensor into
all506 physical via masks; only unused cells above the released token bound
are zero. The admitted full-shape gate checks160 beats from10 boundary tokens,
sixteen invalid-token slots, and independently decodes every released row from
the physical via maps back to the source hash. A second admitted run flips one
actual via cell with the same binary and unchanged scoreboard; it fails on
beat0. The original masks stay unchanged. The gate uses the real ROM model's
744ps SS read delay at833ps, as functional capture evidence. It does not prove
physical setup/hold or the full head path. Output pins launch at request+6..21;
the kernel receives them at+7..22, so its start is sampled at request+6. Actual
Wtable/head-logit producers and prefix pairing are separate native callers;
head logits are never stored as immutable descriptor values.

Canonical PHW10 command support (2026-10-15): instantiate the command endpoint
with PHW=10, use encode_descriptors(..., phase_width=10), and load all117
descriptor bits. This produces f_iss93 with phase10; PHW9 remains an explicit
historical component default. The current native PQ core is PHW10/SAW14 with
75-bit actions, six actual phase/stream ROMs and36 SRAMs. Use ACTION_BITS=75
on both the calendar reader and paired-ROM wrapper, and compile_events(...,
action_bits=75). Rows remain144 bits: action75, timestamp24, reserved45. The
action's top3 bits share the time macro's low3 bits. A legacy72-bit calendar
cannot be connected to the canonical controller. These component tests do not
establish canonical2417/BF519 numerical execution, die connectivity, physical
clock delivery or production throughput.

`dsfd_sp_pq_produced` joins the actual PHW10 descriptor endpoint and 75-bit
paired-ROM reader to `dsfd_sp_pq_n`. It exposes separate command/calendar
clock entries, fixed prime/start inputs and normal fault outputs. The added
`pq_canonical_pins_gate.py --produced` component checks boundary phases511..514
with the real eight total ROM macros and36 SRAMs, fixed command completion33,
and rejects a dropped physical calendar CFG cell and source phase-MSB mutant.
Its zero phase/stream images prove connectivity and pin epochs only; they do
not implement the canonical model numerical programme.
