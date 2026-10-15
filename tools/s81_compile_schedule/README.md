# S81 fixed cycle calendar compiler

`compile_calendar.py` lowers already scheduled stage jobs to exact physical VM
edges. It has no runtime inputs and never adjusts execution in response to
credits, readiness, queue occupancy, observed completion, or fixture values.
Compilation rejects memory/transfer conflicts and requires a revised offline program.
The optional `--schedule-native-jobs` pass assigns fixed job issue cycles
offline using owner-provided native durations, predecessor completions, one
in-flight job per physical engine port, and exact recurring clock phases. It
reports the changed makespan and leaves performance acceptance false. It never
uses priced graph durations in place of missing measured native durations.
Operator fusion and endpoint remapping must precede this scheduling pass.

Every native job needs its real endpoint, native engine, fixed duration, tag,
client, start phase, and explicit accesses. Durations must match the scheduled
program, including physical transport. Evidence pins the implementing RTL and
its separately measured timing/port contract by path and SHA256. Accesses use
stream-relative issue/response/commit/deadline cycles and VM-relative ingress,
bank enqueue and service cycles. The VM origin is the last VM edge at or before
the scheduled job start. Templates only apply at the declared recurring clock
phase; their phase period must repeat both clocks exactly.

Every tensor requires explicit physical base row, row count, native producer
(or declared external input/resident constant), consumers, and pinned allocation
contract evidence. Reads of native-produced rows require complete word-mask
coverage from actual native writes. Overlapping live allocations are rejected.
A C++ snapshot allocator is not a production allocation contract. Internal
reference/fixture tensors are rejected, even if their numerical results match.

The generated schedule is checked using
`tools/s81_suhc/static_vm_reservations.py`. Any missing binding, stale evidence,
unsupported native operation, latency mismatch, timing conflict, or unproduced
read prevents **all** dispatch and emits no partial execution calendar.
`qualified` remains false: source-backed native RTL replay, physically mapped
memories, digital links, die binding/timing and throughput gates are separate.
Compiler tests qualify only this lowering mechanism.

```sh
python3 tools/s81_compile_schedule/compile_calendar.py \
  --programs results/rtl/s81_ctrl_20261008/programs \
  --bindings actual-owner-bindings.json --contract actual-native-vm-contract.json \
  --out compiled-calendar.json
python3 -m unittest discover -s tools/s81_compile_schedule -v
```

The current 59 committed stage programs contain 2,367 jobs: 920 SU, 560 HC,
332 field, 210 collective, 168 service, 97 selector, 59 hop, eight collector,
eight Engram, four head, and one embedding. These programs are arithmetic
operator graphs with ASAP duration estimates. They do not supply the complete
native tensor producer allocation or fixed physical memory calendar. The
fullshape compiler test therefore proves all 59 programs reject absent owner
bindings, not that 2,367 native jobs have been implemented. SU/HC snapshot
addresses and ideal LVM10 response timing cannot be promoted to production
bindings. The native VM service, field/collective mapping and owner-provided
operand contracts must be connected before full-native dispatch is possible.

`lower_native_graph.py` now rewrites the actual 2,367 operators using named
native fusion rules: 704 graph operators fold into existing SU/HC/HCP chains.
It retains every original operation in exact coverage and inserts 80 required
HC raw all-gathers and 40 post-attention HSTORE producers before FFN projection.
The resulting 1,783 jobs are a structural lowering with unbound endpoints and
unmeasured native durations explicitly visible. They are not a qualified native
calendar. The normalized HCP implements HC fn/sumsq/rsqrt; the existing HBM op2
coefficient tail implements pre/post and Sinkhorn. They remain separate jobs
with the real TP4 gather between them.

`operand_layout.py` assigns the first actual field/SU buffers independently of
historical fixture/ISA addresses. It joins all 160 released wq_a/wkv/wq_b source
matrices and 640 rank fragments across 40 layers to QN/KV/QR buffers, preserving
literal source rank slices and scalar identity. QN/KV input data must arrive
from actual field roots and the TP4 collective. The allocation is an integration
contract; the producer packet tags, formats, writes and their fixed calendars
still need actual native implementation evidence. No tensor values are read or
generated. These production-layout candidates and full graph witnesses live in
`results/arch/s81_native_compile_1014/` with explicit incomplete status.

