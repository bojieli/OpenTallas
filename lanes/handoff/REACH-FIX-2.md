# REACH-FIX-2 lane handoff (updated 2026-11-12 07:55 PST)

## 1 Scope
Owner of the ONE deterministic reach tool tools/die_plan/reach_fix.py (owner 11-12 "the reach problem can be resolved via
fixed scripts"), run at compose on every die event. Classes: 1 tap radius, 2 sinks/tap (DIE_CAP S81 800, QC/KV/HEAD/HBM
1200) + density-weighted k-medians re-site + measured sinks + min taps, 3 fclk repeaters, 4 signal hop +k regs,
5 reset reach + role-keeping re-select, 6 landed window (+k cycles from a hops TSV). COORD-assigned classes:
RESET-WAVEFRONT-TAPS (empty taps / stale group overrides after a reset re-solve) and INSERTION-BALANCE (all dies,
DIE-S81-88 ready12b method = die_clock.py run + part-pair score; `reach_fix.py balance`).

## 2 Worktree
epyc7 /srv/opentallas-scratch2/claude/wt/reach-fix-1, branch claude/reach-fix-1112, HEAD e37db65694 (pushed), clean.
Commits: e603275bfb (caps/measured/kmedians/min-taps/tap-table/role/class6), 7d874717a0 (RESET-WAVEFRONT-TAPS),
e37db65694 (balance). Contains merge of claude/street-rule-1112 3cca0a68ed. Tests (run from repo root, epyc7):
python3 -m pytest -p no:cacheprovider --basetemp=/srv/opentallas-scratch2/claude/reach-fix-1/pyt3 tools/die_plan/test_reach_fix.py
tools/die_plan/test_street_rule.py tools/die_plan/test_landing_raw_branches.py tools/die_plan/test_schema.py
tools/die_plan/test_landing_group_rects.py  -> 80 passed. NOT merged to main (gen on other trees rejects the clock keys
reach_fix_sinks / edge_split_ports: schema keys only on this branch).

## 3 Running jobs
- intel1 via ot-run (die prio): rf_dc.sh kv_vN and head_g5p (die_clock.py run --iters 30 + reach_fix balance).
  Out intel1 /srv/opentallas-scratch2/claude/reach-fix-2/dc/{kv_vN,head_g5p}/ ; state dc/<tag>.state ; score dc/<tag>.score,
  balance.json, residue_hops.tsv. Client logs intel2 ~/reach-fix-2-logs/dc_{kv,head}.log. Started 14:48 UTC (S81 took 21 min).
- epyc9 /srv/opentallas-scratch2/claude/reach-fix-2: rf2_run.sh qc_hf1c_s (QC 55d318eece08), kv_vN (77533c398d4d,
  --min-taps kv3_hgi_v8=39), qc_ovr (19 QC types with stale group overrides). Logs o_qc.out o_kv.out o_qcovr.out;
  outputs run/<tag>_{check,event,after}.json, run/<tag>_taps_{before,after}.tsv, plan_<tag>/plan_rf.json.
- epyc8 same dir: s81_r12ng (77cad171c6ee, check has --landed-hops ready11r TSV; fix classes 1-5 only). o_s81.out.
- Check: ssh <host> 'cat /srv/opentallas-scratch2/claude/reach-fix-2/o_*.out'; ps -eo args | grep reach_fix.

## 4 Scripts (Codex re-arms nothing periodic; these are runners)
scratch dir /srv/opentallas-scratch2/claude/reach-fix-2/ on epyc4/epyc8/epyc9/intel1:
- rf2_run.sh TAG PLAN SRC [args]: check(+tap table) -> fix -> after-check, code = ./code (git archive of the branch).
  env J=threads, CHECK_EXTRA=check-only args. Refresh code: ssh epyc7 'cd wt && git archive HEAD tools' | ssh H 'cd .../code && rm -rf tools && tar -xf -'
- rf2_g0.sh TAG BASEPLAN DIEDIR SRC: G0 base vs fix diff (links die dir census etc.).
- rf_dc.sh TAG PLAN SRC [die_clock args]: balanced die clock + score (needs ~/.local/opentallas-tools/bin/sta + NLDM libs:
  only intel1, epyc8 have both). Launch via intel2 ot-run --hosts intel1 --priority die --dir <B> --stage <inputs>.
