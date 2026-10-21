# p4l3 strict bind + real-view die case (S81-DIE8, 10-18 18:15)

Branch claude/s81-die7-1018 = die7 + S81-LBGAP g3 5cb5cddc3 + g2 3eee44b8d + g1 3dca1f9fb + closed landing/crs4 view
records (codex/closure-record-s81dv_land_{70,276l,276,562,682,pvrd}-*, s81coll_cfifo_crs4-c4a-f11bb1950) + origin/main.

1. `python3 tools/s81_dv/dv_diecase.py --plan results/arch/s81_dv_1016/p4l/plan.json --out <S>/bind12 --bind real --bind-table results/arch/s81_dv_1016/bind/bind_table_p4l3.json`
   (4:48, 400 MB). Strict DIE_PORT_BIND **PASS**: 40 masters / 8,391 inst, ambiguous_children 0 (bind table rtl_files now
   names ot_s81ph_coll_lane.sv + rtl/hdc/v41/ot_hdc_fsqrt.sv: main's variant files made 4 children ambiguous), 276 landings
   (all with E), 276 hop-0 ICGx4 lane gates (G1), 714 gate-calendar stations, frame contract PASS. die.v sha256 4b218f66...
2. `python3 tools/s81_dv/dv_rvcase.py --plan .../p4l/plan.json --bind-dir <S>/bind12/bind --bind-table .../bind_table_p4l3.json --land-plan .../landing/p4l2/land_plan.json --out <S>/case_p4l3_rv --view-refs b3e070f59 origin/main --pin-window 3 --die-repair`
   -> rv_case.json: 7,909 closed-view inst / 190 stand-ins / 292 std cells. NOT_A_DIE_RESULT label until the stand-ins close.
   CLOSED views bound: dsdv_bk_col (s81dvbk_colv), dsfd_dvland_70/276/276l/562/682/pvrd (268 landings), 14 dsfd_dvrlyh_*, dsfd_rly_1_WN.
   Stand-ins (views still owed): col_h9_l4 / col_h10_l4 / col_h9_MX_l4 frames (122), dsdv_svc_rs (14) + _entry (2), dsdv_gunit,
   dsdv_seq_host, dsdv_bk_sel, dsfd_ctrl_rg2 (16), dsfd_dvland_512 (8, no kit yet), ot_s81sl_slice (12) / _lepw (2) / _lepe / _lepe_nh;
   modelled PHY: ot_pdie_serdes (8), ot_hbm3e_phy_v41x_aw30_e8p5.
   Leaf views closed inside stand-in parents (s81sl_vn fa3312cfc, s81sl_vs prs1 e7a55f1e1, qxpq RSTP 2bded98f0, crs4, svc_sx_hrow,
   bk cl/cm/g2/selc2) bind when their parent / frame / slice hardens -- the die does not bind leaves directly.
3. dv_rvcase fix (b3e070f59): die repeater step before create_clock. The 07:10 chain case_p4l_rv died at the repeater step:
   fclk_mismatch_hops 108, every hop-0 forwarded clock had 0 repeaters (STA clock net through the forward cell ->
   repair_design skipped it although repeat_nets un-skipped it).
