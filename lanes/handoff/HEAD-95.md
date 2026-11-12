# HEAD-95 lane handoff (HEAD s81_head die owner), refreshed 2026-11-12 07:39 PST

## 1 Scope
HEAD die owner (successor to HEAD-94). COORD 06:09 brief: west growth one pass (CLOSED 08:33, fallback taken), HB4 seam shims, wshim_rx DRV ECO, visual gate via GEOM-VIS-5, route on epyc8/9 (not epyc2), hourly STATE.

## 2 Worktrees / work dirs (all on epyc4)
- /srv/opentallas-scratch2/claude/wt/head-95 : branch claude/head-95-west-1112 @ 9b00af8484 (= origin claude/head-94-heads-1112), no commits yet. Untracked symlinks only (native_domains, core_pins, assets, lat, macro_rects_*, rtl, physical/* -> HEAD-94 wtM8 copy).
- /srv/opentallas-scratch2/claude/wt/head-95-rfsr : detached at REACH-FIX 2e629df9ae + tools/die_plan/street_rule.py from 3cca0a68ed (role-matched reset resel), uncommitted on purpose (tool overlay). THIS is the tool tree for check.py / reach_fix.py / street_rule.py / gen.py (wtM8 tools reject the reach_fix_sinks key).
- head-95-sr (3cca0a68ed), head-95-rf (2e629df9ae): plain tool checkouts.
- Work dir: /srv/opentallas-scratch2/claude/head-95/ : pd/ = prep dir (plans must sit in it: side files resolve relative to the plan dir; symlinks to HEAD-94 srx_pd). Plans: pd/k1_plan.json (base, = HEAD-94 k1, G0 153 errors), pd/srx3_plan.json (HEAD-94 west move), pd/wp1*.json (west pass, abandoned), pd/rp1/rp2/rp3*.json (re-pack fallback). Scripts: west_pass.py, repack_lep.py, relocate_empty_taps.py, genchk.sh (gen phys --trial per type), g0diff.py. Copies of scripts + drawings: intel2 ~/coord/lanes/head-95-west-1112/.

## 3 Running jobs
- wshim_rx DRV ECO pass 2: epyc4 /srv/opentallas-scratch3/claude/head-94/prd_wshim/pass_t10r_p2 (route done 07:38, post-route steps running). Pass 1: TT slew 265 -> 3, FF 147 -> 1, cap 0, clock-freeze rc 0. Result = pass_t10r_p2/prd_result.json + final sign-off log.
- wshim_tx: no ECO (COORD hold). Rebuild from the GEN-CLASS-1 FT-HOP-M2-WIRE branch when READY.
- HEAD-94 routes (logs intel2 ~/head94log/*.log): lb_mesh_st/_eo, lbal_hd_mesh/_eo (epyc7), pf_ctl (epyc2), meshk sign-off (epyc8).

## 4 Watchers
- localhost background loop on epyc4 pass_t10r_p2/prd_result.json (2-min poll). If this session ends, check by hand.
Posting helper: localhost scratchpad h95/post.sh.

## 5 Results (all posted)
- 07:16 TOOL-GAP -> REACH-FIX-2: empty taps, gen vs reach_fix.
- 07:3x RESULT 0-ps contract windows: a missing margin (l48ue raw needs). Class fix lanes/head-95-west-1112/tap_window_floor.py (per_port floor 10, cap per_type). fix2 plan -> 14822917340c; die STA re-timed on the REACH-FIX-2 balance proof: kit-contract neg 37 -> 0 (epyc9 /srv/opentallas-scratch2/claude/head-95/kw0/). Kits to re-sign with W 10: hd_ctl_n, hd_spn_eshim_rx, hd_spn_wshim_tx.
- 07:3x TOOL-GAP lattice encoding not geometry-neutral (street_rule/core_place origin only; reset_tree tree differs flat vs encoded) -> REACH-FIX-2; repro lanes/head-95-west-1112/treecmp.py.
- 07:3x WAIT-FORM -> GEOM-VIS-5: lep0N re-pack v2 = epyc4 head-95/pd/rp11_final.json a50145295ac5 (flat origins; C1-C4 answered; G0 0 NEW, gen rc 0, street 0), drawing lanes/head-95-west-1112/lep0N_repack_v2.png.

## 6 NEXT STEPS
1. Wait for the GEOM-VIS-5 verdict on v2 (GEOM-REVIEW.md / queue). On GOOD/ISSUES-ACCEPT: apply tap_window_floor.py to the plan, then build the hd_lep0N kit: cd /srv/opentallas-scratch2/claude/wt/head-95-rfsr && python3 -I tools/die_plan/gen.py phys <pd/plan> --clock-landing pd/sidecar.json --types hd_lep0N --out <kitdir> --rtl-root <tree> (no --trial), then run_kit.sh KIT GOAL=place via ot-run on epyc8/9; render place, WAIT-VISUAL, then route.
2. The next HEAD form adopts balance (reach_fix.py balance / die_clock, branch claude/reach-fix-1112@dadcdf9535 once merged) and the window floor.
3. wshim_rx: post the pass-2 sign-off verdict.
4. wshim_tx: rebuild from the GEN-CLASS-1 branch when READY; then ask DIE-PROTO-2 for the seam re-measure.
5. Hourly STATE (next due 08:05 PST), times from `TZ=America/Los_Angeles date`.

## 7 Open asks
- 07:20 RESULT: hd_st_turn fork vs fallback (COORD; I took fallback at 08:33).
- 08:33: die reset wavefront re-solve on any partition move moves signed hd_tile trees -> tool class for GEN-CLASS-1 / REACH-FIX-2; REACH-FIX tap export vs gen phys disagree (empty explicit taps) -> REACH-FIX-2.
- GEOM-VIS-5 06:49 verdict on v1: FORM APPROVED WITH CHANGES C1-C5 (v2 answers them).
- 07:16 TOOL-GAP to REACH-FIX-2 (empty taps, gen vs reach_fix) posted.

## 8 Gotchas
- gen/check need the plan INSIDE pd/ (relative side files) and the rfsr tool tree.
- prd_mk.sh needs a SO dir with tools/ AND physical/common_flow (clock_family.tcl); ot-run needs --stage <pass dir> --stage <SO dir>.
- hd_st_turn / hd_st_str are shared by 4 instances (nst1/10, sst1/10; nst2/9, sst2/9): never change them for one instance.
- epyc4 ssh drops intermittently (kex reset): retry.
