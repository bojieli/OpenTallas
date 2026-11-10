"""S81-PLAN-1 11-10: the S81 static control lanes are scheduled from the bound depths (bound_ctl_lanes); +-1 on any lane
moves exactly its terms, a missing / unbound lane fails closed, and lower_bk's rank tree dates the query fan-out and
the child legs from them."""
import json
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from layer_prog import bound_ctl_lanes as BC  # noqa: E402
from layer_prog import lower_bk as LB  # noqa: E402

# bind6 / final 65648816 depths for the timed lanes (other lanes 1)
BASE = dict(tl__bk_sel__s_0N_LP=58, ca__s_0N_LP__bk_sel=59, cb__s_0N_LP__bk_sel=58, qc__iqf__s_0N_LP=76,
            ql__s_0N_LP__iqf=77, tp__bk_sel__s_7N_LP=37, tp__bk_sel__s_7S_LP=50, tp__s_0S_LP__s_0N_LP=40,
            tp__s_7N_LP__bk_sel=60, idx__svc_14__bk_sel=102, idx__s_3S_C__iqf=62, unit__seqhost__s_0N_LP=77,
            unit__seqhost__s_0S_LP=41, unit__seqhost__s_7N_LP=89, unit__seqhost__s_7S_LP=53,
            ctrl__s_0N_LP__seqhost=78, unit__s_7N_LP__seqhost=88)


def bind(**over):
    v = {k: BASE.get(k, 1) for k in BC.LANES}
    v.update(over)
    return dict(buses=[dict(lane=k, bound_stages=n, plan_cycles=n) for k, n in v.items()] +
                [dict(lane='rt_E0_in_0', bound_stages=5, plan_cycles=5)])


def test_load_and_fail_closed(tmp_path):
    a = BC.load(bind())
    assert a['qc__iqf__s_0N_LP'] == 76 and set(a) == set(BC.LANES)
    (tmp_path / 'bind_latency.json').write_text(json.dumps(bind()))
    assert BC.load(tmp_path) == a
    b = bind()
    b['buses'][0]['plan_cycles'] += 1
    with pytest.raises(ValueError):
        BC.load(b)
    b = bind()
    b['buses'] = [x for x in b['buses'] if x['lane'] != 'tp__s_7N_LP__bk_sel']
    with pytest.raises(ValueError):
        BC.load(b)


def test_every_event_class_has_a_reader():
    # TYPE-SAFE-5 11-10 06:25: the 30 control lanes with no class-map row (attn hub->svc already had one)
    ts5 = ['ca__s_0N_LP__bk_sel', 'cb__s_0N_LP__bk_sel', 'ctrl__s_0N_C__seqhost', 'ctrl__s_0N_LP__seqhost',
           'flt__gunit__s_3N_C', 'idx__s_3S_C__iqf', 'idx__svc_14__bk_sel', 'qc__iqf__s_0N_LP', 'ql__s_0N_LP__iqf',
           'tl__bk_sel__s_0N_LP', 'tp__bk_sel__s_7N_LP', 'tp__bk_sel__s_7S_LP', 'tp__s_0S_LP__s_0N_LP',
           'tp__s_7N_LP__bk_sel', 'unit__s_7N_LP__seqhost', 'unit__seqhost__eng', 'unit__seqhost__gunit',
           'unit__seqhost__s_0N_C', 'unit__seqhost__s_0N_LP', 'unit__seqhost__s_0S_LP', 'unit__seqhost__s_7N_LP',
           'unit__seqhost__s_7S_LP', 'unit__seqhost__svc_11', 'unit__seqhost__svc_5', 'unit__svc_11__seqhost',
           'unit__svc_5__seqhost', 'vid_seqhost__svc_0', 'vid_svc_1__seqhost', 'attn__svc_5__s_3S_C',
           'attn__svc_11__s_4S_C']
    assert len(ts5) == 30 and set(ts5) <= set(BC.LANES)


def test_terms_and_plus_minus_one():
    t = BC.idxnet(BC.load(bind()))
    assert t['tree_legs'] == {2: 846, 3: 845}
    assert t['query_lane'] == 153 and BC.query_offset(t, 0) == 0 and BC.query_offset(t, 2) == 2 * 882
    assert BC.tp4_on_die(t) == 50 + 60
    for lane, field in (('tl__bk_sel__s_0N_LP', 'tree'), ('qc__iqf__s_0N_LP', 'q'), ('ql__s_0N_LP__iqf', 'q'),
                        ('tp__bk_sel__s_7S_LP', 'tp'), ('tp__s_7N_LP__bk_sel', 'tp')):
        for d in (1, -1):
            u = BC.idxnet(BC.load(bind(**{lane: BASE[lane] + d})))
            if field == 'tree':
                assert max(u['tree_legs'].values()) == 846 + d
            elif field == 'q':
                assert BC.query_offset(u, 3) == BC.query_offset(t, 3) + 3 * d
            else:
                assert BC.tp4_on_die(u) == 110 + d
    # the shorter hop of each TP4 pair does not move the static date until it becomes the longest
    assert BC.tp4_on_die(BC.idxnet(BC.load(bind(tp__bk_sel__s_7N_LP=38)))) == 110


