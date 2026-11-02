from pathlib import Path
import json
expected=json.load(open('vec/expected.json'));report=dict(status='RUNNING',scope='isolated exact selected CAP wrappers; no bound source/RD arrival or lease authority',source_commit='537b916454f6fa1421d333f80850b7c415225fdb',clock_ps=833,profiles=[])
def check(path,lane,negative=False):
 rows={};fault=None;events=[]
 for line in Path(path).read_text().splitlines():
  s=line.split()
  if s and s[0]=='WRITE':
   f,edge,p,a=map(int,s[1:5]);d=int(s[5],16);rows.setdefault(f,[]).append((p,a,d));events.append(dict(family=f,edge=edge,port=p,address=a,data=d))
  if s and s[0]=='FAULT':fault=s[1]
 for f in range(3):
  ex=sorted((2*r['leaf']+r['port'],r['address'],r['data']) for r in expected[f]);assert sorted(rows.get(f,[]))==ex,(path,f,rows.get(f),ex)
 assert fault=='000',(path,fault)
 return events
try:
 for lane in (0,3,4):report['profiles'].append(dict(e6_lane=lane,writes=check(f'lane{lane}.log',lane)))
 try:check('wrong_payload.log',0,True)
 except AssertionError as e:report['wrong_payload_detected']=True
 else:raise AssertionError('payload control was blind')
 report['status']='PASS_CAP_NATIVE_COMPONENT'
except Exception as e:report.update(status='FAIL',error=str(e));Path('check.json').write_text(json.dumps(report,indent=2));raise
Path('check.json').write_text(json.dumps(report,indent=2)+'\n');print(report['status'])
