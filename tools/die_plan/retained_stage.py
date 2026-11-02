#!/usr/bin/env python3
"""Default-OFF CTS-only continuation of a reviewed retained placement.

No synthesis, proof rerun, async marker, GRT, route or sign-off is permitted.
The standalone proof join is current-byte continuation evidence, not a new
source qualification. Prepare creates a fresh owned copy; run must use ot-run.
"""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kit_modes

SCHEMA = 'opentallas.retained_cts.v1'
MAKEFILE_SHA = '036a76c4b673214f346491ff548d7bd2af2ab74de0351975197d22f081ea3216'
ESSENTIAL = {'cts_post.tcl', 'kit_modes.py', 'orfs_hold_mm.py', 'orfs_hold_mm.tcl',
             'constraint.sdc', 'vclk_ff.sdc'}
LIMIT = ('CTS_ONLY_CONTINUATION: current-byte standalone proof join only; historical provenance limitations '
         'are retained. No source/native/parent qualification, GRT, route, SIGNED or count credit.')


class Refuse(ValueError):
    pass


def read(path):
    return json.loads(Path(path).read_text())


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def local(root, name):
    p = root / name
    if Path(name).is_absolute() or '..' in Path(name).parts or not p.is_file():
        raise Refuse('missing/nonlocal input: ' + name)
    if p.is_symlink() or root not in p.resolve().parents:
        raise Refuse('symlink/external input: ' + name)
    return p


def verify(root, rows):
    for name, sha in rows.items():
        if not re.fullmatch('[0-9a-f]{64}', str(sha)) or digest(local(root, name)) != sha:
            raise Refuse('input hash differs: ' + name)


def work_paths(text):
    return set(re.findall(r'/work/([A-Za-z0-9_./+-]+)', text))


def container_uses(container, roots):
    """A broad shared scratch mount alone is not an exclusive native kit lease."""
    config = container.get('Config', {})
    cwd = Path(config.get('WorkingDir') or '/')
    command = ' '.join(config.get('Cmd') or []) + ' ' + ' '.join(config.get('Entrypoint') or [])
    for mount in container.get('Mounts', []):
        source = Path(mount.get('Source', '/')).resolve()
        for root in roots:
            if source == root or root in source.parents:
                return True
            if source in root.parents:
                # Map container cwd back to the host for ancestor bind mounts.
                destination = Path(mount.get('Destination', '/'))
                if cwd == destination or destination in cwd.parents:
                    host_cwd = source / cwd.relative_to(destination)
                    if host_cwd == root or root in host_cwd.parents:
                        return True
                if str(root) in command:
                    return True
    return False


def native_leases(roots):
    """Fail closed on mounted native containers, matching host CAD, or locked leases."""
    roots = [Path(r).resolve() for r in roots]
    leases = []
    ids = subprocess.run(['docker', 'ps', '-q'], capture_output=True, text=True, check=True).stdout.split()
    if ids:
        ds = json.loads(subprocess.run(['docker', 'inspect', *ids], capture_output=True, text=True, check=True).stdout)
        for d in ds:
            if container_uses(d, roots):
                leases.append('docker:' + d['Id'])
    for p in Path('/proc').iterdir():
        if not p.name.isdigit() or int(p.name) == os.getpid():
            continue
        try:
            comm = (p / 'comm').read_text().strip()
            if comm not in ('openroad', 'yosys', 'yosys-abc', 'make', 'docker', 'ot-heavy', 'ot-heavy-exit'):
                continue
            args = (p / 'cmdline').read_bytes().replace(b'\0', b' ').decode(errors='replace')
            cwd = (p / 'cwd').resolve()
            if any(str(r) in args or (cwd == r or r in cwd.parents) for r in roots):
                leases.append('pid:' + p.name)
        except FileNotFoundError:
            pass
        except PermissionError as e:
            raise Refuse('native lease probe unreadable: ' + p.name) from e
    for root in roots:
        for p in list(root.glob('native*.lease')) + list(root.glob('*.native_lease.json')):
            with p.open('rb') as f:
                try:
                    fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
                except BlockingIOError:
                    leases.append('lease:' + str(p))
    return leases


def no_later_stage(kit):
    later = [str(p.relative_to(kit)) for p in (kit / 'run/results').rglob('*')
             if p.is_file() and re.match(r'[4-6]_', p.name)]
    if later:
        raise Refuse('fresh CTS input has later-stage outputs: ' + ', '.join(later[:3]))


