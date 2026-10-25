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


def _one_station(p):
    """the pre-9.4 tiny geometry (1 station per mid slot, x = 4 cycles, r = 5): latency-only tests (R8 groups, landed,
    fold) keep their small numbers; G0 hops / stations FAIL on it since ruling 9.3/9.4 (405 um)."""
    p = copy.deepcopy(p)
    for s in p["partition_types"]["mid"]["ft_slots"]:
        s["stations"] = 1
    p["latency"]["lanes"] = gen.latency_table(schema.Plan(p))
    return p


EX1 = _one_station(EX)


def g0(mut=None):
    p = copy.deepcopy(EX)
    if mut:
        mut(p)
    R, summ = check.run(p, completeness=True)
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
    # reset: the example plans are reset.release "counted" -> one WARN (OWNER RESET RULE 10-24, reset_tree.py)
    assert R.errors() == [] and [i["check"] for i in R.items] == ["types", "reset", "census"], R.items  # census: none
    R2, _ = check.run(json.loads((HERE / "examples" / "tiny_plan_typegeo.json").read_text()))
    assert [i["check"] for i in R2.items] == ["reset", "census"], R2.items
    assert summ["geometry"]["fill"] == 1.0
    assert summ["latency"]["x"] == 8           # 3 stations per mid slot (R3 <= 405 um, ruling 9.4)


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
    e = errs(lambda p: p["die"].update(reach_um=250.0), "hops")
    assert any("lane x" in x and "> reach 250" in x for x in e)
    # four stations in the mid slot shorten the hop (216 um) -> pass at reach 250 once the latency table is regenerated
    def four(p):
        p["die"]["reach_um"] = 250.0
        for s in p["partition_types"]["mid"]["ft_slots"]:
            s["stations"] = 4
        p["latency"]["lanes"] = gen.latency_table(schema.Plan(p))
    assert errs(four) == []


def test_signal_reach_405_and_station_ceiling():
    """ruling 9.3/9.4 (2026-10-24): die.reach_um is capped at the 405-um M4-M7 signal reach (WARN), ft stations
    <= 405 um apart, a plan ft_station_max_um above 405 is an ERROR."""
    def one(p):
        p.clear()
        p.update(copy.deepcopy(EX1))
        p["die"]["reach_um"] = 1500.0
    R, _ = g0(one)
    e = [i["msg"] for i in R.errors()]
    assert any("lane x" in x and "> reach 405" in x for x in e)
    assert any("ft_station_max_um 405" in x for x in e)
    assert any(i["check"] == "hops" and "die.reach_um 1500" in i["msg"] and i["level"] == "WARN" for i in R.items)
    e = errs(lambda p: p["budgets"].update(ft_station_max_um=750), "stations")
    assert any("ft_station_max_um 750 > 405" in x for x in e)


def test_m89_signals():
    """ruling 9.3: M8/M9 carry only the die clock spine, reset and PG; any planned signal on them is a G0 ERROR."""
    assert errs(None, "m89_signals") == []
    assert any("ft_reserved" in x for x in
               errs(lambda p: p["die"]["layer_budget"]["die_use"].append("ft_reserved"), "m89_signals"))
    assert any("lane x: route_layers" in x for x in
               errs(lambda p: p["lanes"][1].update(route_layers=["M8", "M9"]), "m89_signals"))
    assert any("port c0" in x for x in errs(lambda p: port(p, "c0").update(layers=["M8"]), "m89_signals"))
    assert any("face_layers" in x for x in errs(lambda p: p["partition_types"]["mid"].update(
        face_layers=dict(E=["M4", "M6", "M8"])), "m89_signals"))
    assert any("ft_budget" in x for x in errs(lambda p: p["partition_types"]["mid"].update(
        ft_budget=dict(M8=0.6)), "m89_signals"))
    assert any("partition_signal_max M8" in x for x in errs(lambda p: p["die"]["layer_budget"].update(
        partition_signal_max="M8"), "m89_signals"))


def test_latency_checks():
    assert any("missing from the latency table" in x for x in errs(lambda p: p["latency"]["lanes"].pop("x")))
    assert any("plan gives 9" in x for x in errs(lambda p: p["latency"]["lanes"]["r"].update(cycles=3)))
    assert any("no latency table" in x for x in errs(lambda p: p.pop("latency")))


def test_cut_overflow():
    def m(p):
        p["die"]["layer_budget"]["cut_avail"] = {"M8": 0.0, "M9": 0.0}
        for t in p["partition_types"].values():
            t["ft_track_frac"] = 0.0001
    e = errs(m, "cuts")
    assert any("vertical cut" in x for x in e)


def test_clock_reset_leaf():
    assert any("no clock method" in x for x in errs(lambda p: p["partition_types"]["mid"].pop("clock")))
    assert any("no reset" in x for x in errs(lambda p: p["partition_types"]["mid"].pop("reset")))
    assert any("unknown instance" in x for x in
               errs(lambda p: p["partition_types"]["mid"]["buses"][0].update(leaf="u_x.cfg_i")))


