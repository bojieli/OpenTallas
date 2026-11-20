#!/usr/bin/env python3
"""netlist_inherit.py -- a type inherits the sign-off of a signed sibling whose netlist is the same circuit (SIGN-INHERIT, OWNER 2026-11-20
decision (3), lane SIGN-PROFILE-0400).

OWNER 11-20: types whose netlists differ only in ROM image contents and in instance / net names inherit the sign-off of a signed sibling.
ROMs must carry real weights (OWNER 11-19), so the inheriting type's ROM views (LEF / LIB / GDS, tools/mem_compiler/rom_gen.py) are
still generated; no place and route is run for it.

The proof, per (member, representative) pair, all of which must hold for credit:
  1. GRAPH ISOMORPHISM of the synthesized cell netlists (<base>/1_2_yosys.v, else 1_synth.v; hierarchy flattened) as a bipartite
     graph: cell nodes labelled by master (+ parameters), net nodes, edges labelled by pin (bit).  Instance and net names are NOT
     labels (canonicalised away); TOP PORT names are labels (the pins must match).  ROM contents are masked: a ROM macro is labelled by
     its class -- LEF SIZE + pin names / directions when its LEF is found, else its master -- and its parameters are dropped, so two
     ROM macros of identical size and pins are the same node whatever image they carry.  Method: colour refinement (1-WL) of both
     graphs in lock step (a colour histogram that differs at any round = not isomorphic), then individualisation of the remaining
     symmetric classes, then an EXACT check of the resulting bijection on every cell, pin and net.  Only a bijection that passes the
     exact check is a proof; the canonical colour hash is stored as the structural hash.
  2. PHYSICAL MATCH: same kit pins.json pin table (bus, bit, layer, x, y, face), same DIE_AREA / CORE_AREA, same golden SDC after
     the type names are replaced by a placeholder, and every hard macro placed at the same location / orientation under the
     isomorphism (macro placement / plan hard_cores, when the kit has them).  Other config.mk differences are listed (advisory).
  3. The representative COUNTS (its signoff.json passes the R-MINIMAL gates, tools/die_plan/signoff_profile.judge).

Record (schema opentallas.netlist_inherit.v1, read by tools/fleet/release_tree_plan.py inherit_record_ok / inherit_credit through a
row of ~/coord/autopilot/inherit_members.tsv: die, member, representative, record path, record sha256):
  {schema, die, sibling, representative, credit, credit_blockers, proof {isomorphic, structural_hash, cells, nets, ports, rounds,
   individualised, rom_masked [[inst member, inst rep, class]]}, physical {...}, representative_signoff {path, verdict, gates, period},
   rom_views {status TO-GENERATE, instances}, inputs {netlist / pins / sdc / config paths + sha256}, generated, rule}

    netlist_inherit.py hash NETLIST.v [--lef-dir D ...]                           structural hash of one netlist
    netlist_inherit.py prove --die D --member M --rep R --member-kit KM --rep-kit KR --rep-signoff S --out REC.json [--lef-dir D ...]
CPU only (no STA); a 400k-cell pair takes minutes: run it through ot-run on a gen host for big types.
"""
import argparse
import datetime
import hashlib
import json
import os
import re
import sys
from collections import Counter
from pathlib import Path

SCHEMA = "opentallas.netlist_inherit.v1"
RULE = ("SIGN-INHERIT (OWNER 2026-11-20 decision (3)): a type whose synthesized netlist equals a signed sibling's after ROM contents are "
        "masked and instance / net names canonicalised (graph isomorphism, exact bijection check) and whose pins / outline / SDC / macro "
        "placement match inherits that sign-off; its ROM views are still generated (real weights), no P&R")
ROM_RE_DEFAULT = r"(?i)rom"
MAX_ROUNDS = 400
MAX_INDIV_ROUNDS = 200


def sha256_file(p):
    try:
        h = hashlib.sha256()
        with open(p, "rb") as f:
            for b in iter(lambda: f.read(1 << 20), b""):
                h.update(b)
        return h.hexdigest()
    except OSError:
        return None


def stable_int(s):
    return int.from_bytes(hashlib.blake2b(str(s).encode(), digest_size=8).digest(), "big") >> 1


