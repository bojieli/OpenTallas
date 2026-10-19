import json,gzip,sys,hashlib
from collections import Counter,defaultdict
from pathlib import Path
import strict_contract as S
r=Path(sys.argv[1]);g=json.load(open(r/'geometry.json'));raw=json.load(open(r/'placed/raw.json'));m=next(iter(raw['modules'].values()));libpaths=[p for p in (r/'placed').glob('*.lib*') if 'FAKE' not in p.name]
native=S.native_cells(libpaths,used_masters={c['type'] for c in m['cells'].values()})
areas=Counter();counts=Counter()
for c in g['cells']:
 x,y,X,Y=c['box'];areas[c['master']]+=(X-x)*(Y-y);counts[c['master']]+=1
tie_caps=[]
for n,c in m['cells'].items():
 if not c['type'].startswith('TIE'):continue
 op='H' if c['type'].startswith('TIEHI') else 'L';net=c['connections'][op][0];loads=[]
 for nn,cc in m['cells'].items():
  for p,b in cc['connections'].items():
   if b==[net] and cc['port_directions'][p]=='input':loads.append(dict(instance=nn,pin=p,master=cc['type'],cap=native[cc['type']]['pins'][p]['native_capacitance'],unit=native[cc['type']]['pins'][p]['capacitance_unit']))
 assert len(loads)==1,(n,loads)
 tie_caps.append(dict(instance=n,loads=loads))
faces=defaultdict(list)
for p in g['pins']:
 if p['name'] in ('VDD','VSS'):continue
 x,y,X,Y=p['box'];cx=(x+X)/2;cy=(y+Y)/2
 face='N' if Y>129.5 else 'S' if y<.1 else 'W' if x<.1 else 'E';faces[face].append(cx if face in ('N','S') else cy)
dens={}
for face,coords in faces.items():
 coords.sort();maxper=max(sum(x<=y<x+1 for y in coords) for x in coords);dens[face]=dict(count=len(coords),max_in_1um=maxper,min_spacing_um=min((b-a for a,b in zip(coords,coords[1:])),default=None))
sumcaps=sum(float(t['loads'][0]['cap'].get('capacitance',0)) for t in tie_caps)
res=dict(kind='placement-only diagnostic; no CTS, no routing, no native timing qualification',outline_um=[237.6,129.6],core_area_um2=(235.44-2.16)*(127.44-2.16),std_area_um2=sum(areas.values()),tie_area_um2=sum(v for k,v in areas.items() if k.startswith('TIE')),tie_count=len(tie_caps),tie_load_capacitance_sum_native=sumcaps,tie_capacitance_unit=tie_caps[0]['loads'][0]['unit'],pin_density=dens,cell_counts=dict(counts),tie_loads=tie_caps,clock=dict(port='clk',entry_face='W',entry_region_um=[62.8,64.3],reference='UNMEASURED: actual source has2782FF; original kit2531sink insertion is not inherited',cts=False),source_sha256=hashlib.sha256((r/'safe_mapped.json').read_bytes()).hexdigest())
(r/'metrics.json').write_text(json.dumps(res,indent=2)+'\n');print(json.dumps({k:v for k,v in res.items() if k not in ('cell_counts','tie_loads')}))
