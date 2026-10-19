# Refuse before CTS unless the real placed graph satisfies the source-bound model.
set vb [ord::get_db_block]
set vdu [[ord::get_db_tech] getDbUnitsPerMicron]
set vi [dict create]
foreach inst [$vb getInsts] {
 regsub -all {\\} [$inst getName] {} key
 if {[dict exists $vi $key]} {error "PVM_HOP ambiguous exact cell $key"}
 dict set vi $key $inst
 set m [$inst getMaster]
 if {[$m isBlock] || [$m getType] in {CORE_WELLTAP CORE_SPACER ENDCAP}} continue
 if {[$inst getPlacementStatus] in {NONE UNPLACED}} {error "PVM_HOP unplaced functional cell $key"}
 set bb [$inst getBBox]
 if {[$bb yMin]<round(229.23*$vdu) || [$bb yMax]>round(300.24*$vdu)} {error "PVM_HOP functional cell outside sole band $key"}
}
foreach name {pvm_macro_cone pvm_macro_W_constants} {
 set rg [$vb findRegion $name]
 if {$rg eq "NULL" || [$rg getRegionType] ne "EXCLUSIVE"} {error "PVM_HOP missing real fence $name"}
 set groups [$rg getGroups]
 if {[llength $groups]!=1} {error "PVM_HOP missing physical GPL group $name"}
 set group [lindex $groups 0]
 if {[$group getType] ne "PHYSICAL_CLUSTER" || [llength [$group getInsts]]!=[llength [$rg getRegionInsts]]} {error "PVM_HOP GPL/DPL membership disagreement $name"}
 set boxes [$rg getBoundaries]
 if {[llength $boxes]!=1} {error "PVM_HOP fence $name not rectangular"}
 set box [lindex $boxes 0]
 set n 0
 foreach inst [$rg getRegionInsts] {
  set bb [$inst getBBox]
  if {[$bb xMin]<[$box xMin] || [$bb yMin]<[$box yMin] || [$bb xMax]>[$box xMax] || [$bb yMax]>[$box yMax]} {error "PVM_HOP instance outside actual fence: [$inst getName]"}
  incr n
 }
 if {$n==0} {error "PVM_HOP empty required fence $name"}
 puts "PVM_HOP fence $name actual placed members=$n"
}
proc pvm_hop_bbox {px py bb} {
 global vdu
 set maxd 0.0
 foreach x [list [$bb xMin] [$bb xMax]] {foreach y [list [$bb yMin] [$bb yMax]] {
  set d [expr {(abs($x-$px)+abs($y-$py))/double($vdu)}]
  if {$d>$maxd} {set maxd $d}
 }}
 return $maxd
}
set vm {}
foreach inst [$vb getInsts] {if {[[$inst getMaster] isBlock]} {lappend vm $inst}}
if {[llength $vm]!=1} {error "PVM_HOP wrong macro count"}
set vm [lindex $vm 0]
if {[[$vm getMaster] getName] ne "ot_sram_1r1w_64x512_m1_r2c2_p192_mir" || [$vm getOrient] ne "R180"} {error "PVM_HOP wrong source macro/orientation"}
lassign [$vm getLocation] mx my
if {$mx!=round(43.2*$vdu) || $my!=round(43.2*$vdu)} {error "PVM_HOP macro off actual43.2lattice"}
regsub -all {\\} [$vm getName] {} vmn
set vc [get_cells -quiet $vmn]
set vmax 0.0
set vcount 0
foreach pin [get_pins -of_objects $vc] {
 set pn [lindex [split [get_full_name $pin] /] end]
 if {$pn eq "clk"} continue
 set it [$vm findITerm $pn]
 if {$it eq "NULL"} {error "PVM_HOP missing exact macro port $pn"}
 lassign [$it getAvgXY] ok px py
 if {!$ok} {error "PVM_HOP no actual contact coordinates $pn"}
 if {[string match {rd_out*} $pn]} {set points [get_fanout -from $pin -flat -endpoints_only]} else {set points [get_fanin -to $pin -flat -startpoints_only]}
 foreach point $points {
  set pcs [get_cells -of_objects $point]
  if {[llength $pcs]!=1} {error "PVM_HOP macro endpoint lacks exact register $pn:[get_full_name $point]"}
  set cn [get_full_name [lindex $pcs 0]]
  if {![dict exists $vi $cn]} {error "PVM_HOP missing exact endpoint $cn"}
  set inst [dict get $vi $cn]
  set d [pvm_hop_bbox $px $py [$inst getBBox]]
  if {$d>405.0} {error "PVM_HOP endpoint $pn -> $cn lengthbound $d exceeds405um"}
  if {$d>$vmax} {set vmax $d}
  incr vcount
 }
 # Direct physical net endpoints, including one-sink constant ties.
 set net [$it getNet]
 if {$net eq "NULL"} {error "PVM_HOP unconnected actual macro net $pn"}
 foreach peer [$net getITerms] {
  if {$peer eq $it} continue
  lassign [$peer getAvgXY] pok qx qy
  if {!$pok} {error "PVM_HOP unplaced direct endpoint $pn"}
  set d [expr {(abs($qx-$px)+abs($qy-$py))/double($vdu)}]
  if {$d>405.0} {error "PVM_HOP direct wire endpoint $pn distance $d exceeds405um"}
  if {$d>$vmax} {set vmax $d}
 }
}
puts "PVM_HOP PASS actual endpoint_pairs=$vcount max_Manhattan_um=$vmax; route detours/clock/nativeSTA still require measured signoff"
