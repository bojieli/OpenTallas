#!/bin/bash
set -euo pipefail
E=/srv/opentallas-scratch/codex/realmem-posted-d245e5805f6e
S=/srv/opentallas-scratch/codex/realmem-posted-d245e5805f6e/src
R=/srv/opentallas-scratch/claude/realmem
cd "$S"
export QWEN_O4_GROUPS=6144 QWEN_O4_TP=4 HDC_SU_WIDTH=1024 HDC_KV_FMT=fp8
printf 'source=d245e5805f6efde99cd9d41288cc54f757b9220c posted_kv=1 build_peak64GiB prior_verilate_peak16072860KiB j24 reserve150GiB
' > "$E/jobs/MANIFEST"
/srv/opentallas-scratch/admit.sh 64 -- python3 tools/qwen_rom_rt_token_posted_w12.py --workdir "$E/build" --build-dir "$E/build" --stages "$R/stages_dummy.txt" --oracle /dev/null --pos 0 --token 0 --real-mem --posted-kv --build-only --jobs 24 > "$E/jobs/build.log" 2>&1 && rc=0 || rc=$?
echo "$rc" > "$E/jobs/build.exit"
[ "$rc" = 0 ] || exit "$rc"
run_one() {
 local p=$1 o=$2 tok=$3 n=posted_p$1
 printf 'START %s pid=%s
' "$n" "$BASHPID" >> "$E/jobs/MANIFEST"
 /srv/opentallas-scratch/admit.sh 16 -- python3 tools/qwen_rom_rt_token_posted_w12.py --workdir "$E/runs/$n" --build-dir "$E/build" --stages "$R/stages_E_L0_L2.txt" --oracle "$o/P$p" --pos "$p" --token "$tok" --real-mem --posted-kv --threads 24 --result "$E/runs/$n.json" > "$E/jobs/$n.log" 2>&1 && rc=0 || rc=$?
 echo "$rc" > "$E/jobs/$n.exit"
 printf 'END %s exit=%s
' "$n" "$rc" >> "$E/jobs/MANIFEST"
}
run_one 0 "$R/gold/tok0" 0 &
run_one 255 "$R/gold/prompt" 6280 &
run_one 1023 "$R/gold/prompt_big" 1796 &
wait
printf 'TERMINAL
' >> "$E/jobs/MANIFEST"
