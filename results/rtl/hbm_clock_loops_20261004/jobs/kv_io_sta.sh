#!/bin/bash
# Informational: interface paths of a routed KV lifecycle (final odb + SPEF, SS) with 20% input/output delays
# instead of the sign-off false paths. Usage: kv_io_sta.sh <orfs dir>
O=$1; B=$(ls -d $O/results/asap7/*/base)
cat > $B/q_io.tcl <<'TCL'
foreach l [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*RVT_SS*] { read_liberty $l }
read_db /b/6_final.odb
read_spef /b/6_final.spef
create_clock -name core_clk -period 833 [get_ports clk]
set_clock_uncertainty -setup 60 core_clk
set_propagated_clock [get_clocks core_clk]
set ins [delete_from_list [all_inputs] [get_ports {clk por_n}]]
set_input_delay 166.6 -clock core_clk $ins
set_output_delay 166.6 -clock core_clk [all_outputs]
set_false_path -from [get_ports por_n]
puts "IN2REG"; report_checks -path_delay max -from $ins -to [all_registers -data_pins] -group_path_count 12 -endpoint_path_count 1 -format end
puts "REG2OUT"; report_checks -path_delay max -to [all_outputs] -group_path_count 12 -endpoint_path_count 1 -format end
TCL
docker run --rm -v $B:/b openroad/orfs:latest bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -no_init -exit /b/q_io.tcl" 2>&1 | grep -v "^\[WARNING\|^\[INFO\|DFFHQN.*_R$"
