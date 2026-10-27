# Structural placement policy: S-face c_in capture registers c2 feed the far
# frontq port bank. Move the four capture flops within the S-face band inward
# from the SW corner. Pin locations, RTL, latency and interfaces are unchanged.
set blk [ord::get_db_block]
set dbu [[ord::get_db_tech] getDbUnitsPerMicron]
set cnt 0
for {set b 0} {$b<4} {incr b} {
 set suffix [expr {$b == 0 ? "P" : "PN0"}]
 set name [format {u_g_front_1_u_front.c2\[%d\]$_DFF_%s_} $b $suffix]
 set inst [$blk findInst $name]
 if {$inst eq "NULL"} {error "missing c2 source $name"}
 $inst setLocation [expr {int(round(16.2*$dbu))}] [expr {int(round((16.2+$b*0.54)*$dbu))}]
 $inst setPlacementStatus FIRM
 incr cnt
}
puts "E2_REACH_CONTROL_CLUSTER $cnt sources floorplan=(16.2,16.2..17.82)"
