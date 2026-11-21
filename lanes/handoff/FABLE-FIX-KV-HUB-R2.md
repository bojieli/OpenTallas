# FABLE-FIX-KV-HUB-R2 handoff (Fable; successor of FABLE-FIX-KV-HUB). CURRENT 2026-11-21 06:4x PST
Family: kv3_hroot (representative), kv3_hub_{Ei,Eo,Wi,Wo}, kv3_sys_c. Rows go to KV-PLAN-R5. Read lanes/handoff/FABLE-FIX-KV-HUB.md first
(diagnosis, variant B, gen_b.sh rules); this file only adds what changed.
Work dir: epyc8 /srv/opentallas-scratch2/claude/fable-fix-kv-hub. Scripts of this lane: rtx-pro scratchpad kvh_*.py / kvh_*.sh.

## Live units and waiters
- hroot variant B strict bind B2: intel2 client 3833051 -> epyc8 fable-fix-kv-hub/bindgate_b2/gate.out (started 06:13, about 2 h).
  Re-arm: timeout 14400 ssh -n -o ControlPath=none intel2 'export OT_LANE=FABLE-FIX-KV-HUB-R2; ot-wait 3833051 --poll 120'
- D27d rebind of record (KV-PLAN-R5's unit, read only): client 2222389 -> epyc8 kv-plan-r3/d27c/bindgate_d27d_r5/gate.out.
- hub_Ei D25e3 attempt_4 route: ENDED 06:19, cancelled by the GRT-FLAT watchdog (legit). Job dir kept on epyc10
  ot-jobs/kv3_hub_Ei-route-civil-redfish-2122132-1795231162.

## Findings 06:2x-06:4x
- hub_Ei GRT flat overflow = full-stack reserved-row walls. congestion-5.rpt: 1,005 lines, 996 capacity 0, all vertical; 997 on 7 thin
  horizontal walls = die_clock_tree reserved rows that the D25e3 kit's reserved_sites.tcl obstructs on M1-M7 over the full length.
  Worst 478.5..802.3 x 1654.02..1655.37 under north pin bank ft36_i (523 bits, x 627..714): 573 lines.
  Already fixed in the D26 and D27d plans (route_layers M1-M2 + stack_um windows; 0 classic long rows on all 7 family types; D26 hub_Wo /
  sys_c kits have M3-M7 obstructions <= 2.8 um). No rows needed. Test = the first D26/D27d hub_Ei kit: read congestion at GRT iteration 5,
  expect no wall; then the only open hub_Ei class is port_in hold (seam, parent).
- hub_Wo D26 kit FAILED kit preflight (cland_band_legal_site): u_cland_raw_fs_o_host_host_rst_n_0 on the ft3 comb.
  ROW posted to KV-PLAN-R5: kv3_hub_Wo clock.landing_raw_branches[fs_o_host_host_rst_n].stages[0].xy_um [986.461,829.3] -> [979.461,829.3].
  Verified with kit_preflight.cland_band_sites (0 errors at dx -7). Same site is in D27d and tree_b, so a private D27d hub_Wo kit fails
  preflight until the row is in. hub_Wo otherwise has tb_cdirect, flow_tag, env keys.
- sys_c D26 passed preflight; its place job went to intel1 (reported to COORD / WAVE-FLOW-R2).

## Next
1. Bind B2 green -> gen_b.sh b1 (already reads bindgate_b2) -> diff config.mk against the D26 wave hroot kit
   (epyc7 kw43-wave-1109/runs/qwen_kvsys/kit-wave/qwen_kvsys/KV-D26/items/kv3_hroot/gen/kv3_hroot when it exists, else D25d attempt_5)
   -> run_kit.sh GOAL=route via ot-run on epyc7/8/10 -> read post-hook: OT_TAP_SPAN, 4_2_tapbal_grt.log, OT_CLK_LEAF_REPEAT grt, TT at GRT.
   R8_STALE on B2: r8_refresh as kv-plan-r3/d27c/r8_refresh_d27d.sh on tree_b, rebind.
2. D27d green: private hub_Eo kit (and hub_Wo only with the row above) with the wave env, unless the KV-PLAN-R5 apply relaunches them.
3. Fix 9 (hub_C / sys_c window rows) still not started.

## 07:4x COORD rulings
- hroot kit b1 = variant B control only. Build it with rt/current tools/autopilot/kit_wave.py private-spec kv/qwen_kvsys kv3_hroot
  (--plan, --tree tree_b, --bind-out, --src-manifest off, --host epyc8, --lane); gen_b.sh only as fallback. Diff config.mk vs the D26 wave kit.
- Leaf-balance A/B (OT_CLK_LEAF_GRT_BAL=1, main 36f47f8037) SKIPPED: private-spec has no tool overlay and tree_b is on rt 4e46a7ec46c5.
  Never hand-copy a tcl into a kit. FLOW-CLKGRT-1121 (clock-first GRT) shares kit b1; post the kit path to it after gen.
