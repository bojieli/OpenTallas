"""Opt-in split form of a composed cut (DIE-HBM-92-SU 11-08): the same as-built leaves, regrouped into hard sub-cores.

A plan may name a hard sub-core inside a composed cut (HBM d44v: u_su_Q2_lanes0_3.u_fcore.u_core.u_p0 =
ot_hbm_su_pg_lane1_core = one as-built pinned bank + one as-built pinreg lane).  bind_compose emits the cut flat
(members m0..mN), so the kit has no instance at the plan path (KIT_PREFLIGHT macro_instances).  A split rule
(asbuilt.compose_split) regroups the members of each matching cut under the sub-core master, nested in wires-only
levels (u_fcore, u_core) that carry the cut's ports unchanged:

    {"inst": regex on the cut path, "suffix": module suffix, "levels": ["u_fcore", "u_core"],
     "subs": [{"name": "u_p{k}", "module": sub-core master, "sources": [RTL files of the sub-core],
               "roles": {leaf path inside the sub-core: regex on the member path with ONE group (the sub index)},
               "param_diff_ok": [leaf parameters that may differ from the sub-core source, recorded]}]}

Exactness (fails closed, CompositionError): the sub-core source is flattened bit by bit (ports, wires, assigns,
instances; leaves = modules the sources do not define).  Every sub-core input bit drives member terminals that the cut
wires to ONE net; every output bit has exactly one member driver; every bit private to the sub-core (wires between its
leaves) is one cut net with no terminal outside the group and no cut port; every member terminal is covered.  Leaf
modules and parameters must equal the sub-core source's (param_diff_ok differences are recorded, never hidden).
Nothing else in the cut changes: glue, wires, assigns and the other members are emitted as before.

Re-formed sub-cores (opt-in per sub, DIE-HBM-92-SU-EXP 11-08): "module" stays the REFERENCE the members are proven
against (the uncut core over the as-built leaves, exact as above); "emit_module" + "emit_sources" name the re-formed
composition instantiated in its place (HBM p18: lane_exp_core -> lane_exp_x_core + sfu_s_core).  The emitted module
must have exactly the reference's ports (name, direction, range; check_emit), and "emit_proof" (the
reference-vs-composition equivalence: bench, log, sha) is copied into the receipt.  "same_net": [[port, ...], ...]
requires every bit of each listed port group on ONE cut net (clock replicas a one-clock wrapper merges).
"""
import re
from collections import defaultdict
from pathlib import Path


class SplitError(ValueError):
    pass


_MOD = re.compile(r"\bmodule\s+(\w+)\s*(#\s*\((.*?)\)\s*)?\((.*?)\);(.*?)\bendmodule", re.S)
_DECL = re.compile(r"\b(input|output|inout|wire)\s+(?:wire\s+|reg\s+|logic\s+)?(?:\[(\d+):(\d+)\]\s*)?(\w+)")
_PARAM = re.compile(r"parameter\s+(?:integer\s+)?(\w+)\s*=\s*([^,;)\s]+)")
_INST = re.compile(r"(?m)^\s*(\w+)\s*(#\s*\((?:[^()]|\([^()]*\))*\))?\s*(\w+)\s*\((.*?)\);", re.S)
_CONN = re.compile(r"\.(\w+)\s*\(")


def _strip(text):
    return re.sub(r"//[^\n]*", "", re.sub(r"/\*.*?\*/", "", text, flags=re.S))


_PP = re.compile(r"^\s*`(ifdef|ifndef|elsif|else|endif|define|undef)\b\s*(\w*)")
_PP_SKIP = re.compile(r"^\s*`(timescale|default_nettype|resetall|celldefine|endcelldefine)\b")


