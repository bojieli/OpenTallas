"""Read a completed same-host proof in place; never import proof/physical state.

Explicit opt-in for a new physical continuation. This is pre-route proof reuse,
not source qualification or a replacement for routed equivalence and sign-off.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import socket
import time

from lec_completed_transfer import identity

SCHEMA = 'opentallas.lec_completed_reference.v1'
FILE = 'lec_async.completed_reference.json'
META = ('core.json', 'pins.json', 'constraint.sdc', 'straps.json', 'sdc_lint.json',
        'lec_native_stub_metadata.json', 'lec_options.json', 'lec_hints.json',
        'reset_contract.json')


def digest(data):
    return hashlib.sha256(data).hexdigest()


def local(kit, rel):
    if rel.startswith('/work/'):
        rel = rel[6:]
    if Path(rel).is_absolute():
        raise ValueError('external proof input needs explicit closure: '+rel)
    p = kit / rel
    p.resolve().relative_to(kit)
    return p


def snapshot(original, target, host):
    original, target = Path(original).resolve(), Path(target).resolve()
    if original == target:
        raise ValueError('distinct physical continuation required')
    if host != socket.gethostname():
        raise ValueError('explicit producer host differs from current host')
    for kit in (original, target):
        for name in ('lec_async.stop', 'lec_async.abort', 'lec_async.aborted'):
            if (kit/name).exists():
                raise ValueError('proof has stop/abort marker: '+str(kit/name))
    # A reference never takes ownership of a target watcher or local verdict.
    for name in ('lec_async.pid', 'lec_async.rc', 'lec_async.done', 'lec_async.unit_rc'):
        if (target/name).exists():
            raise ValueError('target has local proof state: '+name)
    if not (original/'lec_async.done').is_file():
        raise ValueError('original proof is not completed')
    if (original/'lec_async.rc').read_text().strip() != '0':
        raise ValueError('original proof did not return zero')
    report_bytes = (original/'lec/lec.json').read_bytes()
    report = json.loads(report_bytes)
    counts = report.get('counts') or {}
    if (report.get('verdict') != 'EQUIVALENT' or counts.get('compare_points', 0) <= 0
            or counts.get('proved') != counts.get('compare_points')
            or counts.get('differs') != 0 or counts.get('undecided') != 0):
        raise ValueError('original proof is not completed EQUIVALENT')
    owner = (original/'lec_async.owner').read_text().strip()
    if not re.fullmatch(r'[A-Za-z0-9_.-]+', owner):
        raise ValueError('invalid original proof owner')
    run = json.loads((original/'lec_async.runs'/(owner+'.json')).read_text())
    if run.get('host') != host or run.get('run_id') != owner:
        raise ValueError('original owner host/identity differs')
    ready = original/'lec_async.ready'
    ready_bytes = ready.read_bytes()
    if (target/'lec_async.ready').exists() and (target/'lec_async.ready').read_bytes() != ready_bytes:
        raise ValueError('target proof command differs')
    epoch = ready.stat().st_mtime
    captured = {}
    for mode, name in (('source', 'lec_async.source_identity'), ('all', 'lec_async.identity')):
        value = (original/name).read_text().strip()
        if not re.fullmatch(r'[0-9a-f]{64}', value):
            raise ValueError('captured proof identity absent: '+name)
        if identity(original, mode, ready) != value or identity(target, mode, ready) != value:
            raise ValueError('captured proof identity differs: '+mode)
        limit = epoch if mode == 'source' else (original/'lec/lec.json').stat().st_mtime
        if (original/name).stat().st_mtime > limit + .001:
            raise ValueError('identity was not captured before proof: '+name)
        if (target/name).exists() and (target/name).read_text().strip() != value:
            raise ValueError('target identity header differs: '+name)
        captured[name] = value
    if run.get('source_id') != captured['lec_async.source_identity']:
        raise ValueError('owner source identity differs')
    args = shlex.split('\n'.join(ready_bytes.decode().splitlines()[1:]))
    if '--netlist' not in args:
        raise ValueError('explicit kit-local proof netlist required')
    net = args[args.index('--netlist')+1]
    if not net.startswith('/work/') or report.get('netlist') != net:
        raise ValueError('completed netlist differs from captured command')
    required = {'lec.py', net[6:]}
    for kit in (original, target):
        for f in (kit/'rtl').rglob('*'):
            if f.is_file():
                f.resolve().relative_to(kit)
                required.add(str(f.relative_to(kit)))
    required.update(META)
    cfg = (original/'config.mk').read_text()
    for line in cfg.splitlines():
        if re.match(r'^(?:override )?export (?:VERILOG_FILES|ADDITIONAL_LIBS)\s*=', line):
            for value in shlex.split(line.split('=', 1)[1]):
                if '$' not in value:
                    required.add(str(local(original, value).relative_to(original)))
    contract = original/'reset_contract.json'
    if contract.exists():
        receipt = json.loads(contract.read_text()).get('proof', {}).get('receipt')
        if receipt:
            required.add(str(local(original, receipt).relative_to(original)))
    rows = {}
    for rel in sorted(required):
        a, b = local(original, rel), local(target, rel)
        if a.is_file() != b.is_file():
            raise ValueError('proof metadata presence differs: '+rel)
        if not a.is_file():
            if rel not in META:
                raise ValueError('proof input absent: '+rel)
            rows[rel] = None
            continue
        if a.read_bytes() != b.read_bytes():
            raise ValueError('proof input differs: '+rel)
        if a.stat().st_mtime > epoch + .001:
            raise ValueError('retained proof input newer than readiness: '+rel)
        rows[rel] = digest(a.read_bytes())
    state = {n: digest((original/n).read_bytes()) for n in
             ('lec_async.ready', 'lec_async.source_identity', 'lec_async.identity',
              'lec_async.owner', 'lec_async.rc', 'lec_async.done', 'lec/lec.json')}
    # Recheck receipt and identities after collecting inputs, without copying them.
    if (original/'lec/lec.json').read_bytes() != report_bytes or ready.read_bytes() != ready_bytes:
        raise ValueError('original proof changed while read')
    for mode, name in (('source', 'lec_async.source_identity'), ('all', 'lec_async.identity')):
        if identity(original, mode, ready) != captured[name] or identity(target, mode, ready) != captured[name]:
            raise ValueError('proof inputs changed while read')
    return dict(schema=SCHEMA, producer_kit=str(original), consumer_kit=str(target),
                producer_host=host, producer_owner=owner, producer_scope=run.get('scope', ''),
                captured_identities=captured, netlist=net[6:], inputs_sha256=rows,
                producer_state_sha256=state, source_qualified=False,
                limitation='Completed pre-route proof reference only; no physical completion, source qualification, or routed EQ is transferred.')


def register(original, target, host):
    target = Path(target).resolve()
    # Never attach a protocol to an active physical scope. A completed PLACE may
    # be consumed later, but a live scope keeps its frozen helper and records.
    for f in (target/'lec_async.runs').glob('*.json'):
        run = json.loads(f.read_text())
        if (target/'physical_completion'/(run.get('run_id', '')+'.json')).exists():
            continue
        scope = run.get('scope', '').splitlines()
        cgroups = [s.split(':', 2)[2] for s in scope if s.startswith('0::')]
        for group in cgroups:
            p = Path('/sys/fs/cgroup')/group.lstrip('/')/'cgroup.procs'
            if p.exists() and p.read_text().strip():
                raise ValueError('target physical scope is still active')
    value = snapshot(original, target, host)
    out = target/FILE
    if out.exists():
        if json.loads(out.read_text()) != value:
            raise ValueError('different completed reference already registered')
    else:
        temp = out.with_suffix('.tmp')
        temp.write_text(json.dumps(value, indent=1)+'\n')
        os.replace(temp, out)
    return value


def validate(target):
    target = Path(target).resolve()
    saved = json.loads((target/FILE).read_text())
    if saved.get('schema') != SCHEMA or saved.get('consumer_kit') != str(target):
        raise ValueError('completed reference protocol/consumer differs')
    now = snapshot(saved['producer_kit'], target, saved['producer_host'])
    if saved != now:
        raise ValueError('completed reference input/receipt snapshot differs')
    return now


if __name__ == '__main__':
    import sys
    try:
        if sys.argv[1] == 'register':
            result = register(*sys.argv[2:])
        elif sys.argv[1] == 'validate':
            result = validate(*sys.argv[2:])
        else:
            raise ValueError('expected register or validate')
        print('LEC_ASYNC completed proof reference '+result['captured_identities']['lec_async.identity'], file=sys.stderr)
    except Exception as exc:
        print('LEC_ASYNC completed reference rejected: '+str(exc), file=sys.stderr)
        sys.exit(11)
