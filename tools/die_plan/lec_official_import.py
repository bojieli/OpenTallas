"""Attach a completed separate-output official proof to a fresh continuation.

This is explicit current-byte cache intake, not a historical async lease or
source qualification. The original kit, failed proof and successful output are
read-only. A routed proof remains required after physical implementation.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import tempfile


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def local(root, rel):
    p = (root / rel).resolve()
    p.relative_to(root)
    if not p.is_file():
        raise ValueError('missing input: ' + str(p))
    return p


def prepare(original, proof, copied, producer_log, producer_unit, checker_sha256, reset_cycles):
    original, proof, copied = [Path(x).resolve() for x in (original, proof, copied)]
    if original == copied or proof == copied / 'lec':
        raise ValueError('fresh continuation and separate proof required')
    if (copied / 'lec_async.pid').exists():
        raise ValueError('destination has an inherited or active proof PID; use a clean fresh copy')
    if not re.fullmatch(r'[A-Za-z0-9_.-]+', producer_unit):
        raise ValueError('invalid producer unit')
    log = Path(producer_log).read_text()
    if not re.search(r'\(unit ' + re.escape(producer_unit) + r'\): exit 0(?:\s|$)', log):
        raise ValueError('actual ot-run producer completion exit0 required')
    report_path = local(proof, 'lec.json')
    report = json.loads(report_path.read_text())
    counts = report.get('counts', {})
    if (report.get('schema') != 'opentallas.lec.v1' or report.get('verdict') != 'EQUIVALENT'
            or type(counts.get('compare_points')) is not int or counts['compare_points'] <= 0
            or counts.get('proved') != counts['compare_points']
            or counts.get('differs') != 0 or counts.get('undecided') != 0):
        raise ValueError('complete official EQUIVALENT counts required')
    if report.get('kept_registers', {}).get('missing', {}).get('n') != 0:
        raise ValueError('missing KEEP evidence')
    reset = report.get('reset_contract', {})
    if reset.get('used') != reset_cycles or reset.get('requested') != reset_cycles or reset.get('debug_overrides') != {}:
        raise ValueError('reset policy or debug override differs')
    if reset.get('contract') is not None:
        raise ValueError('die-reset receipt intake needs its own explicit closure; component proof only')
    if os.environ.get('OT_LEC_RESET_CYCLES', str(reset_cycles)) != str(reset_cycles):
        raise ValueError('current reset environment differs')
    if os.environ.get('OT_LEC_SUPERSET_VEC', '0') != '0':
        raise ValueError('source proof does not supply a postroute superset receipt')
    if any((original / n).exists() for n in ('reset_contract.json',)):
        raise ValueError('component proof cannot replace die reset receipt')
    provenance = json.loads(local(original, 'PROVENANCE.json').read_text())
    source = provenance.get('provenance', {})
    rp = report.get('provenance', {})
    if (source.get('dirty') is not False or rp.get('dirty') is not False
            or rp.get('source') != 'validated kit PROVENANCE.json'
            or rp.get('commit') != source.get('commit')
            or not re.fullmatch('[0-9a-f]{40}', source.get('commit', ''))):
        raise ValueError('validated clean source provenance differs')
    if sha(local(original, 'lec.py')) != checker_sha256:
        raise ValueError('actual independently pinned checker differs')
    net = report.get('netlist', '')
    if not net.startswith('/work/'):
        raise ValueError('official netlist must be kit local')
    # Full generated kit manifest plus all RTL, actual netlist and proof options.
    # Preserve honest historical limitations: manifest hashes were stamped at
    # generation; netlist equality is measured now and must predate proof end.
    required = set(provenance.get('files', {})) | {'config.mk', 'freeze.json', 'lec.py', 'PROVENANCE.json', net[6:]}
    required.update(str(p.relative_to(original)) for p in (original / 'rtl').rglob('*') if p.is_file())
    required.update(n for n in ('lec_options.json',) if (original / n).exists())
    config = local(original, 'config.mk').read_text()
    for line in config.splitlines():
        if re.match(r'^(?:override )?export (?:VERILOG_FILES|VERILOG_INCLUDE_DIRS|ADDITIONAL_LIBS)\s*=', line):
            for value in line.split('=', 1)[1].split():
                if not value.startswith('/work/') or '$' in value:
                    raise ValueError('unclosed external or unresolved proof input: ' + value)
                p = original / value[6:]
                if p.is_dir():
                    required.update(str(f.relative_to(original)) for f in p.rglob('*') if f.is_file())
                else:
                    required.add(value[6:])
    rows = {}
    for rel in sorted(required):
        a, b = local(original, rel), local(copied, rel)
        digest = sha(a)
        if digest != sha(b):
            raise ValueError('continuation input differs: ' + rel)
        expected = provenance.get('files', {}).get(rel)
        if expected and digest != expected:
            raise ValueError('generation manifest input differs: ' + rel)
        if a.stat().st_mtime > report_path.stat().st_mtime + .001:
            raise ValueError('original input newer than completed proof: ' + rel)
        rows[rel] = digest
    hint = local(proof, 'hints.json')
    if report.get('hints', {}).get('sha256') != sha(hint):
        raise ValueError('official hint bytes differ from report')
    if (copied / 'lec_hints.json').exists() and sha(copied / 'lec_hints.json') != sha(hint):
        raise ValueError('destination already has different hints')
    artifacts = {n: sha(local(proof, n)) for n in ('lec.json', 'hyp.json', 'hints.json')}
    descriptor = dict(schema='opentallas.lec_official_import.v1', original=str(original), proof=str(proof), copied=str(copied),
                      producer_unit=producer_unit, producer_log_sha256=sha(Path(producer_log)),
                      checker_sha256=checker_sha256, reset_cycles=reset_cycles, current_files_sha256=rows,
                      artifacts_sha256=artifacts, counts=counts, source_qualified=False,
                      historical_async_lease=False,
                      limitation='Explicit current-byte physical-continuation intake. No historical async lease, die reset qualification or postroute EQ claim.')
    dest = copied / 'lec_async.official_import.json'
    if dest.exists():
        if json.loads(dest.read_text()) != descriptor:
            raise ValueError('different official import already recorded')
        if any(sha(local(copied / 'lec', n)) != digest for n, digest in artifacts.items()):
            raise ValueError('imported official proof artifact changed')
        if (copied / 'lec_async.rc').read_text().strip() != '0':
            raise ValueError('imported proof completion marker changed')
        return descriptor
    # Validate everything before the first mutation; original/output never change.
    backup = copied / 'lec_before_official_import'
    if backup.exists():
        raise ValueError('previous interrupted import retained; inspect before retry')
    stage = Path(tempfile.mkdtemp(prefix='.official-import-', dir=copied))
    try:
        for name in artifacts:
            shutil.copy2(proof / name, stage / name)
        if (copied / 'lec').exists():
            (copied / 'lec').rename(backup)
        stage.rename(copied / 'lec')
        shutil.copy2(hint, copied / 'lec_hints.json')
        for name in ('on', 'ready', 'rc', 'stop', 'abort', 'done', 'identity', 'source_identity', 'owner'):
            p = copied / ('lec_async.' + name)
            if p.exists():
                history = copied / 'lec_before_official_import_markers'
                history.mkdir(exist_ok=True)
                p.rename(history / p.name)
        (copied / 'lec_async.ready').write_text('nz\npython3 -I /work/lec.py /work --out /work/lec --hints /work/lec_hints.json\n')
        (copied / 'lec_async.rc').write_text('0\n')
        (copied / 'lec_async.owner').write_text('official-import-' + producer_unit + '\n')
        dest.write_text(json.dumps(descriptor, indent=1) + '\n')
    finally:
        if stage.exists():
            shutil.rmtree(stage)
    return descriptor


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('original', 'proof', 'copied', 'producer-log', 'producer-unit', 'checker-sha256'):
        p.add_argument('--' + name, required=True)
    p.add_argument('--reset-cycles', type=int, required=True)
    a = p.parse_args()
    print(json.dumps(prepare(**vars(a))))
