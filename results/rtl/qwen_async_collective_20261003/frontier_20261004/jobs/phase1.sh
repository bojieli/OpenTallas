#!/bin/bash
# Frontier/registered-read redesign, phase 1: Verilator gate (SB_PIPE 2,3), ME-write order trace (L0), synth+sta screens.
R=/srv/opentallas-scratch/claude/qwen-async-frontier; S=$R/src
P1=/srv/opentallas-scratch/claude/qwen-async-full; LP=/srv/opentallas-scratch/claude/layer-parallel-sim
st() { echo "$(date -u +%FT%TZ) $*" >> $R/chain.log; }
cd $S
for m in 2 3; do ( python3 tools/qwen_tp4_async_coll_verilator_gate.py --work $R/vg$m --result $R/res/gate_sbpipe$m.json --seeds 2 --sb-pipe $m > $R/logs/gate$m.log 2>&1; st "GATE m=$m rc=$?" ) & done
export OT_ORFS_NUM_CORES=16
COMMON="--view asap7 --top ot_qwen_tp_seq_async_ctx_w12 --source rtl/rom/ot_qwen_tp_seq_async_w12.sv --source rtl/rom/ot_qwen_tp_seq_async_ctx_w12.sv \
 --clock-period-ns 0.833333 --clock-uncertainty-ns 0.060 --clock-uncertainty-hold-ns 0.025 --corner TT --orfs-corner WC --hold-corners WC,BC \
 --max-transition-ns --max-fanout 32 --slew-margin-percent 30 --false-path-io --orfs-var ADDER_MAP_FILE= --keep-heavy-artifacts --hold-margin-ns 0.01 --die-area 0 0 130 130 --core-area 2.16 2.16 127.84 127.84"
for m in 1 2 3; do ( /srv/opentallas-scratch/admit.sh 16 -- python3 tools/run_abi3_physical.py $COMMON --param ASYNC_COLL=1 --param SB_PIPE=$m --stages synth,sta \
   --nickname-tag qafr_pre$m --output $R/out/pre$m.json --force > $R/logs/pre$m.log 2>&1; st "PRE m=$m rc=$?" ) & done
# trace build (SB_PIPE=2 + OT_SB_TRACE), L0 only
T="python3 $S/tools/qwen_rom_layer_parallel_sim.py"
A="--tp 4 --groups 6144 --count-width 18 --su-width 64 --lv 7 --smin 7 --smax 11 --tcut 7 --bd 41 --xvm 1 --nws 5 --tws 38 --ord 7 --mem-extra 1 --scale-local 0 --code-banks 5 --coll-lat 339 --coll-depth 256 --enable-ar256 --async-coll --sb-pipe 2"
/srv/opentallas-scratch/admit.sh 64 -- $T --build --workdir $R/trbuild --source-root $S --driver tools/qwen_rom_rt_token_async_w12.py -- $A --vflags=+define+OT_SB_TRACE --jobs 32 > $R/logs/trbuild.log 2>&1
st "TRACE build rc=$?"
wait; st "phase1 done"
