"""Conditional fixed-hard placement feasibility; ordinary-cycle all bank/data paths."""
import json,math,pathlib,sys,time
from ortools.sat.python import cp_model
root=pathlib.Path('results/arch/qw_cb16_legal_bays_1020/grid43');name=sys.argv[1];d=json.loads((root/(name+'_bank_inputs.json')).read_text());assert not d['unknown_writer_bits'];m=cp_model.CpModel();U=4320;R=405000;W,H=[round(x*1000) for x in d['outline']];v={};xinterval=[];yinterval=[]
old=json.loads((root/'plan_k.json').read_text())[name]['bays']['bays'];old={x['half']:x['bay'] for x in old}
for n,b in d['halves'].items():
 w,h=[round(x*1000/U) for x in b['size_um']];x=m.NewIntVar(2,W//U-w-2,'x'+n);y=m.NewIntVar(2,H//U-h-2,'y'+n);v[n]=(x,y,w,h)
 xinterval.append(m.NewFixedSizeIntervalVar(x,w+1,'ix'+n));yinterval.append(m.NewFixedSizeIntervalVar(y,h+1,'iy'+n))
 for sx in [-1,1]:
  for sy in [-1,1]:
   if b['projection_min_nm'] is not None:m.Add(U*(sx*x+sy*y+max(sx*w,0)+max(sy*h,0))-b['projection_min_nm'][str((sx,sy))]<=R)
 # near-source branch restriction is explicit; infeasibility here is not global physical impossibility.
 ox,oy,_,_=old[n];ox=round(ox*1000);oy=round(oy*1000)
 dx=m.NewIntVar(0,W,'dx'+n);dy=m.NewIntVar(0,H,'dy'+n);m.AddAbsEquality(dx,U*x-ox);m.AddAbsEquality(dy,U*y-oy);m.Add(dx+dy<=405000)
 m.AddHint(x,round(ox/U));m.AddHint(y,round(oy/U))
 for hn,p in d['hard'].items():
  a,b0,c,e=[round(z*1000) for z in [p['x']-21.6,p['y']-21.6,p['x']+p['width']+21.6,p['y']+p['height']+21.6]]
  flags=[m.NewBoolVar(n+'sep'+hn+str(k)) for k in range(4)]
  m.Add(U*(x+w)<=a).OnlyEnforceIf(flags[0]);m.Add(U*x>=c).OnlyEnforceIf(flags[1]);m.Add(U*(y+h)<=b0).OnlyEnforceIf(flags[2]);m.Add(U*y>=e).OnlyEnforceIf(flags[3]);m.AddBoolOr(flags)
m.AddNoOverlap2D(xinterval,yinterval)
for a,b in d['bank_edges']+d['soft_edges']:
 x,y,w,h=v[a];xx,yy,ww,hh=v[b]
 for sx in [-1,1]:
  for sy in [-1,1]:m.Add(U*(sx*(x-xx)+sy*(y-yy)+max(sx*w,0)+max(sy*h,0)+max(-sx*ww,0)+max(-sy*hh,0))<=R)
s=cp_model.CpSolver();s.parameters.num_search_workers=8;s.parameters.random_seed=17;s.parameters.log_search_progress=True
status=s.Solve(m);out={'status':s.StatusName(status),'scope':'fixed43.2hard positions; bay displacement<=405 from original branch; actual hard endpoints, all405ordinarybank/soft/hardpoint cones; not global impossibility','wall_time_s':s.WallTime(),'response':s.ResponseStats(),'source_input_sha256':__import__('hashlib').sha256((root/(name+'_bank_inputs.json')).read_bytes()).hexdigest()}
if status in [cp_model.OPTIMAL,cp_model.FEASIBLE]:out['bays']={n:[s.Value(x)*U/1000,s.Value(y)*U/1000,w*U/1000,h*U/1000] for n,(x,y,w,h) in v.items()}
(root/(name+'_bank_solution.json')).write_text(json.dumps(out,indent=2)+'\n');print('BANK_SOLVE',name,out['status'])
