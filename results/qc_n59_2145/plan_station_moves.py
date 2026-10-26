"""Plan zero-cycle N59 station relocations from complete geometry endpoints.
A proposal only: no physical DB is changed, and new die pin deltas stay pending.
"""
import json,math,re,sys
from pathlib import Path
p=json.load(open(sys.argv[1]));pos={n:list(v) for n,v in p['positions'].items()};targets=p['targets'];mac=p['macros']
# The full cone census finds six command-stage pads with endpoint diameter
# 812..814um. Move the writer4 s1 group32um west in its legal row channel:
# this preserves all station edges and closes the one-source fanout diameter.
shifts=[]
for n,v in pos.items():
 if '.g_w[4].g_stn.u_s1/' in n.replace('\\',''):
  v[0]-=32.0;shifts.append(dict(name=n,xy_um=list(v),dx_um=-32.0,dy_um=0.0))
# D-QC-N59-1C batch1's approved candidate moves the E dr_o window down by168.16um.
for n,v in pos.items():
 if 'u_bout_dr_o/' in n:v[1]-=168.16
original={n:list(pos[n]) for n in targets}
boxes=[[x0-6,y0-6,x1+6,y1+6] for x0,y0,x1,y1 in mac]
def legal(x,y):return 5<=x<=772 and 5<=y<=513 and not any(a<x<c and b<y<d for a,b,c,d in boxes)
def worst(x,y,near):return max((abs(x-a)+abs(y-b) for a,b in near),default=0)
def choose(n):
 near=[pos[k] for k in targets[n]['src']+targets[n]['dst'] if k!=n]
 if not near:return pos[n],0
 uu=[a+b for a,b in near];vv=[a-b for a,b in near]
 uc=(max(uu)+min(uu))/2;vc=(max(vv)+min(vv))/2
 x=(uc+vc)/2;y=(uc-vc)/2
 cs=[pos[n],(x,y)]
 # Nearest legal channel centres plus projections onto macro halo boundaries.
 xs={5,772,max(5,min(772,x))};ys={5,513,max(5,min(513,y))}
 for a,b,c,d in boxes:xs.update((a,c));ys.update((b,d))
 for a in xs:
  for b in ys:cs.append((a,b))
 choices=[(worst(a,b,near),abs(a-pos[n][0])+abs(b-pos[n][1]),[a,b]) for a,b in cs if legal(a,b)]
 if not choices:raise ValueError('no legal point '+n)
 w,_,pt=min(choices);return pt,w
# Coordinate descent includes both ends of every chain, not independent per-stage guesses.
for iteration in range(12):
 change=0
 for n in targets:
  if '.g_w[4].g_stn.u_s1/' in n.replace('\\',''):continue
  q,w=choose(n)
  if q!=pos[n]:pos[n]=q;change+=1
 if not change:break
rows=[];hist={}
for n,t in targets.items():
 group='f_dd' if '.u_qb.f_dd' in n else 'dr_o' if '.u_svc.dr_o' in n else 'f_lcv' if '.u_qb.f_lcv' in n else 's1_w4' if '.g_w[4].g_stn.u_s1/' in n.replace('\\','') else 'pd'
 near=[pos[k] for k in t['src']+t['dst'] if k!=n]
 w=worst(*pos[n],near)
 h=hist.setdefault(group,dict(count=0,over405=0,max_hop_um=0))
 h['count']+=1;h['over405']+=w>405;h['max_hop_um']=max(h['max_hop_um'],w)
 rows.append(dict(name=n,xy_um=pos[n],original_xy_um=original[n],worst_hop_um=w,group=group))
report=dict(scope='PROPOSAL ONLY; requires pack/legalization/full post-DPL cone census and geometry review',pin_delta='D-QC-N59-1C batch1 candidate',cycles_added=0,iterations=iteration+1,summary=hist,stations=rows,writer4_s1_shift=shifts)
Path(sys.argv[2]).write_text(json.dumps(report,indent=1)+'\n')
print(json.dumps(hist,indent=1))
for r in rows:
 if 'u_pd1_layer_context_v_0' in r['name']:print('LAYER_CONTEXT',json.dumps(r))
