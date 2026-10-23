#!/bin/bash
# QW-L1K 10-20: compile the Qwen L1 seam on the g5r2b compute die (its own netlist relay table / die.v / params / lanes, GEN src cfc5a82ac)
# against the CANONICAL KV production table = d22bu (kvs14r-ccc9418ac-gen9d22bu) relay_stages_netlist.json.gz (strict bind v2 PASS 69/46061).
set -u
W=/srv/opentallas-scratch/claude/qw-l1k-1020; S=/srv/opentallas-scratch/claude/mu-die-qw/dv2f20g5r2b; P=$S/p2
export OT_GIT_SHOW_CACHE=$W/gitcache
cd $S/src
timeout 1800 python3 tools/qwen_layerbench/layer_compile.py --out $W/compiled_L1_g5r2b_d22bu --compute-stages $P/relay_stages_netlist.json \
  --kv-stages $W/kv_d22bu_relay_stages_netlist.json.gz --compute-commit cfc5a82ac --kv-commit ccc9418ac \
  --compute-params $P/die.v.params.json --compute-die-v $P/die.v --compute-lanes $P/fwd_lanes.json > $W/layer_compile.log 2>&1
echo "layer_compile rc=$?"; tail -3 $W/layer_compile.log
for d in compute kv; do f=$(ls $W/compiled_L1_g5r2b_d22bu/relay_schedule/${d}_compiled.json* 2>/dev/null | head -1); echo "$d schedule $f"; done
bash tools/die_relay_chain_step.sh $P/relay_stages_netlist.json $(ls $W/compiled_L1_g5r2b_d22bu/relay_schedule/compute_compiled.json* | head -1) $W/relay_check_compute.json; echo "compute relay rc=$?"
bash tools/die_relay_chain_step.sh $W/kv_d22bu_relay_stages_netlist.json.gz $(ls $W/compiled_L1_g5r2b_d22bu/relay_schedule/kv_compiled.json* | head -1) $W/relay_check_kv.json; echo "kv relay rc=$?"
