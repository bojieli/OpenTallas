"""W11: the three vector-memory options' pricing record (tools/w11_vm_options.py, results/uarch/w11_vm_options.json).
Fast: reads the committed record only."""
import hashlib
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
REC = ROOT / "results/uarch/w11_vm_options.json"


@pytest.fixture(scope="module")
def rec():
    return json.loads(REC.read_text())


def test_source_pinned(rec):
    assert len(rec["source_commit"]) == 40
    for name, digest in rec["source_sha256"].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest, name


def test_every_option_priced(rec):
    assert set(rec["options"]) >= {"H", "H_align_only", "C", "C_rotate", "A"}
    flat = rec["rates"]["flat_vm_reference"]
    for k, o in rec["options"].items():
        r = o["rates"]
        # every option adds latency to a flat VM beside the SU: none beats it, and the verify pass still pays
        assert 0 < r["ar_tokens_s"] < flat["ar_tokens_s"], k
        assert r["mtp_tokens_s"] > r["ar_tokens_s"], k
        assert o["sram"]["macros"] == 1536
        for c in ("x_gather", "ret_scatter", "coll_write", "su_results"):
            assert o["clients"][c] >= 1, (k, c)


def test_h_measurement_is_the_vehicle(rec):
    h = rec["h_measurement"]
    assert h["meta"]["stream_ops"] == 2649 and h["ops"] > 2000
    for c, v in h["remote_share_h"].items():
        assert 0 <= v <= h["remote_share_as_laid"][c] + 1e-9 or c in ("E",), c
    assert h["vector_ratio"] >= 1.0