`write_itinerary.py` compiles fixed write staging capture/drain tables, preserving
source port, slot, job, tag, row, mask and event identity. Its independent table
checker rejects missing writes, changed metadata, storage overwrite, early
release and bank service conflicts. It specifies no dynamic queue arbitration.
The current four source-pinned observed demand patterns need at most three
register rows per bank (68 rows with individual bank sizing; 18 simultaneously
live), at most three captures per bank per edge, and at most two extra drain
cycles. The original write visibility deadlines are missing, so these remain
**diagnostic demand itineraries**. Production rebasing can change conflicts.
Actual staging RTL, physical paths, and compiled consumer/commit fences must be
verified before any of these tables become executable native programs.

`canonical_execution_join.py` joins the literal source operation catalogue to
all 324 canonical stage/rank programmes. It checks template identities, actual
elaborated engine and SU/VM instances, independently emitted literal operation
home assignments, pinned programmes/contracts, and exact
source coverage, then invokes the existing native fixed-calendar compiler.
Fused operations require explicit rounding/order proof; provider homes and
parent reservations cannot supply native leaf homes. An incomplete join emits
no partial programmes. Even a complete **local** join cannot enable chip
execution: global transport/producer-consumer, native RTL replay, physical and
throughput gates remain separate and mandatory.

The source replay in `results/arch/s81_canonical_execution_1015` verifies an
expected rejection of the actual screen14/2654-operation catalogue: all324
rank programmes are missing and its literal SU scopes contain no MTP operations.
The 10616 rank-operation obligations are 2654 source operations times TP4,
not 10616 distinct physical elements. The fourteen mechanism tests exercise a
synthetic positive and missing/stale/wrong-home/calendar/fusion mutants. They
qualify this compiler join mechanism only. The replay does not qualify a single
native canonical programme or the required MTP continuation.

Actual native instances are identified by `(die_id, instance)`. Repeated real
hierarchy names on distinct rank dies are legal; inventing globally prefixed
hierarchy names is unnecessary. Independent operation-home assignments still
select the exact physical die and implementing engine.

`source_locality_assignment.py` is a new compiler design pass. It builds literal
symbolic producer/consumer edges from the pinned canonical demand, joins actual
FIELD fragment-stage alternatives, and proposes non-FIELD operation homes with
integer alpha-expansion graph cuts. It preserves independent write bursts such
as W1/W3 and in-place versions; runtime expert alternatives use worst-case
boundary counts. Unanchored operations and missing input producers stay visible.
It does not use provider2L, catalogue position, fixture addresses or prices.

The first full-source candidate preserves all4778 instructions/7925 dependency
edges and1149 FIELD anchors;2654 SU instructions have10616 TP4 candidate homes
across42 stages. The equal-weight symbolic stage-boundary objective goes from
2818 to2282. This is a source graph metric, **not** a measured reduction in wiring,
bandwidth, latency or token time. Ten admitted mechanism tests cover real
producer grouping, source mutations and graph-cut correctness against a small
exhaustive binary optimum. The candidate provides no native physical instance,
programme, epoch or cycle. Native fusion/replication/capacity constraints and
explicit no-op programmes on unused stages still need implementation; the raw
candidate may split existing fused kernels and must not be adopted as-is.
MTP auxiliary programme coverage remains separate and unbound.

`--group-private-su` adds conservative same-tag colocation constraints along
private symbolic SU dependencies. This keeps the source MOE six-add chain and
QN/KV norm chains together. Groups may contain several implemented kernels;
colocation does not establish fusion equivalence or remove hardware/area.
The source replay in `locality_grouped0` constrains448 groups covering2010 SU
operations. All2654 SU operations still receive TP4 candidate assignments across
42 stages, with symbolic objective2391 instead of the unconstrained2282. This
is the stronger source planning candidate. Actual native kernel boundaries,
physical homes and programme/calendar gates remain open.

`verify_locality_candidate.py` independently checks literal template/rank
coverage, groups and the objective against the original source graph and FIELD
alternatives. The full candidate passes; changed templates, missing source-rank
operations, a fabricated objective improvement and a split colocation group all
fail. These are source design proofs; they do not establish native execution.
