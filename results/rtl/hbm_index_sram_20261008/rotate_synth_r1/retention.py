import json,sys,re
from collections import Counter
from pathlib import Path
p=Path(sys.argv[1]);j=json.loads(p.read_text());m=j['modules']['ot_hbm_index_lines_sram'];cells=m['cells'];nets=m['netnames'];drivers={}
for name,c in cells.items():
 for port,bits in c['connections'].items():
  if c.get('port_directions',{}).get(port)=='output':
   for bit in bits:
    if isinstance(bit,int):drivers[bit]=(name,c)
def root(bit,seen=None):
 if not isinstance(bit,int):return 'constant:'+bit
 seen=set() if seen is None else seen
 if bit in seen:return 'loop'
 seen.add(bit)
 if bit not in drivers:return 'undriven'
 name,c=drivers[bit];typ=c['type']
 if 'DFF' in typ:return name
 if typ.startswith(('INV','BUF')):
  ins=[b for p,bs in c['connections'].items() if c['port_directions'].get(p)=='input' for b in bs]
  if len(ins)==1:return root(ins[0],seen)
 return 'combinational:'+typ
pairs=[]
for name,n in nets.items():
 # _n precedes unpacked array subscript in Yosys public wire names.
 if not re.search(r'_n(?:\[\d+\])?$',name):continue
 primary=re.sub(r'_n(?=\[\d+\]$|$)','',name)
 if primary not in nets:continue
 a=nets[primary]['bits'];b=n['bits'];stats=Counter()
 for x,y in zip(a,b):
  rx,ry=root(x),root(y)
  if rx.startswith('constant:') and ry.startswith('constant:'):stats['constant_pair']+=1
  elif rx==ry:stats['shared_driver_failure']+=1
  elif rx.startswith(('combinational:','undriven','loop')) or ry.startswith(('combinational:','undriven','loop')):stats['nonregister_driver_failure']+=1
  else:stats['independent_register_pair']+=1
 pairs.append({'primary':primary,'complement':name,'width':len(a),'counts':dict(stats)})
fail=sum(v for pair in pairs for k,v in pair['counts'].items() if k.endswith('failure'))
print(json.dumps({'source_commit':'859068da1','scope':'Mapped structural independence of complemented mutable control/scoreboard state; not a netlist fault simulation or physical signoff','pairs':pairs,'failure_bits':fail,'verdict':'PASS' if pairs and fail==0 else 'FAIL'},indent=2))
