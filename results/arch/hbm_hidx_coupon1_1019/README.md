# HIDX coupon1: exact useful ownership; electrical/depth HOLD

Standalone default-off coupon, based on RTL5af00a1ab and whole ownership model
eb201. Production RTL, defaults, storage, compiler/reset protocol and closure
helpers are unchanged. `ENABLE=1` is used only by this bounded experiment.
This is a component result, not a whole-tile build/adoption or physical SAFE.

## Actual source and native result

One eight-lane/36-bit group uses nine four-bit compaction owners, one mask per
owner shared across its eight output slots. Each owner samples the actual lane
mask and its disjoint payload bits, computes exclusive prefix counts, and
preserves stable lane order and zero padding. Six independently instantiated
pc8 producers own144 four-bit selector FF; twelve pc16 producers own288
five-bit selector FF. Each producer owns its own same-age registered operands
and actual useful arithmetic D, with24 selector FF sinks per output bit.
There are no BUF/INV distribution trees.

The existing source `keep_hierarchy` contract and unmodified canonical
`ot_keep_regs.tcl` hook precede normal `synth -flatten -noabc`, native SEQ
`dfflibmap`, and exact merged-combinational-Lib ABC. Retained useful leaf
modules are mapped separately because the existing source attributes require
it. A final flatten is representation-only after mapping, with no optimization.
The source/top remains default-off and no production recipe was changed.

Actual map: **7410 native cells/34 masters, 2616 DFFHQNx1**, standard area
**1086.25374um²**, FF area762.82560um², actual native FF clock cap
**1241.909376fF**. FF identity:312 mask operands+288 payload pins+2016
selectors. No extra transaction stage is proposed by this coupon: mask/payload
pin capture precedes the original S1 selector boundary. Arbitrary initialization
is flushed within the two actual input/count edges; whole reset is not tested.
The original compact/copy datapath is unreset, and this coupon preserves that.
There are zero reset endpoints here; the whole reset proposal remains HOLD.

Function-proven transparent census retains every actual native input endpoint,
including QN polarity, and removes only native clock-role contacts. It reports
4957 nontransparent roots, max FF14/comb25/input27, zero>32, no unknown drivers
or literals. Max actual load capacitance by those roles is8.07319/14.023092/
15.088194fF. All305 top input bits, including the actual clock, end at native FF
pins; all2616 clock contacts remain explicitly counted. No clock-name exclusion.
A separate unchanged oracle969965293 independently counts7715 drivers including
transparent outputs/16980 logical endpoints and confirms maximum27/no violations.
Its source-predicate PASS does not qualify boundaries, placement or physics.
Only27 no-pin `$scopeinfo` records are excluded as metadata, with the complete
records retained in the independent packet; no electrical cell/pin is omitted.

The compaction output is the **internal gc combinational boundary**, before the
existing S1 capture FF. There are288 combinational output bits and2016 actual
selector-FF output bits. The separate oracle explicitly reports those288
non-FF outputs. This is not a hardened top or a registered-output claim. Actual
S1 capture/merge consumers, top tie repair, whole reset, clock tree, physical
reach/geometry and SRAM remain integration HOLD. Count D timing below includes
all24 actual native destination FF D pins; compaction output timing has no
qualified downstream capture load and is not promoted as stage closure.

## Exactness and causal controls

Fleet-only Icarus simulation PASS: all65536 two-group masks, every one of256
single-group masks with zero and all288 payload basis vectors, all nine slices,
all144 pair/288 quad selector copies. **28,451,072 checks**. The basis sweep
covers every payload bit of the mask-controlled OR network. Independent stable
append reference uses no prefix/onehot equation.

More strongly, symbolic SAT proves all arbitrary payload/mask values against
that independent append/count reference after the required actual two edges.
A second SAT miter proves the **entire actual native mapped graph** equivalent
to the source for all arbitrary inputs, including the native Liberty FF QN
polarity. Both logs contain `SAT proof finished - no model found: SUCCESS!`.
No trace-only or kept-construction claim substitutes for these checks.

Five independently built causal controls fail: inclusive instead of exclusive
prefix; reverse payload lane order; OR adjacent payload into a selected lane;
drop only slice8; corrupt only selector23 of producer0. Each committed witness
names its mutant and failing semantic predicate. None is a timeout/tool crash.
The production original3072-record miter is not rerun or claimed here.

## Actual TT depth/load failure and next structural model

Native graph depth is11 combinational cells to a selector D, eight to raw gc.
Ideal-wire native TT STA at833ps, setup uncertainty60ps and hold25ps gives
worst count arrival **707.328003ps**, setup **+16.280422ps**. This is pathfinding
only: no clock tree, wire extraction, FF/SS corner, hold or physical qualification.
It misses the600ps combinational-stage guideline and30ps margin target, and has
real electrical slew violations. The worst reported input slew is**474.66ps**
against320ps on a pair-count bit3 net driven by `NOR4xp25_ASAP7_75t_R`.

