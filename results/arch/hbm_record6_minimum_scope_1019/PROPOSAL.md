# R6: minimum source numerical scope for ROOT grant

MODEL / source inspection only. No engine RTL edit, simulation, synthesis,
placement or gate has been launched. Fixed choice: 40 private eight-operand
stations (quarters16/4/16/4) plus one global adder. No further architecture
comparison is requested. Baselines cc83 folded model and5f0 ring ledger remain
history. Identity is image6/k_layer6/price4/q_norm.ss occurrence0; all original
1280 A words VM46336..47615; authentic downstream R VM49920 =40a2a1ed.

## Concrete requested grant

Approve a default-off **bounded R6 arithmetic component**, containing the actual
512-lane front/AA backend,40 private stations,26 fixed fragment entries,one
global adder,and one actual qcore→scalar tree→RF→masked native-VM retirement
chain. Feed all160 sectors through the24 touched native bank identities using
real FILL commands and original fixture words. Exercise the original four
front words per quarter, not an eight-word surrogate or a held group0 command.
Keep generic compiler R-mode refused until this component passes.

One station can prove its mux and recurrence, but cannot establish the160-chunk
canonical256-leaf tree, quarter2 middle-eight join, fragment retention across
four groups, or authentic R. Reusing one station for all chunks changes the
selected41-node calendar and cannot qualify it. Therefore41 nodes is the
smallest numerical shape that answers the requested original-gold question.
The other three qcores, other SM/SFU/COLL/host engines and whole die are outside
this component. Actual qcore SRAM scratch and coherent RF are retained unchanged
as FUNCTIONAL source; RF physical storage remains HOLD (see below).

## Exact source binding, rather than a guessed profile

`source_binding.json` pins the actual GEN2e2 pre_relay contract and every
relevant source hash. It is the immutable source6f783d0a1 generation input,
not a completed GEN2e S4/S5 topology. Its su_SW0 selects scoped pgslice_lg:
MLAT4,ALAT3,LEAF1,FETCH_EXTRA_EDGES2,MULTIRATE1,RF_LOCAL1,COLLPORT1;
PIN_REG is omitted and defaults0. Its READ_RETURN10/WRITE_RETURN7 is the
pre-landing value. Adopted diagnostic GEN2c+l12 source-profile18/15 is the
numerical successor's explicit override, not claimed to be present already.

The proposed successor explicitly selects PIN_REG1. This adds four real lane
edges. The old folded illustrative A29 is withdrawn: MLAT4 source yields
A27 at PIN_REG0 and A31 at PIN_REG1, measured from the edge at which pgslice
samples its control input. These are source-derived edges, not RTL measurements.
All eight arithmetic stage clocks and four insert clocks are the real serial
phase; clock generation retains556ps serial half-period/417ps stream half-period.
No frequency or physical timing qualification follows.

Source anchor: scoped_d4g/pgslice.sv lines130–190(parameters/control),
lines273–349(LEAF),476–594(F0/FETCH/X),630–695(M1/M2/AD),
746–817(E1/E2/OUT),828–971(pin wrapper),1540–1560(broadcast).
The scoped source is read from the frozen generation; matching generic
arithmetic files are independently hashed in source_binding.json.

| Stage | PIN_REG0 edge after control sample E | PIN_REG1 edge |
|---|---:|---:|
|slice broadcast samples the real front/backend word|0|0|
|lane command input pin sample|absent|1|
|LEAF address/position register|1|2|
|F0/live/address|2|3|
|non-gather fetch tag extension|3,4|4,5,6,7|
|m_v then x_v/actual rd_q capture|5,6|8,9|
|PRE/p_a valid; cx controls consumed|7|10|
|M1 AA, p_a×p_a; cp controls first consumed|8..11|11..14|
|M2 bypass/QM_OFF; cm controls consumed|12..15|15..18|
|AD bypass; ca controls consumed|16..18|19..21|
|SFU_NONE direct path; E1 bypass/cs controls|19..22|22..25|
|E2 bypass/ce controls|23..26|26..29|
|OUT FP32/DST_NONE/co controls|27|30|
|lane output pin ro_v/ro_x|absent|31|
|new station held input capture|28|32|

The pin wrapper captures each backend control at its input one edge before the
listed inner consumer. Backend AA/BYP/NONE fields are installed before first
emit and held unchanged until last group's OUT; the entire backend resource
is reserved during that lifetime. Front emit/vb/o_v/i_v/no/ni/ls/lvw are actual
per-quarter/per-group values. LEAF offset bank0 is loaded once and its three
registered loader edges complete before first emit. Absent B/C/D source read
identities alias the genuine live A location, preserving the proven R23 rule.
Source-valid ledger will assert each listed register's operand identity and
age, not merely wait for a correct eventual result.

## The exact new private station

