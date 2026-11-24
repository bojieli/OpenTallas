# DLYRAM-RESET handoff (updated 2026-11-24 03:30 PST)

Lane dir: epyc11 /srv/opentallas-scratch2/claude/dlyram-reset/ (clone = lane clone of main).

## Done
- Step 1: case (a) PROVEN (ring_bmc_all.sh, bmc/all.txt): rp derived from wp; from any state q == D-flop line from edge D, D 4..130; 3 negative controls refuted. SRAM init irrelevant. 4-state X = sim pessimism.
- Step 2: only kit_dly_ram.py emits the ring: 31 KV pv types of D29. S81/HEAD/QC/HBM: none.
- Step 3 (post be3903cd): flush2.py on D29 bound RTL, H=21: 46 wavefront pins in 10 parts get line garbage after release (worst +79 pv_v12/pv_v7 u_vport_W.pr_valid); spine cores need die_rst_n release >= 254; START >= 35. bind_reset.json pv join taps 286/287 dangling (RTL uses die_rst_n spine).
- FABLE (d) (post b8d49880): 135->120 = synthesis opt_merge in qkd_pv16_vport_b (qv[w]==sv[w]); 44->0 = ot_dp_rtail .a(1'b1) synchronous relay copies. No reset lost.
- HOLD row draft (post 9ca315e0): hold/ROWS_DLYRAM-RESET-HOLD.py IN OUT -> reset.source.lock.stable_cycles 16 -> 256 (releases +240). flush2 --hold 261 --rshift 240: 0 wave violations. Sent to KV-ALLFIX.
- Bench + sim-only fix (post cf56cdb3, main 84ccd7f50f): OT_DLY_RAM_PTR_INIT (sim only), rtl/test/dp_dly_ram/run_reset.sh per-domain 4-state + 2-state random; PASS D+2, FAIL D-5. Netlist byte-identical.

- HOLD row in A5t2 (KV-ALLFIX ROWS_KV-ALLFIX-RSTSTABLE a2e424967dfd, plan a160bc6c5c2c). hub_C relaunch note posted (dcd70b4b).
- die_rst_n timing (post fcd8b8cb): not contracted; RTL floor = R_Wi + ~172 (213 now, ~453 with row) vs need 254.
- A5t2 offsets measured (dlyram-reset/a5t2/off*.json): +240 on all 175 parts, max_release 145 -> 385.
- Classes + release order (posts 62a80495, d48d3714): flush3.py = earliest first-valid per source class vs consumer release. pv_v3 SAFE (spine->spine +1), hg SAFE (+9 / +6); START is a level, start_t taps unused. UNSAFE class: 17 cores reset by die_rst_n on a DATA lane (hroot u_kvs_hroot x4, hub_Eo/Wo u_astk, u_seq fan/xs, u_hp_fault) release T_D+8..41, fed by spine producers from T_D+10 (29 pins, worst -32 hroot_EN.i_g). Proposed fix: put those 17 on the spine. Also flagged: A5t2 ready_at_glue 504 is stale (computed before the +240 row).
- A5t3 (post 778c1625): flush2 --hold 261 = 0 wave garbage; flush3 pv/hg SAFE; pv reset CLEAN, reset hold lifted. Residue = 17 lane-reset cores (owned by KV-SPINE-REWIRE row).

## Open
- flush3 on the A5t2 bind too (`flush3.py RTL OUT --reset bind_reset.json --lanearr lanearr.json`; first run with --write-lanearr).
- WAITER: localhost scratchpad dlyram/waiter3.sh (bg, 5 h) fires when intel2 kv-spine-rewire/gate_R*/bind/rtl/qwen_kvsys_bound_top.sv appears -> run flush3 (first --write-lanearr, then --lanearr) on it; post 0 lane-unsafe or residue.
- S81 / HEAD / QC sweep belongs to RESET-HOLD-SWEEP (not this lane).
- Caveats of flush2: name-level graph, cores black boxes, noreset cores optimistic.
