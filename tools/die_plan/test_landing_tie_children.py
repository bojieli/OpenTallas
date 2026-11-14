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
