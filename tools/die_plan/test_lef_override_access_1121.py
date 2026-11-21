"""FLOW-OBS-GCELL-R2 11-21 (fleet pin-access scan, DRT-0073): access-window / pin-clear corrections of qkd_kvs_ctl and
ot_s81hd_he_epc.  Each corrected LEF matches its map row, keeps every PIN section, SIZE and the untouched OBS layers of the
plan LEF (abstract_detail.check), and its receipt records a passing TritonRoute probe."""
import hashlib
import json
from pathlib import Path

import pytest

import abstract_detail as AD
import lef_override as LO

ROOT = Path(__file__).resolve().parents[2]
CASES = [("qkd_kvs_ctl.lef", None, ["M9"]),
         ("ot_s81hd_he_epc.lef", "physical/die_plan/s81_head/plan_of_record/l48hp1_h2/views/ot_s81hd_he_epc.lef", ["M7"])]


@pytest.mark.parametrize("name,base_rel,layers", CASES)
def test_row_matches_file_and_receipt(name, base_rel, layers):
    row = json.loads((LO.DIR / "map.json").read_text())[name]
    b = (LO.DIR / name).read_bytes()
    assert hashlib.sha256(b).hexdigest() == row["sha256"] and hashlib.md5(b).hexdigest() == row["md5"]
    rec = json.loads((LO.DIR / name.replace(".lef", ".splice.json")).read_text())
    assert rec["base_sha256"] == row["base_sha256"] and rec["out_sha256"] == row["sha256"]
    assert rec["probe"]["verdict"] == "PASS" and rec["detail_pins_equal_base"]
    assert rec["layers_detailed"] == layers


@pytest.mark.parametrize("name,base_rel,layers", CASES)
def test_only_obs_of_replaced_layers_or_windows_changed(name, base_rel, layers):
    base = ROOT / base_rel if base_rel else None
    if base is None or not base.is_file():
        pytest.skip("plan view not in this checkout")
    row = json.loads((LO.DIR / "map.json").read_text())[name]
    assert hashlib.sha256(base.read_bytes()).hexdigest() == row["base_sha256"]
    old = base.read_text().splitlines(keepends=True)
    new = (LO.DIR / name).read_text().splitlines(keepends=True)
    assert AD._pin_section(old) == AD._pin_section(new)
    ok, probs = AD.check(old, new, layers, None)
    assert ok, probs
