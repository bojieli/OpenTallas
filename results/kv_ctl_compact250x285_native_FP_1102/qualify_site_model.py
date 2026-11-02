import json,gzip,csv,sys,collections,re,os
from pathlib import Path
O=Path(__file__).resolve().parent;C=Path('/srv/opentallas-scratch/claude/codex-kv-ctl-compact250-0430/collector');sys.path.insert(0,str(O.parents[1]/'tools/autopilot'));import geom_rules as G
D=G.Design(str(C/'geom.tsv'),[str(O.parent/'kv_ctl_place_1102/memory_tt.lib')],True);ids={c[6]:i for i,c in D.cells.items()};poses=json.loads(gzip.decompress((O/os.environ.get('FF_SITE_FILE','FF_sites.json.gz')).read_bytes()));raw=list(csv.DictReader(open(C/'instances.csv')));rows=collections.defaultdict(list)
for r in json.load(open(C/'rows.json'))['rows']:rows[r['bbox'][1]].append(r)
occ=collections.defaultdict(list);bad=[];master_changes=[];byname={q['name']:q for q in raw}
for q in raw:
 if q['kind']=='tap' or(q['kind'] not in ['ff','macro'] and q['status'] in ['FIRM','LOCKED','FIXED']):
  x,y,w,h=[round(float(q[k])*1000) for k in ['x','y','w','h']];occ[y].append((x,x+w,q['name']))
for p in poses:
 x,y=p['ll_dbu'];w,h=p['size_dbu'];match=[r for r in rows[y] if r['bbox'][0]<=x and x+w<=r['bbox'][2] and r['orient']==p['orient'] and (x-r['bbox'][0])%54==0]
 if not match:bad.append(p['name'])
 occ[y].append((x,x+w,p['name']));i=ids[p['name']];c=D.cells[i];D.cells[i]=tuple([c[0],p['master'],x/1000,y/1000,(x+w)/1000,(y+h)/1000]+list(c[6:]))
 if byname[p['name']]['master']!=p['master']:master_changes.append(p['name'])
overlaps=[]
for y,rs in occ.items():
 rs.sort()
 for a,b in zip(rs,rs[1:]):
  if a[1]>b[0]:overlaps.append([y,a,b])
rr=G.r2r_metrics(D);pr=G.pin_reg_metrics(D,re.compile(G.STRAP_RE_DEFAULT));D.cells={i:c for i,c in D.cells.items() if c[0] in 'SM'};area=G.area_metrics(D)
r=dict(status='LEGAL_NATIVE_FF_SITE_MODEL_NOT_PLACE',FFs=len(poses),target_master_resizes=len(master_changes),native_rows=2008,native_taps=7184,row_site_orientation_violations=bad,FF_TAP_fixed_overlap=overlaps,R2R=rr,pins=pr,FF_only_density=area,holds=['Ordinary combinational placement/model channels NOT qualified','No new source state, latency or parent profile adopted'])
assert len(poses)==18768 and len(master_changes)==54 and not bad and not overlaps
(O/os.environ.get('SITE_REPORT_FILE','FF_site_report.json')).write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:v for k,v in r.items() if k not in ['FF_only_density','holds']},indent=2))
