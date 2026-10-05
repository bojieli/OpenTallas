#!/bin/bash
# ORFS route (SS setup WC + 60 ps, hold WC,BC + 25 ps), then corner STA. Usage: route.sh <label> <period> <top> <args...>
R=/srv/opentallas-scratch/claude/hbm-clock-loops
lab=$1; P=$2; top=$3; shift 3
W=$R/routes/$lab; mkdir -p $W
cd $R/src
export OT_ORFS_NUM_CORES=16
/srv/opentallas-scratch/admit.sh ${NEED:-16} -- python3 tools/run_abi3_physical.py --view asap7 --top $top "$@" \
  --clock-period-ns $P --clock-uncertainty-ns 0.06 --clock-uncertainty-hold-ns 0.025 \
  --orfs-corner WC --hold-corners WC,BC --io-delay-fraction 0.2 --stages synth,pnr \
  --core-utilization ${UTIL:-30} --place-density 0.5 --hold-margin-ns 0.01 --orfs-var ADDER_MAP_FILE= \
  --slew-margin-percent 30 --purpose signoff_target --nickname-tag hcl_$lab \
  --keep-workdir $W/work --force --output $W/physical.json > $W/run.log 2>&1
echo "rc=$?" > $W/exit
python3 tools/w18/corner_sta.py --orfs-dir $W/work/orfs --output $W/corner_sta.json > $W/corner.log 2>&1
echo "corner_rc=$?" >> $W/exit
