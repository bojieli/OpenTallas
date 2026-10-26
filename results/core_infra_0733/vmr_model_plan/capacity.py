import json,math
from collections import Counter
from pathlib import Path
import core_infra as CI,core_infra_wire as CW
p=Path('.');s=json.load(open('slice.json'));data=json.load(open('input.json'));routing=json.load(open('merged_report.json'))['routing_model'];plan=CI.compile_slice(s);cells={c['name']:c for c in plan['cells']};children={n['name']:[] for n in plan['core_tree']['nodes']};leaves={}
for n in plan['core_tree']['nodes']:
 if n['parent'] in children:children[n['parent']].append(n['name'])
for l in plan['core_tree']['leaves']:leaves.setdefault(l['node'],[]).extend(l['sinks'])
occupied=set();lines=[];G=10.8
for n in plan['core_tree']['nodes']:
 name=n['name'];point=cells[name]['xy_um'];points=[point]+[cells[q]['xy_um'] for q in children[name]]+[data['points'][q] for q in leaves.get(name,[])];profile=routing['nodes'].get(name,routing['nonleaf' if children[name] else 'leaf']);rc=CW.rooted_rc(points,[0.]*(len(points)-1),**profile);kind='leaf' if not children[name] and name not in routing['nodes'] else 'trunk'
 for seg in rc['merged_segments']:
  a,b=seg['a'],seg['b'];axis=seg['axis'];layer=('M2' if axis=='H' else 'M3') if kind=='leaf' else ('M4' if axis=='H' else 'M5');constant=a[1] if axis=='H' else a[0]
  lines.append(dict(driver=name,layer=layer,a=a,b=b))
  lo=[math.floor(min(a[k],b[k])/G) for k in [0,1]];hi=[math.floor(max(a[k],b[k])/G) for k in [0,1]]
  for x in range(lo[0],hi[0]+1):
   for y in range(lo[1],hi[1]+1):occupied.add((layer,x,y,name,constant))
demand=Counter()
for layer,x,y,name,constant in occupied:demand[layer,x,y]+=1 if layer in ('M2','M3') else 3
peak={L:max([n for (l,x,y),n in demand.items() if l==L]or[0]) for L in ['M2','M3','M4','M5']}
out=dict(qualification='CLOCK-ONLY GEOMETRY CAPACITY SENSITIVITY; NOT fullroutecapacitymargin',gcell_um=G,nominal_tracks_per_layer=225,nominal_track_pitch_um=.048,clock_peak_tracks_by_layer=peak,nominal_clock_fraction={L:n/225 for L,n in peak.items()},nominal_remaining_tracks_before_data_pg={L:225-n for L,n in peak.items()},counting='Merged same-layer conductor intervals; deduplicate same-net/same-line/same-cell fragments. Different nets require distinct tracks. DefaultM2/M3leaf=1track;2W2SM4/M5trunk=3tracks.',open_limits=['Actual M2–M5 signal range can choose alternate layer topology; prototype modelsM2/M3leaf only.','Data routing, PG/clockshield reservations, pin-access/via density and legal track-grid assignment NOT RUN.','Macro own-clockpin profileM4/M5 explicit; R/Cofaccessvias/coupling notincluded.','Nominal remaining tracks cannot authorize physicalbuild or prove0.6roadusagegate.'])
(p/'merged_capacity.json').write_text(json.dumps(out,indent=1));(p/'merged_routes.json').write_text(json.dumps(lines,indent=1));print(out,flush=True)
