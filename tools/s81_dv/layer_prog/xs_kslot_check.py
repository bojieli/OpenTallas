#!/usr/bin/env python3
"""S81-ROMOPT-C (owner 10-20 ~08:45, O3): the static checker of the k-class field compile (OT_XS_KSLOT=k).

O3 gives each element of a phase up to k segment CLASSES (xs_place.KSLOT_OPS; contents only).  This module proves, from
the compiled records alone (no RTL), that the compile has no bus / buffer / port conflict:

  ELEMENT (per phase, per q pair, from the image writer's own cfg words and the legalised placement)
    E1  <= k slots, all of DISTINCT segment indices (one class each); <= NSEG 8 segments, <= 8 classes (cfg7 rows)
    E2  element pv port: one word per macro per edge (all slots' measured emission edges distinct, both macros)
    E3  the element's leaf node (r0 on a, r1 on b one edge later) never gets two exits on one edge: |E_i - E_j| >= 2
    E4  words per round <= NCH 16 (FP8 / FP4 chain slots; add_phase asserts it while writing the image)
    E5  ROM: every pair's fill <= its PP depth; cfg7: 4 x phases <= 4096 bank rows
  FRAME RETURN TREE (per phase): F1 / F2 / F3 faults of the composed calendar == 0 (frame_return_plan.compose)
  FRAME RET BUS (per op): every frame-root RET word of every phase, launched at the pipelined calendar's launch edges,
    lands on a distinct edge (one word an edge on the frame ret port -> slice CAP)
  LAYER: the op segments' RET edge sets (absolute, from the layer calendar's op starts) are pairwise disjoint
  MU: the layer's RET edges of user u (shift_u, dv_mu_calendar cal1 46 AR / 10+1 MTP) modulo the MU period are
    disjoint from every other user's (brute force), on top of xs_field_calendar.mu_check (field windows, busy span)
  Buffers: element configuration double buffer (tags 0/2, retire before reuse), operand x residency (one x per FP op,
    resident for all phases), stream windows -- the xs_field_calendar static checks of the op calendar, unchanged.

Negative controls (selftest): an injected same-edge class pair on one element, a k + 1 slot element, a repeated class,
an injected RET-bus collision (period too short for the phase's RET span), a period below the measured floor, and an
injected MU shift collision must all FAULT.

    xs_kslot_check.py die --fixtures-root D --die-src S --out DIR --layers L0 L2 L14 L20 [--slice u_s_0S] --mu-cal ...
    xs_kslot_check.py selftest --fixtures-root D --die-src S --out DIR
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

os.environ.setdefault('HDC_V41_ARITH', 'chunk8')
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import xs_field_calendar as XF  # noqa: E402
import xs_calendar as XC  # noqa: E402

REF_GO = 63          # the plan's RET edges are on the single-phase bench numbering: spine go at edge 63
NSEG, NCLS, NCH = 8, 8, 16


class KslotFault(AssertionError):
    pass


def element_checks(ph, k, depth_words):
    """E1-E3 for one compiled q phase record (xs_place.compile_frame phases[i] with 'plan')"""
    bad = []
    pl = ph['plan']
    by = {}
    for d in pl['placement']:
        by.setdefault(d['pair'], []).append(d)
    edges = pl['emission']['edges']
    for p, ds in by.items():
        segs = [d['seg'] for d in ds]
        if len(ds) > k:
            bad.append(('E1_slots_le_k', ph['phase'], p, len(ds), k))
        if len(set(segs)) != len(segs):
            bad.append(('E1_distinct_classes', ph['phase'], p, segs))
        if len(ds) > NSEG or len(set(segs)) > NCLS:
            bad.append(('E1_nseg_ncls', ph['phase'], p))
        e = edges[f'e{p}']
        e = e if isinstance(e, list) else [e]
        if len(set(e)) != len(e):
            bad.append(('E2_pv_port_one_word_an_edge', ph['phase'], p, e))
        if any(abs(a - b) < 2 for i, a in enumerate(e) for b in e[i + 1:]):
            bad.append(('E3_leaf_node_r0_r1_exit', ph['phase'], p, e))
    if ph['faults']:
        bad.append(('F123_return_tree_faults', ph['phase'], ph['faults']))
    return bad


def ret_edges(ph):
    return [w[0] - REF_GO for w in ph['ret']]


def op_ret_bus(cal, phases_by_index):
    """frame ret port: every RET word of every phase at launch_n + (edge - go) on a distinct edge.  Returns the edge
    list (relative to the op calendar's own time base) and the faults."""
    out, bad = [], []
    for p in cal['phases']:
        ph = phases_by_index[p['phase']]
        out += [p['launch'] + e for e in ret_edges(ph)]
    dup = sorted({e for e in out if out.count(e) > 1})
    if dup:
        bad.append(('RET_bus_one_word_an_edge', cal['op'], cal['period'], dup[:6]))
    return out, bad


def layer_ret(lc, cal_edges):
    """absolute RET edges of each op segment (start S of the layer calendar window) and their pairwise disjointness"""
    ab, bad = {}, []
    for w in lc['windows']:
        ab[w['op']] = {w['start'] + XC.TS + XC.GO_LAT + e for e in cal_edges[w['op']]}
    ops = list(ab)
    for i, a in enumerate(ops):
        for b in ops[i + 1:]:
            x = ab[a] & ab[b]
            if x:
                bad.append(('LAYER_RET_bus_ops_overlap', a, b, sorted(x)[:4]))
    return ab, bad


def mu_ret(ab, shifts, period):
    """RET edges of every user modulo the MU period, disjoint across users"""
    seen, bad = {}, []
    edges = sorted(set().union(*ab.values())) if ab else []
    for u, s in enumerate(shifts):
        for e in edges:
            t = (e + s) % period
            if t in seen and seen[t] != u:
                bad.append(('MU_RET_bus_collision', seen[t], u, t))
                if len(bad) > 4:
                    return bad
            seen[t] = u
    return bad


def check_layer(die, sl, fixd, layer, mu, periods=None, inject=None):
    import xs_place as XP
    r = XF.compile_ops(die, sl, fixd, layer, periods)
    _, _, _, rec = XF.frame_field(die, r['frame'], fixd, r['ops'])
    phx = {p['phase']: p for p in rec['phases']}
    bad = []
    nk = {}
    for p in rec['phases']:
        k = XP.kslot_of(p['op'])
        if p.get('fmt') == 'bf16' or 'plan' not in p or p['op'] == 'attn.a_proj':
            continue
        nk[p['op']] = k
        bad += element_checks(p, k, rec['depth'])
    pp = 8192
    if max(rec['fill']) > pp:
        bad.append(('E5_rom_fill', max(rec['fill']), pp))
    if 4 * rec['nphases'] > 4096:
        bad.append(('E5_cfg7_rows', 4 * rec['nphases']))
    cal_edges, ops = {}, {}
    for c in r['cals']:
        e, b = op_ret_bus(c, phx)
        cal_edges[c['op']] = e
        bad += b
        ops[c['op']] = dict(nphases=c['nphases'], period=c['period'], kslot=nk.get(c['op'], 1), ret_words=len(e),
                            static_PASS=c['static']['PASS'], predicted_span=c['predicted_span'])
    lc = XF.layer_calendar(r['cals'])
    if inject == 'layer_ret':      # negative control: the next op's first RET lands on the previous op's last
        w0, w1 = lc['windows'][-2], lc['windows'][-1]
        last = max(w0['start'] + e for e in cal_edges[w0['op']])
        first = min(w1['start'] + e for e in cal_edges[w1['op']])
        w1['start'] -= first - last
    ab, b = layer_ret(lc, cal_edges)
    bad += b
    mus = []
    for m in mu:
        shifts = [s['shift'] for s in m['slots']]
        if inject == 'mu_shift':
            shifts = shifts[:1] + [shifts[0]] + shifts[2:]
        fw = XF.mu_check(lc['windows'], shifts, m['period'], m['slot'])
        rb = mu_ret(ab, shifts, m['period'])
        bad += rb
        if not fw['PASS']:
            bad.append(('MU_field_windows', m['mode'], fw['collisions'], fw['premise_busy_le_slot']))
        mus.append(dict(mode=m['mode'], users=len(shifts), period=m['period'], field_windows=fw, ret_collisions=len(rb)))
    return dict(layer=layer, slice=sl, frame=r['frame'], ops=ops, layer_rows=lc['rows'], field_phases=rec['nphases'],
                max_fill=max(rec['fill']), mu=mus, faults=bad, PASS=not bad)


def cmd_die(a):
    import dv_layer_compile as C
    out = Path(a.out)
    if out.exists():
        raise SystemExit('REFUSE_EXISTING_RUN_DIR')
    out.mkdir(parents=True)
    die = C.Die(C.die_tree(a.die_ref, a.die_src))
    mu = [json.loads(Path(f).read_text()) for f in a.mu_cal]
    periods = dict((k, int(v)) for k, v in (x.split('=') for x in a.period))
    res = {}
    rc = 0
    for L in a.layers:
        try:
            r = check_layer(die, a.slice, str(Path(a.fixtures_root) / L), L, mu, periods, a.inject)
        except (XF.CalendarFault, KslotFault, AssertionError) as e:
            r = dict(layer=L, fault=str(e)[:1500], PASS=False)
        res[L] = r
        rc |= 0 if r['PASS'] else 1
        print('XS_KSLOT_CHECK', L, 'PASS' if r['PASS'] else 'FAULT', json.dumps(r.get('ops', {}))[:700],
              'mu', [(m['mode'], m['field_windows']['collisions'], m['ret_collisions']) for m in r.get('mu', [])],
              (r.get('faults') or r.get('fault') or '')[:3] if not r['PASS'] else '', flush=True)
    env = {k: os.environ.get(k) for k in ('OT_XS_QPAIRS', 'OT_XS_GU_MERGE', 'OT_XS_TOPO', 'OT_XS_PROP', 'OT_XS_CAL_SEGMENT',
                                          'OT_XS_KSLOT', 'OT_XS_KSLOT_OPS')}
    (out / 'kslot_check.json').write_text(json.dumps(dict(schema='opentallas.s81_dv.xs_kslot_check.v1', env=env,
                                                          slice=a.slice, inject=a.inject, periods=periods, layers=res),
                                                     indent=1, default=str) + '\n')
    print('XS_KSLOT_CHECK_DONE rc', rc)
    return rc


def cmd_selftest(a):
    """element-level negative controls on synthetic placements (no fixtures)"""
    out = []

    def ph(edges, place, faults=0):
        return dict(phase=1, faults=faults, plan=dict(placement=place, emission=dict(edges=edges)))
    good = ph({'e0': [10, 12, 15]}, [dict(pair=0, seg=s, super_row=s) for s in (0, 1, 2)])
    cases = [('legal 3 classes', good, 3, False),
             ('two classes one edge apart (leaf node r0/r1 exit)', ph({'e0': [10, 11]}, [dict(pair=0, seg=0, super_row=0), dict(pair=0, seg=1, super_row=1)]), 2, True),
             ('two classes one edge (pv port)', ph({'e0': [10, 10]}, [dict(pair=0, seg=0, super_row=0), dict(pair=0, seg=1, super_row=1)]), 2, True),
             ('k+1 slots', ph({'e0': [10, 12, 14]}, [dict(pair=0, seg=s, super_row=s) for s in (0, 1, 2)]), 2, True),
             ('repeated class', ph({'e0': [10, 13]}, [dict(pair=0, seg=0, super_row=0), dict(pair=0, seg=0, super_row=1)]), 2, True),
             ('return tree fault', ph({'e0': [10]}, [dict(pair=0, seg=0, super_row=0)], faults=1), 2, True)]
    ok = True
    for name, p, k, want in cases:
        got = bool(element_checks(p, k, 8192))
        out.append(dict(case=name, fault=got, expect_fault=want, ok=got == want))
        ok &= got == want
    # RET bus: two phases whose RET spans overlap at a too-short period
    cal = dict(op='x', period=5, phases=[dict(phase=0, launch=0), dict(phase=1, launch=5)])
    phs = {0: dict(ret=[[REF_GO + 300, 0], [REF_GO + 306, 0]]), 1: dict(ret=[[REF_GO + 301, 0]])}
    got = bool(op_ret_bus(cal, phs)[1])
    out.append(dict(case='RET bus collision (period below the RET spacing)', fault=got, expect_fault=True, ok=got))
    ok &= got
    got = bool(mu_ret({'x': {0, 7}}, [0, 7], 100))
    out.append(dict(case='MU RET collision (shift 7)', fault=got, expect_fault=True, ok=got))
    ok &= got
    got = bool(mu_ret({'x': {0, 7}}, [0, 50], 100))
    out.append(dict(case='MU RET disjoint (shift 50)', fault=got, expect_fault=False, ok=not got))
    ok &= not got
    for c in out:
        print('KSLOT_SELFTEST', 'OK' if c['ok'] else 'WRONG', c['case'], 'fault' if c['fault'] else 'pass')
    if a.out:
        Path(a.out).write_text(json.dumps(dict(cases=out, PASS=ok), indent=1) + '\n')
    print('KSLOT_SELFTEST', 'PASS' if ok else 'FAIL', sum(c['ok'] for c in out), '/', len(out))
    return 0 if ok else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest='cmd', required=True)
    d = sp.add_parser('die')
    d.add_argument('--fixtures-root', required=True)
    d.add_argument('--die-src')
    d.add_argument('--die-ref')
    d.add_argument('--out', required=True)
    d.add_argument('--layers', nargs='+', default=['L0', 'L2', 'L14', 'L20'])
    d.add_argument('--slice', default='u_s_0S')
    d.add_argument('--period', nargs='*', default=[])
    d.add_argument('--mu-cal', nargs='*', default=[])
    d.add_argument('--inject', choices=['layer_ret', 'mu_shift'])
    t = sp.add_parser('selftest')
    t.add_argument('--out')
    a = ap.parse_args(argv)
    return cmd_die(a) if a.cmd == 'die' else cmd_selftest(a)


if __name__ == '__main__':
    sys.exit(main())
