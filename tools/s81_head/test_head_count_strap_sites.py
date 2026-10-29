"""DIE-HEAD-21: head_count_strap_sites.apply (Codex helper, codex/head-die-1028-0405, unchanged) on the committed
DIE-HEAD-20 one-entry HEAD plan: strip the placed count-strap sites, re-place them, and check the placement rules."""
import copy
import gzip
import json
from pathlib import Path
import re
import sys

import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(ROOT / "tools/die_plan"))
import head_count_strap_sites as CS  # noqa: E402
import gen_phys as G  # noqa: E402
import schema as S  # noqa: E402

PLAN = ROOT / "results/die_head_20_1028/plan_hd_tile_525.json.gz"


@pytest.fixture(scope="module")
def placed():
    return json.loads(gzip.decompress(PLAN.read_bytes()))


def stripped(raw):
    raw = copy.deepcopy(raw)
    for t in raw["partition_types"].values():
        for s in t.get("count_straps", []):
            s.pop("sites_um", None); s.pop("layer", None)
    return raw


def test_rejects_already_placed(placed):
    if not any(s.get("sites_um") for t in placed["partition_types"].values() for s in t.get("count_straps", [])):
        pytest.skip("committed plan carries no placed count sites")
    with pytest.raises(ValueError, match="already placed"):
        CS.apply(placed, PLAN, ROOT)


def test_placement_rules(placed):
    raw, rep = CS.apply(stripped(placed), PLAN, ROOT)
    P = S.Plan(raw, path=PLAN)
    assert rep, "no type with count straps"
    for tn, r in rep.items():
        t = raw["partition_types"][tn]
        sites = [tuple(xy) for s in t["count_straps"] for xy in s["sites_um"]]
        assert len(sites) == sum(s["width"] == len(s["sites_um"]) and s["width"] for s in t["count_straps"]) == r["pins"]
        assert all(s["layer"] == "M5" for s in t["count_straps"])
        w, h = t["outline_um"]
        for x, y in sites:
            assert abs(x / 4.32 - round(x / 4.32)) < 1e-6 and abs(y / 4.32 - round(y / 4.32)) < 1e-6
            assert 0 < x < w and 0 < y < h
        # no two count pins (or a count pin and a plan pin) closer than half a pitch
        pins = [(q["x"], q["y"]) for q in G.plan_pin_records(P, tn, G.type_pins(P, tn))]
        for i, (x, y) in enumerate(sites):
            assert not any(abs(x - a) < 2.16 and abs(y - b) < 2.16 for a, b in sites[:i])
        # whole M5 pin clear of every macro halo (5.4 um) and reserved site (1.08 um)
        for inst, mod, lef, lib, mx, my, orient in G.type_macros(P, tn):
            mw, mh = map(float, re.search(r"\bSIZE\s+([\d.]+)\s+BY\s+([\d.]+)\s*;", (ROOT / lef).read_text()).groups())
            if orient in ("R90", "R270", "E", "W", "FE", "FW", "MXR90", "MYR90"):
                mw, mh = mh, mw
            assert not any(mx - 5.4 <= x <= mx + mw + 5.4 and my - 5.4 <= y <= my + mh + 5.4 for x, y in sites), (tn, inst)
        for q in t.get("clock", {}).get("reserved_sites_um", []):
            x0, y0, x1, y1 = q["rect_um"]
            assert not any(x0 - 1.08 <= x <= x1 + 1.08 and y0 - 1.08 <= y <= y1 + 1.08 for x, y in sites), (tn, q.get("ref"))


def test_deterministic(placed):
    a, ra = CS.apply(stripped(placed), PLAN, ROOT)
    b, rb = CS.apply(stripped(placed), PLAN, ROOT)
    assert a == b and ra == rb
