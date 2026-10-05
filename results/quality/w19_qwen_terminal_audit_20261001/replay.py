"""Bounded retained-output audit; never executes checkpoint arithmetic or an engine."""
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import numpy as np

PARENT = '167bc968a47f8be29e3c9d79cb2e01e36d7194ff'
PARENT_PATH = 'results/quality/parent_qwen_hbm_two_token_terminal_review_20261001/review.json'

def digest(data):
    return hashlib.sha256(data).hexdigest()

def require(condition, message):
    if not condition:
        raise ValueError(message)

def memory_order(events):
    pending, published, leases = {}, set(), {}
    reads = {1: 0, 2: 0}
    for event in events:
        require(event['cycles'] is None, 'unqualified software calendar')
        kind = event['event']
        if kind == 'write_accepted_not_published':
            tag = event['tag']
            require(tag not in pending, 'duplicate write tag')
            pending[tag] = (event['layer'], event['die'], event['position'])
        elif kind == 'software_backing_commit_and_publication':
            require(event['tag'] in pending, 'publication before write')
            key = pending.pop(event['tag'])
            require(key not in published, 'duplicate publication')
            published.add(key)
        elif kind == 'persistent_KV_read':
            count = event['positions']
            require(count in reads, 'unexpected context')
            require(all((event['layer'], event['die'], position) in published
                        for position in range(count)), 'read before publication')
            reads[count] += 1
        elif kind == 'software_reader_lease_acquired':
            require(event['lease'] not in leases, 'duplicate lease')
            require((event['layer'], event['die'], event['position']) in published,
                    'lease before publication')
            leases[event['lease']] = set()
        elif kind == 'software_consumer_done_after_result':
            require(event['lease'] in leases, 'consumer without lease')
            stages = leases[event['lease']]
            require(event['stage'] in {'SCORES', 'PV'} and event['stage'] not in stages,
                    'invalid consumer stage')
            stages.add(event['stage'])
        elif kind == 'software_reader_lease_released':
            require(leases.get(event['lease']) == {'SCORES', 'PV'}, 'early lease release')
            del leases[event['lease']]
        else:
            raise ValueError('unknown event ' + kind)
    require(not pending and not leases, 'outstanding write or lease')
    require(len(published) == 144 and reads == {1: 72, 2: 72}, 'incomplete memory coverage')
    return dict(events=len(events), committed_publications=len(published),
                context1_reads=reads[1], context2_reads=reads[2], outstanding_leases=0,
                outstanding_writes=0)

def rejects(callback):
    try:
        callback()
    except ValueError as error:
        return str(error)
    raise ValueError('negative control unexpectedly accepted')

