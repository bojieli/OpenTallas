import pytest
from tools.w17_D1_reset_qualified_runtime_verify import verify

def healthy():
    lines=['D1_RESET_ACCEPT time_ps=6000 rn=1']
    for row in range(128):
        lines.append(f'D1_QUALIFIED_PRIME time_ps={7501+row*1000} row={row} rn=1 valid=1 active=1 tag={row} user=0 blocks=ffff')
    return '\n'.join(lines+['D1_ALL128_PRIMED time_ps=134501 accepted=128 rn=1',
       'D1_REAL_GATE time=140000 pc=0 me_ready=1 kv_ok=1 kvd_v=0 win_idle=1 waited=1 q_gate=1 m0_gate=1',
       'D1_REAL_DESCRIPTOR time=142000 generation=1 rows=128',
       'D1_REAL_ACCEPT time=145000 address=262144 tag=7 write=0',
       'D1_REAL_RESPONSE time=200000 tag=7 beat=0',
       'D1_PREFIX_GATE_AND_FIRST_RETURN_ONLY reads=1 returns=1 writes=0 acks=0',
       'D1_TERMINAL_PREFIX_ONLY evals=400 time_ps=200501 cycles=197'])

def test_healthy_control_is_model_only_and_does_not_transfer_scope():
    r=verify(healthy(),0)
    assert r['reset_qualified_rows']==128 and r['counts']['returns']==1
    assert not r['fulltoken'] and r['RTL_fidelity']=='UNPROVEN'
    assert r['I66_program_origin'] is None and r['coll_busy'] is None
    assert r['first_return_deadline'] is None

@pytest.mark.parametrize('old,new',[
    ('time_ps=6000 rn=1','time_ps=5000 rn=0'),
    ('time_ps=7501 row=0','time_ps=5501 row=0'),
    ('row=0 rn=1 valid=1','row=0 rn=1 valid=0'),
    ('tag=0 user=0','tag=1 user=0'),
    ('blocks=ffff','blocks=fffe'),
    ('accepted=128','accepted=127'),
    ('rows=128','rows=127'),
    ('time=200000 tag=7','time=200000 tag=8'),
    ('tag=7 beat=0','tag=7 beat=1'),
    ('reads=1 returns=1','reads=1 returns=2'),
    ('me_ready=1','me_ready=2'),
    ('time_ps=6000','time_ps=True'),
])
def test_adversarial_trace_controls(old,new):
    with pytest.raises(ValueError):verify(healthy().replace(old,new,1),0)

@pytest.mark.parametrize('suffix',[
    '\nD1_SOURCE_OR_LEDGER_FAULT',
    '\nD1_PREFIX_CYCLE_CAP_NO_COMPLETION_CREDIT cycles=512',
    '\nD1_REAL_RESPONSE time=201000 tag=7 beat=0',
])
def test_late_fault_cap_or_duplicate_after_endpoint_cannot_pass(suffix):
    with pytest.raises(ValueError):verify(healthy()+suffix,0)

def test_exit_failure_wins_even_with_complete_witness():
    with pytest.raises(ValueError):verify(healthy(),1)

@pytest.mark.parametrize('marker',['D1_RESET_ACCEPT','D1_ALL128_PRIMED','D1_REAL_GATE','D1_REAL_DESCRIPTOR','D1_REAL_ACCEPT','D1_REAL_RESPONSE','D1_PREFIX_GATE_AND_FIRST_RETURN_ONLY','D1_TERMINAL_PREFIX_ONLY'])
def test_missing_required_actual_marker(marker):
    log='\n'.join(x for x in healthy().splitlines() if not x.startswith(marker))
    with pytest.raises(ValueError):verify(log,0)

def test_repeated_prime_rejected_before_endpoint():
    lines=healthy().splitlines();lines.insert(2,lines[1])
    with pytest.raises(ValueError):verify('\n'.join(lines),0)

def test_no_PC_or_busy_progress_credit():
    with pytest.raises(ValueError):verify('D1_HEARTBEAT evals=100000 time_ps=50000000 cycles=50000\nD1_TERMINAL_PREFIX_ONLY evals=100000 time_ps=50000000 cycles=50000',0)


def test_actual_program_binding_cannot_be_inferred_from_row_or_endpoint_markers():
    from tools.w17_D1_reset_qualified_runtime_verify import verify_bound_execution
    expected=['binary','+DIR=/original/input']
    assert verify_bound_execution(healthy(),0,expected,expected)['reset_qualified_rows']==128
    for actual in [['binary'],['binary','+DIR=/other'],['other','+DIR=/original/input']]:
        with pytest.raises(ValueError,match='argv binding'):verify_bound_execution(healthy(),0,actual,expected)
