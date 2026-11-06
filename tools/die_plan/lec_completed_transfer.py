"""Import only a completed EQ receipt with captured, unchanged proof identities.

Physical failure is independent of proof completion. This receipt never grants
source qualification or replaces routed equivalence/signoff.
"""
import hashlib
import json
from pathlib import Path
import re
import shlex
import subprocess


def identity(kit, mode='all', ready=None):
    script = Path(__file__).with_name('lec_async.sh')
    return subprocess.check_output(['bash', str(script), 'identity', str(kit), mode,
                                    str(ready or Path(kit)/'lec_async.ready')], text=True).strip()


def transfer(original, copied):
    original, copied = Path(original).resolve(), Path(copied).resolve()
    if original == copied:
        raise ValueError('fresh continuation copy required')
    for k in (original, copied):
        if (k/'lec_async.stop').exists() or (k/'lec_async.abort').exists():
            raise ValueError('proof has a stop/abort marker')
    if (copied/'lec_async.pid').exists():
        raise ValueError('target has a watcher PID; fresh continuation required')
    if not (original/'lec_async.done').is_file() or not (original/'lec_async.rc').is_file():
        raise ValueError('original proof is not completed')
    raw = (original/'lec/lec.json').read_bytes()
    report = json.loads(raw)
    if report.get('verdict') != 'EQUIVALENT' or (original/'lec_async.rc').read_text().strip() != '0':
        raise ValueError('original proof is not completed EQUIVALENT')
    expected = {}
    ready = original/'lec_async.ready'
    for mode, name in [('source','lec_async.source_identity'),('all','lec_async.identity')]:
        if not (original/name).is_file():
            raise ValueError('captured proof identity absent: '+name)
        value = (original/name).read_text().strip()
        if not re.fullmatch('[0-9a-f]{64}', value):
            raise ValueError('captured proof identity absent: '+name)
        if identity(original,mode,ready) != value or identity(copied,mode,ready) != value:
            raise ValueError('captured proof identity differs: '+mode)
        captured_at = (original/name).stat().st_mtime
        limit = ready.stat().st_mtime if mode=='source' else (original/'lec/lec.json').stat().st_mtime
        if captured_at > limit+.001:
            raise ValueError('identity was not captured before proof: '+name)
        expected[name] = value
    net = report.get('netlist','')
    if not net.startswith('/work/'):
        raise ValueError('proof netlist must be kit-local')
    args = shlex.split('\n'.join(ready.read_text().splitlines()[1:]))
    if '--netlist' not in args or args[args.index('--netlist')+1] != net:
        raise ValueError('completed proof netlist differs from captured command')
    required = ['config.mk','freeze.json','lec.py',net[6:]]
    required += [str(p.relative_to(original)) for p in (original/'rtl').rglob('*') if p.is_file()]
    # Retain proof metadata omitted by older async identity schemas as well.
    required += [n for n in ('core.json','pins.json','lec_native_stub_metadata.json','lec_options.json','lec_hints.json','reset_contract.json') if (original/n).is_file() or (copied/n).is_file()]
    if (original/'reset_contract.json').exists():
        receipt=json.loads((original/'reset_contract.json').read_text()).get('proof',{}).get('receipt')
        if receipt: required.append(receipt[6:] if receipt.startswith('/work/') else receipt)
    for line in (original/'config.mk').read_text().splitlines():
        if re.match(r'^(?:override )?export (?:VERILOG_FILES|ADDITIONAL_LIBS)\s*=',line):
            for value in shlex.split(line.split('=',1)[1]):
                if '$' in value: continue
                if not value.startswith('/work/'):
                    raise ValueError('external proof input needs explicit closure: '+value)
                required.append(value[6:])
    rows = {}
    epoch = ready.stat().st_mtime
    for rel in sorted(set(required)):
        a,b=original/rel,copied/rel
        a.resolve().relative_to(original); b.resolve().relative_to(copied)
        if not a.is_file() or not b.is_file() or a.read_bytes()!=b.read_bytes():
            raise ValueError('continuation input differs or absent: '+rel)
        if a.stat().st_mtime > epoch+.001:
            raise ValueError('retained input newer than proof readiness: '+rel)
        rows[rel]=hashlib.sha256(a.read_bytes()).hexdigest()
    artifacts = {n:(original/n).read_bytes() for n in
                 ['lec_async.ready','lec_async.rc','lec_async.source_identity','lec_async.identity','lec/lec.json']}
    for n,data in artifacts.items():
        dest=copied/n
        if dest.exists() and dest.read_bytes()!=data:
            raise ValueError('target completed receipt differs: '+n)
    image=original/'image.txt'
    descriptor=dict(schema='opentallas.lec_completed_transfer.v2',original=str(original),copied=str(copied),
        historical_provenance=report.get('provenance'),historical_identity_available=True,
        captured_identities=expected,current_files_sha256=rows,
        completed_artifacts_sha256={n:hashlib.sha256(v).hexdigest() for n,v in artifacts.items()},
        donor_physical_receipt_sha256=hashlib.sha256(image.read_bytes()).hexdigest() if image.exists() else None,
        limitation='Exact completed pre-route proof continuation only; no source qualification or replacement for routed EQ.',
        counts=report.get('counts'),source_qualified=False)
    out=copied/'lec_async.transfer.json'
    if out.exists() and json.loads(out.read_text())!=descriptor:
        raise ValueError('different completed-proof transfer already recorded')
    # Recheck the donor after collecting its snapshot. Never import a changing receipt.
    for n,data in artifacts.items():
        if (original/n).read_bytes()!=data: raise ValueError('donor receipt changed during transfer')
    for mode,name in [('source','lec_async.source_identity'),('all','lec_async.identity')]:
        if identity(original,mode,ready)!=expected[name] or identity(copied,mode,ready)!=expected[name]:
            raise ValueError('proof inputs changed during transfer')
    for n,data in artifacts.items():
        dest=copied/n; dest.parent.mkdir(parents=True,exist_ok=True)
        if not dest.exists(): dest.write_bytes(data)
    if not out.exists(): out.write_text(json.dumps(descriptor,indent=1)+'\n')
    return descriptor


if __name__=='__main__':
    import sys
    print(json.dumps(transfer(*sys.argv[1:])))