def preprocess(text, defines=()):
    """Conditional compilation against the recipe defines (fail closed on macro uses and unbalanced blocks)."""
    defs, out, stack = set(defines), [], []          # stack entries: [taking, a branch was taken, parent taking]
    for ln in _strip(text).split("\n"):
        m = _PP.match(ln)
        taking = all(t for t, _, _ in stack)
        if m:
            d, name = m.groups()
            if d in ("ifdef", "ifndef"):
                c = (name in defs) == (d == "ifdef")
                stack.append([taking and c, c, taking])
            elif d in ("elsif", "else", "endif") and not stack:
                raise SplitError(f"`{d} without `ifdef")
            elif d == "elsif":
                t = stack[-1]
                c = not t[1] and name in defs
                t[0], t[1] = t[2] and c, t[1] or c
            elif d == "else":
                t = stack[-1]
                t[0], t[1] = t[2] and not t[1], True
            elif d == "endif":
                stack.pop()
            elif taking and d == "define":
                defs.add(name)
            elif taking and d == "undef":
                defs.discard(name)
            out.append("")
            continue
        if _PP_SKIP.match(ln):
            out.append("")
            continue
        if taking and "`" in ln:
            raise SplitError("macro use not supported in a split source: " + ln.strip()[:80])
        out.append(ln if taking else "")
    if stack:
        raise SplitError("unbalanced `ifdef")
    return "\n".join(out)


def parse(texts, defines=()):
    """{module: dict(ports={name: (dir, lo, width)}, sig={name: (lo, width)}, params={k: v}, assigns, insts)}."""
    mods = {}
    for text in texts:
        for m in _MOD.finditer(preprocess(text, defines)):
            name, ptxt, ports_txt, body = m.group(1), m.group(3) or "", m.group(4), m.group(5)
            ports, sig = {}, {}
            for d in _DECL.finditer(ports_txt + ";" + body):
                kind, hi, lo, n = d.groups()
                if n in ("wire", "reg", "logic"):
                    continue
                lo_i, w = (int(lo), int(hi) - int(lo) + 1) if hi is not None else (0, 1)
                if hi is not None and int(hi) < int(lo):
                    raise SplitError(f"{name}.{n}: descending declarations only")
                sig.setdefault(n, (lo_i, w))
                if kind in ("input", "output", "inout"):
                    if kind == "inout":
                        raise SplitError(f"{name}.{n}: inout")
                    ports[n] = (kind, lo_i, w)
            params = dict(_PARAM.findall(ptxt + ";" + body))
            assigns = [(a.strip(), b.strip()) for a, b in re.findall(r"\bassign\s+(.*?)=(.*?);", body, re.S)]
            insts = []
            for im in _INST.finditer(body):
                typ, pblock, inst, conns = im.groups()
                if typ in ("module", "assign", "wire", "input", "output", "reg", "logic", "parameter", "localparam"):
                    continue
                pv = dict(re.findall(r"\.(\w+)\s*\(([^()]*)\)", pblock or ""))
                cm, pos = {}, 0
                while True:
                    c = _CONN.search(conns, pos)
                    if not c:
                        break
                    d, j = 1, c.end()
                    while j < len(conns) and d:
                        d += {"(": 1, ")": -1}.get(conns[j], 0)
                        j += 1
                    cm[c.group(1)] = conns[c.end():j - 1].strip()
                    pos = j
                insts.append((typ, inst, {k: v.strip() for k, v in pv.items()}, cm))
            mods[name] = dict(ports=ports, sig=sig, params=params, assigns=assigns, insts=insts)
    return mods


def _split_top(s, sep=","):
    out, d, cur = [], 0, ""
    for ch in s:
        d += {"{": 1, "(": 1, "[": 1, "}": -1, ")": -1, "]": -1}.get(ch, 0)
        if ch == sep and d == 0:
            out.append(cur)
            cur = ""
        else:
            cur += ch
    out.append(cur)
    return [x.strip() for x in out]


