# QC-PLAN-G — Codex takeover 2026-11-16 22:18, current 23:06 PST

## Immediate M (owned QC-PLAN-R)
Use existing `g/pre_m_v4/apply_g.py --without-sc`. Qualified non-SC subset output `g/pre_m_v3/subset_no_sc.json` SHA `6c2a2c1d218d`: +33 summed lane cycles /19 lanes. Original +31/17 missed input st_wi on sle_fe_v2; imported per_bit FE rows also lacked leaf_um. Both fixed. Model subset_lane_model.json: +15,791 FFbits at actual die replicas, throughput1 payload+epoch/cycle, memory-port delta0. Actual kit_istations + actual ot_dp_st fullwidth lockstep PASS (4 classes,2987 edges each, all missing-stage mutants detected).

## N (SC successor after M, parent owns compose/bind)
All paths E2 `/srv/opentallas-scratch2/claude/qc-plan-r/g` unless stated.
- Current reusable FULL composer: `pre_m_v7/apply_g.py` with rows_fe.json sibling.
- Strict geometry seed: `pre_m_v2/zz_s29_qc103_s4q9m_g.json` SHA955ddcc5787e. Allocator completed exit0; no process was killed when the attempted stop found it already finished. All9 SC actual-cell halos >=8.652um; actual paired-bit worst <=367.987um, macro-free routes except explicit existing M7 over-core forms.
- Full provisional N on L2d: `pre_m_v7/provisional_n_on_l2d.json` SHA7b57a014124f. Report `.apply_g_report.json`:590 reset localizations,0 dropped, all joint dryruns PASS; reset final hops136–178um (exact2 W street types136um), same release depth and same START role. Newly added FT consumer fragments come from the actual Binder.emit_type ot_dp_st form; final actual N bind still required.
- Provisional preview used explicit --reset-seed and authored helper-dir. For final N on ACTUAL M omit --reset-seed so reset_tree.for_type derives current graphs; use actual M bound RTL with --rtl. Preserve --ft-seed: it checks outline/bus/macro/interface identity plus each bit-cell halo/hop/core-route. No new allocator needed unless physical geometry differs.
- N relative qualified M Gsubset: +90 summed lane cycles across78 lanes, +41,442 FFbits whole die replicas (+30,813 one of each SC type). Reset rewiring0 cycles. `pre_m_v7/SC_N_model.json`. Full G relative L2d123/97. Refresh final model from actual M/N bound LATCHECK.
- Review LOOKED: `results/geom_review/qc_sc_n_1116/QC_SC_N_review.png`, `review.json`: PASS-COND geometry; critical x_fw_fe_p2 goes below u_core, x_fe_stm_p1 around top/side halo; no outline/interface change. Clock/PDN not shown. No P&R launched. Exact2 holds remain until GEN street/hop + actual placement relay/pin halos + GRT0.

Example final composition (through ot-run, declare all input stages):
python3 -I pre_m_v7/apply_g.py ACTUAL_M_PLAN N_PLAN --tree ACTUAL_TOOL_TREE --rtl M_BIND/rtl --ft-seed pre_m_v2/zz_s29_qc103_s4q9m_g.json
Then kp_inject.py make FINAL_N_PLAN BASE_MANIFEST true; run normal guarded CM/KP injection/bind, latency/R8/G0/LATCHECK. KP check on bind log must exclude prior appended KP CHECK lines (they self-match KIT_ISTATION_LATENCY).

## Authored helper, adoption N only
`claude/qc-reset-syncroot-1116 @bd0dc4f939865c3aa87a17dc01fe368a890cf2c7`, existing E2 `/srv/opentallas-scratch2/claude/qc-pinaccess-o/r2`, clean. Physical worker released clone; original physical branch0fa20f991c6 preserved.
- Exact declared sync-entry root support in reset_consumers.py: sync_stages2 and actual canonical same-clock ot_dp_rsync_s2 u_rst_root, exact ports/source/output and unique driver. Declared START root checked similarly. Same-depth/role/lineage remain; normal relayed-root behavior retained.
- Focused41 PASS. Actual production SC root slw_sc_v1__cl63e5a7a2:86-tap graph,83 mission targets equal2979 cycles, missing-stage mutant361 detections; root clock/module/entry mutants rejected. Actual tree + PASS committed in results/rtl/qc_reset_sync_root_1116.
- NORMAL GREEN4/4 main419279e2843. Intel2 client1020263 completed; log ~/qc-plan-g-codex-logs/gate_reset_syncroot.log; gate record ~/merge-queue/gates/bd0dc4f939865c3aa87a17dc01fe368a890cf2c7.json. READY posted via QC-PLAN-G. Root approves/merge queue merges; does not block M.
- Packaging delta `g/reset_syncroot_authored.patch` SHAd6a00b953043, old helper2c1aaaf08cf2 -> new163ad8cc2f46. One production file, engineRTL0. Parent owns N stage; no M stage mutation.

## Diagnosed failures kept
- Original G0 baseline/G failed same unresolved SU relative pin table. Use actual in-tree plan context. Old G0r processes were retained; no new wide sweep launched.
- Original reset rows vacuous empty PASS: stale published relay numbering vs actual emitted graph. Fixed by authoritative reset_tree.for_type/rtl_lines and new FT consumers.
- New targets must have same START role: raw/bootstrap tap126 emits rr_t126, not mission rst_n_t126. Role filter fixes failed lineage.
- SC root uses sync cell, not u_rst_in relay: authored helper above closes class; v6 failure kept.
- V5 own superseded process2232760 stopped only after exact cmdline check; STOPPED_INVALID_1116.json records role-filter defect. V2 finished normally.
- Station fixture failures (filename contract then missing leaf_um) retained; successful r3 proves actual emitter.

No current wave/holds/source tuple edited by this worker. No owner questions. No live worker jobs remain from G at this checkpoint.
