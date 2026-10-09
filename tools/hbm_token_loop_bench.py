#!/usr/bin/env python3
"""hbm-system 2026-10-08 (T3 gap 7): bench of the on-die token loop + stop condition (rtl/hbm_accel/control/
ot_hbm_token_loop.sv, bench rtl/test/hbm_accel/tb_hbm_token_loop.sv, Icarus).

Reference (independent Python): generate() with the HF stop convention -- the step at position p returns token t
(placed at p + 1); t is emitted; stop if t == eos (eos_en), or ngen tokens emitted, or p + 1 >= max_pos, or the host
asked to stop (after the step it was raised in); otherwise the next step runs (t, p + 1).  MTP: each verify commit of
n tokens is emitted in order under the same rules; the effective count is what the spec state commits.
Checks: the doorbells (AR) equal the reference steps; host records (last, status, job, pos, tok) equal; MTP emit
counts equal.  Negative control: MUT=1 (EOS compare removed) must FAIL.

    python3 tools/hbm_token_loop_bench.py --work DIR --out RECORD.json
"""
import argparse, hashlib, json, random, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ['rtl/hbm_accel/control/ot_hbm_token_loop.sv', 'rtl/test/hbm_accel/tb_hbm_token_loop.sv']
EOS = 1    # compiler/models/deepseek-v4.1-flash/config.json eos_token_id


def ref(job):
    jid, tok, pos, ngen, eos, en, maxpos, mtp, hsa, stream = job
    D, R, E = [], [], []
    ne, p = 0, pos
    def verdict(t, p, ne):
        if en and t == eos: return 1
        if ne + 1 >= ngen: return 2
        if p + 2 > maxpos: return 3
        return 0
    if not mtp:
        cur = tok
        for step, t in enumerate(stream, 1):
            D.append((cur, p))
            v = verdict(t, p, ne)
            ne += 1
            if v == 0 and hsa and step >= hsa: v = 5
            R.append((int(v != 0), v, jid, p + 1, t))
            if v: break
            cur, p = t, p + 1
    else:
        for step, (n, ts) in enumerate(stream, 1):
            stop = False
            for i in range(n):
                t = ts[i]
                v = verdict(t, p, ne)
                ne += 1
                if v == 0 and hsa and step >= hsa and i == n - 1: v = 5
                R.append((int(v != 0), v, jid, p + 1, t)); p += 1
                if v:
                    E.append((i + 1, 1)); stop = True; break
            if stop: break
            E.append((n, 0))
    return D, R, E


def scenarios(rng):
    jobs = []
    jid = 1
    for _ in range(60):
        mtp = rng.random() < 0.4
        pos = rng.randrange(0, 1 << 20) if rng.random() < 0.3 else rng.randrange(0, 5000)
        ngen = rng.randrange(1, 40)
        maxpos = min((1 << 20), pos + rng.randrange(2, 60)) if rng.random() < 0.3 else (1 << 20)
        en = int(rng.random() < 0.85)
        hsa = rng.randrange(1, 10) if rng.random() < 0.15 else 0
        if mtp:
            stream = []
            for _ in range(80):
                n = rng.randrange(1, 7)
                stream.append((n, [EOS if rng.random() < 0.04 else rng.randrange(2, 129280) for _ in range(6)]))
        else:
            stream = [EOS if rng.random() < 0.05 else rng.randrange(2, 129280) for _ in range(80)]
        jobs.append((jid, rng.randrange(2, 129280), pos, ngen, EOS, en, maxpos, int(mtp), hsa, stream)); jid += 1
    # directed: EOS at the very first token, EOS at the last allowed, EOS in the middle of an MTP batch, max_pos edge
    jobs.append((jid, 5, 10, 8, EOS, 1, 1 << 20, 0, 0, [EOS] + [7] * 79)); jid += 1
    jobs.append((jid, 5, 10, 3, EOS, 1, 1 << 20, 0, 0, [9, 9, EOS] + [7] * 77)); jid += 1
    jobs.append((jid, 5, 10, 50, EOS, 1, 1 << 20, 1, 0, [(6, [3, 4, EOS, 6, 7, 8])] + [(1, [2] * 6)] * 79)); jid += 1
    jobs.append((jid, 5, (1 << 20) - 3, 50, EOS, 1, 1 << 20, 0, 0, [9] * 80)); jid += 1
    jobs.append((jid, 5, 10, 50, EOS, 0, 1 << 20, 0, 0, [EOS, EOS, 3] + [4] * 77)); jid += 1
    return jobs


