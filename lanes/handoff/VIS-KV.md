# VIS-KV handoff (Opus, started 11-22 22:49 PST; brief scratchpad visual_brief.txt)
Goal: look at KV placed DBs, find the NEXT plan layer before D29 (rows to KV-PLAN-R6 by 01:45 11-23), fix structurally per family.
Local work dir (rtx-pro): /tmp/claude-1000/-home-ubuntu-OpenTallas/c228d9e1-f423-4eaf-829b-3bad2a9c2331/scratchpad/viskv (PNGs, auto_geom json, placed_scan tsv; vk_scan.py summarizer one dir up).
Kits looked at (auto_geom.png + placed_scan.tsv): D28 pc_v3 (intel1), D28+D27d3 hroot (intel1), D28 sys_c (intel1), D28 hgi_v4 (epyc2), hgi_v5 (intel1), hgi_v2__cle (epyc7), pv_v6n private K2 (epyc8 SINKSPREAD).
23:0x: 5 read-only sub-agents dispatched (hgi/hg, pc_v3, hroot east strip DRC, sys_c A1/A2 TT -369, pv_v6n). Waiting for their row specs.
## 23:4x 11-22: scope = all 48 KV types (visual_brief2.txt, LOOK-BEFORE-LAUNCH). VIS-COVERAGE KV rows filled (0c9c9fecef), all DRAFT.
Local files: viskv/all/<type>.{auto_geom.png,json,placed_scan.tsv}; inv_best.tsv (render host:path); cov_final.tsv (rows); cov_apply.py (updater, run on intel2).
Rows handed (owner agent ids): hroot BAND 43a1ac7be69f D29 (FAM-KV-HROOT-R1 ac3aaa15ea4376099, gates on intel1 fork_d28b);
 hgi ECTLPDALL 3cdfb7c858a6 + ECTLH3ALL 425cad93671b D29, HST2SITE D30, hg form D30 (OPUS-FIX-KV-HG-R8 adefa9043e50c771d; hgi_v5 probe after bind ~00:10);
 pc R1 no-growth + 3 R2 stations probe epyc9 (FAM-KV-IOPC-R4 a85bc67efb8bad06b), R3/R4 D30; VIS-KV OWES outline-growth variant (E-side translation) D30;
 pv A/B/C + family form D30 row B (SINKSPREAD-R2 af04044a2625ea60f), pad FIFO -> KV-PLAN-R6;
 sys_c R-DOB/R-RST (D29 if bind-clean) / R-DCAL-RT D30 (FAM-KV-HUBC-SYSC-R2 acfac8231202b7f41).
COORD speed: answer probe renders <=30 min else owner self-marks PROBE-PASS; never hold probe kits. KV-PLAN-R6 (a5df7e7d283adf549) holds only previously-failed types.
TODO: D28 die render epyc8 /srv/opentallas-scratch2/claude/vis-kv/tmp/die/d28_die.png (render.log); render+read composed D29 plan before 06:00 apply.
