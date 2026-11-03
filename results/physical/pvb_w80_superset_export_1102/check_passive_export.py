import hashlib,json
from pathlib import Path
r=Path('/srv/opentallas-scratch2/claude/codex-pvb-tt-0108'); mod='ot_qwen_tp8_pv_join_t'
a=r/'native_view_w80'/mod;b=r/'native_view_w80_superset'/mod
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
oldg=json.loads((a/'gates.json').read_text());newg=json.loads((b/'gates.json').read_text())
proof=r/'t10_w80/lec_own_final_w80/lec.json';lec=json.loads(proof.read_text())
assert lec['verdict']=='EQUIVALENT' and lec['superset_vec']['all_shown'] is True
assert oldg['routed_lec_all_shown'] is None and newg['routed_lec_all_shown'] is True
assert {k:v for k,v in oldg.items() if k!='routed_lec_all_shown'}=={k:v for k,v in newg.items() if k!='routed_lec_all_shown'}
files={}
for p in a.rglob('*'):
    if not p.is_file() or p.name in ('gates.json','provenance.json','.keep'):continue
    rel=p.relative_to(a);q=b/rel
    assert q.is_file() and sha(p)==sha(q),str(rel)
    files[str(rel)]=sha(p)
assert json.loads((r/'EXPORT_VIEW_w80_superset.log').read_text())['complete'] is True
(b/'.keep').write_text('Qualified native core view; retain full witness and exact proof inputs at t10_w80; passive canonical superset reader correction only.\n')
d={'status':'PASS','old_view':str(a),'corrected_view':str(b),'reader_commit':'813a380fc','reader_sha256':sha(r/'export_source_813a380fc/tools/autopilot/export_view.py'),'proof':str(proof),'proof_sha256':sha(proof),'actual_verdict':lec['verdict'],'canonical_all_shown':True,'old_export_all_shown':None,'new_export_all_shown':True,'other_gates_identical':True,'unchanged_payload_sha256':files,'new_CAD_or_proof':False,'flow_release_tag':'NOT_ASSERTED','parent_expansion':'NOT_ASSERTED'}
(r/'PASSIVE_EXPORT_JOIN_w80_superset.json').write_text(json.dumps(d,indent=2)+'\n');print(json.dumps({'status':'PASS','unchanged_payload_files':len(files),'view':str(b)}))
