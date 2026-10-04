#!/usr/bin/env python3
"""DS-V4.1 HBM accelerator, one decode token at position 1,048,575: every per-die HBM load on the token's critical
path, measured in RTL on the HBM accelerator's own stream sequencer (ot_hbm_accel_expert_stream_pc, the 52ce3e9c1 r6
stream PC + notice) with the DRAM checker at main's CORRECTED REFpb rules (54dcb2ab6 / c217afff7: same-bank tRFCpb,
tRREFD after ACT and after REFpb, each bank once a 32-REFpb round), 64 refresh phases a case.

Minimum component: one HBM3E stack (32 PCs); a die is four identical, independent stacks (keys / rows sharded by
position), so per-die bytes are 4x and per-die time is the stack's (the worst-loaded stack for the gather).

    python3 tools/dshbm_1m_hbm.py prep  --out PREP.json          # golden per-source-die CKV row counts (tiny, local)
    python3 tools/dshbm_1m_hbm.py run   --work DIR --prep PREP.json --out RUNS.json [--jobs N] [--points 64]  (remote)
    python3 tools/dshbm_1m_hbm.py record --runs RUNS.json --prep PREP.json --out results/rtl/dshbm_1m_allmeasured_20261004/hbm_streams.json

Bench: rtl/test/hbm_accel/tb_dshbm_1m_streams.sv (successor copy of tb_hbm_accel_dskv_stream.sv: post-at-go scans,
multi-row gathers, distinct per-sector patterns).
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
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
           'rtl/test/hbm_accel/tb_dshbm_1m_streams.sv']
TOP = 'tb_dshbm_1m_streams'
PEAK_STACK_TBPS = 32 * 32 / 1.024e-9 / 1e12          # 1.0 TB/s a stack (32 PCs x 32 B a 1.024 ns CK/2 cycle)
STACKS, TP, KEY_BLOCK = 4, 96, 8
KEY_B, CKV_ROW_B, KV_ROW_B = 68, 288, 576            # FP4 key + ue8m0; gathered CKV row (kv_gather 147,456 / 512);
#                                                      window row (448 FP8 nope + 64 BF16 rope, dshbm_baseline_measure)
HIDDEN = 5120                                         # golden h_in (4, 5120): embedding row 5,120 x BF16
NOTICE, PREFETCH = 300_000, 30_000                    # as tools/hbm_accel_dskv_stream_audit.py (R5a notice; 30 ns)
GOLD = Path('/home/ubuntu/w17work/ref/ctx1048576_seed20260930')
SEL_LAYERS = (2, 8, 14, 20, 24, 28, 32, 36)


def sectors_per_pc(bytes_stack):
    return math.ceil(bytes_stack / 32 / 32)


KEYS_L2, KEYS_L20 = math.ceil(524288 / TP), math.ceil(1048576 / TP)          # 5,462 / 10,923 keys a die
NS_L2 = sectors_per_pc(KEYS_L2 * KEY_B / STACKS)                             # 91
NS_L20 = sectors_per_pc(KEYS_L20 * KEY_B / STACKS)                           # 182
NS_WIN = sectors_per_pc(128 * KV_ROW_B / STACKS)                             # 18
NS_EMB = sectors_per_pc(HIDDEN * 2 / STACKS)                                 # 3


def cases(prep):
    g = prep['ckv_rows']
    worst_stack, worst_die = g['max_rows_per_stack'], g['max_rows_per_die']
    C = []
    for tag, ns, keys in (('L20', NS_L20, KEYS_L20), ('L2', NS_L2, KEYS_L2)):
        C += [(f'scan_{tag}_as_built', 5, dict(mode=0, nsect=ns, nk=0),
               f'{tag}-type index keys ({keys} keys/die, {ns} sectors a PC), R5a landing 32, descriptor posted 200 ns '
               'ahead, RDs at the query, no notice'),
              (f'scan_{tag}_notice', 6, dict(mode=0, nsect=ns, nk=0, notice_lead_ps=NOTICE),
               f'{tag} keys, 64-deep landing + static-schedule notice, RDs at the query'),
              (f'scan_{tag}_prefetch', 6, dict(mode=0, nsect=ns, nk=0, notice_lead_ps=NOTICE, prefetch_ps=PREFETCH),
               f'{tag} keys, notice + key RDs start 30 ns before the query (region known at token start)'),
              (f'scan_{tag}_index_stack_nk16', 6, dict(mode=0, nsect=ns, nk=16, notice_lead_ps=NOTICE),
               f'{tag} keys consumed at the ot_hbm_accel_index_stack rate (16 keys a 1.2 GHz cycle a stack), notice')]
    C += [('window_as_built', 5, dict(mode=0, nsect=NS_WIN, nk=0),
           f'window 128 x {KV_ROW_B} B a die ({NS_WIN} sectors a PC), as built, RDs at the query'),
          ('window_notice', 6, dict(mode=0, nsect=NS_WIN, nk=0, notice_lead_ps=NOTICE), 'window, notice'),
          ('window_prefetch', 6, dict(mode=0, nsect=NS_WIN, nk=0, notice_lead_ps=NOTICE, prefetch_ps=PREFETCH),
           'window, notice + RDs 30 ns before the query (rows known at token start)')]
    for n, why in ((2, 'uniform expectation 512/96/4 = 1.33 rows a stack'),
                   (worst_stack, f'golden worst stack ({worst_stack} rows, stack = (row//8//96) % 4, ASSUMED map)'),
                   (worst_die, f'golden worst source die ({worst_die} rows) all on one stack (bound)')):
        C += [(f'gather_{n}rows_as_built', 5, dict(mode=1, nrows=n), f'selected CKV rows, {why}; posted at the merge '
               '(token-dependent), no notice'),
              (f'gather_{n}rows_notice', 5, dict(mode=1, nrows=n, notice_lead_ps=NOTICE),
               f'selected CKV rows, {why}; static-schedule notice over the gather window')]
    C += [('engram_1row_notice', 5, dict(mode=1, nrows=1, notice_lead_ps=NOTICE),
           'Engram table row by hash: one random 288-B row read on the same gather path (no Engram HBM RTL)'),
          ('embedding_row_post_at_go', 6, dict(mode=0, nsect=NS_EMB, nk=0, post_lead_ps=0),
           f'embedding row ({HIDDEN} x BF16 = {HIDDEN * 2} B a die, {NS_EMB} sectors a PC), address known only at go'),
          ('embedding_row_notice', 6, dict(mode=0, nsect=NS_EMB, nk=0, post_lead_ps=0, notice_lead_ps=NOTICE),
           'embedding row, posted at go, notice')]
    return C


# ---------------------------------------------------------------------------------------------------------------
def cmd_prep(a):
    import numpy as np
    out = dict(golden=str(GOLD), rule='sel = global top-512 of the layer index scores (max first, lowest index on '
               'ties: w19_hbm_tp96_isa op_merge); owner die = (i // 8) % 96 (key_owner, KEY_BLOCK 8); stack within the '
               'die ASSUMED (i // 8 // 96) % 4 (the die interleaves its key blocks over its four stacks)', layers={})
    mx_die = mx_stk = 0
    for L in SEL_LAYERS:
        z = np.load(GOLD / f'ctx1048576_L{L:02d}.npz')
        v = z[f'L{L}.index_scores']
        i = np.arange(len(v))
        order = np.lexsort((i, -v))[:512]
        own = (order // KEY_BLOCK) % TP
        c = np.bincount(own, minlength=TP)
        stk = (order // KEY_BLOCK // TP) % STACKS
        cs = np.zeros((TP, STACKS), int)
        np.add.at(cs, (own, stk), 1)
        out['layers'][L] = dict(n_scores=int(len(v)), finite=int(np.isfinite(v).sum()), max_rows_per_die=int(c.max()),
                                mean_rows_per_die=round(float(c.mean()), 3), dies_with_rows=int((c > 0).sum()),
                                max_rows_per_stack=int(cs.max()), hist_rows_per_die=np.bincount(c).tolist())
        mx_die, mx_stk = max(mx_die, int(c.max())), max(mx_stk, int(cs.max()))
        print(L, out['layers'][L])
    out['ckv_rows'] = dict(max_rows_per_die=mx_die, max_rows_per_stack=mx_stk, row_bytes=CKV_ROW_B)
    out['input_sha256'] = {f'ctx1048576_L{L:02d}.npz': hashlib.sha256((GOLD / f'ctx1048576_L{L:02d}.npz').read_bytes())
                           .hexdigest() for L in SEL_LAYERS}
    Path(a.out).write_text(json.dumps(out, indent=1) + '\n')


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
    bw = [ln for ln in out.splitlines() if ln.startswith('BW ')]
    if len(bw) < 2:
        return dict(t_go_ps=t_go, mut=mut, verdict='FAIL', raw=out[-1500:])
    rec = {k: int(v) for k, v in re.findall(r'(\w+)=(-?\d+)', bw[0])}
    rec.update(mut=mut, verdict=bw[1].split('=')[1])
    # --chk: the independent per-PC DRAM checker (rtl/test/ot_hbm_pc_dram_check.sv, bound into every PC)
    pcl = re.findall(r'DRAMCHK_PC \S+ viol=(\d+) act=(\d+) pre=\d+ ref=(\d+) rd=(\d+)', out)
    if pcl:
        rec.update(pcchk_pcs=len(pcl), pcchk_viol=sum(int(m[0]) for m in pcl), pcchk_ref=sum(int(m[2]) for m in pcl))
    b = rec['bytes']
    rec['steady_tbps'] = round(b / ((rec['rd_last'] - rec['rd_first'] + 1024) * 1e-12) / 1e12, 4)
    rec['end_to_end_tbps'] = round(b / (rec['cons_last'] * 1e-12) / 1e12, 4) if rec['cons_last'] > 0 else None
    rec['first_access_ns'] = rec['cons_first'] / 1000
    rec['complete_ns'] = rec['cons_last'] / 1000
    return rec


def cmd_run(a):
    global SOURCES
    if a.chk:
        SOURCES = SOURCES + ['rtl/test/ot_hbm_pc_dram_check.sv']
    prep = json.loads(Path(a.prep).read_text())
    a.work.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(2) as ex:
        exes = dict(zip((5, 6), ex.map(lambda law: build(a.work, law), (5, 6))))
    t0, span = 8_000_000, 118 * 32 * 1024                      # one 32-command REFpb round (64 phases across it)
    C = [c for c in cases(prep) if not a.only or any(c[0].startswith(o) for o in a.only.split(','))]
    jobs = [(c, law, args, t0 + i * span // a.points + 7013 * i % 1024) for c, law, args, _ in C
            for i in range(a.points)]
    with ThreadPoolExecutor(a.jobs) as ex:
        res = list(ex.map(lambda j: dict(case=j[0], law=j[1], **run(exes[j[1]], j[2], j[3])), jobs))
    g = [c for c in C if c[0].startswith('gather_')][-1]
    neg = [dict(case='neg_corrupt_sector_scan', **run(exes[6], C[1][2], t0, 1)),
           dict(case='neg_corrupt_sector_gather', **run(exes[5], g[2], t0, 1)),
           dict(case='neg_trcd_check_plus_1ns_gather', **run(exes[5], g[2], t0, 2))]
    head = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    rec = dict(source_commit=head, host=os.uname().nodename,
               simulator=subprocess.run([VERILATOR, '--version'], capture_output=True, text=True).stdout.strip(),
               input_sha256={s: hashlib.sha256((ROOT / s).read_bytes()).hexdigest() for s in SOURCES + ['tools/dshbm_1m_hbm.py']},
               points=a.points, cases=res, negative=neg, pc_checker=bool(a.chk))
    Path(a.out).write_text(json.dumps(rec) + '\n')
    print('done', sum(r['verdict'] == 'PASS' for r in res), '/', len(res), [n['verdict'] for n in neg])


# ---------------------------------------------------------------------------------------------------------------
def summ(rows):
    ok = [r for r in rows if r['verdict'] == 'PASS']
    if not ok:
        return dict(cases=len(rows), passed=0)
    comp = sorted(r['complete_ns'] for r in ok)
    return dict(cases=len(rows), passed=len(ok), exact=len(ok) == len(rows),
                bytes_per_stack=ok[0]['bytes'], bytes_per_die=STACKS * ok[0]['bytes'],
                first_access_ns=dict(min=min(r['first_access_ns'] for r in ok), median=statistics.median(
                    r['first_access_ns'] for r in ok), max=max(r['first_access_ns'] for r in ok)),
                complete_ns=dict(min=comp[0], median=statistics.median(comp), max=comp[-1]),
                complete_cycles_1p2GHz=dict(median=math.ceil(statistics.median(comp) * 1.2),
                                            max=math.ceil(comp[-1] * 1.2)),
                steady_tbps_stack=dict(min=min(r['steady_tbps'] for r in ok),
                                       mean=round(statistics.mean(r['steady_tbps'] for r in ok), 4)),
                end_to_end_tbps_stack=dict(min=min(r['end_to_end_tbps'] for r in ok),
                                           mean=round(statistics.mean(r['end_to_end_tbps'] for r in ok), 4)),
                achieved_TBps_die_steady_min=round(STACKS * min(r['steady_tbps'] for r in ok), 4),
                fraction_of_peak_steady_min=round(min(r['steady_tbps'] for r in ok) / PEAK_STACK_TBPS, 4),
                fraction_of_peak_steady_mean=round(statistics.mean(r['steady_tbps'] for r in ok) / PEAK_STACK_TBPS, 4),
                fraction_of_peak_end_to_end_min=round(min(r['end_to_end_tbps'] for r in ok) / PEAK_STACK_TBPS, 4),
                dram_violations=sum(r.get('viol', 0) for r in rows), data_mismatches=sum(r.get('bad', 0) for r in rows),
                **({} if not any('pcchk_pcs' in r for r in rows) else dict(
                    pc_checker=dict(runs=sum('pcchk_pcs' in r for r in rows), pcs=sum(r.get('pcchk_pcs', 0) for r in rows),
                                    violations=sum(r.get('pcchk_viol', 0) for r in rows),
                                    refpb=sum(r.get('pcchk_ref', 0) for r in rows)))),
                activates_max=max(r['act'] for r in ok), refreshes_max=max(r['ref'] for r in ok))


TOKEN_DEP = {
    'scan': ('prefetchable at token start', 'key region = the die\'s position shard of keys 0..P-1, fixed before the '
             'token; only the query is token-dependent, so RDs can start before the query (scan_*_prefetch), but the '
             'scorer consumes them only after index_q, so the scan COMPLETION is on the path: charge max(stream from '
             'prefetch/notice case, scorer compute) after index_q'),
    'window': ('prefetchable at token start', '127 of the 128 window rows are positions < P, stored before the token; '
               'the newest row is produced in-layer (registers). The ROM charges its window load per layer in front of '
               'attention (worst of 64 refresh phases): the fair HBM term is window_prefetch/notice complete_ns max'),
    'gather': ('token-dependent: ON the path', 'rows = the merged top-512 of THIS token\'s index scores (op_merge then '
               'op_kv_gather); address known only after the 96 x 512 merge; the source die\'s read precedes its '
               'kv_gather transmit'),
    'engram': ('known at token start', 'hash ids = f(token history incl. the current token, which the previous '
               'token\'s head produced): the W19 program already keeps engram.* collectives off-path (OFF_PATH_COLL); '
               'charge 0 on the path if issued at token start (the row read completes long before L1)'),
    'embedding': ('token-dependent: ON the path at token start', 'row = embedding[current token id]; address known at '
                  'token start (the previous head\'s argmax); nothing to overlap it with before L0'),
}


def cmd_record(a):
    runs = json.loads(Path(a.runs).read_text())
    prep = json.loads(Path(a.prep).read_text())
    C = cases(prep)
    streams = {}
    for name, law, args, note in C:
        s = summ([r for r in runs['cases'] if r['case'] == name])
        kind = name.split('_')[0]
        dep = TOKEN_DEP[kind]
        streams[name] = dict(note=note, law=law, plusargs=args, clock_hz=1.2e9, controller_clock_ps=1024,
                             refpb_rule='corrected (main 54dcb2ab6 / c217afff7: tRFCpb same bank, tRREFD after ACT '
                                        'and after REFpb, each bank once a 32-REFpb round; checked on every command)',
                             token_dependence=dep[0], evidence=dep[1], ge90_steady=None, **s)
        if s.get('passed') and kind in ('scan', 'window', 'embedding'):
            streams[name]['ge90_steady'] = s['fraction_of_peak_steady_min'] >= 0.9
    # routed-expert fetch: sel90 is already post-REFpb (family_b re-run with ot_hbm_pc_dram_check, 852 runs 0 viol)
    fam = json.loads(gzip.open(ROOT / 'results/rtl/hbm_refpb_fix_20261004/family_b/expert_fetch_la_after.json.gz').read())
    f90 = json.loads((ROOT / 'results/rtl/dshbm_expert_fetch90_20261004/summary.json').read_text())
    chk = json.loads((ROOT / 'results/rtl/hbm_refpb_fix_20261004/family_b/expert_fetch_la.dramchk.json').read_text())
    after = fam['stats']['sel90_notice']
    before = f90['after']
    routed = dict(record='results/rtl/dshbm_expert_fetch90_20261004/summary.json (sel90)',
                  post_refpb_record='results/rtl/hbm_refpb_fix_20261004/family_b/expert_fetch_la_after.json.gz '
                                    '(sel90_notice, re-run after the REFpb fix, ot_hbm_pc_dram_check)',
                  dram_check=dict(runs=chk['runs'], viol=chk['viol']),
                  identical_after_refpb=(after['stream_tbs'] == before['stream_tbs_stack'] and
                                         after['first_access_ns'] == before['first_access_ns']),
                  stream_tbs_stack=after['stream_tbs'], first_access_ns=after['first_access_ns'],
                  fraction_of_peak_mean=after['stream_frac_of_peak_mean'],
                  fraction_of_peak_min=after['stream_frac_of_peak_min'],
                  per_token_fetch_us=f90['per_token']['after'], ge90_mean=after['stream_frac_of_peak_mean'] >= 0.9,
                  flag='min 0.81 of peak (4 of 6 experts in one bank set): below 90% in the worst case',
                  token_dependence='token-dependent (router output): ON the path, priced per layer as the fetch term')
    sm = weight_demand()
    head = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    below = [k for k, v in streams.items() if v.get('ge90_steady') is False]
    rec = dict(schema='opentallas.dshbm_1m.hbm_streams.v1', position=1048575, context=1048576,
               design='DS-V4.1 HBM accelerator, TP-96, 4 HBM3E stacks a die (4.0 TB/s peak)',
               minimum_component='one HBM3E stack (32 PCs, REFpb on schedule, refresh live); die = 4 identical stacks',
               bench='rtl/test/hbm_accel/tb_dshbm_1m_streams.sv on rtl/hbm_accel/service/ot_hbm_accel_expert_stream_pc.sv '
                     '(52ce3e9c1 r6 stream PC + notice) + ot_hbm_accel_cdc_fifo landing; ASSUMED path terms '
                     'PHY_CMD 5 ns + RSP 10 ns + NoC 5 ns (R5a bench)',
               metrics=dict(first_access='go (query / merge / token start) -> first sector at the consumer',
                            complete='go -> last sector at the consumer (the on-path time)',
                            steady='bytes / (first RD -> last RD burst end)',
                            end_to_end='bytes / complete'),
               exactness='every consumed sector compared with its stored pattern (distinct per sector), 0 DRAM timing '
                         'violations at the corrected REFpb rules; negative controls must FAIL',
               negative_controls=[dict(case=n['case'], verdict=n['verdict'], bad=n.get('bad'), viol=n.get('viol'))
                                  for n in runs['negative']],
               ckv_selection=prep, streams=streams, routed_expert_fetch=routed, sm_weight_stream=sm,
               default_on_path=dict(
                   notice=['scan_L20_notice', 'scan_L2_notice', 'window_notice'],
                   as_built=['gather_*_as_built', 'embedding_row_post_at_go'],
                   rule='owner >= 90 % bandwidth rule (2026-10-04): the index-key scans and the window rows are posted '
                        'with the static-schedule notice (the descriptors are known before the query); token-dependent '
                        'loads stay as built.  Composer: tools/dshbm_1m_allmeasured.py Hbm.MODE = "default"',
                   pc_checker='rtl/test/ot_hbm_pc_dram_check.sv bound into every PC when the run used --chk'),
               below_90pct=dict(streams=below, note='random-row gathers and single-row reads are latency-bound '
                                'by construction (a few sectors a PC): time, not bandwidth, is their measure'),
               run=dict(host=runs['host'], simulator=runs['simulator'], points=runs['points'],
                        source_commit=runs['source_commit']),
               input_sha256=runs['input_sha256'], record_tool_commit=head,
               record_tool_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
               note_tool='the run step executed the same case/run code; later edits touched only record/weight_demand')
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(rec, indent=1) + '\n')
    for k, v in streams.items():
        if v.get('passed'):
            print(f"{k:34s} B/die {v['bytes_per_die']:8d} first {v['first_access_ns']['max']:7.1f} "
                  f"complete med {v['complete_ns']['median']:7.1f} max {v['complete_ns']['max']:7.1f} ns  "
                  f"steady {v['fraction_of_peak_steady_min']:.3f}  e2e {v['fraction_of_peak_end_to_end_min']:.3f} "
                  f"exact {v['exact']}")
    print(json.dumps(sm['summary'], indent=1))


def weight_demand():
    """Bytes/s the measured SM schedule demands of the HBM per layer, against the measured sustained streams (static
    96.24% = 3.8496 TB/s a die, results/rtl/hbm_path_bandwidth_audit_20261004/dshbm_static_stream.json; routed sel90
    0.9134 x 4 TB/s), and a window-limited arrival check of the static stream (WINW 160 stream words of 98,304 B =
    15.7 MB ahead of consumption, ot_hbmacc_qwen_wstream default as run) against the measured per-layer timeline."""
    prog = json.loads((ROOT / 'results/rtl/dshbm_baseline_measured_20261004/program.json').read_text())
    meas = json.loads((ROOT / 'results/rtl/dshbm_baseline_measured_20261004/measured.json').read_text())
    lay_t = {str(x['layer']): x for x in meas['scenarios']['measured_target_clock']['layers']}
    ss = json.loads((ROOT / 'results/rtl/hbm_path_bandwidth_audit_20261004/dshbm_static_stream.json').read_text())
    static_tbs = ss['selected']['tbs_per_die']
    word_b = ss['bytes_per_die']['stream_bytes'] / ss['bytes_per_die']['stream_words']
    win_b = 160 * word_b
    fmt = {'fp4': 0.5 + 1 / 32, 'fp8': 1.0 + 1 / (128 * 128), 'bf16': 2.0}
    head_us = lay_t['head']['total_us']
    rows, t, need_cum, stall, stall_ss = [], 0.0, 0.0, 0.0, 0.0
    for lay in prog['layers']:
        st = rt = 0.0
        for op in lay['ops']:
            if op['kind'] == 'mv':
                r0, r1 = op['rows'][0]
                b = (r1 - r0) * op['k'] * fmt[op['fmt']]
                if op['tag'].startswith('expert slot') and 'slot 6' not in op['tag']:
                    rt += b
                else:
                    st += b
        L = lay['layer']
        x = lay_t[str(L)] if str(L) in lay_t else lay_t['head']
        sm_us = x['us']['sm']
        # static stream: landed by layer start = min(rate x t, consumed-before + window); pessimistic: all of the
        # layer's static bytes needed at the layer's start
        avail = min(static_tbs * 1e12 * t * 1e-6, need_cum + win_b)
        short = max(0.0, need_cum + st - avail)
        stall_l = short / (static_tbs * 1e12) * 1e6
        stall += stall_l
        # steady decode: the static stream is token-independent, so the next token's words enter the window while
        # this token's head runs (the head's words leave the window as it consumes them): start head_us earlier
        avail_ss = min(static_tbs * 1e12 * (t + head_us) * 1e-6, need_cum + win_b)
        stall_ss += max(0.0, need_cum + st - avail_ss) / (static_tbs * 1e12) * 1e6
        rows.append(dict(layer=L, static_bytes=round(st), routed_bytes=round(rt), sm_us=sm_us,
                         demand_TBps_during_sm=round((st + rt) / (sm_us * 1e-6) / 1e12, 3) if sm_us else None,
                         static_arrival_stall_us=round(stall_l, 3)))
        need_cum += st
        t += x['total_us']
    by_type = {}
    kinds = {r['layer']: r['kind'] for r in json.loads((ROOT / 'results/rtl/dshbm_baseline_measured_20261004/execute.json')
                                                       .read_text())['layers']}
    for r in rows:
        k = kinds.get(r['layer'], 'head')
        d = by_type.setdefault(k, dict(layers=[], demand_TBps_max=0.0))
        d['layers'].append(r['layer'])
        d['demand_TBps_max'] = max(d['demand_TBps_max'], r['demand_TBps_during_sm'] or 0)
    return dict(sustained_static_TBps_die=static_tbs, sustained_routed_TBps_die_mean=round(4 * 0.9134, 4),
                window_bytes=round(win_b), per_layer=rows, by_type=by_type,
                summary=dict(total_static_arrival_stall_us=round(stall, 3),
                             cold_first_token_stall_us=round(stall, 3),
                             steady_decode_stall_us=round(stall_ss, 3),
                             steady_rule='next token streams from this token\'s head start (window 15.7 MB)',
                             head_total_us=head_us,
                             max_demand_TBps=max(r['demand_TBps_during_sm'] or 0 for r in rows),
                             note='demand during SM-busy exceeds the sustained stream only where the SMs run a '
                                  'layer\'s matvecs faster than the HBM can deliver them; the static stream runs '
                                  'ahead (prefetch window) so the composer charges only the steady_decode_stall_us '
                                  '(cold_first_token_stall_us for a first token); routed experts are the fetch term (sel90)'))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('step', choices=('prep', 'run', 'record'))
    ap.add_argument('--out', required=True)
    ap.add_argument('--work', type=Path)
    ap.add_argument('--prep')
    ap.add_argument('--runs')
    ap.add_argument('--jobs', type=int, default=32)
    ap.add_argument('--points', type=int, default=64)
    ap.add_argument('--chk', action='store_true', help='bind rtl/test/ot_hbm_pc_dram_check.sv into every PC')
    ap.add_argument('--only', default='', help='run only cases with these name prefixes (comma list)')
    a = ap.parse_args(argv)
    {'prep': cmd_prep, 'run': cmd_run, 'record': cmd_record}[a.step](a)


if __name__ == '__main__':
    main()
