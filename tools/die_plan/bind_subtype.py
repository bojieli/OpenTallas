"""Opt-in sub-type binding (BIND-SUBTYPE 11-11; asbuilt.subtype_bind, absent = nothing runs).

A plan may cut one native module into hard sub-types (HBM d44v: the SFU lane = _fr + _ex + _bk under the plan glue
ot_hgi_sfu_split3_lane_core__idpin, the TKM collective = one root core + 32 tile glues, each tile = two htile cores).
The as-built elaboration only knows the native leaf, so the kits find no instance at the plan paths (KIT_PREFLIGHT
macro_instances).  This pass replaces each matching native leaf, after composition and before the connectivity graph,
by the instances of an RTL COMPOSITION whose ports are the native leaf's ports:

    {"leaf": regex (fullmatch) on the leaf path,      "native": module the matched leaf must have,
     "top": composition module,                       "files": [RTL files defining top + its wires-only levels],
     "stops": [modules that become the new leaves],   (the plan glue / sub-core masters; they stay as-built leaves)
     "rename": {top port: native port},               (default: same name)
     "share": {top input port: native input port},    (an extra top input on an existing native input net)
     "local": {stop instance path in top: local name} (optional bound name; default <native local>.<instance path>),
     "defines": [...], "note": "..."}

New leaves: one per stop instance in the flattened top; path = <native path> when the stop instance IS the top
(top in stops: a one-to-one substitution that keeps the bound name), else <native path>.<instance path>.

Exactness (fails closed, SubtypeError): the native leaf has the declared module and no parameters the composition
would drop; every native port bit is exactly one top port bit (same direction, same width after rename); every extra
top port is an input in `share` of the same width; a top port bit wired inside the top to another top port bit must
carry the same native net (no new shorts); every native output bit has exactly one driver among the new leaves'
outputs (stop interfaces from the files), and no input-only net is driven twice; constant bits inside the top are
emitted as constants.  Wires strictly inside the top get fresh nets.  The pass changes no other cell.
The receipt (bind_report.subtype_bind) lists every replaced leaf, its new leaves and the port map, so the wiring
proof (subtype_lec.py) can rebuild the same composition independently.
"""
import re
from pathlib import Path

import bind_compose_split as CS
from bind_elab import Cell


class SubtypeError(ValueError):
    pass


def load(rule, base):
    texts = []
    for f in rule.get("files", []):
        p = Path(f) if Path(f).is_absolute() else Path(base) / f
        texts.append(p.read_text(errors="replace"))
    try:
        mods = CS.parse(texts, rule.get("defines", []))
    except CS.SplitError as exc:
        raise SubtypeError(f"{rule['top']}: {exc}") from exc
    for m in [rule["top"]] + list(rule.get("stops", [])):
        if m not in mods:
            raise SubtypeError(f"{rule['top']}: module {m} is not defined in the rule files")
    return mods


def composition(rule, mods):
    """(top ports {name: (dir, width)}, port bits {(port, i): root}, new leaves {inst path: (module, params, {port: [root|'0'|'1']},
    {port: dir})}).  A top in stops is one leaf at path ''."""
    top, stops = rule["top"], set(rule.get("stops", []))
    if not stops:
        raise SubtypeError(f"{top}: no stops")
    tports = {p: (d, w) for p, (d, lo, w) in mods[top]["ports"].items()}
    if top in stops:
        ports = {(p, i): ("", p, mods[top]["ports"][p][1] + i) for p in tports for i in range(tports[p][1])}
        terms = {p: [("", p, mods[top]["ports"][p][1] + i) for i in range(w)] for p, (d, w) in tports.items()}
        return tports, ports, {"": (top, {}, terms, {p: d for p, (d, w) in tports.items()})}
    hier = {k: v for k, v in mods.items() if k not in stops}
    try:
        port_bits, terms, leaves, consts = _flatten(top, hier)
    except CS.SplitError as exc:
        raise SubtypeError(f"{top}: {exc}") from exc
    out = {}
    for path, (mod, params) in leaves.items():
        if mod not in stops:
            raise SubtypeError(f"{top}: {path} is an instance of {mod}, neither a stop nor defined in the rule files")
        iface = mods[mod]["ports"]
        conn = {}
        for p, roots in terms[path].items():
            if p not in iface:
                raise SubtypeError(f"{top}: {path} has no port {p} on {mod}")
            if len(roots) != iface[p][2]:
                raise SubtypeError(f"{top}: {path}.{p} width {len(roots)} != {iface[p][2]}")
            conn[p] = [consts.get(r, r) if r in consts else r for r in roots]
        out[path] = (mod, params, conn, {p: iface[p][0] for p in conn})
    for root, v in consts.items():
        if root in set(port_bits.values()):
            raise SubtypeError(f"{top}: a top port bit is tied to constant {v} inside the composition")
    return tports, port_bits, out


