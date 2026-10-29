#!/usr/bin/env python3
"""One-region DME predictor/export coupon; no P&R or STA."""
import copy,json,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent/'tools_actual2'/'die_plan'))
import schema as S
import die_trial as D
from clock_reach import actual_reach

plan,calfile,mode,out=sys.argv[1:];out=Path(out);out.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(Path(__file__).resolve().parent))
import fast_detour
adaptive_stats=fast_detour.install(D)
P=S.Plan(S.load(plan),Path(plan))
D.load_stage_cal(calfile);D.EVEN_LEGS=True;D.DME_ACTUAL_MAX_UM=405. if mode=='physical' else None
site=D.clock_site(P)
cal=json.load(open(calfile));old=json.load(open(Path(__file__).parent/'corridor/clock/tree.json'))
taps=[(t['part'],t['tap'],*t['xy']) for t in old['taps'] if t['part']=='NW_sm3'];early={};targets={}
for port,_,_,tp in S.core_taps(P,P.parts['NW_sm3']['type']):
 vals={c:S.core_tap_early_ps(P,tp,c) for c in ('TT','FF')};targets[('NW_sm3',port)]=vals
 if vals['TT']>0:early[('NW_sm3',port)]=(vals['TT']+vals['FF']/.8639019524)/2
start=time.time();dn,root,stats=D.dme_region_tree(site,taps,delay_rep_um=180.,early=early,snake=True,early_mode='merge')
print('DME_DONE',mode,len(dn),time.time()-start,flush=True)
nodes={};original={}
def add(j,parent=None,snake=None):
 d=dn[j];i=len(nodes);q=(round(d['x'],3),round(d['y'],3))
 nodes[i]=dict(id=i,x=q[0],y=q[1],parent=parent,kids=[],taps=list(d['taps']),level=0 if parent is None else nodes[parent]['level']+1)
 original[i]=j
 if parent is not None:
  nodes[parent]['kids'].append(i);pa=(nodes[parent]['x'],nodes[parent]['y'])
  if mode=='physical':nodes[i]['physical_leg']=D.physical_leg(site,pa,q,180.,[pa]+list(snake)+[q] if snake is not None else None)
  if snake:nodes[i]['snake']=[list(p) for p in snake]
 for k in d['kids']:add(k,i,(d.get('snakes') or {}).get(k))
add(root)
v,place,ports,nb,par=D.tree_netlist(nodes,taps,rep_um=180.,site=site,clock_cell='inv2')
(out/'ctree.v').write_text(v);xy={i:[x,y] for i,x,y in place}
tree=dict(meta=dict(clock_cell='inv2'),nodes={i:{k:v for k,v in n.items() if k!='taps'} for i,n in nodes.items()},
          sites=xy,parent_of=par,node_buf=nb,taps=[dict(port=p,part=part,tap=tp,xy=[x,y],node=i) for p,x,y,part,tp,i in ports])
(out/'tree.json').write_text(json.dumps(tree))
reach=actual_reach(tree,405.);(out/'actual_reach.json').write_text(json.dumps(reach,indent=1))
# Derive path delays from the exact emitted clock graph. Root delay is common.
def path(cell):
 p=[cell]
 while p[-1] in par:p.append(par[p[-1]])
 return list(reversed(p))
rows=[]
for p,x,y,part,tp,node in ports:
 driver=nb[node];chain=[xy[c] for c in path(driver)]
 vals={}
 for corner in ('TT','FF'):
  co=cal['leg' if corner=='TT' else 'leg_FF'];tapco=cal['tap' if corner=='TT' else 'tap_FF']
  delay=sum(co[0]+co[1]*D._man(a,b)+co[2]*D._man(a,b)**2 for a,b in zip(chain,chain[1:]))
  # The fitted per-extra-fanout term belongs to each merge driver's branch.
  for cid in path(driver):
   if cid.startswith('b') and cid[1:].isdigit():delay+=co[3]*max(0,len(nodes[int(cid[1:])]['kids'])-1)
  wire=D._man(chain[-1],(x,y));delay+=tapco[0]*wire+tapco[1]*wire*wire
  delay+=targets.get((part,tp),{}).get(corner,0.)
  vals[corner]=delay
 rows.append(dict(port=p,part=part,tap=tp,delay_ps=vals))
summary=dict(mode=mode,taps=len(taps),dme_nodes=len(dn),elapsed_s=time.time()-start,reach=reach,
             window_ps={c:max(r['delay_ps'][c] for r in rows)-min(r['delay_ps'][c] for r in rows) for c in ('TT','FF')},
             stats=stats,rows=rows)
(out/'adaptive_stats.json').write_text(json.dumps(adaptive_stats,indent=1))
(out/'summary.json').write_text(json.dumps(summary,indent=1));print('SUMMARY',mode,summary['window_ps'],reach['over_count'],flush=True)
