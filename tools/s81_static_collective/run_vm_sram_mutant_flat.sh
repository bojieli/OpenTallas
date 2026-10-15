#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
python3 - <<'PY'
from pathlib import Path
p=Path('dsfd_vm_static_xio.sv')
s=p.read_text();needle='w_d[512*k +: 512] = f_collective[551*k+31 +: 512];'
assert needle in s
s=s.replace(needle,"w_d[512*k +: 512] = f_collective[551*k+31 +: 512] ^ ((f_collective[551*k+1 +: 14] >= 14'd4096) ? 512'b1 : 512'b0);")
Path('mutant_vm_xio.sv').write_text(s)
PY
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
FILES=(); for f in *.sv *.v; do [ "$f" = dsfd_vm_static_xio.sv ] || FILES+=("$f"); done
"$V" --binary --timing -O1 -Wno-fatal -j 8 -MAKEFLAGS 'OPT_FAST=-O0 OPT_SLOW=-O0 OPT_GLOBAL=-O0' --top-module tb_s81_static_fmt1_vm_sram --Mdir obj_mutant -o tb "${FILES[@]}" > build_mutant.log 2>&1 || { tail -30 build_mutant.log; exit 2; }
set +e
./obj_mutant/tb +N=28 +MUT=0 +PLAN=plan.mem +BEATS=beats.mem > mutant.log 2>&1
rc=$?
set -e
if [ "$rc" = 0 ] || ! grep -q 'SRAM readback data' mutant.log; then cat mutant.log; exit 1; fi
cat mutant.log
echo "PASS actual VM write payload mutant rejected rc=$rc"
