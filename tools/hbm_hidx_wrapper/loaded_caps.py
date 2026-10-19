import json,re,collections
from pathlib import Path
exec(Path('tools/hbm_hidx_coupon1/direct_caps.py').read_text().split('rows=[dict')[0])
# L includes every true native input cap; augment every output with real80fF ABI.
outputs={}
for n,p in m['ports'].items():
 if p['direction']=='output':
  for i,b in enumerate(p['bits']):
   outputs[b]=f'{n}[{i}]';loads[b].append(dict(cell=None,pin=outputs[b],master=None,cap=80.,role='external_output'))
maxcap={}
for name,body in blocks(Path('out/all.lib').read_text(),r'\bcell\s*\(\s*([^)]*)\)\s*\{'):
 for pin,pbody in blocks(body,r'\bpin\s*\(\s*([^)]*)\)\s*\{'):
  z=re.search(r'max_capacitance\s*:\s*([0-9.eE+-]+)',pbody)
  if z:maxcap[name,pin]=float(z[1])
rows=[]
for b,d in drivers.items():
 cap=sum(x['cap'] for x in loads[b]);lim=maxcap.get((d['master'],d['pin']))
 rows.append(dict(bit=b,driver=d,contacts=loads[b],cap_ff=cap,native_max_cap_ff=lim,cap_violation=lim is not None and cap>lim,wire_cap_ff=None,wire_qualification=False))
assert len(outputs)==2304 and all(drivers[b]['master']=='BUFx8_ASAP7_75t_R' for b in outputs)
assert not any(r['cap_violation'] for r in rows)
summary=dict(scope='native contacts plus fixed80fF external ABI; wire unknown, not timing/route qualification',nets=len(rows),external_output_pins=len(outputs),output_cap_ff=80,max_cap_violation=0,raw_input_max_nonclock_cap_ff=max(sum(e['cap'] for e in loads[b] if e['role']!='clock') for b,d in drivers.items() if d['cell'] is None),clock_cap_ff=sum(e['cap'] for es in loads.values() for e in es if e['role']=='clock'),clock_contacts=sum(e['role']=='clock' for es in loads.values() for e in es))
Path('out/loaded_caps.json').write_text(json.dumps(dict(summary=summary,all_driver_nets=rows),indent=2)+'\n');Path('out/loaded_caps_summary.json').write_text(json.dumps(summary,indent=2)+'\n')
