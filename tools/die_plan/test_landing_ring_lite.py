"""RING-LITE-1 (KV-RING2-LIGHT 11-18): type key clock.landing_ring_lite gives the narrow count-aligned rings of one
(source partition, K) group the data-path-only ring form (ot_dp_clk_landing_cas LITE) under the group's full monitor ring.
Opt-in: without the key the generated RTL is byte-identical; with it only the ring parameter changes (pins, K, strap
ties and lane cycles are untouched)."""
import re
import pytest
import count_align_bind as CAB
from clock_landings import Landings, LandingError, ring_lite_cfg
from test_clock_landings import A_BODY, B_BODY
from test_count_straps import strap_vehicle, cs, pin
from test_param_wrap_hard_ring import _hard

N = 5


def lite_vehicle(k_last=None):
    """strap_vehicle (a -> b, a -> c, tree bus y) + N one-bit buses x<i> -> y<i> on both copies of type B; on each copy
    all N share one K (b: 3, c: 5), except the last bus when k_last is given (its own group of one)."""
    p, t = strap_vehicle()
    ta, tb = p["partition_types"]["A"], p["partition_types"]["B"]
    ca = t["count_aligned"]
    for i in range(N):
        ta["buses"] += [pin(f"fclk_out_x{i}", "out"), pin(f"cland_fstart_out_x{i}", "out")]
        tb["buses"] += [pin(f"y{i}", "in"), pin(f"fclk_in_y{i}", "in"), pin(f"cland_fstart_in_y{i}", "in"),
                        pin(f"landing_ready_y{i}", "out"), pin(f"landing_fault_y{i}", "out")]
        tb["count_straps"].append(cs(f"strap_ca_k_y{i}", 6))
        for inst, reg, k in (("b", "r1", 3), ("c", "r2", 5)):
            pid = f"N{inst}{i}"
            p["ports"].append(dict(id=pid, width=1, kind="data", src=dict(part="a", bus=f"x{i}"), dst=dict(part=inst, bus=f"y{i}")))
            t["ports"].append(dict(port=pid, width=1, src="a", dst=inst, src_region="r0", dst_region=reg, lane=f"L{pid}"))
            ca["ports"][pid] = dict(K=k_last if (k_last is not None and i == N - 1 and inst == "c") else k, depth=4, sched_lat=3, tree=False)
    return p, t


def bodies():
    xs = "".join(f" output wire [1:0] x{i},\n" for i in range(N))
    ys = "".join(f" input wire [1:0] y{i},\n" for i in range(N))
    a = A_BODY.replace(" output wire [4:0] x\n", xs + " output wire [4:0] x\n").replace(
        " assign x = 0;", " assign x = 0;" + "".join(f" assign x{i} = 0;" for i in range(N)))
    b = B_BODY.replace(" input wire [4:0] y // whole bundle\n", ys + " input wire [4:0] y // whole bundle\n").replace(
        " assign y_q = y;", " assign y_q = y;" + "".join(f" wire [1:0] y{i}_q; assign y{i}_q = y{i};" for i in range(N)))
    return a, b


def set_key(plan, value):
    plan["partition_types"]["B"].setdefault("clock", {})["landing_ring_lite"] = value


def rings(rtl):
    return {m.group(2): m.group(1) for m in re.finditer(r"(ot_dp_clk_landing_cas #\([^;]*?\)) u_cland_(\w+) \(", rtl)}


def test_absent_key_is_byte_identical_and_all_rings_full():
    p, t = lite_vehicle()
    a, b = bodies()
    base = Landings(p, t).type_rtl("B", b)
    assert "LITE" not in base and len(rings(base)) == N + 1
    assert ring_lite_cfg(p["partition_types"]["B"], "B") is None


def test_one_monitor_per_group_rest_lite_and_only_the_parameter_changes():
    p, t = lite_vehicle()
    a, b = bodies()
    base = Landings(p, t).type_rtl("B", b)
    ties = CAB.strap_ties(t["count_aligned"], p)
    set_key(p, {})
    land = Landings(p, t)
    got = land.type_rtl("B", b)
    r = rings(got)
    lite = sorted(n for n, m in r.items() if ".LITE(1)" in m)
    assert lite == ["y0", "y1", "y3", "y4"]                 # y2 = the middle of the group keeps the monitor
    assert ".LITE(1)" not in r["y"]                          # the 5-bit start-tree ring is never lite
    assert got.replace(", .LITE(1)", "") == base             # pins, connections, K straps: unchanged text
    assert CAB.strap_ties(t["count_aligned"], p) == ties
    rp = land.reset_placements["B"]
    assert rp["y0"]["ring_lite"] is True and rp["y0"]["ring_lite_added_cycles"] == 0 and rp["y0"]["ring_lite_monitors"] == ["y2"]
    assert rp["y2"]["ring_lite_monitor_of"] == N and "ring_lite" not in rp["y2"] and "ring_lite" not in rp["y"]
    assert land.manifest()["lane_added_cycles"] == Landings(*lite_vehicle()).manifest()["lane_added_cycles"]
    assert "LITE" not in land.type_rtl("A", a)


