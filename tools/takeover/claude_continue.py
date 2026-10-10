#!/usr/bin/env python3
"""Persistent, non-LLM continuation cadence after the single initial handoff.

No usage checks, logins, quota workarounds, initial handoff, or Codex timer changes.
The handoff lock serializes this sender with handoff_watch. Every tick records its
outcome, including quota-limited, busy, duplicate, and pre-handoff skips. A reserve
is durable before typing, so an interrupted delivery is never repeated in its slot.
"""
import argparse
import datetime as dt
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

try:
    from . import handoff_watch as H
except ImportError:
    import handoff_watch as H

STATE = H.COORD / 'claude-continue.json'
LOG = H.COORD / 'claude-continue.jsonl'
LOCK = H.COORD / 'claude-continue.lock'
ALLOWED = {'handoff_sent', 'takeover_evidence_ready_for_coordinator', 'evidence_ready'}
INTERVAL_SECONDS = 1800


def prompt_status(pane):
    """Classify current input, prioritizing live busy signals over old errors.

    Terminal history can retain both rate errors and prior spinner lines. Only
    the latest prompt and current footer can establish an empty prompt. Within
    the latest turn, a completion/limit after a spinner makes that spinner old.
    Remote shells and background-agent listings are not foreground generation.
    """
    prompts = list(re.finditer(r'^❯[^\n]*$', pane, re.M))
    if not prompts:
        return 'no_prompt'
    current = prompts[-1]
    if current.group()[1:].strip():
        return 'partial_input'
    footer = pane[current.end():]
    if 'esc to interrupt' in footer.lower():
        return 'busy'
    # Wrapped/multiline input may begin on the next line of an empty ❯.
    # Claude's horizontal input separator marks the start of status chrome.
    separator = re.search(r'^\s*[─━]{3,}', footer, re.M)
    if separator and footer[:separator.start()].strip():
        return 'partial_input'
    # Previous prompt delimits the current turn, excluding older quota history.
    start = prompts[-2].end() if len(prompts) > 1 else 0
    turn = pane[start:current.start()]
    signals = []
    for m in re.finditer(r'^\s*[✻✽✶]\s+[^\n]+', turn + footer, re.M):
        line = m.group()
        if re.search(r'\bdone\b|\bWaiting\b', line, re.I):
            signals.append((m.start(), 'idle'))
        else:
            signals.append((m.start(), 'busy'))
    for m in re.finditer(r"Goal paused|usage limit reached|You've hit[^\n]*limit|API Error[^\n]*(?:429|rate_limit)|Interrupted ·", turn, re.I):
        signals.append((m.start(), 'idle'))
    if signals and max(signals)[1] == 'busy':
        return 'busy'
    limited = bool(re.search(r"You've hit[^\n]*limit|usage limit reached|rate_limit|HTTP 429", turn, re.I))
    return 'limited_idle' if limited else 'idle'


