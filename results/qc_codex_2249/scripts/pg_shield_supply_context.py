"""Treat actually materialized, tied VSS shields as supply metal, not other-net clocks."""
import json,sys,shutil
from pathlib import Path
s=Path(sys.argv[1]);o=Path(sys.argv[2]);o.mkdir(parents=True,exist_ok=True)
r=json.load(open(s/'joint_reserved.json'));sig=[];power=[]
for n,l,x0,y0,x1,y1 in r:
 if n=='VSS':
  assert l in ('M8','M9')
  # reserve_clock adds280nm clock-NDR margin. Supply geometry uses its real
  # 80nm shield metal; planner checks opposite PG under existing PDK rules.
  e=.28;power.append([n,l,*[round(v*1000) for v in (x0+e,y0+e,x1-e,y1-e)]])
 else:sig.append([n,l,x0,y0,x1,y1])
g=json.load(open(s/'geometry.json'));g['existing_supplies']+=power
json.dump(g,open(o/'geometry.json','w'),separators=(',',':'));json.dump(sig,open(o/'joint_reserved.json','w'),separators=(',',':'));json.dump([],open(o/'clock_seed.json','w'))
for f in ('power_terms.json','endpoints.json','pg_rects.json','probe_census.json'):shutil.copy(s/f,o/f)
json.dump(dict(actual_tied_vss_shields=len(power),other_net_clock_reservations=len(sig),source=str(s),rule='Existing PG planner same-net supply may connect; VDD still blocked by actual VSS metal under standard PG spacing. All signal-clock NDR reservations unchanged.'),open(o/'shield_supply_receipt.json','w'),indent=2)
print('SHIELD_SUPPLY_CONTEXT',len(power),len(sig),flush=True)
