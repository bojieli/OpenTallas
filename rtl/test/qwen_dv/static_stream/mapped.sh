#!/bin/bash
set -euo pipefail
mkdir -p mapped
python3 - <<'PYMERGE'
from pathlib import Path
import re
files=sorted(Path('/home/ubuntu/.local/opentallas-pdk-asap7/lib/NLDM').glob('*RVT_TT*.lib'))
first=next(x for x in files if '_SEQ_' in x.name)
files=[first]+[x for x in files if x!=first]
base=first.read_text();start=re.search(r'\bcell\s*\(',base).start()
header=base[:start];cells=[];templates=[];seen=set(re.findall(r'(?:lu_table_template|power_lut_template)\s*\(([^)]+)\)',header))
for f in files:
 s=f.read_text();i=re.search(r'\bcell\s*\(',s).start();cells.append(s[i:s.rfind('}')])
 for m in re.finditer(r'(?:lu_table_template|power_lut_template)\s*\(([^)]+)\)',s[:i]):
  if m.group(1) in seen:continue
  seen.add(m.group(1));b=s.index('{',m.end());depth=1;e=b+1
  while depth:
   depth+=(s[e]=='{')-(s[e]=='}');e+=1
  templates.append(s[m.start():e])
Path('mapped/combined.lib').write_text(header+'\n'.join(templates)+'\n'+'\n'.join(cells)+'\n}\n')
PYMERGE
yosys -Q -T -p 'read_liberty -lib mapped/combined.lib; read_verilog -sv rtl/qwen_dv/qfd_dv_stream.sv rtl/qwen_dv/qfd_dv_stream_packer.sv; chparam -set STATIC_PACKER 1 qfd_dv_stream_packer; hierarchy -top qfd_dv_stream_packer; synth -top qfd_dv_stream_packer -noabc -nofsm -noshare; abc -liberty mapped/combined.lib; setattr -mod -unset keep_hierarchy; setattr -unset keep_hierarchy; flatten; write_json mapped/net.json; stat -liberty mapped/combined.lib' > mapped/yosys.log 2>&1
python3 - <<'PYAUDIT'
import json,sys,hashlib
from pathlib import Path
sys.path.insert(0,'tools/qwen_dv');from soft_cone_inventory import inventory
p=Path('mapped/net.json');raw=p.read_bytes();d=json.loads(raw)
# ABC instantiated real combinational ASAP7 cells; state remains generic DFF.
# Omit library blackbox declarations in graph analysis: these are gates, not timing cuts.
d['modules']={k:v for k,v in d['modules'].items() if not v.get('attributes',{}).get('blackbox')}
r=inventory(d,'qfd_dv_stream_packer');r['scope']='Actual ASAP7 TT ABC combinational mapping; sequential primitives remain generic. No STA/physical/native-flop qualification.';r['netlist_sha256']=hashlib.sha256(raw).hexdigest()
Path('mapped/inventory.json').write_text(json.dumps(r,indent=2)+'\n')
print(json.dumps({k:r[k] for k in ['cells','issues','register_outputs_over32','driven_nets_over32_count']},indent=2))
PYAUDIT
