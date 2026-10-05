"""HBM path audit: DS-V4.1 HBM-accelerator KV/index load paths of one stack at 1M (RTL, Verilator).

Builds rtl/test/hbm_accel/tb_hbm_accel_dskv_stream.sv with the landing crossing as built (LAW 5, R5a) and
64 deep (LAW 6), sweeps the go time across one REFpb round for every case, and writes one record.

    python3 tools/hbm_accel_dskv_stream_audit.py --work DIR --out RECORD.json [--jobs N] [--points 32]

Per-die figures are four times the stack's (keys / rows sharded by position, four identical stacks a die).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import statistics
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERILATOR = os.environ.get('VERILATOR', str(Path.home() / '.local/opentallas-tools/verilator-5.050/bin/verilator'))
SOURCES = ['rtl/hbm_accel/service/ot_hbm_accel_cdc_fifo.sv',
           'rtl/hbm_accel/service/ot_hbm_accel_expert_stream_pc.sv',
           'rtl/test/hbm_accel/tb_hbm_accel_dskv_stream.sv']
TOP = 'tb_hbm_accel_dskv_stream'
PEAK_STACK_TBPS = 32 * 32 / 1.024e-9 / 1e12        # 32 PCs x 32 B a CK/2 cycle (1.024 ns) = 1.0 TB/s
STACKS_PER_DIE = 4
KEY_B, CKV_ROW_B = 68, 288                         # tools/arch_budget_v41.py IDX_KEY_B, CKV_ROW_B
TP = 96
# case: (name, law, plusargs, note)
PREFETCH = 30_000     # scan RDs start 30 ns before the query (sweep 30-60 ns: same worst completion; 30 keeps steady max)
NOTICE = 300_000      # >= LEAD 48 + tRFCpb 196 + tRCD 19 cycles; static-schedule notice as in R5a
CASES = [
    ('scan_L20_as_built', 5, dict(mode=0, nsect=182, nk=0), 'L20/24/28/32/36 keys, R5a landing (32 deep), no notice'),
    ('scan_L20_law6', 6, dict(mode=0, nsect=182, nk=0), 'L20 keys, 64-deep landing, no notice'),
    ('scan_L20_law6_notice', 6, dict(mode=0, nsect=182, nk=0, notice_lead_ps=NOTICE),
     'L20 keys, 64-deep landing + static-schedule notice (refactor)'),
    ('scan_L20_refactor_prefetch', 6, dict(mode=0, nsect=182, nk=0, notice_lead_ps=NOTICE, prefetch_ps=PREFETCH),
     'L20 keys, refactor + key RDs start PREFETCH before the query (key region known at token start)'),
    ('scan_L2_as_built', 5, dict(mode=0, nsect=91, nk=0), 'L2/8/14 keys, R5a landing, no notice'),
    ('scan_L2_law6_notice', 6, dict(mode=0, nsect=91, nk=0, notice_lead_ps=NOTICE), 'L2/8/14 keys, refactor'),
    ('scan_L2_refactor_prefetch', 6, dict(mode=0, nsect=91, nk=0, notice_lead_ps=NOTICE, prefetch_ps=PREFETCH),
     'L2/8/14 keys, refactor + prefetch'),
    ('window_layer_as_built', 5, dict(mode=0, nsect=17, nk=0),
     'SWA window of one layer IF HBM-resident (128 x 528 B / 4 stacks = 17 sectors a PC), as built'),
    ('window_layer_refactor_prefetch', 6, dict(mode=0, nsect=17, nk=0, notice_lead_ps=NOTICE, prefetch_ps=PREFETCH),
     'same, refactor + prefetch'),
    ('scan_L20_w19_scorer_nk1', 5, dict(mode=0, nsect=182, nk=1),
     'W19 die scorer NK 4 keys/cycle = 1 key/cycle a stack (consumer-bound), as built'),
    ('scan_L20_index_stack_nk16_refactor', 6, dict(mode=0, nsect=182, nk=16, notice_lead_ps=NOTICE),
     'ot_hbm_accel_index_stack rate (NSL 4 x NK 4 = 16 keys/cycle a stack), refactor'),
    ('gather_sel_2rows_as_built', 5, dict(mode=1, nrows=2),
     'selected compressed-KV rows after the merge (512 over 96 dies: 1.33 a stack; 2 rows), no notice'),
    ('gather_sel_2rows_notice', 5, dict(mode=1, nrows=2, notice_lead_ps=NOTICE),
     'same, CKV rows in sets 0..2 + static-schedule notice over the gather window (refactor)'),
]


def build(work, law):
    d = work / f'law{law}'
    exe = d / f'V{TOP}'
    if exe.exists():
        return exe
    cmd = [VERILATOR, '--binary', '--timing', '-Wno-fatal', '-Wno-WIDTH', '-j', '8', '-O2', '--top-module', TOP,
           '--Mdir', str(d), f'-GLAW={law}'] + [str(ROOT / s) for s in SOURCES]
    d.mkdir(parents=True, exist_ok=True)
    with open(work / f'build_law{law}.log', 'w') as log:
        subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT, check=True)
    return exe


def run(exe, args, t_go, mut=0):
    argv = [str(exe), f'+t_go_ps={t_go}', f'+mut={mut}'] + [f'+{k}={v}' for k, v in args.items()]
    out = subprocess.run(argv, capture_output=True, text=True, check=False).stdout
    bw = [l for l in out.splitlines() if l.startswith('BW ')]
    if len(bw) < 2:
        return dict(t_go_ps=t_go, mut=mut, verdict='FAIL', raw=out[-1500:])
    rec = {k: int(v) for k, v in re.findall(r'(\w+)=(-?\d+)', bw[0])}
    rec.update(mut=mut, verdict=bw[1].split('=')[1])
    b = rec['bytes']
    span_rd = rec['rd_last'] - rec['rd_first'] + 1024              # first RD issue -> last RD burst end
    rec['steady_tbps'] = round(b / (span_rd * 1e-12) / 1e12, 4)
    rec['end_to_end_tbps'] = round(b / (rec['cons_last'] * 1e-12) / 1e12, 4)  # go -> last sector at the scorer
    rec['first_access_ns'] = rec['cons_first'] / 1000
    rec['complete_ns'] = rec['cons_last'] / 1000
    return rec


def summ(rows):
    ok = [r for r in rows if r['verdict'] == 'PASS']
    if not ok:
        return dict(cases=len(rows), passed=0)
    f = lambda k, g: round(g(r[k] for r in ok), 4)  # noqa: E731
    return dict(cases=len(rows), passed=len(ok), bytes=ok[0]['bytes'],
                steady_tbps_min=f('steady_tbps', min), steady_tbps_mean=round(statistics.mean(r['steady_tbps'] for r in ok), 4),
                end_to_end_tbps_min=f('end_to_end_tbps', min),
                end_to_end_tbps_mean=round(statistics.mean(r['end_to_end_tbps'] for r in ok), 4),
                first_access_ns_max=f('first_access_ns', max),
                first_access_ns_mean=round(statistics.mean(r['first_access_ns'] for r in ok), 2),
                complete_ns_max=f('complete_ns', max),
                steady_pct_of_peak_min=round(100 * min(r['steady_tbps'] for r in ok) / PEAK_STACK_TBPS, 1),
                end_to_end_pct_of_peak_min=round(100 * min(r['end_to_end_tbps'] for r in ok) / PEAK_STACK_TBPS, 1))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--work', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--jobs', type=int, default=16)
    ap.add_argument('--points', type=int, default=32)
    a = ap.parse_args(argv)
    if a.out.exists():
        raise SystemExit('fresh record path required')
    a.work.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(2) as ex:
        exes = dict(zip((5, 6), ex.map(lambda l: build(a.work, l), (5, 6))))
    t0, span = 8_000_000, 118 * 32 * 1024            # one 32-command REFpb round
    jobs = [(c, law, args, t0 + i * span // a.points + 7013 * i % 1024)
            for c, law, args, _ in CASES for i in range(a.points)]
    with ThreadPoolExecutor(a.jobs) as ex:
        res = list(ex.map(lambda j: dict(case=j[0], law=j[1], **run(exes[j[1]], j[2], j[3])), jobs))
    neg = [dict(case='neg_corrupt_sector', **run(exes[6], CASES[1][2], t0, 1)),
           dict(case='neg_trcd_check_plus_1ns', **run(exes[5], [c for c in CASES if c[0] == 'gather_sel_2rows_as_built'][0][2], t0, 2))]
    st = {c: dict(law=law, note=note, **summ([r for r in res if r['case'] == c])) for c, law, _, note in CASES}
    head = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    dirty = subprocess.run(['git', 'status', '--porcelain', '--', *SOURCES, 'tools/hbm_accel_dskv_stream_audit.py'],
                           cwd=ROOT, capture_output=True, text=True).stdout.strip()
    rec = dict(schema='opentallas.hbm_accel.dskv_stream_audit.v1', source_commit=head, source_dirty=bool(dirty),
               input_sha256={s: hashlib.sha256((ROOT / s).read_bytes()).hexdigest()
                             for s in SOURCES + ['tools/hbm_accel_dskv_stream_audit.py']},
               simulator=subprocess.run([VERILATOR, '--version'], capture_output=True, text=True).stdout.strip(),
               host=os.uname().nodename, controller_clock_ps=1024, consumer_clock_ps=833,
               peak_stack_tbps=PEAK_STACK_TBPS, stacks_per_die=STACKS_PER_DIE,
               assumed_path_ns=dict(noc=5.0, phy_command=5.0, phy_response=10.0, note='R5a bench terms'),
               metrics=dict(steady='bytes / (first RD issue -> last RD burst end)',
                            end_to_end='bytes / (query time -> last sector consumed at the scorer), includes the exposed first access',
                            first_access='go -> first sector consumed'),
               stats=st, negative_controls=[dict(case=n['case'], verdict=n['verdict'], bad=n.get('bad'),
                                                 viol=n.get('viol')) for n in neg],
               cases=res + neg)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(rec, indent=1) + '\n')
    print(json.dumps(dict(stats=st, negative=rec['negative_controls']), indent=1))


if __name__ == '__main__':
    main()