def test_gen_latency_and_render():
    with tempfile.TemporaryDirectory() as d:
        p = copy.deepcopy(EX)
        p.pop("latency")
        tab, sv, js = gen.write_latency(p, d)
        assert "localparam int LAT_X = 8;" in sv.read_text()
        assert json.loads(js.read_text())["lanes"]["r"]["cycles"] == 9
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


def _census_case(d, rows, mp):
    p = copy.deepcopy(EX)
    (Path(d) / "c.json").write_text(json.dumps({"groups": rows}))
    (Path(d) / "m.json").write_text(json.dumps(mp))
    p["census"] = [{"rows": "c.json", "map": "m.json"}]
    R, summ = check.run(p, plan_dir=d)
    return [i["msg"] for i in R.errors() if i["check"] == "census"], summ["census"]


def test_census_coverage():
    """COORD 10-23 06:45: every as-built inter-partition bit carried by the plan; unmapped = ERROR; exempt listed."""
    import tempfile
    MAP = {"parts": {"u_a": "pa", "u_b": "pb", "u_m1": "pm1"}, "rules": [["^u_m2", "pm2"]], "collapse": ["^ld_"],
           "exempt": [{"match": "^rst", "kind": "reset", "replaced_by": "spine + per-partition sync",
                       "reason": "reset spine"}]}

    def row(s, sb, d_, db, bits, kind="data"):
        return dict(src=s, src_bus=sb, dst=d_, dst_bus=db, bits=bits, kind=kind)
    with tempfile.TemporaryDirectory() as d:
        ok = [row("u_a", "x", "ld_0", "i", 64), row("ld_0", "o", "u_b", "x", 64),     # a landing cell in the middle
              row("u_b", "r", "u_a", "r", 16), row("u_a", "cfg", "u_m1", "cfg", 8), row("u_m1", "cfg", "u_m2x", "c", 8),
              row("u_a", "rst_q", "u_b", "rst_n", 1, "reset"), row("u_a", "loc", "u_a", "loc", 999)]
        e, s = _census_case(d, ok, MAP)
        assert e == [] and s["dropped_bits"] == 0, e
        assert s["sources"][0]["exempt"] == {"reset:^rst": 1} and s["sources"][0]["intra_bits"] == 999
        e, s = _census_case(d, ok + [row("u_a", "y", "u_b", "y", 100)], MAP)            # a bus the plan lacks
        assert s["dropped_bits"] == 100 and any("pa -> pb" in m for m in e), e
        e, _ = _census_case(d, ok + [row("u_zz", "q", "u_b", "y", 3)], MAP)              # unmapped -> ERROR
        assert any("u_zz" in m and "maps to no partition" in m for m in e), e
        mp2 = dict(MAP, exempt=[])
        e, s = _census_case(d, ok, mp2)                                                   # reset not exempted
        assert s["dropped_bits"] == 1, e
    R, _ = g0(lambda p: p.pop("census"))
    assert any(i["check"] == "census" for i in R.errors())                                # mandatory


def test_census_forwarded_and_broadcast():
    import tempfile

    def row(s, sb, d_, db, bits):
        return dict(src=s, src_bus=sb, dst=d_, dst_bus=db, bits=bits, kind="data")
    MAP = {"parts": {"u_a": "pa", "u_b": "pb", "u_m1": "pm1", "u_m2": "pm2"}}
    with tempfile.TemporaryDirectory() as d:
        # pa -> pm2 directly in the census; the plan only has pa->pm1 (cfg 8) and pm1->pm2 (cfg 8)
        rows = [row("u_a", "c", "u_m2", "c", 8)]
        e, s = _census_case(d, rows, MAP)
        assert s["dropped_bits"] == 8
        e, s = _census_case(d, rows, dict(MAP, forward_via=["pm1"]))
        assert s["dropped_bits"] == 0 and s["sources"][0]["forwarded_bits"] == 8, e
        e, s = _census_case(d, [row("u_a", "c", "u_m2", "c", 9)], dict(MAP, forward_via=["pm1"]))
        assert s["dropped_bits"] == 1                                    # bottleneck 8
        # broadcast: one 64-bit driver bus to two sink buses in pb: 128 counted unless collapse_broadcast
        bc = [row("u_a", "x", "u_b", "x0", 64), row("u_a", "x", "u_b", "x1", 64)]
        e, s = _census_case(d, bc, MAP)
        assert s["dropped_bits"] == 64
        e, s = _census_case(d, bc, dict(MAP, collapse_broadcast=True))
        assert s["dropped_bits"] == 0 and s["sources"][0]["broadcast_collapsed_bits"] == 64


