"""DS-V4.1 HBM accelerator: per-token KV + index-key WRITE-BACK at 1M (position 1,048,575), one HBM3E stack (RTL,
Verilator).

Unit rtl/hbm_accel/service/ot_hbm_accel_dskv_wb.sv (default-off) on the write-capable stream PC
rtl/hbm_accel/service/ot_hbm_accel_stream_pc_wb.sv (WB_EN default 0 = the r6 + notice stream PC), bench
rtl/test/hbm_accel/tb_hbm_accel_dskv_wb.sv.  The written bytes are the GOLDEN rows of the W17 1M reference
(/home/ubuntu/w17work/ref/ctx1048576_seed20260930: win<L>, ckv<L>, ik<L>) packed to their HBM storage formats by
tools/rtl_v41_fullshape_layer_campaign.py (window FP8 E4M3 + UE8M0 / 32 = 528 B, compressed row FP4 E2M1 + E4M3 / 16
= 288 B, index key FP4 E2M1 + UE8M0 / 32 = 68 B; each packer asserts an exact round trip).  This script computes
the stack's expected writes with an INDEPENDENT Python copy of the address map; the bench compares the DRAM array
and a read-back through the stream PCs with them.

    python3 tools/hbm_accel_dskv_wb.py --work DIR --out RECORD.json [--jobs N] [--points 32]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import statistics
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
VERILATOR = os.environ.get('VERILATOR', str(Path.home() / '.local/opentallas-tools/verilator-5.050/bin/verilator'))
SOURCES = ['rtl/hbm_accel/service/ot_hbm_accel_cdc_fifo.sv',
           'rtl/hbm_accel/service/ot_hbm_accel_stream_pc_wb.sv',
           'rtl/hbm_accel/service/ot_hbm_accel_dskv_wb.sv',
           'rtl/test/hbm_accel/tb_hbm_accel_dskv_wb.sv']
TOP = 'tb_hbm_accel_dskv_wb'
REF = Path('/home/ubuntu/w17work/ref/ctx1048576_seed20260930')
POS = 1_048_575
TP, KEY_BLOCK = 96, 8
WIN_ROW0, CKV_ROW0, KEY_ROW0, SLOT_ROWS = 2000, 3000, 4000, 2       # the unit's default parameters
SRC_LAYERS = [2, 8, 14, 20, 24, 28, 32, 36]                         # index_source_layer_ids
RATIO = {L: (1 if L >= 20 else 2) for L in SRC_LAYERS}               # compress ratio (L2/8/14: 2; L20..36: 1)
CYC_PS, T_BG, INJ_AFTER_BG = 1024, 5_000_000, 300_000
NBG = 1024                                                           # background sectors a PC (1 MiB a stack)


def pat(pc, bk, rw, cl):
    m = 0xFFFFFFFF
    w = ((pc * 0x9E3779B1 + bk * 0x85EBCA77 + rw * 0xC2B2AE3D + cl * 0x27D4EB2F) & m) ^ 0xA5A5A5A5
    return w.to_bytes(4, 'little') * 8


def sector_addr(kind, slot, j):
    """PC-local sector j of (kind, slot) -> (bank, row, col): the stream PC's j order."""
    row = (WIN_ROW0, CKV_ROW0, KEY_ROW0)[kind] + slot * SLOT_ROWS + (j >> 10)
    return ((j >> 7) & 7) * 4 + (j & 3), row, (j >> 2) & 31


