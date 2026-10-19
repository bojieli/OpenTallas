# Whole COLL successor model for ROOT review

Status: MODEL ONLY, not source admission. No RTL changes, synthesis, simulation,
route, REVIEW.json or submission. The proposal covers the whole selected lane,
not only the previously qualified credit helper. The full census reproduces all
37 nonreset and 2 reset drivers above 32 after BUF/INV transparency and expansion
of all six kept hit-comparator instances. It counts all 66,676 mapped cells,
52,513 electrical roots, and every receiver pin. Clock and the two constant
roots are separately recorded. `over32.json.gz` contains complete receivers;
`control_ledger.json` assigns every failing root to its actual receiver families.
The complete census, including passing roots, is compressed without truncation
(the complete failing receiver list is `over32.json.gz`).

Source is functional83d6b8b7f, preserved by e4ebc3c23. Mapped bytes SHA256
512e2b3b6362acd91360d73e09d5c9191163e53cb55d4b07cb22cd86a1d75e0e.
The model parser expands the helper and matches the original 66,676-cell count
and the independent 37+2 census. This is a crosscheck of the preserved design,
not evidence that the proposed design meets SAFE.

## Storage, frame slices and exact visibility

At FB69, SEQW10: payload552 + last1 + sequence10 + CRC32 =595 frame bits.
`f_tx={sequence[9:0], last, payload[551:0], CRC[31:0]}`. Thus frame[31:0]
is CRC, [583:32] payload, [584] last, [594:585] sequence. Slot bit0 is valid;
slot[595:1] is this entire frame. The four sf entries store595 bits each;
sn/sh/st carry validity and occupancy separately. Valid is not silently stored
inside a 594-bit memory. FMT1 keeps the original596-bit rem,456-bit hold and
phase-selected wire format; these are explicit pipeline state, not indexed
runtime arrays.

Use ten exact e26d92503 32x64 dual-clock banks for logical depth4. Banks0..8
carry frame[63:0] through frame[575:512]; bank9 low19 bits carry[594:576].
Bank9 high45 write bits are zero with full masks; their read bits have no fanout.
Macro address[4:2]=0 always, low2 select row. Physical rows4..31 are unreachable
and paid, not credited as useful capacity. Ten banks pay20,480 bits versus2,380
useful,18,100 unused bits; macro area5,535.89568um2 and20 clock contacts.
Nine banks provide576 columns and lose19 real bits: not admissible.

Reuse the coupon's *organization*, not its W553 qualification. W595, AW2,
NS38 means1,190 unconditional payload FF,76 local hit flags,2 write-address FF
and1 write-valid FF =1,269 helper FF. Three compare groups each produce current
and previous hits for at most16 flag D pins. Each flag Q selects at most16
payload bits; full mapping must count both complemented and true cones.
Macro write/read-enable fanout10; address inputs require both ten macro pins
and six comparator cones, so they are separate local kept producers, not a
shared raw sh/st wire. Caller reset supplies38 independent same-depth outputs.

For edge n use ra=sh_next, where sh_next=sh+take modulo4. The pre-edge take,
sn and f_tx_v are the original expressions. Capture the selected row at edge n,
then expose it during cycle n+1. This is the same old sf[sh] row that the next
beat consumes. A current logical write to ra wins, then the previous logical
write, then SRAM data. Registered physical write pins apply the previous
logical write at edge n. If those pins target ra, disable the physical read;
the previous-write payload supplies it. If both logical hits exist, current
wins, including repeated same-address writes. No macro collision result is
used. Full/take/write/wrap/reset/overflow behavior retains the original sh/st/sn
updates, including fault behavior on overrun. No new edge is proposed.

