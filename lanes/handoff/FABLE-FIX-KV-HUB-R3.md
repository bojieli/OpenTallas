# FABLE-FIX-KV-HUB-R3 handoff (Fable; successor of FABLE-FIX-KV-HUB-R2). CURRENT 2026-11-21 10:3x PST
Family: kv3_hub_Eo / kv3_hub_Wo (oversize, 450k placed), kv3_hroot (variant B control), hub_Ei (no rows). Rows go to KV-PLAN-R5.
Read lanes/handoff/FABLE-FIX-KV-HUB-R2.md first; this file only adds what changed. Work dir: epyc8
/srv/opentallas-scratch2/claude/fable-fix-kv-hub/r3 (scripts), logs intel2 ~/tmp/fablefixkvhub-r3/.

## What R3 changed
- R2 rows failed landing_remap ("added tap clk_t8 violates outline/halo/tap spacing"): 4 Eo + 3 Wo added taps sat inside a new
  ring-core box + tap_clear 8.64 (R2 placer kept 2.16 um). r3/kvh_place_r3.py keeps 8.75 um from every grid + added tap;
  rows r3/rows/. taps.grid_explicit_sites passes. Hops: Wo ft2_i 287 um, Eo ft30_i 300, Eo ft31_i 373 (soft band was 402;
  240 again only if added taps clk_t8 [41.58,710.68] and clk_t60 [32.51,950.73] move: blockers are those taps + reserved rows at x>=78.84).
  DO NOT apply the R2 rows files (lanes/handoff/FABLE-FIX-KV-HUB-R2-rows_*).
- Chain (r3/chain_r3.sh -> hub_d28_r3/): landing_remap resel, collector_reattach (Wo +1 cyc), hard_ring_wreg, G0 PASS on cb6b8d5286c4.
- The 11-14 CLAND-MACRO-1 masters are stale (rtl/common/ot_dp_clk_landing_ca.sv changed 11-18). All 5 re-frozen from tree_h source
  (KV-PLAN-R2 1d hub_C recipe), all SIGNED 11-21 ~10:1x: epyc8 r3/rk/<m>/kits/<m>_synth0. Closed views + clock_contract.json:
  r3/views/<m> (export_all.sh), installed in tree_h physical/die_plan/qwen_kvsys/kvd28_hubring_views/, pins in
  plan_of_record/cores/kv_ring/<m>_pins.json. Masters: kv_cland_w1119_ew_86ca8, w300_ew_ebc75, w292_ns_abd47, w268_ns_6081a, w257_ew_aee53.
- Final plan b5bd29148814 = chain plan + row fields (track_offset_um [0.012,0.012], pins_file, lef, lib, reset_net =
  cland_reader_start_<bus>_<depth-1>, Wo _7 / Eo _8) + hub_Wo raw branch fs_o_host_host_rst_n stage 0 x 986.461 -> 979.461
  (the D26 hub_Wo KIT_PREFLIGHT cland_band_legal_site failure). Composer r3/compose.py; final rows r3/rows_final_d28.json.
- hroot B2 bind was hung (bind.py elab 4 h CPU, no output; normal 15 min): cancelled, relaunched once as B3
  (r3/gate_bind_r3.sh = gate_bind_d25.sh + python -X faulthandler on elab; out bindgate_b3).

## 12:4x PST state (supersedes the Live/Next below where different)
- Bind hang ROOT CAUSE: plan_package._gate_uncached quadratic scan on a private cp -al tree (stack via faulthandler). Fixed on main
  eeeac8421b7c; older rt snapshots (4e46a7ec46c5) need OT_BIND_PLAN_PACKAGE=off (r3/bind_gate_r3b.sh; private-spec --ab ... --why).
- Binds done (both after r8_refresh via r3/chain_r8_r3.sh, r8 a3252d36b57d): bindgate_h2 (tree_h, plan b5bd29148814) and bindgate_b5
  (tree_b) = D27d baseline 27 errors + 1 variant-B line "EMIT kv3_hroot: raw Q rst_rl_110: exactly one same-clk plain relay required".
  Ring rows add ZERO bind lines. kv3_hub_Wo emits (bind_of_record/rtl). hub_Eo does NOT emit on D27d (inherited r14 relay_depth rows,
  cut by KV-PLAN-R6 in D27d2). hroot variant B does not emit: needs the raw-branch re-derivation (landing_remap resel --types kv3_hroot,
  the D27d2 EMIT-fix form of KV-PLAN-R6) then rebind. NOT done.