def owner_k(pos, r2):
    n = pos >> 1 if r2 else pos
    b = n >> 3
    return b % TP, (b // TP) * KEY_BLOCK + (n & 7), n


def golden_rows(L):
    from rtl_v41_fullshape_layer_campaign import pack_fp4_e4m3, pack_fp4_ue8m0, pack_fp8_ue8m0
    z = np.load(REF / f'ctx{POS + 1}_L{L:02d}.npz')
    c, s = pack_fp8_ue8m0(z[f'win{L}'][None, :])
    win = bytes(c[0]) + bytes(s[0])
    out = dict(win=win)
    if L in SRC_LAYERS:
        n, sc = pack_fp4_e4m3(z[f'ckv{L}'][None, :])
        out['ckv'] = bytes(n[0]) + bytes(sc[0])
        n2, s2 = pack_fp4_ue8m0(z[f'ik{L}'][None, :])
        out['key'] = bytes(n2[0]) + bytes(s2[0])
    assert len(win) == 528 and len(out.get('ckv', b'x' * 288)) == 288 and len(out.get('key', b'x' * 68)) == 68
    return out


def plan(L, die, pos=POS):
    """Rows the die feeds the unit at layer L, the shadow it holds, and every sector it writes (all stacks)."""
    g = golden_rows(L)
    rows, shadow, writes = [], [], []          # writes: (stack, pc, bank, row, col, data32)
    w = pos % 128
    data = g['win'] + bytes(16)
    rows.append((0, L, 0, data))
    for t in range(17):
        writes.append((w >> 5, w & 31, *sector_addr(0, L, t), data[32 * t:32 * t + 32], 'window'))
    if L in SRC_LAYERS:
        slot, r2 = SRC_LAYERS.index(L), RATIO[L] == 2
        own, k, n = owner_k(pos, r2)
        rows.append((1, slot, int(r2), g['ckv'] + bytes(256)))
        rows.append((2, slot, int(r2), g['key'] + bytes(476)))
        if own == die:
            for t in range(9):
                S = 9 * k + t
                writes.append((S % 128 >> 5, S % 32, *sector_addr(1, slot, S >> 7), g['ckv'][32 * t:32 * t + 32], 'ckv'))
            # the open key block: earlier keys' bytes are the DRAM background (what HBM holds), new key merged
            kb = 17 * (k >> 3)
            blk = bytearray()
            for t in range(17):
                S = kb + t
                blk += pat(S % 32, *sector_addr(2, slot, S >> 7))
            shadow.append((slot, bytes(blk)))
            i = n & 7
            blk[68 * i:68 * i + 68] = g['key']
            for S in range((68 * k) >> 5, ((68 * k + 67) >> 5) + 1):
                t = S - kb
                writes.append((S % 128 >> 5, S % 32, *sector_addr(2, slot, S >> 7), bytes(blk[32 * t:32 * t + 32]), 'key'))
    return rows, shadow, writes, g


def hx(b):
    return format(int.from_bytes(b, 'little'), 'x')


def write_inputs(d, L, die, stack):
    rows, shadow, writes, g = plan(L, die)
    d.mkdir(parents=True, exist_ok=True)
    (d / 'rows.txt').write_text(''.join(f'{k} {s} {r} {hx(b)}\n' for k, s, r, b in rows))
    (d / 'shadow.txt').write_text(''.join(f'{s} {hx(b)}\n' for s, b in shadow))
    mine = [w for w in writes if w[0] == stack]
    (d / 'exp.txt').write_text(''.join(f'{pc} {bk} {rw} {cl} {hx(b)}\n' for _, pc, bk, rw, cl, b, _ in mine))
    return dict(layer=L, die=die, stack=stack, sectors_die=len(writes), sectors_stack=len(mine),
                kinds_stack=sorted({w[6] for w in mine}),
                bytes_written_die=len(writes) * 32,
                golden_sha256={k: hashlib.sha256(v).hexdigest() for k, v in g.items()})


def build(work, stack):
    d = work / f'stack{stack}'
    exe = d / f'V{TOP}'
    if exe.exists():
        return exe
    cmd = [VERILATOR, '--binary', '--timing', '-Wno-fatal', '-Wno-WIDTH', '-j', '8', '-O2', '--top-module', TOP,
           '--Mdir', str(d), f'-GSTACK={stack}'] + [str(ROOT / s) for s in SOURCES]
    d.mkdir(parents=True, exist_ok=True)
    with open(work / f'build_stack{stack}.log', 'w') as log:
        subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT, check=True)
    return exe


