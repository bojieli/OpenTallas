"""FABLE-DIE-QC-R 11-16: OT_CLK_DME_TEMPLATE=2 embeds a template region tree on the sites legal in every instance, so a
mirrored instance whose obstacles are not mirrored still takes the copy (form 1 refused it and kept a second tree)."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
import die_trial as D
from test_die_trial_slice_balance import _c_partition

W, H, DX = 1235.5, 2617.9, 1500.0
CORES = [(84.2, 75.6, 546.5, 1237.7), (689.0, 75.6, 1151.3, 1237.7), (84.2, 1388.9, 546.5, 2551.0), (689.0, 1388.9, 1151.3, 2551.0)]
EXTRA = (DX + 560.0, 1250.0, DX + 680.0, 1370.0)        # only in pB: the centre of its cross channel


@pytest.fixture(autouse=True)
def _no_block(monkeypatch):
    monkeypatch.setattr(D, "leg_blocked_run", lambda site, a, b: 0.0)


def _site():
    s = object.__new__(D.SiteMap)
    s.W, s.H, s.b = DX + W, H, 250.0
    s.parts = [(0.0, 0.0, W, H), (DX, 0.0, DX + W, H)]
    s.forb = [c + ("core",) for c in CORES] + [(DX + c[0], H - c[3], DX + c[2], H - c[1], "core") for c in CORES] + [EXTRA + ("core",)]
    s.idx = {}
    for k, r in enumerate(s.forb):
        for i in range(int(r[0] // s.b), int(r[2] // s.b) + 1):
            for j in range(int(r[1] // s.b), int(r[3] // s.b) + 1):
                s.idx.setdefault((i, j), []).append(k)
    return s


def _case():
    _, taps = _c_partition()
    a = [("pA", t[1], t[2], t[3]) for t in taps]
    b = [("pB", t[1], round(t[2] + DX, 3), round(H - t[3], 3)) for t in taps]
    nodes = {}
    for j, (rn, tl) in enumerate((("RA", a), ("RB", b))):
        nodes[j] = dict(id=j, x=sum(t[2] for t in tl) / len(tl), y=sum(t[3] for t in tl) / len(tl), parent=None, level=0,
                        kids=[], taps=[], region=[0, 0, 1, 1], region_root=rn)
    return _site(), a, b, {"pA": "RA", "pB": "RB"}, nodes


def _shape(nodes, rn):
    out = []
    for i, n in sorted(nodes.items()):
        if n.get("dme") == rn:
            p = nodes[n["parent"]]
            if p.get("dme") == rn:
                out.append((round(n["x"] - p["x"], 1), round(abs(n["y"] - p["y"]), 1), sorted(t[1] for t in n["taps"]), len(n["kids"])))
    return sorted(out)


def test_common_site_is_the_intersection():
    site, a, b, regions, nodes = _case()
    xf = D._dme_template_xform(a, b)
    assert xf == (DX, -1.0, H)
    ts = D._dme_template_site(site, a, [xf])
    assert ts is not site and ts.parts == [(0.0, 0.0, W, H)]
    n = bad = 0
    for i in range(60):
        for j in range(120):
            q = (W * (i + 0.5) / 60, H * (j + 0.5) / 120)
            both = site.legal(q) and site.legal((q[0] + DX, H - q[1]))
            assert ts.legal(q) == both
            n += both
            bad += site.legal(q) and not both
    assert n > 0 and bad > 0            # the pB-only obstacle removed sites from the template


def test_fake_site_without_geometry_gives_no_common_site():
    site, taps = _c_partition()
    assert D._dme_template_site(site, taps, [(1.0, 1.0, 0.0)]) is None


def _run(monkeypatch, common):
    monkeypatch.setattr(D, "DME_TEMPLATE", True)
    monkeypatch.setattr(D, "DME_TEMPLATE_COMMON", common)
    monkeypatch.setattr(D, "DME_TEMPLATE_TYPES", {"pA": "t", "pB": "t"})
    site, a, b, regions, nodes = _case()
    st = D.attach_region_dme(nodes, site, a + b, regions, delay_rep_um=250.0)
    for n in nodes.values():
        if n.get("dme"):
            assert site.legal((n["x"], n["y"])), (n["dme"], n["x"], n["y"])
    return st, nodes


def test_form_1_refuses_the_copy_on_the_extra_obstacle(monkeypatch):
    st, nodes = _run(monkeypatch, False)
    assert "template_of" not in st["RB"]


def test_form_2_copies_into_every_instance(monkeypatch):
    st, nodes = _run(monkeypatch, True)
    assert st["RB"].get("template_of") == "pA" and "template_of" not in st["RA"]
    sa, sb = _shape(nodes, "RA"), _shape(nodes, "RB")
    assert sa and len(sa) == len(sb)
    assert sorted(u[2:] for u in sa) == sorted(v[2:] for v in sb)
    for k in (0, 1):
        assert all(abs(p - q) <= 0.11 for p, q in zip(sorted(u[k] for u in sa), sorted(v[k] for v in sb)))
