#!/usr/bin/env bash
# Stage the exact current control subcomponent against real released head x.
# Heavy compilation must be invoked inside ot-run, with this repository staged.
set -euo pipefail
ROOT=$(git -C "$(dirname "$(readlink -f "$0")")" rev-parse --show-toplevel)
OUT=$(realpath -m "${1:?new output directory}")
XA=$(realpath "${2:?actual xa.hex}")
XB=$(realpath "${3:?actual xb.hex}")
if [ -e "$OUT" ]; then echo "refusing existing output $OUT" >&2; exit 2; fi
mkdir -p "$OUT/rtl" "$OUT/vectors"
cp "$ROOT/rtl/dsrom_sys/s81_head/ot_s81hd_xstore_replay.sv" "$ROOT/rtl/dsrom_sys/s81_head/test/tb_head_xstore.sv" "$OUT/rtl/"
cp "$XA" "$OUT/vectors/xa.hex"; cp "$XB" "$OUT/vectors/xb.hex"
cd "$OUT"
sha256sum rtl/* vectors/* > MANIFEST.sha256
for mut in 0 1; do
 verilator --binary --timing -j 2 -Wno-fatal --top-module tb_head_xstore -GMUT="$mut" --Mdir "obj$mut" rtl/*.sv > "build$mut.log" 2>&1
 if "obj$mut/Vtb_head_xstore" +XA=vectors/xa.hex +XB=vectors/xb.hex > "run$mut.log" 2>&1; then
  test "$mut" = 0
 else
  test "$mut" = 1; grep -q 'actual source stream mismatch' "run$mut.log"
 fi
done
echo PASS-native-positive-and-mutant
