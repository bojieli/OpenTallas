#!/usr/bin/env python3
"""dv_lower_xhead: lowering of the compute-die x CONSUMER and head-row control for the decode-layer matvecs, and the
TILE-DELIVERY composition (QW-XHEAD 10-19, TOK.QW.LAYER gaps 'COLUMN-HEAD x CONSUMER' + 'TILE DELIVERY' of dv_layer.py).

The x consumer of every column-tile matvec is the slice's x-delivery face qfd_dv_heads (rtl/qwen_dv/qfd_dv_heads.sv, inside
qfd_dv_slice2): one ot_qfd_xs_tap + 4 ot_qfd_xhead + 32 ot_qfd_xs_leaf (rtl/qwen_sys/dvm_20261014/ot_qfd_xslice.sv).  Its
control is the head-row bundle hr = {go [452], ib [451:73] (379 b), xpf [72:1] (72 b), v [0]} from qfd_tt_ctlm_dv, W5 -> E5,
hr_o = the slice's pin register (1 edge a hop + the die relay ages of the hr buses).  The x WRITES are the slice stream x
words (qfd_dv_stream xt_v / xt_a, 64 BF16, eaddr = the DV x element) of the producer family (dv_lower_vec: resid XS ->
gate/up and the next stage's qkv, attn XA -> o_proj, SILU -> down).  This module lowers, per matvec:

 (1) DV x RELOCATION.  The ISA programme's ME ops address x in the central VM (PC1 qkv xbase 4096, PC12 o 50672, PC16 gu
     4096, PC20 down 55280); in DV the tap matches the STREAM eaddr, which every producer family emits from 0 (resid:
     128 b + 64 j over 0..4095; attn: 128 i + 64 j over 0..511; silu: 128 s + 64 j over 0..1535).  The op's x footprint
     {xbase + c xcs + k xks} must equal the producer's eaddr set exactly; xbase := 0 in BOTH the XPF arm descriptor and
     the go's ib (ot_qfd_xhead go_ok compares b_xbase with the armed epoch's xbase).  ib packing = ot_qwen_me_array_w12
     {nout, tiles, k, wsrc, wbase, ts, ks, js, xbase, xks, xjs, xcs, jsh, split, wcs, round, obase, ots, ojs, mmode, oen,
     amax, rmax, mbase} (the head's ot_qwen_tp8_rom_relocate adds the stage's ROM base to wbase on the die).
 (2) XPF arm + go edges at the dvs_W5 hr pin, from the producer's x-beat edges at EVERY slice (x stream reference edge of
     the occupancy model, slice m sees a word of slice s 2 |m - s| edges after s): with hr_at[m] the hr arrival offset of
     slice m and the MEASURED constants (xhead_ages.json, rtl/test/qwen_dv/xhead_bench.py --calibrate on the 12-slice
     qfd_dv_slice2 chain, Verilator 5.050): x_tap (stream reference edge -> xt_v at the heads), xpf_lead (the earliest
     xt_v of a slice >= its XPF hr-pin edge + xpf_lead), go_lag (go hr-pin edge >= the slice's last xt_v + go_lag),
       go_w5  >= max_m (last_xt[m] + go_lag - hr_at[m])          (every slice's leaves hold the whole epoch)
       xpf_w5 <= min_m (first_xt[m] - xpf_lead - hr_at[m])        (armed before the first beat everywhere)
       xpf_w5 >= max_m (prev_last_xt[m] + 1 - hr_at[m])            (the previous op's writes are classified first)
       xpf_w5 >= max_m (read_end[n-2][m] + 1 - hr_at[m])           (epochs alternate: op n reuses op n-2's slots)
     read_end = the slice's head go edge + d_head + tiles * k * IL + read_tail (measured: the last corridor x line).
 (3) the tt_ctlm rows: ME fixed-issue cycle = go_w5 - R_HR - ISSUE_TO_ROM - HEAD0; XPF record arm cycle = xpf_w5 - R_HR -
     XPF_ARM_EDGE - XPF0 (ctlm_image PROG_CONSTANTS), first_write_cycle = the first tap write - XPF0, and the record's
     PRODUCER = ONE SU command that issues exactly once in the stage (MONITOR PLAN, below).
 (4) MONITOR PLAN.  ot_qfd_xpf_static_schedule faults when a monitored producer (unit 2, su_pc = the calendar SU pidx)
     issues at a cycle other than its record's or twice.  DV producers are per-slice commands sharing one pidx (XS 3 on
     12 slices, twice a stage: resid1 + resid2; XA 11; SILU 10), so the lowering gives each record's producer a DEDICATED
     pidx (a copy of the same SU word in that slice's PROG store) issued once: the earliest producer command of the
     family; the other slices keep the shared pidx (unmonitored).  Extra PROG words: 1 per record.
 (5) TILE DELIVERY.  The far cluster word of matvec round r, word j at slice s's rs pins =
       go_w5 + hr_at[s] + d_head + d_clu + rs_age + r * round_period + j
     (d_clu / round_period MEASURED on the real-ROM column vehicle XT1, rtl/test/qwen_dv/xhead/, key 'tile' of
     xhead_ages.json; rs_age = the die relay age of the cluster rs lane).  dv_lower_mat's contract for AR destinations
     (o / down) needs slice s's block-b words at M0 + 8 b + j - l8_ar - 2 s; with one go per op on the hr chain slice s
     gets them at G + hr_at[s] + const + 96 r + j while b = 12 r + s needs + 6 s: the as-built hr delivery collides
     (dv_lower_mat mutant 'nostagger').  Required: a per-slice go delay HGD[s] = 6 s - hr_at[s] (o / down; 0 for the VM
     destinations) -> RTL item for Q-DIE15 (lanes/Q-DIE15.md, QW-XHEAD spec), reported as hgd per matvec.

usage: dv_lower_xhead.py --out FILE.json [--stage 1]   (the composed layer of dv_layer.py + this lowering)
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import dv_lower as D  # noqa: E402

ROOT = D.ROOT
N, BLOCK = D.NSLICE, D.BLOCK
XH_AGES = 'results/rtl/qlb_c4b_1018/xhead/xhead_ages.json'
AW, NW, XCW, IL = 24, 18, 12, 8
IBW = 3 * NW + 13 * AW + 13
MV_PC = dict(qkv=1, o=12, gu=16, down=20)
PRODUCER = dict(qkv='resid2', gu='resid1', o='attn', down='silu')     # x stream family (qkv: the previous stage's)
FAMILY_PIDX = dict(resid1=3, resid2=3, attn=11, silu=10)               # dv_lower_vec PIDX xs / xa / silu
MON_PIDX = dict(resid1=12, resid2=13, attn=14, silu=15)                # dedicated monitored copies (MONITOR PLAN)


class LowerError(D.LowerError):
    pass


# ------------------------------------------------------------------------------------------------ ME op fields
def me_ops(program=None):
    """{name: decoded ISA fields} of the four ROM matvecs of the decode-layer programme"""
    import ctlm_image as CI
    words, _, ops, _ = CI.load_programme(ROOT / (program or CI.DEF_PROGRAM), ROOT / CI.DEF_LOWERING)
    out = {}
    for name, pc in MV_PC.items():
        o = ops[pc]
        if o['unit'] != 1 or o['me_wsrc']:
            raise LowerError(f'PC{pc} is not a ROM matvec')
        out[name] = dict(o, pc=pc)
    return out


def footprint(f, xbase=None):
    xb = f['me_xbase'] if xbase is None else xbase
    return {xb + c * f['me_xcs'] + k * f['me_xks'] for c in range(1 << f['me_split']) for k in range(f['me_k'])}


def dv_fields(f, eaddrs):
    """relocate the op's x base to the DV stream eaddr space: the footprint at xbase 0 must equal the producer's eaddr
    set (every element the tiles read is written by the stream, nothing else)"""
    lo = min(eaddrs)
    need = footprint(f, lo)
    if need != set(eaddrs):
        raise LowerError(f'PC{f["pc"]}: x footprint at xbase {lo} ({len(need)} el) != the producer stream eaddrs '
                         f'({len(eaddrs)} el)')
    return dict(f, me_xbase=lo, isa_xbase=f['me_xbase'])


def pack_ib(f):
    """the 379-b ib of ot_qwen_me_array_w12 (MSB first): {nout, tiles, k, wsrc, wbase, ts, ks, js, xbase, xks, xjs, xcs,
    jsh, split, wcs, round, obase, ots, ojs, mmode, oen, amax, rmax, mbase}"""
    g = lambda k: int(f.get('me_' + k, 0))      # noqa: E731
    fields = [('nout', NW), ('tiles', NW), ('k', NW), ('wsrc', 1), ('wbase', AW), ('ts', AW), ('ks', AW), ('js', AW),
              ('xbase', AW), ('xks', AW), ('xjs', AW), ('xcs', AW), ('jsh', 3), ('split', 4), ('wcs', AW),
              ('round', 1), ('obase', AW), ('ots', AW), ('ojs', AW), ('mmode', 1), ('oen', 1), ('amax', 1),
              ('rmax', 1), ('mbase', AW)]
    v, n = 0, 0
    for k, w in fields:
        x = g(k)
        if x >> w:
            raise LowerError(f'ib field {k} = {x} wider than {w} b')
        v = (v << w) | x
        n += w
    assert n == IBW
    return v


def pack_xpf72(f):
    """ctlm_image.xpf_pack x72: {round, k, split, xks, xcs, xbase, v}"""
    return ((f['me_round'] & 1) << 71) | (f['me_k'] << 53) | (f['me_split'] << 49) | (f['me_xks'] << 37) | \
           (f['me_xcs'] << 25) | (f['me_xbase'] << 1) | 1


def hr_word(go=0, ib=0, xpf72=0):
    """qfd_dv_slice2 hr: v [0], xpf [72:1] (xpf[0] = xpf_v), ib [451:73], go [452]"""
    return 1 | (xpf72 << 1) | (ib << 73) | (int(go) << 452)


# ------------------------------------------------------------------------------------------------ hr arrival
def hr_arrival(relay=None, model=None):
    """edges from dvs_W5.hr_wi to slice m's hr pin register input (slice 0 = 0): 1 a hop (hr_o is the pin register) +
    the relay age of each hr bus"""
    smap = D.slice_map() if relay is None and model is None else D.slice_map(model or D.DV_MODEL, relay or D.RELAY)
    r = json.loads((ROOT / (relay or D.RELAY)).read_text())
    names = smap['names']
    at = [0]
    for a, b in zip(names, names[1:]):
        bus = [x for x in r['buses'] if x['src']['inst'] == a and x['dst']['inst'] == b and
               x['src']['port'].startswith('hr_')]
        if len(bus) != 1:
            raise LowerError(f'relay table: {a} -> {b}: {len(bus)} hr buses (one expected)')
        v = bus[0]
        age = v.get('age_edges') if v.get('age_edges') is not None else v['stages']
        at.append(at[-1] + 1 + age)
    return at


def bench_hr_arrival():
    """tb_qfd_dv2: hr_o -> hr_i wired directly (no relays)"""
    return list(range(N))


# ------------------------------------------------------------------------------------------------ ages
def load_ages(path=None, need_tile=False):
    p = ROOT / (path or XH_AGES)
    if not p.exists():
        raise LowerError(f'{path or XH_AGES} missing: measure it (rtl/test/qwen_dv/xhead_bench.py --calibrate)')
    a = json.loads(p.read_text())
    for k in ('x_tap', 'xpf_lead', 'go_lag', 'd_head', 'read_tail'):
        if k not in a:
            raise LowerError(f'{path or XH_AGES}: no {k}')
    if need_tile and not a.get('tile'):
        raise LowerError(f'{path or XH_AGES}: no measured tile delivery (XT1)')
    return a


# ------------------------------------------------------------------------------------------------ x beats
def x_edges(expected_x, shift=0, n=N):
    """{slice m: [stream reference edges of every x word at m]} from a vec family's expected x words (edge_e5 at slice
    N-1; the word left its owner s at edge_e5 - D.ST_HOP (N-1-s) and reaches m D.ST_HOP |m - s| later; 2 slice2 / 4 s8)"""
    out = {m: [] for m in range(n)}
    ea = set()
    for w in expected_x:
        s, e5 = w['slice'], w['edge_e5'] + shift
        e_s = e5 - D.ST_HOP * (n - 1 - s)
        for m in range(n):
            out[m].append(e_s + D.ST_HOP * abs(m - s))
        ea.update(range(w['eaddr'], w['eaddr'] + 64))
    return {m: sorted(v) for m, v in out.items()}, ea


def read_span(f):
    return f['me_tiles'] * f['me_k'] * IL


def consumer_ages(ages, name):
    """TOKe-QW 10-23: go_lag / xpf_lead are properties of the CONSUMER op's read order (tiles, k, split: which x element
    the column heads read first after the go), not of the x stream alone.  The resid-calibrated go_lag -3 (gu: k 32,
    split 7) faults o (tiles 3, k 2, split 8) and down (tiles 3, k 6, split 8) on the binding slice 0 (an element read
    before its write -> sticky heads FAULT).  ages['consumer'][op] (xhead_bench.py --point/--merge, measured per op)
    overrides the global values; a missing op entry falls back to them."""
    c = (ages.get('consumer') or {}).get(name.rstrip('+1'))
    return dict(ages, **{k: c[k] for k in ('go_lag', 'xpf_lead') if k in c}) if c else ages


def lower_consumer(name, f, xs, ages, hr_at, go_at=None, prev_xt=None, prev2_end=None, xpf_at=None):
    """one matvec's XPF / go at the W5 hr pin.  xs: {m: stream reference edges}; go_at: the composed (plan) go -- the
    lowering never issues earlier than the x allows (go = max(go_at, go_min)); prev_xt: {m: last write of the previous
    op}; prev2_end: {m: read end of op n-2}.  Returns the edges, the per-slice slack and the read windows."""
    ages = consumer_ages(ages, name)
    xt = {m: [e + ages['x_tap'] for e in v] for m, v in xs.items()}
    go_min = max(max(v) + ages['go_lag'] - hr_at[m] for m, v in xt.items())
    xpf_max = min(min(v) - ages['xpf_lead'] - hr_at[m] for m, v in xt.items())
    lo = [-10 ** 9]
    if prev_xt:
        lo.append(max(prev_xt[m] + 1 - hr_at[m] for m in prev_xt))
    if prev2_end:
        lo.append(max(prev2_end[m] + 1 - hr_at[m] for m in prev2_end))
    xpf_min = max(lo)
    if xpf_min > xpf_max:
        raise LowerError(f'{name}: no XPF edge: needs >= {xpf_min} (previous writes / epoch reuse) and <= {xpf_max} '
                         '(first x beat)')
    xpf = xpf_max if xpf_at is None else xpf_at
    go = go_min if go_at is None else max(go_at, go_min)
    rs = read_span(f)
    head_go = {m: go + hr_at[m] + ages['d_head'] for m in xt}
    end = {m: head_go[m] + rs + ages['read_tail'] for m in xt}
    return dict(matvec=name, pc=f['pc'], xpf_w5=xpf, go_w5=go, go_min=go_min,
                go_delay=0 if go_at is None else max(0, go_min - go_at),
                xpf_window=[xpf_min, xpf_max],
                slack_go={m: go + hr_at[m] - (max(v) + ages['go_lag']) for m, v in xt.items()},
                slack_xpf={m: min(v) - ages['xpf_lead'] - (xpf + hr_at[m]) for m, v in xt.items()},
                first_xt={m: min(v) for m, v in xt.items()}, last_xt={m: max(v) for m, v in xt.items()},
                head_go=head_go, read_end=end, read_span=rs,
                hr=dict(xpf=f'{hr_word(xpf72=pack_xpf72(f)):0114x}', go=f'{hr_word(go=1, ib=pack_ib(f)):0114x}'))


# ------------------------------------------------------------------------------------------------ tile delivery
def tile_delivery(name, own_m, go, hr_at, ages, l8_ar, need_stagger):
    """far-word edges at each slice's rs pins from the measured go -> far constants; for AR destinations the per-slice go
    delay HGD[s] that realises dv_lower_mat's stagger (slice s, block b = 12 r + s at M0 + 8 b + j - l8_ar - 2 s)"""
    t = ages.get('tile')
    if not t:
        return dict(matvec=name, status='UNMEASURED (XT1 tile constants pending)')
    base = {s: go + hr_at[s] + ages['d_head'] + t['d_clu'] + t.get('rs_age', 0) for s in range(N)}
    rp = t['round_period'].get(name) if isinstance(t['round_period'], dict) else t['round_period']
    out = dict(matvec=name, tile_first={s: base[s] - go for s in range(N)}, round_period=rp)
    if need_stagger:
        # want far(s, r, 0) = M0 + 96 r + 6 s - l8_ar; as built = base[s] + rp r: per-slice delay so all slices align
        hgd = {s: 6 * s - (base[s] - base[0]) for s in range(N)}
        out.update(hgd=hgd, hgd_ok=all(v >= 0 for v in hgd.values()) and rp == 96,
                   note='HGD[s] = 6 s - (hr_at[s] - hr_at[0]): edges slice s must hold its go; round period must be 96 '
                        '(12 slices x 8 words on the one AR lane)')
    return out


