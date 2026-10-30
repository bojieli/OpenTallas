#!/usr/bin/env python3
"""DIE-HEAD-34 src25p (2026-10-29): clock.sink_bins_file for a HEAD ft/shim strip type from its placed HEAD-KITS-T
geometry dump (same census as Codex head_tile_density_1847.py: sequential cells whose clock traces through buffers to
the type clk / clk_t<i> port; forwarded-clock (fclk_*) ring registers are excluded, they have their own edge entry).
usage: strip_sink_bins.py GEOM_TSV TYPE OUT_JSON"""
import collections, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / "tools/die_plan"), str(ROOT / "tools/autopilot")]
import geom_rules as G
dump, tn, out = sys.argv[1:4]
D = G.Design(Path(dump))
bins, excluded = collections.Counter(), collections.Counter()
for cid, cell in D.cells.items():
    clocks = [n for n, c in D.cell_in.get(cid, []) if c]
    if cell[0] != "S" or not clocks:
        continue
    net, seen, root = clocks[0], set(), None
    while net not in seen:
        seen.add(net)
        drv = D.nets[net][1]
        if drv is None:
            break
        if drv[0] == "p":
            root = D.pin_by_k[drv[1]]["name"]; break
        ins = D.cell_in.get(drv[1], [])
        if D.kind(drv[1]) not in ("B", "K") or not ins:
            break
        ck = [n for n, c in ins if c]
        net = ck[0] if ck else ins[0][0]
    if root != "clk" and not (root or "").startswith("clk_t"):
        excluded[str(root)] += 1; continue
    x, y = G.ctr(cell)
    bins[(int(x // 10.8), int(y // 10.8))] += 1
Path(out).write_text(json.dumps(dict(bin_um=10.8, n=sum(bins.values()), type=tn,
    bins=[[round((x + .5) * 10.8, 3), round((y + .5) * 10.8, 3), n] for (x, y), n in sorted(bins.items())],
    source=str(dump), excluded_clock_roots=dict(excluded)), indent=1) + "\n")
print(tn, "local sinks", sum(bins.values()), "bins", len(bins), "excluded", dict(excluded))
