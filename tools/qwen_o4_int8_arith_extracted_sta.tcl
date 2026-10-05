# Extracted route timing, with propagated clock, for the diagnostic block.
set platform /home/ubuntu/.local/opentallas-pdk-asap7-platform/asap7
foreach lib [glob $platform/lib/NLDM/*RVT_TT_nldm*] {
    if {[string match *FAKE* $lib]} { continue }
    read_liberty $lib
}
read_db /tmp/qwen-o4-int8-arith-final.odb
read_sdc /tmp/qwen-o4-int8-arith-sta/constraint.sdc
read_spef /tmp/qwen-o4-int8-arith-final.spef
set_propagated_clock [all_clocks]
puts "EXTRACTED_SETUP"
report_checks -path_delay max
report_wns
puts "EXTRACTED_HOLD"
report_checks -path_delay min
report_check_types -max_slew -max_capacitance -max_fanout -violators
