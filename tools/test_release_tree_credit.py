#!/usr/bin/env python3
"""COUNT-CREDIT rows of release_tree_plan.py (COUNT-AUDIT-1 2026-11-05). Run: python3 -m pytest -q"""
import pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import release_tree_plan as R

TAG = 'a201f608d85fef242ef78721193072e15c7106ae'
ROW = 'qwen_kvsys\tqkd_hr_core_order\tintel1:/s2/dkv79/ord/rs_o4f_c\tflow-20261106-c-kv\tCOORD 13:00 BDD\tbdd 16/16 UNSAT\n'


def rec(path='/s2/dkv79/ord/rs_o4f_c/signoff/signoff.json', host='intel1', top='qkd_hr_core_order', **kw):
    r = dict(path=path, scan_host=host, name='hc_%s__328_32x328_32' % top, top=top, versioned=False)
    r.update(kw)
    return r


def rows(tmp_path, text=ROW):
    f = tmp_path / 'COUNT-CREDIT.tsv'; f.write_text('# die\tname\tkey\tflow_tag\truling\tevidence\n' + text)
    return R.credit_rows(f)


def test_row_versions_that_view_at_tag_commit(tmp_path):
    r = rec(); done = R.apply_credit([r], rows(tmp_path), tag_commit=lambda t: TAG)
    assert len(done) == 1 and r['versioned'] and r['src_commit'] == TAG and r['flow_tag'] == 'flow-20261106-c-kv'
    assert 'COORD 13:00 BDD' in r['credit'] and not R.is_legacy(r, 0)


def test_other_dir_host_or_name_not_credited(tmp_path):
    rs = [rec(path='/s2/dkv79/ord/o4f_i1/signoff/signoff.json'), rec(host='epyc4'), rec(top='qkd_kvs_pcc'),
          rec(path='/s2/dkv79/ord/rs_o4f_c2/signoff/signoff.json')]
    assert R.apply_credit(rs, rows(tmp_path), tag_commit=lambda t: TAG) == []
    assert not any(r['versioned'] for r in rs)


def test_unknown_tag_credits_nothing(tmp_path):
    r = rec()
    assert R.apply_credit([r], rows(tmp_path), tag_commit=lambda t: '') == []
    assert R.apply_credit([r], rows(tmp_path, ROW.replace('flow-20261106-c-kv', 'my-tag')), tag_commit=lambda t: TAG) == []
    assert not r['versioned']


def test_versioned_record_left_alone(tmp_path):
    r = rec(versioned=True, src_commit='abc', flow_tag='flow-20261105-k-kv')
    assert R.apply_credit([r], rows(tmp_path), tag_commit=lambda t: TAG) == [] and r['src_commit'] == 'abc'


def test_missing_file_no_rows(tmp_path):
    assert R.credit_rows(tmp_path / 'none.tsv') == []
