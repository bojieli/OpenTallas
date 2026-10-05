#!/usr/bin/env python3
"""Collect the existing job only; never launch numerical work or mutate it."""
import hashlib
import json
from pathlib import Path
import subprocess
import time

HERE = Path('/tmp/ampere-c0-pc40-payload-20261003')
DEST = HERE / 'terminal_collection'
ROOT = Path('/tmp/opentallas-c0-pc40-payload-lease-20261003')
REMOTE = '/home/ubuntu/otjobs/ampere-c0-pc40-payload-20261003-r1'
UNIT = 'ampere-c0-pc40-payload-20261003-r1.service'

def ssh(command):
    return subprocess.check_output(['ssh', 'ot-pve1', command], text=True)

def write(name, value):
    (DEST / name).write_text(json.dumps(value, sort_keys=True, indent=2) + '\n')

def main():
    print('Watching existing PID918356 only; no prefix or native source invocation', flush=True)
    while True:
        try:
            status = ssh('systemctl --user show ' + UNIT + ' --property=MainPID,ActiveState')
            if 'MainPID=0\n' in status:
                break
        except subprocess.CalledProcessError as error:
            print('Read-only status unavailable: ' + str(error), flush=True)
        time.sleep(15)
    DEST.mkdir(exist_ok=False)
    subprocess.run(['scp', '-r', 'ot-pve1:' + REMOTE + '/payload', str(DEST / 'payload')], check=True)
    original = '/home/ubuntu/OpenTallas-qwen-trained-native-execution'
    provenance = ssh('git -C ' + original + ' rev-parse HEAD; git -C ' + original +
                     ' status --porcelain; sha256sum ' + REMOTE + '/source/tools/h4_c0_pc40_payload_r1.py')
    (DEST / 'source_identity.txt').write_text(provenance)
    (DEST / 'unit_terminal.txt').write_text(ssh('systemctl --user show ' + UNIT +
          ' --property=MainPID,ActiveState,Result,ExecMainStatus,CPUUsageNSec,MemoryPeak'))
    (DEST / 'journal.txt').write_text(ssh('journalctl --user -u ' + UNIT + ' --no-pager'))
    files = sorted(p for p in DEST.rglob('*') if p.is_file())
    write('raw_artifact_pins.json', [{'path':str(p.relative_to(DEST)), 'bytes':p.stat().st_size,
                                    'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in files])
    capture = DEST / 'payload'
    terminal_path = capture / 'terminal.json'
    terminal = json.loads(terminal_path.read_text()) if terminal_path.exists() else {'verdict':'ABSENT'}
    verification = dict(raw_evidence_preserved=True, numerical_prefix_rerun=False,
                        terminal_verdict=terminal.get('verdict'), installed_RF_qualified=False,
                        source_gate_release_inferred=False, source_worktree_identity=provenance.splitlines()[0])
    local_sha = hashlib.sha256((ROOT / 'tools/h4_c0_pc40_payload_r1.py').read_bytes()).hexdigest()
    verification['runner_byte_exact'] = local_sha in provenance
    verification['original_source_commit_exact'] = provenance.splitlines()[0] == '870c5fe581b768df28dd2998b2d0aecc24510c23'
    if terminal.get('verdict') == 'PASS':
        for name in ['offline_replay_r1.json','offline_replay_cold_r1.json']:
            subprocess.run(['python', str(ROOT / 'tools/h4_c0_pc40_payload_replay_r1.py'),
                            '--capture', str(capture), '--out', str(DEST / name)], check=True, cwd=ROOT)
        verification['saved_byte_replay_cold_equal'] = (DEST / 'offline_replay_r1.json').read_bytes() == (DEST / 'offline_replay_cold_r1.json').read_bytes()
    write('collection_verification.json', verification)
    print(json.dumps(verification, sort_keys=True), flush=True)

if __name__ == '__main__':
    main()
