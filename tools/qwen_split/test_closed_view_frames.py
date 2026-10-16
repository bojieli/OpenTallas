"""Q-VIEWFRAME 10-16: qfd_d2d_static / qfd_res_train_issue are drawn exactly as their CLOSED views."""
import json
import sys
from dataclasses import dataclass
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from qwen_split import closed_view as cv
from qwen_split import res_train_bind as rtb
from qwen_split import static_link_bind as slb
from qwen_split.direct_up4 import partition_master
from qwen_split.source_pin_plan import rtl_ports
from qwen_split.test_res_train_bind import _model as rt_model


@dataclass
class Inst:
    name: str
    master: str
    x: float = 0
    y: float = 0
    w: float = 777.576
    h: float = 518.376
    orient: str = 'R0'
    kind: str = 'link'
    region: str = 'io'
    domain: str = 'stream'


class Master:
    def __init__(self, name, w, h, *args):
        self.name, self.w, self.h = name, w, h
        self.ports, self.order = {}, []


def _link_model():
    return dict(insts=[Inst('d2d_rom', 'qfd_d2d_rom', x=500, y=700),
                       Inst('native59', 'native59', x=100, y=1000, w=43.2, h=43.2),
                       Inst('ucie_kv', 'phy', x=1000, y=1000, w=43.2, h=43.2)],
                buses=[('clk', 'clock_trunk', 1, [('pll', 'clk'), ('d2d_rom', 'ck')]),
                       ('rst', 'reset', 1, [('root', 'rst'), ('d2d_rom', 'rst_n')])])


def _bit_geometry(q, rtl):
    """every (pin name -> (face, layer, z)) the die master emits, from its 'pins' ports and alias fragments"""
    out = {}
    for p, sp in q.ports.items():
        if sp[0] == 'pins':
            lays = getattr(q, 'view_pin_layers', {}).get(p) or [sp[3]] * sp[1]
            for b, z in enumerate(sp[4]):
                out[p if sp[1] == 1 else f'{p}[{b}]'] = (sp[2], lays[b], z)
    return out


def test_view_dir_honours_bind_view_select():
    sel = json.loads((cv.ROOT / cv.SELECT).read_text())['views']['qfd_d2d_static']
    assert cv.view_dir('qfd_d2d_static') == cv.ROOT / sel
    assert cv.view_dir('qfd_res_train_issue') == cv.ROOT / 'physical/ref_tile/qfd_res_train_issue_c2/views/qfd_res_train_issue'
    assert cv.view_frame('qfd_d2d_static')[:2] == (475.2, 280.8)
    assert cv.view_frame('qfd_res_train_issue')[:2] == (30.24, 30.24)
    assert cv.view_frame('qfd_rstseq')[:2] == (21.6, 21.6)        # the Q-NETLIST hook still finds its own view


def test_view_dir_refuses_ambiguous_and_missing_selection(tmp_path, monkeypatch):
    for r in ('a', 'b'):
        d = tmp_path / f'physical/ref_tile/m_{r}/views/m'
        d.mkdir(parents=True)
        (d / 'm.lef').write_text('MACRO m\n  SIZE 1 BY 1 ;\nEND m\n')
    monkeypatch.setenv('OT_BIND_VIEW_SELECT', str(tmp_path / 'none.json'))
    with pytest.raises(ValueError, match='closed views'):
        cv.view_dir('m', tmp_path)
    sel = tmp_path / 'sel.json'
    sel.write_text(json.dumps(dict(views=dict(m='physical/ref_tile/m_b/views/m'))))
    monkeypatch.setenv('OT_BIND_VIEW_SELECT', str(sel))
    assert cv.view_dir('m', tmp_path) == tmp_path / 'physical/ref_tile/m_b/views/m'
    sel.write_text(json.dumps(dict(views=dict(m='physical/ref_tile/m_c/views/m'))))
    with pytest.raises(ValueError, match='selected view'):
        cv.view_dir('m', tmp_path)


def test_static_link_slot_and_every_pin_from_the_view():
    m = _link_model()
    rec = slb.apply(m)
    d2d = next(i for i in m['insts'] if i.name == 'd2d_rom')
    assert (d2d.w, d2d.h, d2d.x, d2d.y) == (475.2, 280.8, 500, 700)        # origin stands, frame shrinks
    assert rec['view_frame']['historical_um'] == [777.576, 518.376]
    M = {}
    slb.install_masters(M, m, Master, partition_master)
    q = M[slb.MASTER]
    w, h, P = cv.view_frame(slb.MASTER)
    assert (q.w, q.h) == (w, h)
    rtl = rtl_ports(slb.ROOT / slb.SOURCE, slb.MASTER)
    assert {p: s[1] for p, s in q.ports.items()} == {p: n for p, (n, _) in rtl.items()}
    assert _bit_geometry(q, rtl) == P                                           # every bit: view face, layer, position
    assert q.view_pin_layers                                                    # the view interleaves M3 / M5 bits
    r = m['view_frames'][slb.MASTER]
    assert r['pins_mapped'] == len(P) == sum(n for n, _ in rtl.values())


def test_res_train_issue_slot_pins_and_tap_fragments():
    m = rt_model()
    rtb.apply(m)
    inst = next(i for i in m['insts'] if i.name == rtb.ISSUE)
    assert (inst.w, inst.h) == (30.24, 30.24)
    M = {}
    rtb.install_masters(M, m, Master, partition_master)
    q = M[rtb.ISSUE_MASTER]
    w, h, P = cv.view_frame(rtb.ISSUE_MASTER)
    assert (q.w, q.h) == (w, h)
    rec = m['view_frames'][rtb.ISSUE_MASTER]
    assert rec['pins_mapped'] == len(P)
    assert 'me_go' in rec['scalar_ports_on_1bit_view_bus']                     # view exports scalar me_go as me_go[0]
    # every TT-tap alias is a fragment of the real view pins, bit for bit
    for alias, (real, bits) in m['port_join'][rtb.ISSUE_MASTER].items():
        frag = q.assigned_fragment_rects[alias]
        n = rtl_ports(rtb.ROOT / rtb.ISSUE_SOURCE, rtb.ISSUE_MASTER)[real][0]
        for (lay, r), b in zip(frag, bits):
            f, vl, z = P[cv.bit_pins(P, real, n)[b]]
            assert lay == vl and abs(((r[1] + r[3]) / 2 if f in 'WE' else (r[0] + r[2]) / 2) - z) < 1e-6
    rtb.validate_case_masters(M, m)


def test_die_port_without_view_pin_fails_closed(monkeypatch):
    m = _link_model()
    slb.apply(m)
    real = cv.parse_frame
    def drop(text, master):
        w, h, P = real(text, master)
        P.pop('fdi_tx_flit[7]')
        return w, h, P
    monkeypatch.setattr(cv, 'parse_frame', drop)
    with pytest.raises(ValueError, match=r'fdi_tx_flit\[7\]'):
        slb.install_masters({}, m, Master, partition_master)


def test_gate_off_keeps_generated_frames(monkeypatch):
    monkeypatch.setenv('OT_SPLIT_VIEW_FRAMES', '0')
    m = _link_model()
    rec = slb.apply(m)
    d2d = next(i for i in m['insts'] if i.name == 'd2d_rom')
    assert (d2d.w, d2d.h) == (777.576, 518.376) and 'view_frame' not in rec
    m2 = rt_model()
    rtb.apply(m2)
    assert next(i for i in m2['insts'] if i.name == rtb.ISSUE).w == rtb.ISSUE_WH[0]
