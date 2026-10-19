# HIDX minimal complete registered CSA physical coupon MODEL

MODEL ONLY, for ROOT personal PNG review. No new RTL, synthesis, placement,
CTS, route, timing gate, helper changes, or whole-parent admission. Exact
source/native evidence is eebf00b3d (coupon b8da0b2b6; retained map 3eef);
production HIDX source5af00a1ab remains unchanged and unsafe as a whole.
`MODEL.png` is a row/band allocation drawing, not a placed-native screenshot.
`ports.csv` enumerates all2609 actual proposed signal/clock contacts individually.

## Smallest complete boundary and exact logical ages

Retain all8265 existing native cells and2616 existing ordinary DFFHQNx1 FF.
Existing input operand captures are already present:288 payload FF,72
compaction mask FF,48 pair mask FF,192 quad mask FF =600 operand FF.
These600 physical FF are fed by304 real logical input pins, not600 ports.
The2016 existing selector FF are actual registered outputs and are not delayed.
The remaining288 `compacted` outputs are internal combinational gc. Import
only the corresponding288 unreset `s1_gc<=gc` FF from actual full parent
`ot_hbm_idx_topk_link_static_p.sv` lines273/431–432 at5af00a1ab. Parent S1
capture is unconditionally clocked and unreset; it does not use s1_v as a mask.

| Boundary | Pin bits | E1 after input sample | E2 after next edge |
|---|---:|---|---|
| lane_v / payload inputs |16 /288|Actual operand mask/payload FF|Next transaction may enter|
| pair_select |576|Previous/unprimed data|Existing exact24 copies per count|
| quad_select |1440|Previous/unprimed data|Existing exact24 copies per count|
| compacted |288|Internal combinational gc settles|Actual missing S1 capture publishes gc|
| clock |1|All existing input captures|All existing selectors + imported S1 capture|

Both output families now describe the same E1 input after E2. This is +1 gc
edge relative to the intentionally incomplete standalone coupon, +0 selector
edges, and +0 edges relative to the actual parent's S1 capture timeline.
No full-parent/token rate, area fit or end-to-end age qualification follows.
Maximum sustained functional initiation interval is one sample/edge by this
acyclic source structure; no measured new-wrapper throughput result is claimed.
No MAC, memory traffic, SRAM, delay line, queue or ring is introduced.

Native DFFHQNx1 Liberty is ff(IQN,IQNN), next_state=!D, QN=IQN. Therefore
288 real INVx1 on gc before D preserve the positive registered gc value while
retaining every canonical cell. No inverted data contract, after-output
polarity omission, or hoped-for mapping absorption is assumed.

## Reset and cold priming: actual unreset component contract

Reset endpoints are ZERO in this datapath component, matching original
source. There is no rst_n port, artificial valid output, garbage mask,
asynchronous/stopped-clock claim, or hidden reset stage. At startup outputs
are unconstrained. Supply actual lane masks/payload and provide E1 then E2;
only after E2 are all outputs specified for that sample. No datapath clock
stopping or phase-shifting is introduced. This cold-priming contract is
finite and deterministic, including allzero masks and arbitrary payload.

Actual full HIDX control contains separate resettable validity/transaction
state, while s1_gc and these selectors are unreset. A future parent needs
its authentic two-face reset/phase/POR protocol and native control ownership
proof. This coupon proves no resettable control, POR distribution, parent
admission, or safe use before priming. Adding a reset/valid interface would
be a separate source/protocol change with real FF, clock and age costs;
ROOT chooses that contract rather than this MODEL inventing it.

## Real native electrical load and priced boundary buffers

Use explicit fixed80fF per output under the current physical coupon contract.
The previous unloaded internal-gc arrival480.846ps is NOT reused as evidence
of loaded S1 setup, FF hold, or boundary timing. Exact same-image Liberty:

| Native master | Area um2 | Actual input cap fF | Output max cap fF |
|---|---:|---:|---:|
| DFFHQNx1 |.29160|D .558822; CLK .474736|46.08|
| INVx1 |.04374|A .619928|46.08|
| BUFx8 |.17496|A .852045|368.64|

Raw FF and existing selector INVx1 cannot drive80fF legally. Price one real
function-preserving BUFx8 at EVERY one of2304 output pins, including all288
new gc FF. Retain canonical cells; no replacement reoptimization assumed.
Each original output driver now sees .852045fF BUFx8 input plus its local
wire, and each BUFx8 sees80fF external load PLUS extracted wire. Each port
has a real registered ancestor through a transparent buffer; no other logic
is admitted after capture. Transparent full-driver census still includes
all FF/comb/input/tie roots and all buffers/endpoint ports. Expected unchanged
max27 is a structural prediction, not a newly audited native PASS.

Input contacts remain source-pinned canonical real D endpoints: lane_v low
byte27 loads, high byte12, payload1. Native measured raw maximum input
burden15.088194fF; input FF clock cap and count actual12-D load6.705864fF
are retained. New S1 cone adds288 INV input contacts(.619928fF each),
then288 FF D contacts(.558822fF each). No output is treated as zero load.

