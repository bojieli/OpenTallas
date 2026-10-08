#!/usr/bin/env python3
"""Qwen ROM die: classify a full-die GRT congestion report (global_route -congestion_report_file) by region kind
(tile body / corridor / channel / spine / ...), direction, layer and the bus class of the nets that cross each
overflowed gcell, so a design change can target the cause instead of sweeping settings.

    python3 tools/qwen_die_grt_congestion.py RPT GEOM.json [--out summary.json]

GEOM.json = {"regions": [{name, kind, rect}], "insts": [[name, master, x, y, w, h], ...]} from the floorplan model.
Overflow per violation = usage - capacity (the report's "congestion"); totals are sums over the reported gcells."""
import argparse
import collections
import json
import re
from pathlib import Path

NET_CLASS = [(r'^n_tree_', 'tree_block'), (r'^n_bword_', 'tree_spine'), (r'^n_pword_|^n_pfrag_', 'tree_spine'),
             (r'^n_cor_', 'corridor'), (r'^n_tap_', 'tap'), (r'^n_head_', 'head_chain'), (r'^n_kvl', 'kv_land'),
             (r'^n_lnk', 'link'), (r'^n_cdc', 'cdc'), (r'^n_hcdc|^n_hbm', 'hbm_cdc')]


def ncls(n):
    for p, c in NET_CLASS:
        if re.search(p, n):
            return c
    return n.split('[')[0][:24]


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('rpt', type=Path)
    ap.add_argument('geom', type=Path)
    ap.add_argument('--out', type=Path)
    a = ap.parse_args(argv)
    g = json.loads(a.geom.read_text())
    regs = [r for r in g['regions'] if r['kind'] != 'tile_field'] + [r for r in g['regions'] if r['kind'] == 'tile_field']
    big = [i for i in g['insts'] if i[4] * i[5] > 5e4 and not i[1].startswith('qfd_tile')]

    def where(x, y):
        for r in regs:
            x0, y0, x1, y1 = r['rect']
            if x0 <= x <= x1 and y0 <= y <= y1:
                return 'tile_body' if r['kind'] == 'tile_field' else r['kind']
        for n, mst, ix, iy, w, h in big:
            if ix <= x <= ix + w and iy <= y <= iy + h:
                return 'over_' + mst
        return 'other'

    tot = collections.Counter()
    by = collections.defaultdict(collections.Counter)
    hot = collections.Counter()
    vt = src = None
    for line in a.rpt.open():
        line = line.strip()
        if line.startswith('violation type:'):
            vt = line.split(':', 1)[1].strip().split()[0]
        elif line.startswith('srcs:'):
            src = [s[4:] for s in line.split()[1:] if s.startswith('net:')]
        elif line.startswith('comment:'):
            ov = int(re.search(r'congestion:(\d+)', line).group(1))
        elif line.startswith('bbox'):
            x0, y0, x1, y1 = map(float, re.findall(r'-?\d+\.?\d*', line.split('=')[1])[:4])
            x, y = (x0 + x1) / 2, (y0 + y1) / 2
            w = where(x, y)
            tot[vt] += ov
            by['region'][(w, vt)] += ov
            cl = collections.Counter(ncls(n) for n in src or [])
            for c, k in cl.items():
                by['class_hits'][(c, vt)] += k
            by['dominant'][(cl.most_common(1)[0][0] if cl else '-', w, vt)] += ov
            hot[(round(x / 500) * 500, round(y / 500) * 500)] += ov
    res = dict(total=dict(tot), overflow=sum(tot.values()),
               by_region={f'{k[0]}|{k[1]}': v for k, v in by['region'].most_common()},
               dominant_class={f'{k[0]}|{k[1]}|{k[2]}': v for k, v in by['dominant'].most_common(25)},
               class_hits={f'{k[0]}|{k[1]}': v for k, v in by['class_hits'].most_common(20)},
               hotspots_500um=[[k[0], k[1], v] for k, v in hot.most_common(25)])
    s = json.dumps(res, indent=1)
    if a.out:
        a.out.write_text(s + '\n')
    print(s)


if __name__ == '__main__':
    main()