# ------------------------------------------------------------------ structural Verilog (yosys write_verilog) reader
TOKEN = re.compile(r"""
    (?P<ws>\s+) | (?P<lc>//[^\n]*) | (?P<bc>/\*.*?\*/) | (?P<attr>\(\*.*?\*\)) |
    (?P<esc>\\\S+) | (?P<num>\d*'[sS]?[bBoOdDhH][0-9a-fA-FxXzZ_?]+|\d+) | (?P<str>"(?:[^"\\]|\\.)*") |
    (?P<id>[A-Za-z_$][A-Za-z0-9_$]*) | (?P<sym>[()\[\]{}:;,.=#\-+])
""", re.S | re.X)


def tokens(text):
    out = []
    pos, n = 0, len(text)
    while pos < n:
        m = TOKEN.match(text, pos)
        if not m:
            raise ValueError("verilog: cannot tokenize at %d: %r" % (pos, text[pos:pos + 40]))
        pos = m.end()
        k = m.lastgroup
        if k in ("ws", "lc", "bc", "attr"):
            continue
        v = m.group()
        if k == "esc":
            k, v = "id", v[1:]
        out.append((k, v))
    return out


def const_bits(tok):
    """N'b0101 -> ['1','0','1','0'] LSB first; plain decimal -> 32 bits"""
    m = re.match(r"^(\d*)'[sS]?([bBoOdDhH])([0-9a-fA-FxXzZ_?]+)$", tok)
    if not m:
        v, w = int(tok), 32
        return ["1" if (v >> i) & 1 else "0" for i in range(w)]
    w = int(m.group(1)) if m.group(1) else 32
    base, digs = m.group(2).lower(), m.group(3).replace("_", "").lower()
    bits = []
    if base == "b":
        bits = list(digs)
    elif base in "oh":
        per = 3 if base == "o" else 4
        for d in digs:
            if d in "xz?":
                bits += [d if d != "?" else "z"] * per
            else:
                bits += list(format(int(d, 16 if base == "h" else 8), "0%db" % per))
    else:
        bits = list(format(int(digs), "b"))
    bits = bits[::-1]                                 # LSB first
    bits = (bits + ([bits[-1]] if bits and bits[-1] in "xz" else ["0"]) * w)[:w]
    return ["z" if b == "?" else b for b in bits]


class Module:
    def __init__(self, name):
        self.name, self.ports, self.decl, self.dirs, self.assigns, self.insts = name, [], {}, {}, [], []


