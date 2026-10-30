# DIE-S81-36/H2G1 rerun on main 4ce13fbc4 (FLOW-9 late-legalize fail-closed 006f0586c77 merged)
Date Fri Oct 30 13:32:07 PDT 2026. Same free-site tree + ONE qualified model as claude/die-s81-36-h2g1-1030@4967f87bfa5 (admitted slice/tcl unchanged,
late hook sha a676b4f7b55e identical), fresh copy of the native kit (3_place 56af214f), GEN/prep with main tools: prep PASS
(tcl regenerated exact), kit_preflight PASS. ONE G1: ot-run unit oth-ubuntu-154867-1793391750 exit 0, 4_cts.odb sha 096cf4b9d8cd...
(bit-identical to the pre-fix run).
- Late DPL: max_disp 0.000, and the new fail-closed check_placement inside ot_ci_late_legalize PASSED (no OT_CORE_INFRA_LATE_DPL_UNLEGAL).
- CLOCK-ONLY audit: PASS -- 1811/1811 tree cells exact (0 um) and FIRM, 0 master/orient mismatch, 19747/19747 sinks on planned
  nets, 0 unplanned clock drivers, ck[0] native M5 pin.
- POST-REPAIR audit (kit POST_CTS repair_timing -setup, data side, not disabled): FAIL by the strict no-change rule -- 43 non-tree
  rebuffers added, 1 removed, 45 pre-existing cells moved incl the SAME 4 FFs (u_ep.g_rb_safe.u_m.g_slice[16].addr_r[5],
  g_slice[66].hi_r, u_gb.bg[89], u_gb.bg[90]); post-repair check_placement PASS. Placement-RC WNS -267.842 / 88 viol at
  u_ep.g_rb_safe.g_address[1].ready_r D (UNCHECKED, data path). OT_TAP_RC 230..298 ps (UNCHECKED).
No GRT/DRT/G2. Run dir intel2 /srv/opentallas-scratch2/claude/die-s81-36/h2g1m (kit kept for any authorised G2).
