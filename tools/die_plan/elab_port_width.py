#!/usr/bin/env python3
"""elab_port_width.py -- ELAB-PORT-WIDTH (COORD 11-24 18:0x, S81-SVC-TIED): report only.

Why: slang's empty-blackbox importer reuses the FIRST instance's port ABI for a parameterized leaf that is not in
asbuilt.slang_parameterized_blackboxes.  In the c8 svc elab 848 ot_hdc_v41x_kreg + 64 ot_hdc_v41x_dly cells were bound
at the wrong width (kreg W=576 connected 1 bit) and the bind tied the rest to 0.  svc_width_gate checks only its listed
svc modules, so it did not see it.

This check reads the ELABORATED netlist (Yosys JSON, OUT/asbuilt.json) and, for every cell of every module whose type
is a design module (not a $-primitive), compares each connected port's width with the master's DECLARED width under
that cell's own parameters:

  * leaf (blackbox) masters with a source declaration (OUT/asbuilt_lib_stubs.sv, or --src files): the port ranges of
    the declaration are evaluated with the master's parameter defaults, overridden by the type module's
    parameter_default_values and the cell's parameters (yosys / slang / bind_slang_abi restore all land there);
  * elaborated (body) masters: the port widths of the elaborated module in the netlist;
  * blackbox masters with no source declaration: the netlist module's ports (a parameterized one is UNRESOLVED).

Findings (lines are report-only, never a failure):
  WARN ELAB-PORT-WIDTH <master> cells=<bad>/<all> inst=<bad>/<all> ports=<p:decl/conn,...> [listed] e.g. <where>
  LIST ELAB-PORT-WIDTH-UNRESOLVED <master> ports=<p,...> (<why>)
  LIST ELAB-PORT-WIDTH checked <n> masters / <cells> cells / <inst> instances; mismatched <m> masters ...

    elab_port_width.py --out ELAB_OUT_DIR [--asbuilt ASBUILT.json] [--netlist asbuilt.json] [--stubs F.sv]
                       [--src F.sv ...] [--define D ...] [--json OUT.json]
"""
import argparse
import collections
import json
import re
import sys
from pathlib import Path

PRIM = re.compile(r"^\$(?!paramod)")
IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_$]*")


class Unresolved(ValueError):
    pass


# ------------------------------------------------------------------------------------------------ expressions
_TOK = re.compile(r"\s*(?:(?P<num>\d[\d_]*)?\s*'\s*(?P<sgn>[sS]?)(?P<base>[bBoOdDhH])\s*(?P<dig>[0-9a-fA-F_xXzZ?]+)"
                  r"|(?P<dec>\d[\d_]*)|(?P<sys>\$[A-Za-z_]\w*)|(?P<id>[A-Za-z_][A-Za-z0-9_$]*(?:::[A-Za-z_]\w*)?)"
                  r"|(?P<op><<<|>>>|===|!==|\*\*|<<|>>|<=|>=|==|!=|&&|\|\||[-+*/%<>!~&|^?:(),{}]))")
_BIN = {"||": 1, "&&": 2, "|": 3, "^": 4, "&": 5, "==": 6, "!=": 6, "===": 6, "!==": 6, "<": 7, "<=": 7, ">": 7,
        ">=": 7, "<<": 8, ">>": 8, "<<<": 8, ">>>": 8, "+": 9, "-": 9, "*": 10, "/": 10, "%": 10, "**": 11}


def _tokens(s):
    out, i = [], 0
    s = s.strip()
    while i < len(s):
        m = _TOK.match(s, i)
        if not m or m.end() == i:
            if s[i:].strip() == "":
                break
            raise Unresolved(f"token at {s[i:i + 20]!r}")
        i = m.end()
        if m.group("base"):
            dig = m.group("dig").replace("_", "")
            if re.search(r"[xXzZ?]", dig):
                raise Unresolved("x/z literal")
            out.append(("n", int(dig, {"b": 2, "o": 8, "d": 10, "h": 16}[m.group("base").lower()])))
        elif m.group("dec"):
            out.append(("n", int(m.group("dec").replace("_", ""))))
        elif m.group("sys"):
            out.append(("f", m.group("sys")))
        elif m.group("id"):
            out.append(("i", m.group("id")))
        elif m.group("op"):
            out.append(("o", m.group("op")))
    return out


