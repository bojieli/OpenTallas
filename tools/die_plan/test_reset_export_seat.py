import json, pathlib, sys
import pytest
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import reset_tree as RT


class FakeP:
    def __init__(self, seats, d_xy=(1689.632, 17.312)):
        self.types = {"t": {"reset": {"export_seats_um": seats},
                            "reset_start_raw_exports": [{"port": "rst_start_raw_0", "instance": "u_rrl_31", "net": "rst_rl_31", "xy_um": [1689.632, 17.312]}]}}


def tree():
    return {"relays": [{"name": "u_rrl_30", "xy": [1689.632, 17.312], "q": "rst_rl_30", "d": "rst_rl_29"},
                       {"name": "u_rrl_31", "xy": [1689.632, 17.312], "q": "rst_rl_31", "d": "rst_rl_30"},
                       {"name": "u_rrl_29", "xy": [2015.296, 17.312], "q": "rst_rl_29", "d": "x"}]}


def test_seat_within_reach(monkeypatch):
    monkeypatch.setattr(RT, "relay_um", lambda P, tn: 405.0)
    T = RT._with_export_seats(FakeP({"rst_start_raw_0": [1480.0, 10.8]}), "t", tree())
    assert T["export_seats"] == {"u_rrl_31": [1480.0, 10.8, "rst_start_raw_0"]}


def test_seat_over_reach_refused(monkeypatch):
    monkeypatch.setattr(RT, "relay_um", lambda P, tn: 405.0)
    with pytest.raises(RT.ResetError, match="over the relay reach"):
        RT._with_export_seats(FakeP({"rst_start_raw_0": [1000.0, 10.8]}), "t", tree())


def test_unknown_port_refused(monkeypatch):
    monkeypatch.setattr(RT, "relay_um", lambda P, tn: 405.0)
    with pytest.raises(RT.ResetError, match="not a declared private raw start export"):
        RT._with_export_seats(FakeP({"nope": [1480.0, 10.8]}), "t", tree())


def test_no_key_no_change():
    P = FakeP({}); P.types["t"]["reset"] = {}
    T = tree(); assert RT._with_export_seats(P, "t", T) is T and "export_seats" not in T
