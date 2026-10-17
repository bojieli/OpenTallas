#!/usr/bin/env python3
"""Shared die-level clock check (ROOT 2026-10-16, coordinator direction; reuses H-DIE's clock model of main 9bcff2c0b).

Every die flow (S81, Qwen compute, Qwen KV/system, HBM) runs it on every die trial:

 1. In the trial's OpenROAD session, after the die clock tree is placed and the die STA is set up
    (read_sdc + set_propagated_clock + estimate_parasitics), dump the clock network:
        set ::env(OT_DCC_OUT) /work/out/die_clock_dump.tsv
        source <copy of tools/die_clock_check.tcl>
    (OT_DCC_STA=0 dumps topology only; OT_DCC_ROOTS overrides the SDC clock sources; see the .tcl header.)
 2. python3 tools/die_clock_check.py report die_clock_dump.tsv --out die_clock_check.json [--pairs bus_pairs.json]

It reports, for every tile clock entry pin (a block instance's clock input):
  (a) MODEL insertion from the generated tree's topology, cell and wire positions (H-DIE's repeater-stage model
      tools/hbm_die_v15/die_clock_tree.stage_ps over the Manhattan wire between successive tree nodes), and
  (b) MEASURED insertion = the die STA's propagated clock arrival at that pin (OpenSTA arrival_max_rise/min_rise);
and, for every pair of tiles that exchange data (tiles sharing a die net with <= OT_DCC_MAX_FANOUT tiles, plus any
--pairs list from a die bus list), the NON-COMMON clock path: from the pair's last common tree node (the branch point)
to each tile's entry, model and measured.  noncommon = max(side_a, side_b) (as clock_alt_model.py), side_a + side_b is
also kept.  No pass/fail threshold yet (the coordinator sets it after the first numbers): the report only measures.

Usage:
  die_clock_check.py report DUMP.tsv [--out JSON] [--pairs PAIRS.json] [--top N]
  die_clock_check.py tcl            # print the path of the Tcl dumper
PAIRS.json: [[instA, instB], ...] or {"pairs": [[instA, instB, note?], ...]} (tile instance names as in the die db).
The optional "entry_pairs" list names literal inst/clock_pin nodes, so related
clock entries within one tile and specific same-domain branches can be measured.
"""
import argparse, json, os, statistics, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "hbm_die_v15"))
from die_clock_tree import stage_ps  # H-DIE's measured-calibrated repeater stage model (9bcff2c0b)

SPAN = 420.0   # um per modelled repeater stage, as clock_alt_model.py


def wire_ps(L):
    """H-DIE model delay of L um of buffered clock wire (clock_alt_model.py A())."""
    return stage_ps(min(L, SPAN)) * max(1.0, L / SPAN)


def num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def load(path):
    nodes, pairs, summary = {}, [], {}
    with open(path) as fh:
        for ln in fh:
            f = ln.rstrip("\n").split("\t")
            k = f[0]
            if k == "R":
                nodes[f[1]] = dict(kind="root", cell=None, x=float(f[2]), y=float(f[3]), parent=None,
                                   sta_max=num(f[4]), sta_min=num(f[5]))
            elif k in ("B", "T", "F"):
                nodes[f[1]] = dict(kind={"B": "cell", "T": "tile", "F": "flop"}[k], cell=f[2], x=float(f[3]),
                                   y=float(f[4]), parent=f[5], sta_max=num(f[6]), sta_min=num(f[7]))
            elif k == "P":
                pairs.append((f[1], f[2], f[3] if len(f) > 3 else ""))
            elif k == "S":
                summary[f[1]] = f[2]
    return nodes, pairs, summary


def model_arrivals(nodes):
    arr = {}
    def A(n):
        stack = []
        while n not in arr:
            p = nodes[n]["parent"]
            if p is None or p not in nodes:
                arr[n] = 0.0
                break
            stack.append(n)
            n = p
        while stack:
            c = stack.pop()
            p = nodes[c]["parent"]
            L = abs(nodes[c]["x"] - nodes[p]["x"]) + abs(nodes[c]["y"] - nodes[p]["y"])
            arr[c] = arr[p] + wire_ps(L)
        return arr[n]
    for n in nodes:
        A(n)
    return arr


def ancestors(nodes, n):
    out = []
    while n is not None and n in nodes:
        out.append(n)
        n = nodes[n]["parent"]
    return out


