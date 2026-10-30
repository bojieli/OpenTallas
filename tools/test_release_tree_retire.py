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
