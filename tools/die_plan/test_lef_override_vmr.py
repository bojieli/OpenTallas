"""SONNET-FIX-QC 11-19 (DRT-0073 on slw_su_c / sle_su_c: qfd_dv_s8x_vmr interior M5 pins ck, ft_ck_i/o, ft_rst_i/o under a blanket M6 OBS)."""
import hashlib
import json
from pathlib import Path

import pytest

import abstract_detail as AD
import lef_override as LO

ROOT = Path(__file__).resolve().parents[2]
PINS = ["ck", "ft_ck_i", "ft_ck_o", "ft_rst_i", "ft_rst_o"]


def test_corrected_vmr_lef_gives_every_interior_pin_access_and_matches_the_map():
    name = "qfd_dv_s8x_vmr.lef"
    new = LO.DIR / name
    row = json.loads((LO.DIR / "map.json").read_text())[name]
    assert hashlib.sha256(new.read_bytes()).hexdigest() == row["sha256"] and hashlib.md5(new.read_bytes()).hexdigest() == row["md5"]
    rep = AD.access_report(new.read_text().splitlines(), "M7")
    assert [p for p, e in rep["pins"].items() if not e["ok"]] == []
    assert all(rep["pins"][p]["ok"] for p in PINS)
    base = ROOT / "physical/die_plan/qwen_compute/ft_physical_1106/vmr/qfd_dv_s8x_vmr.lef"
    if not base.is_file():
        pytest.skip("plan view not in this checkout")
    assert hashlib.sha256(base.read_bytes()).hexdigest() == row["base_sha256"]
    old = AD.access_report(base.read_text().splitlines(), "M7")
    assert sorted(p for p, e in old["pins"].items() if not e["ok"]) == sorted(PINS)    # the class: five interior pins without access