def stats(v):
    v = sorted(x for x in v if x is not None)
    if not v:
        return None
    return dict(n=len(v), min=round(v[0], 1), median=round(statistics.median(v), 1),
                p90=round(v[min(len(v) - 1, int(0.9 * len(v)))], 1), max=round(v[-1], 1), spread=round(v[-1] - v[0], 1))


def region_of(nodes, anc):
    """DIE-CLOCK 2026-10-16: the clock region of an entry = the tree of its leaf cell (cells named dc_<region>_<kind><n>
    by tools/die_clock/build.py); otherwise the clock root it hangs from (H-DIE / Codex trees, ideal nets)."""
    import re
    for a in anc:
        if nodes[a]["kind"] == "cell":
            m = re.match(r"^dc_(.+?)_[LBRTP]\d+(?:_(?:tp|gp|hp)\d+)*$", a)
            if m:
                return m.group(1)
    return anc[-1]


def load_targets(path):
    """kit.json masters -> (master, port) -> TT in-arc insertion R (die_sta.py balance_latency semantics)."""
    if not path:
        return None
    km = json.load(open(path))["masters"]
    def R(master, pin):
        port = pin.rsplit("/", 1)[1]
        port = port[:-3] if port.endswith("[0]") else port
        r = km.get(master, {})
        v = r.get("insertion_per_clock_pin_ps", {}).get(port) or r.get("insertion_in_arcs_ps")
        return v[2] if v else 0.0
    return R


