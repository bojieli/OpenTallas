#!/bin/bash
set -euo pipefail
out=$1
if [ -e "$out" ];then echo REFUSE_EXISTING_RUN_DIR >&2;exit 2;fi
mkdir "$out"
python3 - "$out" <<'PY'
import sys,json,hashlib,shutil
from pathlib import Path
out=Path(sys.argv[1]);model=Path('../retained_xs_model_01')
for rec in json.load(open('manifest.json'))['files']:
 assert hashlib.sha256((Path('src')/rec['path']).read_bytes()).hexdigest()==rec['sha256']
for p in model.glob('*.viamap.hex'):shutil.copyfile(p,out/p.name)
shutil.copyfile(model/'source_ctl.txt',out/'source_ctl.txt')
shutil.copyfile('quant_component_03_scorefix/expected_xq.mem',out/'expected_xq.mem')
c=json.loads((model/'contract.json').read_text());assert len(c['epochs'])==15
(out/'expected_reads.mem').write_text(''.join(f"{e['data_reads']:08x}\n" for e in c['epochs']))
PY
sha256sum tb_retained_xs_source.sv manifest.json files.f "$out/source_ctl.txt" "$out/expected_xq.mem" "$out/expected_reads.mem" > "$out/inputs.sha256"
v="$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator"
"$v" --version > "$out/verilator.version"
/usr/bin/time -v -o "$out/build_time.log" "$v" --binary --timing -O1 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD +define+DSFD_PQ_STATIC_X2 \
 --top-module tb_retained_xs_source --Mdir "$out/obj" -f files.f tb_retained_xs_source.sv --build-jobs 4 \
 -MAKEFLAGS 'OPT_FAST=-O1 OPT_SLOW=-O0 OPT_GLOBAL=-O0' > "$out/build.log" 2>&1
"$out/obj/Vtb_retained_xs_source" +DIR="$out" +OT_ROM_DIR="$out" > "$out/baseline.log" 2>&1
tail -5 "$out/baseline.log"
for mut in 4 6;do
 set +e
 "$out/obj/Vtb_retained_xs_source" +DIR="$out" +OT_ROM_DIR="$out" +MUT="$mut" > "$out/mut_${mut}.log" 2>&1
 rc=$?
 set -e
 if [ "$rc" = 0 ] || ! grep -q RETAINED_XS_SOURCE_FAIL "$out/mut_${mut}.log";then echo "MUTANT_NOT_CAUSAL $mut";exit 1;fi
 echo "RETAINED_XS_CAUSAL_MUTANT_REJECTED $mut"
done
