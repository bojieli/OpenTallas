"""C7: the real-core collective stage against the matched stub bench (results/arch/v41_c7_realcore_vs_stub.json)."""

import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("v41_c7_realcore_vs_stub", ROOT / "tools/v41_c7_realcore_vs_stub.py")
tool = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(tool)
REC = json.loads((ROOT / "results/arch/v41_c7_realcore_vs_stub.json").read_text())


def test_record_rederives_from_committed_inputs():
    for path, digest in REC["inputs"].items():
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == digest, path
    real = tool.real_core()
    model = tool.model_side()
    assert real == REC["real_core"]
    assert model == REC["model"]
    assert tool.compare(real, REC["matched_stub"], model) == REC["comparison"]


def test_real_core_stage_is_exact_and_saturated_at_both_link_delays():
    for lat in ("142", "228"):
        r = REC["real_core"][lat]
        assert r["status"] == "pass" and r["mismatches"] == 0
        assert r["words"] == 8 and r["rx_depth"] == 2 and r["tx_queue"] == 2
        assert set(r["fifo_qmax"].values()) == {2}
        assert min(r["producer_stall_cycles"].values()) > 0


def test_matched_stub_has_the_same_collective_timing_on_the_producer_package():
    c = REC["comparison"]
    assert all(REC["matched_stub"][lat]["passed"] for lat in ("142", "228"))
    assert c["collective_wave_period_identical"]
    assert all(v["wave_period_equals_2lat_plus_2"] for v in c["per_lat"].values())
    assert c["local_rank_offset_cycles"] == [0]
    assert len(c["remote_rank_offset_cycles"]) == 1          # a constant offset, not a growing tail


def test_sensitivity_is_reported_not_applied():
    lanes = json.loads((ROOT / "results/arch/v41_lanes.json").read_text())["design_point"]
    cases = REC["comparison"]["sensitivity_upper_bound"]["cases"]
    for case in cases.values():
        for ctx, row in lanes.items():
            assert case[ctx]["ar_now"] == round(row["ar"])
            assert case[ctx]["ar_if_unpriced"] < case[ctx]["ar_now"]
