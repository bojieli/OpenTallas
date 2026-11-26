"""PER_BIT_PORT_1125 (KV-OWN-HUB-R2, kv3_hub_C R6 kit_rtl): the qkd_ahub ck7 view's seven ck pins tapped on seven ports
(clk_c0, clk_c2..clk_c7), bound `.ck({7{clk}})` after swap_ahub_boundary -> `.ck({clk_c7, .., clk_c0})`; the merged
same-port form (MERGED_BUS_1108) and the refusals stay."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kit_core_clocks as K  # noqa: E402

CORES = [dict(inst="ahub", module="qkd_ahub", native_boundary_adapter="qkd_ahub_ck7_strap")]
PORTS = ["clk_c0", "clk_c2", "clk_c3", "clk_c4", "clk_c5", "clk_c6", "clk_c7"]


def _bound():
    return ("module kv3_hub_C_part(\n    input clk,\n    input [35:0] am0,am1,am2,am3\n);\n"
            "    qkd_ahub_static_dw #(.AP_OFS(64'hffe3ffe2ffe1ffe1), .FR_OFS(-7), .Z_IN_STRIDE(4)) u_ahub (\n"
            "        .ck(clk),\n        .am0(am0),\n        .am1(am1),\n        .am2(am2),\n        .am3(am3)\n    );\nendmodule\n")


def _rows(ports):
    return [(p, "u_bound.u_ahub", f"ck[{b}]", 0.0, 242.72) for b, p in enumerate(ports)]


def test_hub_c_seven_ports_wire_per_bit():
    b, _ = K.swap_native_cores(_bound(), CORES)
    assert ".ck({7{clk}})" in b
    out, rec = K.wire(b, "kv3_hub_C_part", _rows(PORTS))
    assert ".ck({clk_c7, clk_c6, clk_c5, clk_c4, clk_c3, clk_c2, clk_c0})" in out
    for p in PORTS:
        assert f"input wire {p}," in out
    assert sorted((r["port"], r["pin"]) for r in rec) == sorted((p, f"ck[{b}]") for b, p in enumerate(PORTS))
    assert {r["rule"] for r in rec} == {"per_bit_port"}


def test_same_port_merged_bus_unchanged():
    b, _ = K.swap_native_cores(_bound(), CORES)
    out, rec = K.wire(b, "kv3_hub_C_part", _rows(["clk_c0"] * 7))
    assert ".ck({7{clk_c0}})" in out
    assert {r["rule"] for r in rec} == {"merged_bus_base"}


def test_gap_still_refused():
    b, _ = K.swap_native_cores(_bound(), CORES)
    rows = [r for r in _rows(PORTS) if r[2] != "ck[3]"]
    with pytest.raises(ValueError, match="more than one planned bit"):
        K.wire(b, "kv3_hub_C_part", rows)


def test_bit_tapped_twice_refused():
    b, _ = K.swap_native_cores(_bound(), CORES)
    rows = _rows(PORTS) + [("clk_c9", "u_bound.u_ahub", "ck[2]", 0.0, 242.72)]
    with pytest.raises(ValueError, match="more than one planned bit"):
        K.wire(b, "kv3_hub_C_part", rows)
