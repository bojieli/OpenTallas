#!/usr/bin/env python3
"""ot-clk P1b: per-region TritonCTS benchmark of a routed die clock tree (planner sanity check, INFO only, no gate).

For one clock region of a routed die trial, cut the region out as a stand-alone CTS problem (sinks at the routed tap
xy, root = the region's lowest common tree node, hard cores = CLASS BLOCK macros at their die outline whose clock pins
carry the declared core insertion relative to the die common latency as liberty max/min_clock_tree_path), run TritonCTS
variants in openroad/orfs:asap7lock (TT builds the tree, FF re-times it), and compare the nominal spread
max-min(arrival + declared insertion) with OUR routed arrivals of the same taps.  A region whose routed spread is more
than --flag-ps (20) worse than the best LEGAL TritonCTS variant is reported as a planner defect (INFO for the die owner;
cause first: stage model -> calibrate, then structure).  A variant is LEGAL only when check_placement passes and no
clock buffer sits inside a hard-core outline (repair_clock_nets ignores macro blockages; OR-CTS-PROBE-1).

Method and tcl generalise claude/or-cts-probe-1-1028@76e78b8c01 results/or_cts_probe_1_1028/scripts (extract/gen/cts/
ours/summ) from its two hand-cut regions to any die / region; no die name in this file.

Usage (fleet host only; docker):
  bench_cts.py prep  --plan P --tree TREE.json --arr-tt A --arr-ff A --region R [--region-map M] --out D
  bench_cts.py run   --out D [--variants v4,v6] [--mem-g 16] [--cpus 4]
  bench_cts.py summ  --out D [--flag-ps 20]
  bench_cts.py all   (prep + run + summ, same flags)
Region R = the taps of every partition mapped to R by --region-map ({"part_region": {part: region}}), else the taps of
partition R.
"""
import argparse
import json
import math
import os
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO / "tools" / "die_plan"))
TCL = HERE / "bench_cts"
IMAGE = "openroad/orfs:asap7lock"
# OR-CTS-PROBE-1 variants (README table): v4 = dist 250 + repair_clock_nets, v6 = dist 150 + repair (the two best)
VARIANTS = {
    "v1": "",
    "v4": "-distance_between_buffers 250 -repair_clock_nets",
    "v6": "-distance_between_buffers 150 -repair_clock_nets",
    "v8": "-distance_between_buffers 250",
}
SITE_W, ROW_H = 0.054, 0.27


def read_arr(path):
    """routed arrival file: 'T <port> <arrival> ...' (tap) and 'M <cell> <arrival>' (tree cell output) lines"""
    taps, cells = {}, {}
    for line in open(path):
        s = line.split()
        if len(s) >= 3 and s[0] == "T":
            taps[s[1]] = float(s[2])
        elif len(s) >= 3 and s[0] == "M":
            cells[s[1]] = float(s[2])
    return taps, cells


def load_plan(path):
    import schema as S                       # tools/die_plan (shared plan model)
    return S, S.Plan(json.loads(Path(path).read_text()), Path(path))


def region_parts(region, region_map, parts):
    if region_map:
        m = json.loads(Path(region_map).read_text())["part_region"]
        sel = sorted(p for p, r in m.items() if r == region)
    else:
        sel = [region] if region in parts else []
    if not sel:
        raise SystemExit(f"bench_cts: region {region!r} has no partition")
    return sel


