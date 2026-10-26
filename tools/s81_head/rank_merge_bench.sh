#!/usr/bin/env bash
# Actual historical controller, with independent extracted rank-merge probe.
# Invoke inside ot-run with the repository staged. Outputs are immutable.
set -euo pipefail
ROOT=$(git -C "$(dirname "$(readlink -f "$0")")" rev-parse --show-toplevel)
OUT=$(realpath -m "${1:?new output directory}")
if [ -e "$OUT" ]; then echo "refusing existing output $OUT" >&2; exit 2; fi
mkdir -p "$OUT/rtl"
cp "$ROOT/rtl/dsrom_sys/s81_head/ot_s81hd_rank_merge_hsf0.sv" "$ROOT/rtl/dsrom_sys/s81_head/test/tb_s81hd_rank_merge_miter.sv" "$OUT/rtl/"
python3 - "$ROOT" "$OUT" <<'PY'
from pathlib import Path
import json,sys,shutil
root,out=map(Path,sys.argv[1:])
m=json.loads((root/'results/arch/s81_head_source_1025/hsf0_component.json').read_text())
for p in m['files']:shutil.copyfile(root/p,out/'rtl'/Path(p).name)
PY
cd "$OUT"
sha256sum rtl/* > MANIFEST.sha256
for mut in 0 1; do
 verilator --binary --timing -j 2 -O1 -Wno-fatal --top-module tb_s81hd_ctl -GMUT="$mut" --Mdir "obj$mut" rtl/*.sv rtl/*.v > "build$mut.log" 2>&1
 if "obj$mut/Vtb_s81hd_ctl" > "run$mut.log" 2>&1; then
  test "$mut" = 0;grep -q 'PASS hd_ctl' "run$mut.log"
 else
  test "$mut" = 1;grep -q 'rank miter payload/identity/fault mismatch' "run$mut.log"
 fi
done
echo PASS-real-controller-rank-miter-mutant
