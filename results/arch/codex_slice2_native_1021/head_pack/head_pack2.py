import json,sys,math,itertools,time,hashlib
from pathlib import Path
from ortools.sat.python import cp_model
raw=Path('head_pack_input2.json').read_bytes();d=json.loads(raw);cs=d['cells'];names=list(cs);W,H=map(float,sys.argv[1:3]);label=sys.argv[3];S=10000;GRID=432000;target=405*S
scale=lambda x:round(x*S)
def xy(p,c,o):
 x,y=p
 if o in(1,3):x=c['w']-x
 if o in(2,3):y=c['h']-y
 return x,y
pairs={}
for e in d['edges']:pairs.setdefault((e['a'],e['b']),[]).append(e)
m=cp_model.CpModel();x={};y={};o={}
for n,c in cs.items():
 x[n]=m.NewIntVar(0,math.floor((W-c['w'])/43.2+1e-6),n+'_x');y[n]=m.NewIntVar(0,math.floor((H-2.16-c['h'])/43.2+1e-6),n+'_y');o[n]=m.NewIntVar(0,3,n+'_orientation')
for a,b in itertools.combinations(names,2):
 bs=[m.NewBoolVar(a+b+str(i))for i in range(4)]
 m.Add(GRID*(x[a]-x[b])+scale(cs[a]['w']+20)<=0).OnlyEnforceIf(bs[0]);m.Add(GRID*(x[b]-x[a])+scale(cs[b]['w']+20)<=0).OnlyEnforceIf(bs[1]);m.Add(GRID*(y[a]-y[b])+scale(cs[a]['h']+20)<=0).OnlyEnforceIf(bs[2]);m.Add(GRID*(y[b]-y[a])+scale(cs[b]['h']+20)<=0).OnlyEnforceIf(bs[3]);m.AddBoolOr(bs)
for (a,b),es in pairs.items():
 code=m.NewIntVar(0,15,a+b+'_code');m.Add(code==4*o[a]+o[b])
 for sx,sy in itertools.product([-1,1],repeat=2):
  vals=[]
  for oa,ob in itertools.product(range(4),repeat=2):
   vals.append(max(scale(sx*(xy(e['axy'],cs[a],oa)[0]-xy(e['bxy'],cs[b],ob)[0])+sy*(xy(e['axy'],cs[a],oa)[1]-xy(e['bxy'],cs[b],ob)[1]))for e in es))
  z=m.NewIntVar(min(vals),max(vals),a+b+str(sx)+str(sy));m.AddElement(code,vals,z);m.Add(GRID*(sx*(x[a]-x[b])+sy*(y[a]-y[b]))+z<=target)
# Exact raw parent N-face input bits; no imaginary landing on these direct paths.
for n in {b['cell']for b in d.get('boundaries',[])}:
 es=[b for b in d['boundaries']if b['cell']==n]
 for sx,sy in itertools.product([-1,1],repeat=2):
  vals=[max(scale(sx*(xy(e['localxy'],cs[n],oo)[0]-e['boundary_x'])+sy*(xy(e['localxy'],cs[n],oo)[1]-(H-0.024)))for e in es)for oo in range(4)]
  z=m.NewIntVar(min(vals),max(vals),n+'_N'+str(sx)+str(sy));m.AddElement(o[n],vals,z);m.Add(GRID*(sx*x[n]+sy*y[n])+z<=target)
solver=cp_model.CpSolver();solver.parameters.num_search_workers=4;solver.parameters.log_search_progress=True
print('MODEL',label,'box',W,H,'cells',len(cs),'matchingbits',len(d['edges']),'pairs',len(pairs),flush=True)
t=time.monotonic();status=solver.Solve(m);out=dict(label=label,box_um=[W,H],status=solver.StatusName(status),wall_s=time.monotonic()-t,input_sha256=hashlib.sha256(raw).hexdigest(),scope=d['scope'],channels_um=20,origin_lattice_um=43.2,reach_um=405)
if status in[cp_model.OPTIMAL,cp_model.FEASIBLE]:
 p={n:dict(x=solver.Value(x[n])*43.2,y=solver.Value(y[n])*43.2,orientation=solver.Value(o[n]))for n in names};out['placements']=p;worst=[]
 for e in d['edges']:
  a,b=e['a'],e['b'];ap=xy(e['axy'],cs[a],p[a]['orientation']);bp=xy(e['bxy'],cs[b],p[b]['orientation']);v=abs(p[a]['x']+ap[0]-p[b]['x']-bp[0])+abs(p[a]['y']+ap[1]-p[b]['y']-bp[1]);worst.append((v,e['a']+'.'+e['ap'],e['b']+'.'+e['bp']))
 out['independent_matching_bit_max_um']=max(v[0]for v in worst);out['worst']=sorted(worst,reverse=True)[:12];assert out['independent_matching_bit_max_um']<=405.0001
 nb=[]
 for e in d.get('boundaries',[]):
  n=e['cell'];pt=xy(e['localxy'],cs[n],p[n]['orientation']);nb.append(abs(p[n]['x']+pt[0]-e['boundary_x'])+abs(p[n]['y']+pt[1]-(H-0.024)))
 out['independent_N_boundary_max_um']=max(nb,default=0);assert max(nb,default=0)<=405.0001
 for a,b in itertools.combinations(names,2):
  assert(p[a]['x']+cs[a]['w']+20<=p[b]['x']+1e-6 or p[b]['x']+cs[b]['w']+20<=p[a]['x']+1e-6 or p[a]['y']+cs[a]['h']+20<=p[b]['y']+1e-6 or p[b]['y']+cs[b]['h']+20<=p[a]['y']+1e-6)
Path(label+'.json').write_text(json.dumps(out,indent=2)+'\n');print('RESULT '+json.dumps(out),flush=True)
