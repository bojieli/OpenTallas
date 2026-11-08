# DIE-S81-80 bf gf3 (COORD 06:07 ruling: u_m0 W / u_m1 E): face flops first (unchanged), then two GPL guide zones keyed by
# endpoint registers: M0 = the new u_m0 -> u_m1 register c1r (u_m0 cone follows it backward), M1 = the bf output registers
# (u_m1 cone + output mux). Everything else stays free (zone_members "ctl"). Released before DPL (pre_dpl_zone.tcl).
source /work/face_flops.tcl
set ::ot_zone_spec {M0 {^c1r(\[|\$)} 2.16 2.16 280.8 170.64 M1 {^o_(d|v|f|l|g|flt)(\[|\$)} 280.8 2.16 429.84 170.64}
source /work/zone_fence.tcl