80fF is the explicit coupon interface obligation, not a measured parent
consumer load. An alternative using smaller actual parent loads must bind
all2304 exact parent consumers and extracted wire/caps and receive ROOT
budget review. Parent selector merge D/comb roles differ and cannot be
replaced by a generic one-DFF assumption. Neither alternative certifies
whole-parent fit. Native TT count body389.826554ps and slew126.87ps remain
original source evidence only. New S1/output-loaded paths, actual IO budgets,
FF-hold/minimum CQ, SS, and neighbor clock reference remain OPEN.

## All real costs and physical geometry

| Inventory | Cells | FF | Standard area um2 | FF clock cap fF |
|---|---:|---:|---:|---:|
| Exact retained coupon |8265|2616|1151.49924|1241.909376|
| Missing S1 capture |288|288|83.98080|136.723968|
| Required pre-D polarity INVx1 |288|0|12.59712|0|
| 2304 true80fF ABI BUFx8 |2304|0|403.10784|0|
| Candidate before CTS |11145|2904|1651.18308|1378.633344|

Native input/clock/output signal wires andPG are not area-free. This MODEL
has no literal endpoints and adds no constants; ties required=0, not a future
constant-repair exemption. Before CTS, all11145 real native cells need22290
native VDD/VSS terminals connected to same-role rails. PG geometry, vias,
coverage and no shorts remain OPEN, including newly created CTS terminals;
apply tested PG binding before any clock-cell protection, then independently
audit every actual terminal rather than trusting network-connected warnings.

Outline140.4x140.4um; core[2.16,2.16,138.24,138.24]; aspect1;
site.054x.270um with2520 sites per row and504 whole legal rows. These
site/row dimensions are the actual native ASAP7 lattice, as independently
seen in the already placed INT8 source packet121b7ec9a. No macro/stretch.

All four full faces are enumerated: W653 contacts(304data input+348output+
clock), N652/E652/S652 outputs. .192um center spacing equals four.048um
M4/M5 track pitches, with centers on .024um offset. W/E useM4, N/S useM5;
pin rectangles require exact native track/width and legal DRC in actual
physicalization. Maximum six pins in EVERY sliding1um window, not merely
average density. No duplicate port, hidden output bus, or omitted clock.
Clock entry is W(0,70.2), beside the central row region. All pin-to-cell or
cell-to-cell Manhattan geometric separations bounded280.8um<405um; actual
routed wire length/reach remains a later native audit, not a route-length PASS.

Cell allocation bands occupy3002.15105um2 at55% local fill, thickness5.759um
inside the actual continuous row lattice. These are conceptual capacity
bands, not invented filler/cells nor actual placement. Native ordinary
core fill is8.91675%, because actual2609 contacts dominate perimeter.
129.6square is the theoretical tighter lattice option but nearly saturates
all four contact faces at this pitch;140.4 retains actual PG/clock/access
margin. No utilization waiver is claimed: sparse pin-bound geometry remains
explicit ROOT HOLD. No helper relaxations or buffer padding for fill.

## Native clock model and honest remaining conditions

2904 real CLK contacts sum1378.633344fF before clock wire. Never reuse the
old2616-sink clock reference. A transparent clock-only BUFx8 analytical
three-level tree could use root1 +second3 +leaf91 =95 useful buffers,
each leaf serving31/32 actual FF. Nominal leaf native load <=15.191552fF;
second level <=31*.852045=26.413395fF; root3*.852045=2.556135fF before
wire. This is fully native load/area arithmetic, not CTS implementation.
Optional95-clock-buffer allowance adds16.62120um2 and80.944275fF input
clock load, giving1667.80428um2/11240cells/22480PG terminals before
any hold/clock repair. Actual CTS may differ and must replace this estimate.

Actual clock insertion, spread<=80ps, neighboring source clock arrival,
source-phase uncertainty, TT setup and FF hold margin>=30ps are OPEN.
Retain833ps/60ps setup/25ps hold policy; no ideal-clock or synthetic-Lib
closure claim. Physical clock-only topology must use actual role marking,
keep/protection semantics, real source entry and native PG coverage.
No clock-name exemptions in nonclock checks. All loops/reconvergent count
roots remain within unchanged native all-root ledger; current functional
coupon is feedforward, and this model adds no feedback.

## Required next bounded proof, only after ROOT MODEL review

1. ROOT personally views MODEL.png and chooses registered unreset/priming,
   explicit80fF ABI and sparse pin-bound contract. No approval inferred.
2. Minimal source wrapper only: import288 actual parent S1 captures, preserve
   selector ages and arithmetic hierarchy. Prove source/native all2304bits
   against original independent reference with ONLY gc E2 alignment; check
   arbitrary masks/payload, cold priming and next-sample sustain. Add causal
   wrong-S1-age/missing-capture controls. Do not resynthesize arithmetic.
3. Reuse immutable mapped native cells; add correctly polarized capture and
   actual buffer instances, prove representation equivalence/cell identity,
   all native<=32 loops/roles/fanout/cap and output polarity. Any canonical
   remap must have a concrete reason and retain original failure evidence.
4. Then ROOT can authorize bounded native placement/PG/CTS with actual timing
   and independent all-pin/geometry/clock review. No full HIDX tile build,
   SRAM gate, production adoption or parent-fit claim follows automatically.

Whole HIDX remains separately HOLD on source ownership/reset/SRAM/floorplan
and production exactness/throughput/native SS/FF/boundaries. This one complete
mechanism coupon closes none of those by implication.
