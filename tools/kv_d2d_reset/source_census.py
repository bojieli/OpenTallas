import json,sys,collections,hashlib
j=json.load(open(sys.argv[1]));top=sys.argv[2];m=j['modules'][top];loads=collections.defaultdict(list);drivers={};const=set();clocks=set(m['ports']['ck']['bits'])
for n,c in m['cells'].items():
 for p,bits in c['connections'].items():
  d=c['port_directions'][p]
  for b in bits:
   if isinstance(b,str):continue
   if d=='output':
    drivers[b]=(n,c['type'],p)
    if c['type'].startswith(('TIEHI','TIELO')):const.add(b)
   else:
    loads[b].append((n,p))
    if (c['type'].startswith('DFF') and p=='CLK') or (c['type'].startswith('$_DFF') and p=='C') or (c['type'].startswith('ot_sram_') and p=='clk'):
     assert b in clocks,(n,p,b,'unexpected clock source')
viol=[dict(bit=b,driver=drivers.get(b),loads=len(v)) for b,v in loads.items() if b not in clocks|const and len(v)>32]
copybits={b for n,v in m['netnames'].items() if n.startswith('kv_reset_copy_') for b in v['bits']}
copies={n:c for n,c in m['cells'].items() if any(b in copybits for p,bits in c['connections'].items() if c['port_directions'][p]=='output' for b in bits)}
print(json.dumps(dict(sha256=hashlib.sha256(open(sys.argv[1],'rb').read()).hexdigest(),top=top,cells=len(m['cells']),copy_output_drivers=len(copies),total_clocked_states=sum(c['type'].startswith(('DFF','$_DFF')) for c in m['cells'].values()),nonclock_nonconst_max=max(len(v) for b,v in loads.items() if b not in clocks|const),violations=viol,copy_cells=copies),indent=2))
assert not viol
assert len(copies)==27
