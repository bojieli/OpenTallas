#!/bin/bash
# Closure-loop form of the STREAM4 CDC margin route m1j_cdc_margin_u123_ioh80 (results/rtl/qwen_stream4_cdc_20261005/
# margin_20261006/m1j_cdc_margin_u123_ioh80/cmd.txt): ot_qwen_stream4_cdc_pc MARGIN 1, r21 qfd_cdc faces (ho E, hi N,
# co W, ci S), route and sign-off at 833.333 (io_skew90.sdc post-SDC: 90 ps intra-region, hold 50).  HM = route hold
# margin (ns); the loop's post-route hold ECO carries the internal synchroniser hold to +18.
# usage: route_cdc.sh NAME OUTROOT [cts]
set -uo pipefail
NAME=$1; OUT=$2; STOP=${3:-}; SRC=${SRC:?}; W=$OUT/$NAME; mkdir -p $W; cd $SRC
SO=(); [ -n "$STOP" ] && SO=(--pnr-stop-after $STOP)
export OT_ORFS_NUM_CORES=16 OT_SYNTH_TIMEOUT_SECONDS=unlimited OT_FLOW_TIMEOUT_SECONDS=unlimited
python3 tools/run_abi3_physical.py --view asap7 --top ot_qwen_stream4_cdc_pc --source rtl/hdc/kv/ot_qwen_stream4_cdc_pc.sv --source rtl/hdc/v41x/ot_hdc_v41x_kreg.sv --param MARGIN=1 --param LCRED=6 --param SYNC=2 --param RSEL=1 --param RNG=10 --core-utilization 50 --slew-margin-percent 30 --pin-region '^(h_cred|h_wv|h_wsec|h_cv|h_csec|h_cdata|h_ctag|h_fault)=right' --pin-region '^(h_lv|h_lsec|h_lrow|h_ldata|h_hand|h_wcon|h_av|h_atag|hclk$|h_arst)=top' --pin-region '^(l_)=left' --pin-region '^(w_|wd_|c_|clk$)=bottom' --clock-port clk --clock-period-ns 0.833333 --clock-uncertainty-ns 0.06 --clock-uncertainty-hold-ns 0.025 --orfs-corner WC --hold-corners WC,BC --io-delay-fraction 0.2 --stages synth,pnr --hold-margin-ns ${HM:-0.01} --orfs-var ADDER_MAP_FILE= --orfs-var NUM_CORES=16 --orfs-var SDC_FILE=/src/physical/qwen_stream4_cdc/cdc_pc_die_m.sdc --nickname-tag qcdc_$NAME --purpose signoff_target --output $W/physical.json --keep-workdir $W/work --orfs-var QCD_SDC_DIR=/src/physical/qwen_stream4_cdc --orfs-var OT_IO_SKEW=90 --orfs-var OT_IO_HOLD_SKEW=80 --step-tcl PRE_CTS=physical/qwen_stream4_cdc/pre_cts_skew.tcl --step-tcl POST_CTS=physical/qwen_stream4_cdc/post_plain.tcl --step-tcl PRE_GLOBAL_ROUTE=physical/qwen_stream4_cdc/pre_ref_skew.tcl --step-tcl POST_GLOBAL_ROUTE=physical/qwen_stream4_cdc/post_plain.tcl --step-tcl PRE_DETAIL_ROUTE=physical/qwen_stream4_cdc/pre_ref_skew.tcl --step-tcl POST_DETAIL_ROUTE=physical/qwen_stream4_cdc/post_plain.tcl --step-tcl PRE_FILLCELL=physical/qwen_stream4_cdc/pre_ref_skew.tcl --step-tcl POST_FILLCELL=physical/qwen_stream4_cdc/post_plain.tcl "${SO[@]}" > $W/flow.log 2>&1
rc=$?; echo "flow_rc=$rc" > $W/status
[ -n "$STOP" ] && exit $rc
python3 tools/w18/corner_sta.py --orfs-dir $W/work/orfs --post-sdc physical/qwen_stream4_cdc/io_skew90.sdc --output $W/corner_sta.json > $W/sta.log 2>&1
src=$?; echo "corner_rc=$src" >> $W/status
[ $rc -eq 0 ] && [ $src -eq 0 ]
