#!/bin/bash
# run_route.sh <label> [extra run_abi3_physical args]   (cwd = pinned source snapshot SRC; env OUT = run base)
# env: IOSDC (route IO SDC; generated with default insertion if absent), PD (place density), CORES, NEED (GB),
#      DIEW/DIEH (um), PER (route period ns, default 0.770)
set -u
# SYNTH_HIER=1: ORFS hierarchical synthesis (SYNTH_HIERARCHICAL=1; KEEP=<nand2-eq> min kept module size, platform
#   default 1000): each unique arithmetic module is synthesised ONCE instead of 64 flattened lane copies.  Flat MEM1
#   synthesis sat 10.5 h in yosys opt_dff re-run loops (225+ passes, one delay-line stage pruned per pass).
lab=$1; shift
W=$OUT/$lab; mkdir -p $W; cd ${SRC:-.}
V=physical/hbm_norm_engine_view_mem1_20261007
MAC=ot_sram_1r1w_128x256_m1_r2c2
SDC=${IOSDC:-$OUT/io.sdc}
[ -f $SDC ] || python3 $V/make_sdc.py --out $SDC > /dev/null
export OT_ORFS_NUM_CORES=${CORES:-16} NUM_CORES=${CORES:-16} OT_SYNTH_TIMEOUT_SECONDS=unlimited OT_FLOW_TIMEOUT_SECONDS=unlimited
DW=${DIEW:-1100}; DH=${DIEH:-1100}
srcargs=""; for s in $(cat $V/sources.f); do srcargs="$srcargs --source $s"; done
echo "label=$lab sdc=$SDC die=${DW}x${DH} pd=${PD:-0.45} $*" > $W/args
/srv/opentallas-scratch/admit.sh ${NEED:-80} -- python3 tools/run_abi3_physical.py --view asap7 --top ot_hbm_norm_engine_view $srcargs \
  --clock-port clk --clock-period-ns ${PER:-0.770} --clock-uncertainty-ns 0.06 --clock-uncertainty-hold-ns 0.05 \
  --orfs-corner WC --hold-corners WC,BC --hold-margin-ns 0.01 --sdc-append $SDC --stages pnr --macro-view $MAC=physical/asap7_memory_macros_v2/$MAC --macro-place-halo 4 4 \
  --die-area 0 0 $((DW+4)) $((DH+4)) --core-area 2 2 $((DW+2)) $((DH+2)) --place-density ${PD:-0.45} \
  --orfs-var NUM_CORES=${CORES:-16} $( [ "${SYNTH_HIER:-0}" = 1 ] && echo "--orfs-var SYNTH_HIERARCHICAL=1 --orfs-var SYNTH_MINIMUM_KEEP_SIZE=${KEEP:-1000}" ) --orfs-var ADDER_MAP_FILE= --orfs-var PLACE_DENSITY_LB_ADDON= \
  --orfs-var "PLACE_PINS_ARGS=-min_distance 1 -min_distance_in_tracks" --orfs-var "IO_PLACER_H=M4 M6" --orfs-var "IO_PLACER_V=M5 M7" \
  --slew-margin-percent 60 --purpose signoff_target --nickname-tag nev_$lab --keep-workdir $W/work --force \
  --synth-timeout-seconds unlimited --flow-timeout-seconds unlimited "$@" --output $W/physical.json > $W/run.log 2>&1
echo "rc=$?" > $W/exit
