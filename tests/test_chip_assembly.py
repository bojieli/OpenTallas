"""Tests of the full-chip hierarchical flow (tools/chip_assembly)."""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from chip_assembly import assemble, budgets, case as cs, floorplans as fp, macros as mc  # noqa: E402


def _overlap(a, b) -> bool:
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


# -- placeholder macros -------------------------------------------------------------


def test_placeholder_pins_are_on_tracks_and_inside_the_macro():
    spec = mc.MacroSpec("t", 50.0, 40.0, mc.pins(("a", "input", 8, "W"), ("b", "output", 8, "N"),
                                                  ("c", "input", 4, "E")))
    rects = mc.pin_rects(spec)
    assert len(rects) == 8 + 8 + 4 + 1          # + the clock
    for name, (layer, (x0, y0, x1, y1)) in rects.items():
        assert 0 <= x0 < x1 <= 50.0 and 0 <= y0 < y1 <= 40.0, name
        centre = (y0 + y1) / 2 if layer == "M4" else (x0 + x1) / 2
        offset = mc.M4_Y_OFFSET if layer == "M4" else mc.M5_X_OFFSET
        assert abs(((centre - offset) / 0.048) - round((centre - offset) / 0.048)) < 1e-6, name


def test_placeholder_refuses_pins_that_do_not_fit():
    spec = mc.MacroSpec("t", 5.0, 5.0, mc.pins(("a", "input", 400, "W")))
    with pytest.raises(ValueError):
        mc.pin_rects(spec)


def test_pin_spans_confine_pins():
    spec = mc.MacroSpec("t", 100.0, 100.0, [mc.Pin("a", "input", 8, "E", span=(10.0, 20.0))])
    for name, (_, (x0, y0, x1, y1)) in mc.pin_rects(spec).items():
        if name.startswith("a"):
            assert 10.0 <= y0 and y1 <= 20.0


def test_liberty_carries_every_pin_and_per_pin_delays():
    spec = mc.MacroSpec("t", 50.0, 40.0, [mc.Pin("a", "input", 4, "W", delay_ns=0.123),
                                          mc.Pin("y", "output", 1, "E", delay_ns=0.321)])
    lib = mc.liberty_text(spec)
    assert "bus(a)" in lib and "pin(y)" in lib and "pin(clk)" in lib
    assert "0.1230" in lib and "0.3210" in lib
    assert lib.count("{") == lib.count("}")


def test_lef_and_stub_agree_on_ports():
    spec = fp.tile_memories("qwen_rom")["ot_mem_vmem"]
    lef = mc.lef_text(spec)
    stub = mc.verilog_stub(spec)
    for pin in spec.pins:
        assert f"PIN {pin.bits()[0]}" in lef
        assert re.search(rf"\b{pin.name}\b", stub)


def test_memory_densities_are_the_stated_models():
    mems = fp.tile_memories("qwen_rom")
    rom = mems["ot_mem_wstore"]
    bits = rom.extra["capacity_bits"]
    assert rom.area_um2 == pytest.approx(mc.rom_area_um2(bits), rel=0.01)
    vm = mems["ot_mem_vmem"]
    assert vm.area_um2 == pytest.approx(16384 * 32 * mc.FAKERAM_BIT_AREA_UM2 * 2.5, rel=0.01)


# -- floorplans ---------------------------------------------------------------------


def test_wire_model_is_fitted_from_the_express_link_records():
    model = fp.wire_delay_model()
    assert 0.4 < model["ps_per_um"] < 0.8
    assert 100 < model["overhead_ps"] < 300


@pytest.mark.parametrize("arch", ["qwen_rom", "hbm"])
def test_tile_macros_are_inside_and_disjoint(arch):
    tile = fp.hdc_tile(arch)
    mems = fp.tile_memories(arch)
    boxes = []
    for p in tile.placements:
        if p.master in fp.BLOCKS:
            w, h = fp.BLOCKS[p.master].width_um, fp.BLOCKS[p.master].height_um
        else:
            w, h = mems[p.master].width_um, mems[p.master].height_um
        box = (p.x, p.y, p.x + w, p.y + h)
        assert 0 < box[0] and 0 < box[1] and box[2] < tile.width_um and box[3] < tile.height_um, p
        for other in boxes:
            assert not _overlap(box, other[1]), (p.inst, other[0])
        boxes.append((p.inst, box))


@pytest.mark.parametrize("arch", ["qwen_rom", "hbm"])
def test_die_macros_are_inside_and_disjoint(arch):
    die = fp.die2x2(arch)
    boxes = []
    for p in die.placements:
        if p.master == "ot_chip_hdc_tile":
            w, h = die.tile.width_um, die.tile.height_um
        else:
            w, h = die.phys[p.master].width_um, die.phys[p.master].height_um
        box = (p.x, p.y, p.x + w, p.y + h)
        assert 0 < box[0] and 0 < box[1] and box[2] < die.width_um and box[3] < die.height_um, p
        for other in boxes:
            assert not _overlap(box, other[1]), (p.inst, other[0])
        boxes.append((p.inst, box))


def test_tile_pin_groups_cover_every_tile_pin_once():
    tile = fp.hdc_tile("qwen_rom")
    ports = assemble.module_ports(ROOT / "rtl/chip/ot_chip_hdc_tile.sv", "ot_chip_hdc_tile")
    groups = assemble.tile_pin_groups(tile, ports)
    names = [n for g in groups for n in g["names"]]
    expected = sum(p["width"] for n, p in ports.items() if n != "clk")
    assert len(names) == len(set(names)) == expected


