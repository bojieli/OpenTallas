#!/bin/bash
# QW-GEN3 phase 2 (local, git): netlist relay export of the bound GEN die + layer_compile of THIS die's schedule.
set -u
WT=/home/ubuntu/wt/qw-gen3-1019; T=${1:-dv2f19g3}
P=/home/ubuntu/scratch/qw-gen3/$T/p2; S=/srv/opentallas-scratch/claude/mu-die-qw/$T; mkdir -p $P
H=$(ssh -o ControlPath=none ot-epyc6 "cut -d' ' -f1 $S/src/SOURCE_COMMIT")
for f in out/case/die.v out/case/fwd_lanes.json out/case/die.v.params.json pre_bind/port_bind.json pre_bind/die_glue.sv out/relay_stages.json; do
  scp -q -o ControlPath=none ot-epyc6:$S/$f $P/ || exit 3; done
cd $WT
timeout 1200 python3 tools/qwen_layerbench/netlist_relay_stages.py --die-v $P/die.v --port-bind $P/port_bind.json --design qwen_compute \
  --commit $H --src-prefix $S/src/ --src-prefix /srv/opentallas-scratch/claude/qwen-split-compute/$T/src/ --local-rtl $P \
  --lanes $P/fwd_lanes.json --plan-id $T-netlist --out $P/relay_stages_netlist.json || exit 4
timeout 1800 python3 tools/qwen_layerbench/layer_compile.py --out $P/compiled_L1 --compute-stages $P/relay_stages_netlist.json \
  --kv-stages results/rtl/qwen_layer_tput_1018/compiled_L1/die_run/kv_kvs14c_relay_stages.json.gz --compute-commit $H \
  --compute-params $P/die.v.params.json --compute-die-v $P/die.v --compute-lanes $P/fwd_lanes.json > $P/layer_compile.log 2>&1; echo "layer_compile rc=$?"
  echo "relay check (netlist table vs this schedule):"; bash $WT/tools/die_relay_chain_step.sh $P/relay_stages_netlist.json $(ls $P/compiled_L1/relay_schedule/compute_compiled.json* | head -1) $P/relay_check.json
