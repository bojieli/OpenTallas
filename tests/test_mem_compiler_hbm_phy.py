"""Tests of the HBM3E PHY hard-macro abstract (tools/mem_compiler/hbm_phy_gen.py)."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools/mem_compiler"))

import asap7  # noqa: E402
import hbm_phy_gen  # noqa: E402

COMMITTED = ROOT / "physical/asap7_memory_macros/ot_hbm3e_phy"


def test_committed_views_match_generator(tmp_path):
    sheet = hbm_phy_gen.generate(tmp_path)
    committed = json.loads((COMMITTED / "ot_hbm3e_phy.json").read_text())
    assert sheet["views"] == committed["views"]


def test_footprint_is_the_technology_table_numbers():
    sheet = hbm_phy_gen.generate(None)
    area = asap7.technology()["hbm"]["hbm3e"]["phy_area_mm2_per_stack"]["value"]
    beach = asap7.technology()["hbm"]["hbm3e"]["stack_beachfront_mm"]["value"]
    f = sheet["footprint"]
    assert f["area_mm2"] == pytest.approx(area, rel=0.01)
    assert f["width_um"] == pytest.approx(beach * 1000, rel=0.001)
    assert f["area_basis"]["grade"] == "assumed"


def test_interface_is_one_hbm3_stack_and_pins_fit_the_core_edge():
    sheet = hbm_phy_gen.generate(None)
    i = sheet["interface"]["hbm3"]["value"]
    assert i["pseudo_channels"] * i["pseudo_channel_dq_bits"] == i["dq_bits"] == 1024
    c = sheet["interface"]["controller_side"]
    assert c["sector_bits"] == i["pseudo_channel_dq_bits"] * i["burst_length"]
    assert sheet["pins"]["fits_on_edge"]
    # request + per-pseudo-channel response ports of ot_hdc_hbm_model
    n = 2 + 1 + 1 + 1 + c["address_bits"] + c["len_bits"] + c["tag_bits"] + 256 + 32 * (2 + 16 + 4 + 256)
    assert sheet["pins"]["signal_pins"] == n


def test_lef_pins_on_top_edge_m5():
    lef = (COMMITTED / "ot_hbm3e_phy.lef").read_text()
    h = float(re.search(r"SIZE [0-9.]+ BY ([0-9.]+)", lef).group(1))
    rects = re.findall(r"LAYER M5 ;\n      RECT [0-9.]+ ([0-9.]+) [0-9.]+ ([0-9.]+) ;", lef)
    assert len(rects) > 9000
    assert all(abs(float(y2) - h) < 1e-6 for _, y2 in rects)


def test_blackbox_ports_match_the_hbm_model():
    bb = (COMMITTED / "ot_hbm3e_phy_bb.v").read_text()
    model = (ROOT / "rtl/hdc/kv/ot_hdc_hbm_model.sv").read_text()
    for port in ("req_v", "req_rdy", "req_we", "req_addr", "req_len", "req_tag", "req_wdata",
                 "rsp_v", "rsp_rdy", "rsp_tag", "rsp_beat", "rsp_data"):
        assert re.search(rf"\b{port}\b", bb) and re.search(rf"\b{port}\b", model), port
