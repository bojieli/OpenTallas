import csv,json,re,collections
from pathlib import Path
P=Path(__file__).parent;d=json.load(open(P/'regions.json'));cells=list(csv.DictReader((P/'placed.csv').open()))
for c in cells:
 c['box']=[float(c['x']),float(c['y']),float(c['x'])+float(c['w']),float(c['y'])+float(c['h'])]
def area(a,b):return max(0,min(a[2],b[2])-max(a[0],b[0]))*max(0,min(a[3],b[3])-max(a[1],b[1]))
fixed=[c for c in cells if c['kind']!='macro' and c['status'] in ('FIRM','LOCKED','COVER')]
bygroup=collections.defaultdict(list)
for c in cells:
 if c['region']:bygroup[c['region']].append(c)
for r in d['regions']:
 box=r['rects'][0];rowarea=sum(area(box,[x,y,x+w*n,y+h]) for x,y,w,h,n,o in d['rows'])
 fa=sum(area(box,c['box']) for c in fixed)
 members=bygroup[r['name']];outside=[]
 for c in members:
  a=c['box'];x=(a[0]+a[2])/2;y=(a[1]+a[3])/2
  if not(box[0]<=x<=box[2] and box[1]<=y<=box[3]):outside.append(c['name'])
 r.update(actual_row_area_um2=rowarea,fixed_nonmacro_area_um2=fa,available_row_area_estimate_um2=max(0,rowarea-fa),member_area_fraction_of_available=r['member_master_area_um2']/max(1e-9,rowarea-fa),member_centers_outside=len(outside),outside_sample=outside[:3])
traces=collections.defaultdict(list)
for line in (P/'input_selector_place.log').read_text().splitlines():
 m=re.match(r'\s*(\d+)\s*\|\s*([0-9.]+)\s*\|.*\|\s*\(?((?:ot_mrg_)\S+)\)?\s*$',line)
 if m:traces[m[3].rstrip(')')].append((int(m[1]),float(m[2])))
for r in d['regions']:
 t=traces.get(r['name'],[]);r['reported_trace']=t;r['reported_last_overflow']=t[-1][1] if t else None;r['reported_min_overflow']=min(p[1] for p in t) if t else None
stdarea=sum(float(c['w'])*float(c['h']) for c in cells if c['kind'] not in ('macro','tap'));macroarea=sum(float(c['w'])*float(c['h']) for c in cells if c['kind']=='macro')
s=dict(scope='FAILED_GPL_LAYOUT_AND_REGION_CAPACITY_DIAGNOSTIC_NOT_LEGALITY',instances=len(cells),groups=len(d['regions']),std_area_um2=stdarea,macro_area_um2=macroarea,max_group_member_area_fraction=max(r['member_area_fraction_of_available'] for r in d['regions']),empty_groups=[r['name'] for r in d['regions'] if not r['members']],warning_region_names='NOT_EMITTED_BY_GPL_WARNING_OR_PERSISTED_IN_ODB; do not guess from last overflow',warning_overflow_changes=[.238849,.108359],global_hpwl_increase_percent=29.2658,completed_regions=sum(r['reported_last_overflow'] is not None and r['reported_last_overflow']<=.1 for r in d['regions']))
d['summary']=s;(P/'analysis.json').write_text(json.dumps(d,indent=1)+'\n');print(json.dumps(s,indent=1));print('largest member/available',[(r['name'],round(r['member_area_fraction_of_available'],4),r['member_centers_outside']) for r in sorted(d['regions'],key=lambda r:r['member_area_fraction_of_available'],reverse=True)[:5]])
