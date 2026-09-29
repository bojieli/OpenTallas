"""The registered four-bank gate must pin the current RTL and HBM bench."""

import json

from tools.rtl_chip_v41x_window_stage4 import ROOT, SOURCES


def test_record_is_current():
    import hashlib

    record = json.loads((ROOT / "results/rtl/chip_v41x_window_stage4.json").read_text())
    assert record["pass"] is True
    assert record["peak_rows_per_cycle"] == 4
    assert record["integrated_simulation_returncode"] == 0
    assert "poison=2" in record["integrated_stdout"]
    assert record["source_sha256"] == {
        str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in SOURCES
    }
