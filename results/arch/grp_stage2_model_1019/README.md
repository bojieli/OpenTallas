# Selected GRP private0 Stage 2 model

MODEL HOLD: no source, synthesis, gate, or release adoption grant. This packet
sizes the exact Stage 1 pair at 733dc3e42/dbb9af91a/b167952d3. Inputs are hashed
in inputs.json; leaves are the exact 16 frozen definitions used by the retained
output component oracle. The retired `_ds` 235/230-root census, old four delay
lists, native area, and physical views do not qualify this source. GEN7 bound
and GEN8 PREP graphs are distinct in selected_chains.json; final GEN8 is OPEN.

## Actual boundary and existing ages

boundary.json retains every selected port and original output equation.
GRP has 1,701 input and 3,047 output bits; H has 1,479 and 2,776. Removing the
four clock/reset pins yields 4,744/4,251 live data ABI bits. Existing direct
paths are scalar EST, the GRP 271-bit downward permutation, and 126 upward
status bits. H status is eight copies of its actual 18-bit local vector.
EST still feeds four actual PC boot-ready inputs per group, 128 total.
No generic alias deletion or constant placeholder is proposed.

Per-bit o_pc_bits.json gives each of the four 128-bit PC controls: bits0..71
and105..127 originate on HBM clock (95 bits); bits72..104 originate on core
clock (33 bits). A uniform output clock would change the protocol. Incoming
PC data/metadata land on core capture FFs, while drain observes HBM health
through independent two-stage synchronizers. These are distinct cohorts.

| Input cohort | Original first state / behavior | Candidate cut obligation |
|---|---|---|
| kreq/vreq | rowctl rq/tq/etc, then VREQ mux stage | coherent core capture; preserve K/V collision semantics |
| i_pc[288:0] x4 | landing PC actual data/metadata capture | align actual and expected put, epoch, sector and valid |
| i_pc health | drain core capture or HBM CDC; cf1 reduction | original domain and sticky lifetime; no health mask |
| i_ctl[193:0] | boot FIFO gating, calendar/phase capture | whole cfg/go/metadata cohort; legal boot spacing |
| i_ctl, i_up transit | direct permutation / concatenation | each transit cut adds an edge; preserve bit ownership |
| stack/group | four kept PC input copies | preserve boot constant and first-arm lifetime |
| afk/afv/afu | combinational reduction before fault FF | add real core face capture, then actual reducer |
| x_est | direct output to four PC boot-ready consumers | coherent core input/output cuts, +2 group-local edges |

All rsp/krsp output bits come from registered rowctl responses, with rsp and
krsp sharing most stored source bits. Every output needs a physical face owner;
duplicating face banks is charged, never assumed free. af_fault is a real core
reducer FF. o_pc contains real registered leaf outputs in the clocks above.
o_ctl local 18 bits contain 8 core-origin and10 HBM-origin bits; incoming chain
bits may already have parent core relays. Their exact incoming sampled-domain
receipt remains OPEN; original HBM ancestry alone does not identify the clock
of a later relay. No CDC bypass or re-synchronization is silently introduced.

Original request edge ledger is E0 request capture, E1 mux, E2 request hop,
E3 PC capture, E4 SRAM/read metadata, E5 PC output, E6 response hop,
E7 row capture, E8 response. Both K/V response layouts derive from that cohort.
Original actual/expected write capture E0 writes SRAM E1. WRITE_PIPE0 is fixed;
turning WRITE_PIPE1 on adds an edge and requires a new no-overwrite/read proof.
CHECK_PIPE1 fault operands land E1, fq E2, sticky PC fault E3; put/actual mismatch
can latch E2. Response hop plus row propagation adds3 core edges to that fault.

## Whole-source sizing and a bounded conservative candidate

The declaration-derived, logically used state count is **16,053 bits per
variant**, plus **1,092 kept WRITE_PIPE0 shadow declarations**. These are not
native FF counts. They exclude 131,072 existing macro payload bits, simulation
assertion state, and optional define-dependent seam latches. model.json gives
leaf arithmetic: 4x1198 PCs +2380 rowctl +1344 hops/reset +171 front calendar
+465 landing calendar +274 phase +110 drain +2 reducers +5x1303 boot wrappers.
Some source state is duplicated or semantically inactive and cannot be priced
as either removed or physically merged without the exact native graph.

