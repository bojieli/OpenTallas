#!/usr/bin/env python3
"""Refresh the owner handoff; deliver once only after authenticated usage resets.

The monitor never disables Codex engineering timers. Sending a handoff is not
proof of takeover. A fresh nonce-bound Claude acknowledgment and new engineering
activity are required, and the coordinator still checks that evidence manually.
"""
import argparse
import collections
import datetime as dt
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import uuid
from zoneinfo import ZoneInfo

COORD = Path('/home/ubuntu/claude-takeover-20261007')
STATE = COORD / 'codex-claude-reset-watch.json'
SNAPSHOT = COORD / 'CODEX_TO_CLAUDE_20261010.json'
ACK = COORD / 'CLAUDE_TAKEOVER_ACK_20261010.json'
NEW_COORD = Path('/home/ubuntu/codex-takeover-20261010')
PANE = '%4'
REPO = Path(__file__).resolve().parents[2]
PACIFIC = ZoneInfo('America/Los_Angeles')
RESET = dt.datetime(2026, 10, 10, 12, tzinfo=PACIFIC)


def run(*args):
    return subprocess.check_output(args, text=True, stderr=subprocess.DEVNULL)


def atomic(path, value):
    tmp = path.with_name(path.name + '.tmp')
    tmp.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')
    tmp.replace(path)


def now():
    return dt.datetime.now(dt.timezone.utc)


def capture():
    return run('tmux', 'capture-pane', '-p', '-t', PANE, '-S', '-80')


def idle_empty(pane):
    prompts = list(re.finditer(r'^❯[^\n]*$', pane, re.M))
    if not prompts:
        return False
    prompt = prompts[-1]
    tail = pane[prompt.start():]
    before = pane[max(0, prompt.start() - 1500):prompt.start()]
    if re.search(r'^\s*[✻✽✶]\s+(?!Waiting\b)[^\n]*\([0-9]', before, re.M):
        return False
    return not prompt.group().lstrip('❯').strip() and 'esc to interrupt' not in tail.lower() and not re.search(r'^\s*[✻✽✶]\s+(?!Waiting\b)', tail, re.M)


def usage_percent(pane):
    m = re.search(r'Current week \(all models\)\s*\n[^\n]*?(\d+)% used', pane)
    return int(m.group(1)) if m else None


