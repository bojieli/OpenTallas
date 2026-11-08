from pathlib import Path
import json,collections
r=Path(__file__).resolve().parent;d=json.loads((r/'periphery_geometry.json').read_text());pm=json.loads((r/'macro_pinmap.json').read_text());mac={m['name'].replace('\\',''):m for m in d['macros']};nets=collections.defaultdict(list)
for p in pm['pins']:
 m=mac[p['inst']];nets[p['net']].append((m['x']+p['x'],m['y']+p['y']))
def extent(n,axis):
 a=[p[axis]for p in n];return min(a),max(a)
def union_span(a):
 a=sorted(a);out=[]
 for lo,hi in a:
  if out and lo<=out[-1][1]:out[-1][1]=max(out[-1][1],hi)
  else:out.append([lo,hi])
 return sum(b-a for a,b in out)
W,H=d['outline'];result=[]
insts=collections.defaultdict(set)
for p in pm['pins']:insts[p['net']].add(p['inst'])
for x in [236.328,470.496]:
 shared=sum(1 for ps in nets.values()if extent(ps,0)[0]<x<extent(ps,0)[1])
 blocked=union_span([(m['y'],m['y']+m['h'])for m in d['macros']if m['x']<x<m['x']+m['w']])
 # Count M2+M4 at50% availability for PDN, M6 unblocked, then60% routing budget.
 cap=.6*((H-blocked)/.048 + H/.064)
 demand=shared+2454+339+40 # AllW/E face traffic crossing + all40clock entries (conservative).
 result.append(dict(axis='vertical',cut_um=x,actual_shared_macro_nets=shared,macro_blocked_height_um=round(blocked,3),capacity_tracks=round(cap,1),planned_bound_with_all_WE_plus_clocks=demand,remaining=round(cap-demand,1),assumption='non-shared macro logic stays in own column; N/S faces descend locally; pilot must verify this locality'))
for y in [67.392,155.52,237.024]:
 shared=sum(1 for ps in nets.values()if extent(ps,1)[0]<y<extent(ps,1)[1])
 n={p['net']for p in pm['pins']if mac[p['inst']]['y']+p['y']>y};south={p['net']for p in pm['pins']if mac[p['inst']]['y']+p['y']<y}
 # Worst allnorth macro nets+allNface traffic, or allsouth macro nets+allSface traffic.
 demand=max(len(n)+3388,len(south)+1)+40
 cap=.6*W/.048
 result.append(dict(axis='horizontal',cut_um=y,actual_shared_macro_nets=shared,capacity_tracks=round(cap,1),bound_macro_north_plus_N_or_south_plus_S=demand,remaining=round(cap-demand,1),assumption='M5 is unobstructed above actual SRAM OBS M1-M4;60% budget reserves remainder for PG/clock'))
report=dict(outline_um=d['outline'],actual_macro_pin_incidences=pm['pin_records'],distinct_macro_nets=pm['distinct_nets'],shared_macro_nets=sum(len(v)>1 for v in insts.values()),local_opposing_LEF_pins=532,local_gap_um=64.8,effective_gap_excluding_halos_um=56.16,local_capacity_M5_60pct=702,cuts=result,physical_release='HOLD for official LEC EQ and actual PLACE locality/density/clock review; no routed claim')
(r/'periphery_demand.json').write_text(json.dumps(report,indent=1));print(json.dumps(report,indent=1))