def test_census_taptree_bit_audit():
    """R5 (COORD 10-23): forward_via credit needs a bit-level tap-tree audit; a split bus on a shared trunk fails."""
    import tempfile
    P = schema.Plan(EX)
    tree = [lid for lid, ln in P.lanes.items()
            if (P.ports[ln["ports"][0]]["src"]["part"], P.ports[ln["ports"][-1]]["dst"]["part"]) in
            (("pa", "pm1"), ("pm1", "pm2"))]
    assert len(tree) == 2
    w = min(int(P.ports[P.lanes[tree[0]]["ports"][0]]["width"]), 8)
    MAP = {"parts": {"u_a": "pa", "u_b": "pb", "u_m1": "pm1", "u_m2": "pm2"}, "forward_via": ["pm1"],
           "tree_lanes": {"u_a.c": tree}}
    rows = [dict(src="u_a", src_bus="c", dst="u_m2", dst_bus="c", bits=w, kind="data")]

    def case(d, pairs):
        p = copy.deepcopy(EX)
        (Path(d) / "c.json").write_text(json.dumps({"groups": rows}))
        (Path(d) / "m.json").write_text(json.dumps(MAP))
        src = {"rows": "c.json", "map": "m.json"}
        if pairs is not None:
            (Path(d) / "b.json").write_text(json.dumps({"conns": pairs}))
            src["bitcon"] = "b.json"
        p["census"] = [src]
        R, summ = check.run(p, plan_dir=d)
        return [i["msg"] for i in R.errors() if i["check"] == "census"], summ["census"]
    with tempfile.TemporaryDirectory() as d:
        e, s = case(d, None)                                       # tree credit without bit pairs
        assert any("without a bit-level tap-tree audit" in m for m in e), e
        bcast = [dict(s="u_a", sp="c", d="u_m2", dp="c", pairs=[[i, i] for i in range(w)]),
                 dict(s="u_a", sp="c", d="u_m1", dp="c", pairs=[[i, i] for i in range(w)])]
        e, s = case(d, bcast)                                       # broadcast: same bits everywhere -> PASS
        assert e == [] and s["sources"][0]["taptree"]["under_carrying_lanes"] == 0, e
        split = [dict(s="u_a", sp="c", d="u_m2", dp="c", pairs=[[i, i] for i in range(w)]),
                 dict(s="u_a", sp="c", d="u_m1", dp="c", pairs=[[w + i, i] for i in range(w)])]
        e, s = case(d, split)                                       # split bus: the pa->pm1 trunk needs 2w
        assert any("deficit" in m for m in e) and s["sources"][0]["taptree"]["deficit_bits"] == w, e


def test_face_layers_m8_and_spare_slots():
    def m8(p, fl=True):
        port(p, "x0")["layers"] = ["M8", "M4"]
        if fl:
            p["partition_types"]["src"]["face_layers"] = {"E": ["M8", "M6", "M4"]}
            p["partition_types"]["mid"]["face_layers"] = {"W": ["M8", "M6", "M4"], "E": ["M6", "M4"]}
    assert any("above partition_signal_max" in m for m in errs(lambda p: m8(p, False), "layers"))
    assert errs(m8, "layers") == []
    assert any("not in pa's face_layers" in m for m in errs(
        lambda p: p["partition_types"]["src"].__setitem__("face_layers", {"E": ["M4"]}), "layers"))

    def spare(lo, hi):
        return lambda p: p["partition_types"]["src"].__setitem__(
            "spare_slots", [dict(name="sp0", face="E", window_um=[lo, hi], layers=["M6"])])
    assert any("spare slot sp0" in m for m in errs(spare(400, 420), "abutment"))
    assert errs(spare(700, 720), "abutment") == []
    assert any("outside face" in m for m in errs(spare(860, 900), "abutment"))


def test_hard_core_track_offset_and_taps():
    def core(off, o="R0"):
        def m(p):
            p["partition_types"]["src"]["hard_cores"] = [dict(
                inst="u_core", origin_um=[8.64, 8.64], outline_um=[21.6, 21.6], orient=o, track_offset_um=off,
                pins=[dict(name="a[0]", layer="M4", xy=[1.0, 0.012]), dict(name="b", layer="M5", xy=[0.012, 21.6])])]
        return m
    e = errs(core([0, 0]), "hard_cores")
    assert any("pin a[0] M4" in m for m in e) and any("pin b M5" in m for m in e)
    assert errs(core([0.012, 0.012]), "hard_cores") == []
    assert any("pin a[0] M4" in m for m in errs(core([0.012, 0.012], "MX"), "hard_cores"))   # MX flips the phase
    assert errs(core([0.012, -0.012], "MX"), "hard_cores") == []
    tap = lambda xy: lambda p: p["partition_types"]["src"].setdefault("clock", {}).__setitem__(  # noqa: E731
        "taps", [dict(name="u_core.ck", kind="core", xy=xy, insertion_ps=250)])
    assert errs(tap([10.0, 10.0]), "clock") == []
    assert any("outside the outline" in m for m in errs(tap([10.0, 9000.0]), "clock"))