def snapshot(state):
    jobs = []
    statuses = collections.Counter()
    for file in sorted((Path.home()/'.local/state/closure_loop/jobs').glob('*.json')):
        try:
            d = json.loads(file.read_text())
        except (OSError, ValueError):
            continue
        statuses[d.get('status', 'unknown')] += 1
        if d.get('status') not in {'RUNNING', 'QUEUED', 'WAITING', 'READY', 'SYNC', 'ECO', 'CALIBRATING', 'BENCH'} and not re.search('bf[a-z_]|ecaae581c', d.get('name', '')):
            continue
        spec = d.get('spec') or {}
        jobs.append({key: d.get(key) for key in ('name', 'status', 'host', 'run', 'reason', 'publish')} | {'source': spec.get('source'), 'owner': spec.get('owner')})
    streams = []
    for file in sorted(list(COORD.glob('*.log')) + list(NEW_COORD.rglob('*.log')) + list(NEW_COORD.rglob('*.json')) + list(NEW_COORD.rglob('*.jsonl'))):
        if file.name.startswith('codex-claude-reset'):
            continue
        text = file.read_text(errors='replace')
        text = re.sub(r'(?:sk-(?:proj-|ant-)?[A-Za-z0-9_-]{20,}|AKIA[0-9A-Z]{16}|gh[pousr]_[A-Za-z0-9]{20,}|(?i:bearer)\s+[A-Za-z0-9_.-]{20,})', '[REDACTED_CREDENTIAL]', text)
        text = re.sub(r'-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----.*?-----END (?:RSA |OPENSSH |EC )?PRIVATE KEY-----', '[REDACTED_PRIVATE_KEY]', text, flags=re.S)
        collect = text.rfind('COLLECT')
        excerpt = text[collect:] if collect >= 0 else text[-8000:]
        streams.append({'path': str(file), 'modified_utc': dt.datetime.fromtimestamp(file.stat().st_mtime, dt.timezone.utc).isoformat(), 'latest_collect_or_tail': excerpt[-12000:], 'excerpt_truncated': len(excerpt) > 12000})
    obj = {'schema': 'opentallas.claude_handoff.v1', 'generated_utc': now().isoformat(), 'main_commit': run('git', '-C', str(REPO), 'rev-parse', 'main').strip(), 'origin_main_commit': run('git', '-C', str(REPO), 'rev-parse', 'origin/main').strip(), 'handoff_nonce': state['nonce'], 'handoff_status': state.get('status', 'monitoring_reset'), 'reset_expected': RESET.isoformat(), 'owner_instruction': 'Take over ALL Codex and prior Claude work after actual authenticated weekly reset. PVE2 and PVE3 are abandoned: do not probe/use them. Preserve progressing pinned jobs. Codex engineering continues until fresh Claude operation is verified.', 'instructions': ['/home/ubuntu/claude-takeover-20261007/CLAUDE_HANDOFF_20261010.md', '/home/ubuntu/OpenTallas/AGENTS.md', '/home/ubuntu/OpenTallas/docs/OWNER_DIRECTIVES_2026_10_07.md', '/home/ubuntu/claude-takeover-20261007/REVIEW_20261009.md'], 'pending_gates': ['BF full rate deadline 09:30 PT: collect current BF report; do not infer a pass from stale sidecar logs; require loop routed-insertion re-STA.', 'Service-segment adoption requires independent transaction scoreboard exact PASS, negatives killed, pinned same-source semantics. Prior ecaae581c svc records are HELD.', 'SM cg backend 80412d770 closures are real backend closures. Their original collection incorrectly pointed at tile_e; corrected isolated views plus exact bench a6d34a72e are merged on main. Gated SM tiles remain OPEN. Do not use backend closure as tile closure; follow latest sm_cg_finish and coordinator logs.', 'ATT d87e24872 is HELD: committed att_run.log predates routed pin-register RTL. Find same-source bench evidence before eligibility.', 'Do not disable Codex drive/review timers until takeover is verified; never interpret mere message delivery as confirmation.'], 'job_counts': dict(statuses), 'live_and_critical_jobs': jobs, 'streams': streams, 'coordination_logs_authoritative': True, 'current_codex_coordination_folder': str(NEW_COORD), 'priority_rule': 'Latest Codex coordinator/stream records supersede older COLLECT excerpts and static handoff caveats; independently inspect their pinned source and gates.', 'ack_path': str(ACK), 'ack_required_fields': ['nonce', 'acknowledged_utc', 'engineering_action_utc', 'registry_command', 'registry_output_path', 'registry_sha256', 'stream_log_path'], 'proof_required': 'A nonce-bound ACK plus a fresh Claude tool action, fresh registry output, and fresh stream engineering log. Coordinator independently verifies; the watcher never marks a sent message as takeover.'}
    atomic(SNAPSHOT, obj)


def event(state, message):
    with (COORD/'codex-claude-reset-watch.log').open('a') as f:
        f.write(now().isoformat() + ' ' + message + '\n')
    state['last_event'] = message
    state['updated_utc'] = now().isoformat()
    atomic(STATE, state)


def check_takeover(state, pane):
    if not ACK.exists():
        event(state, 'HANDOFF_SENT_AWAITING_ACK: Codex timers remain active')
        return
    try:
        ack = json.loads(ACK.read_text())
        sent = dt.datetime.fromisoformat(state['sent_utc'])
        stamp = dt.datetime.fromisoformat(ack['engineering_action_utc'])
        registry = Path(ack['registry_output_path']).resolve()
        stream = Path(ack['stream_log_path']).resolve()
        safe = registry.is_relative_to(COORD) and stream.is_relative_to(COORD)
        fresh = sent <= stamp <= now() and registry.stat().st_mtime >= sent.timestamp() and stream.stat().st_mtime >= sent.timestamp()
        sha_ok = hashlib.sha256(registry.read_bytes()).hexdigest() == ack['registry_sha256']
        command_ok = 'registry_gaps.py' in ack['registry_command'] and bool(re.search(r'^OPEN \d+', registry.read_text(), re.M)) and 'IDLE (open, no live job):' in registry.read_text()
        nonce_ok = ack['nonce'] == state['nonce'] and state['nonce'] in stream.read_text(errors='replace')
        # The pane must actually show a new engineering tool action after delivery.
        old = set(state.get('pane_before_lines', []))
        new_lines = [line for line in pane.splitlines() if line not in old]
        tool_activity = any(re.search(r'(Bash\(|Read\(|Write\(|Edit\(|Ran \d+ shell command|Read \d+ file|Wrote \d+ file)', line) for line in new_lines)
        if safe and fresh and sha_ok and command_ok and nonce_ok and tool_activity:
            state['status'] = 'takeover_evidence_ready_for_coordinator'
            state['ack'] = ack
            event(state, 'FRESH_ACK_AND_ENGINEERING_EVIDENCE: coordinator must independently verify before retiring Codex timers')
        else:
            state['ack_checks'] = {'safe_paths': safe, 'fresh': fresh, 'sha_ok': sha_ok, 'registry_command': command_ok, 'nonce': nonce_ok, 'fresh_tool_activity': tool_activity}
            event(state, 'ACK_NOT_YET_PROVEN: ' + json.dumps(state['ack_checks']))
    except (KeyError, ValueError, OSError, TypeError) as exc:
        event(state, 'ACK_INCOMPLETE: ' + type(exc).__name__)


