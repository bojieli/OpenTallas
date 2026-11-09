import importlib.util,json,shutil
from pathlib import Path
old=Path('/srv/opentallas-scratch3/claude/kw26-wave-1106/runs/qwen_compute/kit-wave/qwen_compute/efdb36e864/items/slw_hc0__cl1bc59e1c/attempt_10/gen/slw_hc0__cl1bc59e1c')
for variant in ['A','B']:
 root=Path('/srv/opentallas-scratch3/claude/codex-qc-hc-rsf3'+('B' if variant=='B' else '')+'-1113')
 root.mkdir(exist_ok=True);new=root/'gen'/old.name
 if not new.exists():
  new.mkdir(parents=True)
  inputs=json.loads((old/'.kw_inputs.json').read_text())
  for rel in inputs['files']:
   (new/rel).parent.mkdir(parents=True,exist_ok=True);shutil.copy2(old/rel,new/rel)
  shutil.copy2(old/'.kw_inputs.json',new/'.kw_inputs.json');shutil.copy2(old.parent/'run_kit.sh',new.parent/'run_kit.sh')
 if variant=='B':
  p=new/'config.mk';text=p.read_text();assert 'PLACE_DENSITY = 0.5' in text
  p.write_text(text.replace('PLACE_DENSITY = 0.5','PLACE_DENSITY = 0.35')+'\n# Private same-row conservative constructor pilot, 0-cycle\nexport OT_CLAND_STRIP_ROWS = 3\n')
 spec=importlib.util.spec_from_file_location('kr','/tmp/qc-reach-kit_resume-fixed.py');kr=importlib.util.module_from_spec(spec);spec.loader.exec_module(kr)
 o=kr.manifest(str(old),runner=str(old.parent/'run_kit.sh'));n=kr.manifest(str(new),runner=str(new.parent/'run_kit.sh'));d=kr.decide(n,o)
 for name,data in [('old_manifest.json',o),('new_manifest.json',n),('decision.json',d)]: (root/name).write_text(json.dumps(data,indent=2))
 print('VARIANT',variant,json.dumps(d),flush=True)
 assert d['decision']=='resume' and d['start']=='place',d
 rec=kr.apply(str(new),str(old),d,{'host':'epyc6','kit':str(old),'attempt':10,'same_host':True,'checkpoint':o['checkpoint']})
 print('RESUME_APPLIED',variant,json.dumps({k:rec[k] for k in ['start','reused_steps','bytes_copy','bytes_link']}),flush=True)
 kr.write_inputs(str(new))
