# qfd_tt_ctlm_dv_safe10a -- QKC-CTLM 10-21: Q.STA.TTC.4 CTLM CALR successor, structural fixes of the safe9c/9co/9cb gate FAIL

Base = safe9c (lp9d_npl netlist, CALR=1 + F16WTN=1 + TABLE_REL, h16c u_hr + closed wtn, 6 SRAM + 3 OPROM + 2 ROM266), unchanged RTL.
Parallel set safe10a (+86.4) / safe10b (+129.6): bind first to close, cancel the other. Not a critical tile.

## safe9c gate FAIL (scratch/qw-ttc9/gate_safe9c.log, 9co, 9cb)
1 textbook.wire_reach 75 stages = pw[74:0]: S pins x333.8 -> u_gi.g_wtn.u_wtn/pw (W face, x648 y409-454) 732-752 um unregistered.
2 clock_rule: ck_core TT/FF pin-flop spread 241/215 (9co 195/180), ck_hr 217/183 (9co 340/303); late S pin-band strips under the
  macro rows (safe8u per-register dump: ck_core S strip 935-1043 vs NE 810-850; ck_hr strip under u_hr 640-752 vs 500-530).
3 9cb (8bu outline): GPL-0305 divergence. Dropped.

## Fixes (structural, no RTL change)
1 pw[74:0] -> N face x540.0..556.0 (M3 0.216; free N gap x530-600) beside the wtn W face: pin -> wtn pw ~330 um (< 405).
2 Every macro row and both children raised by 86.4 um (outline 777.6 x 648 -> 777.6 x 734.4): the S pin band becomes a 129.6 um
  std-cell band so the S pin flops get CTS buffer room instead of a 43 um strip under the SRAM/h16c rows. E pins move with the
  rows (y += 86.4); N/S pins keep x. Region boxes (lp_cone_regions.tcl) raised by the same amount. CTS unclustered (9c form).

## SAFE checklist
1 pins: landed record unchanged; pw moved next to its consumer; faces <= ~4.4 pins/um | 2 reach: pw fixed (was the only reach FAIL)
3 fanout: lp9d native32 max 32 | 4 depth 743.5 ps / 24 lv WARN (unchanged netlist; rule-freeze guidance) | 5 storage: all macros,
on the 43.2 lattice | 6 floorplan: fill 45 %, std density ~4 % | 7 clock: regional ck_core/ck_hr + L5 landings; S band widened
| 8 reset: lp regional reset runs (unchanged).
Die: slot_change_request in spec.json (TTC.3 GEN re-slots). Head h16c stays until h16yb closes (then a head-rebind successor).
