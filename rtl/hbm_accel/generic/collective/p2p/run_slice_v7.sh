#!/usr/bin/env bash
set -euo pipefail
HERE=$(cd -- "$(dirname -- "$0")" && pwd)
OUT=$(realpath -m "${1:?output directory}"); MODE=${2:-pos};mkdir -p "$OUT"
D=()
case "$MODE" in pos) ;; delay) D=(-DOT_COLL_SLICE_MUT_DELAY);; select) D=(-DOT_COLL_SLICE_MUT_SELECT);; *) exit 2;; esac
sha256sum "$HERE/ot_hgi_coll_slice_v7.sv" "$HERE/tb_hgi_coll_slice_v7.sv" "$0" > "$OUT/sources.sha256"
iverilog -g2012 "${D[@]}" -s tb_hgi_coll_slice_v7 -o "$OUT/proof.vvp" "$HERE/tb_hgi_coll_slice_v7.sv" "$HERE/ot_hgi_coll_slice_v7.sv" > "$OUT/build.log" 2>&1
sha256sum "$OUT/proof.vvp" > "$OUT/compiled.sha256"
set +e
vvp "$OUT/proof.vvp" > "$OUT/run.log" 2>&1
rc=$?
set -e
cat "$OUT/run.log"
exit "$rc"
