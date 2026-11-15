"""HCPARAM-ALL (11-15): every hard core of every die, built parameters vs the parameters the die really instantiates.

hard_core_param.py only compares plan rows that carry a `param_wrap`.  S81 dsdv_idx_tx_n32 (rtl dsdv_idx_l20s.sv:1110, nested in
`dsdv_bk_sel_vmtx u_core`) passes only V/IK/EK/UID/SRAM_MACRO/MUT, so the die takes FACE 0 and RDL/WDL/WDC/SCS/RIL/RHP/PDC 0 while the
signed hardened core was built with FACE 2 and all of those 1: a different edge count that no row of the plan shows.  This module
closes the class for every hard-core row (signed view or plan core view), on every die:

  EFFECTIVE parameters  the instance the BOUND RTL really holds: the type module (bind OUT/rtl/<module>.sv) is walked down through
                        every nested instance (nested modules from bind.f), each instance's named/positional overrides are
                        evaluated in its parent's scope, a parameter the instance does not override takes the module header default.
                        generate-if branches whose condition evaluates false are skipped; a value that cannot be evaluated is
                        UNRESOLVED (counted, never an error).
  BUILT parameters      what the hardened view was built with, first record found wins:
                          1 registry  tools/die_plan/hard_core_built_params.json  (curated from the signed record, source named)
                          2 view dir  config.mk VERILOG_TOP_PARAMS (kit config of the signed view), else the kit spec.json
                                      `params` (freeze.json / provenance.json "spec", ref_tile/<kit>/spec.json, legacy specs/<k>/spec.json)
                          3 bind manifest hard_params sidecars (opentallas.frame_kit.hard_params.v1)
  MISMATCH              a built parameter whose effective value differs, or a parameter the die overrides that the built record
                        does not list while the override differs from the module default the view was built with.  Simulation
                        labels (INSTANCE, MB) never count.

Binder.cmd_bind adds HARD_CORE_PARAM_ALL errors (the bind fails, like HARD_CORE_PARAM_WRAP); OT_HCPARAM_ALL=0 switches the gate off.
Report mode (every mismatch, a per-die owner lane, exit 1 if any):
  python3 tools/die_plan/hard_core_param_all.py BINDDIR [--plan PLAN.json] [--root TREE] [--json OUT.json]
"""
import argparse
import json
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REGISTRY = HERE / "hard_core_built_params.json"
ALLOW = HERE / "hard_core_param_allow.json"
LABELS = frozenset({"INSTANCE", "MB"})          # simulation labels: no hardware effect (tools/s81_dv/hard_params.py LABELS)
OWNERS = {"s81": "DIE-S81-92", "qwen_compute": "DIE-QC-103", "qc": "DIE-QC-103", "qwen_kvsys": "KV-102", "kv": "KV-102",
          "s81_head": "HEAD-100", "head": "HEAD-100", "hbm": "HBM (no live owner lane)"}
KEYWORDS = frozenset("""module endmodule input output inout wire reg logic bit integer parameter localparam assign always always_ff
always_comb always_latch initial begin end if else for while case casez casex endcase default generate endgenerate genvar function
endfunction task endtask return posedge negedge or and not nand nor xor xnor buf typedef enum struct union package import export
interface endinterface modport fork join defparam supply0 supply1 tri signed unsigned int real time string""".split())


# ------------------------------------------------------------------------------------------------ text helpers
_CMT = re.compile(r'"(?:[^"\\\n]|\\.)*"|//[^\n]*|/\*.*?\*/', re.S)


def strip_comments(t):
    """comments blanked (newlines kept so offsets stay), string literals kept"""
    return _CMT.sub(lambda m: m.group(0) if m.group(0)[0] == '"' else re.sub(r"[^\n]", " ", m.group(0)), t)


def preprocess(text, defines):
    """`ifdef/`ifndef/`elsif/`else/`endif resolved against `defines`; other directives dropped"""
    if "`" not in text:
        return text
    defs = {d: "1" for d in defines}
    # one-line `ifdef X a `else b `endif (a parameter default with a fallback) is resolved first
    text = re.sub(r"`ifn?def\s+(\w+)\s+([^\n`]*?(?:`\w+[^\n`]*?)*?)\s*`else\s+([^\n]*?)\s*`endif",
                  lambda m: m.group(2) if (m.group(1) in defs) == (m.group(0).startswith("`ifdef")) else m.group(3), text)
    out, stack = [], []          # stack of [active, taken_any, parent_active]
    for line in text.split("\n"):
        s = line.strip()
        m = re.match(r"`(ifdef|ifndef|elsif|else|endif|define|undef)\b\s*(\w*)\s*(.*)", s)
        active = all(f[0] for f in stack)
        if m:
            d, name, rest = m.groups()
            if d in ("ifdef", "ifndef"):
                cond = (name in defs) == (d == "ifdef")
                stack.append([cond, cond, True]); out.append(""); continue
            if d == "elsif" and stack:
                f = stack[-1]; cond = (name in defs) and not f[1]
                f[0] = cond; f[1] = f[1] or cond; out.append(""); continue
            if d == "else" and stack:
                f = stack[-1]; f[0] = not f[1]; f[1] = True; out.append(""); continue
            if d == "endif" and stack:
                stack.pop(); out.append(""); continue
            if d == "define" and active:
                defs[name] = rest.split("//")[0].strip() or "1"
            if d == "undef":
                defs.pop(name, None)
            out.append(""); continue
        out.append(line if active else "")
    text = "\n".join(out)
    # a `MACRO use stays as written: the kit build may define it differently, so a value that depends on one is UNRESOLVED
    return text


