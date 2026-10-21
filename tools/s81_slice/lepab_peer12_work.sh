#!/usr/bin/env bash
set -u
P=${1:?out-prefix}
pids=()
for side in w e; do
 python3 tools/s81_slice/lepab_regional_native.py "$P-native-$side" "physical/ref_tile/dscoll_lane_${side}_s12g/spec.json" > "$P-native-$side.log" 2>&1 & pids+=("$!")
done
for m in 0 5 6 7 8; do
 bash tools/s81_slice/coll_reach12.sh "$P-m$m" "$m" > "$P-m$m.log" 2>&1 & pids+=("$!")
done
for p in "${pids[@]}"; do wait "$p" || true; done
rc=0
for side in w e; do
 if grep -q '^NATIVE_SYNTH_CENSUS_PASS' "$P-native-$side.log";then echo "PEER_NATIVE_PASS $side";else echo "PEER_NATIVE_FAIL $side";rc=1;fi
done
if grep -q '^COLL_REACH7 PASS' "$P-m0/run.log";then echo PEER_PROTOCOL_PASS;else echo PEER_PROTOCOL_FAIL;rc=1;fi
for m in 5 6 7 8; do
 if grep -Eq '(^COLL_REACH7 FAIL errors=|COLL FIFO group state differs|COLL WRL )' "$P-m$m/run.log";then echo "PEER_MUTANT_CAUGHT $m";else echo "PEER_MUTANT_NOT_CAUGHT $m";rc=1;fi
done
exit "$rc"