def test_monitors_count_and_width_limit():
    p, t = lite_vehicle()
    a, b = bodies()
    set_key(p, {"monitors": 2})
    r = rings(Landings(p, t).type_rtl("B", b))
    assert sorted(n for n, m in r.items() if ".LITE(1)" in m) == ["y0", "y2", "y4"]   # monitors y1, y3
    set_key(p, {"monitors": 9})
    assert "LITE" not in Landings(p, t).type_rtl("B", b)                              # every ring keeps its monitor
    set_key(p, {"max_width": 1})
    assert "LITE" not in Landings(p, t).type_rtl("B", b)                              # the rings are 2 bits wide


def test_group_needs_same_source_and_k_on_every_instance():
    p, t = lite_vehicle(k_last=7)          # y4 has another K on copy c only: its own group of one, stays full
    a, b = bodies()
    set_key(p, {})
    r = rings(Landings(p, t).type_rtl("B", b))
    assert sorted(n for n, m in r.items() if ".LITE(1)" in m) == ["y0", "y1", "y3"]
    assert ".LITE(1)" not in r["y4"] and ".LITE(1)" not in r["y2"]


def test_signed_hard_child_is_not_reparameterised_and_not_counted():
    p, t = lite_vehicle()
    a, b = bodies()
    base = rings(Landings(p, t).type_rtl("B", b))["y2"]
    m = re.match(r"(\w+) #\((.*)\)$", base)
    params = {k: int(v) for k, v in re.findall(r"\.(\w+)\((\d+)\)", m.group(2))}
    hc = _hard(p, m.group(1), params, master="b_cland_y2")
    hc[-1].update(inst="cl_y2", physical_inst="u_bound.u_cland_y2")
    set_key(p, {})
    r = rings(Landings(p, t).type_rtl("B", b))
    assert ".LITE(1)" not in r["y2"]                                                   # signed child untouched
    assert sorted(n for n, x in r.items() if ".LITE(1)" in x) == ["y0", "y1", "y4"]    # y3 = middle of the 4 soft rings


@pytest.mark.parametrize("value", [True, 1, [], {"max_width": 0}, {"max_width": 65}, {"monitors": 0}, {"monitors": True},
                                   {"width": 4}])
def test_invalid_key_is_rejected(value):
    p, t = lite_vehicle()
    a, b = bodies()
    set_key(p, value)
    with pytest.raises(LandingError, match="landing_ring_lite"):
        Landings(p, t).type_rtl("B", b)


def test_schema_accepts_the_key():
    import schema
    props = schema.SCHEMA["properties"]["partition_types"]["additionalProperties"]["properties"]["clock"]["properties"]
    assert props["landing_ring_lite"]["properties"].keys() == {"max_width", "monitors", "status_copy"}


def test_status_copy_type_needs_the_opt_in_and_lite_rings_take_no_status_bank():
    """RING-LITE-2 (FABLE-KV-DIE 11-22): a landing_control_status_copy type gets lite rings only with
    landing_ring_lite.status_copy; the lite rings are built without CONTROL_STATUS_COPY, the monitor keeps it."""
    p, t = lite_vehicle()
    a, b = bodies()
    p["partition_types"]["B"]["landing_control_status_copy"] = True
    base = Landings(p, t).type_rtl("B", b)
    assert "LITE" not in base and base.count(".CONTROL_STATUS_COPY(1)") == N + 1
    set_key(p, {})                                            # RING-LITE-1 reading: key inert on a status-copy type
    assert Landings(p, t).type_rtl("B", b) == base
    set_key(p, {"status_copy": False})
    assert Landings(p, t).type_rtl("B", b) == base
    set_key(p, {"status_copy": True})
    land = Landings(p, t)
    got = land.type_rtl("B", b)
    r = rings(got)
    lite = sorted(n for n, m in r.items() if ".LITE(1)" in m)
    assert lite == ["y0", "y1", "y3", "y4"]
    assert all(".CONTROL_STATUS_COPY(1)" not in r[n] for n in lite)            # the RTL refuses LITE with a status bank
    assert ".CONTROL_STATUS_COPY(1)" in r["y2"] and ".CONTROL_STATUS_COPY(1)" in r["y"] and ".LITE(1)" not in r["y2"]
    strip = lambda x: re.sub(r", \.(LITE|CONTROL_STATUS_COPY)\(1\)", "", x)
    assert strip(got) == strip(base)                                           # only ring parameters differ
    rp = land.reset_placements["B"]
    assert rp["y0"]["ring_lite"] is True and "control_status_copy" not in rp["y0"]
    assert rp["y2"]["control_status_copy"] is True and rp["y2"]["ring_lite_monitor_of"] == N
    assert land.manifest()["lane_added_cycles"] == Landings(*lite_vehicle()).manifest()["lane_added_cycles"]


def test_status_copy_flag_must_be_boolean():
    p, t = lite_vehicle()
    a, b = bodies()
    set_key(p, {"status_copy": 1})
    with pytest.raises(LandingError, match="landing_ring_lite"):
        Landings(p, t).type_rtl("B", b)