The setup-critical pc16 path is `_06086_/QN` (DFFHQNx1, mask operand lane1)
through eight XOR/XNOR cells, OR3, AOI211 and A2O1A1O1I to `_05968_/D`
(DFFHQNx1; exact source `on.quad[0].own.count[3]`). `sta3.log` retains every
native cell/input/output pin, fanout, capacitance, transition and arc delay;
`critical_path_ownership.json` preserves exact source aliases for each cell.

| Portion | Actual delay | Actual endpoint load/slew |
| --- | ---: | --- |
| Native FF launch |54.818913ps|3 contacts/2.466482fF/QN32.095711ps|
| Low-fanout popcount body through OR3 |272.902950ps|fanout1..4; OR3 4/1.842539fF/19.787155ps|
| AOI211 intermediate |131.473389ps|25 contacts/13.947189fF/258.450256ps|
| Final A2O1A1O1I count bit |248.132736ps|24 FF D/13.411732fF/377.728760ps|
| Whole combinational portion |652.509090ps|whole arrival707.328003ps|

The last two heavily loaded useful gates contribute379.606125ps. This is an
observed decomposition, not an unloaded intrinsic-delay estimate. The earlier
provisional346.64ps slew was one trailing violation;474.66ps is the actual
worst reported slew. Max32 fanout alone plainly does not solve electrical load.

A **not-built**7-pc8/14-pc16 partition would use <=21 sinks per producer:
144 selector owners partition as6*21+18;288 as13*21+15. It retains2016 selector
FF, increases this coupon's operand FF by40 (8+2*16), and reduces D load only
12.5%; no600ps/electrical PASS is predicted. For the WHOLE source, per-group
raw lane-valid consumption including nine compaction operands and the existing
canonical/S1-count operand is **31/24/17/10/31/24/17/10**, max31. Compared to
model eb201, whole valid pin operands rise1216→1312 (+96FF), clock+45.574656fF,
FF area+27.9936um² for the measured native FF. Do not omit the extra canonical
consumer or retain obsolete duplicate valid copies alongside these counts.

The mapped low-fanout body still contains eight serial XOR/XNOR cells although
source pc8 uses a balanced arithmetic sum. Merely retrying seven/fourteen
cohorts therefore lacks a depth guarantee. Before another build, model useful
retained pc2/pc4/pc8/pc16 arithmetic boundaries or 3:2 carry-save compressors:
full adder `(s,c)=(a^b^c, (a&b)|(a&c)|(b&c))`, with each carry shifted to its
next weight, followed by a bounded final count adder. Those are useful count
functions, not retained buffer aliases. Preserve simultaneous original count
age, explicit full operand Q loads, all count bits and true output D loads.
Canonical ABC may reshape each retained leaf; actual native delay/area must be
measured again. Added useful combinational area, electrical limits and physical
fit are NULL. **No changed coupon, extra pipeline stage, full synthesis or route
was launched in response to this failure.** ROOT reviews this model first.

## Reproduction and immutable evidence

Fleet source/output: ot-epyc4 `/srv/opentallas-scratch/claude/hidx-coupon1-1019`.
All work admitted by unpinned ot-run,8GB/2threads for mapping/proofs/STA and
4GB/1thread for final collection. Docker image is
`openroad/orfs@sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29`,
Yosys0.67/2d1509d1b, OpenROAD26Q3-1510-g6cb3f2b704, Icarus version in receipt.
Original exact Liberty files are loaded separately for timing so each timing
header/template remains intact; the merged Liberty is used only for the
canonical native mapping recipe. The STA-only netlist removes signed keywords
from wire declarations unsupported by OpenSTA; connections/bit widths are
unchanged and the original netlist is retained for SAT/census.

Final `run.sh` composes the individually successful source-proof, map, symbolic,
STA and census commands; its shell syntax is checked. The combined driver was
not rerun merely after fixing collection paths. Reproduction pins the observed
container digest. Source RTL and benches remain exactly those proved above.

Scripts and compact receipts are committed under tools/results. Remote
`out/SHA256SUMS` pins full native graph, hierarchical graph, all endpoint ledgers,
Liberty, netlists, symbolic proofs and logs; current local copy is adjacent.
The independent oracle and parser are byte-identical vendored snapshots from
969965293, with no production activation. No REVIEW.json or submission exists.

Preserved tooling failures are explicit: initial source-only bench launcher
passed all tests/mutants then lacked host-native ORFS libraries; first map
collector refused no-pin Yosys scope metadata; a later analysis placement
landed on a staged-input host without the new collector; early STA attempts
encountered missing binary path, unsupported signed wire syntax/missing LEF,
and early SAT prep retained hierarchy. Successful individual receipts resolve
those tool failures without overwriting failed client logs. Source/pass/native
records are unchanged across those collection fixes. No failed gate or failed
functional verdict was converted into PASS.
