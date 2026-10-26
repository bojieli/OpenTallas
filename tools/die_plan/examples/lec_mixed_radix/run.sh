#!/bin/bash
set -euo pipefail
R=$(cd "$(dirname "$0")" && pwd)
for tag in positive mutant; do
 mkdir -p "$R/$tag/rtl"
 cp "$R/array2d.sv" "$R/$tag/rtl/array2d.sv"
 cat > "$R/$tag/config.mk" <<'CONFIG'
export DESIGN_NAME = array2d
export PLATFORM = asap7
export VERILOG_FILES = /work/rtl/array2d.sv
export SYNTH_HDL_FRONTEND = verilog
export OT_LEC_GOLD_NO_IMPLICIT_MEMORIES = 1
CONFIG
 mut=0; if [ "$tag" = mutant ]; then mut=1; fi
 docker run --rm --cpus=2 --memory=4g --memory-swap=4g -v "$R/$tag":/work -v "$R/lec.py":/lec.py:ro -w /OpenROAD-flow-scripts/flow -e MUT="$mut" openroad/orfs:asap7lock bash -lc '
 set -euo pipefail
 source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
 yosys -Q -p "read_verilog -sv /work/rtl/array2d.sv; chparam -set MUT $MUT array2d; hierarchy -top array2d; proc; opt; memory; opt; write_verilog -noattr /work/gate.v" > /work/synth.log 2>&1
 rc=0
 python3 -I /lec.py /work --netlist /work/gate.v --out /work/lec > /work/run.log 2>&1 || rc=$?
 if [ "$MUT" = 0 ]; then test "$rc" = 0; else test "$rc" = 1; fi
 '
done
python3 - "$R" <<'PY'
from pathlib import Path
import json,sys
root=Path(sys.argv[1])
for tag,verdict in [('positive','EQUIVALENT'),('mutant','NOT EQUIVALENT')]:
 p=root/tag/'lec'
 d=json.loads((p/'lec.json').read_text())
 assert d['verdict']==verdict,d
 assert d['gold_no_implicit_memories']
 assert 'slang mixed-radix keys:' in (p/'lec.log').read_text(),(tag,(p/'lec.log').read_text())
 print(tag,d['verdict'],d['counts'],d['t_total_s'])
PY
