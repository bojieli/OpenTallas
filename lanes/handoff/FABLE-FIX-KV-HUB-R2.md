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

## 09:4x D28 size rows for hub_Eo / hub_Wo (COORD task from FABLE-PD-KV-0840) -- DESIGN DONE, PROOF RUNNING
- Measured (hub_Eo D25e3 attempt_4 netlist, epyc9): 381,852 synth cells -> 450,499 placed (x1.18). Blocks: ft landing rings 114.5k,
  unnamed flat comb 94k, delay lines u_d75/u_d15 seq fan_aq 48.6k flops, ft stations 47.7k, seq xs 11k, other rings ~40k.
  Only the 2 kv3_astk cores are hard today. The 11-18 KV-HUBWO-SPLIT rows (11 cores) were never applied (D23 EMIT on the reset tree,
  lane KV-HUBWO-RESET died at its second bind).
- Form = hub_C form (already live in the plan): the 9 landing rings with W >= 250 become hard child ring cores, 0 added cycles,
  per type 111,015 cells out: 381.9k -> ~271k synth -> ~320k placed (20 % under 400k). No outline change, no split of the type.
  Masters, all SIGNED (signoff.json verdict): kv_cland_w1119_ew_86ca8 x2, w300_ew_ebc75 x2, w268_ns_6081a x2, w257_ew_aee53,
  w292_ns_abd47 x2 (the ew twin w292_ew_abd47 never signed: intel1 run died at place 11-14; ns has the same params).
  Kits: intel1 / epyc2 / epyc10 cland-macro-1/rk/<master>. The bound rings carry NARROW=1 at type level; a hard ring binds with its
  param_wrap params (hub_C precedent).
- Second step only if the placed census of the first kit says so: delay lines u_d75 (Eo) / u_d81 (Wo) W540 as an ot_dp_dly hard core
  (param_wrap supports it; master unsigned) -> another ~40k.
- Rows: lanes/handoff/FABLE-FIX-KV-HUB-R2-rows_kv3_hub_{Wo,Eo}_d28.json (schema kv_hubc_split_rows.v1), writer
  FABLE-FIX-KV-HUB-R2-kvh_place.py (ORD=rev). Placement on the D27d plan: x on 1.728 um, y on 8.64 um (track / row lcm), minimum worst
  pin-to-core hop, clear by 2.16 um of ft bit sites, station regs, internal stations, relay sites, taps, reset sites, START / raw stages,
  reserved clock rows, other landing bands, hard-core halo 4.32. Worst pin-to-core hop 280 um (Wo ft2_i), 284 um (Eo ft30_i); the soft
  bands were 232..402 um.
- NOT in the rows yet (hub_C rows carry them; the D28 applier must add): track_offset_um, pins_file, lef / lib of the 5 masters into a
  tree views dir (kvd23_hubc_views form), reset_net.
- Proof chain = KV-HUBWO-RESET chain, script FABLE-FIX-KV-HUB-R2-hub_d28.sh (epyc8 fable-fix-kv-hub/hub_d28.sh): tree_h = hardlink copy
  of tree_b (plan 9ec33fa3c347 = D27d + hroot variant B) + rows -> landing_remap resel (both types) -> collector_reattach --sidecar ->
  hard_ring_wreg.py (kv-hubwo-reset/) -> G0. LIVE: intel2 client 3910929, log ~/tmp/fablefixkvhub/hub_d28.log, out epyc8
  fable-fix-kv-hub/hub_d28/. Then: ot-run --hosts epyc8 --mem 56 --threads 3 --priority plan --dir W -- bash W/bind_h.sh W/bindgate_h
  (about 3 h), then kv_start_corridor_event.py raw --bind-rtl on tree_h and a second bind if raw branches changed (KV-HUBWO-RESET steps).
  Expect the inherited 27 pc/pv errors of D27d in any bind on this base; judge only kv3_hub_Wo / kv3_hub_Eo / kv3_hroot lines.
- Also still open: hub_Wo preflight row (stage 0 of fs_o_host_host_rst_n to [979.461, 829.3]) is NOT in tree_h; the landing_remap may
  re-pick it, re-run kit_preflight.cland_band_sites on the first hub_Wo kit.

## 09:30 STAND-DOWN state (successor FABLE-FIX-KV-HUB-R3)
- LIVE, handed: hroot variant B strict bind B2, intel2 client 3833051, unit oth-ubuntu-2273706-1795270379 (epyc8, 3 h 17 in bind.py, no
  RC_BIND yet) -> epyc8 fable-fix-kv-hub/bindgate_b2/gate.out. Re-arm ot-wait 3833051. COORD ruling: if its errors are only the 27
  inherited pc/pv ones and kv3_hroot RTL is emitted, build kit b1 as PROOF ONLY through kit_wave.py private-spec (no leaf A/B).
- ENDED rc 3: hub ring chain (client 3952100, unit oth-ubuntu-1700205-1795282163). tree_h + launch_h were built; rows applied (plan_p0);
  landing_remap FAILED: "kv3_hub_Eo: reset_resel: ValueError: kv3_hub_Eo: added tap clk_t8 violates outline/halo/tap spacing"
  (log intel2 ~/tmp/fablefixkvhub/hub_d28.log, epyc8 fable-fix-kv-hub/hub_d28/s1_remap.log). tree_h plan_c.json is still 9ec33fa3c347
  (nothing installed). Cause to check first: my placer keeps 2.16 um to clock.added_taps points, the tap rule wants the hard-core halo /
  tap spacing (see taps / reset_resel check in tools/die_plan); raise the margin to taps in kvh_place.py (clear(): per-class margin) or
  move added tap clk_t8 of kv3_hub_Eo, re-write the rows (ORD=rev), then re-run chain_hub_d28.sh (it re-uses tree_h; remove
  hub_d28/plans first with ot-delete) and then bind_h.sh. Script name must start with chain / bind for --priority plan.
- Dirs to clean later with ot-delete (mine): epyc8 fable-fix-kv-hub/aside_h (hardlinks only), ana/d28, d28rev, d28wo, d28_fwd, d28_rev.
- D27d rebind of record ended RC_BIND 1 (27 pc/pv errors, KV-PLAN-R5 owns); no private D27d hub_Eo / hub_Wo kit was built.
