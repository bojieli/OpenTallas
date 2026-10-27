"""INFRA-FIRST-QC-R21 (NUMBER-CHECK-QC-R20 kit bug): ports across a planned die channel are die-top nets in the GRT
route netlist (not counted as abutted); abutted ports pass the both-sides pin coincidence check."""
import pytest
import die_trial as DT
import schema as S


class FakePlan:
    """three partitions: a | b abutted at x = 10, c above a across a 43.2-um channel (port 'pc' listed in it)."""
    name = "t"

    def __init__(self, shift_b=0.0):
        self.types = {"A": dict(outline_um=[10.0, 10.0], ft_slots=[]), "B": dict(outline_um=[10.0, 10.0], ft_slots=[])}
        self.parts = {"a": dict(type="A", origin_um=[0.0, 0.0]), "b": dict(type="B", origin_um=[10.0 + shift_b, 0.0]),
                      "c": dict(type="B", origin_um=[0.0, 53.2])}
        self.ports = {"pab": dict(src=dict(part="a", bus="x_o"), dst=dict(part="b", bus="x_i"), width=2),
                      "pc": dict(src=dict(part="a", bus="y_o"), dst=dict(part="c", bus="y_i"), width=3)}
        self._ch = {"pc": dict(name="cc", ports=["pc"])}

    def channel_of(self, pid):
        return self._ch.get(pid)

    def to_die(self, part, pt):
        o = self.parts[part]["origin_um"]
        return (o[0] + pt[0], o[1] + pt[1])


def _bits(n):
    return {"A": {"x_o": 2, "y_o": n}, "B": {"x_i": 2, "y_i": n}}


@pytest.fixture(autouse=True)
def _no_standin(monkeypatch):
    monkeypatch.setattr(DT, "standin_module_names", lambda P: {t: f"m_{t}" for t in P.types})
    monkeypatch.setattr(S, "port_pins_count", lambda pr: int(pr["width"]))


def test_channel_port_is_a_die_top_net():
    P = FakePlan()
    v, nft = DT.route_netlist(P, _bits(3))
    assert DT.route_netlist.channel == dict(ports=1, bits=3, new_net_bits=3, ft_joined_bits=0)
    assert "wire [2:0] ch_pc;" in v and ".y_o(ch_pc)" in v and ".y_i(ch_pc)" in v
    assert "x_o" not in v                                # the abutted port stays out of the GRT netlist
    v0, _ = DT.route_netlist(P, _bits(3), channel_nets=False)
    assert "ch_pc" not in v0 and DT.route_netlist.channel["ports"] == 0
    assert [c[0] for c in DT.channel_ports(P)] == ["pc"]


def test_channel_port_bus_width_mismatch_refuses():
    with pytest.raises(ValueError):
        DT.route_netlist(FakePlan(), _bits(4))


def _tp(P):
    # type pin tables: A's E face x = 10, B's W face x = 0, same y per bit
    return {"A": {("x_o", 0): ("M5", 10.0, 1.0), ("x_o", 1): ("M5", 10.0, 2.0)},
            "B": {("x_i", 0): ("M5", 0.0, 1.0), ("x_i", 1): ("M5", 0.0, 2.0)}}


def test_abutted_pin_check_pass_and_fail():
    r = DT.abutted_pin_check(FakePlan(), _tp(None))
    assert r["verdict"] == "PASS" and r["ports"] == 1 and r["bits"] == 2      # the channel port is not checked here
    bad = DT.abutted_pin_check(FakePlan(shift_b=0.054), _tp(None))           # b one site off the a face
    assert bad["verdict"] == "FAIL" and bad["bad_bits"] == 2 and bad["bad_ports"] == 1
    tp = _tp(None)
    tp["B"][("x_i", 1)] = ("M6", 0.0, 2.0)                                    # layer mismatch on one bit
    assert DT.abutted_pin_check(FakePlan(), tp)["bad_bits"] == 1


def test_channel_hop_joins_the_feedthrough_net():
    """a's y slot is a feedthrough (y_i -> y_o); the channel port continues it to c: ONE net, no second driver."""
    P = FakePlan()
    P.types["A"]["ft_slots"] = [dict(name="y")]
    tb = _bits(3)
    tb["A"]["y_i"] = 3
    v, nft = DT.route_netlist(P, tb)
    assert nft == 3 and "ch_pc" not in v
    assert ".y_i(ft_a__y)" in v and ".y_o(ft_a__y)" in v and ".y_i(ft_a__y)" in v.split(" c (")[1]
    assert v.count("wire [2:0] ft_a__y;") == 1
    assert DT.route_netlist.channel == dict(ports=1, bits=3, new_net_bits=0, ft_joined_bits=3)
    import re
    for m in re.finditer(r"\((\.[^;]*)\);", v):                 # no instance pin connected twice
        pins = re.findall(r"\.(\w+)\(", m.group(1))
        assert len(pins) == len(set(pins))
