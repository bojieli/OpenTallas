"""W18: V4.1 ROM full-die assembly -- legal HBM PHY abstract, hierarchical PDN pieces, power-gating
controller, real-element floorplan."""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools/mem_compiler"))
sys.path.insert(0, str(ROOT / "tools/w18"))
sys.path.insert(0, str(ROOT / "tools"))

import hbm_phy_gen  # noqa: E402

PHY = "ot_hbm3e_phy_v41x_aw30_e8p5"
PHY_DIR = ROOT / "physical/asap7_memory_macros" / PHY


def test_legal_phy_views_match_generator(tmp_path):
    sheet = hbm_phy_gen.generate_v41x_legal(tmp_path, edge_mm=8.5)
    committed = json.loads((PHY_DIR / f"{PHY}.json").read_text())
    assert sheet["views"] == committed["views"]


def test_legal_phy_pins_on_m5_track_and_power_reachable():
    lef = (PHY_DIR / f"{PHY}.lef").read_text()
    w = float(re.search(r"SIZE ([0-9.]+) BY", lef).group(1))
    assert abs(w / 0.432 - round(w / 0.432)) < 1e-6          # width on the pack's joint grid
    xs = [float(x) for x in re.findall(r"LAYER M5 ;\n      RECT ([0-9.]+) ", lef)]
    assert len(xs) == 22237
    # pin centre = x + 0.012 must sit on the M5 track (offset 0.012, pitch 0.048): x multiple of 0.048
    assert all(round(x * 1000) % 48 == 0 for x in xs)
    obs = lef.split("  OBS")[1]
    assert "LAYER M5" not in obs and "LAYER M4" in obs          # M5 open over the M4 power straps
    power = re.search(r"PIN VDD.*?END VDD", lef, re.S).group(0)
    assert "LAYER M4" in power


def test_legal_phy_fits_the_edge_and_windows():
    s = json.loads((PHY_DIR / f"{PHY}.json").read_text())
    assert s["footprint"]["edge_basis"]["value_mm"] == 8.5
    assert 8.0 <= s["footprint"]["width_um"] / 1000 <= 9.0
    k0, k1 = s["pins"]["k_pins_in_window_um"]
    w0, w1 = s["pins"]["w_pins_in_window_um"]
    assert k1 < w0 and w1 < s["pins"]["pseudo_channel_window_um"]


def test_v1_views_kept_unchanged():
    # the defective v1 view is history; the generator must still reproduce it byte for byte
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        sheet = hbm_phy_gen.generate_v41x(Path(d), k_aw=30)
    committed = json.loads((ROOT / "physical/asap7_memory_macros/ot_hbm3e_phy_v41x_aw30/"
                                   "ot_hbm3e_phy_v41x_aw30.json").read_text())
    assert sheet["views"] == committed["views"]


def test_power_abstract_lef_pins_and_obs():
    import die_pdn
    t = die_pdn.block_lef("x", 514.08, 2246.4, "t")
    assert t.count("LAYER M8 ;") == 2 and "LAYER M7 ;" in t and "LAYER M8 ;\n      RECT 0 0" not in t
    ys = [float(y) for y in re.findall(r"RECT 0.500 ([0-9.]+) ", t)]
    assert len(ys) > 200 and min(ys) > 0 and max(ys) < 2246.4


def test_switch_ring_arithmetic():
    import die_pdn
    r = die_pdn.switch_ring(16 * 0.239, 2 * (514.08 + 2246.4), 5.4)
    assert r["cells"] > 0 and 0 < r["drop_mv"] < 100


@pytest.mark.skipif(shutil.which("iverilog") is None, reason="iverilog not installed")
def test_pg_ctrl_bench(tmp_path):
    out = tmp_path / "tb"
    subprocess.run(["iverilog", "-g2012", "-o", str(out), str(ROOT / "rtl/chip/ot_chip_v41_pg_ctrl.sv"),
                    str(ROOT / "rtl/test/tb_chip_v41_pg_ctrl.sv")], check=True, capture_output=True)
    r = subprocess.run(["vvp", "-n", str(out)], check=True, capture_output=True, text=True, timeout=600)
    assert "PASS" in r.stdout.splitlines()[-1]
    m = re.search(r"wake_cycles=(\d+)", r.stdout)
    assert int(m.group(1)) * 0.92 < 1000.0            # staggered wake inside the model's 1 us


def test_committed_records_are_consistent():
    d = ROOT / "results/physical_abi3/asap7/chip/v41_w18"
    if not d.exists():
        pytest.skip("records not committed yet")
    fp = d / "die_floorplan.json"
    if fp.exists():
        r = json.loads(fp.read_text())
        assert r["capacity"]["closes"] and r["capacity"]["pairs_needed"] == 7102
