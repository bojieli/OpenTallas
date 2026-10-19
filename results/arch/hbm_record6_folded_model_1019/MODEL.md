# R6 folded exact reduction: executable source model, build HOLD

Identity: image6 / fixture k_layer6 / price4 / q_norm.ss occurrence0;
original A VM46336..47615, 1280 FP32 words; authentic R VM49920 is40a2a1ed.
This packet changes no RTL, compiler, golden, timing contract or programme.
It is a small integer/symbolic analytical calculation, not a numerical PASS.
Baselines db11c6d6c / 5f0ee6d0d remain intact.

**Recommendation for ROOT review:** retain40 independent chunk stations,
one reused adder per station, plus compare1 versus4 global adders. This removes
the skew-delay architecture. Four total adders saves more area but its honest
calendar is over an order of magnitude slower. No prototype is authorized here.
ROOT confirmed that genuine private8-operand compute stations are admissible;
their distinct input/adder/state/ports must exist in the actual successor.

## Exact arithmetic and complete coverage

The original four whole-quarter square emits remain: per group quarters
0/1/2/3 contain128/32/128/32 live words, hence16/4/16/4 chunk stations.
All512 physical source lanes/pin captures are conservatively retained, though
only320 words per group are live. Four groups cover all1280 original words.
AA at M1 squares each original A with original FP32 rounding. Absent B/C/D
read identities must borrow that actual live A, as established by the R23 fix.

Each station holds its own eight words and performs exactly seven dependent
FP32 additions, x0 normalized to canonical +0 when zero, then +x1 through+x7.
After that, reuse the same physical adders for canonical local dyadic joins.
The leftmost station in each subtree performs that subtree's join. Its own
chunk is already complete, and both child results remain held until operand
selection captures them. No station executes two operations concurrently.
Forty result registers retain child outputs; no read of an overwritten child.

Quarter/group boundaries split into the same26 canonical fragments as db11:
2x16,8x8,16x4 chunks, covering160 chunks. Quarter2's middle8 fragment is
formed from the genuine local4:8 and8:12 children, without an associative
substitution. There are1120 chunk additions,134 local joins,27 global joins:
1281 actual arithmetic operations. Canonical padded zero subtrees160:192
and192:256 are real golden padding. No live value is replaced by zero.

model.py constructs the entire ordered expression and proves its structure
equals the untouched256-leaf golden tree. Every variant's expression SHA is
f82ff124f8a26899d7bb5aed78374e449c2bd44b3d94d2297cd60d9b09d7c015.
Three executable analytical mutants refuse swapped words, reversed sibling
pairing and early feedback. Logs are structural fail witnesses; they do not
establish numerical RTL exactness or prove the authentic scalar by simulation.

## Fixed schedules and real control ownership

NL9 conservatively reserves2 added registered mux/transport stages plus
the source LAT6+OPR1 node. This is a stage budget, not timing qualification.
All operations reserve the whole9-edge recurrence interval, including
independent ones; the model never assumes one-edge issue throughput.
Two select stages are also paid in storage. Physical relay stages beyond
these budgeted local selectors remain additional H, not free.

FILL is unchanged from the exact160-sector/24-bank model: one command per
bank per edge, commands0..7, latest native store commit28; first emit32.
There is no prefetch before verified producer visibility. Only16 stream
edges separate modeled producer completion1463.31 from R6 start1479.31;
no actual sector-arrival proof or producer placement is available.

For40 local stations, four whole-quarter front words change only by group;
emits32,144,256,368 at NL9. Actual vb, addresses, positions and live counts
advance per group. Original producer-to-native physical relocation, if any,
is extra. All AA/backend fields remain genuine and unchanged throughout
this record, reserved against every other record until the final consumer.
The LEAF offset bank is installed once before the first group and never
overwritten while live. No backend-idle substitution or fake group0 hold.

Per-station input pin registers capture the genuine ro_x/ro_v only at the
group's actual output age A and retain them through the local reduction.
The existing pretree's unconditional x1 update must become a real held
capture; a shadow delay chain cannot replace it. Capture enable needs kept
copies: a single enable driving32 payload FF plus valid already exceeds32.
At least two useful local copies per captured word are required before
accounting for ancestors. Input liveness, command/group/epoch, stage age and
last-use checks remain real source work, not silently provided by this model.

Each8-word station's operand mux is private. Its sequential counter selects
the original next word; accumulator feedback selects that station's last
actual adder output. Local joins select a fixed legal sibling. Two registered
select stages must hold the selected real operands until OPR captures them.
Selection/valid/control move with the operation, with no new op before its
reserved completion. No credit, readiness arbitration or backpressure.
model.json records every operation, source hashes, physical station, start
and completion edge, and verifies all resource reservations are disjoint.

Global collection uses26 fixed entries of56 bits: FP32, valid, group2,
base8, size5, epoch8. Each entry has one fixed writer and retains its payload
until its single canonical consumer has captured it. One global adder reads
two entries per operation through registered selectors. The four-adder
alternative needs four real selector/operand paths and distinct operation
reservations, not four nominal names over one port. Eight physical operand
reads are acceptable FF-bank reads only with the full mux/fanout cost.

## Honest latency and the four-adder alternative

