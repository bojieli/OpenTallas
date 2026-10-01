#!/usr/bin/env python3
"""Reconcile retained W18b failures with an exactly-once parallel hash check.

The old records and bench remain immutable. Reuse transaction evidence only
when every recorded source digest matches. This establishes functional
steering, not SS/FF closure, model benefit, or adoption.
"""
import argparse
import hashlib
import importlib.util
import json
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BENCH = 'rtl/test/tb_chip_v41x_karb_local_hash_parallel.sv'

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output', type=Path, required=True)
    ap.add_argument('--baseline', type=Path, action='append', required=True)
    ap.add_argument('--exhaustive-log', type=Path)
    a = ap.parse_args()
    spec = importlib.util.spec_from_file_location('gate', ROOT / 'tools/rtl_chip_v41x_karb_local.py')
    g = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(g)
    bases = []
    for p in a.baseline:
        d = json.loads(p.read_text())
        stale = [s for s, h in d['sources'].items() if sha(ROOT / s) != h]
        bases.append(dict(path=str(p), sha256=sha(p), original_pass=d['pass'],
                          stale_sources=stale, transaction_cases=len(d['runs']),
                          kv_cases=len(d['kv_prefetch_bench']),
                          reusable=not stale and len(d['runs']) == 54 and
                          len(d['kv_prefetch_bench']) == 5 and
                          all(r['pass'] for r in d['runs'] + d['kv_prefetch_bench']),
                          original_hash=d['hash_steering_exhaustive']))
    text = (ROOT / BENCH).read_text()
    variants = {
        'exhaustive': text,
        'small_control': text.replace('N = 1 << 17', 'N = 128'),
        'wrong_tag': text.replace('N = 1 << 17', 'N = 128').replace('sent_tag = i[15:0]', "sent_tag = i[15:0] ^ 16'h1"),
        'duplicate': text.replace('N = 1 << 17', 'N = 128').replace('seen[i] = 0', 'seen[i] = 1'),
        'missing_pc0': text.replace('N = 1 << 17', 'N = 128').replace('if (hp_v[p]) begin', 'if (hp_v[p] && p != 0) begin'),
    }
    runs = {}
    with tempfile.TemporaryDirectory(prefix='w18_hash_') as t:
        for name, source in variants.items():
            if name == 'exhaustive' and a.exhaustive_log:
                out = a.exhaustive_log.read_text()
                runs[name] = dict(stdout=out, pass_=('PASS' in out.splitlines() and 'KARB_HASH n=131072 got=131072 pipe_got=131072 bad=0 multi=0 ingress_stalls=0' in out.splitlines()), expected_pass=True, log_sha256=sha(a.exhaustive_log), reused_focused_run=str(a.exhaustive_log))
                continue
            tb = Path(t) / (name + '.sv'); tb.write_text(source)
            exe = Path(t) / (name + '.vvp')
            c = subprocess.run(['iverilog', '-g2012', '-s', 'tb_chip_v41x_karb_local_hash_parallel', '-o', str(exe),
                                str(tb), *[str(ROOT / s) for s in g.KARB_RTL]], capture_output=True, text=True)
            c.check_returncode()
            r = subprocess.run(['vvp', '-n', str(exe)], capture_output=True, text=True)
            passed = r.returncode == 0 and 'PASS' in r.stdout.splitlines()
            runs[name] = dict(stdout=r.stdout, stderr=r.stderr, returncode=r.returncode,
                              variant_sha256=hashlib.sha256(source.encode()).hexdigest(), pass_=passed,
                              expected_pass=name in ('exhaustive', 'small_control'))
            print(name, r.stdout.strip(), flush=True)
    ok = all(b['reusable'] for b in bases) and all(r['pass_'] == r['expected_pass'] for r in runs.values())
    rec = dict(schema='opentallas.w18b.parallel_hash_reconciliation.v1', baselines=bases, runs=runs,
               sources={s: sha(ROOT / s) for s in [*g.SOURCES, BENCH, 'tools/w18/hash_parallel_gate.py']},
               pass_=ok, adoption=False,
               claim='Source-identical transaction/KV evidence reused; parallel hash rerun with exactly-once coverage. Physical signoff and model gain remain separate gates.')
    a.output.parent.mkdir(parents=True, exist_ok=True)
    if a.output.exists():
        raise FileExistsError('Never overwrite an evidence record: ' + str(a.output))
    a.output.write_text(json.dumps(rec, indent=1) + '\n')
    return 0 if ok else 1

if __name__ == '__main__':
    raise SystemExit(main())
