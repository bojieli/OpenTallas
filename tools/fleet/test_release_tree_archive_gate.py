"""archive_gate: signed only when the AGIdock archive holds DB + view + metadata (non-empty); else pending archive."""
import json, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import archive_gate as G


def listing(tmp, entries, age=0, tsv=None):
    p = tmp / 'ai.json'
    p.write_text(json.dumps(dict(agidock=[dict(die=d, name=n, path='/archive/opentallas-signed-1114/%s/%s' % (d, n), files=f) for d, n, f in entries],
                                 agidock_listed=time.time() - age, agidock_index_tsv=tsv)))
    return p


FULL = {'6_final.odb': 10, '6_final.v': 5, 'signoff.json': 3}


def cache():
    return dict(errors=[], plans={'s81/p.json': dict(die='s81', designs={'d1': dict(module='core_a'), 'd2': dict(module='core_b')},
                signed_types={'t_full': ['r'], 't_noview': ['r'], 't_zero': ['r'], 't_fleet': ['r'], 't_tsv': ['r'], 't_target': ['r']},
                signed_cores={'core_a': ['r'], 'core_b': ['r']}, signed_designs={'d1': ['r'], 'd2': ['r']})})


def run(tmp_path, **kw):
    L = listing(tmp_path, [('s81', 't_full', FULL), ('s81', 't_noview', {'6_final.odb': 10, 'signoff.json': 3}), ('s81', 't_zero', {'6_final.odb': 0, '6_final.v': 5, 'signoff.json': 3}),
                            ('DeepSeek_ROM', 't_target', FULL), ('s81', 'core_a', FULL)], tsv='# h\nt_tsv\tx\n', **kw)
    return G.apply(cache(), G.Gate(listing=L, store=tmp_path / 'nostore'))


def test_gate_moves_unarchived_to_pending(tmp_path):
    c = run(tmp_path); e = c['plans']['s81/p.json']
    assert sorted(e['signed_types']) == ['t_full', 't_noview', 't_target', 't_tsv']   # no view file: still counted
    assert sorted(e['pending_archive_types']) == ['t_fleet', 't_zero']
    assert 't_noview' in e['archive_gate']['no_view_pack']
    assert sorted(e['signed_cores']) == ['core_a'] and sorted(e['pending_archive_cores']) == ['core_b']
    assert sorted(e['signed_designs']) == ['d1'] and sorted(e['pending_archive_designs']) == ['d2']
    w = e['archive_gate']['why']
    assert w['t_zero']['missing'] == ['db'] and w['t_zero']['zero_byte'] == ['6_final.odb']
    assert w['t_fleet']['missing'] == ['db', 'metadata']
    assert c['archive_gate']['applied'] and c['archive_gate']['dies']['s81']['pending_archive_types'] == 2


def test_ungate_restores_credited_and_is_idempotent(tmp_path):
    c = run(tmp_path); u = G.ungate(c)
    assert u['plans']['s81/p.json']['signed_types'].keys() == cache()['plans']['s81/p.json']['signed_types'].keys()
    assert 'pending_archive_types' not in u['plans']['s81/p.json']
    L = tmp_path / 'ai.json'
    c2 = G.apply(u, G.Gate(listing=L, store=tmp_path / 'nostore'))
    assert sorted(c2['plans']['s81/p.json']['signed_types']) == ['t_full', 't_noview', 't_target', 't_tsv']


def test_stale_or_missing_listing_does_not_gate_and_says_so(tmp_path):
    c = run(tmp_path, age=G.MAX_AGE_S + 60)
    assert len(c['plans']['s81/p.json']['signed_types']) == 6 and not c['archive_gate']['applied']
    assert any('ARCHIVE GATE NOT APPLIED' in e for e in c['errors'])
    c = G.apply(cache(), G.Gate(listing=tmp_path / 'absent.json'))
    assert not c['archive_gate']['applied'] and len(c['plans']['s81/p.json']['signed_cores']) == 2


def test_index_tsv_status_decides(tmp_path):
    tsv = 'die\telement\tkind\trecord\tdb\trtx_db\tsize\tsha256\tpack\tmeta\tstatus\tsrc\n' \
          's81\tt_fleet\tt\tr\t/a/db\t/h/db\t1\tx\t_view-packs/s81.t.t_fleet/j.json\t/a/m\tARCHIVED-BOTH\texplorer\n' \
          's81\tt_zero\tt\tr\t/a/db\t/h/db\t1\tx\t\t/a/m\tARCHIVED-BOTH-NO-VIEWPACK\texplorer\n' \
          's81\tcore_b\tc\tr\t\t\t\t\t\t\tNO-DB\texplorer\n'
    L = listing(tmp_path, [('s81', 't_full', FULL)], tsv=tsv)
    c = G.apply(cache(), G.Gate(listing=L, store=tmp_path / 'nostore')); e = c['plans']['s81/p.json']
    assert 't_fleet' in e['signed_types'] and 't_zero' in e['signed_types'] and 't_full' in e['signed_types']
    assert 't_zero' in e['archive_gate']['no_view_pack'] and 't_fleet' not in e['archive_gate']['no_view_pack']
    assert 'core_b' in e['pending_archive_cores'] and e['archive_gate']['why']['core_b']['index_status'] == 'NO-DB'


def test_index_tsv_newest_row_per_element_wins(tmp_path):
    head = 'die\telement\tkind\trecord\tdb\trtx_db\tsize\tsha256\tpack\tmeta\tstatus\tsrc\n'
    tsv = head + 's81\tt_fleet\tt\tr\t\t\t\t\t\t\tNO-DB\texplorer\n' + 's81\tt_fleet\tt\tr\t/a/db\t/h/db\t1\tx\t\t/a/m\tARCHIVED-BOTH\texplorer\n' \
               + 's81\tt_zero\tt\tr\t/a/db\t/h/db\t1\tx\t\t/a/m\tARCHIVED-BOTH\texplorer\n' + 's81\tt_zero\tt\tr\t\t\t\t\t\t\tNO-DB\texplorer\n'
    c = G.apply(cache(), G.Gate(listing=listing(tmp_path, [], tsv=tsv), store=tmp_path / 'nostore')); e = c['plans']['s81/p.json']
    assert 't_fleet' in e['signed_types'], 'older NO-DB row then ARCHIVED-BOTH: the later row decides'
    assert 't_zero' in e['pending_archive_types'], 'the later row decides also when it is the worse one'


def test_metadata_only_drops_routed_db_files(monkeypatch):
    import signed_store_ingest as si
    monkeypatch.delenv("OT_INGEST_FULL_DB", raising=False)
    fs = [["a/6_final.odb", 5], ["a/6_final.odb.zst", 5], ["a/signoff.json", 1], ["a/6_final.def", 2]]
    assert [f[0] for f in si.metadata_only(fs)] == ["a/signoff.json"]
    monkeypatch.setenv("OT_INGEST_FULL_DB", "1")
    assert len(si.metadata_only(fs)) == 4
