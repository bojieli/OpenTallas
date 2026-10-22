from pathlib import Path
import shutil,json,hashlib
B=Path('/home/ubuntu/ot-scratch/claude/codex-k-die-1340/health_replay');B.mkdir(exist_ok=True)
W=Path('/home/ubuntu/ot-scratch/claude/qwen-kvsys/wt-kvs14r-c6520b2ee-dsg6f');R=W.with_name('kvs14r-c6520b2ee-dsg6f')
files=[]
def cp(src,dst):
 dst=B/dst;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst);files.append(dict(path=str(dst.relative_to(B)),source=str(src),sha256=hashlib.sha256(dst.read_bytes()).hexdigest()))
for n in ['die.v','place.tcl','elements.lef','die.v.pads.json']:cp(R/'case_kv'/(n+'.prehealth'),'run/case_kv/'+n)
for n in ['fwd_lanes.json','expand.json','kv_flags.env']:cp(R/n,'run/'+n)
for n in ['die.v.params.json']:
 if (R/'case_kv'/n).exists():cp(R/'case_kv'/n,'run/case_kv/'+n)
if (R/'libs/views.json').exists():cp(R/'libs/views.json','run/libs/views.json')
for n in ['tools/die_port_bind.py','tools/qwen_kv_die/kv_expand_parameters.py']:cp(W/n,'source/'+n)
for n in ['kv_health_plane.py','kv_fault_topology.py']:cp(B.parent/n,'source/tools/qwen_kv_die/'+n)
for master,rtl in [('qkd_hp_or2','rtl/qwen_sys/kv_health_20261019/qkd_hp_or2.sv'),('qkd_rlys_1','rtl/qwen_sys/kv_rly_std_20261016/qkd_rlys.sv'),('qkd_astk_fault_join','rtl/qwen_sys/split_20261014/qkd_astk_phys.sv')]:
 cp(W/rtl,'source/'+rtl)
 v=Path('physical/ref_tile')/master/'views'/master
 for src in (W/v).rglob('*'):
  if src.is_file():cp(src,'source/'+str(src.relative_to(W)))
profiles={}
ex=json.loads((R/'expand.json').read_text())
for v in ex.get('parameter_instances',{}).values():
 if v.get('module') in ['qkd_hp_or2','qkd_rlys_1','qkd_astk_fault_join'] and v.get('profile'):
  profiles[v['module']]=v['profile']
for v in profiles.values():
 receipt=v.get('frozen_receipt')
 if receipt:cp(W/receipt['path'],'source/'+receipt['path'])
(B/'profiles.json').write_text(json.dumps(profiles,indent=2)+'\n')
# Remove health-created params/expansion entries from the saved prehealth input.
for name in ['run/case_kv/die.v.params.json','run/expand.json']:
 p=B/name
 if p.exists():
  d=json.loads(p.read_text())
  if name.endswith('params.json'):d={k:v for k,v in d.items() if not k.startswith('hp_')}
  else:
   for field in ['parameter_instances','frames']:
    if field in d:d[field]={k:v for k,v in d[field].items() if not k.startswith('hp_')}
  p.write_text(json.dumps(d,indent=1)+'\n')
(B/'readset_manifest.json').write_text(json.dumps(files,indent=2)+'\n')
print('compact saved health stage',B,'bytes',sum(p.stat().st_size for p in B.rglob('*') if p.is_file()))
