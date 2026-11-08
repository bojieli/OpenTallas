# Private RM_LOCAL4 source/model proposal — physical HOLD

Captured from vH-source branch codex/rck-vh-1551@a5eb3faa18 (base ebd0e1153f); this proposal is recorded on an older intel1 metadata base because the current source tree cannot expand on intel2. This branch does not claim current-main ancestry or adoption. RM_LOCAL4_vs_a5eb.patch is the exact current-source patch; rm_dut.sv is the actual enabled 512-bit/depth8 module. No kit/PLACE/CTS/GRT launched. Reset-copy625 remains a separate proposal.

## Actual parent integration and cycle ledger

Actual COL/native chain: PMA RX model in pma_rck → native-flat-LP decoder q_v/q_d (pma_rck) → ot_s81_rate_match u_rm (write pma_rck; read clk) → COL BOUT egress transport. This change edits only the actual RM module, not native AM/syn/ptx/decoder or COL transport. The writer reset is rn_r and reader reset rn_t; their domain synchronizers remain inherited. Current proof is the actual RM slice, not a full native decoder/COL integration proof.

| Boundary | Delta vs vH RM_STAGED | RM-only delta vs original unstaged |
|---|---:|---:|
| Accepted write → physical memory commit | 0 write edges | +1 write edge |
| Gray write-pointer publication into reader synchronizer | +1 write edge | +1 write edge |
| Local read pipeline | +2 read edges | +3 read edges |

Commit and publication above describe overlapping events, not two serial write-cycle additions: new publication follows the already-staged commit. Current base has two read stages (r_m,r_d); candidate has four (rsel,r_m,r_pipe,r_d). Fully synchronized wp_g2 drives empty/read select; no metastability-prone wp_g1 lookahead. Whole RX/POR latency must also include actual PMA, native decoder and COL transport and is NOT asserted here. One writer edge can quantize into different receiver-edge latency by phase. No constant whole-chain shift claim. Gray publication changes EMPTY/IDLE/full-boundary behavior; arbitrary overloaded input/fault identity is not asserted.

The parent ≥64-low reset contract is inherited. Async-cleared rsel/r_idle produces IDLE after three reader data-flush edges; r_m/r_pipe/r_d are unreset. No new reset-release edge is claimed. At extreme unrelated frequency ratios, freeing rp before the delayed memory-select capture needs a separate protocol proof; this benchmark does not establish arbitrary clock-ratio safety.

## Actual-module result

Ordinary ot-run16GB4T on intel1 physical scratch2, unit oth-ubuntu-570660-1794097462, RC0. Verilator actual modules, actual old staged source captured independently from ebd0e1153f for default-off identity.

3583 checks, zero errors, four reset epochs. Full512-bit accepted non-IDLE stream compared against accepted-write queue; stopped wclk immediately after enqueue/before commit; paused reader eight accepted/ninth sticky overflow; paused-reader IDLE shedding at occupancy6. Publication and all64 selectors directly checked each relevant edge; output relay checked directly so an ordered-stream-only test cannot hide cycle loss. Four source mutants detected: shifted read bank961, live instead of staged write data960, early Gray publication966, missing output relay1398.

Clocks are hardcoded .834ns write and .833ns read, initial phase137ps. This single-phase finite simulation is not ±300ppm directional coverage, formal CDC proof, arbitrary-reset proof, or full-native integration. No additional compile/sweep launched. run.sh reproduces the exact source fixture; result.log is the terminal result. Golden and candidate default-off are separate actual source captures, not a behavioral FIFO model.

## Measured physical class and required repair

Actual vH RM memory4096FF bbox1394..1865×42..391um; R_m512FF bbox1410..2171×26..383um (760×357um), spanning11tap roots. Read pointer near1627..1638×193..226um has root clk_t4, while R_m spans other roots. CTS setup worst rp[0]→r_m[193] has approximately1.4ns wire and is outside one-ECO near-miss class. Existing native RX syn/ptx failures remain separate.

**Supersedes the original444um plan:** registered hops must be≤405um on every layer.450um is only the electrical-repeater interval. The old rectangular3×444um output estimate is FAIL, not PASS-COND. The first budget also used intrinsic DOUTq_d instead of the actual intervening face register; that source is corrected below.

Actual512-bit matched source/destination budget uses u_dec.u_face_q_d.q[bit] → slice[bit/8] → u_bout_coll_o0/q[bit]. Proposed144×144um core1828..1972×98..242,64slices of18×18um, with each slice centered1837+18*(slice%8),107+18*(slice/8). Every bit is bounded over any cell site in its slice (±9um in x/y;18umL1 margin), not arbitrary interchange across the full core. Existing w_dq is placed halfway from its actual face producer to that slice; two free output relays subdivide the slice→actualBOUT trajectory into three legs. Maximum planned registered input hop340.353um, output396.767um, zero>405. No additional data edge is required for this conditional matched-bit model. Strict per-bit/slice placement and coherent clock cohorts are mandatory; this is not an actual placed result or RC proof. See rm_405_perbit_budget.json and viewed rm_405_matched_bits_HOLD.png.

Ordinary8GB2T actual-source generic Yosys proc/memory_map/opt measured7208FFbits, all64rsel/we copies retained (512bits each). This is not ASAP mapping/area or timing. Existing named RM FF area1686.6um² provides only a lower-bound input. The compact footprint avoids macros; actual anonymous logic, clock/reset buffers, PG straps and route capacity remain unmeasured.

64eight-bit slices keep each registered we/rsel Q bit to8data loads. Shared pointer→64copy-D decode and total1029profile-local async-reset bits (512we+512rsel+1idle+4publication, replacing old64we) remain HOLD: processkeep alone cannot localize D wires or reset routes. Need explicit pointer/control copy-D/Q/wire/C budgets, reset source/copy/consumer grouping and pin-flop arrival spread. Do not silently adopt separate held reset-copy625.

A preliminary bridge point(1800,250) could place a replacement same-phase final synchronizer copy between the actual first sync and local RM: reader firstsync(1638.36,361.53)→copyD273.17um; writer firstsync(1647.54,366.12)→copyD268.58um; copyQ→any compactcore site at most324um. This is only geometric feasibility, not source adoption: writer+reader copies need actualCOL phase proof plus clock/recovery/fanout/cap and parent reset-domain budgets. Inherited reset625 proves its original reader-copy mechanism, not this new writer copy or combined fallback.

Existing vH nativeRX syn/ptx classes remain outside this repair. No physical pilot before actual area, control-D/Q, coherent clock roots/arrivals, reset and PG/route-capacity review. No kit or physical release authorized here.
