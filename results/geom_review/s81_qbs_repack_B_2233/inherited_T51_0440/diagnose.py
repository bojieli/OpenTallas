from pathlib import Path
import sys,json
sys.path.insert(0,'/home/ubuntu/OpenTallas/tools/autopilot');import geom_rules as G
R=Path(__file__).parent;D=G.Design(R/'geom.tsv');pairs=[];metrics=G.r2r_metrics(D,pairs);byname={c[6]:i for i,c in D.cells.items()};src={}
for cid,c in D.cells.items():
 if c[0]!='S':continue
 ins=[n for n,isc in D.cell_in.get(cid,[])if not isc]
 if len(ins)!=1:continue
 cur=ins[0]
 for depth in range(G.PINREG_DEPTH+1):
  dr=D.nets[cur][1]
  if not dr or dr[0]!='i':break
  k=D.kind(dr[1])
  if k=='S':
   if dr[1]!=cid:src[cid]=dr[1]
   break
  if k!='B'or not D.cell_in.get(dr[1]):break
  cur=D.cell_in[dr[1]][0][0]
chains=[]
for t in [i for i in src if i not in set(src.values())]:
 chain=[t];cur=t
 while cur in src and src[cur]not in chain and len(chain)<4096:cur=src[cur];chain.append(cur)
 if len(chain)<3:continue
 hops=[sum(abs(x-y)for x,y in zip(G.ctr(D.cells[a]),G.ctr(D.cells[b])))for a,b in zip(chain,chain[1:])]
 if max(hops)>405:chains.append(dict(chain=[D.cells[i][6]for i in reversed(chain)],xy=[G.ctr(D.cells[i])for i in reversed(chain)],hops_um=list(reversed(hops))))
for p in pairs:
 for role in ('launch','capture'):
  c=D.cells[byname[p[role]]];p[role+'_master']=c[1];p[role+'_bbox']=list(c[2:6]);p[role+'_direct_predecessor']=D.cells[src[byname[p[role]]]][6]if byname[p[role]]in src else None
out=dict(metrics=metrics,over405=pairs,collapsed_chains=chains,seq_count=sum(c[0]=='S'for c in D.cells.values()),source_only='saved native geometry + graph; no source edit/CAD');(R/'diagnosis.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
