#!/usr/bin/env bash
# run_inj_copy.sh OUT [pos|skew]: positive age-1 proof, or the rd-bypass mutant (must FAIL).
set -euo pipefail
HERE=$(cd -- "$(dirname -- "$0")" && pwd)
OUT=$(realpath -m "${1:?output directory}"); MODE=${2:-pos}; mkdir -p "$OUT"
D=(); case "$MODE" in pos) ;; skew) D=(-DOT_COLL_INJCOPY_MUT_SKEW);; *) exit 2;; esac
sha256sum "$HERE/ot_hgi_coll_inj_copy.sv" "$HERE/tb_hgi_coll_inj_copy.sv" "$0" > "$OUT/sources.sha256"
iverilog -g2012 "${D[@]}" -s tb_hgi_coll_inj_copy -o "$OUT/proof.vvp" "$HERE/tb_hgi_coll_inj_copy.sv" "$HERE/ot_hgi_coll_inj_copy.sv" > "$OUT/build.log" 2>&1
sha256sum "$OUT/proof.vvp" > "$OUT/compiled.sha256"
set +e; vvp "$OUT/proof.vvp" > "$OUT/run.log" 2>&1; rc=$?; set -e
cat "$OUT/run.log"; exit "$rc"
