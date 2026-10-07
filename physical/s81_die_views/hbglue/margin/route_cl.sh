#!/bin/bash
# Glue (ot_dsrom_head_bundle_glue) MARGIN route for the closure loop: IO from the MEASURED insertion (CK_SS_MEAN / CK_FF_MEAN,
# defaults = glue_m3's measured 231 / 127 ps): in max = ss+250, in min = ff-50, out max = 100-(ss-150), out min = -(ff+50).
# usage: OUT=<dir> SRC=<src root> route_cl.sh <label> [extra args, e.g. --pnr-stop-after cts]
set -o pipefail
L=${1:?label}; shift; S=${SRC:-.}; O=${OUT:?out}/$L; mkdir -p $O; cd $S
SS=${CK_SS_MEAN:-231}; FF=${CK_FF_MEAN:-127}
io(){ python3 -c "print(round($1/1000.0,4))"; }
IMIN=$(io "$FF-50"); IMAX=$(io "$SS+250"); OMIN=$(io "-($FF+50)"); OMAX=$(io "100-($SS-150)")
HM=${HM:-0.035}
export OT_ORFS_NUM_CORES=16 NUM_CORES=16 OPENTALLAS_ORFS_IMAGE=${OPENTALLAS_ORFS_IMAGE:-sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29}
H=physical/s81_die_views/hbglue/margin
sed -e "s/input_delay -max 400/input_delay -max $(python3 -c "print(round($SS+250))")/" -e "s/input_delay -min 125/input_delay -min $(python3 -c "print(round($FF-50))")/" -e "s/output_delay -max 100/output_delay -max $(python3 -c "print(round(100-($SS-150)))")/" -e "s/output_delay -min -225/output_delay -min $(python3 -c "print(round(-($FF+50)))")/" $H/signoff_833_m2.sdc > $O/signoff.sdc
args=(--view asap7 --top ot_dsrom_head_bundle_glue
  --source rtl/s81/ot_dsrom_head_bundle_glue.sv --source rtl/s81/ot_s81_head_min_delay.sv --source rtl/hdc/ot_hdc_delay.sv
  --param USE_MIN_DELAY_CELLS=1 --param MARGIN=1 --param MIN_DEPTH=2
  --clock-period-ns 0.730 --clock-uncertainty-ns 0.060 --clock-uncertainty-hold-ns 0.025
  --orfs-corner WC --hold-corners BC --stages pnr
  --false-path-from rst_n --core-input-delay-min-ns $IMIN --core-input-delay-max-ns $IMAX
  --output-delay-min-ns $OMIN --output-delay-max-ns $OMAX
  --synth-timeout-seconds unlimited --flow-timeout-seconds unlimited
  --core-utilization 30 --place-density .55 --routing-layers M2 M6 --orfs-var ADDER_MAP_FILE=
  --max-transition-ns .25 --slew-margin-percent 20 --hold-margin-ns $HM --orfs-var NUM_CORES=16 --orfs-var PLACE_DENSITY_LB_ADDON=
  --step-tcl PRE_CTS=physical/abi3/v41x_karb_repair_buffer_cap.tcl --step-tcl PRE_GLOBAL_ROUTE=physical/abi3/v41x_karb_repair_buffer_cap.tcl
  --keep-workdir $O/work --output $O/physical.json --nickname-tag $L --keep-heavy-artifacts --force)
for hook in POST_PDN POST_CTS POST_GLOBAL_ROUTE; do args+=(--step-tcl $hook=$H/keep.tcl); done
echo "$(date -Is) START $(hostname) io $IMIN $IMAX $OMIN $OMAX" >> $O/MANIFEST
python3 tools/run_abi3_physical.py "${args[@]}" "$@" > $O/run.log 2>&1; rc=$?
echo "rc=$rc" > $O/exit
if [ $rc -eq 0 ] && [[ " $* " != *"--pnr-stop-after"* ]]; then
  python3 tools/w18/corner_sta.py --orfs-dir $O/work/orfs --post-sdc ${O#$S/}/signoff.sdc --output $O/corner_sta.json > $O/sta.log 2>&1; echo "corner_rc=$?" >> $O/exit
fi
