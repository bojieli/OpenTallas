"""Per-cut tap derivation preserves explicit clock names and qualifies placed inputs."""
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tap_derive


def test_cut_derives_only_geometry_matched_native_bins(tmp_path):
    tile = dict(outline_um=[400, 400], buses=[], clock=dict(
        tap_mode="explicit", taps=[dict(name="clk", xy=[200, 200])]))
    raw = dict(die=dict(name="test", outline_um=[400, 400], reach_um=405),
               partition_types={"T": tile}, partitions=[dict(name="p0", type="T")],
               ports=[], lanes=[])
    native = dict(type="T", native_only=True, placed_kit="place-A", bin_um=10,
                  bins=[[125, 125, 2500], [275, 275, 2500], [125, 275, 2000]])
    (tmp_path / "native.json").write_text(json.dumps(native))
    manifest = tmp_path / "manifest.json"
    args = raw, tmp_path / "plan.json", tmp_path, manifest
    entry = {"bins": "native.json", "footprint_sha256": "different"}
    manifest.write_text(json.dumps({"T": entry}))
    selected, report = tap_derive.derive(*args)
    assert not selected
    assert report["T"]["status"] == "placed footprint differs"

    entry["footprint_sha256"] = tap_derive.footprint_digest(tile)
    manifest.write_text(json.dumps({"T": entry}))
    selected, report = tap_derive.derive(*args)
    assert selected == ["T"]
    assert report["T"]["max_sinks_before"] == 7000
    assert report["T"]["max_sinks_after"] <= 5000
    assert tile["clock"]["taps"][0] == {"name": "clk", "xy": [200, 200]}
    names = [row["name"] for row in tile["clock"]["taps"]]
    assert names == ["clk"] + [f"clk_t{i}" for i in range(1, len(names))]
    assert tap_derive.derive(*args)[0] == []


def test_manifest_builder_feeds_derive(tmp_path):
    import tap_manifest_build
    tile = dict(outline_um=[400, 400], buses=[], clock=dict(
        tap_mode="explicit", taps=[dict(name="clk", xy=[200, 200])]))
    raw = dict(die=dict(name="test", outline_um=[400, 400], reach_um=405),
               partition_types={"T": tile}, partitions=[dict(name="p0", type="T")],
               ports=[], lanes=[])
    lines = [f"clk\tu_{i}\tDFF\t{125 + (i % 2) * 150}.0\t{125 + (i % 3) * 70}.0" for i in range(7000)]
    lines += ["clk\tu_station_x\tDFF\t10.0\t10.0"]
    tsv = tmp_path / "sinks.tsv"
    tsv.write_text("\n".join(lines) + "\n")
    manifest = tap_manifest_build.build(raw, tmp_path / "m", {"T": tsv})
    assert manifest["T"]["footprint_basis"] == "current-plan"
    selected, report = tap_derive.derive(raw, tmp_path / "plan.json", tmp_path, tmp_path / "m" / "manifest.json")
    assert selected == ["T"]
    assert report["T"]["max_sinks_before"] > 5000 >= report["T"]["max_sinks_after"]


def _hot_tile(cap):
    return dict(outline_um=[400, 400], buses=[], clock=dict(
        tap_mode="explicit", tap_max_sinks=cap, taps=[dict(name="clk", xy=[200, 200])]))


def _hot_case(tmp_path, cap):
    tile = _hot_tile(cap)
    raw = dict(die=dict(name="test", outline_um=[400, 400], reach_um=405),
               partition_types={"T": tile}, partitions=[dict(name="p0", type="T")], ports=[], lanes=[])
    # 3,900 sinks all nearest the single tap: over a 1000 plan cap, under the old tool constant 5000
    native = dict(type="T", native_only=True, placed_kit="place-A", bin_um=10,
                  bins=[[125, 125, 650], [135, 125, 650], [275, 275, 650], [285, 275, 650], [125, 275, 650], [135, 275, 650]])
    (tmp_path / "native.json").write_text(json.dumps(native))
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"T": {"bins": "native.json", "footprint_sha256": tap_derive.footprint_digest(tile)}}))
    return raw, (raw, tmp_path / "plan.json", tmp_path, manifest), tile


def test_gate_rederive_uses_the_plan_cap_not_5000(tmp_path):
    """C-TAP-LOAD safety: row_gate calls derive() with no cap; a 1000-cap type carrying 3,900 sinks on one tap must be
    re-derived (the old default cap=5000 reported it 'within limits' and changed nothing)."""
    _, args, tile = _hot_case(tmp_path, 1000)
    selected, report = tap_derive.derive(*args)
    assert selected == ["T"], report
    assert report["T"]["cap"] == 1000 and report["T"]["max_sinks_before"] == 3900
    assert report["T"]["max_sinks_after"] <= 1000


def test_explicit_cap_still_forces_a_constant(tmp_path):
    _, args, tile = _hot_case(tmp_path, 1000)
    selected, report = tap_derive.derive(*args, cap=5000)
    assert selected == [] and report["T"]["status"] == "within limits"


def test_cap_follows_each_types_own_plan(tmp_path):
    _, args, tile = _hot_case(tmp_path, 4000)       # a 4000-cap type with 3,900 sinks is genuinely fine
    selected, report = tap_derive.derive(*args)
    assert selected == [] and report["T"]["cap"] == 4000


def test_row_gate_passes_no_constant_cap():
    src = (Path(__file__).resolve().parent / "row_gate.py").read_text()
    for call in ("tap_derive.derive(", "tap_derive.density_results("):
        line = [ln for ln in src.splitlines() if call in ln][0]
        assert "cap" not in line, line
