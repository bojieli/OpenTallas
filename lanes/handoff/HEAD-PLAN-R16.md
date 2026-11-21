# HEAD-PLAN-R16 handoff (11-20 PST; successor of HEAD-PLAN-R15; review FABLE-PD-HEAD-2040)

Lane dir: epyc10 `M=/srv/opentallas-scratch2/claude/head-plan-r16`. Hub client logs: intel2 `~/head-plan-r16/*.otrun.log`, pids `*.pid`.
Lane clone `M/repo` (main 389231a5c1 + uncommitted patch below). R15 dir/tree read only (`/srv/opentallas-scratch2/claude/head-plan-r15`).

## r15e (taken over, finished, not relaunched)
plan 92bcfc338f0a (form d + local-reset remap). GEN_RTL FAIL: `hd_tile: landing_local_resets.tile_geo_0: consumer u_cland_sin_agg_i_0
reset cland_reset_i depth 5 != copy depth 4 (raw rst_rl_145)`. G0 4921 errors. = RC2 (main re-solves hd_tile 4 -> 5 at 405).

## Lever 2 bisect (done; M/bis, M/cmp.py)
p2c (r13r rows, 405) dumped under 14 tool snapshots: 385f61b5, each of the 6 reset_tree.py commits and its parent, ec4936598992.
r13r old_trees == 385f61b5. Every step 0 types changed EXCEPT 42eeacf87f (legal relay sites, reset_tree._free row/cell free run):
11 types (hd_tile d4->5 239->265; hd_lep0N 1431->1405; hd_spn_end, hd_st_turn, hd_st_m, hd_host_n, hd_st_str, hd_mesh_e,
hd_spn_eshim_rx/tx, hd_turn_b). The R15 attribution was right; the other 5 commits change no HEAD tree.

## Fix (cause, not remaps) = levers 1+3 as plan authority (lane clone, not yet pushed)
- schema reset.reach_cap_um (pos) + reset.relay_site_rule {legal, interior}.
- cbc_rules.plan_reset_hop_cap + reset_hop_cap_um(plan=): receipt cap > plan cap > env > default.
- reset_tree.relay_um uses the plan cap; reset_tree.site_rule scope around _type_tree0 / _wf_type_tree: "interior" = pre-42eeacf87f _free.
- gen.py main runs the whole command under bound_reset_hop_cap(plan cap) (ring fan / raw START see it).
- tests: test_reset_tree.py +2.
Proof (job A): plan p4 = p2c + {reach_cap_um 405, relay_site_rule interior}, patched tools, NO env: 26/26 trees identical to r13r
(names, depth, sites). p2c without keys + env 405: 26/26 identical to ec4936598992 (no change for other dies / new binds).
Plan `M/plan/p4.json` f15722674c75.

## Results
- Tools on main 745c8f11e4 (pushed via ot-push-main, tests PASS); rt `/srv/opentallas-scratch2/claude/rt/745c8f11e429`.
- r16a (private tree M/tree/s81_head_r16_s0, lane-clone tools, plan p4 f15722674c75, no env): GEN PASS, BIND PASS, gen-pass cohort
  DIFF = hd_serdes only (defines; republished), strict cohort 26/26, LATCHECK 329/329, G0 0 errors (`M/g0_r16ab`). R15's G0
  'receipt refused' row was a gate-script bug (receipt written outside the tree, relative paths broke): receipt now written in-tree.
  R-REACH-5 warnings left: 4 rr_t<i> rows (hd_spn_end, hd_st_k5, hd_st_m, hd_st_str), unchanged trees/rows vs r13r; 0 rst_rl dangling.
- r16b = final form: tree M/tree/s81_head_r16b_s0 (R15 tree + tools/{die_plan,autopilot,fleet,precheck} == rt 745c8f11e429),
  plan p5 1a7d319a9ba6 = p4 + hd_lep0N coll_i3 stations re-spaced (1765,600)/(1765,320) -> (1765,700)/(1765,440): hops 267.6/260/182.4
  (was 367.6), same 2 stations, 0 cycles. Pinned-rt trees of p5, no env: 26/26 == r13r. Gates: intel2 ~/head-plan-r16/r16b.otrun.log.
- 300-um hops on signed types (hd_spn be_i/bw_i 850/706, x_o/b_i 340; hd_spn_end 850/706; hd_tile 573/421/398/342) NOT touched:
  signed, station rows would change their netlists -> next event (Fable F7).

## APPLIED (11-20 22:0x PST)
- r16b PASS (pinned rt, tree tools == rt 0 diffs): trees 26/26 == r13r, GEN/BIND PASS, cohort gen DIFF hd_serdes only, strict 26/26,
  LATCHECK 329/329, G0 0 errors, R-REACH-5 4 rr_t<i> warnings (pre-existing class).
- Pack M/pack_r16b (984 add, 2 delete: tools/autopilot tools_refresh*.py removed on main) -> live_tree.py apply: snapshot
  kw45/snap_s81_head/s81_head_r16_s0, manifest 80eaa65ea9cb, epyc10+epyc9 (+epyc7 synced by apply). Candidate M/cand_r16.json
  (= intel2 ~/head-plan-r16/cand_r16.json): tools_sha 745c8f11e429d7b6457d64cd1d78ceb449665054, receipt results/head_native_release_nf15f_r16.
- publish_gate record coord autopilot/publish_gate/s81_head/80eaa65e...json: schema, pre_g0, hashes, dry_gen (hd_serdes) PASS; contained
  FAIL = plan names kw45/snap_s81_head/s81_head_r4_s0 sink bins + an eco99 lib (inherited, same rows as r11b) -> advisory.
- apply_reviewed_tree_marker --optimistic --no-pilot: event head_rp21z20NF15f_r16; receipt lanes/handoff/s81_head_atomic_apply_1795240903731931643.json.
- Block identity r16 vs r11b: 21 equal; changed hd_serdes, hd_lep0N (this event) and hd_host_e, hd_host_w, hd_mesh (r13r base rows, not R16).
  die_ctx changes on all types (new reset keys); signed rows stay terminal on their block.

## Next
1. Confirm the wave launches hd_serdes + hd_lep0N on r16 (log.txt KIT-WAVE). tr2s / sdr2c untouched (any-plan count).
2. Signed >300-um hops (hd_spn be_i/bw_i 850/706, hd_spn_end 850/706, hd_tile 573/421/398/342) + 300-um reset re-solve: next event.
3. Clean the contained finding (copy r4_s0 sink bins into the tree, rewrite plan paths) in the next event.
