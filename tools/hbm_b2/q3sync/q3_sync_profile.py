#!/usr/bin/env python3
"""q3 SYNC_INPUT reset profile generator (source-only, mechanical).

Resolves module definitions from the q3 core tops + the q3 assembly helper
list, walks the recursive instance closure from the core tops, and emits
namespaced copies (<mod>__q3sync) of every module in the closure with each
async-reset event control
    always @(posedge C or negedge R)   /  always_ff @(posedge C, negedge R)
    always @(posedge C or posedge R)   (active-high, checked against the body)
rewritten to the clock-only form `@(posedge C)`.  The block body is kept
byte-for-byte, so the leading `if (!R)` / `if (R)` branch becomes a synchronous
reset.  Nothing else changes: no relay/synchroniser insertion, shared legacy
RTL is never written, modules outside the closure are not emitted, SRAM
macros are leaves (kept as-is, referenced from the legacy macro .v).

The tool refuses (exit 2) on any event control it cannot classify: negedge
clocks, >1 clock, edge lists whose reset cannot be proven from the body's
first `if`, level-sensitive lists, always_latch, bare procedural `@`,
`initial` blocks, unresolved instantiations.

Usage:
  q3_sync_profile.py --root <repo> --files <q3b.files> --out <dir>
                     --census <census.json> [--top core=path.sv:module ...]
"""
import argparse, json, os, re, sys, hashlib, subprocess, datetime
from collections import defaultdict, OrderedDict

SUFFIX = "__q3sync"

DEFAULT_TOPS = OrderedDict([
    ("body", ("rtl/hbm_accel/cores_split/ot_hfd_coll_q3_hard_v8x/ot_hfd_coll_q3_body_core.sv", "ot_hfd_coll_q3_body_core")),
    ("edge", ("rtl/hbm_accel/cores_split/ot_hfd_coll_q3_hard_v8x/ot_hfd_coll_q3_edge_core.sv", "ot_hfd_coll_q3_edge_core")),
    ("vm", ("rtl/hbm_accel/cores_split/ot_hfd_coll_q3_hard_v8x/ot_hfd_coll_q3_vm_core.sv", "ot_hfd_coll_q3_vm_core")),
    ("reduce", ("rtl/hbm_accel/cores_split/ot_hfd_coll_q2_hard_v8g/ot_hfd_coll_q2_reduce_core.sv", "ot_hfd_coll_q2_reduce_core")),
    ("ring_ag", ("rtl/hbm_accel/cores_split/ot_hfd_coll_q2_hard_v8g/ot_hfd_coll_q2_ring_ag_core.sv", "ot_hfd_coll_q2_ring_ag_core")),
])
MACRO_DIR = "physical/asap7_memory_macros_v2"

KEYWORDS = set("""
always always_ff always_comb always_latch and assign automatic begin buf bufif0 bufif1 case casex casez cmos
deassign default defparam disable edge else end endcase endfunction endgenerate endmodule endprimitive
endspecify endtable endtask event for force forever fork function generate genvar highz0 highz1 if ifnone
initial inout input integer join large localparam logic macromodule medium module nand negedge nmos nor not
notif0 notif1 or output parameter pmos posedge primitive pull0 pull1 pulldown pullup rcmos real realtime reg
release repeat rnmos rpmos rtran rtranif0 rtranif1 scalared signed small specify specparam strong0 strong1
supply0 supply1 table task time tran tranif0 tranif1 tri tri0 tri1 triand trior trireg unsigned vectored wait
wand weak0 weak1 while wire wor xnor xor bit byte int shortint longint unique priority return break continue
typedef struct packed enum union static const var void import export interface endinterface modport
""".split())

ID = r"[A-Za-z_][\w$]*"
TOKEN_RE = re.compile(r'//[^\n]*|/\*.*?\*/|"(?:\\.|[^"\\\n])*"|\\\S+', re.S)


def mask(text):
    """Return text of equal length: comments/strings blanked (newlines kept),
    escaped identifiers replaced by '\\' + '_'*(n-1) (so keywords, parens,
    commas inside them are invisible to the scanners)."""
    def rep(m):
        s = m.group(0)
        if s[0] == "\\":
            return "\\" + "_" * (len(s) - 1)
        return re.sub(r"[^\n]", " ", s)
    return TOKEN_RE.sub(rep, text)


