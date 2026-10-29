import sys,json,collections
from pathlib import Path
R0=Path(__file__).parent;sys.path.insert(0,str(R0/'tools/die_plan'));import schema as S
R=Path(sys.argv[1]);P=S.Plan(S.load(sys.argv[2]),Path(sys.argv[2]));T=json.load(open(R/'clock/tree.json'));N=T['nodes'];xy=T['sites'];po=T['parent_of'];nt=collections.Counter(T['node_buf'][str(t['node'])] for t in T['taps']);ch=collections.Counter(po.values());reg=json.load(open('/srv/opentallas-scratch2/claude/die-hbm-9/c21_part_region.json'))['part_region']
for p in P.parts:
 if p.startswith('PHY_N') and p not in reg:reg[p]=reg.get('PHY_N','T060')
cal=json.load(open('/srv/opentallas-scratch2/claude/clk-model-sweep-1/hbm/cal_est_hbm_trial2b.json'));out={}
for C in ('TT','FF'):
 d0,k1,k2,kf=cal[C]['early']['coef_d0_k1_k2_kf'];m={};ci={}
 for part,p in P.parts.items():
  for port,x,y,tp in S.core_taps(P,p['type']):ci[part,port]=S.core_tap_insertion_ps(tp,C)
 def arr(c):
  if c in m:return m[c]
  p=po.get(c)
  if p:
   a,b=xy[c],xy[p];L=abs(a[0]-b[0])+abs(a[1]-b[1]);v=arr(p)+d0+k1*L+k2*L*L+kf*max(ch[c]+nt[c]-1,0)
  else:v=0.
  m[c]=v;return v
 by=collections.defaultdict(list)
 for t in T['taps']:
  c=T['node_buf'][str(t['node'])];q=xy[c];L=abs(q[0]-t['xy'][0])+abs(q[1]-t['xy'][1]);wire=(.03644737*L+.00013425*L*L)*(1 if C=='TT' else .86390195)
  v=arr(c)+wire+ci.get((t['part'],t['tap']),S.common_latency_ps(P,C));by[reg[t['part']]].append((v,t['port']))
 rows=[]
 for r,v in by.items():
  lo,hi=min(v),max(v);rows.append(dict(region=r,spread_ps=round(hi[0]-lo[0],2),early=lo[1],late=hi[1]))
 out[C]=dict(basis='same fitted stage polynomial applied to actual compiled cell-parent spans; unshared OCV/droop not included, planning diagnostic only',worst=sorted(rows,key=lambda x:-x['spread_ps'])[:15],over150=sum(r['spread_ps']>150 for r in rows))
(R/'compiled_model.json').write_text(json.dumps(out,indent=1));print(json.dumps(out,indent=1))
