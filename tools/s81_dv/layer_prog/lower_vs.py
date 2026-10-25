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
TOK-S81-GAPS/VS (10-18):
  SW wr     ot_s81sl_vs.sv imm[25] wr, imm[28:26] wsel: w0 = w1 = word wsel of the row pair a1 = the gunit router's weights
            rows (GU_ROWS router + 1 / + 2, dsdv_gunit_l1 CTL target 5, every leaf): routed slots read their weight in a
            static slot (row pair read at step 0, groups 4 edges later: VS_DUR SW + 4).  The SW command is placed after
            the bound W_BOUND on the weights rows' write edge at the leaf (gunit vo edge + ctl tree + guard).
  QR rows   the token position's cos / sin rows ({c, s, c', s'} x 16 at QR_IN + 2 s + 1) are CTL target-5 row writes of
            the per-token programme (position = the decode token's, fixture meta.position; same rows for every head, one
            beat per row for all leaves of the slice).
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
       r'^ffn\.(swiglu|route_w|quant2|shared_swiglu|shared_quant)$', r'^eng\.(dot|hh|add)$']

OP = dict(SW=8, QB=9, RA=10, RB=11, QR=12)
ENG_V = dict(N=0, S=1)                      # dv_layer_compile ENG VN / VS (seq_host vo_n / vo_s)
LIM = 0x41200000                            # swiglu_limit 10.0 (compiler/models/deepseek-v4.1-flash/inference_config.json)
ONE = 0x3F800000
HEADS_RANK, WO_A_RANK, ROUTER_RANK, ROUTER_ALL, FF_RANK = 16, 2048, 96, 384, 576
NSLICE = 16
# per-leaf vs row map (rows 512.. of the 1,024-row leaf store; vp's own regions: h 0..31, gain 64..79)
VS_ROWS = dict(QR_IN=512, QR_OUT=544, QB_IN=560, RA_IN=576, RA_OUT=578, RB_IN=580, RB_OUT=592, SW_IN=600, SW_OUT=632)
# Current release vsw LR=1 captures each input lane once before the SW datapath.
# It adds one output edge versus the LR=0 component measurement (owner 10-25 11:59).
VSW_LR_CYCLES = 1
# fixed op durations, vp command edge -> the last vs result (bench VSOP on the L0 fixtures, bench_vs run.log: QR 16 = 57,
# QB 8 = 19, RA 6 = 147, RB 6 = 25, SW 16 = 191; the bench fails on measured > model), + GUARD edges before the next
# command of the same leaf
VS_DUR = dict(SW=lambda n, wr=0: 4 * n + 127 + 4 * wr + VSW_LR_CYCLES, QB=lambda n: n + 11, QR=lambda n: 2 * n + 25, RB=lambda n: n + 19,
              RA=lambda n: n + 141)                   # RA measured for n <= 8 only (one read): plan() asserts it
GUARD = 3
W_GUARD = 16                                  # bench: the weights rows are written this many edges before the SW command


def _dvc():
    import sys
    m = sys.modules.get('dv_layer_compile')
    if m is None and hasattr(sys.modules.get('__main__'), 'ctl_path'):
        m = sys.modules['__main__']
    if m is None:
        sys.path.insert(0, str(ROOT / 'tools/s81_dv'))
        import dv_layer_compile as m
    return m
POISON = 0                                    # immediate w of a wr SW (ignored by the RTL; 0 makes an RTL that ignores wr fail)


def gu_weights_vo_edge(sched):
    """the gunit vo edge of the router's last weights row (lower_gu: sc_plan after router_allgather + RT_LAT + RW_GAP + 1)"""
    import importlib.util
    spec = importlib.util.spec_from_file_location('lower_gu', Path(__file__).with_name('lower_gu.py'))
    gu = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gu)
    ag = next((o for o in sched['ops'] if o['op'] == 'ffn.router_allgather'), None)
    if ag is None:
        return None, gu
    t0 = int(math.ceil(ag['end']))
    tl = max(p['cycle'] for p in gu.sc_plan(t0) if p['port'] == 'vi_n')
    return tl + max(gu.RT_LAT_N, gu.RT_LAT_S) + gu.RW_GAP + 1, gu