def _flatten(top, mods):
    """bind_compose_split.flatten with constants allowed on leaf terminals (each constant bit is its own root)."""
    uf, leaves, terms, const = CS._UF(), {}, {}, {}

    def walk(mod, scope, pvals):
        M = mods[mod]
        params = dict(M["params"])
        params.update(pvals)
        for a, b in M["assigns"]:
            la, lb = CS.bits_of(a, M["sig"], scope), CS.bits_of(b, M["sig"], scope)
            if len(la) != len(lb):
                raise CS.SplitError(f"{mod}: assign width {a} = {b}")
            for x, y in zip(la, lb):
                if y[0] == "const":
                    const[x] = y[1]
                else:
                    uf.union(y, x)
        for typ, inst, pv, conns in M["insts"]:
            path = (scope + "." if scope else "") + inst
            val = {k: params.get(v, v) for k, v in pv.items()}
            if typ in mods:
                sub = mods[typ]
                for p, e in conns.items():
                    if p not in sub["ports"]:
                        raise CS.SplitError(f"{mod}.{inst}: no port {p} on {typ}")
                    outer, (d, lo, w) = CS.bits_of(e, M["sig"], scope), sub["ports"][p]
                    if len(outer) != w:
                        raise CS.SplitError(f"{mod}.{inst}.{p}: width {len(outer)} != {w}")
                    for i, x in enumerate(outer):
                        y = (path, p, lo + i)
                        if x[0] == "const":
                            const[y] = x[1]
                        else:
                            uf.union(x, y)
                walk(typ, path, val)
            else:
                leaves[path] = (typ, val)
                bs = []
                for p, e in conns.items():
                    for i, x in enumerate(CS.bits_of(e, M["sig"], scope)):
                        if x[0] == "const":
                            k = ("const", path, p, i)
                            const[k] = x[1]
                            bs.append((p, k))
                        else:
                            bs.append((p, x))
                terms[path] = {}
                for p, x in bs:
                    terms[path].setdefault(p, []).append(x)

    walk(top, "", {})
    T = mods[top]
    port_bits = {(p, i): uf.find(("", p, lo + i)) for p, (d, lo, w) in T["ports"].items() for i in range(w)}
    for leaf, ps in terms.items():
        for p, bs in ps.items():
            ps[p] = [b if b[0] == "const" else uf.find(b) for b in bs]
    consts = {}
    for k, v in const.items():
        r = k if k[0] == "const" else uf.find(k)
        consts[r] = str(int(v)) if str(v) in ("0", "1") else str(v)
    return port_bits, terms, leaves, consts


def _native_map(rule, c, tports):
    """{top port: native port} covering every native port exactly once, plus shared extra inputs."""
    rename, share = dict(rule.get("rename", {})), dict(rule.get("share", {}))
    m = {}
    for tp in tports:
        if tp in share:
            continue
        m[tp] = rename.get(tp, tp)
    covered = list(m.values())
    if sorted(covered) != sorted(c.ports):
        missing = sorted(set(c.ports) - set(covered))
        extra = sorted(set(covered) - set(c.ports))
        raise SubtypeError(f"{c.path}: port cover mismatch (native ports not covered {missing[:8]}, top ports without a "
                           f"native port {extra[:8]})")
    for tp, np_ in list(m.items()) + list(share.items()):
        if tp not in tports:
            raise SubtypeError(f"{c.path}: rule port {tp} is not a port of {rule['top']}")
        if np_ not in c.ports:
            raise SubtypeError(f"{c.path}: native port {np_} missing")
        d, w = tports[tp]
        if c.dirs.get(np_) != d or len(c.ports[np_]) != w:
            raise SubtypeError(f"{c.path}: {rule['top']}.{tp} ({d} {w}) != native {np_} ({c.dirs.get(np_)} "
                               f"{len(c.ports[np_])})")
        if tp in share and d != "input":
            raise SubtypeError(f"{c.path}: shared port {tp} must be an input")
    return m, share


