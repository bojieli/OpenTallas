#!/usr/bin/env python3
"""Re-fold fetched STG evidence locally; a remote legacy PASS is not a gate."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys


def unavailable(stage, label, reason):
    stage = Path(stage)
    stage.mkdir(parents=True, exist_ok=True)
    result = stage / 'result.json'
    if result.exists():
        raw = result.read_bytes()
        (stage / f'original_result.{hashlib.sha256(raw).hexdigest()}.json').write_bytes(raw)
    result.write_text(json.dumps(dict(stage=label, verdict='INCOMPLETE',
        grade='DIAG (required collection evidence unavailable)', failures=[reason],
        source_identity_qualified=False, delivery_timing_qualified=False), indent=1) + '\n')


def verify_build_receipt(stage, asm, repo, rtl_ref='a4cf9a360'):
    """STEWARD-TOKb-QW 10-21: the separate build receipt, verified here from the fetched files (stage_stg.sh
    --object-manifest snapshot/bind/verify).  Per config rel/pos/mut: the identity log says SNAPSHOT OK and BIND or VERIFY OK
    (never REFUSED); build_identity.json source == <cfg>.build_source.json; its binary_sha256 == <cfg>/vtb.sha256 (the
    binary the runs used); flags == vflags.txt; every RTL input (not rtl/test/) hashes equal to the assembly commit's file,
    or to rtl_ref's file (a merged main fix applied as overlay, listed); bench inputs (rtl/test/) are listed with their
    hashes.  -> (ok, record)"""
    rec, fails, cache = dict(asm=asm, rtl_ref=rtl_ref), [], {}

    def git_sha(rev, path):
        if (rev, path) not in cache:
            r = subprocess.run(['git', '-C', repo, 'show', f'{rev}:{path}'], capture_output=True)
            cache[(rev, path)] = hashlib.sha256(r.stdout).hexdigest() if r.returncode == 0 else None
        return cache[(rev, path)]
    ref = subprocess.run(['git', '-C', repo, 'rev-parse', '--short=9', rtl_ref], capture_output=True, text=True)
    rec['rtl_ref_commit'] = ref.stdout.strip()
    for cfg in ('rel', 'pos', 'mut'):
        try:
            log = (stage / f'{cfg}.identity.log').read_text()
            src = json.loads((stage / f'{cfg}.build_source.json').read_text())
            ident = json.loads((stage / cfg / 'build/obj_n12/build_identity.json').read_text())
            vtb = (stage / cfg / 'vtb.sha256').read_text().split()[0]
            vflags = (stage / cfg / 'vflags.txt').read_text().split()
        except (OSError, ValueError, IndexError) as error:
            fails.append(f'{cfg}: receipt unavailable ({error})')
            continue
        if 'REFUSED' in log or 'SNAPSHOT OK' not in log or not ('BIND OK' in log or 'VERIFY OK' in log):
            fails.append(f'{cfg}: identity log not SNAPSHOT + BIND/VERIFY OK')
        if ident.get('source') != src:
            fails.append(f'{cfg}: build_identity source != build_source.json')
        if ident.get('binary_sha256') != vtb:
            fails.append(f'{cfg}: build_identity binary != the run binary (vtb.sha256)')
        if not src.get('inputs') or not all(isinstance(h, str) and len(h) == 64 for h in src.get('inputs', {}).values()):
            fails.append(f'{cfg}: missing or malformed source input hashes')
        if src.get('flags') != vflags:
            fails.append(f'{cfg}: build flags {src.get("flags")} != vflags.txt {vflags}')
        overlay, bench = {}, {}
        for path, h in sorted(src.get('inputs', {}).items()):
            if git_sha(asm, path) == h:
                continue
            if path.startswith('rtl/test/'):
                bench[path] = h
            elif git_sha(rtl_ref, path) == h:
                overlay[path] = h
            else:
                fails.append(f'{cfg}: RTL input {path} matches neither {asm} nor {rtl_ref}')
        rec[cfg] = dict(binary_sha256=vtb, flags=src.get('flags'), inputs=len(src.get('inputs', {})),
                        rtl_overlay_from_rtl_ref=overlay, bench_inputs_not_on_asm=bench)
    rec['fails'] = fails
    return not fails, rec


def normalize(stage, asm=None, repo=None):
    stage = Path(stage).resolve()
    raw = (stage / 'result.json').read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    original = stage / f'original_result.{digest}.json'
    if original.exists():
        assert original.read_bytes() == raw
    else:
        original.write_bytes(raw)
    missing = []
    try:
        legacy = json.loads(raw)
        required = {'runlist.txt'}
        required.update(f'fx/L{layer}_fixture.json' for layer in range(36))
        for cfg, record in legacy.get('configs', {}).items():
            required.update(f'{cfg}/runs/{name}/bench.out' for name in record.get('stages', {}))
        for cfg in ('rel', 'pos', 'mut'):
            required.update(f'{cfg}/{name}' for name in (
                'vtb.sha256', 'vflags.txt', 'build/slice_calibrate.out',
                'build/calibrate.out', 'cal_mat/calibrate.out'))
        missing = sorted(name for name in required if not (stage / name).is_file())
        run = subprocess.run([sys.executable, str(Path(__file__).with_name('stage_stg.collect.py')),
                              str(stage.parent), stage.name], capture_output=True, text=True)
        (stage / 'normalization.log').write_text(run.stdout + run.stderr)
        if run.returncode not in (0, 1) or not run.stdout.startswith('STG '):
            raise ValueError('local collector could not fold fetched evidence: ' + run.stderr[-500:])
        result = json.loads((stage / 'result.json').read_text())
        if not all(key in result for key in ('numeric_case_summary', 'unknown_delivery_cases',
                                             'calibration_gate', 'delivery_timing_qualified')):
            raise ValueError('local collector lacks required calibration/delivery normalization schema')
        result['src_commit'] = legacy.get('src_commit')
    except (ValueError, OSError, KeyError, AttributeError, TypeError) as error:
        result = dict(stage=stage.name, verdict='INCOMPLETE', failures=[str(error)],
                      delivery_timing_qualified=False)
        missing.append('complete parsable local evidence')
    if missing:
        result['verdict'] = 'INCOMPLETE'
        result['delivery_timing_qualified'] = False
    # Executable/source binding: verified from the fetched build receipt when --asm/--repo are given (else DIAG).
    bound, receipt = verify_build_receipt(stage, asm, repo) if asm and repo else (False, None)
    if bound:
        ov = sorted({p for c in ('rel', 'pos', 'mut') for p in receipt[c]['rtl_overlay_from_rtl_ref']})
        result['grade'] = ('RTL-functional (source assembly)' + (f' + {receipt["rtl_ref"]} {receipt["rtl_ref_commit"]} RTL '
                           f'overlay {",".join(ov)}' if ov else '') + '; build receipt verified')
    else:
        result['grade'] = 'DIAG (local evidence fold; binary/source binding requires its separate build receipt)'
    result['source_identity_qualified'] = bound
    result['build_receipt'] = receipt
    result['collection_normalization'] = dict(
        raw_result=original.name, raw_result_sha256=digest,
        missing_evidence=missing, remote_result_unchanged=True,
        corrected_calibration_substituted=False)
    (stage / 'result.json').write_text(json.dumps(result, indent=1) + '\n')
    print(json.dumps(dict(verdict=result['verdict'],
                          numeric_case_summary=result.get('numeric_case_summary'),
                          unknown_delivery_cases=len(result.get('unknown_delivery_cases', [])),
                          missing_evidence=missing)))


if __name__ == '__main__':
    if sys.argv[1] == '--unavailable':
        unavailable(*sys.argv[2:5])
    else:
        normalize(*sys.argv[1:4])
