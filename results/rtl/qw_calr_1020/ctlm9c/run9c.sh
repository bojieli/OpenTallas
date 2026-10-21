#!/bin/bash
set -uo pipefail
R=/srv/opentallas-scratch/claude/qw-calr9-1020
cd $R/src && tar xf ../calr_port.tar && export PATH=/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin:$PATH
rm -f $R/calr_port.log
for m in 0 34 2; do bash rtl/test/qwen_dv/calr_port/run_calr_port.sh $R/calr_port_m$m $m > $R/calr_port_m$m.log 2>&1; echo "CALR_PORT_M$m rc=$?" >> $R/calr_port.log; tail -3 $R/calr_port_m$m.log >> $R/calr_port.log; done
cd $R/src && bash bench9.sh > $R/bench9.log 2>&1; echo "BENCH_RC $?" >> $R/bench9.log
echo RUN9C_DONE
