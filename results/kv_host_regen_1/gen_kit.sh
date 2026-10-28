#!/bin/bash
# KV-HOST-KITS-2 10-27: kit for one qkd_hr_* core whose face proof is 0/1/0 and plan pins match (host_qm recipe).
# usage: gen_kit.sh MODULE RUNHOST [PLAN_JSON]
#   copies RUNHOST:$FP_ROOT/MODULE here first (RUNHOST intel2 = already local).
#   KV-KITS-3: PLAN_JSON optional, default pd/hm_r26q5c39.json (unchanged).
#   COLLECT-2315 10-27 (opt-in, defaults unchanged):
#     FP_ROOT=<dir>         face-proof root (default $R/fp), e.g. $R/fp_coretx for the DIE-KV-3 retimed core_tx proof
#     RESET_PORTS=P1,P2     passed as gen_core_kit_kv.py --reset-ports (needs claude/die-kv-3-coretx-1027 70c0af856f+)
set -eu
M=$1; H=$2
R=/srv/opentallas-scratch2/claude/kv-host-regen-1
PLAN=${3:-$R/pd/hm_r26q5c39.json}
FP=${FP_ROOT:-$R/fp}
W=/srv/opentallas-scratch2/claude/wt/kv-host-regen-1
EXTRA=()
[ -n "${RESET_PORTS:-}" ] && EXTRA+=(--reset-ports "$RESET_PORTS")
if [ "$H" != intel2 ]; then rsync -a -e "ssh -o ControlPath=none" $H:$FP/$M/ $FP/$M/; fi
[ "$(tr -s " \n" " " < $FP/$M/eq_rc.txt)" = "post rc=0 mut rc=1 emitted_v rc=0 " ] || { echo PROOF_NOT_PASS; exit 2; }
cd $W
python3 physical/die_plan/qwen_kvsys/cores/harden/gen_core_kit_kv.py --core-json results/kv_host_regen_1/rtl/$M/${M}_core.json \
  --plan $PLAN --out $R/kits --kit-rtl $R/kit_rtl_b3 --util 0.6 --sigmax M5 \
  --hr-face-ports $FP/$M --plan-inst host__$M "${EXTRA[@]}" > $R/logs/gen_${M#qkd_hr_}.log 2>&1
tail -2 $R/logs/gen_${M#qkd_hr_}.log
