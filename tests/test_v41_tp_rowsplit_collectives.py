"""Keep V4.1 row-split stage timing bound to the exercised RTL sources."""

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _check_pins(record):
    for path, digest in record["source_sha256"].items():
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == digest, path


def test_base_engine_width_matched_gather_record():
    rec = json.loads((ROOT / "results/rtl/v41_tp_rowsplit_collectives.json").read_text())
    assert rec["schema"] == "v41_tp_rowsplit_collectives_v1"
    _check_pins(rec)
    assert rec["patterns"]["act"]["words"] == 266
    assert rec["patterns"]["y"]["words"] == 80
    assert len(rec["cases"]) == 9
    assert all(case["passed"] and case["mismatches"] == 0 and not any(case["faults"])
               for case in rec["cases"])
    assert rec["summary"]["act"]["measured_tail_cycles"] > rec["patterns"]["act"]["model_exposed"]
    assert rec["summary"]["y"]["measured_tail_cycles"] > rec["patterns"]["y"]["model_exposed"]
    wide_queue = next(case for case in rec["cases"] if case["case"] == "rowsplit_act_d64_q512")
    assert wide_queue["producer_stall_cycles"] == 0


def test_adopted_die_engine_gather_record():
    rec = json.loads((ROOT / "results/rtl/v41_tp_rowsplit_die_collectives.json").read_text())
    assert rec["schema"] == "v41_tp_rowsplit_die_collectives_v1"
    _check_pins(rec)
    assert rec["die_contract"]["flit_bytes"] == 64
    assert rec["die_contract"]["CL_DEPTH"] == 16
    assert rec["die_contract"]["DMA_VM_words_per_cycle"] == 1
    assert len(rec["cases"]) == 4
    assert all(case["passed"] and case["mismatches"] == 0 and not any(case["faults"])
               for case in rec["cases"])
    for pattern in ("act", "y"):
        adopted = next(case for case in rec["cases"] if case["pattern"] == pattern
                       and case["order"] == "blocked" and case["rx_depth_words"] == 16)
        assert rec["summary"][pattern]["measured_tail_cycles"] == adopted["exposed_tail_cycles"]
        assert adopted["exposed_tail_cycles"] > rec["patterns"][pattern]["model_exposed"]


def test_measured_ar_reprice_keeps_mtp_open():
    rec = json.loads((ROOT / "results/arch/v41_tp_rowsplit_measured_reprice.json").read_text())
    assert rec["schema"] == "v41_tp_rowsplit_measured_reprice_v1"
    _check_pins(rec)
    bench = json.loads((ROOT / "results/rtl/v41_tp_rowsplit_die_collectives.json").read_text())
    assert rec["measured_tail_cycles"] == {
        pattern: bench["summary"][pattern]["measured_tail_cycles"] for pattern in ("act", "y")
    }
    assert rec["measured_tail_cycles"]["act"] >= 4 * 266
    for point in rec["points"].values():
        ar = point["ar"]
        assert ar["row_split_measured_gathers"] < ar["row_split_old_tail"]
        assert ar["row_split_old_tail"] < ar["old_ksplit_model"]
        assert "uncalibrated" in point["mtp"]["status"]
