#!/usr/bin/env python3
"""Q-CLK 10-18: classify every communicating block pair of a Qwen compute die against its region trees.

  qwen_landed_pairs.py --geom GEOM --lanes fwd_lanes.json [--arr-tt A_TT.tsv --arr-ff A_FF.tsv] --out landed_pairs.json

geom = die_clock_geom_dump.py --pairs output (clknets.tsv: root -> die clock entry pin, blocks.tsv, pairs.tsv).
Classes per directed pair (launch A -> capture B, one net):
  INTRA      A and B share a region root: judged by die_clock_check (flop spread / pair skew <= 80 ps TT + FF)
  FWD        a forwarded-clock hop (A or B is a relay station clocked by the lane's ckf, no die root): STA on the lane
  LANDED     B is a landing (qfd_landh*) whose ring is written on ckf / ck_s and read on B's region root
  RESET_ROOT cross-region reset/boot hop (n_rst_*): owes the die STA release window at TT + FF
  NEIGHBOUR  zero-stage cluster/slice -> cluster/slice hop across regions: allowed only neighbour-matched (v1 trim)
  GAP        any other cross-region data pair with no landing: violates the landed-regions standard (must be 0)
  NO_ROOT    an endpoint has a clock pin with no die root (undriven trunk): a GEN gap, not a clocking verdict
With measured arrivals (build.py arrivals_<c>.tsv) it also reports, per landed lane, the CLOCK part of the landing lag:
  dck_c = arrival(landing ck, dst root) - arrival(hop-0 ck / ck_s, src root) at TT and FF, and its corner drift; the
  L5 window (lanes/LANDING-CONTRACT.md) holds one E per bundle only while the total dL drift stays inside ~D*T - margins.
"""
import argparse
import collections
import json
from pathlib import Path

STATION = ('qfd_rlyh_', 'qfd_rlyr_')          # forwarded mid-lane stations: clocked by ckf only
LANDING = ('qfd_landh_', 'qfd_landh0_', 'qfd_rlyrl_')


