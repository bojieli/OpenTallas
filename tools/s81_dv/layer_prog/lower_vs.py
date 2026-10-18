#!/usr/bin/env python3
"""LB2-S81/CC-VS (10-18): lower the slice SU lane ops (ot_s81sl_vs, vp ops 8..13) of one layer for one DV slice.

ABI of record = the built RTL (origin/main 711fb3da3+), not docs:
  CTL beat payload  ot_s81sl_xr.sv:121  tgt = p[20:16], lmask = p[25:21], body = p[185:26]
    target 0  ot_s81sl_xr.sv:223      c_v <= lmask: body = the vp command c_d of the masked beat leaves
    target 5  ot_s81sl_xr.sv:209-211  one leaf-store row write: sw_a = body[9:0], sw_m = {0, body[13:10]},
                                      sw_d = {0, body[141:14]} (a static constant row, e.g. the router bias)
  vp forward        ot_s81sl_vp.sv:273 / :288  s_v <= cv_c && op[3]; s_d <= cd_c (ops 8..15 to vs, one edge)
  vs command        ot_s81sl_vs.sv:153-155  op = s_d[3:0], a0 = [13:4], a1 = [23:14], n = [31:24], imm = [159:32]
                    ot_s81sl_vs.sv:171-172  ob = imm[9:0], wb = imm[10], uq = imm[11] (QB always streams),
                                            j0 = imm[24:22], lim = imm[63:32], w0 = imm[95:64], w1 = imm[127:96]
                    ot_s81sl_vs.sv:443      um_q = imm[12], um_b = imm[13], um_i = imm[21:14] (vq beat index)
                    ot_s81sl_vs.sv:159-163  c_bad: SW n <= 16 (uq: n even, j0 + n/2 <= 8), QB j0 + n <= 8, n != 0
                    ot_s81sl_vs.sv:468      a command while busy is a sticky fault: ONE op per leaf at a time,
                                            so this module serialises each leaf on a fixed per-op duration (VS_DUR).
  read cadence      ot_s81sl_vs.sv:182-206  QB / RB 1 pair a cycle, QR every 2, SW every 4, RA every 8 (8 elements)
  result rows       ot_s81sl_vs.sv:445-457  SW row ob + s (BF16 in FP32 words, mask 0F), RA row ob + i / 4 (word
                                            masked), RB / QR row ob + s

Leaf share (this compiler's placement; operand rows are produced by the upstream families -- frames / xr RD / ring
collectives -- at the rows of VS_ROWS; `depends` names them).  Leaf G = 5 sid + k (sid = the slice strap, kept a
parameter: siblings move the die to sid = 2c + r):
  attn.q_rope      G < heads_rank (16):  head G's rope tail (64) = 16 QR reads {q quad, cos/sin quad}
  attn.z_quant     G < 2048 / 64:        wo_a elements [64 G, 64 G + 64) of the rank -> QB 8 sub-beats -> vq
  ffn.softplus_sqrt  k == 0:             router rows [6 sid, 6 sid + 6) of the rank (96 / 16)
  ffn.bias         k == 0:               gathered scores [24 sid, 24 sid + 24) (384 / 16) + their bias rows
  ffn.swiglu (+ route_w, quant2) / ffn.shared_swiglu (+ shared_quant):  G < 63: slot = G // 9 (0..5 routed in id
                   order, 6 shared), ff elements [64 (G % 9), +64) of the rank's 576 -> SW 16 groups, wb + uq (vq)
Status:
  LOWERED  softplus_sqrt (RA), bias (RB + target-5 bias rows), shared_swiglu / shared_quant (SW w = 1.0 + vq),
           z_quant (QB + vq): command words + static rows only, proven by the bench (BENCH below).
  PARTIAL  swiglu / route_w / quant2: SW w0 / w1 (imm[95:64] / [127:96]) are the token's routing weights, runtime
           data with no on-die path into the command immediate (the gunit router writes leaf-store rows only);
           attn.q_rope: the cos / sin rows of the token position are runtime rows with no lowered producer.
"""
import math
import re
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
BENCH = 'results/rtl/s81_layer_tput_1018/compiler/bench_vs'
UNIT = 'slice vp (ops 8..13 forward) + vs + vsw + RA lane pair + vq'
OPS = [r'^attn\.q_rope$', r'^attn\.z_quant$', r'^ffn\.softplus_sqrt$', r'^ffn\.bias$',
       r'^ffn\.(swiglu|route_w|quant2|shared_swiglu|shared_quant)$']

