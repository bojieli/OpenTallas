#!/usr/bin/env python3
"""KIT-ISTATIONS 11-10 (COORD LOOP-GAP 23:1x (2), q_hub-split-plan (b)): realise a plan type's HBM core<->core
internal_stations in a BOUND native kit (the HBM equivalent of kit_istations.CORE_CLASSES).  OPT-IN: plan
partition_types[T].hbm_core_stations = true, or kit_istations.py --hbm-core.  Off by default; the bound text is
unchanged when it is off.

Bound native module (bind.py, as-built leaves): every leaf output port p of leaf instance X drives the wire
w_<X minus 'u_'>_<p>; a leaf input port reads such wires directly (bit selects / concatenation).  A LINK is one
item of a sink leaf's input-port connection that reads another leaf's output wire.  Links through assigns or native
glue cells, self loops, and leaf->face paths are not links (reported as such, never changed).

LINK CLASS = (plan launch name, plan capture name): the plan contents / hard-core names of the two leaves (q0/q1 leaves
of one plan name share it).  The class depth D is the deepest planned entry of that class, read in the plan's
launch -> capture direction (KW-FIX-27 rule: one interface, one chain, the deepest entry).  Entries planned only in the
reverse direction are used with their sites reversed and flagged.  Every link of a class gets exactly D stages
(one depth per class: the static schedule), as one ot_dp_dly #(.W, .D) per (sink leaf, sink port, source leaf), the
sink port's items replaced by slices of the chain output.  Stage j of a chain is FIRM at regs_um[j] of the deepest
class entry whose ends lie nearest the two leaves (hard-core / contents centres); without leaf positions, at the
bits-weighted centroid of the deepest entries.

Cycle effect: +D cycles on every link of the class; report()['classes'] lists D, links, bits, register bits per
class so the compiler (TOK-VERIFY-1) reschedules.  Exactness: the kit equals the staged golden (the original bound
module with every link of class c delayed by D_c); tools/die_plan/hbm_cstation_proof.py proves it per class by
sat -tempinduct (negative controls D-1 / D+1 must FAIL).  Reset: stations are reset-less (ot_dp_dly): with the clock
running while rst_n is held for >= D cycles, a chain holds the source's reset-state value, i.e. sink(t) = src(t - D)
also across reset release.  report()['max_depth'] states the D the reset hold must cover.
"""
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

ID = r"[A-Za-z_][A-Za-z0-9_$]*"
INST_START = re.compile(rf"^(\s*)({ID})\s+(?:#\(.*\)\s+)?(u_\w+)\s*\(\s*$")
PORT_LINE = re.compile(rf"^(\s*)\.({ID})\((.*)\)(,?)(\s*(?://.*)?)$")
ITEM = re.compile(rf"^({ID})(?:\[(\d+)(?::(\d+))?\])?$")
DECL = re.compile(r"^\s*(?:wire|logic|reg|input\s+wire|output\s+wire|input|output)\s*(?:\[(\d+):(\d+)\])?\s*(" + ID + r")\s*[;,]",
                  re.M)
PREFIX = "u_hcs_"


def enabled(t, flag=False):
    return bool(flag or t.get("hbm_core_stations"))


def split_concat(expr):
    """'{a, b[3:0]}' -> ['a', 'b[3:0]']; a bare item -> [item]; None when it is not a flat concatenation."""
    e = expr.strip()
    if not (e.startswith("{") and e.endswith("}")):
        return [e]
    inner, depth, cur, out = e[1:-1], 0, "", []
    for ch in inner:
        if ch in "{(":
            depth += 1
        elif ch in "})":
            depth -= 1
        if ch == "," and depth == 0:
            out.append(cur.strip())
            cur = ""
        else:
            cur += ch
    out.append(cur.strip())
    if depth or any(not x for x in out):
        return None
    return out


