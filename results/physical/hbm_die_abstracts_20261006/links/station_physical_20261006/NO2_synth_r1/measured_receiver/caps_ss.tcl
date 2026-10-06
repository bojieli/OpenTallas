read_liberty {/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_AO_RVT_SS_nldm_211120.lib.gz}
read_liberty {/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_SS_nldm_220122.lib.gz}
read_liberty {/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_OA_RVT_SS_nldm_211120.lib.gz}
read_liberty {/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_SS_nldm_220123.lib}
read_liberty {/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SIMPLE_RVT_SS_nldm_211120.lib.gz}
read_verilog /mapped.v
link_design ot_hbm_native_frame_station
set_units -time ps -capacitance fF
set f [open /out/caps_ss.tsv w]
puts $f "port	cap_fF	sink_count	sinks"
foreach p [all_inputs] {
 set cap 0;set sinks {};set pin_count 0
 foreach pin [get_fanout -from $p -flat -pin_levels 1 -trace_arcs all] {
  if {[get_property $pin direction] ne "input"} {continue}
  set cs [get_cells -of_objects $pin]
  if {[llength $cs]!=1} {continue}
  set ref [get_property $cs ref_name]
  set name [lindex [split [get_full_name $pin] /] end]
  set lp [get_lib_pins -quiet */$ref/$name]
  if {[llength $lp]!=1} {continue}
  set c [get_property $lp capacitance]
  set cap [expr {$cap+$c}];incr pin_count;lappend sinks [list [get_full_name $pin] $ref $c]
 }
 if {$cap<=0} {error "no actual positive receiver cap [get_full_name $p]"}
 puts $f [join [list [get_full_name $p] $cap $pin_count $sinks] "	"]
}
close $f
puts OT_RECEIVER_CAPS_DONE
exit
