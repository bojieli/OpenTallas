# Existing E2 groups, cell-inclusive <=405 model. MUST audit post DPL/CTS; do not release these fences silently.
set b [ord::get_db_block]
set dbu [$b getDbUnitsPerMicron]
set r [odb::dbRegion_create $b "ml_e2_WD_0_w"]
odb::dbBox_create $r [expr {round(1414.76*$dbu)}] [expr {round(2356.76*$dbu)}] [expr {round(1421.24*$dbu)}] [expr {round(2363.24*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_0_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[0\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[0].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_0_r"]
odb::dbBox_create $r [expr {round(1597.84*$dbu)}] [expr {round(2499.84*$dbu)}] [expr {round(1602.16*$dbu)}] [expr {round(2504.16*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_0_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[0\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[0].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_1_w"]
odb::dbBox_create $r [expr {round(1421.78*$dbu)}] [expr {round(2356.76*$dbu)}] [expr {round(1428.26*$dbu)}] [expr {round(2363.24*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_1_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[1\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[1].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_1_r"]
odb::dbBox_create $r [expr {round(1603.24*$dbu)}] [expr {round(2499.84*$dbu)}] [expr {round(1607.56*$dbu)}] [expr {round(2504.16*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_1_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[1\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[1].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_2_w"]
odb::dbBox_create $r [expr {round(1428.8*$dbu)}] [expr {round(2356.76*$dbu)}] [expr {round(1435.28*$dbu)}] [expr {round(2363.24*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_2_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[2\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[2].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_2_r"]
odb::dbBox_create $r [expr {round(1608.64*$dbu)}] [expr {round(2499.84*$dbu)}] [expr {round(1612.96*$dbu)}] [expr {round(2504.16*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_2_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[2\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[2].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_3_w"]
odb::dbBox_create $r [expr {round(1435.82*$dbu)}] [expr {round(2356.76*$dbu)}] [expr {round(1442.3*$dbu)}] [expr {round(2363.24*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_3_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[3\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[3].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_3_r"]
odb::dbBox_create $r [expr {round(1614.04*$dbu)}] [expr {round(2499.84*$dbu)}] [expr {round(1618.36*$dbu)}] [expr {round(2504.16*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_3_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[3\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[3].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_4_w"]
odb::dbBox_create $r [expr {round(1442.84*$dbu)}] [expr {round(2356.76*$dbu)}] [expr {round(1449.32*$dbu)}] [expr {round(2363.24*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_4_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[4\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[4].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_4_r"]
odb::dbBox_create $r [expr {round(1619.44*$dbu)}] [expr {round(2499.84*$dbu)}] [expr {round(1623.76*$dbu)}] [expr {round(2504.16*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_4_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[4\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[4].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_5_w"]
odb::dbBox_create $r [expr {round(1449.86*$dbu)}] [expr {round(2356.76*$dbu)}] [expr {round(1456.34*$dbu)}] [expr {round(2363.24*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_5_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[5\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[5].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_5_r"]
odb::dbBox_create $r [expr {round(1624.84*$dbu)}] [expr {round(2499.84*$dbu)}] [expr {round(1629.16*$dbu)}] [expr {round(2504.16*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_5_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[5\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[5].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_6_w"]
odb::dbBox_create $r [expr {round(1456.88*$dbu)}] [expr {round(2356.76*$dbu)}] [expr {round(1463.36*$dbu)}] [expr {round(2363.24*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_6_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[6\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[6].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_6_r"]
odb::dbBox_create $r [expr {round(1630.24*$dbu)}] [expr {round(2499.84*$dbu)}] [expr {round(1634.56*$dbu)}] [expr {round(2504.16*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_6_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[6\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[6].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_7_w"]
odb::dbBox_create $r [expr {round(1463.9*$dbu)}] [expr {round(2356.76*$dbu)}] [expr {round(1470.38*$dbu)}] [expr {round(2363.24*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_7_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[7\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[7].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_7_r"]
odb::dbBox_create $r [expr {round(1635.64*$dbu)}] [expr {round(2499.84*$dbu)}] [expr {round(1639.96*$dbu)}] [expr {round(2504.16*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_7_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[7\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[7].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_8_w"]
odb::dbBox_create $r [expr {round(1470.92*$dbu)}] [expr {round(2356.76*$dbu)}] [expr {round(1477.4*$dbu)}] [expr {round(2363.24*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_8_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[8\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[8].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_8_r"]
odb::dbBox_create $r [expr {round(1641.04*$dbu)}] [expr {round(2499.84*$dbu)}] [expr {round(1645.36*$dbu)}] [expr {round(2504.16*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_8_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[8\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[8].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_9_w"]
odb::dbBox_create $r [expr {round(1477.94*$dbu)}] [expr {round(2356.76*$dbu)}] [expr {round(1484.42*$dbu)}] [expr {round(2363.24*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_9_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[9\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[9].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_9_r"]
odb::dbBox_create $r [expr {round(1646.44*$dbu)}] [expr {round(2499.84*$dbu)}] [expr {round(1650.76*$dbu)}] [expr {round(2504.16*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_9_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[9\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[9].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_10_w"]
odb::dbBox_create $r [expr {round(1484.96*$dbu)}] [expr {round(2356.76*$dbu)}] [expr {round(1491.44*$dbu)}] [expr {round(2363.24*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_10_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[10\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[10].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_10_r"]
odb::dbBox_create $r [expr {round(1651.84*$dbu)}] [expr {round(2499.84*$dbu)}] [expr {round(1656.16*$dbu)}] [expr {round(2504.16*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_10_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[10\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[10].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_11_w"]
odb::dbBox_create $r [expr {round(1491.98*$dbu)}] [expr {round(2356.76*$dbu)}] [expr {round(1498.46*$dbu)}] [expr {round(2363.24*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_11_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[11\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[11].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_11_r"]
odb::dbBox_create $r [expr {round(1657.24*$dbu)}] [expr {round(2499.84*$dbu)}] [expr {round(1661.56*$dbu)}] [expr {round(2504.16*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_11_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[11\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[11].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_12_w"]
odb::dbBox_create $r [expr {round(1414.76*$dbu)}] [expr {round(2363.78*$dbu)}] [expr {round(1421.24*$dbu)}] [expr {round(2370.26*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_12_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[12\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[12].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_12_r"]
odb::dbBox_create $r [expr {round(1597.84*$dbu)}] [expr {round(2505.24*$dbu)}] [expr {round(1602.16*$dbu)}] [expr {round(2509.56*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_12_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[12\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[12].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_13_w"]
odb::dbBox_create $r [expr {round(1421.78*$dbu)}] [expr {round(2363.78*$dbu)}] [expr {round(1428.26*$dbu)}] [expr {round(2370.26*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_13_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[13\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[13].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_13_r"]
odb::dbBox_create $r [expr {round(1603.24*$dbu)}] [expr {round(2505.24*$dbu)}] [expr {round(1607.56*$dbu)}] [expr {round(2509.56*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_13_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[13\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[13].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_14_w"]
odb::dbBox_create $r [expr {round(1428.8*$dbu)}] [expr {round(2363.78*$dbu)}] [expr {round(1435.28*$dbu)}] [expr {round(2370.26*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_14_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[14\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[14].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_14_r"]
odb::dbBox_create $r [expr {round(1608.64*$dbu)}] [expr {round(2505.24*$dbu)}] [expr {round(1612.96*$dbu)}] [expr {round(2509.56*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_14_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[14\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[14].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_15_w"]
odb::dbBox_create $r [expr {round(1435.82*$dbu)}] [expr {round(2363.78*$dbu)}] [expr {round(1442.3*$dbu)}] [expr {round(2370.26*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_15_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[15\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[15].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_15_r"]
odb::dbBox_create $r [expr {round(1614.04*$dbu)}] [expr {round(2505.24*$dbu)}] [expr {round(1618.36*$dbu)}] [expr {round(2509.56*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_15_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[15\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[15].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_16_w"]
odb::dbBox_create $r [expr {round(1442.84*$dbu)}] [expr {round(2363.78*$dbu)}] [expr {round(1449.32*$dbu)}] [expr {round(2370.26*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_16_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[16\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[16].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_16_r"]
odb::dbBox_create $r [expr {round(1619.44*$dbu)}] [expr {round(2505.24*$dbu)}] [expr {round(1623.76*$dbu)}] [expr {round(2509.56*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_16_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[16\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[16].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_17_w"]
odb::dbBox_create $r [expr {round(1449.86*$dbu)}] [expr {round(2363.78*$dbu)}] [expr {round(1456.34*$dbu)}] [expr {round(2370.26*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_17_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[17\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[17].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_17_r"]
odb::dbBox_create $r [expr {round(1624.84*$dbu)}] [expr {round(2505.24*$dbu)}] [expr {round(1629.16*$dbu)}] [expr {round(2509.56*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_17_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[17\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[17].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_18_w"]
odb::dbBox_create $r [expr {round(1456.88*$dbu)}] [expr {round(2363.78*$dbu)}] [expr {round(1463.36*$dbu)}] [expr {round(2370.26*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_18_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[18\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[18].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_18_r"]
odb::dbBox_create $r [expr {round(1630.24*$dbu)}] [expr {round(2505.24*$dbu)}] [expr {round(1634.56*$dbu)}] [expr {round(2509.56*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_18_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[18\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[18].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_19_w"]
odb::dbBox_create $r [expr {round(1463.9*$dbu)}] [expr {round(2363.78*$dbu)}] [expr {round(1470.38*$dbu)}] [expr {round(2370.26*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_19_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[19\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[19].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_19_r"]
odb::dbBox_create $r [expr {round(1635.64*$dbu)}] [expr {round(2505.24*$dbu)}] [expr {round(1639.96*$dbu)}] [expr {round(2509.56*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_19_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[19\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[19].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_20_w"]
odb::dbBox_create $r [expr {round(1470.92*$dbu)}] [expr {round(2363.78*$dbu)}] [expr {round(1477.4*$dbu)}] [expr {round(2370.26*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_20_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[20\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[20].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_20_r"]
odb::dbBox_create $r [expr {round(1641.04*$dbu)}] [expr {round(2505.24*$dbu)}] [expr {round(1645.36*$dbu)}] [expr {round(2509.56*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_20_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[20\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[20].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_21_w"]
odb::dbBox_create $r [expr {round(1477.94*$dbu)}] [expr {round(2363.78*$dbu)}] [expr {round(1484.42*$dbu)}] [expr {round(2370.26*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_21_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[21\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[21].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_21_r"]
odb::dbBox_create $r [expr {round(1646.44*$dbu)}] [expr {round(2505.24*$dbu)}] [expr {round(1650.76*$dbu)}] [expr {round(2509.56*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_21_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[21\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[21].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_22_w"]
odb::dbBox_create $r [expr {round(1484.96*$dbu)}] [expr {round(2363.78*$dbu)}] [expr {round(1491.44*$dbu)}] [expr {round(2370.26*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_22_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[22\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[22].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_22_r"]
odb::dbBox_create $r [expr {round(1651.84*$dbu)}] [expr {round(2505.24*$dbu)}] [expr {round(1656.16*$dbu)}] [expr {round(2509.56*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_22_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[22\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[22].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_23_w"]
odb::dbBox_create $r [expr {round(1491.98*$dbu)}] [expr {round(2363.78*$dbu)}] [expr {round(1498.46*$dbu)}] [expr {round(2370.26*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_23_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[23\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[23].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_23_r"]
odb::dbBox_create $r [expr {round(1657.24*$dbu)}] [expr {round(2505.24*$dbu)}] [expr {round(1661.56*$dbu)}] [expr {round(2509.56*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_23_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[23\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[23].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_24_w"]
odb::dbBox_create $r [expr {round(1414.76*$dbu)}] [expr {round(2370.8*$dbu)}] [expr {round(1421.24*$dbu)}] [expr {round(2377.28*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_24_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[24\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[24].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_24_r"]
odb::dbBox_create $r [expr {round(1597.84*$dbu)}] [expr {round(2510.64*$dbu)}] [expr {round(1602.16*$dbu)}] [expr {round(2514.96*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_24_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[24\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[24].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_25_w"]
odb::dbBox_create $r [expr {round(1421.78*$dbu)}] [expr {round(2370.8*$dbu)}] [expr {round(1428.26*$dbu)}] [expr {round(2377.28*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_25_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[25\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[25].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_25_r"]
odb::dbBox_create $r [expr {round(1603.24*$dbu)}] [expr {round(2510.64*$dbu)}] [expr {round(1607.56*$dbu)}] [expr {round(2514.96*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_25_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[25\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[25].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_26_w"]
odb::dbBox_create $r [expr {round(1428.8*$dbu)}] [expr {round(2370.8*$dbu)}] [expr {round(1435.28*$dbu)}] [expr {round(2377.28*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_26_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[26\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[26].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_26_r"]
odb::dbBox_create $r [expr {round(1608.64*$dbu)}] [expr {round(2510.64*$dbu)}] [expr {round(1612.96*$dbu)}] [expr {round(2514.96*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_26_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[26\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[26].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_27_w"]
odb::dbBox_create $r [expr {round(1435.82*$dbu)}] [expr {round(2370.8*$dbu)}] [expr {round(1442.3*$dbu)}] [expr {round(2377.28*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_27_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[27\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[27].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_27_r"]
odb::dbBox_create $r [expr {round(1614.04*$dbu)}] [expr {round(2510.64*$dbu)}] [expr {round(1618.36*$dbu)}] [expr {round(2514.96*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_27_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[27\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[27].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_28_w"]
odb::dbBox_create $r [expr {round(1442.84*$dbu)}] [expr {round(2370.8*$dbu)}] [expr {round(1449.32*$dbu)}] [expr {round(2377.28*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_28_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[28\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[28].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_28_r"]
odb::dbBox_create $r [expr {round(1619.44*$dbu)}] [expr {round(2510.64*$dbu)}] [expr {round(1623.76*$dbu)}] [expr {round(2514.96*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_28_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[28\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[28].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_29_w"]
odb::dbBox_create $r [expr {round(1449.86*$dbu)}] [expr {round(2370.8*$dbu)}] [expr {round(1456.34*$dbu)}] [expr {round(2377.28*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_29_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[29\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[29].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_29_r"]
odb::dbBox_create $r [expr {round(1624.84*$dbu)}] [expr {round(2510.64*$dbu)}] [expr {round(1629.16*$dbu)}] [expr {round(2514.96*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_29_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[29\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[29].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_30_w"]
odb::dbBox_create $r [expr {round(1456.88*$dbu)}] [expr {round(2370.8*$dbu)}] [expr {round(1463.36*$dbu)}] [expr {round(2377.28*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_30_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[30\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[30].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_30_r"]
odb::dbBox_create $r [expr {round(1630.24*$dbu)}] [expr {round(2510.64*$dbu)}] [expr {round(1634.56*$dbu)}] [expr {round(2514.96*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_30_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[30\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[30].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_31_w"]
odb::dbBox_create $r [expr {round(1463.9*$dbu)}] [expr {round(2370.8*$dbu)}] [expr {round(1470.38*$dbu)}] [expr {round(2377.28*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_31_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[31\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[31].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_31_r"]
odb::dbBox_create $r [expr {round(1635.64*$dbu)}] [expr {round(2510.64*$dbu)}] [expr {round(1639.96*$dbu)}] [expr {round(2514.96*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_31_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[31\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[31].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_32_w"]
odb::dbBox_create $r [expr {round(1470.92*$dbu)}] [expr {round(2370.8*$dbu)}] [expr {round(1477.4*$dbu)}] [expr {round(2377.28*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_32_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[32\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[32].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_32_r"]
odb::dbBox_create $r [expr {round(1641.04*$dbu)}] [expr {round(2510.64*$dbu)}] [expr {round(1645.36*$dbu)}] [expr {round(2514.96*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_32_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[32\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[32].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_33_w"]
odb::dbBox_create $r [expr {round(1477.94*$dbu)}] [expr {round(2370.8*$dbu)}] [expr {round(1484.42*$dbu)}] [expr {round(2377.28*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_33_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[33\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[33].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_33_r"]
odb::dbBox_create $r [expr {round(1646.44*$dbu)}] [expr {round(2510.64*$dbu)}] [expr {round(1650.76*$dbu)}] [expr {round(2514.96*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_33_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[33\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[33].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_34_w"]
odb::dbBox_create $r [expr {round(1484.96*$dbu)}] [expr {round(2370.8*$dbu)}] [expr {round(1491.44*$dbu)}] [expr {round(2377.28*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_34_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[34\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[34].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_34_r"]
odb::dbBox_create $r [expr {round(1651.84*$dbu)}] [expr {round(2510.64*$dbu)}] [expr {round(1656.16*$dbu)}] [expr {round(2514.96*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_34_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[34\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[34].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_35_w"]
odb::dbBox_create $r [expr {round(1491.98*$dbu)}] [expr {round(2370.8*$dbu)}] [expr {round(1498.46*$dbu)}] [expr {round(2377.28*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_35_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[35\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[35].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_35_r"]
odb::dbBox_create $r [expr {round(1657.24*$dbu)}] [expr {round(2510.64*$dbu)}] [expr {round(1661.56*$dbu)}] [expr {round(2514.96*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_35_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[35\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[35].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_36_w"]
odb::dbBox_create $r [expr {round(1414.76*$dbu)}] [expr {round(2377.82*$dbu)}] [expr {round(1421.24*$dbu)}] [expr {round(2384.3*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_36_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[36\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[36].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_36_r"]
odb::dbBox_create $r [expr {round(1597.84*$dbu)}] [expr {round(2516.04*$dbu)}] [expr {round(1602.16*$dbu)}] [expr {round(2520.36*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_36_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[36\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[36].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_37_w"]
odb::dbBox_create $r [expr {round(1421.78*$dbu)}] [expr {round(2377.82*$dbu)}] [expr {round(1428.26*$dbu)}] [expr {round(2384.3*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_37_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[37\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[37].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_37_r"]
odb::dbBox_create $r [expr {round(1603.24*$dbu)}] [expr {round(2516.04*$dbu)}] [expr {round(1607.56*$dbu)}] [expr {round(2520.36*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_37_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[37\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[37].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_38_w"]
odb::dbBox_create $r [expr {round(1428.8*$dbu)}] [expr {round(2377.82*$dbu)}] [expr {round(1435.28*$dbu)}] [expr {round(2384.3*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_38_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[38\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[38].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_38_r"]
odb::dbBox_create $r [expr {round(1608.64*$dbu)}] [expr {round(2516.04*$dbu)}] [expr {round(1612.96*$dbu)}] [expr {round(2520.36*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_38_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[38\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[38].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_39_w"]
odb::dbBox_create $r [expr {round(1435.82*$dbu)}] [expr {round(2377.82*$dbu)}] [expr {round(1442.3*$dbu)}] [expr {round(2384.3*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_39_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[39\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[39].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_39_r"]
odb::dbBox_create $r [expr {round(1614.04*$dbu)}] [expr {round(2516.04*$dbu)}] [expr {round(1618.36*$dbu)}] [expr {round(2520.36*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_39_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[39\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[39].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_40_w"]
odb::dbBox_create $r [expr {round(1442.84*$dbu)}] [expr {round(2377.82*$dbu)}] [expr {round(1449.32*$dbu)}] [expr {round(2384.3*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_40_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[40\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[40].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_40_r"]
odb::dbBox_create $r [expr {round(1619.44*$dbu)}] [expr {round(2516.04*$dbu)}] [expr {round(1623.76*$dbu)}] [expr {round(2520.36*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_40_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[40\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[40].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_41_w"]
odb::dbBox_create $r [expr {round(1449.86*$dbu)}] [expr {round(2377.82*$dbu)}] [expr {round(1456.34*$dbu)}] [expr {round(2384.3*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_41_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[41\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[41].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_41_r"]
odb::dbBox_create $r [expr {round(1624.84*$dbu)}] [expr {round(2516.04*$dbu)}] [expr {round(1629.16*$dbu)}] [expr {round(2520.36*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_41_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[41\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[41].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_42_w"]
odb::dbBox_create $r [expr {round(1456.88*$dbu)}] [expr {round(2377.82*$dbu)}] [expr {round(1463.36*$dbu)}] [expr {round(2384.3*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_42_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[42\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[42].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_42_r"]
odb::dbBox_create $r [expr {round(1630.24*$dbu)}] [expr {round(2516.04*$dbu)}] [expr {round(1634.56*$dbu)}] [expr {round(2520.36*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_42_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[42\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[42].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_43_w"]
odb::dbBox_create $r [expr {round(1463.9*$dbu)}] [expr {round(2377.82*$dbu)}] [expr {round(1470.38*$dbu)}] [expr {round(2384.3*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_43_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[43\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[43].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_43_r"]
odb::dbBox_create $r [expr {round(1635.64*$dbu)}] [expr {round(2516.04*$dbu)}] [expr {round(1639.96*$dbu)}] [expr {round(2520.36*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_43_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[43\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[43].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_44_w"]
odb::dbBox_create $r [expr {round(1470.92*$dbu)}] [expr {round(2377.82*$dbu)}] [expr {round(1477.4*$dbu)}] [expr {round(2384.3*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_44_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[44\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[44].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_44_r"]
odb::dbBox_create $r [expr {round(1641.04*$dbu)}] [expr {round(2516.04*$dbu)}] [expr {round(1645.36*$dbu)}] [expr {round(2520.36*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_44_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[44\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[44].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_45_w"]
odb::dbBox_create $r [expr {round(1477.94*$dbu)}] [expr {round(2377.82*$dbu)}] [expr {round(1484.42*$dbu)}] [expr {round(2384.3*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_45_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[45\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[45].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_45_r"]
odb::dbBox_create $r [expr {round(1646.44*$dbu)}] [expr {round(2516.04*$dbu)}] [expr {round(1650.76*$dbu)}] [expr {round(2520.36*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_45_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[45\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[45].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_46_w"]
odb::dbBox_create $r [expr {round(1484.96*$dbu)}] [expr {round(2377.82*$dbu)}] [expr {round(1491.44*$dbu)}] [expr {round(2384.3*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_46_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[46\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[46].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_46_r"]
odb::dbBox_create $r [expr {round(1651.84*$dbu)}] [expr {round(2516.04*$dbu)}] [expr {round(1656.16*$dbu)}] [expr {round(2520.36*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_46_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[46\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[46].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_47_w"]
odb::dbBox_create $r [expr {round(1491.98*$dbu)}] [expr {round(2377.82*$dbu)}] [expr {round(1498.46*$dbu)}] [expr {round(2384.3*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_47_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[47\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[47].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_47_r"]
odb::dbBox_create $r [expr {round(1657.24*$dbu)}] [expr {round(2516.04*$dbu)}] [expr {round(1661.56*$dbu)}] [expr {round(2520.36*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_47_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[47\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[47].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_48_w"]
odb::dbBox_create $r [expr {round(1414.76*$dbu)}] [expr {round(2384.84*$dbu)}] [expr {round(1421.24*$dbu)}] [expr {round(2391.32*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_48_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[48\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[48].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_48_r"]
odb::dbBox_create $r [expr {round(1597.84*$dbu)}] [expr {round(2521.44*$dbu)}] [expr {round(1602.16*$dbu)}] [expr {round(2525.76*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_48_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[48\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[48].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_49_w"]
odb::dbBox_create $r [expr {round(1421.78*$dbu)}] [expr {round(2384.84*$dbu)}] [expr {round(1428.26*$dbu)}] [expr {round(2391.32*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_49_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[49\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[49].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_49_r"]
odb::dbBox_create $r [expr {round(1603.24*$dbu)}] [expr {round(2521.44*$dbu)}] [expr {round(1607.56*$dbu)}] [expr {round(2525.76*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_49_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[49\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[49].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_50_w"]
odb::dbBox_create $r [expr {round(1428.8*$dbu)}] [expr {round(2384.84*$dbu)}] [expr {round(1435.28*$dbu)}] [expr {round(2391.32*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_50_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[50\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[50].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_50_r"]
odb::dbBox_create $r [expr {round(1608.64*$dbu)}] [expr {round(2521.44*$dbu)}] [expr {round(1612.96*$dbu)}] [expr {round(2525.76*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_50_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[50\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[50].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_51_w"]
odb::dbBox_create $r [expr {round(1435.82*$dbu)}] [expr {round(2384.84*$dbu)}] [expr {round(1442.3*$dbu)}] [expr {round(2391.32*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_51_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[51\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[51].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_51_r"]
odb::dbBox_create $r [expr {round(1614.04*$dbu)}] [expr {round(2521.44*$dbu)}] [expr {round(1618.36*$dbu)}] [expr {round(2525.76*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_51_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[51\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[51].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_52_w"]
odb::dbBox_create $r [expr {round(1442.84*$dbu)}] [expr {round(2384.84*$dbu)}] [expr {round(1449.32*$dbu)}] [expr {round(2391.32*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_52_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[52\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[52].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_52_r"]
odb::dbBox_create $r [expr {round(1619.44*$dbu)}] [expr {round(2521.44*$dbu)}] [expr {round(1623.76*$dbu)}] [expr {round(2525.76*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_52_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[52\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[52].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_53_w"]
odb::dbBox_create $r [expr {round(1449.86*$dbu)}] [expr {round(2384.84*$dbu)}] [expr {round(1456.34*$dbu)}] [expr {round(2391.32*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_53_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[53\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[53].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_53_r"]
odb::dbBox_create $r [expr {round(1624.84*$dbu)}] [expr {round(2521.44*$dbu)}] [expr {round(1629.16*$dbu)}] [expr {round(2525.76*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_53_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[53\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[53].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_54_w"]
odb::dbBox_create $r [expr {round(1456.88*$dbu)}] [expr {round(2384.84*$dbu)}] [expr {round(1463.36*$dbu)}] [expr {round(2391.32*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_54_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[54\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[54].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_54_r"]
odb::dbBox_create $r [expr {round(1630.24*$dbu)}] [expr {round(2521.44*$dbu)}] [expr {round(1634.56*$dbu)}] [expr {round(2525.76*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_54_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[54\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[54].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_55_w"]
odb::dbBox_create $r [expr {round(1463.9*$dbu)}] [expr {round(2384.84*$dbu)}] [expr {round(1470.38*$dbu)}] [expr {round(2391.32*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_55_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[55\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[55].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_55_r"]
odb::dbBox_create $r [expr {round(1635.64*$dbu)}] [expr {round(2521.44*$dbu)}] [expr {round(1639.96*$dbu)}] [expr {round(2525.76*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_55_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[55\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[55].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_56_w"]
odb::dbBox_create $r [expr {round(1470.92*$dbu)}] [expr {round(2384.84*$dbu)}] [expr {round(1477.4*$dbu)}] [expr {round(2391.32*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_56_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[56\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[56].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_56_r"]
odb::dbBox_create $r [expr {round(1641.04*$dbu)}] [expr {round(2521.44*$dbu)}] [expr {round(1645.36*$dbu)}] [expr {round(2525.76*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_56_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[56\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[56].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_57_w"]
odb::dbBox_create $r [expr {round(1477.94*$dbu)}] [expr {round(2384.84*$dbu)}] [expr {round(1484.42*$dbu)}] [expr {round(2391.32*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_57_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[57\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[57].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_57_r"]
odb::dbBox_create $r [expr {round(1646.44*$dbu)}] [expr {round(2521.44*$dbu)}] [expr {round(1650.76*$dbu)}] [expr {round(2525.76*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_57_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[57\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[57].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_58_w"]
odb::dbBox_create $r [expr {round(1484.96*$dbu)}] [expr {round(2384.84*$dbu)}] [expr {round(1491.44*$dbu)}] [expr {round(2391.32*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_58_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[58\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[58].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_58_r"]
odb::dbBox_create $r [expr {round(1651.84*$dbu)}] [expr {round(2521.44*$dbu)}] [expr {round(1656.16*$dbu)}] [expr {round(2525.76*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_58_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[58\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[58].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_59_w"]
odb::dbBox_create $r [expr {round(1491.98*$dbu)}] [expr {round(2384.84*$dbu)}] [expr {round(1498.46*$dbu)}] [expr {round(2391.32*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_59_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[59\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[59].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_59_r"]
odb::dbBox_create $r [expr {round(1657.24*$dbu)}] [expr {round(2521.44*$dbu)}] [expr {round(1661.56*$dbu)}] [expr {round(2525.76*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_59_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[59\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[59].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_60_w"]
odb::dbBox_create $r [expr {round(1414.76*$dbu)}] [expr {round(2391.86*$dbu)}] [expr {round(1421.24*$dbu)}] [expr {round(2398.34*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_60_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[60\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[60].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_60_r"]
odb::dbBox_create $r [expr {round(1597.84*$dbu)}] [expr {round(2526.84*$dbu)}] [expr {round(1602.16*$dbu)}] [expr {round(2531.16*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_60_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[60\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[60].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_61_w"]
odb::dbBox_create $r [expr {round(1421.78*$dbu)}] [expr {round(2391.86*$dbu)}] [expr {round(1428.26*$dbu)}] [expr {round(2398.34*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_61_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[61\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[61].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_61_r"]
odb::dbBox_create $r [expr {round(1603.24*$dbu)}] [expr {round(2526.84*$dbu)}] [expr {round(1607.56*$dbu)}] [expr {round(2531.16*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_61_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[61\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[61].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_62_w"]
odb::dbBox_create $r [expr {round(1428.8*$dbu)}] [expr {round(2391.86*$dbu)}] [expr {round(1435.28*$dbu)}] [expr {round(2398.34*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_62_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[62\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[62].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_62_r"]
odb::dbBox_create $r [expr {round(1608.64*$dbu)}] [expr {round(2526.84*$dbu)}] [expr {round(1612.96*$dbu)}] [expr {round(2531.16*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_62_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[62\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[62].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_63_w"]
odb::dbBox_create $r [expr {round(1435.82*$dbu)}] [expr {round(2391.86*$dbu)}] [expr {round(1442.3*$dbu)}] [expr {round(2398.34*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_63_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[63\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[63].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_63_r"]
odb::dbBox_create $r [expr {round(1614.04*$dbu)}] [expr {round(2526.84*$dbu)}] [expr {round(1618.36*$dbu)}] [expr {round(2531.16*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_63_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[63\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[63].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_64_w"]
odb::dbBox_create $r [expr {round(1442.84*$dbu)}] [expr {round(2391.86*$dbu)}] [expr {round(1449.32*$dbu)}] [expr {round(2398.34*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_64_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[64\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[64].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_64_r"]
odb::dbBox_create $r [expr {round(1619.44*$dbu)}] [expr {round(2526.84*$dbu)}] [expr {round(1623.76*$dbu)}] [expr {round(2531.16*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_64_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[64\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[64].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_65_w"]
odb::dbBox_create $r [expr {round(1449.86*$dbu)}] [expr {round(2391.86*$dbu)}] [expr {round(1456.34*$dbu)}] [expr {round(2398.34*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_65_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[65\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[65].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_65_r"]
odb::dbBox_create $r [expr {round(1624.84*$dbu)}] [expr {round(2526.84*$dbu)}] [expr {round(1629.16*$dbu)}] [expr {round(2531.16*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_65_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[65\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[65].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_66_w"]
odb::dbBox_create $r [expr {round(1456.88*$dbu)}] [expr {round(2391.86*$dbu)}] [expr {round(1463.36*$dbu)}] [expr {round(2398.34*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_66_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[66\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[66].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_66_r"]
odb::dbBox_create $r [expr {round(1630.24*$dbu)}] [expr {round(2526.84*$dbu)}] [expr {round(1634.56*$dbu)}] [expr {round(2531.16*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_66_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[66\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[66].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_67_w"]
odb::dbBox_create $r [expr {round(1463.9*$dbu)}] [expr {round(2391.86*$dbu)}] [expr {round(1470.38*$dbu)}] [expr {round(2398.34*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_67_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[67\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[67].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_67_r"]
odb::dbBox_create $r [expr {round(1635.64*$dbu)}] [expr {round(2526.84*$dbu)}] [expr {round(1639.96*$dbu)}] [expr {round(2531.16*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_67_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[67\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[67].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_68_w"]
odb::dbBox_create $r [expr {round(1470.92*$dbu)}] [expr {round(2391.86*$dbu)}] [expr {round(1477.4*$dbu)}] [expr {round(2398.34*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_68_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[68\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[68].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_68_r"]
odb::dbBox_create $r [expr {round(1641.04*$dbu)}] [expr {round(2526.84*$dbu)}] [expr {round(1645.36*$dbu)}] [expr {round(2531.16*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_68_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[68\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[68].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_69_w"]
odb::dbBox_create $r [expr {round(1477.94*$dbu)}] [expr {round(2391.86*$dbu)}] [expr {round(1484.42*$dbu)}] [expr {round(2398.34*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_69_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[69\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[69].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_69_r"]
odb::dbBox_create $r [expr {round(1646.44*$dbu)}] [expr {round(2526.84*$dbu)}] [expr {round(1650.76*$dbu)}] [expr {round(2531.16*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_69_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[69\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[69].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_70_w"]
odb::dbBox_create $r [expr {round(1484.96*$dbu)}] [expr {round(2391.86*$dbu)}] [expr {round(1491.44*$dbu)}] [expr {round(2398.34*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_70_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[70\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[70].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_70_r"]
odb::dbBox_create $r [expr {round(1651.84*$dbu)}] [expr {round(2526.84*$dbu)}] [expr {round(1656.16*$dbu)}] [expr {round(2531.16*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_70_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[70\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[70].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_71_w"]
odb::dbBox_create $r [expr {round(1491.98*$dbu)}] [expr {round(2391.86*$dbu)}] [expr {round(1498.46*$dbu)}] [expr {round(2398.34*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_71_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[71\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[71].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_71_r"]
odb::dbBox_create $r [expr {round(1657.24*$dbu)}] [expr {round(2526.84*$dbu)}] [expr {round(1661.56*$dbu)}] [expr {round(2531.16*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_71_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[71\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[71].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_72_w"]
odb::dbBox_create $r [expr {round(1414.76*$dbu)}] [expr {round(2398.88*$dbu)}] [expr {round(1421.24*$dbu)}] [expr {round(2405.36*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_72_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[72\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[72].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_72_r"]
odb::dbBox_create $r [expr {round(1597.84*$dbu)}] [expr {round(2532.24*$dbu)}] [expr {round(1602.16*$dbu)}] [expr {round(2536.56*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_72_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[72\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[72].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_73_w"]
odb::dbBox_create $r [expr {round(1421.78*$dbu)}] [expr {round(2398.88*$dbu)}] [expr {round(1428.26*$dbu)}] [expr {round(2405.36*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_73_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[73\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[73].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_73_r"]
odb::dbBox_create $r [expr {round(1603.24*$dbu)}] [expr {round(2532.24*$dbu)}] [expr {round(1607.56*$dbu)}] [expr {round(2536.56*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_73_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[73\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[73].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_74_w"]
odb::dbBox_create $r [expr {round(1428.8*$dbu)}] [expr {round(2398.88*$dbu)}] [expr {round(1435.28*$dbu)}] [expr {round(2405.36*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_74_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[74\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[74].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_74_r"]
odb::dbBox_create $r [expr {round(1608.64*$dbu)}] [expr {round(2532.24*$dbu)}] [expr {round(1612.96*$dbu)}] [expr {round(2536.56*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_74_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[74\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[74].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_75_w"]
odb::dbBox_create $r [expr {round(1435.82*$dbu)}] [expr {round(2398.88*$dbu)}] [expr {round(1442.3*$dbu)}] [expr {round(2405.36*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_75_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[75\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[75].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_75_r"]
odb::dbBox_create $r [expr {round(1614.04*$dbu)}] [expr {round(2532.24*$dbu)}] [expr {round(1618.36*$dbu)}] [expr {round(2536.56*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_75_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[75\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[75].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_76_w"]
odb::dbBox_create $r [expr {round(1442.84*$dbu)}] [expr {round(2398.88*$dbu)}] [expr {round(1449.32*$dbu)}] [expr {round(2405.36*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_76_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[76\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[76].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_76_r"]
odb::dbBox_create $r [expr {round(1619.44*$dbu)}] [expr {round(2532.24*$dbu)}] [expr {round(1623.76*$dbu)}] [expr {round(2536.56*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_76_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[76\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[76].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_77_w"]
odb::dbBox_create $r [expr {round(1449.86*$dbu)}] [expr {round(2398.88*$dbu)}] [expr {round(1456.34*$dbu)}] [expr {round(2405.36*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_77_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[77\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[77].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_77_r"]
odb::dbBox_create $r [expr {round(1624.84*$dbu)}] [expr {round(2532.24*$dbu)}] [expr {round(1629.16*$dbu)}] [expr {round(2536.56*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_77_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[77\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[77].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_78_w"]
odb::dbBox_create $r [expr {round(1456.88*$dbu)}] [expr {round(2398.88*$dbu)}] [expr {round(1463.36*$dbu)}] [expr {round(2405.36*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_78_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[78\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[78].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_78_r"]
odb::dbBox_create $r [expr {round(1630.24*$dbu)}] [expr {round(2532.24*$dbu)}] [expr {round(1634.56*$dbu)}] [expr {round(2536.56*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_78_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[78\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[78].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_79_w"]
odb::dbBox_create $r [expr {round(1463.9*$dbu)}] [expr {round(2398.88*$dbu)}] [expr {round(1470.38*$dbu)}] [expr {round(2405.36*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_79_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[79\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[79].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_79_r"]
odb::dbBox_create $r [expr {round(1635.64*$dbu)}] [expr {round(2532.24*$dbu)}] [expr {round(1639.96*$dbu)}] [expr {round(2536.56*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_79_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[79\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[79].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_80_w"]
odb::dbBox_create $r [expr {round(1470.92*$dbu)}] [expr {round(2398.88*$dbu)}] [expr {round(1477.4*$dbu)}] [expr {round(2405.36*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_80_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[80\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[80].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_80_r"]
odb::dbBox_create $r [expr {round(1641.04*$dbu)}] [expr {round(2532.24*$dbu)}] [expr {round(1645.36*$dbu)}] [expr {round(2536.56*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_80_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[80\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[80].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_81_w"]
odb::dbBox_create $r [expr {round(1477.94*$dbu)}] [expr {round(2398.88*$dbu)}] [expr {round(1484.42*$dbu)}] [expr {round(2405.36*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_81_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[81\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[81].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_81_r"]
odb::dbBox_create $r [expr {round(1646.44*$dbu)}] [expr {round(2532.24*$dbu)}] [expr {round(1650.76*$dbu)}] [expr {round(2536.56*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_81_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[81\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[81].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_82_w"]
odb::dbBox_create $r [expr {round(1484.96*$dbu)}] [expr {round(2398.88*$dbu)}] [expr {round(1491.44*$dbu)}] [expr {round(2405.36*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_82_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[82\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[82].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_82_r"]
odb::dbBox_create $r [expr {round(1651.84*$dbu)}] [expr {round(2532.24*$dbu)}] [expr {round(1656.16*$dbu)}] [expr {round(2536.56*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_82_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[82\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[82].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_83_w"]
odb::dbBox_create $r [expr {round(1491.98*$dbu)}] [expr {round(2398.88*$dbu)}] [expr {round(1498.46*$dbu)}] [expr {round(2405.36*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_83_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[83\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[83].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_83_r"]
odb::dbBox_create $r [expr {round(1657.24*$dbu)}] [expr {round(2532.24*$dbu)}] [expr {round(1661.56*$dbu)}] [expr {round(2536.56*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_83_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[83\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[83].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_84_w"]
odb::dbBox_create $r [expr {round(1414.76*$dbu)}] [expr {round(2405.9*$dbu)}] [expr {round(1421.24*$dbu)}] [expr {round(2412.38*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_84_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[84\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[84].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_84_r"]
odb::dbBox_create $r [expr {round(1597.84*$dbu)}] [expr {round(2537.64*$dbu)}] [expr {round(1602.16*$dbu)}] [expr {round(2541.96*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_84_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[84\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[84].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_85_w"]
odb::dbBox_create $r [expr {round(1421.78*$dbu)}] [expr {round(2405.9*$dbu)}] [expr {round(1428.26*$dbu)}] [expr {round(2412.38*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_85_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[85\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[85].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_85_r"]
odb::dbBox_create $r [expr {round(1603.24*$dbu)}] [expr {round(2537.64*$dbu)}] [expr {round(1607.56*$dbu)}] [expr {round(2541.96*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_85_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[85\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[85].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_86_w"]
odb::dbBox_create $r [expr {round(1428.8*$dbu)}] [expr {round(2405.9*$dbu)}] [expr {round(1435.28*$dbu)}] [expr {round(2412.38*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_86_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[86\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[86].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_86_r"]
odb::dbBox_create $r [expr {round(1608.64*$dbu)}] [expr {round(2537.64*$dbu)}] [expr {round(1612.96*$dbu)}] [expr {round(2541.96*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_86_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[86\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[86].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_87_w"]
odb::dbBox_create $r [expr {round(1435.82*$dbu)}] [expr {round(2405.9*$dbu)}] [expr {round(1442.3*$dbu)}] [expr {round(2412.38*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_87_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[87\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[87].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_87_r"]
odb::dbBox_create $r [expr {round(1614.04*$dbu)}] [expr {round(2537.64*$dbu)}] [expr {round(1618.36*$dbu)}] [expr {round(2541.96*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_87_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[87\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[87].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_88_w"]
odb::dbBox_create $r [expr {round(1442.84*$dbu)}] [expr {round(2405.9*$dbu)}] [expr {round(1449.32*$dbu)}] [expr {round(2412.38*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_88_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[88\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[88].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_88_r"]
odb::dbBox_create $r [expr {round(1619.44*$dbu)}] [expr {round(2537.64*$dbu)}] [expr {round(1623.76*$dbu)}] [expr {round(2541.96*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_88_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[88\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[88].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_89_w"]
odb::dbBox_create $r [expr {round(1449.86*$dbu)}] [expr {round(2405.9*$dbu)}] [expr {round(1456.34*$dbu)}] [expr {round(2412.38*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_89_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[89\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[89].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_89_r"]
odb::dbBox_create $r [expr {round(1624.84*$dbu)}] [expr {round(2537.64*$dbu)}] [expr {round(1629.16*$dbu)}] [expr {round(2541.96*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_89_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[89\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[89].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_90_w"]
odb::dbBox_create $r [expr {round(1456.88*$dbu)}] [expr {round(2405.9*$dbu)}] [expr {round(1463.36*$dbu)}] [expr {round(2412.38*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_90_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[90\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[90].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_90_r"]
odb::dbBox_create $r [expr {round(1630.24*$dbu)}] [expr {round(2537.64*$dbu)}] [expr {round(1634.56*$dbu)}] [expr {round(2541.96*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_90_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[90\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[90].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_91_w"]
odb::dbBox_create $r [expr {round(1463.9*$dbu)}] [expr {round(2405.9*$dbu)}] [expr {round(1470.38*$dbu)}] [expr {round(2412.38*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_91_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[91\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[91].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_91_r"]
odb::dbBox_create $r [expr {round(1635.64*$dbu)}] [expr {round(2537.64*$dbu)}] [expr {round(1639.96*$dbu)}] [expr {round(2541.96*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_91_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[91\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[91].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_92_w"]
odb::dbBox_create $r [expr {round(1470.92*$dbu)}] [expr {round(2405.9*$dbu)}] [expr {round(1477.4*$dbu)}] [expr {round(2412.38*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_92_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[92\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[92].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_92_r"]
odb::dbBox_create $r [expr {round(1641.04*$dbu)}] [expr {round(2537.64*$dbu)}] [expr {round(1645.36*$dbu)}] [expr {round(2541.96*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_92_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[92\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[92].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_93_w"]
odb::dbBox_create $r [expr {round(1477.94*$dbu)}] [expr {round(2405.9*$dbu)}] [expr {round(1484.42*$dbu)}] [expr {round(2412.38*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_93_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[93\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[93].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_93_r"]
odb::dbBox_create $r [expr {round(1646.44*$dbu)}] [expr {round(2537.64*$dbu)}] [expr {round(1650.76*$dbu)}] [expr {round(2541.96*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_93_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[93\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[93].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_94_w"]
odb::dbBox_create $r [expr {round(1484.96*$dbu)}] [expr {round(2405.9*$dbu)}] [expr {round(1491.44*$dbu)}] [expr {round(2412.38*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_94_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[94\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[94].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_94_r"]
odb::dbBox_create $r [expr {round(1651.84*$dbu)}] [expr {round(2537.64*$dbu)}] [expr {round(1656.16*$dbu)}] [expr {round(2541.96*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_94_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[94\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[94].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_95_w"]
odb::dbBox_create $r [expr {round(1491.98*$dbu)}] [expr {round(2405.9*$dbu)}] [expr {round(1498.46*$dbu)}] [expr {round(2412.38*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_95_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[95\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[95].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_95_r"]
odb::dbBox_create $r [expr {round(1657.24*$dbu)}] [expr {round(2537.64*$dbu)}] [expr {round(1661.56*$dbu)}] [expr {round(2541.96*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_95_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[95\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[95].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_96_w"]
odb::dbBox_create $r [expr {round(1414.76*$dbu)}] [expr {round(2412.92*$dbu)}] [expr {round(1421.24*$dbu)}] [expr {round(2419.4*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_96_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[96\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[96].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_96_r"]
odb::dbBox_create $r [expr {round(1597.84*$dbu)}] [expr {round(2543.04*$dbu)}] [expr {round(1602.16*$dbu)}] [expr {round(2547.36*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_96_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[96\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[96].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_97_w"]
odb::dbBox_create $r [expr {round(1421.78*$dbu)}] [expr {round(2412.92*$dbu)}] [expr {round(1428.26*$dbu)}] [expr {round(2419.4*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_97_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[97\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[97].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_97_r"]
odb::dbBox_create $r [expr {round(1603.24*$dbu)}] [expr {round(2543.04*$dbu)}] [expr {round(1607.56*$dbu)}] [expr {round(2547.36*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_97_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[97\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[97].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_98_w"]
odb::dbBox_create $r [expr {round(1428.8*$dbu)}] [expr {round(2412.92*$dbu)}] [expr {round(1435.28*$dbu)}] [expr {round(2419.4*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_98_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[98\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[98].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_98_r"]
odb::dbBox_create $r [expr {round(1608.64*$dbu)}] [expr {round(2543.04*$dbu)}] [expr {round(1612.96*$dbu)}] [expr {round(2547.36*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_98_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[98\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[98].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_99_w"]
odb::dbBox_create $r [expr {round(1435.82*$dbu)}] [expr {round(2412.92*$dbu)}] [expr {round(1442.3*$dbu)}] [expr {round(2419.4*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_99_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[99\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[99].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_99_r"]
odb::dbBox_create $r [expr {round(1614.04*$dbu)}] [expr {round(2543.04*$dbu)}] [expr {round(1618.36*$dbu)}] [expr {round(2547.36*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_99_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[99\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[99].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_100_w"]
odb::dbBox_create $r [expr {round(1442.84*$dbu)}] [expr {round(2412.92*$dbu)}] [expr {round(1449.32*$dbu)}] [expr {round(2419.4*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_100_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[100\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[100].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_100_r"]
odb::dbBox_create $r [expr {round(1619.44*$dbu)}] [expr {round(2543.04*$dbu)}] [expr {round(1623.76*$dbu)}] [expr {round(2547.36*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_100_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[100\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[100].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_101_w"]
odb::dbBox_create $r [expr {round(1449.86*$dbu)}] [expr {round(2412.92*$dbu)}] [expr {round(1456.34*$dbu)}] [expr {round(2419.4*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_101_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[101\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[101].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_101_r"]
odb::dbBox_create $r [expr {round(1624.84*$dbu)}] [expr {round(2543.04*$dbu)}] [expr {round(1629.16*$dbu)}] [expr {round(2547.36*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_101_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[101\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[101].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_102_w"]
odb::dbBox_create $r [expr {round(1456.88*$dbu)}] [expr {round(2412.92*$dbu)}] [expr {round(1463.36*$dbu)}] [expr {round(2419.4*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_102_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[102\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[102].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_102_r"]
odb::dbBox_create $r [expr {round(1630.24*$dbu)}] [expr {round(2543.04*$dbu)}] [expr {round(1634.56*$dbu)}] [expr {round(2547.36*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_102_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[102\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[102].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_103_w"]
odb::dbBox_create $r [expr {round(1463.9*$dbu)}] [expr {round(2412.92*$dbu)}] [expr {round(1470.38*$dbu)}] [expr {round(2419.4*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_103_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[103\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[103].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_103_r"]
odb::dbBox_create $r [expr {round(1635.64*$dbu)}] [expr {round(2543.04*$dbu)}] [expr {round(1639.96*$dbu)}] [expr {round(2547.36*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_103_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[103\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[103].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_104_w"]
odb::dbBox_create $r [expr {round(1470.92*$dbu)}] [expr {round(2412.92*$dbu)}] [expr {round(1477.4*$dbu)}] [expr {round(2419.4*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_104_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[104\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[104].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_104_r"]
odb::dbBox_create $r [expr {round(1641.04*$dbu)}] [expr {round(2543.04*$dbu)}] [expr {round(1645.36*$dbu)}] [expr {round(2547.36*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_104_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[104\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[104].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_105_w"]
odb::dbBox_create $r [expr {round(1477.94*$dbu)}] [expr {round(2412.92*$dbu)}] [expr {round(1484.42*$dbu)}] [expr {round(2419.4*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_105_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[105\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[105].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_105_r"]
odb::dbBox_create $r [expr {round(1646.44*$dbu)}] [expr {round(2543.04*$dbu)}] [expr {round(1650.76*$dbu)}] [expr {round(2547.36*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_105_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[105\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[105].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_106_w"]
odb::dbBox_create $r [expr {round(1484.96*$dbu)}] [expr {round(2412.92*$dbu)}] [expr {round(1491.44*$dbu)}] [expr {round(2419.4*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_106_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[106\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[106].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_106_r"]
odb::dbBox_create $r [expr {round(1651.84*$dbu)}] [expr {round(2543.04*$dbu)}] [expr {round(1656.16*$dbu)}] [expr {round(2547.36*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_106_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[106\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[106].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_107_w"]
odb::dbBox_create $r [expr {round(1491.98*$dbu)}] [expr {round(2412.92*$dbu)}] [expr {round(1498.46*$dbu)}] [expr {round(2419.4*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_107_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[107\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[107].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_107_r"]
odb::dbBox_create $r [expr {round(1657.24*$dbu)}] [expr {round(2543.04*$dbu)}] [expr {round(1661.56*$dbu)}] [expr {round(2547.36*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_107_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[107\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[107].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_108_w"]
odb::dbBox_create $r [expr {round(1414.76*$dbu)}] [expr {round(2419.94*$dbu)}] [expr {round(1421.24*$dbu)}] [expr {round(2426.42*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_108_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[108\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[108].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_108_r"]
odb::dbBox_create $r [expr {round(1597.84*$dbu)}] [expr {round(2548.44*$dbu)}] [expr {round(1602.16*$dbu)}] [expr {round(2552.76*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_108_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[108\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[108].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_109_w"]
odb::dbBox_create $r [expr {round(1421.78*$dbu)}] [expr {round(2419.94*$dbu)}] [expr {round(1428.26*$dbu)}] [expr {round(2426.42*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_109_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[109\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[109].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_109_r"]
odb::dbBox_create $r [expr {round(1603.24*$dbu)}] [expr {round(2548.44*$dbu)}] [expr {round(1607.56*$dbu)}] [expr {round(2552.76*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_109_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[109\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[109].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_110_w"]
odb::dbBox_create $r [expr {round(1428.8*$dbu)}] [expr {round(2419.94*$dbu)}] [expr {round(1435.28*$dbu)}] [expr {round(2426.42*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_110_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[110\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[110].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_110_r"]
odb::dbBox_create $r [expr {round(1608.64*$dbu)}] [expr {round(2548.44*$dbu)}] [expr {round(1612.96*$dbu)}] [expr {round(2552.76*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_110_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[110\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[110].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_111_w"]
odb::dbBox_create $r [expr {round(1435.82*$dbu)}] [expr {round(2419.94*$dbu)}] [expr {round(1442.3*$dbu)}] [expr {round(2426.42*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_111_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[111\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[111].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_111_r"]
odb::dbBox_create $r [expr {round(1614.04*$dbu)}] [expr {round(2548.44*$dbu)}] [expr {round(1618.36*$dbu)}] [expr {round(2552.76*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_111_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[111\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[111].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_112_w"]
odb::dbBox_create $r [expr {round(1442.84*$dbu)}] [expr {round(2419.94*$dbu)}] [expr {round(1449.32*$dbu)}] [expr {round(2426.42*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_112_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[112\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[112].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_112_r"]
odb::dbBox_create $r [expr {round(1619.44*$dbu)}] [expr {round(2548.44*$dbu)}] [expr {round(1623.76*$dbu)}] [expr {round(2552.76*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_112_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[112\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[112].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_113_w"]
odb::dbBox_create $r [expr {round(1449.86*$dbu)}] [expr {round(2419.94*$dbu)}] [expr {round(1456.34*$dbu)}] [expr {round(2426.42*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_113_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[113\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[113].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_113_r"]
odb::dbBox_create $r [expr {round(1624.84*$dbu)}] [expr {round(2548.44*$dbu)}] [expr {round(1629.16*$dbu)}] [expr {round(2552.76*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_113_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[113\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[113].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_114_w"]
odb::dbBox_create $r [expr {round(1456.88*$dbu)}] [expr {round(2419.94*$dbu)}] [expr {round(1463.36*$dbu)}] [expr {round(2426.42*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_114_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[114\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[114].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_114_r"]
odb::dbBox_create $r [expr {round(1630.24*$dbu)}] [expr {round(2548.44*$dbu)}] [expr {round(1634.56*$dbu)}] [expr {round(2552.76*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_114_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[114\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[114].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_115_w"]
odb::dbBox_create $r [expr {round(1463.9*$dbu)}] [expr {round(2419.94*$dbu)}] [expr {round(1470.38*$dbu)}] [expr {round(2426.42*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_115_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[115\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[115].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_115_r"]
odb::dbBox_create $r [expr {round(1635.64*$dbu)}] [expr {round(2548.44*$dbu)}] [expr {round(1639.96*$dbu)}] [expr {round(2552.76*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_115_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[115\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[115].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_116_w"]
odb::dbBox_create $r [expr {round(1470.92*$dbu)}] [expr {round(2419.94*$dbu)}] [expr {round(1477.4*$dbu)}] [expr {round(2426.42*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_116_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[116\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[116].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_116_r"]
odb::dbBox_create $r [expr {round(1641.04*$dbu)}] [expr {round(2548.44*$dbu)}] [expr {round(1645.36*$dbu)}] [expr {round(2552.76*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_116_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[116\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[116].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_117_w"]
odb::dbBox_create $r [expr {round(1477.94*$dbu)}] [expr {round(2419.94*$dbu)}] [expr {round(1484.42*$dbu)}] [expr {round(2426.42*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_117_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[117\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[117].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_117_r"]
odb::dbBox_create $r [expr {round(1646.44*$dbu)}] [expr {round(2548.44*$dbu)}] [expr {round(1650.76*$dbu)}] [expr {round(2552.76*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_117_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[117\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[117].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_118_w"]
odb::dbBox_create $r [expr {round(1484.96*$dbu)}] [expr {round(2419.94*$dbu)}] [expr {round(1491.44*$dbu)}] [expr {round(2426.42*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_118_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[118\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[118].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_118_r"]
odb::dbBox_create $r [expr {round(1651.84*$dbu)}] [expr {round(2548.44*$dbu)}] [expr {round(1656.16*$dbu)}] [expr {round(2552.76*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_118_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[118\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[118].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_119_w"]
odb::dbBox_create $r [expr {round(1491.98*$dbu)}] [expr {round(2419.94*$dbu)}] [expr {round(1498.46*$dbu)}] [expr {round(2426.42*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_119_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[119\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[119].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_119_r"]
odb::dbBox_create $r [expr {round(1657.24*$dbu)}] [expr {round(2548.44*$dbu)}] [expr {round(1661.56*$dbu)}] [expr {round(2552.76*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_119_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[119\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[119].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_120_w"]
odb::dbBox_create $r [expr {round(1414.76*$dbu)}] [expr {round(2426.96*$dbu)}] [expr {round(1421.24*$dbu)}] [expr {round(2433.44*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_120_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[120\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[120].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_120_r"]
odb::dbBox_create $r [expr {round(1597.84*$dbu)}] [expr {round(2553.84*$dbu)}] [expr {round(1602.16*$dbu)}] [expr {round(2558.16*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_120_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[120\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[120].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_121_w"]
odb::dbBox_create $r [expr {round(1421.78*$dbu)}] [expr {round(2426.96*$dbu)}] [expr {round(1428.26*$dbu)}] [expr {round(2433.44*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_121_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[121\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[121].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_121_r"]
odb::dbBox_create $r [expr {round(1603.24*$dbu)}] [expr {round(2553.84*$dbu)}] [expr {round(1607.56*$dbu)}] [expr {round(2558.16*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_121_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[121\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[121].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_122_w"]
odb::dbBox_create $r [expr {round(1428.8*$dbu)}] [expr {round(2426.96*$dbu)}] [expr {round(1435.28*$dbu)}] [expr {round(2433.44*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_122_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[122\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[122].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_122_r"]
odb::dbBox_create $r [expr {round(1608.64*$dbu)}] [expr {round(2553.84*$dbu)}] [expr {round(1612.96*$dbu)}] [expr {round(2558.16*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_122_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[122\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[122].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_123_w"]
odb::dbBox_create $r [expr {round(1435.82*$dbu)}] [expr {round(2426.96*$dbu)}] [expr {round(1442.3*$dbu)}] [expr {round(2433.44*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_123_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[123\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[123].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_123_r"]
odb::dbBox_create $r [expr {round(1614.04*$dbu)}] [expr {round(2553.84*$dbu)}] [expr {round(1618.36*$dbu)}] [expr {round(2558.16*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_123_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[123\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[123].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_124_w"]
odb::dbBox_create $r [expr {round(1442.84*$dbu)}] [expr {round(2426.96*$dbu)}] [expr {round(1449.32*$dbu)}] [expr {round(2433.44*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_124_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[124\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[124].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_124_r"]
odb::dbBox_create $r [expr {round(1619.44*$dbu)}] [expr {round(2553.84*$dbu)}] [expr {round(1623.76*$dbu)}] [expr {round(2558.16*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_124_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[124\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[124].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_125_w"]
odb::dbBox_create $r [expr {round(1449.86*$dbu)}] [expr {round(2426.96*$dbu)}] [expr {round(1456.34*$dbu)}] [expr {round(2433.44*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_125_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[125\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[125].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_125_r"]
odb::dbBox_create $r [expr {round(1624.84*$dbu)}] [expr {round(2553.84*$dbu)}] [expr {round(1629.16*$dbu)}] [expr {round(2558.16*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_125_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[125\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[125].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_126_w"]
odb::dbBox_create $r [expr {round(1456.88*$dbu)}] [expr {round(2426.96*$dbu)}] [expr {round(1463.36*$dbu)}] [expr {round(2433.44*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_126_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[126\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[126].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_126_r"]
odb::dbBox_create $r [expr {round(1630.24*$dbu)}] [expr {round(2553.84*$dbu)}] [expr {round(1634.56*$dbu)}] [expr {round(2558.16*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_126_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[126\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[126].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_127_w"]
odb::dbBox_create $r [expr {round(1463.9*$dbu)}] [expr {round(2426.96*$dbu)}] [expr {round(1470.38*$dbu)}] [expr {round(2433.44*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_127_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[127\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[127].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_127_r"]
odb::dbBox_create $r [expr {round(1635.64*$dbu)}] [expr {round(2553.84*$dbu)}] [expr {round(1639.96*$dbu)}] [expr {round(2558.16*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_127_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[127\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[127].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_128_w"]
odb::dbBox_create $r [expr {round(1470.92*$dbu)}] [expr {round(2426.96*$dbu)}] [expr {round(1477.4*$dbu)}] [expr {round(2433.44*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_128_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[128\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[128].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_128_r"]
odb::dbBox_create $r [expr {round(1641.04*$dbu)}] [expr {round(2553.84*$dbu)}] [expr {round(1645.36*$dbu)}] [expr {round(2558.16*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_128_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[128\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[128].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_129_w"]
odb::dbBox_create $r [expr {round(1477.94*$dbu)}] [expr {round(2426.96*$dbu)}] [expr {round(1484.42*$dbu)}] [expr {round(2433.44*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_129_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[129\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[129].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_129_r"]
odb::dbBox_create $r [expr {round(1646.44*$dbu)}] [expr {round(2553.84*$dbu)}] [expr {round(1650.76*$dbu)}] [expr {round(2558.16*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_129_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[129\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[129].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_130_w"]
odb::dbBox_create $r [expr {round(1484.96*$dbu)}] [expr {round(2426.96*$dbu)}] [expr {round(1491.44*$dbu)}] [expr {round(2433.44*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_130_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[130\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[130].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_130_r"]
odb::dbBox_create $r [expr {round(1651.84*$dbu)}] [expr {round(2553.84*$dbu)}] [expr {round(1656.16*$dbu)}] [expr {round(2558.16*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_130_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[130\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[130].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_131_w"]
odb::dbBox_create $r [expr {round(1491.98*$dbu)}] [expr {round(2426.96*$dbu)}] [expr {round(1498.46*$dbu)}] [expr {round(2433.44*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_131_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[131\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[131].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_131_r"]
odb::dbBox_create $r [expr {round(1657.24*$dbu)}] [expr {round(2553.84*$dbu)}] [expr {round(1661.56*$dbu)}] [expr {round(2558.16*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_131_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[131\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[131].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_132_w"]
odb::dbBox_create $r [expr {round(1414.76*$dbu)}] [expr {round(2433.98*$dbu)}] [expr {round(1421.24*$dbu)}] [expr {round(2440.46*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_132_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[132\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[132].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_132_r"]
odb::dbBox_create $r [expr {round(1597.84*$dbu)}] [expr {round(2559.24*$dbu)}] [expr {round(1602.16*$dbu)}] [expr {round(2563.56*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_132_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[132\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[132].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_133_w"]
odb::dbBox_create $r [expr {round(1421.78*$dbu)}] [expr {round(2433.98*$dbu)}] [expr {round(1428.26*$dbu)}] [expr {round(2440.46*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_133_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[133\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[133].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_133_r"]
odb::dbBox_create $r [expr {round(1603.24*$dbu)}] [expr {round(2559.24*$dbu)}] [expr {round(1607.56*$dbu)}] [expr {round(2563.56*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_133_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[133\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[133].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_134_w"]
odb::dbBox_create $r [expr {round(1428.8*$dbu)}] [expr {round(2433.98*$dbu)}] [expr {round(1435.28*$dbu)}] [expr {round(2440.46*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_134_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[134\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[134].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_134_r"]
odb::dbBox_create $r [expr {round(1608.64*$dbu)}] [expr {round(2559.24*$dbu)}] [expr {round(1612.96*$dbu)}] [expr {round(2563.56*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_134_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[134\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[134].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_135_w"]
odb::dbBox_create $r [expr {round(1435.82*$dbu)}] [expr {round(2433.98*$dbu)}] [expr {round(1442.3*$dbu)}] [expr {round(2440.46*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_135_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[135\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[135].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_135_r"]
odb::dbBox_create $r [expr {round(1614.04*$dbu)}] [expr {round(2559.24*$dbu)}] [expr {round(1618.36*$dbu)}] [expr {round(2563.56*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_135_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[135\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[135].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_136_w"]
odb::dbBox_create $r [expr {round(1442.84*$dbu)}] [expr {round(2433.98*$dbu)}] [expr {round(1449.32*$dbu)}] [expr {round(2440.46*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_136_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[136\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[136].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_136_r"]
odb::dbBox_create $r [expr {round(1619.44*$dbu)}] [expr {round(2559.24*$dbu)}] [expr {round(1623.76*$dbu)}] [expr {round(2563.56*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_136_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[136\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[136].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_137_w"]
odb::dbBox_create $r [expr {round(1449.86*$dbu)}] [expr {round(2433.98*$dbu)}] [expr {round(1456.34*$dbu)}] [expr {round(2440.46*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_137_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_w[./]g_chunk\[137\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_w.g_chunk[137].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_137_r"]
odb::dbBox_create $r [expr {round(1624.84*$dbu)}] [expr {round(2559.24*$dbu)}] [expr {round(1629.16*$dbu)}] [expr {round(2563.56*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_137_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_8_r[./]g_chunk\[137\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_8_r.g_chunk[137].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_0_w"]
odb::dbBox_create $r [expr {round(1426.76*$dbu)}] [expr {round(2486.76*$dbu)}] [expr {round(1433.24*$dbu)}] [expr {round(2493.24*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_0_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[0\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[0].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_0_r"]
odb::dbBox_create $r [expr {round(1386.84*$dbu)}] [expr {round(2706.84*$dbu)}] [expr {round(1391.16*$dbu)}] [expr {round(2711.16*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_0_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[0\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[0].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_1_w"]
odb::dbBox_create $r [expr {round(1433.78*$dbu)}] [expr {round(2486.76*$dbu)}] [expr {round(1440.26*$dbu)}] [expr {round(2493.24*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_1_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[1\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[1].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_1_r"]
odb::dbBox_create $r [expr {round(1391.7*$dbu)}] [expr {round(2706.84*$dbu)}] [expr {round(1396.02*$dbu)}] [expr {round(2711.16*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_1_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[1\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[1].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_2_w"]
odb::dbBox_create $r [expr {round(1440.8*$dbu)}] [expr {round(2486.76*$dbu)}] [expr {round(1447.28*$dbu)}] [expr {round(2493.24*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_2_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[2\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[2].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_2_r"]
odb::dbBox_create $r [expr {round(1396.56*$dbu)}] [expr {round(2706.84*$dbu)}] [expr {round(1400.88*$dbu)}] [expr {round(2711.16*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_2_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[2\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[2].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_3_w"]
odb::dbBox_create $r [expr {round(1447.82*$dbu)}] [expr {round(2486.76*$dbu)}] [expr {round(1454.3*$dbu)}] [expr {round(2493.24*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_3_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[3\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[3].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_3_r"]
odb::dbBox_create $r [expr {round(1401.42*$dbu)}] [expr {round(2706.84*$dbu)}] [expr {round(1405.74*$dbu)}] [expr {round(2711.16*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_3_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[3\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[3].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_4_w"]
odb::dbBox_create $r [expr {round(1454.84*$dbu)}] [expr {round(2486.76*$dbu)}] [expr {round(1461.32*$dbu)}] [expr {round(2493.24*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_4_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[4\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[4].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_4_r"]
odb::dbBox_create $r [expr {round(1406.28*$dbu)}] [expr {round(2706.84*$dbu)}] [expr {round(1410.6*$dbu)}] [expr {round(2711.16*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_4_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[4\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[4].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_5_w"]
odb::dbBox_create $r [expr {round(1461.86*$dbu)}] [expr {round(2486.76*$dbu)}] [expr {round(1468.34*$dbu)}] [expr {round(2493.24*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_5_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[5\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[5].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_5_r"]
odb::dbBox_create $r [expr {round(1411.14*$dbu)}] [expr {round(2706.84*$dbu)}] [expr {round(1415.46*$dbu)}] [expr {round(2711.16*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_5_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[5\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[5].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_6_w"]
odb::dbBox_create $r [expr {round(1468.88*$dbu)}] [expr {round(2486.76*$dbu)}] [expr {round(1475.36*$dbu)}] [expr {round(2493.24*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_6_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[6\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[6].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_6_r"]
odb::dbBox_create $r [expr {round(1386.84*$dbu)}] [expr {round(2711.7*$dbu)}] [expr {round(1391.16*$dbu)}] [expr {round(2716.02*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_6_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[6\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[6].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_7_w"]
odb::dbBox_create $r [expr {round(1475.9*$dbu)}] [expr {round(2486.76*$dbu)}] [expr {round(1482.38*$dbu)}] [expr {round(2493.24*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_7_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[7\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[7].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_7_r"]
odb::dbBox_create $r [expr {round(1391.7*$dbu)}] [expr {round(2711.7*$dbu)}] [expr {round(1396.02*$dbu)}] [expr {round(2716.02*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_7_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[7\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[7].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_8_w"]
odb::dbBox_create $r [expr {round(1482.92*$dbu)}] [expr {round(2486.76*$dbu)}] [expr {round(1489.4*$dbu)}] [expr {round(2493.24*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_8_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[8\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[8].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_8_r"]
odb::dbBox_create $r [expr {round(1396.56*$dbu)}] [expr {round(2711.7*$dbu)}] [expr {round(1400.88*$dbu)}] [expr {round(2716.02*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_8_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[8\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[8].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_9_w"]
odb::dbBox_create $r [expr {round(1489.94*$dbu)}] [expr {round(2486.76*$dbu)}] [expr {round(1496.42*$dbu)}] [expr {round(2493.24*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_9_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[9\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[9].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_9_r"]
odb::dbBox_create $r [expr {round(1401.42*$dbu)}] [expr {round(2711.7*$dbu)}] [expr {round(1405.74*$dbu)}] [expr {round(2716.02*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_9_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[9\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[9].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_10_w"]
odb::dbBox_create $r [expr {round(1496.96*$dbu)}] [expr {round(2486.76*$dbu)}] [expr {round(1503.44*$dbu)}] [expr {round(2493.24*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_10_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[10\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[10].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_10_r"]
odb::dbBox_create $r [expr {round(1406.28*$dbu)}] [expr {round(2711.7*$dbu)}] [expr {round(1410.6*$dbu)}] [expr {round(2716.02*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_10_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[10\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[10].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_11_w"]
odb::dbBox_create $r [expr {round(1503.98*$dbu)}] [expr {round(2486.76*$dbu)}] [expr {round(1510.46*$dbu)}] [expr {round(2493.24*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_11_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[11\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[11].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_11_r"]
odb::dbBox_create $r [expr {round(1411.14*$dbu)}] [expr {round(2711.7*$dbu)}] [expr {round(1415.46*$dbu)}] [expr {round(2716.02*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_11_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[11\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[11].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_12_w"]
odb::dbBox_create $r [expr {round(1426.76*$dbu)}] [expr {round(2493.78*$dbu)}] [expr {round(1433.24*$dbu)}] [expr {round(2500.26*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_12_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[12\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[12].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_12_r"]
odb::dbBox_create $r [expr {round(1386.84*$dbu)}] [expr {round(2716.56*$dbu)}] [expr {round(1391.16*$dbu)}] [expr {round(2720.88*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_12_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[12\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[12].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_13_w"]
odb::dbBox_create $r [expr {round(1433.78*$dbu)}] [expr {round(2493.78*$dbu)}] [expr {round(1440.26*$dbu)}] [expr {round(2500.26*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_13_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[13\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[13].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_13_r"]
odb::dbBox_create $r [expr {round(1391.7*$dbu)}] [expr {round(2716.56*$dbu)}] [expr {round(1396.02*$dbu)}] [expr {round(2720.88*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_13_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[13\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[13].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_14_w"]
odb::dbBox_create $r [expr {round(1440.8*$dbu)}] [expr {round(2493.78*$dbu)}] [expr {round(1447.28*$dbu)}] [expr {round(2500.26*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_14_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[14\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[14].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_14_r"]
odb::dbBox_create $r [expr {round(1396.56*$dbu)}] [expr {round(2716.56*$dbu)}] [expr {round(1400.88*$dbu)}] [expr {round(2720.88*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_14_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[14\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[14].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_15_w"]
odb::dbBox_create $r [expr {round(1447.82*$dbu)}] [expr {round(2493.78*$dbu)}] [expr {round(1454.3*$dbu)}] [expr {round(2500.26*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_15_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[15\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[15].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_15_r"]
odb::dbBox_create $r [expr {round(1401.42*$dbu)}] [expr {round(2716.56*$dbu)}] [expr {round(1405.74*$dbu)}] [expr {round(2720.88*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_15_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[15\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[15].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_16_w"]
odb::dbBox_create $r [expr {round(1454.84*$dbu)}] [expr {round(2493.78*$dbu)}] [expr {round(1461.32*$dbu)}] [expr {round(2500.26*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_16_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[16\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[16].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_16_r"]
odb::dbBox_create $r [expr {round(1406.28*$dbu)}] [expr {round(2716.56*$dbu)}] [expr {round(1410.6*$dbu)}] [expr {round(2720.88*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_16_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[16\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[16].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_17_w"]
odb::dbBox_create $r [expr {round(1461.86*$dbu)}] [expr {round(2493.78*$dbu)}] [expr {round(1468.34*$dbu)}] [expr {round(2500.26*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_17_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[17\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[17].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_17_r"]
odb::dbBox_create $r [expr {round(1411.14*$dbu)}] [expr {round(2716.56*$dbu)}] [expr {round(1415.46*$dbu)}] [expr {round(2720.88*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_17_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[17\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[17].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_18_w"]
odb::dbBox_create $r [expr {round(1468.88*$dbu)}] [expr {round(2493.78*$dbu)}] [expr {round(1475.36*$dbu)}] [expr {round(2500.26*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_18_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[18\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[18].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_18_r"]
odb::dbBox_create $r [expr {round(1386.84*$dbu)}] [expr {round(2721.42*$dbu)}] [expr {round(1391.16*$dbu)}] [expr {round(2725.74*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_18_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[18\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[18].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_19_w"]
odb::dbBox_create $r [expr {round(1475.9*$dbu)}] [expr {round(2493.78*$dbu)}] [expr {round(1482.38*$dbu)}] [expr {round(2500.26*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_19_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[19\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[19].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_19_r"]
odb::dbBox_create $r [expr {round(1391.7*$dbu)}] [expr {round(2721.42*$dbu)}] [expr {round(1396.02*$dbu)}] [expr {round(2725.74*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_19_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[19\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[19].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_20_w"]
odb::dbBox_create $r [expr {round(1482.92*$dbu)}] [expr {round(2493.78*$dbu)}] [expr {round(1489.4*$dbu)}] [expr {round(2500.26*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_20_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[20\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[20].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_20_r"]
odb::dbBox_create $r [expr {round(1396.56*$dbu)}] [expr {round(2721.42*$dbu)}] [expr {round(1400.88*$dbu)}] [expr {round(2725.74*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_20_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[20\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[20].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_21_w"]
odb::dbBox_create $r [expr {round(1489.94*$dbu)}] [expr {round(2493.78*$dbu)}] [expr {round(1496.42*$dbu)}] [expr {round(2500.26*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_21_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[21\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[21].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_21_r"]
odb::dbBox_create $r [expr {round(1401.42*$dbu)}] [expr {round(2721.42*$dbu)}] [expr {round(1405.74*$dbu)}] [expr {round(2725.74*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_21_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[21\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[21].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_22_w"]
odb::dbBox_create $r [expr {round(1496.96*$dbu)}] [expr {round(2493.78*$dbu)}] [expr {round(1503.44*$dbu)}] [expr {round(2500.26*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_22_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[22\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[22].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_22_r"]
odb::dbBox_create $r [expr {round(1406.28*$dbu)}] [expr {round(2721.42*$dbu)}] [expr {round(1410.6*$dbu)}] [expr {round(2725.74*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_22_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[22\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[22].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_23_w"]
odb::dbBox_create $r [expr {round(1503.98*$dbu)}] [expr {round(2493.78*$dbu)}] [expr {round(1510.46*$dbu)}] [expr {round(2500.26*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_23_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[23\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[23].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_23_r"]
odb::dbBox_create $r [expr {round(1411.14*$dbu)}] [expr {round(2721.42*$dbu)}] [expr {round(1415.46*$dbu)}] [expr {round(2725.74*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_23_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[23\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[23].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_24_w"]
odb::dbBox_create $r [expr {round(1426.76*$dbu)}] [expr {round(2500.8*$dbu)}] [expr {round(1433.24*$dbu)}] [expr {round(2507.28*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_24_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[24\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[24].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_24_r"]
odb::dbBox_create $r [expr {round(1386.84*$dbu)}] [expr {round(2726.28*$dbu)}] [expr {round(1391.16*$dbu)}] [expr {round(2730.6*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_24_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[24\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[24].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_25_w"]
odb::dbBox_create $r [expr {round(1433.78*$dbu)}] [expr {round(2500.8*$dbu)}] [expr {round(1440.26*$dbu)}] [expr {round(2507.28*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_25_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[25\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[25].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_25_r"]
odb::dbBox_create $r [expr {round(1391.7*$dbu)}] [expr {round(2726.28*$dbu)}] [expr {round(1396.02*$dbu)}] [expr {round(2730.6*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_25_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[25\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[25].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_26_w"]
odb::dbBox_create $r [expr {round(1440.8*$dbu)}] [expr {round(2500.8*$dbu)}] [expr {round(1447.28*$dbu)}] [expr {round(2507.28*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_26_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[26\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[26].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_26_r"]
odb::dbBox_create $r [expr {round(1396.56*$dbu)}] [expr {round(2726.28*$dbu)}] [expr {round(1400.88*$dbu)}] [expr {round(2730.6*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_26_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[26\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[26].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_27_w"]
odb::dbBox_create $r [expr {round(1447.82*$dbu)}] [expr {round(2500.8*$dbu)}] [expr {round(1454.3*$dbu)}] [expr {round(2507.28*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_27_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[27\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[27].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_27_r"]
odb::dbBox_create $r [expr {round(1401.42*$dbu)}] [expr {round(2726.28*$dbu)}] [expr {round(1405.74*$dbu)}] [expr {round(2730.6*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_27_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[27\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[27].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_28_w"]
odb::dbBox_create $r [expr {round(1454.84*$dbu)}] [expr {round(2500.8*$dbu)}] [expr {round(1461.32*$dbu)}] [expr {round(2507.28*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_28_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[28\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[28].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_28_r"]
odb::dbBox_create $r [expr {round(1406.28*$dbu)}] [expr {round(2726.28*$dbu)}] [expr {round(1410.6*$dbu)}] [expr {round(2730.6*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_28_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[28\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[28].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_29_w"]
odb::dbBox_create $r [expr {round(1461.86*$dbu)}] [expr {round(2500.8*$dbu)}] [expr {round(1468.34*$dbu)}] [expr {round(2507.28*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_29_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[29\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[29].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_29_r"]
odb::dbBox_create $r [expr {round(1411.14*$dbu)}] [expr {round(2726.28*$dbu)}] [expr {round(1415.46*$dbu)}] [expr {round(2730.6*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_29_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[29\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[29].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_30_w"]
odb::dbBox_create $r [expr {round(1468.88*$dbu)}] [expr {round(2500.8*$dbu)}] [expr {round(1475.36*$dbu)}] [expr {round(2507.28*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_30_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[30\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[30].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_30_r"]
odb::dbBox_create $r [expr {round(1386.84*$dbu)}] [expr {round(2731.14*$dbu)}] [expr {round(1391.16*$dbu)}] [expr {round(2735.46*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_30_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[30\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[30].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_31_w"]
odb::dbBox_create $r [expr {round(1475.9*$dbu)}] [expr {round(2500.8*$dbu)}] [expr {round(1482.38*$dbu)}] [expr {round(2507.28*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_31_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[31\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[31].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_31_r"]
odb::dbBox_create $r [expr {round(1391.7*$dbu)}] [expr {round(2731.14*$dbu)}] [expr {round(1396.02*$dbu)}] [expr {round(2735.46*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_31_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[31\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[31].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_32_w"]
odb::dbBox_create $r [expr {round(1482.92*$dbu)}] [expr {round(2500.8*$dbu)}] [expr {round(1489.4*$dbu)}] [expr {round(2507.28*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_32_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[32\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[32].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_32_r"]
odb::dbBox_create $r [expr {round(1396.56*$dbu)}] [expr {round(2731.14*$dbu)}] [expr {round(1400.88*$dbu)}] [expr {round(2735.46*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_32_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[32\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[32].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_33_w"]
odb::dbBox_create $r [expr {round(1489.94*$dbu)}] [expr {round(2500.8*$dbu)}] [expr {round(1496.42*$dbu)}] [expr {round(2507.28*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_33_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[33\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[33].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_33_r"]
odb::dbBox_create $r [expr {round(1401.42*$dbu)}] [expr {round(2731.14*$dbu)}] [expr {round(1405.74*$dbu)}] [expr {round(2735.46*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_33_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[33\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[33].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_34_w"]
odb::dbBox_create $r [expr {round(1496.96*$dbu)}] [expr {round(2500.8*$dbu)}] [expr {round(1503.44*$dbu)}] [expr {round(2507.28*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_34_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[34\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[34].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_34_r"]
odb::dbBox_create $r [expr {round(1406.28*$dbu)}] [expr {round(2731.14*$dbu)}] [expr {round(1410.6*$dbu)}] [expr {round(2735.46*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_34_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[34\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[34].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_35_w"]
odb::dbBox_create $r [expr {round(1503.98*$dbu)}] [expr {round(2500.8*$dbu)}] [expr {round(1510.46*$dbu)}] [expr {round(2507.28*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_35_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[35\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[35].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_35_r"]
odb::dbBox_create $r [expr {round(1411.14*$dbu)}] [expr {round(2731.14*$dbu)}] [expr {round(1415.46*$dbu)}] [expr {round(2735.46*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_35_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[35\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[35].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_36_w"]
odb::dbBox_create $r [expr {round(1426.76*$dbu)}] [expr {round(2507.82*$dbu)}] [expr {round(1433.24*$dbu)}] [expr {round(2514.3*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_36_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[36\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[36].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_36_r"]
odb::dbBox_create $r [expr {round(1386.84*$dbu)}] [expr {round(2736.0*$dbu)}] [expr {round(1391.16*$dbu)}] [expr {round(2740.32*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_36_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[36\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[36].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_37_w"]
odb::dbBox_create $r [expr {round(1433.78*$dbu)}] [expr {round(2507.82*$dbu)}] [expr {round(1440.26*$dbu)}] [expr {round(2514.3*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_37_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[37\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[37].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_37_r"]
odb::dbBox_create $r [expr {round(1391.7*$dbu)}] [expr {round(2736.0*$dbu)}] [expr {round(1396.02*$dbu)}] [expr {round(2740.32*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_37_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[37\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[37].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_38_w"]
odb::dbBox_create $r [expr {round(1440.8*$dbu)}] [expr {round(2507.82*$dbu)}] [expr {round(1447.28*$dbu)}] [expr {round(2514.3*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_38_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[38\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[38].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_38_r"]
odb::dbBox_create $r [expr {round(1396.56*$dbu)}] [expr {round(2736.0*$dbu)}] [expr {round(1400.88*$dbu)}] [expr {round(2740.32*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_38_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[38\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[38].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_39_w"]
odb::dbBox_create $r [expr {round(1447.82*$dbu)}] [expr {round(2507.82*$dbu)}] [expr {round(1454.3*$dbu)}] [expr {round(2514.3*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_39_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[39\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[39].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_39_r"]
odb::dbBox_create $r [expr {round(1401.42*$dbu)}] [expr {round(2736.0*$dbu)}] [expr {round(1405.74*$dbu)}] [expr {round(2740.32*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_39_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[39\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[39].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_40_w"]
odb::dbBox_create $r [expr {round(1454.84*$dbu)}] [expr {round(2507.82*$dbu)}] [expr {round(1461.32*$dbu)}] [expr {round(2514.3*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_40_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[40\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[40].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_40_r"]
odb::dbBox_create $r [expr {round(1406.28*$dbu)}] [expr {round(2736.0*$dbu)}] [expr {round(1410.6*$dbu)}] [expr {round(2740.32*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_40_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[40\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[40].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_41_w"]
odb::dbBox_create $r [expr {round(1461.86*$dbu)}] [expr {round(2507.82*$dbu)}] [expr {round(1468.34*$dbu)}] [expr {round(2514.3*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_41_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[41\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[41].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_41_r"]
odb::dbBox_create $r [expr {round(1411.14*$dbu)}] [expr {round(2736.0*$dbu)}] [expr {round(1415.46*$dbu)}] [expr {round(2740.32*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_41_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[41\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[41].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_42_w"]
odb::dbBox_create $r [expr {round(1468.88*$dbu)}] [expr {round(2507.82*$dbu)}] [expr {round(1475.36*$dbu)}] [expr {round(2514.3*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_42_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[42\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[42].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_42_r"]
odb::dbBox_create $r [expr {round(1386.84*$dbu)}] [expr {round(2740.86*$dbu)}] [expr {round(1391.16*$dbu)}] [expr {round(2745.18*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_42_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[42\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[42].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_43_w"]
odb::dbBox_create $r [expr {round(1475.9*$dbu)}] [expr {round(2507.82*$dbu)}] [expr {round(1482.38*$dbu)}] [expr {round(2514.3*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_43_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[43\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[43].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_43_r"]
odb::dbBox_create $r [expr {round(1391.7*$dbu)}] [expr {round(2740.86*$dbu)}] [expr {round(1396.02*$dbu)}] [expr {round(2745.18*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_43_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[43\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[43].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_44_w"]
odb::dbBox_create $r [expr {round(1482.92*$dbu)}] [expr {round(2507.82*$dbu)}] [expr {round(1489.4*$dbu)}] [expr {round(2514.3*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_44_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[44\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[44].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_44_r"]
odb::dbBox_create $r [expr {round(1396.56*$dbu)}] [expr {round(2740.86*$dbu)}] [expr {round(1400.88*$dbu)}] [expr {round(2745.18*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_44_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[44\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[44].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_45_w"]
odb::dbBox_create $r [expr {round(1489.94*$dbu)}] [expr {round(2507.82*$dbu)}] [expr {round(1496.42*$dbu)}] [expr {round(2514.3*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_45_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[45\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[45].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_45_r"]
odb::dbBox_create $r [expr {round(1401.42*$dbu)}] [expr {round(2740.86*$dbu)}] [expr {round(1405.74*$dbu)}] [expr {round(2745.18*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_45_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[45\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[45].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_46_w"]
odb::dbBox_create $r [expr {round(1496.96*$dbu)}] [expr {round(2507.82*$dbu)}] [expr {round(1503.44*$dbu)}] [expr {round(2514.3*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_46_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[46\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[46].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_46_r"]
odb::dbBox_create $r [expr {round(1406.28*$dbu)}] [expr {round(2740.86*$dbu)}] [expr {round(1410.6*$dbu)}] [expr {round(2745.18*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_46_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[46\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[46].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_47_w"]
odb::dbBox_create $r [expr {round(1503.98*$dbu)}] [expr {round(2507.82*$dbu)}] [expr {round(1510.46*$dbu)}] [expr {round(2514.3*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_47_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[47\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[47].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_47_r"]
odb::dbBox_create $r [expr {round(1411.14*$dbu)}] [expr {round(2740.86*$dbu)}] [expr {round(1415.46*$dbu)}] [expr {round(2745.18*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_47_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[47\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[47].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_48_w"]
odb::dbBox_create $r [expr {round(1426.76*$dbu)}] [expr {round(2514.84*$dbu)}] [expr {round(1433.24*$dbu)}] [expr {round(2521.32*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_48_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[48\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[48].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_48_r"]
odb::dbBox_create $r [expr {round(1386.84*$dbu)}] [expr {round(2745.72*$dbu)}] [expr {round(1391.16*$dbu)}] [expr {round(2750.04*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_48_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[48\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[48].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_49_w"]
odb::dbBox_create $r [expr {round(1433.78*$dbu)}] [expr {round(2514.84*$dbu)}] [expr {round(1440.26*$dbu)}] [expr {round(2521.32*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_49_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[49\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[49].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_49_r"]
odb::dbBox_create $r [expr {round(1391.7*$dbu)}] [expr {round(2745.72*$dbu)}] [expr {round(1396.02*$dbu)}] [expr {round(2750.04*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_49_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[49\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[49].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_50_w"]
odb::dbBox_create $r [expr {round(1440.8*$dbu)}] [expr {round(2514.84*$dbu)}] [expr {round(1447.28*$dbu)}] [expr {round(2521.32*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_50_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[50\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[50].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_50_r"]
odb::dbBox_create $r [expr {round(1396.56*$dbu)}] [expr {round(2745.72*$dbu)}] [expr {round(1400.88*$dbu)}] [expr {round(2750.04*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_50_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[50\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[50].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_51_w"]
odb::dbBox_create $r [expr {round(1447.82*$dbu)}] [expr {round(2514.84*$dbu)}] [expr {round(1454.3*$dbu)}] [expr {round(2521.32*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_51_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[51\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[51].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_51_r"]
odb::dbBox_create $r [expr {round(1401.42*$dbu)}] [expr {round(2745.72*$dbu)}] [expr {round(1405.74*$dbu)}] [expr {round(2750.04*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_51_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[51\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[51].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_52_w"]
odb::dbBox_create $r [expr {round(1454.84*$dbu)}] [expr {round(2514.84*$dbu)}] [expr {round(1461.32*$dbu)}] [expr {round(2521.32*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_52_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[52\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[52].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_52_r"]
odb::dbBox_create $r [expr {round(1406.28*$dbu)}] [expr {round(2745.72*$dbu)}] [expr {round(1410.6*$dbu)}] [expr {round(2750.04*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_52_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[52\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[52].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_53_w"]
odb::dbBox_create $r [expr {round(1461.86*$dbu)}] [expr {round(2514.84*$dbu)}] [expr {round(1468.34*$dbu)}] [expr {round(2521.32*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_53_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[53\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[53].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_53_r"]
odb::dbBox_create $r [expr {round(1411.14*$dbu)}] [expr {round(2745.72*$dbu)}] [expr {round(1415.46*$dbu)}] [expr {round(2750.04*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_53_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[53\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[53].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_54_w"]
odb::dbBox_create $r [expr {round(1468.88*$dbu)}] [expr {round(2514.84*$dbu)}] [expr {round(1475.36*$dbu)}] [expr {round(2521.32*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_54_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[54\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[54].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_54_r"]
odb::dbBox_create $r [expr {round(1386.84*$dbu)}] [expr {round(2750.58*$dbu)}] [expr {round(1391.16*$dbu)}] [expr {round(2754.9*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_54_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[54\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[54].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_55_w"]
odb::dbBox_create $r [expr {round(1475.9*$dbu)}] [expr {round(2514.84*$dbu)}] [expr {round(1482.38*$dbu)}] [expr {round(2521.32*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_55_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[55\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[55].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_55_r"]
odb::dbBox_create $r [expr {round(1391.7*$dbu)}] [expr {round(2750.58*$dbu)}] [expr {round(1396.02*$dbu)}] [expr {round(2754.9*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_55_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[55\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[55].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_56_w"]
odb::dbBox_create $r [expr {round(1482.92*$dbu)}] [expr {round(2514.84*$dbu)}] [expr {round(1489.4*$dbu)}] [expr {round(2521.32*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_56_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[56\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[56].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_56_r"]
odb::dbBox_create $r [expr {round(1396.56*$dbu)}] [expr {round(2750.58*$dbu)}] [expr {round(1400.88*$dbu)}] [expr {round(2754.9*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_56_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[56\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[56].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_57_w"]
odb::dbBox_create $r [expr {round(1489.94*$dbu)}] [expr {round(2514.84*$dbu)}] [expr {round(1496.42*$dbu)}] [expr {round(2521.32*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_57_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[57\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[57].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_57_r"]
odb::dbBox_create $r [expr {round(1401.42*$dbu)}] [expr {round(2750.58*$dbu)}] [expr {round(1405.74*$dbu)}] [expr {round(2754.9*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_57_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[57\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[57].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_58_w"]
odb::dbBox_create $r [expr {round(1496.96*$dbu)}] [expr {round(2514.84*$dbu)}] [expr {round(1503.44*$dbu)}] [expr {round(2521.32*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_58_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[58\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[58].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_58_r"]
odb::dbBox_create $r [expr {round(1406.28*$dbu)}] [expr {round(2750.58*$dbu)}] [expr {round(1410.6*$dbu)}] [expr {round(2754.9*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_58_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[58\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[58].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_59_w"]
odb::dbBox_create $r [expr {round(1503.98*$dbu)}] [expr {round(2514.84*$dbu)}] [expr {round(1510.46*$dbu)}] [expr {round(2521.32*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_59_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[59\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[59].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_59_r"]
odb::dbBox_create $r [expr {round(1411.14*$dbu)}] [expr {round(2750.58*$dbu)}] [expr {round(1415.46*$dbu)}] [expr {round(2754.9*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_59_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[59\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[59].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_60_w"]
odb::dbBox_create $r [expr {round(1426.76*$dbu)}] [expr {round(2521.86*$dbu)}] [expr {round(1433.24*$dbu)}] [expr {round(2528.34*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_60_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[60\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[60].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_60_r"]
odb::dbBox_create $r [expr {round(1386.84*$dbu)}] [expr {round(2755.44*$dbu)}] [expr {round(1391.16*$dbu)}] [expr {round(2759.76*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_60_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[60\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[60].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_61_w"]
odb::dbBox_create $r [expr {round(1433.78*$dbu)}] [expr {round(2521.86*$dbu)}] [expr {round(1440.26*$dbu)}] [expr {round(2528.34*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_61_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[61\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[61].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_61_r"]
odb::dbBox_create $r [expr {round(1391.7*$dbu)}] [expr {round(2755.44*$dbu)}] [expr {round(1396.02*$dbu)}] [expr {round(2759.76*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_61_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[61\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[61].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_62_w"]
odb::dbBox_create $r [expr {round(1440.8*$dbu)}] [expr {round(2521.86*$dbu)}] [expr {round(1447.28*$dbu)}] [expr {round(2528.34*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_62_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[62\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[62].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_62_r"]
odb::dbBox_create $r [expr {round(1396.56*$dbu)}] [expr {round(2755.44*$dbu)}] [expr {round(1400.88*$dbu)}] [expr {round(2759.76*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_62_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[62\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[62].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_63_w"]
odb::dbBox_create $r [expr {round(1447.82*$dbu)}] [expr {round(2521.86*$dbu)}] [expr {round(1454.3*$dbu)}] [expr {round(2528.34*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_63_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[63\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[63].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_63_r"]
odb::dbBox_create $r [expr {round(1401.42*$dbu)}] [expr {round(2755.44*$dbu)}] [expr {round(1405.74*$dbu)}] [expr {round(2759.76*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_63_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[63\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[63].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_64_w"]
odb::dbBox_create $r [expr {round(1454.84*$dbu)}] [expr {round(2521.86*$dbu)}] [expr {round(1461.32*$dbu)}] [expr {round(2528.34*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_64_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[64\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[64].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_64_r"]
odb::dbBox_create $r [expr {round(1406.28*$dbu)}] [expr {round(2755.44*$dbu)}] [expr {round(1410.6*$dbu)}] [expr {round(2759.76*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_64_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[64\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[64].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_65_w"]
odb::dbBox_create $r [expr {round(1461.86*$dbu)}] [expr {round(2521.86*$dbu)}] [expr {round(1468.34*$dbu)}] [expr {round(2528.34*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_65_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[65\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[65].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_65_r"]
odb::dbBox_create $r [expr {round(1411.14*$dbu)}] [expr {round(2755.44*$dbu)}] [expr {round(1415.46*$dbu)}] [expr {round(2759.76*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_65_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[65\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[65].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_66_w"]
odb::dbBox_create $r [expr {round(1468.88*$dbu)}] [expr {round(2521.86*$dbu)}] [expr {round(1475.36*$dbu)}] [expr {round(2528.34*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_66_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[66\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[66].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_66_r"]
odb::dbBox_create $r [expr {round(1386.84*$dbu)}] [expr {round(2760.3*$dbu)}] [expr {round(1391.16*$dbu)}] [expr {round(2764.62*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_66_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[66\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[66].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_67_w"]
odb::dbBox_create $r [expr {round(1475.9*$dbu)}] [expr {round(2521.86*$dbu)}] [expr {round(1482.38*$dbu)}] [expr {round(2528.34*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_67_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[67\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[67].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_67_r"]
odb::dbBox_create $r [expr {round(1391.7*$dbu)}] [expr {round(2760.3*$dbu)}] [expr {round(1396.02*$dbu)}] [expr {round(2764.62*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_67_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[67\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[67].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_68_w"]
odb::dbBox_create $r [expr {round(1482.92*$dbu)}] [expr {round(2521.86*$dbu)}] [expr {round(1489.4*$dbu)}] [expr {round(2528.34*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_68_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[68\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[68].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_68_r"]
odb::dbBox_create $r [expr {round(1396.56*$dbu)}] [expr {round(2760.3*$dbu)}] [expr {round(1400.88*$dbu)}] [expr {round(2764.62*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_68_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[68\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[68].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_69_w"]
odb::dbBox_create $r [expr {round(1489.94*$dbu)}] [expr {round(2521.86*$dbu)}] [expr {round(1496.42*$dbu)}] [expr {round(2528.34*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_69_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[69\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[69].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_69_r"]
odb::dbBox_create $r [expr {round(1401.42*$dbu)}] [expr {round(2760.3*$dbu)}] [expr {round(1405.74*$dbu)}] [expr {round(2764.62*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_69_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[69\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[69].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_70_w"]
odb::dbBox_create $r [expr {round(1496.96*$dbu)}] [expr {round(2521.86*$dbu)}] [expr {round(1503.44*$dbu)}] [expr {round(2528.34*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_70_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[70\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[70].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_70_r"]
odb::dbBox_create $r [expr {round(1406.28*$dbu)}] [expr {round(2760.3*$dbu)}] [expr {round(1410.6*$dbu)}] [expr {round(2764.62*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_70_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[70\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[70].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_71_w"]
odb::dbBox_create $r [expr {round(1503.98*$dbu)}] [expr {round(2521.86*$dbu)}] [expr {round(1510.46*$dbu)}] [expr {round(2528.34*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_71_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[71\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[71].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_71_r"]
odb::dbBox_create $r [expr {round(1411.14*$dbu)}] [expr {round(2760.3*$dbu)}] [expr {round(1415.46*$dbu)}] [expr {round(2764.62*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_71_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[71\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[71].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_72_w"]
odb::dbBox_create $r [expr {round(1426.76*$dbu)}] [expr {round(2528.88*$dbu)}] [expr {round(1433.24*$dbu)}] [expr {round(2535.36*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_72_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[72\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[72].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_72_r"]
odb::dbBox_create $r [expr {round(1386.84*$dbu)}] [expr {round(2765.16*$dbu)}] [expr {round(1391.16*$dbu)}] [expr {round(2769.48*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_72_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[72\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[72].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_73_w"]
odb::dbBox_create $r [expr {round(1433.78*$dbu)}] [expr {round(2528.88*$dbu)}] [expr {round(1440.26*$dbu)}] [expr {round(2535.36*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_73_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[73\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[73].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_73_r"]
odb::dbBox_create $r [expr {round(1391.7*$dbu)}] [expr {round(2765.16*$dbu)}] [expr {round(1396.02*$dbu)}] [expr {round(2769.48*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_73_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[73\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[73].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_74_w"]
odb::dbBox_create $r [expr {round(1440.8*$dbu)}] [expr {round(2528.88*$dbu)}] [expr {round(1447.28*$dbu)}] [expr {round(2535.36*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_74_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[74\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[74].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_74_r"]
odb::dbBox_create $r [expr {round(1396.56*$dbu)}] [expr {round(2765.16*$dbu)}] [expr {round(1400.88*$dbu)}] [expr {round(2769.48*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_74_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[74\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[74].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_75_w"]
odb::dbBox_create $r [expr {round(1447.82*$dbu)}] [expr {round(2528.88*$dbu)}] [expr {round(1454.3*$dbu)}] [expr {round(2535.36*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_75_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[75\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[75].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_75_r"]
odb::dbBox_create $r [expr {round(1401.42*$dbu)}] [expr {round(2765.16*$dbu)}] [expr {round(1405.74*$dbu)}] [expr {round(2769.48*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_75_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[75\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[75].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_76_w"]
odb::dbBox_create $r [expr {round(1454.84*$dbu)}] [expr {round(2528.88*$dbu)}] [expr {round(1461.32*$dbu)}] [expr {round(2535.36*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_76_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[76\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[76].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_76_r"]
odb::dbBox_create $r [expr {round(1406.28*$dbu)}] [expr {round(2765.16*$dbu)}] [expr {round(1410.6*$dbu)}] [expr {round(2769.48*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_76_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[76\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[76].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_77_w"]
odb::dbBox_create $r [expr {round(1461.86*$dbu)}] [expr {round(2528.88*$dbu)}] [expr {round(1468.34*$dbu)}] [expr {round(2535.36*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_77_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[77\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[77].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_77_r"]
odb::dbBox_create $r [expr {round(1411.14*$dbu)}] [expr {round(2765.16*$dbu)}] [expr {round(1415.46*$dbu)}] [expr {round(2769.48*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_77_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[77\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[77].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_78_w"]
odb::dbBox_create $r [expr {round(1468.88*$dbu)}] [expr {round(2528.88*$dbu)}] [expr {round(1475.36*$dbu)}] [expr {round(2535.36*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_78_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[78\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[78].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_78_r"]
odb::dbBox_create $r [expr {round(1386.84*$dbu)}] [expr {round(2770.02*$dbu)}] [expr {round(1391.16*$dbu)}] [expr {round(2774.34*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_78_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[78\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[78].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_79_w"]
odb::dbBox_create $r [expr {round(1475.9*$dbu)}] [expr {round(2528.88*$dbu)}] [expr {round(1482.38*$dbu)}] [expr {round(2535.36*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_79_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[79\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[79].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_79_r"]
odb::dbBox_create $r [expr {round(1391.7*$dbu)}] [expr {round(2770.02*$dbu)}] [expr {round(1396.02*$dbu)}] [expr {round(2774.34*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_79_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[79\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[79].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_80_w"]
odb::dbBox_create $r [expr {round(1482.92*$dbu)}] [expr {round(2528.88*$dbu)}] [expr {round(1489.4*$dbu)}] [expr {round(2535.36*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_80_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[80\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[80].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_80_r"]
odb::dbBox_create $r [expr {round(1396.56*$dbu)}] [expr {round(2770.02*$dbu)}] [expr {round(1400.88*$dbu)}] [expr {round(2774.34*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_80_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[80\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[80].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_81_w"]
odb::dbBox_create $r [expr {round(1489.94*$dbu)}] [expr {round(2528.88*$dbu)}] [expr {round(1496.42*$dbu)}] [expr {round(2535.36*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_81_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[81\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[81].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_81_r"]
odb::dbBox_create $r [expr {round(1401.42*$dbu)}] [expr {round(2770.02*$dbu)}] [expr {round(1405.74*$dbu)}] [expr {round(2774.34*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_81_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[81\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[81].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_82_w"]
odb::dbBox_create $r [expr {round(1496.96*$dbu)}] [expr {round(2528.88*$dbu)}] [expr {round(1503.44*$dbu)}] [expr {round(2535.36*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_82_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[82\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[82].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_82_r"]
odb::dbBox_create $r [expr {round(1406.28*$dbu)}] [expr {round(2770.02*$dbu)}] [expr {round(1410.6*$dbu)}] [expr {round(2774.34*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_82_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[82\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[82].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_83_w"]
odb::dbBox_create $r [expr {round(1503.98*$dbu)}] [expr {round(2528.88*$dbu)}] [expr {round(1510.46*$dbu)}] [expr {round(2535.36*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_83_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[83\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[83].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_83_r"]
odb::dbBox_create $r [expr {round(1411.14*$dbu)}] [expr {round(2770.02*$dbu)}] [expr {round(1415.46*$dbu)}] [expr {round(2774.34*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_83_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[83\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[83].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_84_w"]
odb::dbBox_create $r [expr {round(1426.76*$dbu)}] [expr {round(2535.9*$dbu)}] [expr {round(1433.24*$dbu)}] [expr {round(2542.38*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_84_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[84\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[84].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_84_r"]
odb::dbBox_create $r [expr {round(1386.84*$dbu)}] [expr {round(2774.88*$dbu)}] [expr {round(1391.16*$dbu)}] [expr {round(2779.2*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_84_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[84\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[84].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_85_w"]
odb::dbBox_create $r [expr {round(1433.78*$dbu)}] [expr {round(2535.9*$dbu)}] [expr {round(1440.26*$dbu)}] [expr {round(2542.38*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_85_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[85\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[85].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_85_r"]
odb::dbBox_create $r [expr {round(1391.7*$dbu)}] [expr {round(2774.88*$dbu)}] [expr {round(1396.02*$dbu)}] [expr {round(2779.2*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_85_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[85\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[85].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_86_w"]
odb::dbBox_create $r [expr {round(1440.8*$dbu)}] [expr {round(2535.9*$dbu)}] [expr {round(1447.28*$dbu)}] [expr {round(2542.38*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_86_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[86\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[86].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_86_r"]
odb::dbBox_create $r [expr {round(1396.56*$dbu)}] [expr {round(2774.88*$dbu)}] [expr {round(1400.88*$dbu)}] [expr {round(2779.2*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_86_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[86\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[86].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_87_w"]
odb::dbBox_create $r [expr {round(1447.82*$dbu)}] [expr {round(2535.9*$dbu)}] [expr {round(1454.3*$dbu)}] [expr {round(2542.38*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_87_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[87\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[87].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_87_r"]
odb::dbBox_create $r [expr {round(1401.42*$dbu)}] [expr {round(2774.88*$dbu)}] [expr {round(1405.74*$dbu)}] [expr {round(2779.2*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_87_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[87\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[87].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_88_w"]
odb::dbBox_create $r [expr {round(1454.84*$dbu)}] [expr {round(2535.9*$dbu)}] [expr {round(1461.32*$dbu)}] [expr {round(2542.38*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_88_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[88\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[88].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_88_r"]
odb::dbBox_create $r [expr {round(1406.28*$dbu)}] [expr {round(2774.88*$dbu)}] [expr {round(1410.6*$dbu)}] [expr {round(2779.2*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_88_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[88\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[88].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_89_w"]
odb::dbBox_create $r [expr {round(1461.86*$dbu)}] [expr {round(2535.9*$dbu)}] [expr {round(1468.34*$dbu)}] [expr {round(2542.38*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_89_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[89\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[89].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_89_r"]
odb::dbBox_create $r [expr {round(1411.14*$dbu)}] [expr {round(2774.88*$dbu)}] [expr {round(1415.46*$dbu)}] [expr {round(2779.2*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_89_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[89\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[89].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_90_w"]
odb::dbBox_create $r [expr {round(1468.88*$dbu)}] [expr {round(2535.9*$dbu)}] [expr {round(1475.36*$dbu)}] [expr {round(2542.38*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_90_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[90\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[90].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_90_r"]
odb::dbBox_create $r [expr {round(1386.84*$dbu)}] [expr {round(2779.74*$dbu)}] [expr {round(1391.16*$dbu)}] [expr {round(2784.06*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_90_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[90\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[90].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_91_w"]
odb::dbBox_create $r [expr {round(1475.9*$dbu)}] [expr {round(2535.9*$dbu)}] [expr {round(1482.38*$dbu)}] [expr {round(2542.38*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_91_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[91\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[91].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_91_r"]
odb::dbBox_create $r [expr {round(1391.7*$dbu)}] [expr {round(2779.74*$dbu)}] [expr {round(1396.02*$dbu)}] [expr {round(2784.06*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_91_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[91\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[91].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_92_w"]
odb::dbBox_create $r [expr {round(1482.92*$dbu)}] [expr {round(2535.9*$dbu)}] [expr {round(1489.4*$dbu)}] [expr {round(2542.38*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_92_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[92\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[92].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_92_r"]
odb::dbBox_create $r [expr {round(1396.56*$dbu)}] [expr {round(2779.74*$dbu)}] [expr {round(1400.88*$dbu)}] [expr {round(2784.06*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_92_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[92\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[92].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_93_w"]
odb::dbBox_create $r [expr {round(1489.94*$dbu)}] [expr {round(2535.9*$dbu)}] [expr {round(1496.42*$dbu)}] [expr {round(2542.38*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_93_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[93\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[93].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_93_r"]
odb::dbBox_create $r [expr {round(1401.42*$dbu)}] [expr {round(2779.74*$dbu)}] [expr {round(1405.74*$dbu)}] [expr {round(2784.06*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_93_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[93\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[93].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_94_w"]
odb::dbBox_create $r [expr {round(1496.96*$dbu)}] [expr {round(2535.9*$dbu)}] [expr {round(1503.44*$dbu)}] [expr {round(2542.38*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_94_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[94\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[94].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_94_r"]
odb::dbBox_create $r [expr {round(1406.28*$dbu)}] [expr {round(2779.74*$dbu)}] [expr {round(1410.6*$dbu)}] [expr {round(2784.06*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_94_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[94\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[94].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_95_w"]
odb::dbBox_create $r [expr {round(1503.98*$dbu)}] [expr {round(2535.9*$dbu)}] [expr {round(1510.46*$dbu)}] [expr {round(2542.38*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_95_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[95\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[95].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_95_r"]
odb::dbBox_create $r [expr {round(1411.14*$dbu)}] [expr {round(2779.74*$dbu)}] [expr {round(1415.46*$dbu)}] [expr {round(2784.06*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_95_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[95\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[95].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_96_w"]
odb::dbBox_create $r [expr {round(1426.76*$dbu)}] [expr {round(2542.92*$dbu)}] [expr {round(1433.24*$dbu)}] [expr {round(2549.4*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_96_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[96\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[96].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_96_r"]
odb::dbBox_create $r [expr {round(1386.84*$dbu)}] [expr {round(2784.6*$dbu)}] [expr {round(1391.16*$dbu)}] [expr {round(2788.92*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_96_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[96\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[96].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_97_w"]
odb::dbBox_create $r [expr {round(1433.78*$dbu)}] [expr {round(2542.92*$dbu)}] [expr {round(1440.26*$dbu)}] [expr {round(2549.4*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_97_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[97\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[97].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_97_r"]
odb::dbBox_create $r [expr {round(1391.7*$dbu)}] [expr {round(2784.6*$dbu)}] [expr {round(1396.02*$dbu)}] [expr {round(2788.92*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_97_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[97\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[97].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_98_w"]
odb::dbBox_create $r [expr {round(1440.8*$dbu)}] [expr {round(2542.92*$dbu)}] [expr {round(1447.28*$dbu)}] [expr {round(2549.4*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_98_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[98\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[98].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_98_r"]
odb::dbBox_create $r [expr {round(1396.56*$dbu)}] [expr {round(2784.6*$dbu)}] [expr {round(1400.88*$dbu)}] [expr {round(2788.92*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_98_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[98\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[98].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_99_w"]
odb::dbBox_create $r [expr {round(1447.82*$dbu)}] [expr {round(2542.92*$dbu)}] [expr {round(1454.3*$dbu)}] [expr {round(2549.4*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_99_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[99\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[99].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_99_r"]
odb::dbBox_create $r [expr {round(1401.42*$dbu)}] [expr {round(2784.6*$dbu)}] [expr {round(1405.74*$dbu)}] [expr {round(2788.92*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_99_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[99\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[99].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_100_w"]
odb::dbBox_create $r [expr {round(1454.84*$dbu)}] [expr {round(2542.92*$dbu)}] [expr {round(1461.32*$dbu)}] [expr {round(2549.4*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_100_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[100\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[100].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_100_r"]
odb::dbBox_create $r [expr {round(1406.28*$dbu)}] [expr {round(2784.6*$dbu)}] [expr {round(1410.6*$dbu)}] [expr {round(2788.92*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_100_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[100\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[100].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_101_w"]
odb::dbBox_create $r [expr {round(1461.86*$dbu)}] [expr {round(2542.92*$dbu)}] [expr {round(1468.34*$dbu)}] [expr {round(2549.4*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_101_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[101\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[101].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_101_r"]
odb::dbBox_create $r [expr {round(1411.14*$dbu)}] [expr {round(2784.6*$dbu)}] [expr {round(1415.46*$dbu)}] [expr {round(2788.92*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_101_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[101\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[101].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_102_w"]
odb::dbBox_create $r [expr {round(1468.88*$dbu)}] [expr {round(2542.92*$dbu)}] [expr {round(1475.36*$dbu)}] [expr {round(2549.4*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_102_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[102\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[102].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_102_r"]
odb::dbBox_create $r [expr {round(1386.84*$dbu)}] [expr {round(2789.46*$dbu)}] [expr {round(1391.16*$dbu)}] [expr {round(2793.78*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_102_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[102\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[102].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_103_w"]
odb::dbBox_create $r [expr {round(1475.9*$dbu)}] [expr {round(2542.92*$dbu)}] [expr {round(1482.38*$dbu)}] [expr {round(2549.4*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_103_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[103\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[103].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_103_r"]
odb::dbBox_create $r [expr {round(1391.7*$dbu)}] [expr {round(2789.46*$dbu)}] [expr {round(1396.02*$dbu)}] [expr {round(2793.78*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_103_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[103\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[103].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_104_w"]
odb::dbBox_create $r [expr {round(1482.92*$dbu)}] [expr {round(2542.92*$dbu)}] [expr {round(1489.4*$dbu)}] [expr {round(2549.4*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_104_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[104\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[104].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_104_r"]
odb::dbBox_create $r [expr {round(1396.56*$dbu)}] [expr {round(2789.46*$dbu)}] [expr {round(1400.88*$dbu)}] [expr {round(2793.78*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_104_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[104\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[104].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_105_w"]
odb::dbBox_create $r [expr {round(1489.94*$dbu)}] [expr {round(2542.92*$dbu)}] [expr {round(1496.42*$dbu)}] [expr {round(2549.4*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_105_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[105\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[105].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_105_r"]
odb::dbBox_create $r [expr {round(1401.42*$dbu)}] [expr {round(2789.46*$dbu)}] [expr {round(1405.74*$dbu)}] [expr {round(2793.78*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_105_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[105\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[105].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_106_w"]
odb::dbBox_create $r [expr {round(1496.96*$dbu)}] [expr {round(2542.92*$dbu)}] [expr {round(1503.44*$dbu)}] [expr {round(2549.4*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_106_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[106\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[106].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_106_r"]
odb::dbBox_create $r [expr {round(1406.28*$dbu)}] [expr {round(2789.46*$dbu)}] [expr {round(1410.6*$dbu)}] [expr {round(2793.78*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_106_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[106\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[106].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_107_w"]
odb::dbBox_create $r [expr {round(1503.98*$dbu)}] [expr {round(2542.92*$dbu)}] [expr {round(1510.46*$dbu)}] [expr {round(2549.4*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_107_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[107\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[107].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_107_r"]
odb::dbBox_create $r [expr {round(1411.14*$dbu)}] [expr {round(2789.46*$dbu)}] [expr {round(1415.46*$dbu)}] [expr {round(2793.78*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_107_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[107\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[107].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_108_w"]
odb::dbBox_create $r [expr {round(1426.76*$dbu)}] [expr {round(2549.94*$dbu)}] [expr {round(1433.24*$dbu)}] [expr {round(2556.42*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_108_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[108\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[108].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_108_r"]
odb::dbBox_create $r [expr {round(1386.84*$dbu)}] [expr {round(2794.32*$dbu)}] [expr {round(1391.16*$dbu)}] [expr {round(2798.64*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_108_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[108\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[108].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_109_w"]
odb::dbBox_create $r [expr {round(1433.78*$dbu)}] [expr {round(2549.94*$dbu)}] [expr {round(1440.26*$dbu)}] [expr {round(2556.42*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_109_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[109\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[109].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_109_r"]
odb::dbBox_create $r [expr {round(1391.7*$dbu)}] [expr {round(2794.32*$dbu)}] [expr {round(1396.02*$dbu)}] [expr {round(2798.64*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_109_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[109\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[109].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_110_w"]
odb::dbBox_create $r [expr {round(1440.8*$dbu)}] [expr {round(2549.94*$dbu)}] [expr {round(1447.28*$dbu)}] [expr {round(2556.42*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_110_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[110\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[110].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_110_r"]
odb::dbBox_create $r [expr {round(1396.56*$dbu)}] [expr {round(2794.32*$dbu)}] [expr {round(1400.88*$dbu)}] [expr {round(2798.64*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_110_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[110\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[110].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_111_w"]
odb::dbBox_create $r [expr {round(1447.82*$dbu)}] [expr {round(2549.94*$dbu)}] [expr {round(1454.3*$dbu)}] [expr {round(2556.42*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_111_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[111\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[111].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_111_r"]
odb::dbBox_create $r [expr {round(1401.42*$dbu)}] [expr {round(2794.32*$dbu)}] [expr {round(1405.74*$dbu)}] [expr {round(2798.64*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_111_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[111\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[111].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_112_w"]
odb::dbBox_create $r [expr {round(1454.84*$dbu)}] [expr {round(2549.94*$dbu)}] [expr {round(1461.32*$dbu)}] [expr {round(2556.42*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_112_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[112\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[112].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_112_r"]
odb::dbBox_create $r [expr {round(1406.28*$dbu)}] [expr {round(2794.32*$dbu)}] [expr {round(1410.6*$dbu)}] [expr {round(2798.64*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_112_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[112\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[112].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_113_w"]
odb::dbBox_create $r [expr {round(1461.86*$dbu)}] [expr {round(2549.94*$dbu)}] [expr {round(1468.34*$dbu)}] [expr {round(2556.42*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_113_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[113\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[113].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_113_r"]
odb::dbBox_create $r [expr {round(1411.14*$dbu)}] [expr {round(2794.32*$dbu)}] [expr {round(1415.46*$dbu)}] [expr {round(2798.64*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_113_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[113\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[113].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_114_w"]
odb::dbBox_create $r [expr {round(1468.88*$dbu)}] [expr {round(2549.94*$dbu)}] [expr {round(1475.36*$dbu)}] [expr {round(2556.42*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_114_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[114\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[114].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_114_r"]
odb::dbBox_create $r [expr {round(1386.84*$dbu)}] [expr {round(2799.18*$dbu)}] [expr {round(1391.16*$dbu)}] [expr {round(2803.5*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_114_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[114\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[114].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_115_w"]
odb::dbBox_create $r [expr {round(1475.9*$dbu)}] [expr {round(2549.94*$dbu)}] [expr {round(1482.38*$dbu)}] [expr {round(2556.42*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_115_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[115\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[115].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_115_r"]
odb::dbBox_create $r [expr {round(1391.7*$dbu)}] [expr {round(2799.18*$dbu)}] [expr {round(1396.02*$dbu)}] [expr {round(2803.5*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_115_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[115\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[115].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_116_w"]
odb::dbBox_create $r [expr {round(1482.92*$dbu)}] [expr {round(2549.94*$dbu)}] [expr {round(1489.4*$dbu)}] [expr {round(2556.42*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_116_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[116\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[116].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_116_r"]
odb::dbBox_create $r [expr {round(1396.56*$dbu)}] [expr {round(2799.18*$dbu)}] [expr {round(1400.88*$dbu)}] [expr {round(2803.5*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_116_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[116\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[116].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_117_w"]
odb::dbBox_create $r [expr {round(1489.94*$dbu)}] [expr {round(2549.94*$dbu)}] [expr {round(1496.42*$dbu)}] [expr {round(2556.42*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_117_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[117\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[117].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_117_r"]
odb::dbBox_create $r [expr {round(1401.42*$dbu)}] [expr {round(2799.18*$dbu)}] [expr {round(1405.74*$dbu)}] [expr {round(2803.5*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_117_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[117\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[117].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_118_w"]
odb::dbBox_create $r [expr {round(1496.96*$dbu)}] [expr {round(2549.94*$dbu)}] [expr {round(1503.44*$dbu)}] [expr {round(2556.42*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_118_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[118\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[118].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_118_r"]
odb::dbBox_create $r [expr {round(1406.28*$dbu)}] [expr {round(2799.18*$dbu)}] [expr {round(1410.6*$dbu)}] [expr {round(2803.5*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_118_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[118\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[118].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_119_w"]
odb::dbBox_create $r [expr {round(1503.98*$dbu)}] [expr {round(2549.94*$dbu)}] [expr {round(1510.46*$dbu)}] [expr {round(2556.42*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_119_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[119\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[119].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_119_r"]
odb::dbBox_create $r [expr {round(1411.14*$dbu)}] [expr {round(2799.18*$dbu)}] [expr {round(1415.46*$dbu)}] [expr {round(2803.5*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_119_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[119\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[119].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_120_w"]
odb::dbBox_create $r [expr {round(1426.76*$dbu)}] [expr {round(2556.96*$dbu)}] [expr {round(1433.24*$dbu)}] [expr {round(2563.44*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_120_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[120\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[120].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_120_r"]
odb::dbBox_create $r [expr {round(1386.84*$dbu)}] [expr {round(2804.04*$dbu)}] [expr {round(1391.16*$dbu)}] [expr {round(2808.36*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_120_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[120\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[120].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_121_w"]
odb::dbBox_create $r [expr {round(1433.78*$dbu)}] [expr {round(2556.96*$dbu)}] [expr {round(1440.26*$dbu)}] [expr {round(2563.44*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_121_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[121\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[121].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_121_r"]
odb::dbBox_create $r [expr {round(1391.7*$dbu)}] [expr {round(2804.04*$dbu)}] [expr {round(1396.02*$dbu)}] [expr {round(2808.36*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_121_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[121\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[121].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_122_w"]
odb::dbBox_create $r [expr {round(1440.8*$dbu)}] [expr {round(2556.96*$dbu)}] [expr {round(1447.28*$dbu)}] [expr {round(2563.44*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_122_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[122\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[122].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_122_r"]
odb::dbBox_create $r [expr {round(1396.56*$dbu)}] [expr {round(2804.04*$dbu)}] [expr {round(1400.88*$dbu)}] [expr {round(2808.36*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_122_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[122\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[122].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_123_w"]
odb::dbBox_create $r [expr {round(1447.82*$dbu)}] [expr {round(2556.96*$dbu)}] [expr {round(1454.3*$dbu)}] [expr {round(2563.44*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_123_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[123\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[123].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_123_r"]
odb::dbBox_create $r [expr {round(1401.42*$dbu)}] [expr {round(2804.04*$dbu)}] [expr {round(1405.74*$dbu)}] [expr {round(2808.36*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_123_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[123\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[123].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_124_w"]
odb::dbBox_create $r [expr {round(1454.84*$dbu)}] [expr {round(2556.96*$dbu)}] [expr {round(1461.32*$dbu)}] [expr {round(2563.44*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_124_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[124\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[124].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_124_r"]
odb::dbBox_create $r [expr {round(1406.28*$dbu)}] [expr {round(2804.04*$dbu)}] [expr {round(1410.6*$dbu)}] [expr {round(2808.36*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_124_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[124\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[124].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_125_w"]
odb::dbBox_create $r [expr {round(1461.86*$dbu)}] [expr {round(2556.96*$dbu)}] [expr {round(1468.34*$dbu)}] [expr {round(2563.44*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_125_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[125\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[125].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_125_r"]
odb::dbBox_create $r [expr {round(1411.14*$dbu)}] [expr {round(2804.04*$dbu)}] [expr {round(1415.46*$dbu)}] [expr {round(2808.36*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_125_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[125\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[125].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_126_w"]
odb::dbBox_create $r [expr {round(1468.88*$dbu)}] [expr {round(2556.96*$dbu)}] [expr {round(1475.36*$dbu)}] [expr {round(2563.44*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_126_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[126\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[126].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_126_r"]
odb::dbBox_create $r [expr {round(1386.84*$dbu)}] [expr {round(2808.9*$dbu)}] [expr {round(1391.16*$dbu)}] [expr {round(2813.22*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_126_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[126\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[126].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_127_w"]
odb::dbBox_create $r [expr {round(1475.9*$dbu)}] [expr {round(2556.96*$dbu)}] [expr {round(1482.38*$dbu)}] [expr {round(2563.44*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_127_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[127\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[127].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_127_r"]
odb::dbBox_create $r [expr {round(1391.7*$dbu)}] [expr {round(2808.9*$dbu)}] [expr {round(1396.02*$dbu)}] [expr {round(2813.22*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_127_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[127\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[127].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_128_w"]
odb::dbBox_create $r [expr {round(1482.92*$dbu)}] [expr {round(2556.96*$dbu)}] [expr {round(1489.4*$dbu)}] [expr {round(2563.44*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_128_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[128\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[128].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_128_r"]
odb::dbBox_create $r [expr {round(1396.56*$dbu)}] [expr {round(2808.9*$dbu)}] [expr {round(1400.88*$dbu)}] [expr {round(2813.22*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_128_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[128\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[128].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_129_w"]
odb::dbBox_create $r [expr {round(1489.94*$dbu)}] [expr {round(2556.96*$dbu)}] [expr {round(1496.42*$dbu)}] [expr {round(2563.44*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_129_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[129\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[129].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_129_r"]
odb::dbBox_create $r [expr {round(1401.42*$dbu)}] [expr {round(2808.9*$dbu)}] [expr {round(1405.74*$dbu)}] [expr {round(2813.22*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_129_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[129\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[129].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_130_w"]
odb::dbBox_create $r [expr {round(1496.96*$dbu)}] [expr {round(2556.96*$dbu)}] [expr {round(1503.44*$dbu)}] [expr {round(2563.44*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_130_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[130\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[130].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_130_r"]
odb::dbBox_create $r [expr {round(1406.28*$dbu)}] [expr {round(2808.9*$dbu)}] [expr {round(1410.6*$dbu)}] [expr {round(2813.22*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_130_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[130\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[130].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_131_w"]
odb::dbBox_create $r [expr {round(1503.98*$dbu)}] [expr {round(2556.96*$dbu)}] [expr {round(1510.46*$dbu)}] [expr {round(2563.44*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_131_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[131\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[131].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_131_r"]
odb::dbBox_create $r [expr {round(1411.14*$dbu)}] [expr {round(2808.9*$dbu)}] [expr {round(1415.46*$dbu)}] [expr {round(2813.22*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_131_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[131\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[131].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_132_w"]
odb::dbBox_create $r [expr {round(1426.76*$dbu)}] [expr {round(2563.98*$dbu)}] [expr {round(1433.24*$dbu)}] [expr {round(2570.46*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_132_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[132\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[132].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_132_r"]
odb::dbBox_create $r [expr {round(1386.84*$dbu)}] [expr {round(2813.76*$dbu)}] [expr {round(1391.16*$dbu)}] [expr {round(2818.08*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_132_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[132\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[132].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_133_w"]
odb::dbBox_create $r [expr {round(1433.78*$dbu)}] [expr {round(2563.98*$dbu)}] [expr {round(1440.26*$dbu)}] [expr {round(2570.46*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_133_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[133\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[133].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_133_r"]
odb::dbBox_create $r [expr {round(1391.7*$dbu)}] [expr {round(2813.76*$dbu)}] [expr {round(1396.02*$dbu)}] [expr {round(2818.08*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_133_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[133\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[133].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_134_w"]
odb::dbBox_create $r [expr {round(1440.8*$dbu)}] [expr {round(2563.98*$dbu)}] [expr {round(1447.28*$dbu)}] [expr {round(2570.46*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_134_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[134\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[134].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_134_r"]
odb::dbBox_create $r [expr {round(1396.56*$dbu)}] [expr {round(2813.76*$dbu)}] [expr {round(1400.88*$dbu)}] [expr {round(2818.08*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_134_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[134\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[134].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_135_w"]
odb::dbBox_create $r [expr {round(1447.82*$dbu)}] [expr {round(2563.98*$dbu)}] [expr {round(1454.3*$dbu)}] [expr {round(2570.46*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_135_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[135\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[135].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_135_r"]
odb::dbBox_create $r [expr {round(1401.42*$dbu)}] [expr {round(2813.76*$dbu)}] [expr {round(1405.74*$dbu)}] [expr {round(2818.08*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_135_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[135\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[135].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_136_w"]
odb::dbBox_create $r [expr {round(1454.84*$dbu)}] [expr {round(2563.98*$dbu)}] [expr {round(1461.32*$dbu)}] [expr {round(2570.46*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_136_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[136\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[136].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_136_r"]
odb::dbBox_create $r [expr {round(1406.28*$dbu)}] [expr {round(2813.76*$dbu)}] [expr {round(1410.6*$dbu)}] [expr {round(2818.08*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_136_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[136\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[136].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_137_w"]
odb::dbBox_create $r [expr {round(1461.86*$dbu)}] [expr {round(2563.98*$dbu)}] [expr {round(1468.34*$dbu)}] [expr {round(2570.46*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_137_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_w[./]g_chunk\[137\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_w.g_chunk[137].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_137_r"]
odb::dbBox_create $r [expr {round(1411.14*$dbu)}] [expr {round(2813.76*$dbu)}] [expr {round(1415.46*$dbu)}] [expr {round(2818.08*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_137_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_5_r[./]g_chunk\[137\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_5_r.g_chunk[137].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_wv_w"]
odb::dbBox_create $r [expr {round(1456.88*$dbu)}] [expr {round(2433.98*$dbu)}] [expr {round(1463.36*$dbu)}] [expr {round(2440.46*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_wv_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_7_w[./]g_chunk\[0\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_7_w.g_chunk[0].u_local"}
set r [odb::dbRegion_create $b "ml_e2_WD_wv_r"]
odb::dbBox_create $r [expr {round(1630.24*$dbu)}] [expr {round(2559.24*$dbu)}] [expr {round(1634.56*$dbu)}] [expr {round(2563.56*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_WD_wv_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_7_r[./]g_chunk\[0\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_7_r.g_chunk[0].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_rv_w"]
odb::dbBox_create $r [expr {round(1468.88*$dbu)}] [expr {round(2563.98*$dbu)}] [expr {round(1475.36*$dbu)}] [expr {round(2570.46*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_rv_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_4_w[./]g_chunk\[0\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_4_w.g_chunk[0].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_rv_r"]
odb::dbBox_create $r [expr {round(1386.84*$dbu)}] [expr {round(2818.62*$dbu)}] [expr {round(1391.16*$dbu)}] [expr {round(2822.94*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_rv_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_4_r[./]g_chunk\[0\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_4_r.g_chunk[0].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_fault_w"]
odb::dbBox_create $r [expr {round(1475.9*$dbu)}] [expr {round(2563.98*$dbu)}] [expr {round(1482.38*$dbu)}] [expr {round(2570.46*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_fault_w"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_6_w[./]g_chunk\[0\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_6_w.g_chunk[0].u_local"}
set r [odb::dbRegion_create $b "ml_e2_RD_fault_r"]
odb::dbBox_create $r [expr {round(1391.7*$dbu)}] [expr {round(2818.62*$dbu)}] [expr {round(1396.02*$dbu)}] [expr {round(2822.94*$dbu)}]
set g [odb::dbGroup_create $r "ml_e2_RD_fault_r"]
set matched 0
foreach i [$b getInsts] { regsub -all {\\} [$i getName] {} n; if {[regexp {^u_lpl_6_r[./]g_chunk\[0\][./]u_local[./]} $n]} { $g addInst $i; incr matched } }
if {$matched == 0} {error "ML E2 hierarchy has no cells: u_lpl_6_r.g_chunk[0].u_local"}
