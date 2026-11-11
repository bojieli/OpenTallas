#!/usr/bin/env python3
"""PLAN-ROUTE-1 11-11: core_conns entries from a type's synthesized gate netlist (ORFS 1_2_yosys.v), for the cores
whose bind trace (core_conns_from_bind) found no pure-wiring partner, so route_supply scores them instead of
reporting UNCHECKED.  ADVISORY.

For every hard-core port (bus) the tool walks the netlist from the port's nets through parent cells (any std cell
or kept submodule instance, both directions), up to --depth cells, never through a net with more than --fanout
cell pins (clock / reset / enables).  The ports, faces and cores reached at the smallest depth are the port's
destinations:
  bus:<face bus>          a type port that is a plan face bus
  face:<F>                an ft slot port (<slot>_i -> in_face, <slot>_o -> out_face)
  core:<inst>.<port>      a pin of another hard core of the type
  glue                    nothing within --depth: the port only talks to local parent logic (route_supply scores
                          it as a local escape, the old glue model, but now measured, not assumed)
Ports reached only through more than --max-dest destinations keep the --max-dest most frequent.

usage: core_conns_netlist.py PLAN.json TYPE NETLIST.v OUT.json [--cores inst,...] [--depth 3] [--fanout 32]
OUT = {"core_conns": {TYPE: {inst: {port: [...]}}}, "receipt": {...}}"""
import argparse
import gzip
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict

TOK = re.compile(r"\\\S+|[A-Za-z_][A-Za-z0-9_$]*")


def _open(p):
    return gzip.open(p, "rt") if str(p).endswith(".gz") else open(p)


def bits(expr):
    """net bit tokens of a port expression (concatenation / select / name), MSB first; constants dropped."""
    out = []
    e = expr.strip()
    if e.startswith("{") and e.endswith("}"):
        e = e[1:-1]
    for part in split_top(e):
        part = part.strip()
        if not part or re.match(r"^\d+'[bhdo]", part) or re.match(r"^\d+$", part):
            continue
        m = re.match(r"^(\\\S+|[A-Za-z_][A-Za-z0-9_$.]*)\s*(\[\s*(\d+)\s*(?::\s*(\d+))?\s*\])?$", part)
        if not m:
            continue
        name = m.group(1)
        if m.group(2) is None:
            out.append(name)
        elif m.group(4) is None:
            out.append(f"{name}[{m.group(3)}]")
        else:
            a, b = int(m.group(3)), int(m.group(4))
            rng = range(a, b - 1, -1) if a >= b else range(a, b + 1)
            out.extend(f"{name}[{i}]" for i in rng)
    return out


def split_top(e):
    parts, depth, cur = [], 0, []
    for ch in e:
        if ch in "{(":
            depth += 1
        elif ch in "})":
            depth -= 1
        if ch == "," and depth == 0:
            parts.append("".join(cur))
            cur = []
        else:
            cur.append(ch)
    parts.append("".join(cur))
    return parts