- epyc4 genchk2.sh CODE RTL PLAN SIDE TYPES: gen phys --trial with branch tools (link repo-root dirs into CODE first).
- queue post helper (localhost): scratchpad rf/post.sh FILE.

## 5 Results not yet posted
- HEAD g5p cap 1200: 14 -> 3 viol types (5e0253c70393 -> 8410d31804b9); G0 153 -> 1 error (152 clock_landings cleared, 0 new).
  hd_spn_end c1 33->0 but not applied: landing_local_resets.458 (fstart_face_bd_o) 416 um from nearest same-role depth-4
  relay after re-solve (base 217); terminal lever made it 1 -> 184, so base kept.
- HEAD srx3 (6 moved types, 5b21002c20c2 -> ed976790fa2a): 6 applied, viol 6 -> 1; hd_st_turn empty taps clk_t4/t18/t20
  dropped + re-derived; hd_st_n3_turn 2 raw exports 815/867 um remain. gen --trial (branch tools) now passes the tap stage
  but stops at hd_tile landing_local_resets.tile_geo_3: consumer depth 5 != copy depth 4 (raw rst_rl_95) = depth part of
  the same re-solve class (hd_tile not moved: die wavefront shifted its depth). NOT yet fixed.
- S81 balance scorer validated: reproduces dieclock_run 946 pairs, TT 15/max 534.0, FF 0/399.2. S81 r12ng check: c6 799 lanes
  need +880 cycles if all 780 ready11r hops took registers (do NOT apply; residue after balanced clock is 15 TT pairs).
- QC hf1c_s check: 37 type errors = 18 missing qcviews_1112 LEFs in wt/qc-s28-hf1c (env) + 19 stale group_rects_um overrides.
- epyc4 /srv/opentallas-scratch2/claude/kw45/src_head_main_m8w1_7b84010b1c is a self symlink (ELOOP) -> run HEAD/KV on epyc9.

## 6 Next steps
1. When intel1 dc/*.state shows SCORE: read dc/<tag>/balance.json (TT/FF over_window). Post RESULT: before (DIE-PROTO-2
   1,031 KV / 1,238 HEAD) vs after. If over_window > 0: reach_fix.py fix PLAN --landed-hops dc/<tag>/residue_hops.tsv
   --classes 6 gives +k cycles; post as the residue lever. If die_clock fails on a die: read dc/<tag>.log, fix generically.
2. qc_ovr: when o_qcovr.out shows fix rc: count types whose override error is gone (run/qc_ovr_event.json rows
   fix.group_overrides) -> that is the QC proof for RESET-WAVEFRONT-TAPS.
3. Fix hd_tile depth contract: re-select landing_local_resets raw so depth(raw)+1 == depth(consumer reset)
   (clock_landings.py ~1984 check). Then rerun epyc4 genchk2 on plan_head_srx3. Coordinate with HEAD-95 (decision 08:15).
4. Post READY to COORD for branch claude/reach-fix-1112@<sha> with tests (80 pass) and per-die invocations:
   reach_fix.py fix PLAN --repo SRC --out-plan OUT --event EV -j 16 [--min-taps T=N] [--sinks-dir D] [--landed-hops TSV]
   (cap default per die), then G0 via rf2_g0.sh; balance: die_clock.py run PLAN --out RUN --corner TT --corner FF --iters 30
   then reach_fix.py balance PLAN --run RUN --hops-tsv R.tsv.
5. Hourly STATE in lanes/COORD-REVIEW-QUEUE.md.

## 7 Open READY/ASK
- STATE 06:15 and 07:30 posted. No READY yet for the branch (step 4). COORD must approve for merge (ROOT-MERGE-60).
- Open question to COORD: HEAD/HBM cap 1200 taken from METHODOLOGY 3.3 (12 has no number).

## 8 Gotchas
- ssh with background `&` hangs: use (setsid nohup ... &) inside a subshell.
- ot-run refuses input paths outside --dir unless --stage PATH.
- epyc8 is LOADCAP (load > 1.1x cores): jobs wait; use intel1.
- pytest needs --basetemp under scratch (tmp garbage perms) and must run from repo root for test_schema.
- After schema key changes run python3 tools/die_plan/schema.py dump-schema (test_schema_file_in_sync).