def prep(a):
    S, P = load_plan(a.plan)
    T = json.loads(Path(a.tree).read_text())
    N = T["nodes"]
    parts = region_parts(a.region, a.region_map, P.parts)
    taps = [t for t in T["taps"] if t["part"] in parts]
    if len(taps) < 2:
        raise SystemExit(f"bench_cts: region {a.region}: {len(taps)} taps")
    # declared insertion per tap (schema: core taps = core insertion, every other tap = the die common latency)
    decl = {}
    core_ports = {}
    for p in parts:
        for port, _, _, tp in S.core_taps(P, P.parts[p]["type"]):
            core_ports[f"t_{p}__{port}"] = tp
    for t in taps:
        tp = core_ports.get(t["port"])
        decl[t["port"]] = {c: (S.core_tap_insertion_ps(tp, c) if tp else S.common_latency_ps(P, c)) for c in ("TT", "FF")}
    # region root = lowest common ancestor of the region taps in OUR tree
    def anc(n):
        r = []
        while n is not None:
            r.append(n)
            n = N[str(n)].get("parent")
        return r
    paths = [anc(t["node"]) for t in taps]
    common = set(paths[0]).intersection(*map(set, paths[1:]))
    lca = max(common, key=lambda n: N[str(n)]["level"])
    root = (N[str(lca)]["x"], N[str(lca)]["y"])
    # OUR routed spread
    ours = {}
    for c, f in (("TT", a.arr_tt), ("FF", a.arr_ff)):
        arr, _ = read_arr(f)
        miss = [t["port"] for t in taps if t["port"] not in arr]
        if miss:
            raise SystemExit(f"bench_cts: {f}: no arrival for {len(miss)} region taps, e.g. {miss[:3]}")
        v = [arr[t["port"]] + decl[t["port"]][c] for t in taps]
        lat = [arr[t["port"]] for t in taps]
        ours[c] = dict(spread=round(max(v) - min(v), 1), arr_min=round(min(lat), 1), arr_max=round(max(lat), 1))
    # hard cores of the region (die frame bbox of the plan outline) and their clock taps
    cores = []
    for p in parts:
        ty = P.types[P.parts[p]["type"]]
        for hc in ty.get("hard_cores", []) or []:
            (x0, y0), (w, h) = hc["origin_um"], hc["outline_um"]
            pts = [P.to_die(p, (x, y)) for x in (x0, x0 + w) for y in (y0, y0 + h)]
            cores.append(dict(inst=f"{p}__{hc['inst']}", rect=[min(q[0] for q in pts), min(q[1] for q in pts),
                                                                max(q[0] for q in pts), max(q[1] for q in pts)], taps=[]))
    glue, ctaps = [], []
    for t in taps:
        (ctaps if t["port"] in core_ports else glue).append(t)

    def dist(r, q):
        return math.hypot(max(r[0] - q[0], 0, q[0] - r[2]), max(r[1] - q[1], 0, q[1] - r[3]))
    for t in ctaps:
        if not cores:
            glue.append(t)
            continue
        c = min(cores, key=lambda c: dist(c["rect"], t["xy"]))
        c["taps"].append(t)
    cores = [c for c in cores if c["taps"]]
    xs = [t["xy"][0] for t in taps] + [root[0]] + [v for c in cores for v in (c["rect"][0], c["rect"][2])]
    ys = [t["xy"][1] for t in taps] + [root[1]] + [v for c in cores for v in (c["rect"][1], c["rect"][3])]
    M = 60.0
    DX0 = math.floor((min(xs) - M) / 0.216) * 0.216
    DY0 = math.floor((min(ys) - M) / 1.08) * 1.08
    DX1, DY1 = max(xs) + M, max(ys) + M
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)

    def loc(x, y):
        return round(x - DX0, 4), round(y - DY0, 4)
    common_c = {c: S.common_latency_ps(P, c) for c in ("TT", "FF")}
    if cores:
        lef = ['VERSION 5.8 ;\nBUSBITCHARS "[]" ;\nDIVIDERCHAR "/" ;\n']
        for k, c in enumerate(cores):
            x0, y0, x1, y1 = c["rect"]
            c["master"] = f"OTSINK{k}"
            pins = ""
            for i, t in enumerate(c["taps"]):
                px = min(max(t["xy"][0], x0 + 0.5), x1 - 0.5) - x0
                py = min(max(t["xy"][1], y0 + 0.5), y1 - 0.5) - y0
                pins += (f"  PIN clk{i}\n    DIRECTION INPUT ;\n    USE CLOCK ;\n    PORT\n      LAYER M7 ;\n        RECT "
                         f"{px-0.04:.3f} {py-0.04:.3f} {px+0.04:.3f} {py+0.04:.3f} ;\n    END\n  END clk{i}\n")
            lef.append(f"MACRO {c['master']}\n  CLASS BLOCK ;\n  ORIGIN 0 0 ;\n  SIZE {x1-x0:.3f} BY {y1-y0:.3f} ;\n"
                       f"  SYMMETRY X Y ;\n{pins}  OBS\n" + "".join(f"    LAYER M{m} ;\n      RECT 0 0 {x1-x0:.3f} {y1-y0:.3f} ;\n"
                                                              for m in range(1, 7)) + f"  END\nEND {c['master']}\n")
        lef.append("END LIBRARY\n")
        (out / "sink.lef").write_text("".join(lef))
        for C in ("TT", "FF"):
            s = [f'library (otsink_{C}) {{\n delay_model : table_lookup;\n time_unit : "1ps";\n voltage_unit : "1V";\n'
                 ' current_unit : "1mA";\n capacitive_load_unit (1,ff);\n pulling_resistance_unit : "1kohm";\n'
                 ' leakage_power_unit : "1nW";\n nom_voltage : 0.7; nom_temperature : 25; nom_process : 1;\n']
            for c in cores:
                s.append(f" cell ({c['master']}) {{\n  area : 1;\n  is_macro_cell : true;\n")
                for i, t in enumerate(c["taps"]):
                    rel = round(decl[t["port"]][C] - common_c[C], 1)
                    tim = "".join(f"   timing () {{ timing_type : {k}_clock_tree_path; timing_sense : positive_unate; "
                                  f"cell_rise (scalar) {{ values (\"{rel}\"); }} cell_fall (scalar) {{ values (\"{rel}\"); }} }}\n"
                                  for k in ("max", "min"))
                    s.append(f"  pin (clk{i}) {{\n   direction : input;\n   clock : true;\n   capacitance : 3.0;\n{tim}  }}\n")
                s.append(" }\n")
            s.append("}\n")
            (out / f"sink_{C}.lib").write_text("".join(s))
    v = ["module region (clk);\n input clk;\n"]
    for i, _ in enumerate(glue):
        v.append(f" DFFHQNx1_ASAP7_75t_R g{i} (.CLK(clk), .D(1'b0), .QN());\n")
    for k, c in enumerate(cores):
        v.append(f" {c['master']} m{k} (" + ", ".join(f".clk{i}(clk)" for i, _ in enumerate(c["taps"])) + ");\n")
    v.append("endmodule\n")
    (out / "region.v").write_text("".join(v))
    pl = [f"set DIE {{0 0 {DX1-DX0:.3f} {DY1-DY0:.3f}}}", f"set ROOT {{{loc(*root)[0]} {loc(*root)[1]}}}"]
    for i, t in enumerate(glue):
        x, y = loc(*t["xy"])
        pl.append(f"ot_fix g{i} {round(round(x / SITE_W) * SITE_W, 3)} {round(round(y / ROW_H) * ROW_H, 3)}")
    for k, c in enumerate(cores):
        x, y = loc(c["rect"][0], c["rect"][1])
        pl.append(f"ot_fix m{k} {x} {y}")
    (out / "place.tcl").write_text("\n".join(pl) + "\n")
    meta = dict(schema="ot_clk_bench_cts/1", region=a.region, parts=parts, plan=a.plan, tree=a.tree,
                arr=dict(TT=a.arr_tt, FF=a.arr_ff), lca=lca, root_die=root, origin=[DX0, DY0],
                ntaps=len(taps), glue=[dict(inst=f"g{i}", port=t["port"]) for i, t in enumerate(glue)],
                cores=[dict(inst=f"m{k}", name=c["inst"], rect_local=[round(c["rect"][0] - DX0, 3), round(c["rect"][1] - DY0, 3),
                                                                        round(c["rect"][2] - DX0, 3), round(c["rect"][3] - DY0, 3)],
                            pins={f"clk{i}": t["port"] for i, t in enumerate(c["taps"])}) for k, c in enumerate(cores)],
                declared=decl, ours=ours)
    (out / "meta.json").write_text(json.dumps(meta, indent=1) + "\n")
    print(json.dumps(dict(region=a.region, parts=len(parts), taps=len(taps), glue=len(glue), cores=len(cores),
                          core_taps=sum(len(c["taps"]) for c in cores), ours=ours)))


