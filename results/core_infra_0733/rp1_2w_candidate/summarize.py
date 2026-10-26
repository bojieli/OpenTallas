import json,sys,collections,re
from pathlib import Path
p=Path(sys.argv[1]);out={}
for c in ('TT','FF'):
 groups=collections.defaultdict(list);vals=[]
 for line in (p/f'native_{c}.tsv').read_text().splitlines():
  _,v,net=line.split('\t');v=float(v);groups[net].append(v);vals.append(v)
 means=[sum(v)/len(v) for v in groups.values()];text=(p/f'native_{c}.log').read_text()
 out[c]=dict(sinks=len(vals),min_ps=min(vals),mean_ps=sum(vals)/len(vals),max_ps=max(vals),leaf_mean_window_ps=max(means)-min(means),leaves=len(groups),max_leaf_load=max(map(len,groups.values())),min_leaf_load=min(map(len,groups.values())),grt_lines=[l for l in text.splitlines() if 'overflow' in l.lower()][-5:])
out['qualification']='UNCHECKED; native TT/FF GRT RC diagnostics only, no detail route/signoff;2W Cx1.1 model assumption before build'
(p/'native_result.json').write_text(json.dumps(out,indent=1));print(json.dumps(out))
