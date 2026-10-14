set ::env(OT_GATE_SIGNOFF_SDC) /src/physical/ref_tile/qfd_coll_xfifo_native/signoff.sdc
source /src/tools/ref_tile/path_classes.tcl
puts "NATIVE_AUDIT_CLOCKS"
report_clock_properties [all_clocks]
report_units
foreach port {ck ckd} {
 puts "NATIVE_AUDIT_SOURCE $port"
 report_arrival -digits 6 [get_ports $port]
 report_slews -digits 6 [get_ports $port]
}
set block [ord::get_db_block]
set n [$block findNet ckd]
set count 0;set flops 0;set buffers 0;set macros 0;set other 0
foreach it [$n getITerms] {
 if {![$it isInputSignal]} continue
 incr count
 set i [$it getInst];set name [[$i getMaster] getName]
 if {[string match DFF* $name]} {incr flops} elseif {[string match BUF* $name] || [string match INV* $name]} {incr buffers} elseif {[[$i getMaster] isBlock]} {incr macros;puts "NATIVE_AUDIT_MACRO [$i getName]/[[$it getMTerm] getName]"} else {incr other}
}
puts "NATIVE_AUDIT_CKD_NET name=[$n getName] direct_sinks=$count flops=$flops buffers=$buffers macros=$macros other=$other BTerms=[llength [$n getBTerms]]"
foreach pat {{*u_cq*g_ipr*pd*CLK} {*u_sq*g_ipr*pd*CLK}} {
 set pin [lindex [get_pins -hier -quiet $pat] 0]
 if {$pin eq ""} {error "missing physical reference probe"}
 puts "NATIVE_AUDIT_REF [get_full_name $pin]"
 report_arrival -digits 6 $pin
 report_slews -digits 6 $pin
}
puts "NATIVE_AUDIT_SETUP_PATHS"
report_checks -path_delay max -format full_clock_expanded -fields {slew cap input fanout} -digits 6 -group_path_count 2
puts "NATIVE_AUDIT_HOLD_PATHS"
report_checks -path_delay min -format full_clock_expanded -fields {slew cap input fanout} -digits 6 -group_path_count 1
write_sdc /out/executed_audit.sdc
puts "NATIVE_AUDIT_PASS actual unmodified constraints/source150"
exit
