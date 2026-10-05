# Continue the local direct-OpenROAD diagnostic from its routed global DB.
set platform /home/ubuntu/.local/opentallas-pdk-asap7-platform/asap7
foreach lib [glob $platform/lib/NLDM/*RVT_TT_nldm*] {
    if {[string match *FAKE* $lib]} { continue }
    read_liberty $lib
}
read_db /tmp/qwen-o4-int8-arith-grt.odb
# The local synthesis netlist leaves constants as one_/zero_ nets. This
# diagnostic routes them as ordinary nets; it is not a PDN/tie-cell signoff.
set block [ord::get_db_block]
foreach name {one_ zero_} {
    set net [$block findNet $name]
    if {$net ne "NULL"} { $net setSigType SIGNAL }
}
read_sdc /tmp/qwen-o4-int8-arith-sta/constraint.sdc
source $platform/setRC.tcl
detailed_route -output_drc /tmp/qwen-o4-int8-arith-drc.rpt
extract_parasitics -ext_model_file $platform/rcx_patterns.rules
puts "POST_DRT_SETUP"
report_checks -path_delay max
puts "POST_DRT_HOLD"
report_checks -path_delay min
report_wns
write_db /tmp/qwen-o4-int8-arith-final.odb
write_spef /tmp/qwen-o4-int8-arith-final.spef
