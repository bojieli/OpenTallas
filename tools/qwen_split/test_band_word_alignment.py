import copy
from types import SimpleNamespace

import pytest

from qwen_rom_fulldie import Master, pin_rects
from qwen_split.source_pin_plan import apply_band, apply_slabs
from qwen_split.band_word_alignment import apply_pins, apply_homes, FLAG


def actual_masters():
    band = Master('qfd_sp_band_lanes', 881.28, 1131.84, 5, 'test')
    slab = Master('qfd_port_tiles_1', 1036.8, 2462.4, 5, 'test')
    apply_band(band)
    apply_slabs({slab.name: slab})
    return {band.name: band, slab.name: slab}


def contacts(master, port):
    q = copy.copy(master)
    q.order = [port]
    return [(r[0]+r[2])/2 for _, _, r in pin_rects(q, 1, {port: 4096})]


def model():
    insts = []
    for n in range(3):
        insts += [SimpleNamespace(name=f'sp_port_tiles_{n}', master=f'qfd_port_tiles_{n}',
                                  x=12588.48, y=n*4000, w=1036.8, h=2462.4, orient='MX'),
                  SimpleNamespace(name=f'sp_band_lanes_{n}', master='qfd_sp_band_lanes',
                                  x=12718.08, y=n*4000+2505.6, w=881.28, h=1131.84, orient='MX')]
    return dict(insts=insts, die={'w':20000, 'h':15000})


def test_actual_source_emitters_align_all_8192_word_contacts(monkeypatch):
    monkeypatch.setenv(FLAG, '1')
    masters = actual_masters()
    apply_pins(masters)
    band, slab = masters['qfd_sp_band_lanes'], masters['qfd_port_tiles_1']
    # MX leaves x untouched, R0 does too: this verifies both actual pair forms.
    for port in ('tw', 'ty'):
        a, b = contacts(band, port), contacts(slab, port)
        assert len(a) == len(b) == 4096
        assert max(abs(x+12696.48-y-12588.48) for x,y in zip(a,b)) < 1e-8
    rects = []
    q = copy.copy(band)
    q.order = ['tw', 'ty', 'ck']
    for name, _, r in pin_rects(q, 1, {'tw':4096, 'ty':4096, 'ck':1}):
        rects.append((r[0], r[2], name))
    rects.sort()
    assert all(a[1] < b[0] for a,b in zip(rects,rects[1:]))


def test_default_preserves_source_pin_plan_and_homes(monkeypatch):
    monkeypatch.delenv(FLAG, raising=False)
    masters = actual_masters()
    before = copy.deepcopy(masters)
    apply_pins(masters)
    assert all(masters[k].ports == before[k].ports for k in masters)
    m = model()
    old = copy.deepcopy(m)
    assert apply_homes(m) is None
    assert [vars(i) for i in m['insts']] == [vars(i) for i in old['insts']]


def test_whole_graph_homes_are_transactional_and_reserved_channels_stand(monkeypatch):
    monkeypatch.setenv(FLAG, '1')
    monkeypatch.setenv('OT_SPLIT_HOMES', 'explicit-source-homes.json')
    m = model()
    old = [vars(i).copy() for i in m['insts']]
    with pytest.raises(ValueError, match='overlaps'):
        apply_homes(m, {'channel':dict(x=12697.,y=2506.,w=10.,h=10.)})
    assert [vars(i) for i in m['insts']] == old
    receipt = apply_homes(m)
    assert receipt['cycles_added'] == 0 and receipt['area_added_um2'] == 0
    assert not receipt['qualified']
    assert all(i.x == 12696.48 for i in m['insts'] if i.master == 'qfd_sp_band_lanes')


@pytest.mark.parametrize('field,value', [('orient','R0'),('x',12720.),('master','wrong')])
def test_stale_peer_graph_refused_before_mutation(monkeypatch, field, value):
    monkeypatch.setenv(FLAG, '1')
    monkeypatch.setenv('OT_SPLIT_HOMES', 'explicit-source-homes.json')
    m = model()
    setattr(m['insts'][1], field, value)
    old = [vars(i).copy() for i in m['insts']]
    with pytest.raises(ValueError): apply_homes(m)
    assert [vars(i) for i in m['insts']] == old
