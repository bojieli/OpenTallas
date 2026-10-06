# Run in the pinned ORFS image with the immutable source090bd365 CTS base
# mounted read-only at /checkpoint. This estimates placement RC, not live GRT
# RC or final extracted signoff. No constraint edits, repair or write_db.
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7sc7p5t_28_R_1x_220121a.lef
define_corners ss ff
foreach corner {ss ff} tag {SS FF} {
 foreach family {AO INVBUF OA SEQ SIMPLE} {
  set candidates [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_${family}_RVT_${tag}_*]
  # Pinned families shipped in this image; select the same 211120 / 220122 /
  # 220123 revisions as existing W18 SS/FF signoff reader.
  foreach f $candidates {
   if {[regexp {(211120|220122|220123)\.lib(\.gz)?$} $f]} {read_liberty -corner $corner $f}
  }
 }
}
read_db /checkpoint/4_cts.odb
read_sdc /checkpoint/4_cts.sdc
set_propagated_clock [all_clocks]
source /OpenROAD-flow-scripts/flow/platforms/asap7/setRC.tcl
estimate_parasitics -placement
puts "OT_CHECKPOINT_PHASE RETAINED_CTS_NOT_LIVE_GRT_NOT_SIGNOFF"
report_clock_properties [all_clocks]
foreach corner {ss ff} {
 puts "OT_CORNER $corner"
 foreach endpoint {{data[6562]$_DFF_P_/D} {o_tx_rec[122]}} {
  puts "OT_TARGET $endpoint"
  if {$endpoint eq {o_tx_rec[122]}} {
   set target [get_ports $endpoint]
  } else {
   set target [get_pins $endpoint]
  }
  if {[llength $target] != 1} {error "exact source-bound target is absent: $endpoint"}
  report_checks -corner $corner -to $target -path_delay max -format full_clock_expanded -fields {slew cap fanout input net}
  report_checks -corner $corner -to $target -path_delay min -format full_clock_expanded -fields {slew cap fanout input net}
 }
}
exit
