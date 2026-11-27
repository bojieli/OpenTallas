import json
import sys
from pathlib import Path

import pytest

tools = Path(__file__).resolve().parent
sys.path[:0] = [str(tools), str(tools.parent / 'autopilot')]
from archive_gate import Gate
from count_hourly import index_rows
from count_signoff import archive_record_counts, counts_signed
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
    (dict(signoff(local='SIGNED'), profile='legacy', verdict='LOCAL_PASS_NEEDS_PARENT',
          reasons=['io_hold_parent: boundary hold deferred to die STA'], probe=False), True),
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


@pytest.mark.parametrize('marker', [
    {'probe': True},
    {'checks': {'probe_through': {'verdict': 'FAIL'}}},
    {'reasons': ['probe_through: FAIL probe kit']},
])
def test_probe_cannot_count_even_with_passing_measurements(marker):
    record = signoff()
    record['checks'].update(marker.get('checks', {}))
    record.update({k: v for k, v in marker.items() if k != 'checks'})
    assert not counts_signed(record)
    assert not archive_record_counts(record, declared_minimal=True)
    assert not counts_signed(dict(record, profile='legacy'))
    remote = {}
    exec(PROV_PY, remote)
    assert not remote['counts_signed'](record)


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


def test_exact_odb_revocation_preserves_a_later_same_name_replacement(tmp_path, monkeypatch):
    import count_hourly
    from release_tree_plan import revoke_hit

    coord = tmp_path / 'coord'
    (coord / 'lanes').mkdir(parents=True)
    monkeypatch.setattr(count_hourly, 'COORD', coord)
    odb_old = 'ae' * 32
    odb_new = 'cf' * 32
    (coord / 'lanes/COUNT-REVOKED.tsv').write_text(
        f'qc\tcoll_ucie\todb_sha256:{odb_old}\tfloating PHY clock\n')
    root = tmp_path / 'store'
    manifest = {
        'id': 'a1' * 32, 'origin': 'e7:/old/signoff.json', 'scan': {'name': 'coll_ucie'},
        'files': [['/old/6_final.odb', 10, odb_old]],
    }
    assert signed_store.write_entry(manifest, str(root))
    records, _ = signed_store.load_records(str(root))
    selectors = [{'name': 'coll_ucie', 'key': 'odb_sha256:' + odb_old}]
    assert revoke_hit(records[0], selectors)
    assert not revoke_hit(dict(records[0], odb_sha=odb_new), selectors)

    header = 'die\telement\tkind\trecord\tdb\trtx_db\tsize\tsha256\tpack\tmeta\tstatus\tsrc'
    def row(name, sha):
        return '\t'.join(['qwen_compute', name, 't', '', '', '', '', sha, '',
                          '/archive/' + name + '/signoff.json', 'ARCHIVED-BOTH', 'legacy'])
    path = tmp_path / 'index.json'
    path.write_text(json.dumps({
        'agidock': [], 'agidock_listed': 100,
        'agidock_index_tsv': '\n'.join([header, row('coll_ucie__legalrows_1117', odb_old),
                                        row('coll_ucie', odb_old), row('coll_ucie', odb_new)]),
    }))
    assert index_rows(path) == [('qwen_compute', 'coll_ucie', 't')]
    gate = Gate(path, root, now=100, coord=coord)
    assert gate.index[('qwen_compute', 'coll_ucie')]['sha256'] == odb_new
    assert ('qwen_compute', 'coll_ucie__legalrows_1117') not in gate.index
