# REACH-FIX-2 lane handoff (updated 2026-11-12 08:25 PST)

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
None. Realize loops (1x RC) were stopped on COORD's order; rz_try1 and rz are their partial outputs.
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
WAIT for COORD's decision on A (realized BUFx24 tree) vs B (H-tree to region roots), posted 2026-11-12 08:25. KV NDR is queued behind it.
If B: (a) diagnose the 788 ps region-root spread in die_clock --aware-levels 0 (leaf load imbalance, repeater/4W
quantization); load-match leaves, target under 100 ps; (b) realize --sites channel: lift cells to the nearest channel ancestor, cell HB4xp67;
(c) die STA FF for the cell-vs-wire corner term (wire FF/TT 0.83, cells 0.73-0.76).
Old NDR realize pass-2 recipe (only if A): realize dp/head/rzn/clk1 ARR(intel1 ndr1/pd/arr_TT.txt) -> clk2, NDR=1 rt_grt.sh, pads --no-pads --route-ndr, STA.
Hourly STATE; keep this file current.
## 7 Open
dadcdf9535 APPROVED. READY 08:20 for 7ed95e4f02 (dieclock_routed). ASK 07:21 combo-GRT adapter owner (COORD). Q: HEAD/HBM cap 1200 source.
## 8 Gotchas
- Routed gate must use NDR (rt_grt.sh NDR=1 + pads --route-ndr); 1x GRT RC alone adds ~2 ns spread on HEAD.
- OpenROAD create_ndr here needs explicit {M8:0.08 M9:0.08}; '*:2*' fails.
- NO pkill at all (COORD rule); kill exact PIDs only. ssh + background: (setsid nohup ... &).
- ot-run refuses paths outside --dir unless --stage. epyc8 LOADCAP. epyc4 kw45/src_head_main_m8w1_7b84010b1c self-symlink.
- die_clock tree.json node ids are strings: trial_tap_arrivals cannot read it -> use dieclock_arrivals.py.
- wtM8 physical lacks failfast_rules.py that branch gen needs -> overlay dir (code_head_gen).
- Queue timestamps in my 07:20/07:35 posts were early (real 07:12/07:21 PST).
