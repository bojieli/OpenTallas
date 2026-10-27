"""KV-KITS-4 10-27: declared hard-IP line side (bump_ports) in the partition kit port contract (gen_phys)."""
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gen_phys as G      # noqa: E402
import gen_rtl            # noqa: E402
import port_bind_gate     # noqa: E402

DECL = [dict(pin="link_v", dir="output", width=1), dict(pin="link_flit", dir="output", width=3),
        dict(pin="far_v", dir="input", width=1), dict(pin="far_flit", dir="input", width=3)]


def _plan(orient="R0"):
    c = dict(inst="u_bound.u_ucie_rom", module="phy_m", lef="phy.lef", lib="phy_tt.lib", origin_um=[100.0, 50.0],
             orient=orient, bump_ports=DECL)
    return SimpleNamespace(types={"ts": dict(module="ts_part", contents=[c], outline_um=[400.0, 300.0])})


def _bind(tmp, rows=None, bop=None):
    rows = rows if rows is not None else [
        dict(die_port=f"p0_{b['pin']}", dir=b["dir"], width=b["width"], partition="p0", leaf="p0.u_ucie_rom",
             pin=b["pin"], part_port=f"bump_ucie_rom_{b['pin']}") for b in DECL]
    (tmp / "bind_report.json").write_text(json.dumps(dict(bump_ports=rows)))
    kd = tmp / "kit_rtl"
    kd.mkdir(exist_ok=True)
    bop = bop if bop is not None else [dict(port=f"bump_ucie_rom_{b['pin']}", dir=b["dir"], width=b["width"]) for b in DECL]
    (kd / "kit_rtl.json").write_text(json.dumps(dict(bind_out=str(tmp), instances=["p0"], bound_only_pins=bop)))
    (kd / "kit_rtl.f").write_text("")
    return kd / "kit_rtl.f"


def _lef(tmp):
    pins = []
    for b in DECL:
        names = [b["pin"]] if b["width"] == 1 else [f"{b['pin']}[{i}]" for i in range(b["width"])]
        for k, n in enumerate(names):
            x = 10.0 + 2 * len(pins)
            pins.append(f"  PIN {n}\n    DIRECTION INPUT ;\n    PORT\n      LAYER M5 ;\n"
                        f"      RECT {x:.3f} 79.808 {x + 0.024:.3f} 80.000 ;\n    END\n  END {n}\n")
    (tmp / "phy.lef").write_text("MACRO phy_m\n  SIZE 90.000 BY 80.000 ;\n" + "".join(pins) + "END phy_m\n")


def test_contract_names_from_bind(tmp_path):
    bumps = G.kit_bump_ports(_plan(), "ts", _bind(tmp_path))
    assert [(b["port"], b["dir"], b["width"]) for b in bumps] == [
        ("bump_ucie_rom_far_flit", "input", 3), ("bump_ucie_rom_far_v", "input", 1),
        ("bump_ucie_rom_link_flit", "output", 3), ("bump_ucie_rom_link_v", "output", 1)]
    # the port_bind gate on a netlist carrying exactly these ports + the face pin: PASS, and FAIL without them
    pins = [dict(bus="a", bit=0)] + [dict(bus=b["port"], bit=i) for b in bumps for i in range(b["width"])]
    net = ("module ts_part(a, bump_ucie_rom_far_flit, bump_ucie_rom_far_v, bump_ucie_rom_link_flit, "
           "bump_ucie_rom_link_v);\n input [0:0] a;\n input [2:0] bump_ucie_rom_far_flit;\n input bump_ucie_rom_far_v;\n"
           " output [2:0] bump_ucie_rom_link_flit;\n output bump_ucie_rom_link_v;\nendmodule\n")
    assert port_bind_gate.check(net, "ts_part", pins)["verdict"] == "PASS"
    r = port_bind_gate.check(net, "ts_part", [dict(bus="a", bit=0)])
    assert r["verdict"] == "FAIL" and r["extra"] == 8


def test_no_declaration_no_change(tmp_path):
    P = _plan()
    P.types["ts"]["contents"][0].pop("bump_ports")
    assert G.kit_bump_ports(P, "ts", tmp_path / "missing" / "kit_rtl.f") == []


def test_refuse_mismatch(tmp_path):
    rows = [dict(die_port="p0_link_v", dir="output", width=1, partition="p0", leaf="p0.u", pin="link_v",
                 part_port="bump_ucie_rom_link_v")]
    with pytest.raises(gen_rtl.GenError, match="not bound"):
        G.kit_bump_ports(_plan(), "ts", _bind(tmp_path, rows=rows))
    with pytest.raises(gen_rtl.GenError, match="bound-only pin"):
        G.kit_bump_ports(_plan(), "ts", _bind(tmp_path, bop=[]))


def test_pins_on_macro_pin_shapes(tmp_path):
    _lef(tmp_path)
    P = _plan()
    bumps = G.kit_bump_ports(P, "ts", _bind(tmp_path))
    macros = [("u_bound.u_ucie_rom", "phy_m", "phy.lef", "phy_tt.lib", 100.0, 50.0, "R0")]
    sites = G.bump_pin_sites(P, "ts", bumps, macros, tmp_path)
    assert len(sites) == 8
    by = {(p, i): (ln, x, y) for p, i, ln, x, y, w, h in sites}
    # link_v is the first LEF pin (x 10.000..10.024, y 79.808..80): + macro origin (100, 50)
    assert by[("bump_ucie_rom_link_v", 0)] == ("M5", 110.012, 129.904)
    mx = G.bump_pin_sites(P, "ts", bumps, [macros[0][:6] + ("MX",)], tmp_path)
    assert {(p, i): y for p, i, ln, x, y, w, h in mx}[("bump_ucie_rom_link_v", 0)] == 50.096
    with pytest.raises(ValueError, match="no placed view"):
        G.bump_pin_sites(P, "ts", bumps, [], tmp_path)


NET_BUMP = r"""
module top(clk, a, far, link);
  input clk; input [0:0] a; input [1:0] far; output link;
  wire q; wire qn;
  DFFHQNx1_ASAP7_75t_R \u_bin_a.q[0]$_DFF_P_  (.CLK(clk), .D(a[0]), .QN(qn));
  phy_m u_phy (.clk(clk), .fdi(qn), .far(far), .link(link));
endmodule
"""


def test_face_guard_bump_exempt_only_on_macro_pin(tmp_path):
    import face_guard
    pins = [dict(bus="a", bit=0)]
    bumps = [("far", "input", 2), ("link", "output", 1)]
    assert face_guard.guard(NET_BUMP, pins=pins)["fail_counts"].get("unregistered") == 3
    r = face_guard.guard(NET_BUMP, pins=pins, bumps=bumps)
    assert r["verdict"] == "PASS" and r["bump_bits"] == 3, r
    # a bump that also feeds logic, or is driven by a std cell, fails
    bad = NET_BUMP.replace("phy_m u_phy", "INVx1_ASAP7_75t_R _x_ (.A(far[1]), .Y(q));\n  phy_m u_phy")
    assert face_guard.guard(bad, pins=pins, bumps=bumps)["fail_counts"] == {"bump": 1}
    assert face_guard.guard(NET_BUMP, pins=pins, bumps=[("far", "input", 3), ("link", "output", 1)])["fail_counts"] == {"bump": 1}
    # kit wiring: bump_ports in budget.json beside pins.json
    (tmp_path / "budget.json").write_text(json.dumps(dict(bump_ports=[dict(port="far", dir="input", width=2),
                                                                    dict(port="link", dir="output", width=1)])))
    assert face_guard.kit_bump_list(tmp_path) == bumps
