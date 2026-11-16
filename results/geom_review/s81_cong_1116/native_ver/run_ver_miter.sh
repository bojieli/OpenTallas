#!/bin/bash
set -e
export PATH=$HOME/.local/opentallas-tools/bin:$PATH
cd /srv/opentallas-scratch2/claude/fable-fix-s81-cong/native_ver_1116
verilator --version > verilator.version
verilator --cc --exe --build -j 4 --top-module ver_top -Wno-fatal -Wno-DECLFILENAME --Mdir obj native_cst.sv ver_native_miter.sv ver_miter.cpp > build.log 2>&1
./obj/Vver_top 0 > positive.log 2>&1
set +e
./obj/Vver_top 1 > mutant_valid.log 2>&1
r1=$?
./obj/Vver_top 2 > mutant_reset.log 2>&1
r2=$?
set -e
[ "$r1" -ne 0 ] && grep -q 'MISMATCH valid' mutant_valid.log
[ "$r2" -ne 0 ] && grep -q 'MISMATCH valid warm_\|MISMATCH valid held_' mutant_reset.log
python3 -I - <<'PY'
import json,hashlib
from pathlib import Path
p=Path('.')
r=dict(verdict='PASS',positive=p.joinpath('positive.log').read_text().strip(),mutant_valid=p.joinpath('mutant_valid.log').read_text().strip(),mutant_reset=p.joinpath('mutant_reset.log').read_text().strip(),source_manifest=json.load(open('ver_source_manifest.json')),verilator=p.joinpath('verilator.version').read_text().strip(),files={str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in map(Path,['native_cst.sv','ver_native_miter.sv','ver_miter.cpp'])})
json.dump(r,open('result.json','w'),indent=2);print(r['positive']);print('NEGATIVE_CONTROLS caught valid-stage-skew and missing-reset-clear')
PY
