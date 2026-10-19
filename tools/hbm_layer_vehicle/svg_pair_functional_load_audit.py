"""Fleet-only immutable mapped audit; exact455fc9ff4 BUF/INV terminal-pin rule."""
import collections,functools,hashlib,json,pathlib,re,sys
src=pathlib.Path(sys.argv[1]);design=json.loads(src.read_text());m=design['modules']['ot_hbm_svg_landing_pair_native'];cells=m['cells'];aliases=collections.defaultdict(list);loads=collections.defaultdict(list);drivers=collections.defaultdict(list)
for n,v in m['netnames'].items():
 for i,b in enumerate(v['bits']):
  if isinstance(b,int):aliases[b].append(n if len(v['bits'])==1 else n+'['+str(i+v.get('offset',0))+']')
for n,c in cells.items():
 for port,bs in c['connections'].items():
  for b in bs:
   if isinstance(b,int):(drivers if c['port_directions'][port]=='output' else loads)[b].append((n,c['type'],port))
def transparent(t):return bool(re.match(r'^(INV|BUF)',t))
def seq(t):return bool(re.search('DFF|LATCH|SDFF',t,re.I))
def collapse(bit,seen=None):
 seen=set() if seen is None else seen
 if bit in seen:return set(),set()
 seen=seen|{bit};terminal=set();visited={bit}
 for cn,ct,pt in loads[bit]:
  if transparent(ct):
   for op,bs in cells[cn]['connections'].items():
    if cells[cn]['port_directions'][op]=='output':
     for ob in bs:
      ts,vs=collapse(ob,seen);terminal.update(ts);visited.update(vs)
  else:terminal.add((cn,ct,pt))
 return terminal,visited
clockbits={b for p in ['pair_hbm_clk','pair_clk','return_clk'] for b in m['ports'][p]['bits']}
inputbits={b:p for p,v in m['ports'].items() if v['direction']=='input' for b in v['bits']}
def origin(bit,seen=None):
 seen=set() if seen is None else seen
 if bit in seen:return ('cycle',str(bit))
 if bit in inputbits:return ('port',inputbits[bit]+':'+str(bit))
 ds=drivers[bit]
 if len(ds)!=1:return ('unknown',str(bit))
 cn,ct,pt=ds[0]
 if transparent(ct):
  ins=[b for p,bs in cells[cn]['connections'].items() if cells[cn]['port_directions'][p]=='input' for b in bs]
  if len(ins)==1:return origin(ins[0],seen|{bit})
 return ('FF_Q' if seq(ct) else 'SRAM_Q' if ct.startswith('ot_sram_') else 'combinational',cn+':'+pt+':'+str(bit))
report=[]
for bit,sinks in list(loads.items()):
 pins,visited=collapse(bit);names=list(dict.fromkeys(x for b in visited for x in aliases[b]));driver_kind,driver=origin(bit)
 kind='clock' if bit in clockbits or bool(pins) and all(seq(ct) and pt.upper() in ['CLK','CK','C','CLOCK'] for _,ct,pt in pins) else 'reset' if any(re.search(r'rst|reset|phase0',n,re.I) for n in names) else driver_kind
 report.append(dict(bit=bit,kind=kind,driver_kind=driver_kind,origin=driver,names=names,direct_load=len(sinks),collapsed_load=len(pins),drivers=drivers[bit],sinks=sorted(pins)))
report.sort(key=lambda v:v['collapsed_load'],reverse=True)
over=[v for v in report if v['collapsed_load']>32];unique={}
for v in over:
 key=(v['kind'],v['driver_kind'],v['origin'])
 if key not in unique or unique[key]['collapsed_load']<v['collapsed_load']:unique[key]=v
r=dict(mapped_sha256=hashlib.sha256(src.read_bytes()).hexdigest(),rule='455fc9ff4 exact recursive INV/BUF terminal unique physical input pins',physical_claim=False,max_collapsed_nonclock=max(v['collapsed_load'] for v in report if v['kind']!='clock'),over32_by_kind=dict(collections.Counter(v['kind'] for v in over)),unique_over32_by_kind=dict(collections.Counter(v['kind'] for v in unique.values())),over32=over,unique_over32=list(unique.values()),all_driver_loads=report,all_driver_class_max={k:max(v['collapsed_load'] for v in report if v['kind']==k) for k in set(v['kind'] for v in report)},qualification='audit only; direct-load max27 is not functional fanout proof')
if len(sys.argv)>2:pathlib.Path(sys.argv[2]).write_text(json.dumps(r,indent=2)+'\n')
print(json.dumps({k:v for k,v in r.items() if k not in ['over32','unique_over32','all_driver_loads']},indent=2))
for v in unique.values():print('NET',v['kind'],v['driver_kind'],v['collapsed_load'],v['names'][:4],v['drivers'])
