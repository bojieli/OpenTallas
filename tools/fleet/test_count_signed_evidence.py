import json
import sys
from pathlib import Path

import pytest

tools = Path(__file__).resolve().parent
sys.path[:0] = [str(tools), str(tools.parent / 'autopilot')]
from archive_gate import Gate
from count_hourly import index_rows
from count_signoff import counts_signed
from release_tree_plan import PROV_PY
import signed_store


def signoff(wns=0.0, nviol=0, truncated=0, local='NOT SIGNED'):
    return {
        'profile': 'minimal', 'verdict': 'SIGNED', 'local_verdict': local,
        'release_qualified': False,
        'checks': {
            'drc': {'count': 0}, 'setup_tt': {'wns_ps': -10.48},
            'hold_ff': {'wns_ps': -129.99, 'port_only_needs_parent': True},
        },
        'corners': {'ff': {
            'done': True, 'rc': 0, 'errors': [], 'periods': {'clk': 833},
            'std_min_start': {'err': 0, 'trunc': truncated, 'core_wns': wns, 'core_n': nviol},
        }},
    }


@pytest.mark.parametrize('record,want', [
    (signoff(), True),
    (signoff(truncated=1, local='SIGNED'), False),
    (signoff(wns=-2.5, nviol=1, local='SIGNED'), False),
    ({'profile': 'minimal', 'verdict': 'SIGNED'}, False),
    ({'verdict': 'SIGNED'}, True),
])
def test_local_and_remote_counter_measurement(record, want):
    remote = {}
    exec(PROV_PY, remote)
    assert counts_signed(record) is want
    assert remote['counts_signed'](record) is want


def test_archive_counts_only_matching_measured_record(tmp_path, monkeypatch):
    root = tmp_path / 'store'
    monkeypatch.setattr(signed_store, 'STORE', str(root))
    ident = 'a1' * 32
    old = 'a2' * 32
    path = tmp_path / 'index.json'
    header = 'die\telement\tkind\trecord\tdb\trtx_db\tsize\tsha256\tpack\tmeta\tstatus\tsrc'
    def row(name, record, meta):
        return '\t'.join(['qwen_compute', name, 't', record, '', '', '', '', '', meta,
                          'RTX-FULL-AGI-META', 'AUTO-EXPORT R-MINIMAL: SIGNED'])
    good_path = '/archive/eco/signoff.json'
    unrelated_path = '/archive/another/signoff.json'
    path.write_text(json.dumps({
        'agidock': [], 'agidock_listed': 100,
        'agidock_index_tsv': '\n'.join([header, row('good', ident, good_path),
                                        row('good', old, '/archive/old/signoff.json'),
                                        row('unknown', 'a3' * 32, '/archive/missing/signoff.json')]),
        'agidock_count_signoffs': {good_path: signoff(), unrelated_path: signoff()},
    }))
    bad = {
        'id': old, 'origin': 'host:/old/signoff.json', 'verdict': 'SIGNED',
        'signoff_json': signed_store.blob(signoff(truncated=1)),
    }
    assert signed_store.write_entry(bad, str(root))
    assert signed_store.load_records(str(root), eligible=counts_signed)[0] == []
    assert index_rows(path) == [('qwen_compute', 'good', 't')]
    gate = Gate(path, root, now=100)
    assert gate.index[('qwen_compute', 'good')]['record'] == ident
    assert gate.check('qwen_compute', ['unknown'])[0] is None
