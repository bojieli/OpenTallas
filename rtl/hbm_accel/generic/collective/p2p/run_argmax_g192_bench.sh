#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/../../../../.." && pwd)
OUT=$(realpath -m "${1:?out}");mkdir -p "$OUT";cd "$ROOT"
P=rtl/hbm_accel/generic/collective/p2p
for tc in 96:0 192:0 192:1; do
 IFS=: read -r g mut <<< "$tc"
 tag=g${g}_ranktrunc${mut}
 set +e
 bash "$P/run_argmax_static_bench.sh" "$OUT/$tag" -GG=$g -GRANK_TRUNC=$mut > "$OUT/$tag.log" 2>&1
 rc=$?
 set -e
 if [ "$mut" = 0 ]; then
  [ "$rc" = 0 ] && grep -q 'ARGMAX_STATIC PASS' "$OUT/$tag/run.log"
 else
  [ "$rc" != 0 ] && grep -q 'ARGMAX unexpected protocol fault' "$OUT/$tag/run.log"
 fi
 echo "COLL_ARGMAX_G192 G=$g ranktrunc=$mut checked expected outcome"
done
sha256sum "$P/run_argmax_g192_bench.sh" "$P/tb_hgi_coll_argmax_static.sv" "$P/ot_hgi_coll_argmax_static.sv" rtl/hbm_accel/generic/collective/ot_hgi_coll_amerge.sv > "$OUT/sources.sha256"
echo COLL_ARGMAX_G192_GATE_PASS
