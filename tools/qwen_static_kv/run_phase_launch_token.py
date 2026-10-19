#!/usr/bin/env python3
"""KVJ-E2 2026-10-17: bench of the compiled token-run phase launches through the actual qkd_static_kv_phase_launch.

    run_phase_launch_token.py --report DIE_OUT/report.json --out DIR [--ntok 3]

Runs tb_static_phase_launch_token (iverilog) on the launch table of kv_static_programme.py (phase.launch_table; ctrl_go
and kgo of a stage share one edge, so they form one 2-lane launch):
  production   compiled roots, token period = report phase.token_period_core (a multiple of 768)  -> must PASS
  unpadded     compiled roots, the unpadded token period (249431)                                  -> must FAIL (fault)
  unaligned    roots without the per-stage phase advance, padded period                             -> must FAIL (fault)
Writes DIR/receipt.json.  Component scope: declared clock origin (q = PH0 at the first rn-active edge), no physical
phase qualification."""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCES = ['rtl/qwen_sys/static_kv_20261014/qkd_static_kv_phase_launch.sv',
           'rtl/test/qwen_static_kv/tb_static_phase_launch_token.sv']
LANE = dict(ctrl_go=1, kgo=2, vgo=4)


def table(rep, aligned=True):
    ph = rep['phase']
    groups = rep['profile']['groups']
    al = ph['alignment']
    by = {}
    for l in ph['launch_table']:
        c = l['token_cycle']
        if not aligned:
            c += al['stage_advance'][l['stage'] - 1] + (al['vgo_advance'] if l['root'] == 'vgo' else 0)
        toggle = c + 1 + groups + 1 + 1          # kv_static_programme.launch_gap: capture c' = c + 1 + groups + 1, toggle c' + 1
        e = by.setdefault(toggle, dict(mask=0, layer=l['stage'] - 1))
        if e['layer'] != l['stage'] - 1:
            raise SystemExit('two stages launch on one edge')
        e['mask'] |= LANE[l['root']]
    return [(t, e['mask'], e['layer']) for t, e in sorted(by.items())]


def run(out, name, rows, period, ntok):
    lf = out / f'{name}.hex'
    lf.write_text(''.join(f'{(t << 12) | (m << 8) | ly:08x}\n' for t, m, ly in rows))
    vvp = out / f'{name}.vvp'
    b = subprocess.run(['iverilog', '-g2012', '-s', 'tb_static_phase_launch_token', f'-Ptb_static_phase_launch_token.PERIOD={period}',
                        f'-Ptb_static_phase_launch_token.NTOK={ntok}', f'-Ptb_static_phase_launch_token.NL={len(rows)}',
                        '-o', str(vvp)] + [str(ROOT / s) for s in SOURCES], capture_output=True, text=True)
    if b.returncode:
        raise SystemExit(b.stderr)
    p = subprocess.run(['vvp', '-n', str(vvp), f'+LAUNCH={lf}'], capture_output=True, text=True)
    txt = p.stdout + p.stderr
    (out / f'{name}.log').write_text(txt)
    line = next((x for x in txt.splitlines() if 'PHTOK' in x), 'NO_RESULT')
    return dict(case=name, period=period, ntok=ntok, launches_per_token=len(rows), exit=p.returncode, result=line.strip())


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--report', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--ntok', type=int, default=3)
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    rep = json.loads(a.report.read_text())
    ph = rep['phase']
    period, unpadded = ph['token_period_core'], rep['link'].get('token_period_unpadded', 249431)
    runs = [run(a.out, 'production', table(rep), period, a.ntok),
            run(a.out, 'unpadded', table(rep), unpadded, a.ntok),
            run(a.out, 'unaligned', table(rep, aligned=False), period, a.ntok)]
    want = dict(production='PHTOK PASS', unpadded='PHTOK FAIL', unaligned='PHTOK FAIL')
    ok = all(want[r['case']] in r['result'] and (r['exit'] == 0) == (r['case'] == 'production') for r in runs)
    rec = dict(schema='opentallas.qwen_kv_static.phase_launch_token_bench.v1', verdict='PASS' if ok else 'FAIL',
               expect=want, runs=runs, report_sha256=hashlib.sha256(a.report.read_bytes()).hexdigest(),
               source_sha256={s: hashlib.sha256((ROOT / s).read_bytes()).hexdigest() for s in SOURCES},
               scope='actual qkd_static_kv_phase_launch, compiled launch table of all 36 stages x 3 roots, NTOK token runs; '
                     'declared component clock origin; no physical phase qualification')
    (a.out / 'receipt.json').write_text(json.dumps(rec, indent=1) + '\n')
    print(rec['verdict'], *[f"{r['case']}: {r['result']}" for r in runs], sep='\n')
    return 0 if ok else 1


if __name__ == '__main__':
    raise SystemExit(main())
