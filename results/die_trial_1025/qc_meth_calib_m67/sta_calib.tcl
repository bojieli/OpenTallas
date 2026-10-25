set L /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM
foreach f [glob $L/*RVT_$::env(CORNER)_nldm*.lib*] { read_liberty $f }
read_verilog /work/calib.v
link_design calib
read_spef /work/calib.spef
create_clock -name clk -period 833 [get_ports clk]
set_clock_uncertainty 60 -setup [all_clocks]
set_clock_uncertainty 25 -hold [all_clocks]
report_checks -path_delay max -format end
report_checks -path_delay max -group_path_count 1000 -endpoint_path_count 1 -format end > $::env(OUT).max
report_checks -path_delay min -group_path_count 1000 -endpoint_path_count 1 -format end > $::env(OUT).min
puts OT_DONE
