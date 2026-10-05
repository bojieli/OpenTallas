#!/bin/bash
# ORFS route of the fence (SS setup WC + 60 ps, hold WC,BC + 25 ps, ADDER_MAP off), then corner STA.
# Source: the screen copy with the SECDED package functions inlined (logic identical to the RTL).
# Usage: route.sh <label> <param...>
R=/srv/opentallas-scratch/claude/hbm-fence-loop
lab=$1; shift
W=$R/routes/$lab; mkdir -p $W
cd $R/src
export OT_ORFS_NUM_CORES=16
P=""; for kv in "$@"; do P="$P --param $kv"; done
/srv/opentallas-scratch/admit.sh ${NEED:-16} -- python3 tools/run_abi3_physical.py --view asap7 --top ot_hbm_rf_visibility_fence_live \
  --source ${SRC:-results/rtl/hbm_clock_loops_20261004/fence/fence_live_screen.sv} $P \
  --clock-period-ns 0.833 --clock-uncertainty-ns 0.06 --clock-uncertainty-hold-ns 0.025 \
  --orfs-corner WC --hold-corners WC,BC --io-delay-fraction ${IOD:-0.2} --stages synth,pnr \
  --core-utilization ${UTIL:-30} --place-density 0.5 --hold-margin-ns 0.01 --orfs-var ADDER_MAP_FILE= ${ORFSV} \
  --slew-margin-percent 30 --purpose signoff_target --nickname-tag hcl_fence_$lab \
  --keep-workdir $W/work --force --output $W/physical.json > $W/run.log 2>&1
echo "rc=$?" > $W/exit
python3 tools/w18/corner_sta.py --orfs-dir $W/work/orfs --output $W/corner_sta.json > $W/corner.log 2>&1
echo "corner_rc=$?" >> $W/exit
