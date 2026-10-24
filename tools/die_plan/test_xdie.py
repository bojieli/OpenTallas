"""PLAN-TOOL5 cross-die G0C rules (COORD die-plan visual review 10-23 (a)-(e)).   python3 -m pytest -q tools/die_plan/"""
import copy
import json
import random
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import check  # noqa: E402
import die_io  # noqa: E402
import reach  # noqa: E402
import schema  # noqa: E402
import xdie  # noqa: E402

EX = json.loads((HERE / "examples" / "tiny_plan.json").read_text())
REPO = HERE.parent.parent


def run(mut=None, plan_dir=None, completeness=True):
    p = copy.deepcopy(EX)
    if mut:
        mut(p)
    return check.run(p, plan_dir=plan_dir, completeness=completeness)


def errs(mut, chk, plan_dir=None):
    R, _ = run(mut, plan_dir)
    return [i["msg"] for i in R.errors() if i["check"] == chk]


# ------------------------------------------------------------------------------------------------- (c) reach
def test_reach_table_matches_source():
    src = REPO / reach.SOURCE
    if not src.exists():
        pytest.skip(f"{reach.SOURCE} not in this checkout")
    d = reach.derive(src)
    assert d == reach.MEASURED
    assert reach.TABLE["M4"]["reach_um"] == 405.0 and reach.TABLE["M4"]["measured_um"] == 452.5   # owner local plan
    assert reach.TABLE["M8"]["reach_um"] == 1001.2 and reach.TABLE["M9"]["reach_um"] == 1012.8


def test_reach_layer_class_and_margin():
    R, s = run()
    assert s["reach"]["over"] == 0 and s["reach"]["layers"] == ["M8", "M9"]        # die_use ft_reserved -> M8/M9
    assert s["reach"]["over_if_partition_layers"]["lanes"] >= 1                      # 864-um hop > 0.9 x 405
    # hops on the partition layers: 864 um > 0.9 x 405 -> ERROR, with the hop count needed
    e = errs(lambda p: p["die"]["layer_budget"].update(ft_route_layers=["M4", "M5"]), "reach")
    assert any("lane x" in m and "> 0.9 x reach 405" in m and "need 3 hop(s)" in m for m in e), e
    # a lane override can only lower the reach (half-cycle lanes)
    def half(p):
        next(l for l in p["lanes"] if l["id"] == "x")["reach_um"] = 500.0
    assert any("lane x" in m for m in errs(half, "reach"))
    # per-lane route layers
    def lane_m4(p):
        next(l for l in p["lanes"] if l["id"] == "x")["route_layers"] = ["M4"]
    assert any("lane x" in m and "M4" in m for m in errs(lane_m4, "reach"))
    # G0C gating: plain G0 only WARNs
    p = copy.deepcopy(EX)
    p["die"]["layer_budget"]["ft_route_layers"] = ["M4"]
    R, _ = check.run(p)
    assert not [i for i in R.errors() if i["check"] == "reach"]
    assert any(i["check"] == "reach" and i["msg"].startswith("[G0C]") for i in R.items)


def test_reach_die_constant_warns():
    R, _ = run(lambda p: p["die"].update(reach_um=1500.0))
    assert any(i["check"] == "reach" and "die.reach_um 1500" in i["msg"] and i["level"] == "WARN" for i in R.items)


# --------------------------------------------------------------------------------------------- (a) die IO
def serdes(p):
    p["partition_types"]["src"]["contents"][0]["module"] = "ot_qfd_serdes_112g_x12_phy"


def test_die_io_requires_windows_and_host(tmp_path):
    e = errs(serdes, "die_io_plan")
    assert any("serdes pa.u_core: no die.io window" in m for m in e), e
    # nothing planned at all
    assert any("no die IO planned" in m for m in errs(lambda p: p["die"].pop("io"), "die_io_plan"))
    # the catalog plan covers it; the 864 x 864 partition at the C4 150-um pitch has 25 sites < 4 x 12 + 2 = 50
    p = copy.deepcopy(EX)
    serdes(p)
    io = die_io.plan(schema.Plan(p))
    assert [(w["iface"], w["signals"], w["sites"], w.get("host")) for w in io] == [("serdes", 50, 25, None)]
    p["die"]["io"] = [w for w in p["die"]["io"] if not w.get("iface")] + io
    R, s = check.run(p, completeness=True)
    m = [i["msg"] for i in R.errors() if i["check"] == "die_io_plan"]
    assert any("50 off-die signals > 25 sites" in x for x in m) and not any("no die.io window" in x for x in m)
    assert s["die_io"]["plan"]["by_class"] == {"serdes": {"instances": 1, "signals": 50}}
    # host link required
    for w in p["die"]["io"]:
        w.pop("host", None)
    R, _ = check.run(p, completeness=True)
    assert any("no host link window" in i["msg"] for i in R.errors())


