"""UNIFY-TOOLS pad_hoist: per-instance receiver pads of a merged class move into ft slot stations on the lane path."""
import json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pad_hoist as PH  # noqa: E402


def _plan():
    """two slices: src_i -> ft_i -> ctl_i on bus d_i; ft_a is shared by slices 0/1 (type fa), ft_b own type (fb)"""
    types = {"ctl": dict(ft_slots=[]), "src": dict(ft_slots=[]),
             "fa": dict(ft_slots=[dict(name="d_ctl", stations=2), dict(name="o_x", stations=1)]),
             "fb": dict(ft_slots=[dict(name="d_ctl", stations=2)])}
    parts = [dict(name=n, type=t) for n, t in (("ctl0", "ctl"), ("ctl1", "ctl"), ("ctl2", "ctl"), ("s0", "src"),
                                                ("s1", "src"), ("s2", "src"), ("f0", "fa"), ("f1", "fa"), ("f2", "fb"))]
    ports, lanes = [], []
    for i in range(3):
        ports += [dict(id=f"L{i}__0", src=dict(part=f"s{i}", bus="d_o"), dst=dict(part=f"f{i}", bus="d_ctl_i")),
                  dict(id=f"L{i}__1", src=dict(part=f"f{i}", bus="d_ctl_o"), dst=dict(part=f"ctl{i}", bus="d_i"))]
        lanes.append(dict(id=f"L{i}", ports=[f"L{i}__0", f"L{i}__1"]))
    return dict(partition_types=types, partitions=parts, ports=ports, lanes=lanes)


def test_module_pads_parse():
    sv = ("module m (\n    input  wire [8:0] d_i,   // 8 data + epoch [8]: lane L0, 9 cycles\n"
          "    input  wire [3:0] e_i,   // lane L9\n);\n"
          "    ot_dp_dly #(.W(9), .D(4)) u_lpad_d_i (.clk(clk), .d(x), .q(y));\n")
    assert PH.module_pads(sv) == {"d_i": 4, "e_i": 0}


def test_own_type_slot_takes_the_difference():
    plan = _plan()
    hoists, lanes, unplaced = PH.solve(plan, {"ctl": {"ctl0": {"d_i": 2}, "ctl1": {"d_i": 2}, "ctl2": {"d_i": 7}}})
    assert hoists == {("fb", "d_ctl"): 5} and unplaced == []
    assert lanes["L2"]["hoisted"] == 5 and lanes["L2"]["target"] == 2


def test_shared_type_slot_needs_every_instance():
    plan = _plan()
    # slices 0 and 1 share ft type fa: only one of them needs pad -> the fa slot cannot take it
    hoists, lanes, unplaced = PH.solve(plan, {"ctl": {"ctl0": {"d_i": 5}, "ctl1": {"d_i": 2}, "ctl2": {"d_i": 2}}})
    assert hoists == {} and unplaced[0]["lane"] == "L0" and unplaced[0]["left"] == 3 and not unplaced[0]["below"]
    # both need the same 3 -> one raise of the shared type
    hoists, _, unplaced = PH.solve(plan, {"ctl": {"ctl0": {"d_i": 5}, "ctl1": {"d_i": 5}, "ctl2": {"d_i": 2}}})
    assert hoists == {("fa", "d_ctl"): 3} and unplaced == []


def test_main_writes_raised_stations(tmp_path):
    plan = _plan()
    bd = tmp_path / "bind"
    (bd / "rtl").mkdir(parents=True)
    (bd / "bind_report.json").write_text(json.dumps(dict(type_splits=[dict(type="ctl", variants=[["ctl0", "ctl1"],
                                                                                                    ["ctl2"]])])))
    mk = lambda d: f"module x (\n    input  wire [8:0] d_i,   // lane\n);\n    ot_dp_dly #(.W(9), .D({d})) u_lpad_d_i (\n"
    (bd / "rtl" / "ctl.sv").write_text(mk(1))
    (bd / "rtl" / "ctl_v1.sv").write_text(mk(4))
    pp, op = tmp_path / "p.json", tmp_path / "o.json"
    pp.write_text(json.dumps(plan))
    assert PH.main([str(pp), str(bd), str(op), "--report", str(tmp_path / "r.json")]) == 0
    out = json.loads(op.read_text())
    s = out["partition_types"]["fb"]["ft_slots"][0]
    assert s["stations"] == 5 and "pad_hoist" in s["note"]
    assert out["partition_types"]["fa"] == plan["partition_types"]["fa"]


def test_unplaced_refuses_without_partial(tmp_path):
    plan = _plan()
    bd = tmp_path / "bind"
    (bd / "rtl").mkdir(parents=True)
    (bd / "bind_report.json").write_text(json.dumps(dict(type_splits=[dict(type="ctl", variants=[["ctl1", "ctl2"],
                                                                                                    ["ctl0"]])])))
    mk = lambda d: f"module x (\n    input  wire [8:0] d_i,   // lane\n);\n    ot_dp_dly #(.W(9), .D({d})) u_lpad_d_i (\n"
    (bd / "rtl" / "ctl.sv").write_text(mk(1))
    (bd / "rtl" / "ctl_v1.sv").write_text(mk(4))
    pp, op = tmp_path / "p.json", tmp_path / "o.json"
    pp.write_text(json.dumps(plan))
    assert PH.main([str(pp), str(bd), str(op)]) == 3 and not op.exists()


