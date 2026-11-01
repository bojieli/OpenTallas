#!/usr/bin/env python3
"""DIE-HEAD-51 helper st (l48w-st die clock event): hang the EXISTING HEAD START stage clock ports (t_st_<id>__clk of
head_source_l48w/start_stages_src25q.json, RTL unchanged) on the l48c die clock as real sinks, at the tree nodes chosen in
the re-anchored bind (st_remap.py, bind start_tree_remap.map {stage id: base36 node path}).

Same construction as start_stage_emit.emit (tools/die_plan, reused: ctree_cells, polarity, the ctree.v/ctree.tcl patch
form): one output port per stage driven by its node cell's output net (the cell's INPUT net when the cell output is of
inverted polarity, die_trial --clock-cell inv), pin on M9 at the stage's existing clock pin site.  Writes a stages doc
whose region is 'st:<node path>@<stage id>' so start_stage_emit.py proof keys the measured pins exactly as the bind
('__st__<path>@<id>').
usage: st_ctree.py BIND STAGES TREE_JSON KIT_CLOCK_DIR SSE_DIR OUT_DIR [ENTRY_BUF_MASTER]
ENTRY_BUF_MASTER (e.g. BUFx8_ASAP7_75t_R): one local clock-entry buffer per stage beside its node cell.  Without it
(first build l48w-st a) 1251 legs up to 700 um hung directly on tree nets moved existing taps by up to +318 ps."""
import json, re, sys
from pathlib import Path

bindf, stagesf, treef, kdir, sse, out = sys.argv[1:7]
ENTRY = sys.argv[7] if len(sys.argv) > 7 else None   # optional local clock-entry buffer master (local_entry.py form)
ENTRY_W = {"BUFx8_ASAP7_75t_R": 0.648}
import os
PINBUF_HOP = float(os.environ.get("PINBUF_HOP", "0"))
CHAIN_UM = float(os.environ.get("CHAIN_UM", "0"))   # >0: ENTRY repeaters every CHAIN_UM along the L leg (x then y) + one at the pin end, every stage   # >0: legs longer than this get a second ENTRY buffer at the pin end
sys.path.insert(0, sse)
import start_stage_emit as E

b = json.loads(Path(bindf).read_text()); mp = b["start_tree_remap"]["map"]
old = json.loads(Path(stagesf).read_text())
T = json.loads(Path(treef).read_text())
kdir, out = Path(kdir), Path(out); out.mkdir(parents=True, exist_ok=True)
cv, ct = (kdir / "ctree.v").read_text(), (kdir / "ctree.tcl").read_text()
cells, cxy = E.ctree_cells(cv, ct)
CH = "0123456789abcdefghijklmnopqrstuvwxyz"
nodes = {int(k): v for k, v in T["nodes"].items()}
buf = {int(k): v for k, v in T["node_buf"].items()}
root = next(i for i, n in nodes.items() if n["parent"] is None)
path, stack = {}, [(root, "h")]
while stack:                                  # trial_tap_arrivals (non-physical) node keys
    i, p = stack.pop(); path[i] = p
    stack += [(c, p + CH[k]) for k, c in enumerate(nodes[i].get("kids", []))]
cell_of = {p: buf[i] for i, p in path.items()}
path_of_cell = {}
for p, c in sorted(cell_of.items(), key=lambda x: len(x[0])):
    path_of_cell.setdefault(c, p)
