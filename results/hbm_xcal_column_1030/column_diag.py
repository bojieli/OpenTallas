import importlib.util,json,math,collections
import numpy as np
S=importlib.util.spec_from_file_location('G','/home/ubuntu/OpenTallas/tools/autopilot/geom_rules.py');G=importlib.util.module_from_spec(S);S.loader.exec_module(G)
D=G.Design('/srv/opentallas-scratch/claude/xcal_placed_geom1030.tsv');nets=D.nets;X0,Y0,X1,Y1=D.die;c=127.5;j,k=30,40;nb=int(math.ceil(X1-X0));V=[(n,p)for n,(direction,p)in D.extra['tech'].items()if direction.upper().startswith('V') and 2<=G._layer_idx(n)<=5];cap=np.full(nb,sum(G.TRACK_DERATE/p for n,p in V));macros=[x for x in D.cells.values()if x[0]=='M']
for m in macros:
 if not m[3]<c<m[5]:continue
 obs=D.extra['mobs'].get(m[1],set());keep=sum(G.TRACK_DERATE/p for n,p in V if n not in obs) if obs else 0;a,b=int(max(0,m[2]-X0)),int(min(nb,math.ceil(m[4]-X0)));cap[a:b]=np.minimum(cap[a:b],keep)
cs=np.r_[0,np.cumsum(cap)];cc=cs[k]-cs[j];out=[]
def ep(e):
 if e[0]=='p':return 'PIN:'+D.pin_by_k[e[1]]['name']
 return D.cells[e[1]][6]
for ni,net in enumerate(nets):
 D.nets=[net];boxes=G._net_boxes(D)
 if not boxes:continue
 x0,y0,x1,y1=boxes[0]
 if not y0<c<y1:continue
 a,b=max(0,min(nb-1,int(x0-X0))),max(0,min(nb-1,int(x1-X0)));T=cs[b+1]-cs[a]
 if T<=1e-9:
  aa,bb=G._detour_channel_spans(cap,np.array([a]),np.array([b]));a,b=int(aa[0]),int(bb[0]);T=cs[b+1]-cs[a]
 if T<=1e-9:continue
 lo,hi=max(j,a),min(k,b+1)
 if hi<=lo:continue
 contribution=(cs[hi]-cs[lo])/T
 dr,sk=net[1],net[2];names=[ep(e)for e in ([dr]if dr else[])+sk];families=sorted(set('PROGRAM'if'program_'in n else'TAB'if'tab_'in n else'FACE'if'face_'in n or n.startswith('PIN:')else'LOGIC'for n in names));out.append(dict(net_index=ni,window_crossings=contribution,bbox=boxes[0],families=families,endpoints=names,driver=ep(dr) if dr else None))
D.nets=nets;ratio=sum(x['window_crossings']for x in out)/cc;cnt=collections.Counter()
for x in out:cnt['+'.join(x['families'])]+=x['window_crossings']
pc=collections.Counter();pn=collections.Counter()
for x in out:
 for n in x['endpoints']:
  if 'program_'in n:
   key=n+(' DRIVER'if x['driver']==n else' SINK');pc[key]+=x['window_crossings'];pn[key]+=1
r=dict(program_contributions=dict(pc),program_net_counts=dict(pn),top_program=sorted([x for x in out if 'PROGRAM'in x['families']],key=lambda x:x['window_crossings'],reverse=True)[:12],status='DIAGNOSTIC_COLUMN_CAUSE_NOT_WAIVER',cut_y=c,window_x=[j,k],capacity_tracks=cc,crossing_demand=sum(x['window_crossings']for x in out),ratio=ratio,source_nets=len(out),families=dict(cnt),top=sorted(out,key=lambda x:x['window_crossings'],reverse=True)[:50],macros_at_cut=[m for m in macros if m[3]<c<m[5]])
print(json.dumps({z:r[z]for z in ['capacity_tracks','crossing_demand','ratio','source_nets','families','program_contributions','program_net_counts','macros_at_cut']},indent=1));open('/srv/opentallas-scratch/claude/xcal_column_diag1030.json','w').write(json.dumps(r,indent=1)+'\n')
