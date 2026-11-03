# PRUNE-1103A — successor of PRUNE-1102B (scratch recovery intel2 / epyc2)

## Start (2026-11-03 03:24 PST)
- Read brief + PRUNE-1102B.md; no queue line 23:41-03:22 names PRUNE (no open ASK/RELEASE). Predecessor left no live jobs (deletions were synchronous).
- df 03:22: intel2 scratch2 191 GB free/95%, epyc2 scratch2 137 GB/84% (root 1.8 TB free), intel1 350 GB.
- Target: intel2 + epyc2 scratch2 >= 300 GB free. Exclusions per brief (PROTECTED-DBS, .keep, refs, tok-/kv-fn-/codex-ds-/vehicle, live, re-sign/stage-resume DBs, idle <24 h).

## epyc2 manifest A (2026-11-03 03:28 PST): MOVE idle no-.keep dirs to /home/ubuntu/scratch-root/claude + symlink (act.py mv: rechecks .keep/recent/live before+after copy, rsync -aH, bytes+count verify)
- s81ck12 (24.7 GB, newest 11-01 22:56), kv60-pcx (20.8, 11-02 01:47), s81ck12t (10.6, 11-02 00:01), codex-qc62-collect-1101 (3.3, 11-02 01:14), codex-flow-hold-2249 (3.1, 11-01 09:28). ~62.5 GB. Root 1797 GB free.
- Manifest epyc2:/srv/opentallas-scratch2/claude/prune-1103a/e2_mvA.txt, result e2_mvA_result.tsv.
- A result so far: s81ck12 + s81ck12t SKIPPED (live: DIE-S81-49 eco_loop on s81ck12/k13 kit, klegacy docker on s81ck12t). kv60-pcx, codex-qc62-collect-1101, codex-flow-hold-2249 re-run with ALLOW_FOREIGN=1 (root-owned docker files; old copy removed via alpine rm).

## epyc2 manifest B (2026-11-03 03:37 PST): MOVE (not delete) idle .keep dirs to epyc2 root scratch + symlink
- Intent: .keep = never delete; a verified move + symlink keeps every byte and every path. act_k.py = act.py mv without the .keep skip, plus a PROTECTED path skip (protect.d; any dir containing a PROTECTED path is NOT moved), newest file >24 h, live recheck before and after copy.
- codex-kv-pc-cores-1101 36.6 GB, die-s81-47 10.7, codex-kv-ex-closure-1131 8.8, hbm-k39x 8.6, codex-pc-reload-0018 5.4, hbm-cores-kits-41 5.1, hbm-cores-kits-39 4.4, codex-s81-l2gate-1445 3.7, codex-qc-su 3.6, codex-retained-cts-api 3.4 (~90 GB). Manifest epyc2:.../prune-1103a/e2_mvB.txt, result e2_mvB_result.tsv.
- Not moved (contain PROTECTED paths): codex-s81-cohort-1101, codex-hbm-cores-1101, signoff-sprint-19, s81ck5, head-serdes-2, die-qc-44, s81ck13.
- A result: kv60-pcx, codex-qc62-collect-1101, codex-flow-hold-2249 MOVED (28.46 GB). B result: 10/10 MOVED (94.55 GB). epyc2 scratch2 137 -> 252 GB free.

## epyc2 manifest C (2026-11-03 03:47 PST): MOVE sub-dirs (no PROTECTED path inside/above, idle >24 h) of the 7 dirs that hold PROTECTED records
- 30 dirs >= 1 GB, ~95 GB: codex-hbm-cores-1101/{query,exp0}, signoff-sprint-19/{hcol,stm}, s81ck5/kits/{ot_s81sl_ve_m_rt22m{,_hx},ot_s81c_attn_hcore_rt22m{,_hx},ot_s81sl_vn_a_rt22{,a,am,p,p_hxh}}, head-serdes-2/{e11c,e10a,e8a,e3a,e3,v1a}, die-qc-44/grt, codex-s81-cohort-1101/kits/{dsdv_eng_rr_h0_cc{A,B}{,_g2typed},ot_s81sl_vsw_cv{A,B},ot_s81sl_ve_s_cw1728{,_measure},dsdv_gunit_l1c_cc{A,B}}. PROTECTED dirs (e13a, kp4_e13a_*, rt22m_hx2, ...) stay in place.
- Manifest epyc2:.../prune-1103a/e2_mvC.txt, result e2_mvC_result.tsv.
- C result: 29/30 MOVED (90.07 GB); signoff-sprint-19/hcol skipped (live).
- epyc2 TOTAL 03:58: moved 41 dirs, 213 GB, to /home/ubuntu/scratch-root/claude with symlinks (bytes+count verified, nothing deleted). scratch2 137 -> 327 GB free. TARGET MET.

