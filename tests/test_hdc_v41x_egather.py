"""Per-bank Engram gather (rtl/hdc/v41x/ot_hdc_v41x_egather.sv): the bench's expected words, the committed
campaign against the spec, and the physical records of the slice and the assembler."""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import hdc_golden_v41 as G  # noqa: E402
import hdc_v41_engram_shipped as ES  # noqa: E402
import rtl_hdc_v41x_egather_campaign as C  # noqa: E402
from record_currency_support import assert_current_or_marked_stale  # noqa: E402

PHYS = ROOT / "results/physical_abi3/asap7/hdc/v41x"


def test_words_hold_lane_zero_lowest():
    rows = np.arange(64, dtype=np.int64).reshape(1, 64)
    w = C.words_of(rows, 2)
    assert len(w) == 2 and len(w[0]) == 128
    assert int(w[0], 16) & 0xFFFF == 0 and int(w[1], 16) >> (16 * 31) == 63


def test_decode_expression_is_the_golden_one():
    codes = np.arange(256, dtype=np.int64)[None, :].repeat(4, 0)
    scales = np.array([0, 1, 127, 255])
    got = ES.decode_rows(codes, scales)
    with np.errstate(all="ignore"):
        want = G.to_bf16((G.E4M3[codes] * np.exp2(scales - 127.0)[:, None]).astype(G.F))
    assert np.array_equal(got, (G.bits(want) >> 16).astype(np.int64))


def test_committed_record_meets_the_spec():
    rec = json.loads(C.OUT.read_text())
    assert rec["status"] == "pass"
    for cfg in rec["runs"].values():
        for run in cfg.values():
            assert run["pass"] and run["word_mismatches"] == 0 and run["faults"] == 0
    assert rec["spec"]["bandwidth_met"]
    assert rec["spec"]["measured_bytes_per_cycle"] >= rec["spec"]["required_bytes_per_cycle"]
    assert rec["vectors"]["reduced"]["golden_rows_recorded_and_equal"] > 0
    assert all(m["caught"] for m in rec["mutations"])
    assert rec["io_pins"]["slice"]["total"] < 1000 and rec["io_pins"]["asm"]["total"] < 1000
    assert_current_or_marked_stale(rec, rec["input_sha256"], C.OUT.name)


def test_physical_records_route_the_committed_sources():
    for top in ("ot_hdc_v41x_egather_slice", "ot_hdc_v41x_egather_asm"):
        body = json.loads((PHYS / top / "physical.json").read_text())
        assert body["design"]["top"] == top
        for src in body["design"]["sources"]:
            assert hashlib.sha256((ROOT / src["path"]).read_bytes()).hexdigest() == src["sha256"], src["path"]