def arrivals(p):
    if not p:
        return {}
    r = {}
    for ln in open(p):
        f = ln.rstrip('\n').split('\t')
        try:
            r[f[0]] = float(f[1])
        except (ValueError, IndexError):
            pass
    return r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--geom', required=True, type=Path)
    ap.add_argument('--lanes', required=True)
    ap.add_argument('--arr-tt'); ap.add_argument('--arr-ff')
    ap.add_argument('--period', type=float, default=833.333)
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    roots, pinroot = collections.defaultdict(set), {}
    for ln in open(a.geom / 'clknets.tsv'):
        r, ld, m, x, y = ln.rstrip('\n').split('\t')
        roots[ld.split('/')[0]].add(r); pinroot[ld] = r; pinroot.setdefault(ld[:-3] if ld.endswith('[0]') else ld, r)
    master = {}
    for ln in open(a.geom / 'blocks.tsv'):
        f = ln.split('\t'); master[f[0]] = f[1]
    cnt, ex = collections.Counter(), collections.defaultdict(list)
    gap_rp, gap_bus = collections.Counter(), collections.Counter()
    owed = {}
    for ln in open(a.geom / 'pairs.tsv'):
        f = ln.rstrip('\n').split('\t')
        if f[0] != 'P':
            continue
        A, B, net = f[1], f[2], f[3]
        mA, mB = master.get(A, ''), master.get(B, '')
        RA, RB = roots.get(A, set()), roots.get(B, set())
        if RA & RB:
            c = 'INTRA'
        elif mA.startswith(STATION) or mB.startswith(STATION) or mA.startswith('qfd_rlyh0_') and not RB:
            c = 'FWD'
        elif mB.startswith(LANDING) and RB:
            c = 'LANDED'
        elif not RA or not RB:
            c = 'NO_ROOT'
        elif net.startswith('n_rst') or 'rst' in net:
            c = 'RESET_ROOT'
        elif mA.startswith(('qfd_c_b16', 'qfd_dv_slice')) and mB.startswith(('qfd_c_b16', 'qfd_dv_slice')):
            c = 'NEIGHBOUR'   # zero-stage block->block hop across regions: contract section 2 allows it ONLY if the pair is
            #                   neighbour-matched (<= 80 ps TT + FF at the flops): spec v1 trims these pairs, check judges them
        else:
            c = 'GAP'
        cnt[c] += 1
        if c in ('GAP', 'NEIGHBOUR'):
            for ra in RA:
                for rb in RB:
                    gap_rp[(ra, rb)] += 1
            gap_bus[(mA, mB, net.split('[')[0])] += 1
            # QW-DIECLK 10-19: per instance link, the landing the GEN owes (qfd_landh0 at B: ring written on A's root
            # = ck_s, read on B's root = ck; fixed latency, no backpressure)
            k_ = (A, B, net.split('[')[0])
            o_ = owed.setdefault(k_, dict(cls=c, src=A, src_master=mA, src_root=sorted(RA), dst=B, dst_master=mB,
                                          dst_root=sorted(RB), bus=k_[2], bits=0))
            o_['bits'] += 1
        if len(ex[c]) < 40:
            ex[c].append([A, mA, sorted(RA), B, mB, sorted(RB), net])
    lanes = json.load(open(a.lanes))['lanes']
    at, af = arrivals(a.arr_tt), arrivals(a.arr_ff)
    lag = []
    for L in lanes:
        st = L.get('stations') or []
        land = L.get('landing')
        if not land:
            continue
        lm = master.get(land, '')
        if lm.startswith('qfd_landh0_'):
            sp, dp = f'{land}/ck_s', f'{land}/ck'
        elif st:
            sp, dp = f'{st[0]}/ck', f'{land}/ck'
        else:
            continue
        rec = dict(bid=L['bid'], lane=L.get('lane'), n=L.get('n'), E=L.get('E'), src_ck=L.get('src_ck'),
                   dst_ck=L.get('dst_ck'), src_root=pinroot.get(sp), dst_root=pinroot.get(dp))
        sp, dp = (next((q for q in (x, x + '[0]') if q in at), x) for x in (sp, dp)) if at else (sp, dp)
        if at and af and sp in at and dp in at and sp in af and dp in af:
            rec.update(dck_tt=round(at[dp] - at[sp], 1), dck_ff=round(af[dp] - af[sp], 1))
            rec['drift'] = round(rec['dck_ff'] - rec['dck_tt'], 1)
        lag.append(rec)
    meas = [r for r in lag if 'drift' in r]
    worst = sorted(meas, key=lambda r: -abs(r['drift']))[:15]
    summ = dict(pairs=dict(cnt), gap=cnt['GAP'], no_root=cnt['NO_ROOT'], landed_lanes=len(lag), measured_lanes=len(meas),
                lanes_no_root=sum(1 for r in lag if not r['src_root'] or not r['dst_root']),
                max_abs_drift_ps=max((abs(r['drift']) for r in meas), default=None),
                drift_over_T=sum(abs(r['drift']) > a.period for r in meas),
                drift_over_half_T=sum(abs(r['drift']) > a.period / 2 for r in meas))
    summ['gap_buses'] = len(gap_bus)
    json.dump(dict(schema='opentallas.qwen_compute.landed_pairs.v1', summary=summ, examples=ex, lanes=lag,
                   gap_root_pairs=sorted(gap_rp), gap_root_pair_bits={f'{x}|{y}': n for (x, y), n in gap_rp.most_common()},
                   gap_buses=[[*k, n] for k, n in gap_bus.most_common()],
                   worst_drift=worst,
                   land_owed=sorted(owed.values(), key=lambda o: (o['src'], o['dst'], o['bus']))), open(a.out, 'w'), indent=1)
    print('QWEN LANDED PAIRS', json.dumps(summ))


if __name__ == '__main__':
    main()
