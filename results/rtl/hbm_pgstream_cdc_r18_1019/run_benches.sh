#!/bin/bash
set -uo pipefail
cd "$(dirname "$0")/src"
verilator --version
verilator --version | grep -q '5.050' || exit 2
rc=0
for entry in 'legacy 0 1 10 7 0' 'm0 0 1 18 15 1' 'rr10 0 1 10 7 1' 'qid0 0 0 18 15 1' 'm13 13 1 18 15 1' 'm14 14 1 18 15 1' 'm12 12 1 18 15 1' 'm3 3 1 18 15 1' 'm2 2 1 18 15 1' 'm8 8 1 18 15 1'; do
 read -r name mut qid rr wr freg <<< "$entry"
 bash tools/hbm_static/su_pg_stream_split_vl_run.sh "../out/$name" "$mut" 1500 "$qid" "$rr" "$wr" "$freg" > "../$name.log" 2>&1
 brc=$?
 if [ "$brc" -ne 0 ]; then echo "BUILD_OR_RUN_ERROR $name $brc"; rc=1
 elif [ "$mut" -eq 0 ]; then grep -q 'PG_STREAM_SPLIT PASS checks=' "../$name.log" || rc=1
 else grep -q 'PG_STREAM_SPLIT FAIL errors=' "../$name.log" || rc=1; fi
 tail -n 8 "../$name.log"
done
echo "BENCH_MATRIX_RC=$rc"
exit "$rc"
