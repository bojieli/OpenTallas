import json
from pathlib import Path
import pytest
from tools.w17_D1_parent_fault_evidence import classify
from tools.w17_D1_reset_fault_attribution import verify_pins
ROOT = Path(__file__).resolve().parents[1]
E = ROOT / "results/uarch/w17_D1_parent_bound_fault_attribution_20261002"
B = ROOT / "results/uarch/w17_D1_disjoint_native_actual_runtime_20261002_r1"


def inputs():
    return [json.loads((E / "authoritative_parent_review.json").read_text()),
            json.loads((B / "runtime/receipt.json").read_text()),
            (B / "runtime/runtime.log").read_text(),
            (E / "generated_fatal_branch.txt").read_text(),
            (B / "inputs/source_observer.sv").read_text()]


def test_actual_failure_proves_union_but_never_invents_masks():
    value = classify(*inputs())
    assert value["union_nonzero"]
    assert not value["actual_masks_available"]
    assert [value[n] for n in ("fault_r", "dbg_fs", "violations")] == [None]*3
    assert not any(value["callbacks"].values())
    assert value["original_PC24_cause"] == "UNOBSERVED"
    assert not value["fulltoken"]


@pytest.mark.parametrize("field,bad", [("runtime_exit",0), ("objects_verified",3828),
                                     ("object_intersection",1),
                                     ("actual_binary_archive_program_hashes_verified",False)])
def test_invalid_authority_cannot_qualify_failure(field,bad):
    data = inputs()
    data[0][field] = bad
    with pytest.raises(ValueError):
        classify(*data)


def test_generic_fatal_cannot_be_attributed_as_this_union():
    data=inputs();data[2]=data[2].replace("D1_SOURCE_OR_LEDGER_FAULT", "OTHER_FAILURE")
    with pytest.raises(ValueError): classify(*data)


@pytest.mark.parametrize("operand",["fault_r", "dbg_fs", "violations"])
def test_missing_binary_operand_blocks_oracle(operand):
    data=inputs();data[3]=data[3].replace(operand,"missing_operand")
    with pytest.raises(ValueError): classify(*data)


def test_observer_mirror_is_not_independent_source_fault_mask():
    data=inputs();data[4]=data[4].replace("if(fault)violations[0]<=1", "if(fault)violations[7]<=1")
    with pytest.raises(ValueError): classify(*data)


def test_callback_marker_changes_event_evidence_not_mask_claim():
    data=inputs();data[2]+="\nD1_REAL_ACCEPT time=140000 address=1 tag=0 write=0\n"
    value=classify(*data)
    assert value["callbacks"]["D1_REAL_ACCEPT"] == 1
    assert value["fault_r"] is None


def test_parent_bound_record_keeps_capture_and_I66_separate():
    value=json.loads((E / "diagnosis.json").read_text())
    assert value["observed"]["fatal_union_nonzero"]
    assert value["observed"]["die_fault_mask"] is None
    assert value["source_attribution"]["predicted_die_fault_mask"] == 0x40
    assert value["scope"]["I66_evidence_used"] is False
    assert value["next_experiment"]["status"] == "PREPARED_NOT_EXECUTED"
    assert value["generated_fatal_branch"]["matches_original_generated_inventory"]
    verify_pins(E, json.loads((E / "artifact_SHA256.json").read_text()))