def report(dump, pairs_file=None, top=20, targets=None, strict_entry_pairs=False):
    nodes, pairs, summ = load(dump)
    model = model_arrivals(nodes)
    R = load_targets(targets)
    entries = {}   # tile inst -> [entry pin nodes]
    for n, d in nodes.items():
        if d["kind"] == "tile":
            entries.setdefault(n.rsplit("/", 1)[0], []).append(n)
    tiles = []
    for inst, pins in sorted(entries.items()):
        for p in pins:
            d = nodes[p]
            anc = ancestors(nodes, p)
            tiles.append(dict(inst=inst, entry=p, master=d["cell"], x=d["x"], y=d["y"], root=anc[-1],
                              region=region_of(nodes, anc), R_tt_ps=(R(d["cell"], p) if R else None),
                              levels=sum(1 for a in anc if nodes[a]["kind"] == "cell"),
                              model_ps=round(model[p], 1), sta_max_ps=d["sta_max"], sta_min_ps=d["sta_min"]))
    src = "netlist"
    allpairs = [(a, b, net, src) for a, b, net in pairs]
    if pairs_file:
        pj = json.load(open(pairs_file))
        for e in (pj.get("pairs", []) if isinstance(pj, dict) else pj):
            allpairs.append((e[0], e[1], e[2] if len(e) > 2 else "", "bus_list"))
        if isinstance(pj, dict):
            for e in pj.get("entry_pairs", []):
                allpairs.append((e[0], e[1], e[2] if len(e) > 2 else "", "literal_entry_list"))
    seen, prs, missing, cross = set(), [], [], 0
    anc_cache = {}
    def anc_of(p):
        if p not in anc_cache:
            anc_cache[p] = ancestors(nodes, p)
        return anc_cache[p]
    for a, b, net, how in allpairs:
        key = tuple(sorted((a, b)))
        if key in seen:
            continue
        seen.add(key)
        def entry_nodes(name):
            if name in nodes and nodes[name]['kind'] == 'tile':
                return [name]
            return entries.get(name, [])
        left, right = entry_nodes(a), entry_nodes(b)
        if not left or not right:
            missing.append([a, b, how])
            continue
        if strict_entry_pairs and (len(left) != 1 or len(right) != 1):
            raise ValueError(f'ambiguous timed pair {a} -> {b}: {len(left)} x {len(right)} clock entries; literal launch/capture entries required')
        best = None
        for pa in left:
            for pb in right:
                aa, ab = anc_of(pa), set(anc_of(pb))
                lca = next((k for k in aa if k in ab), None)
                if lca is None:
                    rec = dict(entry_a=pa, entry_b=pb, lca=None)   # different clock roots: no common path at all
                else:
                    ma, mb = model[pa] - model[lca], model[pb] - model[lca]
                    rec = dict(entry_a=pa, entry_b=pb, lca=lca,
                               model_a_ps=round(ma, 1), model_b_ps=round(mb, 1), model_ps=round(max(ma, mb), 1),
                               model_sum_ps=round(ma + mb, 1))
                    sl, sa, sb = nodes[lca]["sta_max"], nodes[pa]["sta_max"], nodes[pb]["sta_max"]
                    if sl is None and nodes[lca]["kind"] == "root":
                        sl = 0.0   # an ideal clock source port carries no arrival of its own
                    if None not in (sl, sa, sb):
                        rec.update(sta_a_ps=round(sa - sl, 1), sta_b_ps=round(sb - sl, 1),
                                   sta_ps=round(max(sa - sl, sb - sl), 1), sta_sum_ps=round(sa + sb - 2 * sl, 1))
                    if None not in (sa, sb):
                        rec["sta_skew_ps"] = round(abs(sa - sb), 1)
                        if R:   # flop-arrival skew: pin arrival + in-arc insertion on each side
                            rec["flop_skew_ps"] = round(abs(sa + R(nodes[pa]["cell"], pa) - sb - R(nodes[pb]["cell"], pb)), 1)
                    rec["region_a"], rec["region_b"] = region_of(nodes, aa), region_of(nodes, anc_of(pb))
                # DIE-CLOCK 2026-10-16: a multi-entry tile (sp_vm has 42 serial / 651 stream clock pins on its faces)
                # talks to a neighbour through the entry beside it, so the pair is judged on the geometrically NEAREST
                # entry pair (ties: worst non-common path); the old worst-over-all-entries pairing reported the root-level
                # branch of a far face (2.5 ns) for an abutting station.
                dist = abs(nodes[pa]["x"] - nodes[pb]["x"]) + abs(nodes[pa]["y"] - nodes[pb]["y"])
                rec["entry_distance_um"] = round(dist, 1)
                score = (-dist, rec.get("sta_ps", rec.get("model_ps", float("inf"))))
                if best is None or score > best[0]:
                    best = (score, rec)
        rec = best[1]
        if rec["lca"] is None:
            cross += 1
        prs.append(dict(a=a, b=b, net=net, source=how, **rec))
    if strict_entry_pairs and missing:
        raise ValueError(f'{len(missing)} timed clock pairs have missing entries: {missing[:3]}')
    prs.sort(key=lambda r: -(r.get("sta_ps") if r.get("sta_ps") is not None else r.get("model_ps", 1e18)))
    # per region: insertion (late / early), flop arrival spread (with targets), intra-region pair NCP / skew;
    # pairs whose ends sit in different regions are listed separately (meso / forwarded crossings or a plan defect)
    regions = {}
    by_reg = {}
    for t in tiles:
        by_reg.setdefault(t["region"], []).append(t)
    for rg, ts in sorted(by_reg.items()):
        intra = [p for p in prs if p.get("region_a") == rg and p.get("region_b") == rg]
        regions[rg] = dict(entries=len(ts), insertion_sta_max_ps=stats([t["sta_max_ps"] for t in ts]),
                           insertion_sta_min_ps=stats([t["sta_min_ps"] for t in ts]),
                           flop_arrival_ps=(stats([t["sta_max_ps"] + t["R_tt_ps"] for t in ts if t["sta_max_ps"] is not None])
                                            if R else None),
                           pairs=len(intra), noncommon_sta_ps=stats([p.get("sta_ps") for p in intra]),
                           skew_sta_ps=stats([p.get("sta_skew_ps") for p in intra]),
                           flop_skew_ps=stats([p.get("flop_skew_ps") for p in intra]) if R else None)
    inter = [p for p in prs if p.get("region_a") and p.get("region_a") != p.get("region_b")]
    inter_summary = dict(pairs=len(inter), by_pair={})
    for p in inter:
        k = "|".join(sorted((p["region_a"], p["region_b"])))
        inter_summary["by_pair"].setdefault(k, []).append(p.get("flop_skew_ps", p.get("sta_skew_ps")))
    inter_summary["by_pair"] = {k: stats(v) for k, v in sorted(inter_summary["by_pair"].items())}
    out = dict(
        schema="opentallas.die_clock_check.v1", dump=os.path.abspath(dump), dump_summary=summ,
        model="tools/hbm_die_v15/die_clock_tree.stage_ps over Manhattan node-to-node wire, %g um/stage (H-DIE 9bcff2c0b)" % SPAN,
        threshold=None,
        insertion=dict(model_ps=stats([t["model_ps"] for t in tiles]), sta_max_ps=stats([t["sta_max_ps"] for t in tiles]),
                       sta_min_ps=stats([t["sta_min_ps"] for t in tiles]), levels=stats([t["levels"] for t in tiles])),
        noncommon=dict(pairs=len(prs), no_common_root=cross, unmatched_pairs=len(missing),
                       model_ps=stats([p.get("model_ps") for p in prs]), sta_ps=stats([p.get("sta_ps") for p in prs]),
                       sta_skew_ps=stats([p.get("sta_skew_ps") for p in prs])),
        counts=dict(tile_entries=len(tiles), tiles=len(entries), clock_cells=sum(1 for d in nodes.values() if d["kind"] == "cell"),
                    die_flops=sum(1 for d in nodes.values() if d["kind"] == "flop"),
                    roots=[n for n, d in nodes.items() if d["kind"] == "root"]),
        regions=regions, inter_region=inter_summary,
        tiles=tiles, pairs=prs, unmatched_pairs=missing[:200])
    return out


