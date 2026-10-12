# dsfd_mtp_hrow rev 3: 30 hardened banks u_st.g_part[p].g_q[q].g_b[k].g_on.u_bk, part p -> columns 2p + k, pair q -> row 4 - q
# (pair 0 beside the N band). column pitch 496.8 = 46 x 10.8 (bank x origins on the 10.8 um M7 PG lattice so the view grid
# M7 stripes land on every bank M7 PG pin; 34.56 um column channel), row pitch 263.52 (60.48 um row channel).
# names are matched with the escape characters removed (ODB may store u_st.g_part\[0\]... from the escaped Verilog
# identifier, MPL-0020 on the literal name): place each bank by odb, FIRM, at the exact origin
set ot_blk [ord::get_db_block]; set ot_dbu [$ot_blk getDbUnitsPerMicron]; set ot_bk [dict create]
foreach ot_i [$ot_blk getInsts] { if {[[$ot_i getMaster] getName] eq "dsfd_mtp_hrow_bank"} { dict set ot_bk [string map {"\\" ""} [$ot_i getName]] $ot_i } }
if {[dict size $ot_bk] != 30} { error "hrow macro placement: [dict size $ot_bk] banks found, 30 expected" }
proc ot_pbk {k x y o} { global ot_bk ot_dbu; if {![dict exists $ot_bk $k]} { error "hrow macro placement: no bank $k" }
  set i [dict get $ot_bk $k]; $i setOrient $o; $i setLocation [expr {round($x * $ot_dbu)}] [expr {round($y * $ot_dbu)}]; $i setPlacementStatus FIRM }
ot_pbk {u_st.g_part[0].g_q[0].g_b[0].g_on.u_bk} 21.6 1084.32 R0
ot_pbk {u_st.g_part[0].g_q[0].g_b[1].g_on.u_bk} 518.4 1084.32 R0
ot_pbk {u_st.g_part[0].g_q[1].g_b[0].g_on.u_bk} 21.6 820.8 R0
ot_pbk {u_st.g_part[0].g_q[1].g_b[1].g_on.u_bk} 518.4 820.8 R0
ot_pbk {u_st.g_part[0].g_q[2].g_b[0].g_on.u_bk} 21.6 557.28 R0
ot_pbk {u_st.g_part[0].g_q[2].g_b[1].g_on.u_bk} 518.4 557.28 R0
ot_pbk {u_st.g_part[0].g_q[3].g_b[0].g_on.u_bk} 21.6 293.76 R0
ot_pbk {u_st.g_part[0].g_q[3].g_b[1].g_on.u_bk} 518.4 293.76 R0
ot_pbk {u_st.g_part[0].g_q[4].g_b[0].g_on.u_bk} 21.6 30.24 R0
ot_pbk {u_st.g_part[0].g_q[4].g_b[1].g_on.u_bk} 518.4 30.24 R0
ot_pbk {u_st.g_part[1].g_q[0].g_b[0].g_on.u_bk} 1015.2 1084.32 R0
ot_pbk {u_st.g_part[1].g_q[0].g_b[1].g_on.u_bk} 1512.0 1084.32 R0
ot_pbk {u_st.g_part[1].g_q[1].g_b[0].g_on.u_bk} 1015.2 820.8 R0
ot_pbk {u_st.g_part[1].g_q[1].g_b[1].g_on.u_bk} 1512.0 820.8 R0
ot_pbk {u_st.g_part[1].g_q[2].g_b[0].g_on.u_bk} 1015.2 557.28 R0
ot_pbk {u_st.g_part[1].g_q[2].g_b[1].g_on.u_bk} 1512.0 557.28 R0
ot_pbk {u_st.g_part[1].g_q[3].g_b[0].g_on.u_bk} 1015.2 293.76 R0
ot_pbk {u_st.g_part[1].g_q[3].g_b[1].g_on.u_bk} 1512.0 293.76 R0
ot_pbk {u_st.g_part[1].g_q[4].g_b[0].g_on.u_bk} 1015.2 30.24 R0
ot_pbk {u_st.g_part[1].g_q[4].g_b[1].g_on.u_bk} 1512.0 30.24 R0
ot_pbk {u_st.g_part[2].g_q[0].g_b[0].g_on.u_bk} 2008.8 1084.32 R0
ot_pbk {u_st.g_part[2].g_q[0].g_b[1].g_on.u_bk} 2505.6 1084.32 R0
ot_pbk {u_st.g_part[2].g_q[1].g_b[0].g_on.u_bk} 2008.8 820.8 R0
ot_pbk {u_st.g_part[2].g_q[1].g_b[1].g_on.u_bk} 2505.6 820.8 R0
ot_pbk {u_st.g_part[2].g_q[2].g_b[0].g_on.u_bk} 2008.8 557.28 R0
ot_pbk {u_st.g_part[2].g_q[2].g_b[1].g_on.u_bk} 2505.6 557.28 R0
ot_pbk {u_st.g_part[2].g_q[3].g_b[0].g_on.u_bk} 2008.8 293.76 R0
ot_pbk {u_st.g_part[2].g_q[3].g_b[1].g_on.u_bk} 2505.6 293.76 R0
ot_pbk {u_st.g_part[2].g_q[4].g_b[0].g_on.u_bk} 2008.8 30.24 R0
ot_pbk {u_st.g_part[2].g_q[4].g_b[1].g_on.u_bk} 2505.6 30.24 R0
