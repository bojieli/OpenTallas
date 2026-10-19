# XR6 whole native graph copy and independent packet-bank model

MODEL ONLY. No RTL, synthesis, simulation, place, route, helper or gate changed.
This extends 67954d13c and preserves its unsafe original results. The actual
native vehicle is **XR1 / HB=0** at source
7ef9383db5788cbb9428ccc264bb34484071b541, XR source SHA
b10a2c142dbf31e465f382b7f6cd3c6b354cd90be536ae015d159bcfe9f1bee6.
ODB SHA 078ca172072d4158e7ae2e53b07fad9c2756932f211b79534efe7856794532ba.
The original native graph has 95,868 cells, 16,789 FF and 357 unsafe roots.
**This census cannot qualify HB=1**, its B input capture, or its separate wide
registered bo gate. Q producer selected ceaed19c4 historical HB1 vehicle remains
distinct; preferred uniform BF16 wire profile 88c536319 changes no generic XR
hardware. No upper payload or live header is removed here.

## Whole graph fixed point

For every original nontransparent native cell n, choose c[n] copies. Every
original endpoint pin on consumer m requires c[m] distinct pins. Recompute
c[n] = ceil(sum(c[m] for every real endpoint pin)/32), monotonically until
stable; external output pins remain one endpoint each. Primary inputs remain
one physical pin. BUF/INV are transparent for counting, with original branch
polarity to be preserved by any eventual source implementation. Distinct input
pins on the same target count separately. Iteration covers data D, asynchronous
SETN/RESETN, feedback, ordinary combinational inputs, ties, and upstream state;
clock pins are priced separately. Original graph zero-load nodes stay present.

The deterministic construction orders endpoint copies and partitions them
among their source copies with at most 32 pins per source. It changes no state
edge. Native gates retain their exact functions; copying arithmetic is not part
of this XR control-plane repair. Complete copied-cell incoming-owner ledgers
are in model.json. They bind D/control/reset owners, rather than just quoting
output-load counts. This is a constructive **graph capacity model**, not a
kept RTL implementation or a measured post-synthesis graph.

| Quantity | Native graph model, 32 | Sensitivity, 24 |
|---|---:|---:|
| Added FF | 421 | 919 |
| Added combinational cells | 136 | 199 |
| Added tie cells | 0 | 1 |
| Added native cell area, um2 | 175.48488 | 371.11932 |
| Added TT clock pin capacitance, fF | 194.892316 | 425.451529 |
| Added FF clock pin capacitance, fF | 211.845850 | 462.472120 |
| Maximum raw input logical pins | 9 | 16 |
| Added data edges in graph construction | 0 | 0 |

Native FF areas and CLK capacitances are read independently from pinned TT and
FF Liberty files, with complete hashes in the model. Clock tree, wire, physical
hold repair and legal placement costs remain open. The 32 model converges from
529 to 556 to 557 extra cells; stopping after the first partition would miss
28 cells. The old +408 FF floor and naive 4995 ancestor clones are not this
construction. No header-capture FF must be copied in the 32 model; the complete
upstream graph reaches a fixed point with input max9. Copies of the broad RD
classifier are independently consumed useful decision cones; eventual source
hierarchies must preserve those boundaries against synthesis merging.

Of the 421 additional FF, 420 use the actual ASR master and one copies the
existing second face reset FF. The four internal region reset FF become
16/9/4/3 copies, total32. Their exact D owner is existing sync_q[1], now32 D
pins. The second face reset state would otherwise drive34 RESETN pins, so it
becomes two same-edge copies. Its D still comes from the original first face
FF. Raw rst_n remains one physical D load. The 2 face +2 synchronizer +1 region
edge ordering is unchanged in this native graph model. Initial values,
asynchronous assertion/release equivalence, source relay representation and
physical recovery/removal remain to be proved; do not transplant the old
25-leaf reset-only proposal or claim reset qualification from these counts.

## Actual packet storage and lifetime

