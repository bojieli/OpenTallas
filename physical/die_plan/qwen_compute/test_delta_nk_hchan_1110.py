"""DIE-QC-97 11-10: QC NK H channel plan event (delta_nk_hchan_1110.py)."""
import importlib.util
import json
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("delta_nk_hchan_1110", HERE / "delta_nk_hchan_1110.py")
D = importlib.util.module_from_spec(spec)
spec.loader.exec_module(D)

NK = dict(module="qfd_tile_nk_a0c", outline_um=[457.92, 1157.76])


def _plan():
    return {"partition_types": {
        "cbx_a": {"hard_cores": [dict(NK, inst="u_t20", origin_um=[77.76, 77.76], orient="R0"),
                                 dict(NK, inst="u_t31", origin_um=[699.84, 1304.64], orient="MY"),
                                 dict(module="other", inst="u_x", outline_um=[10, 10], origin_um=[0, 0])]},
        "cbf_b": {"hard_cores": [dict(NK, inst="u_t00", origin_um=[86.4, 77.76], orient="R0")]},
        "sle": {"hard_cores": []}}}


def test_apply_marks_every_nk_instance_once():
    p, rep = D.apply(_plan())
    assert rep["types"] == ["cbf_b", "cbx_a"] and len(rep["instances"]) == 3
    assert rep["core_rect_um"] == [0.0, 830.0, 457.92, 990.0]
    for t in p["partition_types"].values():
        for h in t["hard_cores"]:
            assert ("route_channels" in h) == (h["module"] == "qfd_tile_nk_a0c")
    assert p["partition_types"]["cbx_a"]["hard_cores"][0]["route_channels"][0]["layers"] == ["M5", "M6"]
    with pytest.raises(SystemExit, match="already declared"):
        D.apply(p)


def test_outline_mismatch_refused():
    p = _plan()
    p["partition_types"]["cbf_b"]["hard_cores"][0]["outline_um"] = [457.92, 1000.0]
    with pytest.raises(SystemExit, match="outline"):
        D.apply(p)


def test_slice_update_and_cli(tmp_path):
    pl = tmp_path / "plan.json"
    pl.write_text(json.dumps(_plan()))
    sl = tmp_path / "slice.json"
    sl.write_text(json.dumps(dict(kind="core", module="qfd_tile_nk_a0c", outline_um=[457.92, 1157.76],
                                  keepouts=[dict(name="clock_entry_island", kind="island", use=["placement"],
                                                 rect_um=[224.652, 574.56, 233.292, 583.2])])))
    out, rep = tmp_path / "out.json", tmp_path / "rep.json"
    assert D.main([str(pl), "--out", str(out), "--report", str(rep), "--slice", str(sl)]) == 0
    s = json.loads(sl.read_text())
    assert [k["kind"] for k in s["keepouts"]] == ["island", "route_channel"]
    assert s["keepouts"][1]["layers"] == ["M5", "M6"] and s["keepouts"][1]["use"] == []
    assert json.loads(pl.read_text()) == _plan()        # --out leaves the base plan untouched
    assert json.loads(rep.read_text())["module"] == "qfd_tile_nk_a0c"


def test_compact_input_stays_compact(tmp_path):
    pl = tmp_path / "plan.json"
    pl.write_text(json.dumps(_plan(), separators=(",", ":")) + "\n")
    out = tmp_path / "out.json"
    assert D.main([str(pl), "--out", str(out)]) == 0
    text = out.read_text()
    assert "\n " not in text and text.endswith("\n")
    assert json.dumps(json.loads(text)["partition_types"]["sle"], separators=(",", ":")) in text
