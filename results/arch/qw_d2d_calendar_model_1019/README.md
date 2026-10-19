# D2D remaining calendar/STATUS/control/reset fixed-point model

**MODEL ONLY; no new RTL, native SAFE claim, gate, GEN, or binding.** Source `cec6a7abc` remains the partial SF6U prototype: 224 actual native violations, including STATUS 491→511 regression. Its existing 200k lockstep, actual full SRAM-leaf 5996 checks/all useful-AND truth states, 35-layer pair and four causal mutants remain the functional evidence; none is rerun, weakened, or relabeled here. Original transport phase, compiled TXDP, first-use and token prices are untouched.

This packet replaces the earlier incomplete 284-FF reservation with a whole native-graph copy-demand model. It is a conditional sizing calculation, not an implemented architecture: source state identity, first use, kept genuine Boolean equations, polarity distribution and physical legalization are still prerequisites. No unsafe held-feedback copy or arbitrary initial-state equality is authorized by a graph result.

## Source and native identity

The only OpenROAD operation reads preserved SF6U `1_synth.odb` from the original fleet directory, read-only. ODB SHA256 `0e60d56ae9e50e4bfe2573a17c4728206c57aac84cd582c8a609553b2a63e903`. OpenROAD `26Q3-1510-g6cb3f2b704`, original ORFS image. `dump_graph.tcl` reuses the exact original census algorithm but records **every unique sink pin**, rather than six examples. Includes all drivers/FF/comb/top-input/reset/macro/tie roles, transparent BUF/INV/HB traversal, no row cap. Exactly 30,782 nonclock roots /37,928 cells /224 unsafe roots agree with the original packet. All root-list lengths are checked against recorded loads. Native input/output directions come from ODB, not cell-name guesses.

`fixed_point.py` starts with one copy per original physical cell. At each iteration a destination's copy count multiplies **every** incoming native input pin, including D and RESETN, not just the favorable target output. Required copies of a genuine logic/FF/tie driver are ceil(total updated demand/32). Copy counts increase monotonically to a fixed point. Top inputs and all macro cells are fixed, so any newly unsafe fixed role is reported as an explicit HOLD. The clock is excluded from a data-fanout count and its additional load is separately priced. Output ports remain individual fixed sinks. No macro, table-data FF, or storage bank is cloned. This is an abstract pin partition; source realization must demonstrate that the partition respects reset/enable/state identity and native gates survive mapping.

## Whole remaining cost and recursion

| Model iteration | Added physical cells | Cells whose copy count changed |
|---|---:|---:|
| 1 | 300 | 224 |
| 2 | 304 | 3 |
| 3 | 304 | 0 |

The second iteration is essential: first-pass final-reset and tie demands grow after other state copies. Whole fixed point adds **169 FF +93 genuine Boolean cells +42 tie cells**. Existing master dimensions price these at respectively 55.75392 /8.25228 /1.83708 um², total **65.84328 um²** beyond SF6U's measured 5911.86924. Reference soft area 5977.71252 um² /11,724 soft FF, four macros unchanged. Clock load grows by169 real soft clock pins. These are reference-master costs, **not an area upper bound**: kept source decoding may map differently, polarity drivers, actual clock/PG wiring and legalization need further cost. Model utilization against the corrected gross central band is about42.47%, before those additions; no parent fit is granted.

Conditional maximum balanced logical pin demands: FF32 /comb32 /tie32 /top-input22 /macro1. No fixed-role excess. These are mathematical partition bounds, not a new native census. `fixed_point.json` records every cloned root and exact original master, updated demand, copies and bound. `boolean_operands.json` records immediate native operands and all state/input/macro/tie leaves of every duplicated Boolean root. Every kept source helper must realize the actual equation; BUF/INV/alias or one-operand identity boundaries cannot implement this model.

## Precise source obligations

| Source cone | Model additions | Required source proof |
|---|---:|---|
| Two calendar advancing one-hot reads | 64 FF | Two 16-bit table-output ownership halves, same original D/clock/reset/priority. Include rotate/self-feedback and control loads. |
| Two calendar segment-base one-hot reads | 64 FF | Same-edge configuration loading into both halves; arbitrary unreset initial copies cannot be assumed equal. Prove segment configuration precedes selected-segment first use. |
| Ten low configuration data pin captures | 10 FF | Unconditional copies of original top-pin D on original input edge. No source-pin overload: full recurrence still max22. Preserve last-write/start exclusion. |
| Segment selects | 4 FF | Unconditional same input-edge D; three total copies per TX/RX segment0 role. No added edge or phase offset. |
| Epoch-begin roles0/1 | 8 FF | Three/seven total copies of original recovery follower D, same reset and edge; unchanged epoch ownership and abort behavior. |
| Write counter bits1/5 | 2 FF | Preserve canonical next-state function, reset, epoch clear and qualified increment. No independent unreset feedback. |
| Regional reset final stage | 17 FF | Regions1/4/5/6 need4/6/7/4 total final-stage copies, respectively. Same predecessor D, original clock and assertion/release; no new raw async input. |
| STATUS slot | 15 Boolean cells minimum | Sixteen private actual live slot predicates, <=32 actual pins each. No FF or edge addition is mathematically required; prove kept source equation and mappings. |
| STATUS held-result epoch reset mask | 4 Boolean cells minimum | Five private `local_reset AND NOT epoch_begin` masks, 30 RESETN loads each, preserving all original clears. |
| Other calendar/write/ownership logic | remaining74 Boolean cells | Full per-cell operands in JSON; row write halves preserve cfg qualification, written-map clear wins collision, fire/rep/start/halt priority unchanged. |
| Constant distribution | 42 real tie cells | Physical constant distribution only, never replace a functional signal or suppress a fault. Recount actual tie/reset/repair pins at native stage. |

