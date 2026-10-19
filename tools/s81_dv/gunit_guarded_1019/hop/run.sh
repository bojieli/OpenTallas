#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../../../.."
R=$PWD
D=$R/tools/s81_dv/gunit_guarded_1019
O=$R/out_hop
mkdir -p "$O"
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
"$V" --version | tee "$O/verilator.version"
python3 "$D/selector.py" --root "$R" --top dsdv_gunit_l5_fs_guarded_1019 > "$O/selected_sources.txt"
python3 - "$R" <<'PY'
import sys,json,hashlib
from pathlib import Path
r=Path(sys.argv[1]);rows=json.loads((r/'results/rtl/s81_gunit_guarded_package_1019/hop_sources.json').read_text())
for row in rows:
 p=r/row['path'];assert hashlib.sha256(p.read_bytes()).hexdigest()==row['sha256'],p
(r/'out_hop/sources.txt').write_text('\n'.join(str(r/x['path']) for x in rows)+'\n')
PY
mapfile -t SOURCES < "$O/sources.txt"
"$V" --binary --timing -j 8 -O2 -Wno-fatal -Wno-WIDTH -Wno-lint -Wno-style -Wno-UNOPTFLAT -Wno-TIMESCALEMOD +define+DSFD_HOST_C_STATIC --top-module tb_gu_layer --Mdir "$O/obj" -o sim "${SOURCES[@]}" -CFLAGS -O1 > "$O/build.log" 2>&1
python3 "$D/hop/sort_calendar.py" "$D/hop/kit0/prog/host_boot.memh" "$D/hop/host_boot_sorted.memh" "$O/sort_receipt.json"
python3 "$D/hop/run_cases.py" "$R" --sorted