OP = dict(SW=8, QB=9, RA=10, RB=11, QR=12)
ENG_V = dict(N=0, S=1)                      # dv_layer_compile ENG VN / VS (seq_host vo_n / vo_s)
LIM = 0x41200000                            # swiglu_limit 10.0 (compiler/models/deepseek-v4.1-flash/inference_config.json)
ONE = 0x3F800000
HEADS_RANK, WO_A_RANK, ROUTER_RANK, ROUTER_ALL, FF_RANK = 16, 2048, 96, 384, 576
NSLICE = 16
# per-leaf vs row map (rows 512.. of the 1,024-row leaf store; vp's own regions: h 0..31, gain 64..79)
VS_ROWS = dict(QR_IN=512, QR_OUT=544, QB_IN=560, RA_IN=576, RA_OUT=578, RB_IN=580, RB_OUT=592, SW_IN=600, SW_OUT=632)
# fixed op durations, vp command edge -> the last vs result (bench VSOP on the L0 fixtures, bench_vs run.log: QR 16 = 57,
# QB 8 = 19, RA 6 = 147, RB 6 = 25, SW 16 = 191; the bench fails on measured > model), + GUARD edges before the next
# command of the same leaf
VS_DUR = dict(SW=lambda n: 4 * n + 127, QB=lambda n: n + 11, QR=lambda n: 2 * n + 25, RB=lambda n: n + 19,
              RA=lambda n: n + 141)                   # RA measured for n <= 8 only (one read): plan() asserts it
GUARD = 3


def vp_cmd(op, a0=0, a1=0, n=0, imm=0):
    return (op & 0xF) | (a0 & 0x3FF) << 4 | (a1 & 0x3FF) << 14 | (n & 0xFF) << 24 | (imm & ((1 << 128) - 1)) << 32


def vs_imm(ob=0, wb=0, uq=0, umq=0, umb=0, umi=0, j0=0, lim=0, w0=0, w1=0):
    return ob | wb << 10 | uq << 11 | umq << 12 | umb << 13 | umi << 14 | j0 << 22 | lim << 32 | w0 << 64 | w1 << 96


def ctl_payload(slice_mask, target, leaf_mask, body160):
    return (slice_mask & 0xFFFF) | (target & 0x1F) << 16 | (leaf_mask & 0x1F) << 21 | (body160 & ((1 << 160) - 1)) << 26


def row_write(a10, m4, d128):
    """CTL target 5 body (ot_s81sl_xr.sv:209-211)"""
    return (a10 & 0x3FF) | (m4 & 0xF) << 10 | (d128 & ((1 << 128) - 1)) << 14


def u32(x):
    return np.asarray(x, np.float32).view(np.uint32)


def fx(fixtures, rel, dtype=np.float32):
    return np.fromfile(Path(fixtures) / rel, dtype=dtype)


