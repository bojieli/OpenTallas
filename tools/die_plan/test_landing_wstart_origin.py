"""CLAND-WSTART-1: the writer START chain is relocated around hard cores from its origin home (like the reader chain);
a chain clear of cores is unchanged."""
import landing_place as LP

md = lambda a, b: abs(a[0] - b[0]) + abs(a[1] - b[1])


def vehicle(stages, cores=True):
    return {'outline_um': [1200.0, 2500.0],
            'hard_cores': [{'origin_um': [86.0, 69.0], 'outline_um': [458.0, 1158.0]}] if cores else [],
            'clock': {'landing_reader_start': {'origin_rect_um': [247.0, 61.5, 264.3, 78.8], 'branches': {}},
                      'landing_writer_start': {'depth': len(stages), 'branches': {'y_o': {'stages': [
                          {'xy_um': xy, 'raw_reset': 'rst_n_t0'} for xy in stages]}}}}}


def chain(t):
    return [LP._centre(r) for name, r, tag in LP._writer_start_groups(t) if tag == 'writer-start:y_o']


def test_origin_hop_bounded_when_stages_cross_a_core():
    stages = [[224.3, 369.9], [192.6, 674.1], [160.9, 978.4], [129.1, 1282.7], [97.4, 1586.9]]
    t = vehicle(stages)
    o = LP._start_origin_xy(t)
    cs = chain(t)
    hops = [md(o, cs[0])] + [md(a, b) for a, b in zip(cs, cs[1:])]
    assert max(hops) < 500, hops                        # unanchored: origin -> stage 0 > 1100 um (cbn_q11 -1065.5 ps)
    old = [LP._centre(r) for r in LP._chain_clear_of_hard_cores(t, None, t['clock']['landing_writer_start']['branches']['y_o']['stages'])]
    assert md(o, old[0]) > 1100                         # the bug this guards


def test_chain_clear_of_cores_is_unchanged():
    stages = [[600.0, 300.0], [600.0, 600.0], [600.0, 900.0]]
    t = vehicle(stages)
    assert chain(t) == [tuple(xy) for xy in stages] or chain(t) == [(x, y) for x, y in stages]
    t2 = vehicle([[224.3, 369.9], [192.6, 674.1]], cores=False)
    assert chain(t2) == [(224.3, 369.9), (192.6, 674.1)]


def test_origin_sources():
    t = vehicle([[600.0, 300.0]])
    assert LP._start_origin_xy(t) == LP._centre([247.0, 61.5, 264.3, 78.8])
    del t['clock']['landing_reader_start']
    assert LP._start_origin_xy(t) is None
    t['clock']['landing_origin_rect_um'] = [10.0, 10.0, 20.0, 20.0]
    assert LP._start_origin_xy(t) == (15.0, 15.0)
