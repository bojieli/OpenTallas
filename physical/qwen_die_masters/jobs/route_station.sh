#!/bin/bash
# Margin route of the die corridor station (KIND=cst: qfd_cst_n/_s, 1,536 copies, TAP 1 SPLIT 0, a N / b S / tap W)
# or column head (KIND=chead: qfd_chead_e/_w, 64 copies, TAP 1 SPLIT 1, a E / b W / t N / c S) in the r20c frame
# 52.68 x 103.656 um, M2-M7.  Corridor ports cross clock regions (150 ps), the station tap stays in its tile's region (90).
# usage: route_station.sh NAME KIND   (env: SRC, R)
set -uo pipefail
NAME=$1; KIND=$2; SRC=${SRC:?}; R=${R:?}; W=$R/$NAME; mkdir -p $W; cd $SRC
D=/src/physical/qwen_die_masters
if [ "$KIND" = cst ]; then
  P=(--param DW=508 --param TAP=1 --param SPLIT=0 --pin-region '^(a_d|a_r)=top:4-48' --pin-region '^(b_d|b_r)=bottom:4-48'
     --pin-region '^(t_d|t_r|c_d|c_r|clk|rst_n)(\[|$)=left:8-96')
  INTER='a_d*,a_r,b_d*,b_r'
elif [ "$KIND" = lsth ]; then
  # qfd_lst_h_e / _w (20 copies, 34.536 x 97.176): one registered 1056-bit link stage, W -> E
  P=(--param DW=1056 --param TAP=0 --param SPLIT=0 --pin-region '^(a_d|a_r|clk|rst_n)(\[|$)=left:4-93'
     --pin-region '^(b_d|b_r|t_d|t_r|c_d|c_r)(\[|$)=right:4-93')
  INTER='a_d*,a_r,b_d*,b_r'; FW=34.536; FH=97.176
else
  P=(--param DW=508 --param TAP=1 --param SPLIT=1 --pin-region '^(a_d|a_r|clk|rst_n)(\[|$)=right:8-96' --pin-region '^(b_d|b_r)=left:8-96'
     --pin-region '^(t_d|t_r)=top:4-48' --pin-region '^(c_d|c_r)=bottom:4-48')
  INTER='a_d*,a_r,b_d*,b_r,t_d*,t_r,c_d*,c_r'
fi
export OT_ORFS_NUM_CORES=8 OT_SYNTH_TIMEOUT_SECONDS=unlimited OT_FLOW_TIMEOUT_SECONDS=unlimited
echo "$(date -Is) start $NAME $KIND src=$(cat SOURCE_COMMIT 2>/dev/null)" >> $W/STATUS
python3 tools/run_abi3_physical.py --view asap7 --top ot_qwen_die_station --source rtl/physical/ot_qwen_die_station.sv \
  "${P[@]}" --die-area 0 0 ${FW:-52.68} ${FH:-103.656} \
  --core-area 2.16 2.16 $(python3 -c "print(round(${FW:-52.68}-2.16,3), round(${FH:-103.656}-2.16,3))") \
  --routing-layers M2 M7 --clock-port clk --clock-period-ns 0.770 --clock-uncertainty-ns 0.06 \
  --clock-uncertainty-hold-ns 0.025 --orfs-corner WC --hold-corners WC,BC --io-delay-fraction 0.2 --stages synth,pnr \
  --place-density 0.6 --hold-margin-ns ${HM:-0.02} --synth-timeout-seconds unlimited --flow-timeout-seconds unlimited \
  --orfs-var ADDER_MAP_FILE= --orfs-var NUM_CORES=8 --orfs-var SDC_FILE=$D/station_p770.sdc --orfs-var QDM_SDC_DIR=$D \
  --orfs-var 'PLACE_PINS_ARGS=-min_distance 1 -min_distance_in_tracks' \
  --step-tcl PRE_CTS=physical/qwen_die_masters/pre_cts_skew.tcl --step-tcl POST_CTS=physical/qwen_die_masters/post_plain.tcl \
  --step-tcl PRE_GLOBAL_ROUTE=physical/qwen_die_masters/pre_ref_skew.tcl --step-tcl POST_GLOBAL_ROUTE=physical/qwen_die_masters/post_plain.tcl \
  --step-tcl PRE_DETAIL_ROUTE=physical/qwen_die_masters/pre_ref_skew.tcl --step-tcl POST_DETAIL_ROUTE=physical/qwen_die_masters/post_plain.tcl \
  --step-tcl PRE_FILLCELL=physical/qwen_die_masters/pre_ref_skew.tcl --step-tcl POST_FILLCELL=physical/qwen_die_masters/post_plain.tcl \
  --orfs-var OT_IO_SKEW=90 --orfs-var OT_IO_HOLD_SKEW=50 --orfs-var 'OT_REF_GLOB=*br_q*' \
  --orfs-var "OT_IO_INTER=$INTER" --orfs-var OT_IO_SKEW_INTER=150 \
  --slew-margin-percent 30 --purpose signoff_target --nickname-tag qdm_$NAME \
  --keep-workdir $W/work --force --output $W/physical.json > $W/flow.log 2>&1
flow_rc=$?
echo $flow_rc > $W/flow.exit
if [ "$flow_rc" -ne 0 ]; then exit "$flow_rc"; fi
{ cat physical/qwen_die_masters/station_signoff.sdc; echo 'set ::env(OT_IO_SKEW) 90'; echo 'set ::env(OT_IO_HOLD_SKEW) 50'; echo 'set ::env(OT_REF_GLOB) {*br_q*}'
  echo "set ::env(OT_IO_INTER) {$INTER}"; echo 'set ::env(OT_IO_SKEW_INTER) 150'
  cat physical/qwen_die_masters/io_ref_skew.sdc; } > $W/io_ref_skew_signoff.sdc
python3 tools/w18/corner_sta_ref.py --orfs-dir $W/work/orfs --extra-sdc $W/io_ref_skew_signoff.sdc \
  --output $W/corner_sta_ref.json > $W/sta_ref.log 2>&1
echo $? > $W/sta.exit
echo "$(date -Is) done flow=$(cat $W/flow.exit) sta=$(cat $W/sta.exit)" >> $W/STATUS
