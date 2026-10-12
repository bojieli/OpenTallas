# dsfd_mtp_hrow rev 3: 30 hardened banks u_st.g_part[p].g_q[q].g_b[k].g_on.u_bk, part p -> columns 2p + k, pair q -> row 4 - q
# (pair 0 beside the N band). column pitch 496.8 = 46 x 10.8 (bank x origins on the 10.8 um M7 PG lattice so the view grid
# M7 stripes land on every bank M7 PG pin; 34.56 um column channel), row pitch 345.6 = 160 x 2.16 (142.56 um row channel; outline grown to 1769.04 for <= 55% util).
# names are matched with the escape characters removed (ODB may store u_st.g_part\[0\]... from the escaped Verilog
# identifier, MPL-0020 on the literal name): place each bank by odb, FIRM, at the exact origin
set ot_blk [ord::get_db_block]; set ot_dbu [$ot_blk getDbUnitsPerMicron]; set ot_bk [dict create]
foreach ot_i [$ot_blk getInsts] { if {[[$ot_i getMaster] getName] eq "dsfd_mtp_hrow_bank"} { dict set ot_bk [string map {"\\" ""} [$ot_i getName]] $ot_i } }
if {[dict size $ot_bk] != 30} { error "hrow macro placement: [dict size $ot_bk] banks found, 30 expected" }
proc ot_pbk {k x y o} { global ot_bk ot_dbu; if {![dict exists $ot_bk $k]} { error "hrow macro placement: no bank $k" }
  set i [dict get $ot_bk $k]; $i setOrient $o; $i setLocation [expr {round($x * $ot_dbu)}] [expr {round($y * $ot_dbu)}]; $i setPlacementStatus FIRM }
ot_pbk {u_st.g_part[0].g_q[0].g_b[0].g_on.u_bk} 21.6 1412.64 R0
ot_pbk {u_st.g_part[0].g_q[0].g_b[1].g_on.u_bk} 518.4 1412.64 R0
ot_pbk {u_st.g_part[0].g_q[1].g_b[0].g_on.u_bk} 21.6 1067.04 R0
ot_pbk {u_st.g_part[0].g_q[1].g_b[1].g_on.u_bk} 518.4 1067.04 R0
ot_pbk {u_st.g_part[0].g_q[2].g_b[0].g_on.u_bk} 21.6 721.44 R0
ot_pbk {u_st.g_part[0].g_q[2].g_b[1].g_on.u_bk} 518.4 721.44 R0
ot_pbk {u_st.g_part[0].g_q[3].g_b[0].g_on.u_bk} 21.6 375.84 R0
ot_pbk {u_st.g_part[0].g_q[3].g_b[1].g_on.u_bk} 518.4 375.84 R0
ot_pbk {u_st.g_part[0].g_q[4].g_b[0].g_on.u_bk} 21.6 30.24 R0
ot_pbk {u_st.g_part[0].g_q[4].g_b[1].g_on.u_bk} 518.4 30.24 R0
ot_pbk {u_st.g_part[1].g_q[0].g_b[0].g_on.u_bk} 1015.2 1412.64 R0
ot_pbk {u_st.g_part[1].g_q[0].g_b[1].g_on.u_bk} 1512.0 1412.64 R0
ot_pbk {u_st.g_part[1].g_q[1].g_b[0].g_on.u_bk} 1015.2 1067.04 R0
ot_pbk {u_st.g_part[1].g_q[1].g_b[1].g_on.u_bk} 1512.0 1067.04 R0
ot_pbk {u_st.g_part[1].g_q[2].g_b[0].g_on.u_bk} 1015.2 721.44 R0
ot_pbk {u_st.g_part[1].g_q[2].g_b[1].g_on.u_bk} 1512.0 721.44 R0
ot_pbk {u_st.g_part[1].g_q[3].g_b[0].g_on.u_bk} 1015.2 375.84 R0
ot_pbk {u_st.g_part[1].g_q[3].g_b[1].g_on.u_bk} 1512.0 375.84 R0
ot_pbk {u_st.g_part[1].g_q[4].g_b[0].g_on.u_bk} 1015.2 30.24 R0
ot_pbk {u_st.g_part[1].g_q[4].g_b[1].g_on.u_bk} 1512.0 30.24 R0
ot_pbk {u_st.g_part[2].g_q[0].g_b[0].g_on.u_bk} 2008.8 1412.64 R0
ot_pbk {u_st.g_part[2].g_q[0].g_b[1].g_on.u_bk} 2505.6 1412.64 R0
ot_pbk {u_st.g_part[2].g_q[1].g_b[0].g_on.u_bk} 2008.8 1067.04 R0
ot_pbk {u_st.g_part[2].g_q[1].g_b[1].g_on.u_bk} 2505.6 1067.04 R0
ot_pbk {u_st.g_part[2].g_q[2].g_b[0].g_on.u_bk} 2008.8 721.44 R0
ot_pbk {u_st.g_part[2].g_q[2].g_b[1].g_on.u_bk} 2505.6 721.44 R0
ot_pbk {u_st.g_part[2].g_q[3].g_b[0].g_on.u_bk} 2008.8 375.84 R0
ot_pbk {u_st.g_part[2].g_q[3].g_b[1].g_on.u_bk} 2505.6 375.84 R0
ot_pbk {u_st.g_part[2].g_q[4].g_b[0].g_on.u_bk} 2008.8 30.24 R0
ot_pbk {u_st.g_part[2].g_q[4].g_b[1].g_on.u_bk} 2505.6 30.24 R0
