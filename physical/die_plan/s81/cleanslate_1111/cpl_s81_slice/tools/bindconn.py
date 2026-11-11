#!/usr/bin/env python3
"""CPL-S81-SLICE: hard-core port connectivity from a flattened native *_bound.sv (bind.py output).

Union-find over net identifiers; glue / station / relay / landing instances are transparent (their data ports are
unioned; clock/reset/epoch-enable ports are not).  Endpoints: hard-core ports (plan cores), macro-owner soft blocks
(soft instances whose name prefixes fixed content macros) and module ports (face buses, epoch bit dropped).
usage: bindconn.py BOUND.sv OUT.json   (OUT: {endpoints: {comp: [...]}, ports: {inst: {port: [targets]}}})
"""
import json
import re
import sys
from collections import defaultdict

ID = re.compile(r"[A-Za-z_][A-Za-z0-9_$]*")
SKIP_PORT = re.compile(r"^(clk|ck|ck_.*|rst.*|arst.*|.*_clk|ea|clk_.*|WR_CLK|RD_CLK|fclk.*)$")
SKIP_ID = re.compile(r"^(clk.*|rst_n|arst_n|fclk.*|rst_.*|d\d+_.*_rst.*)$")


def ids(expr):
    expr = re.sub(r"\d+'[bdhoBDHO][0-9a-fA-FxXzZ_]+", " ", expr)
    expr = re.sub(r"\[[^\]]*\]", " ", expr)
    return [m.group(0) for m in ID.finditer(expr) if not SKIP_ID.match(m.group(0))]


def parse(txt):
    txt = re.sub(r"//[^\n]*", "", re.sub(r"/\*.*?\*/", "", txt, flags=re.S))
    m = re.search(r"\bmodule\s+(\w+)\s*(#\s*\(.*?\)\s*)?\((.*?)\);", txt, flags=re.S)
    ports = {}
    for pm in re.finditer(r"(input|output|inout)\s+wire\s*(\[(\d+):(\d+)\])?\s*(\w+)", m.group(3)):
        ports[pm.group(5)] = (pm.group(1), int(pm.group(3)) - int(pm.group(4)) + 1 if pm.group(2) else 1)
    body = txt[m.end():]
    assigns = [(a.group(1), a.group(2)) for a in re.finditer(r"\bassign\s+(.*?)\s*=\s*(.*?);", body, flags=re.S)]
    insts = []
    i = 0
    hdr = re.compile(r"\n\s*([A-Za-z_]\w*)\s*(#\s*\()?")
    kw = {"assign", "wire", "reg", "logic", "input", "output", "always", "if", "else", "end", "begin", "endmodule",
          "localparam", "parameter", "genvar", "generate", "endgenerate", "for", "initial", "function", "integer"}
    while True:
        mm = hdr.search(body, i)
        if not mm:
            break
        typ = mm.group(1)
        j = mm.end()
        if typ in kw:
            i = j
            continue
        if mm.group(2):           # skip #( ... ) with nesting
            d = 1
            while d and j < len(body):
                d += {"(": 1, ")": -1}.get(body[j], 0)
                j += 1
        nm = re.match(r"\s*([A-Za-z_]\w*)\s*\(", body[j:])
        if not nm:
            i = mm.end()
            continue
        name = nm.group(1)
        k = j + nm.end()
        d = 1
        s = k
        while d and k < len(body):
            d += {"(": 1, ")": -1}.get(body[k], 0)
            k += 1
        conns = {}
        for pc in re.finditer(r"\.(\w+)\s*\(", body[s:k - 1]):
            a = s + pc.end()
            dd, b = 1, a
            while dd and b < k:
                dd += {"(": 1, ")": -1}.get(body[b], 0)
                b += 1
            conns[pc.group(1)] = body[a:b - 1]
        insts.append((typ, name, conns))
        i = k
    return ports, assigns, insts


class UF:
    def __init__(self):
        self.p = {}

    def f(self, x):
        self.p.setdefault(x, x)
        while self.p[x] != x:
            self.p[x] = self.p[self.p[x]]
            x = self.p[x]
        return x

    def u(self, a, b):
        a, b = self.f(a), self.f(b)
        if a != b:
            self.p[a] = b


PASS = re.compile(r"^ot_dp_(st|rrelay|rrelay_nl|dly|landing_collect)$")
PURE = re.compile(r"^[\s{}\[\]:,0-9A-Za-z_$']*$")


def build(bound_txt, hard_modules, macro_owner_names):
    ports, assigns, insts = parse(bound_txt)
    uf = UF()
    for l, r in assigns:
        li = ids(l)
        for x in li:
            uf.f(x)
            if PURE.match(r):
                for y in ids(r):
                    uf.u(x, y)
    ends = defaultdict(set)     # comp -> endpoints
    hard_ports = []
    for typ, name, conns in insts:
        if not PASS.match(typ):
            kind = "core" if typ in hard_modules else ("macro" if name in macro_owner_names else "soft")
            for p, e in conns.items():
                if SKIP_PORT.match(p):
                    continue
                for x in ids(e):
                    ends[uf.f(x)]  # touch
                    hard_ports.append((kind, name, p, x))
        else:
            dp = [x for p, e in conns.items() if not SKIP_PORT.match(p) for x in ids(e)]
            for x in dp[1:]:
                uf.u(dp[0], x)
    for p in ports:
        if p in ("clk", "arst_n") or p.startswith("rst_") or p.startswith("fclk"):
            continue
        uf.f(p)
    comp = defaultdict(set)
    for kind, name, p, x in hard_ports:
        comp[uf.f(x)].add((kind, name, p))
    for p in ports:
        if p in uf.p:
            comp[uf.f(p)].add(("face", p, ""))
    out = defaultdict(lambda: defaultdict(set))
    soft = defaultdict(lambda: defaultdict(set))   # soft inst -> endpoint -> ports
    for c, es in comp.items():
        for e in es:
            if e[0] == "soft":
                for o in es:
                    if o[0] in ("core", "face", "macro"):
                        soft[e[1]]["%s:%s%s" % (o[0], o[1], ("." + o[2]) if o[2] else "")].add(e[2])
    for c, es in comp.items():
        for e in es:
            if e[0] == "core":
                for o in es:
                    if o != e and not (o[0] == "core" and o[1] == e[1]) and o[0] != "soft":
                        out[e[1]][e[2]].add("%s:%s%s" % (o[0], o[1], ("." + o[2]) if o[2] else ""))
                    elif o[0] == "soft":
                        out[e[1]][e[2]].add("soft:%s" % o[1])
    return {k: {p: sorted(v) for p, v in d.items()} for k, d in out.items()}, \
        {nm: typ for typ, nm, _ in insts if typ in hard_modules}


if __name__ == "__main__":
    txt = open(sys.argv[1]).read()
    hm = set(sys.argv[3].split(","))
    mo = set(sys.argv[4].split(",")) if len(sys.argv) > 4 else set()
    res, names = build(txt, hm, mo)
    json.dump({"ports": res, "insts": names}, open(sys.argv[2], "w"), indent=1)
    for k, d in res.items():
        print(k, names.get(k), {p: v[:4] for p, v in list(d.items())[:12]})
