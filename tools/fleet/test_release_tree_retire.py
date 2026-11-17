#!/usr/bin/env python3
"""Retire-by-name / copy rules of release_tree_plan.py (FLOW-11, COORD ruling 2026-10-30 14:40). Run: python3 -m pytest -q"""
import pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import release_tree_plan as R

OLD = dict(name='dp_slice_station__t12', top='s81p_slice_station__t12', generated='2026-10-24T14:45:51-07:00', verdict='SIGNED')
TSV = ('# c\n'
       'epyc2:/x/wt/results/elem_s81_station405/B_1024/signoff/t12.signoff.json\t2026-10-30 14:09 PDT\tDIE-S81-36\tlegacy pins\n'
       'name:s81:slice_station__t12\t2026-10-30 14:09 PDT\tDIE-S81-36\tlegacy pins\n')


def rec(host, path, **kw):
    return dict(OLD, scan_host=host, path=path, **kw)


def test_parse(tmp_path):
    f = tmp_path / 'r.tsv'; f.write_text(TSV)
    assert list(R.retired_refs(f)) == ['epyc2:/x/wt/results/elem_s81_station405/B_1024/signoff/t12.signoff.json']
    n = R.retired_names(f)
    assert list(n) == [('s81', 'slice_station__t12')] and n[('s81', 'slice_station__t12')][0] == R._date_ts('2026-10-30 14:09')


def test_copy_of_retired_record_in_new_path_not_counted(tmp_path):
    f = tmp_path / 'r.tsv'; f.write_text(TSV)
    a = rec('epyc2', '/x/wt/results/elem_s81_station405/B_1024/signoff/t12.signoff.json')
    b = rec('local', '/srv/opentallas-scratch/claude/wt/fresh-1030/results/elem_s81_station405/B_1024/signoff/t12.signoff.json')
    other = dict(rec('local', '/k/signoff.json'), name='dp_slice_station__t13', top='s81p_slice_station__t13')
    kept, gone = R.split_retired([a, b, other], R.retired_refs(f))
    assert kept == [other] and len(gone) == 2 and gone[1]['retired'].startswith('COPY')


def test_name_line_retires_fresh_copy_without_path_line(tmp_path):
    f = tmp_path / 'r.tsv'; f.write_text(TSV)
    names = R.retired_names(f)
    b = rec('intel1', '/new/worktree/t12.signoff.json')          # the path-retired original is not in this scan
    kept, gone = R.split_retired([b], R.retired_refs(f))
    assert kept == [b]                                           # (a) cannot see it ...
    assert R.name_retired(b, 's81', names, ('slice_station__t12', 's81p_slice_station__t12'))   # ... (b) does
    assert R.name_retired(b, 's81_head', names, ('slice_station__t12',)) is None              # other die untouched
    assert R.name_retired(dict(b, generated=None), 's81', names, ('slice_station__t12',))      # no date -> retired


def test_new_signoff_after_retirement_counts(tmp_path):
    f = tmp_path / 'r.tsv'; f.write_text(TSV)
    new = rec('intel1', '/kits/t12/signoff/signoff.json', generated='2026-10-31T09:00:00-07:00')
    assert R.name_retired(new, 's81', R.retired_names(f), ('slice_station__t12', 's81p_slice_station__t12')) is None


def test_repo_tsv_retires_s81_legacy_stations():
    names = R.retired_names()
    for t in ('t12', 't17', 't20', 't21'):
        assert ('s81', 'slice_station__' + t) in names
        r = dict(OLD, name='dp_slice_station__' + t, top='s81p_slice_station__' + t)
        assert R.name_retired(r, 's81', names, ('slice_station__' + t, 's81p_slice_station__' + t))


