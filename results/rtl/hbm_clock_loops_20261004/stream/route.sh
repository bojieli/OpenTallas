#!/bin/bash
# SS route of one channel slice (2 PCs + TDM row slot) of the stream controller; the 52ce3e9c1 REPLAY recipe.
# Usage: route.sh <tag> <period_ns>
R=/srv/opentallas-scratch/claude/hbm-clock-loops/stream
tag=$1; per=$2
cd $R/src
export OT_ORFS_NUM_CORES=16 OT_PHYSICAL_WORK_ROOT=$R/work
mkdir -p $R/routes/$tag
/srv/opentallas-scratch/admit.sh 16 -- python3 tools/run_abi3_physical.py --view asap7 --top ot_hbm_r14_stream_stack \
  --source rtl/model_ready_hbm_r14/ot_hbm_r14_stream_pc.sv --source rtl/model_ready_hbm_r14/ot_hbm_r14_stream_stack.sv \
  --param ENABLE=1 --param REF_MODE=1 --param NCH=1 --clock-period-ns $per --clock-uncertainty-ns 0.06 \
  --clock-uncertainty-hold-ns 0.025 --orfs-corner WC --hold-corners WC,BC --io-delay-fraction 0 --false-path-from rst_n \
  --slew-margin-percent 40 --max-transition-ns 0.32 --purpose characterization --core-utilization 40 \
  --place-density 0.6 --orfs-var ADDER_MAP_FILE= --stages pnr --nickname-tag $tag \
  --keep-workdir $R/routes/$tag/work --output $R/routes/$tag/physical.json > $R/routes/$tag/route.log 2>&1
echo "rc=$?" > $R/routes/$tag/exit
