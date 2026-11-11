"""binddiff: s81p_-prefixed bound RTL and native_internal_stations dirs reach the per-type digest; bind-root paths
inside files do not count as changes."""
import importlib.util
import json
from pathlib import Path

spec = importlib.util.spec_from_file_location("binddiff", Path(__file__).with_name("binddiff.py"))
bd = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bd)

TYPES = {"slice_station__t27", "slice_station__t49", "eng__t1"}


def make(d, t27_body, extra_root_ref=True):
    d.mkdir()
    (d / "rtl").mkdir()
    (d / "rtl" / "s81p_slice_station__t27.sv").write_text(t27_body)
    (d / "rtl" / "s81p_slice_station__t49.sv").write_text("module t49; endmodule\n")
    (d / "rtl" / "bind_cells.sv").write_text("module ot_dp_st; endmodule\n")
    n = d / "native_internal_stations" / "eng__t1"
    n.mkdir(parents=True)
    ref = str(d.resolve()) + "/native_internal_stations/eng__t1/s81p_eng__t1.sv" if extra_root_ref else "x"
    (n / "kit_rtl.json").write_text(json.dumps({"files": [ref]}))
    (d / "bind_report.json").write_text(json.dumps({"types": {t: {"n": 1} for t in TYPES}, "errors": []}))
    return d


def test_type_of_prefixed_and_native():
    assert bd.type_of("rtl/s81p_slice_station__t27.sv", TYPES) == "slice_station__t27"
    assert bd.type_of("rtl/s81p_slice_station__t27.reset_tree.json", TYPES) == "slice_station__t27"
    assert bd.type_of("rtl/slice_station__t49.sv", TYPES) == "slice_station__t49"
    assert bd.type_of("native_internal_stations/eng__t1/kit_rtl.json", TYPES) == "eng__t1"
    assert bd.type_of("rtl/bind_cells.sv", TYPES) is None
    assert bd.type_of("rtl/s81p_slice_station__t2.sv", TYPES) is None


def test_prefixed_rtl_change_is_seen(tmp_path):
    a = make(tmp_path / "a", "module t27; ot_dp_st u_ft_0(); endmodule\n")
    b = make(tmp_path / "b", "module t27; ot_dp_st u_ft_0(); ot_dp_lk u_fl_0(); endmodule\n")
    r = bd.compare(a, b, TYPES, {"slice_station__t27"})
    assert r["changed"] == ["slice_station__t27"]
    assert r["event_unchanged"] == [] and r["changed_not_in_event"] == []


def test_bind_root_path_is_not_a_change(tmp_path):
    a = make(tmp_path / "bind8", "same\n")
    b = make(tmp_path / "bind_ftlk_longer_name", "same\n")
    r = bd.compare(a, b, TYPES, set())
    assert r["changed"] == [] and r["differing_files"] == 0


def test_real_native_change_outside_event_is_reported(tmp_path):
    a = make(tmp_path / "a", "same\n")
    b = make(tmp_path / "b", "same\n", extra_root_ref=False)
    r = bd.compare(a, b, TYPES, {"slice_station__t27"})
    assert r["changed_not_in_event"] == ["eng__t1"]
    assert r["event_unchanged"] == ["slice_station__t27"]