def bits_of(expr, sig, scope):
    """LSB-first [bit key] of an expression: name, name[i], name[h:l], {a, b}, {N{x}}, n'bV constants."""
    e = expr.strip()
    if e == "":
        return []
    if e.startswith("{") and e.endswith("}"):
        inner = e[1:-1].strip()
        rep = re.fullmatch(r"(\d+)\s*(\{.*\})", inner, re.S)
        if rep:
            return bits_of(rep.group(2), sig, scope) * int(rep.group(1))
        out = []
        for part in reversed(_split_top(inner)):
            out += bits_of(part, sig, scope)
        return out
    c = re.fullmatch(r"(\d+)'([bdh])([0-9a-fA-F_]+)", e)
    if c:
        w, v = int(c.group(1)), int(c.group(3).replace("_", ""), {"b": 2, "d": 10, "h": 16}[c.group(2)])
        return [("const", (v >> i) & 1) for i in range(w)]
    m = re.fullmatch(r"(\w+)\s*(?:\[(\d+)(?::(\d+))?\])?", e)
    if not m or m.group(1) not in sig:
        raise SplitError(f"{scope}: unsupported or undeclared expression {e!r}")
    lo, w = sig[m.group(1)]
    if m.group(2) is None:
        idx = list(range(lo, lo + w))
    elif m.group(3) is None:
        idx = [int(m.group(2))]
    else:
        h, l = int(m.group(2)), int(m.group(3))
        idx = list(range(l, h + 1))
    if any(i < lo or i >= lo + w for i in idx):
        raise SplitError(f"{scope}: {e!r} out of range")
    return [(scope, m.group(1), i) for i in idx]


class _UF:
    def __init__(self):
        self.p = {}

    def find(self, x):
        self.p.setdefault(x, x)
        while self.p[x] != x:
            self.p[x] = self.p[self.p[x]]
            x = self.p[x]
        return x

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.p[rb] = ra


def flatten(top, mods):
    """(port bits {(port, i): root}, leaf terminals {leaf path: {port: [root, ...]}}, leaves {path: (module, params)},
    constants {root: 0|1}) of module top; leaves are instances of modules mods does not define."""
    uf, leaves, terms, const = _UF(), {}, {}, {}

    def walk(mod, scope, pvals):
        M = mods[mod]
        params = dict(M["params"])
        params.update(pvals)
        for a, b in M["assigns"]:
            la, lb = bits_of(a, M["sig"], scope), bits_of(b, M["sig"], scope)
            if len(la) != len(lb):
                raise SplitError(f"{mod}: assign width {a} = {b}")
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
                        raise SplitError(f"{mod}.{inst}: no port {p} on {typ}")
                    outer, (d, lo, w) = bits_of(e, M["sig"], scope), sub["ports"][p]
                    if len(outer) != w:
                        raise SplitError(f"{mod}.{inst}.{p}: width {len(outer)} != {w}")
                    for i, x in enumerate(outer):
                        y = (path, p, lo + i)
                        if x[0] == "const":
                            const[y] = x[1]
                        else:
                            uf.union(x, y)
                walk(typ, path, val)
            else:
                leaves[path] = (typ, val)
                terms[path] = {p: bits_of(e, M["sig"], scope) for p, e in conns.items()}

    walk(top, "", {})
    T = mods[top]
    port_bits = {(p, i): uf.find(("", p, lo + i)) for p, (d, lo, w) in T["ports"].items() for i in range(w)}
    for leaf, ps in terms.items():
        for p, bs in ps.items():
            if any(b[0] == "const" for b in bs):
                raise SplitError(f"{top}: constant on leaf terminal {leaf}.{p} (unsupported)")
            ps[p] = [uf.find(b) for b in bs]
    consts = {uf.find(k): v for k, v in const.items()}
    return port_bits, terms, leaves, consts


def _num(v):
    s = str(v).strip()
    try:
        return int(s, 2) if re.fullmatch(r"[01]{8,}", s) else int(s)
    except ValueError:
        return s