driver = {y: k for k, (_, _, y) in cells.items()}
roots_in = set(re.findall(r"\binput\s+(?:wire\s+)?([A-Za-z_][A-Za-z0-9_$]*)\s*;", cv))
stages, nodd, rep = [], 0, 0
for s in old["stages"]:
    p = mp[s["id"]]; c = cell_of[p]
    if c not in cells:
        raise SystemExit(f"{s['id']}: node {p} cell {c} not in ctree.v")
    inv = E.polarity(cells, c) % 2
    net = cells[c][1] if inv else cells[c][2]
    src = driver.get(net)
    nodd += inv
    if src is None:
        if net not in roots_in:
            raise SystemExit(f"{s['id']}: net {net} undriven")
        sp_, sroot = "__source__", True
    else:
        sroot = False
        sp_ = p if not inv else path_of_cell.get(src)
        if sp_ is None:                       # driver is a repeater, not a tree-node cell: walk up to a node cell
            rep += 1; q = src
            while q is not None and q not in path_of_cell:
                q = driver.get(cells[q][1])
            sp_ = path_of_cell[q] if q is not None else "__source__"
            sroot = q is None
    n = dict(s); n.update(region=f"st:{p}@{s['id']}", tree_path_id=p, node_cell=c, node_xy_um=list(cxy[c]),
                          clock_source_path=sp_, clock_source_cell=src, clock_source_root=sroot,
                          clock_source_stages=0, clock_net=net, clock_from="A" if inv else "Y",
                          hk5_region=s["region"], hk5_node_cell=s["node_cell"])
    stages.append(n)
