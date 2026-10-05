"""Source closure and adversarial receipt tests; no DUT/compiler execution."""
import copy
import json
from pathlib import Path
import re
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import DS_recovery_negative_successor as r


@pytest.fixture(scope='module')
def plan():
    return r.plan_object()


def values(label):
    w = dict.fromkeys(r.WITNESS_FIELDS, 0)
    w.update(cycles=30, fault_cycle=10, checking=1, pc=20, stopped_pc=20,
             suffix_closed=1, qe_idle=1, win_idle=1)
    if label == 'physical_QE_gate':
        w.update(qe_accepts=1, qe_idle=0)
    elif label == 'PC_advance':
        w['pc'] = 21
    elif label == 'VM_frozen_store_drop':
        w.update(qe_accepts=1, terminals=16, vm_stores=16)
    elif label == 'scalar_suppression':
        w.update(su_accepts=1, suppress=1, xs_we=1)
    return w


def log(case, w, source='/fixture/sources'):
    return ('W17_RECOVERY_WITNESS ' + case['label'] + ' ' +
            ' '.join(k + '=' + str(w[k]) for k in r.WITNESS_FIELDS) +
            f"\n[13000] %Fatal: tb.sv:{case['fatal_line']}: Assertion failed in tb: {case['fatal_marker']}\n" +
            f"%Error: {source}/tb.sv:{case['fatal_line']}: Verilog $stop\nAborting...\n")


def test_original_assertions_and_order_byte_preserved():
    old = (ROOT / 'rtl/test/w17_window_core_cancel_join_r8/tb.sv').read_text()
    new = r.BENCH.read_text()
    for case in r.read(r.CONTRACT)['cases']:
        marker = re.escape('$fatal(1,"' + case['fatal_marker'] + '")')
        pattern = r'begin\n   \$display\("W17_RECOVERY_WITNESS [^\n]+\n   (' + marker + r');\n  end'
        new, count = re.subn(pattern, r'\1;', new)
        assert count == 1
    assert old == new


def test_model_snapshot_identity_and_scope(plan):
    assert plan['compile_phases'] == 5 and plan['runtime_cases'] == 27
    assert len(plan['jobs'][0]['cases']) == 23
    assert plan['geometry'] == {'SUN': 256, 'SUM': 64, 'BL': 16, 'IL': 8, 'NBMAX': 192,
                                'CHUNK8': 1, 'MP': 1, 'AW': 30, 'NW': 21}
    assert all(x == 0 for x in plan['hardware_delta'].values())
    assert not plan['retained_binary_eligible']
    parent = r.read(ROOT / r.read(r.CONTRACT)['parent_plan'])
    baseline = plan['jobs'][0]['files_sha256']
    assert len(baseline) == 164
    assert {k: baseline[k] for k in parent['source_files_sha256']} == parent['source_files_sha256']
    assert baseline['tb.sv'] != baseline['rtl/test/w17_window_core_cancel_join_r8/tb.sv']
    for job in plan['jobs'][1:]:
        diff = [k for k in baseline if baseline[k] != job['files_sha256'][k]]
        assert len(diff) == 1
    qe = plan['jobs'][1]['cases'][0]
    assert qe['fatal_marker'] == 'local ACK before actual suffix and logical EMPTY'
    assert qe['fatal_line'] < next(i for i, line in enumerate(r.BENCH.read_text().splitlines(), 1)
                                 if '$fatal' in line and 'registered go cut accepted QE' in line)


@pytest.mark.parametrize('index', [1, 2, 3, 4])
def test_exact_refusal_requires_live_invariant_witness(plan, index):
    case = plan['jobs'][index]['cases'][0]
    assert r.verify_negative(case, 1, log(case, values(case['label'])), '/fixture/sources')['verdict'] == 'EXPECTED_MUTATION_REFUSAL'


