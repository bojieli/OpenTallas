S81-BKSEL-2 (DIE-S81-87 fork) 11-12: dsdv_bksel_q vC5 GRT-0232 (P-east channel) -> structural form vC6.
Evidence (vC5 congestion-20.rpt, 44 markers): 26 V markers x 368-400 y 393-397 (strip east of P, P east edge 367.2, 128x256 SRAM column x 414.72 => 47.5 um strip),
8 at x 412-417 (V cap 4, SRAM west pin GCells), rest P top-left y 399 / bank col 4. West strip P west edge 172.8 to 32x128 column east edge ~74 = 98.6 um, blue in density.png.
Form vC6: macro_place.tcl P x 172.8 -> 144.0 (1000 x 0.144). East strip 76.3 (+60%), west 69.8. Same RTL/HLAT/clock form; synth + 2_1 floorplan reused, flow from 2_2.
Fallback vC5c: vC5 3_*/4_1_cts reused, GLOBAL_ROUTE_ARGS = -congestion_report_iter_step 5 -verbose -allow_congestion (resumes at GRT).
Run: epyc7 /srv/opentallas-scratch2/claude/die-s81-85/bksel_vC6 unit oth-ubuntu-3183822-1794498528 (docker ds85-bkselC5-run-3193480); bksel_vC5c unit oth-ubuntu-3290476-1794498645 (docker ds85-bkselC5-run-3299722).
