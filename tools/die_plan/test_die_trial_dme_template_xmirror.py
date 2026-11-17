"""KV-CLK-R2 11-17: opt-in OT_CLK_DME_TEMPLATE_XMIRROR copies the region template onto x-mirrored instances (MY / R180)."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
import die_trial as D
from test_die_trial_dme_template import _shape
from test_die_trial_slice_balance import _c_partition


@pytest.fixture(autouse=True)
def _no_block(monkeypatch):
    monkeypatch.setattr(D, "leg_blocked_run", lambda site, a, b: 0.0)


def test_xform_xmirror_off_by_default():
    c = [("a", "p0", 0.0, 0.0), ("a", "p1", 10.0, 5.0)]
    assert D._dme_template_xform(c, [("b", "p0", 30.0, 7.0), ("b", "p1", 20.0, 12.0)]) is None


def test_xform_xmirror(monkeypatch):
    monkeypatch.setattr(D, "DME_TEMPLATE_XMIRROR", True)
    c = [("a", "p0", 0.0, 0.0), ("a", "p1", 10.0, 5.0)]
    assert D._dme_template_xform(c, [("b", "p0", 3.0, 7.0), ("b", "p1", 13.0, 12.0)]) == (3.0, 1.0, 7.0)
    assert D._dme_template_xform(c, [("b", "p0", 30.0, 7.0), ("b", "p1", 20.0, 12.0)]) == (30.0, 1.0, 7.0, -1.0)
    assert D._dme_template_xform(c, [("b", "p0", 30.0, 7.0), ("b", "p1", 20.0, 2.0)]) == (30.0, -1.0, 7.0, -1.0)
    assert D._dme_template_xform(c, [("b", "p0", 30.0, 7.0), ("b", "p1", 21.0, 12.0)]) is None


def test_xmirror_copy_same_tree(monkeypatch):
    """pB = pA mirrored in x about the partition centre: with XMIRROR the copy is taken and the tree is the x mirror"""
    monkeypatch.setattr(D, "DME_TEMPLATE", True)
    monkeypatch.setattr(D, "DME_TEMPLATE_XMIRROR", True)
    monkeypatch.setattr(D, "DME_TEMPLATE_TYPES", {"pA": "t", "pB": "t"})
    site, taps = _c_partition()
    xs = [t[2] for t in taps]
    x0, x1 = min(xs), max(xs)
    a = [("pA", t[1], t[2], t[3]) for t in taps]
    b = [("pB", t[1], round(x0 + x1 - t[2], 3), t[3]) for t in taps]
    regions = {"pA": "RA", "pB": "RB"}
    nodes = {}
    for j, (rn, tl) in enumerate((("RA", a), ("RB", b))):
        nodes[j] = dict(id=j, x=sum(t[2] for t in tl) / len(tl), y=sum(t[3] for t in tl) / len(tl), parent=None, level=0,
                        kids=[], taps=[], region=[0, 0, 1, 1], region_root=rn)
    st = D.attach_region_dme(nodes, site, a + b, regions, delay_rep_um=250.0)
    assert sorted(t for n in nodes.values() if n.get("dme") == "RB" for t in n["taps"]) == sorted(b)
    assert st["RB"].get("template_of") == "pA"
    mir = lambda sh: sorted((-dx, dy, tp, k) for dx, dy, tp, k in sh)
    assert mir(_shape(nodes, "RA")) == _shape(nodes, "RB")
