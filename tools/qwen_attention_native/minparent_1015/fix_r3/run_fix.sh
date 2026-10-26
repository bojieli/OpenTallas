#!/bin/bash
# run_fix.sh <name> <parent0|parent1> <mode> [cal] [ctx] [vec]
set -uo pipefail
me=/srv/opentallas-scratch/claude/q-attn-1015/fix; stage=/srv/opentallas-scratch/codex/q-attn-minparent-1015
name=$1; par=$2; mode=$3; cal=${4:-13891388138805aa07bc076c06af032705aa03200352}; ctx=${5:-8192}; vec=${6:-$stage/vectors/full8192}
out=$me/runs/$name; mkdir -p $out
bin=${BDIR:-$me/b_rl21}/$par/Vtb_qwen_tp8_attention_native_service
sha256sum $bin > $out/binary.sha256
/usr/bin/time -v stdbuf -oL $bin +VEC=$vec +CTX=$ctx +MODE=$mode +CAL=$cal > $out/native.log 2> $out/native.time
echo $? > $out/exit
grep -E '^\{' $out/native.log > $out/verdict.json || true