# ------------------------------------------------------------------------------------------------ ctlm rows
def ctlm_rows(lw, R, C, stage):
    """the head fixed-issue rows and the XPF records of one stage from the lowered consumers"""
    me, xpf = [], []
    for c in lw:
        if c['matvec'] == 'qkv+1':               # next stage's qkv: its XPF arms in THIS stage, its go is next stage's
            pass
        else:
            me.append(dict(pc=c['pc'], unit=1, cycle=c['go_w5'] - R['R_HR'] - C['ISSUE_TO_ROM'] - C['HEAD0'],
                       matvec=c['matvec']))
        if c['matvec'] == 'qkv':                 # armed in the previous stage (its record is that stage's qkv+1)
            continue
        a = c['xpf_w5'] - R['R_HR'] - C['XPF_ARM_EDGE'] - C['XPF0']
        fw = c['first_write_w5'] - C['XPF0'] if c.get('first_write_w5') is not None else None
        xpf.append(dict(consumer_pc=c['pc'], matvec=c['matvec'], arm_cycle=a, first_write_cycle=fw,
                        producer_unit=2, producer_pc=c.get('mon_pidx'), issue_cycle=c.get('mon_issue_cycle'),
                        stage=stage))
    return me, xpf


# ------------------------------------------------------------------------------------------------ the layer
def monitor_plan(events, fam, pidx):
    """the earliest producer SU command of a family in the spliced calendar -> its dedicated monitored copy"""
    lab = {3: 'XS', 11: 'XA', 10: 'SILU'}[pidx]
    cand = sorted((e['edge_w5'], e) for e in events if e['label'].startswith(f'{fam}: {lab} '))
    if not cand:
        raise LowerError(f'no {fam} {lab} command in the calendar')
    w, e = cand[0]
    c = int(e['cmd'], 16)
    dec = D.decode_cmd(c)
    if dec.get('pidx') != pidx:
        raise LowerError(f'{e["label"]}: pidx {dec.get("pidx")} != {pidx}')
    return dict(label=e['label'], slice=dec['dst'], edge_w5=w, shared_pidx=pidx, mon_pidx=MON_PIDX[fam],
                copies=len(cand))