def write_scen(path, jobs):
    L = []
    for j in jobs:
        jid, tok, pos, ngen, eos, en, maxpos, mtp, hsa, stream = j
        L.append(f'J {jid} {tok} {pos} {ngen} {eos} {en} {maxpos} {mtp} {hsa}')
        L.append(f'N {len(stream)}')
        for s in stream:
            L.append(f'B {s[0]} ' + ' '.join(map(str, s[1])) if mtp else f'T {s}')
    path.write_text('\n'.join(L) + '\n')


def run(work, mut, jobs):
    d = work / f'mut{mut}'; d.mkdir(parents=True, exist_ok=True)
    write_scen(d / 'scen.txt', jobs)
    subprocess.run(['iverilog', '-g2012', f'-Ptb_hbm_token_loop.MUT={mut}', '-o', str(d / 'sim.vvp')] +
                   [str(ROOT / s) for s in SRC], check=True)
    subprocess.run(['vvp', '-n', str(d / 'sim.vvp')], cwd=d, check=True, capture_output=True, timeout=1800)
    lines = (d / 'out.txt').read_text().split('\n')
    got = {}
    cur = {'D': [], 'R': [], 'E': []}
    bad = []
    for l in lines:
        if not l: continue
        f = l.split()
        if f[0] == 'X':
            got[int(f[1])] = cur; cur = {'D': [], 'R': [], 'E': []}
        elif f[0] == 'TIMEOUT': bad.append('timeout')
        elif f[0] in 'DRE': cur[f[0]].append(tuple(map(int, f[1:])))
    for j in jobs:
        D, R, E = ref(j)
        g = got.get(j[0])
        if g is None: bad.append(f'job {j[0]} missing'); continue
        if g['D'] != D and not j[7]: bad.append(f'job {j[0]} doorbells'); continue
        if g['R'] != R: bad.append(f'job {j[0]} records {g["R"][:3]} vs {R[:3]}'); continue
        if j[7] and g['E'] != E: bad.append(f'job {j[0]} mtp emits {g["E"]} vs {E}')
    return bad


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--work', type=Path, required=True); ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    jobs = scenarios(random.Random(20261008))
    b0 = run(a.work, 0, jobs); b1 = run(a.work, 1, jobs)
    stat = {}
    for j in jobs:
        _, R, _ = ref(j); s = R[-1][1]; stat[s] = stat.get(s, 0) + 1
    rec = dict(schema='opentallas.hbm_system.token_loop.v1',
               source_sha256={s: hashlib.sha256((ROOT / s).read_bytes()).hexdigest() for s in SRC + ['tools/hbm_token_loop_bench.py']},
               jobs=len(jobs), records=sum(len(ref(j)[1]) for j in jobs), final_status_counts={str(k): v for k, v in sorted(stat.items())},
               positive=dict(verdict='PASS' if not b0 else 'FAIL', problems=b0[:5]),
               negative_mut1_no_eos=dict(verdict='FAIL' if b1 else 'PASS', problems=b1[:3]),
               verdict='PASS' if (not b0 and b1) else 'FAIL',
               loop_turnaround_cycles='cpl accepted -> next doorbell valid: 1 (record) + DB_LAT 2 + 1 (L_DB) = 4 clk_stream cycles; '
                                      'no host round trip, no inter-die message')
    a.out.parent.mkdir(parents=True, exist_ok=True); a.out.write_text(json.dumps(rec, indent=1) + '\n')
    print(rec['verdict'], rec['positive'], rec['negative_mut1_no_eos']['verdict'], rec['final_status_counts'])
    return 0 if rec['verdict'] == 'PASS' else 1


if __name__ == '__main__':
    sys.exit(main())
