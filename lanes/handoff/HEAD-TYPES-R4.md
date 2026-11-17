# HEAD-TYPES-R4 handoff (Sonnet), successor of HEAD-R3. Started 2026-11-17 06:4x PST.
- Unsigned HEAD types (plan l48uo, 26): hd_serdes (sd9f route), hd_lep0N, hd_mesh (both wait on the NF15f geometry event, see HEAD-R3.md). hd_ctl + hd_st_n3_turn signed by R3.
- sd9f: DRT done 28 DRC = 19 M7 Short + 9 M2 Metal Spacing, all on clk_t*/clk_t*_tb0_n* tap nets (+3 u_rrl/net60340). 5_2_route.odb written 14:47 UTC; kit still finishing + signoff (E7 unit3729170).
  Class = he12h drc2: reserved die-clock-site M7 obstructions over type clock-tap BTerm pins. Fix recipe E9 fable-fix-head-timing/he12h_drc2/hd_host_e/{eco_geom.py,eco_route.tcl,eco_guides.py,eco_drt.tcl}.
- Diagnosis output: E7 head-types-r4/diag_drc.out
- Cause (diag E7 head-types-r4/diag_drc.out): 19 M7 Shorts = reserved die-clock-site M7 obstructions sit on the type clock-tap BTerm pins (clk_t*, clk); 9 M2 spacing = cells (clk_t*_tb0_d*, u_rrl, hold buf) abutting the site edge (pin access). Same two classes as he12h drc2.
- ECO LIVE: E7 head-types-r4/sd9f_eco/run_eco.sh (client log intel2 ~/head-types-r4-logs/sd9f_eco.log): M7 carve 27 obstructions, 3-site pad at marker sites, DPL moved 41 cells, ripped 111 nets, guides + incremental DRT, then fill/final/signoff_r4eco. Original route kept: gen/hd_serdes (kit signoff still running).
- hd_lep0N / hd_mesh: both need the NF15f geometry event (R3 handoff Not-done 1); not started by R4.
