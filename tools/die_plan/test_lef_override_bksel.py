"""S81-BKSEL-R6 11-21 (DRT-0073 on bk_sel__t2: dsdv_bksel_c ck[0] / dsdv_bksel_q ck, the only 0.048-um M5 pins of the signed views,
no access point under the blanket OBS).  The corrections narrow only that PORT rect to the 0.024-um on-track centre of the same metal."""
import hashlib
import json
import re
from pathlib import Path

import pytest

import lef_override as LO

ROOT = Path(__file__).resolve().parents[2]
CASES = [("dsdv_bksel_c.lef", "ck[0]", "physical/die_plan/s81/cores/views/bksel_c_qrx_1117/dsdv_bksel_c/dsdv_bksel_c.lef"),
         ("dsdv_bksel_q.lef", "ck", "physical/die_plan/s81/cores/views/bksel_eco3_1117/dsdv_bksel_q/dsdv_bksel_q.lef")]


def _m5_rect(text, pin):
    m = re.search(r"  PIN " + re.escape(pin) + r"\n.*?LAYER M5 ;\n\s*RECT\s+([\d.]+) ([\d.]+) ([\d.]+) ([\d.]+) ;", text, re.S)
    assert m, pin
    return tuple(map(float, m.groups()))


@pytest.mark.parametrize("name,pin,base_rel", CASES)
def test_corrected_bksel_lef_matches_map_and_narrows_only_the_clock_pin(name, pin, base_rel):
    new = LO.DIR / name
    row = json.loads((LO.DIR / "map.json").read_text())[name]
    b = new.read_bytes()
    assert hashlib.sha256(b).hexdigest() == row["sha256"] and hashlib.md5(b).hexdigest() == row["md5"]
    x0, y0, x1, y1 = _m5_rect(new.read_text(), pin)
    assert abs((x1 - x0) - 0.024) < 1e-9
    assert round(((x0 + x1) / 2 * 1000) % 12) == 0     # centre on the 0.024-um half-pitch grid of the 0.048 M5 tracks
    base = ROOT / base_rel
    if not base.is_file():
        pytest.skip("plan view not in this checkout")
    assert hashlib.sha256(base.read_bytes()).hexdigest() == row["base_sha256"]
    old, cur = base.read_text().splitlines(), new.read_text().splitlines()
    assert len(old) == len(cur)
    diff = [(a, c) for a, c in zip(old, cur) if a != c]
    assert len(diff) == 1                               # only the clock PORT rect changed
    ox0, oy0, ox1, oy1 = _m5_rect(base.read_text(), pin)
    assert abs((ox1 - ox0) - 0.048) < 1e-9 and (oy0, oy1) == (y0, y1)
    assert ox0 < x0 < x1 < ox1                          # a subset of the signed metal
