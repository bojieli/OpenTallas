#!/usr/bin/env python3
"""One fresh W11 route of Fermat's proved export; never resynthesize or transform."""
import argparse
import datetime
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
BASE = 'e3e9e9b8a225d8d6fb5657fc6b33829ce803a040'
PROOF_PIN = '71ba8ca929ccea0101d52d15591d57c325de0a2f'
PROOF_REL = 'results/physical_abi3/asap7/chip/w11_controller_tie_equivalence_20261001/'
PROOF = Path('/home/ubuntu/w11-controller-tie-proof-20261001')
NATIVE = Path('/home/ubuntu/w11-controller-tie-admission-20261001')
OLD = Path('/home/ubuntu/w11ctl_endpoint_e3e9e9b8/work')
OLD_OUT = Path('/tmp/claude-1000/wt/w11-controller-recovery/results/physical_abi3/asap7/chip/w11_attn_eng_ctl/endpoint_e3e9e9b8')
IMAGE = 'sha256:af971398d91e5d154ec40d3df26554efd8790107268a4c7f1e6bb8f222979d34'


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for b in iter(lambda: stream.read(8*1024*1024), b''):
            h.update(b)
    return h.hexdigest()


def git(*args):
    return subprocess.check_output(['git', '-C', str(ROOT), *args])


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--expect-commit', required=True)
    ap.add_argument('--check-only', action='store_true')
    a = ap.parse_args()
    lease = Path('/tmp/claude-1000/queue/W11.controller-tie-route.lease')
    with lease.open('a+') as held:
        fcntl.flock(held, fcntl.LOCK_EX | fcntl.LOCK_NB)
        head = git('rev-parse', 'HEAD').decode().strip()
        assert head == a.expect_commit and not git('status', '--porcelain')
        for p in ['tools/run_abi3_physical.py', 'rtl/chip/physical/ot_v41_attn_eng_ctl_phys.sv',
                  'rtl/hdc/v41x/ot_hdc_v41x_attn.sv', 'physical/abi3/v41x_karb_repair_buffer_cap.tcl']:
            assert (ROOT/p).read_bytes() == git('show', BASE+':'+p), p
        proof_raw = git('show', PROOF_PIN+':'+PROOF_REL+'proof.json')
        assert (PROOF/'proof.json').read_bytes() == proof_raw
        proof = json.loads(proof_raw)
        receipt = json.loads(git('show', PROOF_PIN+':'+PROOF_REL+'receipt.json'))
        assert proof['verdict'] == proof['export_reimport_proof']['verdict'] == 'PASS'
        assert proof['sequential_after'] == proof['sequential_before'] == 337084
        assert proof['guard_expected'] == 338023 and proof['guard_minimum'] == 270418
        for name, sha in proof['input_sha256'].items():
            assert digest(PROOF/name) == sha, name
        for name, sha in receipt['raw_artifact_sha256'].items():
            assert digest(PROOF/name) == sha, name
        assert digest(OLD/'mapped.v') == receipt['source_rechecked_sha256']
        native = json.loads((ROOT/'results/uarch/w11_controller_tie_route_admission_20261001.json').read_text())
        for name, sha in native['native_artifact_sha256'].items():
            assert digest(NATIVE/name) == sha, name
        assert native['native_guard'] == 'PASS' and native['added_cycles'] == 0
        image = subprocess.check_output(['docker', 'image', 'inspect', 'openroad/orfs:latest', '--format', '{{.Id}}'], text=True).strip()
        assert image == IMAGE
        for proc in Path('/proc').iterdir():
            if not proc.name.isdigit() or int(proc.name) == os.getpid():
                continue
            try:
                cmd = (proc/'cmdline').read_bytes()
            except (FileNotFoundError, PermissionError, ProcessLookupError):
                continue
            assert not (b'run_abi3_physical.py' in cmd and b'ot_v41_attn_eng_ctl_phys' in cmd), proc.name
        containers = subprocess.check_output(['docker', 'ps', '-q'], text=True).split()
        if containers:
            details = json.loads(subprocess.check_output(['docker', 'inspect', *containers]))
            assert not any('w11ctl_' in m.get('Source', '') for c in details for m in c.get('Mounts', []))
        mem = {l.split(':')[0]: int(l.split()[1])*1024 for l in Path('/proc/meminfo').read_text().splitlines()}
        resources = dict(observed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                         available_RAM_bytes=mem['MemAvailable'], free_disk_bytes=shutil.disk_usage('/home/ubuntu').free,
                         load_1min=os.getloadavg()[0], CPU=os.cpu_count(), ORFS_threads=4)
        assert resources['available_RAM_bytes'] >= 64*1024**3
        assert resources['free_disk_bytes'] >= 64*1024**3
        assert resources['load_1min'] <= resources['CPU']-4
        print(json.dumps(dict(status='ADMISSION_PASS', source_pin=head, proof_pin=PROOF_PIN, resources=resources)), flush=True)
        if a.check_only:
            return 0
        attempt = Path('/home/ubuntu')/('w11ctl_tie_'+head[:8])
        assert not attempt.exists(), 'Fresh output only; never reuse an attempt'
        work, out = attempt/'work', attempt/'receipt'
        work.mkdir(parents=True)
        out.mkdir()
        shutil.copyfile(PROOF/'tied.v', work/'mapped.v')
        guard = json.loads((OLD/'w11_endpoint_guard.json').read_text())
        assert guard['observed_sequential'] == 337084
        guard.update(normalized_netlist_sha256=digest(work/'mapped.v'),
                     constant_only_proof_commit=PROOF_PIN, original_mapped_sha256=receipt['source_rechecked_sha256'])
        (work/'w11_endpoint_guard.json').write_text(json.dumps(guard, indent=2)+'\n')
        cmd = json.loads((OLD_OUT/'launch.json').read_text())['command']
        cmd[0], cmd[1] = sys.executable, str(ROOT/'tools/run_abi3_physical.py')
        for flag, value in [('--stages', 'pnr'), ('--keep-workdir', str(work)), ('--output', str(out/'physical.json'))]:
            cmd[cmd.index(flag)+1] = value
        launch = dict(source_commit=head, original_source_pin=BASE, proof_commit=PROOF_PIN,
                      command=cmd, launcher_pid=os.getpid(), resources_inside_lease=resources,
                      original_mapped_sha256=receipt['source_rechecked_sha256'],
                      corrected_sha256=guard['normalized_netlist_sha256'], native_admission=native,
                      scope='Flow-error correction; physical stubs only. No arithmetic/timing optimization or CKV retry.')
        (out/'launch.json').write_text(json.dumps(launch, indent=2)+'\n')
        env = dict(os.environ, OT_ORFS_NUM_CORES='4', OT_FLOW_TIMEOUT_SECONDS='86400')
        with (out/'driver.log').open('w') as log:
            driver = subprocess.Popen(cmd, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT)
            launch['driver_pid'] = driver.pid
            (out/'launch.json').write_text(json.dumps(launch, indent=2)+'\n')
            print(json.dumps(dict(status='LAUNCHED', launcher=os.getpid(), driver=driver.pid,
                                  source_pin=head, attempt=str(attempt))), flush=True)
            rc = driver.wait()
        (out/'exit.json').write_text(json.dumps(dict(returncode=rc))+'\n')
        return rc


if __name__ == '__main__':
    sys.exit(main())
