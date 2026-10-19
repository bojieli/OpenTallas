foreach lib [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*RVT_TT*.lib*] {read_liberty $lib}
read_liberty /src/physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2_p192_mir/ot_sram_1r1w_64x512_m1_r2c2_p192_mir_tt.lib
read_db /work/1_synth_tie_split.odb
set macro_name {}
foreach inst [[ord::get_db_block] getInsts] {if {[[$inst getMaster] isBlock]} {set macro_name [$inst getName]}}
set c [get_cells -quiet $macro_name]
puts "STACK_NAME $macro_name COUNT [llength $c]"
if {[llength $c]!=1} {error "expectedexactlyone macro"}
set f [open /work/macro_functional_cones.tsv w]
puts $f "macro_pin\trole\tobject"
foreach p [get_pins -of_objects $c] {
 set n [get_full_name $p];set port [lindex [split $n /] end]
 if {[regexp {^(wd_in|w_addr_in|w_ce_in|r_addr_in)} $port]} {
  foreach q [get_fanin -to $p -flat -startpoints_only] {puts $f "$port\tstartpoint\t[get_full_name $q]"}
  foreach q [get_fanin -to $p -flat] {
   foreach cell [get_cells -of_objects $q] {puts $f "$port\tfanin_cell\t[get_full_name $cell]"}
  }
 } elseif {[string match {rd_out*} $port]} {
  foreach q [get_fanout -from $p -flat -endpoints_only] {puts $f "$port\tendpoint\t[get_full_name $q]"}
  foreach q [get_fanout -from $p -flat] {
   foreach cell [get_cells -of_objects $q] {puts $f "$port\tfanout_cell\t[get_full_name $cell]"}
  }
 }
}
close $f
puts "MACRO_CONES_WRITTEN"
exit
