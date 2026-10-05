#!/usr/bin/env python3
"""Default-off persistent NEW-source-SDC ODB stages; no make/synthesis/restart.

Preparation is available now. Execution requires source review, producer terminal
receipt and a fresh measured PVE1 reservation, passed to the persistent adapter.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import threading
import time

import pve1_odb_endpoint_audit as endpoint_audit
import pve1_source_constraint_successor as source_contract

ROOT = Path(__file__).resolve().parents[1]
PLAN_DIR = ROOT / 'results/rtl/pve1_new_source_constraint_successor_20261003'
EVIDENCE = ROOT / 'results/rtl/pve1_odb_stage_driver_20261003'
STAGES = (
    ('resize', '3_3_place_gp.odb', 'new_source_constraint.sdc', '3_4_place_resized.odb', None),
    ('detail_place', '3_4_place_resized.odb', 'new_source_constraint.sdc', '3_5_place_dp.odb', '3_place.sdc'),
    ('cts', '3_place.odb', '3_place.sdc', '4_1_cts.odb', '4_cts.sdc'),
    ('global_route', '4_cts.odb', '4_cts.sdc', '5_1_grt.odb', '5_1_grt.sdc'),
    ('detail_route', '5_1_grt.odb', '5_1_grt.sdc', '5_2_route.odb', None),
    ('fillcell', '5_2_route.odb', '5_1_grt.sdc', '5_3_fillcell.odb', None),
    ('density_fill', '5_route.odb', '5_route.sdc', '6_1_fill.odb', None),
    ('final_report', '6_1_fill.odb', '6_1_fill.sdc', '6_final.odb', '6_final.sdc'),
)
KNOBS = dict(SLEW_MARGIN='40', HOLD_SLACK_MARGIN='10', MIN_ROUTING_LAYER='M2',
    MAX_ROUTING_LAYER='M6', PRE_CTS_TCL='/work/hooks/pre_cts_v41x_karb_repair_buffer_cap.tcl',
    PRE_GLOBAL_ROUTE_TCL='/work/hooks/pre_global_route_v41x_karb_repair_buffer_cap.tcl')


def digest(path):
    value = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for block in iter(lambda: handle.read(4194304), b''):
            value.update(block)
    return value.hexdigest()


def save(path, record):
    with Path(path).open('x') as handle:
        json.dump(record, handle, indent=2); handle.write('\n')
        handle.flush(); os.fsync(handle.fileno())


def quote(value):
    return '"' + str(value).replace('\\', '\\\\').replace('$', '\\$').replace('[', '\\[').replace(']', '\\]').replace('"', '\\"').replace('\n', '\\n') + '"'


def inputs():
    plan = json.loads((PLAN_DIR / 'plan.json').read_text())
    dependencies = json.loads((EVIDENCE / 'stage_dependencies.json').read_text())
    if any(dependencies['environment'].get(k) != v for k, v in KNOBS.items()):
        raise ValueError('later-stage physical knobs differ')
    if digest(PLAN_DIR / 'new_source_constraint.sdc') != source_contract.SDC_SHA256:
        raise ValueError('source SDC changed')
    return plan, dependencies


def admission(plan, terminal, lease, review, odb):
    producer = plan['terminal_capture_gate']['producer']
    if (terminal.get('producer') != producer or terminal.get('exit_code') != 0
            or terminal.get('writer_closed') is not True or terminal.get('producer_alive') is not False
            or terminal.get('schema') != 'PVE1_CURRENT_STAGE_TERMINAL_V1'):
        raise ValueError('exact successful terminal producer receipt required')
    if Path(odb).name != '3_3_place_gp.odb' or Path(odb).stat().st_size == 0 or digest(odb) != terminal['odb_sha256']:
        raise ValueError('terminal ODB identity differs')
    if digest(terminal['raw_log_path']) != terminal['raw_log_sha256']:
        raise ValueError('terminal raw log differs')
    if terminal.get('historical_timeout_reclassified', False):
        raise ValueError('historical FAIL cannot be changed')
    pid = Path('/proc') / str(producer['pid']) / 'stat'
    if pid.exists() and int(pid.read_text().rsplit(')', 1)[1].split()[19]) == producer['start_ticks']:
        raise ValueError('original producer still alive')
    if (lease.get('status') != 'ACTIVE' or lease.get('provider') != 'ot-pve1'
            or lease.get('host_name') != socket.gethostname() or lease.get('owner') != 'PVE1_NEW_SOURCE_CONSTRAINT'
            or lease.get('disjoint') is not True or lease.get('new_lease') is not True):
        raise ValueError('fresh disjoint measured PVE1 lease required')
    if (review.get('status') != 'APPROVED_FOR_NEW_SOURCE_CONSTRAINT_EXECUTION'
            or review.get('driver_sha256') != digest(__file__)
            or review.get('audit_python_sha256') != digest(endpoint_audit.__file__)
            or review.get('audit_tcl_sha256') != digest(ROOT / 'tools/pve1_odb_endpoint_audit.tcl')
            or review.get('plan_sha256') != digest(PLAN_DIR / 'plan.json')
            or review.get('dependencies_sha256') != digest(EVIDENCE / 'stage_dependencies.json')
            or review.get('native_api_compatibility_reviewed') is not True):
        raise ValueError('exact source/model/native audit review required')
    if lease.get('capacity_basis') != 'MEASURED_ODB_NETLIST_AUDIT_AND_STAGE_INVENTORY':
        raise ValueError('measured resource projection required')
    required = lease.get('required_free_bytes')
    if not isinstance(required, int) or required <= 0:
        raise ValueError('measured disk projection missing')
    for key in ('required_available_ram_bytes', 'reserved_cpu_threads'):
        if not isinstance(lease.get(key), int) or lease[key] <= 0:
            raise ValueError('measured RAM/CPU reservation missing')
    if digest(lease['capacity_evidence_path']) != lease['capacity_evidence_sha256']:
        raise ValueError('measured resource evidence differs')
    return required


def entrypoint(stage, dependencies, *, audit_only=False):
    name, odb, sdc, _, _ = stage
    if audit_only:
        name = 'initial'
    env = dict(dependencies['environment'])
    env['RUN_LOG_NAME_STEM'] = name
    env['OT_AUDIT_ROWS'] = '/work/audit/' + name + '.rows'
    env['OT_AUDIT_SDC'] = '/work/audit/' + name + '.actual.sdc'
    lines = ['# NEW source-constraint lineage; pinned ODB, original stage bytes.']
    lines.extend('set ::env(' + k + ') ' + quote(v) for k, v in sorted(env.items()))
    lines += ['source $::env(SCRIPTS_DIR)/load.tcl', f'load_design {odb} {sdc}']
    if audit_only:
        lines += ['estimate_parasitics -placement', 'write_verilog /work/audit/starting_full_netlist.v']
    else:
        lines += ['source $::env(SCRIPTS_DIR)/' + name + '.tcl']
    # Stage-specific erase_non_stage_variables may remove unrelated variables.
    lines += ['set ::env(OT_AUDIT_ROWS) ' + quote(env['OT_AUDIT_ROWS']),
              'set ::env(OT_AUDIT_SDC) ' + quote(env['OT_AUDIT_SDC']),
              'source /work/prepared/endpoint_audit.tcl']
    return '\n'.join(lines) + '\n'


def prepare(work):
    plan, deps = inputs()
    work = Path(work).resolve()
    # Preparation is always fresh and separate from the existing retained job.
    for forbidden in (Path('/work'), Path('/home/ubuntu/ot-retained/pve1-w11-su2-live-20261003')):
        if work == forbidden or forbidden in work.parents:
            raise ValueError('existing live retention namespace forbidden')
    work.mkdir(exist_ok=False)
    prepared = work / 'prepared'; prepared.mkdir()
    for stage in STAGES:
        (prepared / (stage[0] + '.tcl')).write_text(entrypoint(stage, deps))
    (prepared / 'initial.tcl').write_text(entrypoint(STAGES[0], deps, audit_only=True))
    shutil.copyfile(ROOT / 'tools/pve1_odb_endpoint_audit.tcl', prepared / 'endpoint_audit.tcl')
    save(work / 'preparation.json', dict(status='PREPARED_NOT_EXECUTED', added_cycles=0,
         new_source_constraint=True, plan_sha256=digest(PLAN_DIR / 'plan.json'),
         dependency_sha256=digest(EVIDENCE / 'stage_dependencies.json'),
         stages=[s[0] for s in STAGES], knobs=KNOBS, native_api_verified=False))
    return plan, deps


def run(command, *, log, timeout=None):
    if timeout is not None:
        raise ValueError('runtime caps forbidden')
    log = Path(log)
    stop = threading.Event()
    def observe():
        while not stop.is_set():
            try:
                memory = next(line for line in Path('/proc/meminfo').read_text().splitlines() if line.startswith('MemAvailable:'))
                sample = dict(time_ns=time.time_ns(), free_bytes=shutil.disk_usage(log.parent).free,
                    available_ram_bytes=int(memory.split()[1]) * 1024,
                    purpose='Capacity observation only; no timeout, kill, restart or per-process cap')
                log.with_suffix('.capacity.json').write_text(json.dumps(sample) + '\n')
            except OSError:
                # A failed observer cannot terminate a progressing native job.
                # Terminal signoff remains separate and requires complete evidence.
                return
            stop.wait(30)  # Sampling cadence, not an execution deadline.
    with log.open('xb') as handle:
        observer = threading.Thread(target=observe, daemon=True)
        observer.start()
        try:
            return subprocess.run(command, stdout=handle, stderr=subprocess.STDOUT, timeout=None).returncode
        finally:
            stop.set(); observer.join()


def flow_timeout_seconds(): return None
def synth_timeout_seconds(): return None


def verification_program():
    return ('import hashlib,json; d=json.load(open("/work/dependencies.json")); '
        'exec("for p,v in d.items():\\n h=hashlib.sha256()\\n with open(p, \'rb\') as f:\\n'
        '  for b in iter(lambda:f.read(4194304),b\'\'):h.update(b)\\n'
        ' assert h.hexdigest()==v[\'sha256\'],p")')


def persistent_output_path(work):
    work = Path(work).resolve()
    if Path('/home') not in work.parents:
        raise ValueError('heavy stage outputs require persistent /home storage')
    # Reject a tmpfs bind even when its pathname happens to be below /home.
    mounts = []
    for line in Path('/proc/self/mountinfo').read_text().splitlines():
        left, right = line.split(' - ', 1)
        mount = Path(left.split()[4].replace('\\040', ' '))
        if mount == work or mount in work.parents:
            mounts.append((len(mount.parts), right.split()[0]))
    if mounts and max(mounts)[1] in ('tmpfs', 'ramfs'):
        raise ValueError('persistent output path cannot use tmpfs/ramfs')
    return work


def restore_hooks(work, source_root, dependencies):
    source = Path(source_root) / 'physical/abi3/v41x_karb_repair_buffer_cap.tcl'
    for key in ('PRE_CTS_TCL', 'PRE_GLOBAL_ROUTE_TCL'):
        target = dependencies['environment'][key]
        if digest(source) != dependencies['files'][target]['sha256']:
            raise ValueError('pinned PRE_CTS/PRE_GLOBAL_ROUTE hook differs')
        shutil.copyfile(source, Path(work) / target.removeprefix('/work/'))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepare-dir', type=Path)
    parser.add_argument('--keep-workdir', type=Path)
    parser.add_argument('--terminal-receipt', type=Path)
    parser.add_argument('--lease', type=Path)
    parser.add_argument('--review', type=Path)
    parser.add_argument('--terminal-odb', type=Path)
    parser.add_argument('--source-root', type=Path)
    parser.add_argument('--run-admitted-new-source-constraints', action='store_true')
    args = parser.parse_args(argv)
    if args.prepare_dir is not None:
        if args.run_admitted_new_source_constraints or args.keep_workdir is not None:
            raise ValueError('preparation and execution are distinct modes')
        prepare(args.prepare_dir)
        return 0
    if not args.run_admitted_new_source_constraints:
        raise ValueError('default off: explicit execution admission required')
    if any(getattr(args, k) is None for k in ('keep_workdir', 'terminal_receipt', 'lease', 'review', 'terminal_odb', 'source_root')):
        raise ValueError('complete terminal/review/lease/source admission required')
    plan, deps = inputs()
    source_contract.validate(plan, PLAN_DIR / 'new_source_constraint.sdc', args.source_root)
    head = subprocess.check_output(['git', '-C', str(args.source_root), 'rev-parse', 'HEAD'], text=True).strip()
    dirty = subprocess.check_output(['git', '-C', str(args.source_root), 'status', '--porcelain'], text=True)
    if head != source_contract.SOURCE_COMMIT or dirty:
        raise ValueError('isolated clean exact source worktree required')
    required = admission(plan, json.loads(args.terminal_receipt.read_text()),
                         json.loads(args.lease.read_text()), json.loads(args.review.read_text()), args.terminal_odb)
    work = persistent_output_path(args.keep_workdir)
    if not work.is_absolute() or not work.is_dir() or any(work.iterdir()):
        raise ValueError('persistent adapter must own a fresh empty workdir')
    if shutil.disk_usage(work).free < required:
        raise ValueError('current free space below measured reservation requirement')
    lease = json.loads(args.lease.read_text())
    memory = {line.split(':')[0]: int(line.split()[1]) * 1024
              for line in Path('/proc/meminfo').read_text().splitlines() if line.startswith('MemAvailable:')}
    if memory['MemAvailable'] < lease['required_available_ram_bytes']:
        raise ValueError('current RAM headroom below measured reservation requirement')
    if lease['reserved_cpu_threads'] < int(deps['environment']['NUM_CORES']):
        raise ValueError('CPU reservation smaller than exact stage thread count')
    # Adapter creates the directory. Prepare in a fresh child, then use the
    # parent as the immutable persistent bind. No temporary work lifecycle.
    prepare(work / 'bundle')
    shutil.copytree(work / 'bundle/prepared', work / 'prepared')
    for key in ('RESULTS_DIR', 'REPORTS_DIR', 'LOG_DIR', 'OBJECTS_DIR'):
        (work / deps['environment'][key].removeprefix('/work/')).mkdir(parents=True, exist_ok=True)
    (work / 'audit').mkdir(); (work / 'logs').mkdir(exist_ok=True)
    results = work / deps['environment']['RESULTS_DIR'].removeprefix('/work/')
    shutil.copyfile(args.terminal_odb, results / '3_3_place_gp.odb')
    shutil.copyfile(PLAN_DIR / 'new_source_constraint.sdc', results / 'new_source_constraint.sdc')
    (work / 'hooks').mkdir()
    restore_hooks(work, args.source_root, deps)
    # Verify exact image/tool/scripts/platform libraries and restored hooks in
    # the fresh namespace. No docker rm/stop/exec against the live container.
    expected = deps['files']
    verifier = verification_program()
    save(work / 'dependencies.json', expected)
    image = plan['identity']['image_id']
    prefix = ['docker', 'run', '--rm', '--network', 'none', '--mount', f'type=bind,src={work},dst=/work',
              '--mount', f'type=bind,src={args.source_root.resolve()},dst=/src,readonly', '--workdir', '/OpenROAD-flow-scripts/flow']
    code = run([*prefix, '--entrypoint', 'python3', image, '-c', verifier], log=work / 'logs/identity.log')
    if code != 0:
        save(work / 'identity_process.json', dict(exit_code=code, status='REFUSED_SOURCE_IDENTITY'))
        return code
    save(work / 'identity_process.json', dict(exit_code=0, status='IDENTITY_VERIFIED'))
    sequence = [('initial', None)] + [(s[0], s) for s in STAGES]
    for name, stage in sequence:
        command = [*prefix, '--entrypoint', deps['environment']['OPENROAD_EXE'], image,
                   '-exit', '-no_init', '-threads', deps['environment']['NUM_CORES'], '-no_splash',
                   '/work/prepared/' + name + '.tcl', '-metrics', deps['environment']['LOG_DIR'] + '/' + name + '.json']
        started = time.time_ns()
        code = run(command, log=work / 'logs' / (name + '.raw.log'))
        record = dict(stage=name, argv=command, exit_code=code, started_ns=started,
                      ended_ns=time.time_ns(), qualification='NOT_QUALIFIED')
        save(work / (name + '.process.json'), record)
        if code != 0: return code
        # Output hashes and audit refusal remain even if later gates fail.
        if stage:
            output = results / stage[3]
            if not output.is_file() or output.stat().st_size == 0:
                raise ValueError('expected stage ODB missing: ' + str(output))
            save(work / (name + '.artifact.json'), dict(odb_sha256=digest(output), bytes=output.stat().st_size))
            if stage[4] and not (results / stage[4]).is_file():
                raise ValueError('expected NEW canonical stage SDC missing')
            if name == 'final_report':
                spef = results / '6_final.spef'
                if not spef.is_file() or spef.stat().st_size == 0:
                    raise ValueError('final extracted SPEF missing; estimates cannot qualify timing')
                save(work / 'final_extraction.json', dict(spef_sha256=digest(spef), bytes=spef.stat().st_size))
        try:
            audit = endpoint_audit.audit(endpoint_audit.decode_rows(work / 'audit' / (name + '.rows')),
                 (work / 'audit' / (name + '.actual.sdc')).read_text(), final=name == 'final_report')
        except (ValueError, OSError) as exc:
            save(work / (name + '.audit_refusal.json'), dict(status='AUDIT_REFUSED',
                 reason=str(exc), exception_type=type(exc).__name__, physical_signoff=False,
                 checkpoints_preserved=True))
            raise
        save(work / (name + '.audit.json'), audit)
        if name == 'detail_place': shutil.copyfile(results / '3_5_place_dp.odb', results / '3_place.odb')
        if name == 'cts': shutil.copyfile(results / '4_1_cts.odb', results / '4_cts.odb')
        if name == 'fillcell':
            shutil.copyfile(results / '5_3_fillcell.odb', results / '5_route.odb')
            shutil.copyfile(results / '5_1_grt.sdc', results / '5_route.sdc')
        if name == 'density_fill': shutil.copyfile(results / '5_route.sdc', results / '6_1_fill.sdc')
    # Full physical metrics/DRC/antenna gate is separate; never promote timing
    # coverage or a successful process into complete physical signoff.
    save(work / 'terminal.json', dict(status='STAGES_RETURNED_TIMING_AUDITED', physical_signoff=False,
         historical_failure_unchanged=True, new_constraint_lineage=True))
    return 0


if __name__ == '__main__':
    args = sys.argv[1:]
    if '--run-admitted-new-source-constraints' in args:
        import run_abi3_physical_persistent as persistent
        module = sys.modules[__name__]
        index = args.index('--persistent-workdir')
        workdir = Path(args[index + 1]); del args[index:index + 2]
        index = args.index('--launch-receipt')
        receipt = Path(args[index + 1]); del args[index:index + 2]
        raise SystemExit(persistent.launch(module, args, workdir=workdir, receipt=receipt))
    raise SystemExit(main(args))
