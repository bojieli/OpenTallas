import runpy,copy,json,math
from pathlib import Path
p=Path('/srv/opentallas-scratch2/claude/codex-kv-pv-resume-1029');D=runpy.run_path(str(p/'pv_decompose.py'));P,C,libs,r,c,rec=[D[k]for k in ['P','C','libs','r','c','rec']];base=copy.deepcopy(P['_int']);old_nodes={n[0]:n for n in P['nodes']};changes=[]
def length(pts):return sum(abs(a[0]-b[0])+abs(a[1]-b[1])for a,b in zip(pts,pts[1:]))
def splitpath(pts,t):
 pre=[pts[0]];rest=t
 for i,(a,b)in enumerate(zip(pts,pts[1:])):
  d=abs(a[0]-b[0])+abs(a[1]-b[1])
  if rest<=d+1e-8:
   f=0 if d==0 else rest/d;q=(a[0]+(b[0]-a[0])*f,a[1]+(b[1]-a[1])*f)
   if q!=pre[-1]:pre.append(q)
   post=[q]+pts[i+1:];return pre,post,q
  pre.append(b);rest-=d
 raise ValueError(t)
for B in ['Tpqw_r1','Tpqv_r1']:
 A=old_nodes[B][1];assert A.endswith('_r0');w=next(w for w in P['wires']if w['edge']==B.rsplit('_r',1)[0]);assert len(w['segs'])==3
 path=[tuple(q)for q in w['cells'][-2]]+[tuple(q)for q in w['cells'][-1][1:]];total=length(path);oldprev,oldlast=w['segs'][-2:];rows=[]
 for step in range(1,int(total/rec['maze_g_um'])):
  prev=step*rec['maze_g_um'];last=total-prev
  if prev<3 or last<6:continue
  cand={};safe=True
  for cn in ['TT','FF']:
   I=base[cn];L=libs[cn];LA=L[old_nodes[A][3]];LB=L[old_nodes[B][3]];ctA=c*prev+LB['cin'];slA=I['slew'][A]
   da=.5*(C.H.interp(LA['rise'],slA,ctA)+C.H.interp(LA['fall'],slA,ctA));soa=.5*(C.H.interp(LA['trise'],slA,ctA)+C.H.interp(LA['tfall'],slA,ctA));ela=r*prev*(c*prev/2+LB['cin']);slB=math.hypot(soa,2.2*ela)
   Cl=I['drv'][B][0]-c*oldlast;ctB=c*last+Cl;db=.5*(C.H.interp(LB['rise'],slB,ctB)+C.H.interp(LB['fall'],slB,ctB));sob=.5*(C.H.interp(LB['trise'],slB,ctB)+C.H.interp(LB['tfall'],slB,ctB));elold=r*oldlast*(c*oldlast/2+Cl);elnew=r*last*(c*last/2+Cl)
   childnew=max(e for _,e in I['drv'][B][1])-elold+elnew
   arrival=I['arr'][A]+da+ela+db+childnew
   safe &= max(soa,slB,sob,math.hypot(sob,2.2*childnew))<=80
   cand[cn]=dict(arrival=arrival,A_cell=da,A_wire=ela,B_cell=db,B_wire_max=childnew,A_output_slew=soa,B_input_slew=slB,B_output_slew=sob)
  if safe:rows.append((sum(v['arrival']for v in cand.values()),prev,last,cand))
 assert rows;_,prev,last,choice=min(rows,key=lambda x:(x[0],x[1]));pre,post,xy=splitpath(path,prev);oldxy=old_nodes[B][2]
 P['nodes']=[(n[0],n[1],xy if n[0]==B else n[2],n[3],n[4])for n in P['nodes']];w['segs'][-2:]=[prev,last];w['cells'][-2:]=[pre,post];P['land'][B]=(last,w['edge'])
 changes.append(dict(node=B,old_xy=oldxy,new_xy=xy,old_segments=[oldprev,oldlast],new_segments=[prev,last],length_unchanged=total,local_model=choice))
res,_=C.M7.model_x(P,libs,r,c,{})
out=dict(scope='CAUSAL PLAN ONLY two existing stage10 high-Ct chains, same nodes/depth/masters/counts/caps, along exact existing macro-clear paths; no padding/dummyload/constraintchange',baseline=D['res'],result=res,changes=changes,clock_cells=len(P['nodes']),sinks=sum(len(v)for v in P['leafsinks'].values()))
# Compare each changed stage10 leg under full model, both corners, including unchanged preceding stage input.
for ch in changes:
 B=ch['node'];ch['actual_model_stage10']={}
 for cn in ['TT','FF']:
  old=base[cn];new=P['_int'][cn];L=libs[cn][old_nodes[B][3]]
  def stage(I):
   ct,ks=I['drv'][B];sl=I['slew'][B];d=.5*(C.H.interp(L['rise'],sl,ct)+C.H.interp(L['fall'],sl,ct));return dict(cell=d,wire_max=max(e for _,e in ks),child_arrival_max=I['arr'][B]+d+max(e for _,e in ks))
  ch['actual_model_stage10'][cn]=dict(before=stage(old),after=stage(new))
(p/'pv_resegment_causal.json').write_text(json.dumps(out,indent=1)+'\n');print('PV_RESEGMENT_CAUSAL',json.dumps(out))
