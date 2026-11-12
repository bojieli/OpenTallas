"""HEAD-94 11-12: gen_phys.tap_pins clamps a reset IN pin that a plan reset.in_sites site left outside a cropped outline
(hd_st_n4 GRT-0209 'Pin arst_n is completely outside the die area'); the reset-tree solver keeps the unclamped site, so no
relay / depth changes; a site inside the outline is untouched."""
import copy
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gen_phys  # noqa: E402
import reset_tree as RT  # noqa: E402
import schema  # noqa: E402

TINY = json.loads((HERE / "examples" / "tiny_plan.json").read_text())


def _wave(sites):
    raw = copy.deepcopy(TINY)
    raw.setdefault("reset", {}).update(release="wavefront")
    if sites:
        raw["reset"]["in_sites"] = sites
    assert schema.validate(raw) == []
    return raw


def _soft_type(P):
    return next(tn for tn, t in P.types.items() if not t.get("hard"))


def _arst(P, tn):
    return next((x, y) for n, x, y in gen_phys.tap_pins(P, tn) if n == "arst_n")


def test_outside_in_site_gives_an_inside_pin_and_the_same_reset_tree():
    P0 = schema.Plan(_wave(None))
    tn = _soft_type(P0)
    w, h = P0.types[tn]["outline_um"]
    P = schema.Plan(_wave({tn: [w + 120.0, 5.0]}))
    x, y = _arst(P, tn)
    assert 0.0 <= x <= w and 0.0 <= y <= h
    assert RT.in_pin(P, tn)[0] > w                                      # solver keeps the unclamped site
    assert RT.for_type(P, tn)["relays"]


def test_inside_in_site_is_not_touched():
    P0 = schema.Plan(_wave(None))
    tn = _soft_type(P0)
    w, h = P0.types[tn]["outline_um"]
    site = [round(w * 0.5, 3), round(h * 0.25, 3)]
    P = schema.Plan(_wave({tn: site}))
    ip = RT.in_pin(P, tn)
    assert 0.0 <= ip[0] <= w and 0.0 <= ip[1] <= h
    ax, ay = _arst(P, tn)
    assert abs(ax - ip[0]) < 1e-6 and abs(ay - ip[1]) < 1e-6          # inside site: pin == solver site, not clamped
