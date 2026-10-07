#!/bin/bash
# CLAUDE hbm-router: standalone route of ot_gpu_router_topk_ps (PIPESEL from env) under the owner margin-first rule:
# routed over-constrained (io_vclk_m_<L>.sdc: setup uncertainty 123 ps = 770 ps effective, IO 0.2 T + 150 ps against
# vclk at insertion L), signed off at 833.333/60 (SS setup) and 25 (FF hold) by corner_sta --post-sdc signoff_unc60.sdc.
#   route_block.sh <label> [extra run_abi3_physical args]
# env: SRC (pinned source snapshot with SOURCE_COMMIT), OUT (route base), PIPESEL (1), UTIL (35), PD (0.55), L (150),
#      CORES (12), NEED (GB, 16), HM (hold margin ns, 0.030), DIE ("W H" um: fixed outline instead of UTIL)
set -u
lab=$1; shift
W=$OUT/$lab; mkdir -p $W; cd $SRC
export OT_ORFS_NUM_CORES=${CORES:-12} NUM_CORES=${CORES:-12} OT_SYNTH_TIMEOUT_SECONDS=unlimited OT_FLOW_TIMEOUT_SECONDS=unlimited
P=physical/hbm_router_ps
echo "SRC=$SRC PIPESEL=${PIPESEL:-1} UTIL=${UTIL:-35} PD=${PD:-0.55} L=${L:-150} HM=${HM:-0.030} DIE=${DIE:-} $*" > $W/args
cat SOURCE_COMMIT > $W/SOURCE_COMMIT
area=""; if [ -n "${DIE:-}" ]; then set -- "$@"; read DW DH <<< "$DIE"; area="--die-area 0 0 $DW $DH --core-area 0 0.54 $DW $(python3 -c "print(round($DH-0.54,3))")"; fi
date > $W/start
/srv/opentallas-scratch/admit.sh ${NEED:-16} -- python3 tools/run_abi3_physical.py --view asap7 --top ot_gpu_router_topk_ps \
  --param PIPESEL=${PIPESEL:-1} --source rtl/gpu/ot_gpu_router_topk_ps.sv --source rtl/gpu/ot_gpu_router_topk.sv \
  --clock-period-ns 0.833 --clock-uncertainty-ns 0.06 --clock-uncertainty-hold-ns 0.025 \
  --orfs-corner WC --hold-corners WC,BC --io-delay-fraction 0.2 --sdc-append $P/io_vclk_m_${L:-150}.sdc --stages synth,pnr \
  ${area:---core-utilization ${UTIL:-35}} --place-density ${PD:-0.55} --orfs-var PLACE_DENSITY_LB_ADDON=0 --routing-layers M2 M7 \
  --orfs-var ADDER_MAP_FILE= --step-tcl PRE_CTS=physical/abi3/v41x_karb_repair_buffer_cap.tcl \
  --step-tcl PRE_GLOBAL_ROUTE=physical/abi3/v41x_karb_repair_buffer_cap.tcl --slew-margin-percent 30 \
  --hold-margin-ns ${HM:-0.030} --purpose signoff_target --nickname-tag rps_$lab \
  --synth-timeout-seconds unlimited --flow-timeout-seconds unlimited "$@" \
  --keep-workdir $W/work --force --output $W/physical.json > $W/run.log 2>&1
echo "rc=$?" > $W/exit
python3 tools/w18/corner_sta.py --post-sdc $P/signoff_unc60.sdc --orfs-dir $W/work/orfs --output $W/corner_sta.json > $W/corner.log 2>&1
echo "corner_rc=$?" >> $W/exit
date > $W/end
