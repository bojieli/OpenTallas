"""LEC-R2 11-26: an EQUIVALENT verdict must not be vacuous on primary outputs (COORD safety fix)."""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import lec  # noqa: E402
import pytest  # noqa: E402


def test_register_only_differences_do_not_trip():
    rec = {}
    lec.output_compare_gate(["ff:u_dut.a", "ff:u_dut.b"], ["ff:__gate_anon_1"], rec)
    assert "output_compare_gaps" not in rec


def test_gate_only_outputs_make_the_run_unproven_with_the_full_list():
    rec = {}
    po = [f"po:q[{i}]" for i in range(259)]
    with pytest.raises(lec.Unproven) as e:
        lec.output_compare_gate([], ["ff:__gate_anon_1"] + po, rec)
    assert "259 gate-only" in str(e.value)
    assert rec["output_compare_gaps"]["gate_only"]["n"] == 259 and rec["output_compare_gaps"]["gate_only"]["points"] == po
    assert rec["output_compare_gaps"]["gold_only"]["n"] == 0


def test_gold_only_outputs_make_the_run_unproven():
    rec = {}
    with pytest.raises(lec.Unproven):
        lec.output_compare_gate(["po:fault", "ff:u_dut.x"], [], rec)
    assert rec["output_compare_gaps"]["gold_only"]["points"] == ["po:fault"]
