#!/usr/bin/env bash
set -euo pipefail
G=$(cd "${1:?graph output directory}" && pwd)
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)
cd "$ROOT"
O=$G/retention
mkdir -p "$O"
docker run --rm -v "$ROOT:/src:ro" -v "$G:/graph:ro" -v "$O:/out" openroad/orfs:latest bash -lc '
    source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
    N=/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM
    mkdir -p /tmp/lib
    for k in SIMPLE AO OA; do zcat "$N/asap7sc7p5t_${k}_RVT_TT_nldm_211120.lib.gz" > /tmp/lib/$k.lib; done
    zcat "$N/asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib.gz" > /tmp/lib/INVBUF.lib
    cp "$N/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib" /tmp/lib/SEQ.lib
    for k in SIMPLE AO OA INVBUF SEQ; do echo "read_liberty -lib /tmp/lib/$k.lib"; done > /out/keep.ys
    cat >> /out/keep.ys <<EOF
read_verilog /graph/native.v
hierarchy -check -top ot_s81svc7_bmul_native
tcl /src/physical/common_flow/ot_keep_regs.tcl
synth -top ot_s81svc7_bmul_native -flatten -noshare
abc -liberty /tmp/lib/SIMPLE.lib -liberty /tmp/lib/AO.lib -liberty /tmp/lib/OA.lib -liberty /tmp/lib/INVBUF.lib -liberty /tmp/lib/SEQ.lib
opt_clean
write_verilog -noattr -blackboxes /out/retained_all.v
write_verilog -noattr /out/retained.v
write_json /out/retained.json
EOF
    yosys -l /out/synth.log -s /out/keep.ys
' > "$O/synth.stdout" 2>&1
python3 tools/textbook_lint.py check --netlist "$O/retained.v" --out "$O/native32.json" \
    --set hf_report=32 hf_max=32 hf_port_refuse=32 hf_reset_refuse=32 hf_refuse=32 > "$O/native32.log" 2>&1
python3 - "$G" <<'PY'
import json,sys
from pathlib import Path
g=Path(sys.argv[1]);a=json.loads((g/'mapped.json').read_text());b=json.loads((g/'retention/retained.json').read_text())
def stats(j,top):
    cells=j['modules'][top]['cells'];area=0.;ffs=0;count=0
    for c in cells.values():
        if c['type']=='$scopeinfo':continue
        area+=float(j['modules'][c['type']]['attributes']['area'])
        ffs+=c['type'].startswith('DFF');count+=1
    return dict(std_um2=area,flops=ffs,cells=count)
x=stats(a,'ot_s81svc7_bmul_graph_input');y=stats(b,'ot_s81svc7_bmul_native')
n=json.loads((g/'retention/native32.json').read_text())
result=dict(baseline=x,retained=y,delta_std_um2=y['std_um2']-x['std_um2'],
            over32=len(n.get('refuse',{}).get('high_fanout',[])),
            depth_ps=n['metrics'].get('depth_ps'),depth_levels=n['metrics'].get('depth_levels'),
            scope='mapped census/depth estimate; no routed closure',latency_edges=7)
(g/'retention/summary.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))
assert result['over32']==0
PY
