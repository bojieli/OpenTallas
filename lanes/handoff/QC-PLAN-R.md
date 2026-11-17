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

## S4q9m: child QC-PLAN-M composing on l2 (comb feed + CA re-plan check + (d) 72-pin window). Template form (2bed6a4) not adopted: cb tol 129->104 only.
## io_serdes_2 -> c_W5_bf_01: CONFIRMED. dec8cc442a in main; gate_main (before) CA TT/FF fail 3 (-107.1/-67.0), gate_main3 (after) fail 0 (lo 109.9/105.1), 2993 PASS. No +1K plan row: fixed planner picks it in C; native N43 maps both same-region (delta 0).
