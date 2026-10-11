#!/bin/bash
# [link] 2026-10-10 closure-loop route of hfd_lk_ep (rtl/hbm_accel/tu/lk_ep_20261010/hfd_lk_ep.sv) with the NS closed
# retry pipelines as hard macros (physical/hbm_link_retry_pipeline_20261009/view_wpin_hm10) and the S81 FMT1 gearbox.
#   route.sh <label> [extra run_abi3_physical args]   env: OUT, NS (3), CORES (16), PD (0.55), HM (0.010), DH (900)
# Outline: NS macros in a row (pitch 760) + 60-um edges -> DW = 60 + NS * 760; die-side flit / credit pins north,
# SerDes lane pins (x_tx / x_rx / x_rx_v) south, clk / rst / session west.
set -u
lab=$1; shift
W=${OUT:?}/$lab; mkdir -p $W
NS=${NS:-3}; C=${CORES:-16}; DH=${DH:-900}; DW=$(python3 -c "print(60 + $NS * 760)")
export OT_LKEP_MY=$(python3 -c "print(round(($DH - 460) / 2 / 1.08) * 1.08)")
export OT_ORFS_NUM_CORES=$C NUM_CORES=$C OT_SYNTH_TIMEOUT_SECONDS=unlimited OT_FLOW_TIMEOUT_SECONDS=unlimited
L=${L:-${CK_SS_MEAN:-770}}
bash physical/hbm_accel_die_views/common/make_io_vclk_margin.sh $L > /dev/null
SDCA=physical/hbm_accel_die_views/common/io_vclk_m_$L.sdc
echo "NS=$NS PD=${PD:-0.55} HM=${HM:-0.010} DW=$DW DH=$DH VT=${OT_MULTI_VT:-rvt} $*" > $W/args
cat SOURCE_COMMIT > $W/SOURCE_COMMIT 2>/dev/null
python3 tools/run_abi3_physical_aligned_guarded.py --macro-track-gate --view asap7 --top hfd_lk_ep --param NS=$NS \
 --source rtl/dsrom_sys/s81_ph/ot_s81ph_link_gbx.sv --source rtl/hbm_accel/tu/lk_ep_20261010/hfd_lk_ep.sv \
 --macro-view ot_hbm_link_retry_pipeline=physical/hbm_link_retry_pipeline_20261009/view_wpin_hm10 \
 --macro-place-halo 8 8 --orfs-var MACRO_PLACEMENT_TCL=/src/physical/hbm_lk_ep_20261010/macro_place.tcl \
 --pin-region '^(t_|r_v|r_flit|r_cr)=top' --pin-region '^x_=bottom' --pin-region '^(clk|rst_n|session|fault|locked|st_)=left' \
 --clock-period-ns .833333333 --clock-uncertainty-ns .06 --clock-uncertainty-hold-ns .025 \
 --orfs-corner WC --hold-corners WC,BC --io-delay-fraction .2 --sdc-append $SDCA \
 --die-area 0 0 $DW $DH --core-area 5.4 5.4 $(python3 -c "print($DW-5.4, $DH-5.4)") \
 --stages ${STAGES:-pnr} --place-density ${PD:-0.55} \
 --hold-margin-ns ${HM:-0.010} --orfs-var ADDER_MAP_FILE= --slew-margin-percent 30 \
 --synth-timeout-seconds unlimited --flow-timeout-seconds unlimited \
 --purpose signoff_target --nickname-tag hfd_lk_ep_$(echo $lab | tr -c "A-Za-z0-9_\n" _) \
 --keep-workdir $W/work --force --output $W/physical.json "$@" > $W/run.log 2>&1
rc=$?; echo "rc=$rc" > $W/exit
case " $* " in *"stop-after"*) exit $rc ;; esac
python3 tools/w18/corner_sta.py --post-sdc physical/hbm_accel_die_views/common/signoff_unc60.sdc --post-sdc physical/hbm_accel_die_views/common/vclk_corner_true.sdc --orfs-dir $W/work/orfs --output $W/corner_sta.json > $W/corner.log 2>&1
echo "corner_rc=$?" >> $W/exit
exit $rc
