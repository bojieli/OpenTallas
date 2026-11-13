"""Sparse outline streets require authoritative, unquantized empty footprints."""
import pytest
import street_rule as SR
from test_street_rule import core, face


def sparse_core():
    return core('c', 300., 12.96, 270., 200., {'S': face(81, 0, 270)})


def findings(t):
    c = sparse_core()
    cfg = SR.type_cfg(dict(SR.DEFAULTS), t, 'T', [c])
    return SR.outline_rule(c, 1000., 1000., cfg)


def test_missing_occupancy_context_never_waives():
    v = SR.outline_rule(sparse_core(), 1000., 1000., dict(SR.DEFAULTS))
    assert v[0]['need'] == 43.2 and not v[0]['sparse']
    assert findings({}) == []


@pytest.mark.parametrize('t', [
    # Old 8.64 census centre rounds to y12.96, exactly OUTSIDE the open strip.
    {'ft_slots': [dict(bit_sites_um=[[[400., 12.95]]])]},
    # Even a centre outside the strip still occupies it through the real cell footprint.
    {'ft_slots': [dict(bit_sites_um=[[[400., 13.]]])]},
    {'ft_slots': [dict(regs_um=[[400., 14.]])]},
    {'internal_stations': [dict(regs_um=[[400., 16.]], bits=1)]},
    {'reset': dict(local_taps_um=[[400., 16.]])},
    {'clock': dict(taps=[dict(xy=[400., 16.])])},
    {'clock': dict(landing_contract=dict(collector_tree=dict(relays=[dict(xy=[400., 6.])])) )},
    {'clock': dict(die_islands_um=[[390., 10., 410., 18.]])},
    {'clock': dict(landing_reader_start=dict(origin_rect_um=[390., 10., 410., 18.]))},
    {'clock': dict(landing_writer_start=dict(branches={'q': dict(stages=[dict(xy_um=[400., 6.])])}))},
])
def test_occupied_strip_keeps_dense_floor(t):
    v = findings(t)
    assert v and v[0]['need'] == 43.2 and not v[0]['sparse'] and v[0]['columns_in_slot'] >= 1


def test_remote_sites_and_ports_do_not_occupy_strip():
    assert findings(dict(ft_slots=[dict(bit_sites_um=[[[400., 40.]]])],
                         clock=dict(landing_contract=dict(pins=[dict(xy_um=[400., 0.])]),
                                    sink_sites_um=[[400., 6., 20.]]))) == []


def test_unreadable_site_context_never_waives():
    v = findings(dict(clock=dict(taps_file='missing.json')))
    assert v[0]['need'] == 43.2 and not v[0]['sparse']


@pytest.mark.parametrize("t", [dict(clock=dict(tap_um=[400., float("nan")])),
                                 dict(internal_stations=[dict(regs_um=["bad"])]),
                                 dict(clock=dict(die_islands_um=[[410., 10., 390., 18.]]))])
def test_malformed_occupancy_never_becomes_empty(t):
    v = findings(t)
    assert v[0]["need"] == 43.2 and not v[0]["sparse"]
