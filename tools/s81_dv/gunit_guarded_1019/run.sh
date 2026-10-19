#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../../.."
R=$PWD
D=$R/tools/s81_dv/gunit_guarded_1019
O=$R/out
mkdir -p "$O"
V=/opt/verilator-5.050/bin/verilator
if [ ! -x "$V" ]; then V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator; fi
"$V" --version | tee "$O/verilator.version"
"$V" --version | grep -E -q 'Verilator 5\.050' || exit 2
python3 "$D/selector.py" --root "$R" --top dsdv_gunit_l5_fs_guarded_1019 > "$O/selected_sources.txt"
python3 "$D/test_selection.py" | tee "$O/selection.log"
python3 "$D/source_age.py" "$O"
python3 "$D/vectors.py" "$R/vectors.hex"
python3 - "$R" <<'PY'
import sys,json,hashlib
from pathlib import Path
r=Path(sys.argv[1]);rows=json.loads((r/'results/rtl/s81_gunit_guarded_package_1019/bench_sources.json').read_text())
for row in rows:
 p=r/row['path'];assert hashlib.sha256(p.read_bytes()).hexdigest()==row['sha256'],p
(r/'out/bench_sources.txt').write_text('\n'.join(str(r/x['path']) for x in rows)+'\n')
PY
mapfile -t SOURCES < "$O/bench_sources.txt"
for shape in main private mut8 mut10; do
  base=0;mut=0
  if [ "$shape" = main ];then base=1;fi
  if [ "$shape" = mut8 ];then mut=8;fi
  if [ "$shape" = mut10 ];then mut=10;fi
  mkdir -p "$O/$shape"
  "$V" --binary --timing -I"$O" --top-module tb -Wno-fatal -Wno-WIDTH -Wno-UNOPTFLAT -Wno-TIMESCALEMOD -Wno-PINMISSING -DOT_MEM_NO_INIT --x-initial unique -DBASELINE="$base" -DMUT="$mut" -j 8 --Mdir "$O/$shape/obj" -o sim "${SOURCES[@]}" "$D/tb.sv" -CFLAGS -O1 > "$O/$shape/build.log" 2>&1
  set +e
  "$O/$shape/obj/sim" +verilator+seed+17 +verilator+rand+reset+2 > "$O/$shape/run.log" 2>&1
  rc=$?
  set -e
  printf '%s\n' "$rc" > "$O/$shape/run.rc"
  if [ "$mut" = 0 ];then
    grep -E '^GUARDED_NUMERIC_PASS' "$O/$shape/run.log"
    [ "$rc" = 0 ] || exit 3
  else
    [ "$rc" != 0 ] || exit 4
    grep -E 'GUARDED_NUMERIC_FAIL' "$O/$shape/run.log"
  fi
  if [ "$shape" = private ];then
    for delta in -256 -1 1;do
      set +e
      "$O/$shape/obj/sim" +AGE_DELTA="$delta" +verilator+seed+17 +verilator+rand+reset+2 > "$O/$shape/age_$delta.log" 2>&1
      rc=$?
      set -e
      [ "$rc" != 0 ] || exit 5
      grep -E 'GUARDED_AGE_FAIL' "$O/$shape/age_$delta.log"
    done
  fi
 done
printf '%s\n' 'GUARDED_PACKAGE_BENCH_PASS'
