set cap_by_name [dict create]
foreach i [[ord::get_db_block] getInsts] {dict set cap_by_name [string map [list "\\" ""] [$i getName]] $i}
set cap_n 0
set i [dict get $cap_by_name {u_ls.s3_v$_DFF_PN0_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-0*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,77.004-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_first$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-1*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,65.004-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_split[0]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-2*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,68.988-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_split[1]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-3*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,71.004-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_split[2]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-0*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,73.02-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_split[3]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-1*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,74.988-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[0]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-2*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,6.1080000000000005-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[1]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-3*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,6.348000000000001-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[2]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-0*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,6.539999999999999-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[3]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-1*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,6.779999999999999-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[4]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-2*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,6.9719999999999995-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[5]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-3*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,7.212-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[6]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-0*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,7.404-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[7]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-1*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,7.644-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[8]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-2*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,7.836-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[9]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-3*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,8.076-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[10]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-0*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,8.315999999999999-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[11]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-1*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,8.508-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[12]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-2*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,8.748000000000001-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[13]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-3*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,8.940000000000001-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[14]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-0*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,9.18-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[15]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-1*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,9.372-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[16]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-2*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,9.612-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[17]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-3*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,9.852-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[18]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-0*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,10.044-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[19]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-1*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,10.283999999999999-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[20]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-2*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,10.475999999999999-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[21]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-3*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,10.716000000000001-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[22]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-0*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,10.908000000000001-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[23]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-1*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,11.148-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[24]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-2*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,11.34-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[25]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-3*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,11.58-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[26]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-0*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,11.82-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[27]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-1*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,12.012-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[28]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-2*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,12.251999999999999-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[29]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-3*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,12.443999999999999-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[30]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-0*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,12.684000000000001-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[31]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-1*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,12.876000000000001-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[32]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-2*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,13.136-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[33]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-3*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,13.328-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[34]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-0*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,13.52-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[35]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-1*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,13.776-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[36]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-2*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,13.968-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[37]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-3*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,14.224-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[38]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-0*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,14.416-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[39]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-1*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,14.672-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[40]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-2*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,14.864-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[41]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-3*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,15.056-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[42]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-0*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,15.312-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[43]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-1*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,15.504-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[44]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-2*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,15.76-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[45]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-3*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,15.952-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[46]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-0*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,16.144-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[47]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-1*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,16.4-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[48]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-2*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,16.592-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[49]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-3*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,16.848-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[50]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-0*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,17.04-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[51]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-1*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,17.296-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[52]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-2*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,17.488-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[53]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-3*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,17.68-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[54]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-0*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,17.936-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[55]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-1*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,18.128-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[56]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-2*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,18.384-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[57]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-3*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,18.576-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[58]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-0*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,18.768-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[59]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-1*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,19.024-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[60]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-2*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,19.216-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[61]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-3*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,19.472-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[62]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-0*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,19.664-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[63]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-1*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,19.92-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[64]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-2*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,20.124-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[65]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-3*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,20.316-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[66]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-0*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,20.556-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[67]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-1*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,20.748-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[68]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-2*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,20.988-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[69]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-3*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,21.18-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[70]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-0*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,21.42-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[71]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-1*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,21.66-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[72]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-2*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,21.852-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[73]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-3*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,22.092-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[74]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-0*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,22.284-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[75]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-1*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,22.524-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[76]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-2*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,22.716-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[77]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-3*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,22.956-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[78]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-0*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,23.195999999999998-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[79]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-1*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,23.387999999999998-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[80]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-2*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,23.628-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[81]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-3*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,23.82-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[82]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-0*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,24.06-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[83]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-1*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,24.252-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[84]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-2*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,24.492-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[85]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-3*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,24.684-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[86]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-0*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,24.924-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[87]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-1*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,25.164-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[88]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-2*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,25.356-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[89]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-3*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,25.596-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[90]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-0*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,25.788-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[91]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-1*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,26.028-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[92]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-2*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,26.22-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[93]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-3*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,26.46-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[94]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-0*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,26.652-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[95]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-1*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,26.892-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[96]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-2*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,27.088-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[97]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-3*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,27.344-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[98]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-0*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,27.536-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[99]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-1*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,27.792-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[100]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-2*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,27.984-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[101]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-3*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,28.176000000000002-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[102]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-0*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,28.432000000000002-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[103]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-1*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,28.624000000000002-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[104]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-2*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,28.880000000000003-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[105]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-3*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,29.072000000000003-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[106]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-0*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,29.328000000000003-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[107]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-1*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,29.520000000000003-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[108]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-2*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,29.712000000000003-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[109]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-3*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,29.968000000000004-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[110]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-0*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,30.159999999999997-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[111]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-1*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,30.415999999999997-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[112]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-2*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,30.607999999999997-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[113]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-3*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,30.799999999999997-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[114]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-0*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,31.055999999999997-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[115]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-1*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,31.247999999999998-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[116]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-2*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,31.503999999999998-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[117]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-3*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,31.695999999999998-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[118]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-0*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,31.951999999999998-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[119]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-1*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,32.144-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[120]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-2*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,32.336-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[121]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-3*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,32.592-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[122]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-0*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,32.784-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[123]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-1*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,33.04-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[124]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-2*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,33.232-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[125]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-3*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,33.424-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[126]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-0*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,33.68-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[127]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-1*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,33.872-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[128]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-2*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,34.092-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[129]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-3*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,34.332-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[130]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-0*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,34.524-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[131]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-1*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,34.764-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[132]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-2*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,35.004-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[133]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-3*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,35.196-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[134]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-0*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,35.436-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[135]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-1*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,35.628-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[136]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-2*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,35.868-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[137]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-3*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,36.06-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[138]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-0*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,36.3-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[139]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-1*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,36.54-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[140]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-2*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,36.732-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[141]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-3*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,36.972-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[142]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-0*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,37.164-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[143]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-1*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,37.403999999999996-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[144]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-2*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,37.596000000000004-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[145]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-3*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,37.836-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[146]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-0*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,38.028-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[147]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-1*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,38.268-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[148]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-2*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,38.508-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[149]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-3*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,38.7-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[150]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-0*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,38.94-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[151]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-1*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,39.132-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[152]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-2*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,39.372-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[153]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-3*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,39.564-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[154]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-0*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,39.804-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[155]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-1*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,39.996-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[156]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-2*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,40.236-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[157]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-3*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,40.476-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[158]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-0*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,40.668-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[159]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-1*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,40.908-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[160]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-2*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,41.104-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[161]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-3*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,41.36-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[162]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-0*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,41.552-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[163]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-1*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,41.744-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[164]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-2*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,42.0-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[165]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-3*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,42.192-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[166]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-0*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,42.448-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[167]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-1*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,42.64-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[168]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-2*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,42.832-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[169]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-3*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,43.088-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[170]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-0*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,43.28-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[171]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-1*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,43.536-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[172]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-2*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,43.728-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[173]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-3*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,43.984-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[174]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-0*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,44.176-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[175]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-1*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,44.367999999999995-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[176]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-2*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,44.623999999999995-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[177]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-3*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,44.816-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[178]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-0*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,45.072-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[179]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-1*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,45.263999999999996-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[180]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-2*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,45.456-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[181]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-3*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,45.712-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[182]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-0*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,45.903999999999996-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[183]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-1*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,46.16-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[184]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-2*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,46.352000000000004-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[185]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-3*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,46.608000000000004-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[186]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-0*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,46.8-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[187]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-1*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,46.992000000000004-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[188]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-2*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,47.248000000000005-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[189]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-3*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,47.44-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[190]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-0*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,47.696-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[191]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-1*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,47.888000000000005-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[192]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-2*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,48.108-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[193]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-3*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,48.348-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[194]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-0*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,48.54-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[195]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-1*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,48.78-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[196]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-2*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,48.972-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[197]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-3*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,49.212-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[198]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-0*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,49.403999999999996-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[199]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-1*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,49.644-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[200]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-2*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,49.836-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[201]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-3*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,50.076-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[202]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-0*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,50.316-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[203]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-1*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,50.508-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[204]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-2*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,50.748-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[205]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-3*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,50.94-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[206]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-0*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,51.18-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[207]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-1*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,51.372-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[208]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-2*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,51.612-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[209]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-3*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,51.852000000000004-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[210]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-0*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,52.044-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[211]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-1*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,52.284-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[212]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-2*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,52.476-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[213]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-3*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,52.716-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[214]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-0*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,52.908-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[215]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-1*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,53.147999999999996-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[216]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-2*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,53.34-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[217]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-3*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,53.58-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[218]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-0*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,53.82-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[219]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-1*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,54.012-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[220]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-2*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,54.252-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[221]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-3*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,54.444-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[222]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-0*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,54.684-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[223]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-1*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,54.876-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[224]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-2*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,55.120000000000005-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[225]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-3*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,55.312-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[226]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-0*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,55.568-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[227]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-1*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,55.760000000000005-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[228]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-2*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,56.016-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[229]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-3*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,56.208-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[230]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-0*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,56.4-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[231]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-1*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,56.656-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[232]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-2*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,56.848-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[233]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-3*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,57.104-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[234]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-0*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,57.296-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[235]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-1*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,57.488-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[236]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-2*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,57.744-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[237]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-3*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,57.936-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[238]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-0*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,58.192-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[239]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-1*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,58.384-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[240]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-2*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,58.64-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[241]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-3*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,58.832-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[242]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-0*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,59.024-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[243]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-1*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,59.28-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[244]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-2*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,59.472-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[245]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-3*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,59.728-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[246]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-0*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,59.92-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[247]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-1*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,60.111999999999995-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[248]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-2*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,60.367999999999995-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[249]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-3*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,60.56-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[250]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-0*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,60.816-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[251]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-1*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,61.007999999999996-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[252]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-2*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,61.263999999999996-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[253]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-3*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,61.456-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[254]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-0*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,61.647999999999996-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_w[255]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-1*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,61.903999999999996-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_x[0]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-2*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,78.108-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_x[1]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-3*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,78.252-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_x[2]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-0*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,78.444-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_x[3]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-1*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,78.588-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_x[4]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-2*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,78.78-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_x[5]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-3*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,78.924-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_x[6]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-0*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,79.116-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_x[7]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-1*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,79.30799999999999-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_x[8]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-2*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,79.452-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_x[9]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-3*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,79.644-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_x[10]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-0*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,79.788-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_x[11]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-1*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,79.98-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_x[12]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-2*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,80.172-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_x[13]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-3*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,80.316-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_x[14]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-0*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,80.508-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_x[15]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-1*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,80.652-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_x[16]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-2*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,80.844-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_x[17]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-3*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,80.988-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_x[18]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-0*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,81.18-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_x[19]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-1*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,81.372-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_x[20]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-2*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,81.516-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_x[21]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-3*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,81.708-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_x[22]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-0*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,81.852-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_x[23]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-1*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,82.044-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_x[24]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-2*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,82.188-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_x[25]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-3*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,82.38-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_x[26]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-0*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,82.572-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_x[27]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-1*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,82.716-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_x[28]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-2*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,82.908-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_x[29]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-3*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,83.05199999999999-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_x[30]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-0*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,83.244-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_x[31]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-1*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,83.436-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_x[32]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-2*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,83.6-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_x[33]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-3*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,83.72800000000001-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_x[34]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-0*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,83.92-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_x[35]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-1*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,84.112-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_x[36]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-2*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,84.304-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_x[37]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-3*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,84.43199999999999-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_x[38]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-0*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,84.624-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_x[39]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-1*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,84.816-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_x[40]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-2*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,84.94399999999999-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_x[41]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-3*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,85.136-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_x[42]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-0*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,85.328-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_x[43]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-1*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,85.45599999999999-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_x[44]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-2*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,85.648-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_x[45]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-3*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,85.84-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_x[46]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-0*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,85.96799999999999-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_x[47]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-1*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,86.16-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_x[48]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-2*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,86.352-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_x[49]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-3*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,86.47999999999999-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_x[50]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-0*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,86.672-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_x[51]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-1*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,86.864-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_x[52]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-2*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,86.99199999999999-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_x[53]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-3*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,87.184-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_x[54]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-0*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,87.376-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_x[55]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-1*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,87.56800000000001-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_x[56]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-2*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,87.696-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_x[57]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-3*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,87.888-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_x[58]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-0*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,88.08-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_x[59]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-1*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,88.208-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_x[60]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-2*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,88.4-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_x[61]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-3*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,88.592-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_x[62]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-0*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,88.72-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_x[63]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-1*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,88.912-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_x[64]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-2*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,89.1-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_x[65]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-3*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,89.244-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_x[66]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-0*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,89.436-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_x[67]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-1*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,89.58-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_x[68]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-2*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,89.772-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_x[69]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-3*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,89.964-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_x[70]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-0*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,90.108-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_x[71]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-1*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,90.3-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_x[72]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-2*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,90.444-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_x[73]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-3*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,90.636-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_x[74]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-0*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,90.828-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_x[75]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-1*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,90.972-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_x[76]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-2*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,91.164-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_x[77]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-3*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,91.30799999999999-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_x[78]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-0*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,91.5-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_x[79]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-1*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,91.644-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_x[80]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-2*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,91.836-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_x[81]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-3*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,92.028-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_x[82]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-0*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,92.172-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_x[83]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-1*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,92.364-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_x[84]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-2*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,92.508-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_x[85]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-3*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,92.7-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_x[86]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-0*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,92.844-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_x[87]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-1*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,93.036-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_x[88]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-2*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,93.228-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_x[89]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-3*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,93.372-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_x[90]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-0*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,93.564-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_x[91]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-1*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,93.708-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_x[92]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-2*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,93.9-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_x[93]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-3*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,94.092-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_x[94]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-0*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,94.236-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_x[95]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-1*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,94.428-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_x[96]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-2*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,94.608-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_x[97]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-3*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,94.73599999999999-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_x[98]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-0*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,94.928-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_x[99]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-1*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,95.12-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_x[100]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-2*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,95.24799999999999-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_x[101]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-3*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,95.44-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_x[102]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-0*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,95.632-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_x[103]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-1*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,95.75999999999999-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_x[104]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-2*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,95.952-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_x[105]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-3*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,96.144-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_x[106]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-0*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,96.336-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_x[107]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-1*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,96.464-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_x[108]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-2*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,96.656-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_x[109]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-3*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,96.848-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_x[110]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-0*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,96.976-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_x[111]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-1*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,97.168-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_x[112]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-2*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,97.36-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_x[113]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-3*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,97.488-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_x[114]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-0*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,97.68-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_x[115]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-1*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,97.872-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_x[116]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-2*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,98.0-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_x[117]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-3*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,98.19200000000001-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_x[118]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-0*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,98.384-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_x[119]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-1*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,98.512-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_x[120]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-2*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,98.70400000000001-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_x[121]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-3*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,98.896-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_x[122]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-0*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,99.024-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_x[123]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-1*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,99.21600000000001-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_x[124]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-2*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,99.408-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_x[125]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-3*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,99.6-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_x[126]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-0*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,99.72800000000001-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set i [dict get $cap_by_name {u_ls.s3_x[127]$_DFF_P_}]
set mx [expr {double([[$i getMaster] getWidth])/$ot_dbu}]
set xx [expr {$cx1-$mx-1.0-1*$mx}]
set yy [expr {max($cy0,min($cy1-0.27,99.92-0.135))}]
$i setLocation [expr {int(round($xx*$ot_dbu))}] [expr {int(round($yy*$ot_dbu))}]
$i setPlacementStatus FIRM
lappend ot_list [$i getName]
incr cap_n
set ot_list [lsort -unique $ot_list]
ot_anchor_pack::repair $ot_blk $ot_list
set f [open $::env(RESULTS_DIR)/ot_out_flop_at_pins.txt w]
foreach n $ot_list {puts $f $n}
close $f
puts "NATIVE_CAPTURE anchored $cap_n unique source-derived input FFs; total [llength $ot_list]"
