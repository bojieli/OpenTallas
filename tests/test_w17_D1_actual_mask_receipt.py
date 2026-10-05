import copy
import json
from pathlib import Path
import pytest
from tools.w17_D1_actual_mask_receipt import verify_capture
from tools.w17_D1_reset_fault_attribution import verify_pins
ROOT=Path(__file__).resolve().parents[1]
E=ROOT/"results/uarch/w17_D1_actual_fatal_mask_capture_20261002_r1"


def inputs():
    return json.loads((E/"receipt.json").read_text()), (E/"gdb_runtime.log").read_text()


def test_actual_operand_masks_and_original_failure():
    receipt,log=inputs()
    out=verify_capture(receipt,log)
    assert out["actual_masks"] == {"fault_r":0x40,"dbg_fs":0,"violations":0}
    assert out["WINDOW_kv_fault_bit_observed"]
    assert not out["row0_invalid_directly_observed"]
    assert out["original_PC24_cause"] == "UNOBSERVED"


@pytest.mark.parametrize("field,value",[("inferior_exit_code",0),("GDB_exit_code",1),
 ("input_postcheck",False),("simulator_launches",2),("compiler_or_link_launches",1),
 ("runtime_qualification",True),("fulltoken",True)])
def test_false_qualification_and_wrong_execution_rejected(field,value):
    receipt,log=inputs();receipt[field]=value
    with pytest.raises(ValueError): verify_capture(receipt,log)


def test_missing_mask_cannot_be_replaced_by_source_prediction():
    receipt,log=inputs()
    log="\n".join(line for line in log.splitlines() if "D1_ACTUAL_FATAL_MASK" not in line)
    with pytest.raises(ValueError): verify_capture(receipt,log)


def test_repeated_capture_rejected():
    receipt,log=inputs()
    line=next(line for line in log.splitlines() if line.startswith("D1_ACTUAL_FATAL_MASK fault_r="))
    with pytest.raises(ValueError): verify_capture(receipt,log+"\n"+line)


def test_modified_input_postcheck_rejected():
    receipt,log=inputs();receipt["input_hashes_after"]=dict(receipt["input_hashes_after"],binary="0"*64)
    with pytest.raises(ValueError): verify_capture(receipt,log)


def test_mask_record_cannot_substitute_dbg_fault_or_ledger_fault():
    receipt,log=inputs();receipt["actual_masks"]["violations"]=1
    with pytest.raises(ValueError): verify_capture(receipt,log)


def test_capacity_reserves_and_no_restrictive_caps():
    receipt,_=inputs()
    assert receipt["CPU_affinity"]==[8]
    assert receipt["fresh_memory"]["MemAvailable"] >= sum(receipt[k] for k in
        ("D1_capacity_reservation_bytes","host_reserve_bytes","recovery_reserve_bytes"))
    assert receipt["MemoryMax"] is None
    for key in ("wall_limit","CPU_limit","AS_limit","FS_limit"):
        assert receipt[key] is None
    assert receipt["recovery_reservation_unchanged"]
    verify_pins(E,json.loads((E/"artifact_SHA256.json").read_text()))
