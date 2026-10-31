# DIE-HEAD-47 (HEAD die owner), 2026-10-31

## l47 = l46a + value-only FF insertion bound (OWNER 12.20 one-block fix class; no pin/RTL/geometry/tree change)
- Root cause (DIE-HEAD-46 22:18 FINDING): plan `clock.insertion_ff_ps` 380 is the 'parent_budget ... publish actual routed mean'
  placeholder; the post-CTS gate binds the kit FF pin-register mean to it (tol 20). Measured FF/TT = 0.757-0.765
  (hd_spn_wshim_rx 321.29/419.73, hd_mesh_e 342.67/452.60, hd_st_m 336.79/444.87, GRT pin-register means), so FF 380 fails
  every kit that meets TT 450.
- Edit (`l47/make_l47.py`, reproducible from main results/die_head_46_1030/l46/source_plan_l46a.json.gz):
  insertion_ff_ps 380 -> 342.0 (0.76 x 450) + insertion_basis on 21 types (hd_tile, hd_turn_a/b, hd_spn, hd_spn_end,
  hd_st_turn/str/n4/k5/n3_transit/n3_turn, hd_mesh, hd_ctl, hd_host, hd_spn_wshim_rx/tx, hd_spn_eshim_rx/tx, hd_ctl_n/e,
  hd_host_n). NOT touched: hd_lep0N (signed ECO7, LEC running), hd_serdes (Codex ECO1B in flight), hd_st_m / hd_mesh_e
  (already measured), die-level clock.insertion_ff_ps.
- source_plan sha256 b87c81920f4c5dd23a0f67033f857bbe3adb2267c3cb7923144c81c8ce7a4341 (l46a bd1dd9ff3e30); sidecar = l46a.
- G0C (check.py --completeness, main e71ad1fda tools on the event copy): l46a 1 err / l47 1 err, 0 new / 0 gone (g0c_*.json).
- Die clock: ot_clk kit on l47 = byte-identical to l46aa405 (tree.json 0100fe6f26dd, ctree.v 40ce36ee1cc1, ctree.tcl,
  grt/route.v, grt/obs.tcl); ot_clk does not read insertion_ff_ps, so the die clock numbers of l46aa405 stand.
- Strict bind: no port/pin/RTL change (plan diff = the 42 values above only) -> l46a strict bind PASS stands.
- Known left: hd_spn_wshim_rx still misses the TT bound (419.73 vs 450, clk_t12 tree) -> its own tap fix (successor).