def test_census_explicit_control_routes_fail_closed(tmp_path):
    """A one-bit control can add beside data only with its complete source-bound named route."""
    from types import SimpleNamespace
    import census_cov

    def run(mutate=None, forwarders=("pm",), extra_controls=0, data_bits=8):
        ports = {
            "data": dict(src=dict(part="pa", bus="o_pa_data"), dst=dict(part="pb", bus="i_pa_data"), width=8),
            "c0": dict(src=dict(part="pa", bus="o_pa_c"), dst=dict(part="pm", bus="i_pa_c"), width=1),
            "c1": dict(src=dict(part="pm", bus="o_pa_c_d1"), dst=dict(part="pb", bus="i_pa_c"), width=1)}
        P = SimpleNamespace(raw=dict(census=[dict(rows="rows.json", map="map.json")]), types={},
                            parts={n: {"type": "t"} for n in ("pa", "pm", "pb", "wrong")},
                            ports=ports, lanes={p: dict(ports=[p]) for p in ports})
        rows = [dict(src="pa", src_bus=bus, dst="pb", dst_bus=bus, bits=w, kind="data")
                for bus, w in (("data", data_bits), ("c", 1))]
        route = dict(src="pa", src_bus="c", dst="pb", dst_bus="c", lanes=["c0", "c1"])
        mp = dict(parts={n: n for n in P.parts}, forward_via=list(forwarders), forward_routes=[route])
        for i in range(extra_controls):
            rows.append(dict(src="pa", src_bus="c", dst="pb", dst_bus=f"c_again{i}", bits=1, kind="data"))
            mp["forward_routes"].append(dict(route, dst_bus=f"c_again{i}"))
        if mutate:
            mutate(P, mp)
        (tmp_path / "rows.json").write_text(json.dumps(rows))
        (tmp_path / "map.json").write_text(json.dumps(mp))
        R = check.Report()
        summary = census_cov.coverage(P, tmp_path, R)
        return summary, R

    summary, R = run()
    assert summary["dropped_bits"] == 0 and not R.errors()
    for lid in ("c0", "c1"):
        _, R = run(lambda p, m: p.lanes.pop(lid))
        assert R.errors(), lid
    mutations = [
        lambda p, m: m["forward_routes"][0].update(lanes=["c0"]),
        lambda p, m: m["forward_routes"][0].update(src_bus="absent"),
        lambda p, m: p.ports["c1"]["dst"].update(part="wrong"),
        lambda p, m: p.ports["c1"]["src"].update(bus="o_other_c"),
        lambda p, m: p.ports["c1"].update(width=2),
        lambda p, m: m["forward_routes"].append(dict(m["forward_routes"][0])),
        lambda p, m: m["forward_routes"].__setitem__(0, "malformed")]
    for mutate in mutations:
        _, R = run(mutate)
        assert R.errors()
    _, R = run(forwarders=())
    assert R.errors()
    summary, R = run(lambda p, m: m.pop("forward_routes"))
    assert summary["dropped_bits"] == 1 and R.errors()  # the generic single-path rule stays unchanged

    # Two distinct census rows may refer to the same physical control. Their witnesses cannot reserve the
    # same lane capacity twice, even though their exact row keys differ.
    _, R = run(extra_controls=1)
    assert any("reuse planned lane capacity" in e["msg"] for e in R.errors())

    def direct_cycle(p, m):
        p.ports["direct"] = dict(src=dict(part="pa", bus="o_pa_c"),
                                 dst=dict(part="pb", bus="i_pa_c"), width=1)
        p.ports["back"] = dict(src=dict(part="pb", bus="o_pa_c"),
                               dst=dict(part="pm", bus="i_pa_c"), width=1)
        for lid in ("direct", "back"):
            p.lanes[lid] = dict(ports=[lid])
        m["forward_routes"][0]["lanes"] = ["direct", "back", "c1"]
    summary, R = run(direct_cycle, forwarders=("pm", "pb"), data_bits=9)
    assert summary["dropped_bits"] == 1 and R.errors()  # direct control must not count again as data capacity

    _, R = run(lambda p, m: m.update(groups={"g": ["pa", "pm"]}), forwarders=("g",))
    assert any("witness capacity exceeds planned lanes" in e["msg"] for e in R.errors())


def test_zroute_turn_is_L():
    """COORD 10-23: a turning slot (perpendicular faces) routes as an L, a straight slot with a jog as a Z."""
    assert check.zroute((0, 10), (50, 100), "W", "N") == [(0, 10), (50, 10), (50, 100)]
    assert check.zroute((10, 0), (100, 50), "S", "E") == [(10, 0), (10, 50), (100, 50)]
    assert check.zroute((0, 10), (100, 30), "W", "E") == [(0, 10), (50.0, 10), (50.0, 30), (100, 30)]


