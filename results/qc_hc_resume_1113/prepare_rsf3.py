import importlib.util,json,shutil,os
from pathlib import Path
root=Path('/srv/opentallas-scratch3/claude/codex-qc-hc-rsf3-1113')
old=Path('/srv/opentallas-scratch3/claude/kw26-wave-1106/runs/qwen_compute/kit-wave/qwen_compute/efdb36e864/items/slw_hc0__cl1bc59e1c/attempt_10/gen/slw_hc0__cl1bc59e1c')
new=root/'gen'/old.name
assert not new.exists()
new.mkdir(parents=True)
inputs=json.loads((old/'.kw_inputs.json').read_text())
for rel in inputs['files']:
 a=old/rel;b=new/rel
 b.parent.mkdir(parents=True,exist_ok=True)
 shutil.copy2(a,b)
shutil.copy2(old/'.kw_inputs.json',new/'.kw_inputs.json')
shutil.copy2(old.parent/'run_kit.sh',new.parent/'run_kit.sh')
p=new/'landing_placement.tcl';s=p.read_text()
a='if {[info exists ::env(OT_CLAND_STRIP_ROWS)] && $::env(OT_CLAND_STRIP_ROWS) > $rows} {'
b='if {$tag eq "ring:rsf_i+x+ff" && [info exists ::env(OT_CLAND_STRIP_ROWS)] && $::env(OT_CLAND_STRIP_ROWS) > $rows} {'
assert s.count(a)==1
p.write_text(s.replace(a,b))
p=new/'config.mk';p.write_text(p.read_text()+'\n# Private HC0W RSF-only 0-cycle strip geometry pilot\nexport OT_CLAND_STRIP_ROWS = 3\n')
spec=importlib.util.spec_from_file_location('kr',root/'kit_resume.py');kr=importlib.util.module_from_spec(spec);spec.loader.exec_module(kr)
o=kr.manifest(str(old),runner=str(old.parent/'run_kit.sh'))
n=kr.manifest(str(new),runner=str(new.parent/'run_kit.sh'))
d=kr.decide(n,o)
for name,data in [('old_manifest.json',o),('new_manifest.json',n),('decision.json',d)]: (root/name).write_text(json.dumps(data,indent=2))
print(json.dumps(d,indent=2))
assert d['decision']=='resume' and d['start']=='place',d
rec=kr.apply(str(new),str(old),d,{'host':'epyc6','kit':str(old),'attempt':10,'same_host':True,'checkpoint':o['checkpoint']})
print('RESUME_APPLIED',json.dumps({k:rec[k] for k in ['start','reused_steps','bytes_copy','bytes_link']}))
print('INPUTS',json.dumps(kr.write_inputs(str(new)))[:180])
