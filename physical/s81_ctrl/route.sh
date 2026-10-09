#!/bin/bash
# route.sh <label> <top: dsfd_sp_ctrl | dsfd_sp_ctrl_src | dsfd_sp_ctrl_h> (stream ds-control 2026-10-08): block route of
# the S81 die control-plane master TT pathfinding at nominal0.833 streamingperiod / FF hold, reference20%IO
# until the die generator gives the slab its link budget).  env: SRC (pinned snapshot with SOURCE_COMMIT), OUT, UTIL (45),
# PD (0.55), HM (0.025), CORES (12), NEED (GB, 48), PER (0.833), EXTRA.  Loop convention: OT_ORFS_CORNER_OVERRIDE=TC.
set -u
lab=$1; top=$2; shift 2
W=$OUT/$lab; mkdir -p $W; cd $SRC
cat SOURCE_COMMIT > $W/SOURCE_COMMIT 2>/dev/null
export OT_ORFS_NUM_CORES=${CORES:-12} NUM_CORES=${CORES:-12} OT_SYNTH_TIMEOUT_SECONDS=unlimited OT_FLOW_TIMEOUT_SECONDS=unlimited
S=rtl/dsrom_sys/s81_ctrl
SRCS="rtl/lib/ot_skid_buffer.sv rtl/dsrom_sys/ot_dsrom_stall_export.sv $S/ot_s81_stage_seq.sv $S/ot_s81_pkg_ctrl.sv $S/ot_s81_stage_guard.sv
 $S/ot_s81_hop_tx.sv $S/ot_s81_stop.sv $S/ot_s81_host_cq.sv $S/ot_s81_ctrl.sv physical/s81_ctrl/rtl/dsfd_sp_ctrl_core.sv"
srcargs="--source physical/s81_ctrl/rtl/$top.sv"; for s in $SRCS; do srcargs="$srcargs --source $s"; done
ADMIT=$(ls /srv/opentallas-scratch/admit.sh 2>/dev/null); ADMIT=${ADMIT:+$ADMIT ${NEED:-48} --}
$ADMIT python3 tools/run_abi3_physical.py --view asap7 --top $top $srcargs \
  --clock-port ck --clock-period-ns ${PER:-0.833} --clock-uncertainty-ns 0.06 --clock-uncertainty-hold-ns 0.025 \
  --orfs-corner TC --hold-corners TC,BC --io-delay-fraction 0.2 --stages synth,pnr \
  --core-utilization ${UTIL:-45} --place-density ${PD:-0.55} --routing-layers M2 ${MAXL:-M7} \
  --orfs-var ADDER_MAP_FILE= --orfs-var "CTS_ARGS=-sink_clustering_enable -repair_clock_nets -apply_ndr none" \
  --slew-margin-percent 60 --hold-margin-ns ${HM:-0.025} --purpose characterization --nickname-tag s81ctrl_$lab \
  --synth-timeout-seconds unlimited --flow-timeout-seconds unlimited ${EXTRA:-} "$@" \
  --keep-workdir $W/work --force --output $W/physical.json > $W/run.log 2>&1
echo "rc=$?" > $W/exit
python3 tools/w18/corner_sta.py --orfs-dir $W/work/orfs --output $W/corner_sta.json > $W/corner.log 2>&1
echo "corner_rc=$?" >> $W/exit
