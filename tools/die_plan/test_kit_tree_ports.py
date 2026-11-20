"""DIE-LEVEL-CHECK-1119 (FABLE-PD-S81-2040 fix 2): a die tap whose port has no per-port arrivals takes the range over the
record's ports that are die tree taps of the partition, not the whole-type range (which holds forwarded clock ports)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import die_sta_related as R  # noqa: E402

REG = dict(clkq_max_wire_ps=40.0, clkq_min_nowire_ps=20.0, setup_ps=10.0, hold_ps=5.0)
SPEC = {"corners": {"FF": {"lat_min_ps": 39.35, "lat_max_ps": 416.53, "n": 1504}},
        "ports": {"clk_t16": {"FF": {"lat_min_ps": 279.81, "lat_max_ps": 341.43}},
                  "clk_t18": {"FF": {"lat_min_ps": 314.89, "lat_max_ps": 416.53}},
                  "fclk_in_cland_dn_0[0]": {"FF": {"lat_min_ps": -0.65, "lat_max_ps": 39.52}}}}


def test_own_port_wins():
    m = R.kit_model(SPEC, "FF", "col", REG, "clk_t16", tree_ports={"clk_t16", "clk_t18", "clk_t20"})
    assert (m["lat_early"], m["lat_late"]) == (279.81, 341.43) and m["name"] == "kit:col:clk_t16"


def test_missing_port_takes_tree_port_union_not_forwarded_clock():
    m = R.kit_model(SPEC, "FF", "col", REG, "clk_t20", tree_ports={"clk_t16", "clk_t18", "clk_t20"})
    assert (m["lat_early"], m["lat_late"]) == (279.81, 416.53) and m["name"] == "kit:col:tree-ports"


def test_no_tree_ports_keeps_type_range():
    m = R.kit_model(SPEC, "FF", "col", REG, "clk_t20")
    assert (m["lat_early"], m["lat_late"]) == (39.35, 416.53)
    m = R.kit_model(SPEC, "FF", "col", REG, "clk_t20", tree_ports={"clk_t20"})
    assert (m["lat_early"], m["lat_late"]) == (39.35, 416.53)