def skip_ws(s, i):
    n = len(s)
    while i < n and s[i].isspace():
        i += 1
    return i


def match_paren(s, i):
    """s[i] == '(' ; return index just past the matching ')' (masked text)."""
    assert s[i] == "("
    d = 0
    n = len(s)
    j = i
    while j < n:
        c = s[j]
        if c == "(":
            d += 1
        elif c == ")":
            d -= 1
            if d == 0:
                return j + 1
        j += 1
    raise ValueError("unbalanced paren at %d" % i)


def read_ident(s, i):
    """Identifier (plain or masked-escaped) at i in masked text -> end index or None."""
    if i < len(s) and s[i] == "\\":
        j = i + 1
        while j < len(s) and not s[j].isspace():
            j += 1
        return j
    m = re.compile(ID).match(s, i)
    return m.end() if m else None


def prev_sig_token(s, i):
    """Previous significant token before i in masked text."""
    j = i - 1
    while j >= 0 and s[j].isspace():
        j -= 1
    if j < 0:
        return ""
    if re.match(r"[\w$]", s[j]):
        k = j
        while k >= 0 and re.match(r"[\w$]", s[k]):
            k -= 1
        return s[k + 1:j + 1]
    return s[j]


class Module:
    def __init__(self, name, path, start, end, name_span):
        self.name, self.path, self.start, self.end, self.name_span = name, path, start, end, name_span
        self.instances = []   # dicts: type, inst, type_span, conns, start
        self.blocks = []      # dicts
        self.unclassified = []
        self.unresolved = []
        self.assign_alias = {}
        self.params = set()
        self.endlabel_span = None


class SourceFile:
    def __init__(self, rel, root):
        self.rel = rel
        self.path = os.path.join(root, rel)
        with open(self.path, "r", encoding="utf-8", errors="surrogateescape") as f:
            self.text = f.read()
        self.m = mask(self.text)
        self.modules = []
        self._nl = [i for i, c in enumerate(self.text) if c == "\n"] if len(self.text) < 2000000 else \
            [m.start() for m in re.finditer("\n", self.text)]

    def line(self, pos):
        import bisect
        return bisect.bisect_right(self._nl, pos - 1) + 1


MOD_RE = re.compile(r"(?<![\w$\\])(module|macromodule)\s+(" + ID + r")")
ENDMOD_RE = re.compile(r"(?<![\w$\\])endmodule(?![\w$])")
ALWAYS_RE = re.compile(r"(?<![\w$\\])(always_ff|always_latch|always_comb|always)(?![\w$])")
INITIAL_RE = re.compile(r"(?<![\w$\\])initial(?![\w$])")
CAND_RE = re.compile(r"(?<![\w$\\.`'])(" + ID + r")(?![\w$])(?=\s*(#|\\|[A-Za-z_]))")


def parse_modules(sf):
    pos = 0
    while True:
        m = MOD_RE.search(sf.m, pos)
        if not m:
            break
        e = ENDMOD_RE.search(sf.m, m.end())
        if not e:
            raise SystemExit("ERROR %s: module %s without endmodule" % (sf.rel, m.group(2)))
        end = e.end()
        mod = Module(m.group(2), sf.rel, m.start(), end, m.span(2))
        lab = re.compile(r"\s*:\s*(" + ID + r")").match(sf.m, end)
        if lab and lab.group(1) == mod.name:
            mod.endlabel_span = lab.span(1)
            end = lab.end()
            mod.end = end
        sf.modules.append(mod)
        pos = end


def parse_instance_at(s, i):
    """Given masked s and index i just after a candidate type name, try to parse
    `[#(...)] inst [ranges] (`. Return (inst_span, conn_open, conn_close) or None."""
    j = skip_ws(s, i)
    if j < len(s) and s[j] == "#":
        j = skip_ws(s, j + 1)
        if j >= len(s) or s[j] != "(":
            return None
        j = skip_ws(s, match_paren(s, j))
    k = read_ident(s, j)
    if k is None:
        return None
    inst_span = (j, k)
    name = s[j:k]
    if name in KEYWORDS:
        return None
    j = skip_ws(s, k)
    while j < len(s) and s[j] == "[":
        d = s.find("]", j)
        if d < 0:
            return None
        j = skip_ws(s, d + 1)
    if j >= len(s) or s[j] != "(":
        return None
    close = match_paren(s, j)
    return inst_span, j, close


