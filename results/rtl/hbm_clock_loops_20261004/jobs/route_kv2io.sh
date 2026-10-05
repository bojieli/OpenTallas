#!/bin/bash
# KV lifecycle ORFS route from src_kv2 at 1.2 GHz (SS setup WC + 60 ps, hold WC,BC + 25 ps)
# with the interface constrained (no false paths; input/output delay = IOF x period, default 0), then corner STA.
# Usage: route_kv2.sh <label> <source.sv>   env: UTIL (default 30), PD (0.5), CORES (20), NEED (GB, 48)
R=/srv/opentallas-scratch/claude/hbm-clock-loops
lab=$1; src=$2
W=$R/routes/$lab; mkdir -p $W
cd $R/src_kv2
export OT_ORFS_NUM_CORES=${CORES:-20}
/srv/opentallas-scratch/admit.sh ${NEED:-48} -- python3 tools/run_abi3_physical.py --view asap7 --top ot_hbm_accel_kv_lifecycle --source $src --param ENABLE=1 \
  --clock-period-ns 0.833 --clock-uncertainty-ns 0.06 --clock-uncertainty-hold-ns 0.025 \
  --orfs-corner WC --hold-corners WC,BC --io-delay-fraction ${IOF:-0} --stages synth,pnr \
  --core-utilization ${UTIL:-30} --place-density ${PD:-0.5} --hold-margin-ns 0.01 --orfs-var ADDER_MAP_FILE= \
  --slew-margin-percent 30 --purpose signoff_target --nickname-tag hcl_$lab \
  --keep-workdir $W/work --force --output $W/physical.json > $W/run.log 2>&1
echo "rc=$?" > $W/exit
python3 tools/w18/corner_sta.py --orfs-dir $W/work/orfs --output $W/corner_sta.json > $W/corner.log 2>&1
echo "corner_rc=$?" >> $W/exit