def tick():
    state = json.loads(STATE.read_text()) if STATE.exists() else {'nonce': str(uuid.uuid4()), 'status': 'monitoring_reset', 'usage_confirmed_initial': {'weekly_all_models_pct': 100, 'reset': RESET.isoformat(), 'observed_utc': '2026-10-10T12:01:00+00:00'}}
    snapshot(state)
    pane = capture()
    if state.get('status') in {'handoff_sent', 'takeover_evidence_ready_for_coordinator'}:
        check_takeover(state, pane)
        return
    if state.get('status') == 'delivery_reserved':
        event(state, 'DELIVERY_UNCERTAIN: inspect pane manually; never resend automatically')
        return
    if now().astimezone(PACIFIC) < RESET:
        event(state, 'WAITING_ACTUAL_RESET: 12:00pm PT; snapshot refreshed; Codex engineering remains active')
        return
    if state.get('status') == 'usage_requested':
        pct = usage_percent(pane)
        if pct is None:
            event(state, 'USAGE_NOT_VISIBLE: hold handoff, no prompt interleave')
            return
        state['last_usage'] = {'weekly_all_models_pct': pct, 'observed_utc': now().isoformat()}
        run('tmux', 'send-keys', '-t', PANE, 'Escape')
        state['status'] = 'usage_checked_reset' if pct < 100 else 'monitoring_reset'
        event(state, 'AUTHENTICATED_USAGE_CHECK: ' + str(pct) + '%; handoff still unsent')
        return
    if not idle_empty(pane):
        event(state, 'PANE_BUSY_OR_NONEMPTY: no commands interleaved')
        return
    if state.get('status') != 'usage_checked_reset':
        run('tmux', 'send-keys', '-t', PANE, '-l', '/usage')
        run('tmux', 'send-keys', '-t', PANE, 'Enter')
        state['status'] = 'usage_requested'
        event(state, 'USAGE_REQUESTED_AT_IDLE_EMPTY_PROMPT')
        return
    message = f"[Owner-authorized Codex handoff] Your authenticated weekly usage reset is confirmed. Take over ALL work now. Read {SNAPSHOT} first, then the latest COLLECT sections and owner rules it names. PVE2/3 are abandoned. Preserve progressing pinned jobs. Run gaps/registry_gaps.py now, give every IDLE element an action, and resume highest-risk work; establish your own 30-minute drive and hourly review. Before declaring takeover write {ACK}: nonce={state['nonce']}, acknowledged_utc, engineering_action_utc, registry_command, fresh registry_output_path inside {COORD}, registry_sha256, stream_log_path inside {COORD}. Record this nonce and a concrete engineering action in that stream log. Explicitly acknowledge ALL stream ownership. Codex timers remain active until fresh acknowledgment and real engineering tool activity are independently verified. Sending this message alone is not takeover."
    state['status'] = 'delivery_reserved'
    state['delivery_reserved_utc'] = now().isoformat()
    state['pane_before_lines'] = pane.splitlines()
    atomic(STATE, state)
    # Single tmux buffer paste avoids shell interpolation and partial key typing.
    buf = 'codex-claude-handoff-' + state['nonce']
    subprocess.run(['tmux', 'load-buffer', '-b', buf, '-'], input=message, text=True, check=True)
    run('tmux', 'paste-buffer', '-d', '-b', buf, '-t', PANE)
    run('tmux', 'send-keys', '-t', PANE, 'Enter')
    state['status'] = 'handoff_sent'
    state['sent_utc'] = now().isoformat()
    event(state, 'HANDOFF_DELIVERED_EXACTLY_ONCE: awaiting fresh Claude engineering evidence; Codex timers remain active')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--snapshot-only', action='store_true')
    args = parser.parse_args()
    COORD.mkdir(exist_ok=True)
    with (COORD/'codex-claude-reset-watch.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if args.snapshot_only:
            state = json.loads(STATE.read_text()) if STATE.exists() else {'nonce': str(uuid.uuid4()), 'status': 'monitoring_reset'}
            atomic(STATE, state)
            snapshot(state)
        else:
            tick()
