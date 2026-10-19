#!/usr/bin/env python3
"""LB2-S81/CC-VS bench vector generator: ONE beat leaf (slice, k) of the DV die runs the vs programme lower_vs.py
emits for the layer, at the compiler's cycles, on the layer fixture's TP4 rank-0 operands.

The bench (tb_vs_lowered.sv) instantiates the REAL ot_s81sl_vp + ot_s81sl_vs + ot_s81sl_vsw + the RA lane pair + ot_s81sl_vq
and drives vp exactly as ot_s81sl_xr does for the emitted CTL beats (target 0 -> c_v / c_d = body; target 5 -> the
row-write port sw_a = body[9:0], sw_m = {0, body[13:10]}, sw_d = {0, body[141:14]}, ot_s81sl_xr.sv:209-223), every beat
at bench edge BASE + (calendar issue - first issue) (the CTL path latency is one constant per slice).  Operand rows the
upstream families deliver (frames / RD / collectives) are preloaded before BASE at lower_vs.VS_ROWS.  Expected results
are the FIXTURE values (ops/*.bin): q_rope tail, z_quant / quant2 / shared_quant codes + block exps, softplus_sqrt,
bias, BF16(route_w) / BF16(shared.swiglu); each is also asserted against the CPU golden first.

  python3 gen_vs_bench.py --fixtures DIR --sched schedule.json --slice u_s_0S --leaf 0 --out OUT [--mutant M]
mutants (applied to the lowered programme, not the RTL):
  lim0      wrong field: SW imm[63:32] lim = 0                            (SW rows + vq beats must mismatch)
  biaslate  shifted cycle: the target-5 bias rows 30 edges later          (RB reads stale bias rows: mismatch)
  swearly   shifted cycle: the leaf's SW command 40 edges earlier         (command while busy: vs sticky fault)
  wlate     shifted cycle: the gunit weights rows 12 edges AFTER the routed SW command (TOK-S81-GAPS: SW wr reads the
            stale rows: route_w / quant2 mismatch)
The routed SW (wr) weights rows are written as the gunit router writes them (dsdv_gunit_l1 CTL target 5 rows R+1 = w0..w3,
R+2 = w4, w5 from the fixture ffn.weights) W_GUARD edges before the SW command; the q_rope cos / sin rows are the lowered
target-5 beats (not preloaded).
"""
import argparse
import importlib.util
import json
import os
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'tools/s81_dv'))
os.environ.setdefault('HDC_V41_ARITH', 'chunk8')
import hdc_golden_v41 as V                      # noqa: E402
import rtl_hdc_v41_blockdot_campaign as BC      # noqa: E402

F = np.float32
spec = importlib.util.spec_from_file_location('lower_vs', ROOT / 'tools/s81_dv/layer_prog/lower_vs.py')
LV = importlib.util.module_from_spec(spec)
spec.loader.exec_module(LV)
BASE = 600
OPN = {8: 'SW', 9: 'QB', 10: 'RA', 11: 'RB', 12: 'QR'}


def u32(x):
    return np.asarray(x, F).view(np.uint32)


def rows4(words):
    w = [int(x) for x in words]
    w += [0] * (-len(w) % 4)
    return [w[i:i + 4] for i in range(0, len(w), 4)]


def il(a, b):
    out = []
    for x, y in zip(a, b):
        out += [x, y]
    return out


