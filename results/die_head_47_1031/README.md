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

## Routed die clock regions + HEAD die STA 12.25 (COORD order, 10-31 03:0x)
- DRT (end_iter 6) + OpenRCX on the crops of the 3 worst record regions tW3b5/tW1o1/tW1o8 (l46aa405 die clock incl. tree
  feed): routed/HPWL total 1.002/1.005/1.005 (p90 <= 1.026); region spread routed TT 85.7/99.3/104.5 vs GRT 116.7/116.4/114.7
  (`l47k/routed_regions_summary.json`, `len.py`, `summ.py`). Delta method (crop routed RCX - crop GRT, same crop) added to the
  record taps (`subst.py`, `routed_subst.json`). RCX: platform rules = the 12.24 optimistic set here (no clock NDR on these
  routes, rpersq_opt credit 1.0 on every layer).
- die_sta_related (FLOW-13, nominal, CPPR-LCA, both edges, HB4, core views, --ca-ring hd_tile, count-aligned bind):
  l47 TT setup +145.80 / seam +537.25 (0 neg); FF hold BLOCKED(kits) (0/23 HEAD types signed); CA 11/427 below need
  (sp1->sp2 slot_read -53.5) (`die_sta_l47_summary.txt`).

## l47k = l47 + count-aligned K re-plan on the record die clock (COORD 03:0x: ASK option A APPROVED, +1 cycle accepted)
- Root cause: the bind K (hk5_leaf2, 08-28) was planned on the hk5 leaf clock; the record die clock moves sp2/sp4/lep0N
  capture taps earlier (sp1->sp2 d_lo -945.8 plan vs -1230.7 measured).
- count_align_plan --sta-proof on the record routed proof (`replan_run.sh`, nominal 12.24b, FF 342): all 427 crossings
  pass (worst lo 139.4); lat 3 -> 4 on exactly 11 ports, every other port unchanged. Its start tree is NOT adopted (no
  START loads on the record clock), so `l47k/make_l47k.py` applies K+1 in the hk5_leaf2 frame: parent strap ties only
  (tie = K - R + W, count_align_bind.strap_ties) on sp2 (ad/bd/hd/x), sp4 (au/b/bu/hu), lep0N (coll_i1/i2),
  sp2_bw_i_shim (link_i) + sidecar count_aligned K/sched_lat (`top_diff_l47_l47k.txt`, `l47k_delta.json`).
- Die STA with bind_l47k: CA 0/427 fail, worst lo TT +140.8 / FF +176.3; setup unchanged (`die_sta_l47k_summary.txt`).
- G0C (main 8ce125d6a98 check.py --completeness --landing): l47 1 err / l47k 1 err, 0 new / 0 gone.
- Strict bind (run_source_portbind.py, main 8ce125d6a98): PASS, TIE_AUDIT 1669/0, nested 6111.
- Strap LEC (strap_lec.py --mutant): hd_spn_wshim_rx 5/5 variants EQUIVALENT, mutant caught; hd_lep0N see lane log;
  hd_spn: tool refuses writer_start types (gold parameter form unsupported) -> tie audit is the check there.
- No block RTL / kit change: strap pins are inputs of the signed/kitted masters.