def paren_end(text, i, o="(", c=")"):
    depth = 0
    for j in range(i, len(text)):
        if text[j] == o:
            depth += 1
        elif text[j] == c:
            depth -= 1
            if depth == 0:
                return j
    return -1


def top_items(text):
    out, depth, cur = [], 0, []
    for ch in text:
        depth += {"(": 1, "[": 1, "{": 1, ")": -1, "]": -1, "}": -1}.get(ch, 0)
        if ch == "," and depth == 0:
            out.append("".join(cur)); cur = []
        else:
            cur.append(ch)
    if "".join(cur).strip():
        out.append("".join(cur))
    return out


# ------------------------------------------------------------------------------------------------ expression evaluator
_TOK = re.compile(r"""\s*(?:
    (?P<lit>\d*\s*'[sS]?[bBoOdDhH]\s*[0-9a-fA-FxXzZ_?]+|'[01xXzZ]|\d[\d_]*(?:\.\d+)?)
  | (?P<id>\$?[A-Za-z_][\w$]*|`\w+)
  | (?P<op>\*\*|<<<|>>>|<<|>>|<=|>=|==|!=|&&|\|\||~&|~\||~\^|\^~|[-+*/%<>!~&|^?:(),{}\[\]])
  | (?P<str>"[^"]*")
)""", re.X)


def _lit(s):
    s = s.replace("_", "").replace(" ", "")
    if "." in s:
        return None
    if "'" not in s:
        return int(s)
    w, rest = s.split("'", 1)
    if rest and rest[0] in "sS":
        rest = rest[1:]
    if not rest:
        return None
    if rest[0] in "01" and len(rest) == 1 and not w:
        return int(rest)
    base = {"b": 2, "o": 8, "d": 10, "h": 16}[rest[0].lower()]
    digits = rest[1:]
    if re.search(r"[xXzZ?]", digits):
        return None
    v = int(digits, base)
    if w:
        v &= (1 << int(w)) - 1
    return v


class _Unresolved(Exception):
    pass


class Expr:
    """tiny Verilog constant-expression evaluator; scope(name) -> int | str | None"""

    def __init__(self, text, scope):
        self.toks = []
        pos = 0
        text = text.strip()
        while pos < len(text):
            m = _TOK.match(text, pos)
            if not m or m.end() == pos:
                raise _Unresolved(text)
            pos = m.end()
            k = m.lastgroup
            self.toks.append((k, m.group(k)))
        self.i = 0
        self.scope = scope

    def peek(self):
        return self.toks[self.i] if self.i < len(self.toks) else (None, None)

    def eat(self, v=None):
        t = self.peek()
        if v is not None and t[1] != v:
            raise _Unresolved(f"expected {v}")
        self.i += 1
        return t

    def parse(self):
        v = self.ternary()
        if self.i != len(self.toks):
            raise _Unresolved("trailing")
        return v

    def ternary(self):
        c = self.binary(0)
        if self.peek()[1] == "?":
            self.eat()
            a = self.ternary(); self.eat(":"); b = self.ternary()
            if c is None:
                return a if a == b else None
            return a if c else b
        return c

    _PREC = [["||"], ["&&"], ["|"], ["^", "~^", "^~"], ["&"], ["==", "!="], ["<", ">", "<=", ">="],
             ["<<", ">>", "<<<", ">>>"], ["+", "-"], ["*", "/", "%"], ["**"]]

    def binary(self, lvl):
        if lvl >= len(self._PREC):
            return self.unary()
        a = self.binary(lvl + 1)
        while self.peek()[0] == "op" and self.peek()[1] in self._PREC[lvl]:
            op = self.eat()[1]
            b = self.binary(lvl + 1)
            if op == "||" and (a or b) and (a is not None and a or b is not None and b):
                a = 1; continue
            if op == "&&" and (a == 0 and a is not None or b == 0 and b is not None):
                a = 0; continue
            if a is None or b is None or isinstance(a, str) or isinstance(b, str):
                if op in ("==", "!=") and isinstance(a, str) and isinstance(b, str):
                    a = int((a == b) == (op == "=="))
                    continue
                a = None; continue
            a = self._op(op, a, b)
        return a

    @staticmethod
    def _op(op, a, b):
        if op in ("/", "%") and b == 0:
            return None
        return {"||": lambda: int(bool(a) or bool(b)), "&&": lambda: int(bool(a) and bool(b)), "|": lambda: a | b,
                "^": lambda: a ^ b, "~^": lambda: ~(a ^ b), "^~": lambda: ~(a ^ b), "&": lambda: a & b,
                "==": lambda: int(a == b), "!=": lambda: int(a != b), "<": lambda: int(a < b), ">": lambda: int(a > b),
                "<=": lambda: int(a <= b), ">=": lambda: int(a >= b), "<<": lambda: a << b, "<<<": lambda: a << b,
                ">>": lambda: a >> b, ">>>": lambda: a >> b, "+": lambda: a + b, "-": lambda: a - b, "*": lambda: a * b,
                "/": lambda: int(a / b) if abs(a) < 2 ** 52 else a // b,
                "%": lambda: a - b * int(a / b), "**": lambda: a ** b if 0 <= b < 64 else None}[op]()

    def unary(self):
        k, v = self.peek()
        if k == "op" and v in ("-", "+", "!", "~"):
            self.eat()
            x = self.unary()
            if x is None or isinstance(x, str):
                return None
            return {"-": -x, "+": x, "!": int(not x), "~": ~x}[v]
        return self.primary()

    def primary(self):
        k, v = self.eat()
        if k == "lit":
            r = _lit(v)
            if r is None:
                return None
            return r
        if k == "str":
            return v[1:-1]
        if k == "op" and v == "(":
            x = self.ternary(); self.eat(")")
            return x
        if k == "id":
            if v.startswith("$"):
                self.eat("(")
                args = [self.ternary()]
                while self.peek()[1] == ",":
                    self.eat(); args.append(self.ternary())
                self.eat(")")
                a = args[0]
                if v in ("$signed", "$unsigned"):
                    return a
                if v == "$clog2" and isinstance(a, int):
                    return max(0, (a - 1).bit_length()) if a > 0 else 0
                return None
            if v.startswith("`"):
                return None
            if self.peek()[1] == "(":                    # a function call: not constant here
                depth = 0
                while True:
                    t = self.eat()[1]
                    depth += {"(": 1, ")": -1}.get(t, 0)
                    if depth == 0:
                        return None
            if self.peek()[1] == "[":                    # bit/part select of a parameter
                j = self.i; depth = 0
                while True:
                    t = self.toks[j][1]
                    depth += {"[": 1, "]": -1}.get(t, 0)
                    j += 1
                    if depth == 0:
                        break
                self.i = j
                return None
            return self.scope(v)
        raise _Unresolved(v)


