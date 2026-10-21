#!/usr/bin/env python3
"""S81-SLICE3-LEPENH 10-19: write a die_port_bind-readable netlist form of a wires-only (or lp.py landed) parent.
tools/die_port_bind.py reads one declaration per statement line with literal ranges; the lp.py output packs several
statements per line, comma-lists of wires, arithmetic ranges and MUT ternaries.  This keeps every instance, port and
connection and only re-prints them: non-ANSI ports, one port / wire per line, ranges evaluated, bench-only MUT selects resolved at MUT 0.
    bind_form.py IN.sv TOP OUT.v
"""
import re, sys
src, top, out = sys.argv[1:4]
t = open(src).read()
t = re.sub(r"/\*.*?\*/", " ", t, flags=re.S)
t = re.sub(r"//[^\n]*", "", t)
m = re.search(r"\bmodule\s+%s\b(.*?)\bendmodule" % re.escape(top), t, re.S)
body = m.group(1)
hdr_end = body.index(");")
hdr, rest = body[:hdr_end], body[hdr_end + 2:]
hdr = re.sub(r"#\s*\(\s*parameter[^)]*\)", "", hdr, count=1).strip().lstrip("(")
MUT = 0
# S81-LEPENH2 10-20: lp.py chunked / reset-forest parents declare localparams (LPR_LEAVES_<r>) and index leaf vectors with
# [(a) +: (b)]: evaluate both to literal ranges (integer arithmetic) so die_port_bind sees plain [hi:lo] selects.
ENV = {"MUT": MUT}
def ival(x):
    return int(eval(re.sub(r"(?<![/])/(?![/])", "//", x), dict(ENV)))
for lp_ in re.finditer(r"\blocalparam\s+(?:integer\s+)?(\w+)\s*=\s*([^;]+);", rest):
    ENV[lp_.group(1)] = ival(lp_.group(2))
rest = re.sub(r"\blocalparam\s+[^;]*;", "", rest)
def plusc(s):   # name[(a) +: (b)] -> name[a+b-1:a]
    pat = re.compile(r"\[([^\[\]]*?)\+:([^\[\]]*)\]")
    def one(m):
        lo, n = ival(m.group(1)), ival(m.group(2))
        return f"[{lo + n - 1}:{lo}]"
    return pat.sub(one, s)
def ev(x):
    return str(int(eval(x.replace("MUT", str(MUT)).replace("?", " if ").replace(":", " else ") if False else x, {"MUT": MUT})))
def rng(r):
    a, b = r[1:-1].split(":", 1) if r.count(":") == 1 else (None, None)
    return f"[{ival(a)}:{ival(b)}]"
def tern(s):   # (MUT == k) ? a : b  -> pick at MUT 0
    pat = re.compile(r"\(\s*MUT\s*==\s*(\d+)\s*\)\s*\?\s*([^:,()]+?)\s*:\s*([^,;()]+)")
    while True:
        n = pat.search(s)
        if not n:
            return s
        s = s[:n.start()] + (n.group(2) if int(n.group(1)) == MUT else n.group(3)).strip() + s[n.end():]
def evparams(s):   # .NAME(<arithmetic>) inside #( ... ): evaluate balanced-paren integer expressions
    out, i = "", 0
    for mm in re.finditer(r"\.(\w+)\(", s):
        pass
    k = s.find("#(")
    if k < 0:
        return s
    depth, j = 0, k + 1
    while True:
        depth += s[j] == "("; depth -= s[j] == ")"
        if depth == 0:
            break
        j += 1
    inner = s[k + 2:j]
    def one(seg):
        n = re.match(r"\s*\.(\w+)\((.*)\)\s*$", seg, re.S)
        try:
            return f".{n.group(1)}({ival(n.group(2))})"
        except Exception:
            return seg.strip()
    segs, d, cur = [], 0, ""
    for ch in inner:
        if ch == "," and d == 0:
            segs.append(cur); cur = ""; continue
        d += ch == "("; d -= ch == ")"; cur += ch
    segs.append(cur)
    return s[:k] + "#(" + ", ".join(one(x) for x in segs) + ")" + s[j + 1:]