have = {q.strip() for q in re.search(r"module\s+(\w+)\s*\(([^)]*)\);", cv).group(2).split(",")}
assert not [s["clock_port"] for s in stages if s["clock_port"] in have]
mh = re.search(r"module\s+(\w+)\s*\(([^)]*)\);", cv)
ports = [s["clock_port"] for s in stages]
v = cv[:mh.start(2)] + mh.group(2) + ", " + ", ".join(ports) + cv[mh.end(2):]
k = v.index(";", v.index("module")) + 1
v = v[:k] + "".join(f"\n  output {q};" for q in ports) + v[k:]
e = v.rindex("endmodule")
if ENTRY:
    # one non-inverting entry buffer per stage beside its node cell (tools/clk/local_entry.py idea: the node net sees
    # one buffer input, the long leg to the stage pin is driven by the buffer); placed by start_stage_emit.place_stage
    rows = E.Rows()
    for inst, (x, y) in cxy.items():
        rows.add(x, x + E.CLK_CELL_W_UM, y)
    import math
    body = []
    for s in stages:
        r = E.place_stage(cxy[s["node_cell"]], math.ceil(ENTRY_W[ENTRY] / E.FLOP_W_UM), rows)
        rows.add(r[0], r[0] + ENTRY_W[ENTRY], r[1])
        s["entry_buffer"] = dict(cell=ENTRY, inst=f"stbuf_{s['id']}", xy_um=r[:2], net=f"stn_{s['id']}")
        h = abs(cxy[s["node_cell"]][0] - s["clock_pin_xy_um"][0]) + abs(cxy[s["node_cell"]][1] - s["clock_pin_xy_um"][1])
        if CHAIN_UM > 0:
            (x0, y0), (x1, y1) = cxy[s["node_cell"]], s["clock_pin_xy_um"]; dx, dy = x1 - x0, y1 - y0
            def at(t):
                return (x0 + math.copysign(t, dx), y0) if t <= abs(dx) else (x1, y0 + math.copysign(t - abs(dx), dy))
            pts = [at(k * CHAIN_UM) for k in range(1, int(h // CHAIN_UM) + 1) if h - k * CHAIN_UM > 20.0] + [(x1, y1)]
            prev = f"stn_{s['id']}"; txt = f"  wire stn_{s['id']};\n  {ENTRY} stbuf_{s['id']} (.A({s['clock_net']}), .Y(stn_{s['id']}));\n"
            s["chain"] = []
            for j, (px, py) in enumerate(pts):
                py = round(round(py / E.ROW_UM) * E.ROW_UM, 3); px = round(round(px / 0.054) * 0.054, 3)
                q = E.place_stage((px, py), math.ceil(ENTRY_W[ENTRY] / E.FLOP_W_UM), rows)
                rows.add(q[0], q[0] + ENTRY_W[ENTRY], q[1])
                nm = f"stc{j}_{s['id']}"; s["chain"].append(dict(inst=nm, xy_um=q[:2]))
                txt += f"  wire {nm}_y;\n  {ENTRY} {nm} (.A({prev}), .Y({nm}_y));\n"; prev = f"{nm}_y"
            body.append(txt + f"  assign {s['clock_port']} = {prev};\n")
        elif PINBUF_HOP > 0 and h > PINBUF_HOP:
            px, py = s["clock_pin_xy_um"]; py = round(round(py / E.ROW_UM) * E.ROW_UM, 3); px = round(round(px / 0.054) * 0.054, 3)
            q = E.place_stage((px, py), math.ceil(ENTRY_W[ENTRY] / E.FLOP_W_UM), rows)
            rows.add(q[0], q[0] + ENTRY_W[ENTRY], q[1])
            s["pin_buffer"] = dict(cell=ENTRY, inst=f"stbufp_{s['id']}", xy_um=q[:2], net=f"stp_{s['id']}", hop_um=round(h, 1))
            body.append(f"  wire stn_{s['id']};\n  wire stp_{s['id']};\n  {ENTRY} stbuf_{s['id']} (.A({s['clock_net']}), .Y(stn_{s['id']}));\n"
                        f"  {ENTRY} stbufp_{s['id']} (.A(stn_{s['id']}), .Y(stp_{s['id']}));\n  assign {s['clock_port']} = stp_{s['id']};\n")
        else:
            body.append(f"  wire stn_{s['id']};\n  {ENTRY} stbuf_{s['id']} (.A({s['clock_net']}), .Y(stn_{s['id']}));\n"
                        f"  assign {s['clock_port']} = stn_{s['id']};\n")
    v = v[:e] + "".join(body) + v[e:]
else:
    v = v[:e] + "".join(f"  assign {s['clock_port']} = {s['clock_net']};\n" for s in stages) + v[e:]
pins = "".join(f"place_pin -pin_name {s['clock_port']} -layer M9 -location {{{s['clock_pin_xy_um'][0]:.3f} "
               f"{s['clock_pin_xy_um'][1]:.3f}}} -pin_size {{0.04 0.32}}\n" for s in stages)
m = list(re.finditer(r"^place_pin .*\n", ct, re.M))
t = ct[:m[-1].end()] + pins + ct[m[-1].end():]
if ENTRY:
    mi = list(re.finditer(r"^place_inst .*\n", t, re.M))
    t = t[:mi[-1].end()] + "".join(f"place_inst -name {s['entry_buffer']['inst']} -location {{{s['entry_buffer']['xy_um'][0]:.3f} "
                                    f"{s['entry_buffer']['xy_um'][1]:.3f}}} -status PLACED\n" for s in stages) + "".join(
        f"place_inst -name {s['pin_buffer']['inst']} -location {{{s['pin_buffer']['xy_um'][0]:.3f} {s['pin_buffer']['xy_um'][1]:.3f}}} -status PLACED\n"
        for s in stages if "pin_buffer" in s) + "".join(
        f"place_inst -name {c['inst']} -location {{{c['xy_um'][0]:.3f} {c['xy_um'][1]:.3f}}} -status PLACED\n"
        for s in stages for c in s.get("chain", ())) + t[mi[-1].end():]
(out / "ctree.v").write_text(v); (out / "ctree.tcl").write_text(t)
doc = dict(old, stages=stages, l48w_st=dict(bind=str(bindf), map_from="start_tree_remap.map", odd_nodes_on_A=nodd,
                                            repeater_driven=rep))
(out / "start_stages_l48w_st.json").write_text(json.dumps(doc, indent=1) + "\n")
hop = sorted(abs(cxy[s["node_cell"]][0] - s["clock_pin_xy_um"][0]) + abs(cxy[s["node_cell"]][1] - s["clock_pin_xy_um"][1]) for s in stages)
print("chain buffers", sum(len(s.get("chain", ())) for s in stages), "pin-end buffers", sum("pin_buffer" in s for s in stages), "stages", len(stages), "odd->A", nodd, "repeater-driven", rep, "source-root", sum(s["clock_source_root"] for s in stages),
      "cell->pin um p50/p90/max", round(hop[len(hop)//2]), round(hop[int(.9*len(hop))]), round(hop[-1]))
