#!/usr/bin/env python3
"""Generate physical hooks for already qualified native ASTK; never reapply RTL transforms."""
import argparse,json,sys,subprocess,importlib.util
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('repo');p.add_argument('inputs');p.add_argument('out');a=p.parse_args()
repo,inp,out=map(Path,(a.repo,a.inputs,a.out));src=inp/'source'
cj=json.loads((src/'kv3_astk_core.json').read_text())
for b in ('ck','rst_n'):
 if b in cj['pin_class']: cj['pin_class'][b+'[0]']=cj['pin_class'].pop(b)
 cj['pin_bits']=[b+'[0]' if q==b else q for q in cj['pin_bits']]
cj['report']['clock_nets']={'clk':'ck[0]'}
cj['files']=[str(src/('deps/'+Path(f).name if '/deps/' in f else Path(f).name)) for f in cj['files']]
for f in cj['files']:
 if not Path(f).is_file(): raise SystemExit('missing source '+f)
(inp/'core.json').write_text(json.dumps(cj,indent=1)+'\n')
plan=json.loads((inp/'plan.json').read_text())
for h in plan['partition_types'][cj['type']]['hard_cores']:
 if h['module']=='kv3_astk':
  h['pins_file']=str(inp/'cores'/'kv3_astk_pins_r26q4_index0.json')
  if not Path(h['pins_file']).is_file(): raise SystemExit('missing pins '+h['pins_file'])
(inp/'plan_materialized.json').write_text(json.dumps(plan,indent=1)+'\n')
gen=repo/'physical/die_plan/qwen_kvsys/cores/harden/gen_core_kit_kv.py'
# Physical-only import uses the generator's existing supported API. The original
# flag bundles RTL transforms, which are already present in this native source.
subprocess.run([sys.executable,str(gen),'--core-json',str(inp/'core.json'),'--plan',str(inp/'plan_materialized.json'),'--out',str(out),'--kit-rtl',str(inp/'kit_rtl'),'--sigmax','M7','--cts-setup-only','--two-mode-grt'],check=True)
k=out/'kv3_astk__190.08x181.44';cfg=(k/'config.mk').read_text().splitlines()
sys.path.insert(0,str(gen.parent));s=importlib.util.spec_from_file_location('native_astk_gen',gen);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
# These six instance renames were explicitly qualified in the inherited source receipt.
t=(src/'kv3_astk.sv').read_text()
for i in range(4):
 if 'u_strip_u_strip_g_zn_'+str(i)+'_u_zn' not in t: raise SystemExit('native zone missing '+str(i))
# Run before changing the source or any timing constraints. cts_setup_only's POST
# hook remains chained, while PRE hooks receive the canonical physical partitions.
cfg=m.astk_zone_fences(k,cfg,190.08,181.44,m.CORE_MARGIN_UM,face_taps=True)
(k/'config.mk').write_text('\n'.join(cfg)+'\n')
(k/'native_physical_hooks.json').write_text(json.dumps({'source_receipt':json.loads((src/'source_receipt.json').read_text()),'rtl_transformations_applied':0,'physical_api':'astk_zone_fences(face_taps=True)','cycles_added':0},indent=1)+'\n')
print('ASTK_NATIVE_GEN PASS',k)
