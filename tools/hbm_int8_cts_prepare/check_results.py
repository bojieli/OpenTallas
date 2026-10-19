"""No completed evidence claimed unless each bounded native check passed."""
import json,sys
from pathlib import Path
p=Path(sys.argv[1])
assert (p/'checkpoint.status').read_text().startswith('INT8_PG_CHECKED_CTS_CHECKPOINT_V1 ')
stages=[line.rsplit(' ',1) for line in (p/'stage_exit_status').read_text().splitlines()]
assert [name for name,rc in stages]==['platform_check','pre_export','cts','ff','raw_export','metal_export','metal_proof','strict','signal_identity','checkpoint_immutable']
assert all(rc=='0' for name,rc in stages)
assert 'INT8_BOUNDED_CTS_ONLY_FINISHED' in (p/'cts.log').read_text()
assert 'READONLY_FF_REPLAY_FINISHED' in (p/'ff.log').read_text()
assert json.loads((p/'metal_proof.json').read_text())['geometry_contact_PASS'] is True
assert json.loads((p/'signal_identity.json').read_text())['signal_identity_PASS'] is True
s=json.loads((p/'strict/summary.json').read_text())
assert not s['violations'], 'native fanout violations'

import csv,math
for corner in ('TT','FF'):
 rows=list(csv.DictReader((p/f'clock_pins_{corner}.tsv').open(),delimiter='\t'))
 assert len(rows)==2782 and len({r['pin'] for r in rows})==2782
 assert all(math.isfinite(float(r['active_edge_wire_arrival'])) and math.isfinite(float(r['slew_max_rise'])) for r in rows)

print('BOUNDED_NATIVE_EVIDENCE_COMPLETE; TT/FF timing/electrical and boundary review still required')