def evaluate(text, scope):
    """int | str | None (None = not evaluable here)"""
    try:
        return Expr(text, scope).parse()
    except (_Unresolved, IndexError, KeyError, ValueError, RecursionError):
        return None


def norm(v):
    """comparable form of a parameter value"""
    if isinstance(v, bool):
        return int(v)
    if isinstance(v, int):
        return v
    if isinstance(v, str):
        s = v.strip().strip('"')
        r = evaluate(s, lambda n: None)
        return r if isinstance(r, int) else s
    return v


# ------------------------------------------------------------------------------------------------ modules
class Module:
    def __init__(self, name, file, text, header_params, body, body_params):
        self.name, self.file, self.text, self.body = name, file, text, body
        self.header = header_params          # [(name, expr, local)] in order
        self.body_params = body_params       # [(name, expr, local)] in order
        self._insts = {}
        self.pnames = [p[0] for p in header_params + body_params if not p[2]]

    def all_params(self):
        return self.header + self.body_params


_MOD = re.compile(r"(?m)^\s*(?:\(\*.*?\*\)\s*)?(?:module|macromodule)\s+(?:automatic\s+|static\s+)?([A-Za-z_]\w*)")
_PDECL = re.compile(r"\b(parameter|localparam)\b([^;]*);")


def _parse_decl_item(it):
    """'integer unsigned X = expr' | '[7:0] X = expr' -> (name, expr)"""
    if "=" not in it:
        return None
    lhs, rhs = it.split("=", 1)
    names = re.findall(r"[A-Za-z_]\w*", re.sub(r"\[[^\]]*\]", " ", lhs))
    names = [n for n in names if n not in ("parameter", "localparam", "integer", "int", "bit", "logic", "signed", "unsigned",
                                          "real", "reg", "string", "type", "shortint", "longint", "byte", "time")]
    return (names[-1], rhs.strip()) if names else None


def parse_modules(text, file, defines=()):
    text = preprocess(strip_comments(text), defines)
    mods = []
    ms = list(_MOD.finditer(text))
    for m in ms:
        end = re.compile(r"\bendmodule\b").search(text, m.end())
        end = end.start() if end else len(text)
        i = m.end()
        header, local_from_header = [], False
        mm = re.compile(r"\s*#\s*\(").match(text, i)
        if mm:
            j = paren_end(text, mm.end() - 1)
            for it in top_items(text[mm.end():j]):
                kw = re.match(r"\s*(parameter|localparam)\b", it)
                if kw:
                    local_from_header = kw.group(1) == "localparam"
                d = _parse_decl_item(it)
                if d:
                    header.append((d[0], d[1], local_from_header))
            i = j + 1
        pm = re.compile(r"\s*\(").match(text, i)
        if pm:
            j = paren_end(text, pm.end() - 1)
            i = j + 1 if j > 0 else i
        body = text[i:end]
        bp = []
        for pd in _PDECL.finditer(body):
            local = pd.group(1) == "localparam"
            for it in top_items(pd.group(2)):
                d = _parse_decl_item(pd.group(1) + " " + it)
                if d:
                    bp.append((d[0], d[1], local or bool(header)))   # a body parameter is a localparam when the header has #()
        mods.append(Module(m.group(1), file, text, header, body, bp))
    return mods


def load_index(files, defines=()):
    """{module: Module}: the first definition in `files` order wins; dups counted"""
    idx, dups = {}, {}
    for f in files:
        try:
            t = Path(f).read_text(errors="replace")
        except OSError:
            continue
        if "module" not in t:
            continue
        for m in parse_modules(t, str(f), defines):
            if m.name in idx:
                dups[m.name] = dups.get(m.name, 1) + 1
                continue
            idx[m.name] = m
    return idx, dups


