#!/bin/bash
set -euo pipefail
out=$1
if [ -e "$out" ];then echo REFUSE_EXISTING_RUN_DIR >&2;exit 2;fi
mkdir "$out"
python3 - "$out" <<'PY'
import sys,json,hashlib
from pathlib import Path
sys.path.insert(0,'../tools/s81_static_control')
from pq_calendar import viamap
p=Path(sys.argv[1]);
for record in json.load(open('manifest.json'))['files']:
 assert hashlib.sha256((Path('src')/record['path']).read_bytes()).hexdigest()==record['sha256']
program=json.load(open('../qnorm_program_model_v1/program.json'));gold=json.load(open('../qnorm_program_model_v1/quantized_scoreboard.json'))
window=(1<<6)|(2<<16)|((1<<120)<<26)
(p/'source_ctl.txt').write_text(f'-8 {window:047x}\n'+''.join(f"{x['xr_ctl_pin_edge']} {x['payload']}\n" for x in program))
(p/'expected_xq.mem').write_text(''.join(x['payload532']+'\n' for x in gold))
# No GO is issued in this source-component stage. Actual XS gather storage is live.
zeros=viamap([0]*4096)
for n in ['pq_calendar_action','pq_calendar_time','pq_phase0','pq_stream0','pq_stream1','pq_stream2','pq_stream3']:
 (p/(n+'.viamap.hex')).write_text(zeros)
PY
sha256sum tb_qnorm_source.sv manifest.json files.f "$out/source_ctl.txt" "$out/expected_xq.mem" > "$out/inputs.sha256"
v="$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator"
"$v" --version > "$out/verilator.version"
/usr/bin/time -v -o "$out/build_time.log" "$v" --binary --timing -O1 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD +define+DSFD_PQ_STATIC_X2 \
 --top-module tb_qnorm_source --Mdir "$out/obj" -f files.f tb_qnorm_source.sv --build-jobs 4 \
 -MAKEFLAGS 'OPT_FAST=-O1 OPT_SLOW=-O0 OPT_GLOBAL=-O0' > "$out/build.log" 2>&1
"$out/obj/Vtb_qnorm_source" +DIR="$out" +OT_ROM_DIR="$out" > "$out/baseline.log" 2>&1
cat "$out/baseline.log" | tail -8
