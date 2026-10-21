# Existing E2 groups, cell-inclusive <=405 model. MUST audit post DPL/CTS; do not release these fences silently.
set b [ord::get_db_block]
set dbu [$b getDbUnitsPerMicron]
set r [odb::dbRegion_create $b "ml_e2_WD_0_w"]
odb::dbBox_create $r [expr {round(1501.16*$dbu)}] [expr {round(2443.16*$dbu)}] [expr {round(1507.64*$dbu)}] [expr {round(2449.64*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_0_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[0\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[0].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_0_r"]
odb::dbBox_create $r [expr {round(1684.24*$dbu)}] [expr {round(2586.24*$dbu)}] [expr {round(1688.56*$dbu)}] [expr {round(2590.56*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_0_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[0\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[0].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_1_w"]
odb::dbBox_create $r [expr {round(1508.18*$dbu)}] [expr {round(2443.16*$dbu)}] [expr {round(1514.66*$dbu)}] [expr {round(2449.64*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_1_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[1\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[1].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_1_r"]
odb::dbBox_create $r [expr {round(1689.64*$dbu)}] [expr {round(2586.24*$dbu)}] [expr {round(1693.96*$dbu)}] [expr {round(2590.56*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_1_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[1\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[1].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_2_w"]
odb::dbBox_create $r [expr {round(1515.2*$dbu)}] [expr {round(2443.16*$dbu)}] [expr {round(1521.68*$dbu)}] [expr {round(2449.64*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_2_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[2\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[2].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_2_r"]
odb::dbBox_create $r [expr {round(1695.04*$dbu)}] [expr {round(2586.24*$dbu)}] [expr {round(1699.36*$dbu)}] [expr {round(2590.56*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_2_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[2\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[2].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_3_w"]
odb::dbBox_create $r [expr {round(1522.22*$dbu)}] [expr {round(2443.16*$dbu)}] [expr {round(1528.7*$dbu)}] [expr {round(2449.64*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_3_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[3\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[3].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_3_r"]
odb::dbBox_create $r [expr {round(1700.44*$dbu)}] [expr {round(2586.24*$dbu)}] [expr {round(1704.76*$dbu)}] [expr {round(2590.56*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_3_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[3\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[3].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_4_w"]
odb::dbBox_create $r [expr {round(1529.24*$dbu)}] [expr {round(2443.16*$dbu)}] [expr {round(1535.72*$dbu)}] [expr {round(2449.64*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_4_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[4\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[4].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_4_r"]
odb::dbBox_create $r [expr {round(1705.84*$dbu)}] [expr {round(2586.24*$dbu)}] [expr {round(1710.16*$dbu)}] [expr {round(2590.56*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_4_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[4\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[4].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_5_w"]
odb::dbBox_create $r [expr {round(1536.26*$dbu)}] [expr {round(2443.16*$dbu)}] [expr {round(1542.74*$dbu)}] [expr {round(2449.64*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_5_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[5\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[5].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_5_r"]
odb::dbBox_create $r [expr {round(1711.24*$dbu)}] [expr {round(2586.24*$dbu)}] [expr {round(1715.56*$dbu)}] [expr {round(2590.56*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_5_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[5\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[5].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_6_w"]
odb::dbBox_create $r [expr {round(1543.28*$dbu)}] [expr {round(2443.16*$dbu)}] [expr {round(1549.76*$dbu)}] [expr {round(2449.64*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_6_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[6\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[6].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_6_r"]
odb::dbBox_create $r [expr {round(1716.64*$dbu)}] [expr {round(2586.24*$dbu)}] [expr {round(1720.96*$dbu)}] [expr {round(2590.56*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_6_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[6\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[6].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_7_w"]
odb::dbBox_create $r [expr {round(1550.3*$dbu)}] [expr {round(2443.16*$dbu)}] [expr {round(1556.78*$dbu)}] [expr {round(2449.64*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_7_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[7\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[7].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_7_r"]
odb::dbBox_create $r [expr {round(1722.04*$dbu)}] [expr {round(2586.24*$dbu)}] [expr {round(1726.36*$dbu)}] [expr {round(2590.56*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_7_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[7\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[7].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_8_w"]
odb::dbBox_create $r [expr {round(1557.32*$dbu)}] [expr {round(2443.16*$dbu)}] [expr {round(1563.8*$dbu)}] [expr {round(2449.64*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_8_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[8\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[8].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_8_r"]
odb::dbBox_create $r [expr {round(1727.44*$dbu)}] [expr {round(2586.24*$dbu)}] [expr {round(1731.76*$dbu)}] [expr {round(2590.56*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_8_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[8\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[8].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_9_w"]
odb::dbBox_create $r [expr {round(1564.34*$dbu)}] [expr {round(2443.16*$dbu)}] [expr {round(1570.82*$dbu)}] [expr {round(2449.64*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_9_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[9\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[9].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_9_r"]
odb::dbBox_create $r [expr {round(1732.84*$dbu)}] [expr {round(2586.24*$dbu)}] [expr {round(1737.16*$dbu)}] [expr {round(2590.56*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_9_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[9\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[9].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_10_w"]
odb::dbBox_create $r [expr {round(1571.36*$dbu)}] [expr {round(2443.16*$dbu)}] [expr {round(1577.84*$dbu)}] [expr {round(2449.64*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_10_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[10\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[10].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_10_r"]
odb::dbBox_create $r [expr {round(1738.24*$dbu)}] [expr {round(2586.24*$dbu)}] [expr {round(1742.56*$dbu)}] [expr {round(2590.56*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_10_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[10\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[10].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_11_w"]
odb::dbBox_create $r [expr {round(1578.38*$dbu)}] [expr {round(2443.16*$dbu)}] [expr {round(1584.86*$dbu)}] [expr {round(2449.64*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_11_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[11\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[11].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_11_r"]
odb::dbBox_create $r [expr {round(1743.64*$dbu)}] [expr {round(2586.24*$dbu)}] [expr {round(1747.96*$dbu)}] [expr {round(2590.56*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_11_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[11\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[11].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_12_w"]
odb::dbBox_create $r [expr {round(1501.16*$dbu)}] [expr {round(2450.18*$dbu)}] [expr {round(1507.64*$dbu)}] [expr {round(2456.66*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_12_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[12\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[12].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_12_r"]
odb::dbBox_create $r [expr {round(1684.24*$dbu)}] [expr {round(2591.64*$dbu)}] [expr {round(1688.56*$dbu)}] [expr {round(2595.96*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_12_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[12\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[12].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_13_w"]
odb::dbBox_create $r [expr {round(1508.18*$dbu)}] [expr {round(2450.18*$dbu)}] [expr {round(1514.66*$dbu)}] [expr {round(2456.66*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_13_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[13\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[13].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_13_r"]
odb::dbBox_create $r [expr {round(1689.64*$dbu)}] [expr {round(2591.64*$dbu)}] [expr {round(1693.96*$dbu)}] [expr {round(2595.96*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_13_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[13\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[13].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_14_w"]
odb::dbBox_create $r [expr {round(1515.2*$dbu)}] [expr {round(2450.18*$dbu)}] [expr {round(1521.68*$dbu)}] [expr {round(2456.66*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_14_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[14\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[14].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_14_r"]
odb::dbBox_create $r [expr {round(1695.04*$dbu)}] [expr {round(2591.64*$dbu)}] [expr {round(1699.36*$dbu)}] [expr {round(2595.96*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_14_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[14\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[14].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_15_w"]
odb::dbBox_create $r [expr {round(1522.22*$dbu)}] [expr {round(2450.18*$dbu)}] [expr {round(1528.7*$dbu)}] [expr {round(2456.66*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_15_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[15\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[15].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_15_r"]
odb::dbBox_create $r [expr {round(1700.44*$dbu)}] [expr {round(2591.64*$dbu)}] [expr {round(1704.76*$dbu)}] [expr {round(2595.96*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_15_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[15\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[15].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_16_w"]
odb::dbBox_create $r [expr {round(1529.24*$dbu)}] [expr {round(2450.18*$dbu)}] [expr {round(1535.72*$dbu)}] [expr {round(2456.66*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_16_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[16\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[16].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_16_r"]
odb::dbBox_create $r [expr {round(1705.84*$dbu)}] [expr {round(2591.64*$dbu)}] [expr {round(1710.16*$dbu)}] [expr {round(2595.96*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_16_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[16\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[16].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_17_w"]
odb::dbBox_create $r [expr {round(1536.26*$dbu)}] [expr {round(2450.18*$dbu)}] [expr {round(1542.74*$dbu)}] [expr {round(2456.66*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_17_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[17\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[17].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_17_r"]
odb::dbBox_create $r [expr {round(1711.24*$dbu)}] [expr {round(2591.64*$dbu)}] [expr {round(1715.56*$dbu)}] [expr {round(2595.96*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_17_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[17\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[17].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_18_w"]
odb::dbBox_create $r [expr {round(1543.28*$dbu)}] [expr {round(2450.18*$dbu)}] [expr {round(1549.76*$dbu)}] [expr {round(2456.66*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_18_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[18\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[18].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_18_r"]
odb::dbBox_create $r [expr {round(1716.64*$dbu)}] [expr {round(2591.64*$dbu)}] [expr {round(1720.96*$dbu)}] [expr {round(2595.96*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_18_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[18\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[18].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_19_w"]
odb::dbBox_create $r [expr {round(1550.3*$dbu)}] [expr {round(2450.18*$dbu)}] [expr {round(1556.78*$dbu)}] [expr {round(2456.66*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_19_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[19\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[19].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_19_r"]
odb::dbBox_create $r [expr {round(1722.04*$dbu)}] [expr {round(2591.64*$dbu)}] [expr {round(1726.36*$dbu)}] [expr {round(2595.96*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_19_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[19\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[19].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_20_w"]
odb::dbBox_create $r [expr {round(1557.32*$dbu)}] [expr {round(2450.18*$dbu)}] [expr {round(1563.8*$dbu)}] [expr {round(2456.66*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_20_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[20\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[20].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_20_r"]
odb::dbBox_create $r [expr {round(1727.44*$dbu)}] [expr {round(2591.64*$dbu)}] [expr {round(1731.76*$dbu)}] [expr {round(2595.96*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_20_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[20\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[20].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_21_w"]
odb::dbBox_create $r [expr {round(1564.34*$dbu)}] [expr {round(2450.18*$dbu)}] [expr {round(1570.82*$dbu)}] [expr {round(2456.66*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_21_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[21\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[21].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_21_r"]
odb::dbBox_create $r [expr {round(1732.84*$dbu)}] [expr {round(2591.64*$dbu)}] [expr {round(1737.16*$dbu)}] [expr {round(2595.96*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_21_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[21\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[21].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_22_w"]
odb::dbBox_create $r [expr {round(1571.36*$dbu)}] [expr {round(2450.18*$dbu)}] [expr {round(1577.84*$dbu)}] [expr {round(2456.66*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_22_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[22\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[22].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_22_r"]
odb::dbBox_create $r [expr {round(1738.24*$dbu)}] [expr {round(2591.64*$dbu)}] [expr {round(1742.56*$dbu)}] [expr {round(2595.96*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_22_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[22\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[22].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_23_w"]
odb::dbBox_create $r [expr {round(1578.38*$dbu)}] [expr {round(2450.18*$dbu)}] [expr {round(1584.86*$dbu)}] [expr {round(2456.66*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_23_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[23\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[23].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_23_r"]
odb::dbBox_create $r [expr {round(1743.64*$dbu)}] [expr {round(2591.64*$dbu)}] [expr {round(1747.96*$dbu)}] [expr {round(2595.96*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_23_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[23\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[23].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_24_w"]
odb::dbBox_create $r [expr {round(1501.16*$dbu)}] [expr {round(2457.2*$dbu)}] [expr {round(1507.64*$dbu)}] [expr {round(2463.68*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_24_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[24\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[24].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_24_r"]
odb::dbBox_create $r [expr {round(1684.24*$dbu)}] [expr {round(2597.04*$dbu)}] [expr {round(1688.56*$dbu)}] [expr {round(2601.36*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_24_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[24\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[24].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_25_w"]
odb::dbBox_create $r [expr {round(1508.18*$dbu)}] [expr {round(2457.2*$dbu)}] [expr {round(1514.66*$dbu)}] [expr {round(2463.68*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_25_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[25\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[25].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_25_r"]
odb::dbBox_create $r [expr {round(1689.64*$dbu)}] [expr {round(2597.04*$dbu)}] [expr {round(1693.96*$dbu)}] [expr {round(2601.36*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_25_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[25\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[25].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_26_w"]
odb::dbBox_create $r [expr {round(1515.2*$dbu)}] [expr {round(2457.2*$dbu)}] [expr {round(1521.68*$dbu)}] [expr {round(2463.68*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_26_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[26\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[26].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_26_r"]
odb::dbBox_create $r [expr {round(1695.04*$dbu)}] [expr {round(2597.04*$dbu)}] [expr {round(1699.36*$dbu)}] [expr {round(2601.36*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_26_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[26\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[26].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_27_w"]
odb::dbBox_create $r [expr {round(1522.22*$dbu)}] [expr {round(2457.2*$dbu)}] [expr {round(1528.7*$dbu)}] [expr {round(2463.68*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_27_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[27\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[27].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_27_r"]
odb::dbBox_create $r [expr {round(1700.44*$dbu)}] [expr {round(2597.04*$dbu)}] [expr {round(1704.76*$dbu)}] [expr {round(2601.36*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_27_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[27\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[27].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_28_w"]
odb::dbBox_create $r [expr {round(1529.24*$dbu)}] [expr {round(2457.2*$dbu)}] [expr {round(1535.72*$dbu)}] [expr {round(2463.68*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_28_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[28\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[28].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_28_r"]
odb::dbBox_create $r [expr {round(1705.84*$dbu)}] [expr {round(2597.04*$dbu)}] [expr {round(1710.16*$dbu)}] [expr {round(2601.36*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_28_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[28\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[28].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_29_w"]
odb::dbBox_create $r [expr {round(1536.26*$dbu)}] [expr {round(2457.2*$dbu)}] [expr {round(1542.74*$dbu)}] [expr {round(2463.68*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_29_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[29\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[29].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_29_r"]
odb::dbBox_create $r [expr {round(1711.24*$dbu)}] [expr {round(2597.04*$dbu)}] [expr {round(1715.56*$dbu)}] [expr {round(2601.36*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_29_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[29\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[29].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_30_w"]
odb::dbBox_create $r [expr {round(1543.28*$dbu)}] [expr {round(2457.2*$dbu)}] [expr {round(1549.76*$dbu)}] [expr {round(2463.68*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_30_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[30\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[30].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_30_r"]
odb::dbBox_create $r [expr {round(1716.64*$dbu)}] [expr {round(2597.04*$dbu)}] [expr {round(1720.96*$dbu)}] [expr {round(2601.36*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_30_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[30\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[30].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_31_w"]
odb::dbBox_create $r [expr {round(1550.3*$dbu)}] [expr {round(2457.2*$dbu)}] [expr {round(1556.78*$dbu)}] [expr {round(2463.68*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_31_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[31\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[31].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_31_r"]
odb::dbBox_create $r [expr {round(1722.04*$dbu)}] [expr {round(2597.04*$dbu)}] [expr {round(1726.36*$dbu)}] [expr {round(2601.36*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_31_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[31\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[31].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_32_w"]
odb::dbBox_create $r [expr {round(1557.32*$dbu)}] [expr {round(2457.2*$dbu)}] [expr {round(1563.8*$dbu)}] [expr {round(2463.68*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_32_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[32\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[32].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_32_r"]
odb::dbBox_create $r [expr {round(1727.44*$dbu)}] [expr {round(2597.04*$dbu)}] [expr {round(1731.76*$dbu)}] [expr {round(2601.36*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_32_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[32\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[32].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_33_w"]
odb::dbBox_create $r [expr {round(1564.34*$dbu)}] [expr {round(2457.2*$dbu)}] [expr {round(1570.82*$dbu)}] [expr {round(2463.68*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_33_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[33\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[33].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_33_r"]
odb::dbBox_create $r [expr {round(1732.84*$dbu)}] [expr {round(2597.04*$dbu)}] [expr {round(1737.16*$dbu)}] [expr {round(2601.36*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_33_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[33\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[33].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_34_w"]
odb::dbBox_create $r [expr {round(1571.36*$dbu)}] [expr {round(2457.2*$dbu)}] [expr {round(1577.84*$dbu)}] [expr {round(2463.68*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_34_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[34\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[34].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_34_r"]
odb::dbBox_create $r [expr {round(1738.24*$dbu)}] [expr {round(2597.04*$dbu)}] [expr {round(1742.56*$dbu)}] [expr {round(2601.36*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_34_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[34\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[34].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_35_w"]
odb::dbBox_create $r [expr {round(1578.38*$dbu)}] [expr {round(2457.2*$dbu)}] [expr {round(1584.86*$dbu)}] [expr {round(2463.68*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_35_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[35\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[35].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_35_r"]
odb::dbBox_create $r [expr {round(1743.64*$dbu)}] [expr {round(2597.04*$dbu)}] [expr {round(1747.96*$dbu)}] [expr {round(2601.36*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_35_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[35\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[35].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_36_w"]
odb::dbBox_create $r [expr {round(1501.16*$dbu)}] [expr {round(2464.22*$dbu)}] [expr {round(1507.64*$dbu)}] [expr {round(2470.7*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_36_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[36\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[36].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_36_r"]
odb::dbBox_create $r [expr {round(1684.24*$dbu)}] [expr {round(2602.44*$dbu)}] [expr {round(1688.56*$dbu)}] [expr {round(2606.76*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_36_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[36\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[36].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_37_w"]
odb::dbBox_create $r [expr {round(1508.18*$dbu)}] [expr {round(2464.22*$dbu)}] [expr {round(1514.66*$dbu)}] [expr {round(2470.7*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_37_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[37\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[37].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_37_r"]
odb::dbBox_create $r [expr {round(1689.64*$dbu)}] [expr {round(2602.44*$dbu)}] [expr {round(1693.96*$dbu)}] [expr {round(2606.76*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_37_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[37\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[37].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_38_w"]
odb::dbBox_create $r [expr {round(1515.2*$dbu)}] [expr {round(2464.22*$dbu)}] [expr {round(1521.68*$dbu)}] [expr {round(2470.7*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_38_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[38\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[38].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_38_r"]
odb::dbBox_create $r [expr {round(1695.04*$dbu)}] [expr {round(2602.44*$dbu)}] [expr {round(1699.36*$dbu)}] [expr {round(2606.76*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_38_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[38\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[38].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_39_w"]
odb::dbBox_create $r [expr {round(1522.22*$dbu)}] [expr {round(2464.22*$dbu)}] [expr {round(1528.7*$dbu)}] [expr {round(2470.7*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_39_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[39\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[39].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_39_r"]
odb::dbBox_create $r [expr {round(1700.44*$dbu)}] [expr {round(2602.44*$dbu)}] [expr {round(1704.76*$dbu)}] [expr {round(2606.76*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_39_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[39\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[39].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_40_w"]
odb::dbBox_create $r [expr {round(1529.24*$dbu)}] [expr {round(2464.22*$dbu)}] [expr {round(1535.72*$dbu)}] [expr {round(2470.7*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_40_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[40\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[40].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_40_r"]
odb::dbBox_create $r [expr {round(1705.84*$dbu)}] [expr {round(2602.44*$dbu)}] [expr {round(1710.16*$dbu)}] [expr {round(2606.76*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_40_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[40\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[40].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_41_w"]
odb::dbBox_create $r [expr {round(1536.26*$dbu)}] [expr {round(2464.22*$dbu)}] [expr {round(1542.74*$dbu)}] [expr {round(2470.7*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_41_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[41\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[41].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_41_r"]
odb::dbBox_create $r [expr {round(1711.24*$dbu)}] [expr {round(2602.44*$dbu)}] [expr {round(1715.56*$dbu)}] [expr {round(2606.76*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_41_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[41\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[41].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_42_w"]
odb::dbBox_create $r [expr {round(1543.28*$dbu)}] [expr {round(2464.22*$dbu)}] [expr {round(1549.76*$dbu)}] [expr {round(2470.7*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_42_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[42\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[42].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_42_r"]
odb::dbBox_create $r [expr {round(1716.64*$dbu)}] [expr {round(2602.44*$dbu)}] [expr {round(1720.96*$dbu)}] [expr {round(2606.76*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_42_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[42\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[42].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_43_w"]
odb::dbBox_create $r [expr {round(1550.3*$dbu)}] [expr {round(2464.22*$dbu)}] [expr {round(1556.78*$dbu)}] [expr {round(2470.7*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_43_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[43\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[43].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_43_r"]
odb::dbBox_create $r [expr {round(1722.04*$dbu)}] [expr {round(2602.44*$dbu)}] [expr {round(1726.36*$dbu)}] [expr {round(2606.76*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_43_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[43\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[43].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_44_w"]
odb::dbBox_create $r [expr {round(1557.32*$dbu)}] [expr {round(2464.22*$dbu)}] [expr {round(1563.8*$dbu)}] [expr {round(2470.7*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_44_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[44\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[44].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_44_r"]
odb::dbBox_create $r [expr {round(1727.44*$dbu)}] [expr {round(2602.44*$dbu)}] [expr {round(1731.76*$dbu)}] [expr {round(2606.76*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_44_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[44\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[44].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_45_w"]
odb::dbBox_create $r [expr {round(1564.34*$dbu)}] [expr {round(2464.22*$dbu)}] [expr {round(1570.82*$dbu)}] [expr {round(2470.7*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_45_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[45\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[45].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_45_r"]
odb::dbBox_create $r [expr {round(1732.84*$dbu)}] [expr {round(2602.44*$dbu)}] [expr {round(1737.16*$dbu)}] [expr {round(2606.76*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_45_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[45\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[45].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_46_w"]
odb::dbBox_create $r [expr {round(1571.36*$dbu)}] [expr {round(2464.22*$dbu)}] [expr {round(1577.84*$dbu)}] [expr {round(2470.7*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_46_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[46\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[46].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_46_r"]
odb::dbBox_create $r [expr {round(1738.24*$dbu)}] [expr {round(2602.44*$dbu)}] [expr {round(1742.56*$dbu)}] [expr {round(2606.76*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_46_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[46\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[46].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_47_w"]
odb::dbBox_create $r [expr {round(1578.38*$dbu)}] [expr {round(2464.22*$dbu)}] [expr {round(1584.86*$dbu)}] [expr {round(2470.7*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_47_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[47\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[47].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_47_r"]
odb::dbBox_create $r [expr {round(1743.64*$dbu)}] [expr {round(2602.44*$dbu)}] [expr {round(1747.96*$dbu)}] [expr {round(2606.76*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_47_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[47\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[47].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_48_w"]
odb::dbBox_create $r [expr {round(1501.16*$dbu)}] [expr {round(2471.24*$dbu)}] [expr {round(1507.64*$dbu)}] [expr {round(2477.72*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_48_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[48\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[48].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_48_r"]
odb::dbBox_create $r [expr {round(1684.24*$dbu)}] [expr {round(2607.84*$dbu)}] [expr {round(1688.56*$dbu)}] [expr {round(2612.16*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_48_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[48\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[48].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_49_w"]
odb::dbBox_create $r [expr {round(1508.18*$dbu)}] [expr {round(2471.24*$dbu)}] [expr {round(1514.66*$dbu)}] [expr {round(2477.72*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_49_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[49\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[49].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_49_r"]
odb::dbBox_create $r [expr {round(1689.64*$dbu)}] [expr {round(2607.84*$dbu)}] [expr {round(1693.96*$dbu)}] [expr {round(2612.16*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_49_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[49\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[49].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_50_w"]
odb::dbBox_create $r [expr {round(1515.2*$dbu)}] [expr {round(2471.24*$dbu)}] [expr {round(1521.68*$dbu)}] [expr {round(2477.72*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_50_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[50\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[50].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_50_r"]
odb::dbBox_create $r [expr {round(1695.04*$dbu)}] [expr {round(2607.84*$dbu)}] [expr {round(1699.36*$dbu)}] [expr {round(2612.16*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_50_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[50\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[50].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_51_w"]
odb::dbBox_create $r [expr {round(1522.22*$dbu)}] [expr {round(2471.24*$dbu)}] [expr {round(1528.7*$dbu)}] [expr {round(2477.72*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_51_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[51\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[51].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_51_r"]
odb::dbBox_create $r [expr {round(1700.44*$dbu)}] [expr {round(2607.84*$dbu)}] [expr {round(1704.76*$dbu)}] [expr {round(2612.16*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_51_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[51\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[51].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_52_w"]
odb::dbBox_create $r [expr {round(1529.24*$dbu)}] [expr {round(2471.24*$dbu)}] [expr {round(1535.72*$dbu)}] [expr {round(2477.72*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_52_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[52\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[52].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_52_r"]
odb::dbBox_create $r [expr {round(1705.84*$dbu)}] [expr {round(2607.84*$dbu)}] [expr {round(1710.16*$dbu)}] [expr {round(2612.16*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_52_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[52\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[52].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_53_w"]
odb::dbBox_create $r [expr {round(1536.26*$dbu)}] [expr {round(2471.24*$dbu)}] [expr {round(1542.74*$dbu)}] [expr {round(2477.72*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_53_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[53\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[53].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_53_r"]
odb::dbBox_create $r [expr {round(1711.24*$dbu)}] [expr {round(2607.84*$dbu)}] [expr {round(1715.56*$dbu)}] [expr {round(2612.16*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_53_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[53\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[53].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_54_w"]
odb::dbBox_create $r [expr {round(1543.28*$dbu)}] [expr {round(2471.24*$dbu)}] [expr {round(1549.76*$dbu)}] [expr {round(2477.72*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_54_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[54\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[54].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_54_r"]
odb::dbBox_create $r [expr {round(1716.64*$dbu)}] [expr {round(2607.84*$dbu)}] [expr {round(1720.96*$dbu)}] [expr {round(2612.16*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_54_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[54\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[54].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_55_w"]
odb::dbBox_create $r [expr {round(1550.3*$dbu)}] [expr {round(2471.24*$dbu)}] [expr {round(1556.78*$dbu)}] [expr {round(2477.72*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_55_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[55\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[55].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_55_r"]
odb::dbBox_create $r [expr {round(1722.04*$dbu)}] [expr {round(2607.84*$dbu)}] [expr {round(1726.36*$dbu)}] [expr {round(2612.16*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_55_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[55\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[55].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_56_w"]
odb::dbBox_create $r [expr {round(1557.32*$dbu)}] [expr {round(2471.24*$dbu)}] [expr {round(1563.8*$dbu)}] [expr {round(2477.72*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_56_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[56\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[56].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_56_r"]
odb::dbBox_create $r [expr {round(1727.44*$dbu)}] [expr {round(2607.84*$dbu)}] [expr {round(1731.76*$dbu)}] [expr {round(2612.16*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_56_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[56\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[56].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_57_w"]
odb::dbBox_create $r [expr {round(1564.34*$dbu)}] [expr {round(2471.24*$dbu)}] [expr {round(1570.82*$dbu)}] [expr {round(2477.72*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_57_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[57\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[57].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_57_r"]
odb::dbBox_create $r [expr {round(1732.84*$dbu)}] [expr {round(2607.84*$dbu)}] [expr {round(1737.16*$dbu)}] [expr {round(2612.16*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_57_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[57\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[57].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_58_w"]
odb::dbBox_create $r [expr {round(1571.36*$dbu)}] [expr {round(2471.24*$dbu)}] [expr {round(1577.84*$dbu)}] [expr {round(2477.72*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_58_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[58\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[58].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_58_r"]
odb::dbBox_create $r [expr {round(1738.24*$dbu)}] [expr {round(2607.84*$dbu)}] [expr {round(1742.56*$dbu)}] [expr {round(2612.16*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_58_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[58\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[58].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_59_w"]
odb::dbBox_create $r [expr {round(1578.38*$dbu)}] [expr {round(2471.24*$dbu)}] [expr {round(1584.86*$dbu)}] [expr {round(2477.72*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_59_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[59\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[59].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_59_r"]
odb::dbBox_create $r [expr {round(1743.64*$dbu)}] [expr {round(2607.84*$dbu)}] [expr {round(1747.96*$dbu)}] [expr {round(2612.16*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_59_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[59\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[59].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_60_w"]
odb::dbBox_create $r [expr {round(1501.16*$dbu)}] [expr {round(2478.26*$dbu)}] [expr {round(1507.64*$dbu)}] [expr {round(2484.74*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_60_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[60\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[60].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_60_r"]
odb::dbBox_create $r [expr {round(1684.24*$dbu)}] [expr {round(2613.24*$dbu)}] [expr {round(1688.56*$dbu)}] [expr {round(2617.56*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_60_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[60\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[60].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_61_w"]
odb::dbBox_create $r [expr {round(1508.18*$dbu)}] [expr {round(2478.26*$dbu)}] [expr {round(1514.66*$dbu)}] [expr {round(2484.74*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_61_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[61\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[61].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_61_r"]
odb::dbBox_create $r [expr {round(1689.64*$dbu)}] [expr {round(2613.24*$dbu)}] [expr {round(1693.96*$dbu)}] [expr {round(2617.56*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_61_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[61\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[61].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_62_w"]
odb::dbBox_create $r [expr {round(1515.2*$dbu)}] [expr {round(2478.26*$dbu)}] [expr {round(1521.68*$dbu)}] [expr {round(2484.74*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_62_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[62\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[62].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_62_r"]
odb::dbBox_create $r [expr {round(1695.04*$dbu)}] [expr {round(2613.24*$dbu)}] [expr {round(1699.36*$dbu)}] [expr {round(2617.56*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_62_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[62\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[62].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_63_w"]
odb::dbBox_create $r [expr {round(1522.22*$dbu)}] [expr {round(2478.26*$dbu)}] [expr {round(1528.7*$dbu)}] [expr {round(2484.74*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_63_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[63\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[63].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_63_r"]
odb::dbBox_create $r [expr {round(1700.44*$dbu)}] [expr {round(2613.24*$dbu)}] [expr {round(1704.76*$dbu)}] [expr {round(2617.56*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_63_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[63\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[63].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_64_w"]
odb::dbBox_create $r [expr {round(1529.24*$dbu)}] [expr {round(2478.26*$dbu)}] [expr {round(1535.72*$dbu)}] [expr {round(2484.74*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_64_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[64\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[64].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_64_r"]
odb::dbBox_create $r [expr {round(1705.84*$dbu)}] [expr {round(2613.24*$dbu)}] [expr {round(1710.16*$dbu)}] [expr {round(2617.56*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_64_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[64\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[64].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_65_w"]
odb::dbBox_create $r [expr {round(1536.26*$dbu)}] [expr {round(2478.26*$dbu)}] [expr {round(1542.74*$dbu)}] [expr {round(2484.74*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_65_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[65\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[65].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_65_r"]
odb::dbBox_create $r [expr {round(1711.24*$dbu)}] [expr {round(2613.24*$dbu)}] [expr {round(1715.56*$dbu)}] [expr {round(2617.56*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_65_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[65\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[65].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_66_w"]
odb::dbBox_create $r [expr {round(1543.28*$dbu)}] [expr {round(2478.26*$dbu)}] [expr {round(1549.76*$dbu)}] [expr {round(2484.74*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_66_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[66\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[66].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_66_r"]
odb::dbBox_create $r [expr {round(1716.64*$dbu)}] [expr {round(2613.24*$dbu)}] [expr {round(1720.96*$dbu)}] [expr {round(2617.56*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_66_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[66\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[66].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_67_w"]
odb::dbBox_create $r [expr {round(1550.3*$dbu)}] [expr {round(2478.26*$dbu)}] [expr {round(1556.78*$dbu)}] [expr {round(2484.74*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_67_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[67\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[67].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_67_r"]
odb::dbBox_create $r [expr {round(1722.04*$dbu)}] [expr {round(2613.24*$dbu)}] [expr {round(1726.36*$dbu)}] [expr {round(2617.56*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_67_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[67\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[67].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_68_w"]
odb::dbBox_create $r [expr {round(1557.32*$dbu)}] [expr {round(2478.26*$dbu)}] [expr {round(1563.8*$dbu)}] [expr {round(2484.74*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_68_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[68\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[68].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_68_r"]
odb::dbBox_create $r [expr {round(1727.44*$dbu)}] [expr {round(2613.24*$dbu)}] [expr {round(1731.76*$dbu)}] [expr {round(2617.56*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_68_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[68\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[68].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_69_w"]
odb::dbBox_create $r [expr {round(1564.34*$dbu)}] [expr {round(2478.26*$dbu)}] [expr {round(1570.82*$dbu)}] [expr {round(2484.74*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_69_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[69\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[69].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_69_r"]
odb::dbBox_create $r [expr {round(1732.84*$dbu)}] [expr {round(2613.24*$dbu)}] [expr {round(1737.16*$dbu)}] [expr {round(2617.56*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_69_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[69\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[69].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_70_w"]
odb::dbBox_create $r [expr {round(1571.36*$dbu)}] [expr {round(2478.26*$dbu)}] [expr {round(1577.84*$dbu)}] [expr {round(2484.74*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_70_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[70\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[70].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_70_r"]
odb::dbBox_create $r [expr {round(1738.24*$dbu)}] [expr {round(2613.24*$dbu)}] [expr {round(1742.56*$dbu)}] [expr {round(2617.56*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_70_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[70\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[70].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_71_w"]
odb::dbBox_create $r [expr {round(1578.38*$dbu)}] [expr {round(2478.26*$dbu)}] [expr {round(1584.86*$dbu)}] [expr {round(2484.74*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_71_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[71\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[71].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_71_r"]
odb::dbBox_create $r [expr {round(1743.64*$dbu)}] [expr {round(2613.24*$dbu)}] [expr {round(1747.96*$dbu)}] [expr {round(2617.56*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_71_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[71\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[71].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_72_w"]
odb::dbBox_create $r [expr {round(1501.16*$dbu)}] [expr {round(2485.28*$dbu)}] [expr {round(1507.64*$dbu)}] [expr {round(2491.76*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_72_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[72\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[72].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_72_r"]
odb::dbBox_create $r [expr {round(1684.24*$dbu)}] [expr {round(2618.64*$dbu)}] [expr {round(1688.56*$dbu)}] [expr {round(2622.96*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_72_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[72\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[72].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_73_w"]
odb::dbBox_create $r [expr {round(1508.18*$dbu)}] [expr {round(2485.28*$dbu)}] [expr {round(1514.66*$dbu)}] [expr {round(2491.76*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_73_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[73\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[73].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_73_r"]
odb::dbBox_create $r [expr {round(1689.64*$dbu)}] [expr {round(2618.64*$dbu)}] [expr {round(1693.96*$dbu)}] [expr {round(2622.96*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_73_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[73\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[73].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_74_w"]
odb::dbBox_create $r [expr {round(1515.2*$dbu)}] [expr {round(2485.28*$dbu)}] [expr {round(1521.68*$dbu)}] [expr {round(2491.76*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_74_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[74\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[74].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_74_r"]
odb::dbBox_create $r [expr {round(1695.04*$dbu)}] [expr {round(2618.64*$dbu)}] [expr {round(1699.36*$dbu)}] [expr {round(2622.96*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_74_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[74\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[74].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_75_w"]
odb::dbBox_create $r [expr {round(1522.22*$dbu)}] [expr {round(2485.28*$dbu)}] [expr {round(1528.7*$dbu)}] [expr {round(2491.76*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_75_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[75\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[75].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_75_r"]
odb::dbBox_create $r [expr {round(1700.44*$dbu)}] [expr {round(2618.64*$dbu)}] [expr {round(1704.76*$dbu)}] [expr {round(2622.96*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_75_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[75\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[75].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_76_w"]
odb::dbBox_create $r [expr {round(1529.24*$dbu)}] [expr {round(2485.28*$dbu)}] [expr {round(1535.72*$dbu)}] [expr {round(2491.76*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_76_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[76\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[76].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_76_r"]
odb::dbBox_create $r [expr {round(1705.84*$dbu)}] [expr {round(2618.64*$dbu)}] [expr {round(1710.16*$dbu)}] [expr {round(2622.96*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_76_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[76\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[76].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_77_w"]
odb::dbBox_create $r [expr {round(1536.26*$dbu)}] [expr {round(2485.28*$dbu)}] [expr {round(1542.74*$dbu)}] [expr {round(2491.76*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_77_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[77\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[77].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_77_r"]
odb::dbBox_create $r [expr {round(1711.24*$dbu)}] [expr {round(2618.64*$dbu)}] [expr {round(1715.56*$dbu)}] [expr {round(2622.96*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_77_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[77\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[77].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_78_w"]
odb::dbBox_create $r [expr {round(1543.28*$dbu)}] [expr {round(2485.28*$dbu)}] [expr {round(1549.76*$dbu)}] [expr {round(2491.76*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_78_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[78\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[78].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_78_r"]
odb::dbBox_create $r [expr {round(1716.64*$dbu)}] [expr {round(2618.64*$dbu)}] [expr {round(1720.96*$dbu)}] [expr {round(2622.96*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_78_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[78\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[78].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_79_w"]
odb::dbBox_create $r [expr {round(1550.3*$dbu)}] [expr {round(2485.28*$dbu)}] [expr {round(1556.78*$dbu)}] [expr {round(2491.76*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_79_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[79\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[79].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_79_r"]
odb::dbBox_create $r [expr {round(1722.04*$dbu)}] [expr {round(2618.64*$dbu)}] [expr {round(1726.36*$dbu)}] [expr {round(2622.96*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_79_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[79\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[79].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_80_w"]
odb::dbBox_create $r [expr {round(1557.32*$dbu)}] [expr {round(2485.28*$dbu)}] [expr {round(1563.8*$dbu)}] [expr {round(2491.76*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_80_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[80\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[80].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_80_r"]
odb::dbBox_create $r [expr {round(1727.44*$dbu)}] [expr {round(2618.64*$dbu)}] [expr {round(1731.76*$dbu)}] [expr {round(2622.96*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_80_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[80\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[80].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_81_w"]
odb::dbBox_create $r [expr {round(1564.34*$dbu)}] [expr {round(2485.28*$dbu)}] [expr {round(1570.82*$dbu)}] [expr {round(2491.76*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_81_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[81\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[81].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_81_r"]
odb::dbBox_create $r [expr {round(1732.84*$dbu)}] [expr {round(2618.64*$dbu)}] [expr {round(1737.16*$dbu)}] [expr {round(2622.96*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_81_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[81\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[81].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_82_w"]
odb::dbBox_create $r [expr {round(1571.36*$dbu)}] [expr {round(2485.28*$dbu)}] [expr {round(1577.84*$dbu)}] [expr {round(2491.76*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_82_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[82\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[82].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_82_r"]
odb::dbBox_create $r [expr {round(1738.24*$dbu)}] [expr {round(2618.64*$dbu)}] [expr {round(1742.56*$dbu)}] [expr {round(2622.96*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_82_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[82\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[82].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_83_w"]
odb::dbBox_create $r [expr {round(1578.38*$dbu)}] [expr {round(2485.28*$dbu)}] [expr {round(1584.86*$dbu)}] [expr {round(2491.76*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_83_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[83\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[83].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_83_r"]
odb::dbBox_create $r [expr {round(1743.64*$dbu)}] [expr {round(2618.64*$dbu)}] [expr {round(1747.96*$dbu)}] [expr {round(2622.96*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_83_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[83\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[83].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_84_w"]
odb::dbBox_create $r [expr {round(1501.16*$dbu)}] [expr {round(2492.3*$dbu)}] [expr {round(1507.64*$dbu)}] [expr {round(2498.78*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_84_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[84\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[84].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_84_r"]
odb::dbBox_create $r [expr {round(1684.24*$dbu)}] [expr {round(2624.04*$dbu)}] [expr {round(1688.56*$dbu)}] [expr {round(2628.36*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_84_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[84\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[84].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_85_w"]
odb::dbBox_create $r [expr {round(1508.18*$dbu)}] [expr {round(2492.3*$dbu)}] [expr {round(1514.66*$dbu)}] [expr {round(2498.78*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_85_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[85\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[85].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_85_r"]
odb::dbBox_create $r [expr {round(1689.64*$dbu)}] [expr {round(2624.04*$dbu)}] [expr {round(1693.96*$dbu)}] [expr {round(2628.36*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_85_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[85\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[85].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_86_w"]
odb::dbBox_create $r [expr {round(1515.2*$dbu)}] [expr {round(2492.3*$dbu)}] [expr {round(1521.68*$dbu)}] [expr {round(2498.78*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_86_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[86\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[86].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_86_r"]
odb::dbBox_create $r [expr {round(1695.04*$dbu)}] [expr {round(2624.04*$dbu)}] [expr {round(1699.36*$dbu)}] [expr {round(2628.36*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_86_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[86\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[86].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_87_w"]
odb::dbBox_create $r [expr {round(1522.22*$dbu)}] [expr {round(2492.3*$dbu)}] [expr {round(1528.7*$dbu)}] [expr {round(2498.78*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_87_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[87\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[87].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_87_r"]
odb::dbBox_create $r [expr {round(1700.44*$dbu)}] [expr {round(2624.04*$dbu)}] [expr {round(1704.76*$dbu)}] [expr {round(2628.36*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_87_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[87\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[87].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_88_w"]
odb::dbBox_create $r [expr {round(1529.24*$dbu)}] [expr {round(2492.3*$dbu)}] [expr {round(1535.72*$dbu)}] [expr {round(2498.78*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_88_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[88\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[88].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_88_r"]
odb::dbBox_create $r [expr {round(1705.84*$dbu)}] [expr {round(2624.04*$dbu)}] [expr {round(1710.16*$dbu)}] [expr {round(2628.36*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_88_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[88\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[88].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_89_w"]
odb::dbBox_create $r [expr {round(1536.26*$dbu)}] [expr {round(2492.3*$dbu)}] [expr {round(1542.74*$dbu)}] [expr {round(2498.78*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_89_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[89\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[89].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_89_r"]
odb::dbBox_create $r [expr {round(1711.24*$dbu)}] [expr {round(2624.04*$dbu)}] [expr {round(1715.56*$dbu)}] [expr {round(2628.36*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_89_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[89\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[89].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_90_w"]
odb::dbBox_create $r [expr {round(1543.28*$dbu)}] [expr {round(2492.3*$dbu)}] [expr {round(1549.76*$dbu)}] [expr {round(2498.78*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_90_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[90\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[90].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_90_r"]
odb::dbBox_create $r [expr {round(1716.64*$dbu)}] [expr {round(2624.04*$dbu)}] [expr {round(1720.96*$dbu)}] [expr {round(2628.36*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_90_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[90\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[90].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_91_w"]
odb::dbBox_create $r [expr {round(1550.3*$dbu)}] [expr {round(2492.3*$dbu)}] [expr {round(1556.78*$dbu)}] [expr {round(2498.78*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_91_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[91\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[91].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_91_r"]
odb::dbBox_create $r [expr {round(1722.04*$dbu)}] [expr {round(2624.04*$dbu)}] [expr {round(1726.36*$dbu)}] [expr {round(2628.36*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_91_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[91\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[91].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_92_w"]
odb::dbBox_create $r [expr {round(1557.32*$dbu)}] [expr {round(2492.3*$dbu)}] [expr {round(1563.8*$dbu)}] [expr {round(2498.78*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_92_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[92\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[92].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_92_r"]
odb::dbBox_create $r [expr {round(1727.44*$dbu)}] [expr {round(2624.04*$dbu)}] [expr {round(1731.76*$dbu)}] [expr {round(2628.36*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_92_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[92\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[92].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_93_w"]
odb::dbBox_create $r [expr {round(1564.34*$dbu)}] [expr {round(2492.3*$dbu)}] [expr {round(1570.82*$dbu)}] [expr {round(2498.78*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_93_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[93\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[93].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_93_r"]
odb::dbBox_create $r [expr {round(1732.84*$dbu)}] [expr {round(2624.04*$dbu)}] [expr {round(1737.16*$dbu)}] [expr {round(2628.36*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_93_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[93\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[93].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_94_w"]
odb::dbBox_create $r [expr {round(1571.36*$dbu)}] [expr {round(2492.3*$dbu)}] [expr {round(1577.84*$dbu)}] [expr {round(2498.78*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_94_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[94\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[94].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_94_r"]
odb::dbBox_create $r [expr {round(1738.24*$dbu)}] [expr {round(2624.04*$dbu)}] [expr {round(1742.56*$dbu)}] [expr {round(2628.36*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_94_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[94\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[94].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_95_w"]
odb::dbBox_create $r [expr {round(1578.38*$dbu)}] [expr {round(2492.3*$dbu)}] [expr {round(1584.86*$dbu)}] [expr {round(2498.78*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_95_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[95\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[95].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_95_r"]
odb::dbBox_create $r [expr {round(1743.64*$dbu)}] [expr {round(2624.04*$dbu)}] [expr {round(1747.96*$dbu)}] [expr {round(2628.36*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_95_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[95\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[95].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_96_w"]
odb::dbBox_create $r [expr {round(1501.16*$dbu)}] [expr {round(2499.32*$dbu)}] [expr {round(1507.64*$dbu)}] [expr {round(2505.8*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_96_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[96\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[96].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_96_r"]
odb::dbBox_create $r [expr {round(1684.24*$dbu)}] [expr {round(2629.44*$dbu)}] [expr {round(1688.56*$dbu)}] [expr {round(2633.76*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_96_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[96\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[96].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_97_w"]
odb::dbBox_create $r [expr {round(1508.18*$dbu)}] [expr {round(2499.32*$dbu)}] [expr {round(1514.66*$dbu)}] [expr {round(2505.8*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_97_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[97\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[97].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_97_r"]
odb::dbBox_create $r [expr {round(1689.64*$dbu)}] [expr {round(2629.44*$dbu)}] [expr {round(1693.96*$dbu)}] [expr {round(2633.76*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_97_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[97\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[97].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_98_w"]
odb::dbBox_create $r [expr {round(1515.2*$dbu)}] [expr {round(2499.32*$dbu)}] [expr {round(1521.68*$dbu)}] [expr {round(2505.8*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_98_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[98\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[98].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_98_r"]
odb::dbBox_create $r [expr {round(1695.04*$dbu)}] [expr {round(2629.44*$dbu)}] [expr {round(1699.36*$dbu)}] [expr {round(2633.76*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_98_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[98\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[98].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_99_w"]
odb::dbBox_create $r [expr {round(1522.22*$dbu)}] [expr {round(2499.32*$dbu)}] [expr {round(1528.7*$dbu)}] [expr {round(2505.8*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_99_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[99\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[99].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_99_r"]
odb::dbBox_create $r [expr {round(1700.44*$dbu)}] [expr {round(2629.44*$dbu)}] [expr {round(1704.76*$dbu)}] [expr {round(2633.76*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_99_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[99\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[99].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_100_w"]
odb::dbBox_create $r [expr {round(1529.24*$dbu)}] [expr {round(2499.32*$dbu)}] [expr {round(1535.72*$dbu)}] [expr {round(2505.8*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_100_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[100\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[100].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_100_r"]
odb::dbBox_create $r [expr {round(1705.84*$dbu)}] [expr {round(2629.44*$dbu)}] [expr {round(1710.16*$dbu)}] [expr {round(2633.76*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_100_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[100\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[100].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_101_w"]
odb::dbBox_create $r [expr {round(1536.26*$dbu)}] [expr {round(2499.32*$dbu)}] [expr {round(1542.74*$dbu)}] [expr {round(2505.8*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_101_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[101\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[101].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_101_r"]
odb::dbBox_create $r [expr {round(1711.24*$dbu)}] [expr {round(2629.44*$dbu)}] [expr {round(1715.56*$dbu)}] [expr {round(2633.76*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_101_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[101\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[101].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_102_w"]
odb::dbBox_create $r [expr {round(1543.28*$dbu)}] [expr {round(2499.32*$dbu)}] [expr {round(1549.76*$dbu)}] [expr {round(2505.8*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_102_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[102\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[102].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_102_r"]
odb::dbBox_create $r [expr {round(1716.64*$dbu)}] [expr {round(2629.44*$dbu)}] [expr {round(1720.96*$dbu)}] [expr {round(2633.76*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_102_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[102\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[102].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_103_w"]
odb::dbBox_create $r [expr {round(1550.3*$dbu)}] [expr {round(2499.32*$dbu)}] [expr {round(1556.78*$dbu)}] [expr {round(2505.8*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_103_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[103\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[103].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_103_r"]
odb::dbBox_create $r [expr {round(1722.04*$dbu)}] [expr {round(2629.44*$dbu)}] [expr {round(1726.36*$dbu)}] [expr {round(2633.76*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_103_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[103\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[103].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_104_w"]
odb::dbBox_create $r [expr {round(1557.32*$dbu)}] [expr {round(2499.32*$dbu)}] [expr {round(1563.8*$dbu)}] [expr {round(2505.8*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_104_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[104\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[104].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_104_r"]
odb::dbBox_create $r [expr {round(1727.44*$dbu)}] [expr {round(2629.44*$dbu)}] [expr {round(1731.76*$dbu)}] [expr {round(2633.76*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_104_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[104\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[104].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_105_w"]
odb::dbBox_create $r [expr {round(1564.34*$dbu)}] [expr {round(2499.32*$dbu)}] [expr {round(1570.82*$dbu)}] [expr {round(2505.8*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_105_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[105\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[105].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_105_r"]
odb::dbBox_create $r [expr {round(1732.84*$dbu)}] [expr {round(2629.44*$dbu)}] [expr {round(1737.16*$dbu)}] [expr {round(2633.76*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_105_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[105\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[105].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_106_w"]
odb::dbBox_create $r [expr {round(1571.36*$dbu)}] [expr {round(2499.32*$dbu)}] [expr {round(1577.84*$dbu)}] [expr {round(2505.8*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_106_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[106\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[106].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_106_r"]
odb::dbBox_create $r [expr {round(1738.24*$dbu)}] [expr {round(2629.44*$dbu)}] [expr {round(1742.56*$dbu)}] [expr {round(2633.76*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_106_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[106\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[106].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_107_w"]
odb::dbBox_create $r [expr {round(1578.38*$dbu)}] [expr {round(2499.32*$dbu)}] [expr {round(1584.86*$dbu)}] [expr {round(2505.8*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_107_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[107\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[107].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_107_r"]
odb::dbBox_create $r [expr {round(1743.64*$dbu)}] [expr {round(2629.44*$dbu)}] [expr {round(1747.96*$dbu)}] [expr {round(2633.76*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_107_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[107\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[107].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_108_w"]
odb::dbBox_create $r [expr {round(1501.16*$dbu)}] [expr {round(2506.34*$dbu)}] [expr {round(1507.64*$dbu)}] [expr {round(2512.82*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_108_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[108\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[108].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_108_r"]
odb::dbBox_create $r [expr {round(1684.24*$dbu)}] [expr {round(2634.84*$dbu)}] [expr {round(1688.56*$dbu)}] [expr {round(2639.16*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_108_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[108\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[108].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_109_w"]
odb::dbBox_create $r [expr {round(1508.18*$dbu)}] [expr {round(2506.34*$dbu)}] [expr {round(1514.66*$dbu)}] [expr {round(2512.82*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_109_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[109\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[109].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_109_r"]
odb::dbBox_create $r [expr {round(1689.64*$dbu)}] [expr {round(2634.84*$dbu)}] [expr {round(1693.96*$dbu)}] [expr {round(2639.16*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_109_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[109\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[109].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_110_w"]
odb::dbBox_create $r [expr {round(1515.2*$dbu)}] [expr {round(2506.34*$dbu)}] [expr {round(1521.68*$dbu)}] [expr {round(2512.82*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_110_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[110\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[110].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_110_r"]
odb::dbBox_create $r [expr {round(1695.04*$dbu)}] [expr {round(2634.84*$dbu)}] [expr {round(1699.36*$dbu)}] [expr {round(2639.16*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_110_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[110\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[110].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_111_w"]
odb::dbBox_create $r [expr {round(1522.22*$dbu)}] [expr {round(2506.34*$dbu)}] [expr {round(1528.7*$dbu)}] [expr {round(2512.82*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_111_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[111\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[111].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_111_r"]
odb::dbBox_create $r [expr {round(1700.44*$dbu)}] [expr {round(2634.84*$dbu)}] [expr {round(1704.76*$dbu)}] [expr {round(2639.16*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_111_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[111\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[111].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_112_w"]
odb::dbBox_create $r [expr {round(1529.24*$dbu)}] [expr {round(2506.34*$dbu)}] [expr {round(1535.72*$dbu)}] [expr {round(2512.82*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_112_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[112\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[112].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_112_r"]
odb::dbBox_create $r [expr {round(1705.84*$dbu)}] [expr {round(2634.84*$dbu)}] [expr {round(1710.16*$dbu)}] [expr {round(2639.16*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_112_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[112\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[112].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_113_w"]
odb::dbBox_create $r [expr {round(1536.26*$dbu)}] [expr {round(2506.34*$dbu)}] [expr {round(1542.74*$dbu)}] [expr {round(2512.82*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_113_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[113\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[113].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_113_r"]
odb::dbBox_create $r [expr {round(1711.24*$dbu)}] [expr {round(2634.84*$dbu)}] [expr {round(1715.56*$dbu)}] [expr {round(2639.16*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_113_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[113\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[113].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_114_w"]
odb::dbBox_create $r [expr {round(1543.28*$dbu)}] [expr {round(2506.34*$dbu)}] [expr {round(1549.76*$dbu)}] [expr {round(2512.82*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_114_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[114\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[114].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_114_r"]
odb::dbBox_create $r [expr {round(1716.64*$dbu)}] [expr {round(2634.84*$dbu)}] [expr {round(1720.96*$dbu)}] [expr {round(2639.16*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_114_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[114\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[114].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_115_w"]
odb::dbBox_create $r [expr {round(1550.3*$dbu)}] [expr {round(2506.34*$dbu)}] [expr {round(1556.78*$dbu)}] [expr {round(2512.82*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_115_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[115\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[115].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_115_r"]
odb::dbBox_create $r [expr {round(1722.04*$dbu)}] [expr {round(2634.84*$dbu)}] [expr {round(1726.36*$dbu)}] [expr {round(2639.16*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_115_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[115\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[115].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_116_w"]
odb::dbBox_create $r [expr {round(1557.32*$dbu)}] [expr {round(2506.34*$dbu)}] [expr {round(1563.8*$dbu)}] [expr {round(2512.82*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_116_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[116\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[116].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_116_r"]
odb::dbBox_create $r [expr {round(1727.44*$dbu)}] [expr {round(2634.84*$dbu)}] [expr {round(1731.76*$dbu)}] [expr {round(2639.16*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_116_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[116\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[116].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_117_w"]
odb::dbBox_create $r [expr {round(1564.34*$dbu)}] [expr {round(2506.34*$dbu)}] [expr {round(1570.82*$dbu)}] [expr {round(2512.82*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_117_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[117\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[117].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_117_r"]
odb::dbBox_create $r [expr {round(1732.84*$dbu)}] [expr {round(2634.84*$dbu)}] [expr {round(1737.16*$dbu)}] [expr {round(2639.16*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_117_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[117\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[117].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_118_w"]
odb::dbBox_create $r [expr {round(1571.36*$dbu)}] [expr {round(2506.34*$dbu)}] [expr {round(1577.84*$dbu)}] [expr {round(2512.82*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_118_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[118\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[118].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_118_r"]
odb::dbBox_create $r [expr {round(1738.24*$dbu)}] [expr {round(2634.84*$dbu)}] [expr {round(1742.56*$dbu)}] [expr {round(2639.16*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_118_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[118\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[118].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_119_w"]
odb::dbBox_create $r [expr {round(1578.38*$dbu)}] [expr {round(2506.34*$dbu)}] [expr {round(1584.86*$dbu)}] [expr {round(2512.82*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_119_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[119\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[119].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_119_r"]
odb::dbBox_create $r [expr {round(1743.64*$dbu)}] [expr {round(2634.84*$dbu)}] [expr {round(1747.96*$dbu)}] [expr {round(2639.16*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_119_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[119\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[119].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_120_w"]
odb::dbBox_create $r [expr {round(1501.16*$dbu)}] [expr {round(2513.36*$dbu)}] [expr {round(1507.64*$dbu)}] [expr {round(2519.84*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_120_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[120\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[120].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_120_r"]
odb::dbBox_create $r [expr {round(1684.24*$dbu)}] [expr {round(2640.24*$dbu)}] [expr {round(1688.56*$dbu)}] [expr {round(2644.56*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_120_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[120\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[120].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_121_w"]
odb::dbBox_create $r [expr {round(1508.18*$dbu)}] [expr {round(2513.36*$dbu)}] [expr {round(1514.66*$dbu)}] [expr {round(2519.84*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_121_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[121\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[121].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_121_r"]
odb::dbBox_create $r [expr {round(1689.64*$dbu)}] [expr {round(2640.24*$dbu)}] [expr {round(1693.96*$dbu)}] [expr {round(2644.56*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_121_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[121\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[121].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_122_w"]
odb::dbBox_create $r [expr {round(1515.2*$dbu)}] [expr {round(2513.36*$dbu)}] [expr {round(1521.68*$dbu)}] [expr {round(2519.84*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_122_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[122\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[122].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_122_r"]
odb::dbBox_create $r [expr {round(1695.04*$dbu)}] [expr {round(2640.24*$dbu)}] [expr {round(1699.36*$dbu)}] [expr {round(2644.56*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_122_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[122\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[122].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_123_w"]
odb::dbBox_create $r [expr {round(1522.22*$dbu)}] [expr {round(2513.36*$dbu)}] [expr {round(1528.7*$dbu)}] [expr {round(2519.84*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_123_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[123\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[123].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_123_r"]
odb::dbBox_create $r [expr {round(1700.44*$dbu)}] [expr {round(2640.24*$dbu)}] [expr {round(1704.76*$dbu)}] [expr {round(2644.56*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_123_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[123\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[123].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_124_w"]
odb::dbBox_create $r [expr {round(1529.24*$dbu)}] [expr {round(2513.36*$dbu)}] [expr {round(1535.72*$dbu)}] [expr {round(2519.84*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_124_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[124\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[124].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_124_r"]
odb::dbBox_create $r [expr {round(1705.84*$dbu)}] [expr {round(2640.24*$dbu)}] [expr {round(1710.16*$dbu)}] [expr {round(2644.56*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_124_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[124\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[124].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_125_w"]
odb::dbBox_create $r [expr {round(1536.26*$dbu)}] [expr {round(2513.36*$dbu)}] [expr {round(1542.74*$dbu)}] [expr {round(2519.84*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_125_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[125\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[125].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_125_r"]
odb::dbBox_create $r [expr {round(1711.24*$dbu)}] [expr {round(2640.24*$dbu)}] [expr {round(1715.56*$dbu)}] [expr {round(2644.56*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_125_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[125\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[125].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_126_w"]
odb::dbBox_create $r [expr {round(1543.28*$dbu)}] [expr {round(2513.36*$dbu)}] [expr {round(1549.76*$dbu)}] [expr {round(2519.84*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_126_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[126\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[126].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_126_r"]
odb::dbBox_create $r [expr {round(1716.64*$dbu)}] [expr {round(2640.24*$dbu)}] [expr {round(1720.96*$dbu)}] [expr {round(2644.56*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_126_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[126\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[126].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_127_w"]
odb::dbBox_create $r [expr {round(1550.3*$dbu)}] [expr {round(2513.36*$dbu)}] [expr {round(1556.78*$dbu)}] [expr {round(2519.84*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_127_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[127\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[127].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_127_r"]
odb::dbBox_create $r [expr {round(1722.04*$dbu)}] [expr {round(2640.24*$dbu)}] [expr {round(1726.36*$dbu)}] [expr {round(2644.56*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_127_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[127\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[127].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_128_w"]
odb::dbBox_create $r [expr {round(1557.32*$dbu)}] [expr {round(2513.36*$dbu)}] [expr {round(1563.8*$dbu)}] [expr {round(2519.84*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_128_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[128\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[128].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_128_r"]
odb::dbBox_create $r [expr {round(1727.44*$dbu)}] [expr {round(2640.24*$dbu)}] [expr {round(1731.76*$dbu)}] [expr {round(2644.56*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_128_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[128\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[128].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_129_w"]
odb::dbBox_create $r [expr {round(1564.34*$dbu)}] [expr {round(2513.36*$dbu)}] [expr {round(1570.82*$dbu)}] [expr {round(2519.84*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_129_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[129\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[129].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_129_r"]
odb::dbBox_create $r [expr {round(1732.84*$dbu)}] [expr {round(2640.24*$dbu)}] [expr {round(1737.16*$dbu)}] [expr {round(2644.56*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_129_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[129\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[129].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_130_w"]
odb::dbBox_create $r [expr {round(1571.36*$dbu)}] [expr {round(2513.36*$dbu)}] [expr {round(1577.84*$dbu)}] [expr {round(2519.84*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_130_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[130\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[130].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_130_r"]
odb::dbBox_create $r [expr {round(1738.24*$dbu)}] [expr {round(2640.24*$dbu)}] [expr {round(1742.56*$dbu)}] [expr {round(2644.56*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_130_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[130\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[130].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_131_w"]
odb::dbBox_create $r [expr {round(1578.38*$dbu)}] [expr {round(2513.36*$dbu)}] [expr {round(1584.86*$dbu)}] [expr {round(2519.84*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_131_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[131\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[131].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_131_r"]
odb::dbBox_create $r [expr {round(1743.64*$dbu)}] [expr {round(2640.24*$dbu)}] [expr {round(1747.96*$dbu)}] [expr {round(2644.56*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_131_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[131\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[131].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_132_w"]
odb::dbBox_create $r [expr {round(1501.16*$dbu)}] [expr {round(2520.38*$dbu)}] [expr {round(1507.64*$dbu)}] [expr {round(2526.86*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_132_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[132\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[132].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_132_r"]
odb::dbBox_create $r [expr {round(1684.24*$dbu)}] [expr {round(2645.64*$dbu)}] [expr {round(1688.56*$dbu)}] [expr {round(2649.96*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_132_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[132\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[132].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_133_w"]
odb::dbBox_create $r [expr {round(1508.18*$dbu)}] [expr {round(2520.38*$dbu)}] [expr {round(1514.66*$dbu)}] [expr {round(2526.86*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_133_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[133\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[133].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_133_r"]
odb::dbBox_create $r [expr {round(1689.64*$dbu)}] [expr {round(2645.64*$dbu)}] [expr {round(1693.96*$dbu)}] [expr {round(2649.96*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_133_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[133\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[133].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_134_w"]
odb::dbBox_create $r [expr {round(1515.2*$dbu)}] [expr {round(2520.38*$dbu)}] [expr {round(1521.68*$dbu)}] [expr {round(2526.86*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_134_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[134\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[134].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_134_r"]
odb::dbBox_create $r [expr {round(1695.04*$dbu)}] [expr {round(2645.64*$dbu)}] [expr {round(1699.36*$dbu)}] [expr {round(2649.96*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_134_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[134\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[134].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_135_w"]
odb::dbBox_create $r [expr {round(1522.22*$dbu)}] [expr {round(2520.38*$dbu)}] [expr {round(1528.7*$dbu)}] [expr {round(2526.86*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_135_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[135\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[135].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_135_r"]
odb::dbBox_create $r [expr {round(1700.44*$dbu)}] [expr {round(2645.64*$dbu)}] [expr {round(1704.76*$dbu)}] [expr {round(2649.96*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_135_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[135\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[135].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_136_w"]
odb::dbBox_create $r [expr {round(1529.24*$dbu)}] [expr {round(2520.38*$dbu)}] [expr {round(1535.72*$dbu)}] [expr {round(2526.86*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_136_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[136\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[136].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_136_r"]
odb::dbBox_create $r [expr {round(1705.84*$dbu)}] [expr {round(2645.64*$dbu)}] [expr {round(1710.16*$dbu)}] [expr {round(2649.96*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_136_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[136\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[136].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_137_w"]
odb::dbBox_create $r [expr {round(1536.26*$dbu)}] [expr {round(2520.38*$dbu)}] [expr {round(1542.74*$dbu)}] [expr {round(2526.86*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_137_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[137\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[137].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_137_r"]
odb::dbBox_create $r [expr {round(1711.24*$dbu)}] [expr {round(2645.64*$dbu)}] [expr {round(1715.56*$dbu)}] [expr {round(2649.96*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_137_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[137\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[137].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_0_w"]
odb::dbBox_create $r [expr {round(1513.16*$dbu)}] [expr {round(2573.16*$dbu)}] [expr {round(1519.64*$dbu)}] [expr {round(2579.64*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_0_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[0\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[0].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_0_r"]
odb::dbBox_create $r [expr {round(1473.24*$dbu)}] [expr {round(2793.24*$dbu)}] [expr {round(1477.56*$dbu)}] [expr {round(2797.56*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_0_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[0\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[0].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_1_w"]
odb::dbBox_create $r [expr {round(1520.18*$dbu)}] [expr {round(2573.16*$dbu)}] [expr {round(1526.66*$dbu)}] [expr {round(2579.64*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_1_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[1\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[1].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_1_r"]
odb::dbBox_create $r [expr {round(1478.1*$dbu)}] [expr {round(2793.24*$dbu)}] [expr {round(1482.42*$dbu)}] [expr {round(2797.56*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_1_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[1\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[1].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_2_w"]
odb::dbBox_create $r [expr {round(1527.2*$dbu)}] [expr {round(2573.16*$dbu)}] [expr {round(1533.68*$dbu)}] [expr {round(2579.64*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_2_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[2\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[2].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_2_r"]
odb::dbBox_create $r [expr {round(1482.96*$dbu)}] [expr {round(2793.24*$dbu)}] [expr {round(1487.28*$dbu)}] [expr {round(2797.56*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_2_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[2\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[2].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_3_w"]
odb::dbBox_create $r [expr {round(1534.22*$dbu)}] [expr {round(2573.16*$dbu)}] [expr {round(1540.7*$dbu)}] [expr {round(2579.64*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_3_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[3\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[3].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_3_r"]
odb::dbBox_create $r [expr {round(1487.82*$dbu)}] [expr {round(2793.24*$dbu)}] [expr {round(1492.14*$dbu)}] [expr {round(2797.56*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_3_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[3\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[3].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_4_w"]
odb::dbBox_create $r [expr {round(1541.24*$dbu)}] [expr {round(2573.16*$dbu)}] [expr {round(1547.72*$dbu)}] [expr {round(2579.64*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_4_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[4\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[4].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_4_r"]
odb::dbBox_create $r [expr {round(1492.68*$dbu)}] [expr {round(2793.24*$dbu)}] [expr {round(1497.0*$dbu)}] [expr {round(2797.56*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_4_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[4\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[4].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_5_w"]
odb::dbBox_create $r [expr {round(1548.26*$dbu)}] [expr {round(2573.16*$dbu)}] [expr {round(1554.74*$dbu)}] [expr {round(2579.64*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_5_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[5\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[5].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_5_r"]
odb::dbBox_create $r [expr {round(1497.54*$dbu)}] [expr {round(2793.24*$dbu)}] [expr {round(1501.86*$dbu)}] [expr {round(2797.56*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_5_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[5\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[5].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_6_w"]
odb::dbBox_create $r [expr {round(1555.28*$dbu)}] [expr {round(2573.16*$dbu)}] [expr {round(1561.76*$dbu)}] [expr {round(2579.64*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_6_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[6\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[6].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_6_r"]
odb::dbBox_create $r [expr {round(1473.24*$dbu)}] [expr {round(2798.1*$dbu)}] [expr {round(1477.56*$dbu)}] [expr {round(2802.42*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_6_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[6\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[6].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_7_w"]
odb::dbBox_create $r [expr {round(1562.3*$dbu)}] [expr {round(2573.16*$dbu)}] [expr {round(1568.78*$dbu)}] [expr {round(2579.64*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_7_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[7\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[7].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_7_r"]
odb::dbBox_create $r [expr {round(1478.1*$dbu)}] [expr {round(2798.1*$dbu)}] [expr {round(1482.42*$dbu)}] [expr {round(2802.42*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_7_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[7\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[7].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_8_w"]
odb::dbBox_create $r [expr {round(1569.32*$dbu)}] [expr {round(2573.16*$dbu)}] [expr {round(1575.8*$dbu)}] [expr {round(2579.64*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_8_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[8\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[8].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_8_r"]
odb::dbBox_create $r [expr {round(1482.96*$dbu)}] [expr {round(2798.1*$dbu)}] [expr {round(1487.28*$dbu)}] [expr {round(2802.42*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_8_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[8\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[8].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_9_w"]
odb::dbBox_create $r [expr {round(1576.34*$dbu)}] [expr {round(2573.16*$dbu)}] [expr {round(1582.82*$dbu)}] [expr {round(2579.64*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_9_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[9\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[9].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_9_r"]
odb::dbBox_create $r [expr {round(1487.82*$dbu)}] [expr {round(2798.1*$dbu)}] [expr {round(1492.14*$dbu)}] [expr {round(2802.42*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_9_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[9\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[9].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_10_w"]
odb::dbBox_create $r [expr {round(1583.36*$dbu)}] [expr {round(2573.16*$dbu)}] [expr {round(1589.84*$dbu)}] [expr {round(2579.64*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_10_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[10\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[10].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_10_r"]
odb::dbBox_create $r [expr {round(1492.68*$dbu)}] [expr {round(2798.1*$dbu)}] [expr {round(1497.0*$dbu)}] [expr {round(2802.42*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_10_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[10\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[10].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_11_w"]
odb::dbBox_create $r [expr {round(1590.38*$dbu)}] [expr {round(2573.16*$dbu)}] [expr {round(1596.86*$dbu)}] [expr {round(2579.64*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_11_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[11\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[11].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_11_r"]
odb::dbBox_create $r [expr {round(1497.54*$dbu)}] [expr {round(2798.1*$dbu)}] [expr {round(1501.86*$dbu)}] [expr {round(2802.42*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_11_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[11\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[11].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_12_w"]
odb::dbBox_create $r [expr {round(1513.16*$dbu)}] [expr {round(2580.18*$dbu)}] [expr {round(1519.64*$dbu)}] [expr {round(2586.66*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_12_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[12\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[12].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_12_r"]
odb::dbBox_create $r [expr {round(1473.24*$dbu)}] [expr {round(2802.96*$dbu)}] [expr {round(1477.56*$dbu)}] [expr {round(2807.28*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_12_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[12\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[12].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_13_w"]
odb::dbBox_create $r [expr {round(1520.18*$dbu)}] [expr {round(2580.18*$dbu)}] [expr {round(1526.66*$dbu)}] [expr {round(2586.66*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_13_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[13\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[13].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_13_r"]
odb::dbBox_create $r [expr {round(1478.1*$dbu)}] [expr {round(2802.96*$dbu)}] [expr {round(1482.42*$dbu)}] [expr {round(2807.28*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_13_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[13\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[13].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_14_w"]
odb::dbBox_create $r [expr {round(1527.2*$dbu)}] [expr {round(2580.18*$dbu)}] [expr {round(1533.68*$dbu)}] [expr {round(2586.66*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_14_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[14\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[14].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_14_r"]
odb::dbBox_create $r [expr {round(1482.96*$dbu)}] [expr {round(2802.96*$dbu)}] [expr {round(1487.28*$dbu)}] [expr {round(2807.28*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_14_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[14\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[14].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_15_w"]
odb::dbBox_create $r [expr {round(1534.22*$dbu)}] [expr {round(2580.18*$dbu)}] [expr {round(1540.7*$dbu)}] [expr {round(2586.66*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_15_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[15\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[15].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_15_r"]
odb::dbBox_create $r [expr {round(1487.82*$dbu)}] [expr {round(2802.96*$dbu)}] [expr {round(1492.14*$dbu)}] [expr {round(2807.28*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_15_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[15\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[15].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_16_w"]
odb::dbBox_create $r [expr {round(1541.24*$dbu)}] [expr {round(2580.18*$dbu)}] [expr {round(1547.72*$dbu)}] [expr {round(2586.66*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_16_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[16\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[16].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_16_r"]
odb::dbBox_create $r [expr {round(1492.68*$dbu)}] [expr {round(2802.96*$dbu)}] [expr {round(1497.0*$dbu)}] [expr {round(2807.28*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_16_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[16\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[16].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_17_w"]
odb::dbBox_create $r [expr {round(1548.26*$dbu)}] [expr {round(2580.18*$dbu)}] [expr {round(1554.74*$dbu)}] [expr {round(2586.66*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_17_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[17\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[17].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_17_r"]
odb::dbBox_create $r [expr {round(1497.54*$dbu)}] [expr {round(2802.96*$dbu)}] [expr {round(1501.86*$dbu)}] [expr {round(2807.28*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_17_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[17\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[17].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_18_w"]
odb::dbBox_create $r [expr {round(1555.28*$dbu)}] [expr {round(2580.18*$dbu)}] [expr {round(1561.76*$dbu)}] [expr {round(2586.66*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_18_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[18\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[18].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_18_r"]
odb::dbBox_create $r [expr {round(1473.24*$dbu)}] [expr {round(2807.82*$dbu)}] [expr {round(1477.56*$dbu)}] [expr {round(2812.14*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_18_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[18\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[18].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_19_w"]
odb::dbBox_create $r [expr {round(1562.3*$dbu)}] [expr {round(2580.18*$dbu)}] [expr {round(1568.78*$dbu)}] [expr {round(2586.66*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_19_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[19\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[19].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_19_r"]
odb::dbBox_create $r [expr {round(1478.1*$dbu)}] [expr {round(2807.82*$dbu)}] [expr {round(1482.42*$dbu)}] [expr {round(2812.14*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_19_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[19\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[19].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_20_w"]
odb::dbBox_create $r [expr {round(1569.32*$dbu)}] [expr {round(2580.18*$dbu)}] [expr {round(1575.8*$dbu)}] [expr {round(2586.66*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_20_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[20\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[20].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_20_r"]
odb::dbBox_create $r [expr {round(1482.96*$dbu)}] [expr {round(2807.82*$dbu)}] [expr {round(1487.28*$dbu)}] [expr {round(2812.14*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_20_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[20\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[20].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_21_w"]
odb::dbBox_create $r [expr {round(1576.34*$dbu)}] [expr {round(2580.18*$dbu)}] [expr {round(1582.82*$dbu)}] [expr {round(2586.66*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_21_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[21\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[21].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_21_r"]
odb::dbBox_create $r [expr {round(1487.82*$dbu)}] [expr {round(2807.82*$dbu)}] [expr {round(1492.14*$dbu)}] [expr {round(2812.14*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_21_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[21\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[21].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_22_w"]
odb::dbBox_create $r [expr {round(1583.36*$dbu)}] [expr {round(2580.18*$dbu)}] [expr {round(1589.84*$dbu)}] [expr {round(2586.66*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_22_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[22\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[22].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_22_r"]
odb::dbBox_create $r [expr {round(1492.68*$dbu)}] [expr {round(2807.82*$dbu)}] [expr {round(1497.0*$dbu)}] [expr {round(2812.14*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_22_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[22\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[22].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_23_w"]
odb::dbBox_create $r [expr {round(1590.38*$dbu)}] [expr {round(2580.18*$dbu)}] [expr {round(1596.86*$dbu)}] [expr {round(2586.66*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_23_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[23\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[23].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_23_r"]
odb::dbBox_create $r [expr {round(1497.54*$dbu)}] [expr {round(2807.82*$dbu)}] [expr {round(1501.86*$dbu)}] [expr {round(2812.14*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_23_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[23\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[23].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_24_w"]
odb::dbBox_create $r [expr {round(1513.16*$dbu)}] [expr {round(2587.2*$dbu)}] [expr {round(1519.64*$dbu)}] [expr {round(2593.68*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_24_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[24\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[24].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_24_r"]
odb::dbBox_create $r [expr {round(1473.24*$dbu)}] [expr {round(2812.68*$dbu)}] [expr {round(1477.56*$dbu)}] [expr {round(2817.0*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_24_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[24\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[24].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_25_w"]
odb::dbBox_create $r [expr {round(1520.18*$dbu)}] [expr {round(2587.2*$dbu)}] [expr {round(1526.66*$dbu)}] [expr {round(2593.68*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_25_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[25\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[25].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_25_r"]
odb::dbBox_create $r [expr {round(1478.1*$dbu)}] [expr {round(2812.68*$dbu)}] [expr {round(1482.42*$dbu)}] [expr {round(2817.0*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_25_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[25\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[25].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_26_w"]
odb::dbBox_create $r [expr {round(1527.2*$dbu)}] [expr {round(2587.2*$dbu)}] [expr {round(1533.68*$dbu)}] [expr {round(2593.68*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_26_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[26\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[26].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_26_r"]
odb::dbBox_create $r [expr {round(1482.96*$dbu)}] [expr {round(2812.68*$dbu)}] [expr {round(1487.28*$dbu)}] [expr {round(2817.0*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_26_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[26\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[26].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_27_w"]
odb::dbBox_create $r [expr {round(1534.22*$dbu)}] [expr {round(2587.2*$dbu)}] [expr {round(1540.7*$dbu)}] [expr {round(2593.68*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_27_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[27\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[27].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_27_r"]
odb::dbBox_create $r [expr {round(1487.82*$dbu)}] [expr {round(2812.68*$dbu)}] [expr {round(1492.14*$dbu)}] [expr {round(2817.0*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_27_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[27\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[27].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_28_w"]
odb::dbBox_create $r [expr {round(1541.24*$dbu)}] [expr {round(2587.2*$dbu)}] [expr {round(1547.72*$dbu)}] [expr {round(2593.68*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_28_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[28\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[28].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_28_r"]
odb::dbBox_create $r [expr {round(1492.68*$dbu)}] [expr {round(2812.68*$dbu)}] [expr {round(1497.0*$dbu)}] [expr {round(2817.0*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_28_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[28\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[28].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_29_w"]
odb::dbBox_create $r [expr {round(1548.26*$dbu)}] [expr {round(2587.2*$dbu)}] [expr {round(1554.74*$dbu)}] [expr {round(2593.68*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_29_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[29\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[29].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_29_r"]
odb::dbBox_create $r [expr {round(1497.54*$dbu)}] [expr {round(2812.68*$dbu)}] [expr {round(1501.86*$dbu)}] [expr {round(2817.0*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_29_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[29\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[29].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_30_w"]
odb::dbBox_create $r [expr {round(1555.28*$dbu)}] [expr {round(2587.2*$dbu)}] [expr {round(1561.76*$dbu)}] [expr {round(2593.68*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_30_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[30\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[30].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_30_r"]
odb::dbBox_create $r [expr {round(1473.24*$dbu)}] [expr {round(2817.54*$dbu)}] [expr {round(1477.56*$dbu)}] [expr {round(2821.86*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_30_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[30\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[30].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_31_w"]
odb::dbBox_create $r [expr {round(1562.3*$dbu)}] [expr {round(2587.2*$dbu)}] [expr {round(1568.78*$dbu)}] [expr {round(2593.68*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_31_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[31\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[31].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_31_r"]
odb::dbBox_create $r [expr {round(1478.1*$dbu)}] [expr {round(2817.54*$dbu)}] [expr {round(1482.42*$dbu)}] [expr {round(2821.86*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_31_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[31\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[31].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_32_w"]
odb::dbBox_create $r [expr {round(1569.32*$dbu)}] [expr {round(2587.2*$dbu)}] [expr {round(1575.8*$dbu)}] [expr {round(2593.68*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_32_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[32\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[32].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_32_r"]
odb::dbBox_create $r [expr {round(1482.96*$dbu)}] [expr {round(2817.54*$dbu)}] [expr {round(1487.28*$dbu)}] [expr {round(2821.86*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_32_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[32\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[32].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_33_w"]
odb::dbBox_create $r [expr {round(1576.34*$dbu)}] [expr {round(2587.2*$dbu)}] [expr {round(1582.82*$dbu)}] [expr {round(2593.68*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_33_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[33\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[33].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_33_r"]
odb::dbBox_create $r [expr {round(1487.82*$dbu)}] [expr {round(2817.54*$dbu)}] [expr {round(1492.14*$dbu)}] [expr {round(2821.86*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_33_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[33\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[33].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_34_w"]
odb::dbBox_create $r [expr {round(1583.36*$dbu)}] [expr {round(2587.2*$dbu)}] [expr {round(1589.84*$dbu)}] [expr {round(2593.68*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_34_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[34\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[34].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_34_r"]
odb::dbBox_create $r [expr {round(1492.68*$dbu)}] [expr {round(2817.54*$dbu)}] [expr {round(1497.0*$dbu)}] [expr {round(2821.86*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_34_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[34\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[34].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_35_w"]
odb::dbBox_create $r [expr {round(1590.38*$dbu)}] [expr {round(2587.2*$dbu)}] [expr {round(1596.86*$dbu)}] [expr {round(2593.68*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_35_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[35\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[35].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_35_r"]
odb::dbBox_create $r [expr {round(1497.54*$dbu)}] [expr {round(2817.54*$dbu)}] [expr {round(1501.86*$dbu)}] [expr {round(2821.86*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_35_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[35\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[35].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_36_w"]
odb::dbBox_create $r [expr {round(1513.16*$dbu)}] [expr {round(2594.22*$dbu)}] [expr {round(1519.64*$dbu)}] [expr {round(2600.7*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_36_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[36\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[36].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_36_r"]
odb::dbBox_create $r [expr {round(1473.24*$dbu)}] [expr {round(2822.4*$dbu)}] [expr {round(1477.56*$dbu)}] [expr {round(2826.72*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_36_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[36\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[36].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_37_w"]
odb::dbBox_create $r [expr {round(1520.18*$dbu)}] [expr {round(2594.22*$dbu)}] [expr {round(1526.66*$dbu)}] [expr {round(2600.7*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_37_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[37\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[37].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_37_r"]
odb::dbBox_create $r [expr {round(1478.1*$dbu)}] [expr {round(2822.4*$dbu)}] [expr {round(1482.42*$dbu)}] [expr {round(2826.72*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_37_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[37\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[37].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_38_w"]
odb::dbBox_create $r [expr {round(1527.2*$dbu)}] [expr {round(2594.22*$dbu)}] [expr {round(1533.68*$dbu)}] [expr {round(2600.7*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_38_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[38\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[38].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_38_r"]
odb::dbBox_create $r [expr {round(1482.96*$dbu)}] [expr {round(2822.4*$dbu)}] [expr {round(1487.28*$dbu)}] [expr {round(2826.72*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_38_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[38\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[38].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_39_w"]
odb::dbBox_create $r [expr {round(1534.22*$dbu)}] [expr {round(2594.22*$dbu)}] [expr {round(1540.7*$dbu)}] [expr {round(2600.7*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_39_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[39\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[39].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_39_r"]
odb::dbBox_create $r [expr {round(1487.82*$dbu)}] [expr {round(2822.4*$dbu)}] [expr {round(1492.14*$dbu)}] [expr {round(2826.72*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_39_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[39\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[39].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_40_w"]
odb::dbBox_create $r [expr {round(1541.24*$dbu)}] [expr {round(2594.22*$dbu)}] [expr {round(1547.72*$dbu)}] [expr {round(2600.7*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_40_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[40\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[40].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_40_r"]
odb::dbBox_create $r [expr {round(1492.68*$dbu)}] [expr {round(2822.4*$dbu)}] [expr {round(1497.0*$dbu)}] [expr {round(2826.72*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_40_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[40\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[40].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_41_w"]
odb::dbBox_create $r [expr {round(1548.26*$dbu)}] [expr {round(2594.22*$dbu)}] [expr {round(1554.74*$dbu)}] [expr {round(2600.7*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_41_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[41\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[41].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_41_r"]
odb::dbBox_create $r [expr {round(1497.54*$dbu)}] [expr {round(2822.4*$dbu)}] [expr {round(1501.86*$dbu)}] [expr {round(2826.72*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_41_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[41\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[41].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_42_w"]
odb::dbBox_create $r [expr {round(1555.28*$dbu)}] [expr {round(2594.22*$dbu)}] [expr {round(1561.76*$dbu)}] [expr {round(2600.7*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_42_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[42\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[42].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_42_r"]
odb::dbBox_create $r [expr {round(1473.24*$dbu)}] [expr {round(2827.26*$dbu)}] [expr {round(1477.56*$dbu)}] [expr {round(2831.58*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_42_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[42\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[42].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_43_w"]
odb::dbBox_create $r [expr {round(1562.3*$dbu)}] [expr {round(2594.22*$dbu)}] [expr {round(1568.78*$dbu)}] [expr {round(2600.7*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_43_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[43\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[43].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_43_r"]
odb::dbBox_create $r [expr {round(1478.1*$dbu)}] [expr {round(2827.26*$dbu)}] [expr {round(1482.42*$dbu)}] [expr {round(2831.58*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_43_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[43\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[43].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_44_w"]
odb::dbBox_create $r [expr {round(1569.32*$dbu)}] [expr {round(2594.22*$dbu)}] [expr {round(1575.8*$dbu)}] [expr {round(2600.7*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_44_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[44\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[44].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_44_r"]
odb::dbBox_create $r [expr {round(1482.96*$dbu)}] [expr {round(2827.26*$dbu)}] [expr {round(1487.28*$dbu)}] [expr {round(2831.58*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_44_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[44\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[44].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_45_w"]
odb::dbBox_create $r [expr {round(1576.34*$dbu)}] [expr {round(2594.22*$dbu)}] [expr {round(1582.82*$dbu)}] [expr {round(2600.7*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_45_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[45\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[45].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_45_r"]
odb::dbBox_create $r [expr {round(1487.82*$dbu)}] [expr {round(2827.26*$dbu)}] [expr {round(1492.14*$dbu)}] [expr {round(2831.58*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_45_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[45\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[45].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_46_w"]
odb::dbBox_create $r [expr {round(1583.36*$dbu)}] [expr {round(2594.22*$dbu)}] [expr {round(1589.84*$dbu)}] [expr {round(2600.7*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_46_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[46\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[46].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_46_r"]
odb::dbBox_create $r [expr {round(1492.68*$dbu)}] [expr {round(2827.26*$dbu)}] [expr {round(1497.0*$dbu)}] [expr {round(2831.58*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_46_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[46\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[46].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_47_w"]
odb::dbBox_create $r [expr {round(1590.38*$dbu)}] [expr {round(2594.22*$dbu)}] [expr {round(1596.86*$dbu)}] [expr {round(2600.7*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_47_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[47\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[47].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_47_r"]
odb::dbBox_create $r [expr {round(1497.54*$dbu)}] [expr {round(2827.26*$dbu)}] [expr {round(1501.86*$dbu)}] [expr {round(2831.58*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_47_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[47\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[47].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_48_w"]
odb::dbBox_create $r [expr {round(1513.16*$dbu)}] [expr {round(2601.24*$dbu)}] [expr {round(1519.64*$dbu)}] [expr {round(2607.72*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_48_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[48\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[48].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_48_r"]
odb::dbBox_create $r [expr {round(1473.24*$dbu)}] [expr {round(2832.12*$dbu)}] [expr {round(1477.56*$dbu)}] [expr {round(2836.44*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_48_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[48\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[48].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_49_w"]
odb::dbBox_create $r [expr {round(1520.18*$dbu)}] [expr {round(2601.24*$dbu)}] [expr {round(1526.66*$dbu)}] [expr {round(2607.72*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_49_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[49\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[49].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_49_r"]
odb::dbBox_create $r [expr {round(1478.1*$dbu)}] [expr {round(2832.12*$dbu)}] [expr {round(1482.42*$dbu)}] [expr {round(2836.44*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_49_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[49\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[49].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_50_w"]
odb::dbBox_create $r [expr {round(1527.2*$dbu)}] [expr {round(2601.24*$dbu)}] [expr {round(1533.68*$dbu)}] [expr {round(2607.72*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_50_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[50\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[50].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_50_r"]
odb::dbBox_create $r [expr {round(1482.96*$dbu)}] [expr {round(2832.12*$dbu)}] [expr {round(1487.28*$dbu)}] [expr {round(2836.44*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_50_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[50\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[50].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_51_w"]
odb::dbBox_create $r [expr {round(1534.22*$dbu)}] [expr {round(2601.24*$dbu)}] [expr {round(1540.7*$dbu)}] [expr {round(2607.72*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_51_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[51\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[51].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_51_r"]
odb::dbBox_create $r [expr {round(1487.82*$dbu)}] [expr {round(2832.12*$dbu)}] [expr {round(1492.14*$dbu)}] [expr {round(2836.44*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_51_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[51\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[51].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_52_w"]
odb::dbBox_create $r [expr {round(1541.24*$dbu)}] [expr {round(2601.24*$dbu)}] [expr {round(1547.72*$dbu)}] [expr {round(2607.72*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_52_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[52\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[52].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_52_r"]
odb::dbBox_create $r [expr {round(1492.68*$dbu)}] [expr {round(2832.12*$dbu)}] [expr {round(1497.0*$dbu)}] [expr {round(2836.44*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_52_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[52\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[52].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_53_w"]
odb::dbBox_create $r [expr {round(1548.26*$dbu)}] [expr {round(2601.24*$dbu)}] [expr {round(1554.74*$dbu)}] [expr {round(2607.72*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_53_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[53\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[53].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_53_r"]
odb::dbBox_create $r [expr {round(1497.54*$dbu)}] [expr {round(2832.12*$dbu)}] [expr {round(1501.86*$dbu)}] [expr {round(2836.44*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_53_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[53\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[53].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_54_w"]
odb::dbBox_create $r [expr {round(1555.28*$dbu)}] [expr {round(2601.24*$dbu)}] [expr {round(1561.76*$dbu)}] [expr {round(2607.72*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_54_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[54\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[54].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_54_r"]
odb::dbBox_create $r [expr {round(1473.24*$dbu)}] [expr {round(2836.98*$dbu)}] [expr {round(1477.56*$dbu)}] [expr {round(2841.3*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_54_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[54\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[54].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_55_w"]
odb::dbBox_create $r [expr {round(1562.3*$dbu)}] [expr {round(2601.24*$dbu)}] [expr {round(1568.78*$dbu)}] [expr {round(2607.72*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_55_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[55\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[55].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_55_r"]
odb::dbBox_create $r [expr {round(1478.1*$dbu)}] [expr {round(2836.98*$dbu)}] [expr {round(1482.42*$dbu)}] [expr {round(2841.3*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_55_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[55\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[55].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_56_w"]
odb::dbBox_create $r [expr {round(1569.32*$dbu)}] [expr {round(2601.24*$dbu)}] [expr {round(1575.8*$dbu)}] [expr {round(2607.72*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_56_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[56\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[56].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_56_r"]
odb::dbBox_create $r [expr {round(1482.96*$dbu)}] [expr {round(2836.98*$dbu)}] [expr {round(1487.28*$dbu)}] [expr {round(2841.3*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_56_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[56\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[56].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_57_w"]
odb::dbBox_create $r [expr {round(1576.34*$dbu)}] [expr {round(2601.24*$dbu)}] [expr {round(1582.82*$dbu)}] [expr {round(2607.72*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_57_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[57\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[57].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_57_r"]
odb::dbBox_create $r [expr {round(1487.82*$dbu)}] [expr {round(2836.98*$dbu)}] [expr {round(1492.14*$dbu)}] [expr {round(2841.3*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_57_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[57\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[57].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_58_w"]
odb::dbBox_create $r [expr {round(1583.36*$dbu)}] [expr {round(2601.24*$dbu)}] [expr {round(1589.84*$dbu)}] [expr {round(2607.72*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_58_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[58\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[58].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_58_r"]
odb::dbBox_create $r [expr {round(1492.68*$dbu)}] [expr {round(2836.98*$dbu)}] [expr {round(1497.0*$dbu)}] [expr {round(2841.3*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_58_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[58\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[58].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_59_w"]
odb::dbBox_create $r [expr {round(1590.38*$dbu)}] [expr {round(2601.24*$dbu)}] [expr {round(1596.86*$dbu)}] [expr {round(2607.72*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_59_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[59\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[59].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_59_r"]
odb::dbBox_create $r [expr {round(1497.54*$dbu)}] [expr {round(2836.98*$dbu)}] [expr {round(1501.86*$dbu)}] [expr {round(2841.3*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_59_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[59\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[59].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_60_w"]
odb::dbBox_create $r [expr {round(1513.16*$dbu)}] [expr {round(2608.26*$dbu)}] [expr {round(1519.64*$dbu)}] [expr {round(2614.74*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_60_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[60\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[60].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_60_r"]
odb::dbBox_create $r [expr {round(1473.24*$dbu)}] [expr {round(2841.84*$dbu)}] [expr {round(1477.56*$dbu)}] [expr {round(2846.16*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_60_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[60\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[60].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_61_w"]
odb::dbBox_create $r [expr {round(1520.18*$dbu)}] [expr {round(2608.26*$dbu)}] [expr {round(1526.66*$dbu)}] [expr {round(2614.74*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_61_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[61\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[61].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_61_r"]
odb::dbBox_create $r [expr {round(1478.1*$dbu)}] [expr {round(2841.84*$dbu)}] [expr {round(1482.42*$dbu)}] [expr {round(2846.16*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_61_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[61\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[61].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_62_w"]
odb::dbBox_create $r [expr {round(1527.2*$dbu)}] [expr {round(2608.26*$dbu)}] [expr {round(1533.68*$dbu)}] [expr {round(2614.74*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_62_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[62\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[62].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_62_r"]
odb::dbBox_create $r [expr {round(1482.96*$dbu)}] [expr {round(2841.84*$dbu)}] [expr {round(1487.28*$dbu)}] [expr {round(2846.16*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_62_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[62\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[62].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_63_w"]
odb::dbBox_create $r [expr {round(1534.22*$dbu)}] [expr {round(2608.26*$dbu)}] [expr {round(1540.7*$dbu)}] [expr {round(2614.74*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_63_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[63\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[63].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_63_r"]
odb::dbBox_create $r [expr {round(1487.82*$dbu)}] [expr {round(2841.84*$dbu)}] [expr {round(1492.14*$dbu)}] [expr {round(2846.16*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_63_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[63\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[63].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_64_w"]
odb::dbBox_create $r [expr {round(1541.24*$dbu)}] [expr {round(2608.26*$dbu)}] [expr {round(1547.72*$dbu)}] [expr {round(2614.74*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_64_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[64\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[64].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_64_r"]
odb::dbBox_create $r [expr {round(1492.68*$dbu)}] [expr {round(2841.84*$dbu)}] [expr {round(1497.0*$dbu)}] [expr {round(2846.16*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_64_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[64\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[64].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_65_w"]
odb::dbBox_create $r [expr {round(1548.26*$dbu)}] [expr {round(2608.26*$dbu)}] [expr {round(1554.74*$dbu)}] [expr {round(2614.74*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_65_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[65\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[65].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_65_r"]
odb::dbBox_create $r [expr {round(1497.54*$dbu)}] [expr {round(2841.84*$dbu)}] [expr {round(1501.86*$dbu)}] [expr {round(2846.16*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_65_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[65\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[65].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_66_w"]
odb::dbBox_create $r [expr {round(1555.28*$dbu)}] [expr {round(2608.26*$dbu)}] [expr {round(1561.76*$dbu)}] [expr {round(2614.74*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_66_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[66\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[66].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_66_r"]
odb::dbBox_create $r [expr {round(1473.24*$dbu)}] [expr {round(2846.7*$dbu)}] [expr {round(1477.56*$dbu)}] [expr {round(2851.02*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_66_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[66\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[66].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_67_w"]
odb::dbBox_create $r [expr {round(1562.3*$dbu)}] [expr {round(2608.26*$dbu)}] [expr {round(1568.78*$dbu)}] [expr {round(2614.74*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_67_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[67\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[67].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_67_r"]
odb::dbBox_create $r [expr {round(1478.1*$dbu)}] [expr {round(2846.7*$dbu)}] [expr {round(1482.42*$dbu)}] [expr {round(2851.02*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_67_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[67\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[67].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_68_w"]
odb::dbBox_create $r [expr {round(1569.32*$dbu)}] [expr {round(2608.26*$dbu)}] [expr {round(1575.8*$dbu)}] [expr {round(2614.74*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_68_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[68\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[68].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_68_r"]
odb::dbBox_create $r [expr {round(1482.96*$dbu)}] [expr {round(2846.7*$dbu)}] [expr {round(1487.28*$dbu)}] [expr {round(2851.02*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_68_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[68\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[68].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_69_w"]
odb::dbBox_create $r [expr {round(1576.34*$dbu)}] [expr {round(2608.26*$dbu)}] [expr {round(1582.82*$dbu)}] [expr {round(2614.74*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_69_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[69\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[69].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_69_r"]
odb::dbBox_create $r [expr {round(1487.82*$dbu)}] [expr {round(2846.7*$dbu)}] [expr {round(1492.14*$dbu)}] [expr {round(2851.02*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_69_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[69\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[69].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_70_w"]
odb::dbBox_create $r [expr {round(1583.36*$dbu)}] [expr {round(2608.26*$dbu)}] [expr {round(1589.84*$dbu)}] [expr {round(2614.74*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_70_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[70\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[70].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_70_r"]
odb::dbBox_create $r [expr {round(1492.68*$dbu)}] [expr {round(2846.7*$dbu)}] [expr {round(1497.0*$dbu)}] [expr {round(2851.02*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_70_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[70\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[70].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_71_w"]
odb::dbBox_create $r [expr {round(1590.38*$dbu)}] [expr {round(2608.26*$dbu)}] [expr {round(1596.86*$dbu)}] [expr {round(2614.74*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_71_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[71\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[71].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_71_r"]
odb::dbBox_create $r [expr {round(1497.54*$dbu)}] [expr {round(2846.7*$dbu)}] [expr {round(1501.86*$dbu)}] [expr {round(2851.02*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_71_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[71\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[71].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_72_w"]
odb::dbBox_create $r [expr {round(1513.16*$dbu)}] [expr {round(2615.28*$dbu)}] [expr {round(1519.64*$dbu)}] [expr {round(2621.76*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_72_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[72\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[72].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_72_r"]
odb::dbBox_create $r [expr {round(1473.24*$dbu)}] [expr {round(2851.56*$dbu)}] [expr {round(1477.56*$dbu)}] [expr {round(2855.88*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_72_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[72\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[72].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_73_w"]
odb::dbBox_create $r [expr {round(1520.18*$dbu)}] [expr {round(2615.28*$dbu)}] [expr {round(1526.66*$dbu)}] [expr {round(2621.76*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_73_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[73\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[73].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_73_r"]
odb::dbBox_create $r [expr {round(1478.1*$dbu)}] [expr {round(2851.56*$dbu)}] [expr {round(1482.42*$dbu)}] [expr {round(2855.88*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_73_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[73\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[73].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_74_w"]
odb::dbBox_create $r [expr {round(1527.2*$dbu)}] [expr {round(2615.28*$dbu)}] [expr {round(1533.68*$dbu)}] [expr {round(2621.76*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_74_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[74\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[74].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_74_r"]
odb::dbBox_create $r [expr {round(1482.96*$dbu)}] [expr {round(2851.56*$dbu)}] [expr {round(1487.28*$dbu)}] [expr {round(2855.88*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_74_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[74\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[74].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_75_w"]
odb::dbBox_create $r [expr {round(1534.22*$dbu)}] [expr {round(2615.28*$dbu)}] [expr {round(1540.7*$dbu)}] [expr {round(2621.76*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_75_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[75\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[75].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_75_r"]
odb::dbBox_create $r [expr {round(1487.82*$dbu)}] [expr {round(2851.56*$dbu)}] [expr {round(1492.14*$dbu)}] [expr {round(2855.88*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_75_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[75\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[75].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_76_w"]
odb::dbBox_create $r [expr {round(1541.24*$dbu)}] [expr {round(2615.28*$dbu)}] [expr {round(1547.72*$dbu)}] [expr {round(2621.76*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_76_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[76\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[76].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_76_r"]
odb::dbBox_create $r [expr {round(1492.68*$dbu)}] [expr {round(2851.56*$dbu)}] [expr {round(1497.0*$dbu)}] [expr {round(2855.88*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_76_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[76\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[76].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_77_w"]
odb::dbBox_create $r [expr {round(1548.26*$dbu)}] [expr {round(2615.28*$dbu)}] [expr {round(1554.74*$dbu)}] [expr {round(2621.76*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_77_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[77\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[77].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_77_r"]
odb::dbBox_create $r [expr {round(1497.54*$dbu)}] [expr {round(2851.56*$dbu)}] [expr {round(1501.86*$dbu)}] [expr {round(2855.88*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_77_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[77\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[77].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_78_w"]
odb::dbBox_create $r [expr {round(1555.28*$dbu)}] [expr {round(2615.28*$dbu)}] [expr {round(1561.76*$dbu)}] [expr {round(2621.76*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_78_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[78\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[78].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_78_r"]
odb::dbBox_create $r [expr {round(1473.24*$dbu)}] [expr {round(2856.42*$dbu)}] [expr {round(1477.56*$dbu)}] [expr {round(2860.74*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_78_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[78\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[78].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_79_w"]
odb::dbBox_create $r [expr {round(1562.3*$dbu)}] [expr {round(2615.28*$dbu)}] [expr {round(1568.78*$dbu)}] [expr {round(2621.76*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_79_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[79\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[79].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_79_r"]
odb::dbBox_create $r [expr {round(1478.1*$dbu)}] [expr {round(2856.42*$dbu)}] [expr {round(1482.42*$dbu)}] [expr {round(2860.74*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_79_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[79\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[79].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_80_w"]
odb::dbBox_create $r [expr {round(1569.32*$dbu)}] [expr {round(2615.28*$dbu)}] [expr {round(1575.8*$dbu)}] [expr {round(2621.76*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_80_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[80\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[80].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_80_r"]
odb::dbBox_create $r [expr {round(1482.96*$dbu)}] [expr {round(2856.42*$dbu)}] [expr {round(1487.28*$dbu)}] [expr {round(2860.74*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_80_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[80\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[80].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_81_w"]
odb::dbBox_create $r [expr {round(1576.34*$dbu)}] [expr {round(2615.28*$dbu)}] [expr {round(1582.82*$dbu)}] [expr {round(2621.76*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_81_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[81\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[81].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_81_r"]
odb::dbBox_create $r [expr {round(1487.82*$dbu)}] [expr {round(2856.42*$dbu)}] [expr {round(1492.14*$dbu)}] [expr {round(2860.74*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_81_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[81\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[81].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_82_w"]
odb::dbBox_create $r [expr {round(1583.36*$dbu)}] [expr {round(2615.28*$dbu)}] [expr {round(1589.84*$dbu)}] [expr {round(2621.76*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_82_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[82\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[82].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_82_r"]
odb::dbBox_create $r [expr {round(1492.68*$dbu)}] [expr {round(2856.42*$dbu)}] [expr {round(1497.0*$dbu)}] [expr {round(2860.74*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_82_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[82\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[82].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_83_w"]
odb::dbBox_create $r [expr {round(1590.38*$dbu)}] [expr {round(2615.28*$dbu)}] [expr {round(1596.86*$dbu)}] [expr {round(2621.76*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_83_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[83\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[83].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_83_r"]
odb::dbBox_create $r [expr {round(1497.54*$dbu)}] [expr {round(2856.42*$dbu)}] [expr {round(1501.86*$dbu)}] [expr {round(2860.74*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_83_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[83\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[83].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_84_w"]
odb::dbBox_create $r [expr {round(1513.16*$dbu)}] [expr {round(2622.3*$dbu)}] [expr {round(1519.64*$dbu)}] [expr {round(2628.78*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_84_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[84\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[84].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_84_r"]
odb::dbBox_create $r [expr {round(1473.24*$dbu)}] [expr {round(2861.28*$dbu)}] [expr {round(1477.56*$dbu)}] [expr {round(2865.6*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_84_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[84\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[84].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_85_w"]
odb::dbBox_create $r [expr {round(1520.18*$dbu)}] [expr {round(2622.3*$dbu)}] [expr {round(1526.66*$dbu)}] [expr {round(2628.78*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_85_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[85\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[85].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_85_r"]
odb::dbBox_create $r [expr {round(1478.1*$dbu)}] [expr {round(2861.28*$dbu)}] [expr {round(1482.42*$dbu)}] [expr {round(2865.6*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_85_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[85\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[85].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_86_w"]
odb::dbBox_create $r [expr {round(1527.2*$dbu)}] [expr {round(2622.3*$dbu)}] [expr {round(1533.68*$dbu)}] [expr {round(2628.78*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_86_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[86\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[86].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_86_r"]
odb::dbBox_create $r [expr {round(1482.96*$dbu)}] [expr {round(2861.28*$dbu)}] [expr {round(1487.28*$dbu)}] [expr {round(2865.6*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_86_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[86\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[86].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_87_w"]
odb::dbBox_create $r [expr {round(1534.22*$dbu)}] [expr {round(2622.3*$dbu)}] [expr {round(1540.7*$dbu)}] [expr {round(2628.78*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_87_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[87\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[87].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_87_r"]
odb::dbBox_create $r [expr {round(1487.82*$dbu)}] [expr {round(2861.28*$dbu)}] [expr {round(1492.14*$dbu)}] [expr {round(2865.6*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_87_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[87\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[87].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_88_w"]
odb::dbBox_create $r [expr {round(1541.24*$dbu)}] [expr {round(2622.3*$dbu)}] [expr {round(1547.72*$dbu)}] [expr {round(2628.78*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_88_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[88\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[88].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_88_r"]
odb::dbBox_create $r [expr {round(1492.68*$dbu)}] [expr {round(2861.28*$dbu)}] [expr {round(1497.0*$dbu)}] [expr {round(2865.6*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_88_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[88\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[88].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_89_w"]
odb::dbBox_create $r [expr {round(1548.26*$dbu)}] [expr {round(2622.3*$dbu)}] [expr {round(1554.74*$dbu)}] [expr {round(2628.78*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_89_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[89\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[89].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_89_r"]
odb::dbBox_create $r [expr {round(1497.54*$dbu)}] [expr {round(2861.28*$dbu)}] [expr {round(1501.86*$dbu)}] [expr {round(2865.6*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_89_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[89\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[89].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_90_w"]
odb::dbBox_create $r [expr {round(1555.28*$dbu)}] [expr {round(2622.3*$dbu)}] [expr {round(1561.76*$dbu)}] [expr {round(2628.78*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_90_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[90\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[90].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_90_r"]
odb::dbBox_create $r [expr {round(1473.24*$dbu)}] [expr {round(2866.14*$dbu)}] [expr {round(1477.56*$dbu)}] [expr {round(2870.46*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_90_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[90\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[90].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_91_w"]
odb::dbBox_create $r [expr {round(1562.3*$dbu)}] [expr {round(2622.3*$dbu)}] [expr {round(1568.78*$dbu)}] [expr {round(2628.78*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_91_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[91\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[91].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_91_r"]
odb::dbBox_create $r [expr {round(1478.1*$dbu)}] [expr {round(2866.14*$dbu)}] [expr {round(1482.42*$dbu)}] [expr {round(2870.46*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_91_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[91\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[91].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_92_w"]
odb::dbBox_create $r [expr {round(1569.32*$dbu)}] [expr {round(2622.3*$dbu)}] [expr {round(1575.8*$dbu)}] [expr {round(2628.78*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_92_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[92\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[92].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_92_r"]
odb::dbBox_create $r [expr {round(1482.96*$dbu)}] [expr {round(2866.14*$dbu)}] [expr {round(1487.28*$dbu)}] [expr {round(2870.46*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_92_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[92\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[92].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_93_w"]
odb::dbBox_create $r [expr {round(1576.34*$dbu)}] [expr {round(2622.3*$dbu)}] [expr {round(1582.82*$dbu)}] [expr {round(2628.78*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_93_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[93\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[93].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_93_r"]
odb::dbBox_create $r [expr {round(1487.82*$dbu)}] [expr {round(2866.14*$dbu)}] [expr {round(1492.14*$dbu)}] [expr {round(2870.46*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_93_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[93\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[93].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_94_w"]
odb::dbBox_create $r [expr {round(1583.36*$dbu)}] [expr {round(2622.3*$dbu)}] [expr {round(1589.84*$dbu)}] [expr {round(2628.78*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_94_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[94\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[94].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_94_r"]
odb::dbBox_create $r [expr {round(1492.68*$dbu)}] [expr {round(2866.14*$dbu)}] [expr {round(1497.0*$dbu)}] [expr {round(2870.46*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_94_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[94\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[94].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_95_w"]
odb::dbBox_create $r [expr {round(1590.38*$dbu)}] [expr {round(2622.3*$dbu)}] [expr {round(1596.86*$dbu)}] [expr {round(2628.78*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_95_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[95\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[95].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_95_r"]
odb::dbBox_create $r [expr {round(1497.54*$dbu)}] [expr {round(2866.14*$dbu)}] [expr {round(1501.86*$dbu)}] [expr {round(2870.46*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_95_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[95\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[95].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_96_w"]
odb::dbBox_create $r [expr {round(1513.16*$dbu)}] [expr {round(2629.32*$dbu)}] [expr {round(1519.64*$dbu)}] [expr {round(2635.8*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_96_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[96\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[96].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_96_r"]
odb::dbBox_create $r [expr {round(1473.24*$dbu)}] [expr {round(2871.0*$dbu)}] [expr {round(1477.56*$dbu)}] [expr {round(2875.32*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_96_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[96\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[96].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_97_w"]
odb::dbBox_create $r [expr {round(1520.18*$dbu)}] [expr {round(2629.32*$dbu)}] [expr {round(1526.66*$dbu)}] [expr {round(2635.8*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_97_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[97\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[97].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_97_r"]
odb::dbBox_create $r [expr {round(1478.1*$dbu)}] [expr {round(2871.0*$dbu)}] [expr {round(1482.42*$dbu)}] [expr {round(2875.32*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_97_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[97\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[97].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_98_w"]
odb::dbBox_create $r [expr {round(1527.2*$dbu)}] [expr {round(2629.32*$dbu)}] [expr {round(1533.68*$dbu)}] [expr {round(2635.8*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_98_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[98\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[98].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_98_r"]
odb::dbBox_create $r [expr {round(1482.96*$dbu)}] [expr {round(2871.0*$dbu)}] [expr {round(1487.28*$dbu)}] [expr {round(2875.32*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_98_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[98\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[98].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_99_w"]
odb::dbBox_create $r [expr {round(1534.22*$dbu)}] [expr {round(2629.32*$dbu)}] [expr {round(1540.7*$dbu)}] [expr {round(2635.8*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_99_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[99\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[99].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_99_r"]
odb::dbBox_create $r [expr {round(1487.82*$dbu)}] [expr {round(2871.0*$dbu)}] [expr {round(1492.14*$dbu)}] [expr {round(2875.32*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_99_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[99\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[99].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_100_w"]
odb::dbBox_create $r [expr {round(1541.24*$dbu)}] [expr {round(2629.32*$dbu)}] [expr {round(1547.72*$dbu)}] [expr {round(2635.8*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_100_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[100\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[100].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_100_r"]
odb::dbBox_create $r [expr {round(1492.68*$dbu)}] [expr {round(2871.0*$dbu)}] [expr {round(1497.0*$dbu)}] [expr {round(2875.32*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_100_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[100\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[100].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_101_w"]
odb::dbBox_create $r [expr {round(1548.26*$dbu)}] [expr {round(2629.32*$dbu)}] [expr {round(1554.74*$dbu)}] [expr {round(2635.8*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_101_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[101\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[101].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_101_r"]
odb::dbBox_create $r [expr {round(1497.54*$dbu)}] [expr {round(2871.0*$dbu)}] [expr {round(1501.86*$dbu)}] [expr {round(2875.32*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_101_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[101\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[101].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_102_w"]
odb::dbBox_create $r [expr {round(1555.28*$dbu)}] [expr {round(2629.32*$dbu)}] [expr {round(1561.76*$dbu)}] [expr {round(2635.8*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_102_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[102\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[102].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_102_r"]
odb::dbBox_create $r [expr {round(1473.24*$dbu)}] [expr {round(2875.86*$dbu)}] [expr {round(1477.56*$dbu)}] [expr {round(2880.18*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_102_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[102\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[102].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_103_w"]
odb::dbBox_create $r [expr {round(1562.3*$dbu)}] [expr {round(2629.32*$dbu)}] [expr {round(1568.78*$dbu)}] [expr {round(2635.8*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_103_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[103\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[103].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_103_r"]
odb::dbBox_create $r [expr {round(1478.1*$dbu)}] [expr {round(2875.86*$dbu)}] [expr {round(1482.42*$dbu)}] [expr {round(2880.18*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_103_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[103\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[103].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_104_w"]
odb::dbBox_create $r [expr {round(1569.32*$dbu)}] [expr {round(2629.32*$dbu)}] [expr {round(1575.8*$dbu)}] [expr {round(2635.8*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_104_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[104\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[104].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_104_r"]
odb::dbBox_create $r [expr {round(1482.96*$dbu)}] [expr {round(2875.86*$dbu)}] [expr {round(1487.28*$dbu)}] [expr {round(2880.18*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_104_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[104\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[104].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_105_w"]
odb::dbBox_create $r [expr {round(1576.34*$dbu)}] [expr {round(2629.32*$dbu)}] [expr {round(1582.82*$dbu)}] [expr {round(2635.8*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_105_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[105\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[105].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_105_r"]
odb::dbBox_create $r [expr {round(1487.82*$dbu)}] [expr {round(2875.86*$dbu)}] [expr {round(1492.14*$dbu)}] [expr {round(2880.18*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_105_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[105\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[105].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_106_w"]
odb::dbBox_create $r [expr {round(1583.36*$dbu)}] [expr {round(2629.32*$dbu)}] [expr {round(1589.84*$dbu)}] [expr {round(2635.8*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_106_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[106\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[106].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_106_r"]
odb::dbBox_create $r [expr {round(1492.68*$dbu)}] [expr {round(2875.86*$dbu)}] [expr {round(1497.0*$dbu)}] [expr {round(2880.18*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_106_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[106\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[106].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_107_w"]
odb::dbBox_create $r [expr {round(1590.38*$dbu)}] [expr {round(2629.32*$dbu)}] [expr {round(1596.86*$dbu)}] [expr {round(2635.8*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_107_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[107\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[107].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_107_r"]
odb::dbBox_create $r [expr {round(1497.54*$dbu)}] [expr {round(2875.86*$dbu)}] [expr {round(1501.86*$dbu)}] [expr {round(2880.18*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_107_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[107\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[107].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_108_w"]
odb::dbBox_create $r [expr {round(1513.16*$dbu)}] [expr {round(2636.34*$dbu)}] [expr {round(1519.64*$dbu)}] [expr {round(2642.82*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_108_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[108\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[108].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_108_r"]
odb::dbBox_create $r [expr {round(1473.24*$dbu)}] [expr {round(2880.72*$dbu)}] [expr {round(1477.56*$dbu)}] [expr {round(2885.04*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_108_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[108\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[108].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_109_w"]
odb::dbBox_create $r [expr {round(1520.18*$dbu)}] [expr {round(2636.34*$dbu)}] [expr {round(1526.66*$dbu)}] [expr {round(2642.82*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_109_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[109\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[109].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_109_r"]
odb::dbBox_create $r [expr {round(1478.1*$dbu)}] [expr {round(2880.72*$dbu)}] [expr {round(1482.42*$dbu)}] [expr {round(2885.04*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_109_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[109\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[109].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_110_w"]
odb::dbBox_create $r [expr {round(1527.2*$dbu)}] [expr {round(2636.34*$dbu)}] [expr {round(1533.68*$dbu)}] [expr {round(2642.82*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_110_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[110\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[110].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_110_r"]
odb::dbBox_create $r [expr {round(1482.96*$dbu)}] [expr {round(2880.72*$dbu)}] [expr {round(1487.28*$dbu)}] [expr {round(2885.04*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_110_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[110\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[110].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_111_w"]
odb::dbBox_create $r [expr {round(1534.22*$dbu)}] [expr {round(2636.34*$dbu)}] [expr {round(1540.7*$dbu)}] [expr {round(2642.82*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_111_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[111\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[111].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_111_r"]
odb::dbBox_create $r [expr {round(1487.82*$dbu)}] [expr {round(2880.72*$dbu)}] [expr {round(1492.14*$dbu)}] [expr {round(2885.04*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_111_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[111\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[111].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_112_w"]
odb::dbBox_create $r [expr {round(1541.24*$dbu)}] [expr {round(2636.34*$dbu)}] [expr {round(1547.72*$dbu)}] [expr {round(2642.82*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_112_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[112\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[112].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_112_r"]
odb::dbBox_create $r [expr {round(1492.68*$dbu)}] [expr {round(2880.72*$dbu)}] [expr {round(1497.0*$dbu)}] [expr {round(2885.04*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_112_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[112\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[112].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_113_w"]
odb::dbBox_create $r [expr {round(1548.26*$dbu)}] [expr {round(2636.34*$dbu)}] [expr {round(1554.74*$dbu)}] [expr {round(2642.82*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_113_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[113\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[113].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_113_r"]
odb::dbBox_create $r [expr {round(1497.54*$dbu)}] [expr {round(2880.72*$dbu)}] [expr {round(1501.86*$dbu)}] [expr {round(2885.04*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_113_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[113\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[113].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_114_w"]
odb::dbBox_create $r [expr {round(1555.28*$dbu)}] [expr {round(2636.34*$dbu)}] [expr {round(1561.76*$dbu)}] [expr {round(2642.82*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_114_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[114\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[114].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_114_r"]
odb::dbBox_create $r [expr {round(1473.24*$dbu)}] [expr {round(2885.58*$dbu)}] [expr {round(1477.56*$dbu)}] [expr {round(2889.9*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_114_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[114\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[114].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_115_w"]
odb::dbBox_create $r [expr {round(1562.3*$dbu)}] [expr {round(2636.34*$dbu)}] [expr {round(1568.78*$dbu)}] [expr {round(2642.82*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_115_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[115\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[115].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_115_r"]
odb::dbBox_create $r [expr {round(1478.1*$dbu)}] [expr {round(2885.58*$dbu)}] [expr {round(1482.42*$dbu)}] [expr {round(2889.9*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_115_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[115\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[115].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_116_w"]
odb::dbBox_create $r [expr {round(1569.32*$dbu)}] [expr {round(2636.34*$dbu)}] [expr {round(1575.8*$dbu)}] [expr {round(2642.82*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_116_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[116\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[116].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_116_r"]
odb::dbBox_create $r [expr {round(1482.96*$dbu)}] [expr {round(2885.58*$dbu)}] [expr {round(1487.28*$dbu)}] [expr {round(2889.9*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_116_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[116\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[116].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_117_w"]
odb::dbBox_create $r [expr {round(1576.34*$dbu)}] [expr {round(2636.34*$dbu)}] [expr {round(1582.82*$dbu)}] [expr {round(2642.82*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_117_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[117\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[117].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_117_r"]
odb::dbBox_create $r [expr {round(1487.82*$dbu)}] [expr {round(2885.58*$dbu)}] [expr {round(1492.14*$dbu)}] [expr {round(2889.9*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_117_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[117\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[117].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_118_w"]
odb::dbBox_create $r [expr {round(1583.36*$dbu)}] [expr {round(2636.34*$dbu)}] [expr {round(1589.84*$dbu)}] [expr {round(2642.82*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_118_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[118\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[118].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_118_r"]
odb::dbBox_create $r [expr {round(1492.68*$dbu)}] [expr {round(2885.58*$dbu)}] [expr {round(1497.0*$dbu)}] [expr {round(2889.9*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_118_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[118\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[118].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_119_w"]
odb::dbBox_create $r [expr {round(1590.38*$dbu)}] [expr {round(2636.34*$dbu)}] [expr {round(1596.86*$dbu)}] [expr {round(2642.82*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_119_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[119\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[119].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_119_r"]
odb::dbBox_create $r [expr {round(1497.54*$dbu)}] [expr {round(2885.58*$dbu)}] [expr {round(1501.86*$dbu)}] [expr {round(2889.9*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_119_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[119\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[119].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_120_w"]
odb::dbBox_create $r [expr {round(1513.16*$dbu)}] [expr {round(2643.36*$dbu)}] [expr {round(1519.64*$dbu)}] [expr {round(2649.84*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_120_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[120\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[120].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_120_r"]
odb::dbBox_create $r [expr {round(1473.24*$dbu)}] [expr {round(2890.44*$dbu)}] [expr {round(1477.56*$dbu)}] [expr {round(2894.76*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_120_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[120\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[120].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_121_w"]
odb::dbBox_create $r [expr {round(1520.18*$dbu)}] [expr {round(2643.36*$dbu)}] [expr {round(1526.66*$dbu)}] [expr {round(2649.84*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_121_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[121\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[121].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_121_r"]
odb::dbBox_create $r [expr {round(1478.1*$dbu)}] [expr {round(2890.44*$dbu)}] [expr {round(1482.42*$dbu)}] [expr {round(2894.76*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_121_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[121\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[121].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_122_w"]
odb::dbBox_create $r [expr {round(1527.2*$dbu)}] [expr {round(2643.36*$dbu)}] [expr {round(1533.68*$dbu)}] [expr {round(2649.84*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_122_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[122\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[122].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_122_r"]
odb::dbBox_create $r [expr {round(1482.96*$dbu)}] [expr {round(2890.44*$dbu)}] [expr {round(1487.28*$dbu)}] [expr {round(2894.76*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_122_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[122\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[122].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_123_w"]
odb::dbBox_create $r [expr {round(1534.22*$dbu)}] [expr {round(2643.36*$dbu)}] [expr {round(1540.7*$dbu)}] [expr {round(2649.84*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_123_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[123\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[123].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_123_r"]
odb::dbBox_create $r [expr {round(1487.82*$dbu)}] [expr {round(2890.44*$dbu)}] [expr {round(1492.14*$dbu)}] [expr {round(2894.76*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_123_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[123\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[123].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_124_w"]
odb::dbBox_create $r [expr {round(1541.24*$dbu)}] [expr {round(2643.36*$dbu)}] [expr {round(1547.72*$dbu)}] [expr {round(2649.84*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_124_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[124\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[124].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_124_r"]
odb::dbBox_create $r [expr {round(1492.68*$dbu)}] [expr {round(2890.44*$dbu)}] [expr {round(1497.0*$dbu)}] [expr {round(2894.76*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_124_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[124\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[124].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_125_w"]
odb::dbBox_create $r [expr {round(1548.26*$dbu)}] [expr {round(2643.36*$dbu)}] [expr {round(1554.74*$dbu)}] [expr {round(2649.84*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_125_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[125\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[125].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_125_r"]
odb::dbBox_create $r [expr {round(1497.54*$dbu)}] [expr {round(2890.44*$dbu)}] [expr {round(1501.86*$dbu)}] [expr {round(2894.76*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_125_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[125\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[125].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_126_w"]
odb::dbBox_create $r [expr {round(1555.28*$dbu)}] [expr {round(2643.36*$dbu)}] [expr {round(1561.76*$dbu)}] [expr {round(2649.84*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_126_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[126\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[126].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_126_r"]
odb::dbBox_create $r [expr {round(1473.24*$dbu)}] [expr {round(2895.3*$dbu)}] [expr {round(1477.56*$dbu)}] [expr {round(2899.62*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_126_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[126\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[126].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_127_w"]
odb::dbBox_create $r [expr {round(1562.3*$dbu)}] [expr {round(2643.36*$dbu)}] [expr {round(1568.78*$dbu)}] [expr {round(2649.84*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_127_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[127\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[127].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_127_r"]
odb::dbBox_create $r [expr {round(1478.1*$dbu)}] [expr {round(2895.3*$dbu)}] [expr {round(1482.42*$dbu)}] [expr {round(2899.62*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_127_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[127\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[127].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_128_w"]
odb::dbBox_create $r [expr {round(1569.32*$dbu)}] [expr {round(2643.36*$dbu)}] [expr {round(1575.8*$dbu)}] [expr {round(2649.84*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_128_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[128\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[128].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_128_r"]
odb::dbBox_create $r [expr {round(1482.96*$dbu)}] [expr {round(2895.3*$dbu)}] [expr {round(1487.28*$dbu)}] [expr {round(2899.62*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_128_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[128\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[128].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_129_w"]
odb::dbBox_create $r [expr {round(1576.34*$dbu)}] [expr {round(2643.36*$dbu)}] [expr {round(1582.82*$dbu)}] [expr {round(2649.84*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_129_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[129\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[129].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_129_r"]
odb::dbBox_create $r [expr {round(1487.82*$dbu)}] [expr {round(2895.3*$dbu)}] [expr {round(1492.14*$dbu)}] [expr {round(2899.62*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_129_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[129\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[129].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_130_w"]
odb::dbBox_create $r [expr {round(1583.36*$dbu)}] [expr {round(2643.36*$dbu)}] [expr {round(1589.84*$dbu)}] [expr {round(2649.84*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_130_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[130\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[130].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_130_r"]
odb::dbBox_create $r [expr {round(1492.68*$dbu)}] [expr {round(2895.3*$dbu)}] [expr {round(1497.0*$dbu)}] [expr {round(2899.62*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_130_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[130\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[130].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_131_w"]
odb::dbBox_create $r [expr {round(1590.38*$dbu)}] [expr {round(2643.36*$dbu)}] [expr {round(1596.86*$dbu)}] [expr {round(2649.84*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_131_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[131\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[131].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_131_r"]
odb::dbBox_create $r [expr {round(1497.54*$dbu)}] [expr {round(2895.3*$dbu)}] [expr {round(1501.86*$dbu)}] [expr {round(2899.62*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_131_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[131\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[131].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_132_w"]
odb::dbBox_create $r [expr {round(1513.16*$dbu)}] [expr {round(2650.38*$dbu)}] [expr {round(1519.64*$dbu)}] [expr {round(2656.86*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_132_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[132\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[132].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_132_r"]
odb::dbBox_create $r [expr {round(1473.24*$dbu)}] [expr {round(2900.16*$dbu)}] [expr {round(1477.56*$dbu)}] [expr {round(2904.48*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_132_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[132\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[132].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_133_w"]
odb::dbBox_create $r [expr {round(1520.18*$dbu)}] [expr {round(2650.38*$dbu)}] [expr {round(1526.66*$dbu)}] [expr {round(2656.86*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_133_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[133\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[133].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_133_r"]
odb::dbBox_create $r [expr {round(1478.1*$dbu)}] [expr {round(2900.16*$dbu)}] [expr {round(1482.42*$dbu)}] [expr {round(2904.48*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_133_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[133\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[133].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_134_w"]
odb::dbBox_create $r [expr {round(1527.2*$dbu)}] [expr {round(2650.38*$dbu)}] [expr {round(1533.68*$dbu)}] [expr {round(2656.86*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_134_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[134\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[134].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_134_r"]
odb::dbBox_create $r [expr {round(1482.96*$dbu)}] [expr {round(2900.16*$dbu)}] [expr {round(1487.28*$dbu)}] [expr {round(2904.48*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_134_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[134\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[134].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_135_w"]
odb::dbBox_create $r [expr {round(1534.22*$dbu)}] [expr {round(2650.38*$dbu)}] [expr {round(1540.7*$dbu)}] [expr {round(2656.86*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_135_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[135\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[135].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_135_r"]
odb::dbBox_create $r [expr {round(1487.82*$dbu)}] [expr {round(2900.16*$dbu)}] [expr {round(1492.14*$dbu)}] [expr {round(2904.48*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_135_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[135\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[135].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_136_w"]
odb::dbBox_create $r [expr {round(1541.24*$dbu)}] [expr {round(2650.38*$dbu)}] [expr {round(1547.72*$dbu)}] [expr {round(2656.86*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_136_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[136\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[136].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_136_r"]
odb::dbBox_create $r [expr {round(1492.68*$dbu)}] [expr {round(2900.16*$dbu)}] [expr {round(1497.0*$dbu)}] [expr {round(2904.48*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_136_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[136\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[136].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_137_w"]
odb::dbBox_create $r [expr {round(1548.26*$dbu)}] [expr {round(2650.38*$dbu)}] [expr {round(1554.74*$dbu)}] [expr {round(2656.86*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_137_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[137\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[137].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_137_r"]
odb::dbBox_create $r [expr {round(1497.54*$dbu)}] [expr {round(2900.16*$dbu)}] [expr {round(1501.86*$dbu)}] [expr {round(2904.48*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_137_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[137\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[137].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_wv_w"]
odb::dbBox_create $r [expr {round(1543.28*$dbu)}] [expr {round(2520.38*$dbu)}] [expr {round(1549.76*$dbu)}] [expr {round(2526.86*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_wv_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_7_w[./]g_chunk\[0\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_7_w.g_chunk[0].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_wv_r"]
odb::dbBox_create $r [expr {round(1716.64*$dbu)}] [expr {round(2645.64*$dbu)}] [expr {round(1720.96*$dbu)}] [expr {round(2649.96*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_wv_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_7_r[./]g_chunk\[0\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_7_r.g_chunk[0].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_rv_w"]
odb::dbBox_create $r [expr {round(1555.28*$dbu)}] [expr {round(2650.38*$dbu)}] [expr {round(1561.76*$dbu)}] [expr {round(2656.86*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_rv_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_4_w[./]g_chunk\[0\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_4_w.g_chunk[0].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_rv_r"]
odb::dbBox_create $r [expr {round(1473.24*$dbu)}] [expr {round(2905.02*$dbu)}] [expr {round(1477.56*$dbu)}] [expr {round(2909.34*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_rv_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_4_r[./]g_chunk\[0\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_4_r.g_chunk[0].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_fault_w"]
odb::dbBox_create $r [expr {round(1562.3*$dbu)}] [expr {round(2650.38*$dbu)}] [expr {round(1568.78*$dbu)}] [expr {round(2656.86*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_fault_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_6_w[./]g_chunk\[0\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_6_w.g_chunk[0].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_fault_r"]
odb::dbBox_create $r [expr {round(1478.1*$dbu)}] [expr {round(2905.02*$dbu)}] [expr {round(1482.42*$dbu)}] [expr {round(2909.34*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_fault_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_6_r[./]g_chunk\[0\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_6_r.g_chunk[0].u_local"}