def test_carry_unreachable_keeps_last_verified_credit():
    """SIGNOFF-SPRINT-17 (COORD 11-01 09:2x): a design credited only by records on a host that could not be read keeps
    its credit tagged host-unreachable; a reachable-host loss, a retired path or another host's credit is not carried."""
    import release_tree_plan as rtp
    D = {'a': dict(module='ma', instances=2), 'b': dict(module='mb', instances=1), 'c': dict(module='mc', instances=1),
         'e': dict(module='me', instances=1)}
    old = dict(generated=0, plans={'p': dict(die='s81', designs=D, signed_designs={
        'a': ['intel1:/x/a/signoff.json src 1 flow f DESIGN-MATCH pins'],
        'b': ['intel2:/x/b/signoff.json src 1 flow f DESIGN-MATCH pins'],
        'c': ['intel1:/x/c/signoff.json src 1 flow f DESIGN-MATCH pins'],
        'e': ['intel1:/x/e/signoff.json src 1 flow f DESIGN-MATCH pins']})})
    new = dict(unreachable_hosts=['intel1'], plans={'p': dict(die='s81', designs=D, signed_designs={'e': ['intel2:/y/e']},
                                                              design_unmatched={'ma': ['x']})})
    out = rtp.carry_unreachable(new, old, retired={'intel1:/x/c/signoff.json': 'r'}, names={})
    sd = out['plans']['p']['signed_designs']
    assert sorted(sd) == ['a', 'e'] and sd['e'] == ['intel2:/y/e']
    assert 'host-unreachable, last verified' in sd['a'][0] and 'ma' not in out['plans']['p']['design_unmatched']
    assert [c['design'] for c in out['carried_unreachable']] == ['a']
    # carried again on the next failed refresh: the original verification time is kept, not re-stamped
    again = rtp.carry_unreachable(dict(unreachable_hosts=['intel1'], plans={'p': dict(die='s81', designs=D, signed_designs={})}),
                                  dict(out, generated=10 ** 9), retired={}, names={})
    assert again['plans']['p']['signed_designs']['a'] == sd['a']
    # host readable again -> nothing carried
    assert rtp.carry_unreachable(dict(unreachable_hosts=[], plans={'p': dict(die='s81', designs=D, signed_designs={})}), old)['plans']['p']['signed_designs'] == {}


REV = 'head\thd_turn_a\tsha256:aa\tfstart -55.8\t2026-11-03\nhead\thd_x\tintel2:/k/v/\twhy\t2026-11-03\n# c\n'


def test_revoked_only_that_netlist_counts_new_view(tmp_path):
    f = tmp_path / 'r.tsv'; f.write_text(REV)
    rows = R.revoked_rows(f)
    bad = dict(name='dp_hd_turn_a', top='ot_s81hd_turn_a', scan_host='intel2', path='/a/signoff/signoff.json', sha='aa')
    resign = dict(bad, path='/b/signoff/signoff.json', routed_db='/k/6_final.odb')
    fresh = dict(bad, path='/c/signoff/signoff.json', sha='bb')
    other = dict(name='dp_hd_st_k5', top='ot_s81hd_st_k5', scan_host='intel2', path='/d/signoff/signoff.json', sha='aa')
    kept, gone = R.split_revoked([bad, resign, fresh, other], rows[:1], sha=lambda r: r.get('sha'))
    assert kept == [fresh, other] and len(gone) == 2 and gone[0]['retired'].startswith('COUNT-REVOKED head hd_turn_a')


def test_revoked_view_path_covers_resign_of_that_db(tmp_path):
    f = tmp_path / 'r.tsv'; f.write_text(REV)
    rows = R.revoked_rows(f)[1:]
    base = dict(name='dp_hd_x', top='ot_hd_x', scan_host='intel2')
    view, resign = dict(base, path='/k/v/signoff/signoff.json'), dict(base, path='/s/signoff.json', routed_db='/k/v/run/6_final.odb')
    sibling, host2 = dict(base, path='/k/v2/signoff/signoff.json'), dict(base, path='/k/v/signoff/signoff.json', scan_host='intel1')
    kept, gone = R.split_revoked([view, resign, sibling, host2], rows)
    assert kept == [sibling, host2] and len(gone) == 2


def test_unreadable_netlist_stays_counted_no_rows_no_calls(tmp_path):
    f = tmp_path / 'r.tsv'; f.write_text(REV)
    r = dict(name='dp_hd_turn_a', top='ot_s81hd_turn_a', scan_host='intel2', path='/a/signoff/signoff.json')
    assert R.split_revoked([r], R.revoked_rows(f)[:1], sha=lambda r: None) == ([r], [])
    assert R.split_revoked([r], [], sha=lambda r: 1 / 0) == ([r], [])
    assert R.revoked_rows(tmp_path / 'none.tsv') == []