def test_die_io_shoreline_and_sidecar(tmp_path):
    p = copy.deepcopy(EX)
    serdes(p)
    # move the PHY to the die centre: pa <-> pm1 swap is not abutment-legal; shrink io_edge_max instead
    p["budgets"] = dict(p.get("budgets", {}), io_edge_max_um=1.0)
    p["partition_types"]["src"]["contents"][0].update(origin_um=[432.0, 432.0], outline_um=[216.0, 216.0])
    P = schema.Plan(p)
    io = die_io.plan(P)
    assert io[0]["rect_um"] == [432.0, 432.0, 648.0, 648.0]
    # sidecar: die.io absent from the plan -> PLANDIR/die_io.json
    keep = [w for w in p["die"]["io"] if not w.get("iface")]
    p["die"].pop("io")
    (tmp_path / "die_io.json").write_text(json.dumps(keep + io))
    R, s = check.run(p, plan_dir=tmp_path, completeness=True)
    assert s["die_io"]["source"].endswith("die_io.json") and s["die_io"]["windows"] == 3
    m = [i["msg"] for i in R.errors() if i["check"] == "die_io_plan"]
    assert any("216 um from the die edge > io_edge_max_um 1" in x for x in m), m


def test_die_io_host_bfs():
    p = copy.deepcopy(EX)
    p["partition_types"]["sink"]["contents"][0]["module"] = "ot_qkvd_ucie_x64_phy"
    p["partition_types"]["src"]["contents"].append(dict(inst="u_host", module="qkd_host_rt", status="new"))
    io = die_io.plan(schema.Plan(p))
    assert [(w["part"], w["iface"], w.get("host")) for w in io] == [("pb", "ucie", True)]
    assert "BFS 3 port hop(s) from pa" in io[0]["note"]


def test_die_io_in_band_host():
    """S81-XDIE 10-24: a die with no host link (S81 stage dies, RELEASE_RACK 2.1 S81.HOST) marks the link windows that
    carry the host traffic in-band host: "in_band"; the check accepts it only with a functional lane route to the
    host logic, and never mixed with a dedicated host window."""
    p = copy.deepcopy(EX)
    p["partition_types"]["sink"]["contents"][0]["module"] = "ot_qkvd_ucie_x64_phy"
    p["partition_types"]["src"]["contents"].append(dict(inst="u_host", module="qkd_host_rt", status="new"))
    io = die_io.plan(schema.Plan(p), in_band=["pb"])
    assert [(w["part"], w.get("host")) for w in io] == [("pb", "in_band")]
    assert io[0]["host_route"] == "pb -> [r] -> pa"                 # return lane r: pb -> pa (host logic)
    p["die"]["io"] = [{k: v for k, v in w.items() if k != "host"} for w in p["die"]["io"] if not w.get("iface")] + io
    assert not schema.validate(p)
    R, s = check.run(copy.deepcopy(p), completeness=True)
    assert not [i for i in R.errors() if i["check"] == "die_io_plan"], R.errors()
    assert s["die_io"]["plan"]["host_mode"] == "in_band"
    # a declared lane chain is checked (plan and G0C)
    io2 = die_io.plan(schema.Plan(p), in_band=[("pb", ["r"])])
    assert io2[0]["host_route"] == "pb -> [r] -> pa" and "declared" in io2[0]["note"]
    with pytest.raises(SystemExit):
        die_io.plan(schema.Plan(p), in_band=[("pb", ["x"])])           # lane x starts at pa, not pb
    b = copy.deepcopy(p)
    next(w for w in b["die"]["io"] if w.get("host") == "in_band")["host_route"] = "pb -> [x] -> pb"
    R, _ = check.run(b, completeness=True)
    assert any("lane x starts at pa, not pb" in i["msg"] for i in R.errors() if i["check"] == "die_io_plan")
    # no functional route from the in-band window to any host logic (here: no host logic at all) -> ERROR
    q = copy.deepcopy(p)
    q["partition_types"]["src"]["contents"].pop()
    R, _ = check.run(copy.deepcopy(q), completeness=True)                 # declared route no longer ends at host logic
    assert any("route ends at pa, not at host logic" in i["msg"] for i in R.errors() if i["check"] == "die_io_plan")
    for w in q["die"]["io"]:
        w.pop("host_route", None)
    R, _ = check.run(q, completeness=True)
    assert any("in-band host, but no lane route" in i["msg"] for i in R.errors() if i["check"] == "die_io_plan")
    # mixed dedicated + in-band -> ERROR; a bad host value -> schema ERROR
    m = copy.deepcopy(p)
    m["die"]["io"].append(dict(io[0], name="io_host2", host=True))
    R, _ = check.run(m, completeness=True)
    assert any("a die has either a host link or in-band host" in i["msg"] for i in R.errors())
    m["die"]["io"][-1]["host"] = "maybe"
    assert any("host" in e for e in schema.validate(m))
    with pytest.raises(SystemExit):
        die_io.plan(schema.Plan(p), in_band=["pm1"])                  # no serdes / ucie window there


