"""Pre-GO runner rejection controls. Synthetic logs only; no RTL execution."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import pytest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import w17_window_qdq8_arithmetic_run as R
PLAN=Path('/tmp/window-qdq8-arithmetic-runner-plan-20261002-r2/plan.json')


def test_actual_plan_and_compiler_binding():
    plan,model=R.validate_plan(PLAN)
    assert plan['compiler']['version']=='Verilator 5.050 2026-07-01 rev v5.050'
    assert plan['budget']['compile_seconds']+plan['budget']['total_case_seconds']+plan['budget']['supervision_reserve_seconds']==180
    assert plan['runtime_commands']==model['preparation']['runtime_commands']
    assert not(R.PREPARED/'obj').exists()


@pytest.mark.parametrize('key,value',[
    ('memory_max','max'),('swap_max','max'),('affinity',[30]),
    ('file_limit',[268435457,268435457]),('runtime_usec','4min'),('kill_mode','process')])
def test_caps_fail_closed(key,value):
    bad=copy.deepcopy(R.CAPS);bad[key]=value
    with pytest.raises(AssertionError,match='FAIL_CAPS'):R.validate_caps(bad)


def test_fresh_GO_required_and_no_launch(tmp_path):
    out=tmp_path/'missing_go'
    p=subprocess.run([sys.executable,str(ROOT/'tools/w17_window_qdq8_arithmetic_run.py'),
      '--plan',str(PLAN),'--out',str(out),'--unit','w17-qdq8-never-launch-without-go.service'],capture_output=True)
    assert p.returncode==2
    receipt=json.loads((out/'preflight_receipt.json').read_bytes())
    assert receipt['verdict']=='FAIL_LAUNCH_PREFLIGHT_NO_SERVICE_NO_COMPILE_NO_FALLBACK'
    assert 'Fresh explicit parent GO required' in receipt['error']
    assert not(out/'launch.json').exists() and not(R.PREPARED/'obj').exists()


def test_wrong_oracle_pin_rejected(monkeypatch):
    real=R.sha
    def wrong(path):
        return '0'*64 if str(path).endswith('fp32_rounding/oracle.json') else real(path)
    monkeypatch.setattr(R,'sha',wrong)
    with pytest.raises(AssertionError):R.validate_plan(PLAN)


def test_wrong_GO_options_and_plan_rejected():
    plan=json.loads(PLAN.read_bytes())
    go=dict(status='PARENT_QDQ8_ARITHMETIC_SINGLE_RUN_GO',plan_sha256=R.sha(PLAN),
      compile_command_sha256=R.objsha(plan['compile_command']),**{k:plan[k] for k in ('runner_sha256','model_sha256','manifest_sha256','caps','budget')})
    R.validate_go(go,plan,PLAN)
    for key in ('plan_sha256','compile_command_sha256','runner_sha256','manifest_sha256'):
        bad=copy.deepcopy(go);bad[key]='0'*64
        with pytest.raises(AssertionError):R.validate_go(bad,plan,PLAN)


def synthetic_log(which,model):
    name=['fp32_rounding','bf16_input','nonfinite_flags'][which];healthy=which!=2
    gold=json.loads((R.EVIDENCE/name/'oracle.json').read_bytes());cal=model['edge_calendar'];rows=[]
    pack=lambda a,w:sum(n<<(i*w) for i,n in enumerate(a))
    for b,c in enumerate(cal['read_sample']):rows.append(f'XR_SAMPLE cycle={c} block={b} address={54720+32*b}')
    for b,c in enumerate(cal['capture_sample']):
        y=pack(gold[b]['bf16_widened'],32) if healthy else 0
        rows.append(f'VM_SAMPLE cycle={c} block={b} address={55232+32*b} data={y:x}')
        if healthy:rows.append(f'CAPTURE cycle={c} block={b} address={55232+32*b} codes={pack(gold[b]["codes"],8):x} scale={gold[b]["scale"]:x}')
    if healthy:
        for b,c in enumerate(cal['block_accept']):rows.append(f'BLOCK_ACCEPT cycle={c} block={b} first={57359+512*b} user=37 codes={pack(gold[b]["codes"],8):x} scale={gold[b]["scale"]:x}')
    end=cal['healthy_terminal_sample'] if healthy else cal['invalid_terminal_sample']
    rows.append(f'QDQ8_ARITHMETIC_PASS case={which} cycle={end} reads=16 VMblocks=16 captures={16 if healthy else 0} blocks={16 if healthy else 0} faults={0 if healthy else 16}')
    return '\n'.join(rows)


def test_comparator_rejects_payload_cycle_provenance_and_flags():
    model=json.loads((R.EVIDENCE/'model.json').read_bytes())
    for which in range(3):assert R.compare(synthetic_log(which,model),which,model)['verdict']=='PASS'
    log=synthetic_log(0,model)
    for bad in (log.replace('CAPTURE cycle=17','CAPTURE cycle=18',1),
                log.replace('user=37','user=38',1),log.replace('reads=16 VMblocks=16','reads=15 VMblocks=16',1),
                log.replace('scale=7f','scale=7e',1)):
        assert bad!=log and R.compare(bad,0,model)['verdict']=='FAIL_NO_FIT'
    invalid=synthetic_log(2,model)
    assert R.compare(invalid.replace('faults=16','faults=0'),2,model)['verdict']=='FAIL_NO_FIT'
