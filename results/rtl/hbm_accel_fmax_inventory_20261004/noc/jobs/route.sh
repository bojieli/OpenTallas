#!/bin/bash
# noc-family sign-off route at 1.2 GHz: SS setup WC + 60 ps, hold WC,BC + 25 ps, ADDER_MAP off; then corner STA.
# Usage: route.sh <label> <top> "<--source ... --param ... [--false-path-io] [--blackbox ..]>"
#   env: SRC (src dir under R, default src), UTIL (30), PD (0.55), NEED (GB, 24), CORES (16), IOF (0.2), MACRO (dir for corner_sta)
R=/srv/opentallas-scratch/claude/hbm-fmax-noc
lab=$1; top=$2; args=$3
W=$R/routes/$lab; mkdir -p $W
cd $R/${SRC:-src}
export OT_ORFS_NUM_CORES=${CORES:-16}
/srv/opentallas-scratch/admit.sh ${NEED:-24} -- python3 tools/run_abi3_physical.py --view asap7 --top $top $args \
  --clock-period-ns 0.833 --clock-uncertainty-ns 0.06 --clock-uncertainty-hold-ns 0.025 \
  --orfs-corner WC --hold-corners WC,BC --io-delay-fraction ${IOF:-0.2} --stages synth,pnr \
  --core-utilization ${UTIL:-30} --place-density ${PD:-0.55} --hold-margin-ns 0.01 --orfs-var ADDER_MAP_FILE= \
  --slew-margin-percent 30 --purpose signoff_target --nickname-tag noc_$lab \
  --keep-workdir $W/work --force --output $W/physical.json > $W/run.log 2>&1
echo "rc=$?" > $W/exit
python3 tools/w18/corner_sta.py --orfs-dir $W/work/orfs ${MACRO:+--macro $MACRO} --output $W/corner_sta.json > $W/corner.log 2>&1
echo "corner_rc=$?" >> $W/exit