def _clog2(v):
    v = int(v)
    return 0 if v <= 1 else (v - 1).bit_length()


def sv_eval(expr, env):
    """integer value of a SystemVerilog constant expression (parameters from env); Unresolved otherwise"""
    toks = _tokens(str(expr))
    pos = [0]

    def peek():
        return toks[pos[0]] if pos[0] < len(toks) else ("e", None)

    def take(kind=None, val=None):
        t = peek()
        if (kind and t[0] != kind) or (val is not None and t[1] != val):
            raise Unresolved(f"expected {val or kind} got {t[1]!r}")
        pos[0] += 1
        return t

    def prim():
        k, v = take()
        if k == "n":
            return v
        if k == "i":
            if v not in env:
                raise Unresolved(f"unknown name {v}")
            x = env[v]
            if isinstance(x, bool):
                return int(x)
            if not isinstance(x, int):
                raise Unresolved(f"non-integer {v}={x!r}")
            return x
        if k == "f":
            take("o", "(")
            a = ternary()
            take("o", ")")
            if v == "$clog2":
                return _clog2(a)
            raise Unresolved(f"system function {v}")
        if k == "o" and v == "(":
            x = ternary()
            take("o", ")")
            return x
        if k == "o" and v in ("-", "+", "!", "~"):
            x = unary_operand()
            return {"-": -x, "+": x, "!": int(not x), "~": ~x}[v]
        raise Unresolved(f"unexpected {v!r}")

    def unary_operand():
        return prim()

    def binary(minp):
        lhs = prim()
        while True:
            k, v = peek()
            if k != "o" or v not in _BIN or _BIN[v] < minp:
                return lhs
            p = _BIN[v]
            take()
            rhs = binary(p if v == "**" else p + 1)
            lhs = _apply(v, lhs, rhs)

    def ternary():
        c = binary(1)
        if peek() == ("o", "?"):
            take()
            a = ternary()
            take("o", ":")
            b = ternary()
            return a if c else b
        return c

    x = ternary()
    if pos[0] != len(toks):
        raise Unresolved(f"trailing {toks[pos[0]][1]!r}")
    return x


def _apply(op, a, b):
    if op in ("/", "%") and b == 0:
        raise Unresolved("division by zero")
    if op == "/":
        q = abs(a) // abs(b)
        return q if (a >= 0) == (b >= 0) else -q
    if op == "%":
        return a - b * _apply("/", a, b)
    if op in ("<<", "<<<"):
        return a << b
    if op in (">>", ">>>"):
        return a >> b
    if op == "**":
        if b < 0:
            raise Unresolved("negative power")
        return a ** b
    return {"||": lambda: int(bool(a) or bool(b)), "&&": lambda: int(bool(a) and bool(b)), "|": lambda: a | b,
            "^": lambda: a ^ b, "&": lambda: a & b, "==": lambda: int(a == b), "!=": lambda: int(a != b),
            "===": lambda: int(a == b), "!==": lambda: int(a != b), "<": lambda: int(a < b), "<=": lambda: int(a <= b),
            ">": lambda: int(a > b), ">=": lambda: int(a >= b), "+": lambda: a + b, "-": lambda: a - b,
            "*": lambda: a * b}[op]()


# ------------------------------------------------------------------------------------------------ source declarations
def _split_top(s, sep=","):
    out, d, cur = [], 0, []
    for c in s:
        if c in "([{":
            d += 1
        elif c in ")]}":
            d -= 1
        if c == sep and d == 0:
            out.append("".join(cur))
            cur = []
        else:
            cur.append(c)
    out.append("".join(cur))
    return out


