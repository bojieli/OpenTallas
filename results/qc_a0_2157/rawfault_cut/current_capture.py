import re,json,collections,functools
from pathlib import Path
r=Path('/srv/opentallas-scratch/claude/codex-qc-a0-2157');lib=json.load(open(r/'native_flat.json'))['modules'];s=(r/'current_leaf_mapped.v').read_text();cells={};cons=collections.defaultdict(list)
for m in re.finditer(r'^  (\w+)\s+(\\?\S+)\s+\(\n(.*?)\n  \);',s,re.M|re.S):
 t,n,b=m.groups();ps={p:e.strip().replace('\\','')for p,e in re.findall(r'\.(\w+)\((.*?)\)',b,re.S)};cells[n.lstrip('\\')]=(t,ps)
 for p,e in ps.items():
  if lib[t]['ports'][p]['direction']=='input':cons[e].append(n.lstrip('\\'))
@functools.lru_cache(None)
def cap(bit):
 q=set()
 for n in cons[bit]:
  t,ps=cells[n]
  if t.startswith('DFF'):q.add(n)
  else:
   for p,e in ps.items():
    if lib[t]['ports'][p]['direction']=='output':q|=cap(e)
 return frozenset(q)
ports=['v_d','first_d']+['split_d['+str(i)+']'for i in range(4)]+['w_d['+str(i)+']'for i in range(256)]+['x_d['+str(i)+']'for i in range(128)]
mp={p:list(cap(p))for p in ports};print(collections.Counter(len(x)for x in mp.values()));assert all(len(v)==1 for v in mp.values());insts={x.split('\t')[0].replace('\\',''):x.split('\t')[0]for x in(r/'placed_inst.tsv').read_text().splitlines()};mp={p:insts[v[0].replace('\\','')]for p,v in mp.items()};assert len(set(mp.values()))==390
Path('/srv/opentallas-scratch/claude/wt/codex-qc-a0-2157/results/qc_a0_2157/rawfault_cut/current_capture_map.json').write_text(json.dumps(mp,indent=2))
