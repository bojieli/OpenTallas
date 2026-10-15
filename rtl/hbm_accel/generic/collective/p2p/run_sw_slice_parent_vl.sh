#!/usr/bin/env bash
# Verilator form of run_sw_slice_parent.sh (production KMAX=2048 TKM inside the q3 parent is impractical in Icarus).
# MUT0 must PASS; MUT1..4 must FAIL. usage: run_sw_slice_parent_vl.sh OUT
set -euo pipefail
HERE=$(cd -- "$(dirname -- "$0")" && pwd)
ROOT=${HCOLL_ROOT:-$(cd "$HERE/../../../../.." && pwd)}
OUT=$(realpath -m "${1:?output directory}"); mkdir -p "$OUT"
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
eval "$(sed -n '/^p=\$ROOT/,/ot_sram_1r1w_64x512_m1_r2c2.v")$/p' "$HERE/run_sw_slice_parent.sh")"
sha256sum "${src[@]}" > "$OUT/sources.sha256"
rc_all=0
for m in ${MUTS:-0 1 2 3 4}; do
  cd "$ROOT"
  "$V" --binary --timing --hierarchical -j "${JOBS:-16}" -O1 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-WIDTHCONCAT \
    --top-module tb_hgi_coll_sw_slice_parent -GMUT=$m -Mdir "$OUT/obj$m" "$p/qtkm_hier.vlt" "${src[@]}" > "$OUT/m$m.build.log" 2>&1 \
    || { tail -30 "$OUT/m$m.build.log"; exit 2; }
  set +e; "$OUT/obj$m/Vtb_hgi_coll_sw_slice_parent" > "$OUT/m$m.log" 2>&1; rc=$?; set -e
  grep -E 'HCOLL_SW_SLICE_PARENT|Fatal|fault|mismatch' "$OUT/m$m.log" | head -3
  if [ $m = 0 ]; then { [ $rc = 0 ] && grep -q 'HCOLL_SW_SLICE_PARENT PASS' "$OUT/m$m.log"; } || rc_all=1
  else { [ $rc != 0 ] && ! grep -q 'HCOLL_SW_SLICE_PARENT PASS' "$OUT/m$m.log"; } && echo "MUT$m rejected" || { echo "MUT$m SURVIVED"; rc_all=1; }; fi
  [ $m = 0 ] || rm -rf "$OUT/obj$m"
done
[ $rc_all = 0 ] && echo "HCOLL_SW_SLICE_PARENT GATE PASS" || { echo "HCOLL_SW_SLICE_PARENT GATE FAIL"; exit 1; }
