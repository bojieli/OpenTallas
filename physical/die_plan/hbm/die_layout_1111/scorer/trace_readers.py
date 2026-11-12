#!/usr/bin/env python3
"""DIE-LAYOUT-HBM 11-11: who consumes (in bus) / produces (out bus) each bit range of a bank bus.
usage: trace_readers.py PLAN RTLDIR TYPE BUS [maxdepth]  -> one JSON line per first-hop signal
In bus: first-hop readers of the last bound stage q of <bus>, then a word-level forward BFS through soft logic
(assign / always / soft instances such as ot_dp_dly pads, relays) to hard-core instance inputs.
Out bus: the u_bout_<bus> .d concatenation items (MSB first), then a backward BFS to hard-core outputs.
Per first-hop signal: bit runs, the hard cores reached at the minimal depth, their planned centres and centroid."""
import json
import re
import sys
from collections import defaultdict, deque

ID = re.compile(r"\b([A-Za-z_][A-Za-z0-9_$]*)\b")
KW = {"assign", "always", "posedge", "negedge", "or", "if", "else", "begin", "end", "clk", "rst_n", "wire", "reg",
      "logic", "input", "output", "module", "endmodule"}
INST_START = re.compile(r"^\s*([A-Za-z_]\w*)\s+(?:#\(.*\)\s+)?(u_\w+)\s*\(\s*$")
INST_ONE = re.compile(r"^\s*([A-Za-z_]\w*)\s+(?:#\(.*?\)\s+)?(u_\w+)\s*\((.*)\);\s*$")
PORT = re.compile(r"^\s*\.(\w+)\((.*)\)\s*,?\s*$")
OUTP = re.compile(r"^(q|eq|Q|y|Y|o|z)$|_out$|^rst_n_o")


def ids(expr):
    expr = re.sub(r"\d+'[bhdo][0-9a-fA-F_xzXZ]+", " ", expr)
    return [m for m in ID.findall(expr) if m not in KW]


def ports_one(body):
    out, i = [], 0
    while True:
        m = re.compile(r"\.(\w+)\(").search(body, i)
        if not m:
            return out
        d, j = 1, m.end()
        while j < len(body) and d:
            d += {"(": 1, ")": -1}.get(body[j], 0)
            j += 1
        out.append((m.group(1), body[m.end():j - 1]))
        i = j


class G:
    def __init__(self, txt):
        self.fwd, self.bwd = defaultdict(set), defaultdict(set)
        self.inst_mod, self.inst_in, self.inst_out = {}, defaultdict(set), defaultdict(set)
        cur = None
        for ln in txt.split("\n"):
            code = ln.split("//")[0]
            m = INST_ONE.match(code)
            if m and not cur:
                inst = m.group(2)
                self.inst_mod[inst] = m.group(1)
                for p, e in ports_one(m.group(3)):
                    self._pin(inst, p, e, own=bool(OUTP.search(p)))
                continue
            m = INST_START.match(code)
            if m:
                cur = m.group(2)
                self.inst_mod[cur] = m.group(1)
                continue
            if cur:
                if re.match(r"^\s*\);", code):
                    cur = None
                    continue
                p = PORT.match(code)
                if p:
                    e = ids(p.group(2))
                    own = any(s.startswith("w_" + cur[2:] + "_") or s.startswith("w_" + cur + "_") for s in e)
                    self._pin(cur, p.group(1), p.group(2), own=own or bool(OUTP.search(p.group(1))))
                continue
            if "<=" in code:
                pre, rhs = code.rsplit("<=", 1)
                lhs = ids(pre.split("else")[-1].split(")")[-1])
                rhs_ids = ids(rhs) + (ids(pre.split("else")[0].split("if", 1)[-1]) if "if" in pre else [])
            elif code.strip().startswith("assign") and "=" in code:
                l, rhs = code.strip()[6:].split("=", 1)
                lhs, rhs_ids = ids(l), ids(rhs)
            else:
                continue
            for a in lhs[:1]:
                for s in rhs_ids:
                    if s != a:
                        self.fwd[s].add(a)
                        self.bwd[a].add(s)

    def _pin(self, inst, port, expr, own):
        for s in ids(expr):
            if own:
                self.inst_out[inst].add(s)
                self.bwd[s].add(("I", inst))
            else:
                self.inst_in[inst].add(s)
                self.fwd[s].add(("I", inst))

    def bfs(self, start, hard, maxd, forward=True):
        nxt = self.fwd if forward else self.bwd
        seen, dq, hits = {start}, deque([(start, 0)]), {}
        if isinstance(start, tuple):
            dq = deque([(w, 1) for w in (self.inst_out if forward else self.inst_in)[start[1]]])
        while dq:
            s, d = dq.popleft()
            if d >= maxd:
                continue
            for n in nxt.get(s, ()):
                if isinstance(n, tuple):
                    if n[1] in hard:
                        hits[n[1]] = min(hits.get(n[1], 99), d + 1)
                        continue
                    if n in seen:
                        continue
                    seen.add(n)
                    for w in (self.inst_out if forward else self.inst_in)[n[1]]:
                        if w not in seen:
                            seen.add(w)
                            dq.append((w, d + 1))
                elif n not in seen:
                    seen.add(n)
                    dq.append((n, d + 1))
        return hits


def norm(x):
    return re.sub(r"_+", "_", x.replace(".", "_"))


