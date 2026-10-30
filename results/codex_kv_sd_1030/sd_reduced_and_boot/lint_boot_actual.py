import re,json
from pathlib import Path
r=Path(__file__).resolve().parent;o=r/'full_boot_actual_pruned';lib=r/'sdpg_diamond/rtl'
def refs(s):return set(re.findall(r'\b[A-Za-z_]\w*\b',s))
outputs={'qkd_pll_analog_model':{'locked'}}
for f in ['bind_cells.sv','ot_dp_clk_landing.sv','ot_dp_clk_landing_ca.sv','ot_meso_fifo.sv']:
 for m in re.finditer(r'\bmodule\s+(\w+)\s*(?:#\s*\(.*?\)\s*)?\(.*?\bendmodule',re.sub(r'/\*.*?\*/|//[^\n]*','',(lib/f).read_text(),flags=re.S),re.S):
  h=m[0].split(');',1)[0]
  outputs[m[1]]=set().union(*(refs(re.sub(r'\[[^]]*\]','',seg))-{'wire','reg','signed'} for seg in re.findall(r'output\s+((?:(?!\b(?:input|output|inout)\b).)*)',h,re.S)))
bad={}
for m in re.finditer(r'\bmodule\s+(\w+)\s*(?:#\s*\(.*?\)\s*)?\(.*?\bendmodule',(o/'controls.sv').read_text(),re.S):
 s=m[0];head,body=s.split(');',1)
 drivers=set(re.findall(r'\binput\s+(?:wire\s+|reg\s+)?(?:\[[^]]+\]\s*)?(\w+)',head));decl=set();used=set()
 for d in re.findall(r'^\s*(?:wire|reg)\s+[^;]+;',body,re.M):
  d=re.sub(r'\[[^]]*\]','',d).strip().split(None,1)[1].rstrip(';')
  for n in d.split(','):
   name=n.split('=')[0].strip();decl.add(name)
   if '=' in n:drivers.add(name);used|=refs(n.split('=',1)[1])
 for a in re.findall(r'\bassign\s+([^;]+);',body):
  lhs,rhs=a.split('=',1);drivers|=refs(lhs);used|=refs(rhs)
 for im in re.finditer(r'\b(ot_dp_\w+|qkd_pll_analog_model)\s+(?:#\s*\([^;]*?\)\s*)?\w+\s*\([^;]*?\);',body,re.S):
  for p in re.finditer(r'\.(\w+)\(([^()]*)\)',im[0]):
   names=refs(p[2])
   if p[1] in outputs[im[1]]:drivers|=names
   else:used|=names
 missing=(used&decl)-drivers

 if missing:bad[m[1]]=sorted(missing)
(o/'driver_lint.json').write_text(json.dumps(bad,indent=1))
assert not bad,bad
print('MISSINGTOTAL',sum(map(len,bad.values())),'ROOT',bad.get('kv3_hub_C_part',[])[:8]);print('OUTPORTS',{k:sorted(v)for k,v in outputs.items()if k in ['ot_dp_clk_landing_cas','ot_dp_landing_collect','ot_dp_lockq']})
