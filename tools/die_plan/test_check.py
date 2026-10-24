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
    assert R.errors() == [] and [i["check"] for i in R.items] == ["types", "census"], R.items   # census: none
    R2, _ = check.run(json.loads((HERE / "examples" / "tiny_plan_typegeo.json").read_text()))
    assert [i["check"] for i in R2.items] == ["census"], R2.items
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
    p = copy.deepcopy(EX)
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
    c = copy.deepcopy(EX)
    c["latency_groups"] = [dict(name="bad", lanes=["x", "cfg12"])]
    assert schema.Plan(c).bus_pads()[1]


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