def split_top(s_masked, s_orig, seps_regex):
    """Split original text at top-level separators found in masked text."""
    parts = []
    depth = 0
    last = 0
    i = 0
    n = len(s_masked)
    sep = re.compile(seps_regex)
    while i < n:
        c = s_masked[i]
        if c in "([{":
            depth += 1
        elif c in ")]}":
            depth -= 1
        elif depth == 0:
            m = sep.match(s_masked, i)
            if m and (m.group(0) == "," or (
                    (i == 0 or not re.match(r"[\w$]", s_masked[i - 1])) and
                    (m.end() >= n or not re.match(r"[\w$]", s_masked[m.end()])))):
                parts.append(s_orig[last:i])
                last = m.end()
                i = m.end()
                continue
        i += 1
    parts.append(s_orig[last:])
    return parts


def expr_bases(x):
    """Base net names an expression forwards (ternary -> both branches,
    concatenation -> members, selects dropped).  Bus-level, not bit-level."""
    x = x.strip()
    m = re.match(r"^([^?]*)\?(.*):(.*)$", x, re.S)
    if m and not x.startswith("\\"):
        return expr_bases(m.group(2)) | expr_bases(m.group(3))
    out = set()
    for t in re.finditer(r"\\\S+|(?<![\w$'])" + ID, re.sub(r"\[[^\]]*\]", "", x) if not x.startswith("\\") else x):
        v = t.group(0)
        if v not in KEYWORDS:
            out.add(v)
    return out


def norm(x):
    return re.sub(r"\s+", "", x)


def strip_paren(x):
    while x.startswith("(") and x.endswith(")"):
        x = x[1:-1]
    return x


def reset_cond_matches(cond, net, polarity):
    c = strip_paren(norm(cond))
    r = norm(net)
    if polarity == "neg":
        cands = {"!" + r, "~" + r, "!(" + r + ")", "~(" + r + ")", r + "==0", r + "==1'b0", r + "==1'h0",
                 r + "===1'b0", "1'b0==" + r}
    else:
        cands = {r, "(" + r + ")", r + "==1", r + "==1'b1", r + "==1'h1", r + "===1'b1", r + "!=0", r + "!=1'b0"}
    return c in cands


def first_if_cond(sf, j):
    """At masked index j (just after event control), return original text of the
    condition of the first `if`, allowing `begin [: label]` before it."""
    s = sf.m
    j = skip_ws(s, j)
    m = re.compile(r"begin(?![\w$])(\s*:\s*" + ID + r")?").match(s, j)
    if m:
        j = skip_ws(s, m.end())
        # block-local declarations (named begin) may precede the reset if
        decl = re.compile(r"(reg|integer|logic|bit|int|byte|shortint|longint|real|time)(?![\w$])[^;]*;")
        while True:
            d = decl.match(s, j)
            if not d:
                break
            j = skip_ws(s, d.end())
    m = re.compile(r"if(?![\w$])").match(s, j)
    if not m:
        return None
    j = skip_ws(s, m.end())
    if j >= len(s) or s[j] != "(":
        return None
    e = match_paren(s, j)
    return sf.text[j + 1:e - 1]