A deliberately conservative sizing envelope adds one full input and output
face bank for every live data ABI bit: +4,744 FF/GRP, +4,251 FF/H,
**+149,836 FF across28+4 groups**, before reset distribution, kept copies,
health additions, or new logic. Source state plus shadows plus these banks is
21,889/21,396 bits per instance. This is a bounded candidate, not a minimum or
a recommended final implementation. Reusing/relocating existing same-edge
capture FFs can reduce it only after producer-consumer equivalence proof.
Every new input cut is core-clocked; output cuts keep actual cohort clocks.
Mixed-clock outputs and HBM-to-core health cannot claim a uniform +2 latency.
Converting that envelope to area requires the exact sequential cell mix and
mapping; no obsolete native area or guessed density is used.

Reset must land in two real stages separately on core and HBM faces while
preserving each inherited sampled or asynchronous assertion behavior. Existing
PC/calendar rn is sampled once, hop reset uses branch hrn then hop rn, and FIFO
reset is an AND of both external resets followed by two local asynchronous
assert/synchronous-release conditioners. A blanket reset replacement changes
stopped-clock behavior and is refused. Payload FFs that were reset-free stay
reset-free. For N actual reset endpoints, a two-level32-load distribution
requires ceil(N/32) final kept copies and ceil(ceil(N/32)/32) predecessor copies
before accounting other loads. Both copy groups need identical D/clock/reset
histories; this arithmetic is not an initialized-copy proof. The whole
all-driver native fixed point (D enables, decode, data, reset, ties, inputs,
BUF/INV-transparent roots) is NULL. Source fanout expressions alone cannot
price synthesis factoring or the added replica predecessor loads.

## Storage and resource ports

Four real single-clock128x256 payload SRAMs supply up to128 bytes/core edge
for reads and128 for writes at the group boundary. All four lanes may be active;
32 group replication is not a throughput measurement. Selected CHECK_PIPE1 uses
128 valid bits plus tk2[128]x2 per PC, not legacy ticket[128]x9. Four PCs can make
8 ticket write bits,8 ticket read bits at ra and8 valid read bits at wa/ra
per edge (valid has two independent read addresses; tk2 has one). Metadata per bank is384 bits, below2kb.

The existing SRAM behavioral equation reads OLD data on simultaneous same-row
read/write. The checker permits that event; put wins valid and the consumer
must see the old ticket/data. A narrow replacement must preserve this exact
behavior or prove no collision in every legal programme. Splitting each256-bit
word into four128x64 single-clock banks would mean16 macros/group and512/die,
not a qualified floorplan. No such family is admitted here: local contact pitch,
PG/OBS/vias, masks, boot repair pins, same-edge clock/read timing and actual
anchored abstracts must be derived before choosing it. The old128x256 faces
are approximately10 contacts/um and fail the6/um rule. S81's512x128 single-clock
planner/access model is reusable methodology only; its own union/track/PG
obligations remain open. Dual-clock n64 provenance is not a single-clock swap.

Each of five independent boot FIFOs is a73x16=1,168-bit pointer ring. Summing
them to5,840 bits does not invoke a per-array2kb SRAM requirement. Keeping them
as small flop rings is conditional on actual fanout/native area/closure. Optional
SRAM conversion needs a real dual-clock asynchronous-head/prefetch proof,
first-use/online reset bounds and sealed-producer/drained-consumer lifetimes;
never share independent FIFO ports blindly. There are no traffic credits added.

The actual mandatory long-delay repair is lcal.dl[8]x11=88 bits: replace its
shift chain with an8-entry pointer ring, coherent programmable tap, and LD0
bypass. Ring pointer + history-valid reset state must preserve LD1..8 ages
and zero-filled startup without resetting SRAM contents. LD9..15 currently
alias taps through a3-bit cast; preserve that behavior or establish an actual
legal-programme rejection. Other pipeline processing/CDC chains and the three
independent lane_hold counters are not delay memories.

