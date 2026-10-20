#!/usr/bin/env python3
"""L2H-GEN2D-FP2 10-19 (LEAD3-HBM): classify the die nets whose placed driver->load Manhattan span exceeds the 405 um hop
(d4f_overreach.py census: GEN2c case_a 4,581,555 'nets', worst 13 mm) before any die STA is trusted.

Unit: a NET is one bit (d4f_overreach counts bits); a BUS is (driver instance, driver port base, load instance, load port
base): every bit of one bus has the same endpoints.  Per bus (span = max bit span, placed pins):
  a_artefact   bits beyond the first of every over-reach bus (the census counts a 624-bit hop 624 times).  Manhattan pin
               distance is a LOWER bound on routed length, so 'measured across a hard child' never makes a span look longer
               than the real wire: that artefact class is checked (the routed detour is only ever longer) and is empty.
  b_not_inserted  the PLANNED hop is already > hop + tol: driver/load planned positions (lane relay = its relay-layer row site
               'site (x, y) um', other relay = 'home (x, y) um', block = placed pin) are farther apart than one hop, i.e.
               the relay layer never inserted enough stations (or a block->block bus has no relay at all).
  r_reset_pre_forest  POR / reset fan-out (hb_ckgen por_* -> every 'rs' pin): the pre-forest case has no reset tree yet; the
               H.RST regional reset forest replaces these nets (not a lane-relay fix).
  c_long_wire  planned hop <= hop + tol but PLACED > hop: die_case moved a lane row / relay off its planned site ('row nearest
               free area', slides) and left a real single-cycle long wire (SAFE-DESIGN item 2).  Split by stage kind:
               c_sync = registered single-cycle stage (hbfd_rly / land / blocks), c_fwd = forwarded half-cycle hop between
               hbfd_lh stages (source-synchronous: the clock travels with the data, but the 405 um reach still applies).
tol = 2 x 32.4 um (pin offsets inside the <= 64.8 um relay tiles vs the row-site centre).
    d4g_span_classify.py CASE_DIR CONTRACT [--hop 405] [--out FILE]
"""
import argparse
import collections
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'hbm_die_v15'))
import die_relay_pass as RP  # noqa: E402

RLY = ('hbfd_rly', 'hbfd_lh', 'hbfd_land', 'hbfd_rrl')
SITE = re.compile(r'site \(([-\d.]+), ([-\d.]+)\) um')
HOME = re.compile(r'home \(([-\d.]+), ([-\d.]+)\) um')
RST = re.compile(r'(^|_)(rst|reset|por)(_|n|$)|rst_n|_rstn|^rs$')   # d4f_overreach RESET class (+ lane 'rs' pins)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('case'); ap.add_argument('contract')
    ap.add_argument('--hop', type=float, default=405.0); ap.add_argument('--tol', type=float, default=64.8)
    ap.add_argument('--out'); ap.add_argument('--top', type=int, default=25)
    a = ap.parse_args()
    C = json.loads(Path(a.contract).read_text()); I = C['instances']
    pl, nets, directions, top_inputs = RP.load_case(Path(a.case), C)
    print('loaded', len(pl), 'insts', len(nets), 'nets', flush=True)

    def planned(inst, xy):
        note = I.get(inst, {}).get('note', '') or ''
        m = SITE.search(note)
        if m:
            return (float(m.group(1)), float(m.group(2))), 'site'
        m = HOME.search(note)
        if m:
            v = pl[inst]
            return (float(m.group(1)) + v['w'] / 2, float(m.group(2)) + v['h'] / 2), 'home'
        return xy, 'placed'

    bus = {}
    for n, ends in nets.items():
        if len(ends) < 2 or n in top_inputs:
            continue
        drv = [e for e in ends if directions.get(e[:2]) == 'OUTPUT']
        lds = [e for e in ends if directions.get(e[:2]) == 'INPUT']
        if len(drv) != 1 or not lds:
            continue
        d0 = drv[0]
        for l in lds:
            s = RP.md(d0[2], l[2])
            if s <= a.hop:
                continue
            k = (d0[0], RP.base(d0[1]), l[0], RP.base(l[1]))
            b = bus.get(k)
            if b is None:
                bus[k] = b = dict(bits=0, span=0.0, dxy=d0[2], lxy=l[2], net=n)
            b['bits'] += 1
            if s > b['span']:
                b.update(span=s, dxy=d0[2], lxy=l[2], net=n)
    print('over-reach buses', len(bus), 'bits', sum(b['bits'] for b in bus.values()), flush=True)

    cls_n, cls_b = collections.Counter(), collections.Counter()
    grp = collections.defaultdict(lambda: collections.Counter())
    top = collections.defaultdict(list)
    rule_c = collections.Counter()
    for (di, dp, li, lp), b in bus.items():
        dm, lm = pl[di]['master'], pl[li]['master']
        pd, kd = planned(di, b['dxy']); pq, kl = planned(li, b['lxy'])
        pspan = RP.md(pd, pq)
        if RST.search(dp.lower()):
            c = 'r_reset_pre_forest'      # POR / reset fan-out: replaced by the H.RST regional reset forest (not a lane hop)
        elif pspan > a.hop + a.tol:
            c = 'b_not_inserted'
        else:
            c = 'c_fwd' if dm.startswith('hbfd_lh') and lm.startswith(('hbfd_lh', 'hbfd_land')) else 'c_sync'
        cls_b[c] += 1; cls_n[c] += 1; cls_n['a_artefact'] += b['bits'] - 1
        g = f"{re.sub(r'_(EW|WE|NS|SN).*', '', dm)}.{dp} -> {re.sub(r'_(EW|WE|NS|SN).*', '', lm)}"
        grp[c][g] += 1
        if c.startswith('c'):
            for inst in (di, li):
                r = pl[inst].get('rule', '')
                m = re.search(r': (exact site|slid along|slid across|row nearest free area)', r)
                rule_c[m.group(1) if m else ('relay home' if inst.startswith('rf') else 'block')] += 1
        top[c].append(dict(span_um=round(b['span'], 1), planned_um=round(pspan, 1), bits=b['bits'], driver=f'{di}.{dp}',
                           driver_master=dm, load=f'{li}.{lp}', load_master=lm, planned_basis=f'{kd}/{kl}',
                           driver_rule=pl[di].get('rule', '')[:90], load_rule=pl[li].get('rule', '')[:90]))
    for c in top:
        top[c].sort(key=lambda r: -r['span_um']); top[c] = top[c][:a.top]
    span_hist = collections.Counter()
    for b in bus.values():
        span_hist['405-810' if b['span'] <= 810 else '810-2000' if b['span'] <= 2000 else '>2000'] += 1
    out = dict(schema='opentallas.hbm.span_classify.v1', case=str(a.case), hop_um=a.hop, tol_um=a.tol,
               census_bits=sum(b['bits'] for b in bus.values()), buses=len(bus),
               nets_by_class=dict(cls_n), buses_by_class=dict(cls_b), bus_span_hist=dict(span_hist),
               c_endpoint_rules=dict(rule_c),
               groups={c: [dict(group=g, buses=v) for g, v in grp[c].most_common(15)] for c in grp},
               top_offenders=dict(top),
               note=__doc__.split('\n\n')[0])
    print(json.dumps({k: out[k] for k in ('census_bits', 'buses', 'nets_by_class', 'buses_by_class', 'bus_span_hist', 'c_endpoint_rules')}))
    if a.out:
        Path(a.out).write_text(json.dumps(out, indent=1))


if __name__ == '__main__':
    main()
