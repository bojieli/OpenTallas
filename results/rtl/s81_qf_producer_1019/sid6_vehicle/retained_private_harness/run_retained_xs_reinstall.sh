#!/bin/bash
set -euo pipefail
out=$1
if [ -e "$out" ];then echo REFUSE_EXISTING_RUN_DIR >&2;exit 2;fi
mkdir "$out"
python3 - "$out" <<'PY'
import sys,json,hashlib,shutil
from pathlib import Path
out=Path(sys.argv[1]);old=Path('retained_component_01')
for rec in json.load(open('manifest.json'))['files']:
 assert hashlib.sha256((Path('src')/rec['path']).read_bytes()).hexdigest()==rec['sha256']
for p in old.glob('*.viamap.hex'):shutil.copyfile(p,out/p.name)
for n in ['expected_xq.mem','expected_reads.mem']:shutil.copyfile(old/n,out/n)
raw=json.loads(Path('../qnorm_program_model_v2/program.json').read_text())
commands={x['xr_ctl_pin_edge']:int(x['payload'],16) for x in raw}
window=(1<<6)|(2<<16)|((1<<120)<<26);commands[-8]=window
for line in (old/'source_ctl.txt').read_text().splitlines():
 t,v=line.split();t=int(t)+1400;assert t not in commands;commands[t]=int(v,16)
(out/'source_ctl.txt').write_text(''.join(f'{t} {v:047x}\n' for t,v in sorted(commands.items())))
(out/'programme.json').write_text(json.dumps(dict(scope='Private reset + genuine raw reinstallation',reset_edges=[1300,1310],
 second_source_offset=1400,raw_writes=640,QB=40,gathers=40,expected_macro_writes=80,
 source_payload='original raw1280 FP32 written twice; expected quantized words scoreboard only',
 same_ROMs_as='retained_component_01',original_deadline_unchanged=True),indent=2)+'\n')
PY
sha256sum tb_retained_xs_reinstall.sv manifest.json files.f "$out/source_ctl.txt" "$out/expected_xq.mem" "$out/expected_reads.mem" > "$out/inputs.sha256"
v="$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator"
"$v" --version > "$out/verilator.version"
/usr/bin/time -v -o "$out/build_time.log" "$v" --binary --timing -O1 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD +define+DSFD_PQ_STATIC_X2 \
 --top-module tb_retained_xs_reinstall --Mdir "$out/obj" -f files.f tb_retained_xs_reinstall.sv --build-jobs 4 \
 -MAKEFLAGS 'OPT_FAST=-O1 OPT_SLOW=-O0 OPT_GLOBAL=-O0' > "$out/build.log" 2>&1
"$out/obj/Vtb_retained_xs_reinstall" +DIR="$out" +OT_ROM_DIR="$out" +REINSTALL=1 > "$out/baseline.log" 2>&1
tail -5 "$out/baseline.log"
set +e
"$out/obj/Vtb_retained_xs_reinstall" +DIR="$out" +OT_ROM_DIR="$out" +REINSTALL=1 +MUT=4 > "$out/mut_4.log" 2>&1
rc=$?
set -e
if [ "$rc" = 0 ] || ! grep -q RETAINED_XS_SOURCE_FAIL "$out/mut_4.log";then echo MUTANT_NOT_CAUSAL;exit 1;fi
echo REINSTALL_LATE_GW_CAUSAL_REJECTED
