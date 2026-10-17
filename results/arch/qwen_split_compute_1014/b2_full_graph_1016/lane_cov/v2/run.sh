#!/bin/bash
# Q-B2r 10-16: lane coverage baseline v2 (Codex 1246 source snapshot + rmax ops for the mx stream), then negative
# controls on the SAME binary: wrong SEL+1, TC+1, AM+1, HL+1 must each be REJECTED (REF zero-route vs uncalibrated DUT).
set -u
cd "$(dirname "$0")"
bash tools/qwen_b2_join/run_lane_route_bench.sh build "$PWD/out" "$PWD/tb.sv" > out_build.txt 2>&1; echo "build rc=$?" >> STATUS
bash tools/qwen_b2_join/run_lane_route_bench.sh run "$PWD/out" coverage "$PWD/images" +SEL=3; echo "coverage rc=$?" >> STATUS
grep -q '^PASS b2 lane route equivalence' out/coverage.log && echo "coverage PASS" >> STATUS || echo "coverage NOT_PASS" >> STATUS
for neg in "sel4 +SEL=4" "tc1 +SEL=3 +TC=1" "am1 +SEL=3 +AM=1" "hl1 +SEL=3 +HL=1"; do
 set -- $neg; n=$1; shift
 bash tools/qwen_b2_join/run_lane_route_bench.sh run "$PWD/out" neg_$n "$PWD/images" "$@"; echo "neg_$n rc=$?" >> STATUS
done
echo DONE >> STATUS
