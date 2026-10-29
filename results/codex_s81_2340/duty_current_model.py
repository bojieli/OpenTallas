#!/usr/bin/env python3
"""Recompute clock duty from source-resolved routed T/F rows using the shared clock-cell calibration."""
import json,sys,statistics
from pathlib import Path
sys.path.insert(0,'tools/die_plan');import die_sta_related as STA
period=833.0
result=dict(source=sys.argv[1],clock_cell='inv',calibration='die_sta_related.spice_cal_factor(corner,inv); both measured source-edge LATE arrivals',period_ps=period,corners={})
for c in ('TT','FF'):
 T={};F={}
 for l in Path(sys.argv[1],f'out_{c}',f'arr_{c}.txt').read_text().splitlines():
  a=l.split()
  if a and a[0] in ('T','F'):(T if a[0]=='T' else F)[a[1]]=list(map(float,a[2:]))
 f=STA.spice_cal_factor(c,'inv');rows=[]
 for n in T:
  delta=(F[n][0]-T[n][0])*f;high=period/2+delta;low=period-high;rows.append(dict(port=n,duty=high/period,high_ps=high,low_ps=low))
 bad=[r for r in rows if not .45<=r['duty']<=.55]
 result['corners'][c]=dict(taps=len(rows),shared_scale=f,min_duty=min(r['duty'] for r in rows),max_duty=max(r['duty'] for r in rows),outside_45_55=len(bad),bad=bad,min_pulse_ps=min(min(r['high_ps'],r['low_ps']) for r in rows),worst=sorted(rows,key=lambda r:-abs(r['duty']-.5))[:5])
 print(c,json.dumps(result['corners'][c]),flush=True)
Path(sys.argv[2]).write_text(json.dumps(result,indent=2)+'\n')