def parse(txt):
    """leaf instances (multi-line bind blocks): [(module, inst, [(line_no, port, expr)])], widths, driven ids"""
    lines = txt.split("\n")
    widths = {m.group(3): (int(m.group(1)) - int(m.group(2)) + 1) if m.group(1) else 1 for m in DECL.finditer(txt)}
    driven = set(re.findall(rf"^\s*assign\s+({ID})\b", txt, re.M))
    for ln in re.findall(r"^\s*(?:ot_dp_\w+|ot_bind_native\w*)\b.*$", txt, re.M):   # one-line stage / glue cells
        for m in re.finditer(r"\.(?:q|eq|Y)\(([^()]*)\)", ln):
            driven.update(re.findall(ID, m.group(1)))
    leaves = []
    i = 0
    while i < len(lines):
        m = INST_START.match(lines[i])
        if not m or m.group(2).startswith("ot_dp_"):
            i += 1
            continue
        ports, j = [], i + 1
        while j < len(lines) and not re.match(r"^\s*\);", lines[j]):
            pm = PORT_LINE.match(lines[j])
            if pm:
                ports.append((j, pm.group(2), pm.group(3)))
            j += 1
        leaves.append((m.group(2), m.group(3), ports))
        i = j + 1
    return lines, leaves, widths, driven


def leaf_outputs(leaves, driven):
    """wire -> (leaf inst, port): a port bound to its own w_<inst>_<port> wire that nothing else drives"""
    out = {}
    for _, inst, ports in leaves:
        for _, p, e in ports:
            w = f"w_{inst[2:]}_{p}"
            if e.strip() == w and w not in driven:
                out[w] = (inst, p)
    return out


def item_width(it, widths):
    m = ITEM.match(it)
    if not m:
        return None
    if m.group(2) is None:
        return widths.get(m.group(1))
    hi, lo = int(m.group(2)), int(m.group(3) if m.group(3) is not None else m.group(2))
    return abs(hi - lo) + 1


def links(leaves, outputs, widths):
    """[(sink line, sink inst, sink port, item index, item, width, src inst, src port)] + reasons for skipped items"""
    res, skipped = [], defaultdict(int)
    for _, inst, ports in leaves:
        for ln, p, e in ports:
            if outputs.get(e.strip()) == (inst, p):
                continue
            items = split_concat(e)
            if items is None:
                if re.search(r"\bw_", e):
                    skipped["nested_concat_port"] += 1
                continue
            for k, it in enumerate(items):
                m = ITEM.match(it)
                if not m or m.group(1) not in outputs:
                    if re.search(r"\bw_", it) and not m:
                        skipped["complex_item"] += 1
                    continue
                si, sp = outputs[m.group(1)]
                if si == inst:
                    skipped["self_loop"] += 1
                    continue
                w = item_width(it, widths)
                if not w:
                    skipped["unknown_width"] += 1
                    continue
                res.append((ln, inst, p, k, it, w, si, sp))
    return res, dict(skipped)


def plan_maps(t, leaf_names, names=()):
    """cand(plan name) -> set(leaf insts) (longest-prefix owner); leaf -> (x, y) centre (hard cores, then contents).
    A leaf belongs to the plan name n with u_<n> (or u_<n with __ -> _>) equal to it or a '_' prefix of it, longest
    match first (u_vmb_Q0 owns u_u_vmb_Q0 and u_u_vmb_Q0_mu1; u_hcollgi_Q owns _q0 / _q1), or to a hard core whose
    physical_inst's first scope is that leaf."""
    hc = {h["inst"]: h for h in t.get("hard_cores", [])}
    pools = [set(names), {c["inst"] for c in t.get("contents", [])} | set(hc)]
    owner = {}
    for lf in leaf_names:
        best, bl = set(), -1
        for n in (pools[0] if any(lf == "u_" + v or lf.startswith("u_" + v + "_") for n in pools[0]
                                  for v in {n, n.replace("__", "_")}) else pools[1]):
            for v in {n, n.replace("__", "_")}:
                u = "u_" + v
                if (lf == u or lf.startswith(u + "_")) and len(u) >= bl:
                    if len(u) > bl:
                        best, bl = set(), len(u)
                    best.add(n)
        owner[lf] = best
    phys = defaultdict(set)
    for n, h in hc.items():
        if h.get("physical_inst"):
            seg = h["physical_inst"].split(".")[0]
            for v in ("u_" + seg, "u_" + seg.replace("__", "_")):
                if v in owner:
                    phys[n].add(v)
    inv = defaultdict(set)
    for lf, ns in owner.items():
        for n in ns:
            inv[n].add(lf)

    def cand(n):
        return inv.get(n, set()) | phys.get(n, set())

    def home(n):
        """the leaf a plan object sits in: its physical_inst scope, else the longest leaf name that prefixes u_<n>"""
        if n in phys and len(phys[n]) == 1:
            return next(iter(phys[n]))
        best = None
        for v in {n, n.replace("__", "_")}:
            u = "u_" + v
            for lf in owner:
                if (u == lf or u.startswith(lf + "_")) and (best is None or len(lf) > len(best)):
                    best = lf
        return best

    pos = defaultdict(list)
    for h in t.get("hard_cores", []):
        lf = home(h["inst"])
        if lf and "origin_um" in h:
            (o, w) = h["origin_um"], h.get("outline_um", [0, 0])
            pos[lf].append((o[0] + w[0] / 2, o[1] + w[1] / 2))
    for c in t.get("contents", []):
        cs = cand(c["inst"])
        if len(cs) == 1 and "origin_um" in c and next(iter(cs)) not in pos:
            (o, w) = c["origin_um"], c.get("outline_um", [0, 0])
            pos[next(iter(cs))].append((o[0] + w[0] / 2, o[1] + w[1] / 2))
    centre = {k: (sum(x for x, _ in v) / len(v), sum(y for _, y in v) / len(v)) for k, v in pos.items()}
    return cand, centre


