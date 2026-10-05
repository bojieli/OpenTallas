"""Meaningful scope/integrity checks for the isolated sequential gate generator."""
import importlib.util
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("fastfp_gate", ROOT / "tools/w11_fastfp_prefix_sequential_gate.py")
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)


def test_generated_candidate_changes_only_exact_ksa_body_and_names():
    raw = (ROOT / gate.SOURCE).read_bytes()
    assert gate.digest(raw) == gate.SOURCE_SHA
    source = raw.decode()
    candidate = gate.generated(source)
    restored = re.sub(r"\bgate_sim_(ot_hdc_\w+)\b", r"\1", candidate)
    assert restored == gate.substitute_ksa(source)
    # Preserve the entire sequential datapath and wrappers byte for byte.
    after_ksa = source.index("endmodule", source.index("module ot_hdc_ksa "))
    candidate_after_ksa = restored.index("endmodule", restored.index("module ot_hdc_ksa "))
    assert restored[candidate_after_ksa:] == source[after_ksa:]
    reference = gate.generated(source, "reference")
    assert re.sub(r"\bgate_ref_(ot_hdc_\w+)\b", r"\1", reference) == source


def test_required_mutants_are_specific_and_disjoint_from_good_candidate():
    source = (ROOT / gate.SOURCE).read_text()
    good = gate.generated(source)
    carry = gate.generated(source, "carry_mutant")
    reset = gate.generated(source, "reset_mutant")
    assert carry != good and reset != good and carry != reset
    assert "{(W+1){1'b0}}" in carry
    assert reset.count("if (!rst_n) begin y <= 32'd1;") == 2
    assert "if (!rst_n) begin y <= 32'd1;" not in good


def test_committed_record_requires_every_sample_and_both_negative_controls():
    evidence = ROOT / "results/rtl/w11_fastfp_prefix_sequential_gate_20261001/record.json"
    if not evidence.exists():
        import pytest
        pytest.skip("record has not yet been packaged")
    record = json.loads(evidence.read_text())
    assert record["status"] == "PASS_BOUNDED_DIRECTED_RANDOM_SEQUENTIAL_GATE"
    assert record["workers"] <= 2
    assert record["combinational_formal_proof"]["required_separately"]
    assert not record["sequential_formal_proof"] and not record["hardware_credit"]
    for path, sha in record["gate_sources"].items():
        assert gate.digest((ROOT / path).read_bytes()) == sha
    for entry in record["runs"]:
        assert entry["build"]["returncode"] == 0
        assert gate.digest((ROOT / entry["build"]["retained_log"]).read_bytes()) == entry["build"]["log_sha256"]
        for name, sha in entry["retained_generated_sources"].items():
            assert gate.digest((ROOT / name).read_bytes()) == sha
        for simulation in entry["simulations"]:
            raw = (ROOT / simulation["retained_log"]).read_bytes()
            assert gate.digest(raw) == simulation["log_sha256"]
            logged = [json.loads(line[7:]) for line in raw.decode().splitlines() if line.startswith("RESULT ")]
            assert logged == [simulation["result"]]
            result = simulation["result"]
            if entry["variant"] == "candidate":
                assert simulation["returncode"] == 0 and result["status"] == "PASS"
                assert result["first_mismatch"] is None
                assert result["checked_samples"] == result["clock_cycles"] + result["asynchronous_reset_assertions"]
                assert result["clock_cycles"] == result["valid_output_cycles"] + result["bubble_or_reset_cycles"]
                assert result["asynchronous_reset_assertions"] > 0 and result["reset_held_clock_edges"] > 0
                assert all(n > 0 for n in result["add_err_0_1_2"] + result["mul_err_0_1_2"])
            else:
                assert simulation["returncode"] == 1 and result["status"] == "FAIL"
                assert result["first_mismatch"] is not None
    assert {entry["variant"] for entry in record["runs"]} == {"candidate", "carry_mutant", "reset_mutant"}
    assert [s["result"]["seed"] for s in record["runs"][0]["simulations"]] == list(gate.SEEDS)
