#!/usr/bin/env bash
set -euo pipefail
O=${1:?freshoutput};mkdir -p "$O"
R=results/arch/s81_hostb_envelope_1021/head_producer_r1
python3 - "$R" "$O" <<'PY'
import sys,json,hashlib
from pathlib import Path
x=json.load(open(Path(sys.argv[1])/'MODEL.json'))
for z in x['files']:assert hashlib.sha256(Path(z['path']).read_bytes()).hexdigest()==z['sha256']
Path(sys.argv[2]+'/selected.f').write_text(''.join(z['path']+'\n' for z in x['files']))
PY
V=verilator;[ ! -x ~/.local/opentallas-tools/verilator-5.050/bin/verilator ]||V=~/.local/opentallas-tools/verilator-5.050/bin/verilator
"$V" --binary --timing -O1 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD --top-module tb_head_producer -f "$O/selected.f" tools/s81_dv/hostb_1021/tb_head_producer.sv -Mdir "$O/obj" --build-jobs 4 -MAKEFLAGS 'OPT_FAST=-O1 OPT_SLOW=-O0 OPT_GLOBAL=-O0' >"$O/build.log" 2>&1
python3 tools/s81_dv/hostb_1021/prepare_bench.py --vectors results/arch/s81_hostb_envelope_1021/fixture_vectors.json --out "$O/vectors" --mode 0 >"$O/prepare.log"
rc=0
for p in 0 1;do "$O/obj/Vtb_head_producer" +VECTORS="$O/vectors" +POISON=$p >"$O/bench$p.log" 2>&1 || rc=1;cat "$O/bench$p.log";done
exit "$rc"