The source has five independently live destination-leaf packet buffers. Each
is 1024 bits, with its own ub, un, ul and ur state. The input rdat bus is shared;
there is at most one RD destination write per edge, but up to FOUR ub lifetimes overlap in a legal reset-origin trace. Each
packet auto-advances on every busy edge and holds at most four pairs, so one
arrival per edge cannot establish five simultaneous live packets. The hardware
has five parallel read lanes and updates all five sw_d even when invalid; the
peak qualified RD-store read is four lanes. A separate CTL row-write bypass
can additionally assert sw_v on an idle destination, so total qualified output
ports may still be five; CTL never grants another packet-store read. The reachable-lifetime exploration in
model.json checks every legal destination/count transition from reset. There
is no index selecting a leaf out of a coherent shared array. Within one leaf,
un selects four 256-bit chunks of one captured packet, not four generations.
This supports treating the existing five stores as five genuine local 1kb
packet states in the model. It is **not an adopted owner waiver** and not an
artificial subdivision of a coherent larger indexed store. This does not prove that a shared multi-read interpretation is forbidden: the
five banks have one common producer/broadcast data bus and destination decode.
Owner selection must resolve that interpretation; exact source-level proof is
still required before choosing a physical implementation.

The actual producer selector is re ? eb : rw_ ? wb : bb, where re/rw_
combine registered E/W valid, K_RD/K_CL and this-slice mask; HB0 removes bb.
rl0 selects the destination with rwe[k] = rdv0 && rl0==k. The same stage
registers rdat=rdb0[52+:1024], rrow=rdb0[40+:10], rnp=rdb0[50+:2]. At
the next edge rwe_c[32*k+i] updates the corresponding 32-bit slices of ud[k];
rwe[k] updates only that leaf ul/ur/ub/un context. The source replication has
rwe_c equal to rwe by construction, but post-map retention/equivalence is open.
Every leaf has its own generation until its last un==ul output, including
legal OLD-last-pair / NEW-packet replacement on the same edge. ur+2*un is
computed from old context for that output. There is no cross-leaf read-index
or time-multiplexed arbitration in the source. The collective physical bank
implementation remains an owner choice, not inferred solely from RTL labels.

The 520-state transition quotient covers all leaves, busy/idle states,
1..4-pair counts, legal cursor positions, incoming RD and CTL row writes. It
contains20 legal final-pair replacements and60 early-overwrite collision
transitions. Nonblocking source semantics read OLD ud on a same-edge replace;
new packet pair0 first becomes qualified one edge later. The final OLD output
uses the old row/count context because sw_a and sw_d also sample pre-edge
state. CTL row writes retain their priority and busy-leaf fault; no event is
rescheduled. Reset clears ub/sw_v, not ud. After a new RD writes the packet,
its first qualified read is K+1. Reset stale data may still appear on invalid
sw_d exactly as in the original source; this is not a new data mask.

These are source-derived symbolic transition checks, not an actual RTL miter,
not random-initial-state simulation, and not a producer/compiler lifetime PASS.
The retained negative witnesses reject NEW-data replacement semantics, missing
early-overwrite collision, and omitting upstream clone propagation.

An SRAM replacement must respect **1024 write bits in one edge**, 256 read bits
per live leaf per edge, four qualified concurrent readers across five destinations, first-read K+1,
and OLD on final-pair replacement. A single ordinary 256-bit 1W SRAM per leaf
cannot accept four address writes in one edge. Four 256-bit bank macros per
leaf (20 total) can take four writes but require an explicitly priced output
selection/registered-pin plan and genuine OLD collision behavior; substituting
32x64 macros for width requires16 per leaf,80 total. No qualified family,
geometry, clock count or area is borrowed. A new 1024-bit-wide macro still
needs a priced 4:1 selection/output stage. No free prefetch edge, write striping,
ignored read result, static NP4-only specialization, or functional payload
truncation is allowed as an implicit substitute. Source choice remains HOLD.

## Remaining structural and token closure

Pin ancestry and reset waveform; source graph retention/equivalence (including
branch polarities and feedback); native mapped depths; all endpoint reach405;
legal square-ish outline and one full-width 40..60% standard-cell band; actual
clock roots/CTS/TT-FF spread<=80 and neighbor phase; PG/OBS/escape; macro ports
if storage changes; and cold/occupied-reset behavior remain open. The source
body and original mutants are unchanged. There is no full-safe receipt and no
route grant. The current whole HB0 graph model has zero added data edges;
no token benefit is claimed. Any source or macro stage changes must bind the
actual static compiler calendar and single/multi-user token prices before build.

Next: ROOT selects whether the five independent local states are acceptable,
then reviews a source correspondence/retention plan for this complete graph
model, separately modeling HB1 and any actual macro alternative. Do not run a
reset-only patch or another physical gate from this record.