def core_entries(t):
    return [e for e in t.get("internal_stations", []) if not e.get("conn", "").startswith("bus:")]


def _end(e, k):
    return str(e.get(k) or "").split(".")[0]


def plan_classes(t, cand, link_pairs):
    """(src leaf, dst leaf) -> dict(cls, depth, entries=[(regs, from, to, bits)], reversed) for pairs the plan stations"""
    by = defaultdict(list)
    for e in core_entries(t):
        a, b = _end(e, "launch"), _end(e, "capture")
        if not a or not b or a == "face root" or b == "face root":
            continue
        by[(a, b)].append(e)
    leaf_names = defaultdict(set)
    for a, b in by:
        for n in (a, b):
            for lf in cand(n):
                leaf_names[lf].add(n)
    out = {}
    for s, d in link_pairs:
        found = []
        for a in leaf_names.get(s, ()):
            for b in leaf_names.get(d, ()):
                for e in by.get((a, b), ()):
                    found.append((False, (a, b), e))
                for e in by.get((b, a), ()):
                    found.append((True, (b, a), e))
        if not found:
            continue
        fwd = [x for x in found if not x[0]]
        use = fwd or found                     # the plan direction first; reverse only when nothing else is planned
        depth = max(len(e["regs_um"]) for _, _, e in use)
        clss = sorted({c for _, c, _ in use})
        ents = []
        for rev, _, e in use:
            regs = [list(r) for r in e["regs_um"]]
            fr, to = e.get("from_um"), e.get("to_um")
            if rev:
                regs, fr, to = regs[::-1], to, fr
            ents.append((regs, fr, to, int(e.get("bits", 1))))
        out[(s, d)] = dict(cls="|".join(clss[0]), depth=depth, entries=ents, reversed=not fwd,
                           all_classes=["|".join(c) for c in clss])
    return out


