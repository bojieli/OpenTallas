"""DIE-HBM-57/TAPS: single-root core explicit clock taps (sidecar generator + gen_core_kit_hbm hook)."""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gen_core_kit_hbm as G      # noqa: E402
import single_root_taps as T      # noqa: E402


def _toy(tmp, root=(220.344, 25.92), outline=(427.68, 246.24)):
    """the hfd_ep_static shape: one clk pin at (220.3,25.9), four SRAMs, W/E pin-register columns"""
    pdir = tmp / "plan"
    (pdir / "cores").mkdir(parents=True)
    (pdir / "die_plan.json").write_text("{}")
    pins = [dict(name="clk", layer="M5", x=root[0], y=root[1]), dict(name="d[0]", layer="M4", x=0.0, y=181.0)]
    (pdir / "cores" / "toy.json").write_text(json.dumps(pins))
    rects = [[17.28, 47.532, 188.568, 125.316], [239.112, 47.532, 410.4, 125.316],
             [17.28, 146.892, 188.568, 224.676], [239.112, 146.892, 410.4, 224.676]]
    (pdir / "core_macros.json").write_text(json.dumps(dict(halo_um=0.0, cores=dict(toy=dict(
        status="KNOWN", outline_um=list(outline), macros=[dict(name=f"m{i}", rect_um=r) for i, r in enumerate(rects)])))))
    views = tmp / "core_views.json"
    views.write_text(json.dumps(dict(plan=str(pdir / "die_plan.json"), plan_sha256="x", view_list=[dict(
        view="toy@0123456789ab", module="toy", outline_um=list(outline), pins_file="cores/toy.json",
        pins_sha256="0123456789ab" * 5)])))
    return views, rects


def test_generator_covers_far_columns_on_legal_sites(tmp_path):
    views, rects = _toy(tmp_path)
    out = tmp_path / "A.json"
    assert T.main(["--views", str(views), "--reach", "180", "--out", str(out)]) == 0
    r = json.load(open(out))["views"]["toy@0123456789ab"]
    assert r["reach_before_um"] > 400 and r["reach_after_um"] <= 180
    sites = r["clock_sites_um"]
    assert G.planned_clock_sites_text(sites, r["outline_um"])          # lattice + legal band
    for x, y in sites:                                                  # never ON a macro (hook would error)
        assert not any(x0 <= x <= x1 and y0 <= y <= y1 for x0, y0, x1, y1 in rects)
    # the W-edge register column (x~5, y 0-180) is within reach of a site, not only of the root
    col = np.array([[5.5, y] for y in range(5, 182, 4)])
    assert T.mind(col, sites).max() <= 180 < T.mind(col, [r["root"]]).max()


def test_short_reach_view_unchanged(tmp_path):
    views, _ = _toy(tmp_path, root=(213.84, 123.12), outline=(216.0, 129.6))
    d = json.loads(views.read_text())
    (Path(d["plan"]).parent / "core_macros.json").write_text(json.dumps(dict(halo_um=0.0, cores={})))
    out = tmp_path / "A.json"
    T.main(["--views", str(views), "--out", str(out)])
    doc = json.load(open(out))
    assert doc["views"] == {} or "toy@0123456789ab" not in doc["views"] or doc["report"][0]["reach_before_um"] > 220


def test_hook_exact_view_only(tmp_path):
    sc = tmp_path / "sc.json"
    sc.write_text(json.dumps(dict(variant="A", views={"toy@0123456789ab": dict(
        outline_um=[427.68, 246.24], pins_sha256="ab" * 32, clock_sites_um=[[220.32, 25.92], [8.64, 138.24]])})))
    v = dict(view="toy@0123456789ab", pins_sha256="ab" * 32)
    got = G.single_root_sites(str(sc), v, (427.68, 246.24))
    assert got["clock_sites_um"] == [[220.32, 25.92], [8.64, 138.24]] and got["variant"] == "A"
    assert G.single_root_sites("off", v, (427.68, 246.24)) is None
    assert G.single_root_sites(str(sc), dict(v, pins_sha256="cd" * 32), (427.68, 246.24)) is None   # other pin table
    assert G.single_root_sites(str(sc), v, (427.68, 250.56)) is None                                 # other outline


def test_committed_sidecars_are_legal():
    for f in G.SINGLE_ROOT_TAPS.values():
        doc = json.load(open(f))
        assert doc["schema"] == T.SCHEMA and doc["views"]
        for view, r in doc["views"].items():
            assert G.planned_clock_sites_text(r["clock_sites_um"], r["outline_um"]), view
            assert r["reach_before_um"] > T.CLK_REACH_GATE, view
