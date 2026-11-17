"""FABLE-DIE-QC 11-16: opt-in per-type region clock tree template (OT_CLK_DME_TEMPLATE): a one-partition region of a type
seen before takes the first region's DME tree moved by the partition transform; off by default (trees unchanged)."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
import die_trial as D
from test_die_trial_slice_balance import _c_partition


@pytest.fixture(autouse=True)
def _no_block(monkeypatch):
    monkeypatch.setattr(D, "leg_blocked_run", lambda site, a, b: 0.0)


def _two_instances(dy_mirror=False, shift=(0.0, 0.0)):
    """two regions = two partitions of one type: pA at its place, pB the same taps moved (and y-mirrored)"""
    site, taps = _c_partition()
    ys = [t[3] for t in taps]
    y0, y1 = min(ys), max(ys)
    a = [("pA", t[1], t[2], t[3]) for t in taps]
    b = [("pB", t[1], round(t[2] + shift[0], 3), round((y0 + y1 - t[3] if dy_mirror else t[3]) + shift[1], 3)) for t in taps]
    regions = {"pA": "RA", "pB": "RB"}
    nodes = {}
    for j, (rn, tl) in enumerate((("RA", a), ("RB", b))):
        nodes[j] = dict(id=j, x=sum(t[2] for t in tl) / len(tl), y=sum(t[3] for t in tl) / len(tl), parent=None, level=0,
                        kids=[], taps=[], region=[0, 0, 1, 1], region_root=rn)
    return site, a + b, regions, nodes


def _shape(nodes, rn):
    """topology + leg vectors of region rn's tree, independent of where the region sits"""
    out = []
    for i, n in sorted(nodes.items()):
        if n.get("dme") == rn:
            p = nodes[n["parent"]]
            out.append((round(n["x"] - p["x"], 2), round(abs(n["y"] - p["y"]), 2), sorted(t[1] for t in n["taps"]), len(n["kids"])))
    return sorted(out)


def test_xform_translate_and_mirror():
    c = [("a", "p0", 0.0, 0.0), ("a", "p1", 10.0, 5.0)]
    assert D._dme_template_xform(c, [("b", "p0", 3.0, 7.0), ("b", "p1", 13.0, 12.0)]) == (3.0, 1.0, 7.0)
    assert D._dme_template_xform(c, [("b", "p0", 3.0, 7.0), ("b", "p1", 13.0, 2.0)]) == (3.0, -1.0, 7.0)
    assert D._dme_template_xform(c, [("b", "p0", 3.0, 7.0), ("b", "p1", 14.0, 12.0)]) is None
    assert D._dme_template_xform(c, [("b", "p0", 3.0, 7.0), ("b", "p2", 13.0, 12.0)]) is None


def test_off_by_default():
    assert D.DME_TEMPLATE is False or D.os.environ.get("OT_CLK_DME_TEMPLATE", "0") not in ("", "0")


def test_template_gives_same_tree_in_every_instance(monkeypatch, mirror=False):
    monkeypatch.setattr(D, "DME_TEMPLATE", True)
    monkeypatch.setattr(D, "DME_TEMPLATE_TYPES", {"pA": "t", "pB": "t"})
    site, taps, regions, nodes = _two_instances(dy_mirror=mirror)
    st = D.attach_region_dme(nodes, site, taps, regions, delay_rep_um=250.0)
    assert st["RB"].get("template_of") == "pA" and "template_of" not in st["RA"]
    assert _shape(nodes, "RA") == _shape(nodes, "RB")
    assert sorted(t for n in nodes.values() if n.get("dme") == "RB" for t in n["taps"]) == sorted(t for t in taps if t[0] == "pB")


def test_other_type_is_not_copied(monkeypatch):
    monkeypatch.setattr(D, "DME_TEMPLATE", True)
    monkeypatch.setattr(D, "DME_TEMPLATE_TYPES", {"pA": "t", "pB": "u"})
    site, taps, regions, nodes = _two_instances()
    st = D.attach_region_dme(nodes, site, taps, regions, delay_rep_um=250.0)
    assert "template_of" not in st["RB"]


def test_illegal_copy_keeps_own_tree(monkeypatch):
    """a mirrored instance whose obstacles are not mirrored: the moved sites are illegal, the region embeds its own tree"""
    monkeypatch.setattr(D, "DME_TEMPLATE", True)
    monkeypatch.setattr(D, "DME_TEMPLATE_TYPES", {"pA": "t", "pB": "t"})
    site, taps, regions, nodes = _two_instances(dy_mirror=True)
    st = D.attach_region_dme(nodes, site, taps, regions, delay_rep_um=250.0)
    assert sorted(t for n in nodes.values() if n.get("dme") == "RB" for t in n["taps"]) == sorted(t for t in taps if t[0] == "pB")
