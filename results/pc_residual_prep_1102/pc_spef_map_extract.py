import json,re
from pathlib import Path
O=Path('/srv/opentallas-scratch2/claude/codex-pc-residual-prep-0510');q=json.loads((O/'native_query_with_DEF.json').read_text());want=set(q['nets'])|set(q['positions']);ids={};header=[]
with (Path(q['source'])/'run/results/asap7/hc_qkd_kvs_pc__397_44x362_88/base/6_final.spef').open() as f:
 for l in f:
  if l.startswith('*D_NET'):break
  m=re.match(r'^(\*\d+)\s+(\S+)\s*$',l)
  if m:
   n=m[2].replace('\\','')
   if n in want:ids[m[1]]=n
  elif len(header)<30:header.append(l.rstrip())
(O/'spef_name_map.json').write_text(json.dumps({'ids':ids,'header':header},indent=2)+'\n')
