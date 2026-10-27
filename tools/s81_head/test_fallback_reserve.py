"""FALLBACK-HEAD-2 fallback_reserve: die tree sites -> per-type reserved rects (type frame, union), ring banks."""
import copy
import json
import sys
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools/die_plan"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import schema as S  # noqa: E402
import die_trial as DT  # noqa: E402
import fallback_reserve as FR  # noqa: E402

RAW = json.loads((ROOT / "physical/die_plan/s81_head/die_plan.json").read_text())


def free_point(P, part):
    """a type-frame point clear of hard cores (+5 um) in partition `part`, returned in the die frame."""
    t = P.ptype(part); w, h = t["outline_um"]; cores = [c[:4] for c in DT.core_obs(t)]
    for y in range(5, int(h) - 5, 3):
        for x in range(5, int(w) - 5, 3):
            if not any(c[0] - 5 < x < c[2] + 5 and c[1] - 5 < y < c[3] + 5 for c in cores):
                return (x, y), P.to_die(part, (x, y))
    raise AssertionError("no free point")


def test_union_over_instances_in_type_frame():
    raw = copy.deepcopy(RAW); P = S.Plan(raw)
    tiles = [n for n, p in P.parts.items() if p["type"] == "hd_tile"][:2]
    sites = {}
    for i, n in enumerate(tiles):
        (tx, ty), (x, y) = free_point(P, n)
        sites[f"b{i}"] = [x, y]
    out, rep = FR.reserve(raw, dict(sites=sites), None)
    rows = out["partition_types"]["hd_tile"]["clock"]["reserved_sites_um"]
    assert all(r["kind"] == "die_clock_tree" for r in rows)
    assert rep["types"]["hd_tile"]["tree_rects"] == len(rows) >= 1
    # the site of the first tile maps back to its type-frame point (+halo), whatever that tile's orient
    (tx, ty), _ = free_point(P, tiles[0])
    assert any(r["rect_um"][0] <= tx <= r["rect_um"][2] and r["rect_um"][1] <= ty <= r["rect_um"][3] for r in rows)
    assert rep["physical_qualified"] is False


def test_site_on_a_hard_core_fails_closed():
    raw = copy.deepcopy(RAW); P = S.Plan(raw)
    n = next(n for n, p in P.parts.items() if p["type"] == "hd_tile")
    c = DT.core_obs(P.ptype(n))[0]
    x, y = P.to_die(n, ((c[0] + c[2]) / 2, (c[1] + c[3]) / 2))
    with pytest.raises(ValueError, match="conflicts"):
        FR.reserve(raw, dict(sites={"b0": [x, y]}), None)


def test_site_outside_every_partition_fails_closed():
    raw = copy.deepcopy(RAW)
    with pytest.raises(ValueError, match="not inside any partition"):
        FR.reserve(raw, dict(sites={"b0": [-50.0, -50.0]}), None)


def test_ring_banks_from_landing_contract_and_sidecar_must_match():
    raw = copy.deepcopy(RAW)
    raw["partition_types"]["hd_tile"].setdefault("clock", {})["landing_contract"] = dict(bands={"i": dict(rect_um=[17.28, 362.88, 261.36, 373.68])})
    side = dict(collector=dict(types={"hd_tile": dict(bands={"i": dict(rect_um=[17.28, 362.88, 261.36, 373.68])})}))
    out, rep = FR.reserve(raw, dict(sites={}), side)
    rows = out["partition_types"]["hd_tile"]["clock"]["reserved_sites_um"]
    assert rows == [dict(rect_um=[17.28, 362.88, 261.36, 373.68], kind="landing_ring_bank", ref="u_cland_i")]
    side["collector"]["types"]["hd_tile"]["bands"]["i"]["rect_um"][0] = 18.0
    with pytest.raises(ValueError, match="sidecar"):
        FR.reserve(copy.deepcopy(raw), dict(sites={}), side)
