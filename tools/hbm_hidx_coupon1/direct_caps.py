"""Actual ideal-wire capacitance of each native driven net, including BUF/INV."""
import json,re,collections
from pathlib import Path
def blocks(s,pat):
 for z in re.finditer(pat,s):
  a=s.index('{',z.start());d=1;b=a+1
  while d:d+=(s[b]=='{')-(s[b]=='}');b+=1
  yield z.group(1).strip('" '),s[a+1:b-1]
L={};C={}
for n,body in blocks(Path('out/all.lib').read_text(),r'\bcell\s*\(\s*([^)]*)\)\s*\{'):
 clk=re.search(r'clocked_on\s*:\s*"([^"]+)"',body)
 C[n]=set(re.findall(r'[A-Za-z_][A-Za-z_0-9]*',clk.group(1))) if clk else set()
 pins={p:b for p,b in blocks(body,r'\bpin\s*\(\s*([^)]*)\)\s*\{')}
 L[n]={p:float(z.group(1)) if (z:=re.search(r'\bcapacitance\s*:\s*([0-9.eE+-]+)',b)) else 0 for p,b in pins.items()}
m=json.loads(Path('out/netlist.json').read_text())['modules']['hidx_coupon1'];drivers={};loads=collections.defaultdict(list)
for n,c in m['cells'].items():
 if c['type']=='$scopeinfo':assert not c['connections'];continue
 for p,bs in c['connections'].items():
  assert len(bs)==1
  b=bs[0];e=dict(cell=n,pin=p,master=c['type'])
  if c['port_directions'][p]=='output':assert b not in drivers;drivers[b]=e
  else:loads[b].append(dict(e,cap=L[c['type']][p],role='clock' if p in C[c['type']] else 'nonclock'))
for n,p in m['ports'].items():
 if p['direction']=='input':
  for i,b in enumerate(p['bits']):assert b not in drivers;drivers[b]=dict(cell=None,pin=n+'['+str(i)+']',master=None)
rows=[dict(bit=b,driver=d,cap=sum(x['cap'] for x in loads[b]),nonclock_cap=sum(x['cap'] for x in loads[b] if x['role']!='clock'),contacts=loads[b]) for b,d in drivers.items()]
native=[r for r in rows if r['driver']['cell'] is not None]
summary=dict(units='fF, ideal wire; actual immediate native input contacts, no wire/load estimate',native_max=max(native,key=lambda x:x['cap']),all_max_nonclock=max(rows,key=lambda x:x['nonclock_cap']),native_nets=len(native),all_nets=len(rows))
Path('out/direct_caps.json').write_text(json.dumps(dict(summary=summary,nets=rows),indent=2)+'\n')
Path('out/direct_caps_summary.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps(summary))