def _match(s, k):
    d = 0
    for j in range(k, len(s)):
        if s[j] == "(":
            d += 1
        elif s[j] == ")":
            d -= 1
            if d == 0:
                return j
    raise Unresolved("unbalanced parentheses")


_DIR = re.compile(r"^[ \t]*`(ifdef|ifndef|elsif|else|endif|define|undef)\b[ \t]*(\w*)(.*)$")


def preprocess(text, defines):
    """comments out, `ifdef/`ifndef/`elsif/`else/`endif resolved and `NAME expanded with the `define values seen so far
    (command-line defines first, then the file order); a function-like or unknown macro is left (-> UNRESOLVED)"""
    text = re.sub(r"/\*.*?\*/", lambda m: "\n" * m.group(0).count("\n"), text, flags=re.S)
    text = re.sub(r"//[^\n]*", "", text)
    text = re.sub(r"\\\n", " ", text)
    mac = {}
    for d in defines:
        d = d[2:] if d.startswith("-D") else d
        k, _, v = d.partition("=")
        mac[k] = v if _ else "1"
    out, stack = [], []

    def live():
        return all(f[0] for f in stack)

    def expand(ln):
        for _ in range(6):
            n = re.sub(r"`([A-Za-z_]\w*)(?!\s*\()", lambda m: mac.get(m.group(1), m.group(0)), ln)
            if n == ln:
                break
            ln = n
        return ln

    for ln in text.split("\n"):
        m = _DIR.match(ln)
        if not m:
            out.append(expand(ln) if live() else "")
            continue
        k, name, rest = m.group(1), m.group(2), m.group(3)
        if k in ("ifdef", "ifndef"):
            c = (name in mac) == (k == "ifdef")
            stack.append([c, c])
        elif k in ("elsif", "else", "endif") and not stack:
            raise Unresolved(f"unbalanced `{k}")
        elif k == "elsif":
            f = stack[-1]
            c = not f[1] and name in mac
            f[0], f[1] = c, f[1] or c
        elif k == "else":
            f = stack[-1]
            f[0], f[1] = not f[1], True
        elif k == "endif":
            stack.pop()
        elif k == "define" and live():
            if not rest.startswith("("):
                mac[name] = expand(rest.strip())
        elif k == "undef" and live():
            mac.pop(name, None)
        out.append("")
    return "\n".join(out)


_MOD = re.compile(r"(?ms)^\s*(?:module|macromodule)\s+(?:automatic\s+|static\s+)?([A-Za-z_]\w*)\b(.*?)\bendmodule\b")
_TYPEW = r"(?:(?:wire|reg|logic|bit|var|tri|wand|wor|signed|unsigned|integer|int|byte|shortint|longint|time)\b)"


def _params(chunks, local_default=False):
    """[(name, expr, overridable)] from parameter declaration texts (comma lists carry the keyword)"""
    out = []
    for chunk, local in chunks:
        loc = local
        for it in _split_top(chunk):
            it = " ".join(it.split())
            if not it:
                continue
            m = re.match(r"^(parameter|localparam)\b\s*(.*)$", it)
            if m:
                loc, it = m.group(1) == "localparam", m.group(2)
            if it.startswith("type "):
                continue
            m = re.match(r"^(?:(?:integer|int|unsigned|signed|logic|bit|reg|real|realtime|string|longint|shortint|"
                         r"byte|time)\s+)*(?:\[[^\]]*\]\s*)*([A-Za-z_]\w*)\s*(?:\[[^\]]*\]\s*)*(?:=\s*(.*))?$", it, re.S)
            if m:
                out.append((m.group(1), (m.group(2) or "").strip(), not loc))
    return out