def bind_sub(sub, mods, members, term_expr, term_net, net_terms, port_nets):
    """Port connections {port: [expr per bit LSB first]} of one sub-core over its member cells, plus a receipt.

    members {role leaf path: Cell}; term_expr/term_net[(cell path, port, bit)]; net_terms {net: {(cell, port, bit)}};
    port_nets = nets on the cut's own ports."""
    port_bits, terms, leaves, consts = flatten(sub["module"], mods)
    if set(leaves) != set(members):
        raise SplitError(f"{sub['module']}: leaves {sorted(leaves)} != roles {sorted(members)}")
    cls = defaultdict(list)                      # root -> [(cell path, port, bit, dir)]
    param_diff, open_ports = {}, []
    port_root_set = set(port_bits.values())
    uses = defaultdict(int)
    for ps in terms.values():
        for roots in ps.values():
            for r in roots:
                uses[r] += 1
    for role, cell in members.items():
        lmod, lparams = leaves[role]
        if cell.module != lmod:
            raise SplitError(f"{cell.path}: module {cell.module} != sub-core leaf {role} {lmod}")
        for k, v in lparams.items():
            if k in cell.params and _num(cell.params[k]) != _num(v):
                if k not in sub.get("param_diff_ok", []):
                    raise SplitError(f"{cell.path}: parameter {k}={cell.params[k]} != sub-core {role} {k}={v}")
                param_diff[f"{role}.{k}"] = dict(asbuilt=_num(cell.params[k]), sub_core=_num(v))
        live = {p for p, bs in cell.ports.items() if bs}
        if not live <= set(terms[role]):
            raise SplitError(f"{cell.path}: ports {sorted(live - set(terms[role]))[:6]} not on sub-core leaf {role}")
        for p, roots in terms[role].items():
            if not cell.ports.get(p):
                # an as-built OPEN leaf port (no connection): the sub-core may wire it only to bits nothing else
                # in the sub-core reads or exports (an unused output), recorded
                if any(uses[r] != 1 or r in port_root_set for r in roots):
                    raise SplitError(f"{cell.path}.{p}: open in the cut but used inside the sub-core")
                open_ports.append(f"{role}.{p}")
                continue
            if len(roots) != len(cell.ports[p]):
                raise SplitError(f"{cell.path}.{p}: width {len(cell.ports[p])} != sub-core {len(roots)}")
            for i, r in enumerate(roots):
                cls[r].append((cell.path, p, i, cell.dirs[p]))
    T = mods[sub["module"]]["ports"]
    conn, pnet = {}, {}
    port_roots = defaultdict(list)
    for (p, i), r in port_bits.items():
        port_roots[r].append((p, i))
    for p, (d, lo, w) in sorted(T.items()):
        conn[p] = []
        for i in range(w):
            r = port_bits[(p, i)]
            ts = cls.get(r, [])
            if not ts:
                raise SplitError(f"{sub['module']}.{p}[{i}]: no member terminal")
            nets = {term_net[t[:3]] for t in ts}
            if len(nets) != 1:
                raise SplitError(f"{sub['module']}.{p}[{i}]: member terminals on {len(nets)} cut nets")
            pnet[(p, i)] = next(iter(nets))
            drivers = [t for t in ts if t[3] == "output"]
            if d == "output":
                if len(drivers) != 1:
                    raise SplitError(f"{sub['module']}.{p}[{i}]: {len(drivers)} member drivers")
                conn[p].append(term_expr[drivers[0][:3]])
            else:
                if drivers:
                    raise SplitError(f"{sub['module']}.{p}[{i}]: input driven inside the sub-core")
                conn[p].append(term_expr[ts[0][:3]])
    for grp in sub.get("same_net", []):
        nets = {n for (p, i), n in pnet.items() if p in grp}
        if any(p not in T for p in grp) or len(nets) != 1:
            raise SplitError(f"{sub['module']}: same_net {grp} spans {len(nets)} cut nets")
    inside = {t[0] for t in sum(cls.values(), [])}
    private, seen_out = 0, defaultdict(list)
    for r, ts in cls.items():
        if r in port_roots:
            continue
        nets = {term_net[t[:3]] for t in ts}
        if len(nets) != 1:
            raise SplitError(f"{sub['module']}: private net {r} spans {len(nets)} cut nets")
        n = next(iter(nets))
        if isinstance(n, int):
            if n in port_nets or any(t[0] not in inside for t in net_terms.get(n, ())):
                for t in ts:
                    if t[3] == "output":
                        seen_out[(t[0], t[1])].append(t[2])
                continue
            if len(net_terms.get(n, ())) != len(ts):
                raise SplitError(f"{sub['module']}: private net {r} terminal count differs")
        elif r not in consts or str(consts[r]) != str(n):
            raise SplitError(f"{sub['module']}: private bit {r} is a cut constant {n} the sub-core lacks")
        private += 1
    # A private bit the cut still exports is allowed only when the rule declares it dropped (a dead parent load,
    # cited in drop_reason): the split cannot drive it from the sub-core, so the cut wire is tied 0 and recorded.
    role_of = {c.path: role for role, c in members.items()}
    drop = sub.get("drop_exports", {})
    bad, ties = {}, []
    for (c, p), bs in sorted(seen_out.items()):
        lo_hi = drop.get(f"{role_of[c]}.{p}")
        if lo_hi and all(lo_hi[0] <= b <= lo_hi[1] for b in bs):
            ties += [term_expr[(c, p, b)] for b in sorted(bs)]
        else:
            bad[(c, p)] = bs
    if bad:
        raise SplitError(f"{sub['module']}: sub-core private bits are visible outside the group in the cut: " + "; ".join(
            f"{c}.{p}[{min(b)}..{max(b)}] x{len(b)}" for (c, p), b in sorted(bad.items())))
    return conn, dict(module=sub["module"], private_bits=private, param_diff=param_diff, open_ports=open_ports,
                      dropped_exports=len(ties), tie0=ties,
                      members={role: c.path for role, c in sorted(members.items())})


