"""W11: the V4.1 stream unit's softmax chain at the spec width N = 1,024 / M = 256 (tools/w11_su_softmax_spec.py,
results/rtl/w11_su_spec.json).  Fast: reads the committed record only."""
import hashlib
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
REC = ROOT / "results/rtl/w11_su_spec.json"


@pytest.fixture(scope="module")
def rec():
    return json.loads(REC.read_text())


def test_record_is_source_pinned(rec):
    assert len(rec["git_head"]) == 40
    assert rec["input_sha256"]
    for name, digest in rec["input_sha256"].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest, name


def test_every_case_is_bit_exact(rec):
    assert rec["pass_"]
    for cfg in ("N16_M8", "N1024_M256"):
        cases = rec["configs"][cfg]["cases"]
        assert set(cases) == {"T128", "T640"}
        for variants in cases.values():
            assert set(variants) == {"serial_adapt", "serial_vec", "chained"}
            for r in variants.values():
                assert r["completed"] and r["whole_vm_mismatches"] == 0
                assert r["faults"] == 0 and r["order_faults"] == 0
                assert r.get("schedule_reference_vm_mismatches", 0) == 0


def test_n16_reproduces_the_committed_3280(rec):
    """The calibration case: the same bench and fixture as results/rtl/v41x_su_softmax.json."""
    committed = json.loads((ROOT / "results/rtl/v41x_su_softmax.json").read_text())
    ends = {c["tokens"]: c["end_cycle"][0] for c in committed["cases"]}
    for t in (128, 640):
        assert rec["configs"]["N16_M8"]["cases"][f"T{t}"]["serial_adapt"]["end_cycle"] == ends[t]


def test_spec_width_vector_issue_matches_the_model(rec):
    for v in rec["model_vector_check"].values():
        assert all(row["equal"] for row in v), v
    ops = rec["configs"]["N1024_M256"]["cases"]["T640"]["chained"]["ops"]
    assert [o["vectors"] for o in ops] == [16, 48, 1, 32]
    assert all(o["vectors"] == o["layout_vectors"] for o in ops)


def test_spec_width_is_faster_than_n16_and_chaining_never_slower(rec):
    for t in ("T128", "T640"):
        wide = rec["configs"]["N1024_M256"]["cases"][t]
        narrow = rec["configs"]["N16_M8"]["cases"][t]
        assert wide["serial_adapt"]["end_cycle"] < narrow["serial_adapt"]["end_cycle"]
        assert wide["chained"]["end_cycle"] <= wide["serial_vec"]["end_cycle"]


def test_port_widths(rec):
    p = rec["configs"]["N1024_M256"]["ports"]
    assert p["operand_read_streams"]["bits"] == 4 * 1024 * 32
    assert p["element_write"]["bits"] == 1024 * 32
    assert p["result_write"]["bits"] == 128 * 32
    assert p["vm_banks_256b"]["all_four_operand_streams"] == 512
