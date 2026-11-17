# QC-CLK-R2 handoff (Opus successor of FABLE-DIE-QC-R; QC die clock, event S4q9m). Started 2026-11-16 18:3x PST.
Work dir epyc2 /srv/opentallas-scratch3/claude/fable-die-qc-r (same as FABLE-DIE-QC-R; my files under qcclk2/). Client logs intel2 ~/qc-clk-r2/.

## s4q9m_r die chain (plan S4q9c dd47490db390, comb feed bc93daa9ab2d, OT_CLK_DME_TEMPLATE=2, exact-length clock SPEF LE 15)
- KIT 0: template 198 regions copied, 0 refused (form 1: 17), 42 embedded.
- REG_GRT TT/FF EXIT 0, overflow 0 / 0 / 0. DETOUR 0 (69,791 2-pin clock nets, guide-placed p99 +13 %, max 19.7 %).
- SPEF 127,020 nets, TTA 42,256 taps missing 0 both corners.
- TOL same-type half range: GRT readout max 74.6 (p90 33.9, >10: 2,449); SPEF readout max 36.2 (p90 0.3, p99 4.0, >10: 54, >20: 4);
  all cb types <= 0.3; residual only H-tree regions slw_sc_v2 36.2, sle_fe_v2 18.4, sle_sc_v2 17.5, sle_fe_v1 16.3, sle_sc_v1 10.1.
- REG_STA (plain): intra need 200.8, seam need 147.87. LPO/CA/BIND/STA_C still running (CHAIN.log).

## Rows (COORD lever 6 / FABLE-PD-QC-MCLK lever 1: from SPEF proof only, never GRT)
- qcclk2/rows_r/{rows.json c4c4fcd39cf2 (all 130 types), plan.json bb5f3822bb1a (S4q9c + rows), report.json, cb_rows.json 5eb16cc73797}
  via bin/rows_m.py MARGIN 10: tol = ceil0.1(SPEF half range + 0.05 + 10), tol max 46.3, tap_window = kitwin + 10, seam_ps 110 -> 160
  (ceil10(147.87 + 10)), tap_offset/window table errors 0.
- cb rows (18 types / 192 partitions) copied to hub lanes/handoff/QC-CLK-R2-cb-rows-s4q9m_r.json: tol max 10.1 (cbx_q10_h 10.2) on
  every cb type; check 2 x tol <= 40 PASS on all 18 (was L2 median 48..81, max 139.1).
- Offsets are per-partition-relative (minus the partition median glue tap); cb geometry is unchanged in l2d, so the cb rows compose onto l2d.
- No +1 K row anywhere (serdes K comes from the CA planner).

## Next
1. CHAIN_DONE s4q9m_r: CA_C/D FAIL 0, serdes io_serdes_2 -> c_W5_bf_01 __0 ports (3) margin, STA_C COUNT-ALIGN TT+FF.
2. l2d chain (chain/qc/s4q9m_l2d, unit oth-ubuntu-4106679-1794887119; Codex finalizer pid 4170674 runs rows_m on it after): full-type rows on l2d.
3. S4q9m compose = l2d + rows + region_form sta (K/DEPTH/sched_lat on the built clock; rehearsal qcclk2/reh) -> G0, bind, LATCHECK.

## 20:5x PST
- s4q9m_r CHAIN_DONE: CA_C/D 2,993 FAIL 0 (depth 4: 2,953 / 8: 40, MC 300 0 viol, START 724/724 clean); STA_C COUNT-ALIGN PASS TT lo 105.0 / FF lo 110.3;
  intra TT setup +403.1 neg 0. Serdes io_serdes_2 -> c_W5_bf_01 (3 ports __0) K 4 depth 4 lo 711.3 (was -107.1).
- New rows check (qcclk2/chk.sh): die_sta_related on reg/proof with rows_r/plan.json: TAP-OFFSET-GATE PASS 0 / 84,512; FF kit-contract hold +10.00 (W 70, need 60, neg 0).
- Tool: claude/qc-clk-r2-capin-1116 @060ba63e937 region_form sta --cap-in (built-clock ca_C instead of the fwd-model hull), GREEN 3/3, READY posted.
  Without it the l2d rehearsal (qcclk2/reh) failed 91/2,434 crossings spuriously (model hull widened up to 5,666 ps).
