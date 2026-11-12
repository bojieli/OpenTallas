# HEAD-95 lane handoff (HEAD s81_head die owner), refreshed 2026-11-12 09:15 PST

## 1 Scope
HEAD die owner (successor to HEAD-94). COORD 06:09 brief: west growth one pass (CLOSED 08:33, fallback taken), HB4 seam shims, wshim_rx DRV ECO, visual gate via GEOM-VIS-5, route on epyc8/9 (not epyc2), hourly STATE.

## 2 Worktrees / work dirs (all on epyc4)
- /srv/opentallas-scratch2/claude/wt/head-95 : branch claude/head-95-west-1112 @ 9b00af8484 (= origin claude/head-94-heads-1112), no commits yet. Untracked symlinks only (native_domains, core_pins, assets, lat, macro_rects_*, rtl, physical/* -> HEAD-94 wtM8 copy).
- /srv/opentallas-scratch2/claude/wt/head-95-rfsr : detached at REACH-FIX 2e629df9ae + tools/die_plan/street_rule.py from 3cca0a68ed (role-matched reset resel), uncommitted on purpose (tool overlay). THIS is the tool tree for check.py / reach_fix.py / street_rule.py / gen.py (wtM8 tools reject the reach_fix_sinks key).
- head-95-sr (3cca0a68ed), head-95-rf (2e629df9ae): plain tool checkouts.
- Work dir: /srv/opentallas-scratch2/claude/head-95/ : pd/ = prep dir (plans must sit in it: side files resolve relative to the plan dir; symlinks to HEAD-94 srx_pd). Plans: pd/k1_plan.json (base, = HEAD-94 k1, G0 153 errors), pd/srx3_plan.json (HEAD-94 west move), pd/wp1*.json (west pass, abandoned), pd/rp1/rp2/rp3*.json (re-pack fallback). Scripts: west_pass.py, repack_lep.py, relocate_empty_taps.py, genchk.sh (gen phys --trial per type), g0diff.py. Copies of scripts + drawings: intel2 ~/coord/lanes/head-95-west-1112/.

## 3 Running jobs
- wshim_rx DRV ECO: epyc4 ot-run unit oth-ubuntu-223592-1794492924, pass dir epyc4 /srv/opentallas-scratch3/claude/head-94/prd_wshim/pass_t10r (prd t10, OT_PRD_FROM=route, source kit prd_wshim/kit = pf_wshim fanout-cap route), log intel2 ~/head95log/prd_wshim_t10r.log; result = pass_t10r/prd_result.json then the kit GOAL=post sign-off (signoff.log in the final dir). At 09:00 in 5_2_route.
- wshim_tx DRV ECO: queued on epyc8 load gate since 06:30, pass dir epyc8 /srv/opentallas-scratch/claude/head-95/prd_wtx_t10r (SO dir epyc8 /srv/opentallas-scratch/claude/head-95/so), log intel2 ~/head95log/prd_wtx_t10r.log.
- HEAD-94 routes (logs intel2 ~/head94log/*.log, run logs in kit run/logs/asap7/*/base/): lb_mesh_st, lb_mesh_eo (epyc7 scratch2/claude/head-94/lb_mesh_*), lbal_hd_mesh/_eo (epyc7 scratch2/claude/head-lep0n-bal/build/hd_mesh*/gen/hd_mesh, containers dpkit-hd_mesh-3631383/3632102), pf_ctl (epyc2 scratch2/claude/head-94/pf_ctl), meshk hd_mesh sign-off (epyc8 scratch2/claude/head-94/meshk). All were in GRT repair at 09:00.

## 4 Watchers
None armed. Posting helper: localhost scratchpad h95/post.sh (scp a one-line post to intel2 + coord-commit).

## 5 Results not yet posted
- re-pack v3 (rp3: v2 + blocked local reset taps moved vertically off macros) was launched 09:10 and lost its ssh; NOT run. v2 result: street_rule street 0, tap_street 0, outline_street 0, sliver 33 (stacked rx see-through), outline_sliver 3; REACH-FIX c2 36 -> 0, c5 1 left; gen FAIL 'local reset tap [1287.36, 652.32] is blocked' (top tx row).

## 6 NEXT STEPS
1. epyc4: cd /srv/opentallas-scratch2/claude/head-95/pd && python3 -I ../repack_lep.py k1_plan.json rp3.json ; then in wt/head-95-rfsr: reach_fix.py fix pd/rp3.json --out-plan pd/rp3_rf.json --event ../rf_rp3_event.json --repo /srv/opentallas-scratch3/claude/head-94/wtM8 --types '^hd_lep0N$' ; then ../genchk.sh <rfsr> pd/rp3_rf.json pd/sidecar.json hd_lep0N. Rule: gen rc 0 -> step 2; a new blocked tap/macro error -> fix in repack_lep.py (class, not per point) and repeat.
2. G0: in rfsr tree check.py pd/rp3_rf.json --out ../g0rf_rp3 --quiet; python3 -I g0diff.py g0rf_k1/g0_report.json g0rf_rp3/g0_report.json. Rule: 0 NEW -> step 3, else fix.
3. Render (draw_lep.py) -> post to GEOM-VIS-5 for a form verdict; on GOOD/ISSUES-ACCEPT build the hd_lep0N kit (export/gen like HEAD-94 srx pipeline, epyc8/9 via ot-run) to place, WAIT-VISUAL, then route.
4. wshim_tx ECO: if not admitted on epyc8 by 09:30, kill only that ot-run client on intel2 (pid in ps, args contain prd_wtx_t10r) and relaunch with --hosts epyc9 after copying the pass dir + so dir to epyc9.
5. When wshim_tx (or its ECO) signs off: ask DIE-PROTO-2 for the seam hold re-measure (gate +10 ps, HB4 only, seam_groups off).
6. wshim_rx ECO verdict: read prd_result.json + sign-off line, post RESULT. cland dch fan-in slew class belongs to CLAND lane / GEN-CLASS-1.

## 7 Open asks
- 07:20 RESULT: hd_st_turn fork vs fallback (COORD; I took fallback at 08:33).
- 08:33: die reset wavefront re-solve on any partition move moves signed hd_tile trees -> tool class for GEN-CLASS-1 / REACH-FIX-2; REACH-FIX tap export vs gen phys disagree (empty explicit taps) -> REACH-FIX-2.
- 09:00: GEOM-VIS-5 verdict on lanes/head-95-west-1112/lep0N_repack_v1.png.

## 8 Gotchas
- gen/check need the plan INSIDE pd/ (relative side files) and the rfsr tool tree.
- prd_mk.sh needs a SO dir with tools/ AND physical/common_flow (clock_family.tcl); ot-run needs --stage <pass dir> --stage <SO dir>.
- hd_st_turn / hd_st_str are shared by 4 instances (nst1/10, sst1/10; nst2/9, sst2/9): never change them for one instance.
- epyc4 ssh drops intermittently (kex reset): retry.
