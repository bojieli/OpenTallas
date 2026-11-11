# T41FORM (DIE-S81-85 t41form 11-10) PRE_FLOORPLAN wrapper: the kit's own hook, then
#  (1) set_max_fanout 24 on the design, so every repair_design (floorplan / 3_4 resize / GRT) buffers to <= 24 loads;
#  (2) dont_touch on the RTL hold-pad buffers (ot_t41_hpad u_hp_<slot>), so floorplan unbuffer / GPL remove_buffers /
#      repair_design never remove or resize them.  Fails closed when the pad count is not the generated count.
source /work/pre_floorplan_type.tcl
set_max_fanout 24 [current_design]
puts "T41FORM set_max_fanout 24 [current_design]"
set t41_n 0
foreach t41_i [[ord::get_db_block] getInsts] {
  if {[string match "*u_hp_ft*" [$t41_i getName]] && [[$t41_i getMaster] getName] eq "BUFx2_ASAP7_75t_R"} {
    $t41_i setDoNotTouch 1; incr t41_n
  }
}
puts "T41FORM_HPAD dont_touch $t41_n"
if {$t41_n != 38528} { error "T41FORM_HPAD expected 38528 pad buffers (4816 bits x 8), found $t41_n" }
unset t41_n t41_i