- --cap-in rehearsal on l2d (qcclk2/reh2, s4q9m_r ca_C): 2,525 crossings FAIL 0, K changed 1,219, sched cycles 6,766 -> 6,352,
  lanes changed 936, BUT POST-CHECK FAIL: 23 lanes latency.lanes.*.clock_landing < 0 (c_E*_bn_11__b12 / tn_11__b12: -1/-2).
  Cause: the count frame stays the fwd feed wall-aligned f_v while the comb clock lands regions whole cycles earlier;
  the frame no longer describes the built clock. Fix = re-frame: plan clock.spine.feed = comb feed doc whose frame_offset =
  round(built leaf TT arrival / T) per region (+ sidecar frame), CA re-run with --frame-plan, then sta --cap-in. Not built yet.
- Opus self-review (no BLOCK): absolute SPEF offsets are calibrated to the GRT mean (LE 12 -> 16 moves cb clk_c offsets 22.6 ps median);
  next proof = DRT + RCX of one cb region vs SPEF offsets; 4 single-instance cb types carry no same-type evidence.

## CODEX resumed 22:18 PST
- Exact l2d measured clock rows generated qcclk2/reframe_l2d/clock_rows.json: 130 types / 15386 ports, tol max46.3, minmargin10.05, tap-offset/window table errors0, seam160 (need147.87).
- New comb frame: qcclk2/reframe_l2d/feed_comb_built_tt.json sha dbdd8008624a49a8. Frame offsets=round(TT median non-core glue leaf late_ps /833), ranges1..13 (old fwd1..19), all313regions/377parts covered. mk_frame.py preserves physical K while changing sched_lat/plan cycles/sidecar added_cycles by new-old frame shift.
- Reframe pipeline CA --frame-plan then region_form sta --cap-in running from intel2 client373347 log ~/qc-clk-r2/reframe_l2d_retry1.client.log. E2 qcclk2/reframe_l2d/run2.sh, outputs ca_framed.json, plan_m_clock.json, side_m_clock.json, READY.json. Explicit check no negative clock_landing and no region_form post errors.
- First attempt stopped before CA due python -I sibling import; failure ca.log and reframe_l2d.client.log retained. Retry uses explicit sibling-path bootstrap run_cap.py (no production source modification).
- Parent composes G/w515 then ONE final strict bind/LATCHECK/G0; do not duplicate final bind here. cap-in dependency remains claude/qc-clk-r2-capin-1116 @060ba63e937.

## CODEX M clock READY 2026-11-16 22:38 PST
- E2 qcclk2/reframe_l2d/READY.json; plan_m_clock.json sha02a32c37bb605af6153ba3e01a8c50d57d27b3bd86dae108dc8c22e315cbeda9, side_m_clock.json sha1b43f2b63bfb466661e36ed2a812c3470c94e798f532d2323bf4f40f225b69a0.
- Comb feed sha dbdd8008624a49a8b955b673d5edae6a4427d566d9289eaa73ac82659ce17353; copy exact bytes to treeJ plan_of_record/feed_s4q9m.json, use relative path in final plan (hash unchanged); restore region_map path plan_of_record/regions_s29.json with original hash. Full instructions RELOCATION.txt.
- CA --frame-plan: 2993 FAIL0, frame_min_lat1, START724/724clean, margin105.1/112.5. region_form --cap-in:2525FAIL0, post_check[], negativeclock_landing0. K changes1219; crossing cycles7002->6588 on reframed basis,879lanechanges (changed-lane sums11093->10912),30straps narrowed7->6. Physical frame relabel adds0cycles; subsequent physical K changes priced in report.
- Exact l2d clock rows130types/15386ports, minmargin10.05, tolmax46.3, tables0errors, seam160. Prior old-row TAP-OFFSET FAIL is historical; replacement rows are generated directly from exact TT/FF SPEF proof.
- Parent composes G/w515 then ONE final bind/LATCHECK/G0. Proposed clock plan is ready; no signed real-view die claim.
- Diagnosed/fixed leftover auto-finalizer: counted gate STA omits plain seam kit_contract_window_needed_ps field; stopped helper now uses REG_STA. Failed script preserved as bin/finalize_l2d_rows_gate_summary_failed.sh and chain_l2d_finalize.log; corrected rows already generated, no duplicate job.
- CB release qualification detail: M cbn_q01__clab6e67f2 offset/window rows equal old pilot cb_rows5eb16 exactly, BUT native type count_straps change a00_i/nb_i12 widths7->6. Across13instances/130relevant landed rows:34Kchanges,10depth8->4 (W0/W1/W2/W4 bn11 a00/b12 +W5tn11 a00/b12). Old L2 physical pilot is not automatically byte-equivalent relevant source; use final M dryGEN/source/budget/SDC comparison, likely M-specific cb pilot before cb-ready. Detail lanes/handoff/QC-CLK-R2-cbn-M-contract-delta.json; dieclk worker+parent notified.