def run(exe, inp, die, t_bg, nbg=NBG, nowb=0, mut=0):
    t_inj = t_bg + INJ_AFTER_BG
    argv = [str(exe), f'+rows={inp}/rows.txt', f'+shadow={inp}/shadow.txt', f'+exp={inp}/exp.txt', f'+pos={POS}',
            f'+die={die}', f'+t_inj_ps={t_inj}', f'+nbg={nbg}', f'+nowb={nowb}', f'+mut={mut}']
    # the bench's background starts at its fixed t_bg (5 us); shift both by moving the REFpb phase instead
    argv.append(f'+t_bg_ps={t_bg}')
    out = subprocess.run(argv, capture_output=True, text=True, check=False).stdout
    wb = [l for l in out.splitlines() if l.startswith('WB ')]
    if len(wb) < 2:
        return dict(verdict='FAIL', raw=out[-2000:], t_bg=t_bg, nbg=nbg, nowb=nowb, mut=mut)
    rec = {k: int(v) for k, v in re.findall(r'(\w+)=(-?\d+)', wb[0])}
    rec.update(verdict=wb[1].split('=')[1], t_bg=t_bg, raw_viol=[l for l in out.splitlines() if 'VIOLATION' in l][:3])
    return rec


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--work', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--jobs', type=int, default=16)
    ap.add_argument('--points', type=int, default=32)
    ap.add_argument('--compose', type=Path, help='write the successor DS HBM measured composition here and stop')
    a = ap.parse_args(argv)
    if a.compose:
        return compose(a.out, a.compose)
    if a.out.exists():
        raise SystemExit('fresh record path required')
    a.work.mkdir(parents=True, exist_ok=True)
    # cases: (name, layer, die, stack).  At 1,048,575 ratio-1 groups (L20/24/28/32/36) close on die 31 and
    # ratio-2 groups (L2/8/14) on die 63 (both compressors close: pos + 1 is even); every die writes window rows.
    cases = [('L20_owner_stack1_ckv_key', 20, 31, 1), ('L20_owner_stack3_window', 20, 31, 3),
             ('L20_owner_stack0_none', 20, 31, 0),
             ('L2_owner_stack0_ckv', 2, 63, 0), ('L2_owner_stack2_key', 2, 63, 2), ('L2_owner_stack3_window', 2, 63, 3),
             ('L20_nonowner_die0_stack3_window', 20, 0, 3), ('L39_window_stack3', 39, 5, 3)]
    inputs = {}
    for name, L, die, st in cases:
        inputs[name] = write_inputs(a.work / 'in' / name, L, die, st)
    with ThreadPoolExecutor(4) as ex:
        exes = dict(zip(range(4), ex.map(lambda s: build(a.work, s), range(4))))
    span = 118 * 32 * CYC_PS                              # one 32-command REFpb round
    pts = [T_BG + i * span // a.points + 7013 * i % 1024 for i in range(a.points)]
    jobs = []
    for name, L, die, st in cases:
        for t in pts:
            jobs += [(name, 'bg_wb', dict(t_bg=t)), (name, 'bg_nowb', dict(t_bg=t, nowb=1)),
                     (name, 'idle_wb', dict(t_bg=t, nbg=0))]
    negs = [('L20_owner_stack1_ckv_key', 'neg_corrupt_dram_after_fence', dict(t_bg=T_BG, mut=1)),
            ('L20_owner_stack3_window', 'neg_fence_skipped', dict(t_bg=T_BG, nbg=0, mut=2)),
            ('L20_owner_stack1_ckv_key', 'neg_fence_skipped', dict(t_bg=T_BG, nbg=0, mut=2)),
            ('L20_owner_stack1_ckv_key', 'neg_row_bit_flip', dict(t_bg=T_BG, mut=3)),
            ('L20_owner_stack3_window', 'neg_trcdwr_check_plus_1ns', dict(t_bg=T_BG, nbg=0, mut=4))]
    by = {c[0]: c for c in cases}

    def go(j):
        name, var, kw = j
        _, L, die, st = by[name]
        return dict(case=name, variant=var, **run(exes[st], a.work / 'in' / name, die, **kw))
    with ThreadPoolExecutor(a.jobs) as ex:
        res = list(ex.map(go, jobs + negs))
    main_res, neg_res = res[:len(jobs)], res[len(jobs):]
    stats = {}
    for name, L, die, st in cases:
        rr = {v: [r for r in main_res if r['case'] == name and r['variant'] == v] for v in ('bg_wb', 'bg_nowb', 'idle_wb')}
        ok = all(r['verdict'] == 'PASS' for v in rr.values() for r in v)
        s = dict(layer=L, die=die, stack=st, **{k: inputs[name][k] for k in ('sectors_stack', 'kinds_stack', 'sectors_die')},
                 cases=sum(len(v) for v in rr.values()), passed=sum(r['verdict'] == 'PASS' for v in rr.values() for r in v),
                 viol=sum(r.get('viol', 0) for v in rr.values() for r in v),
                 bad=sum(r.get('bad', 0) + r.get('dram_bad', 0) for v in rr.values() for r in v))
        if ok:
            pair = [(w, n) for w in rr['bg_wb'] for n in rr['bg_nowb'] if w['t_bg'] == n['t_bg']]
            d = [w['bg_last'] - n['bg_last'] for w, n in pair]
            s['background_stream'] = dict(
                bytes=32 * 32 * NBG, nowb_ns_mean=round(statistics.mean(n['bg_last'] for _, n in pair) / 1000, 3),
                nowb_e2e_tbps_min=round(32 * 32 * NBG / max(n['bg_last'] for _, n in pair), 4),   # B / ps = TB/s
                wb_e2e_tbps_min=round(32 * 32 * NBG / max(w['bg_last'] for w, _ in pair), 4),
                delta_ns_mean=round(statistics.mean(d) / 1000, 3), delta_ns_max=round(max(d) / 1000, 3),
                delta_ns_min=round(min(d) / 1000, 3))
            for v in ('bg_wb', 'idle_wb'):
                xs = [r for r in rr[v] if r['exp_wr'] > 0]
                if xs:
                    s[f'fence_{v}'] = dict(fence_ns_mean=round(statistics.mean(r['fence'] for r in xs) / 1000, 3),
                                           fence_ns_max=round(max(r['fence'] for r in xs) / 1000, 3),
                                           last_wr_ns_max=round(max(r['wr_last'] for r in xs) / 1000, 3))
        stats[name] = s
    git = lambda *c: subprocess.run(['git', *c], cwd=ROOT, capture_output=True, text=True).stdout.strip()  # noqa: E731
    me = 'tools/hbm_accel_dskv_wb.py'
    rec = dict(schema='opentallas.hbm_accel.dskv_writeback_1m.v1', source_commit=git('rev-parse', 'HEAD'),
               source_dirty=bool(git('status', '--porcelain', '--', *SOURCES, me)),
               input_sha256={s: hashlib.sha256((ROOT / s).read_bytes()).hexdigest() for s in SOURCES + [me]},
               simulator=subprocess.run([VERILATOR, '--version'], capture_output=True, text=True).stdout.strip(),
               host=os.uname().nodename, position=POS, golden=str(REF),
               controller_clock_ps=CYC_PS, peak_stack_tbps=1.0,
               assumed_path_ns=dict(write_request_noc_plus_phy=10.0, ack_phy_cmd=5.0, ack_rsp=10.0, ack_noc=5.0,
                                    note='R5a bench path terms; ACK = WR + PHY_CMD + CWL + BL8 + RSP + NOC'),
               inputs=inputs, stats=stats,
               negative_controls=[dict(case=n['case'], variant=n['variant'], verdict=n['verdict'], bad=n.get('bad'),
                                       dram_bad=n.get('dram_bad'), viol=n.get('viol')) for n in neg_res],
               cases=main_res + neg_res)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(rec, indent=1) + '\n')
    print(json.dumps(dict(stats=stats, negative=rec['negative_controls']), indent=1))