# ------------------------------------------------------------------------------------------------ instances / guards
class Inst:
    def __init__(self, module, name, named, positional, pos):
        self.module, self.name, self.named, self.positional, self.pos = module, name, named, positional, pos


def _guards(body):
    """[(start, end, [(cond_text, expected)])] for each begin..end block: the if/else conditions that enclose it"""
    blocks, stack, chain, pending, skip = [], [], {}, None, -1
    for m in re.finditer(r"\b(begin|end|if|else)\b|;", body):
        if m.start() < skip:
            continue
        k, d = m.group(0), len(stack)
        if k == ";":
            pending = None
        elif k == "if":
            j = body.find("(", m.end())
            e = paren_end(body, j) if j >= 0 else -1
            if e < 0:
                continue
            cond, skip = body[j + 1:e], e
            if pending and pending[0] == "else":
                pending = ("if", [(c, False) for c in chain.get(d, [])], cond)
            else:
                chain[d] = []
                pending = ("if", [], cond)
        elif k == "else":
            pending = ("else",)
        elif k == "begin":
            if pending is None:
                g, cc = [], None
            elif pending[0] == "if":
                g, cc = pending[1] + [(pending[2], True)], pending[2]
            else:
                g, cc = [(c, False) for c in chain.get(d, [])], None
            stack.append((m.start(), g, d, cc))
            pending = None
        elif k == "end" and stack:
            s0, g, dd, cc = stack.pop()
            blocks.append((s0, m.end(), g))
            if cc is not None:
                chain.setdefault(dd, []).append(cc)
            pending = None
    return blocks


def module_instances(mod, known):
    """[Inst] of every instance of a module in `known` inside mod.body (generate branches included; their guards are Inst.guards)"""
    if len(known) in mod._insts:
        return mod._insts[len(known)]
    body, out = mod.body, []
    blocks = None
    pat = re.compile(r"(?<![\w$.`])([A-Za-z_]\w*)\s*(#\s*\()?")
    pos = 0
    for m in pat.finditer(body):
        if m.start() < pos:
            continue
        name = m.group(1)
        if name in KEYWORDS or name not in known:
            continue
        i, named, positional = m.end(), {}, []
        if m.group(2):
            j = paren_end(body, m.end() - 1)
            if j < 0:
                continue
            for it in top_items(body[m.end():j]):
                a = re.fullmatch(r"\s*\.\s*([A-Za-z_]\w*)\s*\((.*)\)\s*", it, re.S)
                if a:
                    named[a.group(1)] = a.group(2).strip()
                elif it.strip():
                    positional.append(it.strip())
            i = j + 1
        im = re.compile(r"\s*([A-Za-z_]\w*)\s*(\[[^\]]*\]\s*)?\(").match(body, i)
        if not im or im.group(1) in KEYWORDS:
            continue
        inst = Inst(name, im.group(1), named, positional, m.start())
        out.append(inst)
        pos = im.end()
    if out:
        blocks = _guards(body)
        for inst in out:
            inst.guards = [g for (s, e, gl) in blocks if s < inst.pos < e for g in gl]
    mod._insts[len(known)] = out
    return out


# ------------------------------------------------------------------------------------------------ elaboration
class Scope:
    """parameter values of one module instance: overrides (already evaluated values) over header defaults"""

    def __init__(self, mod, overrides, parent_unresolved=()):
        self.mod, self.over, self.memo, self.busy = mod, dict(overrides), {}, set()
        self.decl = {n: (e, loc) for n, e, loc in mod.all_params()}

    def get(self, name):
        if name in self.memo:
            return self.memo[name]
        if name not in self.decl:
            return None
        e, loc = self.decl[name]
        if name in self.over and not loc:
            v = self.over[name]
        elif name in self.busy:
            v = None
        else:
            self.busy.add(name)
            v = evaluate(e, self.get)
            self.busy.discard(name)
        self.memo[name] = v
        return v

    def default(self, name):
        e, _ = self.decl[name]
        return evaluate(e, Scope(self.mod, {}).get)

    def cond(self, guards):
        """True if every guard may hold (unknown counts as may-hold), False if one is definitely violated"""
        for text, want in guards:
            v = evaluate(text, self.get)
            if isinstance(v, int) and bool(v) != want:
                return False
        return True


class Found:
    def __init__(self, path, module, name, explicit, eff, defaults, unresolved_over, declared=True):
        self.declared = declared
        self.path, self.module, self.name = path, module, name
        self.explicit = explicit            # {param: value|None} the instance overrides
        self.eff = eff                      # {param: value|None} effective (overrides + header defaults)
        self.defaults = defaults            # {param: value|None} header defaults
        self.unresolved_over = unresolved_over


def _reach(idx, extra=()):
    """module -> set of module names reachable below it (transitive, static); `extra` = names of modules with no RTL here"""
    direct = {}
    known = set(idx) | set(extra)
    for n, m in idx.items():
        direct[n] = {i.module for i in module_instances(m, known)}
    memo = {}

    def rec(n, stack):
        if n in memo:
            return memo[n]
        if n in stack:
            return set()
        r = set()
        for c in direct.get(n, ()):
            r.add(c)
            r |= rec(c, stack | {n})
        memo[n] = r
        return r
    return {n: rec(n, frozenset()) for n in idx}


