from pathlib import Path
from collections import Counter,defaultdict
import json,re
b=Path('/srv/opentallas-scratch2/claude/codex-sc-cap-0336');p=b/'1_synth_odb.v';counts=Counter();seq=Counter();groups={k:Counter() for k in [1,2,3,4]};sg={k:Counter() for k in groups};patterns=Counter();n=0
r=re.compile(r'^\s+(\w*ASAP7\w*)\s+(\\?\S+)\s*\(')
for line in p.open():
 m=r.match(line)
 if not m:continue
 master,name=m.groups();name=name.lstrip('\\');n+=1;counts[master]+=1;parts=re.split('[/.]',name);is_seq=bool(re.search(r'DFF|SDF|DHL|DLL|LQN',master))
 for k in groups:
  g='.'.join(parts[:k]);groups[k][g]+=1
  if is_seq:sg[k][g]+=1
 if is_seq:seq[master]+=1;patterns[re.sub(r'\\?\[[^\]]+\\?\]','[*]',name).split('$_')[0]]+=1
out=dict(schema='codex.sc.native_census.v1',source=str(p),total_std=n,total_seq=sum(seq.values()),total_comb=n-sum(seq.values()),masters=counts,seq_masters=seq,hierarchy={str(k):[dict(prefix=g,std=c,seq=sg[k][g],comb=c-sg[k][g]) for g,c in groups[k].most_common(40)] for k in groups},state_stems=patterns.most_common(80))
(b/'native_census.json').write_text(json.dumps(out,indent=2)+'\n');print('TOTAL',n,'SEQ',sum(seq.values()),'COMB',n-sum(seq.values()))
for k in [2,3,4]:print('HIER',k,out['hierarchy'][str(k)][:14])
