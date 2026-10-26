# usage: openroad -exit -no_init my_check.tcl  with env DEF, SDC, PAR (spef path or "rcx"), TAG, CELLLEFS (space list), MLEFS, MLIBS
set PLAT /home/ubuntu/.local/opentallas-pdk-asap7-platform/asap7
read_lef $PLAT/lef/asap7_tech_1x_201209.lef
foreach l $::env(CELLLEFS) { read_lef $l }
foreach l $::env(MLEFS) { if {$l ne ""} { read_lef $l } }
foreach l [glob $PLAT/lib/NLDM/*RVT_TT*] { read_liberty $l }
foreach l [glob $PLAT/lib/NLDM/*_LVT_TT_* $PLAT/lib/NLDM/*_SLVT_TT_*] { if {![string match *FAKE* $l]} { read_liberty $l } }
foreach l $::env(MLIBS) { if {$l ne ""} { read_liberty $l } }
read_def $::env(DEF)
set blk [ord::get_db_block]
puts "OT_ORIENT [join [lsort -unique [lmap i [$blk getInsts] {$i getOrient}]] ,]"
if {[catch {check_placement -verbose} e]} { puts "OT_CHECK_PLACEMENT FAIL $e" } else { puts "OT_CHECK_PLACEMENT PASS" }
read_sdc $::env(SDC)
if {$::env(PAR) eq "rcx"} {
  define_process_corner -ext_model_index 0 X
  extract_parasitics -ext_model_file $PLAT/rcx_patterns.rules
  write_spef $::env(TAG).spef
  read_spef $::env(TAG).spef
} else { read_spef $::env(PAR) }
set_propagated_clock [all_clocks]
foreach c [all_clocks] { if {[llength [get_property $c sources]]} { set_clock_latency -source 0 $c } }
set f [open $::env(TAG).ck w]
foreach p [all_registers -clock_pins] {
  puts $f "[get_full_name $p] [get_property $p arrival_max_rise] [get_property $p arrival_min_rise]"
}
foreach inst [$blk getInsts] {
  if {![[$inst getMaster] isBlock]} continue
  foreach it [$inst getITerms] {
    if {[$it isClocked] == 0 && [[$it getMTerm] getSigType] ne "CLOCK"} continue
    set pn [get_pins -quiet "[$inst getName]/[[$it getMTerm] getName]"]
    if {[llength $pn]} { puts $f "[get_full_name $pn] [get_property $pn arrival_max_rise] [get_property $pn arrival_min_rise] MACRO" }
  }
}
close $f
puts "OT_WS max [sta::worst_slack_cmd max] min [sta::worst_slack_cmd min]"
report_clock_skew -setup