def elaborate(idx, top, want, reach=None, max_depth=14, top_over=None, extra=()):
    """-> [Found]: every instance of a module in `want` below `top` (parameters evaluated through the hierarchy)"""
    reach = reach if reach is not None else _reach(idx, extra)
    known = set(idx) | set(extra)
    found = []

    def rec(mod, scope, path, depth):
        if depth > max_depth:
            return
        for inst in module_instances(mod, known):
            tgt = idx.get(inst.module)
            if inst.module not in want and not (want & reach.get(inst.module, set())):
                continue
            if not scope.cond(inst.guards):
                continue
            explicit, unresolved = {}, []
            for p, e in inst.named.items():
                explicit[p] = evaluate(e, scope.get)
            for k, e in enumerate(inst.positional):
                if tgt is not None and k < len(tgt.pnames):
                    explicit[tgt.pnames[k]] = evaluate(e, scope.get)
            p2 = path + [inst.name]
            if tgt is None:                                   # no RTL for this master here: only its overrides are known
                found.append(Found(".".join(p2), inst.module, inst.name, explicit, dict(explicit), {}, [], declared=False))
                continue
            sc = Scope(tgt, explicit)
            if inst.module in want:
                eff = {n: sc.get(n) for n, _, loc in tgt.all_params() if not loc}
                dfl = {n: sc.default(n) for n, _, loc in tgt.all_params() if not loc}
                found.append(Found(".".join(p2), inst.module, inst.name, explicit, eff, dfl,
                                   [p for p, v in explicit.items() if v is None]))
            rec(tgt, sc, p2, depth + 1)

    topmod = idx.get(top)
    if topmod is None:
        return None
    rec(topmod, Scope(topmod, top_over or {}), [], 0)
    return found


# ------------------------------------------------------------------------------------------------ built parameters
def _mk_params(text):
    m = re.search(r"VERILOG_TOP_PARAMS\s*[:?]?=\s*([^\n]*)", text)
    if not m:
        return None
    toks = m.group(1).split()
    if len(toks) % 2:
        return None
    return {toks[i]: toks[i + 1] for i in range(0, len(toks), 2)}


def _json(p):
    try:
        return json.loads(Path(p).read_text())
    except (OSError, ValueError):
        return None


class Built:
    """built-parameter lookup for a hard-core row"""

    def __init__(self, root, hard_params=None, registry=REGISTRY):
        self.root = Path(root) if root else None
        self.hard = hard_params or {}
        reg = _json(registry) if registry and Path(registry).is_file() else None
        self.reg = (reg or {}).get("entries", [])

    def record_shas(self, row):
        """sha256 values the row's view dir carries (signoff/PROVENANCE routed_db_sha256, odb.sha, ...) plus the sha256 of its lib/lef:
        a registry entry is keyed by module + signed-record sha, so a swapped or copied view dir still resolves"""
        import hashlib
        out = set()
        for key in ("lib", "lef"):
            p = self._path(row.get(key))
            if not p or not p.is_file():
                continue
            d = p.parent
            try:
                out.add(hashlib.sha256(p.read_bytes()).hexdigest())
            except OSError:
                pass
            for n in ("PROVENANCE.json", "provenance.json", "signoff.json", "freeze.json", "receipt.json"):
                j = _json(d / n)
                if isinstance(j, dict):
                    out |= set(re.findall(r"\b[0-9a-f]{64}\b", json.dumps(j)))
            if (d / "odb.sha").is_file():
                out |= set(re.findall(r"\b[0-9a-f]{64}\b", (d / "odb.sha").read_text()))
        return out

    def _path(self, rel):
        if not rel:
            return None
        p = Path(rel)
        if p.is_absolute():
            return p
        return self.root / p if self.root else None

    def lookup(self, row, die):
        """-> (params dict, source str) | (None, why)"""
        mod, lib = row.get("module"), row.get("lib") or ""
        why = "no lib/lef in the row"
        if "/asap7_memory_macros" in lib:
            return None, "memory macro view (no RTL parameters)"
        cand = [e for e in self.reg if e.get("module") == mod and (not e.get("die") or e["die"] == die)
                and (not e.get("lib_contains") or e["lib_contains"] in lib)]
        if cand:
            shas = self.record_shas(row)
            hit = [e for e in cand if shas & set(e.get("records") or [])]
            if len(hit) == 1 or (hit and all(h["params"] == hit[0]["params"] for h in hit)):
                return dict(hit[0]["params"]), "registry (record sha) " + hit[0].get("source", "")
            if len(cand) == 1 or all(c["params"] == cand[0]["params"] for c in cand):
                return dict(cand[0]["params"]), "registry (module) " + cand[0].get("source", "")
            why = f"registry has {len(cand)} different parameter sets for {mod} and none matches this view's record sha"
        for key in ("lib", "lef"):
            rel = row.get(key)
            p = self._path(rel)
            if not p:
                continue
            d = p.parent
            why = f"no config.mk / kit spec reachable from {d}"
            cands = []
            if (d / "config.mk").is_file():
                cands.append(("config.mk", d / "config.mk"))
            for pj in ("freeze.json", "provenance.json", "PROVENANCE.json", "receipt.json", "signoff.json"):
                j = _json(d / pj)
                if isinstance(j, dict):
                    kd = j.get("kit")
                    if isinstance(kd, str) and kd.startswith("/") and (Path(kd) / "config.mk").is_file():
                        cands.append(("config.mk", Path(kd) / "config.mk"))
                    sp = (j.get("kit") or {}).get("spec") if isinstance(j.get("kit"), dict) else j.get("spec")
                    if sp and self._path(sp) and self._path(sp).is_file():
                        cands.append(("spec", self._path(sp)))
                    elif sp:
                        why = f"kit spec {sp} not in the tree"
            for up in (d.parent.parent / "spec.json", d.parent / "spec.json"):
                if up.is_file():
                    cands.append(("spec", up))
            for kind, f in cands:
                if kind != "config.mk":
                    why = f"kit spec {f} has no params for {mod}"
                if kind == "config.mk":
                    mp = _mk_params(f.read_text(errors="replace"))
                    if mp is not None:
                        return mp, f"config.mk {f}"
                else:
                    j = _json(f)
                    if isinstance(j, dict) and isinstance(j.get("params"), dict) and j.get("top") in (None, mod):
                        return dict(j["params"]), f"spec {f}"
        if mod in self.hard:
            return dict(self.hard[mod]), "hard_params sidecar"
        return None, why


