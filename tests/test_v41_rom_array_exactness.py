"""W10 item 2: the V4.1 ROM element array is exact against golden on real checkpoint slices."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REC = ROOT / "results/uarch/v41_rom_array_exactness.json"


def test_every_row_exact_at_n_2_4_8():
    rec = json.loads(REC.read_text())
    assert rec["verdict"] == "PASS"
    ns = {c["N"] for c in rec["cases"]}
    assert {2, 4, 8} <= ns
    fams = {c["case"].split("_")[0] for c in rec["cases"]}
    assert {"fp8", "fp4", "bf16", "mixed"} <= fams
    for c in rec["cases"]:
        assert c["rows_out"] == c["rows"] == c["fp32_exact"] == c["bf16_exact"], c["case"]
        assert not c["fault"], c["case"]
        # cycles = the bank map's stream-round issue time + the measured fill
        assert c["cycles_last_row"] == c["t_phase_pred"] + c["fill"]
        assert c["t_rounds_scheduled"] == c["t_phase_pred"], c["case"]


def test_record_is_source_current():
    rec = json.loads(REC.read_text())
    for p, h in rec["source_sha256"].items():
        assert hashlib.sha256((ROOT / p).read_bytes()).hexdigest() == h, p
