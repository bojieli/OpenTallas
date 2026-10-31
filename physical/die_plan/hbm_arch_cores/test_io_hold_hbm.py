"""HBM-CORES-KITS-32 10-31: IO-HOLD option A for HBM hard cores (recipe io_hold sender_min + io_hold_ports, the rows of
the HBM die IO-hold table lanes/IO-HOLD-HBM.md): only the listed input buses take the sender guarantee; the rest of
the SDC is unchanged and the default (no io_hold) kit SDC is byte-identical."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gen_core_kit_hbm as G  # noqa: E402

DIRS = {"block_data": "input", "head_weight": "input", "rst_n": "input", "emit_v": "input", "ql_v": "output"}


def test_legacy_default_no_ports():
    assert G.sender_min_ports({}, DIRS, ["clk"], ["rst_n"]) == {}


def test_sender_min_listed_ports_only():
    m = G.sender_min_ports({"io_hold": "sender_min", "io_hold_ports": ["head_weight", "block_data"]}, DIRS, ["clk"], ["rst_n"])
    g = round((1 - G.UNC_SPLIT) * G.UNC_HOLD_PS, 4)
    assert m == {"block_data": g, "head_weight": g}


@pytest.mark.parametrize("ports", [[], ["ql_v"], ["rst_n"], ["nope"]])
def test_sender_min_fails_closed(ports):
    with pytest.raises(SystemExit):
        G.sender_min_ports({"io_hold": "sender_min", "io_hold_ports": ports}, DIRS, ["clk"], ["rst_n"])


def test_bad_mode():
    with pytest.raises(SystemExit):
        G.sender_min_ports({"io_hold": "plan_demand", "io_hold_ports": ["block_data"]}, DIRS, ["clk"], ["rst_n"])


def test_sdc_override_after_flat_min():
    base = G.sdc(833.0, 250.0, 40.0, ["clk"], ["rst_n"], "t", 250.0)
    assert G.sdc(833.0, 250.0, 40.0, ["clk"], ["rst_n"], "t", 250.0, in_min_ports={}) == base
    s = G.sdc(833.0, 250.0, 40.0, ["clk"], ["rst_n"], "t", 250.0, in_min_ports={"block_data": 12.5, "head_weight": 12.5})
    flat = s.index("set_input_delay -min -40.0000 -clock vclk $non_clk_in")
    over = s.index("set_input_delay -min 12.5000 -clock vclk [get_ports {block_data head_weight}]")
    assert flat < over and s.count("set_input_delay -min 12.5000") == 1
