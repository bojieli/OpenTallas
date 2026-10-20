import sys,json,gzip,hashlib,collections
from pathlib import Path
source=Path(sys.argv[1]);out=Path(sys.argv[2]);out.mkdir(parents=True,exist_ok=True)
d=json.load(gzip.open(source,'rt'));seq={x['instance']:x for x in d['sequential_instances']};worst=[];counts=collections.Counter();allcounts=collections.Counter();maxima={}
for e in d['data_stage_edges']:
 a,b=e['root'],e['endpoint'];dist=sum(abs(x-y) for x,y in zip(a['xy_um'],b['xy_um']));ac=seq.get(a.get('instance'),{}).get('boundary_classification',a['kind']);bc=seq.get(b.get('instance'),{}).get('boundary_classification',b['kind']);key=ac+' -> '+bc;allcounts[key]+=1;maxima[key]=max(maxima.get(key,0),dist)
 if dist>405+1e-8:
  counts[key]+=1;worst.append(dict(e,endpoint_L1_um=dist,root_boundary=ac,endpoint_boundary=bc,root_clock=seq.get(a.get('instance'),{}).get('clock_pins'),endpoint_clock=seq.get(b.get('instance'),{}).get('clock_pins')))
worst.sort(key=lambda x:-x['endpoint_L1_um'])
s={'scope':'READONLY PRE-CTS DIAGNOSTIC3_place complete sequential-stage data endpoint L1 comparison from completed source/Lib identity receipt. Full combinational cones can include multiple native nets; this is stage endpoint reach, distinct from individual native driver/load reach. No macro move, pin move, free-FF assumption, timing or new-layout claim.','input_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'input_branch':'codex/kv-host6-peer-1020','upstream_extractor_commit':'3268d1abd','odb_sha256':d['odb_sha256'],'pairs':len(d['data_stage_edges']),'over405_pairs':len(worst),'max_stage_endpoint_L1_um':worst[0]['endpoint_L1_um'] if worst else None,'over405_by_boundary_class':dict(counts),'all_pairs_by_boundary_class':dict(allcounts),'max_endpoint_L1_by_boundary_class_um':maxima,'worst10':[{k:v for k,v in e.items() if k not in ['root_clock','endpoint_clock']} for e in worst[:10]]}
(out/'summary.json').write_text(json.dumps(s,indent=2)+'\n')
with gzip.open(out/'violations.json.gz','wt') as f:json.dump(worst,f)
print({k:v for k,v in s.items() if k in ['pairs','over405_pairs','max_stage_endpoint_L1_um','over405_by_boundary_class']})