def geometry_join(identity, gate, closure, place_sha, gate_schema,
                  attestation=None, attestation_sha=None, expected_before=None):
    """Formal source identity and physical correction lineage are distinct joins."""
    if closure.get('reviewed_3_place_sha256') != place_sha:
        raise Refuse('placement closure identity differs')
    if gate_schema == 'receipt-and-counts':
        if identity.get('corrected_odb_sha256') != place_sha or gate.get('corrected_odb_sha256') != place_sha:
            raise Refuse('placement review identity differs')
        if any(x is not None for x in (attestation, attestation_sha, expected_before)):
            raise Refuse('unexpected historical geometry adapter on current gate')
        return dict(kind='current-gate-corrected-placement', reviewed_3_place_sha256=place_sha)
    if ('corrected_odb_sha256' in identity or 'corrected_odb_sha256' in gate or
            not re.fullmatch('[0-9a-f]{64}', str(gate.get('checkpoint_sha256')))):
        raise Refuse('unsupported historical physical gate shape')
    if (not attestation or not re.fullmatch('[0-9a-f]{64}', str(attestation_sha)) or
            not re.fullmatch('[0-9a-f]{64}', str(expected_before))):
        raise Refuse('historical geometry requires explicit attestation path/SHA and expected-before SHA')
    attestation = Path(attestation)
    if not attestation.is_file() or digest(attestation) != attestation_sha:
        raise Refuse('geometry attestation digest differs')
    doc = read(attestation)
    fields = {'all_inst_master_dimensions', 'all_other_inst_pose_status_donttouch', 'net_headers',
              'full_iterm_membership', 'full_bterm_membership', 'full_net_graph',
              'typed_clock_graph', 'all_ports_boxes_net_io_sigtype', 'all_rows'}
    before, after = doc.get('old_mover', {}), doc.get('new_mover', {})
    census_counts = {'instances', 'nets', 'iterms', 'net_bterms', 'ports', 'port_boxes', 'rows', 'typed_clock_nets'}
    mover_fields = {'name', 'xy', 'orientation', 'master', 'master_dimensions', 'placement_status', 'dont_touch'}
    if (doc.get('verdict') != 'PASS' or doc.get('old_odb_sha256') != expected_before or
            doc.get('new_odb_sha256') != place_sha or expected_before == place_sha or
            not doc.get('scope', '').startswith('exact one existing reset FF XY change only;') or
            not fields <= set(doc.get('equal_digests', {})) or
            any(not re.fullmatch('[0-9a-f]{64}', str(doc['equal_digests'][k])) for k in fields) or
            not census_counts <= set(doc.get('counts', {})) or
            any(type(doc['counts'][k]) is not int or doc['counts'][k] <= 0 for k in census_counts) or
            any(len(doc.get('outline_dbu', {}).get(k, [])) != 4 for k in ('die', 'core')) or
            not mover_fields <= set(before) or not mover_fields <= set(after) or
            any(len(m.get('xy', [])) != 2 or any(type(v) is not int for v in m['xy']) for m in (before, after)) or
            not before.get('name') or before.get('xy') == after.get('xy') or
            {k:v for k,v in before.items() if k != 'xy'} != {k:v for k,v in after.items() if k != 'xy'}):
        raise Refuse('unsupported/tampered frozen geometry transition attestation')
    return dict(kind='explicit-historical-frozen-census', attestation_path=str(attestation.resolve()),
                attestation_sha256=attestation_sha, expected_before_3_place_sha256=expected_before,
                reviewed_after_3_place_sha256=place_sha,
                historical_gate_checkpoint_sha256=gate['checkpoint_sha256'],
                distinction='Historical gate checkpoint is the earlier3_3 stage; it is NOT the census old3_place. '
                            'Formal source proof is joined independently; this exact caller-bound census joins '
                            'the reviewed old/new placement only, without timing or source qualification.')


