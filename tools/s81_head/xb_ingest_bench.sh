#!/usr/bin/env bash
# Actual historical controller, independent extracted RESULT landing, live full user identity.
# Invoke inside ot-run with the repository staged. Outputs are immutable.
set -euo pipefail
ROOT=${OT_SOURCE_ROOT:-$(git -C "$(dirname "$(readlink -f "$0")")" rev-parse --show-toplevel)}
OUT=$(realpath -m "${1:?new output directory}")
if [ -e "$OUT" ]; then echo "refusing existing output $OUT" >&2; exit 2; fi
mkdir -p "$OUT/rtl"
cp "$ROOT/rtl/dsrom_sys/s81_head/ot_s81hd_xb_ingest.sv" "$ROOT/rtl/dsrom_sys/s81_head/ot_s81hd_xstore_replay.sv" "$ROOT/rtl/dsrom_sys/s81_head/test/tb_s81hd_xb_ingest_miter.sv" "$OUT/rtl/"
python3 - "$ROOT" "$OUT" <<'PY'
from pathlib import Path
import json,sys,shutil
root,out=map(Path,sys.argv[1:])
m=json.loads((root/'results/arch/s81_head_source_1025/hsf0_component.json').read_text())
for p in m['files']:shutil.copyfile(root/p,out/'rtl'/Path(p).name)
PY
cd "$OUT"
sha256sum rtl/* > MANIFEST.sha256
for mut in 0 1 2 3; do
 verilator --binary --timing -j 2 -O1 -Wno-fatal --top-module tb_s81hd_ctl -GMUT="$mut" --Mdir "obj$mut" rtl/*.sv rtl/*.v > "build$mut.log" 2>&1
 if "obj$mut/Vtb_s81hd_ctl" > "run$mut.log" 2>&1; then
  test "$mut" = 0;grep -q 'PASS hd_ctl' "run$mut.log"
 else
  case "$mut" in
   1) grep -q 'XB indexed payload mismatch' "run$mut.log";;
   2) grep -q 'XB identity mismatch' "run$mut.log";;
   3) grep -q 'XB job retired before token identity' "run$mut.log";;
   *) exit 3;;
  esac
 fi
done
verilator --binary --timing -j 2 -O1 -Wno-fatal --top-module tb_s81hd_ctl -GMUT=0 -GTAGGED=0 --Mdir obj_untagged rtl/*.sv rtl/*.v > build_untagged.log 2>&1
obj_untagged/Vtb_s81hd_ctl > run_untagged.log 2>&1
grep -q 'PASS hd_ctl' run_untagged.log
echo PASS-real-controller-XB-ingest-index-identity-retirement-mutants
