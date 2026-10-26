import json,re,sys
from pathlib import Path
prog,log,out=map(Path,sys.argv[1:]);s=json.loads((prog/'schedule.json').read_text());tm=json.loads((prog/'prog/ctl_templates.json').read_text());text=log.read_text();errors=[]
ks=[int(x) for x in re.findall(r'^PROG KS (\d+)',text,re.M)]
beats=[(m[1],int(m[2]),int(m[3],16)) for m in re.finditer(r'^PROG VO ([NS]) (\d+) ([0-9a-fA-F]+)',text,re.M)]
used=set();rows=[];offsets=[]
if len(ks)!=1 or 'PROG END' not in text: errors.append('incomplete producer run: one KS and END required')
for row in s['calendar']:
 if row['engine'] not in (0,1):continue
 side='N' if row['engine']==0 else 'S';want=1|(4<<9)|(int(tm['templates'][row['arg']&127]['payload186'],16)<<21)
 hit=[i for i,b in enumerate(beats) if i not in used and b[0]==side and b[2]==want]
 if not hit:errors.append('missing exact CTL row '+str(row['i']));continue
 i=min(hit,key=lambda i:beats[i][1]);used.add(i);off=beats[i][1]-(ks[0] if ks else 0)-row['issue'];offsets.append(off);rows.append(dict(row=row['i'],side=side,edge=beats[i][1],offset=off))
if len(used)!=len(beats):errors.append('unexpected V beats '+str(len(beats)-len(used)))
if len(set(offsets))!=1:errors.append('CTL rows moved relative to issue schedule')
if re.search(r'^PROG FAULT ',text,re.M):errors.append('issuer fault')
# No MU slot/window programme is loaded in this single-start producer diagnostic.
# Its t_mf is reported separately and receives no multi-user qualification.
if not re.search(r'^PROG KD ',text,re.M):errors.append('KIT completion missing')
r=dict(pass_=not errors,errors=errors,ks=ks,expected_ctl=sum(x['engine'] in (0,1) for x in s['calendar']),observed_ctl=len(beats),checked_ctl=len(rows),offsets=sorted(set(offsets)),rows=rows,scope='exact cap30 native producer and unchanged entry job15 programme; direct ports only; no die route/token qualification')
out.write_text(json.dumps(r,indent=2)+'\n');print('CAP30_PRODUCER', 'PASS' if not errors else 'FAIL',r['checked_ctl'],r['expected_ctl'],errors[:5]);sys.exit(bool(errors))