def parse(path, top=None):
    """-> (top module name, port widths {name: (msb, lsb) | None}, instances [(cell, inst, {pin: [bits]})],
    assigns [(lhs bits, rhs bits)]) of the top module (the last module in the file unless `top`)."""
    txt = _open(path).read()
    mods = [(m.start(), m.group(1)) for m in re.finditer(r"(?m)^module\s+(\\\S+|[A-Za-z_][A-Za-z0-9_$]*)", txt)]
    if not mods:
        raise ValueError("no module in netlist")
    names = [n.lstrip("\\") for _, n in mods]
    idx = None
    if top and top in names:
        idx = names.index(top)
    if idx is None:
        # the top = the largest module that no other module instantiates
        used = set(re.findall(r"(?m)^\s+(\\\S+|[A-Za-z_][A-Za-z0-9_$]*)\s+(?:#\(.*?\)\s*)?\\?[A-Za-z_][\w$.\[\]]*\s*\(", txt))
        used = {u.lstrip("\\") for u in used}
        ends = [st for st, _ in mods[1:]] + [len(txt)]
        cand = [(ends[i] - mods[i][0], i) for i in range(len(mods)) if names[i] not in used]
        idx = max(cand)[1] if cand else max((ends[i] - mods[i][0], i) for i in range(len(mods)))[1]
    start = mods[idx][0]
    end = txt.find("\nendmodule", start)
    body = txt[start:end]
    ports = {}
    for m in re.finditer(r"(?m)^\s*(input|output|inout)\s+(?:wire\s+)?(\[\s*(\d+)\s*:\s*(\d+)\s*\]\s*)?(\\\S+|[A-Za-z_][A-Za-z0-9_$]*)\s*;", body):
        ports[m.group(5)] = (int(m.group(3)), int(m.group(4))) if m.group(2) else None
    insts = []
    for m in re.finditer(r"(?ms)^\s*(\\\S+|[A-Za-z_][A-Za-z0-9_$]*)\s+(?:#\(.*?\)\s*)?(\\\S+|[A-Za-z_][A-Za-z0-9_$]*)\s*\((.*?)\);", body):
        cell, inst, pb = m.group(1), m.group(2), m.group(3)
        if cell in ("module", "input", "output", "inout", "wire", "assign", "reg"):
            continue
        pins = {}
        for pm in re.finditer(r"\.(\\\S+|[A-Za-z_][A-Za-z0-9_$]*)\s*\(", pb):
            i, depth = pm.end(), 1
            while i < len(pb) and depth:
                depth += {"(": 1, ")": -1}.get(pb[i], 0)
                i += 1
            pins[pm.group(1)] = bits(pb[pm.end():i - 1])
        insts.append((cell, inst.lstrip("\\"), pins))
    assigns = []
    for m in re.finditer(r"(?ms)^\s*assign\s+(.*?)\s*=\s*(.*?);", body):
        assigns.append((bits(m.group(1)), bits(m.group(2))))
    return mods[idx][1].lstrip("\\"), ports, insts, assigns


def port_bits(ports):
    out = {}
    for n, w in ports.items():
        if w is None:
            out[n] = n
        else:
            a, b = w
            for i in range(min(a, b), max(a, b) + 1):
                out[f"{n}[{i}]"] = n
    return out


def _toks(name):
    return [x for x in re.split(r"[^A-Za-z0-9]+", name.lstrip("\\").lower()) if x and x not in ("u", "bound")]


def match_cores(hcs, insts):
    """netlist instance -> plan hard-core inst. Names differ by wrapper scopes and flattening (u_bound.<inst>,
    plan u_bk_sel.u_sel.x -> u_bound.u_core.u_sel.x, pv__u_g0_j -> u_bound.u_pv_u_g0_j): match on name tokens
    (u / bound dropped) as a suffix, the plan name in full or without its first scope, same module preferred."""
    out, taken = {}, set()
    by_mod = defaultdict(list)
    for k, (cell, inst, _) in enumerate(insts):
        if not cell.endswith("_ASAP7_75t_R"):
            by_mod[cell.lstrip("\\")].append(k)
    for hi, h in hcs.items():
        mod = str(h.get("module", ""))
        pool = [k for c, ks in by_mod.items() if c == mod or c.endswith("\\" + mod) for k in ks] or \
            [k for ks in by_mod.values() for k in ks]
        pt = _toks(hi)
        alts = [pt]
        if "." in hi:
            alts.append(_toks(hi.split(".", 1)[1]))
        best = None
        for k in pool:
            if k in taken:
                continue
            it = _toks(insts[k][1])
            for rank, a_ in enumerate(alts):
                if a_ and it[-len(a_):] == a_:
                    sc = (rank, len(it) - len(a_))
                    if best is None or sc < best[0]:
                        best = (sc, k)
                    break
        if best:
            taken.add(best[1])
            out[insts[best[1]][1]] = hi
    return out


