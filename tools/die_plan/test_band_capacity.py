"""Unit tests for the G0 band-capacity check (HEAD-PLAN-R4 11-17).   python3 -m pytest -q tools/die_plan/test_band_capacity.py"""
import json
import sys
import types
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import band_capacity as BC  # noqa: E402
import check as C  # noqa: E402

TCL = r"""set cland_groups {
 {{u_core\.u\.g_a\\\[0\\\][/.].*} {0 0 10 1} stage:a}
 {{u_core\.u\.g_b\\\[0\\\][/.].*} {20 0 30 1} stage:b}
 {{u_core\.u\.g_c\\\[0\\\][/.].*} {20 0 30 1} stage:b}
 {u_wrd {40 0 44 4} reader-start:x}
}
dict set ::cland_native_leaf_regex {u_core\.u\.g_a\\\[0\\\][/.].*} {^u_core\.u\.g_a\\\[0\\\]\.q.*}
dict set ::cland_native_tag_density {stage:a} 0.5
"""
STAT = """   Number of cells:   10
      40  11.6640  DFFHQNx1_ASAP7_75t_R
       5   0.4374  INVx1_ASAP7_75t_R
"""
# DFFHQNx1 = 0.2916 um2 each
NET = "\n".join(
    [f"DFFHQNx1_ASAP7_75t_R \\u_core.u.g_a[0].q{i} (" for i in range(10)] +      # 10 FF -> 2.916 / 0.5 = 5.832 over 10
    [f"DFFHQNx1_ASAP7_75t_R \\u_core.u.g_b[0].r.f{i} (" for i in range(20)] +      # shared band 20+10 FF
    [f"DFFHQNx1_ASAP7_75t_R \\u_core.u.g_c[0].r.f{i} (" for i in range(10)] +
    [f"INVx1_ASAP7_75t_R \\u_core.u.g_b[0].r.n{i} (" for i in range(5)])          # comb: not placed


def _measure(tmp_path):
    for n, s in (("lp.tcl", TCL), ("n.v", NET), ("st.txt", STAT)):
        (tmp_path / n).write_text(s)
    return BC.measure(tmp_path / "lp.tcl", tmp_path / "n.v", tmp_path / "st.txt", "T")


def test_measure_density_shared_and_ff_only(tmp_path):
    res = _measure(tmp_path)
    rows = {tuple(r["tags"]): r for r in res["rows"]}
    a = rows[("stage:a",)]
    assert a["nff"] == 10 and abs(a["fill"] - 0.5832) < 1e-3          # density sizing
    b = rows[("stage:b",)]
    assert b["nff"] == 30                                                # both groups summed into the one rect
    sites = -(-round(0.2916 / 0.27 / 0.4 / 0.054, 6) // 1)              # the proc's 40 % site sizing per flop
    assert abs(b["need_um2"] - 30 * sites * 0.054 * 0.27) < 1e-2
    assert b["fill"] > 1.0 and res["over_error"] == 1


def _plan(rect_b):
    t = {"outline_um": [100, 100], "clock": {"landing_contract": {"native_stage_groups": {"groups": [
        {"prefix": "a", "rect_um": [0, 0, 10, 1], "tag": "stage:a"},
        {"prefix": "b", "rect_um": rect_b, "tag": "stage:b"},
        {"prefix": "c", "rect_um": rect_b, "tag": "stage:b"}]}}}}
    return types.SimpleNamespace(types={"T": t})


def test_g0_reads_sidecar_and_plan_rects(tmp_path):
    res = _measure(tmp_path)
    (tmp_path / "band_fill").mkdir()
    (tmp_path / "band_fill" / "T.json").write_text(json.dumps(res))
    R = C.Report()
    s = BC.check(_plan([20, 0, 30, 1]), R, tmp_path)
    assert s["over_error"] == 1 and any(i["level"] == "ERROR" and "stage:b" in i["msg"] for i in R.items)
    R2 = C.Report()                                                      # grown in the plan -> clears without re-measure
    s2 = BC.check(_plan([20, 0, 30, 5]), R2, tmp_path)
    assert s2["over_error"] == 0 and not R2.errors()


def test_g0_silent_without_sidecar(tmp_path):
    R = C.Report()
    s = BC.check(_plan([20, 0, 30, 1]), R, tmp_path)
    assert s["bands"] == 0 and not R.items


def test_warn_band(tmp_path):
    res = {"type": "T", "rows": [{"tags": ["stage:a"], "rects": [[0, 0, 10, 1]], "need_um2": 7.5}]}
    (tmp_path / "band_fill").mkdir()
    (tmp_path / "band_fill" / "T.json").write_text(json.dumps(res))
    R = C.Report()
    s = BC.check(_plan([20, 0, 30, 5]), R, tmp_path)
    assert s["over_warn"] == 1 and not R.errors() and R.items[0]["level"] == "WARN"


def test_reader_start_box_um_opt_in():
    from landing_place import _chain_clear_of_hard_cores
    t = {"outline_um": [400, 400], "hard_cores": []}
    assert _chain_clear_of_hard_cores(t, (5, 5), [{"xy_um": [20, 20]}]) == [[17.84, 17.84, 22.16, 22.16]]   # default
    (r,) = _chain_clear_of_hard_cores(t, (5, 5), [{"xy_um": [20, 20], "box_um": [4.32, 12.96]}])
    assert [round(v, 2) for v in r] == [17.84, 13.52, 22.16, 26.48]


def test_reader_start_box_um_opt_in():
    from landing_place import _chain_clear_of_hard_cores
    t = {"outline_um": [400, 400], "hard_cores": []}
    assert _chain_clear_of_hard_cores(t, (5, 5), [{"xy_um": [20, 20]}]) == [[17.84, 17.84, 22.16, 22.16]]   # default
    (r,) = _chain_clear_of_hard_cores(t, (5, 5), [{"xy_um": [20, 20], "box_um": [4.32, 12.96]}])
    assert [round(v, 2) for v in r] == [17.84, 13.52, 22.16, 26.48]


def test_g0_reader_box_um(tmp_path):
    res = {"type": "T", "rows": [{"tags": ["reader-start:x"], "rects": [[40, 0, 44.32, 4.32]], "need_um2": 27.0,
                                  "groups": [{"prefix": "u_cland_reader_start_x_1", "tag": "reader-start:x", "nff": 37}]}]}
    (tmp_path / "band_fill").mkdir()
    (tmp_path / "band_fill" / "T.json").write_text(json.dumps(res))
    P = _plan([20, 0, 30, 5])
    R = C.Report()
    assert BC.check(P, R, tmp_path)["over_error"] == 1
    P.types["T"]["clock"]["landing_reader_start"] = {"depth": 2, "branches": {"x": {"stages": [
        {"xy_um": [1, 1], "raw_reset": "r"}, {"xy_um": [42, 2], "raw_reset": "r", "box_um": [7.56, 7.56]}]}}}
    R2 = C.Report()
    s = BC.check(P, R2, tmp_path)
    assert s["over_error"] == 0 and s["over_warn"] == 0
