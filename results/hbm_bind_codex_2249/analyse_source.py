import json,sys,collections
from pathlib import Path
W=Path('/srv/opentallas-scratch2/claude/wt/codex-hbm-bind-2249');sys.path.insert(0,str(W/'tools/die_plan'))
import bind
R=Path('/srv/opentallas-scratch2/claude/codex-hbm-bind-2249');R.mkdir(exist_ok=True)
P=Path('/srv/opentallas-scratch2/claude/die-hbm-29/plan/d29d/die_plan.json')
A=Path('/srv/opentallas-scratch2/claude/die-hbm-29/b29d/asbuilt.json')
bind._AB_OVERRIDE['path']=str(A)
raw=bind.load_plan(P);y=json.load(open('/srv/opentallas-scratch2/claude/die-hbm-29/b29d/out/asbuilt.json'))
B=bind.Binder(raw,y,P.parent,bind.plan_base(P,raw));B.map_cells();F,G=B.F,B.G
rows=[]
for ci,c in enumerate(F.cells):
 if not c.path.startswith(('hb_idx__s_NE.scorer.','hb_idx__s_NW.scorer.')) or not c.ytype.startswith('$dff'):continue
 p=B.cpart.get(ci);port=c.ports.get('Q',[])
 if p not in ('NE_b100','NW_b100'):continue
 dst=p[:2]+'_b102';hits=[];allcnt=collections.Counter();dcnt=collections.Counter()
 for i,net in enumerate(port):
  loads=[(j,pn,k) for j,pn,k in G.loads.get(net,[]) if B.cpart.get(j)==dst]
  if not loads:continue
  hits.append(dict(bit=i,loads=[dict(path=F.cells[j].path,port=pn,bit=k) for j,pn,k in loads]))
  s=G.source(c.ports['D'][i]); key=(B.cpart.get(s[1]),F.cells[s[1]].path,s[2]) if s[0]=='pin' else tuple(s[:2]);dcnt[str(key)]+=1
  for j,pn,k in G.loads.get(net,[]):allcnt[str(B.cpart.get(j))]+=1
 if hits:
  rows.append(dict(path=c.path,home=p,destination=dst,width=len(port),selected_bits=len(hits),D_sources=dict(dcnt),Q_load_counts=dict(allcnt),hits=hits))
(R/'scorer_source_analysis.json').write_text(json.dumps(rows,indent=1));print(json.dumps([{k:v for k,v in r.items() if k!='hits'} for r in rows],indent=1),flush=True)
