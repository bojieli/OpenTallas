#!/usr/bin/env python3
"""Q-CLK 10-18: inputs of the PHYSICAL die clock build for a Qwen compute die GEN (landed-regions standard).

Every output of the die's qfd_clkrx (pll_r*, pll_d2d, pll_coll, pll_serdes*, pll_ucie, pll_coll_blk) is one REGION
tree; there is NO balance_group (no die-wide phase: lanes/CLOCK-AUDIT.md, memory landed-regions-standard-1018).
die_clock_check judges intra-region pairs only (families = one family per region, <= 80 ps TT and FF); every
cross-region pair is classified by qwen_landed_pairs.py against the GEN's fwd_lanes.json.

  qwen_compute_dieclk_prep.py --geom GEOM_DIR --clocks-dir CHAIN/libs --out DIR [--die NAME]
writes DIR/spec.json, DIR/families.json, DIR/targets.json (R per master clock pin [ss, ff, tt] from the chain's
clocks_<c>.tcl: R = -(set_clock_latency -source) = measured in-arc insertion of REAL views, 0 for ASSUMED views,
which targets.json lists so the report can say which R are not measured yet).
"""
import argparse
import collections
import json
import re
from pathlib import Path

LAT = re.compile(r'set_clock_latency -source -clock \[get_clocks (\S+)\] (-?[0-9.]+) \[get_pins \{([^}]+)\}\]')
PIN = re.compile(r'get_pins -quiet \{([^}]+)\}')
CLK = re.compile(r'create_clock -name (\S+) -period ([0-9.]+)')


def read_clocks(tcl):
    """pin -> (clock, R ps); clock -> period."""
    lat, per, pin_clk, pend = {}, {}, {}, []
    for ln in open(tcl):
        m = PIN.search(ln)
        if m and 'set p ' in ln:
            pend.append(m.group(1))
            continue
        m = CLK.search(ln)
        if m:
            per[m.group(1)] = float(m.group(2))
            for p in pend:
                pin_clk[p] = m.group(1)
            pend = []
            continue
        m = LAT.search(ln)
        if m:
            lat[m.group(3)] = (m.group(1), -float(m.group(2)))
    return lat, per, pin_clk


def norm(p):
    return p[:-3] if p.endswith('[0]') else p


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--geom', required=True, type=Path)
    ap.add_argument('--clocks-dir', required=True, type=Path)
    ap.add_argument('--out', required=True, type=Path)
    ap.add_argument('--die', default='qwen_compute')
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    cl = {c: read_clocks(a.clocks_dir / f'clocks_{c}.tcl') for c in ('tt', 'ff', 'ss')}
    lat_tt, per, pin_clk = cl['tt']
    views = json.loads((a.clocks_dir / 'views.json').read_text())
    real = set(views.get('real', {})) | set(views.get('hard_macro', {}))
    roots = collections.defaultdict(list)
    for ln in open(a.geom / 'clknets.tsv'):
        r, ld, m, x, y = ln.rstrip('\n').split('\t')
        roots[r].append((ld, m))
    trees, fam, masters, spread = [], {}, {}, collections.defaultdict(set)
    for r in sorted(roots):
        name = r.split('/')[-1].replace('pll_', '').replace('[0]', '')
        doms = collections.Counter()
        for ld, m in roots[r]:
            c = lat_tt.get(ld, lat_tt.get(norm(ld), (None,)))[0] or pin_clk.get(ld) or pin_clk.get(norm(ld))
            doms[(c or 'stream').replace('__early', '')] += 1
            port = ld.split('/', 1)[1]
            rr = []
            for c in ('ss', 'ff', 'tt'):
                v = cl[c][0].get(ld) or cl[c][0].get(norm(ld))
                rr.append(round(v[1], 3) if v else 0.0)
            spread[(m, port)].add(tuple(rr))
            mm = masters.setdefault(m, dict(view='real' if m in real else 'ASSUMED (ideal 0, no measured view)',
                                            source='chain libs/clocks_{ss,ff,tt}.tcl set_clock_latency -source',
                                            insertion_per_clock_pin_ps={}))
            old = mm['insertion_per_clock_pin_ps'].get(port)
            mm['insertion_per_clock_pin_ps'][port] = rr if old is None else [max(o, n) for o, n in zip(old, rr)]
        dom = doms.most_common(1)[0][0]
        trees.append(dict(name=name, root=r, period=round(per.get(dom, 833.333333), 6), domain=dom, select='all',
                          sinks=len(roots[r])))
        fam[name] = [r]
    varying = {f'{m}/{p}': sorted(v) for (m, p), v in spread.items() if len(v) > 1}
    spec = dict(die=a.die, note='Q-CLK 10-18 landed-regions standard: one tree per qfd_clkrx output (region), NO '
                'balance_group; only intra-region flop spread / pairs judged (<= 80 ps TT + FF); cross-region pairs '
                'must be LANDED (qwen_landed_pairs.py).', rc_layer='M8', leaf_um=60, leaf_max=12, trees=trees)
    (a.out / 'spec.json').write_text(json.dumps(spec, indent=1) + '\n')
    (a.out / 'families.json').write_text(json.dumps(fam, indent=1) + '\n')
    (a.out / 'targets.json').write_text(json.dumps(dict(
        schema='opentallas.die_clock.targets.v1', masters=masters, assumed=sorted(m for m in masters if m not in real),
        varying_R_across_instances=varying), indent=1) + '\n')
    print('QCLK_PREP trees', len(trees), 'sinks', sum(t['sinks'] for t in trees), 'masters', len(masters),
          'assumed', sum(m not in real for m in masters), 'varying_R', len(varying))


if __name__ == '__main__':
    main()
