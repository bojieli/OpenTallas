#!/usr/bin/env python3
"""TOK-QK 10-25 (owner decision 14 check): per-PC HBM column / command duty of the COMPILED KV controller calendars
(boot targets 6..9), per controller edge.

    hbm_duty.py --ages AGES --rs RS --out DUTY.json      (same env as kv_boot_v36.py compile; kv_boot_image.sh runs it)

Re-runs kv_static_programme.compile_all exactly as kv_boot_v36.py compile (bound ages + relays) and records every
controller_calendar_image run of every PC before it is encoded: RD reservations (mask 1, one 288-b sector column each)
and the template commands (layer-row descriptor + second command per K and V pass).  The same runs are what targets
6..9 carry (compile_all refuses a PC whose encoded RD events differ from the kv_calendar issue edges).
Duty = columns per controller edge, per PC:
  in_burst     max over sliding windows of 8 edges (columns back-to-back inside an RD burst)
  shape        max over sliding windows of 110 edges = lcm of the RD shapes (K 8 on / 2 off = 0.800, V 8 on / 3 off = 0.727):
               the sustained column rate of the burst train
  mean_active  columns / (last - first + 1) of the PC's RD span in a layer
  mean_layer   columns / layer period in controller edges (kv_params layer_period_core in core edges -> HBM edges)
The calendar's controller edge is static_kv_calendar.HBM_PS (as compiled); the 833-ps view rescales by HBM_PS / 833.000
(same columns in the same wall time on the die clock).  Limit (KV-G3 2026-10-24 21:42, decision 14): <= 0.73 / PC / cycle.
"""
import argparse
import json
import math
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path[:0] = [str(ROOT), str(ROOT / 'tools/qwen_kv_die'), str(ROOT / 'tools')]
LIMIT = 0.73
DIE_PS = 833.0


def edges(run):
    out, e = [], run.edge
    for i in range(run.count):
        out.append(e)
        e += 1 + (run.gap if run.burst and (i + 1) % run.burst == 0 else 0)
    return out


def peak(ev, win):
    ev = sorted(ev)
    best, j = 0, 0
    for i in range(len(ev)):
        while ev[i] - ev[j] >= win:
            j += 1
        best = max(best, i - j + 1)
    return best / win


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--ages', required=True)
    ap.add_argument('--rs', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--rd-shape-k', help='candidate K burst,gap (for example 8,3); full compile, not a rate-only estimate')
    ap.add_argument('--rd-shape-v', help='candidate V burst,gap')
    ap.add_argument('--hbm-ps', type=float, help='WHAT-IF: compile the calendars with this controller period (decision 14: '
                    '833.000 = die clock) instead of static_kv_calendar.HBM_PS; the image is not written')
    a = ap.parse_args()
    if a.rd_shape_k:
        os.environ['OT_KV_RD_SHAPE_K'] = a.rd_shape_k
    if a.rd_shape_v:
        os.environ['OT_KV_RD_SHAPE_V'] = a.rd_shape_v
    from tools.qwen_kv_die import kv_static_programme as P
    if a.hbm_ps:
        P.KC.SOURCED['hbm_ps'] = a.hbm_ps
    P.MU = False
    P.AGES = str(Path(a.ages).resolve())
    os.environ['OT_KV_EMB_FILL_RELAYS'] = str(a.rs)
    os.environ['OT_KV_WRITER_DIE'] = '1'
    cap = []
    orig = P.CCI.compile_image

    def spy(runs, *x, **k):
        cap.append(list(runs))
        return orig(runs, *x, **k)
    P.CCI.compile_image = spy
    pr = P.profile('die', json.loads(Path(a.ages).read_text()))
    r = P.compile_all(pr, 0x0b0b)
    P.CCI.compile_image = orig
    if len(cap) != 128:
        raise SystemExit(f'expected 128 PC controller images, captured {len(cap)}')
    kp = P.kv_params(pr)
    hbm_ps, core_ps = kp['hbm_ps'], kp['core_ps']
    layer_hbm = math.floor(kp['layer_period_core'] * core_ps / hbm_ps)
    win = math.lcm(*(b + g for b, g in (P.RD_SHAPE_K, P.RD_SHAPE_V)))
    pcs = []
    for pc, runs in enumerate(cap):
        col = sorted(e for x in runs if x.mask == 1 for e in edges(x))
        cmd = sorted(x.edge for x in runs if x.mask != 1)
        if len(set(col)) != len(col):
            raise SystemExit(f'PC {pc}: two columns on one edge')
        bus = sorted(set(col) | set(cmd))
        span = col[-1] - col[0] + 1
        pcs.append(dict(pc=pc, columns=len(col), commands=len(cmd), shared_edges=len(set(col) & set(cmd)), span=span,
                        in_burst=peak(col, 8), shape=peak(col, win), mean_active=len(col) / span,
                        mean_layer=len(col) / layer_hbm, cmd_bus_shape=peak(bus, win)))
    agg = lambda k, f: f(p[k] for p in pcs)
    scale = DIE_PS / hbm_ps
    res = dict(schema='opentallas.kv_hbm_duty.v1', ages=str(a.ages), hbm_ps_compiled=hbm_ps, what_if=bool(a.hbm_ps), core_ps=core_ps,
               controller_core=P.CONTROLLER_CORE, phase_ticks=dict(core=P.CORE_U, controller=P.HBM_U, dimensionless=True),
               layer_period_hbm_edges=layer_hbm, burst_window=win, rd_shape=dict(K=P.RD_SHAPE_K, V=P.RD_SHAPE_V),
               limit=LIMIT, token_period=r['link']['token_period'] if isinstance(r.get('link'), dict) else None,
               per_compiled_edge={k: dict(max=agg(k, max), mean=agg(k, lambda g: sum(g) / len(pcs)))
                                  for k in ('in_burst', 'shape', 'mean_active', 'mean_layer', 'cmd_bus_shape')},
               columns=dict(min=agg('columns', min), max=agg('columns', max)),
               commands=dict(min=agg('commands', min), max=agg('commands', max)))
    res['per_833ps_cycle'] = {k: dict(max=v['max'] * scale, mean=v['mean'] * scale) for k, v in res['per_compiled_edge'].items()}
    e = res['per_compiled_edge']
    d = res['per_833ps_cycle']
    res['verdict'] = dict(
        shape_per_833ps=('PASS' if d['shape']['max'] <= LIMIT else 'FAIL'),
        in_burst_per_833ps=('PASS' if d['in_burst']['max'] <= LIMIT else 'FAIL'),
        note='0.73 = 7.0 / 9.6 Gb/s: the priced bandwidth on a 9.6-Gb/s DFI 1:4 PHY (capacity 1.0 column / 833-ps cycle), so '
             'the bound applies to the sustained (shape) rate; in-burst columns are back-to-back by construction')
    res['pcs'] = pcs
    Path(a.out).write_text(json.dumps(res, indent=1) + '\n')
    print(json.dumps({k: v for k, v in res.items() if k != 'pcs'}))


if __name__ == '__main__':
    main()