Each of40 stations owns eight fixed32-bit operand registers and eight valid
bits, privately connected to its one real LAT6/OPR1 FP32 node. The first capture
uses the actual ro_v/ro_x at E+32 and then HOLDS through the final local consumer.
No unconditional x1 update, shadow delay chain, shared operand array or runtime
whole-record indexing remains. First capture retains the existing full512x33
physical pin reservation; only320 words per group participate arithmetically.
Eight words =256 genuine operator payload bits, not a split coherent memory.

One fixed station schedule performs x0(canonical +0) +x1 through+x7, then its
assigned canonical joins. The accumulator/result is one real33-bit held register.
The result is overwritten only after every scheduled child consumer has
captured it; the existing model's1228 result-lifetime checks remain mandatory.
The schedule has no ready/arbitration/credit input. "ready" is the deterministic
countdown-zero AND required-capture-valid invariant; violation faults rather
than stalling or substituting data. Group advances only at its fixed112-edge
boundary after last local consumer; reset aborts the whole episode.

Concrete two-stage selectors, replacing the earlier underspecified132b/station:
A path selects word0 or held accumulator, registered32 then32 bits.
B path selects eight owned words plus up to four fixed canonical sibling results:
three private4:1 mux outputs registered(96b), then a private4:1 select registered
(32b; fourth input is unreachable and selection faults). Selection validity is
registered on both paths at both stages(4b). Total196 selector FF/station =7840,
with416 bitwise2:1 mux equivalents/station =16640 before enables/decode.
No accumulator is read before its actual previous node valid; 2 selectors +
OPR1 +LAT6 =9-edge recurrence, so no nine-edge reservation is shortened.
A station's needed peer set is statically derived from canonical join ownership;
mux_inventory.json verifies the actual fixed peer sets have maximum four.
A generated implementation check must refuse more than four, duplicate/missing sources and
selection of an unavailable peer. This is a required elaboration/model check,
not an assumption to hide an extra port.

Per-station state is explicit: group2,epoch8,operation ordinal5,countdown4,
active1,eight capture-valid bits,result-valid1,fault1 =30 FF. Fixed per-station
operation decoding uses its own immutable schedule; no shared run-time table or
large indexed state. Minimum active-station capture-enable copies are two per33-bit word,
16/station=640 total, each drives at most17 useful payload/valid loads.
At least21 useful ancestor copies distribute these640 captures at fanout32.
If all512 reserved face words retain gated captures, reserve1024 local copies
and33 ancestors; inactive192-word removal must be reported by actual synthesis,
not silently counted as both retained hardware and free control.
Select/decode copies must be per16-bit mux segment; source implementation must
emit/count those actual copies, including ancestors. Arithmetic valid/reset
fanout is audited separately. These counts specify required implementation,
not a synthesis/native fanout PASS.

Global collection has26 fixed56-bit entries (FP32,valid,group2,base8,size5,
epoch8),1456b. Exactly one assigned writer/consumer per entry; no overwrite
before capture. Two real26:1 operand paths use four first-stage7:1 mux groups
(4x56 registered) then one4:1 output(56 registered),560 selector FF total.
The one global node performs all27 canonical joins including real padded-zero
subtrees160:192 and192:256. No live input can be replaced by a padding zero.
Fragment writes require at least52 local useful enable copies plus3 ancestors.

Revised payload/selector/arithmetic reservation is51483 FF before local state,
control copies/reset/faults:16896 input +1320 results +7840 local selects +1456
fragments +560 global selects +23411 unchanged41-node arithmetic registers.
Add1200 local state FF and explicitly count emitted global schedule/identity,
select/capture/ancestor copies and reset stages. The prior49739 aggregate is
superseded, not a safe upper bound. Native combinational/copy/reset cell area,
clock load and parent fit remain NULL until actual source/synthesis; no physical
build is in this grant. A numerical prototype cannot qualify fanout/geometry.

## Real root selection and authentic retirement

Actual frozen sucore_SW master is **ot_hbm_su_static_qcore**, not r5. Preserve
that exact default path, existing SFU/COLL selector and six read classes. Add a
default-off ROOT_OPERAND option, dedicated33-bit root input pin capture and a
separate root_select input captured with red_cmd. In its rc_x stage, the new
selection chooses only that root capture; existing e_os/e_sfu/slice selection
continues when root_select=0. Selected LOAD with missing root-valid faults.
Do not borrow sfu_x, slice_x, an op bit or an active port. Default source/fixture
bytes and original R23 compiler guard remain unchanged.

At real global-root edge T, dedicated operand/valid pin capture and LOAD red_cmd
sample at E=T+1; rc_x consumes that held capture at E+1; reducer iv samples at
E+2 and LOAD scratch0 commits at E+11. EXPORT scratch0 is commanded at E+10,
issues E+12, scalar valid/tag0x100/x appears E+21 =T+22. Source:
qcore.sv lines109–130; reduction/ot_hbm_su_reduce_static.sv lines18–58,79–89.
No compiler/golden scalar is ever injected as the root.