def test_die_io_windows():
    """COORD 10-23 (S81-P5): off-die ports need a pad / bump window over their host partition with enough sites."""
    assert errs(lambda p: None, "die_io") == []
    assert any("no pad / bump window" in m for m in errs(lambda p: p["die"]["io"].pop(), "die_io"))
    assert any("> 20 sites" in m for m in errs(lambda p: p["die"]["io"][0].__setitem__("sites", 20), "die_io"))
    assert any("not inside its host" in m for m in errs(
        lambda p: p["die"]["io"][0].__setitem__("rect_um", [900, 8.64, 950, 50]), "die_io"))
    assert any("not the host" in m for m in errs(lambda p: p["die"]["io"][0].__setitem__("ports", ["dout"]), "die_io"))


def test_latency_groups_pad_to_slowest():
    """R8 (COORD 10-23, QC xt1 0/64): the lanes of one as-built bus arrive in one cycle; pads are realised as type
    stages at the destination in bus; unequal table cycles in a group or per-type pad conflicts fail G0."""
    import gen_rtl
    p = copy.deepcopy(EX1)
    p["latency_groups"] = [dict(name="xbus", kind="bus", lanes=["x", "cfg23"], source="BINDER2 test")]
    P = schema.Plan(p)
    assert P.lane_latency("cfg23")["cycles"] == 4 and P.lane_latency("cfg23")["pad"] == 2
    assert P.bus_pads() == ({("sink", "cfg_i"): 2}, [])
    p["latency"]["lanes"] = gen.latency_table(P)
    R, _ = g0(lambda q: q.update(copy.deepcopy(p)))
    assert [i["msg"] for i in R.errors() if i["check"] == "latency"] == []
    stale = copy.deepcopy(p)
    stale["latency"]["lanes"]["cfg23"]["cycles"] = 2
    R, _ = g0(lambda q: q.update(copy.deepcopy(stale)))
    assert any("unequal delays" in i["msg"] for i in R.errors())
    rtl = gen_rtl.wrapper(schema.Plan(p), "sink", gen_rtl.bus_epochs(schema.Plan(p)))
    assert "u_bin_cfg_i_pad0" in rtl and "u_bin_cfg_i_pad1" in rtl and "u_bin_cfg_i_pad2" not in rtl
    # pads are a TYPE property: pm1 and pm2 (both 'mid') would need different cfg_i pads
    c = copy.deepcopy(EX1)
    c["latency_groups"] = [dict(name="bad", lanes=["x", "cfg12"])]
    assert schema.Plan(c).bus_pads()[1]


def test_landed_group_one_depth_and_window():
    """COORD rule 10-23 (S81-P9-R8EQ): a latency group of kind `landed` (one forwarded-clock landing ring, one K)
    arrives at ONE group depth; its natural lane spread must stay under the landing window margin (window - 1)."""
    p = copy.deepcopy(EX1)
    p["latency_groups"] = [dict(name="xl", kind="landed", window=4, lanes=["x", "cfg23"])]
    P = schema.Plan(p)
    assert P.lane_latency("cfg23")["cycles"] == P.lane_latency("x")["cycles"] == 4 and not P.landed_skew()
    p["latency"]["lanes"] = gen.latency_table(P)
    R, _ = g0(lambda q: q.update(copy.deepcopy(p)))
    assert [i["msg"] for i in R.errors() if i["check"] == "latency"] == []
    p["latency_groups"][0]["window"] = 2                       # spread 2 > margin 1
    assert schema.Plan(p).landed_skew()
    R, _ = g0(lambda q: q.update(copy.deepcopy(p)))
    assert any("landing window margin" in i["msg"] for i in R.errors())
    import pytest
    with pytest.raises(SystemExit):
        gen.write_latency(p, "/tmp/_landed_test_lat")


def test_core_ks_rules(monkeypatch):
    """COORD 10-23 CORE-KS: (a) a type over 400k cells needs hard_cores[], a core without pins is an ERROR;
    (b) M2/M3 core pins are not checked in a mirrored instance's die frame (platform cell-access tracks)."""
    def core(o, pins):
        def m(p):
            p["partitions"][0]["orient"] = o
            p["partition_types"]["src"]["hard_cores"] = [dict(
                inst="u_core", origin_um=[8.64, 8.64], outline_um=[21.6, 21.6], track_offset_um=[0.012, 0.012],
                pins=pins)]
        return m
    m3 = [dict(name="m3p", layer="M3", xy=[0.033, 5.0])]
    assert errs(core("R0", m3), "hard_cores") == []
    assert errs(core("MY", m3), "hard_cores") == []
    monkeypatch.setattr(check, "MIRROR_SKIP", ())
    assert any("pin m3p M3" in m for m in errs(core("MY", m3), "hard_cores"))
    monkeypatch.undo()
    assert any("no pins listed" in m for m in errs(core("R0", []), "hard_cores"))
    big = lambda n: lambda p: p["partition_types"]["src"].__setitem__("cells", n)  # noqa: E731
    assert any("no hard_cores" in m for m in errs(big(450_000), "hard_cores"))
    assert errs(big(350_000), "hard_cores") == []
    assert errs(lambda p: (big(450_000)(p), core("R0", m3)(p)), "hard_cores") == []


