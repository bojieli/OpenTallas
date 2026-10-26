#!/usr/bin/env python3
"""S81-KITS-RTLC 10-24: count the pass-through stations (+1 cycle each in RTLC) on every path inside a frame band.
For each band module (col_h{9,10}_l4_lp_r0/r1/r2[_nx]) build a bit-level net graph: assigns are bitwise edges, relay /
pad / seam / station instances pass every input bit to every output bit (an instance node; a STATION node weighs 1),
any other child (ROM, element, node, cfg seq, cfifo, reset sync, landing forest) is a path start.  Clock / reset pins
are ignored.  Prints, per band output port bit range (grouped by the field it is assigned from), the max station count
on a path ending there, as JSON."""
import json, re, subprocess, sys, collections
sys.setrecursionlimit(1000000)
ROOT = sys.argv[1]; OUT = sys.argv[2]
sys.path.insert(0, ROOT + "/tools")
import die_port_bind as B
STATIONS = {"dsfd_qbank_N", "dsfd_qbank_S", "dsfd_rstg", "ot_s81_sstn_payload536", "ot_s81_sstn_base566"}
# per-output input sets of the stations (their RTL is bitwise per port; base566's status so reads e0/e1/c0/c1/si/nf)
SMAP = {"dsfd_qbank_N": {"d_r0": ["e_r0"], "d_r1": ["e_r1"], "d_st": ["e_st"]},
        "dsfd_qbank_S": {"o_cfg": ["i_cfg"], "o_go": ["i_go"], "o_x0": ["i_x0"], "o_x1": ["i_x1"]},
        "ot_s81_sstn_base566": {"cc": ["cci"], "xa": ["xai"], "xb": ["xbi"], "so": ["e0", "e1", "c0", "c1", "si", "nf"]}}
PASS_RE = re.compile(r"^(dsfd_rly_\w+|ot_pl_pad|ot_pl_seam_\w+|ot_s81_rly(_k)?|ot_pl_land\w*_[wr]|ot_pl_land_n32\w*)$")
CLKRST = re.compile(r"^(clk|ck|ck_\w+|rs|rst|rst_n|rn|rsi|rse|rs_\w*|lk|ck_o)$")
dirs_cache = {}
def port_dirs(mod):
    if mod in dirs_cache: return dirs_cache[mod]
    fs = subprocess.run(["grep", "-rlE", r"^\s*module\s+%s\b" % mod, ROOT + "/rtl"], capture_output=True, text=True).stdout.split()
    d = None
    for f in fs:
        for m in B.parse_modules(open(f).read(), f):
            if m.name == mod:
                d = {p: m.ports[p][0] for p in m.order}; break
        if d: break
    dirs_cache[mod] = d
    return d
def split_top(s, sep=","):
    out, dep, cur = [], 0, ""
    for ch in s:
        if ch in "({[": dep += 1
        if ch in ")}]": dep -= 1
        if ch == sep and dep == 0: out.append(cur); cur = ""
        else: cur += ch
    if cur.strip(): out.append(cur)
    return [x.strip() for x in out]
def bits(expr, widths):
    expr = expr.strip()
    if expr.startswith("{") and expr.endswith("}"):
        inner = expr[1:-1].strip()
        m = re.match(r"^(\d+)\s*\{(.*)\}$", inner, re.S)
        if m: return bits("{" + m.group(2) + "}", widths) * int(m.group(1))
        r = []
        for p in split_top(inner): r += bits(p, widths)
        return r
    if re.match(r"^\d*'[bhd]", expr) or re.match(r"^\d+$", expr): return [None] * 1   # constant: width unknown, ignored
    m = re.match(r"^([\w$]+)\s*\[(\d+)\s*:\s*(\d+)\]$", expr)
    if m:
        hi, lo = int(m.group(2)), int(m.group(3)); return ["%s[%d]" % (m.group(1), i) for i in range(hi, lo - 1, -1)]
    m = re.match(r"^([\w$]+)\s*\[(\d+)\]$", expr)
    if m: return ["%s[%s]" % (m.group(1), m.group(2))]
    m = re.match(r"^([\w$]+)$", expr)
    if m:
        n = m.group(1); w = widths.get(n)
        if w is None: return [n]
        hi, lo = w; return ["%s[%d]" % (n, i) for i in range(hi, lo - 1, -1)]
    return []   # expression (logic): ignored
