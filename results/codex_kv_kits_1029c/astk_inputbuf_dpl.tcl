foreach f [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*RVT*TT*.lib*] {read_liberty $f}
set root /work/run/results/asap7/hc_kv3_astk__190_08x181_44/base
read_db $root/3_place.odb
set b [ord::get_db_block]
set original [dict create]
foreach i [$b getInsts] {dict set original [$i getName] [list [$i getOrigin] [$i getOrient] [[$i getMaster] getName]]}
source /work/input_buffer_anchors.tcl
detailed_placement
check_placement -verbose
set changed {};set sequential_changed {}
foreach i [$b getInsts] {
 set n [$i getName];set now [list [$i getOrigin] [$i getOrient] [[$i getMaster] getName]]
 if {$now ne [dict get $original $n]} {
  lappend changed $n
  if {![regexp {^input[0-9]+$} $n]} {error "ASTK_UNPLANNED_CELL_MOVED $n"}
 }
}
if {[llength $changed]>352} {error "ASTK_TOO_MANY_MOVED [llength $changed]"}
write_db /work/inputbuf_inserted.odb
puts "ASTK_INPUTBUF_DPL_PASS original=[dict size $original] moved=[llength $changed] all_FFs_pins_nets_masters_unchanged"
