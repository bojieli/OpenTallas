"""UNIFY-TOOLS class_merge: a class of types becomes ONE type; monitor children tieable and re-indexed by site."""
import copy, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import class_merge as CM  # noqa: E402
import landing_tie_children as LTC  # noqa: E402


def _child(i, xy):
    return dict(index=i, xy_um=list(xy), seam=True, node=f"n{i}", part=None,
                ready=f"cland_dn_ready_{i}", fault=f"cland_dn_fault_{i}")


def _pins(children):
    out = [dict(name="cland_up_ready", dir="out", kind="ctl", layer="M5", xy_um=[600.0, 0.0]),
           dict(name="d_in", dir="in", kind="data", layer="M5", xy_um=[0.024, 300.0])]
    for i, (x, y) in children:
        out += [dict(name=f"cland_dn_ready_{i}", dir="in", kind="ctl", layer="M5", xy_um=[x, y]),
                dict(name=f"cland_dn_fault_{i}", dir="in", kind="ctl", layer="M5", xy_um=[x, y + 0.48]),
                dict(name=f"fclk_in_cland_dn_{i}", dir="in", kind="clk", layer="M5", xy_um=[x, y + 0.96])]
    return out


def _type(name, children, pad=None):
    t = dict(module=name, outline_um=[1226.88, 1339.2], buses=[dict(name="d_in", width=8)], ft_slots=[],
             hard_cores=[dict(name=f"core_{name}")],
             clock=dict(landing_contract=dict(pins=_pins(children),
                                              collector_children=[_child(i, xy) for i, xy in children])))
    if pad is not None:
        t["r8_strap_pad_max"] = pad
    return t


A, B, C = (8.16, 502.176), (153.376, 1330.592), (460.064, 1330.592)


def _plan():
    types = {"ctl__rep": _type("ctl__rep", [(0, A), (1, B), (2, C)]),
             "ctl__m1": _type("ctl__m1", [(0, C)], pad=31),           # its child 0 is the rep's child 2
             "ctl__m2": _type("ctl__m2", []),
             "other": _type("other", [])}
    parts = [dict(name="p0", type="ctl__rep"), dict(name="p1", type="ctl__m1"), dict(name="p2", type="ctl__m2"),
             dict(name="kid", type="other")]
    edges = [dict(id=f"cland_mon_{k}__kid", src=dict(part="kid", bus="cland_up_ready"),
                  dst=dict(part="p1", bus=f"{pin}_0"))
             for k, pin in (("ready", "cland_dn_ready"), ("fault", "cland_dn_fault"), ("clk", "fclk_in_cland_dn"))]
    plan = dict(partition_types=types, partitions=parts, clock=dict(
        landing_network=dict(edges=edges),
        tap_window=dict(per_type_ps={"ctl__rep": 90, "ctl__m1": 60, "ctl__m2": 70, "other": 10})),
        reset=dict(in_sites={k: [1.0, 2.0] for k in types}))
    side = dict(count_aligned=dict(parts={p: dict(role="origin") for p in ("p0", "p1", "p2")}),
                collector=dict(parts={p["name"]: dict(type=p["type"]) for p in parts},
                               types={k: dict(base_type=k) for k in types},
                               edges=[dict(src="kid", dst="p1", dst_index=0)],
                               boot_budget=dict(local_registered_depths={"p0": 10, "p1": 9, "p2": 10})))
    return plan, side


def test_merge_one_type_reindexed_tieable():
    plan, side = _plan()
    rep = CM.merge(plan, side, "ctl__rep", ["ctl__rep", "ctl__m1", "ctl__m2"])
    assert rep["refused"] == []
    assert {p["type"] for p in plan["partitions"] if p["name"] != "kid"} == {"ctl__rep"}
    assert set(plan["partition_types"]) == {"ctl__rep", "other"}
    lc = plan["partition_types"]["ctl__rep"]["clock"]["landing_contract"]
    assert lc["tieable_children"] == [dict(index=i, seam=True) for i in range(3)]
    names = {p["name"] for p in lc["pins"]}
    assert {"strap_cland_use_0", "strap_cland_use_1", "strap_cland_use_2"} <= names
    # p1's only child (site C) is the representative's child 2
    assert {e["dst"]["bus"] for e in plan["clock"]["landing_network"]["edges"]} == \
        {"cland_dn_ready_2", "cland_dn_fault_2", "fclk_in_cland_dn_2"}
    assert side["collector"]["edges"][0]["dst_index"] == 2
    assert plan["partition_types"]["ctl__rep"]["r8_strap_pad_max"] == 31
    assert set(plan["clock"]["tap_window"]["per_type_ps"]) == {"ctl__rep", "other"}
    assert set(plan["reset"]["in_sites"]) == {"ctl__rep", "other"}
    assert set(side["collector"]["types"]) == {"ctl__rep", "other"}
    assert side["collector"]["boot_budget"]["local_registered_depths"]["p1"] == 10
    # per-instance use straps come from the real edges: p1 uses child 2 only, p0 none, p2 none
    use = LTC.instance_use(plan)
    assert use["p1"] == {"strap_cland_use_0": (1, 0), "strap_cland_use_1": (1, 0), "strap_cland_use_2": (1, 1)}
    assert use["p2"] == {f"strap_cland_use_{i}": (1, 0) for i in range(3)}


