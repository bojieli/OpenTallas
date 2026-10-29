import sys, importlib.util, json, hashlib, subprocess, types
from pathlib import Path
root=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(root/'tools/die_plan'),str(root/'tools/clk')]
import die_trial as new
from test_die_trial_slice_balance import _c_partition

def module(name,path):
 m=types.ModuleType(name); m.__file__=str(root/path)
 src=subprocess.check_output(['git','-C',str(root),'show','a592c118f:'+path])
 exec(compile(src,m.__file__,'exec'),m.__dict__); return m
old=module('baseline_die_trial','tools/die_plan/die_trial.py')

def build(m):
 m.EVEN_LEGS=True
 m.leg_blocked_run=lambda site,a,b:0.0
 site,taps=_c_partition()
 nodes={0:dict(id=0,x=617.,y=1309.,parent=None,level=0,kids=[],taps=[],region=[0,0,1,1],region_root='R0')}
 st=m.attach_region_dme(nodes,site,taps,{t[0]:'R0' for t in taps},delay_rep_um=250.)
 outputs=m.tree_netlist(nodes,taps,rep_um=250.,clock_cell='inv2')
 return json.dumps(dict(nodes=nodes,stats=st,outputs=outputs),sort_keys=True)
a,b=build(old),build(new)
assert a==b,'default tree/netlist output changed'
import ot_clk as onew
oold=module('baseline_ot_clk','tools/clk/ot_clk.py')
argv=[]
for path in sorted((root/'tools/clk/configs').glob('*.yaml')):
 cfg=onew.load_config(path)
 if onew.is_mesh(cfg): continue
 if isinstance(cfg['region'].get('only'),dict) and cfg['region']['only'].get('all_from_map'):
  cfg['region']['only']=['R0','R1']
 x,y=oold.kit_argv(cfg,'OUT'),onew.kit_argv(cfg,'OUT')
 assert x==y,path
 argv.append(path.stem)
report=dict(default_tree_netlist='BYTE_IDENTICAL',sha256=hashlib.sha256(a.encode()).hexdigest(),argv_identical=argv,baseline='a592c118f')
Path(__file__).with_name('default_compare.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
