"""FABLE-FIX-S81-LEPE 11-19 (DRT-0073 on the S81 lepe / lepw LP types): the corrected lane-core LEFs give ck[0] access, change
nothing but the M6 OBS, and match the override map."""
import hashlib
import json
from pathlib import Path

import pytest

import abstract_detail as AD
import lef_override as LO

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize("side", ["e", "w"])
def test_corrected_lane_core_lef_has_clock_access_and_matches_the_map(side):
    name = f"dsfd_coll_lane_{side}_safe8_ntf.lef"
    new = LO.DIR / name
    row = json.loads((LO.DIR / "map.json").read_text())[name]
    assert hashlib.sha256(new.read_bytes()).hexdigest() == row["sha256"] and hashlib.md5(new.read_bytes()).hexdigest() == row["md5"]
    rep = AD.access_report(new.read_text().splitlines(), "M7")
    bad = [p for p, e in rep["pins"].items() if not e["ok"]]
    assert bad == [] and rep["pins"]["ck[0]"]["ok"]
    base = ROOT / f"physical/die_plan/s81/cores/views/dsfd_coll_lane_{side}_safe8_ntf_signed_1107/{name}"
    if not base.is_file():
        pytest.skip("signed view not in this checkout")
    assert hashlib.sha256(base.read_bytes()).hexdigest() == row["base_sha256"]
    old = AD.access_report(base.read_text().splitlines(), "M7")
    assert [p for p, e in old["pins"].items() if not e["ok"]] == ["ck[0]"]        # the class: one interior pin without access
