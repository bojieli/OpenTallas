#!/usr/bin/env python3
"""Approved HEAD-33 local density-entry fix from a placed register census."""
import collections
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'tools/die_plan'), str(ROOT / 'tools/autopilot')]
import geom_rules as G
import schema
import taps

plan_path, dump_path, out_path = map(Path, sys.argv[1:4])
raw = json.loads(plan_path.read_text())
D = G.Design(dump_path)
bins = collections.Counter()
excluded = collections.Counter()
for cid, cell in D.cells.items():
    clocks = [n for n, clock in D.cell_in.get(cid, []) if clock]
    if cell[0] != 'S' or not clocks:
        continue
    net = clocks[0]
    seen = set()
    root = None
    while net not in seen:
        seen.add(net)
        driver = D.nets[net][1]
        if driver is None:
            break
        if driver[0] == 'p':
            root = D.pin_by_k[driver[1]]['name']
            break
        inputs = D.cell_in.get(driver[1], [])
        if D.kind(driver[1]) not in ('B', 'K') or not inputs:
            break
        ck = [n for n, clock in inputs if clock]
        net = ck[0] if ck else inputs[0][0]
    if root != 'clk' and not (root or '').startswith('clk_t'):
        excluded[str(root)] += 1
        continue
    x, y = G.ctr(cell)
    bins[(int(x // 10.8), int(y // 10.8))] += 1
clock = raw['partition_types']['hd_tile']['clock']
clock.update(tap_mode='density', tap_radius_um=200, tap_max_sinks=1500,
             tap_target_sinks=1200, control_sinks=False)
bins_path = out_path.parent / 'hd_tile_sink_bins.json'
bins_path.write_text(json.dumps(dict(bin_um=10.8, n=sum(bins.values()),
    bins=[[(x+.5)*10.8, (y+.5)*10.8, n] for (x,y),n in sorted(bins.items())],
    source=str(dump_path), excluded_clock_roots=dict(excluded)), indent=1)+'\n')
clock['sink_bins_file'] = str(bins_path)
P = schema.Plan(raw, path=plan_path)
out_path.write_text(json.dumps(raw, separators=(',', ':'))+'\n')
try:
    report = taps.report(P, 'hd_tile')
except ValueError as error:
    report = dict(verdict='FAIL', reason=str(error), route_qualified=False,
                  local_sinks=sum(bins.values()), excluded_clock_roots=dict(excluded),
                  added_cycles=0, source=str(plan_path))
    (out_path.parent / 'density_report.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report))
    raise SystemExit(1)
report.update(local_sinks=sum(bins.values()), excluded_clock_roots=dict(excluded), added_cycles=0,
              approval='COORD 2026-10-29 18:43 hd_tile density r200 local fix')
out_path.write_text(json.dumps(raw, separators=(',', ':'))+'\n')
(out_path.parent / 'density_report.json').write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k != 'taps'}))
