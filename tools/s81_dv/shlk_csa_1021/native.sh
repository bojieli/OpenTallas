#!/bin/bash
set -euo pipefail
ROOT=$PWD;O=$(cd ../out;pwd);LIB=$(cd ../lib;pwd)
for k in baseline candidate;do
 mkdir -p "$O/$k";D='';test "$k" != baseline || D=-DBASELINE
 cat > "$O/$k/map.ys" <<YS
read_verilog -defer -sv -DSYNTHESIS $D /src/rtl/hdc/ingest/ot_s81_ing_stream_n32.sv /src/tools/s81_dv/shlk_csa_1021/sum_gate.sv
hierarchy -check -top sum_gate
read_liberty -lib /techlib/SEQ.lib
read_liberty -lib /techlib/SIMPLE.lib
read_liberty -lib /techlib/AO.lib
read_liberty -lib /techlib/OA.lib
read_liberty -lib /techlib/INVBUF.lib
synth -top sum_gate -flatten -noshare
dfflibmap -liberty /techlib/SEQ.lib
abc -liberty /techlib/SEQ.lib -liberty /techlib/SIMPLE.lib -liberty /techlib/AO.lib -liberty /techlib/OA.lib -liberty /techlib/INVBUF.lib
opt_clean
tee -o /out/stat.txt stat -liberty /techlib/SEQ.lib -liberty /techlib/SIMPLE.lib -liberty /techlib/AO.lib -liberty /techlib/OA.lib -liberty /techlib/INVBUF.lib
write_verilog -noattr /out/flat.v
YS
 docker run --rm -v "$ROOT:/src:ro" -v "$O/$k:/out" -v "$LIB:/techlib:ro" openroad/orfs:latest bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1;yosys -l /out/synth.log -s /out/map.ys' > "$O/$k/build.log" 2>&1
 args=();for f in "$LIB"/*.lib;do args+=(--liberty "$f");done
 python3 tools/ref_tile/native_census.py --netlist "$O/$k/flat.v" --top sum_gate --out "$O/$k/census.json" "${args[@]}" > "$O/$k/census.log" 2>&1
 python3 tools/textbook_lint.py check --netlist "$O/$k/flat.v" --top sum_gate --out "$O/$k/depth.json" > "$O/$k/depth.log" 2>&1
 python3 - "$k" "$O/$k" <<'PY2'
import json,sys
from pathlib import Path
p=Path(sys.argv[2]);d=json.loads((p/'depth.json').read_text());c=json.loads((p/'census.json').read_text());print('SUM_MAP',sys.argv[1],d['metrics'].get('depth_ps'),d['metrics'].get('depth_levels'),c['status'],c['max_dynamic_loads'])
PY2
done
