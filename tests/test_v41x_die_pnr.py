"""The adopted V4.1 die's physical views agree with its RTL (tools/v41x_die_pnr.py, hbm_phy_gen --variant v41x)."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tools/mem_compiler"))

import v41x_die_pnr as pnr  # noqa: E402
import hbm_phy_gen  # noqa: E402

PHY_DIR = ROOT / "physical/asap7_memory_macros/ot_hbm3e_phy_v41x"
DIE_PARAMS = {"NPC": 32, "KTAGW": 17, "NPC_W": 8, "LWIN": 10}   # ot_chip_v41x_die.sv g_hbm[s].u_hbm


def rtl_ports(path: Path, module: str, params: dict[str, int]) -> dict[str, tuple[str, int]]:
    text = path.read_text()
    body = text[text.index(f"module {module}"):]
    head, ports = body.split(") (", 1) if ") (" in body.split(");")[0] else ("", body.split("(", 1)[1])
    env = {k: v for k, v in re.findall(r"parameter\s+integer\s+(\w+)\s*=\s*([^,/\n]+)", head)}
    env = {k: eval(v, {}, {}) for k, v in env.items()}
    env.update(params)
    ports = ports[:ports.index(");")]
    out = {}
    for m in re.finditer(r"(input|output)\s+(?:wire|reg)?\s*(?:\[([^\]]+):0\])?\s*(\w+)", ports):
        width = eval(m.group(2).replace("/", "//"), {}, env) + 1 if m.group(2) else 1
        out[m.group(3)] = (m.group(1), width)
    return out


def test_phy_abstract_matches_the_adopted_stack_interface():
    rtl = rtl_ports(ROOT / "rtl/chip/ot_chip_v41x_hbm3e_phy.sv", "ot_chip_v41x_hbm3e_phy", DIE_PARAMS)
    bb = rtl_ports(PHY_DIR / "ot_hbm3e_phy_v41x_bb.v", "ot_hbm3e_phy_v41x", {})
    assert rtl == bb
    lef = (PHY_DIR / "ot_hbm3e_phy_v41x.lef").read_text()
    assert "SIZE 12000.096 BY 833.490" in lef                     # die assembly: 12.0001 x 0.8335 mm
    assert lef.count("\n  PIN ") == sum(w for _, w in bb.values()) + 2          # + VDD, VSS


def test_full_k_address_phy_abstract_matches_full_mode(tmp_path):
    sheet = hbm_phy_gen.generate_v41x(tmp_path, k_aw=30)
    name = "ot_hbm3e_phy_v41x_aw30"
    d = tmp_path / name
    rtl = rtl_ports(ROOT / "rtl/chip/ot_chip_v41x_hbm3e_phy.sv", "ot_chip_v41x_hbm3e_phy",
                    {**DIE_PARAMS, "K_AW": 30})
    bb = rtl_ports(d / f"{name}_bb.v", name, {})
    assert rtl == bb
    assert rtl["k_addr"] == ("input", 32 * 30)
    assert sheet["interface"]["parameters"]["K_AW"] == 30
    lef = (d / f"{name}.lef").read_text()
    assert lef.count("\n  PIN ") == sum(w for _, w in bb.values()) + 2
    assert sheet["pins"]["signal_pins"] == 22237


def test_karb_strip_windows_face_the_phy_windows():
    lef = (PHY_DIR / "ot_hbm3e_phy_v41x.lef").read_text()
    xs = {m.group(1): float(m.group(2))
          for m in re.finditer(r"PIN (\S+)\n(?:.*\n){5}\s+RECT ([\d.]+) ", lef)}
    win = 12000.096 / 32
    for p in (0, 13, 31):
        # the arbiter's stack-side bits of pseudo-channel p sit in the same window as the PHY's
        lo, hi = p * pnr.PHY_PC_WINDOW_UM + pnr.PC_PIN_SPAN[0], p * pnr.PHY_PC_WINDOW_UM + pnr.PC_PIN_SPAN[1]
        for b in (f"k_addr[{28 * p}]", f"kr_data[{256 * p + 255}]", f"k_v[{p}]"):
            assert lo - 0.1 <= xs[b] <= hi, (b, xs[b], lo, hi)
        assert abs(win - pnr.PHY_PC_WINDOW_UM) < 0.01
    karb = rtl_ports(ROOT / "rtl/chip/ot_chip_v41x_hbm_karb.sv", "ot_chip_v41x_hbm_karb", {})
    per_pc = {s: pnr.karb_pc_pins(0, s) for s in ("b", "h")}
    for s, names in per_pc.items():
        buses = {n.partition("[")[0] for n in names}
        assert buses == {n for n in karb if n.startswith(("b_",) if s == "b" else ("h_", "r_")) and n != "b_grants"}
        # every bus contributes exactly its per-channel share
        for bus in buses:
            assert sum(1 for n in names if n.startswith(bus + "[")) * 32 == karb[bus][1]


def test_karb_strip_pin_regions_cover_every_port_once():
    case = pnr.karb_strip()
    regions = [case["args"][i + 1] for i, a in enumerate(case["args"]) if a == "--pin-region"]
    karb = rtl_ports(ROOT / "rtl/chip/ot_chip_v41x_hbm_karb.sv", "ot_chip_v41x_hbm_karb", {})
    all_bits = [n if w == 1 else f"{n}[{i}]" for n, (_, w) in karb.items() for i in range(w)]
    pats = [re.compile(r.rpartition("=")[0]) for r in regions]
    for b in all_bits:
        hits = sum(1 for p in pats if p.search(b))
        assert hits == 1, (b, hits)


def test_karb_bank4_is_a_separate_local_route_boundary():
    case = pnr.karb_bank4()
    args = case["args"]
    assert args[args.index("--param") + 1] == "NPC=4"
    assert case["floorplan"]["die_um"] == [1500.0, 30.24]
    regions = [args[i + 1] for i, a in enumerate(args) if a == "--pin-region"]
    karb = rtl_ports(ROOT / "rtl/chip/ot_chip_v41x_hbm_karb.sv", "ot_chip_v41x_hbm_karb", {"NPC": 4})
    all_bits = [n if w == 1 else f"{n}[{i}]" for n, (_, w) in karb.items() for i in range(w)]
    pats = [re.compile(r.rpartition("=")[0]) for r in regions]
    for b in all_bits:
        assert sum(1 for p in pats if p.search(b)) == 1, b


def test_karb_strip_fit_uses_the_floorplan_band_without_overwriting_the_wider_case():
    fit = pnr.CASES["karb_strip_fit"]()
    wide = pnr.karb_strip()
    assert fit["floorplan"]["die_um"] == [12000.0, 17.28]
    assert fit["floorplan"]["die_um"][1] <= 17.2 + 0.08 + 1e-9
    assert fit["nickname"] != wide["nickname"]
    assert fit["output"] != wide["output"]


def test_karb_bank4_m9_is_an_independent_routing_sensitivity():
    base = pnr.karb_bank4()
    m9 = pnr.CASES["karb_bank4_m9"]()
    args = m9["args"]
    assert args[args.index("--routing-layers") + 1:args.index("--routing-layers") + 3] == ["M2", "M9"]
    assert m9["floorplan"] == base["floorplan"]
    assert m9["nickname"] != base["nickname"]
    assert m9["output"] != base["output"]


def test_karb_bank4_pipe_m9_keeps_the_same_boundary():
    direct = pnr.CASES["karb_bank4_m9"]()
    piped = pnr.CASES["karb_bank4_pipe_m9"]()
    assert piped["floorplan"] == direct["floorplan"]
    assert [piped["args"][i + 1] for i, x in enumerate(piped["args"]) if x == "--param"] == ["NPC=4", "PIPE_OUT=1"]
    assert piped["nickname"] != direct["nickname"]
    assert piped["output"] != direct["output"]
