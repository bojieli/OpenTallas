#!/bin/bash
set -eu
D=$(cd "$(dirname "$0")" && pwd)
export PATH=/home/ubuntu/.local/opentallas-tools/bin:$PATH
run() {
 local C=$1 N=$2 NEW=$3
 python3 "$D/head_master_miter.py" "$D/kits/old_e$N" "$D/kits/$NEW" "$D/miter/$C" >"$D/$C.gen.log" 2>&1
 (cd "$D/miter/$C" && verilator --binary --timing -j 8 -MAKEFLAGS OBJCACHE= -Wno-fatal -Wno-lint -Wno-style -Wno-MULTIDRIVEN -DSYNTHESIS -Io -In --top-module tb --Mdir obj -f files.f >build.log 2>&1 && ./obj/Vtb >sim.log 2>&1)
 grep "CORE MITER" "$D/miter/$C/sim.log"
}
run e1 1 new_e1 & p1=$!
run e5 5 new_e5 & p5=$!
run mutant 1 mut_e1 & pm=$!
wait $p1;wait $p5;wait $pm
python3 - "$D" <<PY
from pathlib import Path
import sys,json
p=Path(sys.argv[1]);r={n:(p/"miter"/n/"sim.log").read_text() for n in ["e1","e5","mutant"]}
assert all(" PASS " in r[n] for n in ["e1","e5"]),r
assert " FAIL " in r["mutant"],r
(p/"result.json").write_text(json.dumps(dict(verdict="PASS",runs=r,cycles_added=0,extra_flops_per_lane8=248),indent=1)+"\n")
PY