## Static compiler and health calendar

Under the conservative input/output bank candidate request-to-response becomes
10 core intervals (+2), not8. Put acceptance moves +1core, response publication
+1core; expected slots, read legality, overwrite lifetimes and both response
consumers must be regenerated jointly. Each upstream GRP control pass adds
2core edges, destination control capture adds1. selected_chains.json enumerates
the actual HROOT permutation and this formula for all32 groups on both frozen
graphs. It excludes additional ROOT/physical relay cuts and has no final GEN8
receipt. No uniform stack-group order is assumed.

Core/HBM periods are625/768u, q evolves(q+143)%768, and original
lcal t0=ta+768*h0+625*rc-625 with ta=q or q+768. A core cut is625u,
an HBM cut768u, and shifting launch changes q itself. Thus SAFE_LOW200,
SAFE_HIGH600, META_HOLD8, rc/h0 and the compiler release/read/fault deadlines
must be rederived from actual target edges. No scalar SU/MU token price or
STATUS cutoff can yet be stated. Added pipeline does not necessarily reduce
steady throughput, but actual production-shape occupancy must demonstrate it.

health_delta.json traces four currently unconsumed real aggregate outputs:
slg.fault, lcal.fault, fcal.fault, phase.fault_hbm. They are sticky until their
actual local reset. The first aggregates four PC checker faults and row response
checks; calendars detect launch overlap/order; phase HBM checks actual held
context/layer on events. Their intentional redundancy under every legal source
is unproven. Correct classification is **unexported fault outputs**, not a
proved cardinality of lost independent primitive failures. phase.fault_core
already enters drain, and existing reducer cf1 is not sticky by itself.

Proposed separate real ports export each actual fault through one source-clock
face FF. Across32 groups this adds128 port bits/128 source FF. A bounded
collector candidate adds64 direct core captures,128 two-stage HBM synchronizer
FF, and32 group sticky reducers:224 FF, **352 FF source+collector floor**,
excluding reset/copy/ancestor/route logic. These are128 new aggregate graph
members, not128 newly identified primitive fault sources. Clock/reset owners
must be matched to actual104/106 owner buckets; the number of new unique
buckets is NULL. Original389 health connections/1320FF floor from1f424 are now
explicitly incomplete rather than silently extended. STATUS, host commit,
future admission and cache poison all require the revised full graph and phase
bounds; no old357/613 count or1982 cutoff is inherited.

## Concrete next source plan and admission checklist

1. Obtain ROOT review of this model, then select minimum useful boundary
   cohorts and the exact single-clock storage/contact architecture. No RTL now.
2. Prove8x11 ring ages/reset/LD behavior on the minimum component; preserve
   original event and arithmetic equations and all existing golden comparisons.
3. Prove each proposed face cohort against original source with explicit
   added-age observables, actual reset/phase assumptions, first-use/static
   compiler programmes and causal wrong-edge/domain/reset/collision mutants.
4. Add default-off distinct whole-pair source only after model grant; propagate
   actual ABI/schema/parent connections together, including any4 real health
   ports. Freeze all public source/default bindings and producer buses.
5. Derive exact native counts and full transparent copy fixed point; price area,
   clock loads, routing tracks/capacity, single-wire reach<=405um and realistic
   40-60% synthesis-area outline. No build before bounded source sizing closes.
6. Prove revised per-region edge calendar, full health/STATUS/commit/admission
   DAG and SU/MU token occupancy; obtain physical grant separately.

Checklist now: pins MODEL/mixed-domain HOLD; reset2 HOLD; fanout HOLD;
depth/timing HOLD; storage actual inventory PASS/delay repair MODEL/macros HOLD;
floorplan/local contacts HOLD; clock spread/neighbour reference HOLD; schedule
relative edge ledger PASS/absolute compiler and SU/MU price HOLD. No tie, stub,
false path, multicycle exception, hidden arbitration or backpressure proposed.
