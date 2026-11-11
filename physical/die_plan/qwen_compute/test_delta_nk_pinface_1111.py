"""DIE-QC-97 11-11: QC NK pin-face plan event (delta_nk_pinface_1111.py)."""
import importlib.util
import json
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("delta_nk_pinface_1111", HERE / "delta_nk_pinface_1111.py")
D = importlib.util.module_from_spec(spec)
spec.loader.exec_module(D)

NK = dict(module="qfd_tile_nk_a0c", outline_um=[457.92, 1157.76], pins_file="cores/a0_nk_pins_ck1109.json")
CH = [dict(dir="EW", span_um=[830.0, 990.0], layers=["M5", "M6"], reason="x")]


def _plan():
    return {"note": "keep", "partition_types": {
        "cbx_a": {"hard_cores": [dict(NK, inst="u_t20", origin_um=[77.76, 77.76], orient="R0", route_channels=CH),
                                 dict(NK, inst="u_t31", origin_um=[699.84, 1304.64], orient="MY"),
                                 dict(module="other", inst="u_x", outline_um=[10, 10], origin_um=[0, 0],
                                      pins_file="cores/x.json")]},
        "cbf_b": {"hard_cores": [dict(NK, inst="u_t00", origin_um=[86.4, 77.76], orient="R0", route_channels=CH)]},
        "sle": {"hard_cores": [], "buses": [1, 2]}}}


def _pins(wx, ex):
    ps = [dict(name="ck", layer="M5", x=228.972, y=578.88)]
    for b, y0 in (("n_a", 699.564), ("n_b", 800.748), ("t_out", 900.972), ("n_y", 1001.388)):
        ps += [dict(name=f"{b}[{i}]", layer="M4", x=wx, y=round(y0 + 0.192 * i, 3)) for i in range(514)]
    ps += [dict(name=f"tap[{i}]", layer="M4", x=ex, y=round(561.036 + 0.192 * i, 3)) for i in range(508)]
    return dict(schema="s", core="qfd_tile_nk_a0c", source="old", pins=ps)


def test_apply_repoints_every_nk_core_and_drops_channels():
    p, rep = D.apply(_plan())
    assert rep["cores"] == 3 and rep["types"] == ["cbf_b", "cbx_a"] and rep["route_channels_removed"] == 2
    for t in p["partition_types"].values():
        for h in t["hard_cores"]:
            if h["module"] == "qfd_tile_nk_a0c":
                assert h["pins_file"] == D.NEW_PINS and "route_channels" not in h
                assert h["origin_um"] and h["orient"]          # placement untouched
            else:
                assert h["pins_file"] == "cores/x.json"
    assert p["partition_types"]["sle"] == _plan()["partition_types"]["sle"] and p["note"] == "keep"
    with pytest.raises(SystemExit, match="event applied"):
        D.apply(p)


def test_move_pins_same_y_and_layer_only_three_buses():
    old = _pins(0.096, 457.824)
    new, n = D.move_pins(old, 0.096, 457.824, "new")
    assert n == 1542 and new["source"] == "new"
    by = {p["name"]: p for p in old["pins"]}
    for p in new["pins"]:
        o = by[p["name"]]
        assert (p["layer"], p["y"]) == (o["layer"], o["y"])
        assert p["x"] == (457.824 if D._bus(p["name"]) in ("n_a", "n_b", "t_out") else o["x"])


def test_move_pins_refuses_collision_and_wrong_face():
    old = _pins(0.096, 457.824)
    old["pins"].append(dict(name="tile_id[0]", layer="M4", x=457.824, y=800.748))   # E-face pin on an n_b track
    with pytest.raises(ValueError, match="already in use"):
        D.move_pins(old, 0.096, 457.824, "new")
    with pytest.raises(ValueError, match="not on the W face"):
        D.move_pins(_pins(0.042, 457.824), 0.096, 457.824, "new")


def test_cli_keeps_serialization_and_writes_event(tmp_path):
    pl = tmp_path / "plan.json"
    pl.write_text(json.dumps(_plan(), separators=(",", ":")) + "\n")
    out, ev = tmp_path / "out.json", tmp_path / "ev.json"
    assert D.main([str(pl), str(out), str(ev)]) == 0
    text = out.read_text()
    assert "\n " not in text and text.endswith("\n")
    assert json.dumps(_plan()["partition_types"]["sle"], separators=(",", ":")) in text
    e = json.loads(ev.read_text())
    assert e["rtl_change"] is False and e["pin_cycles"] == 0 and e["cores"] == 3
    assert json.loads(pl.read_text()) == _plan()


def test_repo_pin_files_moved():
    """the committed pf1111 pin file is the ck1109 file with exactly n_a / n_b / t_out on the E face"""
    old = json.loads((D.POR / D.OLD_PINS).read_text())
    new = json.loads((D.POR / D.NEW_PINS).read_text())
    exp, _ = D.move_pins(old, 0.096, 457.824, new["source"])
    assert new == exp
    dd = json.loads(D.DIR_PINS.read_text())
    assert {p["x"] for p in dd["pins"] if D._bus(p["name"]) in D.BUSES} == {457.878}
    assert {p["x"] for p in dd["pins"] if D._bus(p["name"]) == "n_y"} == {0.042}