- Rows package committed: lanes/handoff/FABLE-FIX-KV-HUB-R3-* (rows_final_d28.json, placer, chain, compose, export, r8 chain). Posted to KV-PLAN-R6.
- kv3_hub_Wi (owned here now): D26 fail = PORT_BIND extra io_pad_die_id[2:0]. Row: kv3_hub_Wi.pads += {name io_pad_die_id, dir in, width 3}
  (hub_C io_pad_refclk form). UNPROVEN: put it in the D27d3-based tree and check G0 + bind + kit gen PORT_BIND. KV-PLAN-R6 also wants
  qkd_hr_core_peer.lef re-exported exact-OBS (view_export b49b697c40) for hub_Wi: not started.
- COORD: run tools/die_plan/kit_pin_site_check.py on every hub kit before place (22-24 face pins under clock-site stacks on D26/D27d;
  cured by KV-PLAN-R6 clksite_pinclear in D27d3). No route/sign-off attempt on a kit with hits.
- LIVE: private-spec hub_Wo kit (place census only): intel2 pid 2468203 kit_wave run-item, log ~/tmp/fablefixkvhub-r3/runitem_Wo.log,
  spec ~/coord/autopilot/private_specs/FABLE-FIX-KV-HUB-R3/qwen_kvsys_kv3_hub_Wo_1121122822/, work epyc8
  kw43-wave-1109/runs/qwen_kvsys/kit-wave/qwen_kvsys/KV-D26/private/FABLE-FIX-KV-HUB-R3/kv3_hub_Wo_1121122822. Read: preflight
  (cland_band_legal_site must pass with the stage-0 row), pin-site check, placed cell count (target ~320k, cap 400k).
- NEXT: when KV-PLAN-R6 has the D27d3 tree (pinclear; ETA bind 13:15, apply 16:30 PST): new private tree = D27d3 + rerun
  kvh_place_r3.py (GRIDTAPS from schema._grid_taps, PREV=r3/rows) + chain_r3 + compose (+ hub_Wi pads row) + G0 + bind, then
  private-spec hub_Eo / hub_Wo / hub_Wi kits with 0 pin-site hits through route to sign-off. A sign-off build needs a src_manifest tree.

## Live units (re-arm with ot-wait <intel2 client pid>)
- final G0: intel2 client 2142778 -> epyc8 hub_d28_r3/g0gate_p4/gate.out.
- hroot B3 strict bind: intel2 client 1401789 -> epyc8 bindgate_b3/gate.out. If elab.log stays 0 bytes > 40 min: kill -ABRT the exact
  bind.py elab PID (stack lands in elab.log), post the stack, no third launch.

## Next
1. G0 PASS on b5bd29148814 -> strict bind: ot-run --hosts epyc8 --mem 56 --threads 3 --priority plan --dir W -- bash W/r3/gate_bind_r3.sh W/launch_h W/bindgate_h
   (judge only kv3_hub_Wo / kv3_hub_Eo / kv3_hroot lines; 27 inherited pc/pv errors expected). Check each ring's bound .rst_n equals reset_net.
2. private-spec kits (wave env): kit_wave.py private-spec kv/qwen_kvsys kv3_hub_Eo --plan <tree_h plan> --tree tree_h --bind-out ... --src-manifest off
   --host epyc8 --rt 4e46a7ec46c5 --lane; same for kv3_hub_Wo (re-run kit_preflight.cland_band_sites). Place census target ~320k.
3. Hand r3/rows_final_d28.json + views dir + pins + masters to KV-PLAN-R5 for D28. A sign-off build needs a src_manifest tree.
4. Optional W540 delay-line hard core only if the census needs it. Fix 9 (hub_C / sys_c window rows) not started.