def _dist(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def _spread(path, n):
    """n points at arclength (j + 1) / (n + 1) along a Manhattan polyline (its straight legs as given)"""
    legs = [_dist(a, b) for a, b in zip(path, path[1:])]
    L = sum(legs)
    out = []
    for j in range(n):
        s, k = L * (j + 1) / (n + 1), 0
        while k < len(legs) - 1 and s > legs[k]:
            s -= legs[k]
            k += 1
        a, b = path[k], path[k + 1]
        f = s / legs[k] if legs[k] else 0.0
        out.append((round(a[0] + f * (b[0] - a[0]), 3), round(a[1] + f * (b[1] - a[1]), 3)))
    return out


def sites_for(pc, sp, dp):
    """-> (stage sites, how, own planned depth, worst hop um, end offset um) of one chain of class depth D.
    The class entry whose ends lie nearest the two leaves is this chain's route (q0 / q1 instances of one plan name
    carry their own entries).  Its depth equals D: its regs_um.  Shallower: the D stages spread evenly along that
    route (from_um -> regs_um -> to_um), so no hop is longer than the route's planned hops.  Without leaf positions:
    the bits-weighted centroid of the deepest entries."""
    D = pc["depth"]
    ents = pc["entries"]
    if sp is not None and dp is not None and all(x[1] and x[2] for x in ents):
        best = min(ents, key=lambda x: (_dist(x[1], sp) + _dist(x[2], dp), -len(x[0]), x[0]))
        path = [tuple(best[1])] + [tuple(r) for r in best[0]] + [tuple(best[2])]
        st = [tuple(r) for r in best[0]] if len(best[0]) == D else _spread(path, D)
        full = [path[0]] + st + [path[-1]]
        hop = max(_dist(a, b) for a, b in zip(full, full[1:]))
        off = _dist(best[1], sp) + _dist(best[2], dp)
        return st, "nearest_entry" if len(best[0]) == D else "nearest_entry_respread", len(best[0]), hop, off
    deep = [x for x in ents if len(x[0]) == D]
    w = sum(x[3] for x in deep)
    st = [(round(sum(x[0][j][0] * x[3] for x in deep) / w, 3), round(sum(x[0][j][1] * x[3] for x in deep) / w, 3))
          for j in range(D)]
    return st, "centroid", D, None, None


REACH_UM = 405.0      # METHODOLOGY 12.1e planning reach per registered hop


def _over_reach(unplanned, centre, reach):
    """unplanned leaf pairs (no plan station) whose leaf centres are farther apart than one registered hop"""
    rows = []
    for (s, d), v in sorted(unplanned.items()):
        n, b = v[0], v[1]
        if s in centre and d in centre and _dist(centre[s], centre[d]) > reach:
            rows.append(dict(pair=f"{s}->{d}", links=n, bits=b, centre_dist_um=round(_dist(centre[s], centre[d]), 1),
                             plan="zero_stations" if "zero" in v[2:] else "no_entry"))
    return dict(pairs=len(rows), bits=sum(r["bits"] for r in rows),
                zero_station_pairs=sum(r["plan"] == "zero_stations" for r in rows),
                zero_station_bits=sum(r["bits"] for r in rows if r["plan"] == "zero_stations"),
                unknown_position_pairs=sum(
        1 for s, d in unplanned if s not in centre or d not in centre), rows=rows)


def realise(t, txt, tn="?"):
    """-> (new text, istations.tcl lines, report).  Fail closed on a re-application (u_hcs_ already present)."""
    if re.search(rf"\b{PREFIX}\d+\b|\bhcs_\d+\b", txt):
        raise SystemExit(f"kit_hbm_cstations: {tn}: HBM core stations already inserted (run on a fresh kit-rtl copy)")
    lines, leaves, widths, driven = parse(txt)
    outputs = leaf_outputs(leaves, driven)
    lk, skipped = links(leaves, outputs, widths)
    cand, centre = plan_maps(t, [i for _, i, _ in leaves], {n for e in core_entries(t) for n in (_end(e, "launch"), _end(e, "capture"))})
    pcs = plan_classes(t, cand, {(x[6], x[1]) for x in lk})
    # group: one chain per (sink line = sink inst + port, source leaf)
    groups = defaultdict(list)
    unplanned = defaultdict(lambda: [0, 0])          # (links, bits[, "zero" = planned with 0 stations | "absent"])
    for x in lk:
        ln, inst, p, k, it, w, si, sp = x
        pc = pcs.get((si, inst))
        if pc is None or pc["depth"] == 0:
            u = unplanned[(si, inst)]
            u.append("zero" if pc is not None else "absent")
            u[0] += 1
            u[1] += w
            continue
        groups[(ln, si)].append(x)
    decl, body, tcl = [], [], []
    edits = defaultdict(dict)            # line -> {item index: replacement}
    classes = {}
    chains = []
    for n, ((ln, si), xs) in enumerate(sorted(groups.items())):
        inst, p = xs[0][1], xs[0][2]
        pc = pcs[(si, inst)]
        D = pc["depth"]
        W = sum(x[5] for x in xs)
        name = f"{PREFIX}{n}"
        wire = name[2:]
        d = ", ".join(x[4] for x in xs)
        decl.append(f"    wire [{W - 1}:0] {wire};  // kit_hbm_cstations")
        body.append(f"    ot_dp_dly #(.W({W}), .D({D})) {name} (.clk(clk), .d({{{d}}}), .q({wire}));  "
                    f"// kit_hbm_cstations: {pc['cls']} {si}.{xs[0][7]} -> {inst}.{p}, {D} FIRM plan station(s)")
        hi = W - 1
        for x in xs:
            lo = hi - x[5] + 1
            edits[ln][x[3]] = f"{wire}[{hi}:{lo}]" if x[5] > 1 or W > 1 else wire
            hi = lo - 1
        st, how, own, hop, off = sites_for(pc, centre.get(si), centre.get(inst))
        hop = None if hop is None else round(hop, 1)
        for j, (sx, sy) in enumerate(st):
            tcl.append(f"is_place {{*{name}[./]r\\[{j}\\]*}} {sx} {sy} hcs:{pc['cls']}")
        c = classes.setdefault(pc["cls"], dict(depth=D, links=0, chains=0, bits=0, register_bits=0, reversed=pc["reversed"],
                                               leaf_pairs=set(), sited=defaultdict(int), worst_hop_um=0.0))
        c["worst_hop_um"] = max(c["worst_hop_um"], hop or 0.0)
        c["own_depth_min"] = min(c.get("own_depth_min", D), own)
        c["register_bits_at_own_depth"] = c.get("register_bits_at_own_depth", 0) + W * own
        if c["depth"] != D:
            raise SystemExit(f"kit_hbm_cstations: {tn}: class {pc['cls']} carries depths {c['depth']} / {D} (fail closed)")
        c["links"] += len(xs)
        c["chains"] += 1
        c["bits"] += W
        c["register_bits"] += W * D
        c["leaf_pairs"].add(f"{si}->{inst}")
        c["sited"][how] += 1
        chains.append(dict(inst=name, cls=pc["cls"], src=si, src_ports=sorted({x[7] for x in xs}), sink=inst, port=p,
                           W=W, D=D, items=[x[4] for x in xs], sites=[list(s) for s in st], worst_hop_um=hop,
                           own_depth=own, end_offset_um=None if off is None else round(off, 1)))
    for ln, rep in edits.items():
        pm = PORT_LINE.match(lines[ln])
        items = split_concat(pm.group(3))
        new = [rep.get(k, it) for k, it in enumerate(items)]
        expr = new[0] if len(new) == 1 and not pm.group(3).strip().startswith("{") else "{" + ", ".join(new) + "}"
        lines[ln] = f"{pm.group(1)}.{pm.group(2)}({expr}){pm.group(4)}{pm.group(5)}"
    out = "\n".join(lines)
    if body:
        k = out.rfind("endmodule")
        if k < 0:
            raise SystemExit(f"kit_hbm_cstations: {tn}: bound text has no endmodule")
        out = out[:k] + "\n".join(["    // kit_hbm_cstations: HBM core<->core plan stations (opt-in hbm_core_stations)"]
                                  + decl + body) + "\n" + out[k:]
    planned_cls = defaultdict(int)
    for e in core_entries(t):
        planned_cls[f"{_end(e, 'launch')}|{_end(e, 'capture')}"] = max(planned_cls[f"{_end(e, 'launch')}|{_end(e, 'capture')}"],
                                                                       len(e["regs_um"]))
    realised = set()
    for pc in pcs.values():
        realised.update(pc["all_classes"])
    rep = dict(
        classes={k: dict(v, leaf_pairs=sorted(v["leaf_pairs"]), sited=dict(v["sited"])) for k, v in sorted(classes.items())},
        chains=len(chains), links=sum(c["links"] for c in classes.values()),
        bits=sum(c["bits"] for c in classes.values()), register_bits=sum(c["register_bits"] for c in classes.values()),
        max_depth=max([c["depth"] for c in classes.values()] or [0]),
        rtl_links_total=len(lk), rtl_link_bits_total=sum(x[5] for x in lk),
        unplanned_links=dict(pairs=len(unplanned), links=sum(v[0] for v in unplanned.values()),
                             bits=sum(v[1] for v in unplanned.values()),
                             over_reach=_over_reach(unplanned, centre, REACH_UM)),
        plan_classes_unrealised=sorted(k for k, d in planned_cls.items() if d and k not in realised),
        skipped_items=skipped)
    return out, tcl, rep, chains


def main(argv):
    """standalone census / realisation: kit_hbm_cstations.py PLAN.json TYPE BOUND.sv OUT_DIR"""
    plan, tn, bound, od = argv
    t = json.load(open(plan))["partition_types"][tn]
    out, tcl, rep, chains = realise(t, Path(bound).read_text(), tn)
    od = Path(od)
    od.mkdir(parents=True, exist_ok=True)
    (od / Path(bound).name).write_text(out)
    (od / "hcs_istations.tcl").write_text("\n".join(tcl) + "\n")
    (od / "hcs_report.json").write_text(json.dumps(dict(report=rep, chains=chains), indent=1))
    print(json.dumps({k: v for k, v in rep.items() if k != "classes"}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
