import runpy,json,hashlib
from pathlib import Path
O=Path('/work/proof6');old=hashlib.sha256((O/'cut.sv').read_bytes()).hexdigest();runpy.run_path('proof_observable.py');assert hashlib.sha256((O/'cut.sv').read_bytes()).hexdigest()==old
r=json.load(open(O/'source_receipt.json'));r.update(schema='opentallas.undef_mux_observability.v1',verdict='PASS',observability_contract='all_effective_next_state_reset_clock_macro_inputs_outputs')
for key,name,phrase in [('positive','positive.log','SAT proof finished - no model found: SUCCESS!'),('negative','negative.log','SAT proof finished - model found: FAIL!'),('cut','cut.sv',None)]:
 p=O/name
 if phrase:assert phrase in p.read_text()
 r[key]=dict(file=name,sha256=hashlib.sha256(p.read_bytes()).hexdigest())
r['generator_sha256']=hashlib.sha256(Path('proof_observable.py').read_bytes()).hexdigest();r['snapshot_helper_sha256']=hashlib.sha256(Path('tools/qwen_dv/ctlm6_snapshot.py').read_bytes()).hexdigest();(O/'undef_receipt.json').write_text(json.dumps(r,indent=2)+'\n');print('EXACT_SOURCE_OBSERVABILITY_RECEIPT_PASS',r['normalized_graph_sha256'])
