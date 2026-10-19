# Complete final-FFN transport: model before source changes

The existing4480-pair placement cannot run on the current RD transport. This
packet proposes a complete mechanism for owner choice. It does not change RTL,
produce production calendar rows, qualify peer arrival ages or repeat the
already passed arithmetic sweeps. The current75-edge VS13 and63-edge POST
component ages, pre1008 and post1009 remain unchanged.

## Actual source cut

The actual bind9 graph has sixteen slices: sid=2*column+tier. East/west is a
1104-bit line split over four276-bit physical lanes. The V rung is276 bits.
`ot_s81sl_rstop` only assembles XQ/XB fragments from V; the XR RD decoder admits
E/W and optional B, and cannot receive a full RD from V. The control injection
does not deliver its own RD back to its local XR. Current V bits are truncated
if a full RD is sent with the V direction.

Of4480 assembly pairs,2240 require a tier crossing,1960 use the same tier at a
different slice, and280 need a local copy. Legal contiguous packing makes1568
packets:896 with two pairs and672 with four. These divide into784 cross-tier,
686 horizontal and98 local packets. No source/destination row boundary or leaf
boundary is crossed by packing. Every pair is still read from its actual source
capture rows and ends in its exact VS13 assembled row.

The actual direct AND landed V bridges are columns2,5,6. Column3 goes through
the GUNIT, column1 through bank service, column4 through host/service paths;
columns0/7 have unlanded end rung lanes. They are not interchangeable direct
RD bridges. The model extracts the endpoints and K/E/station ages from bind9,
not a nominal mesh. Source hashes cover die, land plan, XR, rstop, cap, endpoint,
placement and encoders.

## Alternative A: existing E/W/B with finite turnaround

REJECTED as a complete solution. A same-tier neighbor SRAM turnaround could
supply the280 local pairs, with one extra staged write/read and an explicit
scratch lifetime. It cannot cross the tier cut. E/W and the +1/-1 S, +2 N
inter-die circuits preserve tier. B exists only on s3S/s4S and provides no N
receiver or north/south RD bridge. Adding finite buffers and additional hops
cannot connect2240 assembly pairs across this graph cut. The480 peer result
packets also need data to/from the tier of their actual end-link circuit.
Consequently there is no finite complete edge/buffer price for A on current
source. A slot-only continuation would misrepresent a missing mechanism.

## Alternative B: typed V RD plus local delivery (recommended)

Keep all output-row ownership, seven-expert ID-order arithmetic and existing
capture/assembled/combined rows. Introduce a default-OFF typed RD extension:

1. The XR send config gains a local-copy bit44. A local RDOUT packet uses the
   existing full-width ci_b, ci_dir=0, and the new bit enables an explicit local
   delivery at rstop. The delivery then uses the existing XR RD unpacker and
   write port. This handles different source/destination leaves too; a local
   copy is not a rename of the captured data.
2. Stream a complete row PAIR per V word instead of retaining a full1104-bit
   packet. The exact proposed format is valid1 + kind3 + leaf3 + even row10 +
   data256 =273 bits, with three reserved high bits. The receiver is the actual
   direct V partner; no multicast destination mask is needed. The existing
   lo_sel pair register supplies each SRAM read, existing ci_r/vo carry it,
   existing receiver iv/dl_vb carries it to a new typed V_RD decoder. Reuse the
   existing XR rdat/unpacker with rnp=0 and upper unused payload zeroed. Existing
   XQ/XB assembler is unchanged. No payload compression, BF16 reinterpretation
   or numerical conversion occurs. Each source pair advances row by2. V_RD must
   be recognized before CTL/SC handling and must never be reinjected as a V CTL.
   The proposed encoder is pure Python evidence only, not current RTL support.
   Every other V/own/XQ/XB source reserves distinct slots; collisions fault.
3. Reuse the existing VP SRAM scratch rows480..487. If a source is not on an
   actual V bridge, first RDOUT to that bridge's scratch, then RDOUT on V. If
   the destination is not the partner bridge, stage there and RDOUT on E/W to
   its final rows. The nearest legal bridge minimizes actual horizontal hops;
   tie breaks use the lower column. No arbitrary full-die virtual V edge exists.
