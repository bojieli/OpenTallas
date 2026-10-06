#!/bin/bash
# stn_ckff.sh <route dir>: min FF ck network latency (ps) of the routed view (vclk hold latency, stn_margin_sdc.py)
d=$1; B=$(ls -d $PWD/$d/work/orfs/results/asap7/*/base 2>/dev/null) || exit 1
if [ -f $B/6_final.odb ]; then db=6_final.odb; sdc=6_final.sdc; sp="read_spef /w/6_final.spef"; elif [ -f $B/4_1_cts.odb ]; then db=4_1_cts.odb; sdc=$(ls $B | grep -m1 "4_cts.sdc\|3_place.sdc"); sp="estimate_parasitics -placement"; else exit 1; fi
cat > $B/ckins.tcl <<TCL
foreach l [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*RVT_FF*] { read_liberty \$l }
read_db /w/$db
read_sdc /w/$sdc
source /OpenROAD-flow-scripts/flow/platforms/asap7/setRC.tcl
$sp
set_propagated_clock [all_clocks]
set mx 1e9
foreach p [get_pins -hierarchical */CLK] { set c [get_property \$p clocks]; if {[lsearch [get_full_name \$c] ck] < 0} continue; set a [get_property \$p arrival_min_rise]; if {\$a ne "" && \$a ne "INF" && \$a < \$mx} { set mx \$a } }
puts "CKFF [expr {round(\$mx)}] $db"
exit
TCL
docker run --rm -v $B:/w openroad/orfs:asap7lock bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -exit /w/ckins.tcl" 2>&1 | grep CKFF
