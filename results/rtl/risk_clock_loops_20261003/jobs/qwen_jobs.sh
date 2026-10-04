#!/bin/bash
# Qwen3-8B ROM (W12 / O4 runtime) control-loop SS screens; run from ~/rcl-20261003/src on ot-agidock128.
# Product parameter set: tools/qwen_rom_rt_token_w12.py --tp 4 --su-width 64 --lv 7 --smin 7 --smax 11 --tcut 7
#   --code-banks 5 --mem-extra 1 --bd 41 --xvm 1 --nws 5 --tws 38 --ord 7 (G=6144 NW=18).
cd ~/rcl-20261003/src
S="python3 tools/risk_clock_loops_screen.py --resolve-from ../jobs/qwen_srcs.txt"
O=../runs/qwen
SPINE="--param W=16 --param IL=8 --param AW=24 --param NW=18 --param GT=6144 --param TG=4 --param SMIN=7 --param SMAX=11 --param TCUT=7 --param BD=41 --param XVM=1 --param NWS=5 --param TWS=38 --param ORD=7 --param MEM_EXTRA=1"
CORE="--param W=16 --param G=6144 --param AW=24 --param NW=18 --param PAW=12 --param SU_VEC=1 --param SW=64 --param LV=7 --param KV_FP8=1 --param INT8_WEIGHT=1 --param INT8_SCALE_WCS_BASE=1 --param INT8_EMBED=0 --param QWEN_FULLSHAPE=1 --param ME_STALL=0 --param ME_IDLE_GATE=1 --param SMIN=7 --param SMAX=11 --param TCUT=7 --param BD=41 --param XVM=1 --param NWS=5 --param TWS=38 --param ORD=7 --param SCALE_LOCAL=0 --param MEM_EXTRA=1"
TPS="--param ENABLE_AR256=0 --param N=4 --param NW=18 --param QWEN_FULLSHAPE=1"
FSPINE='--focus issue=(^|\.)(active|pend|pcnt|j|k|t|t_last|k_last)(\[|\$) --focus addr=(^|\.)(cur|base_k|base_t|xk|xc|oa|ot|nb|nb_t|lb)(\[|\$) --focus ctl=(^|\.)(tgo|op_split|go_d|busy|idle_r)'
FCORE='--focus fsm=(^|\.)(st|state|pc|fpc)(\[|\$) --focus issue=(^|\.)(fq_n|pend1|nx_v|d_wait_me|d_wait_su|waited|progress|d_chase_n)(\[|\$) --focus icg=u_icg'
FSU='--focus ctl=(^|\.)(active|cls|inflight|v|o|cura|curb|curc|curd)(\[|\$)'
run() { L=$1; shift; mkdir -p $O; nohup $S --work $O/$L --output $O/$L.json --label $L "$@" > $O/$L.log 2>&1 & }
run tp_seq_1111 --top ot_qwen_tp_seq_w12 --source rtl/rom/ot_qwen_tp_seq_w12.sv $TPS --period-ns 1.111 --domain 0.9GHz-serial --focus 'fsm=^(st|seg)\[' --focus 'txq=^(q_n|q_w|q_r|rd_k|rd_v|tx_k|rx_k)\['
run tp_seq_ar256_833 --top ot_qwen_tp_seq_w12 --source rtl/rom/ot_qwen_tp_seq_w12.sv --param ENABLE_AR256=1 --param N=4 --param NW=18 --param QWEN_FULLSHAPE=1 --period-ns 0.833 --domain 0.9GHz-serial --focus 'fsm=^(st|seg)\[' --focus 'txq=^(q_n|q_w|q_r|rd_k|rd_v|tx_k|rx_k)\['
run spine_fi0_833 --top ot_qwen_me_spine_w12 $SPINE --param ACC_LAT=5 --param TREE_LAT=3 --param MUL_LAT=5 --param FAST_ISSUE=0 --param KV_PREP=0 --period-ns 0.833 --domain 1.2GHz-streaming $FSPINE
run spine_fi1_833 --top ot_qwen_me_spine_w12 $SPINE --param ACC_LAT=7 --param TREE_LAT=7 --param MUL_LAT=6 --param FAST_ISSUE=1 --param KV_PREP=3 --period-ns 0.833 --domain 1.2GHz-streaming $FSPINE
run spine_fi0_1111 --top ot_qwen_me_spine_w12 $SPINE --param ACC_LAT=5 --param TREE_LAT=3 --param MUL_LAT=5 --param FAST_ISSUE=0 --param KV_PREP=0 --period-ns 1.111 --domain 1.2GHz-streaming $FSPINE
run core_bb_1111 --top ot_qwen_rom_core $CORE --param ACC_LAT=5 --param TREE_LAT=3 --param MUL_LAT=5 --param FAST_ISSUE=0 --param KV_PREP=0 --blackbox ot_qwen_me_spine_w12 --blackbox ot_hdc_vstream_rt --blackbox ot_hdc_stream --period-ns 1.111 --domain 0.9GHz-serial $FCORE
run core_bb_833 --top ot_qwen_rom_core $CORE --param ACC_LAT=5 --param TREE_LAT=3 --param MUL_LAT=5 --param FAST_ISSUE=0 --param KV_PREP=0 --blackbox ot_qwen_me_spine_w12 --blackbox ot_hdc_vstream_rt --blackbox ot_hdc_stream --period-ns 0.833 --domain 0.9GHz-serial $FCORE
run vstream_sw64_1111 --top ot_hdc_vstream_rt --param SW=64 --param LV=7 --param WR=16 --param AW=24 --param NW=18 --param KV_FP8=1 --period-ns 1.111 --domain 0.9GHz-serial $FSU
run vreduce_sw64_1111 --top ot_hdc_vreduce --param SW=64 --param LV=7 --param AW=24 --period-ns 1.111 --domain 0.9GHz-serial --focus 'held=(^|\.)(held|held_v)'
run oneshot_die_d32_833 --top ot_rom_oneshot_die --param N=4 --param RANK=0 --param LANES=16 --param TAGW=32 --param DEPTH=32 --period-ns 0.833 --domain 1.2GHz-streaming --focus 'credit=(^|\.)(cr|cnt|wp|rp|g_busy|g_cnt|inflight)(\[|\$)'
run oneshot_die_d256_833 --top ot_rom_oneshot_die --param N=4 --param RANK=0 --param LANES=16 --param TAGW=32 --param DEPTH=256 --period-ns 0.833 --domain 1.2GHz-streaming --focus 'credit=(^|\.)(cr|cnt|wp|rp|g_busy|g_cnt|inflight)(\[|\$)'
wait
