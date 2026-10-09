#!/bin/bash
# route.sh <label> <grp|top> <G> [extra run_abi3_physical args, e.g. $CL_STOP_AFTER]   (cwd = pinned source snapshot)
# Closure-loop route of the partitioned HBM norm engine (stream hbm-norm-split 2026-10-08):
#   grp: the hardened lane group ot_hbm_norm_grp<G> (2 x G/8 SRAM macros inside), die DIEW x DIEH (default by G),
#        then corner_sta (TT setup / FF hold / SS sensitivity) and the macro view (LEF + SS/FF/TT ETM) -> $W/view
#   top: ot_hbm_norm_split_view_g<G> with N/G group macros from views/ot_hbm_norm_grp<G> (installed by
#        tools/tt_views/ttv_install.sh from the first group route that lands); die sized from the group LEF
# env: OUT (run base), PD, CORES (16), PER (route period ns, 0.770), HM (hold margin ns), DIEW/DIEH,
#      IO_ROUTE_SDC (io_vclk_<L>.sdc; default io_vclk_<L0>.sdc at the planning insertion L0), IO_FF_SDC (FF post-SDC)
set -u
lab=$1; kind=$2; G=$3; shift 3
W=${OUT:?}/$lab; mkdir -p $W
V=physical/hbm_norm_split_20261008
C=${CORES:-16}
export OT_ORFS_NUM_CORES=$C NUM_CORES=$C OT_SYNTH_TIMEOUT_SECONDS=unlimited OT_FLOW_TIMEOUT_SECONDS=unlimited
srcargs=""; for s in $(cat $V/sources.f); do srcargs="$srcargs --source $s"; done
KEEPM="ot_hdc_fp32_mul_f12_l5 ot_hdc_fp32_mul_f12_l6 ot_hdc_fp32_mul_f12_l6i ot_dsrom_fp32_add_f12_l6 ot_hdc_fp32_add_f12_l4 ot_hdc_fp32_add_f12_l5 ot_hdc_fp32_add_f12_l5x ot_hdc_fp32_add_f12_l5i"
L0=${L0:-350}
if [ -z "${IO_ROUTE_SDC:-}" ]; then bash physical/hbm_accel_die_views/common/make_io_vclk.sh $L0; IO_ROUTE_SDC=physical/hbm_accel_die_views/common/io_vclk_$L0.sdc; fi
SRAM=ot_sram_1r1w_128x256_m1_r2c2
if [ "$kind" = grp ]; then
  top=ot_hbm_norm_grp$G
  case $G in 8) DW=${DIEW:-380}; DH=${DIEH:-380} ;; 16) DW=${DIEW:-540}; DH=${DIEH:-540} ;; esac
  MV="$SRAM=physical/asap7_memory_macros_v2/$SRAM"; MACD=physical/asap7_memory_macros_v2/$SRAM; HALO="4 4"
else
  top=ot_hbm_norm_split_view_g$G${TOPSFX:-}   # safe-hbm S-C7: TOPSFX=r -> the REP=1 top (broadcast flops per group)
  GV=$V/views/ot_hbm_norm_grp$G
  [ -s $GV/ot_hbm_norm_grp${G}_tt.lib ] || { echo "group view missing: $GV" > $W/run.log; echo "rc=2" > $W/exit; exit 2; }
  read GW GH < <(awk '/^ *SIZE/{print $2, $4; exit}' $GV/ot_hbm_norm_grp$G.lef)
  NG=$((64 / G)); COLS=$((NG / 2)); [ $COLS -lt 1 ] && COLS=1; ROWS=$(( (NG + COLS - 1) / COLS ))
  # groups in ROWS x COLS with 24 um channels, plus a 180 um band for the top logic (vector tree, rsqrt, act-quant,
  # capture / output flops) and a 30 um ring
  read DW DH < <(python3 -c "print(round($COLS*($GW+24)+60,3), round($ROWS*($GH+24)+180+60,3))")
  DW=${DIEW:-$DW}; DH=${DIEH:-$DH}
  MV="ot_hbm_norm_grp$G=$GV"; MACD=$GV; HALO="10 10"
fi
echo "kind=$kind top=$top G=$G die=${DW}x${DH} PD=${PD:-0.5} PER=${PER:-0.770} HM=${HM:-0.050} IO_ROUTE_SDC=$IO_ROUTE_SDC IO_FF_SDC=${IO_FF_SDC:-} $*" > $W/args
python3 tools/run_abi3_physical.py --view asap7 --top $top $srcargs --macro-view $MV --macro-place-halo $HALO \
  --clock-port clk --clock-period-ns ${PER:-0.770} --clock-uncertainty-ns 0.06 --clock-uncertainty-hold-ns 0.025 \
  --orfs-corner WC --hold-corners WC,BC --io-delay-fraction 0.2 --sdc-append $IO_ROUTE_SDC --stages pnr \
  --die-area 0 0 $DW $DH --core-area 2 2 $(python3 -c "print(round($DW-2,3), round($DH-2,3))") --place-density ${PD:-0.5} \
  --orfs-var NUM_CORES=$C --orfs-var ADDER_MAP_FILE= --orfs-var PLACE_DENSITY_LB_ADDON= --orfs-var "SYNTH_KEEP_MODULES=$KEEPM" \
  --orfs-var "PLACE_PINS_ARGS=-min_distance 1 -min_distance_in_tracks" --orfs-var "IO_PLACER_H=M4 M6" --orfs-var "IO_PLACER_V=M5 M7" \
  --step-tcl PRE_CTS=physical/abi3/v41x_karb_repair_buffer_cap.tcl --step-tcl PRE_GLOBAL_ROUTE=physical/abi3/v41x_karb_repair_buffer_cap.tcl \
  --slew-margin-percent 60 --hold-margin-ns ${HM:-0.050} --purpose signoff_target --nickname-tag nsp_$lab \
  --synth-timeout-seconds unlimited --flow-timeout-seconds unlimited "$@" \
  --keep-workdir $W/work --force --output $W/physical.json > $W/run.log 2>&1
rc=$?; echo "rc=$rc" > $W/exit
case " $* " in *"stop-after"*) exit $rc ;; esac
python3 tools/w18/corner_sta.py --macro $MACD --orfs-dir $W/work/orfs ${IO_FF_SDC:+--post-sdc $IO_FF_SDC} --output $W/corner_sta.json > $W/corner.log 2>&1
echo "corner_rc=$?" >> $W/exit
if [ "$kind" = grp ]; then
  python3 tools/tt_views/view_export.py --orfs-dir $W/work/orfs --name $top --out $W/view --tmp-dir $W/abs_tmp \
    --macro-view $MACD --corners ss,ff,tt > $W/export.log 2>&1
  echo "export_rc=$?" >> $W/exit
fi
exit $rc
