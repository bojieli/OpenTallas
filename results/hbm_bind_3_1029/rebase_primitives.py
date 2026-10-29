"""Rebase inherited exact terminal names after new full HC elaboration renumbers Yosys primitives.
Fail closed unless every preserved cell terminal admits one consistent bijection of
canonical net IDs; constants, parameters, directions and bit order must match.
"""
import json,sys,re,collections,pickle,copy
from pathlib import Path
W,R=map(Path,sys.argv[1:3]);sys.path.insert(0,str(W/'tools/die_plan'));import bind_elab as E
oldpath=Path('/srv/opentallas-scratch2/claude/hbm-bind-3-1029/b1/out/asbuilt.json');newpath=R/'combined/out/asbuilt.json'
O=E.flatten(json.loads(oldpath.read_text()),'hbm_current_native_top');N=E.flatten(json.loads(newpath.read_text()),'hbm_current_native_top')
pickle.dump(N,open(R/'combined/flat.pkl','wb'))
def key(c):
 return (re.sub(r'\$\d+(?=\.|$)','$#',c.path),c.module if c.kind=='leaf' else c.ytype,json.dumps(c.params,sort_keys=True),json.dumps(c.yparams,sort_keys=True),tuple(sorted((p,c.dirs[p],len(v)) for p,v in c.ports.items())))
def num(c):return tuple(int(x)for x in re.findall(r'\$(\d+)(?=\.|$)',c.path))
og=collections.defaultdict(list);ng=collections.defaultdict(list)
for c in O.cells:og[key(c)].append(c)
for c in N.cells:ng[key(c)].append(c)
rename={};pairs=[];unmatched=[]
for k,os in og.items():
 ns=ng.get(k,[])
 if len(os)!=len(ns):
  unmatched.extend(c.path for c in os);continue
 for o,n in zip(sorted(os,key=num),sorted(ns,key=num)):rename[o.path]=n.path;pairs.append((o,n))
bad=[p for p in unmatched if not p.startswith('hcb_')]
assert not bad,('unmatched non-HC cells',bad[:20],len(bad))
bij={};inv={};terms=0
for o,n in pairs:
 for p,bs in o.ports.items():
  for a,b in zip(bs,n.ports[p]):
   if isinstance(a,str) or isinstance(b,str):assert a==b,(o.path,p,'constant',a,b)
   else:
    assert bij.setdefault(a,b)==b,(o.path,p,'net conflict',a,b,bij[a])
    assert inv.setdefault(b,a)==a,(o.path,p,'inverse conflict',a,b,inv[b])
   terms+=1
for p,(d,bs) in O.top_ports.items():
 nd,nb=N.top_ports[p];assert d==nd and len(bs)==len(nb)
 for a,b in zip(bs,nb):
  if isinstance(a,int) and a in bij:assert bij[a]==b,('top port changed',p,a,b)
# Existing synthetic fragment paths extend the original cell path.
def path(s):
 if s in rename:return rename[s]
 p=s
 while '.'in p:
  p=p.rsplit('.',1)[0]
  if p in rename:return rename[p]+s[len(p):]
 return s
spec=json.load(open('/srv/opentallas-scratch2/claude/hbm-bind-1-1029/b1/compose_b.json'))
for s in spec.get('primitive_splits',[]):
 s['member']=path(s['member'])
 for f in s['fragments']:f['path']=path(f['path'])
for c in spec['cores']:
 c['members']=[path(x)for x in c['members']]
 for p in c['ports'].values():
  for anchors in p['bits']:
   for a in anchors:a['member']=path(a['member'])
(R/'compose_rebased_base.json').write_text(json.dumps(spec))
m=json.load(open('/srv/opentallas-scratch2/claude/hbm-bind-2-1029/h1/map_b.json'))
m['parts']={path(k):v for k,v in m['parts'].items()};(R/'map_rebased.json').write_text(json.dumps(m))
receipt=dict(schema='hbm.exact_primitive_name_rebase.v1',matched_cells=len(pairs),unmatched_old_hc_banks=unmatched,renamed_cells=sum(a!=b for a,b in rename.items()),checked_terminals=terms,bijective_nets=len(bij),cycles_added=0,terminal_net_bijection=True,original_source=str(oldpath),new_source=str(newpath))
(R/'rebase_receipt.json').write_text(json.dumps(receipt,indent=1));print(receipt)
