#!/bin/bash
# QW-GEN3 10-19 = successor GEN of dv2f19g2 (claude/qw-gen3-1019): + 446 QW-DIECLK2 landings (OT_SPLIT_LAND_LIST) + R2 one hard instance per region root (OT_SPLIT_REGION_ONE_HARD, all hard<->hard direct buses landed) + DC_GRID_CENTER=1 + MU-DQ-BOOTCTX (mu_ctxrx -> tt_ctlm.ctx_x) + relay table = netlist walk vs the schedule recompiled on THIS die. STAND-INS declared in results/rtl/qw_gen3_1019/README.md. PILOT_NOT_A_GATE. (run dv2f19g3r)
# QW-GEN2 side check (does not gate the physical chain): the GEN netlist's relay table (netlist_relay_stages, the
# QW-L1SEAM source) vs results/rtl/qwen_layer_tput_1018/compiled_L1/relay_schedule/compute_compiled.json (dv2f18dh2 table)
S=/srv/opentallas-scratch/claude/qwen-split-compute/dv2f19g3r; cd $S/src || exit 9
for i in $(seq 240); do [ -s $S/chain/port_bind/port_bind.json ] && break; sleep 30; done
[ -s $S/chain/port_bind/port_bind.json ] || { echo "RELAY_SIDE no port_bind.json" > $S/relay_side.txt; exit 1; }
# no git on the run host: every relative RTL dir of the bound masters is passed as --local-rtl (files read from this src)
LR=$(python3 -c 'import json,sys,os;b=json.load(open(sys.argv[1]));ps=set()
def w(x):
    if isinstance(x,dict): [w(v) for v in x.values()]
    elif isinstance(x,list): [w(v) for v in x]
    elif isinstance(x,str) and x.endswith((".sv",".v",".svh")) and not x.startswith("/"): ps.add(os.path.dirname(x))
w(b); print(" ".join("--local-rtl "+sys.argv[2]+"/"+d for d in sorted(ps)))' $S/chain/port_bind/port_bind.json $S/src)
python3 tools/qwen_layerbench/netlist_relay_stages.py $LR --die-v $S/out/case/die.v --port-bind $S/chain/port_bind/port_bind.json \
  --design qwen_compute --commit $(cut -d' ' -f1 SOURCE_COMMIT) --src-prefix $S/src/ --src-prefix /srv/opentallas-scratch/claude/mu-die-qw/dv2f19g3r/src/ --local-rtl $S/chain/port_bind --local-rtl $S/out/case --lanes $S/out/case/fwd_lanes.json \
  --plan-id dv2f19g3r-netlist --out $S/relay_stages_netlist.json || { echo "RELAY_SIDE export FAIL" > $S/relay_side.txt; exit 1; }
bash tools/die_relay_chain_step.sh $S/relay_stages_netlist.json results/rtl/qwen_layer_tput_1018/compiled_L1/relay_schedule/compute_compiled.json $S/relay_check_side.json > $S/relay_side.txt 2>&1
echo "rc=$?" >> $S/relay_side.txt
