# Opt-in real loaded carry-branch buffering; no register or epoch change.
# New physical buffer cells require fresh legalization, PG and area receipts.
set br_block [ord::get_db_block]
set br_report [open $::env(RESULTS_DIR)/s81_adder_branch_buffer.tsv w]
puts $br_report "scope\tinstance\told_master\tnew_buffer\tactual_output_net\tactual_loads"
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
   if {$br_old_name eq "AOI21x1_ASAP7_75t_R" && $br_loads>=12} {
    set br_target BUFx10_ASAP7_75t_R
    set br_master [[ord::get_db] findMaster $br_target]
    if {$br_master eq "NULL"} {error "S81_ADDER_BRANCH missing $br_target"}
    set br_buffer_name "s81_adder_branch_[string map {. _ \[ _ \] _ \\ _} $br_name]"
    if {[$br_block findInst $br_buffer_name] ne "NULL"} {error "S81_ADDER_BRANCH refuses duplicate $br_buffer_name"}
    set br_move {}
    foreach br_pin [$br_net getITerms] {if {[$br_pin isInputSignal]} {lappend br_move $br_pin}}
    if {[llength $br_move]!=$br_loads || [llength [$br_net getBTerms]]} {error "S81_ADDER_BRANCH requires internal actual load-only cut"}
    set br_new_net [odb::dbNet_create $br_block "${br_buffer_name}_out"]
    set br_buffer [odb::dbInst_create $br_block $br_master $br_buffer_name]
    [$br_buffer findITerm A] connect $br_net
    [$br_buffer findITerm Y] connect $br_new_net
    foreach br_pin $br_move {$br_pin disconnect;$br_pin connect $br_new_net}
    # This static probe only seeds geometry; fresh native legalization is mandatory.
    lassign [$br_inst getLocation] br_x br_y
    $br_buffer setOrient [$br_inst getOrient]
    $br_buffer setLocation [expr {$br_x+[$br_old getWidth]}] $br_y
    $br_buffer setPlacementStatus PLACED
    set_dont_touch [get_cells $br_buffer_name]
    puts $br_report "$br_scope\t$br_name\t$br_old_name\t$br_buffer_name:$br_target\t[$br_net getName]\t$br_loads"
    incr br_count
   }
   foreach br_input $br_inputs {if {$br_input ne "NULL"} {lappend br_todo $br_input}}
  }
 }
 puts "S81_USED_DRIVE $br_scope actual_endpoints$br_seeds used_comb_nodes[dict size $br_seen] actual_consumed_buffer_additions$br_count; no new state/epoch, same Boolean load signal"
}
close $br_report
