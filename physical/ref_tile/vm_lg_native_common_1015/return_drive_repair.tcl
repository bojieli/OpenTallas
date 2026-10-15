# Same-edge INV drive repair; source-state, clocks, constraints and ports unchanged.
# The caller sets exact source net; this addresses one measured return capture.
set block [ord::get_db_block]
set net [$block findNet $::ot_lg_repair_net]
if {$net eq "NULL"} {
 # CTS names need not equal routed net names after hold repair. Resolve the
 # literal RTL capture instance, then use its actual ODB D net.
 set target "u_core.return_d\[$::ot_lg_repair_bit\]\$_DFF_P_"
 set target_inst [$block findInst $target]
 if {$target_inst eq "NULL"} {
  foreach candidate [$block getInsts] {
   set normalized [string map [list "\\" ""] [$candidate getName]]
   if {$normalized eq $target} {set target_inst $candidate;break}
  }
 }
 if {$target_inst eq "NULL"} {error "LG repair: capture instance absent $target"}
 set net [[$target_inst findITerm D] getNet]
 puts "LG_SLEW_REPAIR actual CTS net=[$net getName] resolved from $target/D"
}
set drivers {}; set sinks {}
foreach it [$net getITerms] {
 if {[$it getIoType] eq "OUTPUT"} {lappend drivers $it}
 if {[$it getIoType] eq "INPUT"} {lappend sinks $it}
}
if {[llength $drivers] != 1 || [llength $sinks] != 2} {
 error "LG repair: expected one driver/two capture sinks on $::ot_lg_repair_net"
}
set inst [[lindex $drivers 0] getInst]
set old [$inst getMaster]
if {![regexp {^INVx[12]_ASAP7_75t_R$} [$old getName]]} {
 error "LG repair: unexpected driver [$old getName]"
}
set new [[ord::get_db] findMaster INVx4_ASAP7_75t_R]
if {$new eq "NULL"} {error "LG repair: missing INVx4 master"}
set delta [expr {([$new getWidth]*[$new getHeight]-[$old getWidth]*[$old getHeight])/1.0e6}]
puts "LG_SLEW_REPAIR net=$::ot_lg_repair_net inst=[$inst getName] old=[$old getName] new=[$new getName] same_edge=1 delta_area_um2=$delta"
# Native dbSta master-swap callback updates timing and preserves net identity.
if {![$inst swapMaster $new]} {error "LG repair: actual ODB master swap failed"}
# Legalize the actual wider standard cell before routing; no CTS/phase change.
detailed_placement
check_placement -verbose