def parse(text):
    """-> {module name: Module}.  decl {net: (msb, lsb) | None}; insts [(master, inst, params {}, conns {pin: expr})];
    expr = ('id', name) | ('bit', name, i) | ('range', name, a, b) | ('const', bits) | ('cat', [expr]) | ('rep', n, expr)"""
    t = tokens(text)
    i, mods = 0, {}

    def peek(k=0):
        return t[i + k] if i + k < len(t) else (None, None)

    def take(v=None):
        nonlocal i
        tok = t[i]
        if v is not None and tok[1] != v:
            raise ValueError("verilog: expected %r got %r near token %d" % (v, tok[1], i))
        i += 1
        return tok

    def rng():
        if peek()[1] != "[":
            return None
        take("[")
        a = int(take()[1])
        take(":")
        b = int(take()[1])
        take("]")
        return (a, b)

    def expr():
        k, v = peek()
        if v == "{":
            take("{")
            if peek()[0] == "num" and peek(1)[1] == "{":
                n = int(take()[1])
                take("{")
                parts = [expr()]
                while peek()[1] == ",":
                    take(",")
                    parts.append(expr())
                take("}")
                take("}")
                return ("rep", n, ("cat", parts))
            parts = [expr()]
            while peek()[1] == ",":
                take(",")
                parts.append(expr())
            take("}")
            return ("cat", parts)
        if k == "num":
            take()
            return ("const", const_bits(v))
        if k == "id":
            take()
            if peek()[1] == "[":
                take("[")
                a = int(take()[1])
                if peek()[1] == ":":
                    take(":")
                    b = int(take()[1])
                    take("]")
                    return ("range", v, a, b)
                take("]")
                return ("bit", v, a)
            return ("id", v)
        raise ValueError("verilog: bad expression token %r at %d" % (v, i))

    while i < len(t):
        k, v = take()
        if v != "module":
            continue
        m = Module(take()[1])
        if peek()[1] == "#":                           # module parameters (not in netlists; skip balanced)
            take("#")
            depth = 0
            while True:
                x = take()[1]
                depth += x == "("
                depth -= x == ")"
                if depth == 0:
                    break
        if peek()[1] == "(":
            take("(")
            while peek()[1] != ")":
                x = take()
                if x[0] == "id" and x[1] not in ("input", "output", "inout", "wire", "reg"):
                    m.ports.append(x[1])
            take(")")
        take(";")
        while True:
            k, v = peek()
            if v == "endmodule":
                take()
                break
            if v in ("input", "output", "inout", "wire", "reg", "tri", "supply0", "supply1"):
                take()
                while peek()[1] in ("wire", "reg", "signed"):
                    take()
                r = rng()
                names = [take()[1]]
                while peek()[1] == ",":
                    take(",")
                    names.append(take()[1])
                take(";")
                for nm in names:
                    if v in ("input", "output", "inout"):
                        m.dirs[nm] = v
                    m.decl[nm] = r if r is not None or nm not in m.decl else m.decl[nm]
                    if v in ("supply0", "supply1"):
                        m.assigns.append((("id", nm), ("const", ["0" if v == "supply0" else "1"])))
                continue
            if v == "assign":
                take()
                lhs = expr()
                take("=")
                rhs = expr()
                take(";")
                m.assigns.append((lhs, rhs))
                continue
            if k == "id":                                # instance
                master = take()[1]
                params = {}
                if peek()[1] == "#":
                    take("#")
                    take("(")
                    while peek()[1] != ")":
                        if peek()[1] == ",":
                            take(",")
                            continue
                        take(".")
                        pn = take()[1]
                        take("(")
                        depth, val = 1, []
                        while True:
                            x = take()[1]
                            depth += x == "("
                            depth -= x == ")"
                            if depth == 0:
                                break
                            val.append(x)
                        params[pn] = "".join(val)
                    take(")")
                inst = take()[1]
                conns = {}
                take("(")
                pos = 0
                while peek()[1] != ")":
                    if peek()[1] == ",":
                        take(",")
                        continue
                    if peek()[1] == ".":
                        take(".")
                        pn = take()[1]
                        take("(")
                        conns[pn] = None if peek()[1] == ")" else expr()
                        take(")")
                    else:
                        conns["#%d" % pos] = expr()
                        pos += 1
                take(")")
                take(";")
                m.insts.append((master, inst, params, conns))
                continue
            take()                                       # anything else (e.g. stray ';')
        mods[m.name] = m
    return mods


def width_bits(m, name):
    r = m.decl.get(name)
    if r is None:
        return [None]
    a, b = r
    step = -1 if a >= b else 1
    return list(range(a, b + step, step))               # MSB..LSB as declared


def bits_of(m, e, scope):
    """expr -> list of bit keys MSB first; a bit key is (scope, net, idx) or ('const', '0'|'1'|'x'|'z')"""
    k = e[0]
    if k == "id":
        return [(scope, e[1], b) for b in width_bits(m, e[1])]
    if k == "bit":
        return [(scope, e[1], e[2])]
    if k == "range":
        a, b = e[2], e[3]
        step = -1 if a >= b else 1
        return [(scope, e[1], x) for x in range(a, b + step, step)]
    if k == "const":
        return [("const", x) for x in reversed(e[1])]
    if k == "cat":
        out = []
        for p in e[1]:
            out += bits_of(m, p, scope)
        return out
    if k == "rep":
        return bits_of(m, e[2], scope) * e[1]
    raise ValueError(e)


class UF:
    def __init__(self):
        self.p = {}

    def find(self, x):
        p = self.p
        r = x
        while p.get(r, r) != r:
            r = p[r]
        while p.get(x, x) != r:
            p[x], x = r, p[x]
        return r

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            if ra[0] == "const":                         # constants stay roots
                ra, rb = rb, ra
            self.p[ra] = rb


def rom_class_of(master, lef_sigs, rom_re):
    if not re.search(rom_re, master):
        return None
    sig = lef_sigs.get(master)
    return "ROM:" + (sig if sig else "master=" + master)


