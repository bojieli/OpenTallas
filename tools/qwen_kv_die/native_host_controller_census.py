#!/usr/bin/env python3
"""Exact-source generic controller census; no physical outline inference."""
import collections,hashlib,json,pathlib,shutil,subprocess
p=pathlib.Path.cwd();manifest=json.loads((p/'source_manifest.json').read_text())
for f in manifest['files']:assert hashlib.sha256((p/f['staged']).read_bytes()).hexdigest()==f['sha256']
y=pathlib.Path.home()/'.local/opentallas-tools/yosys/bin/yosys';y=str(y) if y.exists() else shutil.which('yosys');assert y
cmd='read_verilog -defer -sv '+' '.join(f['staged'] for f in manifest['files'])+'; hierarchy -check -top qkd_ctrl_pc_host; proc; opt; memory_map; opt; flatten; opt; stat; write_json controller.json'
r=subprocess.run([y,'-Q','-T','-p',cmd],capture_output=True,text=True);(p/'synthesis.log').write_text(r.stdout+r.stderr);assert r.returncode==0,r.stderr
m=json.loads((p/'controller.json').read_text())['modules']['qkd_ctrl_pc_host'];cells=m['cells'];ports=m['ports'];bytype=collections.Counter();byclock=collections.Counter();clockports={b:n for n,v in ports.items()if n in ['ck','pll_hbm'] for b in v['bits']};drivers=collections.defaultdict(list);inputs={b:n for n,v in ports.items()if v['direction']=='input'for b in v['bits']}
for n,c in cells.items():
 if 'dff' in c['type'].lower():
  count=len(c['connections']['Q']);bytype[c['type']]+=count;clk=c['connections'].get('CLK',[]);key=','.join(clockports.get(b,str(b))for b in clk) or 'UNBOUND';byclock[key]+=count
 for port,bits in c['connections'].items():
  if c['port_directions'][port]=='output':
   for b in bits:
    if isinstance(b,int):drivers[b].append(n)
memo={}
def source(bit,seen):
 if isinstance(bit,str):return (0,set(),{'CONSTANT'})
 if bit in memo:return memo[bit]
 if bit in seen:return (0,set(),{'CYCLE'})
 if bit in inputs:return (0,set(),{'INPUT:'+inputs[bit]})
 ds=drivers.get(bit,[])
 if not ds:return (0,set(),{'UNDRIVEN'})
 depth=0;clocks=set();kinds=set()
 for n in ds:
  c=cells[n]
  if 'dff' in c['type'].lower():
   clocks.update(clockports.get(b,str(b)) for b in c['connections'].get('CLK',[]));kinds.add('FLOP');continue
  for name,bits in c['connections'].items():
   if c['port_directions'][name]=='input':
    for b in bits:
     dep,cl,ki=source(b,seen|{bit});depth=max(depth,dep+1);clocks.update(cl);kinds.update(ki)
 result=(depth,clocks,kinds)
 if 'CYCLE' not in kinds:memo[bit]=result
 return result
faces=[]
for n,v in ports.items():
 if v['direction']!='output':continue
 rows=[]
 for i,b in enumerate(v['bits']):
  dep,cl,ki=source(b,set());rows.append({'bit':i,'generic_cell_depth_to_source':dep,'source_clock_ports':sorted(cl),'source_kinds':sorted(ki)})
 faces.append({'port':n,'bits':len(rows),'max_generic_cell_depth':max((x['generic_cell_depth_to_source']for x in rows),default=0),'bit_sources':rows})
s={'scope':manifest['scope'],'source_commit':manifest['commit'],'manifest_sha256':hashlib.sha256((p/'source_manifest.json').read_bytes()).hexdigest(),'parameters':manifest['parameters'],'Q_bits':sum(bytype.values()),'Q_by_generic_type':dict(bytype),'Q_by_clock_port':dict(byclock),'port_bits':{d:sum(len(v['bits'])for v in ports.values()if v['direction']==d)for d in ['input','output']},'ports':{n:{'direction':v['direction'],'width':len(v['bits'])}for n,v in ports.items()},'output_sources':faces,'mapped_area':None,'outline':None,'assigned_pins':False,'clock_insertion':None,'view_qualified':False}
(p/'census.json').write_text(json.dumps(s,indent=2)+'\n');print(json.dumps({k:s[k]for k in ['Q_bits','Q_by_clock_port','port_bits']},indent=2),flush=True)
