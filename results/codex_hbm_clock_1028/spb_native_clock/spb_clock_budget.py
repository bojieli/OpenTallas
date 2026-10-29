import sys,json,hashlib
from pathlib import Path
R0=Path(__file__).parent;sys.path.insert(0,str(R0/'tools/die_plan'));import schema as S,taps,fast_tap_clear
fast_tap_clear.install(S)
plan,place,out=sys.argv[1:];O=Path(out);O.mkdir(parents=True,exist_ok=True);P=S.Plan(S.load(plan),Path(plan));pl=json.load(open(place));tn='q_spb0';t=P.types[tn];ck=t.setdefault('clock',{})
old=S.tap_grid(P,tn);existing=list(ck.get('sink_sites_um',[]));bank=[];groups=[]
for e in pl['entries']:
 w,h=e['cell_envelope_um'];pts=[[x+w/2,y+h/2,1]for x,y in e['sites_um']];bank+=pts;groups.append((e['instance'],e['stage'],pts))
def md(p,q):return abs(p[0]-q[0])+abs(p[1]-q[1])
old_dist=[min(md(p,(x,y))for _,x,y in old)for p in bank]
ck.update(tap_mode='density',tap_radius_um=200.,tap_max_sinks=1500,tap_target_sinks=1200,control_sinks=True,sink_sites_um=existing+bank)
new=taps.density_taps(P,tn);rows=[]
for inst,stage,pts in groups:
 distances=[min(md(p,(x,y))for _,x,y,_,_ in new)for p in pts];rows.append(dict(instance=inst,stage=stage,sinks=len(pts),worst_nearest_tap_um=max(distances)))
rep=dict(status='ESTIMATE ONLY; parent composes newclock interfaces with nativeSPB; no P&R',placement_source='e64c6bba8',source_plan_sha256=hashlib.sha256(Path(plan).read_bytes()).hexdigest(),type=tn,old_grid_taps=len(old),old_bank_ff_over200=sum(x>200 for x in old_dist),old_bank_worst_um=max(old_dist),new_taps=len(new),new_max_load=max(n for _,_,_,n,_ in new),new_max_radius_um=max(r for _,_,_,_,r in new),new_native_sinks=len(bank),tap_rows=[dict(port=n,xy=[x,y],sinks=w,radius_um=r)for n,x,y,w,r in new],banks=rows)
(O/'clock_budget.json').write_text(json.dumps(rep,indent=1));(O/'clock_delta.json').write_text(json.dumps(dict(type=tn,source_plan_sha256=rep['source_plan_sha256'],source_placement_commit='e64c6bba8',clock_update={k:ck[k]for k in ('tap_mode','tap_radius_um','tap_max_sinks','tap_target_sinks','control_sinks','sink_sites_um')},conditions=['nativeFFsites counted once; current planned_sinks excludes these4104internalnativebits','ROOTcomposedplan+bind/GEN/GEOM/G2 required','reserve actual nativeclockbody/R0homes separately; rawtapxy are interface pins']),indent=1))
print(json.dumps({k:v for k,v in rep.items()if k not in ('tap_rows','banks')},indent=1),flush=True)
