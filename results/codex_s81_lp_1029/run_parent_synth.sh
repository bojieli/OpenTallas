#!/bin/bash
set -euo pipefail
b=$1
mem=${2:-48}
# Every source below is an immutable snapshot of the exact selected closure.
python3 - "$b" <<'PY'
import json,sys
from pathlib import Path
b=Path(sys.argv[1]);d=json.load(open(b/'sources.json'));names=d['macros'];fs=(b/'sources.f').read_text().splitlines()
physical_sources={v['source'] for v in names.values()}
physical_files={'/out/'+v['snapshot'] for v in d['files'] if v['path'] in physical_sources}
ys=[]
for f in fs:
    # Real SRAM macros are actual physical views: load their exact ports as library cells,
    # never synthesize their simulation/repair-array implementation into flop logic.
    ys.append('read_verilog '+('-lib ' if f in physical_files else '')+'-sv -DSYNTHESIS '+' '.join('-D'+v for v in d['defines'])+' '+f)
for m in names:ys.append('blackbox '+m)
for k,v in d['params'].items():ys.append('chparam -set '+k+' '+str(v)+' '+d['top'])
ys+=['hierarchy -check -top '+d['top'],'synth -top '+d['top']+' -flatten','tee -o /out/generic_stat.json stat -json','dfflibmap -liberty /out/lib/seq.lib','abc -D 833 -liberty /out/lib/all.lib','opt_clean','tee -o /out/mapped_stat.json stat -json -liberty /out/lib/all.lib','tee -o /out/mapped_stat.txt stat -liberty /out/lib/all.lib','write_verilog -noattr /out/parent_mapped.v']
(b/'synth.ys').write_text('\n'.join(ys)+'\n')
PY
docker run --rm --name s81-lp-parent-synth1029 --cpus=8 --memory="${mem}g" --memory-swap="${mem}g" -v "$b":/out -w /out -e HUID="$(id -u)" -e HGID="$(id -g)" openroad/orfs:asap7lock bash -lc '
set -euo pipefail
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
mkdir -p /out/lib
L=/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM
if [ -f "$L/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib.gz" ]; then zcat "$L/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib.gz" > /out/lib/seq.lib; else cp "$L/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib" /out/lib/seq.lib; fi
for f in AO_RVT_TT_nldm_211120 INVBUF_RVT_TT_nldm_220122 OA_RVT_TT_nldm_211120 SIMPLE_RVT_TT_nldm_211120; do zcat "$L/asap7sc7p5t_$f.lib.gz"; done > /out/lib/comb.lib
python3 - <<"PY"
import re
from pathlib import Path
b=Path("/out/lib");txt=(b/"comb.lib").read_text()+(b/"seq.lib").read_text();libs=re.split(r"(?m)^library\s*\(",txt);head="library ("+libs[1].split("cell (",1)[0];cells=[]
for l in libs[1:]:
 body="cell ("+l.split("cell (",1)[1];body=body[:body.rstrip().rfind("}")];cells.append(body)
(b/"all.lib").write_text(head+"\n".join(cells)+"\n}\n")
PY
yosys -Q -T -l /out/synth.log -s /out/synth.ys > /out/yosys.stdout 2>&1
chown -R "$HUID:$HGID" /out
'
