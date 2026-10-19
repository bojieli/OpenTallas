"""No completed evidence claimed unless each bounded native check passed."""
import json,sys
from pathlib import Path
p=Path(sys.argv[1])
assert 'INT8_BOUNDED_CTS_ONLY_FINISHED' in (p/'cts.log').read_text()
assert 'READONLY_FF_REPLAY_FINISHED' in (p/'ff.log').read_text()
assert json.loads((p/'metal_proof.json').read_text())['geometry_contact_PASS'] is True
assert json.loads((p/'signal_identity.json').read_text())['signal_identity_PASS'] is True
s=json.loads((p/'strict/summary.json').read_text())
assert not s['violations'], 'native fanout violations'
print('BOUNDED_NATIVE_EVIDENCE_COMPLETE; TT/FF timing/electrical and boundary review still required')