@pytest.mark.parametrize('index', [1, 2, 3, 4])
@pytest.mark.parametrize('attack', ['arbitrary', 'site', 'path', 'marker', 'missing_witness',
                                  'unknown_value', 'extra_error', 'wrong_label', 'no_violation'])
def test_unrelated_and_malformed_failures_never_pass(plan, index, attack):
    case = plan['jobs'][index]['cases'][0]
    text = log(case, values(case['label']))
    if attack == 'arbitrary':
        text = 'segmentation fault\n'
    elif attack == 'site':
        text = text.replace('tb.sv:' + str(case['fatal_line']), 'tb.sv:1')
    elif attack == 'path':
        text = text.replace('/fixture/sources', '/other/sources')
    elif attack == 'marker':
        text = text.replace(case['fatal_marker'], 'admission freeze violated')
    elif attack == 'missing_witness':
        text = text.split('\n', 1)[1]
    elif attack == 'unknown_value':
        text = text.replace('qe_idle=', 'qe_idle=x')
    elif attack == 'extra_error':
        text += '%Error: OOM\n'
    elif attack == 'wrong_label':
        text = text.replace('W17_RECOVERY_WITNESS ' + case['label'], 'W17_RECOVERY_WITNESS other')
    else:
        w = values(case['label'])
        w.update(qe_accepts=0, pc=w['stopped_pc'], sink_words=512, written_words=512, xs_we=0, kv_we=0)
        text = log(case, w)
    with pytest.raises(ValueError):
        r.verify_negative(case, 1, text, '/fixture/sources')


@pytest.mark.parametrize('code', [0, 2, -6, -9, 137])
def test_noncanonical_exit_rejected(plan, code):
    case = plan['jobs'][1]['cases'][0]
    with pytest.raises(ValueError):
        r.verify_negative(case, code, log(case, values(case['label'])), '/fixture/sources')


def test_historical_receipt_cannot_be_reclassified(plan):
    old = (ROOT / 'results/rtl/w17_core_full27_parent_terminal_20261002_r2/physical_QE_gate/runtime_0.log').read_text()
    case = plan['jobs'][1]['cases'][0]
    with pytest.raises(ValueError):
        r.verify_negative(case, 1, old, '/fixture/sources')
    diagnosis = r.read(ROOT / 'results/uarch/native_software_parent_intake_20261002/DS_core_recovery_negative_receipt_diagnosis.json')
    assert not diagnosis['full27_campaign_pass']


def test_protocol_timeout_preserved_and_unrelated(plan):
    assert 'cycles>4096' in r.BENCH.read_text()
    case = plan['jobs'][1]['cases'][0]
    text = log(case, values(case['label'])).replace(case['fatal_marker'], 'actual source suffix bounded timeout')
    with pytest.raises(ValueError):
        r.verify_negative(case, 1, text, '/fixture/sources')


def test_reuse_requires_all_source_tools_args_and_binary(tmp_path):
    binary = tmp_path / 'Vtb'
    binary.write_bytes(b'never executed')
    job = {'files_sha256': {'tb.sv': 'abc'}}
    tools = {'compiler': 'def'}
    commands = {'frontend_command': ['verilator', '--assert']}
    artifact = {'source_files_sha256': job['files_sha256'], 'toolchain': tools,
                'commands': commands, 'binary_path': str(binary), 'binary_sha256': r.sha(binary)}
    assert r.reusable(artifact, job, tools, commands)
    for key in ('source_files_sha256', 'toolchain', 'commands', 'binary_sha256'):
        changed = copy.deepcopy(artifact)
        changed[key] = 'changed'
        with pytest.raises(ValueError):
            r.reusable(changed, job, tools, commands)


