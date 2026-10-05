#!/bin/bash
# VPOS core delta and multi-position KV service screens (same tool / corner as screens.sh).
R=/srv/opentallas-scratch/claude/qwen-dspark-closure
cd $R/src
S="python3 tools/risk_clock_loops_screen.py"
O=$R/runs
run() { G=12; L=$2; shift 2; mkdir -p $O; nohup /srv/opentallas-scratch/admit.sh $G -- $S --work $O/$L --output $O/$L.json --label $L "$@" > $O/$L.log 2>&1 & }
CORE="--param W=16 --param G=6144 --param AW=24 --param NW=18 --param PAW=12 --param SU_VEC=1 --param SW=8 --param LV=7 --param KV_FP8=1 --param INT8_WEIGHT=1 --param INT8_SCALE_WCS_BASE=1 --param INT8_EMBED=0 --param QWEN_FULLSHAPE=1 --param HID=4096 --param HALF=64 --param HD=128 --param EMB_CODE_LANES=64 --param EMB_ADDR_BASE=0 --param KV_HBM=1 --param KV_VEC_WRITE_BRIDGE=1 --param ME_STALL=1 --param ME_IDLE_GATE=1 --param SMIN=7 --param SMAX=11 --param TCUT=7 --param BD=41 --param XVM=1 --param NWS=5 --param TWS=38 --param ORD=7 --param SCALE_LOCAL=0 --param MEM_EXTRA=1 --param ACC_LAT=5 --param TREE_LAT=3 --param MUL_LAT=5 --param FAST_ISSUE=0 --param KV_PREP=0"
FCORE='--focus fsm=(^|\.)(st|state|pc|fpc)(\[|\$) --focus issue=(^|\.)(fq_n|pend1|nx_v|d_wait_me|d_wait_su|waited|progress|d_chase_n)(\[|\$) --focus dynp=(^|\.)dynp\[ --focus dyn=(^|\.)dyn\[ --focus decode=(^|\.)(me_nout|me_tiles|me_k|me_wbase|me_xbase|me_obase|su_nin|a_base|b_base|c_base|d_base)\['
BB="--blackbox ot_qwen_me_spine_w12 --blackbox ot_hdc_vstream_rt --blackbox ot_hdc_stream"
for V in 1 0; do
run 60 core_sw8_vpos${V}_0833 --top ot_qwen_rom_core --resolve-from qwen_srcs_dsc_scr.txt $CORE --param VPOS=$V $BB --include rtl/hdc --period-ns 0.833 --domain 1.2GHz-streaming $FCORE
done
KV="--param G=64 --param TG=4 --param AW=24 --param NW=18 --param NPC=8 --param NRD=16 --param NWR=64 --param LKA=4 --param FILL_LAT=1 --param KV_IDEAL=0"
FKV='--focus commit=^(committed_len|committed_v|NPr|P|fault|fault_code)\[ --focus tail=^(tk_data|tk_lm|tk_dirty|tk_st|tk_fill)\[ --focus vasm=^(va_data|va_mask|va_st)\[ --focus wb=^(h_req_v|h_req_we|h_req_addr|h_req_wdata|h_req_tag|w_sec|w_valid)\['
