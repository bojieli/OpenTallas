#!/usr/bin/env python3
"""QDIE-R56: share of a GRT probe's congestion-report overflow that sits on reset pad cells (rstt_* qfd_rst_rep*) and in
the r48 seam bands (y 5.40-5.53 / 10.75-10.93 / 15.20-15.38 / 20.60-20.74 mm).  usage: padband.py PROBE_OUT CASE_DIR"""
import re, sys, os, collections, glob
O, C = sys.argv[1], sys.argv[2]
BANDS = [(5400, 5530), (10750, 10930), (15200, 15380), (20600, 20740)]
tot = band = 0
typ = None; c = 0
for ln in open(O + '/grt_congestion_probe.rpt', errors='replace'):
    if ln.startswith('violation type'): typ = 'H' if 'Horizontal' in ln else 'V'
    elif 'congestion:' in ln: c = int(ln.rsplit('congestion:', 1)[1].split()[0])
    elif ln.strip().startswith('bbox'):
        pts = re.findall(r'\(\s*([\d.]+),\s*([\d.]+)\s*\)', ln)
        if not pts: continue
        y = (float(pts[0][1]) + float(pts[-1][1])) / 2
        tot += c
        if any(a - 50 <= y <= b + 50 for a, b in BANDS): band += c
# pad cell rows (from the GEN DEF placement of rstt_ cells)
ys = collections.Counter()
for f in glob.glob(C + '/*.def')[:1]:
    for ln in open(f, errors='replace'):
        m = re.match(r'\s*-\s+(rstt_\S+)\s+(qfd_rst_rep\S*)\s+\+\s+\S+\s+\(\s*(-?\d+)\s+(-?\d+)', ln)
        if m: ys[int(m.group(4)) // 1000 // 500 * 500] += 1
print(f'PADBAND report_overflow_sum {tot} in_r48_seam_bands {band} ({100.0*band/max(tot,1):.1f}%)')
if ys: print('RST_PAD_ROWS top y-bins(um:count)', ys.most_common(6))