## M2 D8 correction (22:5x CODEX, parent-authorized)
- M1 READY02a32 is clock-ready but NOT bind-ready: read-only source diagnosis found3real hard-child DEPTH mismatches (cbn_q00__cldbcda913 na_i00/nb_i00/rsf_i emitsD4 while actual signedparamsD8). Original M1 source/report/READY preserved.
- Corrected M2 clock plan E2 qcclk2/reframe_l2d/plan_m_clock_D8.json SHA0bd918f6be3ee17ee98a2a07b83ff9d2519eddba51b3176c8e7601f289ed7fd7; side_m_clock_D8.json SHA846056c27104994dc72dab8f242224d0da8d49f8448340a5280c687c0e664fa2; samefeeddbdd8008624a.
- Mechanism: preserve actual signedD8 in exactly3busfamilies/30links over10copies; K/physical lag/schedlat unchanged because count_align_plan computes them before choosing the minimum fitting depth. D8 window strictly contains D4, upper margin grows3332ps. Regenerated via approved region_form cap-in; all172hardring depth contracts match, postcheck[], negativeclock_landing0, lane table byte-equalM1, +0cycles. No RTL/toolchange or newD4view.
- Direct minimal actual TT/FF check PASS:30links/173240actualtap-pairs percorner on exact l2d SPEF proof, nominal singlearrivals+CPPR-LCA (same gate), guard104.125ps. TT min margins716.457/3986.066; FF858.858/3952.181. E2unit2283023-1794898150 exit0. Receipts lanes/handoff/QC-CLK-R2-M2-D8-{reconciliation,physical-corners}.json.
- Parent may apply exact M1->M2 depth/strap delta onto finished G output without rerunning G geometry, then ONE final bind. cbn_q01 pilot remains real softD4 and still requires relevant final-M source/SDC comparison.

## M3 schema metadata correction (parent G composition caught it)
- Existing schema rejects my descriptive plan feed.form comb_built_tt (only fwd allowed). This was inherited into the reframed base, so region_form no-new-errors postcheck did not catch it; preserve M1/M2 and failed final_1116 latencygen evidence.
- Source readers confirm form tag is metadata for the forwarded regional protocol: die_trial link_htree uses explicit root/parent/tap/joined; count_frame uses frame/frame_offset/hash; region_form sta dispatches topology. Thus ONLY plan clock.spine.feed.form -> fwd is correct; keep actual measured comb feed bytes/hash/frame unchanged, no schema waiver/newtool.
- M3 clock plan E2 qcclk2/reframe_l2d/plan_m_clock_D8_fwd.json SHA12f2493f9a4298bb36af52d35a795dd19f66edd3c934c2374fde33c60106818b. Side846056/feeddbdd unchanged. Full schema validate0 errors; complete count-frame identity+offsets identical;0 latency/physical change.
- Parent applies single field to completed G geometry, preserving prior outcomes; no CA or geometry replay needed. Receipt lanes/handoff/QC-CLK-R2-M3-form-fix.json.
- Future stopped mk_frame helper now emits plan tag fwd (old failing helper retained mk_frame_combtag_failed.py); no replay.