def rope_rows(fixtures):
    """{c, s, c', s'} rows of the fixture token's position (Model.freqs_yarn / freqs_plain as hdc_golden_v41)"""
    import json, os, sys
    sys.path.insert(0, str(ROOT / 'tools'))
    os.environ.setdefault('HDC_V41_ARITH', 'chunk8')
    import hdc_golden_v41 as V
    meta = json.loads((Path(fixtures) / 'meta.json').read_text())
    c = json.loads((ROOT / 'compiler/models/deepseek-v4.1-flash/inference_config.json').read_text())
    if c['compress_ratios'][meta['layer_index']] > 0:
        fr = V.rope_freqs(c['rope_head_dim'], c['original_seq_len'], c['compress_rope_theta'], c['rope_factor'],
                          c['beta_fast'], c['beta_slow'])
    else:
        fr = V.rope_freqs(c['rope_head_dim'], 0, c['rope_theta'], c['rope_factor'], c['beta_fast'], c['beta_slow'])
    cos, sin = V.rope_cs(fr, meta['position'])
    cos, sin = u32(cos), u32(sin)
    return [int(cos[2 * i]) | int(sin[2 * i]) << 32 | int(cos[2 * i + 1]) << 64 | int(sin[2 * i + 1]) << 96 for i in range(16)]


def vp_cmd(op, a0=0, a1=0, n=0, imm=0):
    return (op & 0xF) | (a0 & 0x3FF) << 4 | (a1 & 0x3FF) << 14 | (n & 0xFF) << 24 | (imm & ((1 << 128) - 1)) << 32


def vs_imm(ob=0, wb=0, uq=0, umq=0, umb=0, umi=0, j0=0, lim=0, w0=0, w1=0, wr=0, wsel=0):
    return (ob | wb << 10 | uq << 11 | umq << 12 | umb << 13 | umi << 14 | j0 << 22 | wr << 25 | wsel << 26 | lim << 32 |
            w0 << 64 | w1 << 96)


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


def plan(die, sched, sl, fixtures=None, avoid=frozenset()):
    """the slice's whole vs programme for the layer: per op {templates, rows, leaf windows}, leaves serialised"""
    info = die.slices()[sl]
    sid, tier = info['sid'], sl[-1]
    eng = ENG_V[tier]
    by = {o['op']: o for o in sched['ops']}
    w_vo, gu = gu_weights_vo_edge(sched)
    w_bound = None
    if w_vo is not None:
        # the weights rows land in this slice's leaves at vo + the gunit tier link + the line path from the column-4
        # entry (ctl_path minus its seq_host head), as lower_norm_smoke's NORMR row-R dependency; the SW command's CTL
        # beat (issue + ctl_path) must arrive after them: issue >= land + 1 - ctl_path (+ GUARD)
        C = _dvc()
        lat = C.ctl_path(die, sl)['edges']
        head = C.SEQ['v_cmd_to_vo'] + (die.links.get(f'tv{tier}_seqhost') or {}).get('age_edges', 0)
        gl = (die.links.get(f'tv{tier}_gunit') or {}).get('age_edges', 0)
        w_bound = w_vo + gl + (lat - head) + 1 - lat + GUARD
    w_row = (gu.GU_ROWS['router'] + 1) if gu is not None else None
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
                if fixtures is not None and not any(w == 'cs' for _, _, w in pre):
                    for r, d in enumerate(rope_rows(fixtures)):
                        pre.append((None, row_write(R['QR_IN'] + 2 * r + 1, 0xF, d), 'cs'))
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
            elif s['slot'] == 6:
                c = vp_cmd(OP['SW'], a0=R['SW_IN'], n=16, imm=vs_imm(ob=R['SW_OUT'], wb=1, uq=1, umq=1, umi=s['beat'],
                                                                     lim=LIM, w0=ONE, w1=ONE))
                kind, n = 'SW', 16
            else:
                # routed slot: the weight comes from the gunit's weights rows in the leaf store (wr), not the immediate
                c = vp_cmd(OP['SW'], a0=R['SW_IN'], a1=w_row, n=16,
                           imm=vs_imm(ob=R['SW_OUT'], wb=1, uq=1, umq=1, umi=s['beat'], lim=LIM, w0=POISON, w1=POISON,
                                      wr=1, wsel=s['slot']))
                kind, n = 'SWR', 16
            cmds.setdefault(c, []).append((k, kind, n))
        if not cmds:
            out[name] = rec
            continue
        # the target-5 row writes go first (one CTL beat a cycle), on a free leaf, then the commands
        t = max([t_op] + [free[k] + len(pre) for c in cmds for k, _, _ in cmds[c]])
        if name == 'ffn.swiglu' and w_bound is not None and w_bound > t:
            rec['notes'].append(f'SW after the gunit weights rows: bound {w_bound} > {t}')
            t = w_bound
        # S81d-TOK 10-22: issue edges whose CTL beat would meet a column-3 re-injected G-unit V CTL beat on the tier
        # line (dv_layer_compile.line_slot_conflicts) are reserved: rows take the next free edge (one beat a cycle)
        edges, e = [], t - len(pre)
        while len(edges) < len(pre) + len(cmds):
            if e not in avoid:
                edges.append(e)
            e += 1
        if edges[len(pre)] != t:
            rec['notes'].append(f'rows moved past reserved line slots {sorted(x for x in avoid if t - len(pre) <= x < e)}')
        t = edges[len(pre)]
        t_cmd0 = t
        t0 = t - len(pre)
        lm_all = sum(1 << k for c in cmds for k, _, _ in cmds[c])
        for i, (k, body, what) in enumerate(pre):
            lmk = lm_all if k is None else 1 << k
            rec['templates'].append((f'{name}.row.s{sid}m{lmk:02x}.{i}', ctl_payload(1 << sid, 5, lmk, body)))
            rec['rows'].append(dict(eng=eng, issue=edges[i], arg=len(rec['templates']) - 1,
                                    what=f'vs {name} target-5 {what} leaves {lmk:05b}'))
        cmd_edges = iter(edges[len(pre):])
        for c, ks in cmds.items():
            t = next(cmd_edges)
            lm = sum(1 << k for k, _, _ in ks)
            rec['templates'].append((f'{name}.{ks[0][1][:2]}.s{sid}m{lm:02x}', ctl_payload(1 << sid, 0, lm, c)))
            rec['rows'].append(dict(eng=eng, issue=t, arg=len(rec['templates']) - 1,
                                    what=f'vs {name} {ks[0][1]} n={ks[0][2]} leaves {lm:05b}'))
            for k, kind, n in ks:
                dur = VS_DUR['SW'](n, 1) if kind == 'SWR' else VS_DUR[kind](n)
                rec['leaves'][k] = dict(cmd=t, op=kind[:2], wr=kind == 'SWR', n=n, dur=dur, end=t + dur, tix=len(rec['templates']) - 1)
                free[k] = t + dur + GUARD
        if t_cmd0 > t_op:
            rec['notes'].append(f'issue delayed {t_cmd0 - t_op} edges past the priced start (leaf busy)')
        out[name] = rec
    return out


