#!/usr/bin/env python3
"""PLAN-ROUTE-1 11-11: core_conns entries from a type's synthesized gate netlist (ORFS 1_2_yosys.v), for the cores
whose bind trace (core_conns_from_bind) found no pure-wiring partner, so route_supply scores them instead of
reporting UNCHECKED.  ADVISORY.

For every hard-core port (bus) the tool walks the netlist from the port's nets through parent cells (any std cell
or kept submodule instance, along actual input/output directions), up to --depth cells, never through a net with more than --fanout
cell pins (clock / reset / enables).  The ports, faces and cores reached at the smallest depth are the port's
destinations:
  bus:<face bus>          a type port that is a plan face bus
  face:<F>                an ft slot port (<slot>_i -> in_face, <slot>_o -> out_face)
  core:<inst>.<port>      a pin of another hard core of the type
  glue                    a fully explored known local cone has no external endpoint
Unknown directions and truncated cones stay unresolved; an incomplete core is omitted (CLI exits nonzero).
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
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import core_conns_from_bind as wiring

TOK = re.compile(r"\\\S+|[A-Za-z_][A-Za-z0-9_$]*")


def _open(p):
    return gzip.open(p, "rt") if str(p).endswith(".gz") else open(p)


def bits(expr, widths=None):
    """MSB-first wire bits, preserving constant positions as None."""
    return wiring.expression_bits(expr, widths or {})[0]


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


def _parse_details(path, top=None):
    txt = wiring.strip_comments(_open(path).read())
    body = wiring.select_module(txt, top)
    mm = re.search(r"\bmodule\s+(\\\S+|[A-Za-z_][A-Za-z0-9_$]*)", body)
    if not mm:
        raise ValueError("no selected module in netlist")
    topname = mm.group(1).lstrip("\\")
    widths = wiring.declarations(body)
    local_dirs = wiring.module_directions(txt)
    topdirs = local_dirs.get(topname, {})
    ports = {n: ((widths[n][0], widths[n][1]) if widths[n][0] is not None else None)
             for n in topdirs if n in widths}
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
            pins[pm.group(1).lstrip("\\")] = bits(pb[pm.end():i - 1], widths)
        insts.append((cell.lstrip("\\"), inst.lstrip("\\"), pins))
    assigns = []
    for m in re.finditer(r"(?ms)^\s*assign\s+(.*?)\s*=\s*(.*?);", body):
        lhs = bits(m.group(1), widths)
        rhs, signed = wiring.expression_bits(m.group(2), widths)
        pairs = wiring.align_bits(lhs, rhs, signed)
        assigns.append(([a for a, _ in pairs], [b for _, b in pairs]))
    return topname, ports, insts, assigns, widths, topdirs, local_dirs


def parse(path, top=None):
    """Top-module port widths, instance bit connections, and width-aligned wiring assignments."""
    return _parse_details(path, top)[:4]


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
    return [x for x in re.split(r"[^A-Za-z0-9]+", name.lstrip("\\")) if x and x not in ("u", "bound")]


def match_cores(hcs, insts):
    """Require an unambiguous scoped suffix and actual module identity.

    A common dropped wrapper is supported, but equal suffixes never select an
    arbitrary core or overwrite another scope's physical identity.
    """
    candidates = {}
    for cell, inst, _ in insts:
        matches = []
        it = _toks(inst)
        for hi, h in hcs.items():
            if cell.lstrip("\\") != str(h.get("module", "")).lstrip("\\"):
                continue
            alts = [_toks(hi)]
            if "." in hi:
                alts.append(_toks(hi.split(".", 1)[1]))
            for rank, alt in enumerate(alts):
                if alt and it[-len(alt):] == alt:
                    matches.append(((rank, len(it) - len(alt)), hi))
                    break
        if matches:
            best = min(score for score, _ in matches)
            winners = {hi for score, hi in matches if score == best}
            if len(winners) == 1:
                candidates[inst] = next(iter(winners))
    counts = Counter(candidates.values())
    return {inst: hi for inst, hi in candidates.items() if counts[hi] == 1}


def _groups(text, keyword):
    """Balanced Liberty groups, excluding pg_pin when looking for pin."""
    for m in re.finditer(r"(?<![\w])" + keyword + r"\s*\(\s*([^)]*?)\s*\)\s*\{", text):
        depth, i = 1, m.end()
        while i < len(text) and depth:
            depth += {"{": 1, "}": -1}.get(text[i], 0)
            i += 1
        if depth:
            raise ValueError("unbalanced Liberty " + keyword)
        yield m.group(1).strip('" '), text[m.end():i-1]


def liberty_directions(paths):
    out = {}
    for path in paths:
        text = wiring.strip_comments(_open(path).read())
        for name, cell in _groups(text, "cell"):
            dirs = {}
            for pin, body in _groups(cell, "pin"):
                d = re.search(r"\bdirection\s*:\s*(input|output|inout)\s*;", body)
                if d:
                    dirs[pin] = d.group(1).upper()
            if name in out and out[name] != dirs:
                raise ValueError("conflicting Liberty directions for " + name)
            out[name] = dirs
    return out


def derive(plan, tn, netlist, cores=None, depth=3, fanout=32, max_dest=3, top=None, liberty=None):
    t = plan["partition_types"][tn]
    hcs = {h["inst"]: h for h in t.get("hard_cores", []) or []}
    want = set(cores) if cores else set(hcs)
    face_bus = {b["name"] for b in t.get("buses", []) or [] if b.get("face")}
    slot_face = {}
    for f in t.get("ft_slots", []) or []:
        slot_face[f"{f['name']}_i"] = f.get("in_face")
        slot_face[f"{f['name']}_o"] = f.get("out_face")
    topname, ports, insts, assigns, widths, topdirs, localdirs = _parse_details(netlist, top)
    core_of = match_cores(hcs, insts)
    repo = Path(__file__).resolve().parents[2]
    defaults = repo / "physical/asap7_stdcell_native_models/asap7sc7p5t_SIMPLE_RVT_TT_nldm_211120.lib"
    libs = list(liberty or [])
    if defaults.is_file() and str(defaults) not in map(str, libs):
        libs.insert(0, defaults)
    libdirs = liberty_directions(libs)
    hardmods = {str(h.get("module", "")).lstrip("\\") for h in hcs.values()}
    dirs = []
    for cell, inst, _ in insts:
        hi = core_of.get(inst)
        dirs.append(wiring.hc_port_directions(hcs[hi], repo) if hi else
                    {} if cell in hardmods else localdirs.get(cell, libdirs.get(cell, {})))
    # Assigns alias exactly corresponding bit positions, including constant holes.
    par = {}
    def find(a):
        while par.get(a, a) != a:
            par[a] = par.get(par[a], par[a])
            a = par[a]
        return a
    for lhs, rhs in assigns:
        for a, b in zip(lhs, rhs):
            if a is None or b is None:
                continue
            ra, rb = find(a), find(b)
            if ra != rb:
                par[ra] = rb
    net_nodes = defaultdict(list)
    for k, (_, _, pins) in enumerate(insts):
        for pin, bl in pins.items():
            for bt in bl:
                if bt is not None:
                    net_nodes[find(bt)].append((k, pin))
    ports_of_net = defaultdict(list)
    for pn, direction in topdirs.items():
        for bt in bits(pn, widths):
            if bt is not None:
                ports_of_net[find(bt)].append((pn, direction.upper()))
    res, stats, unresolved = defaultdict(dict), Counter(), []
    for hi in sorted(want - set(core_of.values())):
        unresolved.append(dict(core=hi, reason="core_identity_unmatched_or_ambiguous"))
    for k, (_, inst, pins) in enumerate(insts):
        hi = core_of.get(inst)
        if hi is None or hi not in want:
            continue
        for p, bl in pins.items():
            if p in ("clk", "ck", "rst", "rst_n", "arst_n") or not bl:
                continue
            pd = dirs[k].get(p)
            if pd not in ("INPUT", "OUTPUT"):
                unresolved.append(dict(core=hi, port=p, reason="unknown_core_port_direction"))
                continue
            forward = pd == "OUTPUT"
            entry, exit_ = ("INPUT", "OUTPUT") if forward else ("OUTPUT", "INPUT")
            boundary = "OUTPUT" if forward else "INPUT"
            src = {find(b) for b in bl if b is not None}
            if not src:
                res[hi][p] = ["glue"]  # proved literal tie, not an unknown cone
                stats["constant"] += 1
                continue
            seen_nodes, seen_nets = {k}, set(src)
            frontier, dest, blocked = list(src), Counter(), set()
            for d in range(depth + 1):
                hits, nxt_nodes = Counter(), []
                for n in frontier:
                    for pn, direction in ports_of_net.get(n, ()):
                        if direction == "INOUT":
                            blocked.add("ambiguous_top_port_direction:" + pn)
                        if direction != boundary:
                            continue
                        if pn in face_bus:
                            hits[f"bus:{pn}"] += 1
                        elif pn in slot_face and slot_face[pn]:
                            hits[f"face:{slot_face[pn]}"] += 1
                    users = net_nodes.get(n, ())
                    if len(users) > fanout:
                        blocked.add("fanout_bound")
                        continue
                    for j, pj in users:
                        if j in seen_nodes:
                            continue
                        hj = core_of.get(insts[j][1])
                        dj = dirs[j].get(pj)
                        if dj not in ("INPUT", "OUTPUT"):
                            if pj not in ("VDD", "VSS", "VPWR", "VGND"):
                                blocked.add("unknown_cell_port_direction:" + insts[j][0] + "." + pj)
                            continue
                        if hj is not None:
                            if hj != hi and dj == entry:
                                hits[f"core:{hj}.{pj}"] += 1
                            continue
                        # Never enter a cell through the same side we intend
                        # to leave: A-input to B-input is not a signal path.
                        if dj != entry:
                            continue
                        seen_nodes.add(j)
                        nxt_nodes.append(j)
                if hits:
                    dest = hits
                    stats[f"depth{d}"] += 1
                    break
                frontier = []
                for j in nxt_nodes:
                    for pj, blj in insts[j][2].items():
                        if dirs[j].get(pj) != exit_:
                            continue
                        for bt in blj:
                            if bt is not None and find(bt) not in seen_nets:
                                seen_nets.add(find(bt))
                                frontier.append(find(bt))
                if not frontier:
                    break
                if d == depth:
                    blocked.add("depth_bound")
            if blocked:
                unresolved.append(dict(core=hi, port=p, reason=sorted(blocked)))
            if dest:
                res[hi][p] = [x for x, _ in dest.most_common(max_dest)]
            elif not blocked:
                res[hi][p] = ["glue"]
                stats["glue"] += 1
    # A batch caller must not mistake a partially traced core for complete.
    for bad_core in {u["core"] for u in unresolved}:
        res.pop(bad_core, None)
    h = hashlib.sha256(_open(netlist).read().encode()).hexdigest()[:12]
    return dict(core_conns={tn: {c: dict(sorted(v.items())) for c, v in res.items()}},
                receipt=dict(tool="core_conns_netlist.py", type=tn, netlist=str(netlist), netlist_sha256_12=h,
                             top=topname, cores_found=sorted(set(core_of.values())), cores_wanted=sorted(want),
                             depth=depth, fanout=fanout, max_dest=max_dest, ports=dict(stats),
                             liberty=[str(p) for p in libs], unresolved=unresolved,
                             advisory=True, do_not_count=True, qualified=not unresolved))


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
    ap.add_argument("--liberty", action="append", default=[], help="additional actual cell Liberty file(s)")
    a = ap.parse_args(argv)
    op = gzip.open if a.plan.endswith(".gz") else open
    plan = json.load(op(a.plan, "rt"))
    top = a.top or plan["partition_types"][a.type].get("module")
    r = derive(plan, a.type, a.netlist, a.cores.split(",") if a.cores else None, a.depth, a.fanout, a.max_dest, top, a.liberty)
    json.dump(r, open(a.out, "w"), indent=1)
    cc = r["core_conns"][a.type]
    print(f"{a.type}: cores {len(cc)}/{len(r['receipt']['cores_wanted'])} found, ports {r['receipt']['ports']}")
    return 2 if r["receipt"]["unresolved"] else 0


if __name__ == "__main__":
    sys.exit(main())
