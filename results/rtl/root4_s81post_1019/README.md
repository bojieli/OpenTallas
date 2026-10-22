# ROOT4-S81POST receipts (10-19): closures touched by the S81-SMWIRE merge (main 0408184bd)
Fleet ot-epyc5; yosys 0.68; Verilator 5.050.  Tool: tools/s81_slice/rtl_equiv.sh (sequential RTL equivalence).
- ot_s81sl_xr1 (closed s81sl_xr1f-12b616b54, FOREG 1): closed source vs main EQUIV_PROVEN (22,867 cells, 0 unproven; FOREG 0
  too) -> closure stands; receipt results/closure_loop/s81sl_xr1f-s81sl_xr1f-12b616b54/equiv_receipt_0408184bd.json.
- 14 closed dsfd_dvrlyh_* relays (bound in mu5; dsfd_rly_masters_dvh.sv only gained 3 new masters): all EQUIV_PROVEN
  (equiv/relay_receipt_0408184bd.json).
- dsfd_dvland_pvrd (closed p3-b15a4ddad, bound in mu5): EQUIV_NOT_PROVEN (39: SO bypass, a real logic change) -> re-kit p4
  (reroute_reason rtl_change, reset_landing 2 -> bind table landing_reset_stages {dsfd_dvland_pvrd: 2} owed when p4 binds).
- No closed view exists for ot_s81sl_xr3 / rstop / ot_s81ph_coll_lane / slice* / lep* (all stand-ins inside the mu5
  ot_s81sl_slice stand-in); ot_hbm3e_phy_v41x_aw30_e8p5_k.sv is a new behavioural PHY-macro RTL (memory-macro abstract).
- xr3 SAFE item 3: so_lo / so_hi capture enables (512 loads each) -> KEPT copies sol_c / soh_c (64 + 64) over staged so_w;
  flow keep hook (ot_keep_regs.tcl) keeps 64/64 + 64/64 on the paramod (keep3.stdout).  e2e base PASS route 1 / 2 with
  latencies 16/18/18 and 22 = the merge's (0 cycles), bench mutants FAIL, TARGET_MUT CAUGHT (e2e_base/); RTL mutant
  OT_S81SL_XR_MUT_SOEN FAILs (witness/e2e_soen); xr_bench HB0 / HB1 / FOREG PASS; HB1 mutants FAIL (witness/xr3_*).