@pytest.mark.parametrize('cut,prefix', [('GO', None), ('ISSUE', None), ('PREFIX', 0), ('PREFIX', 16), ('SU_SUFFIX', None)])
def test_positive_receipt_identity_and_counters(cut, prefix):
    case = {'CUT': cut}
    if prefix is not None:
        case['PREFIX'] = prefix
    qe = int(cut not in ('GO', 'ISSUE'))
    text = (f'ACTUAL_CORE_CANCEL_PASS cut={cut} prefix={prefix or 0} qe={qe} terminal={16*qe} vm={16*qe} '
            f'capture=0 blocks=0 acceptedWR=0 faultcycle=10 localACKcycle=30 suppressed=1 sinkWords={512*qe} frozenFrames=0\n')
    assert r.verify_positive(case, 0, text)['verdict'] == 'POSITIVE_CONTROL_PASS'
    for bad in (text + text, text.replace(f'cut={cut}', 'cut=OTHER'), text + '%Error: failed'):
        with pytest.raises(ValueError):
            r.verify_positive(case, 0, bad)
    with pytest.raises(ValueError):
        r.verify_positive(case, 1, text)


def test_unreviewed_run_preserves_refusal_before_compiler(tmp_path, monkeypatch):
    called = []
    def refuse(*args):
        raise ValueError('resource review pending')
    monkeypatch.setattr(r, 'validate_review', refuse)
    monkeypatch.setattr(r, 'process', lambda *args: called.append(args))
    out = tmp_path / 'run'
    assert r.execute(tmp_path / 'plan', tmp_path / 'review', out) == 1
    assert not called
    assert r.read(out / 'record.json')['stage'] == 'review'
    with pytest.raises(FileExistsError):
        r.execute(tmp_path / 'plan', tmp_path / 'review', out)


def test_no_arbitrary_limits_or_compile_in_prepare():
    source = r.TOOL.read_text()
    assert 'subprocess.Popen(command, stdout=f, stderr=subprocess.STDOUT)' in source
    assert 'timeout=' not in source and 'setrlimit(' not in source
    assert 'RuntimeMaxSec' not in source and 'MemoryMax' not in source


def review_fixture(tmp_path, plan):
    plan_path = tmp_path / 'plan.json'
    r.write(plan_path, plan)
    r.write(tmp_path / 'host_context.json', {'initial': 'measured'})
    evidence = tmp_path / 'inventory.json'
    r.write(evidence, {'memory_peak': 100, 'disk_inventory': 200})
    review = {'status': 'MODEL_RESOURCE_CONTEXT_REVIEWED', 'plan_sha256': r.sha(plan_path),
              'host_context_sha256': r.sha(tmp_path / 'host_context.json'), 'hostname': r.socket.gethostname(),
              'reviewer': 'test', 'reserved_CPUs': [0, 1], 'active_job_CPUs': [8, 9],
              'measured_memory_peak_bytes': 100, 'reserved_memory_bytes': 110,
              'measured_output_peak_bytes': 200, 'reserved_disk_bytes': 220,
              'inventory_evidence': [{'path': str(evidence), 'sha256': r.sha(evidence)}],
              'reservation_evidence': [{'path': str(evidence), 'sha256': r.sha(evidence)}]}
    review_path = tmp_path / 'review.json'
    r.write(review_path, review)
    return plan_path, review_path, review


@pytest.mark.parametrize('attack', ['none', 'overlap', 'no_measurement', 'no_evidence', 'small_reservation',
                                  'pending', 'source_drift', 'headroom', 'inherited_cap', 'args_drift'])
