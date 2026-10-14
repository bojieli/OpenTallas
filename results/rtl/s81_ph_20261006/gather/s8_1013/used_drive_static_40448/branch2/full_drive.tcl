# Existing Boolean-equivalent stage3 exponent/value/code cone drive repair, no state/epoch change.
set br_block [ord::get_db_block]
set br_report [open $::env(RESULTS_DIR)/s81_adder_full_drive.tsv w]
puts $br_report "scope\tinstance\told_master\tnew_master\tactual_output_net\tactual_loads"
foreach br_scope {adder} {
 set br_todo {};set br_seen {};set br_seeds 0;set br_count 0
 foreach br_inst [$br_block getInsts] {
  if {![[$br_inst getMaster] isSequential]} continue
  set br_name [string map {\\ ""} [$br_inst getName]]
  if {![regexp {^u_l\.g_r\[[0-3]\]\.u_root\.u_add\.s3_} $br_name]} continue
  set br_pin [$br_inst findITerm D]
  if {$br_pin eq "NULL"} {error "S81_USED_DRIVE missing actual sequential input $br_name $br_scope"}
  lappend br_todo [$br_pin getNet];incr br_seeds
 }
 if {$br_seeds<1} {error "S81_USED_DRIVE no actual $br_scope endpoints"}
 while {[llength $br_todo]} {
  set br_net [lindex $br_todo end];set br_todo [lrange $br_todo 0 end-1]
  if {$br_net eq "NULL"} continue
  foreach br_it [$br_net getITerms] {
   if {![$br_it isOutputSignal]} continue
   set br_inst [$br_it getInst];set br_name [$br_inst getName];set br_old [$br_inst getMaster]
   if {[$br_old isSequential] || [$br_old isBlock] || [dict exists $br_seen $br_name]} continue
   dict set br_seen $br_name 1
   set br_inputs {};set br_loads 0
   foreach br_pin [$br_inst getITerms] {if {[$br_pin isInputSignal]} {lappend br_inputs [$br_pin getNet]}}
   foreach br_pin [$br_net getITerms] {if {![$br_pin isOutputSignal]} {incr br_loads}}
   set br_target ""
   set br_old_name [$br_old getName]
   if {$br_loads>=8} {
    if {$br_old_name in {INVx1_ASAP7_75t_R INVx2_ASAP7_75t_R}} {set br_target INVx3_ASAP7_75t_R}
    if {$br_old_name eq "BUFx3_ASAP7_75t_R"} {set br_target BUFx10_ASAP7_75t_R}
    if {$br_old_name eq "AO21x1_ASAP7_75t_R"} {set br_target AO21x2_ASAP7_75t_R}
   }
   # Actual exponent priority path contains loaded OR4 and NAND2 gates.
   if {$br_loads>=4} {
    if {$br_old_name eq "OR4x1_ASAP7_75t_R"} {set br_target OR4x2_ASAP7_75t_R}
    if {$br_old_name eq "NAND2x1_ASAP7_75t_R"} {set br_target NAND2x2_ASAP7_75t_R}
   }
   if {$br_target ne ""} {
    set br_master [[ord::get_db] findMaster $br_target]
    if {$br_master eq "NULL"} {error "S81_USED_DRIVE unavailable native cell $br_target"}
    set br_connections {}
    foreach br_pin [$br_inst getITerms] {dict set br_connections [[$br_pin getMTerm] getName] [$br_pin getNet]}
    if {![$br_inst swapMaster $br_master]} {error "S81_USED_DRIVE failed real cell swap $br_name"}
    dict for {br_pin_name br_pin_net} $br_connections {
     set br_pin [$br_inst findITerm $br_pin_name]
     if {$br_pin eq "NULL" || [$br_pin getNet] ne $br_pin_net} {error "S81_USED_DRIVE altered real signal/PG connectivity $br_name/$br_pin_name"}
    }
    set_dont_touch [get_cells $br_name]
    puts $br_report "$br_scope\t$br_name\t$br_old_name\t$br_target\t[$br_net getName]\t$br_loads"
    incr br_count
   }
   foreach br_input $br_inputs {if {$br_input ne "NULL"} {lappend br_todo $br_input}}
  }
 }
 puts "S81_USED_DRIVE $br_scope actual_endpoints$br_seeds used_comb_nodes[dict size $br_seen] real_existing_cell_swaps$br_count; no new cell/state/epoch, signal/PG connectivity preserved"
}
close $br_report
