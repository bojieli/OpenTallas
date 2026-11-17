# QC-PLAN-R handoff (successor of FABLE-FIX-QC-KNEE-HC + FABLE-DIE-QC; owns QC plan events + die). Started 2026-11-16 17:1x PST.

## S4q9kf publication (plan a826abb3a3fd, stage E2 /srv/opentallas-scratch2/claude/tools-converge/qc/jkf_closure_1116/stage)
- DONE: 11 missing bind/*.py siblings copied from treeJ (all 12 now byte-equal, cmp). 4 runtime assets present (sha c71a3feb / 38336cfa / 60098047 / 46a62e7f).
- DONE KPmake: sibling plan_of_record/zz_s29_qc103_s4q9kf.kit_pricing.json (a4b65fb11f2d) bound to portable manifest 65000b87450a; inject byte-idempotent; check 0 KIT_ISTATION_LATENCY. Receipt ../kp_revalidation/KP_PASS.json.
  Note: kp_inject check on a bind log self-matches the appended "KP CHECK 0" line; check the log minus those lines.
- CM helper committed claude/tools-converge-cm-revalidate-1116 @77fd955f2ac (E2 lanes/holdgen-1115), GREEN 2/2, READY posted.
- Producer claude/qc-pinaccess-o-1116 @7af064b5ed0 (adfd + fixture fix test_kit_wave_nohub roam=True), GREEN 200/200, READY posted. Clone E2 /srv/opentallas-scratch2/claude/qc-pinaccess-o/r2.
- NEXT: after both merge -> normal src_manifest/data_pack publication of the stage on gen hosts, current tree guard, candidate JSON + apply_reviewed_tree_marker_1116.py (format: lanes/handoff/HG1A_PGR1_D3_ADOPT_candidate_1116.json).

## S4q9l2 (replaces L; COORD 17:2x: one bind of L + need+10 rows + tail1 param rows)
- Plan treeJ plan_of_record/zz_s29_qc103_s4q9l2.json sha 19be3f0a3bb42d8e = L 50d472e1a81f + tol = ceil(half range+0.05+10) on 15,391 ports (max 139.1), offsets unchanged, tap gate PASS 0/84,512 + 24 tail1 param_wrap rows (6 st_a_v1 types u_r0..3) + source text mid-range. Composer/report E2 /srv/opentallas-scratch2/claude/qc-plan-r/l2/.
- Bind RUNNING: E2 bin/chain_s4q9l2.sh, tag s29q103S4Q9L2BQ, client intel2 ~/fable-fix-qc-knee-hc/chain_s4q9l2.client.log (started 17:22). Fable review FABLE-PD-QC-S4q9l2 running in parallel.
- Adopt after Kf adopts: bind errors 0, r8rc 0, LATCHECK PASS, hcparam 0, G0 = 2 inherited faces rows, no Fable BLOCK.

## S4q9m: COORD 17:4x scope: FABLE-DIE-QC-R owns die clock design (feed, per-type trees, need+10, serdes proof) and hands rows; QC-PLAN-R composes + binds S4q9m. Child QC-PLAN-M narrowed to item (d) only (72-pin window sl_W5_fw.W / coll_f4.E) -> zz_s29_qc103_s4q9l2d.json. Template form (2bed6a4) not adopted: cb tol 129->104 only.
## io_serdes_2 -> c_W5_bf_01: CONFIRMED. dec8cc442a in main; gate_main (before) CA TT/FF fail 3 (-107.1/-67.0), gate_main3 (after) fail 0 (lo 109.9/105.1), 2993 PASS. No +1K plan row: fixed planner picks it in C; native N43 maps both same-region (delta 0).

## 19:2x PST
- S4q9l2 bind S4Q9L2BQ: errors 0, r8rc 0, LATCHECK 1921/1921, hcparam 0 (20 param_wrap types, 0 mismatches), G0 = 2 inherited faces only. Fable verdict pending. Adopt after Kf.
- CM helper + producer MERGED (cfe4802327f / fcd8d406457). Kf publication + atomic apply delegated to child QC-KF-PUB (running).
- (d) COMPOSED by QC-PLAN-M: zz_s29_qc103_s4q9l2d.json sha a915f1136c27 (coll_ftc +43.2 um, coll_ftn -43.2 um, 22 windows repacked): G0 0 errors, pre PASS, knee 0/988. Rebuild coll_ftc, coll_ftn, slw_fw_v3. Rows epyc2 /srv/opentallas-scratch2/claude/qc-plan-r/m/s4q9l2d.rows.json, image d_before_after.png. S4q9m = l2d + FABLE-DIE-QC-R clock rows (feed tap coll_f4->coll_f5 y 12217.0 -> 12260.16; coll_ftc/ftn tap rows re-derive).

## CODEX parked on Claude return 2026-11-16 19:5x PST
- Kf E7/E8 published DONE, manifest c8e63f164faa. Both portable KFBQ contexts DONE native-contract equal, bind_matches130/130; E7 relocation unit1844237 exit0, E8 relocation395155 exit0. Source guard full_ok both hosts result0a5b2330460e6404d611c74890fa233ab77b7a574478c5ed313d19bd1f7d5924.
- Candidate lanes/handoff/QC_S4Q9KF_ADOPT_candidate_1116.json committed7b10da4, READY post29f962f. NOT APPLIED. Event proposed s29q103S4Q9KF, hosts E7/E8, pilot should sle_fe_v1__cl1cbb7497 (release-on-Kf FE type); root tuple approved pending inherited hold leak repair.
- Hold leak coverage committed7e7381c: lanes/handoff/QC_KF_hold_coverage_1116.json lists all52 clock types and27 with NO existing hold. Proposed materialization: inherited r344 clock52 release event_adopt:S4q9l2; face slw_fw_v3/coll_ftc release event_adopt:S4q9m (l2d geometry); six st_a_v1 already covered. Root must rule/materialize inherited findings before pilot release. Existing holds unchanged by QC.
- HOLDGEN is preparing mig007 split: fw11 keep old S4q6d terms; exact-equal st_b11 retype Kf at apply. su_c3 differ internal_stations, NOT equality-qualified. No blanket successor inference.
- L2 pack running via child qc_l2_pack (canonical intel2 clients2111615 E8 publish /2111617 E2 raw staging; ~/qc-plan-r-l2-logs). Compiled raw KFBQ/L2BQ asbuilt.json ec5fb2617e74 and sourcesed45aca575c3 identical. Portable65000b reused; minimal delta plan19be3f0a3bb4+cland bins+KP. See its final handoff. No L2 apply.
- QC clock baseline m_r kit DONE template198copied/0refused/42embedded; TT/FF proofs running. Exact l2d clock proof admitted E2 unit4106679-1794887119; finalizer4170674 waits bash4106745 then generates need+10 proposed rows, no adoption. Child qc_clock maintained FABLE-DIE-QC-R handoff.
- QC physical child: headseg44 hf SIGNED TT+133.23 DRC0 internalFF0 and archived both+INDEX coord3fd3e9a. W0 route858 progressing; final_after_route.sh staged NOT launched. W1 floorplan-only admitted E2 qc-types-r/w1_hf_1116 unit4167269-1794887316, next LOOK actual image before route. coll_n logical-clean LEC4 admitted E2 unit4123742-1794887165; LEC3 DECAP failure preserved. P3m10 live retained. QC-TYPES-R handoff has details.
- Failure diagnoses: old cbx -1803/-1928 uses source missing r301 xcst fanout fix; fresh coherent source required. cbn_q01 cee3540cfd65 = cross-tap DLATCH_N hold (21431 endpoints); 36093 guard45 buffers no gain, oldCTS restored then450iterations timecap. r301 alone does NOT fix latch debt; L2 first proof must inspect forwarded-ring/latch endpoint before routing.
- Kf review render attempted E8 lacked matplotlib; local tools copy/read-only render preparation unfinished. No routes launched by QC plan takeover. Existing r344 review retained; do not claim new visual PASS from this attempt.
