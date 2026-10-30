DIE-HEAD-36 fork C src25q (2026-10-29 22:12 PDT): ONE HEAD source = src25p + fork A status-depth sidecar (d1ecb2c69dd)
+ re-sited stale START raw reset exports (HEAD-KITS-U 20:40 ASK, COORD default).
Source: intel2 /srv/opentallas-scratch2/claude/die-head-36/src25q/src25q  source_plan.json sha256 ccfe76f0b881fc255af94af9c48d7c4a71639f13fdd40814e5def23bf28c108c
        source_sidecar.json sha256 d4e4df85143f88b724c838877cc27a36804dddd214d4ce8ce447062488d25b44 (= fork A dh36a/src25q sidecar)
Generator: src25q.py ROOT dh36a/src25q codex-head-start-0828/hk5_source/provider/start_stages.json OUT (tools d1ecb2c69dd).
Cause: src25p density taps (turn_b, 4 shims, hd_tile) and the src25n lep0N/st_n4 delta re-derive the reset relay trees
(relays renamed/moved), but reset_start_raw_exports rows + src25p type RTL kept the old trees: 32 of 171 rows in 8 types
(hd_lep0N, hd_spn_eshim_rx/tx, hd_spn_wshim_rx/tx, hd_st_n4, hd_tile, hd_turn_b) failed the reset_source_prep raw-Q fixed point.
(hd_mesh_e rst_start_raw_0/1/3 differ 0.032 um = COORD-approved M7 snap, same relay/Q: kept.)
Fix: each stale (type,port) re-sited on an actual new raw relay minimising the max hop to the START stages it feeds
(provider stage wiring and port names unchanged); a row that reused rst_o_k keeps rst_o_k. Export pins move with
their relay (per-row old/new + hop in src25q_report.json). Whole source regenerated as head_start_sources.
No outline, data pin, clock tap or cycle change (plan identical outside reset export rows + their rst_start_raw pins;
plan clock + every type clock identical -> ot_clk die clock result of src25p stands, not re-run).
Gates (CHECKED):
 fixed point 171/171 rows, 0 mismatch; max START reset hop 402.1 um (<=405, 0 over); raw relative span 68 (+4 <= SETTLE 74)
   (src25p had stale lep0N rst_start_raw_6 at 458.7 um; now 225.4).
 G0C --completeness: 2680 ERR, finding set identical to src25p g0c_final for errors (0 new, 0 gone); 2 core_pg WARN gone =
   src25p run lacked results/head_core_clockfreeze_release LEFs (env).
 Strict port bind (run_source_portbind.py, rev d1ecb2c69dd): HEAD_DIE_PORTBIND_SOURCE PASS, nested PASS (4427 instances).
 Kit gen (HEAD-KITS-U head_rekit_hk5m.py, main tools d1ecb2c69dd) rc 0 for all 10: hd_turn_b, hd_spn_eshim_rx, hd_spn_wshim_rx,
   hd_st_n4, hd_tile (the 5 that failed on src25p), hd_spn_eshim_tx, hd_spn_wshim_tx, hd_st_str, hd_st_n3_transit, hd_st_m.
Source RTL vs src25p also differs on hd_ctl/hd_host_n/hd_mesh_e/hd_spn/hd_spn_end only by ot_dp_landing_face status flops
that main clock_landings already emits (kits gen them anyway).
(b) hd_st_n3_turn band: main band tool (clock_landing_plan resize-bands) re-sizes 0 bands: u1_i band 206.0x45.36 = 9344 um2
 >= ring_ff reserve 4522 um2 (spread 2.07). PLACE failures are not band size: v3nofr DPL-0033 = 2 FIRM ring flops
 (u_cland_u1_i/u_ring.dch[0].u_dsel/y[30], dch[1]...y[34]) on TAPCELLs (3_5_place_dp.log); v3 FIT_RESERVE = no site for status
 flop u_cland_up_d1_o/fault_o (fixed window at top-margin pin y 602.144 > core 600.48). Both are landing_placement FLOW items.
