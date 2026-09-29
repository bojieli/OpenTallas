"""W11 index-key reader rate record: pins, arithmetic and verdicts are consistent (fast)."""

import json
import math

from tools.w11_idx_reader_rate import (LEGACY_RECORD, OUT, ROOT, RUNS, SPEC,
                                       TARGET_SECTORS_PER_CYCLE, legacy_sectors,
                                       qs_sectors, sources)


def _record():
    return json.loads(OUT.read_text())


def test_record_pins_current_sources():
    rec = _record()
    assert rec["status"] == "pass"
    assert rec["sources_sha256"] == sources()


def test_every_case_is_exact_and_self_consistent():
    rec = _record()
    assert [c["name"] for c in rec["cases"]] == [r[0] for r in RUNS]
    for case in rec["cases"]:
        n = case["keys"]
        assert case["checked_keys"] == n
        want = (legacy_sectors(n) if case["layout"] == "legacy"
                else qs_sectors(n, case["parameters"]["OSTEP"]))
        assert case["sectors"] == want
        assert case["sectors_per_cycle"] == round(case["sectors"] / case["cycles"], 3)
        assert len(case["hbm_per_stack"]) == 4
        assert sum(s["hbm_reads"] for s in case["hbm_per_stack"]) == case["sectors"]


def test_legacy_reproduces_gate_and_after_meets_target():
    rec = _record()
    by = {c["name"]: c for c in rec["cases"]}
    gate = {c["keys"]: c["cycles"] for c in json.loads((ROOT / LEGACY_RECORD).read_text())["cases"]}
    for n in (65, 1040, 262144):
        assert by[f"legacy_n{n}"]["cycles"] == gate[n]
    spec = by["quarter_stack_n262144"]
    assert {k: spec["parameters"][k] for k in SPEC} == SPEC
    assert spec["parameters"]["CLK_PS"] == 967
    budget = math.ceil(legacy_sectors(262144) / TARGET_SECTORS_PER_CYCLE)
    assert rec["target"]["max_cycles_after_fill"] == budget
    long = by["quarter_stack_n1048576"]
    long_budget = math.ceil(long["sectors"] / TARGET_SECTORS_PER_CYCLE)
    assert rec["summary"]["meets_target"] == (
        spec["cycles"] - spec["first_output_cycle"] <= budget and
        long["cycles"] - long["first_output_cycle"] <= long_budget)
    assert rec["summary"]["meets_target"]
    assert spec["cycles"] < by["legacy_n262144"]["cycles"]
    assert rec["element"]["count_per_die"] == 128
    assert rec["element"]["rob_bits"] == SPEC["WB"] * 1024
