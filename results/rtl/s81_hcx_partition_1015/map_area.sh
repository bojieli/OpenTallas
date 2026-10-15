#!/usr/bin/env bash
set -euo pipefail
cd /work
python3 - <<'PY'
import gzip,pathlib,re
p=pathlib.Path('/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM')
libs=[]
for kind,version in [('AO','211120.lib.gz'),('OA','211120.lib.gz'),('INVBUF','220122.lib.gz'),('SIMPLE','211120.lib.gz'),('SEQ','220123.lib')]:
 f=p/f'asap7sc7p5t_{kind}_RVT_TT_nldm_{version}'
 libs.append(gzip.open(f,'rt').read() if f.suffix=='.gz' else f.read_text())
head=libs[0][:re.search(r'\bcell\s*\(',libs[0]).start()]
cells=[]
for s in libs:
 for match in re.finditer(r'\bcell\s*\(',s):
  a=s.index('{',match.start()); depth=1;i=a+1
  while depth:
   depth+=(s[i]=='{')-(s[i]=='}');i+=1
  cells.append(s[match.start():i])
pathlib.Path('area_tt.lib').write_text(head+'\n'.join(cells)+'\n}\n')
PY
cat > map_area.ys <<'YS'
read_json hierarchy.json
synth -top ot_s81_hcx_projection_partition
read_liberty -lib area_tt.lib
dfflibmap -liberty area_tt.lib
abc -liberty area_tt.lib
clean
write_json mapped_area.json
stat -liberty area_tt.lib
YS
/OpenROAD-flow-scripts/tools/install/yosys/bin/yosys -Q -T -s map_area.ys > map_area.log 2>&1