_cache = {}


def w_row_ok(P):
    """every routed SW of the plan reads its weight from the gunit rows (wr)"""
    lv = P.get('ffn.swiglu', {}).get('leaves', {})
    return bool(lv) and all(v.get('wr') for v in lv.values())


ENG_HB, ENG_HB2 = 300, 400                   # vp HSTORE base (h for REDUCE) / ADD write-back base (then HLOAD), the slice_eng bench map
ENG_ADD_DUR = 81                             # ADD command -> last write (tb_s81sl_slice_eng, results/rtl/s81_lbgap_1018/g2_regress/eng)
ENG_HSTORE_LEAD = 64                         # HSTORE (32 row pairs) completes before the REDUCE reads h


def lower_eng(die, op, ctx, sl, sid):
    """TOK-S81-GAPS/VS: Engram mix words on every leaf of the slice: vp HSTORE -> vs op 14 REDUCE at eng.dot (eng.hh is
    the same REDUCE: hh partials ride with kk / dd), vs op 14 ADD at eng.add -> vp HLOAD.  A0 = the layer's K / W / V region
    (results/arch/s81_dv_1016/eng/kv_rowmap.json).  PARTIAL: the xfin ENG go (CTL target 1), the gates (eng.gate: xfin ENG
    + eg -> g_v) and the K / W / V rows (svc Engram row read, eng.hbm_read) are other families; no family bench yet."""
    import json
    name, layer = op['op'], ctx.get('layer')
    rm = json.loads((ROOT / 'results/arch/s81_dv_1016/eng/kv_rowmap.json').read_text())['layers']
    base = dict(unit='slice vp + vs op 14 + ve (Engram mix)', insts=[sl], gunit_rows=[], svc_jobs=[], files={}, sid=sid,
                bench=None, depends='K / W / V rows at A0 (svc Engram read + capture, kv_rowmap), xfin ENG go, eg gates')
    if layer not in rm:
        return dict(base, status='GAP', rows=[], templates=[], events=[],
                    gap=dict(module='results/arch/s81_dv_1016/eng/kv_rowmap.json', port='layers', missing=f'no A0 for {layer}'))
    A0 = rm[layer]['A0']
    eng = ENG_V[sl[-1]]
    t = int(math.floor(op['start']))
    LM = 0x1F
    if name == 'eng.hh':
        return dict(base, status='PARTIAL', rows=[], templates=[], events=[], fused_into='eng.dot',
                    gap=dict(module='ot_s81sl_vs op 14', port='REDUCE', missing='hh partials leave with the eng.dot REDUCE'))
    if name == 'eng.dot':
        cmds = [(t - ENG_HSTORE_LEAD, 'HSTORE', vp_cmd(4, a0=ENG_HB)), (t, 'REDUCE', vp_cmd(14, a0=ENG_HB, a1=A0, n=64))]
        dur = None
    else:
        cmds = [(t, 'ADD', vp_cmd(14, a0=A0, a1=ENG_HB2, n=32, imm=1 << 30)),
                (t + ENG_ADD_DUR + GUARD, 'HLOAD', vp_cmd(3, a0=ENG_HB2))]
    tpl, rows, ev = [], [], []
    for i, (c, what, body) in enumerate(cmds):
        tpl.append((f'{name}.{what}.s{sid}', ctl_payload(1 << sid, 0, LM, body)))
        rows.append(dict(eng=eng, issue=c, arg=i, what=f'vs {name} {what} A0 {A0} leaves 11111'))
        if what in ('REDUCE', 'ADD'):
            ev += [dict(cycle=c, inst=f'{sl}.leaf{k}.vs', port='s_d', dir='internal', kind='VS', tag=f'{name}.{what}',
                        payload=f'op 14 {what}', issue=c, carried_by=f'template {i}') for k in range(5)]
    gap = dict(module='ot_s81sl_xfin (ENG) / ot_s81sl_eg / dsdv_svc_rs',
               port='CTL target 1 ENG go, g_v gates, K/W/V rows at A0',
               missing='op 14 words lowered; the xfin ENG go + gate fan-out (eng.gate) and the svc Engram row read '
                       '(eng.hbm_read) that fills A0 are not lowered, and no family bench runs op 14 at compiler cycles '
                       '(tb_s81sl_slice_eng proves the words with waits)')
    return dict(base, status='PARTIAL', rows=rows, templates=tpl, events=ev, gap=gap)