class Bench:
    def __init__(self, fx):
        self.fx = Path(fx)
        self.img = {}
        self.prog = []          # (kind, cycle, op, dur, body)
        self.chk = []           # (op, base, rows, masks)
        self.xq = []            # (codes0, e0, codes1, e1, idx)

    def f(self, name, dtype=F):
        return np.fromfile(self.fx / name, dtype=dtype)

    def put(self, a, rows):
        for i, r in enumerate(rows):
            assert a + i not in self.img, f'row {a + i} placed twice'
            self.img[a + i] = list(r)

    def expect_rows(self, op, base, rows, mask=0xF, last_mask=None):
        ms = [mask] * len(rows)
        if last_mask is not None:
            ms[-1] = last_mask
        self.chk.append((op, base, rows, ms))

    def expect_xq(self, q64, e2, idx, golden_in=None):
        """vq XQ beat {e1, q1, e0, q0}: codes from the fixture's E4M3 values, block exps from the fixture"""
        c = BC.e4m3_codes(q64)
        if golden_in is not None:
            q, e = V.quant_fp8(np.asarray(golden_in, F))
            assert np.array_equal(q, q64) and np.array_equal(e.astype(np.int64), np.asarray(e2, np.int64)), 'xq golden'
        w = lambda cs: int.from_bytes(bytes(np.asarray(cs, np.uint8)), 'little')
        self.xq.append(w(c[:32]) | (int(e2[0]) & 0x3FF) << 256 | w(c[32:]) << 266 | (int(e2[1]) & 0x3FF) << 522)
        self.xqi.append(idx)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--fixtures', required=True)
    ap.add_argument('--sched', required=True)
    ap.add_argument('--slice', default='u_s_0S')
    ap.add_argument('--leaf', type=int, default=0)
    ap.add_argument('--layer', default='L0')
    ap.add_argument('--die-src', default=None)
    ap.add_argument('--out', required=True)
    ap.add_argument('--mutant', default=None, choices=(None, 'lim0', 'biaslate', 'swearly', 'wlate'))
    a = ap.parse_args()
    import dv_layer_compile as C
    die = C.Die(C.die_tree(src=a.die_src))
    sched = json.loads(Path(a.sched).read_text())
    sl, k = a.slice, a.leaf
    sid = die.slices()[sl]['sid']
    G = 5 * sid + k
    meta = json.loads((Path(a.fixtures) / 'meta.json').read_text())
    assert meta['rank'] == 0 and meta['layer'] == a.layer
    V.set_arith(meta.get('arith', 'chunk8'))
    b = Bench(a.fixtures)
    b.xqi = []
    # ------------------------------------------------ the lowered programme of this slice, this leaf's beats
    ctx = dict(layer=a.layer, slice=sl, sched=sched, fixtures=Path(a.fixtures))
    import re
    beats, lowered = [], {}
    for o in sched['ops']:
        if not any(re.search(rx, o['op']) for rx in LV.OPS):
            continue
        if o['op'].startswith('eng.'):      # Engram op 14 words (PARTIAL): proven by tb_s81sl_slice_eng, not this bench
            continue
        r = LV.lower(die, o, dict(ctx, t_issue=int(o['start'])))
        lowered[o['op']] = dict(status=r['status'], rows=len(r['rows']), gap=r['gap'], leaves=r.get('leaves', {}),
                                fused_into=r.get('fused_into'))
        for row in r['rows']:
            p = r['templates'][row['arg'] & 0x7F][1]
            tgt, lm, body = (p >> 16) & 0x1F, (p >> 21) & 0x1F, p >> 26
            assert (p & 0xFFFF) == 1 << sid
            if lm >> k & 1:
                beats.append(dict(op=o['op'], issue=row['issue'], tgt=tgt, body=body, what=row['what'],
                                  dur=r.get('leaves', {}).get(k, {}).get('dur', 0)))
    assert beats, f'leaf {G} has no vs work in {a.layer}'
    # mutants on the lowered beats
    if a.mutant == 'lim0':
        for x in beats:
            if x['tgt'] == 0 and x['body'] & 0xF == 8:
                x['body'] &= ~(0xFFFFFFFF << 64)
    elif a.mutant == 'biaslate':
        for x in beats:
            if x['tgt'] == 5:
                x['issue'] += 30
    elif a.mutant == 'swearly':
        for x in beats:
            if x['tgt'] == 0 and x['body'] & 0xF == 8:
                x['issue'] -= 40
    t0 = min(x['issue'] for x in beats)
    R = LV.VS_ROWS
    sh = LV.shares(sid, k)
    # ------------------------------------------------ operands (upstream deliveries) + expected results (fixtures)
    if 'attn.q_rope' in sh:
        h = sh['attn.q_rope']['head'] + meta['tp_split']['heads'][0][0]
        qb = b.f('ops/attn.wq_b.bin').reshape(64, 512)
        qr = b.f('ops/attn.q_rope.bin').reshape(64, 512)
        c = json.loads((ROOT / 'compiler/models/deepseek-v4.1-flash/inference_config.json').read_text())
        if c['compress_ratios'][meta['layer_index']] > 0:          # Model.freqs_yarn (compressed-attention layers)
            fr = V.rope_freqs(c['rope_head_dim'], c['original_seq_len'], c['compress_rope_theta'], c['rope_factor'],
                              c['beta_fast'], c['beta_slow'])
        else:                                                       # Model.freqs_plain
            fr = V.rope_freqs(c['rope_head_dim'], 0, c['rope_theta'], c['rope_factor'], c['beta_fast'], c['beta_slow'])
        cos, sin = V.rope_cs(fr, meta['position'])
        assert np.array_equal(u32(V.rope_tail(qb[h:h + 1], (cos, sin))[0]), u32(qr[h])), 'q_rope golden vs fixture'
        tail = qb[h][-64:]
        cs = [[int(u32([cos[2 * i]])[0]), int(u32([sin[2 * i]])[0]), int(u32([cos[2 * i + 1]])[0]),
               int(u32([sin[2 * i + 1]])[0])] for i in range(16)]
        cs_low = any(x['tgt'] == 5 and R['QR_IN'] <= (x['body'] & 0x3FF) < R['QR_IN'] + 32 for x in beats)
        if cs_low:                                  # lowered: the target-5 beats write the cs rows; check they are the golden's
            got = {x['body'] & 0x3FF: (x['body'] >> 14) & ((1 << 128) - 1) for x in beats
                   if x['tgt'] == 5 and R['QR_IN'] <= (x['body'] & 0x3FF) < R['QR_IN'] + 32}
            for i in range(16):
                assert got[R['QR_IN'] + 2 * i + 1] == sum(w << (32 * j) for j, w in enumerate(cs[i])), 'lowered cs row'
            for i, r in enumerate(rows4(u32(tail))):
                b.put(R['QR_IN'] + 2 * i, [r])
        else:
            b.put(R['QR_IN'], il(rows4(u32(tail)), cs))
        b.expect_rows('attn.q_rope', R['QR_OUT'], rows4(u32(qr[h][-64:])))
    if 'attn.z_quant' in sh:
        lo = sh['attn.z_quant']['lo'] + meta['tp_split']['wo_a_rows'][0][0]
        z = b.f('ops/attn.wo_a.bin')[lo:lo + 64]
        zq = b.f('ops/attn.z_quant.bin', np.float64)
        b.put(R['QB_IN'], rows4(u32(z)))
        b.expect_xq(zq[lo:lo + 64], zq[8192 + lo // 32: 8192 + lo // 32 + 2], G, golden_in=z)
    if 'ffn.softplus_sqrt' in sh:
        s = sh['ffn.softplus_sqrt']
        lo = s['lo'] + meta['tp_split']['router_rows'][0][0]
        x = b.f('ops/ffn.router.bin')[lo:lo + s['n']]
        y = b.f('ops/ffn.softplus_sqrt.bin')[lo:lo + s['n']]
        assert np.array_equal(u32(V.sqrt(V.softplus(x))), u32(y)), 'softplus_sqrt golden'
        b.put(R['RA_IN'], rows4(u32(x)))
        rr = rows4(u32(y))
        b.expect_rows('ffn.softplus_sqrt', R['RA_OUT'], rr, last_mask=(1 << (s['n'] - 4 * (len(rr) - 1))) - 1)
    if 'ffn.bias' in sh:
        s = sh['ffn.bias']
        sc = b.f('ops/ffn.router_allgather.bin')[s['lo']:s['lo'] + s['n']]
        y = b.f('ops/ffn.bias.bin')[s['lo']:s['lo'] + s['n']]
        bias = b.f('weights/gate.bias.bin')[s['lo']:s['lo'] + s['n']]
        assert np.array_equal(u32(V.add(sc, bias)), u32(y)), 'bias golden'
        for i, r in enumerate(rows4(u32(sc))):
            b.put(R['RB_IN'] + 2 * i, [r])                 # bias rows (RB_IN + 2 i + 1) come from the target-5 beats
        b.expect_rows('ffn.bias', R['RB_OUT'], rows4(u32(y)))
    for nm in ('ffn.swiglu', 'ffn.shared_swiglu'):
        if nm not in sh:
            continue
        s = sh[nm]
        lo = s['lo'] + meta['tp_split']['expert_ff_rows' if s['slot'] < 6 else 'shared_ff_rows'][0][0]
        if s['slot'] < 6:
            eid = int(b.f('ops/ffn.top6_order.bin', np.int64)[s['slot']])
            pre, wfx = f'ops/ffn.experts.{eid}', 'route_w'
            swr = [x for x in beats if x['tgt'] == 0 and x['body'] & 0xF == 8 and (x['body'] >> 57) & 1]
            assert swr, 'routed SW must be lowered with wr (weights from the gunit rows)'
            wrow = (swr[0]['body'] >> 14) & 0x3FF
            wts = [int(v) for v in u32(b.f('ops/ffn.weights.bin')[:6])]
            t_w = swr[0]['issue'] + (12 if a.mutant == 'wlate' else -LV.W_GUARD)
            for i, ws in enumerate((wts[0:4], wts[4:6] + [0, 0])):
                body = (wrow + i) | (0xF if i == 0 else 0x3) << 10 | sum(w << (32 * j) for j, w in enumerate(ws)) << 14
                beats.append(dict(op='ffn.weights', issue=t_w + i, tgt=5, body=body, dur=0,
                                  what=f'gunit router weights row {wrow + i} (dsdv_gunit_l1 target 5)'))
        else:
            pre, wfx = 'ops/ffn.shared', 'swiglu'
        gu = b.f(f'{pre}.gu.bin')
        g, uu = gu[lo:lo + 64], gu[2304 + lo:2304 + lo + 64]
        a_fx = b.f(f'{pre}.{wfx}.bin')[lo:lo + 64]
        ab = V.to_bf16(a_fx)
        q2 = b.f(f'{pre}.quant2.bin', np.float64)
        b.put(R['SW_IN'], il(rows4(u32(g)), rows4(u32(uu))))
        b.expect_rows(nm, R['SW_OUT'], rows4(u32(ab)))
        b.expect_xq(q2[lo:lo + 64], q2[2304 + lo // 32: 2304 + lo // 32 + 2], G, golden_in=ab)
    # ------------------------------------------------ prog: timed beats, then RDOUT checks
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    prog = []
    for x in sorted(beats, key=lambda x: (x['issue'], x['tgt'] != 5)):
        kind = 3 if x['tgt'] == 5 else 1
        op = x['body'] & 0xF if kind == 1 else 0
        prog.append(kind << 252 | (BASE + x['issue'] - t0) << 228 | op << 224 | (x['dur'] & 0xFFFF) << 186 | x['body'])
    exp, expm = [], []
    names = sorted({c[0] for c in b.chk})
    for op, base, rows, ms in b.chk:
        assert base % 2 == 0
        if len(rows) % 2:
            rows, ms = rows + [[0] * 4], ms + [0]
        idx = len(exp)
        for i in range(0, len(rows), 2):
            exp.append(sum(w << (32 * j) for j, w in enumerate(rows[i] + rows[i + 1])))
            expm.append(ms[i] | ms[i + 1] << 4)
        prog.append(2 << 252 | names.index(op) << 224 | idx << 210 | (len(rows) // 2) << 202 | base)
    prog.append(0)
    with open(out / 'img.mem', 'w') as f, open(out / 'imgv.mem', 'w') as g:
        for r in range(1024):
            ws = b.img.get(r, [0, 0, 0, 0])
            f.write('%032x\n' % sum(w << (32 * j) for j, w in enumerate(ws)))
            g.write('%d\n' % (r in b.img))
    (out / 'prog.mem').write_text(''.join('%064x\n' % p for p in prog))
    (out / 'exp.mem').write_text(''.join('%064x\n' % e for e in exp) or '0\n')
    (out / 'expm.mem').write_text(''.join('%02x\n' % m for m in expm) or '0\n')
    (out / 'xq.mem').write_text(''.join('%0133x\n' % e for e in b.xq) or '0\n')
    (out / 'xqi.mem').write_text(''.join('%02x\n' % e for e in b.xqi) or '0\n')
    last = max(x['issue'] for x in beats) - t0 + BASE
    (out / 'params.txt').write_text(f'+sid={sid} +k={k} +nxq={len(b.xq)} +last={last}\n')
    man = dict(layer=a.layer, slice=sl, sid=sid, leaf=k, G=G, mutant=a.mutant, base=BASE, first_issue=t0,
               beats=[dict(op=x['op'], issue=x['issue'], bench_edge=BASE + x['issue'] - t0, target=x['tgt'],
                           body=f"{x['body']:040x}", what=x['what'], model_dur=x['dur']) for x in sorted(beats, key=lambda x: x['issue'])],
               checks=[dict(op=op, base=base, rows=len(rows)) for op, base, rows, _ in b.chk], check_names=names,
               xq=len(b.xq), lowered=lowered)
    (out / 'manifest.json').write_text(json.dumps(man, indent=1) + '\n')
    print(f'VS_BENCH_GEN {a.layer} {sl} leaf {k} G={G} beats={len(beats)} checks={len(b.chk)} xq={len(b.xq)} '
          f'mutant={a.mutant} span={max(x["issue"] for x in beats) - t0}')


if __name__ == '__main__':
    main()