def validate(kit, proof, place_sha, place_sdc_sha, stage='cts', lease_probe=native_leases, *,
             geometry_attestation=None, geometry_attestation_sha=None, geometry_before_sha=None):
    if stage != 'cts':
        raise Refuse('only CTS_ONLY_CONTINUATION is supported')
    kit, proof = Path(kit).resolve(), Path(proof).resolve()
    if kit == proof:
        raise Refuse('separate retained placement and standalone proof required')
    active = lease_probe([kit, proof])
    if active:
        raise Refuse('active native lease: ' + ', '.join(active))
    no_later_stage(kit)
    if any(p.name != 'lec_async.sh' for p in kit.glob('lec_async.*')):
        raise Refuse('standalone consumer refuses async controller state')
    if any(p.is_symlink() for p in kit.rglob('*')):
        raise Refuse('retained input tree contains symlinks')
    identity = read(kit / 'source_proof_identity.json')
    gate = read(kit / 'SOURCE_EQ_GATE.json')
    closure = read(kit / 'prepared_input_closure.json')
    rows = identity['inputs_sha256']
    if gate.get('source_inputs_verified') != len(rows) or closure.get('source_inputs_verified') != len(rows):
        raise Refuse('source identity census differs')
    if not rows or gate.get('verdict') != 'PASS' or closure.get('verdict') != 'PASS':
        raise Refuse('source proof/closure gate is missing or not PASS')
    if str(proof) != identity.get('proof_kit'):
        raise Refuse('standalone proof location differs from identity')
    verify(kit, rows)
    verify(proof, rows)
    required = {'config.mk', 'constraint.sdc', 'vclk_ff.sdc', 'pins.json', 'reset_contract.json',
                'lec_hints.json'} | {str(p.relative_to(kit)) for p in (kit / 'rtl').rglob('*') if p.is_file()}
    cfg = (kit / 'config.mk').read_text()
    variables = kit_modes.mk_vars(cfg)
    for key in ('VERILOG_FILES', 'ADDITIONAL_LIBS'):
        for value in shlex.split(variables.get(key, '')):
            if not value.startswith('/work/') or '$' in value:
                raise Refuse('proof input requires explicit local closure: ' + value)
            required.add(value[6:])
    reset = read(kit / 'reset_contract.json')
    required.add(reset['proof']['receipt'])
    net = read(proof / 'lec/lec.json').get('netlist', '')
    if not net.startswith('/work/'):
        raise Refuse('standalone proof netlist is not kit-local')
    required.add(net[6:])
    mapped = list(kit.glob('run/results/*/*/base/1_synth.v'))
    if len(mapped) != 1:
        raise Refuse('exact mapped synthesis netlist required')
    required.add(str(mapped[0].relative_to(kit)))
    if not required <= set(rows):
        raise Refuse('proof identity closure incomplete: ' + ', '.join(sorted(required - set(rows))))
    rp = local(proof, 'lec/lec.json')
    report = read(rp)
    receipt_sha = digest(rp)
    if any(x != receipt_sha for x in (identity.get('receipt_sha256'), closure.get('official_eq_sha256'),
                                      digest(local(kit, 'source_proof/lec.json')))):
        raise Refuse('standalone EQ receipt hash differs')
    if 'counts' in gate:
        gate_schema = 'receipt-and-counts'
        gate_counts = gate['counts']
        if gate.get('official_receipt_sha256') != receipt_sha:
            raise Refuse('SOURCE_EQ_GATE receipt hash differs')
        if 'official_counts' in gate and gate['official_counts'] != gate_counts:
            raise Refuse('conflicting SOURCE_EQ_GATE count fields')
    elif 'official_counts' in gate:
        # Historical R2 gate: no digest is invented or inserted into that file.
        # The completed receipt has already joined independently to identity,
        # closure, and the retained source_proof copy above.
        gate_schema = 'historical-official-counts'
        gate_counts = gate['official_counts']
        if ('official_receipt_sha256' in gate and
                gate['official_receipt_sha256'] != receipt_sha):
            raise Refuse('historical SOURCE_EQ_GATE receipt hash differs')
    else:
        raise Refuse('unsupported SOURCE_EQ_GATE proof-count schema')
    status = (proof / 'official_lec.status').read_text()
    if not re.search(r'(^|\s)official_lec_exit=0(\s|$)', status):
        raise Refuse('official standalone proof did not complete exit 0')
    if local(kit, 'source_proof/official_lec.status').read_text() != status:
        raise Refuse('standalone completion status copy differs')
    counts = report.get('counts', {})
    if (report.get('verdict') != 'EQUIVALENT' or not counts.get('compare_points') or
            counts.get('proved') != counts.get('compare_points') or counts.get('differs') != 0 or
            counts.get('undecided') != 0 or report.get('failing') or report.get('unproven_points') or
            report.get('top') != variables.get('DESIGN_NAME') or gate_counts != counts):
        raise Refuse('completed EQ/all-point result missing')
    if report.get('hints', {}).get('sha256') != rows['lec_hints.json']:
        raise Refuse('official proof used different hints')
    keep = report.get('kept_registers', {})
    if (not isinstance(keep, dict) or not keep.get('declared') or keep.get('in_netlist') != keep['declared'] or
            any(keep.get(k, {}).get('n') != 0 for k in ('constant_proved', 'missing', 'unobservable_removed'))):
        raise Refuse('complete KEEP proof missing')
    rc = report.get('reset_contract', {})
    if not rc.get('used') or rc.get('debug_overrides') or report.get('noreset_constants', {}).get('raw_base_steps', 0):
        raise Refuse('missing or debug reset policy')
    helpers = closure.get('required_runtime_files_sha256', {})
    if not ESSENTIAL <= set(helpers):
        raise Refuse('common CTS/MM helper closure incomplete')
    verify(kit, helpers)
    for name in work_paths(cfg):
        p = kit / name
        if p.is_dir():
            if any(str(f.relative_to(kit)) not in rows for f in p.rglob('*') if f.is_file()):
                raise Refuse('config directory has unbound files: ' + name)
        elif name not in rows and name not in helpers:
            raise Refuse('config reference not bound: ' + name)
    for edge in closure.get('hook_edges', []):
        if edge['from'] not in helpers or edge['to'] not in helpers:
            raise Refuse('runtime hook edge is not closed')
    places = list(kit.glob('run/results/*/*/base/3_place.odb'))
    if len(places) != 1:
        raise Refuse('one reviewed 3_place checkpoint required')
    place = str(places[0].relative_to(kit));sdc = str(places[0].with_suffix('.sdc').relative_to(kit))
    geometry = geometry_join(identity, gate, closure, place_sha, gate_schema,
                             geometry_attestation, geometry_attestation_sha, geometry_before_sha)
    binding = {**rows, **helpers, place: place_sha, sdc: place_sdc_sha}
    for name in ('sdc_lint.json', 'clock_binding.json', 'freeze.json', 'source_proof/lec.json',
                 'source_proof/official_lec.status', 'source_proof_identity.json',
                 'SOURCE_EQ_GATE.json', 'prepared_input_closure.json'):
        binding[name] = digest(local(kit, name))
    if (kit / 'lec_async.sh').is_file():
        binding['lec_async.sh'] = digest(local(kit, 'lec_async.sh'))
    for f in (kit / 'run/results').rglob('*'):
        if f.is_file() and re.match('[1-3]_', f.name):
            binding.setdefault(str(f.relative_to(kit)), digest(f))
    verify(kit, binding)
    modes = kit_modes.check(kit, 'cts')
    return dict(schema=SCHEMA, stage='CTS_ONLY_CONTINUATION', kit=str(kit), proof_kit=str(proof),
                proof_receipt_sha256=receipt_sha, files_sha256=binding, placement=place, placement_sdc=sdc,
                counts=counts, kept_registers=keep, reset_contract=rc, historical_provenance=report.get('provenance'),
                source_gate_schema=gate_schema, geometry_evidence=geometry,
                modes=modes, source_qualified=False, limitation=LIMIT)


