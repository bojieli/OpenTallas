#!/usr/bin/env python3
"""QLB-C4b/3b 10-18 (G-C4): the matrix-side DV slice lowering (tools/qwen_layerbench/dv_lower_mat.py) on the 12-slice
qfd_dv_slice2 die chain (tb_qfd_dv2.sv N 12, the dv_lower_bench build), Verilator 5.050.

    dv_lower_mat_bench.py --work DIR --calibrate
    dv_lower_mat_bench.py --work DIR --run qkv|gu|od|lm|emb [--mutant M] [--ages FILE] [--seed N]

Stimulus = what the compiler emitted (every command on its compiled edge at dvs_W5.cmd_wi, the BTAB scale table and the
bench readback PROG words as stream table words on dvs_W5.st_wi -- tied idle on the die: dv_lower die gap) plus the
TILE-DELIVERY CONTRACT the lowering outputs: the golden level-6 cluster words (tools/hdc_golden matvec chunk sums,
rtl/test/qwen_dv/dv_bench.l6_parts) on each slice's rs ports at the compiled far / near edges, the embedding row on the
D2D return pin at the provider slots, the 8 all-gather returns at the io_collective timing.
Checks (bit-exact vs hdc_golden: y = matvec(w, x, split) * bf16 row scale):
  qkv / gu  every receiver / finishing slice's VM QKV / GU region (read back by a bench-only SU copy to the D2D window)
  od        o and down: all 256 AR words of each message leave dvs_W5 on their compiled edge (global row order, one an
            edge = io_collective's c + 1 + w), tag = global row element address, data exact; XC: ONE cc word at dvs_W5
            on its compiled edge, no other slice; the io_collective in-pin contract (tag == cmd tag, last only on the
            message's last word) is REPORTED (RTL gap), not part of PASS
  lm        LM head (18,992 rows, 25 rounds, 6 receivers): die argmax token at every slice (TOK), the ARX AR word exact,
            the XC gather word, the cross-die GATHER token at every slice
  emb       stage 0: every slice's X region holds exactly its residual blocks of the embedding row
  all       no slice fault, no station busy at the end.
--calibrate measures the constants the lowering reads (stn_ages.json): l8_ar, ar_hop, amax_ami, arx_after_amv, xc_cc.
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
import dv_bench as B          # noqa: E402
import dv_bench2 as B2        # noqa: E402
import dv_lower as D          # noqa: E402
import dv_lower_bench as LB   # noqa: E402
import dv_lower_mat as M      # noqa: E402

G, F = B.G, B.F
N = D.NSLICE
P_CMD, P_ARET, P_DRET, P_SWI = 0, 1, 40, 41
SK = 14
KC = 2
RB_PIDX = dict(QKV=500, GU=501, X=502)
ARF = dict(on=False)   # QW-LAYERGAP --arf: the slice AR message framer (qfd_dv_slice2 ARF 1) contract is part of PASS


def P_RSS(k):
    return 2 + 2 * k


def P_RSN(k):
    return 3 + 2 * k


def put_chain(ev, base, chain_cmds):
    for c in chain_cmds:
        ev.cmd(base + c['edge'], int(c['cmd'], 16))


def readback_words(regions, xbase):
    """bench-only SU copies of a region to the D2D window: address (slice << 12) | element"""
    out = {}
    for s in range(N):
        w = [D.su_word(nout=1, nin=regions['QKV']['size'], a=regions['QKV']['base'], asi=1, dst=1, d=D.W_D2D | (s << 12), dsi=1),
             D.su_word(nout=1, nin=regions['GU']['size'], a=regions['GU']['base'], asi=1, dst=1, d=D.W_D2D | (s << 12), dsi=1),
             D.su_word(nout=1, nin=3 * D.BLOCK, a=xbase, asi=1, dst=1, d=D.W_D2D | (s << 12), dsi=1), 0]
        out[s] = [(250, w[0] | (w[1] << 512)), (251, w[2] | (w[3] << 512))]
    return out


def prelude(ev, t, btab=None):
    """SETID, the BTAB tables (kind 2) and the readback PROG words (kind 3) on dvs_W5.st_wi."""
    own = D.ownership()
    regions = M.vm_regions(own)
    ev.cmd(t, D.cmd_setid(0))
    t += 2 * N + 6
    rb = readback_words(regions, D.vm_map(own)['X']['base'])
    for s in range(N):
        for w0, pay in (btab or {}).get(s, []):
            ev.at(t, P_SWI, D.stream_table_word(2, s, w0, pay))
            t += 1
        for ea, pay in rb[s]:
            ev.at(t, P_SWI, D.stream_table_word(3, s, ea, pay))
            t += 1
    return t + 2 * N + 8, regions


def readback(ev, t, region, slices):
    """one copy per slice, far apart (bench observation only)"""
    for s in slices:
        ev.cmd(t, D.cmd_su(RB_PIDX[region], s))
        t += 2 * s + 450
    return t


def dd_by_slice(log):
    vals = B.dd_values(log, 'S0DD')
    out = {}
    for a, v in vals.items():
        out.setdefault(a >> 12, {})[a & 0xFFF] = v
    return out


def mat(rng, rows, split, kc):
    w = rng.integers(-127, 128, size=(rows, split * kc)).astype(F)
    x = (rng.standard_normal(split * kc) * 2.0).astype(F)
    s = G.to_bf16((rng.random(rows) * 0.02 + 1e-3).astype(F))
    parts = B.l6_parts(w, x, split)
    return dict(w=w, x=x, s=s, parts=parts, y=None)


def expect_y(name, gm, split):
    """bench expectation with the compiler's station row scale (o / down: 1.0; others: the matrix scale)"""
    if gm['y'] is None:
        gm['y'] = B.fbits(G.mul(G.matvec(gm['w'], gm['x'], split), M.station_row_scales(name, gm['s'])))
    return gm


