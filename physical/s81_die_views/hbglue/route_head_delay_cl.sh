#!/bin/bash
# route_head_delay_cl.sh <label> (TT-VIEWS 2026-10-07): closure-loop TC re-route of the S81 head delay leaf
# ot_s81_head_delay8x32 (argv of results/rtl/s81_hbglue_20261006/leaf/physical.json; the Codex run dir was deleted) +
# its view at SS/FF/TT (tools/tt_views/view_export.py, routed 6_final.sdc as the original export) -> $W/view.  env OUT.
lab=$1; W=${OUT:?}/$lab; mkdir -p $W
python3 tools/run_abi3_physical.py --view asap7 --top ot_s81_head_delay8x32 --source rtl/s81/ot_s81_head_delay8x32.sv \
  --clock-period-ns .833 --clock-uncertainty-ns .060 --clock-uncertainty-hold-ns .025 --orfs-corner WC --hold-corners WC,BC \
  --stages pnr --io-delay-fraction .2 --synth-timeout-seconds unlimited --flow-timeout-seconds unlimited \
  --keep-workdir $W/work --force --output $W/physical.json --core-utilization 55 --place-density .65 --routing-layers M2 M6 \
  --orfs-var ADDER_MAP_FILE= --max-transition-ns .25 --orfs-var NUM_CORES=${CORES:-8} --nickname-tag hd_$lab > $W/run.log 2>&1
echo "rc=$?" > $W/exit
python3 tools/w18/corner_sta.py --orfs-dir $W/work/orfs --output $W/corner_sta.json > $W/corner.log 2>&1
echo "corner_rc=$?" >> $W/exit
python3 tools/tt_views/view_export.py --orfs-dir $W/work/orfs --name ot_s81_head_delay8x32 --out $W/view --tmp-dir $W/abs_tmp --corners ss,ff,tt > $W/export.log 2>&1
echo "export_rc=$?" >> $W/exit
