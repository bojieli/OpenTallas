"""Unit tests for the G0 checker, latency generator and render.   python3 -m pytest -q tools/die_plan/"""
import copy
import json
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import check  # noqa: E402
import gen  # noqa: E402
import schema  # noqa: E402

EX = json.loads((HERE / "examples" / "tiny_plan.json").read_text())


def g0(mut=None):
    p = copy.deepcopy(EX)
    if mut:
        mut(p)
    R, summ = check.run(p)
    return R, summ


def errs(mut, chk=None):
    R, _ = g0(mut)
    return [i["msg"] for i in R.errors() if chk is None or i["check"] == chk]


def port(p, pid):
    return next(x for x in p["ports"] if x["id"] == pid)


def part(p, n):
    return next(x for x in p["partitions"] if x["name"] == n)


def test_example_passes():
    R, summ = g0()
    assert R.errors() == [] and [i["check"] for i in R.items] == ["types"], R.items   # mid: no type-frame windows
    R2, _ = check.run(json.loads((HERE / "examples" / "tiny_plan_typegeo.json").read_text()))
    assert R2.items == [], R2.items
    assert summ["geometry"]["fill"] == 1.0
    assert summ["latency"]["x"] == 4


def test_not_abutted():
    e = errs(lambda p: part(p, "pb").update(origin_um=[2600.64, 0.0]), "abutment")
    assert any("do not abut" in x for x in e)


def test_overlap_and_grid():
    e = errs(lambda p: part(p, "pb").update(origin_um=[2500.0, 0.0]), "geometry")
    assert any("overlap" in x for x in e) and any("grid" in x for x in e)


def test_window_outside_face():
    assert any("outside the" in x for x in errs(lambda p: port(p, "x0").update(window_um=[850.0, 870.0])))


def test_mirrored_replica_pins_differ():
    # pm2 mirrored in y: its fx pins move in the type frame -> replicated-type pin table mismatch (or off-track)
    e = errs(lambda p: part(p, "pm2").update(orient="MX"), "abutment")
    assert any("pin table differs" in x or "off-track" in x for x in e)


def test_face_density():
    e = errs(lambda p: port(p, "x0").update(window_um=[400.0, 410.0]) or port(p, "x1").update(
        window_um=[400.0, 410.0]) or port(p, "x2").update(window_um=[400.0, 410.0]), "faces")
    assert any("/um > 6" in x for x in e)


def test_layer_budget():
    assert any("above partition_signal_max" in x for x in errs(lambda p: port(p, "c0").update(layers=["M8"])))


def test_hop_reach():
    e = errs(lambda p: p["die"].update(reach_um=500.0), "hops")
    assert any("lane x" in x and "> reach 500" in x for x in e)
    # two stations in the mid slot halve the hop -> pass at reach 500 once the latency table is regenerated
    def two(p):
        p["die"]["reach_um"] = 500.0
        for s in p["partition_types"]["mid"]["ft_slots"]:
            s["stations"] = 2
        p["latency"]["lanes"] = gen.latency_table(schema.Plan(p))
    assert errs(two) == []


def test_latency_checks():
    assert any("missing from the latency table" in x for x in errs(lambda p: p["latency"]["lanes"].pop("x")))
    assert any("plan gives 5" in x for x in errs(lambda p: p["latency"]["lanes"]["r"].update(cycles=3)))
    assert any("no latency table" in x for x in errs(lambda p: p.pop("latency")))


def test_cut_overflow():
    def m(p):
        p["die"]["layer_budget"]["cut_avail"] = {"M8": 0.0, "M9": 0.0}
        for t in p["partition_types"].values():
            t["ft_track_frac"] = 0.0001
    e = errs(m, "cuts")
    assert any("vertical cut" in x for x in e)


def test_clock_reset_leaf():
    assert any("no clock tap" in x for x in errs(lambda p: p["partition_types"]["mid"].pop("clock")))
    assert any("no reset" in x for x in errs(lambda p: p["partition_types"]["mid"].pop("reset")))
    assert any("unknown instance" in x for x in
               errs(lambda p: p["partition_types"]["mid"]["buses"][0].update(leaf="u_x.cfg_i")))


def test_gen_latency_and_render():
    with tempfile.TemporaryDirectory() as d:
        p = copy.deepcopy(EX)
        p.pop("latency")
        tab, sv, js = gen.write_latency(p, d)
        assert "localparam int LAT_X = 4;" in sv.read_text()
        assert json.loads(js.read_text())["lanes"]["r"]["cycles"] == 5
        R, summ = check.run(copy.deepcopy(EX), png=Path(d) / "p.png")
        assert (Path(d) / "p.png").stat().st_size > 10000


def test_gen_rtl_lint_and_bench():
    import shutil
    import subprocess
    import gen_rtl
    root = HERE.parent.parent
    rs = root / "rtl" / "lib" / "ot_reset_sync.sv"
    with tempfile.TemporaryDirectory() as d:
        files = [str(f) for f in gen_rtl.write_rtl(copy.deepcopy(EX), d, rtl_root=str(root))]
        src = files + [str(HERE / "examples" / "tiny_leaves.sv"), str(rs)]
        if shutil.which("verilator") and rs.is_file():
            r = subprocess.run(["verilator", "--lint-only", "-Wall", "-Wno-DECLFILENAME", "-Wno-UNUSED",
                                "--top-module", "tiny_top"] + src, capture_output=True, text=True)
            assert r.returncode == 0, r.stderr
        if shutil.which("iverilog") and rs.is_file():
            exe = str(Path(d) / "a.out")
            subprocess.run(["iverilog", "-g2012", "-o", exe, str(HERE / "examples" / "tb_tiny.sv")] + src, check=True)
            out = subprocess.run(["vvp", "-n", exe], capture_output=True, text=True).stdout
            assert "TB_TINY PASS" in out, out


def test_gen_rtl_refuses_open_ports():
    import gen_rtl
    root = HERE.parent.parent
    p = copy.deepcopy(EX)
    p["partition_types"]["sink"]["contents"][0]["bind"].pop("x_ep")
    try:
        gen_rtl.write_rtl(p, tempfile.mkdtemp(), rtl_root=str(root))
    except gen_rtl.GenError as e:
        assert "unbound ports ['x_ep']" in str(e)
    else:
        raise AssertionError("expected GenError")
    p = copy.deepcopy(EX)
    p["partition_types"]["mid"]["buses"][0].pop("leaf")
    try:
        gen_rtl.write_rtl(p, tempfile.mkdtemp())
    except gen_rtl.GenError as e:
        assert "not bound to any leaf port" in str(e)
    else:
        raise AssertionError("expected GenError")


def test_near_duplicate_types():
    def m(p):
        t = copy.deepcopy(p["partition_types"]["mid"])
        t["module"] = "tiny_mid2_part"
        p["partition_types"]["mid2"] = t
        part(p, "pm2")["type"] = "mid2"
    R, summ = g0(m)
    assert summ["types"]["near_duplicate_groups"] == 1 and summ["types"]["types"] == 4
    assert any("near-duplicate types ['mid', 'mid2']" in i["msg"] for i in R.items)