def compare(found, built):
    """-> ([(param, built, effective, kind)], n_unresolved)"""
    out, unres = [], 0
    if not found.declared and any(p not in LABELS for p in built):
        return [("*", dict(built), None, "NO_SOURCE")], 0
    for p, bv in sorted(built.items()):
        if p in LABELS:
            continue
        if p not in found.eff:
            if found.declared:
                out.append((p, bv, None, "NOT_DECLARED"))
            else:
                unres += 1
            continue
        ev = norm(found.eff[p])
        bn = norm(bv)
        if ev is None:
            unres += 1
        elif ev != bn:
            out.append((p, bn, ev, "DIFF"))
    for p, v in sorted(found.explicit.items()):
        if p in built or p in LABELS or p not in found.eff or not found.declared:
            continue
        ev, df = norm(found.eff[p]), norm(found.defaults.get(p))
        if ev is None or df is None:
            unres += 1
        elif ev != df:
            out.append((p, df, ev, "DIE_OVERRIDE"))
    return out, unres


def match_rows(rows, found):
    """row -> [Found] (the instances of the row's module that can be the row)"""
    res = {}
    for k, row in enumerate(rows):
        c = [f for f in found if f.module == row["module"]]
        pi = (row.get("physical_inst") or "").removeprefix("u_bound.")
        comps = (row.get("inst") or "").split(".")
        if len(c) > 1:
            n = [f for f in c if f.path == pi or f.name == pi] if pi else []
            if not n:
                n = [f for f in c if f.name == comps[-1]]
            if len(n) > 1:
                n2 = [f for f in n if all(x in f.path.split(".") for x in comps)]
                n = n2 or n
            c = n or c
        res[k] = c
    return res


# ------------------------------------------------------------------------------------------------ driver
def die_name(plan):
    d = plan.get("die")
    return str(d.get("name") if isinstance(d, dict) else d or "")


def die_owner(plan):
    d = die_name(plan).lower()
    if d in OWNERS:
        return OWNERS[d]
    for k in sorted(OWNERS, key=len, reverse=True):
        if k in d:
            return OWNERS[k]
    return "unowned"


def load_allow(path=ALLOW):
    """{(die, module): reason}: signed cores the check may leave unchecked, explicit per die and with a reason"""
    j = _json(path) if path and Path(path).is_file() else None
    out = {}
    for e in (j or {}).get("entries", []):
        if e.get("die") and e.get("reason"):
            for m in e.get("modules") or [e.get("module")]:
                if m:
                    out[(e["die"], m)] = e["reason"]
    return out


def _full_index(root, idx, defines):
    """idx + every module of root/rtl the bind.f closure does not define (the bind's own definitions win)"""
    files = []
    for d, subs, names in os.walk(Path(root) / "rtl"):
        subs[:] = [x for x in subs if x not in ("tb", "test", "tests", "build", "obj_dir")]
        files += [os.path.join(d, n) for n in names if n.endswith((".sv", ".v")) and not n.startswith("tb_") and not n.endswith("_bb.v")]
    extra, _ = load_index(sorted(files), defines)
    merged = dict(extra)
    merged.update(idx)
    return merged


