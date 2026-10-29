# DIE-KV-32-KITS 2026-10-29: bind face-flop fix + KV kits_gen4

Failing face_guard "shared" bits (kits_gen3 synth netlists, fg3/*.json): io_cor/io_cor_v1/io_ft/io_ft_v1 2 each, hub_Ei 5.

| bit | root cause | fix (commit 87505104b, tools/die_plan) |
|---|---|---|
| cland_tstart_out | assign = cland_start (44 io_ft / 204 io_cor / 678 hub_Ei internal loads) | own face flop ot_dp_landing_relay u_cland_tstart_o (d=start_d, start raw reset), DIE-HEAD-10 FSTART form |
| cland_raw_reset_out | keep reg aliased to the port -> Yosys BUF onto the kept wire = 1 extra load | ot_dp_rrelay u_cland_raw_reset_o drives the port alone (same D) |
| hub_Ei rst_o_0 | reset_tree out tap rr_t21 reused as raw reset by u_cland_monitor_0 + collector (5 loads) | landing_collector.raw_reset: a raw tap driving assign rst_o_k takes the existing same-parent copy relay u_cland_reset_rst_n_t21 (d=rst_rl_57 = u_rrl_58 D) |
| hub_Ei cland_dn_ready_0/fault_0 | 4 slot loads of the plain DEPTH-4 ring u_cland_monitor_0 (by design) | declared hold_mux in land_slots.json via DIE-S81-26 plain-ring emitter (da623c93b) - scratch port, see below |
| kv3_hroot place 3_3_place_gp | landing_placement.tcl findNet(landing_ready_ft0_i) misses u_bound.landing_ready_ft0_i | unique hierarchical suffix match, ambiguous/none fail closed (commit fed4129294) |

Exactness: bound diffs bound_diff_*.txt are exactly the 3 hunks. yosys equiv (eq.sh: equiv_simple+equiv_induct -seq 3):
io_ft 47908/47909, io_cor 144338/144339 proven; the 1 unproven is cland_tstart_out (needs the reset-reachable
invariant start(t+1)==start_d(t)), proven by sat -tempinduct with reset (fv_tstart_o_P0_E0.sv form, PADW 1 x pad 0/1 x efall 0/1: 4/4 PASS,
OT_ORIGIN_MUTANT_LATE 4/4 caught) = results/die_head_1028/die_head_10_fstart/fv_start_o.sh case A.

Bind: run_bind.sh in a symlink tree of codex/kv-0822-1029@9178c9c155 (its clock_landings/landing_collector == origin/main) with the
two patched files: strict bind errors 0, 4:13 wall, 8.7 GB RSS. Kits: gen4.sh (gen tree = DIE-KV-31 gen_root (landslots 810219984)
+ fed4129294 landing_placement.tcl + scratch port of plain_ring_land_slots taking pins.json + plan_pins.json names (S81 code takes
pins.json only; the hub_Ei monitor pins are bound-only)); hroot keeps bind_fast kit RTL (diff vs kits_gen3 = landing_placement.tcl).