def table(r, top=20):
    L = []
    c, ins, nc = r["counts"], r["insertion"], r["noncommon"]
    L.append(f"die clock check: {c['tiles']} tiles / {c['tile_entries']} clock entries, {c['clock_cells']} die clock cells, "
             f"{c['die_flops']} die flops, roots {', '.join(c['roots'])}")
    def s(x):
        return "n/a" if not x else f"min {x['min']} / med {x['median']} / p90 {x['p90']} / max {x['max']} (spread {x['spread']})"
    L.append(f"insertion model ps : {s(ins['model_ps'])}")
    L.append(f"insertion STA ps   : {s(ins['sta_max_ps'])}  [late]; {s(ins['sta_min_ps'])} [early]")
    L.append(f"tree levels        : {s(ins['levels'])}")
    L.append(f"non-common pairs {nc['pairs']} (no common root {nc['no_common_root']}, unmatched {nc['unmatched_pairs']})")
    L.append(f"non-common model ps: {s(nc['model_ps'])}")
    L.append(f"non-common STA ps  : {s(nc['sta_ps'])}")
    L.append(f"pair skew STA ps   : {s(nc['sta_skew_ps'])}")
    if r.get("regions"):
        L.append(f"per region ({len(r['regions'])}): entries | insertion STA late | flop arrival spread | intra pairs NCP / skew")
        for rg, x in sorted(r["regions"].items(), key=lambda kv: -((kv[1]["insertion_sta_max_ps"] or {}).get("spread", 0)))[:top]:
            ins_, fa = x["insertion_sta_max_ps"], x.get("flop_arrival_ps")
            L.append(f"  {rg[:28]:28} {x['entries']:6} | {('n/a' if not ins_ else str(ins_['min'])+'..'+str(ins_['max'])):>18} | "
                     f"{('n/a' if not fa else fa['spread']):>8} | {x['pairs']:6} "
                     f"{('n/a' if not x['noncommon_sta_ps'] else x['noncommon_sta_ps']['max'])} / "
                     f"{('n/a' if not x['skew_sta_ps'] else x['skew_sta_ps']['max'])}")
        L.append(f"inter-region pairs: {r['inter_region']['pairs']}")
    L.append(f"worst {min(top, len(r['pairs']))} pairs (non-common = max side from the branch point):")
    L.append(f"  {'tile A':34} {'tile B':34} {'model':>8} {'STA':>8} {'skew':>8}  branch")
    for p in r["pairs"][:top]:
        f = lambda k: "-" if p.get(k) is None else f"{p[k]:.1f}"
        L.append(f"  {p['a'][:34]:34} {p['b'][:34]:34} {f('model_ps'):>8} {f('sta_ps'):>8} {f('sta_skew_ps'):>8}  {p.get('lca') or 'NO COMMON ROOT'}")
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("report")
    r.add_argument("dump")
    r.add_argument("--out")
    r.add_argument("--pairs")
    r.add_argument("--strict-entry-pairs", action="store_true", help="refuse missing or ambiguous launch/capture clock entries")
    r.add_argument("--top", type=int, default=20)
    r.add_argument("--targets", help="die kit kit.json: per master clock pin in-arc insertion R -> flop arrival / skew")
    sub.add_parser("tcl")
    a = ap.parse_args()
    if a.cmd == "tcl":
        print(os.path.join(HERE, "die_clock_check.tcl"))
        return
    res = report(a.dump, a.pairs, a.top, a.targets, a.strict_entry_pairs)
    txt = table(res, a.top)
    if a.out:
        with open(a.out, "w") as fh:
            json.dump(res, fh, indent=1)
        with open(os.path.splitext(a.out)[0] + ".txt", "w") as fh:
            fh.write(txt + "\n")
    print(txt)


if __name__ == "__main__":
    main()
