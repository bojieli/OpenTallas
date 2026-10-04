#!/bin/bash
# Top violating reg-to-reg endpoints of an ORFS stage odb (SS libs, placement parasitics). Usage: kv_odb_top.sh <orfs dir> <stage e.g. 4_cts> [N]
O=$1; st=$2; N=${3:-300}
B=$(ls -d $O/results/asap7/*/base)
cat > $B/q_$st.tcl <<TCL
foreach l [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*RVT_SS*] { read_liberty \$l }
read_db /b/$st.odb
read_sdc /b/$st.sdc
source /OpenROAD-flow-scripts/flow/platforms/asap7/setRC.tcl
estimate_parasitics -placement
report_checks -path_delay max -from [all_registers -clock_pins] -to [all_registers -data_pins] -group_path_count $N -endpoint_path_count 1 -format end
report_checks -path_delay max -from [all_registers -clock_pins] -to [all_registers -data_pins] -group_path_count 1 -fields {fanout slew cap} -digits 1
TCL
docker run --rm -v $B:/b openroad/orfs:latest bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -no_init -exit /b/q_$st.tcl" 2>&1 | grep -v "^\[WARNING\|^\[INFO"
