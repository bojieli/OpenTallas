"""KV-BIND11 10-20: OT_KV_D2D_PINS draws the d2ds words at the bound view's pins, measures d2d hops to the farthest
view pin, and levels the HOST stand-in words with the d2d anchors (host on the face toward the d2d end)."""
import importlib
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
KIT = 'qkd_d2d_static_r7w_sfm2'
ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture()
def K(monkeypatch):
    if not (ROOT / 'physical/ref_tile' / KIT / 'spec.json').exists():
        pytest.skip('d2ds kit view not checked out')
    monkeypatch.setenv('OT_KV_D2D_FIT', '1')
    monkeypatch.setenv('OT_KV_D2D_PINS', '1')
    monkeypatch.setenv('OT_KV_D2DS_KIT', KIT)
    import kv_die
    k = importlib.reload(kv_die)
    yield k
    monkeypatch.delenv('OT_KV_D2D_PINS')
    monkeypatch.delenv('OT_KV_D2D_FIT')
    importlib.reload(kv_die)


def test_anchor_and_farthest_pin(K):
    V = K.d2d_view_ports()
    assert V['srx'][0] == 'W' and V['svc'][0] == 'E' and V['rec_tx'][0] == 'S'
    d = K.F.Inst('d2d_kv', 'qkd_d2ds', 1000.0, 2000.0, 475.2, 280.8, 'R0')
    ax, ay = K._d2d_pin(d, 'srx')
    assert ax == 1000.0 and 2000.0 < ay < 2280.8
    far = K.ep_far('d2d_kv', 'srx', (ax, ay))
    assert far == pytest.approx(V['srx'][2], abs=0.2)          # from its own anchor: the recorded spread
    assert K.ep_far('host', 'svc', (0, 0)) is None


def test_host_words_level_with_d2d(K):
    d = K.F.Inst('d2d_kv', 'qkd_d2ds', 1000.0, 2000.0, 475.2, 280.8, 'R0')
    h = K.F.Inst('host', 'qkd_host_rt', 1000.0, 1350.0, 777.6, 518.4, 'R0')
    hm = K.F.Master('qkd_host_rt', 777.6, 518.4, 'M9', 'host')
    hm.face('rec_tx', 549, 'N', 'M5', 600.0, 1)
    hm.face('svc', 174, 'W', 'M4', 400.0, 1)
    dm = K.F.Master('qkd_d2ds', 475.2, 280.8, 'M9', 'd2d')
    dm.face('rec_tx', 549, 'N', 'M5', 100.0, 1)
    dm.face('svc', 174, 'W', 'M4', 100.0, 1)
    m = dict(insts=[d, h], buses=[('hrec_tx', 'spine_local', 549, [('host', 'rec_tx'), ('d2d_kv', 'rec_tx')]),
                                  ('hsvc', 'spine_local', 174, [('d2d_kv', 'svc'), ('host', 'svc')])])
    M = dict(qkd_host_rt=hm, qkd_d2ds=dm)
    K._d2d_view_pins(m, M)
    V = K.d2d_view_ports()
    assert dm.ports['rec_tx'][2] == 'S' and dm.ports['rec_tx'][4] == V['rec_tx'][1]
    assert hm.ports['rec_tx'][2] == 'N' and hm.ports['svc'][2] == 'N'
    hx, hy = K.pin_xy(h, hm, 'rec_tx')
    dx, dy = K._d2d_pin(d, 'rec_tx')
    assert abs(hx - dx) < 30.0                                   # level with the d2d anchor (was ~half a face away)
    sx, _ = K.pin_xy(h, hm, 'svc')
    assert sx > 1000.0 + 475.2 - 60.0                            # svc under the d2d E face (its view pins)
