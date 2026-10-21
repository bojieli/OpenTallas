import hashlib
import json
from pathlib import Path
import subprocess


SCRIPT = Path(__file__).with_name('guarded_case.sh')


def fixture(tmp_path):
    for name in ('contract.json', 'manifest.json', 'die.v'):
        (tmp_path / name).write_text('{}')
    (tmp_path / 'run.tcl').write_text('define_corners tt ff\nset_wire_rc -signal -layer M8\n'
                                     'set_routing_layers -signal M4-M8 -clock M7-M9\n')
    facts = dict(input_sha256={k: hashlib.sha256((tmp_path / p).read_bytes()).hexdigest()
                               for k, p in [('contract', 'contract.json'), ('manifest', 'manifest.json'),
                                            ('die_v', 'die.v')]},
                 channels=[[0, 0, 10, 10]], regions={'r': {'root': 'r'}},
                 crossings=[{'id': 'crossing'}], wires=[{'id': 'wire'}])
    return facts


def run(tmp_path, facts):
    if facts is not None:
        (tmp_path / 'facts.json').write_text(json.dumps(facts))
    return subprocess.run(['bash', str(SCRIPT), str(tmp_path), str(tmp_path / 'contract.json'),
                           str(tmp_path / 'facts.json'), '--check-only'], capture_output=True, text=True)


def test_missing_facts_blocks_before_reach_or_route(tmp_path):
    fixture(tmp_path)
    r = run(tmp_path, None)
    assert r.returncode == 1 and 'facts missing' in r.stderr
    assert not (tmp_path / 'safety_chain/reach_check.log').exists()


def test_foreign_facts_blocks_before_reach_or_route(tmp_path):
    facts = fixture(tmp_path)
    facts['input_sha256']['die_v'] = 'wrong'
    r = run(tmp_path, facts)
    assert r.returncode == 1 and 'actual die_v' in r.stderr


def test_missing_channels_blocks_before_reach_or_route(tmp_path):
    facts = fixture(tmp_path)
    facts['channels'] = []
    r = run(tmp_path, facts)
    assert r.returncode == 1 and 'census required' in r.stderr


def test_m9_signal_legacy_case_blocks_before_reach_or_route(tmp_path):
    facts = fixture(tmp_path)
    p = tmp_path / 'run.tcl'
    p.write_text(p.read_text().replace('-signal M4-M8', '-signal M4-M9'))
    r = run(tmp_path, facts)
    assert r.returncode == 1 and 'M9 PG/clock only' in r.stderr


def test_stale_m6_rc_blocks_before_reach_or_route(tmp_path):
    facts = fixture(tmp_path)
    p = tmp_path / 'run.tcl'
    p.write_text(p.read_text().replace('-signal -layer M8', '-signal -layer M6'))
    r = run(tmp_path, facts)
    assert r.returncode == 1 and 'M8 RC and TT+FF required' in r.stderr
