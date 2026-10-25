#!/usr/bin/env python3
"""QLB-C4b/3a 10-18 (G-C4): the DV slice lowering of the lane-local vector op families
(tools/qwen_layerbench/dv_lower_vec.py) on the 12-slice qfd_dv_slice2 die chain (tb_qfd_dv2.sv N 12), Verilator 5.050.

    dv_lower_vec_bench.py --work DIR --mode calibrate|resid|qk|silu [--mutant NAME] [--ages FILE] [--seed N]

Stimulus = what the compiler emitted (PROG images as kind-3 table words, the CROM table words, every command on its
compiled edge at dvs_W5.cmd_wi, in resid the AR return words on their compiled calendar edges) plus, as bench
stimulus, the vectors the previous ops leave: x (resid), the station landings QKV / GU and r at RX (qk / silu),
landed over the AR return chain with generous PORTS windows.  Checks (PASS needs all), golden = hdc_golden:
  resid: (1) r at every slice = rsqrt(reduce_chunked(x' x') 2^-12 + eps), x' = (t * pscale) + x; (2) every PSUM on
         its compiled edge / tag; (3) the 64 BF16 x' words (to_bf16(x')) at the E5 end on their compiled edges, each
         once; (4) x' FP32 bit-exact in every slice (bench-only D2D readback); (5) no fault.
  qk:    q heads (rope(QN), FP32, D2D kind 0), k (fp8, kind 1), v (fp8(v r), kind 2) bit-exact on their compiled W5
         edges; no fault.
  silu:  the 24 BF16 act words (to_bf16(silu(g r) (u r))) at the E5 end on their compiled edges; no fault.
  attn:  (QW-ATTNRET 10-19) the 32 attention-result words enter dvs_W5.ch_dn_i (TB port 40) in the exact
         qfd_native59_dv_service.dr_o group-0 format {v, em 0, 0, beat 5, data 512 (lane j = element 16 b + j)} on the
         compiled dr calendar (beat b on consecutive edges, ascending, as qkd_attn_result_face emits them); checks:
         (1) the 8 BF16 o_proj x words (to_bf16(attn), eaddr 128 i + 64 j) at the E5 end on their compiled edges, each
         once, nothing else; (2) no fault; prints the MEASURED span first dr word at the W5 pin -> last x word at E5.
calibrate measures every timing constant the compiler schedules with -> DIR/vec_ages.json.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / 'tools' / 'qwen_layerbench'))
import dv_bench as B            # noqa: E402
import dv_bench2 as B2          # noqa: E402
import dv_lower as D            # noqa: E402
import dv_lower_bench as LB     # noqa: E402
import dv_lower_vec as V        # noqa: E402

G, F = B.G, B.F
N, BLOCK = D.NSLICE, D.BLOCK
P_CMD, P_ARET, P_SWI = LB.P_CMD, LB.P_ARET, LB.P_SWI
P_DRET = 40                     # dvs_W5.ch_dn_i D2D return half (native59 dr_o)
T0 = 16
BENCH_PIDX = dict(qkr_ps=16, rs_dd=17, qn_dd=18, gur_dd=19, readback=20)
PLACEHOLDER = dict(add_psum_out=[0, 100, 200], xs_out=[0, 8, 16, 24, 32, 40], silu_out=[0, 8], red_vm=100,
                   root_cfg_lead=4, d2d=dict(v=list(range(16)), rs=[0], qn=list(range(16)), rope_q=list(range(8)),
                                             rope_k=list(range(8)), gur=list(range(32)), readback=list(range(48))),
                   source='calibration placeholder (PROG / CROM fields only)')


def variant(word, **chg):
    f = D.su_unpack(word)
    f.pop('go')
    f.update(chg)
    return D.su_word(**f)


def bench_words(lw):
    """bench-only probe / readback words (pidx 16..20) appended to every slice image"""
    vm = lw['vm']
    out = {}
    for s in range(N):
        img = [int(w, 16) for w in lw['prog'][s]]
        img += [0] * (max(BENCH_PIDX.values()) + 1 - len(img))
        n = len(lw['ownership']['residual']['blocks_per_slice'][s])
        img[BENCH_PIDX['readback']] = D.su_word(nout=n, nin=BLOCK, a=vm['X']['base'], aso=BLOCK, asi=1, dst=V.DST_VM,
                                                d=D.W_D2D, dso=BLOCK, dsi=1)
        if lw['qkv_roles'].get(s, {}).get('role') in ('q', 'k'):
            img[BENCH_PIDX['qkr_ps']] = variant(img[V.PIDX['qkr']], rb=D.W_SC)
            img[BENCH_PIDX['rs_dd']] = variant(img[V.PIDX['rs']], d=D.W_D2D)
            img[BENCH_PIDX['qn_dd']] = variant(img[V.PIDX['qn']], d=D.W_D2D)
        img[BENCH_PIDX['gur_dd']] = variant(img[V.PIDX['gur']], d=D.W_D2D)
        out[s] = img
    return out


def land(ev, t, s, base, vals):
    """bench stimulus: vals into slice s at local base over the AR return chain (one PORTS window, generous gaps)"""
    ev.cmd(t, D.cmd_ports(s, ar_base=base, ar_en=1))
    t += 2 * s + 6
    for w in range(0, len(vals), 16):
        ev.at(t, P_ARET, B.ar_word(vals[w:w + 16]))
        t += 1
    t += s + 6
    ev.cmd(t, D.cmd_ports(s, ar_base=base, ar_en=0))
    return t + 2 * s + 8


def boot(ev, imgs):
    ev.cmd(T0, D.cmd_setid(0))
    t = T0 + 2 * N + 6
    for s in range(N):
        for a, p in D.prog_words(imgs[s]):
            ev.at(t, P_SWI, D.stream_table_word(3, s, a, p))
            t += 1
    return t + 2 * N + 8


def lowered(ev, lw, base):
    for w in lw['crom_table']:
        ev.at(base + w['edge'], P_SWI, D.stream_table_word(1, w['dst'], w['eaddr'], int(w['payload'], 16)))
    for w in lw.get('rope_return', []):            # QW-LAYERGAP: the RoPE row as group-1 dr words (native59 format)
        ev.at(base + w['edge'], P_DRET, int(w['word'], 16))
    for c in lw['commands']:
        ev.cmd(base + c['edge'], int(c['cmd'], 16))
    return base + max(c['edge'] for c in lw['commands'])


def bf16_bits(x):
    return (B.fbits(G.to_bf16(np.asarray(x, dtype=F))) >> 16).astype(np.int64)


def e5_words(log):
    """{cycle: (src, eaddr, payload)} of kind-0 (x) words leaving the E5 end"""
    out = {}
    for c, w in log.get(f'S{N - 1}E', []):
        if (w >> 1087) & 1 and ((w >> 1084) & 7) == 0:
            out[c] = ((w >> 1076) & 0xF, (w >> 1052) & 0xFFFFFF, w & ((1 << 1024) - 1))
    return out


def dd_words(log):
    """[(cycle, kind, [(addr, value)])] of D2D words leaving W5"""
    out = []
    for c, w in log.get('S0DD', []):
        k, mask = (w >> 545) & 3, (w >> 537) & 0xFF
        out.append((c, k, [((w >> (89 + 256 + 24 * l)) & 0xFFFFFF, (w >> (89 + 32 * l)) & 0xFFFFFFFF)
                           for l in range(8) if mask >> l & 1]))
    return out


def consts_for(rng, pos=1234):
    return dict(ps1=G.to_bf16((1.0 + 0.3 * rng.standard_normal(4096)).astype(F)),
                ps2=G.to_bf16((1.0 + 0.3 * rng.standard_normal(4096)).astype(F)),
                q_norm=G.to_bf16((1.0 + 0.3 * rng.standard_normal(128)).astype(F)),
                k_norm=G.to_bf16((1.0 + 0.3 * rng.standard_normal(128)).astype(F)), pos=pos)


# ------------------------------------------------------------------------------------------------ calibrate
def calibrate(work, seed):
    rng = np.random.default_rng(seed)
    consts = consts_for(rng)
    lw = {m: V.lower_vec(m, ages=PLACEHOLDER, consts=consts) for m in ('resid', 'qk', 'silu')}
    imgs = bench_words(lw['resid'])
    vm, P, arr = lw['resid']['vm'], V.PIDX, lw['resid']['slice_map']['cmd_arrival']
    ev = LB.Events()
    t = boot(ev, imgs)
    for s, base, n in ((1, 'X', 384), (11, 'X', 256), (1, 'T', 384), (11, 'T', 256), (10, 'X', 256),
                       (2, 'QKV', 128), (8, 'QKV', 128), (10, 'QKV', 128), (3, 'GU', 256)):
        t = land(ev, t, s, vm[base]['base'], (rng.standard_normal(n) * 0.5).astype(F))
    for s in (2, 3, 8, 10):
        t = land(ev, t, s, vm['RX']['base'], np.full(16, F(0.75)))
    for w in lw['qk']['crom_table'] + lw['resid']['crom_table']:
        ev.at(t, P_SWI, D.stream_table_word(1, w['dst'], w['eaddr'], int(w['payload'], 16)))
        t += 1
    t += 2 * N + 8
    for s in range(N):
        ev.cmd(t + s, D.cmd_root(s, int(s == 0), 32, vm['SSX']['base'], fuse=int(s == 0), rx=vm['RX']['base'],
                                 eps=lw['resid']['expected']['root']['eps'] if s == 0 else 0,
                                 k=lw['resid']['expected']['root']['k'] if s == 0 else 0))
    t += N
    for s in (1, 3, 10):
        ev.cmd(t, D.cmd_stream(s, 3, 7))
        t += 1
    t += 40
    probes = [('add', 1, P['res1']), ('add', 11, P['res1']), ('xs', 1, P['xs']), ('xs', 10, P['xs']),
              ('silu', 3, P['silu']), ('red_vm', 2, BENCH_PIDX['qkr_ps']), ('rs', 2, BENCH_PIDX['rs_dd']),
              ('qn', 2, BENCH_PIDX['qn_dd']), ('rope_q', 2, P['rlo']), ('rope_k', 8, P['rlo']), ('v', 10, P['qkr']),
              ('gur', 3, BENCH_PIDX['gur_dd']), ('readback', 1, BENCH_PIDX['readback'])]
    at = []
    for name, s, pidx in probes:
        ev.cmd(t, D.cmd_su(pidx, s))
        at.append((name, s, t))
        t += 800
    log = LB.run(work, 'cal', ev, t + 100)
    errs = B2.status_ok2(log)
    ps, e5, dd = LB.psums(log), e5_words(log), dd_words(log)
    meas = {}
    for name, s, te in at:
        lo, hi = te, te + 800
        if name in ('add', 'red_vm'):
            v = sorted(c - (te + arr[s]) for (m, c), _ in ps.items() if m == s and lo <= c < hi)
        elif name in ('xs', 'silu'):
            v = sorted(c - te - arr[s] - D.ST_HOP * (N - 1 - s) for c, (src, _, _) in e5.items() if src == s and lo <= c < hi)
        else:
            v = sorted(c - te - arr[s] - 2 * s for c, _, _ in dd if lo <= c < hi)
        meas[f'{name}@{s}'] = v
    print('CALIBRATE raw', json.dumps(meas))
    A = dict(schema='opentallas.qwen.dv-slice-vec-ages.v1', add_psum_out=meas['add@1'], xs_out=meas['xs@1'],
             silu_out=meas['silu@3'], red_vm=(meas['red_vm@2'] or [None])[-1], root_cfg_lead=4,
             d2d={k: meas[f'{k}@{s}'] for k, s in (('rs', 2), ('qn', 2), ('rope_q', 2), ('rope_k', 8), ('v', 10),
                                                    ('gur', 3), ('readback', 1))},
             per_probe=meas,
             source='rtl/test/qwen_dv/dv_lower_vec_bench.py --mode calibrate (tb_qfd_dv2 N 12, Verilator 5.050). '
                    'Offsets from the slice cmd landing (entry + 2 s): PSUM = leave edge of the slice dn_o (S<s>SD); '
                    'x = edge at the E5 end (S11E) - ST_HOP (11 - s); D2D = edge at W5 (S0DD) - 2 s; d2d rs / qn / gur are '
                    'the VM-only ops re-targeted to the D2D window (same pipeline) = their last-write ages; red_vm = '
                    'the head SSQ reducer result (PSUM-window variant) age')
    want = dict(add_psum_out=3, xs_out=6, silu_out=2)
    for k, n in want.items():
        if len(A[k]) != n:
            errs.append(f'{k}: {len(A[k])} offsets, want {n}')
    if meas['add@11'] != meas['add@1'][:2]:
        errs.append(f'add PSUM offsets differ by slice {meas["add@1"]} / {meas["add@11"]}')
    if meas['xs@10'] != meas['xs@1'][:4]:
        errs.append(f'x stream offsets differ by slice ({D.ST_HOP}-edge stream hop model, dv_lower.ST_HOP) {meas["xs@1"]} / {meas["xs@10"]}')
    for k, n in (('rs', 1), ('qn', 16), ('rope_q', 8), ('rope_k', 8), ('v', 16), ('gur', 32), ('readback', 48)):
        if len(A['d2d'][k]) != n:
            errs.append(f'd2d {k}: {len(A["d2d"][k])} words, want {n}')
    if A['red_vm'] is None:
        errs.append('no head-SSQ PSUM')
    (work / 'vec_ages.json').write_text(json.dumps(A, indent=1) + '\n')
    print(f'CALIBRATE {"PASS" if not errs else "FAIL"}')
    for e in errs[:10]:
        print('   ', e)
    return 0 if not errs else 1


# ------------------------------------------------------------------------------------------------ runs
def measured_span(base, cycles):
    """measured span = last checked output edge seen in the RTL log - the first lowered edge (base)"""
    return f'span_cycles={max(cycles) - base if cycles else None}'


def gold_check(fx, mine):
    """QW-REALSTG: the bench's own hdc_golden expectation vs the ISA golden's stage output in the fixture (TP4 ISA
    golden re-executed by tools/qwen_layerbench/dv_layer_fixture.py): bit-exact, else the check fails"""
    res = {}
    for k, v in mine.items():
        if k in fx:
            a, b = B.fbits(np.asarray(v, dtype=F)), B.fbits(fx[k].astype(F))
            res[k] = (int(np.sum(a == b)), len(b)) if len(a) == len(b) else (0, len(b))
    words = sum(n for _, n in res.values())
    return dict(res=res, info=f'isa_gold_words={sum(o for o, _ in res.values())}/{words}' if res else 'isa_gold=none')


def fold_gold(gold, ok, n, errs):
    for k, (o, m) in gold['res'].items():
        n += 1
        if o == m:
            ok += 1
        else:
            errs.append(f'ISA gold {k}: bench golden differs from the ISA golden in {m - o}/{m} words')
    return ok, n


def golden_res(x, t, ps, root):
    xn = G.add(G.mul(t, ps), x)
    eps = np.array([root['eps']], dtype=np.uint32).view(F)[0]
    r = G.rsqrt(G.add(G.mul(G.reduce_chunked(G.mul(xn, xn)), F(2.0 ** -root['k'])), eps))
    return xn, r


def run_resid(work, lw, rng, tag):
    consts = lw['_consts']
    vm, own = lw['vm'], lw['ownership']['residual']['blocks_per_slice']
    x = (rng.standard_normal(4096) * rng.choice([0.05, 1.0, 30.0])).astype(F)
    x[rng.integers(0, 4096, 8)] *= F(50)
    x = (x * np.repeat(F(10.0) ** rng.uniform(-1.5, 1.5, 32).astype(F), 128)).astype(F)
    tv = (rng.standard_normal(4096) * 0.3 * np.repeat(F(10.0) ** rng.uniform(-1, 1, 32).astype(F), 128)).astype(F)
    fx = lw.get('_fix') or {}
    if 'x' in fx:                                      # QW-REALSTG: real stage operands (dv_layer_fixture.py)
        x, tv = fx['x'].astype(F), fx['t'].astype(F)
    xn, r = golden_res(x, tv, consts['ps1'], lw['expected']['root'])
    gold = gold_check(fx, dict(gold_x=xn, gold_r=np.array([r], dtype=F)))
    ev = LB.Events()
    imgs = bench_words(lw)
    t = boot(ev, imgs)
    for s in range(N):
        t = land(ev, t, s, vm['X']['base'], np.concatenate([x[BLOCK * b:BLOCK * (b + 1)] for b in own[s]]))
    base = t + 8
    for a in lw['ar_return']:
        w0 = BLOCK * a['block'] + 16 * a['word']
        ev.at(base + a['edge'], P_ARET, B.ar_word(tv[w0:w0 + 16]))
    end = lowered(ev, lw, base) + 900
    rb_at = {}
    for s in range(N):                                 # bench-only readback of x', one slice at a time
        ev.cmd(end, D.cmd_su(BENCH_PIDX['readback'], s))
        rb_at[s] = end
        end += 260
    log = LB.run(work, f'run_{tag}', ev, end + 100)
    errs = B2.status_ok2(log)
    ok, n = 0, 0
    exp = B.u32(r)
    for s in range(N):
        n += 1
        rb = [w & 0xFFFFFFFF for _, w in log.get(f'S{s}SU', []) if (w >> 44) & 7 == 2]
        if rb == [exp]:
            ok += 1
        else:
            errs.append(f'slice {s}: RB {[hex(v) for v in rb]} want [{exp:#010x}]')
    n += 1
    ps = LB.psums(log)
    want = {tuple(int(v) for v in k.split(',')): tag_ for k, tag_ in lw['expected']['psum'].items()}
    want = {(m, base + e): tg for (m, e), tg in want.items()}
    miss = {k: v for k, v in want.items() if ps.get(k) != v}
    extra = {k: v for k, v in ps.items() if k not in want}
    if miss or extra:
        errs.append(f'PSUM schedule: {len(miss)}/{len(want)} off their edge/tag (first {sorted(miss.items())[:3]}), '
                    f'{len(extra)} unscheduled (first {sorted(extra.items())[:3]})')
    else:
        ok += 1
    n += 1
    e5 = e5_words(log)
    span = measured_span(base, [c for c in e5 if base <= c < rb_at[0]] + [c for (_, c) in ps if c >= base])
    hb = bf16_bits(xn)
    bad = []
    for xw in lw['expected']['x']:
        c = base + xw['edge_e5']
        got = e5.get(c)
        pay = sum(int(h) << (16 * i) for i, h in enumerate(hb[xw['eaddr']:xw['eaddr'] + 64]))
        if got is None or got[1] != xw['eaddr'] or got[2] != pay:
            bad.append((xw['slice'], xw['eaddr'], c, None if got is None else got[1]))
    nx = sum(1 for c, (src, ea, _) in e5.items() if c >= base)
    if bad or nx != len(lw['expected']['x']):
        errs.append(f'x stream: {len(bad)}/{len(lw["expected"]["x"])} words wrong / off edge (first {bad[:3]}), '
                    f'{nx} x words at E5')
    else:
        ok += 1
    dd = dd_words(log)
    for s in range(N):
        n += 1
        got = {}
        for c, k, lst in dd:
            if rb_at[s] <= c < rb_at[s] + 260:
                got.update(lst)
        want_x = np.concatenate([xn[BLOCK * b:BLOCK * (b + 1)] for b in own[s]])
        before = len(errs)
        B.cmp(f'slice {s} x\' (readback)', got, B.fbits(want_x), errs)
        if len(errs) == before and len(got) == len(want_x):
            ok += 1
        elif len(errs) == before:
            errs.append(f'slice {s} readback: {len(got)} elements')
    ok, n = fold_gold(gold, ok, n, errs)
    return ok, n, errs, f'r={exp:#010x} x_words={len(lw["expected"]["x"])} psums={len(want)} {span} {gold["info"]}'


def run_qk(work, lw, rng, tag):
    consts = lw['_consts']
    vm, roles = lw['vm'], lw['qkv_roles']
    qkv = (rng.standard_normal(768) * np.repeat(rng.uniform(0.5, 4.0, 6), 128)).astype(F)
    r = F(rng.uniform(0.3, 3.0))
    fx = lw.get('_fix') or {}
    if 'qkv' in fx:                                    # QW-REALSTG: real stage operands
        qkv, r = fx['qkv'].astype(F), F(fx['r'][0])
    ev = LB.Events()
    t = boot(ev, bench_words(lw))
    for s in sorted(roles):
        b = roles[s]['block']
        t = land(ev, t, s, vm['QKV']['base'], qkv[BLOCK * b:BLOCK * (b + 1)])
        t = land(ev, t, s, vm['RX']['base'], np.full(16, r))
    base = t + 8
    end = lowered(ev, lw, base) + 900
    log = LB.run(work, f'run_{tag}', ev, end)
    errs = B2.status_ok2(log)
    eps = np.array([lw['isa']['head_eps']], dtype=np.uint32).view(F)[0]
    cos, sin, half = G.rope_tables(consts['pos'], 128, V.ROPE_THETA)
    want = {}
    for s, ro in roles.items():
        v = qkv[BLOCK * ro['block']:BLOCK * (ro['block'] + 1)]
        qr = G.mul(v, r)
        if ro['role'] == 'v':
            out, kind, a0 = G.to_fp8(qr), 2, 0
        else:
            rs = G.rsqrt(G.add(G.mul(G.reduce_chunked(G.mul(qr, qr)), F(2.0 ** -7)), eps))
            qn = G.mul(G.mul(qr, rs), consts['q_norm' if ro['role'] == 'q' else 'k_norm'])
            out = G.rope(qn, cos, sin, half)
            kind, a0 = (0, 128 * ro['head']) if ro['role'] == 'q' else (1, 0)
            if ro['role'] == 'k':
                out = G.to_fp8(out)
        for i in range(128):
            want[(kind, a0 + i)] = int(B.fbits(out)[i])
    dd = dd_words(log)
    span = measured_span(base, [c for c, _, _ in dd if c >= base])
    gw = {}
    if 'gold_q' in fx:
        vals = lambda k, m: np.array([want[(k, i)] for i in range(m)], dtype=np.uint32).view(F)
        gw = dict(gold_q=vals(0, 512), gold_k=vals(1, 128), gold_v=vals(2, 128))
    gold = gold_check(fx, gw)
    got = {}
    for c, k, lst in dd:
        for a, v in lst:
            if (k, a) in got:
                errs.append(f'D2D ({k}, {a}) twice')
            got[(k, a)] = v
    ok, n = 0, 0
    for role, kind in (('q', 0), ('k', 1), ('v', 2)):
        keys = [k for k in want if k[0] == kind]
        n += 1
        bad = [k for k in keys if got.get(k) != want[k]]
        if bad:
            k = bad[0]
            errs.append(f'{role}: {len(bad)}/{len(keys)} mismatches, first {k} got '
                        f'{None if got.get(k) is None else hex(got[k])} want {want[k]:#010x}')
        else:
            ok += 1
    n += 1
    edges = sorted(base + d['edge_w5'] for d in lw['expected']['d2d'])
    seen = sorted(c for c, _, _ in dd)
    if edges != seen:
        errs.append(f'D2D edges: {len(seen)} words at W5, {len(edges)} compiled; first differing '
                    f'{next(((a, b) for a, b in zip(edges, seen) if a != b), None)}')
    else:
        ok += 1
    if len(got) != len(want):
        errs.append(f'{len(got)} D2D elements, want {len(want)}')
    ok, n = fold_gold(gold, ok, n, errs)
    return ok, n, errs, f'q heads 4 / k / v, d2d words={len(edges)} {span} {gold["info"]}'


def run_silu(work, lw, rng, tag):
    vm = lw['vm']
    gu = (rng.standard_normal((N, 256)) * 2.5).astype(F)
    gu[0, :8] = F([-100.0, -88.5, -20.0, 0.0, 95.0, 1e-30, -1e-30, 40.0])
    r = F(rng.uniform(0.3, 3.0))
    fx = lw.get('_fix') or {}
    if 'gu' in fx:                                     # QW-REALSTG: real stage operands (no injected corner values)
        gu, r = fx['gu'].astype(F).reshape(N, 256), F(fx['r'][0])
    ev = LB.Events()
    t = boot(ev, bench_words(lw))
    for s in range(N):
        t = land(ev, t, s, vm['GU']['base'], gu[s])
        t = land(ev, t, s, vm['RX']['base'], np.full(16, r))
    base = t + 8
    end = lowered(ev, lw, base) + 900
    log = LB.run(work, f'run_{tag}', ev, end)
    errs = B2.status_ok2(log)
    act = np.concatenate([G.mul(G.silu(G.mul(gu[s, :128], r)), G.mul(gu[s, 128:], r)) for s in range(N)])
    gold = gold_check(fx, dict(gold_act=act))
    hb = bf16_bits(act)
    e5 = e5_words(log)
    span = measured_span(base, [c for c in e5 if c >= base])
    bad = []
    for xw in lw['expected']['x']:
        c = base + xw['edge_e5']
        got = e5.get(c)
        pay = sum(int(h) << (16 * i) for i, h in enumerate(hb[xw['eaddr']:xw['eaddr'] + 64]))
        if got is None or got[1] != xw['eaddr'] or got[2] != pay:
            bad.append((xw['slice'], xw['eaddr'], c, None if got is None else got[1]))
    nx = sum(1 for c in e5 if c >= base)
    ok = 0
    if bad or nx != len(lw['expected']['x']):
        errs.append(f'act stream: {len(bad)}/{len(lw["expected"]["x"])} words wrong / off edge (first {bad[:3]}), '
                    f'{nx} x words at E5')
    else:
        ok = 1
    ok, n = fold_gold(gold, ok, 1, errs)
    return ok, n, errs, f'act words={len(lw["expected"]["x"])} {span} {gold["info"]}'


def dr_word(beat, vals):
    """qfd_native59_dv_service dr_o group 0: {1'b1, 1'b0, 1'b0, beat[4:0], data[511:0]}"""
    data = sum(int(v) << (32 * j) for j, v in enumerate(B.fbits(np.asarray(vals, dtype=F))))
    return (1 << 519) | (beat << 512) | data


def run_attn(work, lw, rng, tag):
    att = (rng.standard_normal(512) * np.repeat(F(10.0) ** rng.uniform(-2, 1.5, 32).astype(F), 16)).astype(F)
    att[:4] = F([0.0, 7.5, 1.00390625, -1.01171875])  # zero, exact value, exact BF16 ties (RNE even / odd)
    ev = LB.Events()
    t = boot(ev, bench_words(lw))
    base = t + 8
    for d in lw['dd_return']:
        b = d['beat']
        ev.at(base + d['edge'], 40, dr_word(b, att[16 * b:16 * b + 16]))
    end = lowered(ev, lw, base) + 900
    log = LB.run(work, f'run_{tag}', ev, end)
    errs = B2.status_ok2(log)
    hb = bf16_bits(att)
    e5 = e5_words(log)
    bad = []
    for xw in lw['expected']['x']:
        c = base + xw['edge_e5']
        got = e5.get(c)
        pay = sum(int(h) << (16 * i) for i, h in enumerate(hb[xw['eaddr']:xw['eaddr'] + 64]))
        if got is None or got[1] != xw['eaddr'] or got[2] != pay:
            bad.append((xw['slice'], xw['eaddr'], c, None if got is None else got[1]))
    seen = sorted(c for c in e5 if c >= base)
    ok = 0
    if bad or len(seen) != len(lw['expected']['x']):
        errs.append(f'o_proj x stream: {len(bad)}/{len(lw["expected"]["x"])} words wrong / off edge (first {bad[:3]}), '
                    f'{len(seen)} x words at E5')
    else:
        ok = 1
    first = base + lw['dd_r0']
    span = (seen[-1] - first) if seen else None
    info = (f'owners={lw["attn_owners"]} x_words={len(seen)} MEASURED_SPAN first dr word at W5 pin (edge {first}) -> '
            f'last x word at E5 (edge {seen[-1] if seen else None}) = {span} edges (compiled '
            f'{max(x["edge_e5"] for x in lw["expected"]["x"]) - lw["dd_r0"]})')
    return ok, 1, errs, info


def main_run(work, mode, mutant, seed, ages, ar_order='slice', fixture=None, rope='stream'):
    rng = np.random.default_rng(seed)
    consts = consts_for(rng)
    fix = {}
    if fixture:                                        # QW-REALSTG: real stage operands + ISA gold outputs
        z = np.load(fixture)
        fix = {k: z[k] for k in z.files}
        for k in ('ps1', 'ps2', 'q_norm', 'k_norm'):
            if k in fix:
                consts[k] = fix[k].astype(F)
        if 'pos' in fix:
            consts['pos'] = int(fix['pos'])
    lw = V.lower_vec(mode, mutant, ages=ages, consts=consts, ar_order=ar_order, rope=rope)
    (work / f'lowering_{mode}.json' if not mutant else work / f'lowering_{mode}_{mutant}.json').write_text(
        json.dumps(lw, indent=1) + '\n')
    lw['_consts'] = consts
    lw['_fix'] = fix
    tag = f'{mode}_{mutant or "m0"}'
    ok, n, errs, info = dict(resid=run_resid, qk=run_qk, silu=run_silu, attn=run_attn)[mode](work, lw, rng, tag)
    verdict = 'PASS' if ok == n and not errs else 'FAIL'
    print(f'DV_LOWER_VEC {mode} {verdict} {ok}/{n} mutant={mutant or 0} commands={len(lw["commands"])} '
          f'collisions={len(lw["collisions"])} ar_order={ar_order} rope={rope} fixture={Path(fixture).name if fixture else 0} {info}')
    for e in errs[:10]:
        print('   ', e)
    return 0 if verdict == 'PASS' else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--work', required=True)
    ap.add_argument('--mode', required=True, choices=('calibrate', 'resid', 'qk', 'silu', 'attn'))
    ap.add_argument('--mutant')
    ap.add_argument('--ar-order', choices=('slice', 'row'), default='slice',
                    help='residual AR return order; row matches the production collective')
    ap.add_argument('--ages', help='vec_ages.json (default: the committed one)')
    ap.add_argument('--seed', type=int, default=1)
    ap.add_argument('--rope', choices=('stream', 'rx'), default='stream',
                    help='QW-LAYERGAP: rx = RoPE row over the D2D return chain (needs the RP 1 slice: DV_LOWER_VFLAGS=-GRP=1)')
    ap.add_argument('--fixture', help='npz of real stage operands + ISA gold (tools/qwen_layerbench/dv_layer_fixture.py)')
    a = ap.parse_args()
    work = Path(a.work)
    work.mkdir(parents=True, exist_ok=True)
    if a.mode == 'calibrate':
        return calibrate(work, a.seed)
    ages = V.load_ages(a.ages) if a.ages else None
    return main_run(work, a.mode, a.mutant, a.seed, ages, a.ar_order, a.fixture, a.rope)


if __name__ == '__main__':
    raise SystemExit(main())