Actual source RF transport is resolved: str_C root +stl_SW leaf,14 stu_SW
registered up stations and14 paired std_SW down stations. Tree source
L=leaf1+up14+root2+down14+leaf1=32, not a guessed direct RF_RELAY36.
The numerical component retains the actual leaf/root and directional hard
relay master sources from these selected paths, not a newly introduced long
behavioral shift chain. All disabled unrelated producer slots are explicitly
inactive; they cannot supply arithmetic data. Source/tree path reset startup
and valid suppression remain intact. Physical reach/clock qualification of
this historical pre-landing topology is HOLD, not implied by L32.

RF write pin samples scalar+33 and commits scalar+34=T+56. At T+57 issue actual
RF class5 address0 (9b command valid=1,addr0), then DRAIN at T+59 (=class5+2,
RF_LOCAL1). Use q0/slice0/port0 only; vmw source1, mask01, actual physical sector
allocated to logical49920. Pgslice genuine RF_LOCAL dsec enters real write
packet at DRAIN+4 and native18/15 completion is DRAIN+20=T+79. All seven other
VM words must retain OLD values. Read/check original complete256b sector through
native host owner1 port after actual done; a mask-only scalar comparison is
insufficient. Premature drain,wrong tag/address,wrong class5 lead and corruption
of untouched words are causal negatives.

The actual qcore RF is globally addressed256x32 logical8192b with six coherent
reader replicas=49152 payload FF, plus pin/read state. Its64 four-word banks
share architectural bank/row decoding: they are NOT independent small operator
registers and cannot be declared physically admissible by splitting the array.
Retain only as explicitly permitted baseline FUNCTIONAL proof; physical storage
HOLD survives a numerical PASS. Native reducer's two coherent128x256 SRAMs are
actual source instances; no nominal Elmore CQ or unqualified SC2 lib is used
for a timing claim. No new macro is invented or silently substituted.

## Component host calendar and boundary of available evidence

Reuse original R23 mechanism for CP96 programme bank/row installation, index
packing, host cfg leaf and VM calendar descriptor installation/launch. Install
fresh per-episode descriptor after reset and before launch; repeatrequest
requires descriptor rearm, preserving the proven causal omission negative.
The new component must emit and count every actual packed instruction and
literal with per-bank occupancy<=128, total<=7111, no modulo overwrite.
The41-node internal static schedule need not be encoded as external per-add
commands; its group front emits and actual LOAD/EXPORT/class5/DRAIN do.
No untested R-mode enable is added to the production compiler during this work.

Fill all160 sectors at relative serial0..7, latest actual store commit28;
first control emit32. With A31 instead of29 and unchanged NL9/112 spacing,
folded source model root becomes590 and native R done669 serial =892 stream
edges (extra709.82 over original182.18), **before parent transport/host H**.
The explicit component observation is separately scheduled after native done,
never reused original3750/3770 host deadlines. Its own programme installation,
reset landing/startup9 and host cfg/calendar edges are logged separately from
useful R latency; no invented zero-cost installation or throughput claim.

Real producer is image5/k5 x_projections_gather.qa, O SHA f2d1351f… matches every
original A word; completion1463.31→R6start1479.31 gives only16 stream edges.
No sector-arrival/VM-allocation proof exists. The component seeds original
fixture words through real native producer ports and labels this boundary
"fixture-owned producer input", not an actual all-gather co-simulation.
It prices no prefetch before ownership. Full producer transport/relocation H,
regional landing H, host distribution H and downstream calendar shifts remain
parent obligations. Exact reason: GEN2e2 remains S2; no emitted S4/S5 placement,
landed contract, source sector-arrival ledger or final18/15 topology currently
exists. A real parent H cannot be extracted from an unproduced topology.

Thus ROOT can approve this component's original-gold and control/retirement
mechanism without claiming complete producer-to-host token timing. A requirement
for full actual producer arrival before *any* component numerical simulation
would need the all-gather writer's actual sector visibility/allocation table
and the emitted GEN2e landed routes; that is external input, not missing source
inspection. No old182.18 ceiling is enforced; downstream q_norm.rs/y and every
colliding SU/RF/native slot shift honestly after this component's measured price.

## Required verdicts from the proposed one bounded fleet run

PASS requires1280 original words each captured once with correct group/lane/
address,1281 actual FP32 adds in untouched canonical expression order, authentic
root40a2a1ed, real LOAD→EXPORT→RF→VM chain, complete OLD-sector preservation,
all source-stage ages and fixed calendars matched, all faults0, reset abort plus
reinstall, and a second episode with rearm and distinct input/gold ownership.
Causal mutants: word order,canonical sibling order,early feedback,early capture,
front group held0,backend AA lifetime broken,early result overwrite,wrong root
selection,missing root-valid,RF tag/address,class5 lead,OLD-word mask corruption,
descriptor rearm omitted,mid-record reset without reinstall. Preserve each
actual fail witness; do not call a timeout/compile error a causal FAIL.

All builds/sims run Verilator5.050 via unpinned ot-run with measured memory
admission and incremental objects; no local simulation or native gate. ROOT
reviews this concrete source scope first. This document is not that grant.
