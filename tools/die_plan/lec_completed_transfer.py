"""Explicit current-byte transfer of an unchanged completed legacy proof candidate.

Historical input identity remains unknown. This is physical-continuation evidence,
not source qualification or a replacement for actual post-route EQ.
"""
import hashlib
import json
from pathlib import Path
import re
import shlex
import shutil
import os


def transfer(original, copied, *, finished_proof=False):
    original, copied = Path(original).resolve(), Path(copied).resolve()
    if original == copied:
        raise ValueError('fresh continuation copy required')
    required = ['config.mk', 'freeze.json', 'lec.py']
    if not finished_proof:
        required += ['lec_async.ready', 'lec_async.rc', 'lec/lec.json']
    report = json.loads((original / 'lec/lec.json').read_text())
    if report.get('verdict') != 'EQUIVALENT' or (original / 'lec_async.rc').read_text().strip() != '0':
        raise ValueError('original proof is not completed EQUIVALENT')
    if (original / 'lec_async.stop').exists():
        raise ValueError('original proof has a stop marker')
    # Legacy transfer needs a successful physical scope. Explicit finished-proof
    # intake instead verifies the completed async proof independently of PLACE.
    if not finished_proof:
        image = (original / 'image.txt').read_text()
        if not re.search(r'^end\s+.+\s+rc\s+0\s*$', image, re.M):
            raise ValueError('original physical completion receipt absent')
        required.append('image.txt')
    else:
        if (copied / 'lec_async.pid').exists():
            raise ValueError('fresh copy retains a proof PID; remove only owned inherited transport state')
        if not (original / 'lec_async.done').exists() or not (original / 'lec_async.ready').is_file():
            raise ValueError('original async proof has not completed its ready/done protocol')
        counts = report.get('counts', {})
        if (type(counts.get('compare_points')) is not int or counts['compare_points'] <= 0
                or counts.get('proved') != counts['compare_points']
                or counts.get('differs') != 0 or counts.get('undecided') != 0
                or report.get('kept_registers', {}).get('missing', {}).get('n') != 0):
            raise ValueError('complete comparison and KEEP proof required')
        prov = json.loads((original / 'PROVENANCE.json').read_text())
        rp, sp = report.get('provenance', {}), prov.get('provenance', {})
        if (rp.get('source') != 'validated kit PROVENANCE.json' or rp.get('dirty') is not False
                or sp.get('dirty') is not False or rp.get('commit') != sp.get('commit')
                or not re.fullmatch('[0-9a-f]{40}', sp.get('commit', ''))):
            raise ValueError('finished proof needs validated clean source identity')
        required += list(prov.get('files', {}))
        for rel, digest in prov.get('files', {}).items():
            stamped=(original/rel).resolve(); stamped.relative_to(original)
            if hashlib.sha256(stamped.read_bytes()).hexdigest() != digest:
                raise ValueError('generation proof input changed: ' + rel)
        reset = report.get('reset_contract', {})
        if reset.get('debug_overrides') != {} or type(reset.get('used')) is not int:
            raise ValueError('native reset policy absent or overridden')
        if 'OT_LEC_RESET_CYCLES' in os.environ and str(reset.get('requested')) != os.environ['OT_LEC_RESET_CYCLES']:
            raise ValueError('current reset environment differs from completed proof')
        if os.environ.get('OT_LEC_SUPERSET_VEC', '0') != '0' and (report.get('superset_vec') or {}).get('all_shown') is not True:
            raise ValueError('completed source proof lacks requested superset coverage')
        contract = reset.get('contract')
        if contract:
            staged = json.loads((original / 'reset_contract.json').read_text())
            if contract.get('file') != '/work/reset_contract.json' or contract.get('edges') != staged.get('edges') or contract.get('die') != staged.get('die') or reset['used'] != staged.get('edges'):
                raise ValueError('completed native reset contract differs')
            receipt = contract.get('receipt', '')
            if not receipt.startswith('/work/'):
                raise ValueError('reset receipt must be kit local')
            rp=staged.get('proof', {})
            receipt_file=(original/receipt[6:]).resolve();receipt_file.relative_to(original)
            if (staged.get('schema') != 'opentallas.reset_contract.v1'
                    or report.get('top') not in staged.get('modules', [])
                    or rp.get('verdict') != 'PASS' or rp.get('mutant') != 'CAUGHT'
                    or rp.get('assert_edges') != contract.get('assert_edges')
                    or rp.get('receipt') != receipt[6:]
                    or hashlib.sha256(receipt_file.read_bytes()).hexdigest() != rp.get('receipt_sha256')):
                raise ValueError('native die reset contract/receipt proof differs')
            required.append(receipt[6:])
        elif (original / 'reset_contract.json').exists() or (copied / 'reset_contract.json').exists():
            raise ValueError('unexpected die reset receipt')
        for n in ('lec_options.json', 'lec_hints.json', 'reset_contract.json'):
            if (original / n).exists() != (copied / n).exists():
                raise ValueError('proof policy input presence differs: ' + n)
        original_rtl = {str(p.relative_to(original)) for p in (original/'rtl').rglob('*') if p.is_file()}
        copied_rtl = {str(p.relative_to(copied)) for p in (copied/'rtl').rglob('*') if p.is_file()}
        if original_rtl != copied_rtl:
            raise ValueError('RTL inventory differs')
        ready_args=shlex.split('\n'.join((original/'lec_async.ready').read_text().splitlines()[1:]))
        if ready_args[:4] != ['python3','-I','/work/lec.py','/work'] or '--netlist' not in ready_args or '--out' not in ready_args:
            raise ValueError('unrecognized actual official async invocation')
        if ready_args[ready_args.index('--netlist')+1] != report.get('netlist') or ready_args[ready_args.index('--out')+1] != '/work/lec':
            raise ValueError('actual async invocation differs from report')
        if '--hints' in ready_args:
            hint=ready_args[ready_args.index('--hints')+1]
            if not hint.startswith('/work/'):
                raise ValueError('async hints must be kit local')
            required.append(hint[6:])
            if hashlib.sha256((original/hint[6:]).read_bytes()).hexdigest() != (report.get('hints') or {}).get('sha256'):
                raise ValueError('actual async hint input differs from report')
    freeze = json.loads((original / 'freeze.json').read_text())
    if not isinstance(freeze, dict) or not freeze.get('schema'):
        raise ValueError('original freeze absent or invalid')
    net = report.get('netlist', '')
    if not net.startswith('/work/'):
        raise ValueError('proof netlist must be kit-local')
    required.append(net[6:])
    required += [str(p.relative_to(original)) for p in (original / 'rtl').rglob('*') if p.is_file()]
    required += [n for n in ('lec_options.json','lec_hints.json','reset_contract.json','PROVENANCE.json') if (original/n).is_file()]
    cfg = (original/'config.mk').read_text()
    for line in cfg.splitlines():
        if re.match(r'^(?:override )?export (?:VERILOG_FILES|ADDITIONAL_LIBS)\s*=',line):
            for value in shlex.split(line.split('=',1)[1]):
                if '$' in value:
                    continue
                if not value.startswith('/work/'):
                    raise ValueError('external proof input needs explicit closure: '+value)
                required.append(value[6:])
    rows = {}
    proof_end = (original/'lec/lec.json').stat().st_mtime
    for rel in sorted(set(required)):
        a,b=original/rel,copied/rel
        a.resolve().relative_to(original)
        b.resolve().relative_to(copied)
        if not a.is_file() or not b.is_file():
            raise ValueError('missing retained proof input: '+rel)
        old=a.read_bytes(); new=b.read_bytes()
        if old != new:
            raise ValueError('continuation input differs: '+rel)
        if rel not in ('image.txt','lec_async.rc') and a.stat().st_mtime > proof_end + .001:
            raise ValueError('retained input newer than completed proof: '+rel)
        rows[rel] = hashlib.sha256(old).hexdigest()
    descriptor = dict(schema='opentallas.lec_completed_transfer.v1',original=str(original),copied=str(copied),
        historical_provenance=report.get('provenance'),historical_identity_available=False,
        limitation='Hashes are measured at transfer time, not at historical proof time. Physical continuation only; no source qualification or replacement for actual post-route EQ.',
        current_files_sha256=rows,counts=report.get('counts'),source_qualified=False)
    if finished_proof:
        descriptor.update(kind='completed_async_proof_independent_of_physical_result',
                          physical_success_claimed=False, historical_async_lease=False,
                          ready_sha256=hashlib.sha256((original/'lec_async.ready').read_bytes()).hexdigest(),
                          report_sha256=hashlib.sha256((original/'lec/lec.json').read_bytes()).hexdigest())
    out=copied/'lec_async.transfer.json'
    if out.exists():
        if json.loads(out.read_text()) != descriptor:
            raise ValueError('different completed-proof transfer already recorded')
        if finished_proof and hashlib.sha256((copied/'lec/lec.json').read_bytes()).hexdigest() != descriptor['report_sha256']:
            raise ValueError('imported finished proof report changed')
    else:
        if finished_proof:
            backup = copied/'lec_before_finished_import'
            if backup.exists():
                raise ValueError('prior interrupted import retained')
            if (copied/'lec').exists():
                (copied/'lec').rename(backup)
            (copied/'lec').mkdir()
            for n in ('lec.json', 'hyp.json', 'hints.json'):
                if (original/'lec'/n).is_file():
                    shutil.copy2(original/'lec'/n, copied/'lec'/n)
            history = copied/'lec_before_finished_import_markers'
            history.mkdir(exist_ok=True)
            for n in ('ready','rc','stop','abort','done','on','identity','source_identity','owner'):
                f=copied/('lec_async.'+n)
                if f.exists(): f.rename(history/f.name)
            shutil.copy2(original/'lec_async.ready', copied/'lec_async.ready')
            shutil.copy2(original/'lec_async.rc', copied/'lec_async.rc')
        out.write_text(json.dumps(descriptor,indent=1)+'\n')
    return descriptor


if __name__ == '__main__':
    import sys
    args=sys.argv[1:]
    finished='--finished-proof' in args
    if finished: args.remove('--finished-proof')
    print(json.dumps(transfer(*args, finished_proof=finished)))