def test_cells_estimator(tmp_path):
    """PLAN-TOOL4 (COORD 10-23): types without type.cells get a cell estimate from evidence files (by type, by
    partition = max over instances, per_type rep -> partition, module table / Yosys stat), and the 400k hard-core
    rule bites on it."""
    import cells
    p = copy.deepcopy(EX)
    for t in p["partition_types"].values():
        t.pop("cells", None)
    (tmp_path / "bt.json").write_text(json.dumps({"cells_per_type": {"src": {"cells": 500_000}}}))
    (tmp_path / "bp.json").write_text(json.dumps({"pm1": {"cells": 10}, "pm2": {"cells": 30}}))
    (tmp_path / "rep.json").write_text(json.dumps({"per_type": {"old_sink": {"rep": "pb", "flat_k": 2.5}}}))
    est, used = cells.estimate(p, None, [tmp_path / "bt.json", tmp_path / "bp.json", tmp_path / "rep.json"])
    assert est["src"] == (500_000, "by_type bt.json") and est["mid"][0] == 30 and est["sink"][0] == 2500
    assert [r[0] for r in cells.over_cap(p, est)] == ["src"]
    stat = ("=== tiny_src_core ===\n   Number of wires: 3\n   Number of cells:  4321\n"
            "=== other ===\n   Number of cells: 7\n")
    (tmp_path / "y.stat").write_text(stat)
    assert cells.parse_stat(stat) == {"tiny_src_core": 4321, "other": 7}
    est, _ = cells.estimate(p, None, [tmp_path / "y.stat"])
    assert est["src"] == (4321, "modules 1/1")
    R, summ = check.run(p, evidence=[tmp_path / "bt.json"], completeness=True)
    e = [i["msg"] for i in R.errors() if i["check"] == "hard_cores"]
    assert len(e) == 1 and "500000 cells (by_type bt.json)" in e[0] and summ["taps_cores"]["over_cap_no_cores"] == 1
    # auto-discovery in the plan directory
    (tmp_path / "plan_notes.json").write_text(json.dumps({"cells_per_type": {"mid": {"cells": 900_000}}}))
    R, _ = check.run(p, plan_dir=tmp_path, completeness=True)
    assert any("type mid: 900000 cells" in i["msg"] for i in R.errors())


def _face_core(pin_faces, orient="R0", conns=None):
    """src type gets hard core u_core (box 216..648, centre 432,432) with one pin per port on the given core face;
    tiny_plan: src bus din (leaf u_core.din) enters on W (y 100-120), x_o (leaf u_core.x) leaves on E (y 400-420)."""
    pos = dict(W=(0.0, 200.0), E=(432.0, 200.0), S=(200.0, 0.0), N=(200.0, 432.0))

    def m(p):
        t = p["partition_types"]["src"]
        t["hard_cores"] = [dict(inst="u_core", origin_um=[216.0, 216.0], outline_um=[432.0, 432.0], orient=orient,
                                pins=[dict(name=f"{port}[0]", layer="M4", xy=list(pos[f]))
                                      for port, f in pin_faces.items()])]
        if conns:
            conns(t)
    return m


def test_core_face_rule():
    """PLAN-TOOL4 (COORD 10-23, GEOM face rule): a hard-core port must sit on a core face that faces its partner."""
    ok = errs(_face_core(dict(din="W", x="E")), "core_faces")
    assert ok == []
    e = errs(_face_core(dict(din="E", x="E")), "core_faces")
    assert len(e) == 1 and "port din" in e[0] and "re-pin to face W" in e[0]
    e = errs(_face_core(dict(din="W", x="W")), "core_faces")
    assert len(e) == 1 and "port x" in e[0] and "re-pin to face E" in e[0]
    # the core orient is applied: MY swaps the E/W pins, so the R0-correct pins now face away
    assert len(errs(_face_core(dict(din="W", x="E"), "MY"), "core_faces")) == 2
    assert errs(_face_core(dict(din="E", x="W"), "MY"), "core_faces") == []
    # perpendicular (N face for a W partner well below the core centre): cos ~ -0.1..0 -> WARN, not ERROR
    R, summ = g0(_face_core(dict(din="W", x="N")))
    assert [i for i in R.errors() if i["check"] == "core_faces"] == []
    assert summ["core_faces"]["groups"] == 2


