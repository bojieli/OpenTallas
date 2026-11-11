"""S81-SVC-9: entry NORMR slots and the Engram REDUCE split derive from the bound leaf routes (leaf_transport)."""
import copy
import hashlib
import json
import sys
from pathlib import Path

import pytest

sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parent)]

from layer_prog import bound_control as BC
from layer_prog import entry_norm as EN
from layer_prog import leaf_transport as LT
from layer_prog import lower_vs as LV
from layer_prog import selected_entry_norm as SEL

import dv_layer_compile as D


SLICES = {f'u_s_{c}{t}': 2 * c + (t == 'N') for c in range(8) for t in 'SN'}


def totals(sid, leaf, tie=False):
    dn = 2 * leaf + sid % 3
    if tie and leaf == 3:
        dn -= 4                    # leaf 3 ties leaf 2 on dn + up + pdsk
    return dn, leaf, leaf & 1      # dn, up, pdsk: total grows with leaf, distinct across leaves


def report(tie=False):
    rows = []
    for sl, sid in SLICES.items():
        for leaf in range(5):
            dn, up, pdsk = totals(sid, leaf, tie)
            rows.append(dict(slice=sl, sid=sid, leaf=leaf, xr_command_to_leaf_boundary_edges=dn,
                             vn_b_partial_to_xr_input_edges=up, pdsk_edges=pdsk, crossing_plus_pdsk_edges=dn + up + pdsk))
    return dict(schema='opentallas.s81.emitted_leaf_boundary_routes.v1', verdict='PASS_SELECTED_BOUNDARY_WIRING',
                source_top_sha256='top', source_view_sha256='view', leaves=rows)


class Die:
    die_sha = 'top'
    source_record = dict(source_view_sha256='view')

    def __init__(self):
        self.deskew = {sl: [totals(sid, k)[2] for k in range(5)] for sl, sid in SLICES.items()}

    def slices(self):
        return {sl: dict(sid=sid) for sl, sid in SLICES.items()}


def base_entry():
    die = Die()
    readers = [dict(slice=sl, sid=sid, leaf=k, normr_a0=1008, global_beat=5 * sid + k)
               for sl, sid in SLICES.items() for k in range(5)]
    entry = dict(die_sha256='top', readers=readers, input_sources={}, fixture_meta_sha256='fx')
    return die, EN.compile_norm(die, entry, 0x2edbe6ff, first_issue=20)


def test_retime_aligns_every_leaf_on_the_route_totals_and_keeps_engine_slots_unique():
    die, prog = base_entry()
    rep = report()
    p = BC.retime_norm(prog, die, deskew_by_slice=die.deskew, leaf_routes=rep)
    table = LT.slices(rep)
    by_sl = {}
    for c in p['commands']:
        by_sl.setdefault(c['slice'], {})[c.get('leaf', 'GO')] = c['issue']
    for sl, issues in by_sl.items():
        s = table[sl]
        ends = {issues[k] + s['dn'][k] + s['up'][k] + s['pdsk'][k] for k in range(5)}
        assert len(ends) == 1
        assert issues['GO'] - max(issues[k] for k in range(5)) >= 8
    for tier in (0, 1):                   # one row per engine per edge
        edges = [c['issue'] for c in p['commands'] if (c['sid'] & 1) == tier]
        assert len(edges) == len(set(edges)) == 48
    rows = {r['tix']: r for r in p['rows']}
    assert all(rows[c['template']]['issue'] == c['issue'] and rows[c['template']]['done'] == c['issue'] + 5 for c in p['commands'])
    assert p['retime']['leaf_routes']['source_top_sha256'] == 'top'
    assert p['status'] == 'PROPOSED_CONTROL_RETIME'


def test_check_control_catches_a_one_edge_misalignment():
    die, prog = base_entry()
    rep = report()
    p = BC.retime_norm(prog, die, deskew_by_slice=die.deskew, leaf_routes=rep)
    assert SEL.check_control(p, die, rep)['normr_count'] == 80
    bad = copy.deepcopy(p)
    used = {(x['sid'] & 1, x['issue']) for x in bad['commands']}
    c = next(x for x in bad['commands'] if x['kind'] == 'NORMR' and (x['sid'] & 1, x['issue'] + 1) not in used)
    r = next(x for x in bad['rows'] if x['tix'] == c['template'])
    c['issue'] += 1
    r['issue'] += 1
    r['done'] += 1
    r['row76'] = f"{D.pack_row(r['done'], r['issue'], r['eng'], r['arg']):019x}"
    with pytest.raises(ValueError, match='leaf routes do not align'):
        SEL.check_control(bad, die, rep)