def lef_signatures(dirs):
    """{macro: 'SIZE w BY h|pins dir...'} from every *.lef below dirs"""
    out = {}
    for d in dirs or []:
        for p in Path(d).rglob("*.lef"):
            try:
                text = p.read_text(errors="replace")
            except OSError:
                continue
            for m in re.finditer(r"^\s*MACRO\s+(\S+)(.*?)^\s*END\s+\1\s*$", text, re.M | re.S):
                body = m.group(2)
                size = re.search(r"SIZE\s+([\d.]+)\s+BY\s+([\d.]+)", body)
                pins = sorted("%s:%s" % (pm.group(1), (re.search(r"DIRECTION\s+(\w+)", pm.group(2)) or [None, "?"])[1])
                              for pm in re.finditer(r"^\s*PIN\s+(\S+)(.*?)^\s*END\s+\1\s*$", body, re.M | re.S))
                out[m.group(1)] = "SIZE %s BY %s|%s" % (size.group(1) if size else "?", size.group(2) if size else "?",
                                                       hashlib.sha256(",".join(pins).encode()).hexdigest()[:16])
    return out


class Graph:
    """bipartite cell / net graph with integer labels"""

    def __init__(self):
        self.cell_name, self.cell_label, self.cell_master, self.cell_adj = [], [], [], []
        self.net_label, self.net_adj, self.net_name = [], [], []
        self.rom = []                                   # (cell id, class)


def build(mods, top=None, lef_sigs=None, rom_re=ROM_RE_DEFAULT):
    """flatten from top (the module nobody instantiates) into a Graph"""
    lef_sigs = lef_sigs or {}
    used = {i[0] for m in mods.values() for i in m.insts}
    if top is None:
        tops = [n for n in mods if n not in used]
        if len(tops) != 1:
            raise ValueError("netlist: %d top modules %s" % (len(tops), tops[:5]))
        top = tops[0]
    uf = UF()
    cells = []                                          # (path, master, params, [(pin, bitkey)])
    port_bits = {}                                      # bitkey -> label

    def walk(mname, scope, binding):
        m = mods[mname]
        for p, bk in binding.items():                   # bind child port bits to parent nets
            uf.union((scope, p[0], p[1]), bk)
        for lhs, rhs in m.assigns:
            lb, rb = bits_of(m, lhs, scope), bits_of(m, rhs, scope)
            n = min(len(lb), len(rb))
            for a, b in zip(lb[len(lb) - n:], rb[len(rb) - n:]):
                uf.union(a, b)
        for master, inst, params, conns in m.insts:
            path = scope + (inst,)
            if master in mods:
                cm = mods[master]
                b = {}
                for pn, e in conns.items():
                    if e is None:
                        continue
                    pbits = bits_of(m, e, scope)
                    cbits = width_bits(cm, pn)
                    n = min(len(pbits), len(cbits))
                    for cb, pb in zip(cbits[len(cbits) - n:], pbits[len(pbits) - n:]):
                        b[(pn, cb)] = pb
                walk(master, path, b)
                continue
            pins = []
            for pn, e in conns.items():
                if e is None:
                    continue
                bl = bits_of(m, e, scope)
                if len(bl) == 1:
                    pins.append((pn, bl[0]))
                else:
                    for j, bk in enumerate(reversed(bl)):  # LSB = index 0
                        pins.append(("%s[%d]" % (pn, j), bk))
            cells.append((path, master, params, pins))

    tm = mods[top]
    for p in tm.ports:
        for b in width_bits(tm, p):
            port_bits[((), p, b)] = "port:%s:%s%s" % (tm.dirs.get(p, "?"), p, "" if b is None else "[%d]" % b)
    walk(top, (), {})
    g = Graph()
    net_id = {}

    def nid(bk):
        r = uf.find(bk)
        if r not in net_id:
            net_id[r] = len(g.net_label)
            g.net_label.append(None)
            g.net_adj.append([])
            g.net_name.append(r)
        return net_id[r]

    labels_of_net = {}
    for bk, lab in port_bits.items():
        labels_of_net.setdefault(nid(bk), []).append(lab)
    for ci, (path, master, params, pins) in enumerate(cells):
        rc = rom_class_of(master, lef_sigs, rom_re)
        lab = rc if rc else master + ("" if not params else "#" + json.dumps(params, sort_keys=True))
        g.cell_name.append(".".join(path))
        g.cell_master.append(master)
        g.cell_label.append(stable_int("cell|" + lab))
        if rc:
            g.rom.append((ci, rc))
        adj = []
        for pn, bk in pins:
            n = nid(bk)
            p = stable_int("pin|" + pn)
            adj.append((p, n))
            g.net_adj[n].append((p, ci))
        g.cell_adj.append(adj)
    for n, r in enumerate(g.net_name):
        labs = sorted(labels_of_net.get(n, []))
        if r[0] == "const":
            labs.append("const:" + r[1])
        g.net_label[n] = stable_int("net|" + "|".join(labs))
    return g


