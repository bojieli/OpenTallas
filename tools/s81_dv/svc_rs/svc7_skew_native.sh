#!/usr/bin/env bash
set -euo pipefail
O=$PWD/${1:-out_skew_native}
mkdir -p "$O"
M=physical/asap7_memory_macros_v2/ot_sram_1r1w_32x64_m1
cat > "$O/map.ys" <<'YS'
read_verilog -lib /src/physical/asap7_memory_macros_v2/ot_sram_1r1w_32x64_m1/ot_sram_1r1w_32x64_m1_bb.v
read_verilog -sv /src/rtl/hdc/v41x/ot_s81svc7_skew_sram.sv
hierarchy -check -top ot_s81svc7_skew_sram
chparam -set D 30 ot_s81svc7_skew_sram
tcl /src/physical/common_flow/ot_keep_regs.tcl
synth -top ot_s81svc7_skew_sram -flatten -noshare
dfflibmap -liberty /tmp/lib/SEQ.lib
abc -liberty /tmp/lib/SIMPLE.lib -liberty /tmp/lib/AO.lib -liberty /tmp/lib/OA.lib -liberty /tmp/lib/INVBUF.lib -liberty /tmp/lib/SEQ.lib
opt_clean
write_verilog -noattr /out/mapped.v
YS
for k in SIMPLE AO OA INVBUF SEQ; do echo "read_liberty -lib /tmp/lib/$k.lib" >> "$O/map.ys"; done
cat >> "$O/map.ys" <<'YS'
hierarchy -check -top ot_s81svc7_skew_sram
write_json /out/mapped.json
YS
docker run --rm -v "$PWD:/src:ro" -v "$O:/out" openroad/orfs:latest bash -lc '
 source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
 N=/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM
 mkdir -p /tmp/lib
 for k in SIMPLE AO OA; do zcat "$N/asap7sc7p5t_${k}_RVT_TT_nldm_211120.lib.gz" > /tmp/lib/$k.lib; done
 zcat "$N/asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib.gz" > /tmp/lib/INVBUF.lib
 cp "$N/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib" /tmp/lib/SEQ.lib
 sha256sum /tmp/lib/*.lib /src/physical/common_flow/ot_keep_regs.tcl /src/rtl/hdc/v41x/ot_s81svc7_skew_sram.sv > /out/source_identity.sha256
 yosys -V > /out/tool_identity.txt
 yosys-abc -c version >> /out/tool_identity.txt
 yosys -l /out/synth.log -s /out/map.ys
' > "$O/synth.stdout" 2>&1
python3 tools/textbook_lint.py check --netlist "$O/mapped.v" --out "$O/native32.json" --set hf_report=32 hf_max=32 hf_port_refuse=32 hf_reset_refuse=32 hf_refuse=32 > "$O/native32.log" 2>&1
python3 - "$O" <<'PYCODE'
import json,sys
from pathlib import Path
p=Path(sys.argv[1]);j=json.loads((p/'native32.json').read_text());m=json.loads((p/'mapped.json').read_text());cells=m['modules']['ot_s81svc7_skew_sram']['cells'];counts={};area=0
for c in cells.values():
 t=c['type'];counts[t]=counts.get(t,0)+1
 area+=float(m['modules'].get(t,{}).get('attributes',{}).get('area',0))
r=dict(over32=len(j.get('refuse',{}).get('high_fanout',[])),std_um2=area,flops=sum(v for k,v in counts.items() if k.startswith('DFF')),macros=sum(v for k,v in counts.items() if k.startswith('ot_sram')),depth_ps=j['metrics'].get('depth_ps'),depth_levels=j['metrics'].get('depth_levels'),scope='standalone internal ring D30, W21; enclosing chunk must supply registered pins')
(p/'summary.json').write_text(json.dumps(r,indent=2)+'\n');print(r)
assert r['over32']==0
PYCODE
