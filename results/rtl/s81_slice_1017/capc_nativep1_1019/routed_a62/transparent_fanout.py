"""Native every-driver BUF/INV-transparent loads, clocks retained separately."""
import collections,csv,json,re,hashlib
from pathlib import Path
p=Path(__file__).resolve().parent
norm=lambda s:s.replace('\\[','[').replace('\\]',']')
masters={norm(r['instance']):r['master']for r in csv.DictReader((p/'instance_masters.tsv').open(),delimiter='\t')}
nets=collections.defaultdict(dict);pins={};outs=collections.defaultdict(set)
for r in csv.DictReader((p/'driver_reach.tsv').open(),delimiter='\t'):
 n=norm(r['endpoint']);pins[n]=r;nets[r['net']][n]=r
 if r['io']=='OUTPUT':outs[n.rsplit('/',1)[0]].add(n)
# Match explicit native standard-cell names, never arbitrary module spelling.
transparent={i for i,m in masters.items()if (re.fullmatch(r'(?:BUF|INV)x\d+f?_ASAP7_75t_R',m) or m=='HB4xp67_ASAP7_75t_R')}
adj=collections.defaultdict(set)
for ns in nets.values():
 ds={n for n,r in ns.items()if r['io']in('OUTPUT','PORT_INPUT')};ls={n for n,r in ns.items()if r['io']in('INPUT','PORT_OUTPUT')}
 for d in ds:adj[d]|=ls
c=[]
for driver in sorted(n for n,r in pins.items()if r['io']in('OUTPUT','PORT_INPUT')):
 todo=list(adj[driver]);seen=set();loads=set()
 while todo:
  n=todo.pop()
  if n in seen:continue
  seen.add(n);inst=n.rsplit('/',1)[0]
  if pins[n]['io']=='INPUT'and inst in transparent:
   for o in outs[inst]:todo.extend(adj[o])
  else:loads.add(n)
 c.append({'driver':driver,'master':masters.get(driver.rsplit('/',1)[0],'TOP_INPUT'),'net_type':pins[driver]['type'],'logical_loads':len(loads),'loads':sorted(loads)})
data=[r for r in c if r['net_type']!='CLOCK'];clock=[r for r in c if r['net_type']=='CLOCK'];source=Path(__file__).resolve().parents[5]
summary={'scope':'Every native nonPG driver through exact master BUF/INV contraction; first nontransparent input/port is a logical load. Clock network explicitly separate.','native_drivers':len(c),'transparent_masters':sorted({masters[i]for i in transparent}),'data_driver_count':len(data),'clock_driver_count':len(clock),'max_data':max(data,key=lambda r:r['logical_loads']),'data_over32':[r for r in data if r['logical_loads']>32],'max_clock':max(clock,key=lambda r:r['logical_loads'])if clock else None,'clock_over32_count':sum(r['logical_loads']>32for r in clock)}
(p/'transparent_fanout_census.json').write_text(json.dumps(c,indent=1)+'\n');(p/'transparent_fanout_summary.json').write_text(json.dumps(summary,indent=1)+'\n');print('drivers',len(c),'maxdata',summary['max_data'],'dataover32',len(summary['data_over32']),'maxclock',summary['max_clock']['logical_loads']if clock else None)