# ------------------------------------------------------------------ isomorphism
MASK = (1 << 62) - 1


def refine_round(g, cc, nc):
    ncc = [hash((cc[i], sum(hash((p, nc[n])) & MASK for p, n in g.cell_adj[i]) & MASK, len(g.cell_adj[i]))) & MASK
           for i in range(len(cc))]
    nnc = [hash((nc[j], sum(hash((p, cc[c])) & MASK for p, c in g.net_adj[j]) & MASK, len(g.net_adj[j]))) & MASK
           for j in range(len(nc))]
    return ncc, nnc


def hist(cc, nc):
    return Counter(cc), Counter(nc)


def lockstep(ga, gb, ca, na, cb, nb, max_rounds=MAX_ROUNDS):
    """refine both until the partition of A stops growing; -> (ca, na, cb, nb, rounds, same) where same = histograms equal throughout"""
    rounds = 0
    ka = len(set(ca)) + len(set(na))
    while rounds < max_rounds:
        ca2, na2 = refine_round(ga, ca, na)
        cb2, nb2 = refine_round(gb, cb, nb)
        rounds += 1
        if hist(ca2, na2) != hist(cb2, nb2):
            return ca2, na2, cb2, nb2, rounds, False
        k2 = len(set(ca2)) + len(set(na2))
        ca, na, cb, nb = ca2, na2, cb2, nb2
        if k2 == ka:
            break
        ka = k2
    return ca, na, cb, nb, rounds, True


def canonical_hash(cc, nc):
    h = hashlib.sha256()
    for x in sorted(Counter(cc).items()):
        h.update(b"c%d:%d;" % x)
    for x in sorted(Counter(nc).items()):
        h.update(b"n%d:%d;" % x)
    return h.hexdigest()


def structural_hash(g, max_rounds=MAX_ROUNDS):
    cc, nc = list(g.cell_label), list(g.net_label)
    k = len(set(cc)) + len(set(nc))
    for r in range(max_rounds):
        cc, nc = refine_round(g, cc, nc)
        k2 = len(set(cc)) + len(set(nc))
        if k2 == k:
            break
        k = k2
    return canonical_hash(cc, nc), r + 1


def verify(ga, gb, cmap, nmap):
    """exact check of a bijection: labels and every (pin, net) of every cell"""
    if len(set(cmap.values())) != len(cmap) or len(cmap) != len(ga.cell_label) or len(gb.cell_label) != len(ga.cell_label):
        return "cell map is not a bijection"
    if len(set(nmap.values())) != len(nmap) or len(nmap) != len(ga.net_label) or len(gb.net_label) != len(ga.net_label):
        return "net map is not a bijection"
    for n, m in nmap.items():
        if ga.net_label[n] != gb.net_label[m]:
            return "net label differs (port / constant) at %s" % (ga.net_name[n],)
    for a, b in cmap.items():
        if ga.cell_label[a] != gb.cell_label[b]:
            return "cell label differs %s vs %s" % (ga.cell_name[a], gb.cell_name[b])
        if Counter((p, nmap[n]) for p, n in ga.cell_adj[a]) != Counter(gb.cell_adj[b]):
            return "connections differ at %s vs %s" % (ga.cell_name[a], gb.cell_name[b])
    return None


