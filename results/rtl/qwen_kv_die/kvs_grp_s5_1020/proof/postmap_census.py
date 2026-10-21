import sys,json,hashlib,importlib.util
from pathlib import Path
base=Path('/srv/opentallas-scratch/claude/ref_gate')
report={}
for p in [base/'codex_s5_1020']:
 if not p.is_dir():continue
 tool=base/'qkd_kvs_grp_h_s4b-20261019-221603/src/tools/textbook_lint.py'
 spec=importlib.util.spec_from_file_location('tl',tool);m=importlib.util.module_from_spec(spec);sys.modules['tl']=m;spec.loader.exec_module(m)
 for v in sorted(p.glob('*.mapped.v')):
  exec_one=True

  g,top=m.flatten(m.parse_verilog(v.read_text()),None);a=m.build(g,None);clk,_=m.clock_nets(g,a)
  rows=[];maximum=0;roots=0
  for x,d in a['driver'].items():
   if x in clk or x<=3 or (d[0]>=0 and a['kind'][d[0]] in ('buf','tie')):continue
   n,ff,ex=m.bufinv_fanout(g,a,x,clk);maximum=max(maximum,n);roots+=1
   if n>32:rows.append(dict(net=m.net_label(g,a,x),loads=n,flops=ff,example=ex))
  rows.sort(key=lambda r:-r['loads'])
  report[v.name]=dict(top=top,netlist=str(v),sha256=hashlib.sha256(v.read_bytes()).hexdigest(),tool_sha256=hashlib.sha256(tool.read_bytes()).hexdigest(),roots=roots,max_loads=maximum,violations=rows,pass_all_drivers_32=not rows)
  print(v.name,maximum,len(rows),flush=True)
Path('/srv/opentallas-scratch/claude/ref_gate/codex_s5_postmap_census_1020.json').write_text(json.dumps(report,indent=1)+'\n')
print('CENSUS_COMPLETE',flush=True)
