"""R-REACH re-sites the remaining writer stages after the real registered rx."""
import copy
from types import SimpleNamespace
import pytest
import clock_landings as CL
import reach_rules as RR
import reset_tree as RT


def vehicle(depth=3, width=1200.):
    stage = lambda x: dict(xy_um=[x, 200.], raw_reset='rr_t0')
    return dict(outline_um=[width, 400.], landing_relay_start_copy=True,
                clock=dict(landing_contract=dict(bands={}, pins=[
                    dict(name='cland_rstart_in', xy_um=[2., 200.]),
                    dict(name='cland_fstart_out_far', xy_um=[width - 2., 200.]),
                    dict(name='cland_fstart_out_near', xy_um=[100., 2.])]),
                    landing_reader_start=dict(depth=0, origin_rect_um=[91.36, 193.52, 108.64, 206.48], branches={}),
                    landing_writer_start=dict(depth=depth, reuse_relay_origin=True,
                        branches={b: dict(stages=[stage(100.+i*5.4) for i in range(depth-1)])
                                  for b in ('far', 'near')})))


@pytest.fixture
def taps(monkeypatch):
    monkeypatch.setattr(RT, 'consumer_taps', lambda P, tn: [('tap0', 100., 200.), ('tap1', 1000., 200.)])


def test_fixed_phase_sites_and_actual_emitter(taps):
    t = vehicle()
    p = SimpleNamespace(types={'T': t})
    original_origin = copy.deepcopy(t['clock']['landing_reader_start']['origin_rect_um'])
    assert RR.start_findings(t, 'T')[0]['writer_over']
    report = RR.fix_start(p, t, 'T')
    ws = t['clock']['landing_writer_start']
    assert ws['depth'] == 3 and ws['reuse_relay_origin'] is True
    assert all(len(b['stages']) == 2 for b in ws['branches'].values())
    assert t['clock']['landing_reader_start']['origin_rect_um'] == original_origin
    assert report['writer']['phase_changed'] is False
    assert RR.start_findings(t, 'T')[1] == []
    # Consume the fixed plan with the actual RTL emitter: stage0 takes the RX Q,
    # never its D, and two new physical stages implement logical phase3.
    l = CL.Landings.__new__(CL.Landings)
    l.types, l.plan = {'T': t}, {'partition_types': {'T': t}}
    l.ca_type, l.reset_placements = {'T': {'role': ('relay',)}}, {}
    body = 'ot_dp_rrelay u_r0 (.clk(clk), .d(r), .q(rr_t0));\not_dp_rrelay u_r1 (.clk(clk), .d(r), .q(rr_t1));'
    logic = []
    l._writer_start_rtl('T', 'far', '', body, logic)
    assert '.d(cland_start), .q(cland_writer_start_far_0)' in '\n'.join(logic)
    assert l.reset_placements['T']['far']['writer_start']['depth'] == 3
    before = copy.deepcopy(t)
    assert RR.fix_start(p, t, 'T')['changed'] == [] and t == before


def test_insufficient_phase_fails_without_partial_edit(taps):
    t = vehicle(depth=2)
    before = copy.deepcopy(t)
    with pytest.raises(ValueError, match='rerun REGION/STA/K'):
        RR.fix_start(SimpleNamespace(types={'T': t}), t, 'T')
    assert t == before


def test_requires_actual_pinned_relay_copy(taps):
    for mode in ['no_copy', 'no_home', 'nonrelay']:
        t = vehicle()
        if mode == 'no_copy': t['landing_relay_start_copy'] = False
        if mode == 'no_home': t['clock']['landing_reader_start'].pop('origin_rect_um')
        if mode == 'nonrelay': t['clock']['landing_contract']['pins'][0]['name'] = 'cland_tstart_in'
        before = copy.deepcopy(t)
        with pytest.raises(ValueError, match='pinned actual relay rx'):
            RR.fix_start(SimpleNamespace(types={'T': t}), t, 'T')
        assert t == before


def test_obstacle_route_and_short_path_dwell():
    o, dst = (100., 200.), (1000., 200.)
    obs = [[450., 100., 550., 300.]]
    free = lambda p: tuple(p)
    sites = RR._reuse_writer_sites(o, dst, 3, obs, [], 1200., 400., free, 405.)
    assert len(sites) == 3 and all(not (450<x<550 and 100<y<300) for x,y in sites)
    assert max(RR.man(a,b) for a,b in zip([o]+sites, sites+[dst])) <= 405.
    dwell = RR._reuse_writer_sites(o, o, 2, [], [], 1200., 400., free, 405.)
    assert len(dwell) == 2 and all(RR.man(o,p) <= RR.PAD_SPAN_UM for p in dwell)