def _port_items(txt):
    """ANSI port list -> [(name, dir, packed dims, unpacked dims, typed)] ; non-ANSI names -> dir None"""
    out, d, pk, typed = [], None, [], False
    for it in _split_top(txt):
        it = " ".join(it.split())
        if not it:
            continue
        it = re.sub(r"\(\*.*?\*\)", " ", it).strip()
        m = re.match(rf"^(input|output|inout|ref)?\s*((?:{_TYPEW}\s*)*)((?:\[[^\]]*\]\s*)*)([A-Za-z_]\w*)\s*((?:\[[^\]]*\]\s*)*)$", it)
        if m:
            if m.group(1):
                d, pk, typed = m.group(1), re.findall(r"\[([^\]]*)\]", m.group(3)), False
            elif m.group(2) or m.group(3):
                pk, typed = re.findall(r"\[([^\]]*)\]", m.group(3)), False
            out.append((m.group(4), d, list(pk), re.findall(r"\[([^\]]*)\]", m.group(5)), typed))
            continue
        m = re.match(r"^(input|output|inout|ref)?\s*(?:var\s+)?([A-Za-z_][\w:.]*)\s*((?:\[[^\]]*\]\s*)*)([A-Za-z_]\w*)"
                     r"\s*((?:\[[^\]]*\]\s*)*)$", it)
        if m:   # user type / interface port: width not derivable here
            d, pk, typed = m.group(1) or d, [], True
            out.append((m.group(4), d, [], [], True))
            continue
        out.append((None, d, [], [], True))
    return out


def declarations(text, defines=()):
    """{module: dict(params=[(name, expr, overridable)], ports={name: (packed dims, unpacked dims, typed)})}"""
    t = preprocess(text, defines)
    mods = {}
    for m in _MOD.finditer(t):
        name, rest = m.group(1), m.group(2)
        try:
            i = 0
            while i < len(rest) and rest[i].isspace():
                i += 1
            chunks = []
            if rest[i:i + 1] == "#":
                k = rest.index("(", i)
                e = _match(rest, k)
                chunks.append((rest[k + 1:e], False))
                i = e + 1
                while i < len(rest) and rest[i].isspace():
                    i += 1
            ports_txt = ""
            if rest[i:i + 1] == "(":
                e = _match(rest, i)
                ports_txt, i = rest[i + 1:e], e + 1
            semi = rest.find(";", i)
            body = rest[semi + 1:] if semi >= 0 else ""
            body = re.sub(r"\bfunction\b.*?\bendfunction\b|\btask\b.*?\bendtask\b", ";", body, flags=re.S)
            for st in re.finditer(r"(?:^|(?<=;))\s*((parameter|localparam)\b[^;]*);", body):
                chunks.append((st.group(1), st.group(2) == "localparam"))
            items = _port_items(ports_txt)
            ports = {}
            ansi = any(x[1] for x in items)
            for nm, d, pk, up, typed in items:
                if nm is not None:
                    ports[nm] = (pk, up, typed) if ansi else None
            if not ansi:
                for st in re.finditer(r"(?:^|(?<=;))\s*((?:input|output|inout)\b[^;]*);", body):
                    for nm, d, pk, up, typed in _port_items(st.group(1)):
                        if nm is not None:
                            ports[nm] = (pk, up, typed)
            mods[name] = dict(params=_params(chunks), ports=ports)
        except Unresolved as e:
            mods[name] = dict(params=[], ports={}, error=str(e))
    return mods


def _dim(d, env):
    if ":" in d and not re.search(r"[+-]:", d):
        parts = _split_top(d, ":")
        if len(parts) != 2:
            raise Unresolved(f"range {d}")
        return abs(sv_eval(parts[0], env) - sv_eval(parts[1], env)) + 1
    for op in ("+:", "-:"):
        if op in d:
            return sv_eval(d.split(op, 1)[1], env)
    return sv_eval(d, env)     # [N] (unpacked C-style size)


def declared_widths(decl, values):
    """{port: width or Unresolved message} of a declaration under parameter overrides `values` (python ints)"""
    env, bad = {}, {}
    for name, expr, over in decl["params"]:
        if over and name in values:
            env[name] = values[name]
            continue
        if not expr:
            continue
        try:
            env[name] = sv_eval(expr, env)
        except Unresolved as e:
            bad[name] = str(e)
    out = {}
    for pn, d in decl["ports"].items():
        if d is None:
            out[pn] = Unresolved("no declaration")
            continue
        pk, up, typed = d
        if typed:
            out[pn] = Unresolved("typed / interface port")
            continue
        try:
            w = 1
            for x in pk + up:
                w *= _dim(x, env)
            out[pn] = w
        except Unresolved as e:
            out[pn] = Unresolved(str(e) + (f" (parameters unresolved: {sorted(bad)})" if bad else ""))
    return out


