"""Actual column identity and field evidence control checks; no numeric oracle."""
import importlib.util
import json
from pathlib import Path
import pytest
from tools.hbm_accel_program_compare import predecessor_released,compare_fields,same_memory,digest
from tools.hbm_accel_program_engine import RTLColumnEngine
from tools.gpu_sys.ds_hbm_sm_engine20_guarded import SMEngine20Guarded

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('ha5_receipt_boundary',ROOT/'tests/test_hbm_accel_program_engine.py')
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)


def test_submitted_column_identity_is_not_nonresult_cpl_token_zero():
    pins=mod.BoundaryPins()
    engine=RTLColumnEngine(pins,{'swapout':0},lambda c:[('swapout',i,i) for i in range(6)],
        ndie=2,nsm=2,position_extent=32,swapin_positions=(),source_sha256='1'*64,
        enable=True,sm_engine_factory=SMEngine20Guarded)
    engine.run(dict(job=9,generation=3))
    assert [r['token'] for r in engine.receipts]==list(range(6))
    assert [r['input_token'] for r in engine.receipts]==list(range(6))
    assert [r['completion_token'] for r in engine.receipts]==[0]*6


def test_missing_or_invalid_original_terminal_retains_owner(tmp_path):
    with pytest.raises(RuntimeError,match='no authoritative terminal'):
        predecessor_released(tmp_path,'1'*64)
    (tmp_path/'run/backend').mkdir(parents=True)
    (tmp_path/'run/result.json').write_text(json.dumps(dict(verdict='FAILED')))
    (tmp_path/'run/backend/owner.json').write_text('{}')
    (tmp_path/'exit.rc').write_text('1\n')
    with pytest.raises(RuntimeError,match='did not complete'):
        predecessor_released(tmp_path,'1'*64)


def field_result(root,payload,cycles):
    (root/'fields').mkdir(parents=True)
    field=root/'fields/column_d0_X.bin';field.write_bytes(payload)
    result=dict(command=dict(op='VLAYER',idx=0,ncol=1,pos=0,toks=[0],job=1,generation=1),
        source_inputs=[dict(sha256='input',bytes=4)],fields={field.name:dict(bytes=len(payload),sha256=digest(field))},
        actual_context_edges=cycles,actual_context_time_ps=cycles*833)
    (root/'result.json').write_text(json.dumps(result));return result


def test_field_bit_mismatch_and_slower_measurement_reject_without_tuning(tmp_path):
    a,b,c=tmp_path/'baseline',tmp_path/'different',tmp_path/'slower'
    field_result(a,b'\x00\x80\x00\x00',100)
    field_result(b,b'\x00\x00\x00\x00',90)
    field_result(c,b'\x00\x80\x00\x00',101)
    mismatch=compare_fields(a,b)
    assert mismatch['verdict']=='REJECTED_FIELD_MISMATCH'
    assert mismatch['mismatches']==[dict(field='column_d0_X.bin',first_byte=1)]
    slower=compare_fields(a,c)
    assert slower['verdict']=='REJECTED_SLOWER_ACTUAL_LAYER' and not slower['adopt']
    assert slower['composed_gain_us'] is None


def test_changed_actual_source_memory_is_not_same_loaded_source():
    source=dict(layout={},position_extent=32,topology={},prompt=[0],noise=3559,
                artifacts={'mem_d0_p0.hex':'1','die0.bin':'2','prog_d0_s0.hex':'old'})
    candidate=dict(source,artifacts=dict(source['artifacts'],**{'prog_d0_s0.hex':'new'}))
    assert same_memory(source,candidate)=={'die0.bin':'2','mem_d0_p0.hex':'1'}
    candidate['artifacts']['mem_d0_p0.hex']='changed'
    with pytest.raises(ValueError,match='checkpoint memory'):same_memory(source,candidate)
