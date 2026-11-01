"""Two package receivers in a partition need separate physical top input pins."""
from types import SimpleNamespace
import bind


def test_same_pin_names_are_leaf_specific():
    b = bind.Binder.__new__(bind.Binder)
    b.members = {'glue': [0, 1], 'phy': [2]}
    b.parts = {'glue': {'type': 'glue'}, 'phy': {'type': 'phy'}}
    c = lambda inst: {'inst': inst, 'module': 'pad', 'bump_ports': [dict(pin='pad_i', dir='input', width=1)]}
    b.types = {'glue': {'contents': [c('u_bump_fwd_epoch'), c('u_bump_fwd_lrst')]},
               'phy': {'contents': [c('u_phy')]}}
    b.F = SimpleNamespace(cells=[SimpleNamespace(module='pad', ports={}, path=n)
        for n in ('bump_fwd_epoch', 'bump_fwd_lrst', 'phy')])
    b.G = SimpleNamespace(kind={0:'leaf',1:'leaf',2:'leaf'})
    b.rel_of = lambda ci: b.F.cells[ci].path
    got = b.bump_pins()
    assert [x['dport'] for x in got['glue']] == ['glue_bump_fwd_epoch_pad_i','glue_bump_fwd_lrst_pad_i']
    assert got['phy'][0]['dport'] == 'phy_pad_i'  # Existing unique physical input name stays unchanged.
    assert got['glue'][0]['pport'] != got['glue'][1]['pport']
    assert b.bump_pins() is got
