#!/bin/bash
# CLAUDE HBM-ABSTRACTS (hub): re-harden a CLOSED hub lane element (unchanged RTL) in a die-dense footprint with every
# pin on the left edge (mirrored columns in the quarter face a shared channel), signals M2-M7 (M8/M9 left to the
# quarter / die PDN), SS60/FF25 at 0.833 ns, IO false-pathed (register-direct, checked after the route), corner STA.
#   route_lane.sh <label> <top> <W> <H> [run_abi3_physical args]   env: R (scratch base with src0), SRCS, KEEP, CORES, NEED
R=${R:?}; lab=$1; top=$2; W_=$3; H_=$4; shift 4
W=$R/routes/$lab; mkdir -p $W; cd $R/src0
export OT_ORFS_NUM_CORES=${CORES:-8} NUM_CORES=${CORES:-8} OT_SYNTH_TIMEOUT_SECONDS=unlimited OT_FLOW_TIMEOUT_SECONDS=unlimited
echo "$top $W_ $H_ $SRCS $*" > $W/args; cat SOURCE_COMMIT > $W/SOURCE_COMMIT
S=""; for s in $SRCS; do S="$S --source $s"; done
/srv/opentallas-scratch/admit.sh ${NEED:-12} -- python3 tools/run_abi3_physical.py --view asap7 --top $top $S "$@" \
  --clock-period-ns 0.833 --clock-uncertainty-ns 0.06 --clock-uncertainty-hold-ns 0.025 \
  --orfs-corner WC --hold-corners WC,BC --io-delay-fraction 0.2 --false-path-io --stages pnr \
  --die-area 0 0 $W_ $H_ --core-area 0 0.54 $W_ $(python3 -c "print(round($H_-0.54,3))") --pin-region ".*=left" --routing-layers M2 M7 \
  --place-density ${PD:-0.65} --hold-margin-ns ${HM:-0.01} --orfs-var ADDER_MAP_FILE= \
  --slew-margin-percent 30 --purpose signoff_target --nickname-tag hub_$lab \
  ${KEEP:+--orfs-var "SYNTH_KEEP_MODULES=$KEEP"} \
  --step-tcl PRE_CTS=physical/abi3/v41x_karb_repair_buffer_cap.tcl --step-tcl PRE_GLOBAL_ROUTE=physical/abi3/v41x_karb_repair_buffer_cap.tcl \
  --synth-timeout-seconds unlimited --flow-timeout-seconds unlimited \
  --keep-workdir $W/work --force --output $W/physical.json > $W/run.log 2>&1
echo "rc=$?" > $W/exit
python3 tools/w18/corner_sta.py --orfs-dir $W/work/orfs --output $W/corner_sta.json > $W/corner.log 2>&1
echo "corner_rc=$?" >> $W/exit
python3 $R/outcheck.py $W/work/orfs > $W/outcheck.txt 2>&1
echo "post_rc=$?" >> $W/exit
