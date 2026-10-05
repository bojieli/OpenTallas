#!/usr/bin/env python3
"""W18 functional reconciliation; cached exhaustive results require provenance.

Retained failures are immutable. Passing transaction evidence is reusable only
with identical sources. Neither functional PASS nor timing diagnostics adopts
hardware or certifies origin/main. Fresh exhaustive runs write a record and log;
reuse requires both, matching all compiler inputs, gate sources, tools and recipe.
"""
import argparse
import hashlib
import importlib.util
import json
import platform
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BENCH = 'rtl/test/tb_chip_v41x_karb_local_hash_parallel.sv'
HARNESS = 'tools/rtl_chip_v41x_karb_local.py'
GATE = 'tools/w18/hash_parallel_gate.py'
TOP = 'tb_chip_v41x_karb_local_hash_parallel'
SCHEMA = 'opentallas.w18b.exhaustive_hash.v2'
SUMMARY = 'KARB_HASH n=131072 got=131072 pipe_got=131072 bad=0 multi=0 ingress_stalls=0'


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def write_new(p, data):
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open('x') as f:
        f.write(data)


def tool_identity(name, args):
    path = Path(shutil.which(name) or name).resolve(strict=True)
    r = subprocess.run([str(path), *args], capture_output=True, text=True, check=True)
    return dict(path=str(path), sha256=sha(path), version_stdout=r.stdout, version_stderr=r.stderr)


def context(root, rtl):
    inputs = [BENCH, *rtl]
    # These inputs are standalone. Fail closed if a future change introduces
    # include files that this complete-input manifest does not yet capture.
    for s in inputs:
        if '`include' in (root / s).read_text():
            raise ValueError('Untracked include dependency: ' + s)
    return dict(sources={s: sha(root / s) for s in dict.fromkeys([*inputs, HARNESS, GATE])},
                compiler_inputs=inputs,
                recipe=dict(compiler_args=['-g2012', '-s', TOP, '-o', '{exe}', *inputs],
                            simulator_args=['-n', '{exe}']),
                tools=dict(compiler=tool_identity('iverilog', ['-V']),
                           simulator=tool_identity('vvp', ['-V']),
                           python=dict(version=platform.python_version(), sha256=sha(Path(sys.executable).resolve()))))


def validate_cached(record_path, log_path, expected):
    record = json.loads(record_path.read_text())
    if record.get('schema') != SCHEMA:
        raise ValueError('Missing or unsupported exhaustive provenance schema')
    for field in ('sources', 'compiler_inputs', 'recipe', 'tools'):
        if record.get(field) != expected[field]:
            raise ValueError('Exhaustive provenance mismatch: ' + field)
    if record.get('log_sha256') != sha(log_path):
        raise ValueError('Exhaustive log digest mismatch')
    if record.get('compile_returncode') != 0 or record.get('simulation_returncode') != 0:
        raise ValueError('Cached exhaustive execution did not succeed')
    if record.get('sources_unchanged') is not True:
        raise ValueError('Cached exhaustive source stability not established')
    lines = log_path.read_text().splitlines()
    if lines != [SUMMARY, 'PASS']:
        raise ValueError('Exhaustive output is not the expected complete PASS')
    return record


