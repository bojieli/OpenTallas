KV-PLAN-DELTA hm_r26q3 (CLOCK-KV lane, 2026-10-27). One event on hm_r26q2 1d257518 -> hm_r26q3 256600e2.
Real-copy plan dir: intel2:/srv/opentallas-scratch2/claude/kv-plan-q3-1027/pd (plan.sha256, cores.sha256 73 files, 0 symlinks).
Delta script q3_delta.py (asserts everything below). Event source plan = codex/kv-clock-1027@3cb5395c6 die_plan.json f1daa8ad.
(a) D-KV-STRAP-FORM: e1/e5 strap_bsel[0..1] y 216.000 -> 215.904 (x/layer unchanged), new cores/kv3_head_eighth_{e1,e5}_pins_r26q3.json,
    136 hard_core entries repointed. e0/e2/e6 strap_bsel (W face M4 x=0) and e2_on_e6/e6 strap_hid (N y=216) are alone on
    their face -> one form, unchanged (keeps e2/e6 rows valid). canon pins (die_sta_related.canon_pins):
    e1 38dbd436 -> 56143cef391cca24143de85c80675e74dca755816d1547f7dc421d2c735a13dd
    e5 6ee6e53d -> 5d6b0e8bab43a19be2e86376366518201935df71ad2bd8c5d480b0ca84904e89
(b) D-KV-ISLAND-ROWS: all 12 island_ft arcs of 7 pin views (pv_pair R0/fMX, kvs_pc R0/fMX, h_head_p fMY, ectlk_q0/q2) are
    already on the kit row (0.27 from 4.32) / site (0.054) grid in R0/MX/MY/R180 images -> 0 moves (max 0.000 um).
    ROOT CAUSE of KV-CORES-R8 OT_ISLAND_FT_NO_ROW (pv_pair R0): rtl_macro_placer (free RTLMP, plan gives no macro
    placement/keepout) put SRAM u_s0.g_mem[1] at [68.688,122.076,120.096,142.866] over island cells [107.46..110.7,138.24];
    tapcell cut rows 496 to x<=66.636 / x>=122.148. fMX RTLMP put all SRAMs at y>=144.1 -> row intact -> PASS. Same rect,
    same row; the plan is not the defect. Kit fix (KV-CORES): make clock.mesh.core_islands rects (+halo) macro blockages
    before rtl_macro_placer, or stage MACRO_PLACEMENT_TCL. render pv_pair_islands_q3.png (VIEWED).
(c) D-KV-FT-SLOTS-GRAFT (COORD 11:03): event ft_slots for 46 types (933 slots: stations +205, regs_um/bit_sites_um/
    bit_site_cell_um) + latency.lanes 130 rows (+210 cycles, stations/natural/cycles only). kv3_hub_Ei: event counts kept,
    sites dropped (ft_corridor re-site = separate item). NOT taken: event hard_cores (pv_join 259.2 outline + pin files,
    ectlk_q1/q2, kvs_ctl pin files), clock, reset, PG, SD contents, kv3_pv_v12 internal_stations move (PV). Graft touches
    no hard_core pin table/outline (asserted) -> nothing had to wait.
G0 checks added (tools/die_plan/check.py): core_pin_form (one face = one pin form, edge d=0 or centre 0<d<0.5) and
island_ft_rows (rect n x cell on one row/site of the kit core area in all 4 images, cells in clock.mesh.core_islands, ports
M5-track pins on the row). Unit tests test_island_ft_rows_pin_form.py 6 PASS (mutants caught). hm_r26q2 with the new
checker: 1 ERROR (core_pin_form e1 N strap_bsel) -> hm_r26q3: G0 PASS 0E/1851W, G0C PASS 0E/1851W, finding set identical
to the q2 baseline (0 added / 0 removed).
