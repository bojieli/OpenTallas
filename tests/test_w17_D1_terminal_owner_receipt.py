import copy
import hashlib
import json
from pathlib import Path
import pytest
from tools.w17_D1_terminal_owner_receipt import parse,lower_bound,D,C,W,L,Q
ROOT=Path(__file__).resolve().parents[1]
E=ROOT/'results/uarch/w17_D1_terminal_owner_actual_20261002_r1'
P=ROOT/'results/uarch/w17_D1_terminal_program_binding_model_20261002'

def inputs():
    return ((E/'gdb.log').read_text(),json.loads((E/'receipt.json').read_text()),json.loads((P/'plan.json').read_text()),json.loads((E/'live_inferior_argv.json').read_text()))

def mutate(old,new):
    text,receipt,plan,live=inputs();assert old in text
    text=text.replace(old,new,1);receipt['log_SHA256']=hashlib.sha256(text.encode()).hexdigest()
    return text,receipt,plan,live

def test_actual_firstreply_ownership_snapshot_not_token():
    r=parse(*inputs());v=r['owner_values']
    assert r['read_accept_sample_ps']==143500 and r['read_reply_sample_ps']==196500
    assert r['actual_reply_delta_cycles']==53
    assert v[C+'pc']==0 and v[C+'st']==6 and v[C+'idles']==31
    assert v[D+'kv_ok']==0 and v[C+'me_go']==0
    assert v[L+'state']==1 and v[L+'active_gen']==1 and v[L+'active_rows']==128
    assert v[W+'u_window__DOT__state']==5 and v[W+'u_window__DOT__sec']==1
    assert v[Q+'returns']==1 and v[Q+'pending']==0
    assert r['finite_service_upper_bound']=='BOUND_MISSING' and not r['fulltoken']

@pytest.mark.parametrize('old,new',[
    ('D1_OWNER_000 value=193','D1_OWNER_000 value=True'),
    ('D1_OWNER_000 value=193','D1_OWNER_001 value=193'),
    ('D1_OWNER_010 value=0','D1_OWNER_010 value=64'),
    ('D1_OWNER_063 value=0','D1_OWNER_063 value=4'),
    ('D1_OWNER_058 value=1','D1_OWNER_058 value=2'),
    ('D1_OWNER_062 value=0','D1_OWNER_062 value=1'),
    ('D1_OWNER_073 value=0','D1_OWNER_073 value=1'),
    ('D1_OWNER_065 value=4294967295','D1_OWNER_065 value=4294967294'),
    ('D1_OWNER_037 value=5','D1_OWNER_037 value=6'),
    ('D1_REAL_RESPONSE time=197000 tag=0','D1_REAL_RESPONSE time=197000 tag=1'),
    ('D1_REAL_RESPONSE time=197000','D1_REAL_RESPONSE time=197001'),
    ('D1_QUALIFIED_PRIME time_ps=7501 row=0','D1_QUALIFIED_PRIME time_ps=5501 row=0'),
    ('D1_INFERIOR_EXIT code=0','D1_INFERIOR_EXIT code=1'),
])
def test_real_journal_semantic_negatives_fail_even_with_updated_integrity_hash(old,new):
    with pytest.raises(ValueError):parse(*mutate(old,new))

def test_no_clock_rounding_waiver_timestamp_shift_changes_measured_delta():
    r=parse(*mutate('D1_REAL_ACCEPT time=144000','D1_REAL_ACCEPT time=145000'))
    assert r['actual_reply_delta_cycles']==52 # Correctly reports changed input; never forces predicted53.
    assert r['read_accept_sample_ps']==144500

@pytest.mark.parametrize('kind',['missing','twice','late_fault','cycle_cap'])
def test_capture_endpoint_and_fault_negatives(kind):
    text,receipt,plan,live=inputs()
    if kind=='missing':text=text.replace('D1_OWNER_078 value=0\n','')
    if kind=='twice':text+='\nD1_TERMINAL_OWNER_CAPTURE_BEGIN\n'
    if kind=='late_fault':text+='\nD1_SOURCE_OR_LEDGER_FAULT\n'
    if kind=='cycle_cap':text+='\nD1_PREFIX_CYCLE_CAP_NO_COMPLETION_CREDIT cycles=512\n'
    receipt['log_SHA256']=hashlib.sha256(text.encode()).hexdigest()
    with pytest.raises(ValueError):parse(text,receipt,plan,live)

def test_actual_program_missing_and_posthash_failure_both_rejected():
    text,receipt,plan,live=inputs();live['actual_argv'].pop()
    with pytest.raises(ValueError):parse(text,receipt,plan,live)
    text,receipt,plan,live=inputs();receipt['input_postchecks'][next(iter(receipt['input_postchecks']))]=False
    with pytest.raises(ValueError):parse(text,receipt,plan,live)

@pytest.mark.parametrize('value',[True,1.5,-1,0,33])
def test_lower_bound_has_no_arbitrary_deadline_or_invalid_inputs(value):
    with pytest.raises(ValueError):lower_bound(value)

def test_source_sequential_stage_lower_bound_beyond_prefixstop():
    r=lower_bound(53)
    assert r['minimum_request_to_due_ps']==33524 and r['minimum_later_reply_cycles']==34
    assert r['row0_minimum_cycles_from_first_request']==613
    assert r['all128_minimum_cycles_from_first_request']==76178
    assert r['upper_bound'] is None and r['score_completion_deadline'] is None
    src=ROOT/'results/uarch/w17_D1_current_core_probe_20261002/source_authority'
    idx=(src/'rtl/hdc/v41x/ot_hdc_v41x_idx_hbm.sv').read_text()
    assert 'tmin = arr + REQ_PS;' in idx
    assert 'r_t[p][k] = h_tcol[p] + CL_PS + BURST_PS + RSP_PS;' in idx
    window=(src/'rtl/chip/ot_chip_v41x_window_kv_prefetch.sv').read_text()
    assert 'FR_DONE: if (response)' in window and 'state <= FR;' in window


def test_no_original_failed_receipt_is_modified():
    parent=ROOT/'results/rtl/w17_D1_reset_qualified_prefix_parent_20261002/runtime.log'
    assert 'D1_PREFIX_CYCLE_CAP_NO_COMPLETION_CREDIT cycles=512' in parent.read_text()
    original=ROOT/'results/uarch/w17_D1_disjoint_native_actual_runtime_20261002_r1/runtime/runtime.log'
    assert 'D1_SOURCE_OR_LEDGER_FAULT' in original.read_text()
