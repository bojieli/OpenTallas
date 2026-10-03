The x-need successor belongs to the existing qpipe scope
======================================================

Pinned diagnostic: 2078c269c4a14dd566b96a73b52a272582faa13f, ds15_elem_q.
Its repaired control-loop screen is 634.6712901 MHz, -742.618774 ps at SS
0.833 ns / 60 ps setup uncertainty: n_c[1] to n_q[2]. This is placed, ideal-clock
screening of the baseline; it is neither routed sign-off nor a qpipe verdict.
The inherited 281bde911 RTL/jobs remain unchanged. Their word-walker last-unit
register does not remove this x-need successor/enable cone.

One proposed successor, no sweep
--------------------------------
QP_NEED_LOOKAHEAD=0 is a proposed default-off parameter in NEW module copies.
Retain NB2/NSEG8/NCH16/XF4, FAST1/PP1, MTP1/EARLY1, HC3 and the real four
4096x274 macro instances. Do not reduce pipeline, lanes, chunks, positions,
classes or ROM words for qualification. QP_CAP and QP_XS remain bound to the
reviewed inherited case; they are not free search dimensions.

Keep each existing canonical/shadow need-state register and each nA/nB/nQ2
register. Add per local HC copy a 72-bit current/next class-priority table and
11 successor facts: next class (3), first next-q class (3), last unit, next-class
valid, last round, last sub-block and last position. The current first class
is already in the table, not another three fact FF. Add one async-invalidated
valid FF per local copy. Total increment: 249 data FF + 3 valid FF = 252.

At go, seed current and next tables from the exact same source sbf0/sbf1 and
family selection as nA/nB. At a q transition, current takes the already-prepared
next table; the next table refreshes from the new stable nB. A sub-block needs
eight round ends even with one unit, leaving >=8 accepted beats between q
transitions. At a new MTP position, reseed from the same fF0/fF1/base_live as
the source restart, not the prior q's table. Empty go/reset invalidate; no
stalled beat advances state or facts. For each accepted beat choose the exact
successor, then refresh the facts for that successor. No two-cycle walker,
extra bubble or reduced field issue rate is permitted.

The Python transition gate tests the mathematical invariant facts=F(current
state), all class priority masks, unit boundaries, round/sub-block boundaries,
full eight-position walks, stalls and model mutants. It does NOT prove a
cycle-accurate implementation of table warmup, reset, refill or the source
caller. These are mandatory actual RTL assertions/gates before adoption.

Cost and composition
--------------------
The model consumes exact archived uarch_model.py DFF basis and SS cell blocks
read from an existing live ORFS container. It prices 252 FF, a deliberately
unshared priority/bit-mux construction reserve, 120 local control buffers and
37 added clock-tree buffers (eight-sink tree reservation). Total reserved cell
area is 486.66582 um2, or 973.33164 um2 at 50% placement utilisation. This is a
construction reserve, not measured mapped occupancy or a guarantee of slew,
hold, clock or slot fit. Internal metadata reservation is 252 logical wires;
actual cut tracks and finite capacity require the station placement ledger.
External ports, external bits/cycle, ROM/SRAM bytes/cycle, MAC work and golden
CSA/adder state do not increase. Current nA/nB/nQ2 are not charged again.

The proposed x-need repair adds zero fill cycles and retains II1. It preserves
the inherited qpipe +2/+3 cycle prices, rather than putting an extra cycle in
every walker step. New token delta is deltaL * source-owned q-op count / 1.2GHz,
which is zero for deltaL=0. Replicated area is R * 486.66582 um2. Scenario C
model direction is owner-approved but its current count/slot handoff is still
pending; no stage/die/rate table was regenerated. Existing element footprint
rows remain inputs to that new replication. The archived S58 pricing is
historical provenance, not a current Scenario C result. Other three designs
receive no hardware or latency change from this DS ROM-only successor.

Before RTL/admission
--------------------
Bind current Scenario C finite slot, local clock/reset/PG/escape tracks and
loaded SS60/FF25 arc budgets with Maxwell/Archimedes. Check both the shallow
state-update cone and successor-to-facts refresh cone, plus go/init/restart.
A register renamed as lookahead while retaining the old priority feedback
cone is not closure. Clock target and uncertainties remain unchanged.

Source preparation must also carry the already-qualified mandatory second-row
config decoder correction in BOTH reference and successor. The inherited
qpipe copy retains the original truncation expression at its live/shadow row
writes. Its old same-bug differential PASS cannot be full arithmetic golden
qualification. Preserve that baseline and all original failure receipts.

Next actual gate, after reviewed source package
----------------------------------------------
1. New reference/candidate namespaces, same corrected config contract and
   unchanged golden arithmetic/CSA source. Immutable synthetic ROM input-only
   image; independent numerical assertions at public partials, flags and tags.
2. Whole full-shape q element: consecutive accepted inputs, production cadence,
   delayed/mismatched/duplicate inputs, class/unit/q/round/position boundaries,
   FP4/FP8, config decoder last address, reset at each active seam, empty go,
   gating/wake, fault ownership and complete drain. Preserve exact first fail.
3. Require stale last-unit, stale priority-table/q, bad restart, and II2 mutants
   to produce explicit semantic DIFF, not compile errors or crashes. The II2
   control must fail accepted-beat throughput and output timing/order assertions.
4. Compare actual accepted beats, issued ROM words, public partial cycles and
   total operation latency with the full source-shaped baseline. No helper-only
   or reduced-element substitute. No adoption until measured gain and in-context
   extracted SS setup/FF hold plus real ROM/ICG timing close.

No RTL, HDL compile, simulation or physical launch is authorised by this model
record. No new PVE2/PVE3 work. Existing live jobs are not edited or restarted.
