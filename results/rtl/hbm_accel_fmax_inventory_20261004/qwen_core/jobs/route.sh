#!/bin/bash
# qwen-core fmax family: ORFS route at 1.2 GHz (SS setup WC + 60 ps, hold WC,BC + 25 ps, ADDER_MAP off), then corner STA
# (tools/w18/corner_sta.py: SS setup / FF hold, the authority).  Runs on ot-epyc1tb from a pinned source snapshot.
# Usage: route.sh <sub> <label> <src_snapshot_dir> <run_abi3_physical args: --top T --source S ... --param P=V ...>
# env: UTIL (30) PD (0.5) CORES (20) NEED (GB, 32) FPIO=1 (--false-path-io) MACRO=<macro dir for corner_sta> STAGES (synth,pnr)
R=${QC_ROOT:-/srv/opentallas-scratch/claude/hbm-fmax-qcore}; ADMIT=${ADMIT:-/srv/opentallas-scratch/admit.sh}
sub=$1; lab=$2; src=$3; shift 3
W=$R/$sub/routes/$lab; mkdir -p $W; rm -f $W/exit
cd $R/$src || exit 2
export OT_ORFS_NUM_CORES=${CORES:-20}
$ADMIT ${NEED:-32} -- python3 tools/run_abi3_physical.py --view asap7 "$@" \
  --clock-period-ns 0.833 --clock-uncertainty-ns 0.06 --clock-uncertainty-hold-ns 0.025 \
  --orfs-corner WC --hold-corners WC,BC --io-delay-fraction 0.2 $([ "${FPIO:-0}" = 1 ] && echo --false-path-io) \
  --stages ${STAGES:-synth,pnr} --core-utilization ${UTIL:-30} --place-density ${PD:-0.5} --hold-margin-ns 0.01 \
  --orfs-var ADDER_MAP_FILE= --slew-margin-percent 30 --purpose signoff_target --nickname-tag qc_$lab \
  --keep-workdir $W/work --force --output $W/physical.json > $W/run.log 2>&1
echo "rc=$?" > $W/exit
python3 tools/w18/corner_sta.py --orfs-dir $W/work/orfs ${MACRO:+--macro $MACRO} --output $W/corner_sta.json > $W/corner.log 2>&1
echo "corner_rc=$?" >> $W/exit
