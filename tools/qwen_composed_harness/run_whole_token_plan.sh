#!/usr/bin/env bash
# runplan.sh <name> <plan> [expected_token expected_value]
set -uo pipefail
S=/srv/opentallas-scratch/claude/qwen-wholetoken-1014; E=/srv/opentallas-scratch/codex/qwen-host-embedding-1014/embedding
name=$1; plan=$2; tok=${3:-50994}; val=${4:-1100755280}; out=$S/runs/$name
mkdir -p $S/runs; [[ ! -e $out ]] || { echo "exists $out"; exit 3; }
mkdir -p $out; sha256sum $S/bin_v1/whole_token $plan > $out/inputs.sha256
/usr/bin/time -v $S/bin_v1/whole_token $plan $E/embedding_program.hex $E/vectors $S/plans/head/image $S/plans/head/program \
  $S/deps/qwen-full-layer-sequence-1014/libnative59.so $out/actual $tok $val > $out/run.log 2> $out/run.err
rc=$?; echo $rc > $out/exit_status.txt; grep -E "FAIL|PASS|layers executed|Maximum resident|Elapsed" $out/run.err $out/run.log | tail -6; exit $rc
