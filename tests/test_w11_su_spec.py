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


@pytest.mark.parametrize("lv,ok", [(7, True), (8, False)])
def test_reducer_levels_above_7_fail_elaboration(lv, ok):
    """l_in is 3 bits: LV > 7 must be refused at elaboration (not clamped), even under -Wno-fatal."""
    import shutil
    import subprocess
    sys_path = str(ROOT / "tools")
    import sys
    if sys_path not in sys.path:
        sys.path.insert(0, sys_path)
    import rtl_hdc_v41x_vec_campaign as C
    if not shutil.which(C.VERILATOR) and not Path(C.VERILATOR).exists():
        pytest.skip("no verilator")
    srcs = [*map(str, C.LIB), *map(str, C.RTL), str(ROOT / "rtl/hdc/v41x/ot_hdc_v41x_su_adapt.sv")]
    r = subprocess.run([C.VERILATOR, "--lint-only", "-Wno-fatal", "-Wno-lint", "-Wno-style",
                        "--top-module", "ot_hdc_v41x_su_adapt", f"-GLV={lv}", *srcs], capture_output=True, text=True)
    assert (r.returncode == 0) == ok, r.stderr[-2000:]
    if not ok:
        assert "LV_must_be_1_to_7" in r.stderr