def test_target_lowers_when_the_shared_slot_blocks():
    plan = _plan()
    # ctl0 at 3, ctl1 at 2 share fa; ctl2 (own fb) at 2.  At target 2 only ctl0 needs the shared fa slot: blocked.
    # At target 1 ctl0 needs 2, ctl1 1, ctl2 1 -> fa +1 (both), fb +1, ctl0 still 1: blocked.  At 0: 3 / 2 / 2 ->
    # fa +2, fb +2, ctl0 1 left: never placed -> back to the class minimum, nothing hoisted for that bus.
    hoists, lanes, unplaced = PH.solve(plan, {"ctl": {"ctl0": {"d_i": 3}, "ctl1": {"d_i": 2}, "ctl2": {"d_i": 2}}})
    assert hoists == {} and unplaced[0]["target"] == 2
    # ctl0 and ctl1 need the same: the shared fa slot takes it at the class minimum
    hoists, lanes, unplaced = PH.solve(plan, {"ctl": {"ctl0": {"d_i": 2}, "ctl1": {"d_i": 2}, "ctl2": {"d_i": 1}}})
    assert unplaced == [] and hoists == {("fa", "d_ctl"): 1} and lanes["L0"]["target"] == 1


def test_apply_keeps_latency_table_in_step():
    plan = _plan()
    row = lambda: dict(cycles=12, boundary=2, stations=4, fixed=2, clock_landing=0, natural=8, pad=4)
    plan["latency"] = dict(lanes={f"L{i}": row() for i in range(3)})
    plan["lanes"][2]["fixed_cycles"] = 2
    PH.apply(plan, {("fb", "d_ctl"): 3})
    assert plan["latency"]["lanes"]["L2"] == dict(row(), stations=7, natural=11, pad=1)
    assert plan["latency"]["lanes"]["L0"] == row()
    # 2 more than the table pad: the member's fixed cycles the merged type lacks are cut, cycles stay
    assert PH.apply(plan, {("fb", "d_ctl"): 2}) == [dict(lane="L2", table_pad=1, hoisted=2, fixed_cut=1)]
    assert plan["latency"]["lanes"]["L2"] == dict(row(), stations=9, fixed=1, natural=12, pad=0)
    assert plan["lanes"][2]["fixed_cycles"] == 2      # raw lane fixed_cycles stay: they price kit stations


def test_raise_cycles_levels_up_the_lower_instances(tmp_path):
    plan = _plan()
    plan["latency"] = dict(lanes={f"L{i}": dict(cycles=12, stations=4, natural=8, pad=4) for i in range(3)})
    bd = tmp_path / "bind"
    (bd / "rtl").mkdir(parents=True)
    (bd / "bind_report.json").write_text(json.dumps(dict(type_splits=[dict(type="ctl", variants=[["ctl1", "ctl2"],
                                                                                                    ["ctl0"]])])))
    mk = lambda d: f"module x (\n    input  wire [8:0] d_i,   // lane\n);\n    ot_dp_dly #(.W(9), .D({d})) u_lpad_d_i (\n"
    (bd / "rtl" / "ctl.sv").write_text(mk(1))
    (bd / "rtl" / "ctl_v1.sv").write_text(mk(4))
    pp, op, rp = tmp_path / "p.json", tmp_path / "o.json", tmp_path / "r.json"
    pp.write_text(json.dumps(plan))
    assert PH.main([str(pp), str(bd), str(op), "--raise-cycles", "--report", str(rp)]) == 0
    lat = json.loads(op.read_text())["latency"]["lanes"]
    assert lat["L0"]["cycles"] == 12 and lat["L1"]["cycles"] == 15 and lat["L2"]["cycles"] == 15
    assert json.loads(rp.read_text())["raised_cycles"] == [dict(type="ctl", bus="d_i", lane="L1", add=3),
                                                           dict(type="ctl", bus="d_i", lane="L2", add=3)]


def test_in_station_floor_raises_the_instances_below_it():
    plan = _plan()
    plan["latency"] = dict(lanes={f"L{i}": dict(cycles=12, stations=4, natural=8, pad=4) for i in range(3)})
    plan["partition_types"]["ctl"]["internal_stations"] = [dict(conn="bus:d_i", regs_um=[[1, 1], [2, 2]])]
    hoists, lanes, unplaced = PH.solve(plan, {"ctl": {"ctl0": {"d_i": 2}, "ctl1": {"d_i": 2}, "ctl2": {"d_i": 1}}})
    assert hoists == {} and [(u["lane"], u["below"], u["target"]) for u in unplaced] == [("L2", True, 2)]
    assert PH.raise_cycles(plan, {"ctl": {"ctl0": {"d_i": 2}, "ctl1": {"d_i": 2}, "ctl2": {"d_i": 1}}}, unplaced) == \
        [dict(type="ctl", bus="d_i", lane="L2", add=1)]