def check_plan(plan, bind_dir, root, files=None, defines=(), hard_params=None, only_types=None, registry=REGISTRY, types=None,
               modules=None, remap=None, allow=ALLOW):
    """-> dict(mismatches=[str], rows=[dict], stats) over every hard-core row of every type of the plan.
    types: {type: type dict} when the bind renamed/split them (Binder.types); modules: {type: bound module name}
    (bind_report.json types[].module) else the type's own `module`."""
    bind_dir = Path(bind_dir)
    types = types if types is not None else plan["partition_types"]
    modules = modules or {}
    rtl_dir = next((bind_dir / d for d in ("rtl", "gen") if (bind_dir / d).is_dir()), bind_dir)
    if files is None:
        files = []
        for n in ("bind.f", "portbind.f"):
            if (bind_dir / n).is_file():
                files += (bind_dir / n).read_text().split()
        for old, new in remap or []:
            files = [new + f[len(old):] if f.startswith(old) else f for f in files]
    gen = sorted(str(p) for p in rtl_dir.glob("*.sv"))
    gen_set = set(gen)
    idx, dups = load_index(gen + [f for f in files if f not in gen_set], defines)
    allrow = {h["module"] for t in types.values() for h in t.get("hard_cores") or [] if h.get("module")}
    reach = _reach(idx, allrow)
    built = Built(root, hard_params, registry)
    die = die_name(plan)
    owner = die_owner(plan)
    allowed = load_allow(allow) if not isinstance(allow, dict) else allow
    res = dict(mismatches=[], rows=[], macro=0, allowed=0, no_record={}, no_built=0, no_built_why={}, shared=0, not_found=0, unresolved=0, rows_checked=0, rows_total=0, no_rtl=[], owner=owner, die=die)
    views = {}
    full = full_reach = None
    for tn, t in sorted(types.items()):
        if only_types and tn not in only_types:
            continue
        rows = [h for h in t.get("hard_cores") or [] if not h.get("param_wrap")]
        res["rows_total"] += len(rows)
        if not rows:
            continue
        top = modules.get(tn) or t["module"]
        if top not in idx:
            res["no_rtl"].append(tn)
            continue
        want = {h["module"] for h in rows}
        found = elaborate(idx, top, want, reach, extra=allrow) or []
        by_row = match_rows(rows, found)
        if (any(not by_row[k] for k in by_row) or any(not f.declared for f in found)) and root and (Path(root) / "rtl").is_dir():
            # the bind.f closure stops at the leaf cores; the module bodies below them are in the source tree: look there too
            if full is None:
                full = _full_index(root, idx, defines)
                full_reach = _reach(full, allrow)
            f2 = elaborate(full, top, want, full_reach, extra=allrow) or []
            b2 = match_rows(rows, f2)
            if sum(1 for k in b2 if b2[k]) >= sum(1 for k in by_row if by_row[k]):
                found, by_row = f2, b2
        seen = set()
        for k, row in enumerate(rows):
            cands = by_row[k]
            bp, src = built.lookup(row, die)
            if bp is None and src.startswith("memory macro"):
                res["macro"] += 1
                continue
            if bp is None:
                res["no_built"] += 1
                w = res["no_built_why"].setdefault(src.split(" /")[0].split(" in ")[0][:70], {})
                w[row["module"]] = w.get(row["module"], 0) + 1
                if (die, row["module"]) in allowed:
                    res["allowed"] += 1
                else:
                    nr = res["no_record"].setdefault(row["module"], dict(n=0, example=f"{tn} {row.get('inst')}", why=src))
                    nr["n"] += 1
            if len(cands) == 1 and row.get("lib") and "/asap7_memory_macros" not in row["lib"]:
                views.setdefault(os.path.dirname(row["lib"]), []).append((tn, row, cands[0]))
            if bp is None:
                continue
            if not cands:
                res["not_found"] += 1
                if (die, row["module"]) in allowed:
                    res["allowed"] += 1
                else:
                    nr = res["no_record"].setdefault(row["module"], dict(n=0, example=f"{tn} {row.get('inst')}",
                                                                      why="the die RTL has no instance of this hard-core module"))
                    nr["n"] += 1
                continue
            key = (row["module"], row.get("lib"), tuple(sorted(bp.items())), tuple(f.path for f in cands))
            res["rows_checked"] += 1
            bad_all, un = [], 0
            for f in cands:
                d, u = compare(f, bp)
                un += u
                bad_all.append((f, d))
            res["unresolved"] += un
            if all(d for _, d in bad_all):
                if key in seen:
                    continue
                seen.add(key)
                for f, d in bad_all:
                    if not d:
                        continue
                    txt = ", ".join(f"{p} die {'(no such parameter in the die module)' if kind == 'NOT_DECLARED' else '(the bound source has no definition of the module)' if kind == 'NO_SOURCE' else e}, hardened {bv}"
                                    f" [{kind}]" for p, bv, e, kind in d)
                    res["mismatches"].append(f"type {tn} row {row.get('inst')} ({f.path}) module {row['module']}: {txt}; "
                                             f"built from {src}")
                    for p, bv, e, kind in d:
                        res["rows"].append(dict(type=tn, row=row.get("inst"), path=f.path, module=row["module"], param=p,
                                                die_value=e, built_value=bv, kind=kind, source=src, owner=owner))
    # one hardened view holds ONE parameter set: instances of it whose resolved parameters differ from each other cannot all be right
    for vdir, members in sorted(views.items()):
        vals = {}
        for tn, row, f in members:
            for p, v in f.eff.items():
                n = norm(v)
                if p in LABELS or n is None:
                    continue
                vals.setdefault(p, {}).setdefault(n, []).append(f"{tn}:{f.path}")
        for p, d in sorted(vals.items()):
            if len(d) > 1:
                res["shared"] += 1
                top = sorted(d.items(), key=lambda kv: -len(kv[1]))
                line = (f"view {vdir}: parameter {p} differs between instances of the one hardened view: "
                        + "; ".join(f"{v} on {len(w)} (e.g. {w[0]})" for v, w in top[:4]) + " [VIEW_SHARED_DIFF]")
                res["mismatches"].append(line)
                res["rows"].append(dict(type=members[0][0], row=members[0][1].get("inst"), path=members[0][2].path,
                                        module=members[0][1]["module"], param=p, die_value=[v for v, _ in top], built_value=None,
                                        kind="VIEW_SHARED_DIFF", source=vdir, owner=owner))
    for m, nr in sorted(res["no_record"].items()):
        res["mismatches"].append(f"module {m}: {nr['n']} signed hard-core row(s) cannot be checked ({nr['why']}; e.g. {nr['example']}); "
                                 f"add its built parameters to hard_core_built_params.json from the signed record, or list die {die} / "
                                 f"{m} with a reason in hard_core_param_allow.json [NO_RECORD]")
        res["rows"].append(dict(type=None, row=nr["example"], path=None, module=m, param=None, die_value=None, built_value=None,
                                kind="NO_RECORD", source=nr["why"], owner=owner, n=nr["n"]))
    res["dup_modules"] = len(dups)
    return res