def derive(plan, tn, netlist, cores=None, depth=3, fanout=32, max_dest=3, top=None):
    t = plan["partition_types"][tn]
    hcs = {h["inst"]: h for h in t.get("hard_cores", []) or []}
    want = set(cores) if cores else set(hcs)
    face_bus = {b["name"] for b in t.get("buses", []) or [] if b.get("face")}
    slot_face = {}
    for f in t.get("ft_slots", []) or []:
        slot_face[f"{f['name']}_i"] = f.get("in_face")
        slot_face[f"{f['name']}_o"] = f.get("out_face")
    topname, ports, insts, assigns = parse(netlist, top)
    pb = port_bits(ports)
    # hard-core instance in the netlist: its plan inst, possibly under a wrapper scope (u_bound.<inst>)
    core_of = match_cores(hcs, insts)
    # net -> [(node, pin)] ; nodes = instances (index) ; assigns join nets (union-find)
    par = {}

    def find(a):
        while par.get(a, a) != a:
            par[a] = par.get(par[a], par[a])
            a = par[a]
        return a
    for lhs, rhs in assigns:
        for a, b in zip(lhs[::-1], rhs[::-1]):
            ra, rb = find(a), find(b)
            if ra != rb:
                par[ra] = rb
    net_nodes = defaultdict(list)
    node_nets = []
    for k, (cell, inst, pins) in enumerate(insts):
        nets = []
        for p, bl in pins.items():
            for i, bt in enumerate(bl):
                n = find(bt)
                net_nodes[n].append((k, p))
                nets.append(n)
        node_nets.append(nets)
    port_of_net = {}
    for b, n in pb.items():
        port_of_net[find(b)] = n
    res = defaultdict(dict)
    stats = Counter()
    for k, (cell, inst, pins) in enumerate(insts):
        hi = core_of.get(inst)
        if hi is None or hi not in want:
            continue
        for p, bl in pins.items():
            src = {find(b) for b in bl}
            if not src or p in ("clk", "rst", "rst_n", "arst_n") or any(n in port_of_net and
                                                                       port_of_net[n].startswith("clk") for n in src):
                continue
            dest = Counter()
            seen_nodes = {k}
            seen_nets = set(src)
            frontier = list(src)
            for d in range(depth + 1):
                hits = Counter()
                nxt_nodes = []
                for n in frontier:
                    if n in port_of_net:
                        pn = port_of_net[n]
                        if pn in face_bus:
                            hits[f"bus:{pn}"] += 1
                        elif pn in slot_face and slot_face[pn]:
                            hits[f"face:{slot_face[pn]}"] += 1
                    users = net_nodes.get(n, ())
                    if len(users) > fanout:
                        continue
                    for (j, pj) in users:
                        if j in seen_nodes:
                            continue
                        hj = core_of.get(insts[j][1])
                        if hj is not None:
                            if hj != hi:
                                hits[f"core:{hj}.{pj}"] += 1
                            seen_nodes.add(j)
                            continue
                        seen_nodes.add(j)
                        nxt_nodes.append(j)
                if hits:
                    dest = hits
                    stats[f"depth{d}"] += 1
                    break
                frontier = []
                for j in nxt_nodes:
                    for n in node_nets[j]:
                        if n not in seen_nets:
                            seen_nets.add(n)
                            frontier.append(n)
                if not frontier:
                    break
            if dest:
                res[hi][p] = [x for x, _ in dest.most_common(max_dest)]
            else:
                res[hi][p] = ["glue"]
                stats["glue"] += 1
    h = hashlib.sha256(_open(netlist).read().encode()).hexdigest()[:12]
    return dict(core_conns={tn: {c: dict(sorted(v.items())) for c, v in res.items()}},
                receipt=dict(tool="core_conns_netlist.py", type=tn, netlist=str(netlist), netlist_sha256_12=h,
                             top=topname, cores_found=sorted(set(core_of.values())), cores_wanted=sorted(want),
                             depth=depth, fanout=fanout, max_dest=max_dest, ports=dict(stats),
                             advisory=True, do_not_count=True))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("plan")
    ap.add_argument("type")
    ap.add_argument("netlist")
    ap.add_argument("out")
    ap.add_argument("--cores", help="comma list of plan core insts (default all)")
    ap.add_argument("--depth", type=int, default=3)
    ap.add_argument("--fanout", type=int, default=32)
    ap.add_argument("--max-dest", type=int, default=3)
    ap.add_argument("--top")
    a = ap.parse_args(argv)
    op = gzip.open if a.plan.endswith(".gz") else open
    plan = json.load(op(a.plan, "rt"))
    top = a.top or plan["partition_types"][a.type].get("module")
    r = derive(plan, a.type, a.netlist, a.cores.split(",") if a.cores else None, a.depth, a.fanout, a.max_dest, top)
    json.dump(r, open(a.out, "w"), indent=1)
    cc = r["core_conns"][a.type]
    print(f"{a.type}: cores {len(cc)}/{len(r['receipt']['cores_wanted'])} found, ports {r['receipt']['ports']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
