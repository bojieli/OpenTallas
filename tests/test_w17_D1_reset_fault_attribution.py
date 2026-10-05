import json
from pathlib import Path
import pytest
from tools.w17_D1_reset_fault_attribution import (
    priming_timeline, first_prefetch, display_time_ps, admission,
    drop_kv_ok_witness, verify_pins,
)
ROOT = Path(__file__).resolve().parents[1]
E = ROOT / "results/uarch/w17_D1_reset_fault_attribution_20261002"


def test_original_reset_phase_loses_only_first_row():
    result = priming_timeline()
    assert len(result["handshakes"]) == 128
    assert result["lost_rows"] == [0]
    assert result["handshakes"][0] == {"row": 0, "time_ps": 5500,
                                        "consumer_out_of_reset": False}
    assert result["handshakes"][1]["consumer_out_of_reset"] is True


def test_one_cycle_later_negative_control_changes_failure():
    result = priming_timeline(1)
    assert result["lost_rows"] == []
    assert len(result["valid_rows"]) == 128
    assert first_prefetch(result["valid_rows"])["predicted_die_fault_mask"] == 0


def test_first_prefetch_source_fault_matches_failure_window_only_as_prediction():
    result = first_prefetch(priming_timeline()["valid_rows"])
    assert result["prefetch_edge_ps"] == 140500
    assert result["sticky_fault_edge_ps"] == 141500
    assert result["predicted_pf_fault_code"] == 1
    assert result["predicted_die_fault_mask"] == 0x40
    assert result["mask_observed"] is False
    assert result["service_bound"] == "BOUND_MISSING"
    assert display_time_ps(result["sticky_fault_edge_ps"] + 1) == 142000


def gates():
    return dict(waited=True, q_gate=True, m0_gate=True, me_ready=True,
                kv_ok=False, kvd_v=False, win_idle=True)


def test_true_same_phase_predicate_mutant():
    packet = gates()
    assert not admission(packet)
    assert drop_kv_ok_witness(packet, packet)
    assert admission(dict(packet, kv_ok=True))


def test_descriptor_pulse_mixed_phase_marker_rejected():
    with pytest.raises(ValueError, match="mixed"):
        drop_kv_ok_witness(dict(gates(), kvd_v=True), gates())


@pytest.mark.parametrize("field", ["waited", "q_gate", "m0_gate", "me_ready", "win_idle"])
def test_other_disabled_gates_prevent_mutant_credit(field):
    packet = dict(gates(), **{field: False})
    assert not drop_kv_ok_witness(packet, packet)


@pytest.mark.parametrize("bad", [True, 1.5, -1])
def test_phase_parameter_rejects_invalid_types(bad):
    with pytest.raises(ValueError):
        priming_timeline(bad)


def test_source_pins_and_record_replay():
    record = json.loads((E / "assessment.json").read_text())
    verify_pins(ROOT, record["source_SHA256"])
    assert record["phase_model"] == priming_timeline()
    assert record["prefetch_model"] == first_prefetch(priming_timeline()["valid_rows"])
    assert record["actual_fault_masks"] is None
    assert record["original_PC24_cause"] == "UNOBSERVED"


def test_modified_source_is_rejected(tmp_path):
    (tmp_path / "source.sv").write_text("changed")
    with pytest.raises(ValueError, match="pin mismatch"):
        verify_pins(tmp_path, {"source.sv": "0" * 64})


def test_debugger_plan_is_offline_only_and_exact_existing_binary():
    plan = json.loads((E / "debugger_plan.json").read_text())
    assert plan["status"] == "PREPARED_NOT_ADMITTED_NOT_EXECUTED"
    assert plan["binary_SHA256"] == "b7d605fa323444f14fbc60b8912b9fd894f257f36b137f78fbab882407c60153"
    assert plan["simulator_runs_launched"] == 0
    assert not plan["debugger"]["inferior_started"]
    assert plan["debugger"]["offline_exit"] == 0
    script = (E / "capture_masks.gdb").read_text()
    assert not any(line.strip().split()[0] in ("run", "start", "starti", "attach")
                   for line in script.splitlines() if line.strip() and not line.startswith("#"))
    assert "+0x91d" in script
    for field in plan["debugger"]["fields"].values():
        assert field["offset_hex"] in script
    assert plan["cost_basis"]["sample_is_peak"] is False
    for limit in ("wall_limit", "CPU_time_limit", "per_file_limit", "per_process_AS_limit"):
        assert plan["capacity_proposal"][limit] is None


def test_all_additive_evidence_hashes():
    pins = json.loads((E / "artifact_SHA256.json").read_text())
    verify_pins(E, pins)
    disassembly = (E / "actor_disassembly.txt").read_text()
    for fragment in ("0x28021", "0x5f0fc", "0x27fe2", "11251:", "112e3:"):
        assert fragment in disassembly
