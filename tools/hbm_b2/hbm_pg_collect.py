#!/usr/bin/env python3
"""Collect co-located above-M7 coupon loss. It never claims full die IR closure."""
import csv,json,re,sys
from pathlib import Path
for arg in sys.argv[1:]:
 k=Path(arg);m=json.loads((k/'irwin.json').read_text());log=(k/'psm/psm.log').read_text();reasons=[]
 for token in ['OT_PG_CHECK_OK VDD','OT_PG_CHECK_OK VSS','OT_PSM_OK VDD','OT_PSM_OK VSS','OT_DONE','EXIT 0']:
  if token not in log:reasons.append('missing:'+token)
 if re.search(r'OT_(PG_CHECK_FAIL|PSM_FAIL)',log):reasons.append('PG/PSM error')
 if not re.search(r'pad_fallback 0\b',log):reasons.append('pad fallback unknown/nonzero')
 rows={};xy={}
 for net in ['VDD','VSS']:
  f=k/'psm'/f'ir_{net}.csv';v={}
  if not f.exists():reasons.append('missing:'+str(f));continue
  for r in csv.DictReader(f.open()):
   n=r['Instance'];drop=((.7-float(r['Voltage'])) if net=='VDD' else float(r['Voltage']))*1000
   if drop>v.get(n,-1):v[n]=drop;xy[n]=(float(r['X location']),float(r['Y location']))
  rows[net]=v
 x0,y0,x1,y1=m['window_um'];w,h=x1-x0,y1-y0
 interior=[(rows['VDD'][n]+rows['VSS'][n],n,*xy[n]) for n in rows.get('VDD',{}) if n in rows.get('VSS',{}) and min(xy[n][0],xy[n][1],w-xy[n][0],h-xy[n][1])>=450]
 if not interior:reasons.append('no co-located interior data')
 interior.sort()
 r=dict(source_plan=m.get('plan_sha256'),tool_source=m.get('tool_source'),power_basis=m.get('power_basis'),window_um=m['window_um'],power_w=m['power_w'],bump_pad_um=m['bump_pad_um'],status='ERROR' if reasons else 'MEASURED',reasons=reasons,interior_blocks=len(interior),below_m7_mv=None,full_ir_gate='INCOMPLETE: lower-stack and actual activity power owed',scope='Core-only structural coupon. PHY and actual unified native composition not covered.')
 if interior:r.update(colocated_above_m7_mv=interior[-1][0],worst_instance=interior[-1][1],worst_local_xy=list(interior[-1][2:]),above_m7_verdict='PASS' if interior[-1][0]<=35 else 'FAIL',remaining_to_35_mv=35-interior[-1][0])
 (k/'colocated.json').write_text(json.dumps(r,indent=1)+'\n');print(k.name,json.dumps(r))