ports = []
cur = None
for tok in [x.strip() for x in hdr.split(",") if x.strip()]:
    mm = re.match(r"(input|output|inout)\s+(?:wire\s+|reg\s+|logic\s+)?(\[[^\]]+\])?\s*(\w+)$", tok)
    if mm:
        cur = (mm.group(1), rng(mm.group(2)) if mm.group(2) else "")
        ports.append((cur[0], cur[1], mm.group(3)))
    else:
        ports.append((cur[0], cur[1], tok))
# non-ANSI (die netlist style): header names only, port declarations in the body
L = [f"module {top} (" + ", ".join(n for _, _, n in ports) + ");"]
L += [f"    {d} {r + ' ' if r else ''}{n};" for d, r, n in ports]
for st in [s.strip() for s in rest.split(";") if s.strip()]:
    st = re.sub(r"\s+", " ", st)
    w = re.match(r"wire\s*(\[[^\]]*\])?\s*(.*)$", st)
    if w and "=" in w.group(2):     # wire x = expr  ->  wire x; assign x = expr (folded below)
        r = rng(w.group(1)) + " " if w.group(1) else ""
        nm, ex = w.group(2).split("=", 1)
        L.append(f"    wire {r}{nm.strip()};")
        L.append(f"    assign {nm.strip()} = {plusc(ex.strip())};")
        continue
    if w:
        r = rng(w.group(1)) + " " if w.group(1) else ""
        for n in w.group(2).split(","):
            L.append(f"    wire {r}{n.strip()};")
        continue
    st = tern(st)
    st = evparams(st)
    st = plusc(st)
    L.append(f"    {st};")
# assigns are not drivers in die_port_bind: fold them into the instance connections
outs = {n for d, _, n in ports if d == "output"}
wid = {}
for l in L:
    w = re.match(r"\s*(?:wire|input|output)\s*(?:\[(\d+):(\d+)\])?\s*(\w+);", l)
    if w:
        wid[w.group(3)] = int(w.group(1)) - int(w.group(2)) + 1 if w.group(1) else 1
sub, drop = {}, set()
for l in L:
    a = re.match(r"\s*assign\s+(\w+)\s*=\s*(.*);$", l)
    if not a:
        continue
    lhs, rhs = a.group(1), a.group(2).strip()
    if lhs in outs:          # out = {x1, x0}: each 1-bit wire xi becomes out[i]
        parts = [x.strip() for x in rhs.strip("{}").split(",")]
        assert all(re.fullmatch(r"\w+", x) and wid.get(x) == 1 for x in parts), l
        for i, x in enumerate(reversed(parts)):
            sub[x] = f"{lhs}[{i}]"; drop.add(x)
    else:                    # internal alias / concatenation: the reader takes the expression itself
        sub[lhs] = rhs; drop.add(lhs)
    drop.add(l)
def rep(l):
    for k, v in sub.items():
        l = re.sub(r"\(%s\)" % re.escape(k), "(" + v + ")", l)
        # S81-SLICERTL 10-20: an alias of a plain net is also read through part-selects (lp.py landed reads:
        # .c_d(dn_l0__l_L0[592:433]) with assign dn_l0__l_L0 = lpl_0_o): select the aliased net itself
        if re.fullmatch(r"\w+", v):
            l = re.sub(r"\(%s\[" % re.escape(k), "(" + v + "[", l)
    return l
L = [rep(l) for l in L if l not in drop and not re.match(r"\s*wire\s*(?:\[[^\]]*\])?\s*(%s);" % "|".join(map(re.escape, drop - set(L)) or ["$^"]), l)]
L.append("endmodule")
open(out, "w").write("\n".join(L) + "\n")
print(f"bind_form {top}: {len(ports)} ports, {len(L)} lines -> {out}")