def test_mesh_pins_interleave_out_and_in():
    tile = fp.hdc_tile("qwen_rom")
    ports = assemble.module_ports(ROOT / "rtl/chip/ot_chip_hdc_tile.sv", "ot_chip_hdc_tile")
    east = assemble.tile_pin_groups(tile, ports)[1]["names"]
    assert east[:4] == ["m_out_data[512]", "m_in_data[512]", "m_out_data[513]", "m_in_data[513]"]


def test_macro_placement_snaps_to_the_track_grid():
    tcl = assemble.placement_tcl(fp.hdc_tile("qwen_rom").placements)
    for m in re.finditer(r"^ot_place \{\S+\} (\S+) (\S+) ", tcl, re.M):
        for v in (float(m.group(1)), float(m.group(2))):
            assert abs(v / assemble.GRID_UM - round(v / assemble.GRID_UM)) < 1e-6


# -- case construction -----------------------------------------------------------


def test_strip_param_overrides_keeps_everything_else():
    text = "ot_hdc_matvec #(.W(W), .G(G)) u_me (.clk(clk));\nfoo #(.A(1)) u (.x(y));\n"
    out, removed = cs.strip_param_overrides(text, ["ot_hdc_matvec"])
    assert out.startswith("ot_hdc_matvec u_me (.clk(clk));")
    assert "foo #(.A(1))" in out and removed == ["ot_hdc_matvec #(.W(W), .G(G))"]


def test_the_core_passes_only_hardened_defaults_to_its_units():
    """Stripping the overrides is sound only while the core's values equal the
    hardened blocks' defaults (both 16/4/8/24/16)."""
    core = (ROOT / "rtl/hdc/ot_hdc_core.sv").read_text()
    matvec = (ROOT / "rtl/hdc/ot_hdc_matvec.sv").read_text()
    stream = (ROOT / "rtl/hdc/ot_hdc_stream.sv").read_text()
    tile = (ROOT / "rtl/chip/ot_chip_hdc_tile.sv").read_text()
    for name, value in (("W", 16), ("G", 4), ("IL", 8), ("AW", 24), ("NW", 16)):
        assert re.search(rf"parameter integer {name}\s*=\s*{value}\b", matvec), name
        assert re.search(rf"\b{name} = {value}\b", tile), name
    for name, value in (("W", 16), ("WR", 64), ("AW", 24), ("NW", 16)):
        assert re.search(rf"parameter integer {name}\s*=\s*{value}\b", stream), name
    assert ".WR(G * W)" in core


def test_write_case_preserves_the_sdc_mtime(tmp_path):
    spec = cs.CaseSpec(nickname="x", top="x", sources=[], die_um=(10, 10), sdc="a\n")
    cs.write_case(tmp_path, spec)
    before = (tmp_path / "constraint.sdc").stat().st_mtime
    spec.sdc = "b\n"
    cs.write_case(tmp_path, spec)
    assert (tmp_path / "constraint.sdc").read_text() == "b\n"
    assert (tmp_path / "constraint.sdc").stat().st_mtime == before


# -- budgets -----------------------------------------------------------------------


def test_block_stub_models_the_boundary_delays():
    char = {"ports": {"a": {"direction": "input", "width": 2, "in2reg_ps": 123.0},
                      "y": {"direction": "output", "width": 1, "reg2out_ps": 45.0}}}
    stub = budgets.block_stub(fp.BLOCKS["ot_chip_pkg_ctrl"], char)
    delays = {p.name: p.delay_ns for p in stub.pins}
    assert delays == {"a": pytest.approx(0.123), "y": pytest.approx(0.045)}


def test_committed_budget_tables_are_consistent():
    table = ROOT / "results/physical_abi3/asap7/chip/budgets/hdc_tile_qwen_rom.json"
    if not table.is_file():
        pytest.skip("no budget table yet")
    import json
    b = json.loads(table.read_text())
    T, U = b["period_ps"], b["uncertainty_ps"]
    for name, blk in b["blocks"].items():
        for port, r in blk["ports"].items():
            assert r["external_ps"] + r["internal_budget_ps"] == pytest.approx(T - U, abs=0.2) or \
                r["status"] == "untimed", (name, port)
            if r["status"] == "fits" and "feedthrough_ps" not in r:
                assert r["internal_budget_ps"] >= r["internal_ps"] - 0.1, (name, port)


# -- RTL ------------------------------------------------------------------------------


@pytest.mark.skipif(shutil.which("iverilog") is None, reason="iverilog not available")
@pytest.mark.parametrize("stall", [0, 40, 90])
def test_mesh_link_delivers_in_order_at_full_rate(tmp_path, stall):
    binary = tmp_path / "tb.vvp"
    subprocess.run(["iverilog", "-g2012", "-o", str(binary),
                    str(ROOT / "rtl/test/tb_chip_mesh_link.sv"),
                    str(ROOT / "rtl/chip/ot_chip_mesh_link.sv")], check=True)
    out = subprocess.run(["vvp", "-n", str(binary), f"+STALL={stall}"], capture_output=True,
                         text=True, check=True).stdout
    line = [l for l in out.splitlines() if l.startswith(("PASS", "FAIL"))][-1]
    assert line.startswith("PASS"), line
    if stall == 0:
        assert line.split()[1:] == ["2000", "2000"]
