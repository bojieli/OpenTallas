#!/bin/bash
# Top violating reg-to-reg endpoints of an ORFS final odb + SPEF (SS libs), worst path detail. Usage: kv_final_top.sh <orfs dir> [N]
O=$1; N=${2:-100}
B=$(ls -d $O/results/asap7/*/base)
cat > $B/q_final.tcl <<TCL
foreach l [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*RVT_SS*] { read_liberty \$l }
read_db /b/6_final.odb
read_sdc /b/6_final.sdc
read_spef /b/6_final.spef
report_checks -path_delay max -from [all_registers -clock_pins] -to [all_registers -data_pins] -group_path_count $N -endpoint_path_count 1 -format end
report_checks -path_delay max -from [all_registers -clock_pins] -to [all_registers -data_pins] -group_path_count 3 -fields {fanout slew cap} -digits 1
TCL
docker run --rm -v $B:/b openroad/orfs:latest bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -no_init -exit /b/q_final.tcl" 2>&1 | grep -v "^\[WARNING\|^\[INFO\|DFFHQN.*_R$"
