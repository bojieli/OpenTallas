import gzip,json,sys,hashlib,collections
from pathlib import Path
identity,pinfile,out=map(Path,sys.argv[1:]);d=json.load(gzip.open(identity,'rt'));p=json.loads(pinfile.read_text());ports={x['port']:x for x in p['ports']};seq={x['instance']:x for x in d['sequential_instances']};rows=[];unresolved=[]
for e in d['data_stage_edges']:
 a,b=[seq.get(e[k].get('instance'),{}) for k in ['root','endpoint']]
 if a.get('boundary_classification')!='direct_port_data_input' or b.get('boundary_classification')!='direct_port_data_output':continue
 ap,bp=a['direct_input_port_bits'],b['direct_output_port_bits']
 if len(ap)!=1 or len(bp)!=1 or ap[0] not in ports or bp[0] not in ports:
  unresolved.append(e);continue
 delta=[[ports[q]['new_pin_center_um'][k]-ports[q]['old_pin_center_um'][k] for k in range(2)] for q in [ap[0],bp[0]]]
 xy=[[e[x]['xy_um'][k]+delta[j][k] for k in range(2)] for j,x in enumerate(['root','endpoint'])];dist=sum(abs(x-y) for x,y in zip(*xy))
 rows.append({'input_port':ap[0],'output_port':bp[0],'root':e['root'],'endpoint':e['endpoint'],'root_delta_um':delta[0],'endpoint_delta_um':delta[1],'projected_L1_um':dist})
rows.sort(key=lambda x:-x['projected_L1_um']);bad=[x for x in rows if x['projected_L1_um']>405+1e-8];counts=collections.Counter((x['input_port'].split('[')[0]+' -> '+x['output_port'].split('[')[0]) for x in bad)
s={'scope':'MODEL ONLY: translate only FFs with uniquely proven direct data-port membership by exact prospective pin displacement, preserving original FF-to-port pin offset. This is an explicit anchored-FF placement assumption, not a generated layout or measured new gate. FF bit/clock/reset and source stages unchanged. Full-cone endpoint metric; individual native wire reach differs. No added-stage or coordinate waiver.','identity_sha256':hashlib.sha256(identity.read_bytes()).hexdigest(),'pinmodel_sha256':hashlib.sha256(pinfile.read_bytes()).hexdigest(),'outline_um':p['outline_um'],'direct_input_to_direct_output_pairs':len(rows),'unresolved_membership':len(unresolved),'over405_pairs':len(bad),'violations_by_portbase':dict(counts),'max_projected_L1_um':rows[0]['projected_L1_um'] if rows else None,'worst10':rows[:10]}
out.mkdir(parents=True,exist_ok=True);(out/'summary.json').write_text(json.dumps(s,indent=2)+'\n')
with gzip.open(out/'violations.json.gz','wt') as f:json.dump(bad,f)
print({k:v for k,v in s.items() if k in ['outline_um','direct_input_to_direct_output_pairs','unresolved_membership','over405_pairs','violations_by_portbase','max_projected_L1_um']})
