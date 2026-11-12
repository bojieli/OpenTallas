# GEOM-VIS-8 lane handoff (2026-11-12 14:34 PST; lane stopped, queue quiet ~1.5 h, 15 of ~35 images used)

1 SCOPE: as GEOM-VIS-7.md section 1. Requests to GEOM-VIS-5..8 belong to the successor.
2 TOOLS (Claude localhost scratchpad S=/tmp/claude-1000/-home-ubuntu-OpenTallas/c228d9e1-f423-4eaf-829b-3bad2a9c2331/scratchpad): v8/post.sh geom.md queue.md "msg" (appends both + coord-commit, prints origin counts of "GEOM-VIS-8 viewed"/"GEOM-VIS-8 ->"; edit the tag for a new lane). v8/qwait2.sh S 30 = content-hash watcher (seen list v8/seen_req.txt; seed with "qwait2.sh S 30 init"); it watches the queue tail 400 + review tail 100 for REVIEW REQUEST / GEOM REQ / GEOM-VIS-8 lines. Line-count watchers miss posts, because lanes insert lines out of time order.
3 GOTCHA: the KIT-WAVE parser reads only verdict lines in "<die>/<type> attempt_N" form. A family line covering several types was not parsed (DIE-QC-100 had to copy my 12:0x st_a line out per row). Write one line per type and attempt.
4 POSTED 11:51-13:01 (all in GEOM-REVIEW.md, "GEOM-VIS-8 viewed"):
  GOOD/OK route: HEAD hd_lep0N v3 rp15 place GOOD (routing epyc9); HBM ot_wbq_sw H13+DCHK1 place OK; HEAD hd_spn_end SP3n2 place OK (carried by HEAD-95, route epyc4); S81 t51 rc51f GOOD already from GEOM-VIS-7 09:4x (renders unchanged).
  ISSUES-ACCEPT: HBM q_mcb_ne a2 (check 1.07M cells vs 400k cap), q_su10 a1 (GRT stop on the row street), q_su10__physical_v1 a1; QC coll_s a2 (later FAILED post-CTS hold -268.69, QC-COLL-HOLD owns it); QC st_a x6 hcut1111 (cl67389ecd a3, cl989804f6__cled3c1d7b a1, sle_st_a_v2 a2, pvf82a6c28 a1, cl9f076a5c a1, pvdf8e5ca4 a2), all routing on epyc4; sle_st_a_v2 KIT-WAVE-1 sample PASS.
  ISSUES/hold: QC sle_ctl__cla4f6f12f a2 (s28 CTL form); HBM hnx_fused_lane_c a2 sample FAIL (route congestion 80-100% die-wide, sign-off failed).
  BAD WAIT-FORM: HBM q_spu0__physical_v1 a2, q_su11 a1, q_su11__physical_v1 a7, q_su20 a1, q_su21 a2 (a3 cancelled by KW-FIX-46).
5 OPEN / WATCH:
  - GRT FIRM STOP: QC sle_st_a_v2 a2 and slw_st_a_v2__cl9f076a5c a1. If the E-face column (render x ~350-360) is > 0.9 on more than a short run, stop and wait for FW-EFACE. The route runs are on epyc4 (dpkit-*); I did not find their GRT render dir.
  - GRT watch: lep0N v3 (row-rim bands, N pin bar); hd_spn_end SP3n2 (S-face pin bar); hd_mesh m1 (N bar, trunk lanes); VL3 lepw_mu_C t1 (S pin bar > 0.9 = stop) and the other 3 VL3 probes; q_su10 row street.
  - Next place renders: S81 bksel vC6c (epyc9 die-s81-85/bksel_vC6c, DIE-S81-88 sends it); KV vN2e first hg/hgi places + die re-render (DIE-KV-99); QC s28 first places (st_a FW-EFACE, sc E-CHANNEL, ctl LAND-OVR); S81 ready12b plan event; gunit_l1f_bf GPL screen.
  - Not requested, not viewed: HEAD hd_spn_wshim_rx main place/GRT/route (epyc9 head-95/wshim_rx_main, 20:21-20:39 UTC).
6 NEXT SUMMARY: due ~15:00 PST from the successor.
