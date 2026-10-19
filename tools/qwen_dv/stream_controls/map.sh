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
yosys -Q -T -p 'read_liberty -lib mapped/combined.lib; read_verilog -sv rtl/qwen_dv/qfd_dv_stream.sv rtl/qwen_dv/qfd_dv_stream_packer.sv; chparam -set STATIC_PACKER 1 qfd_dv_stream_packer; hierarchy -top qfd_dv_stream_packer; synth -top qfd_dv_stream_packer -noabc -nofsm -noshare; abc -liberty mapped/combined.lib; setattr -mod -unset keep_hierarchy; setattr -unset keep_hierarchy; flatten; write_json mapped/net.json; write_verilog -noattr mapped/source.v; stat -liberty mapped/combined.lib' > mapped/yosys.log 2>&1
