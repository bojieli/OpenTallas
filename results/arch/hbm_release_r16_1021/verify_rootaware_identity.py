#!/usr/bin/env python3
import json,sys,hashlib
from pathlib import Path
review,manifest,regionmap,report=map(Path,sys.argv[1:]);r=json.loads(review.read_text());m=json.loads(manifest.read_text());reg=json.loads(regionmap.read_text());bad=[]
for x in r['changed_bodies']:
 n=x['instance'];a=m['placement'].get(n,{});e=x['after']
 for k in ['m','o','x','y','w','h']:
  ok=abs(a.get(k,1e99)-e[k])<.001 if isinstance(e[k],(int,float)) else a.get(k)==e[k]
  if not ok:bad.append([n,k,a.get(k),e[k]])
 b=[a.get('x',0),a.get('y',0),a.get('x',0)+a.get('w',0),a.get('y',0)+a.get('h',0)]
 for s in r['all_45_root_contacts']:
  q=s['keepout']
  if min(b[2],q[2])>max(b[0],q[0])+1e-6 and min(b[3],q[3])>max(b[1],q[1])+1e-6:bad.append([n,'fixed_root_keepout_contact',s['region']])
for s in r['all_45_root_contacts']:
 xy=reg['regions'].get(s['region'],{}).get('site');e=s['root']
 if xy!=e:bad.append([s['region'],'root_site',xy,e])
 if s['keepout']!=[e[0]-30,e[1]-30,e[0]+30,e[1]+30]:bad.append([s['region'],'keepout_identity'])
if m.get('reserved_reset_homes')!=r['reserved_reset_areas']:bad.append(['reserved_reset_identity'])
x=dict(status='FAIL' if bad else 'PASS_LOCAL_IDENTITY_DIAGNOSTIC_ONLY',review_sha256=hashlib.sha256(review.read_bytes()).hexdigest(),changed_bodies=11,fixed_roots=45,bad=bad,global_physical_clock_constraints='OPEN_UNCHANGED_NOT_QUALIFIED');report.write_text(json.dumps(x,indent=2)+'\n');print(x['status'],'bad',len(bad));sys.exit(25 if bad else 0)