# ---------------------------------------------------------------------------------------- (b) cut lines
def test_cut_lines_count_abutted_bits():
    R, s = run()
    v = {r["at_um"]: r for r in s["cut_lines"]["vertical"]}
    assert v[864.0]["abutted_bits"] == 65 + 17 + 9 and v[864.0]["route_bits"] == 0     # x0 + r2 + c0 (+ epoch)
    # the 250-um sweep never sees the abutted face crossing
    assert all(r["at_um"] != 864.0 for r in s["cuts"]["vertical"])
    e = errs(lambda p: p.setdefault("budgets", {}).update(cut_ratio_max=1e-5), "cut_lines")
    assert any("vertical face line 864: 91 bits (91 abutted + 0 ft/die routes)" in m for m in e), e


# ---------------------------------------------------------------------------------------- (d) face tracks
def test_tracks_count_matches_usable_tracks():
    rnd = random.Random(7)
    for ln, L in {L["name"]: L for L in schema.ASAP7_LAYERS}.items():
        T = xdie.Tracks(L, ln)
        for _ in range(200):
            lo = rnd.uniform(0, 300)
            hi = lo + rnd.uniform(0, 40)
            assert T.count(lo, hi) == schema.usable_tracks(L, ln, lo, hi), (ln, lo, hi)


def test_face_tracks_ratio():
    R, s = run()
    assert s["face_tracks"]["over"] == 0 and s["face_tracks"]["worst"][0]["allowed"] == ["M4", "M6"]
    # 300 M4 pins in 3 um of one face: the 10-um window has ~208 M4 + ~150 M6 usable tracks -> 0.83 (all) and 1.4 (M4)
    P = schema.Plan(copy.deepcopy(EX))
    R = check.Report(True)
    out = xdie.check_face_tracks(P, R, {("pa", "E"): [(400.0 + 0.01 * i, "M4", "x0") for i in range(300)]})
    m = [i["msg"] for i in R.errors()]
    assert out["over"] == 1 and any("type src face E" in x and "(M4)" in x and "> 0.6" in x for x in m), m
    # an M8 third layer on the face adds its tracks to the allowed set
    p = copy.deepcopy(EX)
    for tn in ("src", "mid"):
        p["partition_types"][tn]["face_layers"] = {"E": ["M6", "M4", "M8"], "W": ["M6", "M4", "M8"]}
    P = schema.Plan(p)
    assert xdie.face_allowed_layers(P, "pa", "E") == ["M4", "M6", "M8"]


# ----------------------------------------------------------------------------------------- (e) ft budget
def test_ft_budget():
    R, s = run()
    mid = next(r for r in s["ft_budget"]["worst"] if r["type"] == "mid")
    assert mid["H"]["ft_bits"] == 64 + 16 and mid["V"]["ft_bits"] == 0 and s["ft_budget"]["over"] == 0
    assert mid["H"]["reserved"] == int(xdie.Tracks(schema.ASAP7_LAYERS[6], "M8").count(0, 864.0) * 0.6)
    e = errs(lambda p: p["partition_types"]["mid"].update(ft_budget={"M8": 0.001}), "ft_budget")
    assert any("type mid: 80 over-the-top M8 tracks needed (80 ft bits + 0 M8 face pins)" in m for m in e), e


def test_g0c_summary_counts():
    R, s = run(lambda p: p["die"]["layer_budget"].update(ft_route_layers=["M4"]))
    assert s["xdie_counts"]["reach"] >= 1 and s["g0c"]["clean"] < s["g0c"]["types"]