def isomorphism(ga, gb, max_rounds=MAX_ROUNDS, max_indiv=MAX_INDIV_ROUNDS):
    """-> dict(isomorphic, why, rounds, individualised, cmap, nmap, structural_hash)"""
    res = dict(isomorphic=False, why=None, rounds=0, individualised=0, cmap=None, nmap=None, structural_hash=None,
               cells=(len(ga.cell_label), len(gb.cell_label)), nets=(len(ga.net_label), len(gb.net_label)))
    if res["cells"][0] != res["cells"][1] or res["nets"][0] != res["nets"][1]:
        res["why"] = "cell / net counts differ %s %s" % (res["cells"], res["nets"])
        return res
    if hist(ga.cell_label, ga.net_label) != hist(gb.cell_label, gb.net_label):
        res["why"] = "cell masters / port labels differ (histogram)"
        return res
    ca, na, cb, nb, r, same = lockstep(ga, gb, list(ga.cell_label), list(ga.net_label), list(gb.cell_label), list(gb.net_label),
                                       max_rounds)
    res["rounds"] = r
    if not same:
        res["why"] = "colour refinement separates the graphs at round %d" % r
        return res
    res["structural_hash"] = canonical_hash(ca, na)
    fresh = 1 << 61
    while True:
        ga_cls, gb_cls = {}, {}
        for i, c in enumerate(ca):
            ga_cls.setdefault(c, []).append(i)
        for i, c in enumerate(cb):
            gb_cls.setdefault(c, []).append(i)
        na_cls, nb_cls = {}, {}
        for i, c in enumerate(na):
            na_cls.setdefault(c, []).append(i)
        for i, c in enumerate(nb):
            nb_cls.setdefault(c, []).append(i)
        multi = [c for c, v in ga_cls.items() if len(v) > 1]
        nmulti = [c for c, v in na_cls.items() if len(v) > 1]
        if not multi and not nmulti:
            break
        if res["individualised"] >= max_indiv:
            res["why"] = "symmetric classes left after %d individualisation rounds" % max_indiv
            return res
        res["individualised"] += 1
        ca, cb, na, nb = list(ca), list(cb), list(na), list(nb)
        for c in multi:                                  # one element per symmetric class, paired in order
            fresh += 1
            ca[ga_cls[c][0]] = fresh
            cb[gb_cls[c][0]] = fresh
        if not multi:
            for c in nmulti:
                fresh += 1
                na[na_cls[c][0]] = fresh
                nb[nb_cls[c][0]] = fresh
        ca, na, cb, nb, r, same = lockstep(ga, gb, ca, na, cb, nb, max_rounds)
        res["rounds"] += r
        if not same:
            res["why"] = "individualisation round %d separates the graphs (unproven, not a disproof)" % res["individualised"]
            return res
    pos_b = {c: i for i, c in enumerate(cb)}
    npos_b = {c: i for i, c in enumerate(nb)}
    cmap = {i: pos_b[c] for i, c in enumerate(ca)}
    nmap = {i: npos_b[c] for i, c in enumerate(na)}
    bad = verify(ga, gb, cmap, nmap)
    if bad:
        res["why"] = "exact check failed: " + bad
        return res
    res.update(isomorphic=True, cmap=cmap, nmap=nmap)
    return res


# ------------------------------------------------------------------ kit side
def kit_netlist(kit):
    """the synthesized netlist of a kit: run/results/asap7/*/base/1_2_yosys.v, else 1_synth.v"""
    for name in ("1_2_yosys.v", "1_synth.v"):
        c = sorted(Path(kit).glob("run/results/asap7/*/base/" + name))
        if c:
            return c[0]
    return None


def config_vars(kit):
    out = {}
    try:
        for ln in Path(kit, "config.mk").read_text().splitlines():
            m = re.match(r"^\s*(?:override\s+)?export\s+(\w+)\s*:?=\s*(.*)$", ln)
            if m:
                out[m.group(1)] = m.group(2).strip()
    except OSError:
        pass
    return out


def norm_names(text, names):
    for n in sorted(names, key=len, reverse=True):
        if n:
            text = text.replace(n, "<TYPE>")
    return text


def macro_places(kit):
    """{instance: (x, y, orient)} from the kit's macro placement Tcl (MACRO_PLACEMENT_TCL / *macro*place*.tcl), else {}"""
    out = {}
    cv = config_vars(kit)
    cands = [cv.get(k, "").replace("/work", str(kit)) for k in ("MACRO_PLACEMENT_TCL", "MACRO_PLACEMENT")]
    cands += [str(p) for p in Path(kit).glob("*macro*place*.tcl")]
    for c in cands:
        if not c or not os.path.isfile(c):
            continue
        for ln in Path(c).read_text(errors="replace").splitlines():
            inst = re.search(r"-(?:macro_name|inst_name)\s+\{?([^\s}]+)", ln)
            loc = re.search(r"-location\s+\{\s*([\d.]+)\s+([\d.]+)\s*\}", ln)
            ori = re.search(r"-orient(?:ation)?\s+(\S+)", ln)
            if inst and loc:
                out[inst.group(1).replace("\\", "")] = (float(loc.group(1)), float(loc.group(2)), ori.group(1) if ori else "R0")
        if out:
            break
    return out


