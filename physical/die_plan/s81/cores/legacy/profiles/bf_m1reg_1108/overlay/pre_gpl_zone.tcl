# DIE-S81-80 bf gf3 (COORD 06:07 ruling: u_m0 W / u_m1 E): face flops first (unchanged), then two GPL guide zones keyed by
# endpoint registers: M0 = the new u_m0 -> u_m1 register c1r (u_m0 cone follows it backward), M1 = the bf output registers
# (u_m1 cone + output mux). Everything else stays free (zone_members "ctl"). Released before DPL (pre_dpl_zone.tcl).
# try3 fix: boxes tiled the whole core -> top-level region had no free area (GPL-0019 -301%, GPL-0305 diverged); 20-um central gap x250-270 for the unfenced remainder.
source /work/face_flops.tcl
set ::ot_zone_spec {M0 {^c1r(\\?\[|\$)} 2.16 2.16 210.0 170.64 M1 {^o_(d|v|f|l|g|flt)(\\?\[|\$)} 230.0 2.16 429.84 170.64}
source /work/zone_fence.tcl
# try4 fix: M1 region util 41.2% > PLACE_DENSITY 0.40 (infeasible, GPL-0305); M1 x230-430 -> ~33% (load 10673 um2 / ~32360 um2), M0 x2-210, gap 210-230.