FIX = {}                                              # QW-REALSTG: --fixture npz (dv_layer_fixture.py)


def real_mat(name, split):
    """real int8 rows / BF16 scales / matvec input of the fixture (TP8 die 0 cut of the recorded ISA golden)"""
    pre = '' if name in ('qkv', 'gu') else f'{name}_'
    w, x, sc = FIX[pre + 'w'].astype(F), FIX[pre + 'x'].astype(F), FIX[pre + 's'].astype(F)
    if 'split' in FIX and int(FIX['split']) != split:
        raise SystemExit(f'fixture split {int(FIX["split"])} != ownership split {split}')
    parts = B.l6_parts(w, x, split)
    # s = the MATRIX row scales (the compiler's input); the expectation applies the COMPILER's station row scale
    # (dv_lower_mat.station_row_scales: o / down -> BF16 1.0, the ISA all-reduces RAW partials -- QW-ODSCALE)
    y = G.mul(G.matvec(w, x, split), M.station_row_scales(name, sc))
    return dict(w=w, x=x, s=sc, parts=parts, y=B.fbits(y))


def gold_y(gm, errs):
    """the bench's hdc_golden y vs the ISA golden's VM rows (fixture gold_y), bit-exact"""
    if 'gold_y' not in FIX:
        return 0, 0, 'isa_gold=none'
    g = B.fbits(FIX['gold_y'].astype(F))
    o = int(np.sum(g == gm['y']))
    if o != len(g):
        errs.append(f'ISA gold y: bench golden differs from the ISA golden in {len(g) - o}/{len(g)} rows')
    return int(o == len(g)), 1, f'isa_gold_words={o}/{len(g)}'


