"""Joint station43.2 and ring-bay model; no multi-cycle bank data paths."""
import json,pathlib,sys,collections,math,hashlib
from ortools.sat.python import cp_model
import sys as _s, pathlib as _p; _s.path.insert(0, str(_p.Path(__file__).resolve().parent)); import qc_cluster_cfg as CF   # SQC-CB8: OT_QC_CLUSTER
root=pathlib.Path(CF.PLAN);name=sys.argv[1];inputpath=root/(name+'_bank_inputs.json');d=json.loads(inputpath.read_text());assert not d['unknown_writer_bits'];m=cp_model.CpModel();U=4320;R=405000;W,H=[round(x*1000/U) for x in d['outline']];hv={};bv={};hi=[];hj=[];bi=[];bj=[];motion=int(__import__("os").environ.get("OT_JOINT_MOTION","4"))
for n,p in d['hard'].items():
 w,h=[round(p[k]*1000/U) for k in ['width','height']];ox,oy=[round(p[k]*1000/U) for k in ['x','y']]
 if 'stn5' in p['kind']:
  xg=m.NewIntVar(max(1,ox//10-motion),min((W-w-5)//10,ox//10+motion),'gx'+n);yg=m.NewIntVar(max(1,oy//10-motion),min((H-h-5)//10,oy//10+motion),'gy'+n);x=10*xg;y=10*yg;m.AddHint(xg,ox//10);m.AddHint(yg,oy//10)
 else:x=ox;y=oy
 hv[n]=(x,y,w,h);hi.append(m.NewFixedSizeIntervalVar(x,w+5,'hx'+n));hj.append(m.NewFixedSizeIntervalVar(y,h+5,'hy'+n))
m.AddNoOverlap2D(hi,hj)
for n,b in d['halves'].items():
 w,h=[round(x*1000/U) for x in b['size_um']];x=m.NewIntVar(2,W-w-2,'x'+n);y=m.NewIntVar(2,H-h-2,'y'+n);bv[n]=(x,y,w,h);bi.append(m.NewFixedSizeIntervalVar(x,w+1,'bx'+n));bj.append(m.NewFixedSizeIntervalVar(y,h+1,'by'+n))
 for hn,(xx,yy,ww,hh) in hv.items():
  flags=[m.NewBoolVar(n+'sep'+hn+str(k)) for k in range(4)]
  m.Add(x+w+5<=xx).OnlyEnforceIf(flags[0]);m.Add(x>=xx+ww+5).OnlyEnforceIf(flags[1]);m.Add(y+h+5<=yy).OnlyEnforceIf(flags[2]);m.Add(y>=yy+hh+5).OnlyEnforceIf(flags[3]);m.AddBoolOr(flags)
 # exact all-bit input/output point extrema grouped by actual owning hard macro.
 refs=collections.defaultdict(list)
 for pt in b['anchor_refs']:refs[pt.get('node','PORT')].append(pt.get('offset',pt.get('fixed')))
 for hn,pts in refs.items():
  xx,yy=hv[hn][:2] if hn!='PORT' else (0,0)
  for sx in [-1,1]:
   for sy in [-1,1]:
    lo=round(min(sx*a+sy*z for a,z in pts)*1000)
    m.Add(U*(sx*(x-xx)+sy*(y-yy)+max(sx*w,0)+max(sy*h,0))-lo<=R)
m.AddNoOverlap2D(bi,bj)
for a,b in d['bank_edges']+d['soft_edges']:
 x,y,w,h=bv[a];xx,yy,ww,hh=bv[b]
 for sx in [-1,1]:
  for sy in [-1,1]:m.Add(U*(sx*(x-xx)+sy*(y-yy)+max(sx*w,0)+max(sy*h,0)+max(-sx*ww,0)+max(-sy*hh,0))<=R)
groups=collections.defaultdict(list)
for a,b in d['hard_hops']:
 na,nb=a.get('node','PORT'),b.get('node','PORT');aa=a.get('offset',a.get('fixed'));bb=b.get('offset',b.get('fixed'));groups[na,nb].append((aa,bb))
for (a,b),terms in groups.items():
 x,y=hv[a][:2] if a!='PORT' else (0,0);xx,yy=hv[b][:2] if b!='PORT' else (0,0)
 for sx in [-1,1]:
  for sy in [-1,1]:
   bias=round(max(sx*(aa[0]-bb[0])+sy*(aa[1]-bb[1]) for aa,bb in terms)*1000)
   m.Add(U*(sx*(x-xx)+sy*(y-yy))+bias<=R)
s=cp_model.CpSolver();s.parameters.num_search_workers=8;s.parameters.random_seed=17;s.parameters.log_search_progress=True
status=s.Solve(m);out={'status':s.StatusName(status),'scope':'A0/xstn fixed; station43.2 within4lattice steps; all-bit hard+bank+soft data405; macro/bay clearance21.6; not global impossibility','wall_time_s':s.WallTime(),'response':s.ResponseStats(),'input_sha256':hashlib.sha256(inputpath.read_bytes()).hexdigest()}
def val(x):return x if isinstance(x,int) else s.Value(x)
if status in [cp_model.OPTIMAL,cp_model.FEASIBLE]:
 out['hard']={n:[val(x)*U/1000,val(y)*U/1000,w*U/1000,h*U/1000] for n,(x,y,w,h) in hv.items()};out['bays']={n:[val(x)*U/1000,val(y)*U/1000,w*U/1000,h*U/1000] for n,(x,y,w,h) in bv.items()}
(root/(name+'_joint_solution.json')).write_text(json.dumps(out,indent=2)+'\n');print('JOINT_SOLVE',name,out['status'])
