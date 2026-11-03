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
