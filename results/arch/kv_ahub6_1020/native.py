import sys,json,importlib.util
from pathlib import Path
R=Path('/srv/opentallas-scratch/claude/ref_gate/qkd_ahub_g4a-20261019-215713')
s=importlib.util.spec_from_file_location('tl',R/'src/tools/textbook_lint.py');m=importlib.util.module_from_spec(s);sys.modules['tl']=m;s.loader.exec_module(m)
n=next(R.glob('routes/gate/work/orfs/results/asap7/*/base/1_2_yosys.v'))
g,t=m.flatten(m.parse_verilog(n.read_text()),'qkd_ahub_static_dw_g3_lp');a=m.build(g,None);cl,_=m.clock_nets(g,a);v=[]
for x,d in a['driver'].items():
 if x in cl or x<=3 or (d[0]>=0 and a['kind'][d[0]] in ('buf','tie')):continue
 k,f,e=m.bufinv_fanout(g,a,x,cl)
 if k>32:v.append(dict(driver=m.net_label(g,a,x),loads=k,flops=f))
v.sort(key=lambda x:-x['loads']);Path('/srv/opentallas-scratch/codex/kv-ahub6/native_over32.json').write_text(json.dumps(v,indent=1));print('NATIVE_OVER32',len(v));print(json.dumps(v[:25],indent=1))
