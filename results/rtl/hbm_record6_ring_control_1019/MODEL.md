# R6 control, ownership, ring ports and authentic retirement

MODEL ONLY, default-off successor proposal. No RTL/compiler changes, numerical
build, synthesis or physical gate. Baselines db11c6d6c / 04423a7d8 and pretree
1dad69123. `model.json` is an integer-edge resource calculation, not an RTL PASS.

## Producer and identity

Image6 / k_layer6 / price4 / tag q_norm.ss / occurrence0 consumes original
VM46336..47615, 1280 FP32 words, and writes authentic R at VM49920. Golden
0x40a2a1ed is unchanged. Its actual fixture producer is image5 / k_layer5,
`x_projections_gather.qa`: its O hash f2d1351fa018cc6708973313ba3d7fb4ac974ea4156553246faa710e04fd89c5
exactly equals R6 A. The preceding SM image4 is only the local partial and
cannot substitute for the all-gather result. Producer records and their full
records.json SHA are archived in `producer_records.json`.

The producer's modeled completion is1463.31 stream edges; R6 begins1479.31,
only16 stream edges later. That is12 serial edges, less than native FILL21
even before8 per-port rounds. No sector-level physical visibility calendar is
present. Therefore prefetch before actual producer visibility is REFUSED.
The 16-edge priced gap is possible overlap, not evidence that the data is
already owned or native-readable. The candidate below conservatively begins
all FILLs at R6's own start. Actual producer/consumer VM placement must agree:
the fresh physical-sector mapping here requires a priced relocation if the
real producer does not already emit it. Fixture preload is not that proof.

## Exact FILL and per-stage control ledger

`model.json.fill.sectors` lists every logical word, quarter, actual native
port, VM row/sector, store group/row, issue group and FILL command/commit.
All160 sectors /1280 unique words cover all4 quarters and24 touched native
bank identities. Full quarters0/2: port p handles groups k=p,p+8 for each
issue group g, command at2g+floor(k/8), store row g. Short quarters1/3:
ports0..3, command g, store row g. There is at most one command/port/edge;
last command7, last native18/15 commit28. No fill/lane write overlap: R6 has
no O destination, every live lane's destination is NONE.

Candidate emits g=0,1,2,3 at serial32,34,36,38 after all fills commit. These
are four distinct complete front-end words per quarter, never group0 held in
place of the later groups. The following is the required field ownership:

| Consumer | Fields and owner | Lifetime rule |
|---|---|---|
|broadcast input and32 replicas/slice|all1742 bits|emit front word changes by g; backend fields below remain genuine AA signature|
|three-edge LEAF offset loader|ld, ld_bank, ld_c|one setup into bank0, completed before first leaf sum; source lowerer computes ld_c once outside all groups|
|leaf and F0|emit, bank, o_v/i_v/no/ni, ls/lvw, vb, srcs, addresses/liveness|original per-g/per-q positions; vb selects actual filled store row g; absent B/C/D reader identities alias that same live A row, not zero data|
|X/PRE|cx_srcs, arnd/relu/min/cclip/imm3|VM source, no rounding/clipping; sampled at actual operand capture, not at emit|
|M1 input|cp_m1, cp_imm1|AA=2 for each live A; original FP32 multiplier rounding|
|M1 output/M2|cm_m1, cm_m2, cm_qm, cm_imm1|AA selected through M1 output; M2 BYP/QM_OFF|
|AD/S|ca_ad/imm2, ci_sfu/cs_sfu|AD BYP, SFU_NONE, maintained until last group exits these stages|
|E1/E2|cs_e1/imm2, ce_e2/imm1|BYP throughout all four groups|
|OUT|co_rnd/co_dst|FP32 unrounded, DST_NONE; ro_v/ro_x captured exactly once by pretree|
|pretree input and taps|valid, group, epoch, canonical base/size|registered capture per actual output age; no selection of a non-live lane|

