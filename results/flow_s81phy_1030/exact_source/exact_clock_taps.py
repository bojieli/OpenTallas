"""Source-derived PHY candidate primary taps; no source adoption or physical receipt."""
import copy,json,sys,hashlib
from pathlib import Path
R=Path(__file__).parent;sys.path.insert(0,str(R/'tool_snapshot/tools/die_plan'))
import schema as S,gen_phys as G
src=R/'authoritative_plan.json';base=json.loads(src.read_text());result=[]
for x in (63.64,138.24):
 raw=copy.deepcopy(base)
 for pn in ('lk_ES0','lk_ES1'):
  part=next(p for p in raw['partitions'] if p['name']==pn);t=raw['partition_types'][part['type']]
  phy=next(c for c in t['contents'] if c['inst']=='u_phy');phy['origin_um']=[x,86.4]
  pg=[x-10.8,75.6,x+2608.48+10.8,1021.68]
  t['clock']['keepouts_um']=list(t['clock'].get('keepouts_um',[]))+[pg]
 P=S.Plan(raw)
 rows=[]
 for pn in ('lk_ES0','lk_ES1'):
  part=P.parts[pn];tn=part['type'];t=P.types[tn];before=G.clock_pins(S.Plan(base),tn);after=G.clock_pins(P,tn)
  assert len(after)==32 and [z[0] for z in before]==[z[0] for z in after]
  pg=t['clock']['keepouts_um'][-1]
  assert all(not(pg[0]<a<pg[2] and pg[1]<b<pg[3]) for _,a,b in after)
  rows.append(dict(part=pn,type=tn,old_clock_pins=before,clock_pins=after,grid_taps=S.tap_grid(P,tn),keepouts_um=t['clock']['keepouts_um'],phy_pg_guard_um=10.8))
 result.append(dict(macro_x_um=x,parts=rows))
 (R/('clock_overlay_A.json' if x==63.64 else 'clock_overlay_B.json')).write_text(json.dumps(raw)+'\n')
res=dict(scope='Source-derived geometry only: authoritative Plan plus explicit PHY and additive clock keepout overlay; PG domains/reset/START assembly NOT adopted',source_sha256=hashlib.sha256(src.read_bytes()).hexdigest(),generator='schema.tap_grid + gen_phys.clock_pins; actual default8.64um obstacle clearance and PG track snapping',variants=result,build_allowed=False)
(R/'exact_clock_taps.json').write_text(json.dumps(res,indent=1)+'\n')
for v in result:
 for p in v['parts']:print(v['macro_x_um'],p['part'],p['clock_pins'][:8])