Inductive argument: before an edge, abstract memory equals SRAM contents plus
the pending registered write. Reading next sh selects the abstract post-edge
row: current logical write if matching, otherwise pending previous write if
matching, otherwise the physical row. These are exactly the three priorities
above. Empty cycles may expose uninitialized payload internally, as before;
sn gates take and slot valid, so it must never turn into a valid frame. This
argument does not replace the W595/depth4 gearbox miter. Coupon evidence
1298888bc proves only W553/depth8:19,994 comparisons,7,113 takes,772 suppressed
physical collisions, current/previous-forward mutants1,766/1,862 errors and
unsafe-read fatal. New shape must repeat those mechanisms and all FMT1 cases.

## Complete control and producer ownership

All copies below are independent kept, unparameterized physical modules with
distinct same-depth reset pins where reset exists. Copy D is computed from
local original-state copies at the *same* original edge. Copying a shared wide
D expression and creating another high fanout upstream is forbidden. The
ledger's1,159 output copies at16 loads is a conservative allocation lower bound
for the OLD failing cones, not1,159 proven new FF: sf mux cones disappear with
SRAM and other cones overlap. It cannot be used as mapped successor area.

| Owner | State and affected receivers | Proposed structure |
|---|---|---|
| Gearbox TX | sh2382/1191; sf write gates; take/rem; ph431/288; idle439 | Delete sf selector network via ten-bank prefetch. Partition rem596 and beat payload456 into16-bit regions (38 and29). Each region has local ph[1:0], idle, sn/take predicate and the exact original enable/next-state cone. st/sh copies serve macro/comparator contacts in groups whose total loads are <=16. Raw f_tx_v gets same-edge producer copies at the existing endpoint tp_v final edge, not a new gearbox stage. |
| Gearbox RX | mc882/845; hold456; anonymous hold/cut enables | Partition hold456 into29 regions and f_rx595 into38. Keep local mc[1:0], hunt[1:0], bv/bm/bi and original comparison predicates per region. Preserve unconditional f_rx capture and conditional hold updates exactly. Replicate lr flag producer flops at their existing landing edge if aggregate D/input counts exceed32; actual rx port loads remain explicit. |
| Endpoint TX | a_rep1106; rb ready snd→ready635.1ps |35 regions for553-bit replay/input payload. a_rep copies capture replaying at existing a_rep edge; data and a_snd retain their edges. Preserve qualified old-read helper and grouped pointers. Split ready next-state into local registered predicates on the existing ready edge; preserve dependency on actual snd/ack/credit state. Boolean equivalence and critical depth are REQUIRED, currently OPEN. No claim that copies alone shorten635.1ps. |
| Endpoint reverse/control | rr_ok58, una[6]42; anonymous37/68/140+ cones | Copy the full relevant source state/next-state predicate per listed receiver region. Keep S2 ACK/error/timeout application age. Do not register an already combinational predicate one edge later. Endpoint191 reset receivers become<=16 regions. |
| Credit TX | send/reset gate1108, downstream payload553 |35 payload regions each retain conditional load/hold. Local cr_q and full count state use local send predicates; upstream endpoint output-valid producer replicated at its existing edge as needed. DFREE remains0: DFREE1 changes invalid-cycle payload and is not bitwise equivalent at this boundary. |
| Credit RX | l_credit next-state61 plus helper boundary | Preserve six qualified hit compares, all current/previous forwarding and accepted-beat flag contract. Local copies of exact pop/count/credit state for the distinct receiver regions, with input and producer counts in final census. Existing35 caller reset outputs retained. |

All anonymous combinational roots, including1190/734/632/595/456/421/420/315/
294/283/176/174/164/163/140/68/61/37/33, are covered by exact receiver lists in
the ledger. RTL implementation must trace each back to its source-register
closure and replace each affected cone. A naming-based whitelist is forbidden.
The model explicitly leaves the minimal producer-copy graph and its exact FF/
gate total OPEN: it is not legitimate to claim complete source admission from
an output-copy estimate. Source review should approve the structure and require
a concrete finite graph before any full RTL build.

## Reset, clock, silicon and layout cost

