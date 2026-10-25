# W128 HC physical cut — parked candidate, NOT merge/adoption ready

Native source snapshot `codex/hbm-native-1025@591bcf802`, copied into a branch based on HBM-CORES `f5bf82c17`. No physical route or timing closure is claimed.

Banks: one reusable pair master contains two unchanged eight-lane HC leaves, two weight SRAMs, one x SRAM and 768 raw capture flops. Eight pairs cover all sixteen groups of a W128 bank. Four actual native bank styles (plain, first, feed, terminal) pass the same-cycle boundary composition miter and deliberately wrong SRAM write-enable mutant. The first bank has its own master without the 512-bit `sum_in` interface. Plain/feed/terminal have 1,605 pins; first has 1,093. Structural cut adds zero cycles; future face shells add one input plus one output cycle and must be separately bound/priced.

Qhub: four 32-input, five-level subtree masters plus the original three upper adders and parent control preserve all seven FP32 tree levels and per-node fault timing. Common subtree master has 1,027 input / 64 output bits. Boundary/state-point miter proves 16,253 equivalence points; first adder bit mutation is caught (one unproven `s_i[0]` alias). The first classifier expected the adder name and returned infrastructure failure; the actual counterexample is the intended alias. The original failure log is retained remotely. No reset-delay mutant has run yet.

Measured TT mapping supplied by the HBM parent: pair 115,521 cells / 13,970.2644 um² logic + 28,528.56288 um² SRAM; subtree 130,293 cells / 13,572.50742 um² logic. Each fits the 400k hard cap. Candidate pair outline 250.56 x 267.84 um permits eight rows with 34.56-um gaps in a 2,419.2-um bank. Capacity agent recommends x=25.92, preserving 17.28-um left and 95.04-um right free channel after halo in the narrowest bank. This outline and channel model have NOT been rendered/reviewed or placed; no route authorization.

IMPORTANT RESET FAILURE: `OT_FP_DATA_NORST` does not affect `ot_hdc_fp32_mul_lat`, whose DRST default is 1. The HC lane leaf omits the multiplier DRST parameter even when ADRST=0. Current pair census still finds 8,388 reset-controlled FF bits (20 at reset delivery depth 1, 8,368 at depth 2), with 22,482 plain FF bits. Required next change: explicit multiplier `.DRST(ADRST)` plus valid-masked equivalence and mutant, then regenerate and remeasure. Subtree has only 217 reset-controlled valid bits at depth 1 and 18,724 plain bits; no local reset relay. Upstream bank/qcen reset relay ownership remains outside these cuts. The census measures reset delivery depth, not functional pipeline length. Final CLOCK/native RESET acceptance and timed recovery are still owed.

All raw designs and scripts: epyc3:/srv/opentallas-scratch/claude/codex-hbm-hc-physical-1025/. Bank variants are `plain_norst`, `first_norst`, `feed_norst`, `term_norst` (the directory suffix is historical; see the DRST failure above), each with `native128.json`, `pair_cut`, `pair_compact/compact128.json`, exported core SV, port map, and `miter/result.json`. Qhub data in `qhub128_hier.json`, `qhub_cut`, `qhub_compact/qhub_compact128.json`, exported SV, port map and `eq_r2`. The JSON designs preserve the exact new-core-to-parent connections; a final per-pin native reference manifest has not yet been exported.

Remaining: remove HC multiplier data resets and gate it; export exact per-pin binding/pin tables for all styles; render and integrate the channel-aware B2o floorplan; implement density clock taps; adopt/price face shells; re-kit and close timing. Native root still needs NQ2/TPRE7 physical cuts for its seven old NQ4 views; the old `ot_hbm_hc_root_static -> _s` alias must stay excluded until corrected. No owner question was introduced.

## HBM-W128 (Claude, 2026-10-25 04:40 PDT): reset fix, regenerated cuts, kits

Branch `claude/hbm-cores-w128-1025`.

