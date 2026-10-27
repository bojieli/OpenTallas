"""Prepare a diagnostic canonical68 + FT-only input, never the parent plan."""
import argparse,subprocess,json,hashlib,types
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--repo',required=True);p.add_argument('--out',required=True);a=p.parse_args();repo=Path(a.repo);out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
def show(commit,path):return subprocess.check_output(['git','-C',str(repo),'show',commit+':'+path])
base=show('18c6286d88','physical/die_plan/qwen_compute/die_plan.json');delta=show('2b588c310c','results/qc_r29_planfix_1351/ft_delta.json');source=show('2b588c310c','results/qc_r29_planfix_1351/apply_delta.py');mod=types.ModuleType('ft_delta_apply');exec(compile(source,'pinned_apply_delta.py','exec'),mod.__dict__)
raw=json.loads(base);fixed=mod.apply(raw,json.loads(delta));restore=json.loads(json.dumps(fixed))
for k in raw['partition_types']:restore['partition_types'][k]['ft_slots']=raw['partition_types'][k]['ft_slots']
assert restore==raw,'overlay changed a non-FT field'
path=out/'canonical68_ft.json';path.write_text(json.dumps(fixed,indent=1)+'\n')
facts=dict(base='18c6286d88',ft_source='2b588c310c',plan_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),outline_um=fixed['die']['outline_um'],types=len(fixed['partition_types']),partitions=len(fixed['partitions']),changed_ft_types=[r['type'] for r in json.loads(delta)['types']],clock_channels=[c for c in fixed['die'].get('channels',[]) if c.get('clock_channel')],centre_channel_assumption_um=0,scope='Fresh diagnostic canonical68 input; no parent plan mutation, no adoption, no old tree-plan checksum rebind')
(out/'facts.json').write_text(json.dumps(facts,indent=1)+'\n');print(json.dumps(facts,indent=1))