All backend values are identical across these four groups. They may therefore
remain live from before group0 until group3's final consumer without a
backend signature collision; this does not permit holding front-end vb,
positions, emit or liveness. Two-edge emit spacing is an analytical choice,
not a throughput measurement. Bank1 is not loaded or selected for this
record; no offset bank is overwritten while live. A different op interleaved
between these groups must supply a real per-stage merge or wait for the last
consumer. This proposal reserves the entire control lifetime against other
records. Actual packed programme/dictionary/index lowering remains required.

Exact lane output age A depends on selected MLAT/ALAT/LEAF/PIN_REG/FETCH
profile. The source comment's25 edges plus pin-register4 is only the A=29
illustration below; it is not a calibrated age for this proposed wrapper.
The minimum numerical prototype must first instrument the real F0→X→PRE→
M1→M2→AD→S→E1→E2→OUT valid/operand ledger. Clock stages must retain actual
source phases. There is no license to shift gold or mask an early/late group.

## Independent FF pointer rings: selected source-model baseline

ROOT's exact storage classification is controlling: these384 streams are
genuinely independent lane-word delays, each with its own address pointer,
one write/read port and lifetime. They are not one coherent297792-bit array
that has been split to evade a storage rule. Each original33-bit private
D−1-slot array is at most41x33=1353 bits. Even an optional43-bit identity
word remains41x43=1763 bits, under2kb. Therefore real FF POINTER rings are
admissible; there is no mandatory new SRAM dependency for this mechanism.
All delays>=3 use the circular pointer/OLD read, never a FF shift chain.

The unchanged source's `mem[p] <= d; q <= mem[p]` uses nonblocking OLD
semantics, exactly one independent read and one write per stream/edge.
For D7/14/21/28/35/42 the slot counts are6/13/20/27/34/41. Payload+valid
storage is297792 FF, outputs12672 FF and first pretree capture16896 FF:
327360 payload/capture FF total. Pointer bits are1856 across384 independent
rings; maturity count upper bound is another1856. Raw payload is not reset;
pointer/valid/maturity use the inherited reset landing and startup suppresses
old unread contents until that private ring is completely overwritten. The
integer model tests this exact OLD schedule separately from the macro option.

No group/epoch bits are silently assumed free: the minimum33-bit ring is
valid only for this single static programme episode, all groups in fixed
known order and no user-context overlap. Group identity follows the emitted
static calendar; a reset aborts the episode and drains/mutes all ring/fragment
valids before producer reinstallation. If later source proof requires actual
per-word tags, the43-bit option costs388032 indexed FF and16512 output FF,
with each private array still1763 bits. Neither option permits stale identity
at epoch wrap or replay. Fragment identity/storage is separately priced.

Using actual DFFHQNx1_ASAP7_75t_R area0.2916um2 and TT CLK0.474736fF,
the327360 payload/capture FF alone cost95458.176um2 and155409.57696fF
clock load. These are lower bounds: read mux/one-hot decode, write enables,
pointer/maturity arithmetic/reset, useful fanout copies and536 arithmetic
pipelines are extra. Real synthesized cell choice may grow those bounds.
Liberty source: local immutable export
`/home/ubuntu/artifacts/hbm-int8-raw-export-1019/t1/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib`,
SHA57a0b403485b99ebd676942af4673ac086b86c7c75fbdc3e5c0038501dd22ba3,
cell area at2702, CLK capacitance at2934, capacitance unit ff. This is cost
evidence, not native timing qualification. Private ring placement, mux depth,
write-enable/read-select/reset fanout<=32 and real regional clock plan remain
mandatory. A pointer bit may not drive all storage bits without a priced
kept local decode/copy structure.

## Port-exact SRAM alternative, not a prerequisite

