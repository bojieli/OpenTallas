#!/bin/bash
# QLB-GEN 10-18 post-GEN (netlist only): strict bind (port bind + lane audit + record_bundles audit + die param audit),
# record_bundles audit with the GEN lane E, c_ctl slice re-cut (qfd_tt_ctlm_dv + qfd_sys_face + relays/landings/rst_rep).
set -u
S=$(readlink -f "$1"); cd $S/src || exit 9
grep -q "^rc=0" $S/out.log || { echo "GEN not rc=0"; exit 7; }
P=$S/post; mkdir -p $P
OT_PORT_BIND_STRAPS=$S/src/results/arch/qwen_split_compute_1014/q_slice_1017/straps_dv2f8.json bash tools/qwen_split/port_bind_compute.sh $S/out/case/die.v $P/port_bind > $P/port_bind.line 2>&1
echo "strict_bind rc=$?" >> $P/port_bind.line
python3 tools/qwen_split/record_bundles.py audit $S/out/case/die.v --lanes $S/out/case/fwd_lanes.json --out $P/record_bundles_lanes.json > $P/record_bundles_lanes.txt 2>&1
echo "record_bundles(lanes E) rc=$?" >> $P/record_bundles_lanes.txt
GR="qfd_(rly|rlyh|rlyh0|land|landh|landh0)_.*|qfd_rst_rep(_p8)?"
python3 tools/qwen_layerbench/slice_cut.py --die-v $S/out/case/die.v --bind $P/port_bind/port_bind.json --src $S/src --master "qfd_(tt_ctlm_dv|sys_face)" --grow "$GR" --top qwc_slice_ctl --out $P/c_ctl > $P/cut.log 2>&1
echo "cut rc=$?" >> $P/cut.log
cat $P/port_bind.line; tail -1 $P/record_bundles_lanes.txt; tail -2 $P/cut.log
