"""LEAF-DRT73-1 11-13: plan hard cores in an unrealizable orient -> nearest realizable one (box kept, offsets on track)"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import macro_grid_snap as M  # noqa: E402
import orient_realize as OR  # noqa: E402
from test_macro_grid_snap import KIT_TRACKS, hcpl_lef  # noqa: E402


def plan(lef, cores):
    return {"partition_types": {"ot_s81sl_leaf__t13": {"hard_cores": [
        dict(inst=i, lef=str(lef), module="HC", orient=o, origin_um=[100.008, 200.016], outline_um=[14.4, 14.4],
             track_offset_um=off) for i, o, off in cores]}}}


def test_r180_my_become_mx_r0_with_on_track_offsets(tmp_path):
    s, p = hcpl_lef(tmp_path)
    P = plan(p, [("a", "R180", [0.108, 0.012]), ("b", "MY", [0.108, 0.012]), ("c", "MX", [0.1, 0.036]),
                 ("d", "R0", [0.1, 0.008])])
    ch, refused = OR.realize(P, "/", tracks=KIT_TRACKS)
    assert refused == [] and [(c["inst"], c["orient"]) for c in ch] == [("a", ["R180", "MX"]), ("b", ["MY", "R0"])]
    hc = {h["inst"]: h for h in P["partition_types"]["ot_s81sl_leaf__t13"]["hard_cores"]}
    for i in "ab":
        x, y = (hc[i]["origin_um"][k] + hc[i]["track_offset_um"][k] for k in (0, 1))
        assert M.off_track(s, x, y, hc[i]["orient"], KIT_TRACKS) == {"x": 0, "y": 0}
        assert hc[i]["origin_um"] == [100.008, 200.016] and hc[i]["outline_um"] == [14.4, 14.4]
    assert ch[0]["faces_change_side"] == {"MY": {"E": 0, "W": 1}}
    assert ch[0]["unrealizable_axes"] == ["x"]
    assert hc["c"]["track_offset_um"] == [0.1, 0.036] and hc["d"]["orient"] == "R0"   # realizable cores: untouched


def test_cli_dry_run_and_out(tmp_path):
    _, p = hcpl_lef(tmp_path)
    src = tmp_path / "plan.json"
    src.write_text(json.dumps(plan(p, [("a", "R180", [0.108, 0.012])])))
    rep, out = tmp_path / "rep.json", tmp_path / "out.json"
    real = OR.plan_tracks
    OR.plan_tracks = lambda _plan: KIT_TRACKS
    try:
        assert OR.main([str(src), "--report", str(rep)]) == 0 and not out.exists()
        assert OR.main([str(src), "--report", str(rep), "--out", str(out)]) == 0
    finally:
        OR.plan_tracks = real
    r = json.loads(rep.read_text())
    assert r["changed"] == 1 and r["by_move"] == {"R180->MX": 1}
    assert json.loads(out.read_text())["partition_types"]["ot_s81sl_leaf__t13"]["hard_cores"][0]["orient"] == "MX"
