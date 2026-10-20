# smh_pvm_ref_s7b -- PVM distributed source (H.STA.BLK.14.3.1, L2H-SMATT/PVMD 10-19)
Parallel twins smh_pvm_ref_s7a / smh_pvm_ref_s7b (same RTL). Bind the first to close; cancel the other.
Successor of smh_pvm_ref_s5a/s5b (same geometry). Current cent33 source: separate kept status barrel counter from entry decoder, +0 data edges. In-flow source cc33b9ac7 failed one c_ent[1] sequential driver at33; current actualORFS mapped census PASS63713/max32; physical gate pending. Historical standalone r4 PASS below did not bind the later ORFS mapping.
Why (s5): smh_pvm_ref_s4a (SAFE2) CLOSED but carried the waived single-source ev / tag_d[14] input-pin capture (~1,500 loads);
the coordinator rejected that waiver. RTL ot_hbm_sm_pv_merge_distributed (+_core): Codex fae1ece6e reviewed and fixed,
see results/arch/hbm_pvm_distributed_source_1019/README.md.
Floorplan: 432 x 302.4 (parallel variant, +86.4 um): macro at x 129.6 / y 43.2 R180 (lattice); W band 127 um, E band 131 um for the doubled source copies beside both data-contact faces, N band 103 um; single centre root.
SAFE-DESIGN checklist (owner 10-19):
1 Pins: PASS (source-registered) -- every input captured at the pin in RTL then kept second copies; every output one RTL
  register; flow pin_regs OFF with reason (a flow reg would add a third input edge). Reset: RTL lands rst_n in 2 stages
  (2 first -> 8 second) then 54 third-level groups; flow reset_landing OFF with reason.
2 Reach: PENDING -- full buffer-transparent launch→capture placed reach must be <=405um; a direct-net-only diameter is insufficient. Pin->first capture anchored at the pins; no blanket cone-locality claim.
3 Fanout: PASS current actualORFS census63713/max32/0violations/0roleerrors, 12TT/FFLib receipts results/arch/pvmd_cent33_1020. Historical actual predecessor ORFS native census 63725 roots, max33, one c_ent[1] sequential violation. New kept c_ent_status handles e_busy/e_fl/e_k status readers, while c_ent drives entry decode. Both reset identically on cohort10 (24->27 terminals), same edge/cycle. Explicit reset-clear coupon and every-edge bp observer cover both. Current kept c_ent loads12/11/12 and status9/18/7, reset/comb drivers<=32. No waiver.
4 Depth: PASS -- SAFE2 core (operand registers, LAT7 adders), 8-bit slice selects shorten the operand cones.
5 Storage: PASS -- 32,768-bit stack = one 64x512 p192 SRAM; no new indexed storage.
6 Floorplan: PASS/WAIVED -- macro on the 43.2 lattice, std bands at both contact faces + N, continuous rows; util low
  (macro-bound) WAIVED as s4a.
7 Clock: PENDING current gate -- single centre root (historical s4a spread27.8/26.7ps); io_hold_margin0.03. Native protected/fixed PG audit required before review; exact final6_final ODB/SPEF PG receipt before publication.
8 Schedule: PRICED -- +1 input/result edge (DS +40 cycles/token 0.0069%, Qwen +72 0.0057%; price.json) + 1 cold release
  edge; benches exact/tight/reassert/stopclk/xrand PASS vs SAFE2 at +1 age; 12 mutant witnesses FAIL.
smh_pvm is not a critical prefix: submit after a clean gate.

Current source06641422a, proofdd97505e6, nativec0b9b7c5b. Model delta +0data/reset/II edges, +3flops, synthesized area35869.2929→35881.21934um2 incl SRAM26363.2787, std9517.94064um2 (model_delta.json). ROOT68b9cad6c helper refresh; no prior gate/ODB relabeled. Gold exact/stopXRAND/legacy240checksPASS and causal MUT14 async-only STOPCLK65nsFAIL.