def load_hard_params(files, base):
    """{master: {param: value}} from the frame-kit hard_params sidecars (bind manifest key hard_params); unreadable ones skipped"""
    out = {}
    for f in files or []:
        p = Path(f) if Path(f).is_absolute() else Path(base) / f
        j = _json(p)
        if isinstance(j, dict) and j.get("schema") == "opentallas.frame_kit.hard_params.v1":
            for m, ps in (j.get("masters") or {}).items():
                out.setdefault(m, dict(ps))
    return out


def manifest_info(manifest, root):
    """(defines, hard_params) of a bind manifest (asbuilt json) path"""
    if not manifest:
        return [], {}
    p = Path(manifest) if Path(manifest).is_absolute() else Path(root) / manifest
    j = _json(p)
    if not isinstance(j, dict):
        return [], {}
    return list(j.get("defines") or []), load_hard_params(j.get("hard_params"), j.get("base") or root)


def gate(binder, out, files):
    """Binder hook: [error str] (OT_HCPARAM_ALL=0 disables)"""
    if os.environ.get("OT_HCPARAM_ALL", "1") == "0":
        return []
    ab = binder.ab or {}
    hard = load_hard_params(ab.get("hard_params"), binder.base)
    try:
        res = check_plan(binder.plan, out, binder.base, files=list(files), defines=ab.get("defines") or [], hard_params=hard,
                         types=binder.types)
    except Exception as exc:                      # a defect of this check must not look like a design error: say so, fail open
        print(f"HARD_CORE_PARAM_ALL_SKIPPED {type(exc).__name__}: {exc}", file=sys.stderr)
        binder.hcparam_stats = dict(skipped=f"{type(exc).__name__}: {exc}")
        return []
    binder.hcparam_stats = {k: res[k] for k in ("rows_total", "rows_checked", "macro", "allowed", "no_built", "not_found", "unresolved",
                                                "shared")}
    binder.hcparam_stats["unchecked_allowlisted"] = res["allowed"]
    binder.hcparam_stats["unchecked_no_record_modules"] = len(res["no_record"])
    binder.hcparam_stats["mismatches"] = len(res["mismatches"])
    binder.hcparam_stats["owner"] = res["owner"]
    return ["HARD_CORE_PARAM_ALL " + m for m in res["mismatches"]]


def _find_root(bind_dir, plan_rel):
    bf = Path(bind_dir) / "bind.f"
    if not bf.is_file() or not plan_rel:
        return None
    seen = set()
    for ln in bf.read_text().split():
        for a in Path(ln).parents:
            if a in seen:
                break
            seen.add(a)
            if (a / plan_rel).is_file():
                return a
    return None


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("bind_dir")
    ap.add_argument("--plan")
    ap.add_argument("--root")
    ap.add_argument("--defines", default="")
    ap.add_argument("--src-remap", action="append", default=[], metavar="OLD=NEW",
                    help="a bind.f source tree that was removed: read the same relative files from NEW")
    ap.add_argument("--json")
    a = ap.parse_args(argv)
    bd = Path(a.bind_dir)
    prov = (_json(bd / "provenance_bind.json") or {}).get("provenance", {})
    plan_rel = prov.get("plan")
    root = Path(a.root) if a.root else _find_root(bd, plan_rel)
    if not root:
        sys.exit("cannot find the code tree root: pass --root")
    plan_path = Path(a.plan) if a.plan else root / plan_rel
    plan = json.load(open(plan_path))
    defines = [d for d in a.defines.split(",") if d]
    mdefs, hard = manifest_info(prov.get("manifest"), root)
    defines = defines or mdefs
    rep = _json(bd / "bind_report.json") or {}
    modules = {tn: v.get("module") for tn, v in (rep.get("types") or {}).items() if isinstance(v, dict)}
    res = check_plan(plan, bd, root, defines=defines, hard_params=hard, modules=modules,
                     remap=[tuple(x.split("=", 1)) for x in a.src_remap])
    for m in res["mismatches"]:
        print("HARD_CORE_PARAM_ALL", m)
    print("HARD_CORE_PARAM_ALL_SUM", str(bd), "die", res["die"], "owner", res["owner"], "rows", res["rows_total"], "checked",
          res["rows_checked"], "macro", res["macro"], "unchecked_allowlisted", res["allowed"], "no_record_modules",
          len(res["no_record"]), "no_built_record", res["no_built"], "not_found", res["not_found"], "unresolved_values",
          res["unresolved"], "shared_view_diffs", res["shared"], "mismatches", len(res["mismatches"]))
    for why, mods in sorted(res["no_built_why"].items(), key=lambda kv: -sum(kv[1].values())):
        print("HARD_CORE_PARAM_ALL_NOBUILT", why, "rows", sum(mods.values()), "modules", len(mods),
              ",".join(f"{m}:{n}" for m, n in sorted(mods.items(), key=lambda kv: -kv[1])[:6]))
    if a.json:
        Path(a.json).write_text(json.dumps(res, indent=1))
    return 1 if res["mismatches"] else 0


if __name__ == "__main__":
    sys.exit(main())
