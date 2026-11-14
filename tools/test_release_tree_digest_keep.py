#!/usr/bin/env python3
"""DIGEST-KEEP of release_tree_plan.py (EXPERT-REVIEW-4 / COORD 2026-11-13, PROFILE-1): a plan event keeps the count of a
type whose plan block digest is unchanged, also when a class re-split renamed it. Run: python3 -m pytest -q"""
import hashlib, json, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import release_tree_plan as R

BLK = dict(module='slice_station', clock=dict(core_taps=[[1, 2]]), outline_um=[100, 200])


def plan(types, budgets=None):
    return dict(partition_types=types, budgets=budgets or {})


def test_digest_matches_kit_wave_raw_block_identity():
    P = plan({'t1': BLK}, {'t1': dict(lat=3)})
    raw = hashlib.sha256(json.dumps({'type': BLK, 'budget': dict(lat=3)}, sort_keys=True, default=str).encode()).hexdigest()
    assert R.type_blocks(P) == {'t1': raw}


def test_name_is_not_in_the_digest_and_a_change_is():
    a = R.type_blocks(plan({'slice_station__t30__clold': BLK}))['slice_station__t30__clold']
    assert R.type_blocks(plan({'slice_station__t30__clnew': BLK}))['slice_station__t30__clnew'] == a
    moved = dict(BLK, clock=dict(core_taps=[[1, 3]]))
    assert R.type_blocks(plan({'x': moved}))['x'] != a


def test_keep_renamed_unchanged_block_not_changed_block():
    led, live = {}, {'epyc2:/k/a/signoff.json', 'epyc2:/k/b/signoff.json'}
    old = R.type_blocks(plan({'t30__clold': BLK, 't31': dict(BLK, module='m31')}))
    st = {'t30__clold': ['epyc2:/k/a/signoff.json src x flow y'], 't31': ['epyc2:/k/b/signoff.json src x flow y']}
    assert R.digest_keep('s81', old, st, led, live, 'p_old') == {}
    assert len(led['s81']) == 2
    # plan event: t30 renamed (same block), t31 tap moved (block changed)
    new = R.type_blocks(plan({'t30__clnew': BLK, 't31': dict(BLK, module='m31', clock=dict(core_taps=[[9, 9]]))}))
    st2 = {'t31': ['epyc2:/k/b/signoff.json src x flow y']}   # name match still counts as before
    kept = R.digest_keep('s81', new, st2, led, live, 'p_new')
    assert list(kept) == ['t30__clnew'] and 't30__clold' in kept['t30__clnew'] and 'p_old' in kept['t30__clnew']
    assert st2['t30__clnew'] == ['epyc2:/k/a/signoff.json src x flow y' + R.DIGEST_TAG + kept['t30__clnew']]
    # the kept credit is never re-recorded with its tag; a later refresh keeps it again
    st3 = {}   # (t31 was name-counted on its new block in the last refresh, so that block is in the ledger too)
    assert sorted(R.digest_keep('s81', new, st3, led, live, 'p_new')) == ['t30__clnew', 't31']
    assert st3['t30__clnew'][0].count(R.DIGEST_TAG) == 1


def test_retired_or_gone_record_never_carries():
    led = {}
    blocks = R.type_blocks(plan({'t1': BLK}))
    R.digest_keep('s81', blocks, {'t1': ['epyc2:/k/a/signoff.json']}, led, {'epyc2:/k/a/signoff.json'}, 'p1')
    renamed = {'t1__cl2': blocks['t1']}
    st = {}
    assert R.digest_keep('s81', renamed, st, led, set(), 'p2') == {} and st == {}   # record retired / not counted now
    st = {}
    assert R.digest_keep('qwen_compute', renamed, st, led, {'epyc2:/k/a/signoff.json'}, 'p2') == {}   # other die


def test_ledger_roundtrip(tmp_path):
    f = tmp_path / 'l.json'
    assert R.load_ledger(f) == {}
    R.save_ledger({'s81': {'ab': dict(type='t', refs=['h:/p'])}}, f)
    assert R.load_ledger(f)['s81']['ab']['type'] == 't'