def lower(die, op, ctx):
    name = op['op']
    if name.startswith('eng.'):
        sl0 = ctx['slice'] if ctx['slice'].startswith('u_') else 'u_' + ctx['slice']
        return lower_eng(die, op, ctx, sl0, die.slices()[sl0]['sid'])
    sl = ctx['slice'] if ctx['slice'].startswith('u_') else 'u_' + ctx['slice']
    avoid = (ctx.get('line_avoid') or {}).get(sl[-1], frozenset())
    key = (id(die), ctx.get('layer'), sl, str(ctx.get('fixtures')), avoid)
    if key not in _cache:
        _cache[key] = plan(die, ctx['sched'], sl, ctx.get('fixtures'), avoid)
    P = _cache[key]
    sid = die.slices()[sl]['sid']
    base = dict(unit=UNIT, insts=[sl], gunit_rows=[], svc_jobs=[], files={}, bench=BENCH)
    gap = None
    host = {'ffn.route_w': 'ffn.swiglu', 'ffn.quant2': 'ffn.swiglu', 'ffn.shared_quant': 'ffn.shared_swiglu'}.get(name)
    rec = P.get(host or name, dict(templates=[], rows=[], leaves={}, notes=[]))
    if host:
        # fused into the host op's SW command (route_w = the w factor, quant2 = uq -> vq): no rows of its own
        r = dict(base, rows=[], templates=[], events=[], fused_into=host,
                 status='LOWERED' if host == 'ffn.shared_swiglu' or w_row_ok(P) else 'PARTIAL')
    else:
        # LB2-S81/EVENTS: the vs command is slice-internal (vp forward -> s_d); at a cut boundary it is the CTL beat of
        # the calendar row that carries it (dv_layer_compile emits that CTL event from the row): dir 'internal',
        # carried_by = the template (family-local index, re-pointed by Prog.absorb); cycle = the calendar issue edge
        ev = [dict(cycle=v['cmd'], inst=f'{sl}.leaf{k}.vs', port='s_d', dir='internal', kind='VS',
                   tag=f"{name}.{v['op']}", payload=f"n={v['n']} busy until {v['end']}", issue=v['cmd'],
                   carried_by=f"template {v['tix']}") for k, v in rec['leaves'].items()]
        r = dict(base, rows=rec['rows'], templates=rec['templates'], events=ev, status='LOWERED',
                 leaves=rec['leaves'], notes=rec['notes'])
    if name in ('ffn.swiglu', 'ffn.route_w', 'ffn.quant2') and w_row_ok(P):
        pass
    elif name == 'attn.q_rope' and ctx.get('fixtures') is not None:
        pass
    elif name in ('ffn.swiglu', 'ffn.route_w', 'ffn.quant2'):
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