def test_review_admission_is_measured_and_disjoint(tmp_path, monkeypatch, plan, attack):
    p, review_path, review = review_fixture(tmp_path, plan)
    monkeypatch.setattr(r, 'plan_object', lambda: plan)
    monkeypatch.setattr(r.os, 'sched_getaffinity', lambda _: {0, 1, 8, 9})
    context = {'memory': {'MemAvailable': 1000}, 'disk_free_bytes': 1000,
               'inherited_rlimits': {k: [-1, -1] for k in ('RLIMIT_CPU', 'RLIMIT_FSIZE', 'RLIMIT_AS')}}
    monkeypatch.setattr(r, 'host_context', lambda _: context)
    if attack == 'overlap':
        review['active_job_CPUs'] = [0, 1]
    elif attack == 'no_measurement':
        review['measured_memory_peak_bytes'] = None
    elif attack == 'no_evidence':
        review['reservation_evidence'] = []
    elif attack == 'small_reservation':
        review['reserved_disk_bytes'] = 1
    elif attack == 'pending':
        review['status'] = 'PENDING_MODEL_RESOURCE_CONTEXT_REVIEW'
    elif attack in ('source_drift', 'args_drift'):
        changed = copy.deepcopy(plan)
        if attack == 'source_drift':
            changed['bench_sha256'] = '0' * 64
        else:
            changed['jobs'][1]['frontend_command'].append('--build')
        monkeypatch.setattr(r, 'plan_object', lambda: changed)
    elif attack == 'headroom':
        context['disk_free_bytes'] = 10
    elif attack == 'inherited_cap':
        context['inherited_rlimits']['RLIMIT_CPU'] = [10, 10]
    review_path.write_text(json.dumps(review))
    if attack == 'none':
        assert r.validate_review(review_path, p, tmp_path)[0] == plan
    else:
        with pytest.raises(ValueError):
            r.validate_review(review_path, p, tmp_path)


def test_first_runtime_failure_stops_and_keeps_binary(tmp_path, monkeypatch):
    fixture = {'tb.sv': b'fixture only; never compiled'}
    job = {'label': 'baseline', 'files_sha256': {'tb.sv': r.hashlib.sha256(fixture['tb.sv']).hexdigest()},
           'frontend_command': ['mock_frontend'], 'CXX_command': ['mock_make'], 'cases': [{'CUT': 'GO'}]}
    plan = {'jobs': [job, dict(job, label='must_not_start')], 'toolchain': {'mock': 'pinned'}}
    monkeypatch.setattr(r, 'validate_review', lambda *args: (plan, {'reserved_CPUs': [0, 1]}))
    monkeypatch.setattr(r.os, 'sched_setaffinity', lambda *args: None)
    monkeypatch.setattr(r, 'git', lambda *args: b'' if args[0] == 'status' else b'a' * 40)
    monkeypatch.setattr(r, 'snapshot', lambda *args: fixture)
    calls = []
    def process(command, logfile, out):
        calls.append(command)
        logfile.write_text('unrelated assertion\n' if len(calls) == 3 else '')
        if command == ['mock_make']:
            binary = out / 'baseline/obj/Vtb'
            binary.parent.mkdir()
            binary.write_bytes(b'unexecuted test fixture')
        return 1 if len(calls) == 3 else 0
    monkeypatch.setattr(r, 'process', process)
    plan_path = tmp_path / 'plan.json'
    review = tmp_path / 'review.json'
    r.write(plan_path, plan)
    r.write(review, {})
    out = tmp_path / 'run'
    assert r.execute(plan_path, review, out) == 1
    assert len(calls) == 3
    assert not (out / 'must_not_start').exists()
    assert (out / 'baseline/obj/Vtb').exists()
    assert r.read(out / 'record.json')['stage'] == 'baseline/runtime_0'


def test_resource_event_not_accepted_as_negative(tmp_path, monkeypatch):
    events = iter([{'oom': 0}, {'oom': 1}])
    monkeypatch.setattr(r, 'memory_events', lambda: next(events))
    class Child:
        def poll(self):
            return 1
        def wait(self):
            return 1
    monkeypatch.setattr(r.subprocess, 'Popen', lambda *args, **kwargs: Child())
    with pytest.raises(ValueError, match='resource failure'):
        r.process(['not_executed'], tmp_path / 'runtime.log', tmp_path)
    assert r.read(tmp_path / 'runtime.process.json')['returncode'] == 1