def replace(F, R, c, rule, comp):
    """new Cells for native leaf c (see module doc)."""
    tports, port_bits, leaves = comp
    if c.params and not rule.get("drop_params"):
        raise SubtypeError(f"{c.path}: native leaf has parameters {sorted(c.params)[:6]} (set drop_params to record them)")
    m, share = _native_map(rule, c, tports)
    root_net, root_src = {}, {}
    for (tp, i), root in port_bits.items():
        np_ = m.get(tp) or share[tp]
        net = c.ports[np_][i]
        if root in root_net and root_net[root] != net:
            raise SubtypeError(f"{c.path}: {rule['top']} wires {tp}[{i}] to {root_src[root]} but the native nets differ")
        root_net[root], root_src[root] = net, f"{tp}[{i}]"
    part = R.part_of(c.path)
    if part is None:
        raise SubtypeError(f"{c.path}: leaf is in no partition")
    base_local = R.local_of(c.path) or c.path
    fresh = {}
    drivers = {}
    cells = []
    for ip, (mod, params, conn, dirs) in sorted(leaves.items()):
        ports = {}
        for p, roots in conn.items():
            bits = []
            for r in roots:
                if isinstance(r, str):
                    bits.append(r)
                elif r in root_net:
                    bits.append(root_net[r])
                else:
                    if r not in fresh:
                        fresh[r] = F.new(1)
                    bits.append(fresh[r])
            ports[p] = bits
            if dirs[p] == "output":
                for b in bits:
                    if isinstance(b, int):
                        drivers[b] = drivers.get(b, 0) + 1
        path = c.path if ip == "" else c.path + "." + ip
        if ip:
            R.parts[path] = [part, (rule.get("local") or {}).get(ip, base_local + "." + ip)]
        cells.append(Cell(path, mod, {k: v for k, v in params.items()}, ports, dict(dirs), "leaf", ytype=mod,
                          yparams={}, src=c.src))
    for np_, bits in c.ports.items():
        if c.dirs.get(np_) == "output":
            for i, b in enumerate(bits):
                if isinstance(b, int) and drivers.get(b, 0) != 1:
                    raise SubtypeError(f"{c.path}: native output {np_}[{i}] has {drivers.get(b, 0)} drivers in "
                                       f"{rule['top']}")
    multi = [b for b, k in drivers.items() if k > 1]
    if multi:
        raise SubtypeError(f"{c.path}: {len(multi)} nets with several drivers in {rule['top']}")
    return cells, dict(leaf=c.path, native=c.module, top=rule["top"], part=part,
                       new=[dict(path=x.path, module=x.module) for x in cells],
                       port_map=m, share=share, internal_nets=len(fresh), dropped_params=dict(c.params))


def apply(binder, rules):
    """Replace every matching leaf of binder.F; returns the receipt list.  Every rule must match at least one leaf."""
    F, R = binder.F, binder.R
    out, receipts = [], []
    prepared = []
    for r in rules:
        for k in ("leaf", "native", "top", "files", "stops"):
            if k not in r:
                raise SubtypeError(f"subtype_bind rule without {k}: {r}")
        mods = load(r, binder.base)
        prepared.append((re.compile(r["leaf"]), r, composition(r, mods), mods))
    hits = [0] * len(prepared)
    alias = {}
    for c in F.cells:
        rule = None
        if c.kind == "leaf":
            for k, (rx, r, comp, mods) in enumerate(prepared):
                if rx.fullmatch(c.path):
                    if rule is not None:
                        raise SubtypeError(f"{c.path}: matched by two subtype_bind rules")
                    rule = (k, r, comp)
        if rule is None:
            out.append(c)
            continue
        k, r, comp = rule
        if c.module != r["native"]:
            raise SubtypeError(f"{c.path}: native module {c.module} != rule native {r['native']}")
        cells, rec = replace(F, R, c, r, comp)
        if len(cells) == 1 and cells[0].path == c.path:
            # one-to-one substitution: the leaf keeps its path and every native port bit is the same bit of the renamed
            # top port, so a table written on the native bind (r8 landing) names (leaf, native port) -> (leaf, top port)
            for tp, np_ in rec["port_map"].items():
                if tp != np_:
                    alias[(c.path, np_)] = (c.path, tp)
        hits[k] += 1
        out.extend(cells)
        receipts.append(rec)
    for k, (rx, r, comp, mods) in enumerate(prepared):
        if not hits[k]:
            raise SubtypeError(f"subtype_bind rule {r['leaf']} matched no leaf")
        for f in r["files"]:
            p = str(Path(f) if Path(f).is_absolute() else Path(binder.base) / f)
            if p not in binder.extra_lib:
                binder.extra_lib.append(p)
    F.cells[:] = out
    binder.subtype_alias = alias
    return receipts
