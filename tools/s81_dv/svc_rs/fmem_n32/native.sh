#!/bin/bash
set -euo pipefail
ROOT=$PWD
mkdir -p ../out_fmem_native_r2
OUT=$(cd ../out_fmem_native_r2 && pwd)
LIB=/srv/opentallas-scratch/claude/elemsvc-g4-1021/out_sram/map/lib
for case in baseline candidate;do
 mkdir -p "$OUT/$case"
 flag='';test "$case" != baseline || flag='-DFMEM_BASELINE'
 cat > "$OUT/$case/map.ys" <<YS
read_verilog -lib /src/physical/asap7_memory_macros/ot_sram_1r1w_32x128_m1/ot_sram_1r1w_32x128_m1_bb.v
read_verilog -defer -sv -DSYNTHESIS -DOT_SVC_FMEM_N32 $flag /src/tools/s81_dv/svc_rs/fmem_n32/fmem_actual.sv /src/tools/s81_dv/svc_rs/fmem_n32/fmem_ref.sv /src/tools/s81_dv/svc_rs/fmem_n32/fmem_gate.sv /src/rtl/hdc/v41x/ot_hdc_v41x_kreg.sv
hierarchy -check -top fmem_gate
read_liberty -lib /techlib/SEQ.lib
read_liberty -lib /techlib/SIMPLE.lib
read_liberty -lib /techlib/AO.lib
read_liberty -lib /techlib/OA.lib
read_liberty -lib /techlib/INVBUF.lib
tcl /src/physical/common_flow/ot_keep_regs.tcl
synth -top fmem_gate -flatten -noshare
dfflibmap -liberty /techlib/SEQ.lib
abc -liberty /techlib/SEQ.lib -liberty /techlib/SIMPLE.lib -liberty /techlib/AO.lib -liberty /techlib/OA.lib -liberty /techlib/INVBUF.lib
opt_clean
setattr -mod -unset keep_hierarchy
flatten
opt_clean
tee -o /out/stat.txt stat -liberty /techlib/SEQ.lib -liberty /techlib/SIMPLE.lib -liberty /techlib/AO.lib -liberty /techlib/OA.lib -liberty /techlib/INVBUF.lib
write_verilog -noattr /out/flat.v
YS
 docker run --rm -v "$ROOT:/src:ro" -v "$OUT/$case:/out" -v "$LIB:/techlib:ro" openroad/orfs:latest bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; yosys -l /out/synth.log -s /out/map.ys' > "$OUT/$case/build.log" 2>&1
 args=();for f in "$LIB"/*.lib;do args+=(--liberty "$f");done
 python3 tools/ref_tile/native_census.py --netlist "$OUT/$case/flat.v" --top fmem_gate --out "$OUT/$case/census.json" "${args[@]}" > "$OUT/$case/census.log" 2>&1 || true
 python3 - "$case" "$OUT/$case/census.json" <<'PY'
import json,sys
r=json.load(open(sys.argv[2]));print('FMEM_NATIVE',sys.argv[1],r['status'],r['max_dynamic_loads'],len(r['violations']),len(r.get('role_errors',[])))
if sys.argv[1]=='candidate':assert r['status']=='PASS' and not r['violations'] and not r.get('role_errors')
else:assert r['status']=='FAIL'
PY
done
