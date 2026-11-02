"""Explicit current-byte transfer of an unchanged completed legacy proof candidate.

Historical input identity remains unknown. This is physical-continuation evidence,
not source qualification or a replacement for actual post-route EQ.
"""
import hashlib
import json
from pathlib import Path
import re
import shlex


def transfer(original, copied):
    original, copied = Path(original).resolve(), Path(copied).resolve()
    if original == copied:
        raise ValueError('fresh continuation copy required')
    required = ['config.mk', 'freeze.json', 'lec.py', 'lec_async.ready', 'lec_async.rc', 'lec/lec.json']
    report = json.loads((original / 'lec/lec.json').read_text())
    if report.get('verdict') != 'EQUIVALENT' or (original / 'lec_async.rc').read_text().strip() != '0':
        raise ValueError('original proof is not completed EQUIVALENT')
    if (original / 'lec_async.stop').exists():
        raise ValueError('original proof has a stop marker')
    # Verify a real physical scope ended, not merely that an ODB exists.
    image = (original / 'image.txt').read_text()
    if not re.search(r'^end\s+.+\s+rc\s+0\s*$', image, re.M):
        raise ValueError('original physical completion receipt absent')
    required.append('image.txt')
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
    out=copied/'lec_async.transfer.json'
    if out.exists():
        if json.loads(out.read_text()) != descriptor:
            raise ValueError('different completed-proof transfer already recorded')
    else:
        out.write_text(json.dumps(descriptor,indent=1)+'\n')
    return descriptor


if __name__ == '__main__':
    import sys
    print(json.dumps(transfer(*sys.argv[1:])))
