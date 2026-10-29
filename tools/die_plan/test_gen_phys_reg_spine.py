"""DIE-HEAD-17 REG-SPINE (opt-in partition_types.<t>.reg_spine): register clock spine + local trees + core early-tap
branches in PRE_CTS.  Default kits stay byte-identical; the planner is deterministic and honours the radius cap.
python3 -m pytest -q tools/die_plan/test_gen_phys_reg_spine.py"""
import copy
import filecmp
import json
import random
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gen_phys  # noqa: E402
import reg_spine  # noqa: E402
import schema  # noqa: E402
from test_g2 import PAIR  # noqa: E402

SPEC = dict(trunk=[["R", 50.0, 50.0, "-"], ["A", 50.0, 20.0, "CLK"], ["B", 50.0, 80.0, "CLK"], ["X", 90.0, 50.0, "CLK"],
                   ["H", 90.0, 90.0, "X"]],
            express=["X"], radius_um=30.0, bin_um=[40.0, 40.0], min_bin_sinks=20, min_tap_sinks=5,
            keepouts_um=[[40.0, 40.0, 60.0, 60.0]], pads={"0": 2, "3": 1},
            core_taps=[dict(inst="u_c", pin="ck", xy=[55.0, 45.0], stages=3, repeaters=[[52.0, 30.0]])],
            root_split_xy=[50.0, 50.0], cts_extra_nets=["fclk_in_i"])


def _sinks(n=400, seed=7):
    rnd = random.Random(seed)
    return sorted((f"r{i}", round(rnd.uniform(0, 100), 2), round(rnd.uniform(0, 100), 2)) for i in range(n))


def _same_tree(a, b):
    c = filecmp.dircmp(a, b)
    assert not c.left_only and not c.right_only and not c.diff_files, (c.left_only, c.right_only, c.diff_files)
    for sub in c.common_dirs:
        _same_tree(Path(a) / sub, Path(b) / sub)


def test_planner_deterministic_radius_and_express():
    s = _sinks()
    t1, taps1, a1 = reg_spine.plan(SPEC, s)
    t2, taps2, a2 = reg_spine.plan(copy.deepcopy(SPEC), list(reversed(s)))
    assert taps1 == taps2 and a1 == a2
    assert len(a1) == len(s) and set(a1.values()) == {t["id"] for t in taps1}
    assert all(t["node"] not in ("X", "R") for t in taps1)           # express / root marker carry no taps
    for t in taps1:                                                 # taps outside the keep-out
        assert not (40.0 < t["x"] < 60.0 and 40.0 < t["y"] < 60.0)
    assert [t["pad"] for t in taps1[:4]] == [2, 0, 0, 1]
    # radius cap on the cluster centroids (the snap-out may move a tap driver beyond it, reported per tap)
    cent = reg_spine.cluster(s, SPEC)
    for i, c in enumerate(cent):
        pts = [(x, y) for n, x, y in s if min(range(len(cent)), key=lambda j: (abs(cent[j][0] - x) + abs(cent[j][1] - y), j)) == i]
        assert max(abs(x - c[0]) + abs(y - c[1]) for x, y in pts) <= SPEC["radius_um"] + 1e-9


def test_planner_cli_writes_tcl():
    with tempfile.TemporaryDirectory() as d:
        sp = Path(d) / "spec.json"; sp.write_text(json.dumps(SPEC))
        sk = Path(d) / "sinks.txt"
        sk.write_text("".join(f"clk {n} DFFHQNx1_ASAP7_75t_R CLK {x} {y} PLACED\n" for n, x, y in _sinks())
                      + "clk u_c core ck 55 45 FIRM\n")              # core pin: not a register sink
        out = subprocess.run([sys.executable, str(HERE / "reg_spine.py"), str(sp), str(sk), d], capture_output=True,
                             text=True, check=True).stdout
        assert out.startswith("REG_SPINE sinks 400 taps ")
        tcl = (Path(d) / "reg_spine_plan.tcl").read_text()
        assert "set rsp_cfg {" in tcl and "root_split_xy {50.0 50.0}" in tcl and "cts_extra_nets {fclk_in_i}" in tcl
        assert "  {u_c ck 55.0 45.0 3 {{52.0 30.0}}}\n" in tcl
        assert "  {R 50.0 50.0 -}\n" in tcl and "  {H 90.0 90.0 X}\n" in tcl
        assert "u_c" not in (Path(d) / "reg_spine_assign.txt").read_text()


def test_bad_parent_fails_closed():
    bad = copy.deepcopy(SPEC); bad["trunk"].append(["Z", 1.0, 1.0, "nope"])
    try:
        reg_spine.plan(bad, _sinks())
    except ValueError as e:
        assert "unknown parent" in str(e)
    else:
        raise AssertionError("unknown trunk parent accepted")


def test_schema_accepts_spec():
    raw = copy.deepcopy(PAIR)
    raw["partition_types"]["fa"]["reg_spine"] = copy.deepcopy(SPEC)
    schema.Plan(raw)


def test_kit_byte_identical_without_spine_and_hook_with_it():
    P0 = schema.Plan(copy.deepcopy(PAIR))
    raw = copy.deepcopy(PAIR)
    raw["partition_types"]["fa"]["reg_spine"] = copy.deepcopy(SPEC)
    P1 = schema.Plan(raw)
    with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b, tempfile.TemporaryDirectory() as c:
        gen_phys.write_type_kit(P0, "fa", a, [])
        gen_phys.write_type_kit(schema.Plan(copy.deepcopy(PAIR)), "fa", b, [])
        _same_tree(Path(a) / "fa", Path(b) / "fa")
        k0 = Path(a) / "fa"
        assert not (k0 / "reg_spine.json").exists() and "OT_TAP_REPORT_ONLY" not in (k0 / "config.mk").read_text()
        assert "reg_spine" not in (k0 / "pre_cts.tcl").read_text()
        gen_phys.write_type_kit(P1, "fa", c, [])
        k1 = Path(c) / "fa"
        assert json.loads((k1 / "reg_spine.json").read_text()) == json.loads(json.dumps(SPEC))
        assert (k1 / "reg_spine.py").read_text() == (HERE / "reg_spine.py").read_text()
        assert (k1 / "reg_spine.tcl").read_text() == (HERE / "reg_spine.tcl").read_text()
        pre0, pre1 = (k0 / "pre_cts.tcl").read_text(), (k1 / "pre_cts.tcl").read_text()
        assert pre1 == pre0 + "\nuplevel #0 {source /work/reg_spine.tcl}\n"
        cfg0, cfg1 = (k0 / "config.mk").read_text().splitlines(), (k1 / "config.mk").read_text().splitlines()
        assert [x for x in cfg1 if x not in cfg0] == ["export OT_TAP_REPORT_ONLY = 1"]
        assert cfg1.index("export OT_TAP_REPORT_ONLY = 1") == cfg1.index("export POST_CTS_TCL = /work/cts_post.tcl") + 1
        # every other kit file is unchanged
        c_ = filecmp.dircmp(k0, k1)
        assert set(c_.right_only) == {"reg_spine.json", "reg_spine.py", "reg_spine.tcl"} and not c_.left_only
        assert set(c_.diff_files) <= {"pre_cts.tcl", "config.mk"}, c_.diff_files