def analyse(text, top):
    m = re.search(r"\bmodule\s+%s\b(.*?)\bendmodule\b" % re.escape(top), text, re.S)
    body = re.sub(r"//[^\n]*", "", m.group(1))
    body = re.sub(r"/\*.*?\*/", "", body, flags=re.S)
    widths = {}
    for mm in re.finditer(r"\b(input|output|wire|reg)\s+(?:wire\s+|reg\s+)?(?:\[(\d+)\s*:\s*(\d+)\]\s*)?([\w$]+)", body):
        if mm.group(2): widths[mm.group(4)] = (int(mm.group(2)), int(mm.group(3)))
    ports_out = [mm.group(2) for mm in re.finditer(r"\boutput\s+wire\s+(\[[^\]]*\]\s*)?([\w$]+)", body)]
    ports_in = [mm.group(2) for mm in re.finditer(r"\binput\s+wire\s+(\[[^\]]*\]\s*)?([\w$]+)", body)]
    drv = collections.defaultdict(list)    # bit -> list of (node) drivers
    inst_in = collections.defaultdict(list); inst_w = {}; inst_type = {}
    # statements
    for st in body.split(";"):
        s = st.strip()
        if s.startswith("assign "):
            mm = re.match(r"assign\s+(.*?)\s*=\s*(.*)$", s, re.S)
            if not mm: continue
            L, R = bits(mm.group(1), widths), bits(mm.group(2), widths)
            if len(L) == len(R):
                for a, b in zip(L, R):
                    if a and b: drv[a].append(("n", b))
            continue
        mm = re.match(r"^([A-Za-z_]\w*)\s*", s)
        if not mm or mm.group(1) in ("module", "wire", "reg", "input", "output", "localparam", "parameter", "assign", "always", "genvar", "integer"):
            continue
        typ = mm.group(1); k = mm.end()
        if s[k:k + 1] == "#":
            k = s.index("(", k); dep = 0
            while True:
                dep += {"(": 1, ")": -1}.get(s[k], 0); k += 1
                if dep == 0: break
        m2 = re.match(r"\s*([A-Za-z_][\w$]*)\s*\((.*)\)$", s[k:], re.S)
        if not m2: continue
        inst, conns = m2.group(1), m2.group(2)
        d = port_dirs(typ)
        if d is None:
            print("WARN no definition for", typ, file=sys.stderr); continue
        passing = typ in STATIONS or bool(PASS_RE.match(typ))
        sm = SMAP.get(typ)
        for c in split_top(conns):
            pm = re.match(r"^\.([\w$]+)\s*\((.*)\)$", c, re.S)
            if not pm: continue
            p, e = pm.group(1), pm.group(2)
            if CLKRST.match(p) or not e.strip(): continue
            bl = [b for b in bits(e, widths) if b]
            if d.get(p) == "output":
                key = inst + ("/" + p if sm else "")
                inst_type[key] = typ
                for b in bl: drv[b].append(("i", key) if passing else ("src", inst))
            elif d.get(p) == "input" and passing:
                if sm:
                    for o, ins in sm.items():
                        if p in ins: inst_in[inst + "/" + o] += bl
                else:
                    inst_in[inst] += bl
    memo = {}
    def cnt_bit(b, stack):
        if b in memo: return memo[b]
        if b in stack: return 0
        stack.add(b)
        v = 0
        for k, x in drv.get(b, []):
            if k == "n": v = max(v, cnt_bit(x, stack))
            elif k == "i": v = max(v, cnt_inst(x, stack))
        stack.discard(b); memo[b] = v; return v
    imemo = {}
    def cnt_inst(i, stack):
        if i in imemo: return imemo[i]
        v = max([cnt_bit(b, stack) for b in set(inst_in[i])] or [0]) + (1 if inst_type[i] in STATIONS else 0)
        imemo[i] = v; return v
    res = {}
    for p in ports_out:
        w = widths.get(p, (0, 0)); res[p] = [cnt_bit("%s[%d]" % (p, i), set()) for i in range(w[1], w[0] + 1)]
    # field map: assign <port>[hi:lo] = <field>;
    fields = {}
    for mm in re.finditer(r"assign\s+(\w+)\[(\d+):(\d+)\]\s*=\s*(\w+)\s*;", body):
        if mm.group(1) in res: fields.setdefault(mm.group(1), []).append((mm.group(4), int(mm.group(3)), int(mm.group(2))))
    for mm in re.finditer(r"assign\s+(\w+)\[(\d+)\]\s*=\s*(\w+)\s*;", body):
        if mm.group(1) in res: fields.setdefault(mm.group(1), []).append((mm.group(3), int(mm.group(2)), int(mm.group(2))))
    out = {}
    for p, v in res.items():
        fl = sorted(fields.get(p, [(p, 0, len(v) - 1)]), key=lambda x: x[1])
        out[p] = {"max": max(v) if v else 0,
                  "fields": {f: dict(bits="%d:%d" % (hi, lo), max=max(v[lo:hi + 1]), min=min(v[lo:hi + 1])) for f, lo, hi in fl}}
    return out
R = {}
for h in ("h9", "h10"):
    f = "%s/rtl/dsrom_sys/s81_dv/frame_lp/plan/col_%s_l4_lp_plan.sv" % (ROOT, h)
    text = open(f).read()
    for top in re.findall(r"\bmodule\s+(col_%s_l4_lp_r\w+)" % h, text):
        R[top] = analyse(text, top)
        print(top, {p: v["max"] for p, v in R[top].items()}, file=sys.stderr)
json.dump(R, open(OUT, "w"), indent=1)