The +169 FF decompose into 74 reset-initialized copies and95 plain/unreset copies. Of those95,64 are held segment-onehot state requiring an actual config-before-use proof;10 config-pin and4 segment captures are unconditional input captures;17 are unconditional final-reset-stage captures. No complete first-use proof is claimed. Keep original canonical state for any domain whose equality cannot be established; do not create feedback clones merely because a formal induction assumes matching values at time zero.

STATUS native `_31344_/Y` has511 sinks and needs16 balanced private predicates. Its two immediate live operand roots currently drive10 and5 pins. Fifteen extra native operand pins give25 and20, so an additional registered event stage is unnecessary for this sizing. Native truth is NAND-equivalent to the existing slot polarity; source must preserve complete `tv AND (tp==2)` decoding and held-result/tx-payload priorities, not simply clone an already overloaded slot wire. Kept full-decoder realization can cost more than the native minimum and must be counted anew.

Reset recursion is explicitly nonlocal: TX/RX calendar reset demands85→117 from copied one-hot state, giving4 final copies rather than3. End-control179→181 gives6, slot-link200 stays200 gives7, RX85→117 gives4. STATUS mask150 stays150 gives5 private masks. Original `ot_rst_pipe` has two async face synchronizer FF followed by two plain regional pipeline stages: this packet preserves that original four-edge release path, the two regional assertion propagation edges and clock-running requirement. It does not relabel the path as a two-edge reset, remove inherited reset stages or add raw-async copies. The exact assertion/recovery behavior must be exercised with original reset pulses, stopped-clock assumptions and earliest production first op before implementation can qualify.

## Storage, physical fit and schedule remain HOLD

All four real 64x137 p192 SRAMs and all read/write/data/mask/repair/contact roles remain unchanged. No fake indexed flop substitute. Two existing independent1024-bit calendar arrays total2048 bits, with no array duplication; source shape must remain explicit and future storage growth reopens the SRAM requirement. Same-edge OLD read/bypass semantics must stay identical to original causal controls.

345.6x216 outline /four57.912x45.672 macro bodies /43.2 lattice origins remain only a proposal. Full standard band is y88.872..129.6 =40.728 um, gross14075.5968 um², not43.2um. Macro pin density is5.23/um; full-face allocation must preserve <=6/um after clock/reset/PG cutouts. Outline diagonal407.55um exceeds405: exact source placement stage/reach proof required. No current slot regrant, PG/access/escape proof, native clock insertion/spread, stage-depth/electrical timing or source production phase proof is claimed.

Zero added edge/bit-boundary/bandwidth target, unchanged TXDP and3:4 source phase. Because there is no implementation, the composed token-cycle delta is **not measured**. Existing pair C2K63/K2C62/1840cycle roundtrip is functional PHY5 evidence, not production pin-clock/first-use qualification.

## Bounded next source recommendation

First implement only the **STATUS private live decode plus its five held-result reset masks**, default-off and with a distinct source master. This contains no new storage or functional edge, minimum+19 native logic cells /1.66212um² reference-master area, and no first-use equality premise. Before any source change, freeze explicit per-bit ownership, actual decode equations/truth table, complete native operand budget25/20 and5+ original reset/epoch inputs, exact source age ledger, and a source-level area allowance for full decoder retention rather than assuming native NAND cost. Run original200k/35-layer/causal witnesses plus all slot/decode truth states and reset/epoch priorities. Then fresh all-role native census must show STATUS511 and reset150 repaired and every regression counted. All unrelated remaining roots stay HOLD; this partial step never authorizes physical gate or binding.

A later source implementation of all calendar copies requires real config/start/segment first-use and arbitrary-initial-state proofs, exact all-copy D/reset/enable equations, complete native census, depth/clock/area and physical-parent model. No generic helper changes, gates, routes or data timing exceptions are part of this packet.

## Fleet receipts

Only read-only extraction and analytical Python ran via unpinned `ot-run`, data-local to original ep8 ODB. Initial extractor unit1638635 failed127 because image PATH lacked `openroad`; no output was treated as success. Corrected `source /OpenROAD-flow-scripts/env.sh` extractor unit1645934 completed0. Analytical runs1650644,1658006 and1665592 completed0. No simulation/synthesis/place/route was launched. All units are terminal. Exact scripts, complete input graph and checksummed model are committed; raw graph files are gzip-compressed losslessly; the model reads either representation. Reproduce on the fleet with `python3 fixed_point.py` beside the committed inputs.
