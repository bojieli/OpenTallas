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

## Running
- r16a gates (`M/gates16.sh`, private hardlinked tree `M/tree/s81_head_r16_s0` with patched tools, plan p4, no env): receipt, gen-pass
  bind + cohort; republish ONLY if cohort DIFF within {hd_serdes, hd_lep0N}, else STOP; strict bind + LATCHECK; G0.
- unit tests job T.

## Next
1. r16a pass -> push tools (ot-push-main), re-pin rt, publish tree with the new pin, stage, apply; launch hd_serdes + hd_lep0N
   (tell OPUS-FIX-HEAD-LEP0N-R2 / FABLE-FIX-HEAD-SERDES-R2; tr2s / sdr2c untouched).
2. Station rows for the >300 hops on UNSIGNED types only (hd_lep0N coll_i3 368); hd_spn/hd_spn_end/hd_tile are signed -> next event.
Stop list kept: no apply at 300, no auto-republish of signed DIFF types, no hd_tile relaunch on a depth-5 tree.