def test_refuses_child_site_not_on_representative():
    plan, side = _plan()
    plan["partition_types"]["ctl__m2"] = _type("ctl__m2", [(0, (1217.76, 1171.808))])
    before = copy.deepcopy(plan)
    rep = CM.merge(plan, side, "ctl__rep", ["ctl__m1", "ctl__m2"])
    assert any("not a representative child site" in r for r in rep["refused"])
    assert plan == before


def test_refuses_outline_and_role_difference():
    plan, side = _plan()
    plan["partition_types"]["ctl__m2"]["outline_um"] = [1226.88, 1400.0]
    side["count_aligned"]["parts"]["p2"]["role"] = "relay"
    rep = CM.merge(plan, side, "ctl__rep", ["ctl__m1", "ctl__m2"])
    assert any("outline_um differs" in r for r in rep["refused"])
    assert any("landing role differs" in r for r in rep["refused"])


def test_types_outside_the_class_unchanged(tmp_path):
    plan, side = _plan()
    other = json.dumps(plan["partition_types"]["other"], sort_keys=True)
    pp, sp = tmp_path / "p.json", tmp_path / "s.json"
    pp.write_text(json.dumps(plan)); sp.write_text(json.dumps(side))
    rc = CM.main([str(pp), str(sp), str(tmp_path / "op.json"), str(tmp_path / "os.json"), "--rep", "ctl__rep",
                  "--stem", "ctl", "--report", str(tmp_path / "r.json")])
    assert rc == 0
    out = json.loads((tmp_path / "op.json").read_text())
    assert json.dumps(out["partition_types"]["other"], sort_keys=True) == other
    assert json.loads((tmp_path / "r.json").read_text())["instances"] == 3


def test_role_strap_union_of_start_pins_and_straps():
    plan, side = _plan()
    side["count_aligned"]["parts"]["p2"]["role"] = "relay"
    rx = dict(name="cland_rstart_in", dir="in", kind="ctl", layer="M5", xy_um=[700.0, 0.0])
    plan["partition_types"]["ctl__m2"]["clock"]["landing_contract"]["pins"].append(rx)
    plan["partition_types"]["ctl__rep"]["count_straps"] = [dict(name="strap_ca_pad", width=2),
                                                           dict(name="strap_ca_efall", width=1)]
    plan["partition_types"]["ctl__m1"]["count_straps"] = [dict(name="strap_ca_pad", width=3)]
    assert CM.merge(copy.deepcopy(plan), copy.deepcopy(side), "ctl__rep", ["ctl__m1", "ctl__m2"])["refused"]
    rep = CM.merge(plan, side, "ctl__rep", ["ctl__m1", "ctl__m2"], role_strap=True)
    assert rep["refused"] == [] and rep["role_strap"]["pins_added"] == ["cland_rstart_in"]
    t = plan["partition_types"]["ctl__rep"]
    assert t["landing_role_strap"] is True
    assert {c["name"]: c["width"] for c in t["count_straps"]} == {"strap_ca_pad": 3, "strap_ca_efall": 1,
                                                                  "strap_ca_relay": 1}
    assert rx in t["clock"]["landing_contract"]["pins"]


def test_role_strap_moves_a_colliding_start_pin_to_a_free_track():
    plan, side = _plan()
    side["count_aligned"]["parts"]["p2"]["role"] = "relay"
    taken = dict(name="cland_rstart_in", dir="in", kind="ctl", layer="M5", xy_um=[0.024, 300.0])   # d_in's site
    plan["partition_types"]["ctl__m2"]["clock"]["landing_contract"]["pins"].append(taken)
    rep = CM.merge(plan, side, "ctl__rep", ["ctl__m1", "ctl__m2"], role_strap=True)
    assert rep["refused"] == []
    old, new = rep["role_pins_moved"]["cland_rstart_in"]
    assert old == [0.024, 300.0] and new[1] == 300.0 and new[0] >= 1.0      # M5 is vertical: moved in x, on a track
    assert abs(round((new[0] - 0.024) / 0.048) * 0.048 + 0.024 - new[0]) < 1e-6


def test_role_strap_refuses_unknown_layer_collision():
    plan, side = _plan()
    side["count_aligned"]["parts"]["p2"]["role"] = "relay"
    plan["partition_types"]["ctl__rep"]["clock"]["landing_contract"]["pins"][1]["layer"] = "MX"
    taken = dict(name="cland_rstart_in", dir="in", kind="ctl", layer="MX", xy_um=[0.024, 300.0])
    plan["partition_types"]["ctl__m2"]["clock"]["landing_contract"]["pins"].append(taken)
    rep = CM.merge(plan, side, "ctl__rep", ["ctl__m1", "ctl__m2"], role_strap=True)
    assert any("no free site" in r for r in rep["refused"])