def test_core_face_rule_internal_station():
    """QC-P6-G0C 10-23: a bus with R3-INTERNAL stations reaches the core from its last station (regs_um[-1]), so
    the face rule scores the pins against that register, not the face window."""
    def st(t):
        t["internal_stations"] = [dict(conn="bus:din", from_um=[0.0, 110.0], to_um=[648.0, 432.0],
                                       regs_um=[[324.0, 100.0], [700.0, 432.0]])]
    # din pins on the core E face, window on W: away from the window, but the last station sits E of the core
    assert len(errs(_face_core(dict(din="E", x="E")), "core_faces")) == 1
    assert errs(_face_core(dict(din="E", x="E"), conns=st), "core_faces") == []
    assert len(errs(_face_core(dict(din="W", x="E"), conns=st), "core_faces")) == 1


def test_core_face_rule_core_to_core(tmp_path):
    """leaf-to-leaf nets (contents bind net:) and the core_conns.json sidecar name core-to-core partners."""
    def two(t, via_sidecar=False):
        t["hard_cores"].append(dict(inst="u_b", origin_um=[8.64, 8.64], outline_um=[100.0, 100.0],
                                    pins=[dict(name="y", layer="M4", xy=[100.0, 50.0])]))
        if not via_sidecar:
            t["contents"][0]["bind"]["q"] = "net:n_qy"
            t["contents"].append(dict(inst="u_b", module="tiny_b", status="new", bind={"y": "net:n_qy"}))
    # u_core port q on its E face; the partner u_b sits SW of u_core -> faces away; u_b's y (E face) faces u_core
    m = _face_core(dict(din="W", x="E", q="E"), conns=two)
    e = errs(m, "core_faces")
    assert len(e) == 1 and "core u_core port q" in e[0] and "u_b (net n_qy)" in e[0]
    assert errs(_face_core(dict(din="W", x="E", q="S"), conns=two), "core_faces") == []
    p = copy.deepcopy(EX)
    _face_core(dict(din="W", x="E", q="E"), conns=lambda t: two(t, True))(p)
    (tmp_path / "core_conns.json").write_text(json.dumps({"src": {"u_core": {"q": ["core:u_b"]}}}))
    R, summ = check.run(p, plan_dir=tmp_path, completeness=True)
    e = [i["msg"] for i in R.errors() if i["check"] == "core_faces"]
    assert len(e) == 1 and "port q" in e[0]
    assert summ["core_faces"]["cores_unchecked"] == 1      # u_b: no connectivity named for it


def test_plan_completeness():
    """PLAN COMPLETENESS (COORD 10-23): a missing field is an ERROR, counted per field in summary.complete."""
    def fields(mut):
        R, summ = g0(mut)
        return sorted({i["field"] for i in R.errors() if i["check"] == "complete"}), summ["complete"]
    assert fields(None)[0] == []
    f, miss = fields(lambda p: p["clock"].pop("common_latency_ps"))
    assert f == ["common_latency"] and miss["common_latency"] == 1
    assert fields(lambda p: p["partition_types"]["mid"]["clock"].__setitem__("insertion_ps", 300))[0] == \
        ["insertion_target"]
    assert fields(lambda p: p["partition_types"]["mid"].pop("reset"))[0] == ["reset_sync"]
    assert fields(lambda p: p["partition_types"]["mid"].pop("cells", None) or
                  p["partition_types"]["mid"].__setitem__("contents", [dict(inst="u", module="m", status="new")]))[0] \
        == ["cells"]

    def core(off=True, st=None):
        def m(p):
            t = p["partition_types"]["src"]
            hc = dict(inst="u_core", origin_um=[803.52, 803.52], outline_um=[51.84, 51.84],
                      pins=[dict(name="din[0]", layer="M4", xy=[0.0, 1.0])])
            if off:
                hc["track_offset_um"] = [0.0, 0.0]
            t["hard_cores"] = [hc]
            if st is not None:
                t["internal_stations"] = st
        return m
    # src bus din enters on W at y 100-120; the core sits at the NE corner: >= 1384 um internal -> stations needed
    f, _ = fields(core())
    assert f == ["internal_station"]
    assert "track_offset" in fields(core(off=False))[0]
    good = [dict(conn="bus:din", from_um=[0.0, 110.0], to_um=[803.52, 803.52],      # hops <= 405 (R3, 9.4)
                 regs_um=[[400.0, 110.0], [650.0, 260.0], [803.52, 410.0]])]
    assert fields(core(st=good))[0] == []
    far = [dict(conn="bus:din", from_um=[0.0, 110.0], to_um=[803.52, 803.52], regs_um=[[700.0, 500.0]])]
    assert fields(core(st=far))[0] == ["internal_station"]          # first hop 1090 um
    # face_flop: a bus with no planned port / pin geometry is already a schema ERROR (no face-flop site)
    extra = lambda p: p["partition_types"]["src"]["buses"].append(dict(name="zz_o", dir="out", width=4))  # noqa
    assert any("unbound" in m for m in errs(extra, "schema"))


