#!/usr/bin/env python3
"""Read actual DS ROM system completions against existing cached comparisons.

No simulator, model, checkpoint, preparation or expected-state injection. Token
intervals come only from TOK cycles in the same actual system clock. Heartbeat
PC snapshots cannot supply field issue/completion times or a composed calendar.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path

from tools.dsrom_reduced_token_binding import CachedReducedTokenBinding


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def observe(text, binding, *, terminal_rc=None):
    tokens, completions, done, errors, snapshots = {}, {}, [], [], []
    summary = None
    for line in text.splitlines():
        m = re.fullmatch(r'TOK user=(\d+) pos=(\d+) token=(\d+) cycle=(\d+)', line)
        if m:
            user, pos, token, cycle = map(int, m.groups())
            key = (user, pos)
            if key in tokens:
                errors.append('duplicate token ' + str(key))
                continue
            try:
                expected = binding.expected_output(user, pos)
            except ValueError:
                errors.append('unowned token ' + str(key))
                continue
            if token != expected:
                errors.append('cached token mismatch ' + str(key))
            tokens[key] = dict(user=user, position=pos, token=token,
                               expected_comparison_token=expected, cycle=cycle)
        m = re.fullmatch(r'CPL TOKEN tag=([0-9a-fA-F]+) user=(\d+) pos=(\d+) token=(\d+) stamp=(\d+)', line)
        if m:
            tag = int(m[1], 16)
            user, pos, token, stamp = map(int, m.groups()[1:])
            key = (user, pos)
            if key in completions:
                errors.append('duplicate host completion ' + str(key))
            if tag != 0x5a:
                errors.append('foreign completion tag ' + str(key))
            completions[key] = dict(token=token, stamp=stamp, tag=tag)
        m = re.fullmatch(r'CPL DONE tag=([0-9a-fA-F]+) users=(\d+) stamp=(\d+)', line)
        if m:
            done.append(line)
            if int(m[1], 16) != 0x5a or int(m[2]) != binding.users:
                errors.append('foreign DONE completion')
        if re.match(r'^(?:FAIL|TIMEOUT|WATCHDOG|SYS_FAULT|CPL ERROR|CPL_MISMATCH|MISMATCH|HOSTCQ_FAIL|KVHBM_FAIL|IDXHBM_FAIL)(?:\s|$)', line):
            errors.append(line)
        if line.startswith('HDC41_ARRAY '):
            if summary is not None:
                errors.append('duplicate terminal summary')
            summary = {k: int(v) for k, v in re.findall(r'(\w+)=(\d+)', line)}
        if line.startswith('HB '):
            snapshots.append({k: int(v) for k, v in re.findall(r'(\w+)=(\d+)', line)})
    rows = []
    for user in range(binding.users):
        previous = None
        for pos in range(binding.steps):
            key = (user, pos)
            if key not in tokens:
                continue
            row = dict(tokens[key])
            receipt = completions.get(key)
            if receipt is not None and receipt['token'] != row['token']:
                errors.append('host/device token mismatch ' + str(key))
            row['host_completion'] = receipt
            row['interval_from_previous_token_cycles'] = None
            row['input_token'] = None
            if pos < binding.plen:
                row['input_token'] = binding.input_token(user, pos)
            elif (previous is not None and previous['position'] == pos - 1
                  and previous['host_completion'] is not None):
                row['input_token'] = binding.input_token(user, pos,
                    previous_completion=(user, pos - 1, previous['token']))
            if previous is not None and previous['position'] == pos - 1:
                interval = row['cycle'] - previous['cycle']
                if interval <= 0:
                    errors.append('nonmonotonic token cycle ' + str(key))
                row['interval_from_previous_token_cycles'] = interval
            rows.append(row)
            previous = row
    expected_keys = {(u, p) for u in range(binding.users) for p in range(binding.steps)}
    complete = (set(tokens) == expected_keys and set(completions) == expected_keys)
    if set(completions) - set(tokens):
        errors.append('host completion lacks actual token')
    if summary is not None:
        required = dict(nodes=binding.nodes, users=binding.users,
                        generated=binding.users * binding.ngen,
                        mismatches=0, logit_mismatch=0, state_mismatch=0)
        for key, value in required.items():
            if summary.get(key) != value:
                errors.append('terminal summary mismatch ' + key)
        if summary.get('lm_head_checks', 0) <= 0 or summary.get('total_cycles', 0) <= 0:
            errors.append('terminal has no actual head checks or cycle extent')
    if terminal_rc is not None and terminal_rc != 0:
        errors.append('actual process failed: ' + str(terminal_rc))
    terminal = (terminal_rc == 0 and summary is not None
                and 'PASS' in text.splitlines() and len(done) == 1
                and 'USERS_DONE ' + str(binding.users) in text.splitlines())
    return dict(schema='opentallas.dsrom.actual_token_calendar.v1',
        verdict='REJECTED_ACTUAL_TOKEN_RECORD' if errors else
                'REDUCED_ACTUAL_TOKEN_COMPARISON_PASS' if terminal and complete else
                'INCOMPLETE_ACTUAL_TOKEN_RECORD',
        errors=errors, tokens=rows, actual_terminal_summary=summary,
        token_census_complete=complete, actual_terminal=terminal,
        heartbeat_snapshots=snapshots,
        first_token_latency_cycles=None,
        first_token_latency_scope='launch acceptance is not exported by this bench',
        numerical_field_scope='existing bench terminal mismatch counters only; Sagan owns raw-field qualification',
        field_calendar=None,
        field_calendar_scope='requires actual source-bound field issue/completion receipts; PC heartbeats are not intervals',
        clock_frequency_hz=None, full_shape_qualified=False, adopted=False)


def collect(scratch, name, log, *, gate_record=None):
    scratch, log = Path(scratch), Path(log)
    binding = CachedReducedTokenBinding(scratch, name)
    rc = None
    if gate_record is not None:
        record = json.loads(Path(gate_record).read_text())
        if record['config_name'] != name or record['config'] != binding.prep['config']:
            raise ValueError('terminal gate belongs to another cached configuration')
        rc = record.get('returncode')
    report = observe(log.read_text(), binding, terminal_rc=rc)
    paths = [scratch / ('prep_' + name + '.json'), scratch / ('svh_' + name + '.svh'),
             binding.img / 'prompts.hex', binding.img / 'expect_tokens.hex', log]
    paths += [binding.img / f'prog_stage{s:02d}.hex' for s in range(binding.nodes)]
    if gate_record is not None:
        paths.append(Path(gate_record))
        report['selected_source_sha256'] = record.get('input_sha256')
        report['actual_execution_command'] = record.get('execution_command')
        if record.get('execution_command'):
            paths.append(Path(record['execution_command'][0]))
    else:
        report['selected_source_sha256'] = binding.prep.get('input_sha256')
        report['actual_execution_command'] = None
    report['input_sha256'] = {str(p.resolve()): digest(p) for p in paths}
    report['cached_expected_scope'] = 'comparison only; generated inputs use previous actual completion'
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scratch', type=Path, required=True)
    parser.add_argument('--name', required=True)
    parser.add_argument('--log', type=Path, required=True)
    parser.add_argument('--gate-record', type=Path)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    report = collect(args.scratch, args.name, args.log, gate_record=args.gate_record)
    with args.out.open('x') as stream:
        stream.write(json.dumps(report, indent=2) + '\n')
    print(report['verdict'])