- **Reset fix (RTL)**: `ot_hdc_v41x_hcp_lanes` and `ot_hdc_v41x_hcp_stage` now pass `.DRST(ADRST)` to `ot_hdc_fp32_mul_lat`, the same way they already did for the adder. With ADRST 0, only the multiplier valid bits are reset; the data FFs have no reset. No cycles added.
- **Regenerated cuts** (`drst_fix/`, tools `tools/hbm_b2/w128_drst/run_regen.sh`): all four bank styles were re-elaborated, cut, compacted and exported.
  - Miters pass again: plain 17919 / first 21985 / feed 18407 / term 17675. The write-enable mutant is caught in each one.
  - Pair reset census: 8388 -> **260** reset-controlled FF bits (20 at depth 1 + 240 at depth 2 = the leaf reset flops plus valid bits). 30610 plain FF bits.
  - The qhub subtree has no multiplier, so it is unchanged: 217 valid reset bits, 0 data reset bits.
- **One pair master**: plain, feed and term export the same circuit (`drst_fix/pair_master_identity.json`, equiv 3398/4422 proven). So there are three core types: `ot_hbm_hc_bank128_pair_core`, `ot_hbm_hc_bank128_pair_first_core` and `ot_hbm_hc_subtree32_core` (`rtl/hbm_accel/cores_w128/`).
- **Valid-masked checks of the fix**: `tools/hbm_b2/w128_drst/{run_mul_eq.sh,run_drst_sim.sh}`.
  - Multiplier: k-induction miter.
  - Multiplier and 8-lane leaf: 4-state random simulation, gold = pre-fix source.
  - Each has two mutants: valid bit unreset, and output data bit flipped.
  - Results are in `drst_fix/drst_check.json` when collected.
- **Views and kits** (`physical/die_plan/hbm_arch_cores/w128/`): pin tables were derived top-down from the B2o Rh bank column and q_hub slot (see `mk_w128_views.py` docstring and `geom/`). Kits use `gen_core_kit_hbm.py` with the face shell on: +1 in / +1 out cycle on every crossing.

### HBM-W128 CTS review + native bind note (2026-10-25 05:09 PDT)

Place+CTS (GOAL=cts, review image only, no route):

| core | cells (placed) | fill of free | bins>0.8 | pin->reg p90/max um | OT_HOLD_GATE (post-CTS, pre-repair) |
|---|---|---|---|---|---|
| ot_hbm_hc_bank128_pair_core@ba77076d4cc8 (x120) | 122,020 (synth 152,716) | 0.49 | 0 | 6.8 / 11.0 | **FAIL** wns -116.46 ps, 1827 reg2reg ep; ports -235.7 |
| ot_hbm_hc_bank128_pair_first_core@0c39789d46b1 (x8) | synth 139,823 | 0.32 | 0 | 7.3 / 9.7 | PASS wns -63.35, 1070 ep |
| ot_hbm_hc_subtree32_core@3abde8dae72d (x4) | synth 135,546 | 0.28 | 0 | 8.1 / 11.9 | PASS wns -14.57, 314 ep |

pair_core hold FAIL: CTS skew report shows a N-face write_addr face flop at 519.8 ps
source latency vs SRAM macro clk 288.5 ps (231 ps skew). Structural fix before route:
macro-clock latency balance against the 3-face (W/E/N) face-flop ring (pair_skew / macro
insertion), not hold-buffer padding. Needs a pair_core re-kit; first_core passes with -63.

DRST check: results drst_fix/drst_check.json (gate PASS; MUT_NORST/MUT_DATA caught;
SAT tempinduct inconclusive, killed).

TOK-HBM native-bind note (pin/face cycles; native NQ4/NQ2 root views NOT changed):
- every hardened pair adds the face shell: +1 in, +1 out cycle per crossing.
- sum chain: +2 cycles per bank hop UNLESS the native bank sets the sum-bus CPI/CPO
  pin registers to 0 (shell flops take their place) while keeping descriptor CPI/CPO;
  then net added = 0 per hop. Recommended.
- write path (write_addr/data/we): +1 (shell in-flop, no matching native register to drop).
- qhub: 4 x subtree32 (2x2 in the old 734.4^2 W64 slot + 103.68 soft centre row);
  +2 cycles on the reduction (shell in+out) unless the qhub data pin register is dropped.
- bank context: sum hop 129.6 um (380.16 bank) / 302.4 um (552.96 bank), both < 405 reach.
