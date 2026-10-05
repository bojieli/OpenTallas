# PRE_GLOBAL_ROUTE_TCL: real ASAP7 constant drivers on a retained CTS database.
# This completes omitted hilomap physical input preparation, not PG retagging.
set block [ord::get_db_block]
set db [ord::get_db]
set units [$block getDbUnitsPerMicron]
set specs {{one_ TIEHIx1_ASAP7_75t_R H 1} {zero_ TIELOx1_ASAP7_75t_R L 0}}
set plan {}
set area 0.0
set count 0
set cost [open /work/tie_cost.tsv w]
puts $cost "constant\tmaster\tpin\titerm_loads\tbterm_loads\tcell_area_um2\ttotal_area_um2"
# Inspect and price ALL actual loads before modifying the checkpoint.
foreach spec $specs {
 lassign $spec name master_name pin value
 set net [$block findNet $name]
 if {$net eq "NULL" || $net eq "" || [$net isSpecial]} {error "Expected nonspecial undriven constant $name"}
 set master [$db findMaster $master_name]
 if {$master eq "NULL" || $master eq ""} {error "Missing standard tie master $master_name"}
 set mt [$master findMTerm $pin]
 if {$mt eq "NULL" || $mt eq "" || [$mt getIoType] ne "OUTPUT"} {error "Tie output pin missing $master_name/$pin"}
 set iterms [$net getITerms]
 set bterms [$net getBTerms]
 foreach term $iterms {if {[$term getIoType] ne "INPUT"} {error "Constant $name already has a driver/inout"}}
 foreach term $bterms {if {[$term getIoType] ne "OUTPUT"} {error "Constant $name is not an output padding port"}}
 set n [expr {[llength $iterms]+[llength $bterms]}]
 set cell_area [expr {[$master getWidth]*double([$master getHeight])/($units*double($units))}]
 set price [expr {$n*$cell_area}]
 puts $cost "$name\t$master_name\t$pin\t[llength $iterms]\t[llength $bterms]\t$cell_area\t$price"
 set area [expr {$area+$price}]
 incr count $n
 lappend plan [list $net $master $pin $value $iterms $bterms]
}
puts $cost "TOTAL\t$count\t$area\tadded_state_bits=0\tadded_cycles=0\tclock_sinks=0\tPG_pins=[expr {2*$count}]"
close $cost
puts "PAULI_TIE_PRICE cells=$count area_um2=$area signal_fanout=1 added_state_bits=0 added_cycles=0"
set receipt [open /work/tie_bindings.tsv w]
puts $receipt "value\tcell\toutput_pin\tnet\tload"
set index 0
foreach row $plan {
 lassign $row old master pin value iterms bterms
 foreach term [concat $iterms $bterms] {
  set stem "pauli_tie_${value}_$index"
  if {[$block findInst $stem] ne "NULL" && [$block findInst $stem] ne ""} {error "Duplicate tie cell $stem"}
  set inst [odb::dbInst_create $block $master $stem]
  set net [odb::dbNet_create $block "${stem}_out"]
  # A new ordinary signal net has an actual tie source; old PG types are never retagged.
  [$inst findITerm $pin] connect $net
  if {[lsearch -exact $iterms $term]>=0} {
   set sink [$term getInst]
   lassign [$sink getLocation] x y
   set load "[$sink getName]/[[$term getMTerm] getName]"
  } else {
   set boxes [[lindex [$term getBPins] 0] getBoxes]
   if {![llength $boxes]} {error "Padding port lacks actual physical pin [$term getName]"}
   set box [lindex $boxes 0]
   set x [$box xMin]; set y [$box yMin]
   set load "PORT/[$term getName]"
  }
  $inst setLocation $x $y
  $inst setOrient R0
  $inst setPlacementStatus PLACED
  $term connect $net
  puts $receipt "$value\t$stem\t$pin\t[$net getName]\t$load"
  incr index
 }
 if {[llength [$old getITerms]] || [llength [$old getBTerms]]} {error "Constant loads not completely rebound"}
 # Delete the now-empty virtual constant; real VDD/VSS special nets are untouched.
 odb::dbNet_destroy $old
}
close $receipt
# Platform's existing real supply rules connect the new VDD/VSS pins.
global_connect
# Same classic legalizer already selected for this fenced context.
detailed_placement -use_diamond_legalizer
check_placement -verbose
set n 0
foreach inst [$block getInsts] {
 if {![string match pauli_tie_* [$inst getName]]} {continue}
 incr n
 foreach supply {VDD VSS} {
  set term [$inst findITerm $supply]
  set net [$term getNet]
  if {$net eq "NULL" || $net eq "" || ![$net isSpecial]} {error "Actual tie supply unconnected [$inst getName]/$supply"}
 }
}
if {$n!=$count} {error "Tie count changed during legalization"}
write_db $::env(RESULTS_DIR)/4_cts_ties.odb
write_verilog $::env(RESULTS_DIR)/4_cts_ties.v
puts "PAULI_TIE_READY legal_cells=$n actual_supply_pins=[expr {2*$n}]"
