"""pre_route_gate.check_slew_longnet: max-slew violators FAIL, long single-driver nets WARN / FAIL (S81-CAPC 10-19)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pre_route_gate as G  # noqa: E402

OK = ("GATE_SLEW violations 0 worst_slack none (-) (TT placement RC after CTS)\n"
      "GATE_LONGNET count 0 threshold_um 120.0 max_um 79.5 signal_nets 9000\n")
BAD = ("GATE_SLEW violations 2 worst_slack -40.71 (_1653_/A slew 300.71 limit 260.00) (TT placement RC after CTS)\n"
       "GATE_LONGNET count 1 threshold_um 120.0 max_um 157.3 signal_nets 9000\n"
       "GATE_LONGNET_TOP 157.3 um net net2389 driver place2390/Y (BUFx3_ASAP7_75t_R) loads 1\n")


def run(out, spec=None, rc="0"):
    g = G.Gate()
    G.check_slew_longnet(g, spec or {}, out, {"GATE_CTS_RC": rc})
    return {i["check"]: i["severity"] for i in g.items}


def test_clean():
    assert run(OK) == {"max_slew": "INFO", "long_net": "INFO"}


def test_violations_fail_and_long_warn():
    assert run(BAD) == {"max_slew": "FAIL", "long_net": "WARN"}


def test_spec_cap_makes_long_net_fail():
    assert run(BAD, {"max_signal_net_um": 120})["long_net"] == "FAIL"
    assert run(OK, {"max_signal_net_um": 120})["long_net"] == "INFO"


def test_missing_line_warns_and_failed_cts_skips():
    assert run("")["max_slew"] == "WARN"
    assert run(BAD, rc="1") == {}