def run(a):
    out = Path(a.out).resolve()
    for v in a.variants.split(","):
        (out / v).mkdir(exist_ok=True)
        for C in ("TT", "FF"):
            cmd = ["docker", "run", "--rm", "--name", f"otclk-bench-{os.getpid()}-{v}-{C}", f"--memory={a.mem_g}g",
                   f"--memory-swap={a.mem_g}g", f"--cpus={a.cpus}", "-e", f"CORNER={C}", "-e", "D=/w", "-e", f"V={v}",
                   "-e", f"OPTS={VARIANTS[v]}", "-e", "TRACKS=/t/tracks.tcl", "-v", f"{out}:/w", "-v", f"{TCL}:/t:ro",
                   IMAGE, "bash", "-lc",
                   "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -no_init -threads 4 -exit /t/cts.tcl"
                   f" > /w/{v}/log_{C}.txt 2>&1; echo EXIT $? >> /w/{v}/log_{C}.txt; chown -R {os.getuid()}:{os.getgid()} /w/{v}"]
            rc = subprocess.call(cmd)
            print(f"{v} {C} rc={rc}", flush=True)


def summ(a):
    out = Path(a.out)
    meta = json.loads((out / "meta.json").read_text())
    pin_port = {f"{c['inst']}/{p}": port for c in meta["cores"] for p, port in c["pins"].items()}
    glue_port = {f"{g['inst']}/CLK": g["port"] for g in meta["glue"]}
    rects = [c["rect_local"] for c in meta["cores"]]
    rows = []
    for v in sorted(d.name for d in out.iterdir() if d.is_dir() and (d / "arr_FF.txt").is_file()):
        d = out / v
        row = dict(variant=v, opts=VARIANTS.get(v))
        log = (d / "log_TT.txt").read_text(errors="replace")
        inside = 0
        for C in ("TT", "FF"):
            arr, nb, slew = {}, 0, 0.0
            for line in open(d / f"arr_{C}.txt"):
                s = line.split()
                if s[0] == "S":
                    port = glue_port.get(s[1]) or pin_port.get(s[1])
                    if port:
                        arr[port] = float(s[2])
                        slew = max(slew, float(s[4]))
                elif s[0] == "B":
                    nb += 1
                    if C == "TT":
                        x, y = float(s[3]), float(s[4])
                        inside += any(r[0] < x < r[2] and r[1] < y < r[3] for r in rects)
            if len(arr) != meta["ntaps"]:
                row[C] = dict(error=f"{len(arr)} of {meta['ntaps']} sinks timed")
                continue
            vals = [arr[p] + meta["declared"][p][C] for p in arr]
            row[C] = dict(spread=round(max(vals) - min(vals), 1), arr_min=round(min(arr.values()), 1),
                          arr_max=round(max(arr.values()), 1), max_slew=round(slew, 1), nbuf=nb)
        row["bufs_inside_cores"] = inside
        row["check_placement_fail"] = "OT_CHECK_PLACEMENT_FAIL" in log
        row["done"] = "OT_DONE" in log
        row["legal"] = row["done"] and not row["check_placement_fail"] and inside == 0 and "spread" in row.get("TT", {})
        rows.append(row)
    legal = [r for r in rows if r["legal"]]
    best = min(legal, key=lambda r: r["TT"]["spread"]) if legal else None
    ours = meta["ours"]
    res = dict(schema="ot_clk_bench_cts/1", region=meta["region"], ntaps=meta["ntaps"], ncores=len(meta["cores"]),
               ours=ours, variants=rows, best_legal=best and best["variant"], flag_ps=a.flag_ps)
    if best:
        res["delta_TT"] = round(ours["TT"]["spread"] - best["TT"]["spread"], 1)
        res["delta_FF"] = round(ours["FF"]["spread"] - best["FF"]["spread"], 1)
        res["verdict"] = "PLANNER_DEFECT" if max(res["delta_TT"], res["delta_FF"]) > a.flag_ps else "OK"
    else:
        res["verdict"] = "NO_LEGAL_TRITONCTS"     # TritonCTS could not build a legal tree here: nothing to compare
    (out / "bench.json").write_text(json.dumps(res, indent=1) + "\n")
    print(json.dumps({k: res[k] for k in ("region", "ours", "best_legal", "verdict") if k in res} |
                     {k: res[k] for k in ("delta_TT", "delta_FF") if k in res}))
    return res


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=("prep", "run", "summ", "all"))
    ap.add_argument("--out", required=True)
    ap.add_argument("--plan")
    ap.add_argument("--tree")
    ap.add_argument("--arr-tt")
    ap.add_argument("--arr-ff")
    ap.add_argument("--region")
    ap.add_argument("--region-map")
    ap.add_argument("--variants", default="v4,v6")
    ap.add_argument("--mem-g", type=int, default=16)
    ap.add_argument("--cpus", type=int, default=4)
    ap.add_argument("--flag-ps", type=float, default=20.0)
    a = ap.parse_args(argv)
    if a.cmd in ("prep", "all"):
        prep(a)
    if a.cmd in ("run", "all"):
        run(a)
    if a.cmd in ("summ", "all"):
        summ(a)
    return 0


if __name__ == "__main__":
    sys.exit(main())
