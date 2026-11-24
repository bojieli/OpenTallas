# QC-ALLFIX handoff (integrator + family, die QC)
Brief: scratchpad allfix_brief.txt (+ITERATION LOOP). Base C4 81fd3e6370c0. Table lanes/ALLFIX-QC.tsv.
Work dir: epyc8 /srv/opentallas-scratch2/claude/QC-ALLFIX (OT_LANE=QC-ALLFIX). rt 70b6f0430ea9.
- compose A plan = b25b1cf7c404 + cbn_q00 tapoff fill = cA/rows/plan_b25_tapoff.json f418c1b290f3 (census PASS).
- cA/tree = ot-tree-fork of kw45/snap_qwen_compute/qwen_compute_v4c4 (C4).
- Helpers: QC-ALLFIX-SU (su_c re-floor, SU-2, RED+2, rc103, RHI su_l1), QC-ALLFIX-COLL (coll_core reset clock-open, coll rows, SLE CTL B_TW + clock entry).
- QC-V4 keeps RSN FLT (tools bug, kit regen on c84f) + seal/apply. Adopted from QC-V4: b25 strict, RED+2, F16 (f16_physical_1536 + combined_abi_1554: PRE FIXEDCYC lane glue__f16_auth_f16_auth missing latency row), SU-C next form, rc97 narrow parent.

## 18:35 PST state
- A f418c1b290f3: PRE PASS, strict 0, LAT 1921/1921 (cA/bind). G0 running (cA/g0.ot, g0.sh). Render viewed: epyc8 QC-ALLFIX/render/qc_allfix_A.png + streets.png (render_run.py + pylib matplotlib).
- A probes (goal grt, rt 70b6, OT_TAP_ESCAPE_CLEAR_UM=0.30) via intel2 /srv/opentallas-scratch2/claude/QC-ALLFIX-probe.sh: cbf_q11 cbn_q00__cl622f65d2 cbx_q10 x3 sle_ctl__cla4f6f12f slw_fe_v2__clf110fab2 sle_st_a_v1__cl989804f6__cled3c1d7b slw_st_a_v2__cl9f076a5c slw_su_l1__cla2a78701 slw_hc0__cl1bc59e1c phy_serdes_b. Specs hub autopilot/private_specs/QC-ALLFIX/.
- B1 99ab093a8b8f (A+F16+TTC-NECK-1) on epyc8 cB: standalone PRE only ROWS-NO-PROOF (inherited). Bind died R8_UNCOVERED f16_auth -> r8fix.sh (r8_refresh, +1 member) -> rebind cB/bindB1c.ot.
- B2 9ecb9b695705 = B1 + rst_row (cbf_q00) + ctlclk_row (14 hc) + SU2R merge3 (db537389cc92) + RED2 overlay (ov_red2) + fixed R8 (ov_r8) on epyc7 cC via bindB3.sh (waiter b4imdww41 launches after forkC).
- rc97: COORD reopened; HCST-R3 re-hardens sta_region_nb0 at BT_LAT=2 (ETA 23:30-02:00), I do parent row (param_wrap BT_LAT 2 on 20 region cores + btab s4r) for compose C.
- COLL helper next: TTCTLM late-cone setup row, 6 in-core stations cbn_q00__cld7bf7197, coll_core probe on rt with 32027184aff.
- SU helper: SUC-Q0 stage-0 legs row for C.

## 11-24 08:35 PST state (fresh lane after 11-24 limit)
- C1i 3e46ebd69a97 PASS (E9 cI, unit 3859502): 0 bind err, LATCHECK 1922/1922, G0 PASS, render+streets viewed (cI/g0_review_0632).
- C1i kits (28 + glue probe-through) on E9: intel2 /srv/opentallas-scratch2/claude/QC-ALLFIX-c1i/launch_c1i.sh, lists grt.txt route.txt grt_coord.txt pt.txt, logs launch_*.log. Set = C1i-changed not in C1j + dead C1h kits not in C1j. Not launched: phy_serdes/phy_serdes_b/phy_ucie_kv (repeat gen FAIL).
- C1h relaunch of 3 C1j-touched place NOT-RUN kits: intel2 QC-ALLFIX-c1h/relaunch_*.log.
- COORD re-own of 7 QC-V4 holds: slw_fe_v2__clf110fab2 released (kit_wave 1f26cfdb); other 6 held (owner QC-ALLFIX), release on a C1i probe CTS >= -42.
- C1j 7fbc73d3f7cf intel1 cJ unit 17244: PRE ROWS-NO-PROOF only -> elab + strict bind running. On PASS: native59 exact C1j pair next; native59 held until then.
- Type diff tool: intel1 QC-ALLFIX/tmp/typediff.py (C1j vs C1i = 33 types + clock/reset/latency).
C1j-deferred: cbf_q00__cl1b5a6458 cbf_q00__cl870de686 cbn_q00__cl622f65d2 cbn_q00__cld7bf7197 cbn_q00__cldbcda913 cbn_q01__clab6e67f2 cbn_q01__cld9ff4c40 cbn_q01__cldd6ea846 cbn_q11__cl49ae4555 cbn_q11__cl5cc92dfe cbx_q10__cl89936551 cbx_q10__cl89936551_h cbx_q10__cl94a12200_h coll_core coll_ftn sle_ctl__cla4f6f12f sle_sc_v1__cl115da35f sle_sc_v1__cl7479a5ec sle_sc_v3 sle_st_a_v2__pv30dda31f__pvd2ec7769 sle_st_a_v2__pv4242de79 sle_su_c sle_su_l1__clc6d66f5b slw_sc_v1__cl63e5a7a2 slw_sc_v1__cl64543eaf__cl4590432d slw_sc_v1__cl64543eaf__cl5e017c6f slw_su_l1__cla2a78701
C1j kits pin rt c66a01ee7285 (the C1j bind rt) until FLOW-OPS-R3 toolskew fix lands (QC-GEOM-UNITS warning 11-24).
STATE-1500: C1j PASS 11:48 (intel1 cJ); C1k PASS 14:29 (epyc7 cK, rt 1145a6e17e79), TIED-BITS 0 both. From C1j: tt_ctlm grt probe, slw_su_c x2 + sle_su_l0 + slw_su_l0 x2 route, native59 geom (controller reattached 14:50). From C1k: 14 non-cb deferred types route. The 13 cb C1k kits were stopped at kit_rtl 14:5x (COORD: no piecemeal cb). Child lanes: QC-COLLS-LEC (lec.py nearest-pair fix, H2 proof ~15:30), QC-HC3-LEC (hc3 R8 51 differ), QC-CB-C1L (C1l = C1k + PIPESEAT + TAPBINS + COREPHASE + QC cbc_pass, cb pilot then family), QC-STSLW-ROUTE (SETUP_TRIAGE drv class x4).