def shares(sid, k):
    """the op shares of leaf (sid, k)"""
    G = 5 * sid + k
    s = {}
    if G < HEADS_RANK:
        s['attn.q_rope'] = dict(head=G)
    if G < WO_A_RANK // 64:
        s['attn.z_quant'] = dict(beat=G, lo=64 * G)
    if k == 0:
        s['ffn.softplus_sqrt'] = dict(lo=6 * sid, n=ROUTER_RANK // NSLICE)
        s['ffn.bias'] = dict(lo=24 * sid, n=ROUTER_ALL // NSLICE)
    if G < 63:
        slot, j = divmod(G, 9)
        s['ffn.shared_swiglu' if slot == 6 else 'ffn.swiglu'] = dict(slot=slot, j=j, lo=64 * j, beat=G)
    return s


def plan(die, sched, sl, fixtures=None):
    """the slice's whole vs programme for the layer: per op {templates, rows, leaf windows}, leaves serialised"""
    info = die.slices()[sl]
    sid, tier = info['sid'], sl[-1]
    eng = ENG_V[tier]
    by = {o['op']: o for o in sched['ops']}
    w_rt = fx(fixtures, 'ops/ffn.weights.bin') if fixtures else None
    bias = fx(fixtures, 'weights/gate.bias.bin') if fixtures else None
    out = {}
    free = [0] * 5                                     # per leaf: first edge a new command may arrive
    order = [o for o in ('attn.q_rope', 'attn.z_quant', 'ffn.softplus_sqrt', 'ffn.bias', 'ffn.shared_swiglu',
                         'ffn.swiglu') if o in by]
    order.sort(key=lambda o: by[o]['start'])
    for name in order:
        t_op = int(math.floor(by[name]['start']))
        rec = dict(templates=[], rows=[], leaves={}, notes=[])
        cmds = {}                                      # body -> leaf mask (identical commands share one template)
        pre = []                                       # target-5 row writes before the command
        for k in range(5):
            s = shares(sid, k).get(name)
            if s is None:
                continue
            R = VS_ROWS
            if name == 'attn.q_rope':
                c, kind, n = vp_cmd(OP['QR'], a0=R['QR_IN'], n=16, imm=vs_imm(ob=R['QR_OUT'])), 'QR', 16
            elif name == 'attn.z_quant':
                c, kind, n = vp_cmd(OP['QB'], a0=R['QB_IN'], n=8, imm=vs_imm(umq=1, umi=s['beat'])), 'QB', 8
            elif name == 'ffn.softplus_sqrt':
                assert s['n'] <= 8, 'VS_DUR RA is measured for one read (n <= 8) only'
                c, kind, n = vp_cmd(OP['RA'], a0=R['RA_IN'], n=s['n'], imm=vs_imm(ob=R['RA_OUT'])), 'RA', s['n']
            elif name == 'ffn.bias':
                c, kind, n = vp_cmd(OP['RB'], a0=R['RB_IN'], n=s['n'] // 4, imm=vs_imm(ob=R['RB_OUT'])), 'RB', s['n'] // 4
                if bias is not None:
                    b = u32(bias[s['lo']:s['lo'] + s['n']])
                    for r in range(s['n'] // 4):
                        d = sum(int(b[4 * r + w]) << (32 * w) for w in range(4))
                        pre.append((k, row_write(R['RB_IN'] + 2 * r + 1, 0xF, d), f'bias row {r}'))
            else:
                w = ONE if s['slot'] == 6 else (int(u32([w_rt[s['slot']]])[0]) if w_rt is not None else 0)
                c = vp_cmd(OP['SW'], a0=R['SW_IN'], n=16, imm=vs_imm(ob=R['SW_OUT'], wb=1, uq=1, umq=1, umi=s['beat'],
                                                                     lim=LIM, w0=w, w1=w))
                kind, n = 'SW', 16
            cmds.setdefault(c, []).append((k, kind, n))
        if not cmds:
            out[name] = rec
            continue
        # the target-5 row writes go first (one CTL beat a cycle), on a free leaf, then the commands
        t = max([t_op] + [free[k] + len(pre) for c in cmds for k, _, _ in cmds[c]])
        t_cmd0 = t
        t0 = t - len(pre)
        for i, (k, body, what) in enumerate(pre):
            rec['templates'].append((f'{name}.row.s{sid}k{k}.{i}', ctl_payload(1 << sid, 5, 1 << k, body)))
            rec['rows'].append(dict(eng=eng, issue=t0 + i, arg=len(rec['templates']) - 1,
                                    what=f'vs {name} target-5 {what} leaf {k}'))
        for c, ks in cmds.items():
            lm = sum(1 << k for k, _, _ in ks)
            rec['templates'].append((f'{name}.{ks[0][1]}.s{sid}m{lm:02x}', ctl_payload(1 << sid, 0, lm, c)))
            rec['rows'].append(dict(eng=eng, issue=t, arg=len(rec['templates']) - 1,
                                    what=f'vs {name} {ks[0][1]} n={ks[0][2]} leaves {lm:05b}'))
            for k, kind, n in ks:
                dur = VS_DUR[kind](n)
                rec['leaves'][k] = dict(cmd=t, op=kind, n=n, dur=dur, end=t + dur)
                free[k] = t + dur + GUARD
            t += 1
        if t_cmd0 > t_op:
            rec['notes'].append(f'issue delayed {t_cmd0 - t_op} edges past the priced start (leaf busy)')
        out[name] = rec
    return out


_cache = {}


def lower(die, op, ctx):
    name = op['op']
    sl = ctx['slice'] if ctx['slice'].startswith('u_') else 'u_' + ctx['slice']
    key = (id(die), ctx.get('layer'), sl, str(ctx.get('fixtures')))
    if key not in _cache:
        _cache[key] = plan(die, ctx['sched'], sl, ctx.get('fixtures'))
    P = _cache[key]
    sid = die.slices()[sl]['sid']
    base = dict(unit=UNIT, insts=[sl], gunit_rows=[], svc_jobs=[], files={}, bench=BENCH)
    gap = None
    host = {'ffn.route_w': 'ffn.swiglu', 'ffn.quant2': 'ffn.swiglu', 'ffn.shared_quant': 'ffn.shared_swiglu'}.get(name)
    rec = P.get(host or name, dict(templates=[], rows=[], leaves={}, notes=[]))
    if host:
        # fused into the host op's SW command (route_w = the w factor, quant2 = uq -> vq): no rows of its own
        r = dict(base, rows=[], templates=[], events=[], status='LOWERED' if host == 'ffn.shared_swiglu' else 'PARTIAL',
                 fused_into=host)
    else:
        ev = [dict(cycle=v['cmd'], inst=f'{sl}.leaf{k}.vs', port='s_d', dir='in', kind='VS', tag=f"{name}.{v['op']}",
                   payload=f"n={v['n']} busy until {v['end']}", plan_only=True) for k, v in rec['leaves'].items()]
        r = dict(base, rows=rec['rows'], templates=rec['templates'], events=ev, status='LOWERED',
                 leaves=rec['leaves'], notes=rec['notes'])
    if name in ('ffn.swiglu', 'ffn.route_w', 'ffn.quant2'):
        gap = dict(module='ot_s81sl_vs', port='s_d imm[95:64] / imm[127:96] (SW w0 / w1)',
                   missing='the routing weights are runtime (gunit router, delivered as leaf-store rows by CTL target 5); '
                           'SW takes w only from the command immediate (ot_s81sl_vs.sv:171), so a boot-loaded CTL '
                           'template cannot carry them (the bench proves the SW / vq path with the fixture weights)',
                   file_line='rtl/dsrom_sys/s81_dv/slice/ot_s81sl_vs.sv:171')
    elif name == 'attn.q_rope':
        gap = dict(module='ot_s81sl_vs', port='QR operand rows a0 + 2 s + 1 ({cos, sin, cos\', sin\'})',
                   missing='cos / sin of the token position are runtime rows (32 FP32 per position, all heads); no '
                           'lowered producer writes them into the QR leaves (seq_host context splice / host row write '
                           'not emitted); the bench proves QR with the golden rope_cs rows',
                   file_line='rtl/dsrom_sys/s81_dv/slice/ot_s81sl_vs.sv:22-23')
    elif name == 'ffn.bias' and ctx.get('fixtures') is None:
        gap = dict(module='lower_vs', port='bias rows (CTL target 5)', missing='needs the layer weights (--fixtures)',
                   file_line='tools/s81_dv/layer_prog/lower_vs.py')
    if gap:
        r['status'] = 'PARTIAL'
    r['gap'] = gap
    r['depends'] = dict(DEPENDS).get(host or name)
    r['sid'] = sid
    return r


DEPENDS = [
    ('attn.q_rope', 'frames wq_b -> RD rows QR_IN + 2 s (head q tail quads)'),
    ('attn.z_quant', 'frames wo_a -> RD rows QB_IN .. + 15 (BF16 in FP32 words)'),
    ('ffn.softplus_sqrt', 'frames router -> rows RA_IN, RA_IN + 1 (6 FP32); RA_OUT -> router_allgather send (RDOUT)'),
    ('ffn.bias', 'router_allgather -> rows RB_IN + 2 s (score quads); RB_OUT -> gunit router SC beats'),
    ('ffn.shared_swiglu', 'frames shared w1 / w3 -> rows SW_IN + 2 s (g quad) / + 1 (u quad)'),
    ('ffn.swiglu', 'frames expert w1 / w3 -> rows SW_IN + 2 s / + 1; weights from the gunit router (runtime)'),
]