def l6_running_parts(gm, split):
    """Actual per-k FP32 recurrence, then the same 64-chunk tree as B.l6_parts.

    This is stimulus at the cluster-output cut. It does not replace a MAC DUT.
    Every prefix starts from +0, BF16-rounds x, and uses G.mul/G.add exactly as
    hdc_golden.matvec_fp32. The final prefix must equal the existing final golden.
    """
    if 'running_parts' in gm:
        return gm['running_parts']
    w, xb = gm['w'], G.to_bf16(gm['x'])
    kc = w.shape[1] // split
    if kc * split != w.shape[1]:
        raise M.LowerError('running-partial split does not divide the matrix K')
    chunks = [np.zeros(w.shape[0], dtype=F) for _ in range(split)]
    result = []
    for k in range(kc):
        for c in range(split):
            chunks[c] = G.add(chunks[c], G.mul(w[:, c * kc + k], xb[c * kc + k]))
        parts = []
        for cl in range(split // 64):
            tree = chunks[64 * cl:64 * (cl + 1)]
            while len(tree) > 1:
                tree = [G.add(tree[i], tree[i + 1]) for i in range(0, len(tree), 2)]
            parts.append(tree[0])
        result.append(parts)
    if any(not np.array_equal(B.fbits(a), B.fbits(b)) for a, b in zip(result[-1], gm['parts'])):
        raise M.LowerError('running-partial final prefix differs from existing l6_parts golden')
    gm['running_parts'] = result
    return result


def drive(ev, low, gm, mutant=None):
    """Drive all k*8 running words; the existing far[] edges name the FINAL block.

    Last-k selection and the production kc field remain active. Earlier prefixes
    carry genuine recurrence values, rather than copies of the final output.
    """
    lv, kc = low['level'], low['kc']
    sequence = l6_running_parts(gm, 64 * len(gm['parts']))
    if len(sequence) != kc:
        raise M.LowerError(f'producer kc {len(sequence)} != compiled station kc {kc}')
    for d in low['deliveries']:
        s = d['slice']
        for k, parts in enumerate(sequence):
            if mutant == 'drop_last_k' and k == kc - 1:
                continue
            for j, last_tf in enumerate(d['far']):
                tf = last_tf - (kc - 1 - k) * low['k_block_words']
                if lv == 7:
                    b0, b1 = d['blocks']
                    r0, r1 = D.BLOCK * b0 + 16 * j, D.BLOCK * b1 + 16 * j
                    LB_pair(ev, s, parts[0][r0:r0 + 16], parts[1][r0:r0 + 16], parts[1][r1:r1 + 16], parts[0][r1:r1 + 16], tf)
                else:
                    b = d['blocks'][0]
                    r0 = D.BLOCK * b + 16 * j
                    o = 4 if d['role'] == 'snd' else 0
                    LB_pair(ev, s, parts[o][r0:r0 + 16], parts[o + 1][r0:r0 + 16], parts[o + 3][r0:r0 + 16],
                            parts[o + 2][r0:r0 + 16], tf)


def LB_pair(ev, s, lo_far, lo_near, hi_far, hi_near, t):
    pad = lambda v: np.concatenate([v, np.zeros(16 - len(v), dtype=F)]) if len(v) < 16 else v
    ev.at(t, P_RSS(s), B.cluster_word(pad(lo_far)) << 514)
    ev.at(t - SK, P_RSS(s), B.cluster_word(pad(lo_near)))
    ev.at(t, P_RSN(s), B.cluster_word(pad(hi_far)) << 514)
    ev.at(t - SK, P_RSN(s), B.cluster_word(pad(hi_near)))


def check_vm(low, region_vals, ybits, errs, tag):
    ok = n = 0
    for s, amap in low['expected_vm'].items():
        got = region_vals.get(s, {})
        base = min(amap)
        for a, row in amap.items():
            for l in range(16):
                n += 1
                if row + l >= len(ybits):
                    n -= 1
                    continue
                g = got.get(a - base + l)
                if g == int(ybits[row + l]):
                    ok += 1
                elif len(errs) < 40:
                    errs.append(f'{tag} slice {s} row {row + l}: got {g if g is None else hex(g)} exp {int(ybits[row + l]):#010x}')
    return ok, n


# ------------------------------------------------------------------------------------------------ calibrate
def calibrate(work, seed):
    rng = np.random.default_rng(seed)
    ev = LB.Events()
    t, _ = prelude(ev, LB.T0)
    v = lambda: (rng.standard_normal(16) * 3).astype(F)
    probes = {}
    for s in (0, N - 1):                                   # L8 AR, unscaled
        land = t
        # The ARF-enabled positive vehicle must have one root framer arm per
        # eight-word probe, before its first AR word. ARF=0 ignores the arm.
        far = land + 10
        ev.cmd(land - 2 * s - 1, D.cmd_xc(0, 0, 8, 0x100 * (s + 1)))
        # TOK-QK/S8B 10-25: the STN lands M.STN_LEAD edges before the first far word (the compiler's rule, after the
        # near words that run SK ahead).  It used to land 10 before far = inside the near words: the s8 / safe stations
        # (cfg_schedule_fault: cfg_v landing while rs / nb words land) fault on that; slice2 tolerated it.
        ev.cmd(far - M.STN_LEAD - 2 * s, D.cmd_stn(s, 1, 1, 8, 0, M.DST_AR, 0x100 * (s + 1), kc=1))
        for j in range(8):
            LB_pair(ev, s, v(), v(), v(), v(), far + j)
        probes[s] = far
        t += 200
    xc_e = t
    # This marker also arms the final one-word AMAX/ARX gather message. Seven
    # words would leave the framer armed after the single actual ARX result.
    ev.cmd(xc_e, D.cmd_xc(0, 1, 1, 0x55))
    t += 40
    # AMAX: root s0 (amnb 2) + s5; ARX armed on the root
    ev.cmd(t - 2, D.cmd_amax(15, clear=1))  # MU lifecycle: user 0 must be open before AMAX results
    ev.cmd(t, D.cmd_root(0, 1, 32, 0, amnb=2))
    ev.cmd(t + 1 - 10, D.cmd_root(5, 0, 0, 0))
    ev.cmd(t + 2, D.cmd_amax(0, arx=1))
    t += 30
    for s in (0, 5):
        ev.cmd(t + 10 - M.STN_LEAD - 2 * s - 1, D.cmd_stn(s, 1, 1, 8, 0, 0, 0x40 * s, amax=1, kc=1))   # as above
    for j in range(8):
        for s in (0, 5):
            LB_pair(ev, s, v(), v(), v(), v(), t + 10 + j)
    t += 120
    ev.cmd(t, D.cmd_amax(0, emit=1))
    e5 = t + 40
    ev.cmd(e5 - 10, D.cmd_amax(5, emit=1))
    log = LB.run(work, 'cal', ev, e5 + 300)
    errs = B2.status_ok2(log)
    ar = [c for c, _ in log.get('S0AR', [])]
    l8 = ar[0] - probes[0]
    a11 = [c for c in ar if c > probes[N - 1]][0]
    hop = (a11 - probes[N - 1] - l8) / (N - 1)
    # Probe pre-arms produce earlier CC pulses; measure only this unique marker.
    cc = [c for c, word in log.get('S0CC', []) if (word & 0xFFFFFFFF) == 0x55]
    ami = [c for c, w in log.get('S5SD', []) if (w >> 44) & 7 == 3]
    amv1 = [c for c, w in log.get('S1SD', []) if (w >> 44) & 7 == 4]
    arx = [c for c, w in log.get('S0AR', []) if (w >> 513) & 1 and c > e5]
    rec = dict(schema='opentallas.qwen.dv-mat-ages.v1', l8_ar=l8, ar_hop=hop, xc_cc=cc[0] - xc_e if cc else None,
               amax_ami=ami[0] - e5 if ami else None, arx_after_amv=(arx[0] - amv1[-1]) if arx and amv1 else None,
               source='rtl/test/qwen_dv/dv_lower_mat_bench.py --calibrate (tb_qfd_dv2 N 12, Verilator 5.050): l8_ar = '
                      'S0AR edge of word 0 - far-word edge (slice 0, L8, AR dst); ar_hop from slice 11; xc_cc = S0CC edge - '
                      'XC chain entry; amax_ami = AMI leaving slice 5 dn_o - emit landing (entry + cmd arrival); '
                      'arx_after_amv = ARX AR word at W5 - the last AMV leaving slice 1 dn_o',
               faults=errs)
    (work / 'stn_ages.json').write_text(json.dumps(rec, indent=1) + '\n')
    print('CALIBRATE', json.dumps({k: v for k, v in rec.items() if k not in ('source',)}))
    bad = errs or any(rec[k] is None for k in ('xc_cc', 'amax_ami', 'arx_after_amv')) or hop != 2
    print('CALIBRATE', 'FAIL' if bad else 'OK')
    return 1 if bad else 0


# ------------------------------------------------------------------------------------------------ runs
def run_vm(work, name, ages, rng, mutant):
    m = D.ownership()[name]
    gm = real_mat(name, m['split']) if FIX else expect_y(name, mat(rng, m['blocks'][-1]['rows'][1], m['split'], M.STN_KC[name]), m['split'])
    lay = M.btab_layout(D.ownership())
    tabs = M.btab_stream(lay, {name: gm['s']})
    ev = LB.Events()
    t, regions = prelude(ev, LB.T0, tabs)
    ch = M.Chain(D.slice_map())
    low = M.lower_matvec(name, 400, ages, ch, mutant=mutant, running_k=True)
    base = t + 20 - min(c['edge'] for c in ch.commands())
    put_chain(ev, base, ch.commands())
    for d in low['deliveries']:
        d['far'] = [f + base for f in d['far']]
    drive(ev, low, gm, mutant)
    t = max(f for d in low['deliveries'] for f in d['far']) + 200
    reg = 'GU' if name == 'gu' else 'QKV'
    t = readback(ev, t, reg, sorted(low['expected_vm']))
    log = LB.run(work, f'{name}_{mutant or "m0"}', ev, t + 100)
    errs = B2.status_ok2(log)
    ok, n = check_vm(low, dd_by_slice(log), gm['y'], errs, name)
    go, gn, ginfo = gold_y(gm, errs)
    last = max(f for d in low['deliveries'] for f in d['far'])
    vw = vm_writes(log, low)
    return ok + go, n + gn, errs, dict(stn=len(low['stn']), slices=sorted(low['expected_vm']), isa_gold=ginfo,
                                       delivery_span_cycles=None if vw['last'] is None else vw['last'] - base,
                                       delivery_span_origin='chain schedule base (same origin as od span_cycles and the legacy anchor)',
                                       legacy_schedule_anchor_span_cycles=last - base,
                                       first_stn_command_edge=base + min(c['edge'] for c in ch.commands()),
                                       first_cluster_word_edge=min(d['far'][0] - low['prefix_edges'] - SK for d in low['deliveries']),
                                       last_cluster_word_edge=last,
                                       first_vm_write_edge=vw['first'], last_vm_write_edge=vw['last'],
                                       vm_write_window_cycles=None if vw['last'] is None else vw['last'] - vw['first'],
                                       vm_writes_observed=vw['observed'], vm_writes_expected=vw['expected'],
                                       vm_write_addresses_missing=vw['missing'], vm_write_observability=vw['scope'],
                                       producer_kc=low['kc'],
                                       producer_words_per_cluster_per_round=8 * low['kc'],
                                       producer_scope='STN/VM cut-boundary protocol; upstream MAC arithmetic not simulated here',
                                       span_note='legacy anchor span is not measured VM latency; input pin edges and readback/drain bounds are recorded separately')


def vm_writes(log, low):
    """Actual VM-write edges of the station results (tb_qfd_dv2 S<k>VW: st_vm write port, 24-bit word address).
    Only writes to this matvec's expected VM words count; edges stay None when the binary has no probe."""
    want = {(s, a) for s, amap in low['expected_vm'].items() for a in amap}
    hits = [(c, s, a) for s in low['expected_vm'] for c, a in log.get(f'S{s}VW', []) if (s, a & 0xFFFFFF) in want]
    probed = any(k.endswith('VW') and k[1:-2].isdigit() for k in log)
    seen = {(s, a) for _, s, a in hits}
    return dict(first=min(c for c, _, _ in hits) if hits else None, last=max(c for c, _, _ in hits) if hits else None,
                observed=len(hits), expected=len(want), missing=len(want - seen),
                scope=('tb_qfd_dv2 S<k>VW probe: station-result VM write (st_vm) edges at the expected word addresses'
                       if probed else 'binary has no S<k>VW VM-write probe lines; edges unknown'))


def run_od(work, ages, rng, mutant):
    own = D.ownership()
    lay = M.btab_layout(own)
    gms = {n: (real_mat(n, own[n]['split']) if FIX else expect_y(n, mat(rng, 4096, own[n]['split'], M.STN_KC[n]), own[n]['split']))
           for n in ('o', 'down')}
    tabs = M.btab_stream(lay, {n: g['s'] for n, g in gms.items()}, mutant=mutant)   # matrix scales in; BTAB 1.0 out
    ev = LB.Events()
    t, _ = prelude(ev, LB.T0, tabs)
    ch = M.Chain(D.slice_map())
    lows, xcs = {}, {}
    w0 = {'o': 600, 'down': 1300}
    for k, n in enumerate(('o', 'down')):
        xcs[n] = M.lower_xc(ch, ages, w0[n], 256, k, mutant=mutant)          # exact edge: reserved first
        lows[n] = M.lower_matvec(n, w0[n], ages, ch, own=own, mutant=None if mutant in ('xc_bc', 'rawscale') else mutant, running_k=True)
    coll = {n: M.ar_collisions(lows[n], ages) for n in lows}
    if ARF['on']:
        M.ar_framer_order([(xcs[n], lows[n]['expected_ar']) for n in lows])
    base = t + 20 - min(c['edge'] for c in ch.commands())
    put_chain(ev, base, ch.commands())
    for n in lows:
        for d in lows[n]['deliveries']:
            d['far'] = [f + base for f in d['far']]
        drive(ev, lows[n], gms[n], mutant)
    end = base + max(w0.values()) + 400
    log = LB.run(work, f'od_{mutant or "m0"}', ev, end)
    errs = B2.status_ok2(log)
    ar = {c: w for c, w in log.get('S0AR', [])}
    ok = n_ = 0
    gap = []
    for n in ('o', 'down'):
        y = gms[n]['y']
        exp_ar = M.ar_framed(lows[n]['expected_ar'], xcs[n]) if ARF['on'] else lows[n]['expected_ar']
        for e in exp_ar:
            n_ += 1
            w = ar.get(base + e['edge'])
            want_d = sum(int(y[e['row'] + l]) << (32 * l) for l in range(16))
            if w is not None and (w >> 514) & 0xFFFFFFFF == e['tag'] and (w >> 512) & 1 == e['last'] and \
                    (w >> 513) & 1 == 0 and w & ((1 << 512) - 1) == want_d:
                ok += 1
            elif len(errs) < 30:
                errs.append(f'{n} AR word row {e["row"]} edge {base + e["edge"]}: got '
                            f'{None if w is None else hex((w >> 514) & 0xFFFFFFFF)} want tag {e["tag"]:#x}')
        # XC: one cc word at W5 on its edge, no other slice
        x = xcs[n]
        n_ += 1
        cc0 = [w for c, w in log.get('S0CC', []) if c == base + x['cc_edge']]
        if cc0 == [x['cc_word']]:
            ok += 1
        else:
            errs.append(f'XC {n}: S0CC at {base + x["cc_edge"]} = {[hex(v) for v in cc0]} want {x["cc_word"]:#x}')
        # io_collective in-pin contract (reported): tag == cmd tag, last only on the last word
        tags = [(w >> 514) & 0xFFFFFFFF for e in lows[n]['expected_ar'] for w in [ar.get(base + e['edge'], 0)]]
        lasts = [(w >> 512) & 1 for e in lows[n]['expected_ar'] for w in [ar.get(base + e['edge'], 0)]]
        gap.append(dict(message=n, cmd_tag=x['cc_word'] & 0xFFFFFFFF, words=256,
                        tag_mismatch=sum(1 for tg in tags if tg != (x['cc_word'] & 0xFFFFFFFF)),
                        last_set=sum(lasts), last_on_final=lasts[-1] if lasts else None))
    arc = [c for c in ar if c >= base]
    span = (max(arc) - base) if arc else None
    others = sorted({nm for nm in log if nm.endswith('CC') and nm != 'S0CC'})
    n_ += 1
    if others:
        errs.append(f'XC: cc words on {others} (only dvs_W5 reaches io_collective)')
    else:
        ok += 1
    # TP8 ISA gold (dv_layer_fixture.py tp8od: qwen_tp8_layer_gold collective<s>_partial of die 0 = the RAW o / down
    # partial the die all-reduces): the bench expectation (= the RTL AR words, checked above) bit-exact vs the gold
    gold = 'TP8-gold-only (TP8 partial, split 256; no TP4 value)' if FIX else 'none'
    if FIX and all(f'{n}_gold_y' in FIX for n in ('o', 'down')):
        res = {}
        for n in ('o', 'down'):
            g = B.fbits(FIX[f'{n}_gold_y'].astype(F))
            o = int(np.sum(g == gms[n]['y']))
            res[n] = f'{o}/{len(g)}'
            n_ += 1
            if o == len(g):
                ok += 1
            else:
                errs.append(f'TP8 ISA gold {n}: bench expectation differs from the gold partial in {len(g) - o}/{len(g)} rows')
        gold = 'tp8_isa_gold_words=' + ','.join(f'{k}:{v}' for k, v in res.items())
    return ok, n_, errs, dict(span_cycles=span, isa_gold=gold, collisions={k: len(v) for k, v in coll.items()}, collective_contract=gap,
                              stn={n: len(l['stn']) for n, l in lows.items()})


def okey(v):
    return (~v & 0xFFFFFFFF) if v >> 31 else (v | 0x80000000)


def run_lm(work, ages, rng, mutant):
    own = D.ownership()
    lay = M.btab_layout(own)
    hg = own['lm_head']
    rows = hg['blocks'][-1]['rows'][1]
    gm = expect_y('lm_head', mat(rng, rows, 512, M.STN_KC['lm_head']), 512)
    tabs = M.btab_stream(lay, {'lm_head': gm['s']})
    ev = LB.Events()
    t, _ = prelude(ev, LB.T0, tabs)
    ch = M.Chain(D.slice_map())
    row0 = 0
    lm = M.lower_lm(200, ages, ch, row0=row0, mutant=mutant, running_k=True)
    lo_e = min(c['edge'] for c in ch.commands())
    base = t + 20 - lo_e
    put_chain(ev, base, ch.commands())
    for d in lm['matvec']['deliveries']:
        d['far'] = [f + base for f in d['far']]
    drive(ev, lm['matvec'], gm, mutant)
    # golden die argmax (okey order, the lowest row on ties)
    y = [int(v) for v in gm['y']]
    best = max(range(rows), key=lambda r: (okey(y[r]), -r))
    # the 8 all-gather returns (rank order; this die = rank die_rank carries its own ARX candidate)
    cand = [(1000 * r + 7, int(B.fbits(np.array([rng.standard_normal() * 4], dtype=F))[0])) for r in range(8)]
    cand[lm['die_rank']] = (row0 + best, y[best])
    cand[5] = (5 * 18992 + 11, y[best])                 # a tie with this die's value: the earlier rank must win
    gbest = max(range(8), key=lambda r: (okey(cand[r][1]), -r))
    g0 = base + lm['gather_first']
    for r in range(8):
        ev.at(g0 + r, P_ARET, (1 << 517) | (r << 513) | (int(r == 7) << 512) | (cand[r][0] << 32) | cand[r][1])
    log = LB.run(work, f'lm_{mutant or "m0"}', ev, g0 + 100)
    errs = B2.status_ok2(log)
    ok = n = 0
    for s in range(N):
        toks = [w & 0xFFFFFF for _, w in log.get(f'S{s}TOK', [])]
        n += 2
        if toks and toks[0] == row0 + best:
            ok += 1
        else:
            errs.append(f'slice {s}: die token {toks[:1]} want {row0 + best}')
        stv = (log[f'S{s}ST'][0][1] >> 74) & 0xFFFFFFFF
        if toks and toks[-1] == cand[gbest][0] and stv == cand[gbest][1]:
            ok += 1
        else:
            errs.append(f'slice {s}: gather token {toks[-1:]} value {stv:#x} want {cand[gbest][0]} (rank {gbest})')
    ar = [(c, w) for c, w in log.get('S0AR', [])]
    atag = (lm['xc']['cc_word'] & 0xFFFFFFFF) if ARF['on'] else row0 + best     # ARF: framed with the XC tag
    want = (1 << 546) | (atag << 514) | (1 << 513) | (1 << 512) | ((row0 + best) << 32) | y[best]
    n += 1
    if [w for _, w in ar] == [want] and ar[0][0] == base + lm['arx_at_w5']:
        ok += 1
    else:
        errs.append(f'ARX {[(c, hex(w)) for c, w in ar]} want edge {base + lm["arx_at_w5"]} {want:#x}')
    n += 1
    x = lm['xc']
    cc0 = [(c, w) for c, w in log.get('S0CC', [])]
    if cc0 == [(base + x['cc_edge'], x['cc_word'])]:
        ok += 1
    else:
        errs.append(f'XC gather {[(c, hex(w)) for c, w in cc0]} want {(base + x["cc_edge"], hex(x["cc_word"]))}')
    return ok, n, errs, dict(best=best, gather_rank=gbest, rounds=hg['rounds'], stn=len(lm['matvec']['stn']),
                             collective_contract=dict(arx_tag=row0 + best, xc_tag=x['cc_word'] & 0xFFFFFFFF,
                                                      tag_mismatch=int(row0 + best != (x['cc_word'] & 0xFFFFFFFF))))


def run_emb(work, ages, rng, mutant):
    ev = LB.Events()
    t, _ = prelude(ev, LB.T0)
    ch = M.Chain(D.slice_map())
    em = M.lower_embed(100, ch, mutant=mutant)
    lo_e = min(c['edge'] for c in ch.commands())
    base = t + 20 - lo_e
    put_chain(ev, base, ch.commands())
    x = (rng.standard_normal(4096) * 0.05).astype(F)
    for w in range(256):
        ev.at(base + em['word0'] + w, P_DRET, (1 << 519) | (1 << 518) | B.word16(x[16 * w:16 * w + 16]))
    t = readback(ev, base + em['word0'] + 300, 'X', range(N))
    log = LB.run(work, f'emb_{mutant or "m0"}', ev, t + 100)
    errs = B2.status_ok2(log)
    got = dd_by_slice(log)
    xb = B.fbits(x)
    ok = n = 0
    for s, amap in em['expected_vm'].items():
        for a, row in amap.items():
            for l in range(16):
                n += 1
                g = got.get(s, {}).get(a - em['x_base'] + l)
                if g == int(xb[row + l]):
                    ok += 1
                elif len(errs) < 30:
                    errs.append(f'slice {s} X[{a + l}] (row {row + l}): got {g if g is None else hex(g)} exp {int(xb[row + l]):#x}')
    return ok, n, errs, dict(ports=len(ch.used))


RUNS = dict(qkv=lambda w, a, r, m: run_vm(w, 'qkv', a, r, m), gu=lambda w, a, r, m: run_vm(w, 'gu', a, r, m),
            od=run_od, lm=run_lm, emb=run_emb)
MUTANTS = dict(qkv=('sbase1', 'drop_last_k'), gu=('sbase1', 'drop_last_k'), od=('nostagger', 'xc_bc', 'rawscale'), lm=('amax_local',), emb=('emb_late',))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--work', required=True)
    ap.add_argument('--calibrate', action='store_true')
    ap.add_argument('--run', choices=sorted(RUNS))
    ap.add_argument('--mutant')
    ap.add_argument('--ages', default=None)
    ap.add_argument('--seed', type=int, default=1)
    ap.add_argument('--arf', action='store_true', help='QW-LAYERGAP: expect the framed AR words (build with '
                    'DV_LOWER_VFLAGS=-GARF=1): tag = XC tag on every word, last only on the message\'s last word')
    ap.add_argument('--fixture', help='npz of real operands + ISA gold (tools/qwen_layerbench/dv_layer_fixture.py)')
    a = ap.parse_args()
    work = Path(a.work)
    work.mkdir(parents=True, exist_ok=True)
    ARF['on'] = a.arf
    if a.calibrate:
        return calibrate(work, a.seed)
    if a.mutant and a.mutant not in MUTANTS[a.run]:
        raise SystemExit(f'mutant {a.mutant} not defined for {a.run}')
    if a.fixture:
        z = np.load(a.fixture)
        FIX.update({k: z[k] for k in z.files})
    ages = M.load_ages(a.ages or M.STN_AGES)
    rng = np.random.default_rng(a.seed)
    try:
        ok, n, errs, info = RUNS[a.run](work, ages, rng, a.mutant)
    except M.LowerError as e:
        print(f'DV_LOWER_MAT {a.run} REFUSED mutant={a.mutant or 0}: {e}')
        return 1
    v = 'PASS' if ok == n and not errs else 'FAIL'
    print(f'DV_LOWER_MAT {a.run} {v} {ok}/{n} mutant={a.mutant or 0} arf={int(a.arf)} fixture={Path(a.fixture).name if a.fixture else 0} '
          f'{json.dumps(info)}')
    for e in errs[:10]:
        print('   ', e)
    return 0 if v == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
