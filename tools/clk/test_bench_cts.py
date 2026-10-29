"""CLK-TOOL-2 tests for tools/clk/bench_cts.py (P1b per-region TritonCTS benchmark: legality + verdict logic)."""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import bench_cts as B  # noqa: E402


def _case(tmp_path, ours_tt, variants):
    meta = dict(region="r", ntaps=3, glue=[dict(inst="g0", port="p0"), dict(inst="g1", port="p1")],
                cores=[dict(inst="m0", name="c", rect_local=[100, 100, 200, 200], pins={"clk0": "pc"})],
                declared={"p0": {"TT": 250, "FF": 202.5}, "p1": {"TT": 250, "FF": 202.5}, "pc": {"TT": 665.8, "FF": 576.5}},
                ours={"TT": {"spread": ours_tt}, "FF": {"spread": ours_tt}})
    (tmp_path / "meta.json").write_text(json.dumps(meta))
    for v, (arr, bufs, cpfail) in variants.items():
        d = tmp_path / v
        d.mkdir()
        (d / "log_TT.txt").write_text(("OT_CHECK_PLACEMENT_FAIL x\n" if cpfail else "") + "OT_DONE\n")
        for C in ("TT", "FF"):
            lines = [f"S g0/CLK {arr[0]} 0 50 0", f"S g1/CLK {arr[1]} 0 60 0", f"S m0/clk0 {arr[2]} 0 40 0"]
            lines += [f"B b{i} BUFx24_ASAP7_75t_R {x} {y}" for i, (x, y) in enumerate(bufs)]
            (d / f"arr_{C}.txt").write_text("\n".join(lines) + "\n")
    return B.summ(type("A", (), dict(out=str(tmp_path), flag_ps=20.0))())


def test_spread_adds_declared_insertion_and_flags_planner_defect(tmp_path):
    # glue 600/610 + 250, core pin 190 + 665.8 -> 850 / 860 / 855.8 -> spread 10 (ours 45 -> +35 > 20)
    r = _case(tmp_path, 45.0, {"v4": ([600, 610, 190], [(50, 50)], False)})
    assert r["variants"][0]["TT"]["spread"] == round(max(850, 860, 190 + 665.8) - min(850, 860, 190 + 665.8), 1)
    assert r["best_legal"] == "v4" and r["verdict"] == "PLANNER_DEFECT"


def test_ok_within_20ps(tmp_path):
    r = _case(tmp_path, 20.0, {"v4": ([600, 610, 190], [(50, 50)], False)})
    assert r["verdict"] == "OK"


def test_buffer_inside_core_or_placement_fail_is_never_best(tmp_path):
    r = _case(tmp_path, 300.0, {"v4": ([600, 610, 190], [(150, 150)], False),
                                "v6": ([600, 610, 190], [(50, 50)], True)})
    assert [v["legal"] for v in r["variants"]] == [False, False]
    assert r["variants"][0]["bufs_inside_cores"] == 1
    assert r["best_legal"] is None and r["verdict"] == "NO_LEGAL_TRITONCTS"


def test_no_die_names_in_bench_code():
    src = (HERE / "bench_cts.py").read_text()
    for die in ("qwen", "s81", "kv_", "hbm", "head_", "c_W2", "svc_"):
        assert not re.search(die, src, re.I), die