def test_tied_round_trips_are_refused_not_silently_slotted():
    die, prog = base_entry()
    with pytest.raises(ValueError, match='tie on dn'):
        BC.retime_norm(prog, die, deskew_by_slice=die.deskew, leaf_routes=report(tie=True))


def test_report_of_another_die_is_refused():
    die, prog = base_entry()
    rep = report()
    rep['source_top_sha256'] = 'other'
    with pytest.raises(ValueError, match='different emitted top'):
        BC.retime_norm(prog, die, deskew_by_slice=die.deskew, leaf_routes=rep)


def test_default_retime_is_unchanged():
    die, prog = base_entry()
    p = BC.retime_norm(prog, die, deskew_by_slice={sl: [4, 3, 2, 1, 0] for sl in SLICES})
    assert p['retime']['normr_order'] == 'five consecutive commands per actual source SID'
    assert 'leaf_routes' not in p['retime']
    gos_before = {c['slice']: c['issue'] for c in prog['commands'] if c['kind'] == 'XFIN_GO'}
    assert {c['slice']: c['issue'] for c in p['commands'] if c['kind'] == 'XFIN_GO'} == gos_before
    for ordinal, sl in enumerate(sorted((s for s in SLICES if s.endswith('S')), key=SLICES.get)):
        local = {c['leaf']: c['issue'] for c in p['commands'] if c['slice'] == sl and c['kind'] == 'NORMR'}
        assert local == {k: 20 + 5 * ordinal + k for k in range(5)}


class LvDie:
    def slices(self):
        return {'u_s_0S': dict(sid=0)}


def eng_op(tmp_path):
    rm = tmp_path / 'results/arch/s81_dv_1016/eng'
    rm.mkdir(parents=True)
    (rm / 'kv_rowmap.json').write_text(json.dumps(dict(layers=dict(L1=dict(A0=2048)))))
    return dict(op='eng.dot', start=1000.5, end=1100, id='x')


def test_engram_reduce_without_routes_is_the_single_mask_11111_beat(tmp_path, monkeypatch):
    op = eng_op(tmp_path)
    monkeypatch.setattr(LV, 'ROOT', tmp_path)
    r = LV.lower_eng(LvDie(), op, dict(layer='L1', slice='u_s_0S'), 'u_s_0S', 0)
    assert [x['what'] for x in r['rows']] == ['vs eng.dot HSTORE A0 2048 leaves 11111', 'vs eng.dot REDUCE A0 2048 leaves 11111']
    assert [x['issue'] for x in r['rows']] == [1000 - LV.ENG_HSTORE_LEAD, 1000]
    assert len(r['events']) == 5


def test_engram_reduce_splits_by_round_trip_group(tmp_path, monkeypatch):
    op = eng_op(tmp_path)
    monkeypatch.setattr(LV, 'ROOT', tmp_path)
    groups = [(0, 0b11000), (5, 0b00111)]        # leaves 3,4 issue first (longest round trip), leaves 0-2 five edges later
    ctx = dict(layer='L1', slice='u_s_0S', leaf_route_summary={'u_s_0S': dict(eng_ctls=groups)})
    r = LV.lower_eng(LvDie(), op, ctx, 'u_s_0S', 0)
    reduces = [x for x in r['rows'] if 'REDUCE' in x['what']]
    assert [x['issue'] for x in reduces] == [1000, 1005]
    assert 'leaves 11000' in reduces[0]['what'] and 'leaves 00111' in reduces[1]['what']
    assert [e['cycle'] for e in r['events']] == [1000, 1000, 1005, 1005, 1005]
    assert {e['inst'] for e in r['events'] if e['cycle'] == 1000} == {'u_s_0S.leaf3.vs', 'u_s_0S.leaf4.vs'}
    assert (r['templates'][1][1] & 0x7FFFFFF0000) != (r['templates'][2][1] & 0x7FFFFFF0000)  # leaf masks differ
    # a line-avoid edge moves the whole split, keeping the relative offsets
    ctx = dict(ctx, line_avoid={'S': frozenset({1005})})
    r = LV.lower_eng(LvDie(), op, ctx, 'u_s_0S', 0)
    assert [x['issue'] for x in r['rows'] if 'REDUCE' in x['what']] == [1001, 1006]


