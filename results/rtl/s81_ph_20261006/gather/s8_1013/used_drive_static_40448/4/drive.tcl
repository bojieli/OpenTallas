# Opt-in physical drive repair. Original arithmetic RTL and register edges stay.
# Select only real INVx1 drivers in the actual four-root stage-3 data cones.
set ad_block [ord::get_db_block]
set ad_target INVx4_ASAP7_75t_R
if {[info exists ::env(S81_ADDER_INV_MASTER)]} {set ad_target $::env(S81_ADDER_INV_MASTER)}
if {![regexp {^INVx(3|4|6|8)_ASAP7_75t_R$} $ad_target]} {error "S81_ADDER_DRIVE unsupported Boolean-equivalent inverter $ad_target"}
set ad_master [[ord::get_db] findMaster $ad_target]
if {$ad_master eq "NULL"} {error "S81_ADDER_DRIVE missing native master $ad_target"}
set ad_todo {};set ad_seen {};set ad_seeds 0
foreach ad_inst [$ad_block getInsts] {
 if {![[$ad_inst getMaster] isSequential]} continue
 set ad_name [string map {\\ ""} [$ad_inst getName]]
 if {[regexp {^u_l\.g_r\[[0-3]\]\.u_root\.u_add\.s3_val\[[0-9]+\]\$_DFF} $ad_name]} {
  set ad_dp [$ad_inst findITerm D]
  if {$ad_dp eq "NULL"} {error "S81_ADDER_DRIVE genuine s3_val lacks D"}
  lappend ad_todo [$ad_dp getNet];incr ad_seeds
 }
}
if {$ad_seeds!=108} {error "S81_ADDER_DRIVE expected108 actual stage3 state endpoints, got$ad_seeds"}
set ad_report [open $::env(RESULTS_DIR)/s81_adder_drive.tsv w]
puts $ad_report "instance\told_master\tnew_master\tactual_output_net\tactual_loads\tactual_stage3_data_endpoints"
set ad_count 0
while {[llength $ad_todo]} {
 set ad_net [lindex $ad_todo end];set ad_todo [lrange $ad_todo 0 end-1]
 foreach ad_it [$ad_net getITerms] {
  if {![$ad_it isOutputSignal]} continue
  set ad_inst [$ad_it getInst];set ad_name [$ad_inst getName];set ad_old [$ad_inst getMaster]
  if {[$ad_old isSequential] || [$ad_old isBlock] || [dict exists $ad_seen $ad_name]} continue
  dict set ad_seen $ad_name 1
  set ad_inputs {};set ad_loads 0
  foreach ad_pin [$ad_inst getITerms] {if {[$ad_pin isInputSignal]} {lappend ad_inputs [$ad_pin getNet]}}
  foreach ad_pin [$ad_net getITerms] {if {![$ad_pin isOutputSignal]} {incr ad_loads}}
  if {[$ad_old getName] eq "INVx1_ASAP7_75t_R" && $ad_loads>=8} {
   set ad_a [$ad_inst findITerm A];set ad_y [$ad_inst findITerm Y]
   if {$ad_a eq "NULL" || $ad_y eq "NULL" || [$ad_y getNet] ne $ad_net} {error "S81_ADDER_DRIVE unexpected inverter ABI $ad_name"}
   set ad_anet [$ad_a getNet]
   if {![$ad_inst swapMaster $ad_master]} {error "S81_ADDER_DRIVE native master swap failed $ad_name"}
   if {[[$ad_inst findITerm A] getNet] ne $ad_anet || [[$ad_inst findITerm Y] getNet] ne $ad_net} {error "S81_ADDER_DRIVE changed real connectivity $ad_name"}
   set_dont_touch [get_cells $ad_name]
   puts $ad_report "$ad_name\tINVx1_ASAP7_75t_R\t$ad_target\t[$ad_net getName]\t$ad_loads\t$ad_seeds"
   incr ad_count
  }
  foreach ad_input $ad_inputs {if {$ad_input ne "NULL"} {lappend ad_todo $ad_input}}
 }
}
close $ad_report
if {$ad_count<1} {error "S81_ADDER_DRIVE no consumed weak driver found; refuses unused candidate"}
puts "S81_ADDER_DRIVE actual$ad_count existing used INV drivers ->$ad_target in108 genuine stage3 data endpoint cones; no new cell/state/epoch, A/Y connectivity preserved"
