#!/bin/bash
# CLAUDE S81-PH: route one S81 placeholder-kind view (top module named as its tools/dsrom_s81_fulldie.py r9 master) at
# the generator's outline with every die pin at the generator's position (physical/s81_ph_views/ports/<die>/<master>),
# MARGIN-FIRST (OWNER 2026-10-06): routed against io_vclk_m_770.sdc (setup uncertainty 123 ps on 833.333 = 770 ps
# effective, IO 0.2 T + 150 ps die clock-arrival allowance, vclk at the measured insertion), signed off at 833.333 / 60 ps
# (signoff_unc60.sdc via corner_sta --post-sdc).  Then LEF + SS/FF ETM export and the pin check against the generator.
# Adapted from the HBM-ABSTRACTS route_view.sh (claude/hbm-abstracts-hub-20261006).
#   route_view.sh <label> <die> <master> <top-source> [extra run_abi3_physical args]
# env: SRC (pinned source snapshot with SOURCE_COMMIT), OUT (route base), PD (0.45), CORES (16), NEED (GB, 24),
#      SRCS (extra sources), CLK (clock port, ck), MAXL (M7), HM (hold margin ns 0.035: sign-off FF >= +15 needs repair beyond the route corner; svc_pc FF -5.3 / ctrl_ctr +8.4 at 0.010), SDCX (extra sdc appended after
#      the margin sdc), CTSA, STEPS, PER (clock period ns, 0.833333; the VM serial domain 1.1111)
set -euo pipefail
lab=$1; die=$2; master=$3; topsrc=$4; shift 4
W=$OUT/$lab
# A label identifies immutable evidence. Retrying requires a fresh label; never
# truncate the original log before run_abi3_physical rejects a frozen output.
mkdir -p "$W"
for evidence in physical.json run.log exit args SOURCE_COMMIT corner_sta.json corner.log export.log check.json work view; do
    if [[ -e "$W/$evidence" ]]; then
        echo "S81 route refuses existing evidence: $W/$evidence; use a fresh label" >&2
        exit 73
    fi
done
cd "$SRC"
export OT_ORFS_NUM_CORES=${CORES:-16} NUM_CORES=${CORES:-16} OT_SYNTH_TIMEOUT_SECONDS=unlimited OT_FLOW_TIMEOUT_SECONDS=unlimited
P=physical/s81_ph_views/ports/$die/$master
read DW DH < <(python3 -c "import json;d=json.load(open('$P/ports.json'));print(d['w_um'],d['h_um'])")
mkdir -p $SRC/.views/$lab; cp $P/io_place.tcl $SRC/.views/$lab/io_place.tcl
# SDCM: the IO SDC regenerated at the measured insertion (closure-loop calibrate stage: make_io_vclk_margin.sh $CK_SS_MEAN)
cat ${SDCM:-physical/s81_ph_views/common/io_vclk_m_770.sdc} ${SDCX:+$SDCX} > $SRC/.views/$lab/margin.sdc
# Current S81 selector variants use isolated successors, preserving golden source pins.
if [[ "$topsrc" == rtl/dsrom_sys/s81_ph/ot_s81ph_sel_tile.sv ]]; then
    SRCS="${SRCS:-} rtl/dsrom_sys/s81_ph/selector_native/ot_s81ph_native_sel.sv rtl/dsrom_sys/s81_ph/selector_native/ot_s81ph_native_sel_lib.sv rtl/dsrom_sys/s81_ph/selector_native/ot_s81ph_native_sel_slice.sv"
fi
srcargs="--source $topsrc"; for s in ${SRCS:-}; do srcargs="$srcargs --source $s"; done
mvargs=""; for mv in ${MACROS:-}; do mvargs="$mvargs --macro-view $mv"; done
echo "SRC=$SRC die=$die master=$master top=$topsrc DW=$DW DH=$DH PD=${PD:-0.45} MAXL=${MAXL:-M7} SRCS=${SRCS:-} CLK=${CLK:-ck} SDCX=${SDCX:-} CTSA=${CTSA:-} $*" > $W/args
cat SOURCE_COMMIT > $W/SOURCE_COMMIT
rc=0
/srv/opentallas-scratch/admit.sh ${NEED:-24} -- python3 tools/run_abi3_physical.py --view asap7 --top $master $srcargs $mvargs ${MACROS:+--macro-place-halo 5 5} \
  --clock-port ${CLK:-ck} --clock-period-ns ${PER:-0.833333} --clock-uncertainty-ns 0.06 --clock-uncertainty-hold-ns 0.025 \
  --orfs-corner WC --hold-corners WC,BC --io-delay-fraction 0.2 --sdc-append .views/$lab/margin.sdc --stages pnr \
  --die-area 0 0 $DW $DH --core-area 0 0.54 $DW $(python3 -c "print(round($DH-0.54,4))") --place-density ${PD:-0.45} --routing-layers M2 ${MAXL:-M7} \
  --orfs-var PDN_TCL=/src/${PDN:-physical/s81_ph_views/common/pdn_view.tcl} --orfs-var IO_CONSTRAINTS=/src/.views/$lab/io_place.tcl \
  --orfs-var ADDER_MAP_FILE= ${CTSA:+--orfs-var "CTS_ARGS=$CTSA"} ${STEPS:-} \
  --step-tcl PRE_CTS=${PRECTS:-physical/s81_ph_views/common/pre_cts_fclk_root_buf.tcl} --step-tcl POST_CTS=${POSTCTS:-physical/s81_ph_views/common/post_cts_vclk.tcl} \
  --step-tcl PRE_GLOBAL_ROUTE=physical/abi3/v41x_karb_repair_buffer_cap.tcl \
  --slew-margin-percent 60 --hold-margin-ns ${HM:-0.035} --purpose signoff_target --nickname-tag s81ph_$(echo $lab | tr -c "A-Za-z0-9_\n" "_") \
  --synth-timeout-seconds unlimited --flow-timeout-seconds unlimited "$@" \
  --keep-workdir $W/work --force --output $W/physical.json > $W/run.log 2>&1 || rc=$?
echo "rc=$rc" > $W/exit
if (( rc != 0 )); then exit "$rc"; fi
# CTS-only calibration run (closure loop: --pnr-stop-after cts): no sign-off / export
case " $* " in *" --pnr-stop-after "*) echo DONE >> $W/exit; exit 0;; esac
mac1=$(echo ${MACROS:-} | awk '{print $1}' | cut -d= -f2)
python3 tools/w18/corner_sta.py ${mac1:+--macro $mac1} --post-sdc physical/s81_ph_views/common/signoff_unc60.sdc --orfs-dir $W/work/orfs --output $W/corner_sta.json > $W/corner.log 2>&1 || rc=$?
echo "corner_rc=$rc" >> $W/exit
if (( rc != 0 )); then exit "$rc"; fi
mvx=""; for mv in ${MACROS:-}; do mvx="$mvx --macro-view $(echo $mv | cut -d= -f2)"; done
python3 tools/hbm_fmax_attn_abstract.py --orfs-dir $W/work/orfs --name $master --out $W/view $mvx --tmp-dir $W/abs_tmp > $W/export.log 2>&1 || rc=$?
echo "export_rc=$rc" >> $W/exit
if (( rc != 0 )); then exit "$rc"; fi
python3 tools/s81_ph/s81_ph_views.py check --die $die --master $master --lef $W/view/$master.lef --ports physical/s81_ph_views/ports > $W/check.json 2>&1 || rc=$?
echo "check_rc=$rc" >> $W/exit
if (( rc != 0 )); then exit "$rc"; fi
echo DONE >> $W/exit
exit 0