def simulate(root, rtl, source, work, name):
    tb = work / (name + '.sv'); tb.write_text(source)
    exe = work / (name + '.vvp')
    c = subprocess.run(['iverilog', '-g2012', '-s', TOP, '-o', str(exe), str(tb),
                        *[str(root / s) for s in rtl]], capture_output=True, text=True)
    if c.returncode:
        raise RuntimeError('Compilation failed: ' + c.stderr)
    r = subprocess.run(['vvp', '-n', str(exe)], capture_output=True, text=True)
    return dict(stdout=r.stdout, stderr=r.stderr, returncode=r.returncode,
                compile_returncode=c.returncode, compile_stdout=c.stdout, compile_stderr=c.stderr,
                executable_sha256=sha(exe), variant_sha256=hashlib.sha256(source.encode()).hexdigest(),
                pass_=r.returncode == 0 and 'PASS' in r.stdout.splitlines())


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output', type=Path, required=True)
    ap.add_argument('--baseline', type=Path, action='append', required=True)
    ap.add_argument('--exhaustive-log', type=Path, help='Reuse only with --exhaustive-record')
    ap.add_argument('--exhaustive-record', type=Path, help='Record to reuse alongside log, or fresh record destination')
    a = ap.parse_args()
    if a.exhaustive_log and not a.exhaustive_record:
        ap.error('--exhaustive-log requires a source-pinned --exhaustive-record')
    fresh_record = a.exhaustive_record or a.output.with_suffix('.exhaustive.json')
    fresh_log = fresh_record.with_suffix('.log')
    targets = [a.output] if a.exhaustive_log else [a.output, fresh_record, fresh_log]
    if len(set(p.resolve() for p in targets)) != len(targets):
        ap.error('Evidence destinations must be distinct')
    for p in targets:
        if p.exists():
            ap.error('Never overwrite evidence: ' + str(p))
    spec = importlib.util.spec_from_file_location('gate', ROOT / HARNESS)
    g = importlib.util.module_from_spec(spec); spec.loader.exec_module(g)
    expected = context(ROOT, g.KARB_RTL)
    # Reject unpinned/stale cache before any RTL compilation or simulation.
    cached = validate_cached(a.exhaustive_record, a.exhaustive_log, expected) if a.exhaustive_log else None
    bases = []
    for p in a.baseline:
        d = json.loads(p.read_text())
        stale = [s for s, h in d['sources'].items() if sha(ROOT / s) != h]
        bases.append(dict(path=str(p), sha256=sha(p), original_pass=d['pass'], stale_sources=stale,
                          transaction_cases=len(d['runs']), kv_cases=len(d['kv_prefetch_bench']),
                          reusable=not stale and len(d['runs']) == 54 and len(d['kv_prefetch_bench']) == 5 and
                          all(r['pass'] for r in d['runs'] + d['kv_prefetch_bench']),
                          original_hash=d['hash_steering_exhaustive']))
    text = (ROOT / BENCH).read_text()
    small = text.replace('N = 1 << 17', 'N = 128')
    variants = dict(exhaustive=text, small_control=small,
                    wrong_tag=small.replace('sent_tag = i[15:0]', "sent_tag = i[15:0] ^ 16'h1"),
                    duplicate=small.replace('seen[i] = 0', 'seen[i] = 1'),
                    missing_pc0=small.replace('if (hp_v[p]) begin', 'if (hp_v[p] && p != 0) begin'))
    runs = {}
    with tempfile.TemporaryDirectory(prefix='w18_hash_v2_') as t:
        for name, source in variants.items():
            if name == 'exhaustive' and cached:
                r = dict(stdout=a.exhaustive_log.read_text(), pass_=True,
                         record_path=str(a.exhaustive_record), record_sha256=sha(a.exhaustive_record),
                         log_sha256=sha(a.exhaustive_log), reused=True)
            else:
                r = simulate(ROOT, g.KARB_RTL, source, Path(t), name)
                if name == 'exhaustive':
                    after = context(ROOT, g.KARB_RTL)
                    proof = dict(schema=SCHEMA, **expected, sources_unchanged=after == expected,
                                 source_root=str(ROOT), source_commit=subprocess.check_output(
                                     ['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], text=True).strip(),
                                 compile_returncode=r['compile_returncode'], simulation_returncode=r['returncode'],
                                 executable_sha256=r['executable_sha256'],
                                 compile_stdout=r['compile_stdout'], compile_stderr=r['compile_stderr'],
                                 simulation_stderr=r['stderr'],
                                 log_sha256=hashlib.sha256(r['stdout'].encode()).hexdigest())
                    write_new(fresh_log, r['stdout'])
                    write_new(fresh_record, json.dumps(proof, indent=1) + '\n')
                    validate_cached(fresh_record, fresh_log, expected)
                    r.update(record_path=str(fresh_record), record_sha256=sha(fresh_record),
                             log_sha256=sha(fresh_log), reused=False)
            r['expected_pass'] = name in ('exhaustive', 'small_control')
            runs[name] = r
            print(name, r['stdout'].strip(), flush=True)
    stable = context(ROOT, g.KARB_RTL) == expected
    ok = stable and all(b['reusable'] for b in bases) and all(r['pass_'] == r['expected_pass'] for r in runs.values())
    rec = dict(schema='opentallas.w18b.parallel_hash_reconciliation.v2', baselines=bases, runs=runs,
               sources={s: sha(ROOT / s) for s in dict.fromkeys([*g.SOURCES, BENCH, GATE])},
               context=expected, sources_unchanged=stable, pass_=ok, adoption=False,
               claim='W18 stream-source functional reconciliation only; not a current origin/main gate. Physical signoff and model gain remain separate gates.')
    write_new(a.output, json.dumps(rec, indent=1) + '\n')
    return 0 if ok else 1

if __name__ == '__main__':
    raise SystemExit(main())
