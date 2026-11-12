# REACH-FIX-2 lane handoff (updated 2026-11-12 07:25 PST)

## 1 Scope
Owner of the deterministic reach tool tools/die_plan/reach_fix.py (owner 11-12 "reach resolved via fixed scripts"), run at
compose on every die event: class 1 tap radius, 2 sinks/tap (cap S81 800, QC/KV/HEAD/HBM 1200; k-medians re-site,
measured sinks, min taps, empty-tap drop), 3 fclk repeaters, 4 signal hop +k regs, 5 reset reach + role- AND depth-keeping
re-select, 6 landed window (+k cycles from a hops TSV). COORD classes: RESET-WAVEFRONT-TAPS (done, proven) and
INSERTION-BALANCE all dies (priority; proven on HEAD fix2 + KV vN in DIE-PROTO-2's die STA with die_clock ladder RC).

## 2 Worktree
epyc7 /srv/opentallas-scratch2/claude/wt/reach-fix-1, branch claude/reach-fix-1112, HEAD dadcdf9535 (pushed), clean.
Commits e603275bfb, 7d874717a0, e37db65694 (balance), dadcdf9535 (depth contract + dieclock_arrivals.py).
Tests (epyc7, repo root): python3 -m pytest -p no:cacheprovider --basetemp=/srv/opentallas-scratch2/claude/reach-fix-1/pyt3
tools/die_plan/test_reach_fix.py tools/die_plan/test_street_rule.py tools/die_plan/test_landing_raw_branches.py
tools/die_plan/test_schema.py tools/die_plan/test_landing_group_rects.py -> 82 pass. READY posted 07:21 (not merged).
Local edit copies: localhost scratchpad rf/ (reach_fix.py, test_reach_fix.py, dieclock_arrivals.py) = branch HEAD.

## 3 Running jobs
- epyc9 /srv/opentallas-scratch2/claude/reach-fix-2: rf2_run.sh qc_hf1c_s (QC 55d318eece08, all 122 types) and kv_vN
  (77533c398d4d, --min-taps kv3_hgi_v8=39) fix stages, started 14:35 UTC, -j 24 each. Logs o_qc.out / o_kv.out; outputs
  run/<tag>_{check,event,after}.json, plan_<tag>/plan_rf.json. Check: ssh epyc9 'tail -n1 .../o_kv.out'.
- epyc9 dp/kv/dc_bal: dump_landed (landed/landed_pairs.json) via ot-run; STATE file there.
- epyc8 o_s81.out (S81 r12ng 77cad171c6ee fix classes 1-5) may still run.

## 4 Scripts
- scratch .../reach-fix-2/ on epyc4/8/9/intel1: rf2_run.sh TAG PLAN SRC [args] (check+tap table -> fix -> after);
  rf2_g0.sh TAG BASEPLAN DIEDIR SRC (G0 diff); rf_dc.sh TAG PLAN SRC (die_clock run + balance score; needs sta+libs:
  intel1/epyc8 only; launch intel2 ot-run --hosts intel1 --priority die --dir B --stage <inputs>).
- epyc9 .../reach-fix-2/dp/: my copy of DIE-PROTO-2 chain (proto_die.sh with :ro mounts of their wt/scratch,
  dump_landed.py, mk_combo_kv.py), dieclock_arrivals.py, dcsta.sh DIE TAG PLAN (die_sta_related on dieclock proof).
- epyc4 genchk2.sh CODE RTL PLAN SIDE TYPES; CODE for HEAD = .../reach-fix-2/code_head_gen (branch tools + wtM8 links +
  branch physical/common_flow/failfast_rules.py overlay); mkgen.sh rebuilds it and reruns srx3e.
- localhost scratchpad rf/post.sh FILE: queue post + coord-commit + origin confirm.

## 5 Results (all posted 07:12-07:21)
HEAD fix2 landed 1237.93 -> 30.27 TT; KV vN 1031.15 -> 78.07 TT, KV contract 732 -> 0; srx3 gen 8/8 rc=0; QC overrides
19/19. Negative control: die_trial top.form htree breaks intra (HEAD 24,566 / KV 25,900 contract violations).

## 6 Next steps
1. When o_kv.out / o_qc.out show fix rc: post RESULT (types_viol before/after, applied), run rf2_g0.sh on them.
2. If COORD answers the ASK (route die_clock tree in combo GRT): adapter die_clock ctree.v/place.json -> mk_combo_kv
   kit clock form (kit/clock/tree.json, ctree.v, ctree.tcl), then proto_die.sh with KITSRC; decision: landed damage
   <= 416.5 routed -> hand to DIE-KV-99/HEAD-95 as die clock of record candidate.
3. Hourly STATE to lanes/COORD-REVIEW-QUEUE.md (last 07:25 PST).
## 7 Open
READY 07:21 branch dadcdf9535 (COORD/ROOT-MERGE). ASK 07:21 combo-GRT adapter owner (COORD). Q: HEAD/HBM cap 1200 source.
## 8 Gotchas
- NEVER pkill (I matched my own ssh shell once); kill exact PIDs only. ssh + background: (setsid nohup ... &).
- ot-run refuses paths outside --dir unless --stage. epyc8 LOADCAP. epyc4 kw45/src_head_main_m8w1_7b84010b1c self-symlink.
- die_clock tree.json node ids are strings: trial_tap_arrivals cannot read it -> use dieclock_arrivals.py.
- wtM8 physical lacks failfast_rules.py that branch gen needs -> overlay dir (code_head_gen).
- Queue timestamps in my 07:20/07:35 posts were early (real 07:12/07:21 PST).
