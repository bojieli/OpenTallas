#!/usr/bin/env bash
# Retain the existing native512/1024 default load ABI after opt-in indexing.
set -euo pipefail
ROOT=${OT_SOURCE_ROOT:-$(git -C "$(dirname "$(readlink -f "$0")")" rev-parse --show-toplevel)}
OUT=$(realpath -m "${1:?new output directory}")
if [ -e "$OUT" ]; then echo "refusing existing output $OUT" >&2; exit 2; fi
mkdir -p "$OUT/rtl"
cp "$ROOT/rtl/dsrom_sys/s81_head/ot_s81hd_xstore_replay.sv" "$ROOT/rtl/dsrom_sys/s81_head/test/tb_s81hd_xstore_wide.sv" "$OUT/rtl/"
cp "$ROOT/results/arch/s81_head_source_1025/vectors/xa.hex" "$ROOT/results/arch/s81_head_source_1025/vectors/xb.hex" "$OUT/"
cd "$OUT"
sha256sum rtl/* xa.hex xb.hex > MANIFEST.sha256
for indexed in 0 1; do
 verilator --binary --timing -j 2 -O1 -Wno-fatal --top-module tb_s81hd_xstore_wide -GINDEXED="$indexed" --Mdir "obj$indexed" rtl/*.sv > "build$indexed.log" 2>&1
 "obj$indexed/Vtb_s81hd_xstore_wide" +XA=xa.hex +XB=xb.hex > "run$indexed.log" 2>&1
 grep -q 'XSTORE_WIDE PASS native_pairs=16538' "run$indexed.log"
 cat "run$indexed.log"
done
