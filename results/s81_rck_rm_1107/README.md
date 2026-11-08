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

Proposed compact memory/read-select/r_m core1800..1960×90..250um intersects no current macro. Existing named RM FF area1686.6um² is only a lower-bound area input; anonymous combinational logic and changed flop count have not been synthesized. No PG/placement approval follows from empty macro intersection.

64eight-bit slices keep each registered we/rsel Q bit to8data loads. Shared pointer→64copy-D decode and total1029profile-local async-reset bits (512we+512rsel+1idle+4publication, replacing old64we) remain HOLD: processkeep alone cannot localize their D wires/reset routes. Need compact pointer/control placement, explicit copy-D/Q/wire/C budgets and parent reset-domain budgeting. Do not silently adopt held reset-copy625.

Existing producer DOUT q_d spans1434..1873×28..360um. Place w_dq between each producer and compact memory slice: worst rectangular source→target L1≈796um, two legs≈398um. Proposed core→fixed BOUT face near2881×6..119um has worst L1≈1330um: existing one free r_d row gives two ~665um legs; two output relay rows give three~444um legs. This is a geometric estimate with little450um-heuristic margin, not extracted RC/STA. Actual per-bit trajectories, coherent DATA/control clock cohorts, reset-D/Q legs, buffers, PG and route capacity require review before one future PLACE pilot. No physical release authorized here.