Keep the three-edge tree: root→group→region, constant D1 at every relay, async
assertion cascades as current tree3. Final region Q drives<=16 actual reset pins
(32 maximum only after explicit census). Existing216 leaves plus38 SRAM flag
leaves, endpoint legacy ceil191/16=12 replacing1, gearbox ceil36/16=3 replacing1
gives at least267 leaves before new local control state. Then add ceil(new
reset-bearing FF/16) dedicated leaves; root drives ceil(total_leaves/32) group
resets, each group <=32 leaves. If total leaves>1024, another reset edge is a
paid contract change, not an automatic tree extension. No added payload reset.
Input rs asynchronous assertion load and SETN tied contacts remain disclosed.

New bank clock input capacitance =20×9.3458=186.916fF, excluding internal
switching, wires and CTS. Both clocks tie to the SAME root with actual routed
clock timing; no asynchronous group or collision-order assumption. Existing
15 macros stay; whole lane becomes25. Replacing2,380 sf FF by1,269 helper FF
removes1,111 FF before control/reset additions. At measured DFFHQ area
0.2916um2 this saves323.9676um2 of FF only; mux removal, new controls and actual
hold/clock padding must be measured. Added macro area is5,535.89568um2.
Standard-cell clock capacitance is unpriced pending actual kept-copy census
and Liberty pin inventory; there is no power-saving claim.

The frozen561.6square/15-bank band216..246.24 is not a25-bank fit. Proposed
MODEL reservation648×561.6 adds48,522.24um2 (+15.3846%) paid outline. Keep all15
old origins. Put ten new31.992×17.304 banks at x561.6, y43.2/86.4/129.6/172.8/
302.4/345.6/388.8/432/475.2/518.4, all43.2 lattice; vertical clear25.896um.
Gap from old east-bank right526.608 to new x561.6 is34.992um. New east clear
54.408um. Candidate full-width band216..259.2, usable x2.16..645.84, gives
27,806.976um2 and admits11,122.79..16,684.19um2 at40–60% BEFORE actual row cuts.
Current9,891.8um2 does not automatically fill that band; mapping determines
whether to select a narrower legal row band or pay a different shape. The
07f31b7da GP-envelope mechanics remain frozen; any new coordinate hook needs
explicit model review and actual occupied-row census. No fill waiver.

Bank-local control and flags belong beside each bank/owning row; global
band-center coordinates alone do not prove405um pin reach. All pin/relay
paths, channels, PG/vias and clock spread/native launch/capture remain OPEN.
No raw-area parent substitution: the950×4600 aggregate stand-in proves no
actual child fit. Parent strict baseline unread161694/open45 is inherited
debt; a clean interface alone is not a parent PASS.

## Whole SRAM inventory changes the admission decision

`macro_inventory.json` hashes every selected LEF, functional model and TT/FF
Liberty, and counts *contacts*, including clocks, rather than only bus names.
This exposes another hard blocker that the earlier fifteen-bank outline did
not price:

| Master | Count | Raw bits | Useful bits | Clock | Signal/clock contacts W/E and full-face density |
|---|---:|---:|---:|---|---|
|512x128_m4_r2c2, aligned v2|10 (five replay, five receive)|655360|566272 (two553x512)|one clk each|219/218;7.365/7.331 perum over29.736um|
|32x128_m1, legacy dense|5 credit|20480|4424 (553x8)|one clk each|199/198;9.572/9.524 perum over20.79um|
|32x64 dualclock exact e26|10 proposed gearbox|20480|2380 (595x4)|wclk+rclk each|103/103;5.952 each over17.304um|

