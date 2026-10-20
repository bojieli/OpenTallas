#!/usr/bin/env python3
"""QW-DIECLK 10-19: REGIONAL (landed-regions standard) variant of a Qwen compute die clock spec.  Replaces the GEN16
pad-balanced spine (dv2f18dh2: 34,718 cells / 685 levels / 24,742 pads / 24.6 ns model insertion, 43/55 neighbour
region pairs over 80 ps, worst 9.6 ns) which tried to neighbour-match the unlanded NEIGHBOUR crossings across mm.

  qwen_regional_spec.py --spec D/spec.json --pairs D/landed_pairs_pre.json --out-spec D/spec_V.json
      --out-families D/families_V.json --out-owed D/land_owed_V.json [--source clk_rx/pll_rK[0]] [--ideal]

Topology:
  * every region tree gets a regional clock entry (local_root = sink median, root buffer there) and a LOCAL tree; the
    only skew judged is intra-region (flop spread / pair skew <= 80 ps at TT and FF);
  * the region entries of the stream period are fed by ONE FORWARDED spine (spine.balance = false: geometric merge,
    repeaters <= 200 um, NO pads, NO compensation of region insertion, no trim): fixed latency, no global target;
    --ideal leaves the entries on ideal sources instead (diagnostic control: region trees alone);
  * every region is its own family (die_clock_check --per-region): cross-region pairs are mesochronous and must be
    LANDED (qfd_landh0 for zero-stage hops) or forwarded; the unlanded NEIGHBOUR / GAP links are written to --out-owed
    as the landings the GEN owes, and the landed-lane clock drift (TT->FF) is judged by regional_verdict.py.
"""
import argparse
import json


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--spec', required=True)
    ap.add_argument('--pairs', required=True)
    ap.add_argument('--out-spec', required=True)
    ap.add_argument('--out-families', required=True)
    ap.add_argument('--out-owed', required=True)
    ap.add_argument('--source')
    ap.add_argument('--period', type=float, default=833.333333)
    ap.add_argument('--ideal', action='store_true')
    ap.add_argument('--grid-center', action='store_true', help='QW-DIECLK2: clock sites in the 17.28-um column gaps '
                    '(build.py grid_center: centre-rule cells + exact site check against block rectangles)')
    ap.add_argument('--safe-tree', action='store_true', help='QW-DIECLK3: build.py safe tree (every unbuffered clock '
                    'segment <= 220 um, no run over a block > 200 um, leaves within 160 um; violations fail the build)')
    ap.add_argument('--neighbours', action='store_true', help='QW-DIECLK3: trim every UNLANDED cross-region pair '
                    '(GAP root pairs + land_owed src/dst roots) to --neighbour-budget at TT and FF (measured trim, '
                    'targets only rise): region insertion matched along every unlanded crossing')
    ap.add_argument('--neighbour-budget', type=float, default=60.0)
    ap.add_argument('--balance-spine', action='store_true', help='QW-DIECLK3: the spine merge compensates each region '
                    "tree's model insertion (spine.balance true, pads allowed) so region entries meet at their flops")
    a = ap.parse_args()
    sp = json.load(open(a.spec))
    for t in sp['trees']:
        t['local_root'] = 'median'
        t.pop('balance_group', None)
    stream = [t for t in sp['trees'] if abs(t['period'] - a.period) < 1e-3]
    src = a.source or max(stream, key=lambda t: t.get('sinks', 0))['root']
    sp['clock_at_root_buffer'] = True
    if a.grid_center:
        sp['grid_center'] = True
    sp.pop('neighbours', None); sp.pop('neighbour_budget_ps', None)
    if a.safe_tree:
        sp['safe_tree'] = True
    if not a.ideal:
        sp['spine'] = dict(source=src, period=a.period, balance=bool(a.balance_spine))
    sp['note'] = (sp.get('note', '') + ' QW-DIECLK regional: local trees at regional entries (sink median)' +
                  (' on ideal entries (control)' if a.ideal else f', fed by ONE forwarded unpadded spine from {src} '
                   '(balance false: no pads, no region compensation)') +
                  '; every region its own family; cross-region crossings LANDED (land_owed lists the GEN debt).' +
                  (f' QW-DIECLK3 neighbour trim: {len(nb)} unlanded region pairs <= {a.neighbour_budget} ps TT+FF.' if nb else '') +
                  (' Safe tree (segments <= 220 um, never over blocks).' if a.safe_tree else ''))
    lp = json.load(open(a.pairs))
    owed = lp.get('land_owed', [])
    nb = set()
    if a.neighbours:
        name = {t['root']: t['name'] for t in sp['trees']}
        rp = [tuple(p) for p in lp.get('gap_root_pairs', [])]
        rp += [(x, y) for o in owed for x in o.get('src_root', []) for y in o.get('dst_root', [])]
        nb = {tuple(sorted((name[x], name[y]))) for x, y in rp if x in name and y in name and name[x] != name[y]}
        sp['neighbours'] = sorted(map(list, nb)); sp['neighbour_budget_ps'] = a.neighbour_budget
    json.dump(sp, open(a.out_spec, 'w'), indent=1)
    json.dump({t['name']: [t['root']] for t in sp['trees']}, open(a.out_families, 'w'), indent=1)
    by = {}
    for o in owed:
        k = (o['src_master'], o['dst_master'], o['bus'])
        b = by.setdefault(k, dict(src_master=k[0], dst_master=k[1], bus=k[2], links=0, bits=0))
        b['links'] += 1; b['bits'] += o['bits']
    json.dump(dict(schema='opentallas.qwen_compute.land_owed.v1', rule='every cross-region data crossing without a '
                   'landing gets qfd_landh0 at the receiver (ck_s = sender region root, ck = receiver region root, '
                   'fixed latency E from measured setup/hold, 4-slot ring, no backpressure); schedule +E cycles priced',
                   links=len(owed), bits=sum(o['bits'] for o in owed), buses=sorted(by.values(), key=lambda b: -b['bits']),
                   detail=owed), open(a.out_owed, 'w'), indent=1)
    print('QCLK_REGIONAL_SPEC', 'ideal entries' if a.ideal else f'forwarded spine {src} balance=false', 'trees',
          len(sp['trees']), 'stream', len(stream), 'land_owed links', len(owed), 'bits', sum(o['bits'] for o in owed),
          'bus classes', len(by), 'grid_center', bool(a.grid_center), 'safe_tree', bool(a.safe_tree),
          'neighbour_pairs', len(nb), 'balance_spine', bool(a.balance_spine))


if __name__ == '__main__':
    main()
