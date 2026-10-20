#!/bin/bash
set -euo pipefail
out=$1
if [ -e "$out" ];then echo REFUSE_EXISTING_RUN_DIR >&2;exit 2;fi
mkdir "$out"
python3 - "$out" <<'PY'
from pathlib import Path
import sys,shutil,json,hashlib
out=Path(sys.argv[1]);old=Path('retained_component_01')
for p in old.glob('*.viamap.hex'):shutil.copyfile(p,out/p.name)
for n in ['source_ctl.txt','expected_xq.mem','expected_reads.mem']:shutil.copyfile(old/n,out/n)
for r in json.load(open('manifest.json'))['files']:
 assert hashlib.sha256((Path('src')/r['path']).read_bytes()).hexdigest()==r['sha256']
for r in json.load(open('input_marker_sources/sources.json')):
 assert hashlib.sha256((Path('input_marker_sources')/Path(r['original_path']).name).read_bytes()).hexdigest()==r['sha256']
fl=Path('files.f').read_text()
for p in sorted(Path('input_marker_sources').glob('*.sv')):fl+=str(p)+'\n'
(out/'files.f').write_text(fl)
PY
sha256sum tb_input_source_ledger.sv input_marker_sources/* "$out/source_ctl.txt" "$out/expected_xq.mem" "$out/expected_reads.mem" > "$out/inputs.sha256"
v="$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator"
"$v" --version > "$out/verilator.version"
/usr/bin/time -v -o "$out/build_time.log" "$v" --binary --timing -O1 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD +define+DSFD_PQ_STATIC_X2 \
 --top-module tb_input_source_ledger --Mdir "$out/obj" -f "$out/files.f" tb_input_source_ledger.sv --build-jobs 4 \
 -MAKEFLAGS 'OPT_FAST=-O1 OPT_SLOW=-O0 OPT_GLOBAL=-O0' > "$out/build.log" 2>&1
set +e
"$out/obj/Vtb_input_source_ledger" +DIR="$out" +OT_ROM_DIR="$out" > "$out/baseline.log" 2>&1
rc=$?
set -e
tail -12 "$out/baseline.log"
if [ "$rc" != 0 ];then exit "$rc";fi
for mut in 7 8 9 10 11;do
 set +e
 "$out/obj/Vtb_input_source_ledger" +DIR="$out" +OT_ROM_DIR="$out" +MUT="$mut" > "$out/mut_${mut}.log" 2>&1
 mrc=$?
 set -e
 if [ "$mrc" = 0 ] || ! grep -q INPUT_SOURCE_LEDGER_FAIL "$out/mut_${mut}.log";then echo "INPUT_MUTANT_SURVIVED $mut";exit 1;fi
 echo "INPUT_CAUSAL_MUTANT_REJECTED $mut"
done