def lower_layer(comp, ages=None, stage=1):
    """the x-consumer lowering of one composed decode stage (dv_layer.compose output): XPF / go of qkv (this stage, x
    from the previous stage's resid2), o, gu, down and next-stage qkv; the monitor plan; the tt_ctlm rows; tile
    delivery (measured constants when present)."""
    import ctlm_image as CI
    import dv_layer as L
    ages = ages or load_ages()
    rec = L.ctlm_rec(stage)
    R, C = rec['relay'], rec['constants']
    hr_at = hr_arrival()
    ops = me_ops()
    sh = comp['calendar']['shifts']
    gos = {t['matvec']: t['go_w5'] for t in comp['composition']['tile']}
    period = comp['composition']['chained_period']
    fams = {}
    for fam, mode in (('resid1', 'resid'), ('resid2', 'resid'), ('attn', 'attn'), ('silu', 'silu')):
        lw, _ = L.vec_family(mode, comp['ar_order'] if mode == 'resid' else 'slice')
        xs, ea = x_edges(lw['expected']['x'], shift=sh[fam])
        fams[fam] = (xs, ea)
    # resid2 of the PREVIOUS stage feeds this stage's qkv: the same schedule one period earlier
    xs_prev = {m: [e - period for e in v] for m, v in fams['resid2'][0].items()}
    order = [('qkv', xs_prev, fams['resid2'][1], gos['qkv'], 'resid2(prev)'),
             ('o', *fams['attn'], gos['o'], 'attn'), ('gu', *fams['resid1'], gos['gu'], 'resid1'),
             ('down', *fams['silu'], gos['down'], 'silu'),
             ('qkv+1', fams['resid2'][0], fams['resid2'][1], gos['qkv'] + period, 'resid2')]
    out, errs, notes = [], [], []
    for n, (name, xs, ea, go_at, fam) in enumerate(order):
        f = dv_fields(ops[name.rstrip('+1')], ea)
        prev_xt = {m: max(e + ages['x_tap'] for e in v) for m, v in order[n - 1][1].items()} if n else None
        prev2 = out[n - 2]['read_end'] if n >= 2 else None
        try:
            c = lower_consumer(name, f, xs, ages, hr_at, go_at=go_at, prev_xt=prev_xt, prev2_end=prev2)
        except LowerError as e:
            errs.append(str(e))
            continue
        c['producer'] = fam
        c['first_write_w5'] = min(c['first_xt'].values())
        if c['go_delay']:
            notes.append(f'{name}: the composed go {go_at} is {c["go_delay"]} edges before the x allows; '
                         f'lowered go {c["go_w5"]} (+{c["go_delay"]} on the layer path)')
        if fam != 'resid2(prev)':
            mp = monitor_plan(comp['events'], fam.split('(')[0], FAMILY_PIDX[fam])
            c['monitor'] = mp
            c['mon_pidx'] = mp['mon_pidx']
            c['mon_issue_cycle'] = mp['edge_w5'] - R['R_CMD'] + 3 - C['XPF0'] - 1
        a = c['xpf_w5'] - R['R_HR'] - C['XPF_ARM_EDGE'] - C['XPF0']
        T = rec.get('xpf_transport_edges') or C.get('XPF_TRANSPORT_EDGES')
        if T is not None and c['first_write_w5'] - C['XPF0'] < a + T + C['XPF_TAP']:
            errs.append(f'{name}: XPF seal first_write {c["first_write_w5"] - C["XPF0"]} < arm {a} + T {T} + 3')
        out.append(c)
    stage_ops = [c for c in out if c['matvec'] in ('o', 'gu', 'down', 'qkv+1')]
    me, xpf = ctlm_rows(out, R, C, stage)
    own = D.ownership()
    import dv_lower_mat as M
    mages = M.load_ages()
    tile = [tile_delivery(c['matvec'].rstrip('+1'), own, c['go_w5'], hr_at, ages, mages['l8_ar'],
                          need_stagger=c['matvec'] in ('o', 'down')) for c in out if c['matvec'] != 'qkv+1']
    prog_extra = {c['monitor']['slice']: [] for c in stage_ops if 'monitor' in c}
    for c in stage_ops:
        if 'monitor' in c:
            prog_extra[c['monitor']['slice']].append(dict(pidx=c['mon_pidx'], copy_of=c['monitor']['shared_pidx']))
    return dict(
        schema='opentallas.qwen.dv-xhead-lowering.v1', tool='tools/qwen_layerbench/dv_lower_xhead.py', stage=stage,
        ages=XH_AGES, hr_arrival=hr_at, consumers=out, me_rows=me, xpf_records=xpf, tile_delivery=tile,
        monitor_prog_words=prog_extra, errors=errs, notes=notes,
        xpf_records_per_stage=len([r for r in xpf if r['matvec'] != 'qkv']),
        rule='x relocation xbase 0 (footprint == producer eaddrs, checked); XPF at the latest edge before every '
             "slice's first beat (- xpf_lead), go = max(composed go, every slice's last beat + go_lag); epochs alternate "
             '(op n XPF after op n-2 reads end at every slice); one monitored producer per XPF record (dedicated pidx)')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    ap.add_argument('--stage', type=int, default=1)
    ap.add_argument('--ages')
    a = ap.parse_args()
    import dv_layer as L
    comp = L.compose(a.stage)
    r = lower_layer(comp, load_ages(a.ages), a.stage)
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(r, indent=1) + '\n')
    print(json.dumps(dict(errors=r['errors'], notes=r['notes'], go={c['matvec']: c['go_w5'] for c in r['consumers']},
                          xpf={c['matvec']: c['xpf_w5'] for c in r['consumers']},
                          go_slack={c['matvec']: min(c['slack_go'].values()) for c in r['consumers']})))
    return 1 if r['errors'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
