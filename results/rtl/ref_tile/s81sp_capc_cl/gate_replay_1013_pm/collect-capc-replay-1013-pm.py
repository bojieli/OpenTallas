"""Re-evaluate only the known scalar clock-spelling matcher defect after the saved gate finishes."""
import json, re, sys
from pathlib import Path
sys.path.insert(0, '/home/ubuntu/wt/codex-takeover-coord-1013-pm/tools/ref_tile')
import pre_route_gate as G
root = Path('/home/ubuntu/claude-takeover-20261007')
raw_path = Path('/tmp/ref_gate_s81sp_capc_cl_20261013-163609.log')
out = raw_path.read_text()
original = json.loads((root / 'capc-gate-replay-1013-pm.json').read_text())
kit = Path('/home/ubuntu/wt/codex-capc-gate-replay-1013-pm/physical/ref_tile/s81sp_capc_cl')
spec = json.loads((kit / 'spec.json').read_text())
for key in ('GATE_FLOW_RC', 'GATE_CTS_RC', 'GATE_CK_RC'):
    assert re.search(r'^' + key + r'=0(?:\s|$)', out, re.M), key
assert re.search(r'^GATE_DONE$', out, re.M), 'gate not complete'
m = re.search(r'^GATE_SPINE_DONE .*OT_SPINE done port (\S+)', out, re.M)
assert m, 'spine did not build'
assert re.sub(r'\[0\]$', '', m[1]) == re.sub(r'\[0\]$', '', spec['clock_port'])
assert m[1] != spec['clock_port'], 'no scalar-spelling mismatch to repair'
items = original['items']
removed = [i for i in items if i['severity'] == 'FAIL' and i['check'] == 'clock_spine'
           and i['message'].startswith("no 'OT_SPINE done port " + spec['clock_port'] + "'")]
assert len(removed) == 1, 'expected exactly the known original matcher failure'
kept = [i for i in items if i not in removed]
kept.append(dict(severity='INFO', check='clock_spine', message='spine built on scalar port ' + m[1], fix=''))
verdict = 'FAIL' if any(i['severity'] == 'FAIL' for i in kept) else ('WARN' if any(i['severity'] == 'WARN' for i in kept) else 'PASS')
clock = G.clock_record(out, True, spec)
assert clock.get('tt_insertion_ps') is not None, 'missing measured clock insertion'
record = dict(schema='takeover.capture_gate_receipt_replay/1', original_verdict=original['verdict'], verdict=verdict,
              items=kept, clock=clock, removed_known_matcher_failure=removed,
              main_harness_fix='4d5098d10', source='89c4aea41+published_ck_insertion_4d5098d10',
              scope='Re-evaluate completed receipt only; no physical rerun, no threshold/geometry/clock-policy change')
(root / 'capc-gate-replay-1013-pm.corrected.json').write_text(json.dumps(record, indent=2) + '\n')
print(json.dumps(dict(verdict=verdict, clock=clock), indent=2))