def analyse_module(sf, mod, known_defs, macros):
    s = sf.m
    body_lo = mod.name_span[1]
    body_hi = mod.end
    seg = s[body_lo:body_hi]
    # --- instances -------------------------------------------------------
    for m in CAND_RE.finditer(seg):
        name = m.group(1)
        a = body_lo + m.start(1)
        b = body_lo + m.end(1)
        if name in KEYWORDS:
            continue
        r = parse_instance_at(s, b)
        if r is None:
            continue
        pt = prev_sig_token(s, a)
        stmt_start = pt in (";", "", "begin", "end", "generate", "endgenerate", "else", ":", ")",
                            "endfunction", "endtask", "endcase") or pt.startswith("end")
        (isp, op, cl) = r
        if name in known_defs or name in macros:
            conns = {}
            inner_m = s[op + 1:cl - 1]
            inner_o = sf.text[op + 1:cl - 1]
            ordered = False
            for part_o, part_m in zip(split_top(inner_m, inner_o, r","), split_top(inner_m, inner_m, r",")):
                pm = re.match(r"\s*\.\s*(" + ID + r")\s*\(", part_m)
                if pm:
                    po = part_o[pm.end():]
                    # closing paren of the connection
                    po_m = part_m[pm.end():]
                    k = po_m.rfind(")")
                    conns[pm.group(1)] = po[:k].strip()
                elif part_o.strip():
                    ordered = True
            mod.instances.append(dict(type=name, inst=sf.text[isp[0]:isp[1]].strip(), type_span=(a, b),
                                      conns=conns, ordered=ordered, macro=name in macros,
                                      line=sf.line(a)))
        elif stmt_start:
            mod.unresolved.append(dict(type=name, inst=sf.text[isp[0]:isp[1]].strip(),
                                       line=sf.line(a)))
    for m in re.finditer(r"(?<![\w$])(parameter|localparam)(?![\w$])([^;]*)", seg):
        for q in re.finditer(r"(" + ID + r")\s*=(?!=)", m.group(2)):
            mod.params.add(q.group(1))
    # --- base-level aliases (for clock tracing): assign / wire-init ------
    for m in re.finditer(r"(?<![\w$])assign\s+([^;=]+?)\s*=\s*([^;]+?)\s*;", seg):
        lhs = sf.text[body_lo + m.start(1):body_lo + m.end(1)]
        rhs = sf.text[body_lo + m.start(2):body_lo + m.end(2)]
        for lb in expr_bases(lhs):
            mod.assign_alias.setdefault(lb, set()).update(expr_bases(rhs))
    for m in re.finditer(r"(?<![\w$])wire\s+(\[[^\]]*\]\s*)?(" + ID + r")\s*=\s*([^;]+?)\s*;", seg):
        rhs = sf.text[body_lo + m.start(3):body_lo + m.end(3)]
        mod.assign_alias.setdefault(m.group(2), set()).update(expr_bases(rhs))
    # --- event controls --------------------------------------------------
    used_at = set()
    for m in ALWAYS_RE.finditer(seg):
        kw = m.group(1)
        a = body_lo + m.start(1)
        line = sf.line(a)
        j = skip_ws(s, body_lo + m.end(1))
        if kw == "always_latch":
            mod.unclassified.append(dict(line=line, kind="always_latch", text=sf.text[a:j + 40].split("\n")[0]))
            continue
        if j >= len(s) or s[j] != "@":
            if kw == "always_comb":
                mod.blocks.append(dict(kind="comb", line=line))
            else:
                mod.unclassified.append(dict(line=line, kind="always_without_event", text=sf.text[a:a + 80].split("\n")[0]))
            continue
        used_at.add(j)
        k = skip_ws(s, j + 1)
        if s[k] == "*":
            mod.blocks.append(dict(kind="comb", line=line))
            continue
        if s[k] != "(":
            mod.unclassified.append(dict(line=line, kind="bad_event", text=sf.text[a:a + 80].split("\n")[0]))
            continue
        e = match_paren(s, k)
        inner_m, inner_o = s[k + 1:e - 1], sf.text[k + 1:e - 1]
        if inner_m.strip() == "*":
            mod.blocks.append(dict(kind="comb", line=line))
            continue
        items = [x.strip() for x in split_top(inner_m, inner_o, r",|or")]
        parsed = []
        for it in items:
            mm = re.match(r"(posedge|negedge)\s+(.+)$", it, re.S)
            parsed.append((mm.group(1), mm.group(2).strip()) if mm else (None, it))
        evtext = "@(" + inner_o + ")"
        if any(p[0] is None for p in parsed):
            mod.unclassified.append(dict(line=line, kind="level_sensitive_list", text=evtext))
            continue
        if len(parsed) == 1:
            ed, net = parsed[0]
            if ed != "posedge":
                mod.unclassified.append(dict(line=line, kind="negedge_clock", text=evtext))
                continue
            mod.blocks.append(dict(kind="clock_only", clock=net, line=line))
            continue
        if len(parsed) != 2:
            mod.unclassified.append(dict(line=line, kind="multi_edge_list", text=evtext))
            continue
        cond = first_if_cond(sf, e)
        roles = []
        for idx, (ed, net) in enumerate(parsed):
            pol = "neg" if ed == "negedge" else "pos"
            if cond is not None and reset_cond_matches(cond, net, pol):
                roles.append(idx)
        if len(roles) != 1:
            mod.unclassified.append(dict(line=line, kind="reset_not_provable", text=evtext,
                                         first_if=cond))
            continue
        ri = roles[0]
        ci = 1 - ri
        if parsed[ci][0] != "posedge":
            mod.unclassified.append(dict(line=line, kind="negedge_clock", text=evtext))
            continue
        clk = parsed[ci][1]
        rst = parsed[ri][1]
        newtxt = "posedge " + clk + (" " if clk.startswith("\\") else "")
        mod.blocks.append(dict(kind="async_converted", clock=clk, reset=rst,
                               polarity="active_low" if parsed[ri][0] == "negedge" else "active_high",
                               line=line, edit=(k + 1, e - 1, newtxt), legacy=evtext))
    # bare procedural @ anywhere else
    for mm in re.finditer(r"@", seg):
        a = body_lo + mm.start()
        if a not in used_at:
            mod.unclassified.append(dict(line=sf.line(a), kind="procedural_event",
                                         text=sf.text[a:a + 60].split("\n")[0]))
    for mm in INITIAL_RE.finditer(seg):
        a = body_lo + mm.start()
        mod.unclassified.append(dict(line=sf.line(a), kind="initial_block",
                                     text=sf.text[a:a + 80].split("\n")[0]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--files", default="tools/hbm_b2/q3sync/q3b.files",
                    help="repo-relative helper list (paths + macro:<name> lines), read at --root")
    ap.add_argument("--out", required=True)
    ap.add_argument("--census", required=True)
    ap.add_argument("--top", action="append", default=[], help="core=relpath:module (default: 5 q3 cores)")
    args = ap.parse_args()
    root = os.path.abspath(args.root)
    tops = OrderedDict()
    if args.top:
        for t in args.top:
            c, rest = t.split("=", 1)
            p, mname = rest.rsplit(":", 1)
            tops[c] = (p, mname)
    else:
        tops = DEFAULT_TOPS
    rels, macros = [], []
    if os.path.isabs(args.files):
        raise SystemExit("REFUSE --files must be repo-relative (owner rule: evidence reads repo-relative paths at its commit)")
    for ln in open(os.path.join(root, args.files)):
        ln = ln.strip()
        if not ln or ln.startswith("#"):
            continue
        if ln.startswith("macro:"):
            macros.append(ln[6:])
        else:
            rels.append(ln)
    for c, (p, _) in tops.items():
        if p not in rels:
            rels.insert(0, p)
    files = [SourceFile(r, root) for r in rels]
    defs = {}
    dups = []
    for sf in files:
        parse_modules(sf)
        for md in sf.modules:
            if md.name in defs:
                dups.append((md.name, defs[md.name].path, sf.rel))
            defs[md.name] = md
    if dups:
        print("REFUSE duplicate module definitions: %s" % dups, file=sys.stderr)
        sys.exit(2)
    file_of = {sf.rel: sf for sf in files}
    macro_set = set(macros)
    # analyse only modules reachable (analyse lazily in BFS)
    analysed = set()
    closure = OrderedDict()   # module -> set of cores
    core_mods = {}
    for core, (p, top) in tops.items():
        if top not in defs:
            print("REFUSE core %s top %s not defined" % (core, top), file=sys.stderr)
            sys.exit(2)
        seen, stack, order = set(), [top], []
        while stack:
            n = stack.pop()
            if n in seen:
                continue
            seen.add(n)
            order.append(n)
            md = defs[n]
            if n not in analysed:
                analyse_module(file_of[md.path], md, defs, macro_set)
                analysed.add(n)
            for ins in md.instances:
                if not ins["macro"]:
                    stack.append(ins["type"])
        core_mods[core] = order
        for n in order:
            closure.setdefault(n, set()).add(core)
    # multiplicity per core (static paths; generate-loop replication counted once)
    def multiplicity(top):
        mult = defaultdict(int)
        mult[top] = 1
        # topological order via DFS post-order
        topo, vis = [], set()
        def dfs(n):
            vis.add(n)
            for ins in defs[n].instances:
                if not ins["macro"] and ins["type"] not in vis:
                    dfs(ins["type"])
            topo.append(n)
        sys.setrecursionlimit(10000)
        dfs(top)
        macro_mult = defaultdict(int)
        for n in reversed(topo):
            for ins in defs[n].instances:
                if ins["macro"]:
                    macro_mult[ins["type"]] += mult[n]
                else:
                    mult[ins["type"]] += mult[n]
        return mult, macro_mult
    # ---- refusal checks -------------------------------------------------
    unclassified, unresolved = [], []
    for n in closure:
        md = defs[n]
        for u in md.unclassified:
            unclassified.append(dict(module=n, file=md.path, **u))
        for u in md.unresolved:
            unresolved.append(dict(module=n, file=md.path, **u))
        for ins in md.instances:
            if ins["ordered"]:
                pass
    # ---- clock tracing ----------------------------------------------------
    def parents_of(core):
        par = defaultdict(list)
        for n in core_mods[core]:
            for ins in defs[n].instances:
                if not ins["macro"]:
                    par[ins["type"]].append((n, ins))
        return par

    def is_top_input(top, name):
        md = defs[top]
        txt = file_of[md.path].text[md.start:md.end]
        return re.search(r"(?<![\w$])input\s[^;)]*?(?<![\w$\\])" + re.escape(name) + r"(?![\w$])", txt) is not None

    def base_of(net):
        net = net.strip()
        return net if net.startswith("\\") else re.sub(r"\s*\[[^\]]*\]", "", net).strip()

    def trace(core, mod, base, par, seen):
        top = tops[core][1]
        key = (mod, base)
        if key in seen:
            return set()
        seen.add(key)
        md = defs[mod]
        if base in md.assign_alias:
            out = set()
            for r in md.assign_alias[base]:
                out |= trace(core, mod, r, par, seen)
            return out
        if mod == top:
            return {("top_port", base)} if is_top_input(top, base) else {("internal", "%s:%s" % (mod, base))}
        out, hit = set(), False
        for (pm, ins) in par.get(mod, []):
            if base in ins["conns"]:
                hit = True
                for r in expr_bases(ins["conns"][base]):
                    if r in defs[pm].params:
                        continue
                    out |= trace(core, pm, r, par, seen)
        return out if hit else {("internal", "%s:%s" % (mod, base))}

    clocks = {}
    for core in tops:
        par = parents_of(core)
        ports, internal, unres = set(), set(), set()
        local = set()
        for n in core_mods[core]:
            for b in defs[n].blocks:
                if b["kind"] in ("clock_only", "async_converted"):
                    local.add((n, b["clock"]))
        for (n, c) in sorted(local):
            for kind, v in trace(core, n, base_of(c), par, set()):
                {"top_port": ports, "internal": internal, "unresolved": unres}[kind].add(v)
        rports, rinternal = set(), set()
        rlocal = set((n, b["reset"]) for n in core_mods[core] for b in defs[n].blocks if b["kind"] == "async_converted")
        for (n, r) in sorted(rlocal):
            for kind, v in trace(core, n, base_of(r), par, set()):
                (rports if kind == "top_port" else rinternal).add(v)
        clocks[core] = dict(top_clock_ports=sorted(ports), internal_clock_nets=sorted(internal),
                            unresolved_traces=sorted(unres), local_clock_names=len(local),
                            converted_reset_sources_top_ports=sorted(rports),
                            converted_reset_sources_internal=sorted(rinternal)[:80],
                            converted_reset_sources_internal_count=len(rinternal))
    # ---- census -----------------------------------------------------------
    census_mods = OrderedDict()
    totals = OrderedDict()
    for core in tops:
        mult, mmult = multiplicity(tops[core][1])
        conv_src = conv_w = clk_only = 0
        by_rst = defaultdict(int)
        for n in core_mods[core]:
            md = defs[n]
            c = sum(1 for b in md.blocks if b["kind"] == "async_converted")
            conv_src += c
            conv_w += c * mult[n]
            clk_only += sum(1 for b in md.blocks if b["kind"] == "clock_only") * mult[n]
            for b in md.blocks:
                if b["kind"] == "async_converted":
                    by_rst["%s|%s" % (n, b["reset"])] += mult[n]
        totals[core] = dict(top=tops[core][1] + SUFFIX, legacy_top=tops[core][1], source=tops[core][0],
                            modules_in_closure=len(core_mods[core]),
                            converted_blocks_source=conv_src,
                            converted_blocks_static_paths=conv_w,
                            clock_only_blocks_static_paths=clk_only,
                            macro_instances_static_paths=dict(mmult),
                            unclassified=sum(len(defs[n].unclassified) for n in core_mods[core]),
                            distinct_reset_nets=len(by_rst),
                            clocks=clocks[core])
        for n in core_mods[core]:
            md = defs[n]
            e = census_mods.setdefault(n, dict(file=md.path, emitted_as=n + SUFFIX, cores={},
                                               instantiation_sites_in_closure=0))
            e["cores"][core] = mult[n]
    for n, e in census_mods.items():
        md = defs[n]
        e["instantiation_sites_in_closure"] = sum(1 for p in closure for ins in defs[p].instances if ins["type"] == n)
        groups = defaultdict(int)
        for b in md.blocks:
            if b["kind"] == "async_converted":
                groups[(b["clock"], b["reset"], b["polarity"])] += 1
        e["converted_blocks"] = [dict(clock=k[0], reset=k[1], polarity=k[2], count=v) for k, v in
                                 sorted(groups.items(), key=lambda kv: -kv[1])]
        e["converted_total"] = sum(groups.values())
        e["clock_only_blocks"] = sum(1 for b in md.blocks if b["kind"] == "clock_only")
        e["comb_blocks"] = sum(1 for b in md.blocks if b["kind"] == "comb")
        e["unclassified_events"] = md.unclassified
        e["children"] = sorted(set(i["type"] + ("" if i["macro"] else SUFFIX) for i in md.instances))
    # ---- emit -----------------------------------------------------------------
    os.makedirs(args.out, exist_ok=True)
    emitted = []
    for sf in files:
        cl = [md for md in sf.modules if md.name in closure]
        if not cl:
            continue
        edits = []
        for md in sf.modules:
            if md.name in closure:
                edits.append((md.name_span[0], md.name_span[1], md.name + SUFFIX))
                if md.endlabel_span:
                    edits.append((md.endlabel_span[0], md.endlabel_span[1], md.name + SUFFIX))
                for ins in md.instances:
                    if not ins["macro"]:
                        edits.append((ins["type_span"][0], ins["type_span"][1], ins["type"] + SUFFIX))
                for b in md.blocks:
                    if b["kind"] == "async_converted":
                        edits.append(b["edit"])
            else:
                edits.append((md.start, md.end, "// [q3sync] module %s is outside the q3 closure: not emitted" % md.name))
        edits.sort()
        for x, y in zip(edits, edits[1:]):
            if x[1] > y[0]:
                raise SystemExit("overlapping edits in %s: %s %s" % (sf.rel, x[:2], y[:2]))
        out = []
        last = 0
        for a, b, t in edits:
            out.append(sf.text[last:a]); out.append(t); last = b
        out.append(sf.text[last:])
        hdr = "// GENERATED by tools/hbm_b2/q3sync/q3_sync_profile.py from %s (sha1 %s): q3 SYNC_INPUT reset profile.\n" \
              "// Closure modules renamed <mod>%s; async event controls rewritten clock-only; nothing else changed.\n" % (
                  sf.rel, hashlib.sha1(sf.text.encode("utf-8", "surrogateescape")).hexdigest(), SUFFIX)
        base = os.path.basename(sf.rel)
        stem, ext = os.path.splitext(base)
        op = os.path.join(args.out, stem + SUFFIX + ext)
        with open(op, "w", encoding="utf-8", errors="surrogateescape") as f:
            f.write(hdr + "".join(out))
        emitted.append(dict(source=sf.rel, emitted=os.path.basename(op), modules=[m.name for m in cl]))
    core_files = {}
    for core in tops:
        fl = []
        mods = set(core_mods[core])
        for em in emitted:
            if any(m in mods for m in em["modules"]):
                fl.append(em["emitted"])
        mm = sorted(set(i["type"] for n in core_mods[core] for i in defs[n].instances if i["macro"]))
        core_files[core] = dict(files=fl, macros=["%s/%s/%s.v" % (MACRO_DIR, x, x) for x in mm])
        with open(os.path.join(args.out, core + ".f"), "w") as f:
            for x in fl:
                f.write(x + "\n")
            for x in core_files[core]["macros"]:
                f.write(x + "\n")
    git = subprocess.run(["git", "-C", root, "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    inputs = [args.files, "tools/hbm_b2/q3sync/q3_sync_profile.py"] + rels
    dirty = subprocess.run(["git", "-C", root, "status", "--porcelain", "--"] + inputs,
                           capture_output=True, text=True).stdout.strip()
    untracked = [r for r in inputs if subprocess.run(["git", "-C", root, "ls-files", "--error-unmatch", r],
                                                     capture_output=True).returncode != 0]
    if dirty or untracked:
        raise SystemExit("REFUSE inputs not clean/tracked at %s: %s %s" % (git, dirty, untracked))
    status = "PASS_GENERATED" if not unclassified and not unresolved else "REFUSED"
    census = OrderedDict(
        status=status,
        generated=subprocess.run(["date"], capture_output=True, text=True).stdout.strip(),
        tool="tools/hbm_b2/q3sync/q3_sync_profile.py",
        source_commit=git,
        inputs_clean_at_commit=True,
        helper_list=args.files,
        suffix=SUFFIX,
        rule="each `always @(posedge C or|, negedge R)` (or posedge R active-high, reset proven by the body's first if) -> `@(posedge C)`; body byte-unchanged; no relay/synchroniser inserted; legacy RTL unchanged; macros are leaves",
        count_note="*_static_paths = instance-weighted by static instantiation paths; a site inside a generate loop counts once (not elaborated); *_source = per module definition",
        modules_in_closure=len(closure),
        totals_per_core=totals,
        unclassified_total=len(unclassified),
        unclassified=unclassified,
        unresolved_instantiations=unresolved,
        modules=census_mods,
        emitted=emitted,
        core_filelists=core_files,
        next_gate=OrderedDict(
            claim_to_prove="each <core>__q3sync equals its legacy core cycle-for-cycle once reset has been held >= the core's max reset release depth (the async->sync change only alters behaviour while reset is asserted: the reset now takes effect on the next clock edge instead of immediately)",
            bench="reset-held-long lockstep sim: legacy core top and <core>__q3sync compiled together (names are disjoint), every clock port on one clock (single 833 ps domain), every reset port on one reset; identical per-cycle stimulus; cold reset held H cycles, run, warm reset re-asserted H cycles mid-run, run; compare every output on every cycle outside the reset windows; H >= max release depth (relay chains: body rcp[]/u_control rst_l/u_fj rst_q, vm rst_q, edge argmax rst_l; use H=256 for body unless the relay depth is measured)",
            tools="tools/hbm_b2/q3sync/q3_lockstep_tb.py (TB generator) + lockstep.sh recipe in census lint field",
            stronger_followups=["production-shape stimulus (the selected TKM token-gate stimulus) instead of random inputs for writer/edge/reduce/ring_ag/body", "Yosys equiv/SEC of the reset-free next-state functions (async vs sync differ only in reset timing)", "die reset-contract check that every q3 flop's reset is now in the 833 ps clock's data timing (no recovery/removal arcs) after synthesis of the __q3sync tops"],
            not_done_here=["no P&R, no adoption, no substitution into the q3 parent", "body/edge/reduce/ring_ag lockstep not run"]),
    )
    with open(args.census, "w") as f:
        json.dump(census, f, indent=1)
    print(json.dumps(dict(status=status, modules_in_closure=len(closure),
                          converted={c: (t["converted_blocks_source"], t["converted_blocks_static_paths"]) for c, t in totals.items()},
                          unclassified=len(unclassified), unresolved=len(unresolved)), indent=1))
    if status != "PASS_GENERATED":
        for u in unclassified[:50] + unresolved[:50]:
            print("REFUSE", u, file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
