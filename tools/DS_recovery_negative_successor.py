#!/usr/bin/env python3
"""Prepare and execute the source-bound DS recovery successor, without resource caps.

prepare is read-only with respect to old artifacts and never invokes a compiler.
execute requires a reviewed inventory and disjoint capacity reservation. Outputs
are exclusive, incremental and retained on failure; simulation liveness is RTL's.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import resource
import shutil
import socket
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
TOOL = Path(__file__).resolve()
CONTRACT = ROOT / 'results/uarch/DS_recovery_negative_successor_20261002/contract.json'
BENCH = ROOT / 'rtl/test/DS_recovery_negative_successor/tb.sv'
SIZING = ROOT / 'results/uarch/DS_recovery_negative_successor_20261002/model.json'
WITNESS_FIELDS = ('cycles fault_cycle checking pc stopped_pc rec_active suffix_closed '
                  'qe_idle win_idle qe_accepts terminals vm_stores sink_words '
                  'written_words su_accepts suppress su_idle xs_we kv_we').split()


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def write(path, value):
    with Path(path).open('x') as f:
        json.dump(value, f, indent=2)
        f.write('\n')
        f.flush()
        os.fsync(f.fileno())


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)


def source_bytes(path, model):
    if path in model['original_source_sha256']:
        return git('show', model['pin'] + ':' + path)
    return (ROOT / path).read_bytes()


def tool_identity(path):
    path = Path(path).resolve(strict=True)
    return {'path': str(path), 'sha256': sha(path)}


def tools_identity(parent):
    wrapper = Path(parent['compiler']['wrapper']).resolve(strict=True)
    kit = wrapper.parent.parent / 'share/verilator/include'
    if not kit.is_dir():
        raise ValueError('Verilator runtime inventory absent')
    return {'verilator': tool_identity(wrapper),
            'verilator_bin': tool_identity(wrapper.parent / 'verilator_bin'),
            **{name: tool_identity(shutil.which(name)) for name in ('make', 'g++', 'ar', 'perl')},
            'runtime': {str(p): sha(p) for p in sorted(kit.rglob('*'))
                        if p.is_file() and p.suffix in ('.h', '.cpp', '.mk')}}


def mutated(data, mutation):
    text = data.decode()
    start = 0 if mutation.get('target') == 'bench' else text.index('module ot_hdc_core_v41x_cancel_fastpp_enabled #(')
    if text[start:].count(mutation['old']) != 1:
        raise ValueError('mutation not unique in selected body')
    return (text[:start] + text[start:].replace(mutation['old'], mutation['new'], 1)).encode()


def snapshot(label, contract, parent, model):
    result = {}
    for path, expected in parent['source_files_sha256'].items():
        data = source_bytes(path, model)
        if hashlib.sha256(data).hexdigest() != expected:
            raise ValueError('historical source pin ' + path)
        result[path] = data
    result['tb.sv'] = BENCH.read_bytes()
    if label != 'baseline':
        case = next(c for c in contract['cases'] if c['label'] == label)
        target = 'tb.sv' if case['mutation'].get('target') == 'bench' else model['runtime_cone_path']
        result[target] = mutated(result[target], case['mutation'])
    return result


def negative_ok(label, w):
    if w['cycles'] < w['fault_cycle']:
        return False
    if label == 'physical_QE_gate':
        return w['qe_accepts'] >= 1 and (w['rec_active'] == 1 or w['suffix_closed'] == 0 or
                                        w['qe_idle'] == 0 or w['win_idle'] == 0)
    if label == 'PC_advance':
        return w['checking'] == 1 and w['pc'] != w['stopped_pc']
    if label == 'VM_frozen_store_drop':
        return (w['qe_accepts'] == 1 and w['terminals'] == 16 and w['vm_stores'] == 16 and
                0 <= w['sink_words'] < 512 and 0 <= w['written_words'] < 512)
    if label == 'scalar_suppression':
        return (w['su_accepts'] == 1 and w['suppress'] == 1 and w['su_idle'] == 0 and
                (w['xs_we'] == 1 or w['kv_we'] == 1))
    return False


def verify_negative(case, code, text, source_dir):
    # Deliberately anchored: extra errors, wrong locations, signals, missing live
    # values, unknown bits and alternate assertions cannot qualify this case.
    fields = ' '.join(re.escape(k) + r'=([0-9]+)' for k in WITNESS_FIELDS)
    site = case['fatal_line']
    pattern = (r'\AW17_RECOVERY_WITNESS ' + re.escape(case['label']) + ' ' + fields +
               r'\n\[([0-9]+)\] %Fatal: tb\.sv:' + str(site) +
               r': Assertion failed in tb: ' + re.escape(case['fatal_marker']) +
               r'\n%Error: ' + re.escape(str(Path(source_dir) / 'tb.sv')) + ':' + str(site) +
               r': Verilog \$stop\nAborting\.\.\.\n\Z')
    match = re.fullmatch(pattern, text)
    if code != case['expected_exit'] or not match:
        raise ValueError('unrelated failure or missing exact source-bound refusal receipt')
    w = dict(zip(WITNESS_FIELDS, map(int, match.groups()[:-1])))
    for key in ('checking', 'rec_active', 'suffix_closed', 'qe_idle', 'win_idle',
                'suppress', 'su_idle', 'xs_we', 'kv_we'):
        if w[key] not in (0, 1):
            raise ValueError('nonbinary witness ' + key)
    if not negative_ok(case['label'], w):
        raise ValueError('fatal has no declared invariant violation and mutation witness')
    return {'verdict': 'EXPECTED_MUTATION_REFUSAL', 'witness': w,
            'fatal_time': int(match.groups()[-1]), 'fatal_line': site}


def verify_positive(case, code, text):
    # Require the complete original semantic counters, including PREFIX identity.
    pattern = (r'ACTUAL_CORE_CANCEL_PASS cut=([A-Z_]+) prefix=([0-9]+) qe=([0-9]+) '
               r'terminal=([0-9]+) vm=([0-9]+) capture=([0-9]+) blocks=([0-9]+) '
               r'acceptedWR=([0-9]+) faultcycle=([0-9]+) localACKcycle=([0-9]+) '
               r'suppressed=([0-9]+) sinkWords=([0-9]+) frozenFrames=([0-9]+)')
    matches = re.findall(pattern, text)
    if code != 0 or len(matches) != 1 or re.search(r'%Error|%Fatal|Assertion failed|W17_RECOVERY_WITNESS', text):
        raise ValueError('positive control failed')
    cut, prefix, qe, terminal, vm, capture, blocks, writes, fault, ack, suppressed, words, frozen = matches[0]
    if cut != case['CUT'] or ('PREFIX' in case and int(prefix) != case['PREFIX']):
        raise ValueError('positive control identity')
    if int(qe) != (0 if cut in ('ISSUE', 'GO') else 1):
        raise ValueError('positive acceptance count')
    expected = 0 if cut in ('ISSUE', 'GO') else 16
    if int(terminal) != expected or int(vm) != expected or int(words) != (512 if expected else 0):
        raise ValueError('positive suffix counters')
    if int(ack) <= int(fault) or (cut == 'SU_SUFFIX' and int(suppressed) == 0):
        raise ValueError('positive liveness/suppression coverage')
    return {'verdict': 'POSITIVE_CONTROL_PASS', 'cut': cut, 'prefix': int(prefix)}


def plan_object():
    c = read(CONTRACT)
    parent = read(ROOT / c['parent_plan'])
    model = read(ROOT / c['parent_model'])
    if len(parent['source_files_sha256']) != 163 or len(model['cases']) != 23 or len(c['cases']) != 4:
        raise ValueError('campaign inventory changed')
    for case in c['cases']:
        if case['mutation'] != model['future_mutants'][case['label']]:
            raise ValueError('mutation contract drift')
    jobs = []
    template = parent['jobs'][1]['frontend_command']
    for label in ['baseline'] + [case['label'] for case in c['cases']]:
        files = snapshot(label, c, parent, model)
        bench = files['tb.sv'].decode().splitlines()
        cases = model['cases'] if label == 'baseline' else [next(x for x in c['cases'] if x['label'] == label).copy()]
        if label != 'baseline':
            marker = '$fatal(1,"' + cases[0]['fatal_marker'] + '")'
            hits = [i for i, line in enumerate(bench, 1) if marker in line]
            if len(hits) != 1:
                raise ValueError('unique fatal site required')
            cases[0]['fatal_line'] = hits[0]
        frontend = [x.replace('{out}/physical_QE_gate', '{run}/' + label) for x in template]
        make = [x.replace('{out}/physical_QE_gate', '{run}/' + label) for x in parent['jobs'][1]['CXX_command']]
        jobs.append({'label': label, 'files_sha256': {p: hashlib.sha256(data).hexdigest() for p, data in files.items()},
                     'frontend_command': frontend, 'CXX_command': make, 'cases': cases})
    diagnosis = 'results/uarch/native_software_parent_intake_20261002/DS_core_recovery_negative_receipt_diagnosis.json'
    return {'status': 'PREPARED_NOT_COMPILED', 'schema': c['schema'], 'base_commit': c['base_commit'],
            'contract_sha256': sha(CONTRACT), 'runner_sha256': sha(TOOL), 'bench_sha256': sha(BENCH),
            'sizing_model_sha256': sha(SIZING),
            'historical_inputs_sha256': {p: sha(ROOT / p) for p in (c['parent_plan'], c['parent_model'], diagnosis)},
            'geometry': c['geometry'], 'allocation': c['allocation'], 'hardware_delta': c['hardware_delta'],
            'toolchain': tools_identity(parent), 'jobs': jobs, 'compile_phases': 5,
            'runtime_cases': 27, 'retained_binary_eligible': False,
            'retained_refusal_reason': 'Instrumented tb.sv differs; historical source/tool/args cannot match.',
            'protocol_liveness_checks_preserved': True, 'resource_policy': c['resource_policy'],
            'runtime_qualification': False, 'fulltoken': False, 'adoption': False}


def host_context(out):
    mem = {line.split(':')[0]: int(line.split()[1]) * 1024 for line in Path('/proc/meminfo').read_text().splitlines() if line.startswith(('MemAvailable:', 'MemTotal:'))}
    return {'hostname': socket.gethostname(), 'memory': mem, 'disk_free_bytes': shutil.disk_usage(out).free,
            'affinity': sorted(os.sched_getaffinity(0)),
            'processes': subprocess.check_output(['ps', '-eo', 'pid,pcpu,rss,comm', '--sort=-rss'], text=True),
            'inherited_rlimits': {name: list(resource.getrlimit(getattr(resource, name)))
                                 for name in ('RLIMIT_CPU', 'RLIMIT_FSIZE', 'RLIMIT_AS')},
            'user_services': subprocess.run(['systemctl', '--user', 'list-units', '--type=service', '--state=running', '--no-pager'], capture_output=True, text=True).stdout}


def prepare(out):
    p = plan_object()
    out.mkdir(parents=True, exist_ok=False)
    write(out / 'plan.json', p)
    write(out / 'host_context.json', host_context(out))
    write(out / 'review_template.json', {'status': 'PENDING_MODEL_RESOURCE_CONTEXT_REVIEW',
          'plan_sha256': sha(out / 'plan.json'), 'host_context_sha256': sha(out / 'host_context.json'),
          'hostname': socket.gethostname(), 'reserved_CPUs': [], 'active_job_CPUs': [],
          'reserved_memory_bytes': None, 'reserved_disk_bytes': None,
          'measured_memory_peak_bytes': None, 'measured_output_peak_bytes': None,
          'inventory_evidence': [], 'reservation_evidence': [], 'reviewer': None})
    return p


def validate_review(review, plan_path, run):
    p = read(plan_path)
    r = read(review)
    if p != plan_object():
        raise ValueError('plan/source/tool/arguments changed')
    if r['status'] != 'MODEL_RESOURCE_CONTEXT_REVIEWED' or r['plan_sha256'] != sha(plan_path):
        raise ValueError('source-bound model/resource/context review required')
    context = Path(plan_path).parent / 'host_context.json'
    if r['host_context_sha256'] != sha(context) or r['hostname'] != socket.gethostname() or not r['reviewer']:
        raise ValueError('review host/context identity')
    cpus = r['reserved_CPUs']
    if (len(set(cpus)) != len(cpus) or len(cpus) < 2 or
            set(cpus) & set(r['active_job_CPUs']) or not set(cpus) <= os.sched_getaffinity(0)):
        raise ValueError('disjoint CPU reservation required')
    for key in ('measured_memory_peak_bytes', 'measured_output_peak_bytes', 'reserved_memory_bytes', 'reserved_disk_bytes'):
        if type(r[key]) is not int or r[key] <= 0:
            raise ValueError('measured inventory/capacity absent ' + key)
    if r['reserved_memory_bytes'] < r['measured_memory_peak_bytes'] or r['reserved_disk_bytes'] < r['measured_output_peak_bytes']:
        raise ValueError('reservation smaller than measured inventory')
    for key in ('inventory_evidence', 'reservation_evidence'):
        if not r[key]:
            raise ValueError('review needs actual evidence ' + key)
        for e in r[key]:
            if sha(e['path']) != e['sha256']:
                raise ValueError('resource evidence identity')
    # A scheduler reservation is reviewed evidence, not a guessed process limit.
    current = host_context(run)
    if current['memory']['MemAvailable'] < r['reserved_memory_bytes'] or current['disk_free_bytes'] < r['reserved_disk_bytes']:
        raise ValueError('actual headroom below reviewed reservation')
    if any(tuple(current['inherited_rlimits'][k]) != (resource.RLIM_INFINITY, resource.RLIM_INFINITY)
           for k in current['inherited_rlimits']):
        raise ValueError('inherited arbitrary CPU/file/address-space cap')
    return p, r


def memory_events():
    relative = next(line.split('::', 1)[1].strip() for line in Path('/proc/self/cgroup').read_text().splitlines() if line.startswith('0::'))
    path = Path('/sys/fs/cgroup') / relative.lstrip('/') / 'memory.events'
    return {key: int(value) for key, value in (line.split() for line in path.read_text().splitlines())}


def capacity_sample(run):
    mem = next(int(line.split()[1]) * 1024 for line in Path('/proc/meminfo').read_text().splitlines() if line.startswith('MemAvailable:'))
    return {'monotonic': time.monotonic(), 'memory_available_bytes': mem,
            'disk_free_bytes': shutil.disk_usage(run).free}


def process(command, log, run):
    # No timeout, setrlimit, RuntimeMax or file/address-space/CPU quota. Monitor
    # actual capacity without killing or restarting a progressing pinned job.
    before = memory_events()
    with log.open('xb') as f:
        child = subprocess.Popen(command, stdout=f, stderr=subprocess.STDOUT)
        try:
            with (run / 'capacity_samples.jsonl').open('a') as samples:
                while child.poll() is None:
                    samples.write(json.dumps(capacity_sample(run)) + '\n')
                    samples.flush()
                    time.sleep(1)
            code = child.wait()
        except BaseException:
            # Do not allow an interrupted runner to orphan a build while a new
            # owner assumes it is safe to retry. Record the PID; never restart.
            write(run / 'interrupted_child.json', {'pid': child.pid, 'command': command, 'retry': False})
            raise
        f.flush()
        os.fsync(f.fileno())
    after = memory_events()
    write(log.with_suffix('.process.json'), {'command': command, 'returncode': code,
          'log_sha256': sha(log), 'memory_events_before': before, 'memory_events_after': after})
    if any(after.get(k, 0) != before.get(k, 0) for k in ('max', 'oom', 'oom_kill', 'oom_group_kill')):
        raise ValueError('resource failure is not a mutation refusal')
    return code


def reusable(artifact, job, toolchain, commands):
    if (artifact['source_files_sha256'] != job['files_sha256'] or
            artifact['toolchain'] != toolchain or artifact['commands'] != commands or
            sha(artifact['binary_path']) != artifact['binary_sha256']):
        raise ValueError('retained binary lacks exact source/tool/args identity')
    return True


def execute(plan_path, review, out):
    out.mkdir(parents=True, exist_ok=False)
    stage = 'review'
    receipts = []
    try:
        p, r = validate_review(review, plan_path, out)
        if git('status', '--porcelain').strip():
            raise ValueError('clean pinned worktree required')
        for key in ('CC', 'CXX', 'CFLAGS', 'CXXFLAGS', 'CPPFLAGS', 'LDFLAGS', 'MAKEFLAGS', 'MFLAGS', 'LD_PRELOAD', 'LD_LIBRARY_PATH', 'VERILATOR_ROOT', 'VERILATOR_BIN'):
            if os.environ.get(key):
                raise ValueError('unbound build environment ' + key)
        write(out / 'launch.json', {'commit': git('rev-parse', 'HEAD').decode().strip(),
              'plan_sha256': sha(plan_path), 'review_sha256': sha(review), 'runner_sha256': sha(TOOL),
              'hostname': socket.gethostname(), 'no_retry': True})
        os.sched_setaffinity(0, r['reserved_CPUs'])
        c = read(CONTRACT)
        parent = read(ROOT / c['parent_plan'])
        model = read(ROOT / c['parent_model'])
        for job in p['jobs']:
            label = job['label']
            stage = label + '/snapshot'
            home = out / label
            src = home / 'sources'
            src.mkdir(parents=True)
            files = snapshot(label, c, parent, model)
            for path, data in files.items():
                target = src / path
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
            actual = {str(x.relative_to(src)): sha(x) for x in src.rglob('*') if x.is_file()}
            if actual != job['files_sha256']:
                raise ValueError('snapshot identity')
            write(home / 'snapshot_sha256.json', actual)
            commands = {k: [x.format(run=str(out.resolve())) for x in job[k]] for k in ('frontend_command', 'CXX_command')}
            for phase, command in commands.items():
                stage = label + '/' + phase
                write(home / (phase + '_started.json'), {'command': command, 'toolchain_digest': digest(p['toolchain'])})
                code = process(command, home / (phase + '.log'), out)
                if code != 0:
                    raise ValueError('build failure: ' + stage + ' exit=' + str(code))
                if phase == 'frontend_command' and '%Warning-UNOPTFLAT:' in (home / (phase + '.log')).read_text():
                    raise ValueError('UNOPTFLAT; no runtime qualification')
            binary = home / 'obj/Vtb'
            artifact = {'source_files_sha256': actual, 'toolchain': p['toolchain'], 'commands': commands,
                        'binary_path': str(binary.resolve()), 'binary_sha256': sha(binary)}
            write(home / 'artifact.json', artifact)
            reusable(artifact, job, p['toolchain'], commands)
            for index, case in enumerate(job['cases']):
                stage = label + '/runtime_' + str(index)
                if label == 'baseline':
                    args = ['+CUT=' + case['CUT']] + (['+PREFIX=' + str(case['PREFIX'])] if 'PREFIX' in case else [])
                else:
                    args = case['args']
                log = home / ('runtime_' + str(index) + '.log')
                code = process([str(binary.resolve()), *args], log, out)
                if sha(binary) != artifact['binary_sha256'] or any(sha(src / path) != h for path, h in actual.items()):
                    raise ValueError('runtime source/binary identity changed')
                receipt = verify_positive(case, code, log.read_text()) if label == 'baseline' else verify_negative(case, code, log.read_text(), src.resolve())
                receipt.update(stage=stage, args=args, returncode=code, log_sha256=sha(log),
                               binary_sha256=artifact['binary_sha256'], snapshot_digest=digest(actual))
                write(home / ('runtime_' + str(index) + '_receipt.json'), receipt)
                receipts.append(receipt)
        write(out / 'record.json', {'verdict': 'PASS_SUCCESSOR_RECOVERY_SIMULATION_ONLY', 'receipts': receipts,
              'historical_full27_verdict': 'FAIL_UNCHANGED', 'plan_sha256': sha(plan_path),
              'runtime_qualification': True, 'fulltoken': False, 'adoption': False, 'hardware_admitted': False})
        return 0
    except BaseException as error:
        write(out / 'record.json', {'verdict': 'FAIL_SUCCESSOR_PRESERVED', 'stage': stage,
              'error': repr(error), 'receipts': receipts, 'no_retry': True,
              'historical_full27_verdict': 'FAIL_UNCHANGED', 'runtime_qualification': False})
        return 1


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest='action', required=True)
    prep = sub.add_parser('prepare')
    prep.add_argument('--out', type=Path, required=True)
    run = sub.add_parser('execute')
    run.add_argument('--plan', type=Path, required=True)
    run.add_argument('--review', type=Path, required=True)
    run.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    if a.action == 'prepare':
        prepare(a.out)
        return 0
    return execute(a.plan, a.review, a.out)


if __name__ == '__main__':
    raise SystemExit(main())
