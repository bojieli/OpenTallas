#!/bin/bash
set -euo pipefail
ulimit -c 0
mkdir -p out
python3 - <<'PY'
import pathlib,hashlib,json
pathlib.Path('out/source.json').write_text(json.dumps({p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [*pathlib.Path('.').glob('*.sv'),*pathlib.Path('.').glob('*.v')]},indent=2)+'\n')
PY
verilator --binary --timing -j 4 -Wno-fatal --top-module tb_hgi_hc_prefetch_direct_controller_static --Mdir out/obj -o sim *.sv *.v >out/compile.log 2>&1
for p in 1080 1400;do
 set +e
 out/obj/sim +IMAGE=../inputs/all24rows.hex +PERIOD=$p >out/period$p.log 2>&1
 rc=$?
 set -e
 cat out/period$p.log
 echo "ACTUAL_CONTROLLER_PERIOD=$p EXIT=$rc"
done
