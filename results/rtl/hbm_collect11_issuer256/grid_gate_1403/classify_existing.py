import hashlib,json,sys,tempfile,shutil,subprocess
from pathlib import Path
repo=Path(sys.argv[1]).resolve(); logs=Path(sys.argv[2]).resolve()
sys.path.insert(0,str(repo/'tools/ref_tile'))
import pre_route_gate as P
outdir=repo/'results/rtl/hbm_collect11_issuer256/grid_gate_1403'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
commit=subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip()
for k in ['grid','gridb']:
 kd=repo/'physical/ref_tile'/('hcoll_issuer_r256v8_'+k)
 old=json.loads((outdir/(k+'.original_spec.json')).read_text());new=json.loads((kd/'spec.json').read_text())
 reason=new.pop('fill_reason');assert new==old,'non-metadata spec change'
 new['fill_reason']=reason
 original=json.loads((kd/'gate_result.json').read_text());assert original['verdict']=='FAIL'
 failed=[x for x in original['items'] if x['severity']=='FAIL'];assert failed and all(x['check']=='fill' for x in failed)
 log=logs/(k+'.execution.log')
 assert 'GATE_SOURCE_ARCHIVE_SHA256='+original['source_binding']['archive_sha256'] in log.read_text()
 with tempfile.TemporaryDirectory() as td:
  scratch=Path(td)/kd.name;scratch.mkdir();shutil.copy2(kd/'floorplan.json',scratch/'floorplan.json')
  g=P.Gate();P.gate_layout(g,scratch,new,log.read_text())
  fills=[x for x in g.items if x['check']=='fill'];assert len(fills)==1 and fills[0]['severity']=='WARN'
  derived=[x for x in original['items'] if x['check']!='fill']+fills
  assert not [x for x in derived if x['severity']=='FAIL']
  r=dict(schema='opentallas.issuer_pinbound_classification_candidate.v1',status='CANONICAL_CLASSIFICATION_REPLAY_BINDING_PENDING',qualified_for_submit=False,
    classification_source_commit=commit,new_spec_sha256=sha(kd/'spec.json'),original_spec_sha256=sha(outdir/(k+'.original_spec.json')),
    original_gate_result_sha256=sha(kd/'gate_result.json'),original_gate_result_verdict=original['verdict'],original_physical_manifest_sha256=original['source_binding']['manifest_sha256'],
    original_physical_start_commit=original['source_binding']['start_commit'],original_execution_log=str(log),original_execution_log_sha256=sha(log),
    canonical_classifier='tools/ref_tile/pre_route_gate.py:gate_layout',canonical_classifier_sha256=sha(repo/'tools/ref_tile/pre_route_gate.py'),
    semantic_delta={'fill_reason':reason},old_fill_items=failed,new_canonical_fill_items=fills,
    unchanged_original_items_sha256=hashlib.sha256(json.dumps([x for x in original['items'] if x['check']!='fill'],sort_keys=True).encode()).hexdigest(),
    replay_trial_route=g.trial_route,original_clock=original['clock'],would_be_gate_verdict='WARN',
    provenance='Only existing canonical fill_reason.pin_bound classification rerun over exact immutable original physical log; NO new synthesis/place/CTS/GRT/STA/native measurement. Original gate_result/FAIL remains byte-identical. New consumed spec hash intentionally differs. This packet is NOT an accepted gate result or source_binding override. ROOTintegration validates keyed binding before normal guard/submit.')
  (outdir/(k+'.canonical_pinbound_evaluation.json')).write_text(json.dumps(r,indent=1)+'\n')
  print(k,r['status'],r['new_spec_sha256'],fills[0]['severity'])