Both existing families FAIL the6/um full-face contact rule. Their active
contact spans are even shorter:512x128 W0.780..21.708;32x128 W0.780..19.788.
PG contact counts are also preserved separately (512x128 S38/N39;32x128
S26/N27;32x64 S22/N22). No collision forwarding proof, wide placement gap,
pin-name count or abstract area qualifies these dense LEFs. Larger-pitch
compiler variants with actual functional/Lib/LEF/escape evidence are needed.
At minimum the512x128 needs>=219/6=36.5um *usable* face; dense32x128 needs
>=199/6=33.167um, plus real end keepouts. These are sizing lower bounds,
not permission to stretch a LEF. ROOT's32x64 single-primitive escape receipt
qualifies only that primitive; all bank arrays and all other masters remain
unqualified. Keepouts/via escape must be checked on actual chosen masters.

A fully paid alternative using only the exact32x64 primitive is:
two553x512 stores each9 width banks x16 depth groups=144 primitives/store;
credit9; gearbox10; total307 primitives,628736 raw bits/573076 useful bits,
55660 paid unused bits,169951.997376um2 macro area. This requires a16:1
553-bit read merge for EACH deep store, two independent depth/address/enable
selection networks, local write-select decoding and current/previous-write
forwarding at all applicable logical read/write collision boundaries. Read
address[8:5] selects group, [4:0] the row; group select must align with the
same physical read edge. A shared high-bit select across553 muxes is forbidden.
The existing OLD-read endpoint helper must preserve OLD semantics; the credit
and gearbox helpers preserve their own NEW/current/previous semantics. They
cannot all be replaced by a single forwarding priority without proof.

307 banks present614 clock pins and5738.3212fF primitive input capacitance
before CTS, plus merge/control clock costs. A conservative arithmetic square
reservation1166.4x1166.4 (43.2 lattice) can host13 columns at x43.2+86.4*i
and24 rows at43.2*j, j1..26 excluding13,14:312 bank positions,307 used.
Horizontal gap54.408, vertical25.896; candidate band561.6..604.8 has25.896
clear from the previous bank row and43.2 to the following row. Macro-only
geometry does not show std utilization or local producer reach. This adds
1045094.4um2 (+331.36%) over561.6square and makes<=405um reach across the
array impossible from one band-center source without real regional stages.
No-edge and slot fit are therefore OPEN. This is an honestly priced fallback,
not a qualified recommended implementation. Prefer investigating real wider-
pitch512x128 compiler/escape first; source build must wait for ROOT choice.

The648x561.6 partial reservation above is withdrawn as a whole-lane candidate:
it only priced gearbox storage and retained unsafe legacy memories. It remains
an explicit component cost bound. No frozen fifteen-bank source is relabeled.

Parent fit already fails before these alternatives: old COLL561.6 + LEPA/H475.2
+43.2 channel=1080um > actual950um aggregate reservation by130um. The partial
648-wide COLL would need1166.4um (+216.4); the all-bank64 1166.4-wide square
would need1684.8um (+734.8). These sums are orientation-specific width lower
bounds, not complete arrangements. A real parent repack must pay width/height,
channels, relay stations, reset/clock/PG and changed calendars for every added
edge. Raw area equivalence or stand-in aggregation cannot close this debt.

## Required decision and next guarded step

ROOT may review this model as a complete blocker/cost inventory and select the
actual SRAM family first, then the ten-bank storage plus local-control structure
for a source proposal. This model
does NOT request a route or full RTL build. Before that build: commit the exact
producer-copy graph (including all local transitions, reset leaf counts, input
loads and cell/cap estimates), real W595 gearbox edge/collision miter plan,
ready-cone Boolean equivalence plan and final floorplan choice. After source:
full uncapped BUF/INV-transparent mapping must show<=32 on every nonconstant
data/reset producer, with clock and asynchronous input loads separately paid.
Then all23996 endpoint and27994 full-lane boundary checks, actual mutants,
marker/idle/relock/full/wrap/reset cases, zero extra data edges or priced deltas;
then measured band/PNG/SAFE review, actual own-native TT/FF and parent binding.
Original P1 W/E jobs1883886/1883887 are preserved and were never touched.
