# GEOM-VIS-9 lane handoff (2026-11-12 16:06 PST; lane LIVE, 11 of ~35 images used)

1 SCOPE: the visual gate, as in GEOM-VIS-8.md. Requests to GEOM-VIS-5..9 and VISUAL-QUEUE.tsv rows belong to the live lane.
2 TOOLS (Claude localhost scratchpad S=/tmp/claude-1000/-home-ubuntu-OpenTallas/c228d9e1-f423-4eaf-829b-3bad2a9c2331/scratchpad): v9/post.sh geom.md queue.md "msg" (appends to both and runs coord-commit; tag GEOM-VIS-9). v9/mon.sh S runs the Monitor loop: new REVIEW REQUEST / GEOM REQ / GEOM-VIS-8/9 lines (seen list v9/seen_req.txt, own posts excluded), plus the epyc4 GRT state of the two st_a firm-stop routes and the wrx_wreg proof. v9/conghist.py histograms a GRT congestion-N.rpt. The Monitor expires every 30 min, so re-arm it.
3 POSTED (GEOM-REVIEW.md, "GEOM-VIS-9 viewed"):
  - 15:06 s81_head hd_spn_wshim_rx wrx_wreg proof GRT: NO CHANGE vs the main build. The W hot column is the fan-in of the dense W pin bar (566 pins in y 709-1008 um, 0.53 um pitch). COORD 15:07 took it to HEAD-95 rp18 (spread the W/E link bars).
  - 15:1x st_a firm GRT stop, numbers: sle_st_a_v2 a2 and slw_st_a_v2__cl9f076a5c a1 both GRT0 with 0 overflow at iteration 8/30 (use 11.9%). The stop is not triggered on numbers. The render is still pending: the 5_1 post-GRT repair is running at 00:06 UTC, and layout_review/grt is not written yet.
  - 16:1x HBM VISUAL-QUEUE rows: NE_iorly a1, NW_iorly a1 and PHY_NC a4 are all BAD, WAIT-FORM, form changes named. CLASS BUG reported to KW-FIX-46: these are the SAME builds the old BAD verdicts rated, because 3_place.odb predates the verdicts. The binding takes the build time from geom/launch, not from the place odb. Also check s81 ot_s81sl_leaf__t38 a6.
  - 16:2x S81 dsdv_gunit_l1f_bf kit_gf3ds60: ISSUES-ACCEPT (watch DRT in the old window, slew on the E-face paths). S81 dsdv_bksel_q vC6c: GOOD (GRT stop if the P-east channel x 337-413 um, y 177-422 runs above 0.9).
4 OPEN / WATCH:
  - The st_a GRT render (ot-jobs/<type>-route-aware-parakeet-*/work/run/layout_review/grt) needs a confirming view of the E-face column.
  - Place renders not yet seen: KV vN2e/vN2f hg/hgi, QC s28, S81 ready12b.
  - Carried: lep0N v3, hd_spn_end SP3n2, hd_mesh m1, VL3 lepw_mu_C t1 (S pin bar > 0.9 = stop), q_su10 row street, bksel vC6c GRT.
  - Owed: a summary to COORD at lane stop.
