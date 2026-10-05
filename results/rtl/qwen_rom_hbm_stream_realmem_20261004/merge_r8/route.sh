#!/bin/bash
# SS/FF route of one channel slice of the merged (r8 + WR_EN) stream controller, WR_EN=1 WQ=4.
# Usage: route.sh <tag> <period_ns> [WR_EN]
R=/srv/opentallas-scratch/claude/hbmstream-realmem
tag=$1; per=$2; wr=${3:-1}
cd $R/src_merge
export OT_ORFS_NUM_CORES=16 OT_PHYSICAL_WORK_ROOT=$R/phys_work
mkdir -p $R/routes/$tag
echo "$(date -u +%FT%TZ) START route $tag $per WR_EN=$wr src=$(cat SOURCE_SHA)" >> $R/jobs/MANIFEST
/srv/opentallas-scratch/admit.sh 16 -- python3 tools/run_abi3_physical.py --view asap7 --top ot_hbm_r14_stream_stack \
  --source rtl/model_ready_hbm_r14/ot_hbm_r14_stream_pc.sv --source rtl/model_ready_hbm_r14/ot_hbm_r14_stream_stack.sv \
  --param ENABLE=1 --param REF_MODE=1 --param NCH=1 --param WR_EN=$wr --param WQ=4 --clock-period-ns $per --clock-uncertainty-ns 0.06 \
  --clock-uncertainty-hold-ns 0.025 --orfs-corner WC --hold-corners WC,BC --io-delay-fraction 0 --false-path-from rst_n \
  --slew-margin-percent 40 --max-transition-ns 0.32 --purpose characterization --core-utilization 40 \
  --place-density 0.6 --orfs-var ADDER_MAP_FILE= --stages pnr --nickname-tag $tag \
  --keep-workdir $R/routes/$tag/work --output $R/routes/$tag/physical.json > $R/routes/$tag/route.log 2>&1
rc=$?; echo "rc=$rc" > $R/routes/$tag/exit
echo "$(date -u +%FT%TZ) END route $tag exit=$rc" >> $R/jobs/MANIFEST
