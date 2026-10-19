#!/usr/bin/env python3
"""GEN16 item 6 (10-19): die STA on the PHYSICAL die clock built before GRT (tools/qwen_split/chain_dieclk.sh).

The Qwen die STA clocks (chain libs/clocks_<c>.tcl, INSERTION_COMPENSATED, propagated) are created AT each block clock
pin with -source latency -R (the view's in-arc insertion).  The die clock tree in ckpt_grt.odb is upstream of those
pins, so its delay must enter as source latency: for every pin the build measured, the source latency becomes
A(pin) - R, A = the measured propagated arrival of the die clock at that pin (TT: late, FF: early; same STA setup as
build.py: placement parasitics, two-corner libs).  Pins the die clock does not reach (forwarded-lane hop clocks, PHY
faces) keep their ideal -R; they are counted.  Writes a Tcl block inserted after the clocks in grt_<c>.tcl.
  dieclk_sta_lat.py --clocks clocks_<c>.tcl --arrivals arrivals.tsv --col late|early --out dieclk_lat_<c>.tcl
Fails (exit 1) if fewer than --min-frac of the clocks' pins have a measured arrival."""
import argparse
import re
import sys

LAT = re.compile(r'set_clock_latency -source -clock \[get_clocks (\S+)\] (-?[0-9.]+) \[get_pins \{([^}]+)\}\]')


def norm(p):
    return p[:-3] if p.endswith('[0]') else p


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--clocks', required=True)
    ap.add_argument('--arrivals', required=True)
    ap.add_argument('--col', choices=('late', 'early'), required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--min-frac', type=float, default=0.5)
    a = ap.parse_args()
    arr = {}
    for ln in open(a.arrivals):
        f = ln.rstrip('\n').split('\t')
        v = f[1] if a.col == 'late' else f[2]
        if v not in ('NA', '', 'INF', '-INF'):
            arr[norm(f[0])] = float(v)
    rows, hit, miss = [], 0, []
    for ln in open(a.clocks):
        m = LAT.search(ln)
        if not m:
            continue
        clk, v, pin = m.group(1), float(m.group(2)), m.group(3)
        A = arr.get(norm(pin))
        if A is None:
            miss.append(pin)
            continue
        hit += 1
        rows.append(f'set_clock_latency -source -clock [get_clocks {clk}] {A + v:.1f} [get_pins {{{pin}}}]')
    tot = hit + len(miss)
    head = [f'# DIE CLOCK PHYS ({a.col} arrivals {a.arrivals}): source latency = measured die-clock arrival - R',
            f'puts "OT_DIE_CLOCK_PHYS col={a.col} measured={hit} ideal={len(miss)} of {tot}"']
    open(a.out, 'w').write('\n'.join(head + rows) + '\n')
    print(f'DIECLK_STA_LAT {a.col} measured {hit} ideal {len(miss)} of {tot} (ideal e.g. {" ".join(miss[:6])})')
    if not tot or hit < a.min_frac * tot:
        sys.exit(1)


if __name__ == '__main__':
    main()