# ------------------------------------------------------------------------------------------------ netlist
def _pint(v):
    """Yosys JSON parameter value -> python int when integral (32-bit two's complement for 32-char bit strings)"""
    if isinstance(v, bool):
        return int(v)
    if isinstance(v, int):
        return v
    if isinstance(v, str) and v and re.fullmatch(r"[01]+", v):
        n = int(v, 2)
        return n - (1 << 32) if len(v) == 32 and n >> 31 else n
    if isinstance(v, str) and re.fullmatch(r"-?\d+", v.strip()):
        return int(v)
    return v


def master_of(ctype, mods):
    m = mods.get(ctype)
    if m is not None:
        h = m.get("attributes", {}).get("hdlname")
        if h:
            return str(h).strip().split(" ")[-1]
    n = ctype
    if n.startswith("$paramod"):
        n = n.split("\\")[1] if "\\" in n else n
    return n.lstrip("\\").split("$")[0]


def _is_bb(m):
    v = str((m or {}).get("attributes", {}).get("blackbox", "0")).strip()
    return v not in ("", "0", "false") and not re.fullmatch(r"0+", v)


def instance_counts(mods, top):
    """{module: number of instances under top} (hierarchical netlist; each module definition counted per use)"""
    cnt = collections.Counter({top: 1})
    order, seen = [], set()

    def visit(n):
        if n in seen or n not in mods:
            return
        seen.add(n)
        for c in mods[n].get("cells", {}).values():
            visit(c["type"])
        order.append(n)
    sys.setrecursionlimit(max(10000, sys.getrecursionlimit()))
    visit(top)
    for n in reversed(order):
        k = cnt.get(n, 0)
        if not k:
            continue
        for c in mods[n].get("cells", {}).values():
            if c["type"] in mods:
                cnt[c["type"]] += k
    return cnt


def check(yjs, decls, top=None, listed=(), max_examples=4):
    mods = yjs["modules"]
    listed = set(listed)
    inst = instance_counts(mods, top) if top and top in mods else None
    rep = collections.OrderedDict()
    cache = {}
    for pname, pm in mods.items():
        if _is_bb(pm):
            continue
        k_parent = inst.get(pname, 0) if inst is not None else 1
        for cn, c in pm.get("cells", {}).items():
            ct = c["type"]
            if PRIM.match(ct) and ct not in mods:
                continue
            master = master_of(ct, mods)
            sub = mods.get(ct)
            r = rep.setdefault(master, dict(cells=0, inst=0, bad_cells=0, bad_inst=0, ports={}, unresolved={},
                                            source=None, listed=master in listed, examples=[]))
            r["cells"] += 1
            r["inst"] += k_parent
            if sub is not None and not _is_bb(sub):
                r["source"] = "body"
                decl_w = {pn: len(p["bits"]) for pn, p in sub.get("ports", {}).items()}
            elif master in decls and not decls[master].get("error"):
                r["source"] = "declaration"
                vals = {}
                # a specialized type ($paramod / bind_slang_abi variant) carries its evaluated parameters; a plain blackbox
                # module's parameter_default_values are the RTL defaults (derived ones too: PW = FW+51 at the default FW),
                # so only the cell's own overrides apply there
                spec = ct.startswith("$paramod") or (sub is not None and master != ct)
                for src in (((sub or {}).get("parameter_default_values", {}) if spec else {}), c.get("parameters", {})):
                    for k, v in src.items():
                        vals[k] = _pint(v)
                key = (master, tuple(sorted((k, str(v)) for k, v in vals.items())))
                if key not in cache:
                    cache[key] = declared_widths(decls[master], vals)
                decl_w = cache[key]
            elif sub is not None:
                r["source"] = "netlist-blackbox"
                decl_w = {pn: len(p["bits"]) for pn, p in sub.get("ports", {}).items()}
                if sub.get("parameter_default_values") or c.get("parameters"):
                    for pn in decl_w:
                        r["unresolved"].setdefault(pn, "parameterized blackbox with no source declaration")
                    continue
            else:
                r["source"] = "none"
                for pn in c.get("connections", {}):
                    r["unresolved"].setdefault(pn, "master not in the netlist and no declaration"
                                               + (f" ({decls[master]['error']})" if master in decls else ""))
                continue
            bad = []
            for pn, bits in c.get("connections", {}).items():
                if not bits:       # .p() -- explicitly open, not a width bind
                    r["open_ports"] = r.get("open_ports", 0) + 1
                    continue
                w = decl_w.get(pn)
                if pn not in decl_w:
                    bad.append((pn, None, len(bits)))
                    continue
                if isinstance(w, Unresolved):
                    r["unresolved"].setdefault(pn, str(w))
                    continue
                if w != len(bits):
                    bad.append((pn, w, len(bits)))
            if bad:
                r["bad_cells"] += 1
                r["bad_inst"] += k_parent
                for pn, w, h in bad:
                    p = r["ports"].setdefault(pn, dict(cells=0, delta_bits=0, sample=[w, h]))
                    p["cells"] += 1
                    p["delta_bits"] += (h - (w or 0)) * max(1, k_parent)
                if len(r["examples"]) < max_examples:
                    r["examples"].append(dict(parent=pname[:160], cell=cn[:120], params={k: _pint(v) for k, v in list(
                        c.get("parameters", {}).items())[:6]}, ports=[[pn, w, h] for pn, w, h in bad[:6]]))
    return rep