def test_g0c_gated():
    """COORD 10-23: completeness / hard-core findings are ERRORs only with --completeness (G0C); plain G0 WARNs."""
    def m(p):
        p["clock"].pop("common_latency_ps")
        p["partition_types"]["mid"]["cells"] = 450_000
    p = copy.deepcopy(EX)
    m(p)
    R, summ = check.run(p)
    assert R.errors() == [] and any(i["msg"].startswith("[G0C]") for i in R.items)
    R, summ = check.run(copy.deepcopy(p), completeness=True)
    assert {i["check"] for i in R.errors()} == {"hard_cores", "complete"}
    g = summ["g0c"]
    assert g["by_type"] == {"mid": {"hard_cores": 1}} and g["die_level"] == {"complete:common_latency": 1}
    assert g["g3_eligible"] == [] and g["clean"] == 2


def test_core_face_broadcast_station_capture_scope():
    """A later broadcast leg to another core must not replace this core's final relay."""
    def stations(t):
        t['internal_stations'] = [
            dict(conn='bus:din', capture='u_core.din', from_um=[0,110], to_um=[648,432], regs_um=[[700,432]]),
            dict(conn='bus:din', capture='u_other.din', from_um=[0,110], to_um=[100,432], regs_um=[[100,432]])]
    assert errs(_face_core(dict(din='E', x='E'), conns=stations), 'core_faces') == []
    assert len(errs(_face_core(dict(din='W', x='E'), conns=stations), 'core_faces')) == 1


def test_gen_latency_fold_r8():
    """COORD 10-24 18:55: gen.py latency --fold-r8 prices the R8 landing pads per lane (cycles = base + r8_pad, largest
    member pad of the lane); --rebase-bind moves the bind's bound depths onto this plan; --inplace keeps the base."""
    def m(port, bits, asb, bound, lane):
        return dict(sink_port=port, sink_bits=bits, source="u_a.o", source_bits=bits, asbuilt_stages=asb,
                    bound_stages=bound, landed_stages=bound, lane=lane)
    bg = dict(die="tiny", replica=[], landing=[dict(sink="u_b", sink_part="pb", src_part="pa", members=[
        m("xi", [[0, 7]], 0, 4, "x"), m("ri", [[0, 3]], 0, 5, "r"), m("q", [[0, 0]], 0, 2, "UNPLANNED")])])
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        plan = d / "plan.json"
        plan.write_text(json.dumps(EX1))
        (d / "bg.json").write_text(json.dumps(bg))
        (d / "bl.json").write_text(json.dumps(dict(buses=[dict(lane="x", plan_cycles=2), dict(lane="r", plan_cycles=5)])))
        assert gen.main(["latency", str(plan), "--out", str(d / "a"), "--groups", str(d / "bg.json"), "--fold-r8"]) == 0
        js = json.loads((d / "a" / "tiny_latency.json").read_text())
        x, r = js["lanes"]["x"], js["lanes"]["r"]
        assert (x["base"], x["r8_pad"], x["cycles"]) == (4, 1, 5) and (r["base"], r["r8_pad"], r["cycles"]) == (5, 0, 5)
        assert "localparam int LAT_X = 5;" in (d / "a" / "tiny_lat_pkg.sv").read_text()
        assert js["r8"]["fold"]["lanes_padded"] == 1 and js["r8"]["fold"]["not_plan_lanes"] == {"UNPLANNED": 3}
        # rebase: the bind had x at 2 cycles, this plan has 4 -> x bound 6, offset 6 > r 5: r is padded now, x not
        assert gen.main(["latency", str(plan), "--out", str(d / "b"), "--groups", str(d / "bg.json"), "--fold-r8",
                         "--rebase-bind", str(d / "bl.json"), "--inplace"]) == 0
        js = json.loads((d / "b" / "tiny_latency.json").read_text())
        assert js["lanes"]["x"]["cycles"] == 4 and js["lanes"]["r"]["r8_pad"] == 1 and js["lanes"]["r"]["cycles"] == 6
        assert js["r8"]["rebase"]["moved"] == 1
        inpl = json.loads(plan.read_text())["latency"]["lanes"]
        assert inpl["r"]["cycles"] == 5 and "r8_pad" not in inpl["r"]       # in-plan table stays base (binder, G0)


def test_two_beat_lane():
    """DEC12: a lane carrying word_bits in `beats` beats: port = ceil(word / beats) + beat-index bits, latency
    word_cycles = cycles + beats - 1, census credit = word_bits."""
    def mut(word):
        def m(p):
            ln = next(x for x in p["lanes"] if x["id"] == "din")
            ln.update(beats=2, word_bits=word)
            p["latency"]["lanes"] = gen.latency_table(schema.Plan(p))
        return m
    assert not errs(mut(62), "latency")                      # 32 = 31 + 1 beat bit
    p = copy.deepcopy(EX)
    mut(62)(p)
    d = p["latency"]["lanes"]["din"]
    assert d["beats"] == 2 and d["word_cycles"] == d["cycles"] + 1
    assert any("need port width 33" in e for e in errs(mut(64), "latency"))
