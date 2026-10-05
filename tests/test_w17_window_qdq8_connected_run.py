"""GO/cap/calibration controls for prepared connected runner. No RTL runs."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import pytest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import w17_window_qdq8_connected_run as R
PLAN=Path('/tmp/window-qdq8-connected-runner-plan-20261002-r1/plan.json')


def test_exact_plan_and_shared_compile_budget():
    plan,model=R.validate_plan(PLAN)
    assert list(plan['commands'])==['retain0','retain1']
    assert R.remaining_compile_budget(90)==60
    with pytest.raises(AssertionError):R.remaining_compile_budget(150)
    assert R.BUDGET['compile_total_seconds']+R.BUDGET['total_case_seconds']+R.BUDGET['supervision_reserve_seconds']==180
    assert not any((R.PREPARED/('obj_'+n)).exists() for n in ('retain0','retain1'))


@pytest.mark.parametrize('key,value',[('memory_max','max'),('swap_max','max'),('affinity',[30]),('file_limit',[268435457]*2),('runtime_usec','4min'),('kill_mode','process')])
def test_cap_fail_closed(key,value):
    bad=copy.deepcopy(R.CAPS);bad[key]=value
    with pytest.raises(AssertionError):R.caps_lib.validate_caps(bad)


def test_no_fresh_GO_no_service_no_compile(tmp_path):
    out=tmp_path/'refusal'
    p=subprocess.run([sys.executable,str(ROOT/'tools/w17_window_qdq8_connected_run.py'),'--plan',str(PLAN),'--out',str(out),'--unit','w17-connected-never-without-go.service'],capture_output=True)
    assert p.returncode==2
    assert json.loads((out/'preflight_receipt.json').read_bytes())['verdict']=='FAIL_PREFLIGHT_NO_SERVICE_NO_COMPILE_NO_RETRY'
    assert not(out/'launch.json').exists()


def test_wrong_oracle_and_GO_digest_rejected(monkeypatch):
    plan=json.loads(PLAN.read_bytes())
    go=dict(status='PARENT_QDQ8_CONNECTED_SINGLE_SERVICE_GO',plan_sha256=R.sha(PLAN),commands_sha256=R.objsha(plan['commands']),**{k:plan[k] for k in ('runner_sha256','runner_dependencies_sha256','model_sha256','manifest_sha256','caps','budget','healthy_added_guard_cycles')})
    R.validate_GO(go,plan,PLAN)
    for key in ('plan_sha256','commands_sha256','model_sha256'):
        bad=copy.deepcopy(go);bad[key]='0'*64
        with pytest.raises(AssertionError):R.validate_GO(bad,plan,PLAN)
    real=R.sha
    monkeypatch.setattr(R,'sha',lambda p:'0'*64 if str(p).endswith('/oracle.json') else real(p))
    with pytest.raises(AssertionError):R.validate_plan(PLAN)


def synthetic_log(summary,events):
    keys={
      'block':('BLOCK',('cycle','block')),
      'descriptor':('DESCRIPTOR',('cycle','op','generation','user','rows')),
      'write_ack':('WRITE_ACK',('cycle','count')),
      'logical_publish':('LOGICAL_PUBLISH',('cycle',)),
      'request':('REQUEST',('cycle','pc','address','tag','we','strobe')),
      'reply':('REPLY',('cycle','pc','address','tag','op')),
      'column':('COLUMN',('cycle','pc','tcol_ps','address','tag','we')),
      'lifecycle_done':('LIFECYCLE_DONE',('cycle','op','generation'))}
    lines=[];acks=0
    for e in events:
        if e['kind'] not in keys:continue
        e=dict(e)
        if e['kind']=='write_ack':acks+=1;e['count']=acks
        marker,fields=keys[e['kind']]
        lines.append(marker+' '+' '.join(k+'='+str(int(e[k])) for k in fields))
        if e['kind']=='reply' and e['tag']&65535==16:lines.append(f'NATURAL_EPOCH_WRAP cycle={e["cycle"]} coldrow=512')
    for i,c in enumerate(summary['staged_samples']):lines.append(f'STAGE cycle={c} op={i} generation={i+1} refill={summary["refill_counters"][i]}')
    for p in summary['per_PC']:lines.append('PC_DRAIN '+' '.join(k+'='+str(p[k]) for k in ('pc','reads','writes','refreshes','activations','q','r')))
    gold=json.loads((R.EVIDENCE/'oracle.json').read_bytes())
    for b,c in enumerate(summary['QE_capture_cycles']):
        packed=sum(v<<(8*i) for i,v in enumerate(gold[b]['codes']))
        lines.append(f'QE_CAPTURE cycle={c} block={b} address={55232+32*b} codes={packed:x} scale={gold[b]["scale"]:x}')
    lines.append(f'QDQ8_CONNECTED_LIFECYCLE_PASS retain={summary["retain"]} writes=32 acks=32 reads={summary["read_requests"]} replies={summary["read_requests"]} beats={summary["total_packed_beats"]} epoch={summary["final_epoch"]}')
    return '\n'.join(lines)


def test_complete_trace_comparison_and_mutants():
    model=json.loads((R.EVIDENCE/'model.json').read_bytes())
    for name,summary in model['cases'].items():
        events=[json.loads(x) for x in (R.EVIDENCE/(name+'_events.jsonl')).read_text().splitlines()]
        log=synthetic_log(summary,events)
        assert R.compare(log,summary,events)['verdict']=='PASS'
        for bad in (log.replace('QE_CAPTURE cycle=317','QE_CAPTURE cycle=318',1),log.replace('NATURAL_EPOCH_WRAP','MISSING_WRAP',1),log.replace('activations=','badACT=',1),log.replace('WRITE_ACK cycle=','MISSING_ACK cycle=',1)):
            assert R.compare(bad,summary,events)['verdict']=='FAIL_PRESERVED_NO_FIT'


def test_source_producer_recovery_gap_is_not_fault_gated():
    s=(ROOT/'rtl/hdc/v41x/ot_hdc_v41x_window_kv_blocks.sv').read_text()
    assert 'assign blk_v = state == DRAIN;' in s and 'assign issue_ready = state == FULL;' in s
    assert 'if (cap_v) begin' in s and 'if (blk_v && blk_ready) begin' in s
    assert 'input  wire              cancel' not in s and 'input  wire              freeze' not in s
    r=json.loads((ROOT/'results/uarch/w17_window_qdq8_producer_freeze_cancel_gap_20261002/model.json').read_bytes())
    assert r['verdict'].startswith('GAP_PRESERVED')
    assert r['healthy_local_completion_example']['predicted_last_block_accept_cycle']<r['healthy_local_completion_example']['predicted_final_WR_ack_cycle']
