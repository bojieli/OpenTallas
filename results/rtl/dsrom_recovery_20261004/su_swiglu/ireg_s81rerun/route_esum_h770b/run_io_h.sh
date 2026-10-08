#!/bin/bash
# CLAUDE S81-RERUN: die-context SS / FF sign-off of a routed swiglu lane at its OWN measured insertion
# (inside openroad/orfs: /work = the ORFS dir).  usage: run_io_h.sh
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
L=/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM
D=$(ls -d /work/results/asap7/*/base); mkdir -p /work/sta833
for C in SS FF; do
cat > /work/sta833/lat_$C.tcl <<T
foreach l [glob $L/asap7sc7p5t_{AO,INVBUF,OA,SEQ,SIMPLE}_RVT_${C}_nldm_*.lib*] { read_liberty \$l }
read_db $D/6_final.odb
read_spef $D/6_final.spef
create_clock -name core_clk -period 833.333 [get_ports {clk}]
set_propagated_clock [get_clocks core_clk]
report_clock_latency -clock core_clk
T
openroad -exit -no_init -threads 4 /work/sta833/lat_$C.tcl > /work/sta833/lat_$C.log 2>&1
read LO HI < <(grep -A30 "rise -> rise" /work/sta833/lat_$C.log | grep -Eo "^ *[0-9.]+ +[0-9.]+ +latency" | head -1 | awk '{print $1, $2}')
[ -z "$LO" ] && read LO HI < <(grep -Eo "[0-9]+\.[0-9]+ +[0-9]+\.[0-9]+ +latency" /work/sta833/lat_$C.log | head -1 | awk '{print $1, $2}')
if [ $C = SS ]; then LI=$HI; LOUT=$LO; else LI=$LO; LOUT=$HI; fi
echo "$C insertion $LO .. $HI -> io_in $LI io_out $LOUT"
cat > /work/sta833/die_$C.sdc <<S
create_clock -name core_clk -period 833.333 [get_ports {clk}]
set_clock_uncertainty -setup 60.0 core_clk
set_clock_uncertainty -hold 25.0 core_clk
set_propagated_clock [get_clocks core_clk]
create_clock -name io_in -period 833.333
create_clock -name io_out -period 833.333
set_clock_latency $LI [get_clocks io_in]
set_clock_latency $LOUT [get_clocks io_out]
set_clock_uncertainty -setup 60.0 [get_clocks {io_in io_out}]
set_clock_uncertainty -hold 25.0 [get_clocks {io_in io_out}]
set ins [get_ports {v g[*] u[*] w[*] lim[*]}]
set outs [all_outputs]
set_input_delay -max 200.0 -clock io_in \$ins
set_input_delay -min -50.0 -clock io_in \$ins
set_output_delay -max 200.0 -clock io_out \$outs
set_output_delay -min -50.0 -clock io_out \$outs
S
cat > /work/sta833/io_$C.tcl <<T
foreach l [glob $L/asap7sc7p5t_{AO,INVBUF,OA,SEQ,SIMPLE}_RVT_${C}_nldm_*.lib*] { read_liberty \$l }
read_db $D/6_final.odb
read_spef $D/6_final.spef
read_sdc /work/sta833/die_$C.sdc
report_worst_slack -max
report_worst_slack -min
report_tns
report_checks -path_delay min -endpoint_path_count 1 -format end -slack_max 15 -group_path_count 20
T
openroad -exit -no_init -threads 4 /work/sta833/io_$C.tcl > /work/sta833/io_$C.log 2>&1
grep -E "worst slack|tns" /work/sta833/io_$C.log | sed "s/^/$C /"
done
