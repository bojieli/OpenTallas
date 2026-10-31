"""DIE-QC-52: an empty snake from the deeper-root fallback ("no elongated chain beats one plain stage") is attached as
the plain physical leg, so inv2 (even-leg) parity holds; before, [pa, q] was taken as a 1-stage explicit chain and
attach_region_dme raised "physical clock chain has odd inverter parity" (QC gen52, 10-31 00:29)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import die_trial as D
from test_die_trial_region_dme_snake import _su_like


def _fake_tree(x, y, taps):
    # new top node 1 at the old root site (x, y) with an EMPTY snake to the old root 0 (dme_region_tree fallback form)
    dn = [dict(x=x, y=y, kids=[], taps=list(taps), S=10.0, Smin=10.0, W=0.0),
          dict(x=x, y=y, kids=[0], taps=[], S=20.0, Smin=20.0, W=0.0, snakes={0: []})]
    return dn, 1, dict(merges=0, imbalanced=0, spread_um=0.0, snakes=1, snake_wire_um=0.0, snake_buffers=0)


def test_empty_snake_is_plain_even_leg(monkeypatch):
    site, taps = _su_like()
    x, y = 100.0, 900.0
    assert site.legal((x, y))
    monkeypatch.setattr(D, "EVEN_LEGS", True)
    monkeypatch.setattr(D, "DME_ACTUAL_MAX_UM", 405.0)
    monkeypatch.setattr(D, "DME_WORKERS", 1)
    monkeypatch.setattr(D, "dme_region_tree", lambda site_, rt, **kw: _fake_tree(x, y, rt))
    nodes = {0: dict(id=0, x=x, y=y, parent=None, kids=[], taps=[], level=0, region=[0, 0, 1300, 1400],
                     region_root="r")}
    regions = {t[0]: "r" for t in taps}
    D.attach_region_dme(nodes, site, taps, regions, delay_rep_um=250.0, snake="all")
    legs = [nd["physical_leg"] for nd in nodes.values() if nd.get("physical_leg")]
    assert len(legs) == 2
    assert all(pl["stages"] % 2 == 0 for pl in legs), [pl["stages"] for pl in legs]
    assert not any(nd.get("snake") for nd in nodes.values())


def test_explicit_odd_chain_still_rejected(monkeypatch):
    site, _ = _su_like()
    monkeypatch.setattr(D, "EVEN_LEGS", True)
    monkeypatch.setattr(D, "DME_ACTUAL_MAX_UM", 405.0)
    p = (100.0, 900.0)
    try:
        D.physical_leg(site, p, p, 250.0, [p, p])
    except ValueError as e:
        assert "odd inverter parity" in str(e)
    else:
        raise AssertionError("odd explicit chain accepted")
