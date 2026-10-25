import json,re,sys
from pathlib import Path
r=Path(__file__).parent;vs=sys.argv[1]if len(sys.argv)>1 else'r2';cases=json.loads((r/'cases.json').read_text());out={};bad=[]
for c,e in cases.items():
 s=(r/(c+'.'+vs+'.log')).read_text();a=[(int(m[0]),int(m[1],16))for m in re.findall(r'^LO (\d+) ([0-9a-f]+)',s,re.M)];b=[int(x,16)for x in e['expected_beats']];mismatch=sum(x!=y for x,y in zip([v for _,v in a],b))+abs(len(a)-len(b));st=int(re.search(r'I13_RESULT.*st=([0-9a-f]+)',s)[1],16);ctl=int(re.search(r'JOB_ACCEPT (\d+)',s)[1]);done=int(re.search(r'JOB_DONE (\d+)',s)[1])
 out[c]=dict(beats=len(a),expected=len(b),mismatches=mismatch,status=f'{st:04x}',fault=bool(st&1),command_edge=ctl,first_lookup=int(re.search(r'FIRST_LOOKUP (\d+)',s)[1]),first_return=int(re.search(r'FIRST_RETURN (\d+)',s)[1]),first_output=a[0][0],last_output=a[-1][0],done_edge=done,issue_to_done=done-ctl,output_span=a[-1][0]-a[0][0]+1)
 if e['expected_fault']:
  if not st&1:bad.append(c+':negative escaped')
 elif mismatch or st&1 or not st&8 or done-ctl>640:bad.append(c+':positive failed')
print(json.dumps(dict(cases=out,bad=bad,verdict='PASS'if not bad else'FAIL'),indent=2));(r/('summary_'+vs+'.json')).write_text(json.dumps(dict(cases=out,bad=bad,verdict='PASS'if not bad else'FAIL'),indent=2)+'\n');sys.exit(bool(bad))
