# Refuse before CTS unless the real placed graph satisfies the source-bound model.
set vb [ord::get_db_block]
set vdu [[ord::get_db_tech] getDbUnitsPerMicron]
set vi [dict create]
if {![info exists pvm_stage]} {set pvm_stage pre_dpl}
set pvm_unlegal 0
foreach inst [$vb getInsts] {
 regsub -all {\\} [$inst getName] {} key
 if {[dict exists $vi $key]} {error "PVM_HOP ambiguous exact cell $key"}
 dict set vi $key $inst
 set m [$inst getMaster]
 if {[$m isBlock] || [$m getType] in {CORE_WELLTAP CORE_SPACER ENDCAP}} continue
 if {[$inst getPlacementStatus] in {NONE UNPLACED}} {error "PVM_HOP unplaced functional cell $key"}
 set bb [$inst getBBox]
 if {[$bb yMin]<round(229.23*$vdu) || [$bb yMax]>round(300.24*$vdu)} {
  # Pre-DPL, resizer repeaters (repair_design long wires) sit at unlegalized PLACED spots; rows exist only in the band, so
  # DPL legalizes them into it. Anything else outside the band is an error; the strict band check reruns on 3_place.odb.
  if {$pvm_stage eq "pre_dpl" && [$inst getPlacementStatus] eq "PLACED" && [string match {wire*} $key]} {incr pvm_unlegal; continue}
  error "PVM_HOP functional cell outside sole band $key"
 }
}
puts "PVM_HOP stage=$pvm_stage unlegalized_repeaters_below_band=$pvm_unlegal"
# constants: FIRM on legal sites inside their two rows (macro_regions.tcl pvm_fix_constants, df4214d0d)
set vcn 0
foreach inst [$vb getInsts] {
 if {[[$inst getMaster] getName] ni {TIEHIx1_ASAP7_75t_R TIELOx1_ASAP7_75t_R}} continue
 set bb [$inst getBBox]
 if {[$bb yMin]>=round(229.23*$vdu) && [$bb yMax]<=round(229.77*$vdu) && [$bb xMin]>=round(86.4*$vdu) && [$bb xMax]<=round(172.8*$vdu)} {
  if {[$inst getPlacementStatus] ne "FIRM"} {error "PVM_HOP constant not FIRM [$inst getName]"}
  incr vcn
 }
}
if {$vcn<546} {error "PVM_HOP only $vcn of 546 W constants in their rows"}
puts "PVM_HOP W constants FIRM in rows=$vcn"
foreach name {pvm_macro_cone} {
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
set ::pvm_vdu $vdu
proc pvm_hop_bbox {px py bb} {
 set vdu $::pvm_vdu
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
