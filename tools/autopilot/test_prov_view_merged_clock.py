"""DIE-HBM-92-GEN 11-08 (HBM q_b100 gen phys "u_hb_idx__s_Q_r0c0_k0h1/clk_pair[0]: actual LEF input clock required"):
a contract abstract marks the pins of a merged core clock tap USE CLOCK (its lib marks them clock : true); other pins
and abstracts without a merged tap are unchanged."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import prov_view as PV  # noqa: E402

PINS = [dict(name="clk_pair[0]", x=10.0, y=0.0, layer="M5"), dict(name="clk_pair[1]", x=10.0, y=20.0, layer="M5"),
        dict(name="clk", x=0.0, y=5.0, layer="M4"), dict(name="d", x=0.0, y=7.0, layer="M4")]
DIRS = {"clk_pair[0]": "INPUT", "clk_pair[1]": "INPUT", "clk": "INPUT", "d": "INPUT"}
T = {"clock": {"taps": [{"kind": "core", "name": "u_c.clk_pair", "merged_clock_ports": ["clk_pair[0]", "clk_pair[1]"]},
                        {"kind": "core", "name": "u_other.ck", "merged_clock_ports": ["ck[0]", "ck[1]"]}]}}


def _use(lef, pin):
    blk = lef.split(f"  PIN {pin}\n", 1)[1]
    return blk.split("\n", 2)[1].strip()


def test_merged_tap_pins_are_use_clock():
    assert PV.merged_clock_pins(T, "u_c") == {"clk_pair[0]", "clk_pair[1]"}
    lef = PV.contract_lef("m", 20.0, 20.0, PINS, DIRS, 5, PV.merged_clock_pins(T, "u_c"))
    assert _use(lef, "clk_pair[0]") == "USE CLOCK ;" and _use(lef, "clk_pair[1]") == "USE CLOCK ;"
    assert _use(lef, "clk") == "USE SIGNAL ;" and _use(lef, "d") == "USE SIGNAL ;"


def test_no_merged_tap_is_byte_identical():
    assert PV.merged_clock_pins(T, "u_x") == set()
    assert PV.contract_lef("m", 20.0, 20.0, PINS, DIRS, 5, PV.merged_clock_pins(T, "u_x")) == \
        PV.contract_lef("m", 20.0, 20.0, PINS, DIRS, 5)
    assert "USE CLOCK" not in PV.contract_lef("m", 20.0, 20.0, PINS, DIRS, 5).split("  PIN VDD")[0]