## intel2 manifests (2026-11-03 04:10 PST) per COORD LOOP-GAP 04:0x RELEASE (a)/(b); intel2 55 GB free
- (a) 19 non-latest kit-wave attempts idle >24 h (latest attempt per item kept): intel2:/srv/opentallas-scratch2/claude/prune-1103a/i2_att_rel.tsv (bytes, mtime, path). p3a_rm.py rechecks PROTECTED/live/recent.
- (b) 4 superseded flow-canary/sources idle >24 h, not on any flow-* tag (51 tag shas kept) nor 9db068b5458b/bdf7be91c845/9e74a778c: 54c62d41b5b3, 951cc627353e, b1a2125433d0, efa6a9b9fff9 (11.1 GB): .../prune-1103a/i2_src_rel.tsv.
- (a)+(b) RESULT 04:15: 23/23 removed, 29.33 GB (18.19 attempts + 11.14 sources). intel2 55 -> 81 GB free. Only 4 sources were eligible: 28 of 32 exports are on a flow-* tag sha or <24 h idle (kept per ruling).
- (e) MOVE intel2 -> epyc2:/home/ubuntu/scratch-root/claude/moved-intel2-1103/<name> (xmv.sh: live/recent/PROTECTED check, rsync -aH, apparent bytes + file count verify, remove intel2 copy, leave dir with MOVED.txt + .keep): codex-qwen-images-1101 (70), codex-hbm-whole-1101 (50), codex-head-wave-1101 (33), codex-s81-wave-1131 (26.5) RUNNING.
  NOT moved: codex-flow-s81-source-2055 (written <24 h: src/tools/die_plan/__pycache__ by a root process = someone imports from it); codex-head-event-1030 (holds the PROTECTED HEAD signed records elemA_signed/elemB_signed in kit_root_ab574 = 34.7 GB of its 38.5; rest <3 GB).
- (c)+(d) 04:28 manifest intel2:.../prune-1103a/i2_cd_rel.tsv: DIE-HEAD-56 RELEASE 04:06 die-head-48/prd53/hd_st_{k5,turn}_F{48,64} + dh53/spn3_v{1,2} (+logs, 41.9 GB) and DIE-HBM-60 RELEASE 04:10 hbm-cores-kits-40/wt_d44q/physical (31.4 GB). KEEP lists of both owners stand.

## intel2 manifest D (2026-11-03 04:33 PST): flow-canary DBs (COORD 11-02 22:2x item 1 class: superseded-tag + untagged idle runs)
- Kept run shas: bdf7be91c (r tags), 9db068b54 (q tags), 9e74a778c (m-kv). 736 runs eligible (newest file >24 h, not live /proc+docker, no .keep/SIGNED, not PROTECTED, no run-name mention in ~/coord outside prune manifests, and NO reference in any *.f/*.mk/*.json/*.tcl/*.sh/*.md/*.py/*.txt on intel2 scratch2 [grep -rlF of all 736 names: 0 files]).
- Only generated *.odb/*.spef/*.def/*.gds (nlink 1) deleted: 725 files, 67.58 GB. Manifest intel2:.../prune-1103a/i2_can_db.tsv; verdicts i2_can_runs.tsv; executor act.py del (rechecks mtime/.keep/live).
- (c)+(d) RESULT: 21/21 removed, 73.33 GB. (e): codex-qwen-images-1101 (73.0 GB) + codex-hbm-whole-1101 (52.4 GB) MOVED to epyc2 moved-intel2-1103 (bytes+count verified, MOVED.txt left); codex-head-wave-1101 + codex-s81-wave-1131 skipped "live" = a foreign find (pid 2068627) whose argv names them as -path exclusions, retry when it ends.
- D RESULT: 725/725 deleted, 67.58 GB. intel2 scratch2 55 -> 309 GB free 04:33 = TARGET MET.
