#!/usr/bin/env python3
"""Link one testbench phase driver to completed quarter objects; no native build.

The original Verilator scheduler and all native instructions are reused.
Only main's ELF symbol in a separate 6.7MiB object copy is renamed to allow
the external driver. The original archive/objects/source are immutable.
"""
import argparse
import json
from pathlib import Path
import subprocess

from dsrom_reindex_native_quarter_gate import capacity, sha


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--original', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--driver', type=Path, required=True)
    a = p.parse_args()
    a.out.mkdir(parents=True, exist_ok=False)
    obj = a.original / 'run/obj'
    archive = obj / 'Vtb_dsrom_reindex_native_quarter__ALL.a'
    fixture = a.original / 'src/results/rtl/dsrom_reindex_parent_20261005/native_quarter_runtime_prepared'
    record = dict(scope='Sourcebench phase1 using completed original native16/IW20 objects',
                  original_failure=str(a.original / 'run/record.json'),
                  archive_path=str(archive), archive_sha256=sha(archive),
                  driver_sha256=sha(a.driver), seed=1062026, ready_phase=1,
                  native_recompiled=False, scheduler_replaced=False,
                  testbench_configuration='Initial edge-counter origin +1 before first clock edge; original SV periodic ready process executes normally. Constant origin cancels in cycle differences.',
                  parent_qualified=False, physical_qualified=False, runs=[])
    def save():
        (a.out / 'record.json').write_text(json.dumps(record, indent=2) + '\n')
    c = record['post_admission_capacity'] = capacity(a.out)
    save()
    if c['load1'] >= c['cores'] or c['idle_cores'] < 1 or c['available_RAM_GiB'] < 116 or c['available_disk_GiB'] < 30:
        record['verdict'] = 'CAPACITY_REFUSAL'
        save()
        return 3
    main_object = obj / 'Vtb_dsrom_reindex_native_quarter_vm_classes_15.o'
    renamed = a.out / 'retained_main_renamed.o'
    subprocess.run(['objcopy', '--redefine-sym', 'main=ot_kc8_retained_main', str(main_object), str(renamed)], check=True)
    objects = [str(renamed if name == main_object.name else obj / name)
               for name in subprocess.check_output(['ar', 't', str(archive)], text=True).splitlines()]
    include = Path(next(line.split('=', 1)[1].strip() for line in
                        (obj / 'Vtb_dsrom_reindex_native_quarter.mk').read_text().splitlines()
                        if line.startswith('VERILATOR_ROOT ='))) / 'include'
    exe = a.out / 'quarter_phase1'
    cmd = ['g++', '-O0', '-fcoroutines', '-DVM_TIMING=1', '-DVL_TIME_CONTEXT',
           '-I' + str(obj), '-I' + str(include), '-I' + str(include / 'vltstd'),
           str(a.driver), *objects, *[str(obj / n) for n in
                                    ['verilated.o', 'verilated_timing.o', 'verilated_threads.o']],
           '-pthread', '-latomic', '-o', str(exe)]
    record['link_argv'] = cmd
    save()
    with (a.out / 'link.log').open('x') as f:
        rc = subprocess.run(cmd, stdout=f, stderr=subprocess.STDOUT).returncode
    record['link_exit'] = rc
    save()
    if rc:
        record['verdict'] = 'LINK_FAIL_PRESERVED'
        save()
        return 1
    record['executable_sha256'] = sha(exe)
    for name, options, expected in [('golden', [], 'PASS_KC8_NATIVE_QUARTER'),
                                    ('negative_score', ['+NEGATIVE_SCORE=1'], 'golden mismatch'),
                                    ('negative_ids', ['+NEGATIVE_IDS=1'], 'index not consecutive')]:
        cmd = [str(exe), '+verilator+seed+1062026', '+READY_PHASE=1', f'+FIXTURE={fixture}', *options]
        with (a.out / (name + '.log')).open('x') as f:
            rc = subprocess.run(cmd, stdout=f, stderr=subprocess.STDOUT).returncode
        text = (a.out / (name + '.log')).read_text()
        passed = expected in text and ((rc == 0) if name == 'golden' else (rc != 0))
        record['runs'].append(dict(name=name, argv=cmd, exit_code=rc, pass_=passed))
        save()
        print(name, rc, passed, text, flush=True)
        if not passed:
            record['verdict'] = 'NATIVE_QUARTER_FAIL_PRESERVED'
            save()
            return 1
    assert sha(archive) == record['archive_sha256']
    record['verdict'] = 'NATIVE_QUARTER_PASS'
    save()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
