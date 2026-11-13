# REACH-FIX-2 lane handoff (updated 2026-11-12 16:4x PST)

## 1 Scope
Owner of the deterministic reach tool tools/die_plan/reach_fix.py (owner 11-12 "reach resolved via fixed scripts"), run at
compose on every die event: class 1 tap radius, 2 sinks/tap (cap S81 800, QC/KV/HEAD/HBM 1200; k-medians re-site,
measured sinks, min taps, empty-tap drop), 3 fclk repeaters, 4 signal hop +k regs, 5 reset reach + role- AND depth-keeping
re-select, 6 landed window (+k cycles from a hops TSV). COORD classes: RESET-WAVEFRONT-TAPS (done, proven) and
INSERTION-BALANCE all dies (priority; proven on HEAD fix2 + KV vN in DIE-PROTO-2's die STA with die_clock ladder RC).

## 2 Worktree
epyc7 /srv/opentallas-scratch2/claude/wt/reach-fix-1, branch claude/reach-fix-2-main-1112 HEAD 39e04ecad5 (pushed, clean; + 39e04ecad5 column to COORD spec (geometric parent, exit at child line, data-sink band); + e60e4fab8d reset column mode + relay_rule slew_safe 130 um; + 8f61cd7a19 per-type reset.relay_um; + c81d837870 FAIL-LOUD, 082b2c63ca/b251146029 leafcell, bd0bf92f81 regeq --routed) =
main d3f85cdf01 + 7 cherry-picked REACH-FIX-2 commits (5e19ca2647..72e2c1295a) + FIXED-CYCLES 54d2a1ec4b. READY posted 13:00
(ROOT-MERGE-60) and 13:2x (adds 54d2a1ec4b). Old branch claude/reach-fix-1112 (370eac82bd) is superseded by it.
Tests (epyc7 repo root, --basetemp under reach-fix-2/pyt): test_reach_fix (20) test_dieclock_routed test_die_clock*.py
test_taps* test_die_sta_related test_street_rule* test_schema -> 188 passed 8 skipped.
Local edit copies: localhost scratchpad rf/ (reach_fix.py, test_reach_fix.py) = branch HEAD.

## 3 Running jobs
None. RESET-SLEW sweeps done: rsw/{s81 epyc8, head+kv epyc4, qc+hbm epyc9}.json (sweep.py, summ.py). Measure epyc9 reach-fix-2/rp17/rsl.
## 4 Scripts
- scratch .../reach-fix-2/ on epyc4/8/9/intel1: rf2_run.sh TAG PLAN SRC [args] (check+tap table -> fix -> after);
  rf2_g0.sh TAG BASEPLAN DIEDIR SRC (G0 diff); rf_dc.sh TAG PLAN SRC (die_clock run + balance score; needs sta+libs:
  intel1/epyc8 only; launch intel2 ot-run --hosts intel1 --priority die --dir B --stage <inputs>).
- epyc9 .../reach-fix-2/dp/: my copy of DIE-PROTO-2 chain (proto_die.sh with :ro mounts of their wt/scratch,
  dump_landed.py, mk_combo_kv.py), dieclock_arrivals.py, dcsta.sh DIE TAG PLAN (die_sta_related on dieclock proof).
- epyc4 genchk2.sh CODE RTL PLAN SIDE TYPES; CODE for HEAD = .../reach-fix-2/code_head_gen (branch tools + wtM8 links +
  branch physical/common_flow/failfast_rules.py overlay); mkgen.sh rebuilds it and reruns srx3e.
- epyc9 reach-fix-2/rt_leg.sh + rtleg.py (NDR 8W levels<=10 / 4W per net, pads --route-ndr with 4w+wide10 globals).
- epyc8/epyc4 reach-fix-2/reprice.py CODE EVENT OUT: FIXED-CYCLES sync on an existing reach_fix output.
- localhost scratchpad rf/post.sh FILE: queue post + coord-commit + origin confirm.

## 5 Results
- 2026-11-12 16:1x READY dieclock_regeq --routed + dieclock_route_step (bd0bf92f81); smoke on rl/rb3 = 25.3/25.4 overflow 0 (rl/smoke).
- 2026-11-12 15:4x CAP-2000 STEP (posted): 25.3 TT / 25.4 FF, landed 397.88/395.89 PASS, overflow 0, FF contract 37 need 5.57 -> gate FAIL.
  All 37 = 0-5 ps plan per_port_ps on early-side ports of hd_ctl_n / hd_spn_eshim_rx / hd_spn_wshim_tx; asked HEAD-95 to re-derive
  (kitwin dp/head/rloop3_sta/kitwin.json + 10). S81 fail-loud type svc_lo_dsdv_svc_rs__t7 told to DIE-S81-88 (hbm_i0 rect_um != rects_um[0]).
- 2026-11-12 15:0x DELAY-CELL STEP (posted): gate FAIL. 17/41 capped leaves have a channel on their own leg; 24 are 0.25-6.4 mm inside types.
  HB4 measured 51-81 ps TT (125-269 with 126-154 um detours), FF/TT 0.55-0.60 -> ~25 ps FF tracking error per cell. Run2 B: 122.9 TT /
  59.3 FF, landed 316.85/377.24, FF contract 61. Best form still wire step 2. Proposed (a) leaf cap 2000 um on the 41 leaves; awaiting COORD.
- 2026-11-12 14:3x FAIL-LOUD READY (c81d837870): reach_fix check/fix exit 3 + REACH-FIX-FAIL type list on any per-type error / broken bind rule.
- 2026-11-12 14:0x ROUTED RE-BALANCE (posted + correction): step0 136.2 -> step1 42.1 TT / 36.9 FF -> step2 43.3 no gain; overflow 0 all steps;
  landed margin 375.39/382.49 (step1); FF contract 308 -> 44 -> 33 (need 4.66). Stall = 41 leaves at the 1500 um cap (n10_694 needs 43.3 ps).
  Proposed: 1 HB4xp67 at each capped leaf root (channel site) or lift cap ~2000 um; awaiting COORD. epyc9 rl/rloop.py, rl/rloop.json.
- 2026-11-12 13:3x HEAD ROUTED CHECK (posted): GRT overflow 0, M8/M9 0.06%, pad 5.53 m, worst gcell 13.06 mm M8 (fits);
  routed spread 136.2 TT / 115.1 FF (model 2.4/4.2); landed damage 84.28/70.21 PASS (margin 334/346); FF contract 308 need 38.57.
  Data epyc9 dp/head/rtleg (grt_<C>, pd_<C>), dp/head/rtleg_sta, arrivals dir dp/dc/head_rtleg.
- 2026-11-12 13:2x FIXED-CYCLES (54d2a1ec4b, posted): sync_fixed_cycles (bus-station delta -> lane fixed_cycles, bind rule check,
  latency table refresh). S81 79e22ea61177 -> 2d689bfae217 (epyc8 plan_s81_r12ng/plan_rf_fc.json): dn_s_5S_L4 2->3, coll__lk_EN0/EN1 1->2,
  +23 cycles on 20 lanes, rule broken 0. HEAD sp3n2/srx3e and KV vN: 0 lanes changed.
- 2026-11-12 13:00 KV PHY tap-site ASK posted to DIE-KV-99 (vN2e event).
- 2026-11-12 12:57 TAP-CAP PROVEN (posted): SP3n2 kit placed (epyc4 reach-fix-2/kit_sp3n2), nearest busiest tap 958 <= 1000, 68 taps.
- 2026-11-12 12:40 TAP-CAP (b) (370eac82bd): class 2 on the nearest split + anchor sinks; SP3 placed sinks 1225 -> 964 (plan 3ac13457f663).
- 0c2348e9e2 regeq caps (the 324 GB SPEF in s4/best/it6 was my diverged scratch run; I removed it).
- HEAD regeq with long-hop + L choice (a8006d1570): 14.1 ps TT, 3899 insertion; KV refused (393 ps regional residual, PHY last mile).
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
DONE (posted): column READY 39e04ecad5; RESET-SLEW RESULT (L_safe 130 um, per-die a/b sweep, ASK: 0-cycle repeater pitch vs relay pitch).
1. COORD ruling on RESET-SLEW form (relay pitch opt-in already on branch vs 0-cycle reset-hop repeaters at 130 um).
2. (3) rp18 die clock + reset gate re-run when HEAD-95 freezes rp18: same recipe as rp17 (epyc9 reach-fix-2/rp17/rp17run.sh + rp17run3.sh,
   regions reg/proof_m by part from fix2), plus RT.check / wf_plan on rp18.
3. SP3n2 GRT hold if it fails like SP2: mine. Merge-lane questions on @39e04ecad5.
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