def hard_sites(t, g):
    cen = {}
    for h in t["hard_cores"]:
        k = norm(re.sub(r"__r[ab]$", "", h["inst"]))
        cen.setdefault(k, []).append((h["origin_um"][0] + h["outline_um"][0] / 2, h["origin_um"][1] + h["outline_um"][1] / 2))
    hard = {}
    for i in g.inst_mod:
        k = norm(i[2:])
        if k in cen:
            pts = cen[k]
            hard[i] = (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts))
    return hard


def runs_of(bits):
    out = []
    for x in sorted(b for b in bits if b >= 0):
        if out and out[-1][1] == x - 1:
            out[-1][1] = x
        else:
            out.append([x, x])
    return out


def first_hop_in(txt, q):
    qre = re.compile(rf"\b{re.escape(q)}\b(?:\[(\d+)(?::(\d+))?\])?")
    out, cur = defaultdict(set), None
    for ln in txt.split("\n"):
        code = ln.split("//")[0]
        if re.match(r"^\s*(wire|reg)\b", code):
            continue
        m1 = INST_ONE.match(code)
        m = INST_START.match(code)
        if m:
            cur = m.group(2)
            continue
        if cur and re.match(r"^\s*\);", code):
            cur = None
            continue
        refs = list(qre.finditer(code))
        if not refs:
            continue
        if m1 and not cur:
            key = ("I", m1.group(2))
        elif cur:
            key = ("I", cur)
        elif "<=" in code:
            k = ids(code.rsplit("<=", 1)[0].split("else")[-1].split(")")[-1])[:1]
            key = k[0] if k else "?"
            if "negedge" in code and not k:
                key = "?async"
        elif code.strip().startswith("assign"):
            k = ids(code.strip()[6:].split("=", 1)[0])[:1]
            key = k[0] if k else "?"
        else:
            key = "?" + code.strip()[:30]
        for r in refs:
            if r.group(1) is None:
                out[key].add(-1)
                continue
            hi, lo = int(r.group(1)), int(r.group(2) if r.group(2) is not None else r.group(1))
            out[key].update(range(min(hi, lo), max(hi, lo) + 1))
    return out


def trace(plan_t, txt, bus, maxd=14):
    g = G(txt)
    hard = hard_sites(plan_t, g)
    b = next(x for x in plan_t["buses"] if x["name"] == bus)
    res = []
    if b["dir"] == "in":
        cands = sorted(set(re.findall(rf"\b({re.escape(bus)}(?:_p\d+|_is\d+)?_q)\b", txt)))
        q = f"{bus}_q" if f"{bus}_q" in cands and len(cands) == 1 else cands[-1]
        for key, bits in first_hop_in(txt, q).items():
            if isinstance(key, tuple):
                hits = {key[1]: 0} if key[1] in hard else g.bfs(key, hard, maxd, True)
            else:
                hits = g.bfs(key, hard, maxd, True) if not key.startswith("?") else {}
            res.append((key, bits, hits))
    else:
        m = re.search(rf"u_bout_{re.escape(bus)}\s*\(.*?\.d\((\{{.*?\}}|[^,]*)\),\s*\.ea", txt, re.S)
        items = [s.strip() for s in m.group(1).strip("{}").split(",")] if m else []
        decl = {d.group(3): int(d.group(1)) - int(d.group(2)) + 1 if d.group(1) else 1
                for d in re.finditer(r"^\s*(?:wire|reg)\s*(?:\[(\d+):(\d+)\])?\s*(\w+)\s*;", txt, re.M)}
        W = sum(1 for _ in [])
        widths = []
        for it in items:
            im = re.match(r"^(\w+)(?:\[(\d+)(?::(\d+))?\])?$", it)
            if not im:
                widths.append((it, None))
                continue
            w = decl.get(im.group(1), 1) if im.group(2) is None else abs(int(im.group(2)) - int(im.group(3) or im.group(2))) + 1
            widths.append((im.group(1), w))
        pos = sum(w or 0 for _, w in widths)
        for s, w in widths:
            bits = set(range(pos - (w or 0), pos))
            pos -= (w or 0)
            res.append((s, bits, g.bfs(s, hard, maxd, False) if w else {}))
    out = []
    for key, bits, hits in res:
        dmin = min(hits.values()) if hits else None
        near = sorted(k for k, d in hits.items() if d == dmin) if hits else []
        c = None
        if near:
            c = (round(sum(hard[k][0] for k in near) / len(near), 2), round(sum(hard[k][1] for k in near) / len(near), 2))
        out.append(dict(sig=key if isinstance(key, str) else key[1], nbits=len([x for x in bits if x >= 0]),
                        runs=runs_of(bits), depth=dmin, cores=near, centroid=c, reach_all=len(hits),
                        all_hits=sorted(hits.items(), key=lambda kv: kv[1])))
    return out, hard


def main(argv):
    plan, rtldir, tn, bus = argv[:4]
    maxd = int(argv[4]) if len(argv) > 4 else 14
    t = json.load(open(plan))["partition_types"][tn]
    out, _ = trace(t, open(f"{rtldir}/hbm_arch_{tn}.sv").read(), bus, maxd)
    for o in sorted(out, key=lambda o: o["runs"][0][0] if o["runs"] else -1):
        o = dict(o)
        o.pop("all_hits")
        o["runs"] = o["runs"][:5]
        o["cores"] = o["cores"][:3] + (["+%d" % (len(o["cores"]) - 3)] if len(o["cores"]) > 3 else [])
        print(json.dumps(o))


if __name__ == "__main__":
    main(sys.argv[1:])
