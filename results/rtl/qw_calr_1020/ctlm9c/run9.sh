#!/bin/bash
set -uo pipefail
R=/srv/opentallas-scratch/claude/qw-calr9-1020
docker run --rm -u $(id -u):$(id -g) -v $R:/work -w /work/src openroad/orfs:latest bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; bash chain9.sh' > $R/chain9.log 2>&1; echo "CHAIN_RC $?" >> $R/chain9.log
docker run --rm -u $(id -u):$(id -g) -v $R:/work -w /work/src openroad/orfs:latest bash -lc 'bash depth7.sh' > $R/depth9.log 2>&1; echo "DEPTH_RC $?" >> $R/depth9.log
cd $R/src && bash bench9.sh > $R/bench9.log 2>&1; echo "BENCH_RC $?" >> $R/bench9.log
# unit regression: CALR port bench (ported calendar == F16 reference, both on the depth-fixed qfd_dv_calendar_rom)
cd $R/src && tar xf ../calr_port.tar && export PATH=/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin:$PATH
for m in 0 34 2; do bash rtl/test/qwen_dv/calr_port/run_calr_port.sh $R/calr_port_m$m $m > $R/calr_port_m$m.log 2>&1; echo "CALR_PORT_M$m rc=$?" >> $R/calr_port.log; tail -3 $R/calr_port_m$m.log >> $R/calr_port.log; done
echo RUN9_DONE