def physical_match(km, kr, member, rep, cmap=None, gm=None, gr=None):
    """-> dict(ok, checks {name: PASS|FAIL|NOT RUN}, advisory [config differences], shas)"""
    km, kr = Path(km), Path(kr)
    chk, adv, shas = {}, [], {}

    def pins(k):
        try:
            rows = json.loads(Path(k, "pins.json").read_text())
            rows = rows.get("pins", rows) if isinstance(rows, dict) else rows
            return sorted(json.dumps(r, sort_keys=True) for r in rows)
        except (OSError, ValueError):
            return None
    pm, pr = pins(km), pins(kr)
    chk["pins"] = "NOT RUN" if pm is None or pr is None else ("PASS" if pm == pr else "FAIL")
    shas["pins"] = [sha256_file(km / "pins.json"), sha256_file(kr / "pins.json")]
    cm, cr = config_vars(km), config_vars(kr)
    chk["outline"] = "PASS" if (cm.get("DIE_AREA"), cm.get("CORE_AREA")) == (cr.get("DIE_AREA"), cr.get("CORE_AREA")) and cm.get("DIE_AREA") \
        else "FAIL"
    names = {member, rep, cm.get("DESIGN_NAME", ""), cr.get("DESIGN_NAME", ""), cm.get("DESIGN_NICKNAME", ""), cr.get("DESIGN_NICKNAME", "")}
    try:
        sm = norm_names(Path(km, "constraint.sdc").read_text(), names)
        sr = norm_names(Path(kr, "constraint.sdc").read_text(), names)
        chk["sdc"] = "PASS" if sm == sr else "FAIL"
    except OSError:
        chk["sdc"] = "NOT RUN"
    for k in sorted(set(cm) | set(cr)):
        if k in ("DESIGN_NAME", "DESIGN_NICKNAME", "VERILOG_FILES"):
            continue
        a, b = norm_names(cm.get(k, ""), names), norm_names(cr.get(k, ""), names)
        if a != b:
            adv.append("%s: %s | %s" % (k, a[:120], b[:120]))
    mm, mr = macro_places(km), macro_places(kr)
    if not mm and not mr:
        chk["macro_place"] = "NOT RUN"
    elif cmap is None or gm is None or gr is None:
        chk["macro_place"] = "NOT RUN"
    else:
        idx_m = {n: i for i, n in enumerate(gm.cell_name)}
        bad = []
        for inst, place in mm.items():
            i = idx_m.get(inst)
            other = gr.cell_name[cmap[i]] if i is not None and i in cmap else None
            if other is None or mr.get(other) != place:
                bad.append(inst)
        chk["macro_place"] = "PASS" if not bad and len(mm) == len(mr) else "FAIL"
        if bad:
            adv.append("macro placement differs at %s" % ", ".join(bad[:5]))
    ok = chk["pins"] == "PASS" and chk["outline"] == "PASS" and chk["sdc"] == "PASS" and chk["macro_place"] != "FAIL"
    return dict(ok=ok, checks=chk, advisory=adv, shas=shas)


def load_graph(netlist, lef_sigs, rom_re=ROM_RE_DEFAULT):
    return build(parse(Path(netlist).read_text(errors="replace")), lef_sigs=lef_sigs, rom_re=rom_re)