BASE = 'results/rtl/dshbm_baseline_measured_20261004/measured.json'
AUDIT = 'results/rtl/hbm_path_bandwidth_audit_20261004/summary.json'


def compose(rtl_path, out):
    """Successor of the DS HBM measured composition (main 75b6fe4fd) with the KV write-back term added."""
    if out.exists():
        raise SystemExit('fresh composition path required')
    rtl = json.loads(Path(rtl_path).read_text())
    base = json.loads((ROOT / BASE).read_text())
    audit = json.loads((ROOT / AUDIT).read_text())['dshbm_token']
    st = rtl['stats']
    win, ck1 = st['L20_owner_stack3_window'], st['L20_owner_stack1_ckv_key']
    ck2c, ck2k = st['L2_owner_stack0_ckv'], st['L2_owner_stack2_key']
    assert all(v['passed'] == v['cases'] and v['viol'] == 0 and v['bad'] == 0 for v in st.values())
    assert all(n['verdict'] == 'FAIL' for n in rtl['negative_controls'])
    n_win, n_r1, n_r2 = 40, 5, 3                       # window rows a token; ratio-1 / ratio-2 source layers
    by_die = {'die31_owner_ratio1': n_win * 544 + n_r1 * (288 + 96), 'die63_owner_ratio2': n_win * 544 + n_r2 * (288 + 96),
              'other_94_dies': n_win * 544}
    fence_max = max(v[f] ['fence_ns_max'] for v in (win, ck1, ck2c, ck2k) for f in ('fence_bg_wb', 'fence_idle_wb'))
    # stream interference: every window row of the token lands on PC (pos mod 128) of stack 3 (40 events);
    # the owner's compressed row + key on stack 1 (die 31, 5 events) / stacks 0 + 2 (die 63, 3 events)
    per_stack_us = {
        'stack3_window_40': dict(mean=round(n_win * win['background_stream']['delta_ns_mean'] / 1000, 3),
                                 worst=round(n_win * win['background_stream']['delta_ns_max'] / 1000, 3)),
        'stack1_ckv_key_5_die31': dict(mean=round(n_r1 * ck1['background_stream']['delta_ns_mean'] / 1000, 3),
                                       worst=round(n_r1 * ck1['background_stream']['delta_ns_max'] / 1000, 3)),
        'stack0_ckv_3_die63': dict(mean=round(n_r2 * ck2c['background_stream']['delta_ns_mean'] / 1000, 3),
                                   worst=round(n_r2 * ck2c['background_stream']['delta_ns_max'] / 1000, 3)),
        'stack2_key_3_die63': dict(mean=round(n_r2 * ck2k['background_stream']['delta_ns_mean'] / 1000, 3),
                                   worst=round(n_r2 * ck2k['background_stream']['delta_ns_max'] / 1000, 3))}
    stream_add_worst = max(v['worst'] for v in per_stack_us.values())
    stream_add_mean = max(v['mean'] for v in per_stack_us.values())
    after = audit['after']
    hbm_active_wb = after['hbm_active_us'] + stream_add_worst
    head_us = base['representative_layers']['head']['measured_total']
    token = base['headline']['measured_total_us']
    exposed_fence_us = max(0.0, fence_max / 1000 - head_us)
    hidden = hbm_active_wb < after['sm_busy_us']
    delta_us = (0.0 if hidden else hbm_active_wb - after['sm_busy_us']) + exposed_fence_us
    upper_us = stream_add_worst + fence_max / 1000
    rec = dict(
        schema='opentallas.rtl.dshbm_measured_composition.kv_writeback.v1',
        successor_of=dict(record=BASE, main='75b6fe4fd', note='not overwritten; this row adds the KV write-back term'),
        position=POS, rtl_record=str(rtl_path), rtl_source_commit=rtl['source_commit'],
        write_back=dict(
            what='per token: window row of every layer on every die (528 B -> 17 sectors at ring slot pos mod 128 = '
                 'one PC); compressed row (288 B, 9 sectors over 9 PCs) + index key (68 B packed, 2-3 whole sectors '
                 'merged with the open key block shadow) on the owner die of every closing index-source layer',
            owners_at_pos=dict(ratio1_layers_20_24_28_32_36='die 31', ratio2_layers_2_8_14='die 63 (group close: pos+1 even)'),
            bytes_per_token_by_die=by_die,
            audit_estimate_bytes=23968,
            exact='768/768 PASS: golden W17 rows written through the RTL unit + PCs, DRAM array and stream read-back '
                  'equal to golden bytes (untouched sectors equal to background), 0 DRAM timing violations incl. write '
                  'rules; negatives FAIL: corrupt DRAM sector, fence skipped (stale read), row bit flip, tRCDWR +1 ns',
            fence_ns_max=round(fence_max, 3),
            fence_note='posted-write ACK count == issued; worst case is a write held behind a REFpb (tRFCpb 200 ns) '
                       'on its bank'),
        token_critical_path=dict(
            sm_wait_us=0.0, sm_wait_note='rows are posted to the unit (1-cycle handshake); no SM waits on a write',
            stream_interference_us_per_stack=per_stack_us,
            stream_interference_worst_us=round(stream_add_worst, 3), stream_interference_mean_us=round(stream_add_mean, 3),
            hbm_active_us=dict(before=after['hbm_active_us'], after_worst=round(hbm_active_wb, 3),
                               sm_busy=after['sm_busy_us'], hidden=hidden),
            fence_slack_us=head_us,
            fence_slack_note='the latest write (layer 39 window row) must be visible before token t+1 reads layer 39; '
                             'token t+1 cannot read before token t\'s head (measured 4.379 us) ends, and earlier layers '
                             'have a full token of slack',
            exposed_fence_us=round(exposed_fence_us, 3),
            token_delta_us=round(delta_us, 3),
            upper_bound_if_all_serial_us=round(upper_us, 3),
            upper_bound_pct_of_token=round(100 * upper_us / token, 3)),
        token=dict(before_us=token, after_us=round(token + delta_us, 3),
                   tokens_s_before=base['headline']['measured_tokens_s'],
                   tokens_s_after=(base['headline']['measured_tokens_s'] if delta_us == 0
                                   else round(1e6 / (token + delta_us), 1)),
                   routed_expert_term='unchanged from the HBM-path audit (fetch measured 5.446 mean / 6.056 worst us vs '
                                      'model 5.33; +0.116 / +0.726 us), not folded here'),
        default_off=dict(unit='ot_hbm_accel_dskv_wb ENABLE=0 ties every output to 0; nothing pinned instantiates it',
                         pc='ot_hbm_accel_stream_pc_wb WB_EN=0: tb_hbm_accel_dskv_stream (the audit bench) with the PC '
                            'swapped prints byte-identical BW lines to ot_hbm_accel_expert_stream_pc on 4 cases (scan '
                            'L20 refactor+prefetch, scan L2 as built, gather 2 rows + notice, scan nk 16), 2026-10-04',
                         pinned_files='none changed (new files only)'),
        unvalidated=['write-request / ACK path terms (10 ns each way, R5a bench values)',
                     'one stack simulated; die = 4 independent stacks (sectors sharded by address)',
                     'background stream on the r6 + notice stream PC policy (the r14 static stream PC with WR_EN=0 is '
                     'the same read policy); interference composed per event, not one 47.7-us stream run',
                     'open-key-block shadow priming at block open (one 544-B HBM read per source slot per 8 groups) '
                     'not simulated'])
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rec, indent=1) + '\n')
    print(json.dumps(rec['token_critical_path'], indent=1), json.dumps(rec['token'], indent=1))


if __name__ == '__main__':
    main()