def offsets_table():
    return dict(plan='p', tool='t', slices=LT.summary(report()), norm_blocked=[])


def test_offsets_table_becomes_a_report_that_compiles():
    off = json.loads(json.dumps(offsets_table()))       # as read from the JSON file: tuples are lists
    rep = LT.report_from_offsets(off, 'top', 'view')
    assert LT.slices(rep) == LT.slices(report())
    assert rep['derived_from_plan_offsets']['plan'] == 'p' and rep['norm_producer_qualified'] is False
    die, prog = base_entry()
    p = BC.retime_norm(prog, die, deskew_by_slice=die.deskew, leaf_routes=rep)
    assert SEL.check_control(p, die, rep)['normr_count'] == 80


def test_offsets_table_from_another_formula_is_refused():
    off = json.loads(json.dumps(offsets_table()))
    off['slices']['u_s_0S']['norm_issue'][0] += 1
    with pytest.raises(ValueError, match='disagrees with leaf_transport on u_s_0S norm_issue'):
        LT.report_from_offsets(off, 'top')
    off = json.loads(json.dumps(offsets_table()))
    off['slices']['u_s_0S']['dn'][1] += 1
    with pytest.raises(ValueError, match='disagrees'):
        LT.report_from_offsets(off, 'top')


def vpx_routes(lo):
    return {'u_s_0N': dict(lo_after_ctl=lo)}


def test_lo_send_takes_the_leaf_value_and_default_keeps_the_constant():
    from unittest.mock import patch
    from layer_prog import lower_vpx as VP
    die = object()
    sl = {'u_s_0N': dict(sid=1), 'u_s_7N': dict(sid=15)}
    spec = [('u_s_0N', 'W', 'u_s_7N', list(range(16)), 2, None, 0, 0)]
    def emit(routes):
        rows, tpl, ev, ins = [], [], [], []
        with patch('dv_layer_compile.ctl_path', return_value={'edges': 10}):
            VP._emit(die, sl, spec, 100, rows, tpl, ev, ins, leaf_routes=routes)
        return [(r['issue'], r['what']) for r in rows]
    base = VP.leg_program(1, 'W', 15, list(range(16)), leaf=2)
    wide = VP.leg_program(1, 'W', 15, list(range(16)), leaf=2, lo_after_ctl=30)
    assert base['sends'][0]['cycle'] != wide['sends'][0]['cycle']
    assert emit(None) == emit(vpx_routes([VP.LO_AFTER_CTL] * 5))     # S81-XTIER-FIX: the bound form's value (xrt 16)
    assert emit(vpx_routes([9, 9, 30, 9, 9])) != emit(None)
    with pytest.raises(ValueError, match='no slice'):
        emit({'u_s_9N': dict(lo_after_ctl=[1] * 5)})


def test_substage_segments_do_not_overlap_when_a_later_leaf_arrives_sooner():
    from layer_prog import lower_vpx as VP
    default = VP._stage_trel(None)
    assert default == [sum(m // 8 for _, _, m in VP.STAGE_SEGS[:k]) * VP.beat_period() for k in range(len(VP.STAGE_SEGS))]
    lo = [15] * 5
    for f, (lf, _, _) in enumerate(VP.STAGE_SEGS):
        lo[lf] = 40 - 7 * f                      # each later segment's leaf has a shorter round trip
    trel = VP._stage_trel(vpx_routes(lo))
    for k in range(1, len(trel)):
        prev_leaf, _, prev_n = VP.STAGE_SEGS[k - 1]
        leaf = VP.STAGE_SEGS[k][0]
        # the first lo pair of segment k reaches xr after the last pair of segment k-1
        prev_end = trel[k - 1] + (prev_n // 8 - 1) * VP.beat_period(lo[prev_leaf]) + lo[prev_leaf]
        assert trel[k] + lo[leaf] > prev_end