Values below use **illustrative** A29 and RF route L32; H=0. Root is the
global adder output. Collector output register adds1; actual root-to-qcore
LOAD/EXPORT adds22; RF L+2, RF_LOCAL drain2, native completion20.
Thus R_done=root+79, plus any difference in A/L and all unresolved H.

| Architecture | Root serial | Native R serial | Stream | Extra vs182.18 |
|---|---:|---:|---:|---:|
|40 local+1 global, NL9/period112|588|667|889.33|707.15|
|40 local+4 global, NL9/period112|534|613|817.33|635.15|
|40 local+1 global, optimistic NL7/period80|450|529|705.33|523.15|
|4 total, NL9/chunk emit period112|7451|7530|10040|9857.82|

The4-total version requires NEW per-chunk liveness/front lowering,64 emit
slots,8 live words per participating quarter. It cannot capture a full
128-word quarter into its one private8-word station. Every chunk follows
the same seven adds; the quarter's one adder performs binary carries inside
that chunk's112-edge slot. Global joins then reuse q0's actual adder after
all local work drains. Its26-entry fragment bank remains finite. This is a
valid abstract resource schedule, not the best possible four-adder schedule.
Its new input gathering must select an8-word chunk out of128 physical lane
outputs on full quarters: eight16:1 data paths per full quarter, with real
registered mux/transport and fanout cost. Its actual capture age is not
measured; that added ingress cost belongs in A/H, beyond this illustration.

The41-adder candidate keeps four existing-shape groups and is the balanced
area candidate;44 adders buys54 serial/72 stream edges for three more real
nodes and selectors. None meets the original record price. Original window
is not a hard ceiling: all dependent q_norm.rs/y and every colliding shared
SU/control/RF/native resource must be shifted honestly in the token model.
These numbers are not achieved latency bounds because A/L/H remain open.
No single-user rate, throughput or multi-user isolation claim is made.

## Explicit storage, ports, physical cost and remaining holds

Each station's actual operands are eight fixed32-bit input registers,
256 bits, privately feeding that station's adder. There is no coherent
runtime-indexed whole-record array and no sharding to avoid SRAM. All512
input payload/valid pin registers are retained conservatively:16896 FF.
Forty result/valid registers add1320 FF. Two-stage local selection at two
33-bit operands per station adds5280 FF. Fragment bank1456 bits is below2kb;
global two-stage56-bit operand selectors add224 FF. Local schedule state
reservation1024 FF and tag/fault reservation128 FF are separate.

At exact1dad69123 LAT6 source, adder register bundles are120+98+102+73+71+35
=499 bits; OPR65 and seven mode bits give571 per unchanged node. Forty-one
nodes therefore add23411 arithmetic FF. Total explicit FF reservation49739
precedes useful control/capture/reset copies, fault comparators and routing.
This is **not** a synthesized cell census or a complete upper bound.
Reference all-DFFHQNx1 cost is14503.8924um2 and23612.893904fF TT CLK.
For44 adders, add1713 node FF and672 selector FF:52124 total before copies,
15199.3584um2 and24745.139264fF reference FF-only cost. Real arithmetic,
mux/decode, write-enable, register masters, reset trees and CTS cost is NULL.

Forty8:1 word-select muxes and forty sibling/feedback selects are real;
global26:1 selection requires two paths per global adder. First pin capture
is a512x33 bus (16896 bits), with320 live words (10560 payload+valid bits)
per group. Fragment output peaks at7x56=392 bits per group. Mux/control/
signal tracks, crossing width, local root placement and parent slot are OPEN.
Reference area alone requires at least29007.8um2 at50% util, before all
combinational arithmetic and routing. It is not a floorplan slot grant.

There are no NEW operand SRAM macros in this folded mechanism. Existing
native VM FILL store/SRAM and authentic RF must still be real. FILL writes
finish before source reads; none overlaps lane output writes (DST_NONE).
R is a distinct address with real class5 masked RF-source DRAIN, only after
actual RF commit; untouched seven sector words retain OLD values. No
same-address SRAM read/write behavior is assumed, and no SC2 or nominal
Elmore CQ is admitted for timing. Existing SRAM clocks/access/hold, RF
8192-bit storage mapping, R sector port and producer binding remain OPEN.

Reset aborts the episode, clears operation/fragment validity and faults old
epoch reuse, then requires producer/descriptor reinstallation. Raw operands
need not reset: no valid may emerge until its actual new capture and complete
pipeline lifetime. Two face landing stages and existing inherited reset
stages are retained and priced; exact copies and stopped-clock behavior
must be established in source. No long delay>=3 survives as a shift chain.

Original command store has7111 enforced/8192 physical slots,128 per bank;
it is not a128-command whole-engine store. Four versus64 emits are model
counts, not packed programme capacity proof. Exact new instruction/literal/
index packing and per-bank occupancy remain NULL; no modulo overwrite.

Build HOLD: resolve exact source A/control pipeline, root operand/qcore
binding, true RF/native route L and host H, actual mux/control/fanout/reset
cost and complete token/calendar composition. Then ROOT can approve a
source-only minimum numerical prototype. No RTL, synth, gate or full vehicle
was launched by this packet.
