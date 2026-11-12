# HEAD-95 lane handoff (HEAD s81_head die owner), refreshed 2026-11-12 14:46 PST

## 1 Scope
HEAD die owner (successor to HEAD-94). COORD 06:09 brief: west growth one pass (CLOSED 08:33, fallback taken), HB4 seam shims, wshim_rx DRV ECO, visual gate via GEOM-VIS-5, route on epyc8/9 (not epyc2), hourly STATE.

## 2 Worktrees / work dirs (all on epyc4)
- /srv/opentallas-scratch2/claude/wt/head-95 : branch claude/head-95-west-1112 @ 9b00af8484 (= origin claude/head-94-heads-1112), no commits yet. Untracked symlinks only (native_domains, core_pins, assets, lat, macro_rects_*, rtl, physical/* -> HEAD-94 wtM8 copy).
- /srv/opentallas-scratch2/claude/wt/head-95-rfsr : detached at REACH-FIX 2e629df9ae + tools/die_plan/street_rule.py from 3cca0a68ed (role-matched reset resel), uncommitted on purpose (tool overlay). THIS is the tool tree for check.py / reach_fix.py / street_rule.py / gen.py (wtM8 tools reject the reach_fix_sinks key).
- head-95-sr (3cca0a68ed), head-95-rf (2e629df9ae): plain tool checkouts.
- Work dir: /srv/opentallas-scratch2/claude/head-95/ : pd/ = prep dir (plans must sit in it: side files resolve relative to the plan dir; symlinks to HEAD-94 srx_pd). Plans: pd/k1_plan.json (base, = HEAD-94 k1, G0 153 errors), pd/srx3_plan.json (HEAD-94 west move), pd/wp1*.json (west pass, abandoned), pd/rp1/rp2/rp3*.json (re-pack fallback). Scripts: west_pass.py, repack_lep.py, relocate_empty_taps.py, genchk.sh (gen phys --trial per type), g0diff.py. Copies of scripts + drawings: intel2 ~/coord/lanes/head-95-west-1112/.

## 3 Running jobs
- hd_lep0N v2 KIT PLACE: v2b FAILED port_bind (gen phys lacks rst_start_raw ports); v2c = v2b + raw_patch.py (kit_rtl alias+private patches) queued on epyc8 /srv/opentallas-scratch2/claude/head-95/lep0N_v2c, log ~/head95log/lep0N_v2c_place.log. Old: epyc8 /srv/opentallas-scratch2/claude/head-95/lep0N_v2b (run_kit.sh hd_lep0N place 64 16), ot-run launched from intel2 at 07:5x, log intel2 ~/head95log/lep0N_v2b_place.log (queued on the epyc8 memory gate at launch). Kit from plan epyc4 head-95/pd/rp14.json df181b8d64d0 = rp13 418072d26cc1 (v2 form + landing-band trim, GEOM-VIS-6 07:44 FORM GOOD) + tap_window floor. Kit source copy: epyc4 head-95/kit_lep0N_v2b.
- wshim_rx ECO: prd_run DONE 07:14 PST (pass 2: TT slew 1, FF slew 1, cap 0, clk-freeze rc 0, finish rc 0; post_runner '-' = die owner signs off). SIGN-OFF job: ot-run epyc4 signoff.py run --run-dir pass_t10r_p2/run --kit pass_t10r_p2 --out pass_t10r_p2/signoff, log intel2 ~/head95log/wshim_rx_p2_signoff.log.
- wshim_tx: no ECO (COORD hold). Rebuild from the GEN-CLASS-1 FT-HOP-M2-WIRE branch when READY.
- HEAD-94 routes (logs intel2 ~/head94log/*.log): lb_mesh_st/_eo, lbal_hd_mesh/_eo (epyc7), pf_ctl (epyc2), meshk sign-off (epyc8).

- hd_ctl_n W10 RE-SIGN DONE + RECORDED 08:39 (ctln_w10/resign/PROVENANCE.json, LOCAL_PASS_NEEDS_PARENT, LEC EQ). Was: ot-run epyc4, dir /srv/opentallas-scratch2/claude/head-95/ctln_w10 (kit copy, SDC -early clk_t6/t7/t9 -> -10, run -> signed dh86/ctln_eco1/i1/run), resign.py tag flow-20261112-lz-head, out ctln_w10/resign, log intel2 ~/head95log/ctln_w10_resign.log.
- hd_spn_eshim_rx W10 BUILD routed, NOT SIGNED (TT -10.59, slew 194/190; same as pre-W10: RE-FORM item, CLAND-SLEW-1 likely for drv). Was: epyc9 /srv/opentallas-scratch2/claude/head-95/eshim_rx_w10 GOAL route, log intel2 ~/head95log/eshim_rx_w10_route.log; then sign-off.
- Tool branch READY: claude/head-95-twf-1112@0e5ce1603c (worktree epyc4 wt/head-95-twf).

- PLAN OF RECORD now rp15 epyc4 head-95/pd/rp15.json sha 7931b5662082 (= rp14 + lep0N land SRAM g_t[0]/[1] y 4.32/47.52 core-inset fix (MPL-0034) + window floor). lep0N v3 kit epyc4 head-95/kit_lep0N_v3 -> epyc8 head-95/lep0N_v3 place, log ~/head95log/lep0N_v3_place.log; place RUNNING on epyc8 (admitted before FLEET BALANCE; COORD: keep it). Then render -> GEOM-VIS-7 (a8bbc2a208a5175e9; GEOM-VIS-6 retired) -> route on epyc9.
- Kit-gen recipe sent to VISLAYOUT3-KVHEAD (a8e402dfc900a5ca8): gen.py phys + raw_patch.py (needed for port_bind), run_kit.sh place/route.

- hd_mesh (M1 m1_final e9c3c429) + hd_spn_end (SP2 6ef4172a = chosen form, routing epyc9; SP3 44a11562 dropped: kit tap split 1225 > SP2 1186) are owned by VISLAYOUT3-KVHEAD (a8e402dfc900a5ca8): kits placing on epyc9 vislayout3-kvhead/head/kit_*, renders go to GEOM-VIS-7. Do NOT build these here; after the GEOM-VIS-7 verdicts, merge their deltas onto rp15 (G0 + gen). Raw-port count explained: 19 declared, 5 reuse rst_o_1..5 (existing_port), so 14 new ports is correct; port_bind confirmation pending from VISLAYOUT3.

- 2026-11-12 11:54: lep0N v3 PLACE DONE (epyc8, rc 0); REVIEW REQUEST to GEOM-VIS-8 posted (renders lanes/head-95-west-1112/lep0N_v3_place_*.png). On GOOD/ISSUES-ACCEPT: ot-run --hosts epyc9 route (copy epyc8 head-95/lep0N_v3 to epyc9 first).
- rp16 (epyc4 head-95/pd/rp16.json f3655867deef) = rp15 + hd_mesh from VL3 m1_final + hd_spn_end from VL3 sp2. G0 0 NEW vs rp15; gen hd_mesh rc 0; hd_spn_end/lep0N gen results in epyc4 head-95/rp16.out (RP16_DONE). Becomes plan of record when all three pass.
- VL3 hd_mesh M1: place GOOD (GEOM-VIS-7) but NO route launched; asked COORD who launches it.

- 2026-11-12 12:02: PLAN OF RECORD = rp16 epyc4 head-95/pd/rp16.json f3655867deef (PLAN EVENT posted; G0 0 NEW, gen rc 0 mesh/spn_end/lep0N).
- hd_mesh M1 TAKEN OVER from VISLAYOUT3 (parked): route epyc9 kit vislayout3-kvhead/head/kit_mesh_m1, log ~/head95log/mesh_m1_route.log. Also own the sign-off of SP2 route (vislayout3-kvhead/jobs/hd_spn_sp2/route.log).
- hd_spn_wshim_rx FRESH kit from main 26c9ae03a493 (worktree epyc4 wt/head-95-main, sparse + head-93 prep links): epyc9 head-95/wshim_rx_main GOAL route, log ~/head95log/wshim_rx_main_route.log. raw_patch.py now takes OT_ROOT=<tree>.

- lep0N v3: GEOM-VIS-8 GOOD 11:51; ROUTE epyc9 head-95/lep0N_v3, log ~/head95log/lep0N_v3_route.log (sign-off at end).

- wshim_rx main kit: NOT SIGNED drv only (TT 154 / FF 134 slew pins, worst 419 u_cland_origin s2 D; CLAND-SLEW-1 copies present but nets still ~360 ps). Class fix requested from GEN-CLASS-1 / CLAND-SLEW owner; no re-run until it lands.

- hd_spn_end: CARRY SP3n2 (REACH-FIX-2 plan 3ac13457f663, taps 958/1000; GEOM-VIS-8 OK 13:01). Route epyc4 head-95/sp3n2 (copy of reach-fix-2/kit_sp3n2), log ~/head95log/sp3n2_route.log. SP2 route STOPPED at GRT 13:xx (hold_structural, FF ws -110 on bin bars u_bin_bw_i/u_bin_be_i, buffer cap x2): dropped. On SP3n2 sign-off: plan event rp17 with hd_spn_end from 3ac13457f663.

- wshim_rx: GEN-CLASS-1 LOCAL=1 ring form on claude/cland-hop-maxwire-1112@aee2a3f4707; recipe posted for their private rebind + sign-off. rp17 ITEM: wshim_rx reset relay hop u_srl_17/u_rrl_17 334 um (add relay or move site).

- rp17 CANDIDATE epyc4 head-95/pd/rp17wr.json 3d2929bfcc2b = rp16 + windows (kitwin rloop3, 11 ports, max 16) + landing_ring_wreg on wshim_rx/eshim_rx. G0 0 NEW. Freeze adds SP3n2 (3ac13457f663) on its sign-off; reset hop needs REACH-FIX-2 per-type reset reach knob (asked) else rp18. After freeze: send path to REACH-FIX-2; re-sign ctl_n/eshim_rx/wshim_tx (window-only).

- 2026-11-12 14:46: PLAN OF RECORD = rp17 FROZEN epyc4 head-95/pd/rp17.json 501a3ad70cc107d1 (copy on epyc9). Main worktree epyc4 wt/head-95-main now at 3b73826c4114. Jobs on rp17: hd_ctl_n re-sign DONE + RECORDED (ctln_w17/resign/PROVENANCE.json, LOCAL_PASS_NEEDS_PARENT); eshim_rx + wshim_tx full builds epyc9 head-95/k17_<type> (logs ~/head95log/k17_<type>_route.log); SP3n2 route epyc4; wshim_rx = GEN-CLASS-1 proof build. rp18 items: wshim_rx reset hop (needs REACH-FIX-2 per-type reset reach).

- eshim_rx rp17 build: NOT SIGNED drv only (TT 124/FF 134, 122 on read-select copies g_srep.sr[*].u_sel); setup fixed by wreg (+4.28). Rebuild when CLAND read-copy locality fix lands on main.

- DIE CLOCK FORM OF RECORD (rp17): epyc9 reach-fix-2/rp17/routed/it4 (ctree.v 2433b628b63c, pads.json 37517e5f3dc6, routed/kitwin.json 55daf79b71d8) + routed/leafpad4.json f0147100ea1f. Gate BLOCKED(kits) only.
- rp18 items: wshim_rx reset.relay_um 300 after 8f61cd7a19 (train 15) + wshim_tx relay_um (rp17 build NOT SIGNED: 4 reset-relay slew pins, hops ~340 um; value asked of REACH-FIX-2); hd_lep0N clk_t4/t6/t7 windows 93/90/90 from it4 kitwin (needs 83/80/80 > 71/69/61).
- Die STA view feed: post every signed HEAD view to REACH-FIX-2 (hd_ctl_n rp17 sent); post when measured pair count rises. FF hold all-pair diag -62.2 intra / -15.0 seam (watch).

- rp18 pin/outline (GEOM-REVIEW 16:0x): wshim_tx 4 slew nets = in-band W-E reset hops (340 um) -> relay_um 300 still the fix; start_i/arst_n W-face y518 pin -> move into band (y 711-1009). wshim_rx: pins spread over empty lower 65%, 45 relays, 334 hop in empty space -> move pins into band, then re-check relay_um. Outline shrink to ~700x320 proposed to COORD (die floorplan call).

- rp18 EVENT SHAPE ASK posted (sweep epyc4 head-95/sweep17, tool lanes/head-95-west-1112/outline_sweep.py): no shrink (pitch-locked); reset pass-through columns via reset.in_sites/parent_pins for wshim_tx/rx, eshim_tx/rx, turn_a/b; relay_um 300 wshim_tx; lep0N windows 93/90/90. Default build if no answer 30 min. Asked REACH-FIX-2 for a reset.column solver mode.

## 4 Watchers
- localhost background loop on ~/head95log/wshim_rx_p2_signoff.log. If this session ends, check by hand: verdict = signoff.py verdict pass_t10r_p2/signoff/signoff.json.
Posting helper: localhost scratchpad h95/post.sh.

## 5 Results (all posted)
- 07:16 TOOL-GAP -> REACH-FIX-2 (empty taps, gen vs reach_fix). 07:3x RESULT 0-ps windows (missing margin; lanes/head-95-west-1112/tap_window_floor.py; kit-contract neg 37 -> 0; re-sign hd_ctl_n, hd_spn_eshim_rx, hd_spn_wshim_tx at W 10). 07:3x TOOL-GAP lattice encoding (treecmp.py). 07:3x WAIT-FORM v2 drawing (GEOM-VIS-6 07:44 FORM GOOD). 07:5x STATE (band trim, rp13/rp14).

## 6 NEXT STEPS
1. When the epyc8 place finishes: render the place layout (layout_render_hook / GEOM tools), post WAIT-VISUAL to GEOM-VIS-6. Route only after their verdict (route on epyc8/9).
2. wshim_rx: verdict POSTED 07:5x = NOT SIGNED (1 slew pin u_cland_link_i dch[1] dsel = CLAND class; io_hold_parent needs the parent receipt). Re-sign after the CLAND fix.
3. wshim_tx: rebuild from the GEN-CLASS-1 branch when READY (with tap_window floor W 10 on clk/clk_t1); then ask DIE-PROTO-2 for the seam re-measure.
4. W10 batch running (see 3): post the hd_ctl_n re-sign verdict; sign off eshim_rx after its route.
5. The next HEAD form adopts balance (reach_fix.py balance / die_clock, claude/reach-fix-1112@dadcdf9535 once merged).
6. Hourly STATE (next due 08:55 PST), times from `TZ=America/Los_Angeles date`.

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