def makefile_contract(path):
    text = Path(path).read_text()
    if digest(path) != MAKEFILE_SHA:
        raise Refuse('pinned ORFS Makefile differs; review do-cts contract before use')
    for anchor in ('do-cts:\n\t$(UNSET_AND_MAKE) do-4_1_cts do-4_cts',
                   'do-$(1): $(OBJECTS_DIR)/copyright.txt', 'do-$(1)$(if $(4),$(4),):\n\tcp '):
        if anchor not in text:
            raise Refuse('ORFS dependency-free CTS contract absent')


def runtime_bootstrap_script(threads):
    # Generation-only constants need a repository tree. Runtime verification
    # at /retained-api must not eagerly import that module.
    import core_flow
    if type(threads) is not int or threads < 1:
        raise Refuse('positive integer threads required')
    return ('#!/bin/bash\nset -euo pipefail\n'
            'trap \'r=$?; chown -R "${HUID:-1000}:${HGID:-1000}" /work 2>/dev/null || true; exit "$r"\' EXIT\n'
            'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1\n'
            'python3 -I /retained-api/retained_stage.py check-makefile /OpenROAD-flow-scripts/flow/Makefile\n'
            'python3 -I /work/kit_modes.py check /work --step cts > /work/retained_cts_modes.log 2>&1\n'
            'rc=0\n' + core_flow.runtime_mm_patch_step() + '\n[ "$rc" = 0 ] || exit "$rc"\n'
            'cd /OpenROAD-flow-scripts/flow\n')