4. Reinject/deliver only one packet at a time in the reference static schedule.
   This needs one scratch slot per used leaf, no queues or credit protocol.
   Both read/write ports, every line lane and every V fragment must be reserved;
   a two-source collision is a fault, never arbitration. A source capture lease
   lasts through its RDOUT, scratch through re-read, assembled through VS13,
   combined through all three peer sends and own POST, pre/post through all
   four rank POST completions. Scratch480..487 is disjoint from the proven
   rows but requires the actual dead-VPX lifetime inventory before admission.

The complete enumerated model routes all1568 assembly packets and480 peer
result packets. Peer circuits are source ES→peer WS for rank+1, source WS→peer
ES for rank-1, and source EN→peer WN for rank+2. Each requires real on-die
staging before and after the actual reliable link, including the needed tier
crossings; none is replaced by a direct abstract peer copy.

Complete data submoves:3129 horizontal,1264 typed V,158 local copies,480 end
links =5031. There are30528 physical276-bit horizontal-lane slots,5056 V
fragment slots, and960552-bit end-link flits. Local logical payload143360B
and peer payload61440B are preserved; they are distinct from wire occupancy.
Each submove needs a real RDOUT and a config. Including80 VS13 and320 POST
commands gives10462 command occurrences before template deduplication. Host
calendar KIT/END and job reload cost is additional, not hidden inside these
figures. The model emits the literal config/RDOUT words for every leg; local
bit44 and typed V are explicitly marked proposals that current RTL ignores.

The rejected full-packet serializer would add1104 payload FF per slice,
70656 across all64 slices. The preferred pair stream adds ZERO payload FF if
existing lo_sel/ci_r/vo/iv/dl_vb/rdat storage is reused as proposed. This still
needs elaboration/mapping proof; no claim is made that logic optimizes away
all old full-packet registers used by other paths. Existing VP scratch reserve is1024 bits
per leaf, at most327680 bits across all320 leaves, using existing SRAM capacity
and zero extra SRAM macros. Global in-flight capacity is one full packet.
The pair-stream control/enable distribution and full-width local delivery mux
still need mapped sizing. A lower bound is nine kept mode copies for273-bit
selection and36 kept enables for1104-bit local delivery with31 data loads plus
one state load:45 FF per slice,2880 across64. Hierarchical precursor generation,
reset landing, collision faults, typed row+2 logic, capture enable and clock
buffers add cost;2880 is not a SAFE proof or final area claim. The existing
pair counter can be reused only after exact edge/row proof. Reset applies to
valid/control, not payload. No new runtime queue is proposed; any successor
queue exceeding2kb must use a real SRAM. Exact mapped cell area/clock power is
OPEN pending the approved smallest source cut. Use each actual local clock;
no new balanced die-wide tree or single high-fanout control root.

No physical channel widening is proposed: V uses the existing276 tracks at
one occupied edge per row pair. The full serializer would use5056 V slots;
the pair stream uses4160 (2240 local-assembly pairs plus1920 peer-path pairs). Existing forwarded half-cycle relay stations
and landings remain mandatory; no newly inferred combinational wire may span
405um. The enumerated routes include883 traversals of currently unlanded end
horizontal lanes: these are explicit open obligations, not source-qualified
calendar edges. No new gate is ready before reset/fanout/depth/storage/clock,
landing/reach and full physical slot checks.

Proposed edge chain, to be measured on the exact successor: source CTL pin →
XR classify/cmd → actual VP SRAM RDOUT → existing pair register → typed
ci/vo word OR full local packet → actual landed V link age → existing receiver
V delivery → typed XR unpack → actual destination SRAM write.
For staged routes this chain repeats, and E/W legs use each extracted link age
plus two rstop edges per hop. Peer routes additionally require source-qualified
reliable-lane and PHY age under the reserved host/control traffic. The compiler
must subtract each actual ctl_path age from pin-issue cycles and reserve those
control-line slots too. Existing lower_vpx CFG_AT=3/RX_WR_AFTER_PIN=5 is pre-XR2;
V injection is source-qualified7, but that is not a qualified replacement for
RD send/receive ages. The actual peer POST age is therefore NULL, with formula
last qualified peer RD write + actual CTL-to-VP age +63. A guessed integer is
not a bound. Reuse ep8 arithmetic binaries; build only the new transport cut.

## Alternative C: source-owned capture redistribution

