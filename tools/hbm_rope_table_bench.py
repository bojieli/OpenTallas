#!/usr/bin/env python3
"""hbm-system 2026-10-08 (T3 gap 6): bench of the RoPE cos/sin producer ot_hbm_rope_table (HBM-resident golden table,
one-step-ahead prefetch) against the timed HBM3E stack (rtl/test/hbm_accel/tb_hbm_rope_table.sv, Verilator).
Golden: tools/hdc_golden_v41.py rope_freqs / rope_cs with the released config (rope_head_dim 64, plain theta 1e4,
YaRN theta 1.6e5, factor 16, original 65,536, beta 32 / 1).  Checks every step's three entries bit for bit; stall
cycles (the step waited on the table) must be 0 at a realistic cadence; a back-to-back cadence measures the fetch
latency.  Negative: MUT=1 (YaRN read from the plain set) must FAIL.

    python3 tools/hbm_rope_table_bench.py --work DIR --out RECORD.json
"""
import argparse, hashlib, json, os, random, re, subprocess, sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import hdc_golden_v41 as G  # noqa: E402
VERILATOR = os.environ.get('VERILATOR', str(Path.home() / '.local/opentallas-tools/verilator-5.050/bin/verilator'))
SRC = ['rtl/hbm_accel/control/ot_hbm_rope_table.sv', 'rtl/hdc/v41x/ot_hdc_v41x_idx_hbm.sv', 'rtl/test/hbm_accel/tb_hbm_rope_table.sv']
C = json.loads((ROOT / 'compiler/models/deepseek-v4.1-flash/inference_config.json').read_text())
RD = C['rope_head_dim']
FP = G.rope_freqs(RD, 0, C['rope_theta'], C['rope_factor'], C['beta_fast'], C['beta_slow'])
FY = G.rope_freqs(RD, C['original_seq_len'], C['compress_rope_theta'], C['rope_factor'], C['beta_fast'], C['beta_slow'])
T1 = 1 << 21


def entry(freqs, pos):
    c, s = G.rope_cs(freqs, pos)
    return [int(np.float32(x).view(np.uint32)) for x in c], [int(np.float32(x).view(np.uint32)) for x in s]


def sectors(freqs, pos):
    c, s = entry(freqs, pos)
    out = []
    for q in range(8):
        v = 0
        for k in range(4):
            v |= c[4 * q + k] << (64 * k) | s[4 * q + k] << (64 * k + 32)
        out.append(v)
    return out


def pack(words):
    v = 0
    for k, w in enumerate(words):
        v |= w << (32 * k)
    return v


def scenario(d, start, n, gaps):
    d.mkdir(parents=True, exist_ok=True)
    tab = {}
    for p in range(max(start - 1, 0), start + n + 2):
        for i, v in enumerate(sectors(FP, p)):
            tab[8 * p + i] = v
        for i, v in enumerate(sectors(FY, p)):
            tab[T1 + 8 * p + i] = v
    (d / 'table.txt').write_text(''.join(f'{a} {v:064x}\n' for a, v in sorted(tab.items())))
    (d / 'steps.txt').write_text(f'{start} {n}\n' + ''.join(f'{g}\n' for g in gaps))


def check(d, start, n):
    txt = (d / 'out.txt').read_text()
    bad = 0
    rows = re.findall(r'^C (\d+) (\S+) (\S+) (\S+) (\S+) (\S+) (\S+)$', txt, re.M)
    for k, r in enumerate(rows):
        p = int(r[0])
        if p != start + k:
            bad += 1; continue
        cp, sp = entry(FP, p); cy, sy = entry(FY, p); cy1, sy1 = entry(FY, p - 1)
        want = [pack(cp), pack(sp), pack(cy), pack(sy), pack(cy1), pack(sy1)]
        bad += sum(int(r[1 + i], 16) != want[i] for i in range(6))
    st = re.search(r'^S (\d+)', txt, re.M)
    return dict(steps=len(rows), mismatches=bad + (n - len(rows)), stall_cycles=int(st[1]) if st else None)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--work', type=Path, required=True); ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args(); a.work.mkdir(parents=True, exist_ok=True)
    exes = {}
    for mut in (0, 1):
        o = a.work / f'obj{mut}'
        subprocess.run([VERILATOR, '--binary', '--timing', '-Wno-fatal', '-Wno-WIDTH', '-j', '8', '-O2', '--top-module',
                        'tb_hbm_rope_table', f'-GMUT={mut}', '--Mdir', str(o)] + [str(ROOT / s) for s in SRC], check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
        exes[mut] = o / 'Vtb_hbm_rope_table'
    rng = random.Random(20261008)
    runs = []
    for name, start, n, gaps, mut in (
            ('cadence_400', rng.randrange(1, 1 << 18 - 1) , 40, [400] * 40, 0),
            ('cadence_400_hi', (1 << 18) - 60, 40, [400] * 40, 0),
            ('pos0_edge', 1, 20, [300] * 20, 0),
            ('back_to_back', rng.randrange(1, 1 << 17), 30, [0] * 30, 0),
            ('neg_mut1', 5000, 10, [400] * 10, 1)):
        d = a.work / name
        scenario(d, start, n, gaps)
        subprocess.run([str(exes[mut])], cwd=d, capture_output=True, timeout=1800)
        r = check(d, start, n); r.update(case=name, start=start, cadence_cycles=gaps[0], mut=mut)
        r['verdict'] = 'PASS' if r['mismatches'] == 0 else 'FAIL'
        runs.append(r)
    pos = [r for r in runs if not r['mut']]; neg = [r for r in runs if r['mut']]
    ok = all(r['verdict'] == 'PASS' for r in pos) and all(r['verdict'] == 'FAIL' for r in neg) and \
        all(r['stall_cycles'] == 0 for r in pos if r['cadence_cycles'] >= 300)
    rec = dict(schema='opentallas.hbm_system.rope_table.v1',
               input_sha256={s: hashlib.sha256((ROOT / s).read_bytes()).hexdigest() for s in SRC + ['tools/hbm_rope_table_bench.py']},
               golden='tools/hdc_golden_v41.py rope_freqs/rope_cs, compiler/models/deepseek-v4.1-flash/inference_config.json',
               runs=runs, verdict='PASS' if ok else 'FAIL',
               table_bytes_per_die=2 * (1 << 20) * 256, fetch_per_step='3 entries x 8 sectors = 768 B (6 reads of 4 sectors)')
    a.out.parent.mkdir(parents=True, exist_ok=True); a.out.write_text(json.dumps(rec, indent=1) + '\n')
    print(rec['verdict']); [print(r) for r in runs]
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
