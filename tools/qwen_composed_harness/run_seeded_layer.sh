#!/usr/bin/env bash
# runseed.sh <name> <layer 0..35|head> [plan_override]  -- seeded per-layer run (OT_SEED_X = oracle layer-input X)
set -uo pipefail
S=/srv/opentallas-scratch/claude/qwen-wholetoken-1014; E=/srv/opentallas-scratch/codex/qwen-host-embedding-1014/embedding
B=/srv/opentallas-scratch/codex/qwen-native-fulltoken-1014/banks/oracle
name=$1; k=$2; out=$S/runs/$name; BIN=${BIN:-bin_v5}
odir(){ if [ $1 -lt 2 ]; then echo $B/cold_token0_first2/layer$1; else echo $B/cold_token0_continue2_to35/layer$1; fi; }
if [ "$k" = head ]; then plan=$S/plans/seeded/layer35.plan; export OT_SEED_X=$S/plans/seeded/head_input_x.hex OT_SEED_HEAD=1
else plan=${3:-$S/plans/seeded/layer$k.plan}; export OT_SEED_X=$(odir $k)/vm_x_fp32.hex; fi
mkdir -p $S/runs; [[ ! -e $out ]] || { echo "exists $out"; exit 3; }
mkdir -p $out; sha256sum $S/$BIN/whole_token $plan $OT_SEED_X > $out/inputs.sha256; env | grep ^OT_ > $out/env.txt
/usr/bin/time -v $S/$BIN/whole_token $plan $E/embedding_program.hex $E/vectors $S/plans/head/image $S/plans/head/program \
  $S/deps/qwen-full-layer-sequence-1014/libnative59.so $out/actual 50994 1100755280 > $out/run.log 2> $out/run.err
rc=$?; echo $rc > $out/exit_status.txt; grep -E "FAIL|PASS|layers executed|Maximum resident|Elapsed" $out/run.err $out/run.log | tail -6; exit $rc
