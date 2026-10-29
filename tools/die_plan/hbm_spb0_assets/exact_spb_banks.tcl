# Exact FF placement for the declared ot_hbm_spb0_regs primitive only; no nearest-site fallback.
# Source from face_flops.tcl, after loading spb_native_sites.tcl.
set spb_seen {}
set spb_fh [open $::env(RESULTS_DIR)/ot_face_flops.txt a]
foreach cell [$ff_blk getInsts] {
 set nm [string map {\\ {}} [$cell getName]]
 if {![regexp {(u_hbm_spb0_rx|u_hbm_spb0_tx)[/.]g_stage\[([0-9]+)\][/.]rd\[([0-9]+)\]} $nm -> inst stage bit]} {continue}
 if {![string match "*DFF*" [[$cell getMaster] getName]]} {error "SPB station is not a DFF: $nm"}
 set key "$inst,$stage,$bit"
 if {![dict exists $spb_native_sites $key] || [dict exists $spb_seen $key]} {error "SPB missing/duplicate stage bit: $nm"}
 lassign [dict get $spb_native_sites $key] x y
 set cx [expr {round($x*$ff_dbu)}];set cy [expr {round($y*$ff_dbu)}]
 if {![dict exists $ff_orient $cy] || ($cx-$ff_x0)%$ff_sw != 0} {error "SPB site not on actual row/site: $nm $x $y"}
 set master [$cell getMaster]
 if {[$master getWidth] > 1.35*$ff_dbu+1 || [$master getHeight] > .27*$ff_dbu+1} {error "SPB master exceeds allocation: $nm"}
 if {$cx<$ff_x0 || $cy<$ff_y0 || $cx+[$master getWidth]>$ff_x1 || $cy+[$master getHeight]>$ff_y1} {error "SPB site outside partition: $nm"}
 $cell setPlacementStatus PLACED
 $cell setOrient [dict get $ff_orient $cy]
 $cell setLocation $cx $cy
 $cell setPlacementStatus FIRM
 dict set spb_seen $key 1
 puts $spb_fh "$nm\tspb-native:$inst:$stage\t$x\t$y\t-"
}
close $spb_fh
if {[dict size $spb_seen] != 4104 || [dict size $spb_native_sites] != 4104} {error "SPB expected exactly 4104 declared native FFs, got [dict size $spb_seen]"}
puts "SPB_NATIVE exact placement 4104 FFs; no fallback"
