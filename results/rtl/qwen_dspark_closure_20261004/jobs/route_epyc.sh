#!/bin/bash
# Routed SS/FF authority (tools/run_abi3_physical.py at ORFS WC, hold WC,BC, ADDER_MAP_FILE off, 60/25 ps,
# then tools/w18/corner_sta.py SS setup / FF hold).  usage: route.sh SRC_DIR LABEL TOP PERIOD -- <--source/--param args>
R=/srv/opentallas-scratch/claude/qwen-dspark-closure
SRC=$1; L=$2; TOP=$3; P=$4; shift 5
export OT_ORFS_NUM_CORES=${OT_ORFS_NUM_CORES:-16}
W=$R/routes/$L; mkdir -p $W
cd $SRC
/srv/opentallas-scratch/admit.sh 24 -- python3 tools/run_abi3_physical.py --view asap7 --top $TOP "$@" \
  --clock-period-ns $P --clock-uncertainty-ns 0.06 --clock-uncertainty-hold-ns 0.025 \
  --orfs-corner WC --hold-corners WC,BC --io-delay-fraction 0.2 --stages synth,pnr \
  --core-utilization 30 --place-density 0.5 --hold-margin-ns 0.01 --orfs-var ADDER_MAP_FILE= \
  --slew-margin-percent 30 --purpose signoff_target --nickname-tag dsc_$L \
  --keep-workdir $W/work --force --output $W/physical.json > $W/run.log 2>&1
echo "rc=$?" > $W/exit
python3 tools/w18/corner_sta.py --orfs-dir $W/work/orfs --output $W/corner_sta.json > $W/corner.log 2>&1
echo "corner_rc=$?" >> $W/exit