Keep the previous full512 physical lanes and536 adder nodes conservative
count, including quarter2's extra middle8 node and27 canonical global joins.
The26 fragments and original chunk8 sequential sums are unchanged; chunks
160:192 and192:256 are canonical golden padding, not fabricated live inputs.
The earlier fixed quarter collapse must be split to expose actual 4/8/16
chunk taps. Those ports do not exist in the current pretree/pgslice exports.
The fragment bank is separately reserved at26x56=1456 bits: FP32/valid/
group2/base8/size5/epoch8. It is finite (<2kb), with static entry assignment
per canonical fragment, no runtime search/arbitration and no more than one
writer per entry. Those extra identity bits correct the earlier1248-bit
reservation which had no epoch field. Duplicate/wrong-base/size/group/epoch
entries fault; none may substitute a missing fragment. The exact emitted
register/pointer/reset/comparator inventory still requires source proof.

For each of64 chunks, six independent delayed lane words require delays
D=7,14,21,28,35,42. A true full-rate port allocation uses ONE existing n64
128x64 1R1W2C macro per delayed stream:384 macros. This is a conservative
full-rate architecture, not a minimum for this sparse four-issue record.
Dividing297792 bits by8192 gives37 but cannot meet384 simultaneous writes
and reads. Sharing macros needs a different, explicitly scheduled input
holding/serialization model and its register, mux and latency costs.

Each occupied word carries43 real bits: FP32[31:0], valid, issue-group2,
epoch8; remaining21 bits are unused macro capacity with masked writes, not
functional placeholders. Each delay's wrapper has an explicit43-bit input
pin capture and43-bit output pin capture. Memory write/read clocks are the
same serial root logically; their physical insertion/slew contract is OPEN.

Let N=D−2, with one row counter per stream. At local serial edge t write
the previous input pin word at w=t mod N; read r=(t+1) mod N into the macro's
registered output; capture its previous output at the output face. Input
sampled at edge e emerges after edge e+D−1, exactly the D-stage shift-line
edge convention. The write and read rows are ALWAYS different (N>=5).
This is essential: the shared dual-clock functional model uses a blocking
write task and explicitly requires no same-slot read/write. It does NOT
establish the same-address OLD behavior required by the current D−1-entry
nonblocking FF ring. No scheduler race may be accepted as SRAM OLD proof.

Ports are exact: each macro r_ce/w_ce is statically enabled per active
serial edge, r_addr/w_addr seven bits from its local counter, wd43 bits and
w_mask43 ones; ignored upper bits are masked. rd43 is captured at the output
face. No cross-stream arbitration or credits. Pointer reset and mature
counter reset use the actual two-stage face landing; input/output valid is
suppressed until D−1 edges have completely displaced arbitrary stale SRAM.
Payload SRAM is not reset and OT_MEM_NO_INIT must be used in the RTL proof.
Epoch must remain fixed until all old output valids and fragment consumers
drain; eight-bit wrap is legal only with that explicit drain invariant.
Mid-record reset aborts, clears fragment validity and requires producer
reinstallation; it must not preserve an unproven scalar from the old epoch.

The integer model checks138240 valid output identities across384 streams
and six reset offsets, including all distinct read/write addresses. It proves
only this abstract schedule, not macro access timing or reset pulse behavior.
No bypass is needed because no read/write rows collide. First-use mute is
an explicit startup/reset contract, not a mask of valid numeric mismatches.

| Resource | Charged bound |
|---|---:|
|physical SRAM capacity|3,145,728 bits in384 macros|
|used row payload/identity capacity|371,520 bits|
|new ring input/output payload FF|33,024|
|existing first pretree capture FF retained|16,896|
|pointer FF upper bound|2,688|
|maturity FF upper bound|2,304|
|macro area alone|357,067.28448 um2|
|macro clock contacts|768|
|modeled TT macro clock pin C|7,177.5744 fF|

These counts exclude536 arithmetic pipelines, fragment taps, each node's
mode/valid/error state, address/enable/mask pin replication, reset trees,
fault/identity comparators and transport. A macro input bit cannot directly
drive43 mask/enable pins; local useful copies/decodes must keep all logical
fanout<=32. Counters and maturity trees are not declared SAFE by this model.
Pin FF cell area and clock cap are NULL until exact synthesis masters exist.