def lines(rep):
    out = []
    hit = {m: r for m, r in rep.items() if r["bad_cells"]}
    for m, r in sorted(hit.items(), key=lambda kv: -kv[1]["bad_inst"]):
        ps = ",".join(f"{pn}:{p['sample'][0]}/{p['sample'][1]}" for pn, p in sorted(r["ports"].items())[:6])
        ex = r["examples"][0] if r["examples"] else {}
        out.append(f"WARN ELAB-PORT-WIDTH {m} cells={r['bad_cells']}/{r['cells']} inst={r['bad_inst']}/{r['inst']} "
                   f"ports={ps} (declared/connected; {r['source']}){' listed' if r['listed'] else ''} e.g. "
                   f"{ex.get('parent', '')}.{ex.get('cell', '')} {ex.get('params', '')}")
    for m, r in sorted(rep.items()):
        if r["unresolved"]:
            ps = sorted(r["unresolved"])
            out.append(f"LIST ELAB-PORT-WIDTH-UNRESOLVED {m} ports={','.join(ps[:8])}{'...' if len(ps) > 8 else ''} "
                       f"({r['unresolved'][ps[0]][:120]})")
    n_c = sum(r["cells"] for r in rep.values())
    n_i = sum(r["inst"] for r in rep.values())
    out.append(f"LIST ELAB-PORT-WIDTH checked {len(rep)} masters / {n_c} cells / {n_i} instances; mismatched "
               f"{len(hit)} masters / {sum(r['bad_cells'] for r in hit.values())} cells / "
               f"{sum(r['bad_inst'] for r in hit.values())} instances; unresolved masters "
               f"{sum(1 for r in rep.values() if r['unresolved'])} (report only)")
    return out


def load_netlist(p):
    import gzip
    p = Path(p)
    with (gzip.open(p, "rt") if p.suffix == ".gz" else open(p)) as f:
        return json.load(f)


def sources_of(out):
    """the elab's own lib + full source files (OUT/asbuilt_sources.json): declarations of masters with no stub"""
    try:
        d = json.loads((Path(out) / "asbuilt_sources.json").read_text())
    except (OSError, ValueError):
        return []
    return [f for f in list(d.get("full") or []) + list(d.get("lib") or []) if isinstance(f, str) and Path(f).is_file()]


