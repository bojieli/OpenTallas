#!/bin/bash
# Hierarchical sign-off route of the DS HBM SM element ot_hbm_accel_sm_v ENABLE=1 (NC 8, RMAX 4096) at 0.833 ns:
# leaf macros (ot_hbm_accel_tc16, ot_hbm_accel_bd_col) as routed abstracts with SS/FF/TT timing models, x-store and
# staging-ring SRAM macros, manual macro grid (tools/hbm_accel_sm_v_floorplan.py), level-2 PDN (pdn_sm.tcl), M2-M9,
# die-budget IO (rtl/hbm_accel/sm/ot_hbm_accel_sm_v_die_budget.sdc, NOT false-pathed), ring multicycle SDC; then
# corner STA with every macro at its own SS / FF model.   Usage: route_sm.sh <label>   env: NEED (GB), CORES, PD
R=/srv/opentallas-scratch/claude/hbm-fmax-sm
lab=$1
W=$R/routes/$lab; mkdir -p $W
cd $R/src
FPD=$W/fp
python3 tools/hbm_accel_sm_v_floorplan.py --out $FPD $FPARGS > $W/floorplan.log 2>&1 || exit 1
mkdir -p physical/hbm_accel_sm_views/fp_$lab && cp $FPD/macro_place.tcl physical/hbm_accel_sm_views/fp_$lab/
read X0 Y0 X1 Y1 <<< $(python3 -c "import json;print(*json.load(open('$FPD/floorplan.json'))['die'])")
read C0 D0 C1 D1 <<< $(python3 -c "import json;print(*json.load(open('$FPD/floorplan.json'))['core'])")
pins=()
while read -r p; do pins+=(--pin-region "$p"); done < <(python3 -c "import json;print('\n'.join(json.load(open('$FPD/floorplan.json'))['pin_regions']))")
FP=$(cat $R/jobs/fp_srcs.txt)
srcs=()
for s in $FP rtl/gpu/ot_gpu_issue.sv rtl/hbm_accel/epilogue/ot_hbm_accel_issue.sv rtl/gpu/ot_gpu_bulk_copy.sv \
  rtl/hbm_accel/epilogue/ot_hbm_accel_bulk_copy.sv rtl/gpu/ot_gpu_stack.sv rtl/hbm_accel/sm/ot_hbm_accel_sm_v.sv \
  physical/hbm_accel_sm_views/ot_hbm_accel_tc16/ot_hbm_accel_tc16_bb.v \
  physical/hbm_accel_sm_views/ot_hbm_accel_bd_col/ot_hbm_accel_bd_col_bb.v \
  physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2_bb.v \
  physical/hbm_accel_macros/ot_sram_1r1w_512x256_m1_r2c2/ot_sram_1r1w_512x256_m1_r2c2_bb.v; do srcs+=(--source $s); done
MV="ot_hbm_accel_tc16=physical/hbm_accel_sm_views/ot_hbm_accel_tc16 ot_hbm_accel_bd_col=physical/hbm_accel_sm_views/ot_hbm_accel_bd_col ot_sram_1r1w_128x256_m1_r2c2=physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2 ot_sram_1r1w_512x256_m1_r2c2=physical/hbm_accel_macros/ot_sram_1r1w_512x256_m1_r2c2"
margs=(); cargs=()
for m in $MV; do margs+=(--macro-view $m); cargs+=(--macro ${m#*=}); done
export OT_ORFS_NUM_CORES=${CORES:-24}
/srv/opentallas-scratch/admit.sh ${NEED:-120} -- python3 tools/run_abi3_physical.py --view asap7 --top ot_hbm_accel_sm_v \
  "${srcs[@]}" --param ENABLE=1 "${margs[@]}" --macro-place-halo ${HALO:-2} ${HALO:-2} \
  --sdc-append rtl/hbm_accel/epilogue/ot_hbm_accel_bulk_copy_mc2.sdc --sdc-append rtl/hbm_accel/sm/ot_hbm_accel_sm_v_die_budget.sdc \
  --orfs-var PDN_TCL=/src/tools/chip_assembly/tcl/pdn_sm.tcl \
  --orfs-var MACRO_PLACEMENT_TCL=/src/physical/hbm_accel_sm_views/fp_$lab/macro_place.tcl \
  --routing-layers M2 M9 --die-area $X0 $Y0 $X1 $Y1 --core-area $C0 $D0 $C1 $D1 "${pins[@]}" \
  --clock-period-ns 0.833 --clock-uncertainty-ns 0.06 --clock-uncertainty-hold-ns 0.025 \
  --orfs-corner WC --hold-corners WC,BC --io-delay-fraction 0.2 --stages pnr \
  --place-density ${PD:-0.55} --hold-margin-ns 0.01 --orfs-var ADDER_MAP_FILE= \
  --slew-margin-percent 30 --purpose signoff_target --nickname-tag fsm_$lab \
  --keep-workdir $W/work --force --output $W/physical.json > $W/run.log 2>&1
echo "rc=$?" > $W/exit
python3 tools/w18/corner_sta.py --orfs-dir $W/work/orfs "${cargs[@]}" --output $W/corner_sta.json > $W/corner.log 2>&1
echo "corner_rc=$?" >> $W/exit
