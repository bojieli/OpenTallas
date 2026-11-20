import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import landing_tie_children as LTC  # noqa: E402
import straps as STR  # noqa: E402

TIE = [{"index": 0, "seam": True}, {"index": 1, "seam": False}]


def test_ports_and_connections():
    assert LTC.tie_ports(TIE) == {"cland_dn_ready_0": "1'b1", "cland_dn_fault_0": "1'b0", "fclk_in_cland_dn_0": "1'b0",
                                  "cland_dn_ready_1": "1'b1", "cland_dn_fault_1": "1'b0"}
    assert LTC.tie_connections(TIE, {0, 1}) == []
    c = LTC.tie_connections(TIE, {0})
    assert c == ["        .cland_dn_ready_1(1'b1)", "        .cland_dn_fault_1(1'b0)"]
    assert len(LTC.tie_connections(TIE, set())) == 5


def test_validate_names_missing_pins():
    pins = [{"name": "cland_dn_ready_0", "dir": "in"}, {"name": "cland_dn_fault_0", "dir": "in"}]
    assert LTC.validate([{"index": 0, "seam": False}], pins) == []
    assert LTC.validate([{"index": 0, "seam": True}], pins) == ["fclk_in_cland_dn_0"]


def test_landing_ties_from_types():
    t = {"a": {"clock": {"landing_contract": {"tieable_children": TIE}}}, "b": {"clock": {}}}
    assert set(LTC.landing_ties(t)) == {"a"}


def test_audit_accepts_only_declared_ties():
    top = "bt_a u_x (\n  .cland_dn_ready_1(1'b1),\n  .cland_dn_fault_1(1'b0)\n);\n"
    lt = LTC.landing_ties({"a": {"clock": {"landing_contract": {"tieable_children": TIE}}}})
    man = {"types": {}, "instances": {}}
    ok = STR.audit_top_ties(top, man, {"bt_a": "a"}, landing_ties=lt)
    assert ok["verdict"] == "PASS" and len(ok["rows"]) == 2
    assert STR.audit_top_ties(top, man, {"bt_a": "a"})["verdict"] == "FAIL"            # undeclared: still rejected
    wrong = top.replace("cland_dn_ready_1(1'b1)", "cland_dn_ready_1(1'b0)")
    assert STR.audit_top_ties(wrong, man, {"bt_a": "a"}, landing_ties=lt)["verdict"] == "FAIL"   # wrong value
    other = top.replace(".cland_dn_fault_1", ".some_other_pin")
    assert STR.audit_top_ties(other, man, {"bt_a": "a"}, landing_ties=lt)["verdict"] == "FAIL"


class _P:
    """minimal Plan stand-in for landing_contract.check: one partition, no landing edges at all"""
    def __init__(self, tieable):
        pins = [dict(name=n, dir=d, kind=k, layer="M7", xy_um=[5.0, 5.0 + i], epoch=False)
                for i, (n, d, k) in enumerate([("cland_dn_ready_0", "in", "ctl"), ("cland_dn_fault_0", "in", "ctl"),
                                               ("cland_up_ready", "out", "ctl"), ("cland_up_fault", "out", "ctl")])]
        lc = dict(pins=pins, **({"tieable_children": tieable} if tieable else {}))
        self.types = {"T": {"outline_um": [100, 100], "clock": {"landing_contract": lc, "edge_clocks": []}}}
        self.parts = {"a": {"type": "T"}}
        self.layers = {"M7": 7}
        self.clock = {"landing_network": {"edges": [], "root_observer": {"part": "a", "module": "m", "fault_port": "f", "ready_port": "r"}}}


def test_check_unused_tied_landing_pins_are_no_error():
    import landing_contract as LCO
    res = LCO.check(_P([{"index": 0, "seam": False}]))
    assert not [e for e in res["errors"] if "used 0 times" in e], res["errors"]


def test_check_without_declaration_keeps_the_strict_rule():
    import landing_contract as LCO
    errs = [e for e in LCO.check(_P(None))["errors"] if "used 0 times" in e]
    assert len(errs) == 4        # 2 dn inputs + 2 up outputs, all unused, nothing declared


def test_seam_use_only_masks_optional_children():
    assert LTC.seam_use_ports(TIE) == {0: "strap_cland_use_0"}
    assert LTC.use_connections(TIE, {0}) == ["        .strap_cland_use_0(1'b1)"]
    assert LTC.use_connections(TIE, {1}) == ["        .strap_cland_use_0(1'b0)"]
    ready = "word[0] && trained && !guard"
    fault = "word[1] || guard"
    assert LTC.qualified_status(ready, fault, None) == (ready, fault)
    assert LTC.qualified_status(ready, fault, "use") == (
        "(!use || (word[0] && trained && !guard))", "(use && (word[1] || guard))")


def test_monitor_use_literally_matches_the_real_parent_edges():
    pin_names = ("cland_dn_ready_0", "cland_dn_fault_0", "fclk_in_cland_dn_0")
    plan = {
        "partition_types": {"T": {"clock": {"landing_contract": {"tieable_children": TIE}}}},
        "partitions": [{"name": part, "type": "T"} for part in ("present", "spare")],
        "clock": {"landing_network": {"edges": [
            {"dst": {"part": "present", "bus": pin}} for pin in pin_names]}}}
    expect = LTC.instance_use(plan)
    assert expect == {"present": {"strap_cland_use_0": (1, 1)}, "spare": {"strap_cland_use_0": (1, 0)}}
    top = "bt_T present (\n .strap_cland_use_0(1'b1)\n);\nbt_T spare (\n .strap_cland_use_0(1'b0)\n);"
    assert STR.audit_count_strap_values(top, expect, prefix=LTC.MONITOR_USE_PREFIX)["verdict"] == "PASS"
    mutant = top.replace("1'b1", "1'b0")
    assert STR.audit_count_strap_values(mutant, expect, prefix=LTC.MONITOR_USE_PREFIX)["verdict"] == "FAIL"
    import pytest
    with pytest.raises(ValueError, match="partial landing monitor child"):
        plan["clock"]["landing_network"]["edges"].pop()
        LTC.instance_use(plan)


def test_use_pin_preserves_existing_pins_and_avoids_their_tracks():
    pins = [
        {"name": "cland_dn_ready_0", "xy_um": [2.0, 5.0], "layer": "M7"},
        {"name": "cland_dn_fault_0", "xy_um": [2.0, 6.0], "layer": "M7"},
        {"name": "fclk_in_cland_dn_0", "xy_um": [2.0, 4.0], "layer": "M7"},
        {"name": "neighbor", "xy_um": [2.0, 7.0], "layer": "M7"},
    ]
    result = LTC.with_use_pins(pins, TIE, [10, 10])
    assert result[:-1] == pins
    assert result[-1] == {"name": "strap_cland_use_0", "xy_um": [2.0, 8.0], "dir": "in",
                          "kind": "ctl", "epoch": False, "layer": "M7"}
    assert LTC.with_use_pins(result, TIE, [10, 10]) == result
