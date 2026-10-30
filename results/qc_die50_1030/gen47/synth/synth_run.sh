#!/bin/bash
set -euo pipefail
# Run inside the standard ASAP7 ORFS image; /work is this own run directory.
cd /work
python3 - <<'PY'
from pathlib import Path
import gzip,re
root=Path('/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM')
libs=[next(root.glob(f'asap7sc7p5t_{g}_RVT_TT*')) for g in ['AO','INVBUF','OA','SEQ','SIMPLE']]
texts=[gzip.open(p,'rt').read() if p.suffix=='.gz' else p.read_text() for p in libs]
cells=[];header=None;names=set()
for txt in texts:
 starts=list(re.finditer(r'\bcell\s*\(\s*([^)]*)\s*\)\s*\{',txt))
 if header is None:header=txt[:starts[0].start()]
 for m in starts:
  name=m[1].strip('" ');assert name not in names;names.add(name)
  n=1;i=m.end()
  while n:
   n+=(txt[i]=='{')-(txt[i]=='}');i+=1
  cells.append(txt[m.start():i])
Path('stdcells.lib').write_text(header+'\n'.join(cells)+'\n}\n')
Path('lib_sources.txt').write_text('\n'.join(map(str,libs))+'\n')
PY
yosys -Q -l yosys.log synth.ys
python3 inventory_guarded.py provider_mapped.json start_stages.json /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7sc7p5t_28_R_1x_220121a.lef --out provider_cells.json
