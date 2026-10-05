#!/bin/bash
# HBM_STREAM REAL_MEM campaign: build (WBW=$1) then P0/P255/P1023, detached.
set -uo pipefail
W=${1:-1}
E=/srv/opentallas-scratch/claude/hbmstream-realmem
S=$E/src
R=/srv/opentallas-scratch/claude/realmem
B=$E/build_w$W
mkdir -p $E/jobs $E/runs
cd "$S"
export QWEN_O4_GROUPS=6144 QWEN_O4_TP=4 HDC_SU_WIDTH=1024 HDC_KV_FMT=fp8
echo "$(date -u +%FT%TZ) START build_w$W src=$(cat $S/SOURCE_SHA)" >> $E/jobs/MANIFEST
/srv/opentallas-scratch/admit.sh 64 -- python3 tools/qwen_rom_rt_token_stream_w12.py --workdir "$B" --build-dir "$B" --stages "$R/stages_dummy.txt" --oracle /dev/null --pos 0 --token 0 --real-mem --hbm-stream --wbw $W --build-only --jobs 24 > "$E/jobs/build_w$W.log" 2>&1; rc=$?
echo "$(date -u +%FT%TZ) END build_w$W exit=$rc" >> $E/jobs/MANIFEST
[ "$rc" = 0 ] || exit "$rc"
run_one() {
 local p=$1 o=$2 tok=$3 n=stream_w${W}_p$1
 echo "$(date -u +%FT%TZ) START $n" >> $E/jobs/MANIFEST
 /srv/opentallas-scratch/admit.sh 16 -- python3 tools/qwen_rom_rt_token_stream_w12.py --workdir "$E/runs/$n" --build-dir "$B" --stages "$R/stages_E_L0_L2.txt" --oracle "$o/P$p" --pos "$p" --token "$tok" --real-mem --hbm-stream --wbw $W --threads 24 --result "$E/runs/$n.json" > "$E/jobs/$n.log" 2>&1; local rc=$?
 echo "$(date -u +%FT%TZ) END $n exit=$rc" >> $E/jobs/MANIFEST
}
run_one 0 "$R/gold/tok0" 0 &
run_one 255 "$R/gold/prompt" 6280 &
run_one 1023 "$R/gold/prompt_big" 1796 &
wait
echo "$(date -u +%FT%TZ) TERMINAL w$W" >> $E/jobs/MANIFEST