def runtime_script(threads):
    return (runtime_bootstrap_script(threads) +
            f'make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES={threads} do-cts\n')


def prepare(kit, proof, output, place_sha, place_sdc_sha, *, enabled=False, stage='cts',
            threads=8, image='openroad/orfs:asap7lock', lease_probe=native_leases,
            geometry_attestation=None, geometry_attestation_sha=None, geometry_before_sha=None):
    if not enabled:
        raise Refuse('retained CTS is default-OFF; explicit --enable-retained-cts required')
    desc = validate(kit, proof, place_sha, place_sdc_sha, stage, lease_probe,
                    geometry_attestation=geometry_attestation, geometry_attestation_sha=geometry_attestation_sha,
                    geometry_before_sha=geometry_before_sha)
    output = Path(output).absolute()
    if output.exists() or output.is_symlink() or Path(kit).resolve() in output.parents:
        raise Refuse('fresh separate owned output required')
    image_id = subprocess.run(['docker', 'image', 'inspect', '--format', '{{.Id}}', image],
                              capture_output=True, text=True, check=True).stdout.strip()
    if not re.fullmatch(r'sha256:[0-9a-f]{64}', image_id):
        raise Refuse('immutable ORFS image identity missing')
    script_text = runtime_script(threads)
    output.mkdir(parents=True)
    shutil.copytree(kit, output / 'kit', symlinks=False)
    # Re-validate after the snapshot: a changing input cannot become a joined proof.
    verify(output / 'kit', desc['files_sha256'])
    if geometry_attestation:
        shutil.copy2(geometry_attestation, output / 'geometry_attestation.json')
        if digest(output / 'geometry_attestation.json') != geometry_attestation_sha:
            raise Refuse('geometry attestation changed during snapshot')
    api = output / 'api';api.mkdir()
    for name in ('retained_stage.py', 'core_flow.py', 'kit_modes.py'):
        shutil.copy2(Path(__file__).parent / name, api / name)
    script = output / 'cts_runtime.sh';script.write_text(script_text)
    desc.update(output=str(output), image=image_id, threads=threads, make_target='do-cts',
                orfs_makefile_sha256=MAKEFILE_SHA,
                api_sha256={p.name:digest(p) for p in api.iterdir()}, script_sha256=digest(script))
    (output / 'standalone_proof_join.json').write_text(json.dumps(desc, indent=1) + '\n')
    (output / '.keep').write_text(LIMIT + '\n')
    return desc


def admitted_memory(memory):
    if type(memory) is not int or memory < 1:
        raise Refuse('positive admitted memory cap required')
    groups = Path('/proc/self/cgroup').read_text().splitlines()
    paths = [x.split(':', 2)[2] for x in groups if x.startswith('0::')]
    if len(paths) != 1 or not re.search(r'oth-[^/]+\.scope', paths[0]):
        raise Refuse('run this CTS consumer through ot-run admission')
    current = Path('/sys/fs/cgroup') / paths[0].lstrip('/')
    while current != Path('/sys/fs/cgroup'):
        if current.name.startswith('oth-') and current.name.endswith('.scope'):
            cap = (current / 'memory.max').read_text().strip()
            if cap == 'max' or memory * (1 << 30) > int(cap):
                raise Refuse('container memory exceeds admitted native scope')
            return
        current = current.parent
    raise Refuse('admitted native memory scope absent')


