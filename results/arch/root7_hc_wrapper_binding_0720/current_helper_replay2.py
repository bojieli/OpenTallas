import json,sys,copy
from pathlib import Path
R=Path.cwd();sys.path.insert(0,str(R/'cand/tools/ref_tile'));import source_binding as SB
result={'helper_view':json.loads(Path('current_helpers.json').read_text()),'scope':'explicit current-main executed-helper byte view; route_overlay=False, not a current daemon capture_plan receipt','kits':{}}
for kit in ('hbm_hcq_tree16_c1','hbm_hcq_tree16_c1b'):
 b=json.loads(Path(kit+'.source_snapshot.json').read_text());g=json.loads(Path(kit+'.gate_result.json').read_text());saved=copy.deepcopy(b);savedg=copy.deepcopy(g)
 ok,why=SB.validate(b,R/'cand',R/'current_helpers',commit='0dd3a0a14',route_overlay=False,gate=g)
 expected = all(v['sha256'] == v['original_sha256'] for v in result['helper_view']['files'].values())
 assert ok == expected,(kit,why,expected)
 assert ('stdout repair compatible' in why) == expected
 assert b==saved and g==savedg
 result['kits'][kit]={'ok':ok,'why':why,'manifest_unchanged':True,'gate_unchanged':True}
Path('current_helper_replay2.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
