# S81-ALLFIX-INT handoff (Opus 5.5; started 11-23 16:28 PST). S81 INTEGRATOR, combined ALLFIX plan = AMENDMENT-1 widened.
Brief: localhost scratchpad allfix_brief.txt (+ ITERATION LOOP section) + resume_1123b.txt + rules.txt.
Base: B1 v3 3255f32bd901 / post-tail ae3101241d6b (E10 s81-j9-r6/b1_tree/physical/die_plan/s81/plan_j9_b1_exact_1123_ae3101241d6b.json). Rebase if ASSEMBLY posts a newer plan of record.
Table: lanes/ALLFIX-S81.tsv (67 ledger rows + 10 named extras). Family lanes: S81-ALLFIX-COL/SLICE/SVC/MULTI post ROW-REBASED to me.
Adopted from ASSEMBLY (do not relaunch): amd1_tree fork E10 unit oth-ubuntu-1615361 (s81-j9-r6/amd1_tree), RTL stage s81-j9-r6/amd1_rtl_6ca14d0fb59b; AMENDMENT-1 order (ASSEMBLY post 16:00).
Compose tools: E10 s81-j9-r6/compose/{compose.py,jlib.py,tail.sh}; gate template compose/b1/gate_mt.sh (point at amd1_tree + main rt >=70b6f0430ea9).
Exclusions: LF_VN_XRD=0; rc35lk 69a5599765ce fallback only.
Deadlines PST: rows 19:00; first combined PRE 19:30; PRE-clean 20:30; strict+LAT+G0 22:30; probes 23:00. Then OWNER iteration loop (I own it).
Note: E10 scratch2 99% full (136 GB free at 16:35).
## 16:35
- Posted TAKING, HANDOFF REQUEST to ASSEMBLY, SVC-CUT-FACE row request to ALLFIX-SVC (grow hi4 seam faces), LOOP OWNER ack.
## 16:45
- Lane dir E10 /srv/opentallas-scratch2/claude/s81-allfix-int (compose/{compose.py,jlib.py,tail.sh,gate_allfix.sh}).
- AMENDMENT tools+rtl sha = main 70b6f0430ea9 (= rt current; contains 52aebeb23d, GFLOCAL c72b212af81 [=26042b7e1b content], 17a29101a3, ab9599202a, 11c3801a01, 132f74ad81, ENG e68a1c8b0e0/df0b0ceac37/7438d9dffa3, 358d836ceea3). rt 70b6 bind.py has TYPE-DEFINES-1123 (per-type verilog_defines realized) -> GFLOCAL per-type defines OK.
- Overlay git archive -> s81-allfix-int/overlay_70b6f0430ea9 (unit oth-ubuntu-2395635). Apply with apply_overlay.py onto amd1_tree after ASSEMBLY's fork (oth-ubuntu-1615361) finishes, then ADV-TREE-DRIFT 0.
- gate_allfix.sh PLAN TAG [ASBUILT]: fresh strict ELAB (RTL changed), bind --strict --all-gaps (PRE refuse), LATCHECK as-bound, G0 total + compare vs B1 g0 (gate_b1_exact_1123/g0_j9).
- Family lanes all TAKING 16:29-16:30. ALLFIX-SVC adopted MISC comb_b1 rows. ENG XS-BIND reproof PASS (intel1 proof.json).
