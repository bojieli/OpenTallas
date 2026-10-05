#!/usr/bin/env python3
"""DS ROM HBM load paths at the 1M target (HBM path audit 2026-10-04): minimum-component benches.

  window   tb_dsrom_window_load_bw: one die's 128-row packed WINDOW load from one stack, as built
           (ot_chip_v41x_window_kv_prefetch, REFILL_CREDITS 1/8/16) vs ot_dsrom_window_stream_la, 64 refresh phases.
  cand     tb_dsrom_idx_cand_gather_bw: a re-index layer's candidate-key read (golden 1M candidate set, rank r,
           each of its four stacks = one quarter of the rank's positions) with ot_dsrom_hbm_list_gather_la.

    python3 tools/dsrom_hbm_path_audit.py window --work DIR --out JSON
    python3 tools/dsrom_hbm_path_audit.py cand --work DIR --out JSON --cand ctx1048576_cand.npz
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERILATOR = os.environ.get('VERILATOR', str(Path.home() / '.local/opentallas-tools/verilator-5.050/bin/verilator'))
HBM = 'rtl/hdc/v41x/ot_hdc_v41x_idx_hbm.sv'
WIN_SRC = [HBM, 'rtl/chip/ot_chip_v41x_window_kv_prefetch.sv', 'rtl/chip/ot_chip_v41x_window_row_codec.sv',
           'rtl/chip/ot_chip_v41x_window_stage4.sv', 'rtl/chip/ot_dsrom_window_stream_la.sv',
           'rtl/test/tb_dsrom_window_load_bw.sv']
CAND_SRC = [HBM, 'rtl/chip/ot_dsrom_hbm_list_gather_la.sv', 'rtl/test/tb_dsrom_idx_cand_gather_bw.sv']
CLK_PS = 833
PEAK_STACK_TBPS = 32 * 32 / 1.024 / 1000          # 1.0 TB/s
TREFI_CYC = 3_900_000 // CLK_PS                    # one refresh interval of start phases


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def build(work, top, srcs, params, name):
    d = work / name
    exe = d / f'V{top}'
    if not exe.exists():
        d.mkdir(parents=True, exist_ok=True)
        cmd = [VERILATOR, '--binary', '--timing', '-Wno-fatal', '-Wno-WIDTH', '-Wno-UNOPTFLAT', '-j', '4', '-O2',
               '--top-module', top, '--Mdir', str(d)] + [f'-G{k}={v}' for k, v in params.items()] + \
              [str(ROOT / s) for s in srcs]
        with open(d.parent / f'{name}.build.log', 'w') as log:
            subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT, check=True)
    return exe


def kv(line):
    out = {}
    for k, v in re.findall(r'(\w+)=(-?[\d.]+)', line):
        out[k] = float(v) if '.' in v else int(v)
    return out


def run(exe, args):
    o = subprocess.run([str(exe)] + args, capture_output=True, text=True).stdout
    bw = [l for l in o.splitlines() if l.startswith('BW ')]
    ver = [l for l in o.splitlines() if l.startswith('VERDICT ')]
    r = kv(bw[-1]) if bw else {}
    r['verdict'] = ver[-1].split()[1] if ver else 'FAIL'
    if not bw:
        r['raw'] = o[-1500:]
    return r


def stats(rows, key='cycles'):
    v = sorted(r[key] for r in rows)
    return dict(n=len(v), min=v[0], median=v[len(v) // 2], p90=v[int(len(v) * 0.9)], max=v[-1],
                mean=round(sum(v) / len(v), 1))


def cmd_window(a):
    work = a.work.resolve()
    arms = [('asbuilt_c1', dict(MODE=0, CREDITS=1)), ('asbuilt_c8', dict(MODE=0, CREDITS=8)),
            ('asbuilt_c16', dict(MODE=0, CREDITS=16)), ('stream_la', dict(MODE=1))]
    with ThreadPoolExecutor(4) as ex:
        exes = dict(zip([n for n, _ in arms], ex.map(lambda x: build(work, 'tb_dsrom_window_load_bw', WIN_SRC,
                                                                        x[1], x[0]), arms)))
    phases = [5000 + i * TREFI_CYC // 64 + (i * 37) % 11 for i in range(64)]
    res = {}
    with ThreadPoolExecutor(a.jobs) as ex:
        res['stream_la'] = list(ex.map(lambda t: run(exes['stream_la'], [f'+t0={t}']), phases))
        for n in ('asbuilt_c1', 'asbuilt_c8', 'asbuilt_c16'):
            res[n] = list(ex.map(lambda t: run(exes[n], [f'+t0={t}']), phases[:4]))
    summ = {}
    for n, rows in res.items():
        ok = all(r['verdict'] == 'PASS' and r.get('bad', 1) == 0 and r.get('fault', 1) == 0 for r in rows)
        st = stats(rows)
        nsect, nbytes = rows[0]['sectors'], rows[0]['bytes']
        first = stats(rows, 'first_rsp_cycles')
        summ[n] = dict(exact=ok, phases=len(rows), cycles=st, first_access_cycles=first,
                       us_median=round(st['median'] * CLK_PS / 1e6, 4), us_max=round(st['max'] * CLK_PS / 1e6, 4),
                       tbps_median=round(nbytes / (st['median'] * CLK_PS * 1e-12) / 1e12, 4),
                       tbps_worst=round(nbytes / (st['max'] * CLK_PS * 1e-12) / 1e12, 4),
                       frac_peak_median=round(nbytes / (st['median'] * CLK_PS * 1e-12) / 1e12 / PEAK_STACK_TBPS, 4),
                       sustained_after_first_access_frac=round(
                           nsect / (st['median'] - first['median']) / (32 * CLK_PS / 1024), 4),
                       sectors=nsect, bytes=nbytes)
    rec = dict(schema='opentallas.dsrom.hbm_path.window_load.v1', **provenance(WIN_SRC), clk_ps=CLK_PS,
               peak_stack_tbps=PEAK_STACK_TBPS, scope='one die, one layer, 128 packed WINDOW rows x 17 sectors '
               '(544-B pitch) from one HBM3E stack (32 PCs) on the timed refresh-live model ot_hdc_v41x_idx_hbm '
               '(QD 64, RQD 32, RW 16, MAXSKIP 16, REFPB 3, 10 ns controller+PHY each way), absolute rows '
               '1,048,448..1,048,575 (the 1M token)', summary=summ, runs=res)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(rec, indent=1) + '\n')
    print(json.dumps(summ, indent=1))


def group_major_addr(base_block, g, j, hashed):
    """GROUP-MAJOR layout (re-index layers' own index keys): 8-key group g (its 16 code sectors then the
    sector of its 8 x 4 B scales, 17 sectors) lives on ONE pseudo-channel p, PC-local sectors 17k..17k+16
    (k = g div 32), PC-local sector j -> (row, bank, column, BG) with the column fastest, so a group opens 4
    banks (one per bank group) instead of 16.  Inverse of the stack map: x = p ^ col ^ (s >> 12)."""
    p = (g * 0x9E3779B1 >> 7) % 32 if hashed else g % 32
    jj = (g // 32) * 17 + j
    bg, c = jj % 4, jj // 4
    col, rest = c % 32, c // 32
    bk, row = rest % 8, rest // 8
    hi = (base_block * 128) >> 15                     # row-region offset of the layer's area
    row += hi
    s_hi = (row << 15) | (bk << 12)
    x = (p ^ col ^ (s_hi >> 12)) & 31
    s = s_hi | (col << 7) | (x << 2) | bg
    assert ((s >> 2) ^ (s >> 7) ^ (s >> 12)) & 31 == p
    return s


def cand_lists(cand_npz, rank, base_block, layout='w11'):
    """Per stack (quarter of the rank's positions) request list: per 8-key group, four code columns + one
    scale sector, the W11 key layout (1,024-key superblock = scale block + 16 code blocks of 64 keys)."""
    import numpy as np
    c = np.flatnonzero(np.load(cand_npz)['cand'])
    per = 1048576 // 4
    lists = []
    for q in range(4):
        lo = rank * per + q * per // 4
        hi = lo + per // 4
        mine = c[(c >= lo) & (c < hi)] - lo
        groups = sorted(set(int(x) // 8 for x in mine))
        reqs, off = [], 0
        for g in groups:
            if layout != 'w11':
                j = 0
                while j < 17:                                  # requests split at 4-sector chunk boundaries
                    a0 = group_major_addr(base_block, g, j, layout == 'group_hash')
                    n = min(4 - (a0 & 3), 17 - j)
                    reqs.append((a0, n, off)); off += n; j += n
                continue
            w0 = g * 8
            sb, w = divmod(w0, 1024)
            cb = base_block + sb * 17 + 1 + w // 64
            s0 = cb * 128 + (w % 64) * 2
            for j in range(4):
                reqs.append((s0 + 4 * j, 4, off)); off += 4
            reqs.append(((base_block + sb * 17) * 128 + w // 8, 1, off)); off += 1
        # issue order: w11 keeps key order (a group's 5 requests are on distinct PCs); the group-major layouts
        # put a group's requests on ONE PC, so they are issued round robin over the PCs (k-th request of every
        # PC, then the (k+1)-th) to keep the in-order IW-wide issue from blocking on one PC
        if layout == 'w11':
            lists.append(dict(stack=q, keys=int(len(mine)), groups=len(groups), requests=reqs, sectors=off))
            continue
        pcq = {}
        for r in reqs:
            pcq.setdefault(((r[0] >> 2) ^ (r[0] >> 7) ^ (r[0] >> 12)) & 31, []).append(r)
        order = [q_[k] for k in range(max(len(v) for v in pcq.values())) for _, q_ in sorted(pcq.items())
                 if k < len(q_)]
        lists.append(dict(stack=q, keys=int(len(mine)), groups=len(groups), requests=order, sectors=off))
    return lists


LAYOUTS = ('w11', 'group_mod', 'group_hash')


def cmd_cand(a):
    work = a.work.resolve()
    exe = build(work, 'tb_dsrom_idx_cand_gather_bw', CAND_SRC, {}, 'cand')
    jobs = []
    for rank in range(4):
        for base in (0, 123):
            for layout in LAYOUTS:
                for li in cand_lists(a.cand, rank, base, 'group_mod' if layout == 'group_mod' else
                                     ('group_hash' if layout == 'group_hash' else 'w11')):
                    f = work / f'list_{layout}_r{rank}_s{li["stack"]}_b{base}.hex'
                    f.write_text(''.join(f'{ad:06x}{ln:01x}{of:04x}\n' for ad, ln, of in li['requests']))
                    for t0 in (5000, 5000 + TREFI_CYC // 3, 5000 + 2 * TREFI_CYC // 3):
                        jobs.append((rank, base, layout, li, f, t0))
    with ThreadPoolExecutor(a.jobs) as ex:
        rows = list(ex.map(lambda j: dict(rank=j[0], base_block=j[1], layout=j[2], stack=j[3]['stack'],
                                          keys=j[3]['keys'], groups=j[3]['groups'], start_cycle=j[5],
                                          **run(exe, [f'+list={j[4]}', f'+n_req={len(j[3]["requests"])}',
                                                      f'+n_sect={j[3]["sectors"]}', f'+t0={j[5]}'])), jobs))
    summ = {}
    for layout in LAYOUTS:
        lr = [r for r in rows if r['layout'] == layout]
        per_rank = {}
        for r in lr:
            per_rank.setdefault((r['rank'], r['base_block'], r['start_cycle']), []).append(r)
        rc = sorted(max(x['cycles'] for x in v) for v in per_rank.values())
        wk, wv = max(per_rank.items(), key=lambda kv_: max(x['cycles'] for x in kv_[1]))
        wc = max(x['cycles'] for x in wv)
        sect = sum(x['sectors'] for x in wv)
        med = rc[len(rc) // 2]
        summ[layout] = dict(exact=all(r['verdict'] == 'PASS' for r in lr), cases=len(lr),
                            rank_cycles=dict(min=rc[0], median=med, max=rc[-1]), worst_rank_sectors=sect,
                            worst_rank_us=round(wc * CLK_PS / 1e6, 4),
                            worst_rank_tbps=round(sect * 32 / (wc * CLK_PS * 1e-12) / 1e12, 4),
                            worst_rank_frac_of_4stack_peak=round(sect * 32 / (wc * CLK_PS * 1e-12) / 1e12 /
                                                                 (4 * PEAK_STACK_TBPS), 4),
                            first_access_cycles=max(r['first_rsp_cycles'] for r in lr),
                            cycles_saved_vs_full_scan_worst=5821 - rc[-1])
    summ['full_scan_reference'] = dict(cycles=5821, sectors=557056, frac_of_4stack_peak=0.919,
                                       record='claude dsrom-1m-measured reader csa1_full_L20_clk833 (the as-built '
                                              're-index read is the L20-shaped full scan, then masked)')
    rec = dict(schema='opentallas.dsrom.hbm_path.cand_gather.v1', **provenance(CAND_SRC), clk_ps=CLK_PS,
               cand_sha256=sha(a.cand), scope='re-index layer candidate-key read at the 1M token (golden candidate '
               'set: 16,384 keys in 2,048 aligned 8-key groups), per rank (slowest of its 4 stacks), timed '
               'refresh-live stack model, 3 refresh phases x 2 placements; layouts: w11 = the scan layout '
               '(superblock scale block + 64-key code blocks), group_mod / group_hash = GROUP-MAJOR layout (each '
               '8-key group 17 contiguous sectors on one PC; PC = g mod 32 or hashed); landed sectors checked',
               summary=summ, runs=rows)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(rec, indent=1) + '\n')
    print(json.dumps(summ, indent=1))


def provenance(srcs):
    head = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    return dict(git_head=head, input_sha256={s: sha(ROOT / s) for s in srcs + ['tools/dsrom_hbm_path_audit.py']},
                simulator=subprocess.run([VERILATOR, '--version'], capture_output=True, text=True).stdout.strip())


def main():
    ap = argparse.ArgumentParser()
    sp = ap.add_subparsers(dest='cmd', required=True)
    for n in ('window', 'cand'):
        p = sp.add_parser(n)
        p.add_argument('--work', type=Path, required=True)
        p.add_argument('--out', type=Path, required=True)
        p.add_argument('--jobs', type=int, default=16)
        if n == 'cand':
            p.add_argument('--cand', type=Path, required=True)
    a = ap.parse_args()
    (cmd_window if a.cmd == 'window' else cmd_cand)(a)


if __name__ == '__main__':
    main()
