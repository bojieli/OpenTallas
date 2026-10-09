#!/bin/bash
# struct-close 2026-10-09 ("-cl" line): closure-loop route of the UNGUARDED retry pipeline (ot_hbm_link_retry_pipeline_cl.sv,
# W 545, replay 512 x 16 SRAM macros) on the current flow: the loop exports OT_ORFS_CORNER_OVERRIDE=TC (WC names read TT),
# OT_MM_FF_SDC / OT_CTS_FIX_HOOKS; outline / macro placement as the Codex pathfinding (690 x 460, macro_place.tcl).
#   route_cl.sh <label> [extra run_abi3_physical args]   env: OUT, CORES (16), UTIL (55), PD (0.55), HM (0.010), DW/DH (690/460)
set -u
lab=$1; shift
W=${OUT:?}/$lab; mkdir -p $W
C=${CORES:-16}; DW=${DW:-690}; DH=${DH:-460}
export OT_ORFS_NUM_CORES=$C NUM_CORES=$C OT_SYNTH_TIMEOUT_SECONDS=unlimited OT_FLOW_TIMEOUT_SECONDS=unlimited
# r3: IO referenced to the block's measured clock like every HBM view (route_mtp.sh): io_vclk_m_<L>.sdc (L = the
# calibrated CK_SS_MEAN), sign-off post-SDCs signoff_unc60 + vclk_corner_true.  r1/r2 had no virtual clock: outputs were
# judged against an ideal clock while the launch flops carried ~973 ps of CTS insertion (the -481 / -513 "reg->out").
L=${L:-${CK_SS_MEAN:-770}}
bash physical/hbm_accel_die_views/common/make_io_vclk_margin.sh $L > /dev/null
SDCA=physical/hbm_accel_die_views/common/io_vclk_m_$L.sdc
echo "UTIL=${UTIL:-55} PD=${PD:-0.55} HM=${HM:-0.010} DW=$DW DH=$DH VT=${OT_MULTI_VT:-rvt} $*" > $W/args
cat SOURCE_COMMIT > $W/SOURCE_COMMIT 2>/dev/null
python3 tools/run_abi3_physical_aligned_guarded.py --macro-track-gate --view asap7 --top ot_hbm_link_retry_pipeline \
 --param ENABLE=1 --param W=545 --param EW=24 --param DEPTH=512 \
 --source rtl/common/ot_secded.sv --source rtl/hbm_accel/tu/link_retry_sram_20261008/ot_hbm_replay_sram.sv \
 --source rtl/hbm_accel/tu/link_retry_pipeline_20261009/ot_hbm_link_retry_pipeline_cl.sv \
 --macro-view ot_sram_1r1w_128x256_m1_r2c2=physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2 \
 --macro-place-halo 4 4 --orfs-var MACRO_PLACEMENT_TCL=/src/physical/hbm_link_retry_pipeline_20261009/macro_place.tcl \
 --clock-period-ns .833333333 --clock-uncertainty-ns .06 --clock-uncertainty-hold-ns .025 \
 --orfs-corner WC --hold-corners WC,BC --io-delay-fraction .2 --sdc-append $SDCA \
 --die-area 0 0 $DW $DH --core-area 5.4 5.4 $(python3 -c "print($DW-5.4, $DH-5.4)") \
 --stages ${STAGES:-pnr} --core-utilization ${UTIL:-55} --place-density ${PD:-0.55} \
 --hold-margin-ns ${HM:-0.010} --orfs-var ADDER_MAP_FILE= --slew-margin-percent 30 \
 --synth-timeout-seconds unlimited --flow-timeout-seconds unlimited \
 --purpose signoff_target --nickname-tag hbm_retry_cl_$(echo $lab | tr -c "A-Za-z0-9_\n" _) \
 --keep-workdir $W/work --force --output $W/physical.json "$@" > $W/run.log 2>&1
rc=$?; echo "rc=$rc" > $W/exit
case " $* " in *"stop-after"*) exit $rc ;; esac
python3 tools/w18/corner_sta.py --post-sdc physical/hbm_accel_die_views/common/signoff_unc60.sdc --post-sdc physical/hbm_accel_die_views/common/vclk_corner_true.sdc --orfs-dir $W/work/orfs --output $W/corner_sta.json > $W/corner.log 2>&1
echo "corner_rc=$?" >> $W/exit
exit $rc
