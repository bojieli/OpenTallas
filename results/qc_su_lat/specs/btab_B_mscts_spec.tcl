# QC-SU-LAT variant B (2026-10-26): split W/E band trunks (W x=106, E x=255), legs <=~35 um; derived from /srv/opentallas-scratch2/claude/path-qc-sramif4/btab_fh_s40/mscts_spec.tcl
# PATH-QC-SRAMIF3 2026-10-25 btab variant F + GEOM (b') per-row BAND clock (GEOM-REVIEW [PATH-QC-SRAMIF2-F-POSTCTS] 20:13/20:30/20:31):
# each SRAM row k: band trunk root -> W-column channel point (106.0, y_ch[k]) (NOT to x177: no vertical channel there, 20:30 correction),
# ONE branch node there, three matched legs (same cell chain): W (W-edge wd + banded write stage), M (macro CK leaf), E (E-edge IF + read capture + banded write stage).
# S taps unchanged; P tap = E-face pin registers (x>300). MACRO_EARLY 0. Needs cf/mscts_band.tcl.
set ot_ms_port ck
set ot_ms_root {177.132 6}
set ot_ms_taps {
 {S0 {177.132000 6 44.280000 6 44.280000 16} {{0.000000 0 88.560000 25.92}}}
 {S1 {177.132000 6 132.840000 6 132.840000 16} {{88.560000 0 177.120000 25.92}}}
 {S2 {177.132000 6 221.400000 6 221.400000 16} {{177.120000 0 265.680000 25.92}}}
 {S3 {177.132000 6 309.960000 6 309.960000 16} {{265.680000 0 354.240000 25.92}}}
 {P0 {177.132 6 330.0 6 330.0 130.0} {{300.0 25.92 354.24 259.2}}}
}
set ot_ms_bands {
 {B0W {177.132 6 106 6 106 25.0}}
 {B0E {177.132 6 255 6 255 25.0}}
 {B1W {177.132 6 106 6 106 79.0}}
 {B1E {177.132 6 255 6 255 79.0}}
 {B2W {177.132 6 106 6 106 135.0}}
 {B2E {177.132 6 255 6 255 135.0}}
 {B3W {177.132 6 106 6 106 191.0}}
 {B3E {177.132 6 255 6 255 191.0}}
}
set ot_ms_legs {
 {R0W B0W {106 25.0 114.0 25.0 114.0 38.24} {{0.0 25.92 125.28 79.2}}}
 {R0M B0E {255 25.0 231.424 25.0 231.424 31.24} MACRO}
 {R0E B0E {255 25.0 245.0 25.0 245.0 50.24} {{224.42 25.92 300.0 79.2}}}
 {R1W B1W {106 79.0 114.0 79.0 114.0 94.40} {{0.0 79.2 125.28 135.36}}}
 {R1M B1E {255 79.0 231.424 79.0 231.424 87.40} MACRO}
 {R1E B1E {255 79.0 245.0 79.0 245.0 106.40} {{224.42 79.2 300.0 135.36}}}
 {R2W B2W {106 135.0 114.0 135.0 114.0 150.56} {{0.0 135.36 125.28 191.52}}}
 {R2M B2E {255 135.0 231.424 135.0 231.424 143.56} MACRO}
 {R2E B2E {255 135.0 245.0 135.0 245.0 162.56} {{224.42 135.36 300.0 191.52}}}
 {R3W B3W {106 191.0 114.0 191.0 114.0 206.72} {{0.0 191.52 125.28 259.2}}}
 {R3M B3E {255 191.0 231.424 191.0 231.424 199.72} MACRO}
 {R3E B3E {255 191.0 245.0 191.0 245.0 218.72} {{224.42 191.52 300.0 259.2}}}
}
set ot_ms_macros {
 {g_btb*0*.u_m R0M {231.424 31.24}}
 {g_btb*1*.u_m R1M {231.424 87.40}}
 {g_btb*2*.u_m R2M {231.424 143.56}}
 {g_btb*3*.u_m R3M {231.424 199.72}}
}