The unchanged n64 abstract is33.72x27.576 um,105 signal pins/side,3.808/um.
It fits one43.2-lattice macro site but requires real signal and PG escape.
A geometric lower-bound arrangement of384 macros is24x16 lattice sites:
1036.8x691.2 um BEFORE full-width std-cell bands, halo/route channels or the
536-node logic. This is not a parent slot grant. A1.04-mm parent requires
regional clocks/landed crossings; no single long balanced clock or >405um
data hop is permitted. Every added landing edge must enter the schedule.
The full replicated FF, routing-track and parent-slot budgets remain OPEN.

## Authentic R→RF→VM chain and honest latency

Use a separately registered global-root operand connection into a selected
qcore. Neither selected slice_x nor the native pretree's two fixed subtree
outputs already implements that connection. Do not steal sfu_x or silently
rebind an active COLLSFU port. The source proposal must add/price the actual
operand pin/selector and preserve all defaults.

For a global root visible at edge T, a conservative source sequence is:

1. Capture the new operand at T+1; qcore LOAD command at E=T+1, scratch0.
   qcore command/operand pipeline issues at E+2, LOAD commits at E+11.
2. EXPORT scratch0 command at E+10, issue at E+12 (dependency distance10),
   scalar valid at E+21. Tag0x100 selects actual RF write, RF word0.
3. Send the41-bit {valid,tag[7:0],FP32} through the actual RF route of L
   registered stages; RF write pins sample scalar+L+1, commit scalar+L+2.
   No O descriptor or direct fabricated scalar VM write.
4. Class5 command after RF commit, aligned RF address0. With RF_LOCAL1,
   the actual RF-source DRAIN command follows two edges later, only slice0
   port0, mask0x01. Pgslice write leaves at DRAIN+4; native18/15 done is
   DRAIN+20. Allocate real physical VM sector for logical49920 at that port;
   other seven words retain their old values through mask0x01.
5. Descriptor retirement and downstream q_norm.rs may occur only after the
   actual native write completion and fixed host observation/retirement hops.

The registered RF tree default UP14/DN14 gives L32, but actual source-selected
die route count and RF physical implementation are NOT established here.
The generic r5 RF is8192-bit indexed FF storage and is not an admissible
new physical implementation merely because this sequence uses one word.
Exact native RF master/binding, collision/OLD lifetime, complete unused-read
audit, host leaf installation/rearm and R sector placement remain required.

With original LAT6/OPR1 nodes, a last squared word requires49 serial edges
for its chunk recurrence and56 for the padded global tree, plus first capture
and tap/output registration:107 edges. The illustrative last emit38, lane
age A, registered root capture/LOAD/EXPORT22, RF L+2, RF_LOCAL drain2 and
native done20 give final R completion **191 + A + L + H serial edges** from
first FILL. H is the as-yet unpriced additional fragment/region/host landing
cost. A29/L32/H0 gives252 serial=336 stream edges, versus original182.18:
**+153.82 stream edges** before any additional physical/host cost. This is
an illustrative longer-record price, not a timing qualification or schedule
upper bound with unknown H. Completion1815.31 would push q_norm.rs and its
dependent q_norm.y; unrelated records may overlap only after resource checks.
No old-window PASS or achieved token rate is claimed. The16-edge preceding
gap cannot remove this large deficit without a new justified architecture.

## Root review / next bounded step

Keep build HOLD. The controls now have a collision-free candidate ownership
strategy and independent FF rings remove an unnecessary macro prerequisite,
but source
age A, real producer placement/arrival, root operand binding, RF/native route
L, landing/host H, parent area and clocks are still unresolved. ROOT can
select the independent33-bit FF-pointer-ring baseline for a minimum component
prototype once exact remaining bindings/ages are written, or investigate the
much larger384-macro alternative if the FF clock/mux cost fails the model.
Do not launch the whole four-quarter numerical vehicle or any physical gate
from an aggregate capacity calculation. ROOT review is still required before
requesting a source-only minimum numerical prototype.
