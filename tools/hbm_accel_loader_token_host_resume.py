#!/usr/bin/env python3
"""Replay the retained host-loaded reduced smoke with only the selected d391 fix.

Preserve the donor case/build/failure. Clone its objects for incremental reuse,
verify every retained byte and source, and use the host's existing admission core.
The unchanged bench checks the released golden and stops at its first mismatch.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
SELECTED = 'rtl/hbm_accel/collective/ot_hbm_accel_simt_sm.sv'
CORRECTED = '8ed10381416be54890d2100184d65331e2bd254845bc9a115b2fd824d2643a29'


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')


def admit(work, stage, disk_need):
    sys.path.insert(0, '/srv/opentallas-scratch')
    from admit_core import try_admit
    print(f'ADMISSION_WAIT stage={stage} load<128 reserve=64GiB', flush=True)
    while True:
        available = int(next(l.split()[1] for l in Path('/proc/meminfo').read_text().splitlines()
                             if l.startswith('MemAvailable:'))) * 1024
        free = shutil.disk_usage(work).free
        if os.getloadavg()[0] < 128 and free >= disk_need and try_admit(64 * 2**30):
            if os.getloadavg()[0] >= 128:
                time.sleep(10)
                continue
            evidence = dict(stage=stage, time=time.time(), load=os.getloadavg(),
                            cpu_count=os.cpu_count(), mem_available=available,
                            disk_free=free, inventory_disk_need=disk_need,
                            declared_peak_gib=64)
            save(work / f'admission_{stage}.json', evidence)
            print(f'ADMITTED stage={stage} load={evidence["load"][0]:.2f}', flush=True)
            return
        time.sleep(10)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--donor', type=Path, required=True)
    p.add_argument('--work', type=Path, required=True)
    p.add_argument('--source-pin', required=True)
    a = p.parse_args()
    donor, work = a.donor.resolve(), a.work.resolve()
    work.mkdir(parents=True, exist_ok=False)
    old = json.loads((donor / 'source_binding.json').read_text())
    assert old['source_pin'] == '1488fe4a82e3f39afa715f0a9dc990db738e65bd'
    pins = {s: sha(ROOT / s) for s in old['source_sha256']}
    changed = [s for s, h in old['source_sha256'].items() if pins[s] != h]
    assert changed == [SELECTED], changed
    assert pins[SELECTED] == CORRECTED
    assert old['expected_steps'][0] == dict(pos=0, input=0, next=2815)
    for name, h in old['fixture_sha256'].items():
        assert sha(donor / 'case' / name) == h, name
    for die, image in enumerate(old['host_images']):
        assert sha(donor / 'case' / f'host_die{die}.hex') == image['host_sha256']
        assert (donor / 'case' / f'host_die{die}.crc').read_text().strip() == image['CRC']
    rec = dict(schema='opentallas.hbm.selected_host_resume.v1', source_pin=a.source_pin,
               base_source_pin=old['source_pin'], source_sha256=pins, changed_sources=changed,
               fixture_sha256=old['fixture_sha256'], host_images=old['host_images'],
               params=old['params'], expected_steps=old['expected_steps'],
               donor=str(donor), driver_sha256=sha(Path(__file__)),
               scope=old['scope'], physical_qualified=False, verdict='PENDING_ADMISSION')
    save(work / 'record.json', rec)
    objects = {f.name: sha(f) for f in (donor / 'obj').glob('*.o')}
    inventory = sum(f.stat().st_size for d in ['obj', 'case']
                    for f in (donor / d).rglob('*') if f.is_file())
    # Two object inventories allow retained + regenerated C++/objects; case is
    # retained unchanged. This is free-space admission, never an output cap.
    disk_need = 2 * inventory + 2**30
    while shutil.disk_usage(work).free < disk_need:
        time.sleep(10)
    subprocess.run(['cp', '-a', '--reflink=auto', str(donor / 'obj'), str(work / 'obj')], check=True)
    subprocess.run(['cp', '-a', '--reflink=auto', str(donor / 'case'), str(work / 'case')], check=True)
    old_cmd = json.loads((donor / 'build_command.json').read_text())
    old_root = str(Path(next(s for s in old_cmd if s.endswith('/' + SELECTED))).parents[3])
    cmd = [str(work / 'obj') if s == str(donor / 'obj') else
           str(ROOT / s[len(old_root) + 1:]) if s.startswith(old_root + '/') else s
           for s in old_cmd]
    assert cmd[cmd.index('--Mdir') + 1] == str(work / 'obj')
    assert str(ROOT / SELECTED) in cmd
    save(work / 'build_command.json', cmd)
    admit(work, 'build', disk_need)
    started = time.monotonic()
    with (work / 'build.log').open('w') as log:
        rc = subprocess.run(cmd, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT).returncode
    rec.update(build_rc=rc, build_seconds=time.monotonic() - started,
               donor_object_count=len(objects), reused_object_count=sum(
                   (work / 'obj' / n).exists() and sha(work / 'obj' / n) == h
                   for n, h in objects.items()), verdict='FAIL_BUILD' if rc else 'PENDING_RUN')
    save(work / 'record.json', rec)
    if rc:
        return rc
    assert all(sha(ROOT / s) == h for s, h in pins.items()), 'source drift after build'
    cmd = [str(work / 'obj/Vtb_hbm_accel_loader_token_host'), '+DIR=' + str(work / 'case')]
    save(work / 'run_command.json', cmd)
    rec.update(verdict='RUNNING', run_started_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
               binary_sha256=sha(Path(cmd[0])))
    save(work / 'record.json', rec)
    admit(work, 'run', 2**30)
    started = time.monotonic()
    with (work / 'run.log').open('w') as log:
        rc = subprocess.run(cmd, cwd=work / 'case', stdout=log, stderr=subprocess.STDOUT).returncode
    log = (work / 'run.log').read_text()
    rec.update(run_rc=rc, run_seconds=time.monotonic() - started,
               terminal_lines=[s for s in log.splitlines() if s.startswith(
                   ('HOST_IMAGE_VISIBLE', 'CODE_PUBLISHED', 'STEP', 'CQ', 'TB_GPU_HBM_SYSTEM', '%Error', '%Fatal'))],
               verdict='PASS' if rc == 0 and 'TB_GPU_HBM_SYSTEM PASS' in log else 'FAIL_FUNCTIONAL')
    save(work / 'record.json', rec)
    print(rec['verdict'], flush=True)
    return 0 if rec['verdict'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
