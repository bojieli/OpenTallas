#!/usr/bin/env python3
"""CP-SAT feasibility probe for hard children and complete CB16 connectivity.
No route/gate output. A feasible result still requires actual corridor routing,
clock references, reset hardening, and schedule replay. No solver time limit.
"""
import argparse,json,math,time
from pathlib import Path
from ortools.sat.python import cp_model
from qc_safe_graph import ROOT,extract
S=1000;GRID=43200;GAP=20000

def main():
 p=argparse.ArgumentParser();p.add_argument('--step',type=float,required=True);p.add_argument('--out',required=True);p.add_argument('--workers',type=int,default=8);p.add_argument('--core',action='store_true');p.add_argument('--full-land',action='store_true');a=p.parse_args();g=extract();assert not g['unresolved'];c=g['contract'];cols=[172.8+i*a.step for i in range(4)];W=math.ceil((cols[-1]+457.92+172.8)/43.2-1e-8)*43.2;H=c['outline_um']['h'];oldx=sorted(set(t['at'][0]for t in c['tiles']))
 knots=sorted([(0,0),(c['outline_um']['w'],W)]+[(x+d,y+d)for x,y in zip(oldx,cols)for d in [0,457.92]])
 def mx(x):
  for(oa,na),(ob,nb)in zip(knots,knots[1:]):
   if oa-1e-5<=x<=ob+1e-5:return na+(x-oa)*(nb-na)/(ob-oa)
  raise ValueError(x)
 m=cp_model.CpModel();xs=[];ys=[];jobs={};groups={};fixed={n:(round(mx(v['at'][0])*S),round(v['at'][1]*S))for n,v in g['ports'].items()}
 for n,v in g['nodes'].items():
  if v['bits']<=1:continue
  if v['kind'].startswith('qfd_c_land_'):
   keys=[n] if a.full_land else [n+'_p0',n+'_p1'];shape=(103.68,181.44) if a.full_land else (64.8,129.6)
  else:keys=[n];shape=(90.72,129.6)if'xstn'in v['kind']else(90.72,64.8)
  groups[n]=keys
  for k in keys:
   w,h=[round(t*S)for t in shape];ix=m.new_int_var(1,math.floor((W*S-GAP-w)/GRID),k+'_ix');iy=m.new_int_var(1,math.floor((H*S-GAP-h)/GRID),k+'_iy')
   x=m.new_int_var(GRID,round(W*S),k+'_x');y=m.new_int_var(GRID,round(H*S),k+'_y');m.add(x==ix*GRID);m.add(y==iy*GRID)
   xs.append(m.new_fixed_size_interval_var(x,w+GAP,k+'_xr'));ys.append(m.new_fixed_size_interval_var(y,h+GAP,k+'_yr'))
   jobs[k]=dict(logical=n,kind=v['kind'],region=v['region'],w=shape[0],h=shape[1],ix=ix,iy=iy,x=x,y=y,center=(x+w//2,y+h//2))
   m.add_hint(ix,min(math.floor((W*S-GAP-w)/GRID),max(1,round((mx(v['at'][0])-shape[0]/2)/43.2))))
   m.add_hint(iy,min(math.floor((H*S-GAP-h)/GRID),max(1,round((v['at'][1]-shape[1]/2)/43.2))))
 for t in c['tiles']:
  col=int(t['inst'][4]);tx=round(cols[col]*S);ty=round(t['at'][1]*S)
  xs.append(m.new_fixed_size_interval_var(tx,round(457.92*S)+GAP,t['inst']+'_xr'));ys.append(m.new_fixed_size_interval_var(ty,round(1166.4*S)+GAP,t['inst']+'_yr'))
 m.add_no_overlap_2d(xs,ys)
 def center(k):return jobs[k]['center']if k in jobs else fixed[k]
 ee=[];assume={}
 for e in g['edges']:
  ss=groups.get(e['src'],[e['src']]);dd=groups.get(e['dst'],[e['dst']]);pairs=zip(ss,dd)if len(ss)==len(dd)==2 else((s,d)for s in ss for d in dd)
  for src,dst in pairs:
   x0,y0=center(src);x1,y1=center(dst);i=len(ee);dx=m.new_int_var(0,round(W*S),f'ex{i}');dy=m.new_int_var(0,round(H*S),f'ey{i}');m.add_abs_equality(dx,x0-x1);m.add_abs_equality(dy,y0-y1)
   # Necessary geometric reach condition, including each bank. Corridor path is
   # checked after packing. No multicycle relaxation is used by this solver.
   if a.core:
    active=m.new_bool_var(f'edge{i}_reach');m.add(dx+dy<=405*S).only_enforce_if(active);m.add_assumption(active);assume[active.index]=i
   else:m.add(dx+dy<=405*S)
   ee.append(dict(e,src=src,dst=dst))
 solver=cp_model.CpSolver();solver.parameters.num_search_workers=1 if a.core else a.workers;solver.parameters.log_search_progress=True
 print('CP_PLACE_START',a.step,'outline',W,H,'jobs',len(jobs),'edges',len(ee),flush=True)
 started=time.time();status=solver.solve(m);name=solver.status_name(status);print('CP_PLACE_STATUS',name,'wall',time.time()-started,flush=True)
 result=dict(schema='opentallas.cb16.cp_place.v1',diagnostic_only=True,source=g['source'],outline_um=dict(w=W,h=H),step_um=a.step,area_mm2=W*H/1e6,area_ratio=W/c['outline_um']['w'],status=name,solver_wall_s=time.time()-started,shape_policy='stations90.72x64.8; xstn90.72x129.6; half-ring/read64.8x129.6; all pins<=6/um',clock_domain_rule='logical domain unchanged; physical regions may overlap; clock closure unqualified',reset_hardening_remaining=len(g['reset_nodes']),storage_waiver_required=a.full_land,landing_child_profile='full103.68x181.44'if a.full_land else'split64.8x129.6',release_ready=False)
 if status==cp_model.INFEASIBLE:
  result['infeasible_edge_core']=[ee[assume[i]] for i in solver.sufficient_assumptions_for_infeasibility() if i in assume]
  print('CP_PLACE_CORE',[(e['src'],e['dst'],e['net'])for e in result['infeasible_edge_core']],flush=True)
 if status in [cp_model.OPTIMAL,cp_model.FEASIBLE]:
  placed=[]
  for k,j in jobs.items():placed.append(dict(inst=k,**{v:j[v]for v in ['logical','kind','region','w','h']},at=[solver.value(j['x'])/S,solver.value(j['y'])/S]))
  result.update(placement=placed,edges=ee)
 out=Path(a.out);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(result,indent=1)+'\n')
if __name__=='__main__':main()