def run(yjs, ab=None, stubs=None, srcs=(), defines=(), top=None):
    ab = ab or {}
    defs = list(defines) or [d[2:] if d.startswith("-D") else d for d in ab.get("defines", [])]
    decls = {}
    for f in list(srcs) + ([stubs] if stubs else []):
        try:
            decls.update(declarations(Path(f).read_text(errors="replace"), defs))
        except (OSError, Unresolved) as e:
            print(f"elab_port_width: {f}: {e}", file=sys.stderr)
    rep = check(yjs, decls, top or ab.get("_elab_top") or ab.get("top"), ab.get("slang_parameterized_blackboxes", []))
    return dict(lines=lines(rep), masters=rep, n_declarations=len(decls))


def bind_report(yjs, ab, out):
    """bind hook (report only): never raises; writes OUT/elab_port_width.json and returns the finding lines"""
    try:
        out = Path(out)
        stubs = out / "asbuilt_lib_stubs.sv"
        tops = [t for t in (ab.get("_elab_top"), ab.get("top")) if t and t in yjs.get("modules", {})]
        r = run(yjs, ab, stubs if stubs.is_file() else None, sources_of(out), top=tops[0] if tops else None)
        (out / "elab_port_width.json").write_text(json.dumps(r, indent=1, default=str) + "\n")
        unres = [ln for ln in r["lines"] if "-UNRESOLVED " in ln]
        return ([ln for ln in r["lines"] if "-UNRESOLVED " not in ln][:-1] + unres[:5]
                + ([f"LIST ELAB-PORT-WIDTH-UNRESOLVED ... {len(unres) - 5} more in {out / 'elab_port_width.json'}"]
                   if len(unres) > 5 else []) + r["lines"][-1:])
    except Exception as e:     # report-only: a crash here must never stop the bind
        return [f"LIST ELAB-PORT-WIDTH not run: {type(e).__name__}: {e}"[:300]]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", help="elab out dir (asbuilt.json + asbuilt_lib_stubs.sv)")
    ap.add_argument("--netlist")
    ap.add_argument("--stubs")
    ap.add_argument("--asbuilt", help="manifest (defines, top, slang_parameterized_blackboxes)")
    ap.add_argument("--src", action="append", default=[])
    ap.add_argument("--define", action="append", default=[])
    ap.add_argument("--top")
    ap.add_argument("--json")
    a = ap.parse_args(argv)
    out = Path(a.out) if a.out else None
    net = a.netlist or (out and next((str(q) for q in (out / "asbuilt.json", out / "asbuilt.json.gz") if q.is_file()), None))
    if not net:
        ap.error("no netlist (--netlist or --out with asbuilt.json)")
    stubs = a.stubs or (out and (out / "asbuilt_lib_stubs.sv").is_file() and str(out / "asbuilt_lib_stubs.sv")) or None
    ab = json.loads(Path(a.asbuilt).read_text()) if a.asbuilt else {}
    ys = out / "asbuilt.ys" if out else None
    if ys and ys.is_file():     # no manifest: the elab script's own -D defines and top
        yt = ys.read_text(errors="replace")
        if not ab.get("defines") and not a.define:
            a.define = sorted(set(re.findall(r"(?<!\S)-D\s*([A-Za-z_]\w*(?:=\S+)?)", yt)))
        tm = re.search(r"(?:hierarchy\b[^\n]*?-top|--top)\s+(\S+)", yt)
        if tm and not a.top and not ab.get("top"):
            a.top = tm.group(1)
    yjs = load_netlist(net)
    if not a.top and not ab.get("top"):
        tops = [n for n, m in yjs["modules"].items() if str(m.get("attributes", {}).get("top", "0")).strip("0")]
        a.top = tops[0] if tops else None
    r = run(yjs, ab, stubs, list(a.src) + (sources_of(out) if out else []), a.define, a.top)
    for ln in r["lines"]:
        print(ln)
    if a.json:
        Path(a.json).write_text(json.dumps(r, indent=1, default=str) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