def prove(a):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "die_plan"))
    import signoff_profile as SP
    lef_sigs = lef_signatures(a.lef_dir)
    nm, nr = (Path(a.member_netlist) if a.member_netlist else kit_netlist(a.member_kit)), \
        (Path(a.rep_netlist) if a.rep_netlist else kit_netlist(a.rep_kit))
    blockers = []
    rec = dict(schema=SCHEMA, die=a.die, sibling=a.member, representative=a.rep, rule=RULE,
               generated=datetime.datetime.now().astimezone().isoformat(timespec="seconds"), host=os.uname().nodename,
               inputs=dict(member_kit=str(a.member_kit), rep_kit=str(a.rep_kit), member_netlist=str(nm), rep_netlist=str(nr),
                           member_netlist_sha=sha256_file(nm) if nm else None, rep_netlist_sha=sha256_file(nr) if nr else None,
                           lef_dirs=list(a.lef_dir or []), rom_re=a.rom_re))
    try:
        so = json.loads(Path(a.rep_signoff).read_text())
        j = SP.judge(so)
        rec["representative_signoff"] = dict(path=str(a.rep_signoff), sha256=sha256_file(a.rep_signoff), verdict=j["verdict"],
                                             gates=j["gates"], signed_period_ps=j.get("signed_period_ps"))
        if j["verdict"] != "SIGNED":
            blockers.append("representative sign-off does not pass R-MINIMAL: %s" % "; ".join(j["reasons"]))
    except (OSError, ValueError) as e:
        rec["representative_signoff"] = dict(path=str(a.rep_signoff), error=str(e))
        blockers.append("representative sign-off unreadable")
    if not nm or not nr or not nm.exists() or not nr.exists():
        blockers.append("synthesized netlist missing (member %s, representative %s)" % (nm, nr))
        rec.update(credit=False, credit_blockers=blockers, proof=dict(isomorphic=False, why="netlist missing"))
    else:
        gm, gr = load_graph(nm, lef_sigs, a.rom_re), load_graph(nr, lef_sigs, a.rom_re)
        iso = isomorphism(gm, gr)
        rom = []
        if iso["isomorphic"]:
            for ci, cls in gm.rom:
                rom.append([gm.cell_name[ci], gr.cell_name[iso["cmap"][ci]], cls, gm.cell_master[ci], gr.cell_master[iso["cmap"][ci]]])
        else:
            blockers.append("netlists not proven isomorphic: %s" % iso["why"])
        rec["proof"] = dict(isomorphic=iso["isomorphic"], why=iso["why"], structural_hash=iso["structural_hash"],
                            method="1-WL colour refinement in lock step + individualisation + exact bijection check (names not labels; "
                                   "top port names, masters, parameters, pins are labels; ROM macros by LEF size + pins)",
                            cells=iso["cells"][0], nets=iso["nets"][0], ports=sum(1 for x in gm.net_label if x),
                            rounds=iso["rounds"], individualised=iso["individualised"], rom_masked=rom)
        ph = physical_match(a.member_kit, a.rep_kit, a.member, a.rep, iso.get("cmap"), gm, gr)
        rec["physical"] = ph
        if not ph["ok"]:
            blockers.append("physical match: %s" % ", ".join("%s %s" % kv for kv in ph["checks"].items() if kv[1] == "FAIL") or "NOT RUN")
        rec["rom_views"] = dict(status="TO-GENERATE", rule="OWNER 11-19: ROMs carry real weights; generate the member's ROM views "
                                "(LEF/LIB/GDS, tools/mem_compiler/rom_gen.py personalise) for these instances; no P&R",
                                instances=[r[0] for r in rom])
        rec["credit"] = not blockers
        rec["credit_blockers"] = blockers
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(rec, indent=1) + "\n")
    print(json.dumps(dict(sibling=a.member, representative=a.rep, credit=rec["credit"], blockers=blockers,
                          hash=(rec.get("proof") or {}).get("structural_hash"))))
    return 0 if rec["credit"] else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    h = sub.add_parser("hash")
    h.add_argument("netlist")
    h.add_argument("--lef-dir", action="append")
    h.add_argument("--rom-re", default=ROM_RE_DEFAULT)
    p = sub.add_parser("prove")
    for k in ("--die", "--member", "--rep", "--member-kit", "--rep-kit", "--rep-signoff", "--out"):
        p.add_argument(k, required=True)
    p.add_argument("--member-netlist")
    p.add_argument("--rep-netlist")
    p.add_argument("--lef-dir", action="append")
    p.add_argument("--rom-re", default=ROM_RE_DEFAULT)
    a = ap.parse_args(argv)
    if a.cmd == "hash":
        g = load_graph(a.netlist, lef_signatures(a.lef_dir), a.rom_re)
        hh, r = structural_hash(g)
        print(json.dumps(dict(netlist=a.netlist, structural_hash=hh, rounds=r, cells=len(g.cell_label), nets=len(g.net_label),
                              rom=len(g.rom))))
        return 0
    return prove(a)


if __name__ == "__main__":
    sys.exit(main())