def test_mu_rx_window():
    m = BC.mu_transport(BC.load(bind()))
    assert m['7N'] == dict(out=89, ret=88) and m['0S'] == dict(out=41)
    assert BC.check_rx_window(m, 0, 179) == {}
    assert BC.check_rx_window(m, 0, 178) == {'7N': 178}


def test_svc_cross_check():
    a = BC.load(bind(unit__seqhost__svc_5=9, unit__svc_5__seqhost=10, unit__seqhost__svc_11=15,
                     unit__svc_11__seqhost=16))
    ok = {lk: dict(age_edges=a[ln], legacy_age_edges=40) for lk, ln in BC.SVC_LINKS.items()}
    assert BC.svc_cross_check(a, ok) == {}
    bad = dict(ok, jd_W={'legacy_age_edges': 47})
    assert set(BC.svc_cross_check(a, bad)) == {'jd_W'}
    bad = dict(ok, jw_E_l0=dict(age_edges=16, legacy_age_edges=42))
    assert set(BC.svc_cross_check(a, bad)) == {'jw_E_l0'}


def _fx(tmp, q4=512, seed=3):
    rng = np.random.default_rng(seed)
    n = 4 * q4
    s = (-(1.0 + rng.random(n))).astype(np.float32)
    s = (s.view(np.uint32) & 0xFFFF0000).view(np.float32).astype(np.float64)
    kr = min(LB.K_MAX, q4)
    loc = np.concatenate([np.sort(LB.topk_lowest_index(LB.bf16_key(s[r * q4:(r + 1) * q4]),
                                                       np.arange(r * q4, (r + 1) * q4), kr)) for r in range(4)])
    (tmp / 'ops').mkdir()
    s.tofile(tmp / 'ops/attn.idx.score.bin')
    loc.astype(np.int64).tofile(tmp / 'ops/attn.idx.topk_local.bin')
    (tmp / 'ops.json').write_text(json.dumps({'attn.idx.score': dict(dtype='float64', shape=[n]),
                                              'attn.idx.topk_local': dict(dtype='int64', shape=[len(loc)])}))
    return tmp


def test_rank_tree_query_offset_from_bind(tmp_path):
    fx = _fx(tmp_path)
    t = BC.idxnet(BC.load(bind()))
    q = lambda h: BC.query_offset(t, h)
    plans, summ = LB.job_rank_tree_rd(fx, k_dies=3, t_q=200, leg=846, q_off=q)
    assert summ['closure']
    for d, p in plans.items():
        assert p['e0'] == 200 + q(p['depth'])
    t1 = BC.idxnet(BC.load(bind(ql__s_0N_LP__iqf=78)))
    p1, _ = LB.job_rank_tree_rd(fx, k_dies=3, t_q=200, leg=846, q_off=lambda h: BC.query_offset(t1, h))
    assert all(p1[d]['e0'] == plans[d]['e0'] + plans[d]['depth'] for d in plans)
    legacy, _ = LB.job_rank_tree_rd(fx, k_dies=3, t_q=200, leg=846)
    assert all(legacy[d]['e0'] == 200 + 846 * legacy[d]['depth'] for d in legacy)


def test_hwin_book_bound_transport():
    from layer_prog import native_hwin_calendar as NH
    bt = BC.hwin_bound_transport(BC.load(bind()))
    assert bt == {'s_0N': 77, 's_0S': 41, 's_7N': 89, 's_7S': 53}
    ev = dict(event=0, kind=0, endpoint=2, endpoint_name='s_0N', pin_visible_after_edge=500)
    led = dict(events=[ev], clock_reset_identity='ck')
    row = lambda tr: dict(ev, consumer_sampling_edge=500 + tr, transport_edges=tr, consumer_source='lep')
    book = lambda tr: dict(schema='opentallas.s81.native_hwin_consumer_booking.v1', clock_reset_identity='ck',
                           resource=['r'], events=[row(tr)])
    assert NH.check_consumer_book(led, book(77), ('r',), bound_transport=bt) == []
    for d in (1, -1):
        p = NH.check_consumer_book(led, book(77 + d), ('r',), bound_transport=bt)
        assert [x['cause'] for x in p] == ['native_HWIN_consumer_transport_not_bound_depth']
    assert NH.check_consumer_book(led, book(76), ('r',)) == []        # legacy call unchanged
