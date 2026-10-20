#!/usr/bin/env python3
"""MU-S81: tests of tools/s81_dv/dv_mu_calendar.py (pure python).  exit 0 = PASS

1. AR: the largest lemma-clean calendar on the owner config; every duplicated group 23/23 users a copy; latency user
   shift 0 on copy A; brute force 0 collisions; the committed record is reproduced (--check).
2. Negative controls (the checker must FAULT): 47 users (odd: one same-copy adjacency on a full-scan group), the
   latency user moved to copy B on S029 with its neighbour also on B, an MTP user squeezed into the filler gap.
3. dv_layer_compile --mu-cal tables: one row a user, ctx body {user 10, pos 21, tok 21} at body[159:108].
4. S81-L20SPLIT (0li): the split calendar keeps 46 AR / 10 + 1 MTP with the helper (S030) windows clean; the
   committed *_l20split records reproduce; negative control: a helper window longer than the slot FAULTs.
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
import dv_mu_calendar as M  # noqa: E402
import dv_layer_compile as C  # noqa: E402


def main():
    m = M.load_model()
    st = M.stage_windows(m)
    d = M.design(m)
    assert d['dies'] == 520 and d['stacks'] == 520, d['dies']
    ar = M.calendar_ar(m, st, d)
    n = len(ar['users'])
    assert n == 46, n
    bad, _ = M.collisions(st, ar['users'], ar['P'], ar['col'])
    assert not bad
    for gid, c in ar['col'].items():
        assert c[0] == 'A' and sorted(c.values()).count('A') == 23, gid
    # 47 users: FAIL with an explanation, never silently accepted
    a47 = M.calendar_ar(m, st, d, N=47)
    assert not a47['users'] and a47['tried'][0]['result'] == 'FAIL' and 'S0' in a47['tried'][0]['why']
    # force 47 with plain alternation: brute force must see the clash
    P = ar['P']
    u47 = [dict(user=k, shift=(k * P) // 47, kind='ar') for k in range(47)]
    col = {g: {k: M.COPIES[k % 2] for k in range(47)} for g in M.DUP}
    bad, _ = M.collisions(st, u47, P, col)
    assert any(b['resource'].startswith('S029.A') for b in bad), bad[:3]
    # mutant: user 1 moved onto user 0's copy on S029
    col = {g: dict(c) for g, c in ar['col'].items()}
    col['S029'][1] = 'A'
    bad, _ = M.collisions(st, ar['users'], P, col)
    assert any(b['resource'] == 'S029.A' and sorted(b['users']) == [0, 1] for b in bad)
    # MTP: 10 users + fillers clean; an 11th MTP user in the gap must collide
    mt = M.calendar_mtp(m, st, d)
    assert len([u for u in mt['users'] if u['kind'] != 'filler']) == 10
    assert not M.collisions(st, mt['users'], mt['P'], mt['col'])[0]
    u11 = [u for u in mt['users'] if u['kind'] != 'filler'] + [dict(user=10, shift=10 * mt['S'], kind='mtp')]
    col = {g: {**c, 10: 'A'} for g, c in mt['col'].items()}
    assert M.collisions(st, u11, mt['P'], col)[0]
    # committed records reproduce
    assert M.main(['--check']) == 0
    # layer compiler tables
    cal = json.loads((M.OUT / 'calendar_ar.json').read_text())
    t = C.mu_slot_tables(cal, 'L20')
    assert len(t['rows']) == 46 and t['users_per_copy'] == {'A': 23, 'B': 23}
    r1 = [r for r in t['rows'] if r['user'] == 1][0]
    assert (int(r1['ctx_body'], 16) >> 108) >> 42 == 1 and r1['copy'] == 'B' and r1['local'] == 0
    # L20 split: helper-die windows in the calendar check
    for mode, n_users in (('ar', 46), ('mtp', 10)):
        r = M.build(mode, split=M.split_config())
        c = r['l20_split']['check']
        assert r['users'] == n_users and c['result'] == 'PASS' and c['n_collisions'] == 0, (mode, r['users'], c)
        assert r['lemma']['brute_force']['result'] == 'PASS'
    bad_sp = dict(M.SPLIT_L20, helper_window_ar=int(ar['P'] / 46) + 1000)
    assert M.build('ar', split=bad_sp)['l20_split']['check']['result'] == 'FAULT'
    assert M.main(['--check', '--l20-split']) == 0
    print('PASS test_dv_mu_calendar')


if __name__ == '__main__':
    main()