def main(repo):
    def git_bytes(revision, name):
        return subprocess.check_output(['git', 'show', revision + ':' + name], cwd=repo)
    parent_bytes = git_bytes(PARENT, PARENT_PATH)
    parent = json.loads(parent_bytes)
    root = Path(parent['artifact_root'])
    artifacts = {}
    for name, pin in parent['artifacts'].items():
        data = (root / name).read_bytes()
        require(len(data) == pin['bytes'] and digest(data) == pin['sha256'], 'artifact pin ' + name)
        artifacts[name] = pin
    for name, pin in parent['source_pins_verified'].items():
        require(digest(git_bytes(parent['source_commit'], name)) == pin, 'source pin ' + name)
    load = lambda name: json.loads((root / name).read_text())
    rc, terminal = load('execution_rc.json'), load('execution/terminal.json')
    require(rc['actual_returncode'] == 0 and rc['guard_breach'] is None, 'terminal RC/guard')
    require(rc['source_commit'] == parent['source_commit'], 'terminal source identity')
    require(terminal['status'] == 'CHECKPOINT_SOFTWARE_COMPLETE' and terminal['tokens_completed'] == 2,
            'terminal completion')
    require(not terminal['actual_RTL_executed'] and not terminal['fulltoken_RTL']
            and terminal['token_cycles'] is None and terminal['token_rate'] is None, 'qualification scope')
    hashes = {(r['position'], r['register']): r for r in load('execution/instruction_output_hashes.json')}
    comparisons, tokens, payloads, executions = [], [], {}, []
    for position in range(2):
        execution = load(f'execution/token{position}_execution.json')
        executions.append(execution)
        require(execution['status'] == 'SOFTWARE_PROGRAM_COMPLETED' and execution['fullshape']
                and execution['complete_program_executed'], 'software completion')
        require(execution['instructions_retired'] == len(execution['trace']) == 1737, 'retirement count')
        done = set()
        for index, instruction in enumerate(execution['trace']):
            require(instruction['id'] == index and set(instruction['dependencies']) <= done, 'dependency order')
            require(instruction['cycles'] is None, 'software instruction cycles')
            done.add(index)
        require(not execution['actual_RTL_executed'] and not execution['actual_hardware_memory_provider']
                and not execution['full_token_RTL'] and not execution['hardware_consumer_leases_qualified']
                and execution['token_cycles'] is None and execution['token_rate'] is None, 'execution qualification')
        require(execution['position'] == position, 'position identity')
        names = {f'L{layer}.X' for layer in range(36)} | {'head.norm', 'head.d0.scaled', 'head.d1.scaled'}
        cumulative_checks = execution['post_execution_comparisons']
        require(cumulative_checks[:len(comparisons)] == comparisons, 'comparison prefix')
        checks = cumulative_checks[len(comparisons):]
        require(len(checks) == 39 and {c['register'] for c in checks} == names, 'comparison coverage')
        require(all(c['bit_mismatches'] == c['actual_nonfinite'] == c['reference_nonfinite'] == 0
                    for c in checks), 'comparison failure')
        comparisons.extend(checks)
        def payload(name, register, shape):
            path = root / 'execution' / name
            data = path.read_bytes()
            payloads[name] = digest(data)
            array = np.load(path, allow_pickle=False)
            require(array.dtype == np.dtype('float32') and array.shape == shape
                    and np.isfinite(array).all(), 'payload shape/type/nonfinite')
            pin = hashes[position, register]
            require(pin['shape'] == list(shape) and digest(array.tobytes()) == pin['sha256'], 'payload trace pin')
            return array
        for layer in range(36):
            payload(f'token{position}_L{layer:02}.npy', f'L{layer}.X', (4096,))
        head = np.concatenate([payload(f'token{position}_head.d{die}.scaled.npy',
                                      f'head.d{die}.scaled', (75968,)) for die in range(2)])
        require(int(np.argmax(head)) == execution['next_token'], 'head argmax')
        token = dict(position=position, input_token=execution['input_token'], next_token=execution['next_token'],
                     instructions_retired=1737, head_fp32_sha256=digest(head.tobytes()))
        require(token == parent['tokens'][position], 'parent token proof')
        tokens.append(token)
    require(executions[1]['memory_events'][:len(executions[0]['memory_events'])]
            == executions[0]['memory_events'], 'cumulative memory event prefix')
    require(tokens[1]['input_token'] == tokens[0]['next_token'], 'token chain')
    require(terminal['next_token'] == tokens[-1]['next_token'], 'terminal token')
    require(comparisons == load('execution/post_execution_comparisons.json'), 'comparison file linkage')
    events = executions[1]['memory_events']
    memory = memory_order(events)
    require(memory == parent['software_memory_event_order_verified'], 'parent memory proof')
    early_read = copy.deepcopy(events)
    early_read[1], early_read[2] = early_read[2], early_read[1]
    early_release = copy.deepcopy(events)
    early_release[5], early_release[6] = early_release[6], early_release[5]
    priced = copy.deepcopy(events)
    priced[0]['cycles'] = 1
    negatives = dict(read_before_publication=rejects(lambda: memory_order(early_read)),
                     release_before_PV=rejects(lambda: memory_order(early_release)),
                     fabricated_software_cycles=rejects(lambda: memory_order(priced)))
    return dict(verdict='PASS_bounded_retained_terminal_provenance', parent_review_commit=PARENT,
                parent_review_sha256=digest(parent_bytes), source_commit=parent['source_commit'],
                actual_process_returncode=0, tokens=tokens, comparison_boundaries=78,
                comparisons_scope='Pinned harness results inspected; arithmetic NOT rerun',
                source_pins_verified=parent['source_pins_verified'], artifacts_verified=artifacts,
                retained_payload_file_sha256=payloads, software_memory_event_order_verified=memory,
                negative_controls=negatives, original_worker_present=Path('/proc/1425410').exists(),
                actual_RTL_executed=False, actual_hardware_memory_provider=False,
                whole_hardware_calendar_priced=False, physical_qualification=False,
                token_cycles=None, token_rate=None,
                limitations=['No checkpoint shard reread or independent scientific arithmetic rerun',
                             'Software publication order is not finite hardware credit/port/calendar evidence',
                             'Whole terminal archive remains exclusive Einstein owner scope'])

if __name__ == '__main__':
    print(json.dumps(main(Path(sys.argv[1])), indent=2, sort_keys=True))