A global64-word-aligned, same-tier source placement can avoid local assembly
crossings only by changing real frame ownership/ROM placement, not merely cap
addresses. Rank-local1280 words require20 complete64-word beats across16
sources. A balanced assignment uses four128-row slices and twelve64-row
slices, versus current80 each: max work/weight mass per slice grows60%.
There are two128-row slices and six64-row slices per tier. Weight bit total is
unchanged, but maximum per-frame down rows rise10→16 and legal phases/element
capacity/calendar emission must be rederived for every routed/shared matrix.
The actual cap first-row/rcnt and ROM frame row tags must agree, preserving
rank output ownership and the global head G8 beat order; changing owner() alone
would break downstream contracts. Leaf gathering/local copy remains necessary
unless64-word placement and cap output ABI are both rebuilt. More decisively,
the fixed peer circuits use S for two peers and N for one, so broadcasting the
replicated residual requires tier crossings on some peer legs regardless of
where a result is produced. C therefore does not replace a real tier-crossing
mechanism for the COMPLETE segment. It is a later optional load-balance study,
not the lowest-risk next implementation.

## Validation and requested decision

Eight fleet Python tests validate exact coverage, source pins, all actual landed
bridges, all480 real peer circuits and causal refusals for missing/duplicate/
wrong-owner/wrong-row pairs, phantom tier edges, stale sources, missing calendar
reservations and leases. Even supplied arbitrary positive flags/ages cannot
admit this model. These are architecture tests, not transport RTL PASS.

ROOT choice requested through the coordinator: approve B as a source-only,
default-OFF transport mechanism, starting with the smallest local-copy plus
typed row-pair V/SRAM-staging RTL cut and exact causal mutants. No full-die
build, gate, arithmetic sweep, main edits, timing masks or native qualification
are requested. Gain/G8/NX/XB/head physical/full-token remain separate gaps.

## Minimal source cut and full-token price prerequisites

Before any full implementation, independently price a two-slice cut with:
actual VP SRAM source RDOUT, real XR send config, typed273-bit V row-pair,
existing landed276-bit V timing, receiver XR write port, and SRAM readback.
Include same-slice different-leaf local delivery and staged two/four-pair
packets. Check all256 data bits, exact row+2/leaf/order, exact source/destination
edges, consecutive single-pair receives and simultaneous last-write/new-receive.
Mutants must corrupt row, leaf, pair order, last pair, V type, local delivery,
reset release and an intentionally colliding RD/CTL/V slot. The existing
ub&&un!=ul collision rule permits last-write/new-receive in principle; only
real source-bound replay can establish sustained one pair/edge. No new full
die or arithmetic bench is needed. Preserve all initial failures.

The supplied model gives every read and write port its exact pair-slot demand,
all actual physical line-lane and V slot demands, and control words by rank.
These are sustained-capacity lower bounds, not a priced static latency. The
conservative reference is globally serialized packets with explicit stage
leases; its span is the sum of qualified per-leg read/control/propagation/write
and drain intervals plus host reloads,80*75 owner-combine edge intervals,
320*63 POST intervals where those engines cannot overlap, and actual peer
link ages. Parallelism may reduce this only with a collision-free complete
calendar. A total full-token cycle delta remains NULL because the new mechanism,
XR2 RD path, host reload and link ages are unmeasured and883 unlanded end-hop
traversals have no legal landed timing contract. Adopting a numerical token
rate before these are measured would hide the very cost under review.

Root can approve a bounded source-only pricing cut separately from full transport
admission. Exact cell area cannot be established from FF count alone: the
existing technology library, retained mux/port/register mass and clock/reset
buffering need a canonical mapped synthesis of that cut. This packet makes
that dependency explicit rather than substituting guessed area or link ages.

Measured model inventory (not RTL timing): busiest actual physical V lane requires
520 pair slots; busiest E/W lane196 full-beat slots. Busiest logical SRAM
read/write ports need248/208 pair edges. Every directed external circuit carries40 beats
and has a capacity-only lower bound53 edges at0.764353503 beats/edge; startup,
host traffic and return/drain ages are additional. The combined bandwidth-only
parallel lower bound is520 edges; the reference serialized read/write work is16960
pair slots before any propagation, CTL, reload, arithmetic or drain. Those two
numbers bound different execution assumptions and are not a measured token
delta. Across ranks, control occurrences are{'0': 2806, '1': 2494, '2': 2494, '3': 2668}, requiring at
least85 128-row jobs if two rows per job are reserved for KIT/END, before the
actual ordered walker/host loading constraints. No empty reservation set is
admitted.
