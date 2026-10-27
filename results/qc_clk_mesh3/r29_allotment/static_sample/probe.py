import sys,json,copy,random,collections
from pathlib import Path
sys.path.insert(0,'/src/tools/die_plan');sys.path.insert(0,'/work')
import die_clock_mesh as D,die_clock_128 as C,qc_track_allotment as A
root=Path('/work');spec=json.loads((root/'clock_spec.json').read_text());errors=json.loads((root/'dry12_errors.json').read_text())['rows'];edge_ndr={e['edge']:e['ndr'] for e in spec['nets']};by=collections.defaultdict(list)
for r in errors:
 if r.get('edge') in edge_ndr:by[edge_ndr[r['edge']]].append(r)
rng=random.Random(20261027);chosen={}
for n,rs in sorted(by.items()):
 for r in rng.sample(rs,min(100,len(rs))):chosen[r['edge']]=r
results=[];current=None;static=None;orig=C.TrackRouter.place
class Finished(BaseException):pass

def place(self,layer,ideal,a0,a1,net,avoid=(),keep=None,dry=False):
 got=orig(self,layer,ideal,a0,a1,net,avoid=avoid,keep=keep,dry=dry)
 if current is not None and not dry:
  req=dict(id=str(len(current['calls'])),owner=net,layer=layer,ideal=ideal,interval=sorted([a0,a1]),ndr=dict(self.nd),wide_merge_um=self.wide_merge_um)
  if keep is not None:req['keep']=list(keep)
  # Count exact tied tracks against fixed PG+mesh only, not the replayed branch.
  C.TrackRouter.place=orig
  static.max_move=self.max_move
  cand=A.candidates(static,req)
  C.TrackRouter.place=place
  current['calls'].append(dict(req,result=list(got),tied_static_candidates=len(cand),tracks=[q['track'] for q in cand]))
 return got

def capture(out,cells,nets,groups,router,off,r8,exact,default_ndr):
 global current,static
 static=copy.deepcopy(router);initial=len(router.ix.shapes);proxy={k:dict(c) for k,c in cells.items()};ties={us[0]:list(us) for us in groups.values() if len(us)>1}
 for us in groups.values():
  if len(us)<2:continue
  xc=sum(cells[u]['x']+D.cell_width(cells[u])/2 for u in us)/len(us)
  for u in us:proxy[u].update(x=xc-D.BUF_W/2,lib=D.BUF)
 C.TrackRouter.place=place
 for n in nets:
  for e in n.get('plan_connections') or []:
   if e.get('edge') not in chosen:continue
   key=e['edge'];ndr=e.get('ndr',default_ndr);nd=D.NDR[ndr];current=dict(edge=key,ndr=ndr,original_failure=chosen[key],calls=[])
   router.nd=nd;router.wide_merge_um=nd.get('wide_merge_um',C.WIDE_MERGE_UM) if r8 else None;router.ix.space=nd['space']
   n0=dict(n,loads=[e['loads'][0]],plan_connections=None,physical_edge=key,physical_layer=e.get('layer'))
   try:
    C.fixed_wires(out,proxy,[n0],D.BUF_W,D.ROW_Y,off=off,router=router,pin_stack=True,port_on_trunk=r8,ties=ties,l_drops=True,exact_reserve=exact)
    current['static_branch']='PLACED_ACCESS_UNQUALIFIED'
   except C.PlanError as err:
    current['static_branch']='FAIL';current['static_errors']=err.rows
   results.append(current);current=None;router.ix.truncate(initial);router.moves.clear();router.modes.clear()
 C.TrackRouter.place=orig
 raise Finished()
D._explicit_v2_wires=capture
try:
 D.main(['build','plan.json','--explicit-cells','clock_spec.json','--ndr','16w','--libdir','/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM','--out','not_a_full_build'])
except Finished:pass
finally:
 C.TrackRouter.place=orig
 summary={}
 for nd in by:
  rs=[r for r in results if r['ndr']==nd];bad=[r for r in rs if r['static_branch']=='FAIL']
  summary[nd]=dict(original_failures=len(by[nd]),sampled=len(rs),static_branch_placed=len(rs)-len(bad),static_branch_failed=len(bad),failed_calls_zero_tied_static=sum(1 for r in bad for c in r['calls'] if c['result'][0] is None and c['tied_static_candidates']==0),original_kinds=dict(collections.Counter(r['original_failure']['detail'].split(' ideal')[0] for r in rs)))
 packet=dict(scope='Representative dry12 failed edges replayed independently against exact prepared static PG+mesh. No33k routing loop, no plan/site/NDR changes. Driver-jog replay path may differ from original pressure-selected path; original exact intervals were not logged.',source='99eaa6d63',selected=len(chosen),replayed=len(results),summary=summary,rows=results)
 (root/'static_result.json').write_text(json.dumps(packet,indent=1));print(json.dumps({k:v for k,v in packet.items() if k!='rows'},indent=1))
