"""Repeated PC+PHY clock subtrees keep their two partition identities and one logical CA region."""
import sys
from pathlib import Path
import pytest
sys.path.insert(0, str(Path(__file__).parent))
import die_trial as D
from test_die_trial_slice_spine import FakeSite
from test_die_trial_dme_template import _shape


def _fixture(monkeypatch):
    monkeypatch.setattr(D, "DME_TEMPLATE", True)
    monkeypatch.setattr(D, "DME_TEMPLATE_COMMON", True)
    monkeypatch.setattr(D, "DME_TEMPLATE_XMIRROR", True)
    monkeypatch.setattr(D, "DME_TEMPLATE_COMPOUND", True)
    monkeypatch.setattr(D, "DME_TEMPLATE_TYPES", {"pcA": "pc", "phyA": "phy", "pcB": "pc", "phyB": "phy"})
    monkeypatch.setattr(D, "leg_blocked_run", lambda site, a, b: 0.0)
    a = [(p, f"clk_t{k}", x, y) for p, x in (("pcA", 20.), ("phyA", 80.)) for k, y in enumerate((20., 80.))]
    b = [(dict(pcA="pcB", phyA="phyB")[p], port, 1100-x, y) for p, port, x, y in a]
    site = FakeSite(1100., 100., [])
    site.parts = [(0., 0., 50., 100.), (50., 0., 100., 100.), (1000., 0., 1050., 100.), (1050., 0., 1100., 100.)]
    site.forb = []
    return site, a, b


def test_compound_default_off_and_duplicate_port_names(monkeypatch):
    site, a, b = _fixture(monkeypatch)
    monkeypatch.setattr(D, "DME_TEMPLATE_COMPOUND", False)
    assert D._dme_template_xform(a, b) is None
    monkeypatch.setattr(D, "DME_TEMPLATE_COMPOUND", True)
    assert D._dme_template_xform(a, b) == (1100., 1., 0., -1.)
    broken = [(*b[0][:2], b[0][2]+1, b[0][3]), *b[1:]]
    assert D._dme_template_xform(a, broken) is None
    # Two identical types in one region cannot be silently guessed into roles.
    monkeypatch.setattr(D, "DME_TEMPLATE_TYPES", {"pcA": "same", "phyA": "same", "pcB": "same", "phyB": "same"})
    assert D._dme_template_xform(a, b) is None


def test_compound_common_site_is_union_of_both_partition_rects(monkeypatch):
    site, a, b = _fixture(monkeypatch)
    q = D._dme_template_site(site, a, [D._dme_template_xform(a,b)])
    assert q.parts == [(0.,0.,50.,100.), (50.,0.,100.,100.)]


def test_two_compound_regions_copy_exact_taps_and_keep_ca_ids(monkeypatch):
    site, a, b = _fixture(monkeypatch)
    regions = {"pcA":"RA", "phyA":"RA", "pcB":"RB", "phyB":"RB"}
    original = dict(regions)
    nodes = {j:dict(id=j,x=sum(t[2] for t in ts)/len(ts),y=sum(t[3] for t in ts)/len(ts),parent=None,level=0,
                   kids=[],taps=[],region=[0,0,1100,100],region_root=rn)
             for j,(rn,ts) in enumerate((("RA",a),("RB",b)))}
    st = D.attach_region_dme(nodes, site, a+b, regions, delay_rep_um=250.)
    assert st["RB"].get("template_of") in {"pcA","phyA"}
    assert regions == original
    assert sorted(t for n in nodes.values() if n.get("dme")=="RB" for t in n["taps"]) == sorted(b)
    assert sorted((-dx,dy,tp,k) for dx,dy,tp,k in _shape(nodes,"RA")) == _shape(nodes,"RB")
