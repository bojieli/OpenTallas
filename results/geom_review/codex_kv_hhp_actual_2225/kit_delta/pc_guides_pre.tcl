source /work/face_flops.tcl
set ot_zone_spec {
  pc0 {g_pc\[0\][./]u_pc[./]} 86.4 198.72 483.84 561.6
  pc1 {g_pc\[1\][./]u_pc[./]} 552.96 198.72 950.4 561.6
  pc2 {g_pc\[2\][./]u_pc[./]} 552.96 959.04 950.4 1321.92
  pc3 {g_pc\[3\][./]u_pc[./]} 86.4 959.04 483.84 1321.92
}
set ot_zone_members_spec $ot_zone_spec
lappend ot_zone_members_spec ctl {^[^_].*[./]} 0 0 1036.8 1520.64
source /work/zone_fence.tcl