def check_emit(sub, ref_mods, base):
    """Receipt of a re-formed emit_module: its ports must equal the reference sub-core's exactly."""
    em, found = sub["emit_module"], None
    for f in sub.get("emit_sources", []):
        text = (Path(f) if Path(f).is_absolute() else Path(base) / f).read_text(errors="replace")
        if re.search(r"\bmodule\s+" + re.escape(em) + r"\b", text):
            if found is not None:
                raise SplitError(f"{em}: defined in two emit sources")
            found = parse([text])[em]
    if found is None:
        raise SplitError(f"{em}: no emit source defines it")
    ref = ref_mods[sub["module"]]["ports"]
    if found["ports"] != ref:
        diff = sorted(set(found["ports"].items()) ^ set(ref.items()))[:6]
        raise SplitError(f"{em}: ports differ from the reference {sub['module']}: {diff}")
    return dict(module=em, reference=sub["module"], ports=len(ref), proof=sub.get("emit_proof"))


def load(rule, base):
    texts = []
    for f in rule.get("sources", []):
        p = Path(f) if Path(f).is_absolute() else Path(base) / f
        texts.append(p.read_text(errors="replace"))
    return parse(texts, rule.get("defines", []))


def groups(rule_sub, cells):
    """[(k, {role: Cell})] ordered by the role regexes' captured index."""
    by = defaultdict(dict)
    for role, rx in rule_sub["roles"].items():
        r = re.compile(rx)
        for c in cells:
            m = r.search(c.path)
            if m:
                k = int(m.group(1)) if m.groups() and m.group(1) else 0   # a role regex without a group: one sub
                if role in by[k]:
                    raise SplitError(f"{rule_sub['module']}: role {role} matches two members at index {k}")
                by[k][role] = c
    out = []
    for n, (k, roles) in enumerate(sorted(by.items())):
        if set(roles) != set(rule_sub["roles"]):
            raise SplitError(f"{rule_sub['module']}: index {k} lacks roles {sorted(set(rule_sub['roles']) - set(roles))}")
        out.append((n, roles))
    return out


def emit(mod, declarations, body_lines, levels):
    """[(module, text)]: mod (cut ports) -> levels of wires-only pass-through -> the core body."""
    names = [mod] + [mod + "__" + lv.replace("u_", "", 1) for lv in levels]
    pnames = [re.findall(r"(\w+)\s*$", d)[0] for d in declarations]
    out = []
    for i, lv in enumerate(levels):
        conns = ", ".join(f".{p}({p})" for p in pnames)
        out.append((names[i], "\n".join([f"module {names[i]} (", ",\n".join(declarations), ");",
                                         f"    {names[i + 1]} {lv} ({conns});", "endmodule\n"])))
    out.append((names[-1], "\n".join([f"module {names[-1]} (", ",\n".join(declarations), ");"] + body_lines +
                                     ["endmodule\n"])))
    return out
