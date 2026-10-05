#!/usr/bin/env python3
"""One changed-source native connected pair, reusing an immutable donor build.

Run on the donor host. Only private source/object copies are changed. The
retained GU inputs, NS2 images, numerical engine and CP writer stay pinned.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import os
import signal


def record_exit(job, stage, rc):
    (job / (stage + '.exit')).write_text(str(rc) + '\n')
    detail = {'returncode': rc, 'signal': signal.Signals(-rc).name if rc < 0 else None}
    (job / (stage + '_terminal.json')).write_text(json.dumps(detail, indent=2) + '\n')
    if rc:
        print(stage + ' failed: ' + json.dumps(detail), flush=True)


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def run(donor, job, overlay, reuse_objects=None):
    object_dir = reuse_objects if reuse_objects is not None else donor / 'build/obj'
    pins = json.loads((donor / 'build/source_pin.json').read_text())
    # Actual original frontend allocation, not a process address-space cap.
    available_kb = int(next(x.split()[1] for x in Path('/proc/meminfo').read_text().splitlines()
                            if x.startswith('MemAvailable:')))
    loads = os.getloadavg()
    if max(loads) >= 128 or available_kb < 16722.289 * 1024:
        raise RuntimeError('donor host lacks current permitted load/memory headroom; keep objects')
    object_bytes = sum(p.stat().st_size for p in object_dir.rglob('*') if p.is_file())
    source_bytes = sum((donor / 'src' / rel).stat().st_size for rel in pins)
    if shutil.disk_usage(job.parent).free < object_bytes + source_bytes + int(366.634 * 1024**2):
        raise RuntimeError('private retained object/source copy lacks actual disk headroom')
    job.mkdir(parents=True, exist_ok=False)
    for rel, expected in pins.items():
        source = donor / 'src' / rel
        if sha(source) != expected:
            raise ValueError('immutable donor source changed: ' + rel)
        target = job / 'src' / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    replacements = [
        'rtl/hbm_accel/integrated_20261005/ot_hbm_integrated_w2_result_sink.sv',
        'rtl/test/hbm_accel/integrated_20261005/tb_hbm_integrated_gu_w2_hubble.sv',
        'rtl/hbm_accel/integrated_20261005/ot_hbm_integrated_cp_reset.sv',
    ]
    for rel in replacements:
        target = job / 'src' / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(overlay / rel, target)
    # Reflink when supported, ordinary private copies otherwise. Never hardlink
    # generated mutable objects into the original completed job.
    subprocess.run(['cp', '-a', '--reflink=auto', str(object_dir), str(job / 'obj')], check=True)
    command = json.loads((donor / 'build/command.json').read_text())
    command = [x.replace(str(donor / 'src'), str(job / 'src')) for x in command]
    command[command.index('--Mdir') + 1] = str(job / 'obj')
    command[1:1] = ['-GPROTECTED_TRANSACTION_PIPELINE=1', '-GLOCAL_CP_RESET_ENABLE=1']
    command.append(str(job / 'src' / replacements[2]))
    all_sources = list(dict.fromkeys(list(pins) + replacements))
    receipt = dict(source_commit=(overlay / 'source.commit').read_text().strip(),
                   donor=str(donor), reused_objects=str(object_dir), load=loads, available_kb=available_kb,
                   retained_case=str(donor / 'case'), original_NS2_prefix=str(donor / 'original/mem'),
                   source_sha256={rel: sha(job / 'src' / rel) for rel in all_sources},
                   immutable_donor_sha256=pins, default_source_option=0,
                   selected_run_mode=1, physical_admission=False)
    (job / 'source_pin.json').write_text(json.dumps(receipt, indent=2) + '\n')
    (job / 'command.json').write_text(json.dumps(command, indent=2) + '\n')
    with (job / 'compile.log').open('w') as log:
        rc = subprocess.run(command, cwd=job, stdout=log, stderr=subprocess.STDOUT).returncode
    record_exit(job, 'compile', rc)
    if rc:
        raise SystemExit(1)
    runtime = [str(job / 'obj/Vtb_hbm_integrated_gu_w2_hubble'),
               '+DIR=' + str(donor / 'case'),
               '+gpu_sys_mem_prefix=' + str(donor / 'original/mem'),
               * (donor / 'case/args.txt').read_text().split(), '+WARM_QUARANTINE']
    (job / 'runtime_command.json').write_text(json.dumps(runtime, indent=2) + '\n')
    with (job / 'runtime.log').open('w') as log:
        rc = subprocess.run(runtime, cwd=job, stdout=log, stderr=subprocess.STDOUT).returncode
    record_exit(job, 'runtime', rc)
    log = (job / 'runtime.log').read_text()
    if rc or 'PASS_W2_PARENT_WARM_QUARANTINE' not in log or 'PASS_NATIVE_W2_CONNECTED_PUBLICATION_CPL' not in log:
        raise SystemExit(1)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--donor', type=Path, required=True)
    p.add_argument('--job', type=Path, required=True)
    p.add_argument('--overlay', type=Path, required=True)
    p.add_argument('--reuse-objects', type=Path)
    a = p.parse_args()
    run(a.donor.resolve(), a.job.resolve(), a.overlay.resolve(),
        a.reuse_objects.resolve() if a.reuse_objects else None)
