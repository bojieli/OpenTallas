set_thread_count 1
read_db /work/results/asap7/opentallas_ot_v41_rom_stage_q_pg_cdc_w10_asap7_spine_cdc_E1_20261004/base/4_cts.odb
set b [ord::get_db_block]
foreach name {VDD VSS} {
 set n [$b findNet $name]
 foreach w [$n getSWires] { foreach r [$w getWires] {
  if {[$r isVia]} { continue }
  if {[[$r getTechLayer] getName] ne "M5"} { continue }
  if {1} { puts "PDN $name [$r xMin] [$r yMin] [$r xMax] [$r yMax]" }
 } }
}
puts "CLEAR_CMD [info commands clear_io_pin_constraints]"
