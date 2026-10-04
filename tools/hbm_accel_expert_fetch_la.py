"""HA4 R5a-LA: routed-expert fetch BANDWIDTH and first access on the lookahead stream path (RTL, Verilator).

Builds rtl/test/hbm_accel/tb_hbm_accel_expert_fetch_la.sv in the VARIANTS below (selected: PICK=2, REPICK=1,
RESERVE=1, PULL=0, TAILPULL=12; 'pred' is the predecessor's LA refresh policy) and sweeps the router's top-6 time across a whole REFpb round
with random top-6 id sets (seeded), with and without the static-schedule refresh notice.  One stack
(32 PCs at CK/2 = 1.024 ns, 32 B per RD) peaks at 32 * 32 B / 1.024 ns = 1.0 TB/s.

    python3 tools/hbm_accel_expert_fetch_la.py --work DIR --out RECORD.json [--jobs N]

Metrics per case: stream TB/s = bytes / (last - first sector returned at the PHY + one burst);
end-to-end TB/s = bytes / (router top-6 out -> every SM released the task); first access (w13 of
expert 1 at every SM).  Exactness: every released line equals the c52 SM-line pattern (bench check).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import re
import statistics
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERILATOR = os.environ.get('VERILATOR', str(Path.home() / '.local/opentallas-tools/verilator-5.050/bin/verilator'))
SOURCES = ['rtl/hbm_accel/service/ot_hbm_accel_cdc_fifo.sv',
           'rtl/hbm_accel/service/ot_hbm_accel_expert_stream_pc_la.sv',
           'rtl/hbm_accel/service/ot_hbm_accel_expert_fetch_stream_la.sv',
           'rtl/test/hbm_accel/tb_hbm_accel_expert_fetch_la.sv']
TOP = 'tb_hbm_accel_expert_fetch_la'
BYTES = 6 * 392 * 128                 # six experts' 392 SM lines of 128 B on this stack (9,408 sectors of 32 B)
PEAK_TBS = 32 * 32 / 1.024e3          # 1.0 TB/s
NOTICE_LEAD_PS = 300_000
NEXPERT = 256                         # V4.1 routed experts; ids drawn per task without replacement


VARIANTS = {'sel': dict(PICK=2, REPICK=1, RESERVE=1, PULL=0, TAILPULL=12),
            'pred': dict(PICK=0, REPICK=0, RESERVE=0, PULL=16, TAILPULL=0),
            'pick1': dict(PICK=1, REPICK=1, RESERVE=1, PULL=0, TAILPULL=12),
            'pick0': dict(PICK=0, REPICK=1, RESERVE=1, PULL=0, TAILPULL=12),
            'no_tailpull': dict(PICK=1, REPICK=1, RESERVE=1, PULL=0, TAILPULL=0),
            # 2026-10-04 expert-fetch >= 90% successors (all default-off parameters):
            #   ORDER=1  rate-balanced line order (load-time cfg_lut; w1/w3 still first, per-SM order unchanged)
            #   PCPROT=1 per-PC refresh protection (only the sets this PC still has to stream)
            #   STEER=1  in-stream REFpb slot steering (pending REFpb issues early when no ACT is wanted)
            #   NWIN=300 ramp-aware notice (a REFpb due in the window's first-ACT ramp issues before it)
            'o1': dict(PICK=2, REPICK=1, RESERVE=1, PULL=0, TAILPULL=12, ORDER=1),
            'o1_pcprot': dict(PICK=2, REPICK=1, RESERVE=1, PULL=0, TAILPULL=12, ORDER=1, PCPROT=1),
            'o1_pcprot_steer': dict(PICK=2, REPICK=1, RESERVE=1, PULL=0, TAILPULL=12, ORDER=1, PCPROT=1, STEER=1),
            'pcprot_steer_nwin': dict(PICK=2, REPICK=1, RESERVE=1, PULL=0, TAILPULL=12, PCPROT=1, STEER=1, NWIN=300),
            'sel90': dict(PICK=2, REPICK=1, RESERVE=1, PULL=0, TAILPULL=12, ORDER=1, PCPROT=1, STEER=1, NWIN=300),
            'sel90_law7': dict(PICK=2, REPICK=1, RESERVE=1, PULL=0, TAILPULL=12, ORDER=1, PCPROT=1, STEER=1, NWIN=300, LAW=7)}
NEG_VARIANTS = ('sel', 'sel90')


def build(work, name):
    d = work / f'build_{name}'
    exe = d / 'obj' / f'V{TOP}'
    if exe.exists():
        return exe
    d.mkdir(parents=True, exist_ok=True)
    cmd = [VERILATOR, '--binary', '--timing', '-Wno-fatal', '-Wno-WIDTH', '-j', '8', '-O2', '--top-module', TOP,
           '--Mdir', str(d / 'obj')] + [f'-G{k}={v}' for k, v in VARIANTS[name].items()] + [str(ROOT / s) for s in SOURCES]
    with open(d / 'build.log', 'w') as log:
        subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT, check=True)
    return exe


def run(exe, t_route_ps, lead_ps, ids, mut=0):
    args = [str(exe), f'+t_route_ps={t_route_ps}', f'+notice_lead_ps={lead_ps}', f'+mut={mut}']
    args += [f'+id{k}={v}' for k, v in enumerate(ids)]
    out = subprocess.run(args, capture_output=True, text=True, check=False).stdout
    first = [l for l in out.splitlines() if l.startswith('FIRST ')]
    bw = [l for l in out.splitlines() if l.startswith('BW ')]
    if len(first) < 2 or not bw:
        return dict(t_route_ps=t_route_ps, notice_lead_ps=lead_ps, ids=ids, mut=mut, verdict='FAIL', raw=out[-2000:])
    rec = {k: int(v) for k, v in re.findall(r'(\w+)=(-?\d+)\b', first[0])}
    rec.update({k: int(v) for k, v in re.findall(r'(\w+_ps|n_ret)=(-?\d+)', bw[0])})
    rec.update(ids=ids, mut=mut, verdict=first[1].split('=')[1])
    span = rec['ret_last_ps'] - rec['ret_first_ps'] + 1024
    rec['stream_tbs'] = round(BYTES / span, 4)
    rec['e2e_tbs'] = round(BYTES / rec['done_ps'], 4)
    rec['w13_first_all_ns'] = rec['w13_first_all_ps'] / 1000
    return rec


def stats(rows):
    ok = [r for r in rows if r['verdict'] == 'PASS']
    if not ok:
        return dict(cases=len(rows), passed=0)
    def s(key, nd=4):
        v = [r[key] for r in ok]
        return dict(min=round(min(v), nd), mean=round(statistics.mean(v), nd), max=round(max(v), nd))
    return dict(cases=len(rows), passed=len(ok), stream_tbs=s('stream_tbs'), e2e_tbs=s('e2e_tbs'),
                stream_frac_of_peak_min=round(min(r['stream_tbs'] for r in ok) / PEAK_TBS, 4),
                stream_frac_of_peak_mean=round(statistics.mean(r['stream_tbs'] for r in ok) / PEAK_TBS, 4),
                first_access_ns=s('w13_first_all_ns', 3), viol=sum(r['viol'] for r in ok), bad=sum(r['bad'] for r in ok))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--work', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--jobs', type=int, default=16)
    ap.add_argument('--points', type=int, default=64)
    ap.add_argument('--seed', type=int, default=20261004)
    a = ap.parse_args(argv)
    if a.out.exists():
        raise SystemExit('fresh record path required')
    a.work.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(len(VARIANTS)) as ex:
        exes = dict(zip(VARIANTS, ex.map(lambda n: build(a.work, n), VARIANTS)))
    exe1 = exes['sel']
    rng = random.Random(a.seed)
    t0, pb_span = 8_000_000, 3_866_624
    jobs = []
    for i in range(a.points):
        ids = rng.sample(range(NEXPERT), 6)
        t = t0 + i * pb_span // a.points + 7_013 * i % 1024
        for name, exe in exes.items():
            jobs.append((f'{name}_notice', exe, t, NOTICE_LEAD_PS, ids))
        jobs.append(('sel_no_notice', exe1, t, 0, ids))
        jobs.append(('sel90_no_notice', exes['sel90'], t, 0, ids))
    # adversarial: all six experts in one bank set (no set alternation possible)
    for i in range(8):
        base = rng.randrange(7)
        ids = [base + 7 * rng.randrange(36) for _ in range(6)]
        while len(set(ids)) < 6:
            ids = [base + 7 * rng.randrange(36) for _ in range(6)]
        jobs.append(('sel_notice_same_set', exe1, t0 + i * pb_span // 8, NOTICE_LEAD_PS, ids))
        jobs.append(('sel90_notice_same_set', exes['sel90'], t0 + i * pb_span // 8, NOTICE_LEAD_PS, ids))
    with ThreadPoolExecutor(a.jobs) as ex:
        res = list(ex.map(lambda j: dict(case=j[0], **run(j[1], j[2], j[3], j[4])), jobs))
    neg = []
    for v in NEG_VARIANTS:
        sfx = '' if v == 'sel' else f'_{v}'
        neg += [dict(case=f'neg_corrupt_sector{sfx}', **run(exes[v], t0, NOTICE_LEAD_PS, [61, 69, 112, 170, 299, 357], 1)),
                dict(case=f'neg_trcd_check_plus_1ns{sfx}', **run(exes[v], t0, NOTICE_LEAD_PS, [61, 69, 112, 170, 299, 357], 2))]
    names = sorted({r['case'] for r in res})
    st = {c: stats([r for r in res if r['case'] == c]) for c in names}
    sel = [r for r in res if r['case'] in ('sel_notice', 'sel90_notice')]
    exact = all(r['verdict'] == 'PASS' and r.get('bad', 1) == 0 and r.get('viol', 1) == 0 for r in res)
    git = lambda *c: subprocess.run(['git', *c], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    rec = dict(schema='opentallas.hbm_accel.ha4.expert_fetch_la.v1',
               source_commit=git('rev-parse', 'HEAD'),
               source_dirty=bool(git('status', '--porcelain', '--untracked-files=no', '--', *SOURCES)),
               input_sha256={s: hashlib.sha256((ROOT / s).read_bytes()).hexdigest() for s in SOURCES},
               simulator=subprocess.run([VERILATOR, '--version'], capture_output=True, text=True).stdout.strip(),
               host=os.uname().nodename, controller_clock_ps=1024, sm_clock_ps=833, peak_tbs_per_stack=PEAK_TBS,
               bytes_per_task_per_stack=BYTES, variants=VARIANTS, seed=a.seed, notice_lead_ps=NOTICE_LEAD_PS,
               baseline_r5a=dict(stream_tbs=0.395, record='results/rtl/hbm_accel_ha4_20261004/expert_first_access.json',
                                 note='R5a: every expert in bank set 0; 774 ns done for the same 301,056 B'),
               stats=st, exact=dict(verdict='PASS' if exact else 'FAIL', cases=len(res),
                                    scope='every case of every variant: every released line compared, 0 DRAM violations'),
               negative_controls=[dict(case=n['case'], verdict=n['verdict'], bad=n.get('bad'), viol=n.get('viol')) for n in neg],
               cases=res + neg)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(rec, indent=2) + '\n')
    print(json.dumps(dict(stats=st, exact=rec['exact'], negative=rec['negative_controls']), indent=2))


if __name__ == '__main__':
    main()
