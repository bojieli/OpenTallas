set C $::env(CORNER)
set P /OpenROAD-flow-scripts/flow/platforms/asap7
foreach l [glob $P/lib/NLDM/*RVT_${C}*] {read_liberty $l}
if {[info exists ::env(SRAM)] && $::env(SRAM) eq "1"} {
 set lower [string tolower $C]
 read_liberty /src/physical/asap7_memory_macros/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2_${lower}.lib
}
read_db /base/6_final.odb
read_sdc /base/6_final.sdc
read_spef /base/6_final.spef
read_sdc /src/physical/s81_engc_tiles/rso_closure/child_mean.sdc
puts "IO18_REPLAY $C regs=[llength [all_registers -clock_pins]] boundary=[dict get $ot_ir_ins core_clk]"
report_worst_slack -max
report_worst_slack -min
report_checks -from [get_ports rst] -path_delay max -format full_clock_expanded -digits 6 -group_path_count 4
report_checks -from [get_ports rst] -path_delay min -format full_clock_expanded -digits 6 -group_path_count 4
write_sdc /tmp/replay.sdc
set f [open /tmp/replay.sdc r]
foreach line [split [read $f] "\n"] {
 if {[regexp {^(create_clock|set_clock_latency|set_input_transition)} $line]} {puts "SOURCE_CONTEXT $line"}
}
close $f
puts "IO18_DONE $C"
