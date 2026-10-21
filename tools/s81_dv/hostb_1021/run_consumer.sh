#!/usr/bin/env bash
set -euo pipefail
O=${1:?fresh output};SELECTED=${2:?selectedsource root};B=${3:?sealed TOKEN vectors}
mkdir -p "$O"
python3 - "$SELECTED" "$O" <<'PY'
import json,hashlib,sys
from pathlib import Path
r=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();x=json.load(open(r/'kit.json'))
assert hashlib.sha256((r/'kit.json').read_bytes()).hexdigest()=='cbc4fbf0a7a492a61b5b06e2367953ed25a8cdb085798418d473924f8c7ad8ea'
exclude='rtl/dsrom_sys/s81_dv/slice/ot_s81sl_slice.sv';files=[]
for z in x['files']:
 if z['path']==exclude:continue # Unreachable array source known689overlay; not this L0 proof.
 p=r/'src'/z['path'];assert hashlib.sha256(p.read_bytes()).hexdigest()==z['sha256'],z['path'];files.append(p)
assert len(files)==177
inc=sorted({str(p.parent) for p in files})
(out/'selected.f').write_text(''.join('+incdir+'+p+'\n' for p in inc)+''.join(str(p)+'\n' for p in files))
(out/'selected_manifest.json').write_text(json.dumps(dict(scope='EXACT8afL0_CONSUMER_ONLY_NOT_WHOLECUT',source_inventory_sha256=hashlib.sha256((r/'kit.json').read_bytes()).hexdigest(),excluded_unreachable=exclude,files=[dict(path=str(p.relative_to(r)),sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in files]),indent=2)+'\n')
PY
V=verilator
[ ! -x ~/.local/opentallas-tools/verilator-5.050/bin/verilator ] || V=~/.local/opentallas-tools/verilator-5.050/bin/verilator
HEAD_ARGS=()
if [ "${HBE_REAL_HEAD:-0}" = 1 ];then
 python3 - "$O/head.f" <<'PYHEAD'
import json,sys,hashlib
from pathlib import Path
x=json.load(open("results/arch/s81_hostb_envelope_1021/head_producer_r1/MODEL.json"))
files=x["files"]
for z in files:assert hashlib.sha256(Path(z["path"]).read_bytes()).hexdigest()==z["sha256"]
Path(sys.argv[1]).write_text("".join(z["path"]+"\n" for z in files))
PYHEAD
 HEAD_ARGS=(+define+HBE_REAL_HEAD -f "$O/head.f")
fi
H=rtl/dsrom_sys/s81_dv/hostb
# Actual selected host subtree; no additional source/macros guessed.
"$V" --binary --timing -O1 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD --top-module tb_hostb \
 "${HEAD_ARGS[@]}" +define+HBE_REAL_CONSUMER +define+DSFD_PQ_STATIC_X2 +define+OT_COLL_NATIVE32 +define+OT_COLL_NATIVE32_OFF \
 +incdir+tools/s81_dv/hostb_1021 -Mdir "$O/obj" -f "$O/selected.f" \
 "$H/dsdv_hostb_hold.sv" "$H/dsdv_hostb_crc512.sv" "$H/dsdv_hostb_rx.sv" "$H/dsdv_hostb_tx.sv" "$H/dsdv_hostb_stage.sv" \
 "$H/dsdv_hostb_return.sv" "$H/dsdv_hostb_head.sv" "$H/dsdv_hostb_landing.sv" tools/s81_dv/hostb_1021/tb_hostb.sv \
 --build-jobs 4 -MAKEFLAGS 'OPT_FAST=-O1 OPT_SLOW=-O0 OPT_GLOBAL=-O0' >"$O/build.log" 2>&1
n=$(python3 tools/s81_dv/hostb_1021/prepare_bench.py --vectors "$B" --out "$O/v0" --mode 0)
"$O/obj/Vtb_hostb" +VECTORS="$O/v0" +STOP="$n" +MODE=0 >"$O/bench.log" 2>&1
cat "$O/bench.log"
