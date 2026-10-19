import json,collections,gzip
from pathlib import Path
p=Path(__file__).resolve().parent
j=json.load(gzip.open(p/'pg_geometry.json.gz','rt'));metal=[r for r in j['rails']if not r['via']and r['layer']=='M1'];via=[r for r in j['rails']if r['via']and 'M1'in r['via_layers']]
def overlap(a,b):return min(a[2],b[2])>max(a[0],b[0]) and min(a[3],b[3])>max(a[1],b[1])
results=[]
for m in j['missing']:
 matches=[r for r in metal if r['role']==m['role'] and any(overlap(x['box'],r['box'])for x in m['rects'])]
 contacts=[v for v in via if v['role']==m['role']and any(overlap(v['box'],r['box'])for r in matches)]
 rows=[r['name']for r in j['rows']if r['bbox'][0]<=m['bbox'][0]and r['bbox'][1]<=m['bbox'][1]and r['bbox'][2]>=m['bbox'][2]and r['bbox'][3]>=m['bbox'][3]]
 results.append(dict(instance=m['instance'],pin=m['pin'],master=m['master'],bbox=m['bbox'],pin_rects=m['rects'],rows=rows,matching_m1_rails=matches,m1_via_contacts_on_matched_rail=len(contacts),m1_via_definition_names=sorted(set(v['via_name']for v in contacts))))
s=dict(odb_sha256=j['odb_sha256'],missing_pins=len(results),pins_with_same_role_m1_overlap=sum(bool(x['matching_m1_rails'])for x in results),pins_with_m1_via_on_matched_rail=sum(bool(x['m1_via_contacts_on_matched_rail'])for x in results),pins_with_containing_row=sum(bool(x['rows'])for x in results),scope='Read-only native geometry overlap; not net binding or complete PG-network extraction',pins=results)
print({k:v for k,v in s.items()if k!='pins'});(p/'pg_geometry_summary.json').write_text(json.dumps(s,indent=2)+'\n')
