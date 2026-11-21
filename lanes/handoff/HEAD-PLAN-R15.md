# HEAD-PLAN-R15 handoff (11-20 PST; target apply 11-21 ~18:00)

Lane dir: epyc10 `L=/srv/opentallas-scratch2/claude/head-plan-r15` (all work). Hub client logs: intel2 `~/head-plan-r15/*.otrun.log`.
Lane clone: `L/repo` (main cca0222940, nothing committed). Pinned tools: rt `/srv/opentallas-scratch2/claude/rt/ec4936598992`
(tools_sha ec4936598992b920726119eed4d6c40bbdc32a88, rt_pin.py resolved 11-20 ~20:0x PST; includes 3553de9af815).
Base: r13r NOMCAP tree `kw45/snap_s81_head/s81_head_r13r_nomcap_s0` (plan eccfe487c232, tools 385f61b5). Live HEAD stays r11b.
hd_serdes / hd_lep0N kits of their own lanes: not touched.

## Event tree
- `L/tree/s81_head_r15_s0` = r13r tree + ADOPT-DIFF LAG carry from main (879 files, 2 deletions; hardlinked, so every write
  there must be copy+mv). ADOPT-DIFF report `L/adopt/` (966 commits, LAG 881, BOTH 17, ledger 12 missing -> carried by tools).
  BOTH tools/die_plan (14 files) take main's version. BOTH kept at the event version: rtl/.../ot_s81hd_lep_nr.sv,
  tools/s81_head/head_lep_nr_sources.py (event = main + RST-FAN-1 superset), tools/s81_head_die_model.py (comment only).
  Check: tree tools/{die_plan,autopilot,fleet,precheck} *.py == rt: 0 diffs. `src_manifest.py publish` still owed before staging.

## Plan rows (L/compose.py, L/rows/)
- pre: hd_serdes verilog_defines + OT_S81_RM_STAGED, OT_S81_KP4_ENC_LA, OT_S81HD_SERDES_RLEAF (RLEAF needs main db39768f4a6:
  in the carry); hd_serdes START parent rows from Codex serdes_r1_300_trial_v2.json (reader coll_i0, writer coll_o0);
  hd_lep0N r14 delta (133 relay sites, 64 differ; 2 x stage:mlwd_h4 rect -> [1199.0 660.69 1209.0 674.19]) -> `plan/p0_rows.json`.
- OT_GPL_SPARSE_OVERFLOW=0 for hd_serdes: carried by the pinned tools (gpl_sparse_overflow is off for s81_head since
  FLOW-NOADV-R2/R3); no plan key exists. Verify no OT_GPL_SPARSE_OVERFLOW line in the r15 hd_serdes config.mk.
- post: hd_lep0N tap_offset = all 251 rows on the r13 die clock tree_e5c13a, routed RC (OPUS-FIX-HEAD-LEP0N-R2
  r13_routed_all251.json: 195 re-derived, drift mean -3.9 sd 24.9 min -79.9 max +63.6 ps, + 56 clk_t191..t246). Only
  hd_lep0N has a tap table in this plan.

## Reset re-pick: variants and why each failed
- a (`s1_repick.py`, cap 300, reset_anchor same-depth nearest-to-old-site): 12 types fail closed (no same-depth relay within
  405 um): the 300-um trees are 1-4 levels deeper (hd_ctl 3->4, hd_spn 7->10, hd_lep0N 7->10), so depth-d relays moved.
- a2 (cap 300, pick by worst leg to the START stage, any depth as fallback): legs fine (3 types >300: st_k5 384, ctl_n 322,
  host_n 391) but ~100 depth changes; gates run r15: GEN_RTL FAIL `hd_ctl landing_local_resets.k0 consumer depth 4 != copy
  depth 3 (release edge would move)`; G0 5749 errors, all START-tree class: `tE*/tW*/sp* rst_start_raw_N: raw reset export
  source instance/net/xy differs from actual reset tree` + `infrastructure pin used N times`. reset_start_raw_exports
  (every type, die START tree wiring) and local resets also name relays; a 300 re-solve re-dates the die START tree.
- c (no re-pick, OT_RESET_HOP_CAP_UM=405): hd_ctl.a_tx_o passes, next `hd_host_n.ad_o writer START raw reset rst_rl_13 has
  no registered wavefront driver`; G0 4393 errors, same export class. Cause: legal relay sites (42eeacf87f) move relays
  even at 405.
- d (`s1b.py`, identity re-pick: same depth + start role + nearest site; tap exports -> tap at the site, leaf depth may move;
  local resets left to the generator's LOCAL-RESET-RAW-1; cap 405): 0 errors, 17/26 types zero remaps (byte-identical
  trees), changes only in hd_tile (depth 4->5, 6 stage + 9 export remaps, max 378 um), hd_spn_end (58 stage + 14 export),
  hd_st_turn, hd_st_str, hd_st_m, hd_lep0N, hd_host_n, hd_turn_b, hd_spn_eshim_rx/tx, hd_mesh_e. Plan `plan/p3_cap405.json`
  (943e8f90269c), receipt `plan/p3_cap405.receipt.json`. Cap-300 version `plan/p3_cap300.json` still fails closed on
  hd_tile (rst_rl_118 554 um).
  GATES r15d RUNNING: intel2 client pid in ~/head-plan-r15/gates15d.pid, log ~/head-plan-r15/gates15d.otrun.log
  (L/gates15d.sh -> L/gates15.sh: install plan, native receipt, gen-pass bind + cohort, republish DIFF types, strict bind +
  cohort + LATCHECK, G0).

## Why 405 and not 300
The 300-um default (aced0fb210 / CBC rule 4) applies to NEW binds; bound plans keep the cap they were bound with
(FLOW-NOADV-R2 bound_reset_hop_cap, 9172a65b43; owner 11-20 "defaults come from the bound plan"). At 300 every HEAD reset
tree re-solves 1-4 levels deeper with roughly twice the relays: every type's netlist changes (all 25 signed relaunch), and
the die START tree (raw exports, local resets, START dates) must be re-derived. That is a die-wide re-date, not a re-pin,
and is not doable safely by 11-21 18:00. r15 keeps 405 as the bound cap and moves only what the legal-site change moved.
HEAD has no bound-native receipt cap, so 405 must be in the event's die_gen_env (OT_RESET_HOP_CAP_UM=405) or HEAD needs a
receipt reach_cap_um. That needs a COORD ruling. The 300 re-solve stays on the next-event list (variant a2 = starting point).

## Next
1. Read r15d: GEN/COHORT/BIND/LATCHECK/G0. G0 baseline on r13r was 0 errors: any residual export/infra-pin rows are the
   remap's to fix.
2. plan_geom_census + event_census (`L/census.sh`, after the plan is in the tree). event_census `hold` only from the hub.
3. reset_leg_plan.py (lockup default 2aad63e13d, legal sites) for the types over 300 in the census, on placed geometry.
4. `src_manifest.py publish` the tree, stage to kw45/snap_s81_head/s81_head_r15_s0 (E9+E10), marker with tools_sha
   ec4936598992b920726119eed4d6c40bbdc32a88 + die_gen_env OT_RESET_HOP_CAP_UM=405.
5. One proof kit through CTS: hd_ctl (the rst_rl_22 type) or hd_tile (largest remap); kit_rtl export with the r15 prep,
   preflight reset_tree_coherence must pass.
6. Apply. Relaunch only types whose published wrapper changed (cohort DIFF list); 17 types expect identical trees.
7. FABLE-PD-HEAD-2040 reviews R15 in parallel: take its levers when they are posted.
