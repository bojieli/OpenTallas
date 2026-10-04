#!/bin/bash
# Qwen async sequencer in-context SS/FF A/B (claude/qwen-async-physical-20261004 @ c584832a5)
E=/srv/opentallas-scratch/claude/qwen-async-phys; W=$E/wt; J=$E/jobs; O=$E/out
cd $W
export OT_ORFS_NUM_CORES=20
COMMON="--view asap7 --top ot_qwen_tp_seq_async_ctx_w12 --source rtl/rom/ot_qwen_tp_seq_async_w12.sv --source rtl/rom/ot_qwen_tp_seq_async_ctx_w12.sv \
 --clock-period-ns 0.833333 --clock-uncertainty-ns 0.060 --clock-uncertainty-hold-ns 0.025 --corner TT --orfs-corner WC --hold-corners WC,BC \
 --max-transition-ns --max-fanout 32 --slew-margin-percent 30 --false-path-io --orfs-var ADDER_MAP_FILE= --keep-heavy-artifacts --die-area 0 0 130 130 --core-area 2.16 2.16 127.84 127.84"
run() { # a stages tag
  local a=$1 st=$2 tag=$3
  echo "$(date -Is) START $tag" >> $J/MANIFEST
  /srv/opentallas-scratch/admit.sh 24 -- python3 tools/run_abi3_physical.py $COMMON --param ASYNC_COLL=$a --stages $st \
    --nickname-tag qasyncctx_$tag --keep-workdir $O/work_$tag --output $O/$tag.json --force > $J/$tag.log 2>&1
  echo $? > $J/$tag.exit; echo "$(date -Is) END $tag exit=$(cat $J/$tag.exit)" >> $J/MANIFEST
}
#pre-layout done in first launch
run 0 synth,pnr route_a0 & run 1 synth,pnr route_a1 &
wait
echo "$(date -Is) TERMINAL" >> $J/MANIFEST
