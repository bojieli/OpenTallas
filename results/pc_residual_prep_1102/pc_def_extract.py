import json,re
from pathlib import Path
O=Path('/srv/opentallas-scratch2/claude/codex-pc-residual-prep-0510');q=json.loads((O/'native_query.json').read_text());nets=set(q['nets']);need=set(q['selected_cells'])|{r['instance'] for v in q['nets'].values() for r in v};defs={};netdefs={};act=None;buf=[]
with (Path(q['source'])/'run/results/asap7/hc_qkd_kvs_pc__397_44x362_88/base/6_final.def').open() as f:
 for l in f:
  line=l.lstrip()
  if line.startswith('- '):
   name=line.split()[1].lstrip('\\');act=('cell' if name in need else 'net' if name in nets else None,name);buf=[l] if act[0] else []
  elif act and act[0]:buf.append(l)
  if act and act[0] and ';' in l:
   (defs if act[0]=='cell' else netdefs)[act[1]]=''.join(buf);act=None;buf=[]
pos={}
for n,s in defs.items():
 m=re.search(r'\+ (?:PLACED|FIXED|FIRM) \(\s*(-?\d+)\s+(-?\d+)\s*\)\s+(\w+)',s)
 if m:pos[n]={'x':int(m[1])/q['DEF_units'],'y':int(m[2])/q['DEF_units'],'orient':m[3]}
assert len(pos)>=len(q['selected_cells'])
q['positions']=pos;(O/'native_query_with_DEF.json').write_text(json.dumps(q,indent=2)+'\n');(O/'selected_components.def').write_text('\n'.join(defs.values()));(O/'selected_nets.def').write_text('\n'.join(netdefs.values()));print(len(pos),'positions',len(netdefs),'native routes')
