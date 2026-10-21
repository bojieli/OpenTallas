#!/bin/bash
set -euo pipefail
ROOT=$PWD;O=$(mkdir -p ../out_reset_asr_native;cd ../out_reset_asr_native;pwd);LIB=$(cd ../lib;pwd)
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
S=rtl/dsrom_sys/s81_dv/svc_rs/ot_s81svc_reset9_n32.sv;K=rtl/hdc/v41x/ot_hdc_v41x_kreg.sv
for k in baseline candidate;do
 mkdir -p "$O/$k";D='';test "$k" != baseline || D=-DBASELINE
 cat > "$O/$k/map.ys" <<YS
read_verilog -sv -DSYNTHESIS $D /src/$S /src/$K /src/tools/s81_dv/svc_rs/reset_profile/reset_asr_gate.sv
hierarchy -check -top reset_asr_gate
read_liberty -lib /techlib/SEQ.lib
read_liberty -lib /techlib/SIMPLE.lib
read_liberty -lib /techlib/AO.lib
read_liberty -lib /techlib/OA.lib
read_liberty -lib /techlib/INVBUF.lib
tcl /src/physical/common_flow/ot_keep_regs.tcl
synth -top reset_asr_gate -flatten -noshare
dfflibmap -liberty /techlib/SEQ.lib
abc -liberty /techlib/SEQ.lib -liberty /techlib/SIMPLE.lib -liberty /techlib/AO.lib -liberty /techlib/OA.lib -liberty /techlib/INVBUF.lib
setattr -mod -unset keep_hierarchy
flatten
opt_clean
tee -o /out/stat.txt stat -liberty /techlib/SEQ.lib
write_verilog -noattr /out/flat.v
YS
 docker run --rm -v "$ROOT:/src:ro" -v "$O/$k:/out" -v "$LIB:/techlib:ro" openroad/orfs:latest bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1;yosys -l /out/synth.log -s /out/map.ys' > "$O/$k/build.log" 2>&1
 args=();for f in "$LIB"/*.lib;do args+=(--liberty "$f");done
 python3 tools/ref_tile/native_census.py --netlist "$O/$k/flat.v" --top reset_asr_gate --out "$O/$k/census.json" "${args[@]}" > "$O/$k/census.log" 2>&1 || true
 python3 - "$k" "$O/$k/census.json" <<'PY'
import json,sys
r=json.load(open(sys.argv[2]));print('RESET9_NATIVE',sys.argv[1],r['status'],r['max_dynamic_loads'],len(r['violations']),len(r['role_errors']))
assert (r['status']=='PASS')==(sys.argv[1]=='candidate')
PY
done
