# HEAD-TYPES-R4 handoff (Sonnet), successor of HEAD-R3. Started 2026-11-17 06:4x PST.
- Unsigned HEAD types (plan l48uo, 26): hd_serdes (sd9f route), hd_lep0N, hd_mesh (both wait on the NF15f geometry event, see HEAD-R3.md). hd_ctl + hd_st_n3_turn signed by R3.
- sd9f: DRT done 28 DRC = 19 M7 Short + 9 M2 Metal Spacing, all on clk_t*/clk_t*_tb0_n* tap nets (+3 u_rrl/net60340). 5_2_route.odb written 14:47 UTC; kit still finishing + signoff (E7 unit3729170).
  Class = he12h drc2: reserved die-clock-site M7 obstructions over type clock-tap BTerm pins. Fix recipe E9 fable-fix-head-timing/he12h_drc2/hd_host_e/{eco_geom.py,eco_route.tcl,eco_guides.py,eco_drt.tcl}.
- Diagnosis output: E7 head-types-r4/diag_drc.out
