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
