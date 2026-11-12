# REACH-FIX-2 lane handoff (updated 2026-11-12 09:00 PST)

## 1 Scope
Owner of the deterministic reach tool tools/die_plan/reach_fix.py (owner 11-12 "reach resolved via fixed scripts"), run at
compose on every die event: class 1 tap radius, 2 sinks/tap (cap S81 800, QC/KV/HEAD/HBM 1200; k-medians re-site,
measured sinks, min taps, empty-tap drop), 3 fclk repeaters, 4 signal hop +k regs, 5 reset reach + role- AND depth-keeping
re-select, 6 landed window (+k cycles from a hops TSV). COORD classes: RESET-WAVEFRONT-TAPS (done, proven) and
INSERTION-BALANCE all dies (priority; proven on HEAD fix2 + KV vN in DIE-PROTO-2's die STA with die_clock ladder RC).

## 2 Worktree
epyc7 /srv/opentallas-scratch2/claude/wt/reach-fix-1, branch claude/reach-fix-1112, HEAD 7ed95e4f02 (pushed), clean.
dadcdf9535 APPROVED by COORD (own merge train). 310e03fb32 + 7ed95e4f02 = dieclock_routed.py (prep/pads/realize); READY posted 08:20.
Commits e603275bfb, 7d874717a0, e37db65694 (balance), dadcdf9535 (depth contract + dieclock_arrivals.py).
Tests (epyc7, repo root): python3 -m pytest -p no:cacheprovider --basetemp=/srv/opentallas-scratch2/claude/reach-fix-1/pyt3
tools/die_plan/test_reach_fix.py tools/die_plan/test_street_rule.py tools/die_plan/test_landing_raw_branches.py
tools/die_plan/test_schema.py tools/die_plan/test_landing_group_rects.py -> 82 pass. READY posted 07:21 (not merged).
Local edit copies: localhost scratchpad rf/ (reach_fix.py, test_reach_fix.py, dieclock_arrivals.py) = branch HEAD.

## 3 Running jobs
- intel1 ot-run kvreg.sh: KV vN dieclock_regeq (same flags as HEAD) -> .../reach-fix-2/kvleg/b/ (b.log; KV_DONE at end).
## 4 Scripts
- scratch .../reach-fix-2/ on epyc4/8/9/intel1: rf2_run.sh TAG PLAN SRC [args] (check+tap table -> fix -> after);
  rf2_g0.sh TAG BASEPLAN DIEDIR SRC (G0 diff); rf_dc.sh TAG PLAN SRC (die_clock run + balance score; needs sta+libs:
  intel1/epyc8 only; launch intel2 ot-run --hosts intel1 --priority die --dir B --stage <inputs>).
- epyc9 .../reach-fix-2/dp/: my copy of DIE-PROTO-2 chain (proto_die.sh with :ro mounts of their wt/scratch,
  dump_landed.py, mk_combo_kv.py), dieclock_arrivals.py, dcsta.sh DIE TAG PLAN (die_sta_related on dieclock proof).
- epyc4 genchk2.sh CODE RTL PLAN SIDE TYPES; CODE for HEAD = .../reach-fix-2/code_head_gen (branch tools + wtM8 links +
  branch physical/common_flow/failfast_rules.py overlay); mkgen.sh rebuilds it and reruns srx3e.
- localhost scratchpad rf/post.sh FILE: queue post + coord-commit + origin confirm.

## 5 Results
- 2026-11-12 09:00 HEAD STEP 1 CONVERGED (posted): dieclock_regeq (d19e52b867) on intel1 s4/b2/it2: tap spread 2.4 TT / 4.2 FF, insertion 3953 TT,
  0 balance cells, pad 5.29 m; die STA dp/head/leg (epyc9; REF regions = die-proto-3/head/fix2/proof, NOT fix2_bal which has 1 region):
  landed dmg 2.01/3.17, margin 414.6/413.4 PASS; intra setup 647.05; FF contract 34 need 2.42. OCV5 worst landed 391 TT.
- 2026-11-12 08:43 STEP-1 (decision B, posted): die_clock --pad leg (commit eed85b641c): root spread 788 -> 15.6 TT; best = aware 0, window 0,
  --wide-levels 10 --ndr 4w: tap spread 109 TT (region last-mile residual), insertion 3880/3945 TT; seam OCV5 386 ps (unc 3829).
  Channel-only HB4: median 1.37 mm to a channel (HEAD is 90.6% type area; the tree's own cells are 90% inside types) -> residual by wire (regeq.py).
- 2026-11-12 08:25 STRUCTURE RESULT (queue): realize BUFx24 18,733 = 99.5% inside types (hd_tile 17,117), +19.3% area, +5.9% cap.
  HB4xp67 = 18.2 cells/ns, 1.85 um2/ns (vs BUFx24 45.9 / 20.1). Pure H-tree (die_clock build --aware-levels 0 --window 0)
  model geometry: spread 1846 -> 881 TT, insertion max 5774 -> 4609, cells -34%; but region-root spread is 788 ps.
  Data intel1 .../reach-fix-2/study/ (study.py cells|where|geom, study.sh, rzest.sh). Recommended B (H-tree fix + HB4 at roots).
- Routed findings (posted 07:29 partly): die_clock balance = 5.73 m SPEF-only pads + 4W NDR on >520 um hops; combo GRT
  (1x RC) of the padded tree: tap spread 6.7 ns; no pads 2.9-4.0 ns. pads self-test exact (0.37 ps). Hence REALIZE.
- HEAD realize it0: routed spread 3998 ps -> 47,207 BUFx24 delay cells on 12,453 branches (step 15 ps).
Earlier (posted 07:12-07:21):
HEAD fix2 landed 1237.93 -> 30.27 TT; KV vN 1031.15 -> 78.07 TT, KV contract 732 -> 0; srx3 gen 8/8 rc=0; QC overrides
19/19. Negative control: die_trial top.form htree breaks intra (HEAD 24,566 / KV 25,900 contract violations).

## 6 Next steps
1. KV: read kvleg/b.log; copy it<N> (tree.json arr_TT/FF.txt) to epyc9 dp/dc/kv_leg; dp/legsta.sh pattern with REF = DIE-PROTO-2 KV region proof
   (find the one with regions > 1, e.g. /srv/opentallas-scratch2/claude/die-proto-3/kv/*/proof) and dcsta.sh kv leg PLAN; post.
2. Step 2 (proposed, waiting on COORD): routed check of the leg tree: rt_grt.sh NDR with 8W on levels 1-10 and 4W, plus the pads (dieclock_routed pads --route-ndr).
3. Hourly STATE; keep this file current.
## 7 Open
- Open: realize --sites channel moves cells a median 1.37 mm on HEAD; proposed wire residual instead (posted). OCV 386 ps on top-cut landed pairs; mesh/spine at level 2-4 is the next lever.
dadcdf9535 APPROVED. READY 08:20 for 7ed95e4f02 (dieclock_routed). ASK 07:21 combo-GRT adapter owner (COORD). Q: HEAD/HBM cap 1200 source.
## 8 Gotchas
- Routed gate must use NDR (rt_grt.sh NDR=1 + pads --route-ndr); 1x GRT RC alone adds ~2 ns spread on HEAD.
- OpenROAD create_ndr here needs explicit {M8:0.08 M9:0.08}; '*:2*' fails.
- NO pkill at all (COORD rule); kill exact PIDs only. ssh + background: (setsid nohup ... &).
- ot-run refuses paths outside --dir unless --stage. epyc8 LOADCAP. epyc4 kw45/src_head_main_m8w1_7b84010b1c self-symlink.
- die_clock tree.json node ids are strings: trial_tap_arrivals cannot read it -> use dieclock_arrivals.py.
- wtM8 physical lacks failfast_rules.py that branch gen needs -> overlay dir (code_head_gen).
- Queue timestamps in my 07:20/07:35 posts were early (real 07:12/07:21 PST).
