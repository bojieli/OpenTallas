import json,re,gzip,hashlib
from pathlib import Path
root=Path('/audit')
def blocks(s,k):
 for m in re.finditer(r'\b'+k+r'\s*\(([^)]*)\)\s*\{',s):
  a=i=m.end();d=1
  while d:d+=(s[i]=='{')-(s[i]=='}');i+=1
  yield m[1].strip('" '),s[a:i-1]
for width in ['107','116']:
 d=root/width;j=json.load(open(d/'native/summary.json'));out={}
 for lib in j['lib_sources']:
  p=Path(lib['path']);assert hashlib.sha256(p.read_bytes()).hexdigest()==lib['sha256']
  s=gzip.open(p,'rt').read() if p.suffix=='.gz' else p.read_text()
  for name,body in blocks(s,'cell'):
   if name in j['master_roles']:
    out[name]={'ff':bool(re.search(r'\bff\s*\(',body)),'latch':bool(re.search(r'\blatch\s*\(',body)),'clock_pins':[n for n,v in j['master_roles'][name]['pins'].items() if v.get('clock')]}
 (d/'lib_clock_roles.json').write_text(json.dumps(out,indent=2))