def record(outcome, stamp, **fields):
    obj = {'time_utc': stamp.isoformat(), 'outcome': outcome, **fields}
    LOG.parent.mkdir(parents=True, exist_ok=True)
    line = (json.dumps(obj, sort_keys=True) + '\n').encode()
    fd = os.open(LOG, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
    try:
        os.write(fd, line)
    finally:
        os.close(fd)
    print(json.dumps(obj, sort_keys=True))
    return obj


def message(stamp):
    return (f'continue [Owner-authorized 30-minute continuation, {stamp.isoformat()}]. '
            f'Continue ALL Codex and prior Claude streams using the latest {H.SNAPSHOT} '
            'and authoritative coordinator/COLLECT records. Preserve progressing pinned jobs. '
            'Run registry_gaps.py, give every IDLE element an action, collect and merge/push '
            'bench-verified closures, and continue the highest-risk engineering with measured '
            'resource admission. Keep the 30-minute drive and hourly fleet/progress/48h review. '
            'PVE2 and PVE3 remain abandoned. Follow current owner decisions and held exactness '
            'gates; do not infer adoption from stale evidence. This is a continuation, not a '
            'new initial handoff. Respect quota/authentication limits; do not bypass them. '
            'Codex cadence remains active until the coordinator independently verifies takeover.')


def tick(stamp=None, capture_fn=None, load_fn=None, run_fn=None):
    stamp = stamp or H.now()
    capture_fn = capture_fn or H.capture
    run_fn = run_fn or H.run
    load_fn = load_fn or (lambda buf, text: subprocess.run(
        ['tmux', 'load-buffer', '-b', buf, '-'], input=text, text=True, check=True,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL))
    try:
        handoff = json.loads(H.STATE.read_text()) if H.STATE.exists() else {}
        state = json.loads(STATE.read_text()) if STATE.exists() else {}
    except (OSError, ValueError):
        return record('STATE_UNREADABLE', stamp)
    if stamp.astimezone(H.PACIFIC) < H.RESET:
        return record('BEFORE_NOON_RESET', stamp)
    status = handoff.get('status')
    if status not in ALLOWED:
        return record('INITIAL_HANDOFF_NOT_CONFIRMED', stamp, handoff_status=status)
    # Bind deduplication to the initial handoff identity; never write its state.
    nonce = handoff.get('nonce')
    if not isinstance(nonce, str) or not nonce:
        return record('HANDOFF_NONCE_MISSING', stamp)
    slot = int(stamp.timestamp()) // INTERVAL_SECONDS
    if state.get('handoff_nonce') == nonce:
        if state.get('last_slot') == slot:
            return record('DUPLICATE_SLOT', stamp, slot=slot)
        try:
            previous = dt.datetime.fromisoformat(state['reserved_utc'])
            if (stamp - previous).total_seconds() < INTERVAL_SECONDS:
                return record('CADENCE_NOT_DUE', stamp, slot=slot)
        except (KeyError, ValueError, TypeError):
            pass
    try:
        pane = capture_fn()
    except (OSError, subprocess.SubprocessError):
        return record('PANE_UNAVAILABLE', stamp)
    observed = prompt_status(pane)
    if observed not in {'idle', 'limited_idle'}:
        return record('PANE_NOT_IDLE_EMPTY', stamp, prompt_status=observed)
    text = message(stamp)
    state.update(handoff_nonce=nonce, last_slot=slot, reserved_utc=stamp.isoformat(),
                 status='delivery_reserved', prompt_status=observed,
                 message_sha256=hashlib.sha256(text.encode()).hexdigest())
    H.atomic(STATE, state)
    # Buffer name uses a hash, not an untrusted nonce as a command or shell string.
    buf = 'claude-continue-' + hashlib.sha256(nonce.encode()).hexdigest()[:12] + '-' + str(slot)
    try:
        load_fn(buf, text)
        # Recheck after buffer load: never overwrite text entered during preparation.
        recheck = prompt_status(capture_fn())
        if recheck not in {'idle', 'limited_idle'}:
            run_fn('tmux', 'delete-buffer', '-b', buf)
            state['status'] = 'prompt_changed_before_paste'
            H.atomic(STATE, state)
            return record('PROMPT_CHANGED_NO_PASTE', stamp, slot=slot, prompt_status=recheck)
        run_fn('tmux', 'paste-buffer', '-d', '-b', buf, '-t', H.PANE)
        run_fn('tmux', 'send-keys', '-t', H.PANE, 'Enter')
    except (OSError, subprocess.SubprocessError):
        # A paste may already have happened. Keep its durable reservation; no retry.
        return record('DELIVERY_UNCERTAIN_RESERVED', stamp, slot=slot)
    state['status'] = 'continuation_sent'
    state['sent_utc'] = stamp.isoformat()
    H.atomic(STATE, state)
    return record('CONTINUATION_SENT', stamp, slot=slot, prompt_status=observed)


def main():
    argparse.ArgumentParser(description=__doc__).parse_args()
    H.COORD.mkdir(parents=True, exist_ok=True)
    with (H.COORD / 'codex-claude-reset-watch.lock').open('a') as initial_lock, LOCK.open('a') as own_lock:
        try:
            fcntl.flock(initial_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            fcntl.flock(own_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            record('SENDER_LOCK_BUSY', H.now())
            return 0
        tick()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
