# DIE-HEAD-11 (2026-10-28): HEAD duty fix (inverter spine) + start-stage emitter

Labels: CHECKED = my own tool runs on the named files (not NUMBER-CHECKed). ESTIMATE = a model claim.
Runs: intel2:/srv/opentallas-scratch2/claude/die-head-11/{duty,inv}.

## 1. Duty-cycle risk on the BUF spine (CHECKED)
- Tree: sfb250 spine_fishbone, 1493 BUFx24.
- Tap fall-rise: TT 173.9..419.6 ps, FF 147.6..369.1 ps.
- OpenSTA min_pulse_width, with one DFFHQNx1 sink per tap (`scripts/mk_mpw.py`):
  - TT: 60/326 violated, worst -34.4 ps.
  - FF: 0/326 violated.

## 2. Inverter spine (CHECKED)
Tool: DIE-QC-11 die_trial `--clock-cell inv2` (local commit 1465eff51c, not a fork). Same plan and flags as sfb250. A BUF rebuild with that tool reproduces sfb250 ctree.v/ctree.tcl byte-identically.

| form | cells | max slew/cap viol | tap fall-rise TT / FF (ps) | MPW viol TT / FF | worst MPW slack |
|---|---|---|---|---|---|
| BUF rep 250 | 1493 | 0 | 173.9..419.6 / 147.6..369.1 | 60 / 0 | -34.4 |
| inv2 rep 250 | 1840 | 3 (377.6 > 320 ps, top-rib legs) | -11.3..19.7 / -1.5..34.5 | 0 / 0 | rejected (slew) |
| **inv2 rep 200** | 1904 | 0 | -7.3..14.1 / -1.1..25.3 | 0 / 0 | +322.9 TT / +336.2 FF |

inv2 rep 200 on the real-netlist die kit (die-head-5), die GRT incl clock at 50 iterations, cnp 0:
- Overflow is 0 at TT and FF.
- Tap fall-rise: TT -10.5..+6.7 ps, FF -1.3..+20.0 ps.
- Max tap arrival: 5892.8 ps TT.
- Geometry: 0 illegal cells, 0 cell overlaps. The render `inv2r200.png` was viewed.

## 3. CA gate on the inverter arrivals (CHECKED; `scripts/run_ca_inv.sh`)
- Proof: built with mk_proof --tree-path. On the BUF run it reproduces the die-head-5 proof byte-identically.
- Pipeline: landed_phase_ocv -> spice_scale -> count_align_plan with `--start-tree clock --start-clean width`, then bind, then die_sta_related.
- die_sta_related settings: related pairs, TT 250 / FF 202.5, table, shared droop, spice, cppr-lca.

Results:
- 427 D4, 0 FAIL, plan min 138.0 ps, MC 2000 with 0 violations.
- Die STA: TT 137.8 PASS, FF 159.2 PASS. Start ports 518/518 clean by width.
- Stage count: 193 (38 retimes).

## 4. Start-stage emitter `tools/die_plan/start_stage_emit.py` (shared, new file, opt-in)
- `emit`: takes BIND + PROOF + die_trial clock dir (+ plan for SiteMap legality). It gives each virtual stage:
  - one `ot_dp_landing_origin` (3 sync + PAD + EDGE_FALL);
  - a row segment beside its node cell, clear of all clock cells and other stages;
  - a tap port `t_st_<cell>__clk` on the node net. On an inverting tree, an inverted node takes the true-polarity input net instead.
- `proof`: adds the measured stage clock pins as `__st__<path>` taps. `die_sta_related.virtual_tap` models only absent stages, so the plan, bind and die STA then time the built arrival.

HEAD results (CHECKED):
- 193 stages, 600 flops, max 3.78 um from the node cell.
- 33 inverted nodes take the input net.
- 26 die inputs and 326 die outputs. iverilog compiles the module.

Real-netlist GRT with the stage taps:
- Overflow is 0 at TT and FF.
- Partition taps shift by +2.2..15.7 ps TT.

Replan on the measured proof (`scripts/run_ca_st.sh`):
- 427 D4, 0 FAIL, min 137.1 ps, MC 0 violations.
- 517/517 start ports clean.
- Die STA: TT 137.0 PASS, FF 159.3 PASS, start-skew 0/517.
- Stage set: 192 stages, all among the 193 emitted (1 retime dropped, 0 new), so it converged in one pass.

Next slice: compose. Regions whose parent is a stage, or that launch one, get a dedicated start in/out pin. Today clock_landings needs the tree port to be a landed data crossing.
