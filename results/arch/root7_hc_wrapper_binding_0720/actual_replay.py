import copy,hashlib,json,sys,subprocess
from pathlib import Path
from unittest.mock import patch
R=Path.cwd();sys.path.insert(0,str(R/'cand/tools/ref_tile'));import source_binding as SB
rows={}
for kit in ('hbm_hcq_tree16_c1','hbm_hcq_tree16_c1b'):
 binding=json.loads((R/(kit+'.source_snapshot.json')).read_text());gate=json.loads((R/(kit+'.gate_result.json')).read_text())
 before=copy.deepcopy(binding);before_gate=copy.deepcopy(gate)
 ok,why=SB.validate(binding,R/'cand',R/'original_helpers',commit='0dd3a0a14',route_overlay=False,gate=gate)
 assert ok,(kit,why)
 assert binding==before and gate==before_gate
 assert 'stdout repair compatible' in why
 row={'original_gate_verdict':gate['verdict'],'consumed':binding['consumed']['count'],'exact_original_executed_helper_view':{'ok':ok,'why':why},'manifest_unchanged':True,'gate_unchanged':True,'causals':{}}
 original_tree=SB.git_files(R/'cand','0dd3a0a14')
 for tag,path in [('rtl',next(q for q in binding['consumed']['paths'] if q.startswith('rtl/') and q.endswith('.sv'))),('physical_spec',f'physical/ref_tile/{kit}/spec.json')]:
  assert path in binding['consumed']['paths'],path
  tree=dict(original_tree);tree[path]='f'*40
  with patch.object(SB,'git_files',return_value=tree):
   nok,nwhy=SB.validate(binding,R/'cand',R/'original_helpers',commit='0dd3a0a14',route_overlay=False,gate=gate)
  assert not nok,(tag,nwhy)
  row['causals'][tag]={'path':path,'ok':nok,'why':nwhy,'method':'single target-tree blob mutation in memory; immutable receipt untouched'}
 failed=dict(gate,verdict='FAIL');saved=copy.deepcopy(failed)
 fok,fwhy=SB.validate(binding,R/'cand',R/'original_helpers',commit='0dd3a0a14',route_overlay=False,gate=failed)
 assert fok and failed==saved and failed['verdict']=='FAIL'
 row['failed_verdict_preserved']=True
 assert binding==before and gate==before_gate
 rows[kit]=row
Path('actual_replay.json').write_text(json.dumps(rows,indent=2)+'\n');print(json.dumps(rows,indent=2))