def run(output, memory, *, enabled=False, stage='cts', lease_probe=native_leases):
    if not enabled or stage != 'cts':
        raise Refuse('explicit CTS_ONLY_CONTINUATION required')
    output = Path(output).resolve();desc = read(output / 'standalone_proof_join.json');kit = output / 'kit'
    if desc.get('stage') != 'CTS_ONLY_CONTINUATION' or desc.get('output') != str(output):
        raise Refuse('wrong continuation descriptor/stage')
    admitted_memory(memory)
    if not isinstance(memory, int) or memory < 1:
        raise Refuse('admitted memory cap required')
    lock = (output / 'native_cts.lease').open('a+')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    if (output / 'cts_completion.json').exists():
        raise Refuse('continuation already completed; preserve its result')
    if lease_probe([kit]):
        raise Refuse('active native lease on continuation')
    verify(kit, desc['files_sha256']);verify(output / 'api', desc['api_sha256'])
    geometry = desc.get('geometry_evidence', {})
    if geometry.get('kind') == 'explicit-historical-frozen-census':
        if digest(local(output, 'geometry_attestation.json')) != geometry['attestation_sha256']:
            raise Refuse('sealed geometry attestation changed')
    if digest(output / 'cts_runtime.sh') != desc['script_sha256']:
        raise Refuse('common CTS runtime changed')
    no_later_stage(kit)
    command = ['docker', 'run', '--rm', '--name', 'retained-cts-' + str(os.getpid()),
               '--memory', f'{memory}g', '--memory-swap', f'{memory}g', '--cpus', str(desc['threads']),
               '-e', f'HUID={os.getuid()}', '-e', f'HGID={os.getgid()}',
               '-v', f'{kit}:/work', '-v', f'{output / "api"}:/retained-api:ro',
               '-v', f'{output / "cts_runtime.sh"}:/retained_cts.sh:ro', '-w', '/work',
               desc['image'], 'bash', '/retained_cts.sh']
    started = time.time()
    native_error = None
    with (output / 'cts_native.log').open('w') as log:
        try:
            rc = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT).returncode
        except OSError as error:
            native_error = str(error);rc = 127
    completion = dict(schema=SCHEMA, stage='CTS_ONLY_CONTINUATION', started=started, ended=time.time(),
                      native_rc=rc, rc=rc, source_qualified=False, limitation=LIMIT)
    if native_error:
        completion['native_error'] = native_error
    try:
        verify(kit, desc['files_sha256'])
        unexpected = [p.name for p in (kit / 'run').rglob('*') if re.match('[5-6]_', p.name)]
        if unexpected:
            raise Refuse('unexpected later physical stage: ' + str(unexpected[:3]))
        result = list(kit.glob('run/results/*/*/base/4_cts.odb'))
        if rc == 0 and (len(result) != 1 or not result[0].with_suffix('.sdc').is_file()):
            raise Refuse('native CTS exit0 without 4_cts ODB/SDC checkpoint')
        if result:
            completion['checkpoint'] = dict(path=str(result[0].relative_to(kit)), sha256=digest(result[0]))
            if result[0].with_suffix('.sdc').is_file():
                completion['checkpoint']['sdc_sha256'] = digest(result[0].with_suffix('.sdc'))
    except (Refuse, OSError) as error:
        completion.update(rc=11, refusal=str(error))
    (output / 'cts_completion.json').write_text(json.dumps(completion, indent=1) + '\n')
    return completion


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='cmd', required=True)
    v = sub.add_parser('prepare');v.add_argument('--kit', required=True);v.add_argument('--proof-kit', required=True)
    v.add_argument('--out', required=True);v.add_argument('--place-sha256', required=True);v.add_argument('--place-sdc-sha256', required=True)
    v.add_argument('--threads', type=int, default=8);v.add_argument('--image', default='openroad/orfs:asap7lock')
    v.add_argument('--geometry-attestation');v.add_argument('--geometry-attestation-sha256');v.add_argument('--geometry-before-sha256')
    r = sub.add_parser('run');r.add_argument('output');r.add_argument('--mem', type=int, required=True)
    for a in (v, r):
        a.add_argument('--enable-retained-cts', action='store_true');a.add_argument('--stage', default='cts')
    c = sub.add_parser('check-makefile');c.add_argument('path')
    a = p.parse_args()
    try:
        if a.cmd == 'check-makefile':
            makefile_contract(a.path);return 0
        if a.cmd == 'prepare':
            result = prepare(a.kit, a.proof_kit, a.out, a.place_sha256, a.place_sdc_sha256,
                             enabled=a.enable_retained_cts, stage=a.stage, threads=a.threads, image=a.image,
                             geometry_attestation=a.geometry_attestation, geometry_attestation_sha=a.geometry_attestation_sha256,
                             geometry_before_sha=a.geometry_before_sha256)
        else:
            result = run(a.output, a.mem, enabled=a.enable_retained_cts, stage=a.stage)
        print(json.dumps(result, indent=1))
        return result.get('rc', 0)
    except (Refuse, OSError, ValueError, subprocess.CalledProcessError) as e:
        p.exit(2, 'RETAINED_CTS REFUSED: ' + str(e) + '\n')


if __name__ == '__main__':
    raise SystemExit(main())
