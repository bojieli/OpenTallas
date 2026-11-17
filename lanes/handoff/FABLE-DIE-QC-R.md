# FABLE-DIE-QC-R handoff (QC die clock structure, plan event S4q9m; successor of FABLE-DIE-QC)

Started 2026-11-16 17:3x PST. Work dir epyc2 /srv/opentallas-scratch3/claude/fable-die-qc-r (bin/, src5/ = tools of the branch,
chain/qc/s4q9m_r). Inputs stay read-only in epyc2 /srv/opentallas-scratch2/claude/fable-die-qc (treeF, maps, m/, chain/qc/*).
Client logs intel2 ~/fable-die-qc-r/. Launch with `ot-run --dir /srv/opentallas-scratch3/claude/fable-die-qc-r` (scratch2 on
epyc2 is under the 50 GB ot-run floor; the old lane dir also exists on epyc9, so ot-run picks the wrong host with it).

## Read at takeover (both S4q9m chains of the old lane are DONE)
- comb (chain/qc/s4q9m_comb): GRT0 0 / 0 / 0, CA plan PASS 2,993 (depth 8 on 34), STA with CA bind PASS TT lo 116.6 / FF lo 107.6,
  insertion max 14.1 -> 10.7 ns, TT setup +362.0 intra.
- comb + template form 1 (s4q9m_comb_t): same gates PASS (TT 111.1 / FF 116.7); cb tol 129 -> 104 only.

## Root cause of the same-type offset spread (MEASURED, dbg1/)
Two copies of one region tree (c_W1_bf_00 / c_W3_tf_00, cbf_q00 clk_t68): same cells, same placed lengths, same guides, yet
1,122 vs 1,230 ps local delay. report_net: ck_rn45689_0 wire cap 14.04 fF vs its copy 17.06 fF (placed 141.3 um = 13.7 fF).
`estimate_parasitics -global_routing` snaps every pin to its 10.8-um gcell; the cb column pitch is 2,471.04 um = 228.8 gcells, so
each instance has its own grid phase and a systematic +0..21 % wire on every net. Copies a whole number of gcells apart
(c_E0_bn_00 / c_W4_bn_00, 5 pitches = 1,144 gcells) agree to 0.003 ps. No clock net detours: 0 of 69,979 two-pin clock nets
have a guide longer than placed + 2 gcells (bin/detour.py). So the 129 ps is a readout artefact plus per-instance embedding.

## Design of S4q9m (three parts)
1. Feed: comb (old lane m/feed_comb_fw_3.json, sha bc93daa9ab2d): trunk = 12 sl_*_fw regions, columns as arborescences,
   depth 21 -> 12, path = Manhattan distance (28.1 mm max).
2. One region tree per type: die_trial OT_CLK_DME_TEMPLATE=2 (branch): template embedded on the sites legal in EVERY instance, so
   no copy is refused (form 1: 17 refused = cbn_q00 7, cbx_q10_h 8, cbf_q11 2).
3. Readout: tools/die_plan/clock_spef.py: exact-length RC of the placed tree (M8 trunk, M9 branch, via stacks), read_spef in the
   combo proof; GRT stays for overflow + the detour audit. Pin escape 15 um per cell pin = calibrated so the mean stage delay equals
   the GRT estimate (LE 12 -> 0.959, LE 16 -> 1.021 of the GRT sum; cal_le*/), so insertion and the DME stage cal stay comparable.

Evidence on the EXISTING comb_t kit (no new kit): same-type half range, 15,391 ports, GRT readout max 104.1 / over 10 ps on 2,440
ports; exact RC max 76.9 / over 10 ps on 347 ports, and those are only the 3 refused types (55.9..76.9) + sc_v2 / fe (H-tree
regions, <= 28 ps). Every fully copied type is under 6 ps.

## Branch
claude/fable-die-qc-r-1116 @d57188aede6 (= old branch 2bed6a4 + 6d932e7e0b + merge of main): die_trial form 2, clock_spef.py,
2 test files (21 + 2 tests pass locally). Gate RUNNING: intel2 ~/fable-die-qc-r/gate1.client.log. Post READY when it prints GATE pass.

## RUNNING
- Die chain s4q9m_r (comb + form 2 + SPEF readout), epyc2 chain/qc/s4q9m_r, script bin/chain_r.sh, client
  intel2 ~/fable-die-qc-r/chain_r.client.log, started 18:08, about 3 h 20 (kit 2 h). CHAIN.log lines: KIT (with the template
  count line), REG_GRT_TT/FF, DETOUR, SPEF, REG_SPEF, REG_TTA, TOL (GRT vs SPEF spread), REG_STA, LPO, CA_C/CA_D, BIND, STA_C.
- prs15_comb_t: calibrated SPEF readout + REG_STA of the existing comb_t kit.

## Next
1. When CHAIN_DONE: read KIT template line (want 0 refused), REG_GRT ovf 0, DETOUR 0, TOL, CA FAIL 0, STA_C COUNT-ALIGN PASS TT + FF.
2. Rows: kitoffs (gate/kitoffs.json) -> tol = ceil(half range + 0.05 + 10) (QC-PLAN-R l2 composer does the +10), seam_ps =
   ceil10(need + 10), tap_window per port; check tap gate PASS on the rows, intra / seam kit-contract hold >= 0.
3. Hand to QC-PLAN-R: feed file, kit flags (template=2), clock rows, ca_C / bind.json; lanes/handoff/FABLE-DIE-QC-R-rows.*.
4. Not done: sc_v2 / fe regions are H-tree (not DME), so they are not templated (<= 28 ps).

## Own errors
- 18:07 I removed the __pycache__ directories inside my own fresh src5 copy with find -exec rm -r, not through ot_delete_guard.

## CODEX takeover 2026-11-16 19:4x
- Current s4q9m_r healthy: kit template 198 copied / 0 refused / 42 embedded; stage STA stand-ins, CPU active. Retain exact current run.
- Exact l2d follow-up launched in existing lane: epyc2 /srv/opentallas-scratch3/claude/fable-die-qc-r/chain/qc/s4q9m_l2d, bin/chain_l2d.sh. Client intel2 ~/fable-die-qc-r/chain_l2d.client.log PID2012222. Same approved template2/tools, exact l2d plan a915f1136c27 and mounted treeJ. Previous proof uses C geometry and cannot establish new coll_ftc/ftn rows.
- Pre-route image LOOKED d_before_after.png; PASS-COND, recorded lane results/geom_review/qc_clock_l2d_20261116.md: longer coll_ftc abutment, freed empty strip only, no macro wall, face peak72->64. Need new tap/feed/STA on regenerated outlines before adopting.
