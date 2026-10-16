#!/usr/bin/env python3
"""die_port_bind: does a generated die netlist bind to REAL RTL?  (owner rule 2026-10-14 08:05 PT, "NO STUBS": every die
target -- Qwen compute die, Qwen KV/system die, S81, HBM -- must pass this before a die result counts.)

Input: the die's structural netlist (die.v of a die kit, or a die_top_lint top) and the RTL that is meant to implement
every master (default: every *.sv / *.v under rtl/, minus test benches; plus --rtl-file / -f lists for generated glue,
macro behavioural models etc.).  For every instance of the die top:

  * BIND     the master has exactly one RTL module definition (no definition = UNBOUND; several different headers =
             AMBIGUOUS unless --prefer picks the file);
  * STUB     the module has no behaviour: no always / assign of a non-constant / child instance (a pin-only shell,
             black box, placeholder or tie-off module).  A hard-macro model is allowed only as a CHILD of real RTL
             (--allow-model MODULE: e.g. an analog PHY or a ROM bit array) -- the die master itself must be real;
  * PORTS    every port the die connects exists in the RTL (DIE_PORT_NOT_IN_RTL), every RTL input is connected
             (INPUT_UNCONNECTED), no input bit is tied to a constant / 'z by the die (INPUT_TIED), outputs left open are
             listed (OUTPUT_OPEN, informational);
  * WIDTHS   die connection width == RTL port width evaluated with the INSTANCE's parameter overrides (#(...)) over the
             module's defaults (WIDTH_MISMATCH);
  * PADS     DEDUPE (owner rule 19:50 10-15, fewer distinct tiles): a standard master used below its width may tie its
             DECLARED spare input bits low (--pad-file / DIE_V.pads.json, per master with a reason and per-port bit ranges
             or a logical width); undeclared ties, ties high and 'z stay INPUT_TIED; spare outputs are OUTPUT_OPEN
             (informational) as before;
  * NETS     bit-level: every die-net bit read by an input has exactly one driver (an output port of a bound instance or a
             top input) -- UNDRIVEN / MULTI_DRIVEN.

Exit 0 only when every count is zero (OUTPUT_OPEN excepted).  JSON record with --out.

    python3 tools/die_port_bind.py DIE_V [--top dsfd_die] [--rtl-root rtl ...] [--rtl-file F ...] [-f FILELIST ...]
                                   [--define NAME ...] [--allow-model MODULE ...] [--prefer FILE ...] --out JSON
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = 'opentallas.die_port_bind.v2'


# ------------------------------------------------------------------------------------------------ text helpers
def _lexical_mask(text: str, strings=False) -> str:
    """Blank comments (and optionally strings), preserving offsets and newlines."""
    chars = list(text)
    i = 0
    while i < len(text):
        start = i
        if text[i] == "\\":
            # Escaped identifiers end at whitespace; comment markers inside
            # their spelling are not lexical comments.
            i += 1
            while i < len(text) and not text[i].isspace():
                i += 1
            continue
        if text[i] == '"':
            i += 1
            while i < len(text):
                if text[i] == "\\":
                    i += 2
                elif text[i] == '"':
                    i += 1
                    break
                else:
                    i += 1
            else:
                raise ValueError('unterminated SystemVerilog string')
            blank = strings
        elif text.startswith('//', i):
            end = text.find('\n', i)
            i = len(text) if end < 0 else end
            blank = True
        elif text.startswith('/*', i):
            end = text.find('*/', i + 2)
            if end < 0:
                raise ValueError('unterminated SystemVerilog comment')
            i = end + 2
            blank = True
        else:
            i += 1
            continue
        if blank:
            chars[start:i] = ['\n' if c == '\n' else ' ' for c in text[start:i]]
    return ''.join(chars)


def strip_comments(t: str) -> str:
    return _lexical_mask(t)


def _closing_paren(text, start):
    masked = _lexical_mask(text, strings=True)
    depth = 0
    for i in range(start, len(masked)):
        if masked[i] == '(':
            depth += 1
        elif masked[i] == ')':
            depth -= 1
            if depth == 0:
                return i
    raise ValueError('unterminated SystemVerilog module header')


def preprocess(t: str, defines: dict) -> str:
    """`define / `ifdef / `ifndef / `elsif / `else / `endif (nested); `include and other directives dropped."""
    out, stack = [], []          # stack of (taking, any_taken)
    for line in t.split('\n'):
        s = line.strip()
        m = re.match(r'`(ifdef|ifndef|elsif|else|endif|define|undef|include|timescale|default_nettype|resetall)\b\s*(\w*)\s*(.*)', s)
        live = all(x[0] for x in stack)
        if not m:
            out.append(line if live else '')
            continue
        d, name, rest = m.groups()
        if d in ('ifdef', 'ifndef'):
            c = (name in defines) == (d == 'ifdef')
            stack.append([c, c])
        elif d == 'elsif':
            top = stack[-1]
            c = (not top[1]) and name in defines
            top[0] = c; top[1] = top[1] or c
        elif d == 'else':
            top = stack[-1]
            top[0] = not top[1]; top[1] = True
        elif d == 'endif':
            stack.pop()
        elif d == 'define' and live:
            defines[name] = rest.strip()
        elif d == 'undef' and live:
            defines.pop(name, None)
        out.append('')
    t = '\n'.join(out)
    # simple object-like macro use (`NAME) -> its text
    for _ in range(3):
        t2 = re.sub(r'`(\w+)', lambda m: defines.get(m.group(1), m.group(0)), t)
        if t2 == t:
            break
        t = t2
    return t


# ------------------------------------------------------------------------------------------------ expressions
def _clog2(x):
    x = int(x)
    return 0 if x <= 1 else (x - 1).bit_length()


def _split_top(expr, ch):
    depth = 0
    for i, c in enumerate(expr):
        if c in '([{':
            depth += 1
        elif c in ')]}':
            depth -= 1
        elif c == ch and depth == 0:
            return i
    return -1


def _ternary(e: str) -> str:
    """Verilog ?: -> Python conditional expressions, at every nesting level (inside parentheses too)"""
    e = e.strip()
    q = _split_top(e, '?')
    if q >= 0:
        rest = e[q + 1:]
        # the ':' that matches this '?' (nested ternaries in the false arm are right-associative)
        depth, nest, col = 0, 0, -1
        for i, c in enumerate(rest):
            if c in '([{':
                depth += 1
            elif c in ')]}':
                depth -= 1
            elif depth == 0 and c == '?':
                nest += 1
            elif depth == 0 and c == ':':
                if nest == 0:
                    col = i
                    break
                nest -= 1
        if col >= 0:
            return f'(({_ternary(rest[:col])}) if ({_ternary(e[:q])}) else ({_ternary(rest[col + 1:])}))'
    out, i = [], 0
    while i < len(e):                       # recurse into each top-level parenthesised group
        if e[i] == '(':
            depth, k = 0, i
            while k < len(e):
                if e[k] == '(':
                    depth += 1
                elif e[k] == ')':
                    depth -= 1
                    if depth == 0:
                        break
                k += 1
            out.append('(' + _ternary(e[i + 1:k]) + ')')
            i = k + 1
        else:
            out.append(e[i]); i += 1
    return ''.join(out)


def to_py(expr: str) -> str:
    e = _ternary(expr)
    e = re.sub(r"(\d+)?'[sS]?([dDhHbBoO])([0-9a-fA-F_xXzZ]+)",
               lambda m: str(int(m.group(3).replace('_', '').replace('x', '0').replace('X', '0').replace('z', '0')
                                 .replace('Z', '0'), {'d': 10, 'h': 16, 'b': 2, 'o': 8}[m.group(2).lower()])), e)
    e = e.replace('$clog2', '_clog2').replace('&&', ' and ').replace('||', ' or ')
    e = re.sub(r'!(?!=)', ' not ', e)
    e = re.sub(r'(?<![<>!=/])/(?!/)', '//', e)
    return e


def ev(expr: str, env: dict):
    try:
        return int(eval(to_py(expr), {'_clog2': _clog2, '__builtins__': {}}, dict(env)))
    except Exception:
        return None


# ------------------------------------------------------------------------------------------------ RTL modules
class Module:
    def __init__(self, name, path, params, ports, body, order):
        self.name, self.path, self.params, self.ports, self.body, self.order = name, path, params, ports, body, order
        self._kind = None

    def env(self, overrides=None):
        env = {}
        ov = dict(overrides or {})
        for _ in range(6):
            for k, v in self.params.items():
                if k in ov:
                    x = ev(str(ov[k]), env) if not isinstance(ov[k], int) else ov[k]
                else:
                    x = ev(v, env)
                if x is not None:
                    env[k] = x
        return env

    def width(self, port, env):
        d, rng = self.ports[port]
        if not rng:
            return 1
        tot = 1
        for r in rng:
            hi, lo = r
            a, b = ev(hi, env), ev(lo, env)
            if a is None or b is None:
                return None
            tot *= abs(a - b) + 1
        return tot

    def children(self, idx):
        out = set()
        for m in re.finditer(r'(?:^|;|\bbegin\b|\bend\b|\)|:)\s*(\w+)', self.body, re.M):
            if m.group(1) in idx and m.group(1) != self.name:
                out.add(m.group(1))
        return out

    def kind(self, idx):
        """real | stub (no behaviour).  Behaviour = an always block, a continuous assign of a non-constant, a
        generate-for / function-driven assign, or an instance of another known module."""
        if self._kind is not None:
            return self._kind
        b = self.body
        if re.search(r'\balways(_ff|_comb|_latch)?\b', b) or re.search(r'\binitial\b[^;]*\$readmem', b):
            self._kind = 'real'; return 'real'
        for m in re.finditer(r'\bassign\b([^;]*)=([^;]*);', b):
            rhs = m.group(2).strip()
            if not re.fullmatch(r"[\s{}(),\d'bBhHdDoOxXzZ_]*", rhs):
                self._kind = 'real'; return 'real'
        for m in re.finditer(r'^\s*(\w+)\s*(#\s*\(.*?\)\s*)?\w+\s*\(', b, re.M | re.S):
            if m.group(1) in idx and m.group(1) != self.name:
                self._kind = 'real'; return 'real'
        # gate primitives count as behaviour (a hand netlist)
        if re.search(r'^\s*(and|or|nand|nor|xor|xnor|not|buf|bufif[01])\s+\w*\s*\(', b, re.M):
            self._kind = 'real'; return 'real'
        self._kind = 'stub'
        return 'stub'


def _range_colon(x):
    """Index of the msb:lsb colon of one packed range: the first ':' outside parentheses that does not close a
    ternary ('[((N>0)?N:1)-1:0]' splits at the last colon, not inside the conditional)."""
    depth = tern = 0
    for i, c in enumerate(x):
        if c in '([{':
            depth += 1
        elif c in ')]}':
            depth -= 1
        elif depth == 0 and c == '?':
            tern += 1
        elif depth == 0 and c == ':':
            if tern:
                tern -= 1
            else:
                return i
    return -1


def _parse_ranges(s):
    out = []
    for x in re.findall(r'\[((?:[^\[\]]|\[[^\]]*\])+)\]', s or ''):
        i = _range_colon(x)
        out.append((x[:i], x[i + 1:]) if i >= 0 else (x, x))
    return out


def parse_modules(text: str, path: str):
    text = strip_comments(text)
    masked = _lexical_mask(text, strings=True)
    mods = []
    for m in re.finditer(r'\bmodule\s+(\w+)\s*', masked):
        name = m.group(1)
        em = re.search(r'\bendmodule\b', masked[m.end():])
        end = m.end() + em.start() if em else -1
        if end < 0:
            continue
        seg = text[m.end():end]
        params = {}
        i = 0
        if seg.lstrip().startswith('#'):
            j = seg.find('(')
            k = _closing_paren(seg, j)
            plist = seg[j + 1:k]
            for item in _split_commas(plist):
                pm = re.match(r'\s*(?:parameter|localparam)?\s*(?:integer|int|logic|bit|signed|unsigned|real|string|\[[^\]]*\]\s*)*\s*(\w+)\s*=\s*(.+)$', item.strip(), re.S)
                if pm:
                    params[pm.group(1)] = pm.group(2).strip()
            i = k + 1
        j = seg.find('(', i)
        semi = seg.find(';', i)
        ports, order, port_errors = {}, [], []
        if j >= 0 and (semi < 0 or j < semi):
            k = _closing_paren(seg, j)
            plist = seg[j + 1:k]
            body = seg[k + 1:]
            cur = (None, [])
            for item in _split_commas(plist):
                it = item.strip()
                if not it:
                    continue
                pm = re.match(r'(input|output|inout)?\s*(wire|reg|logic|var)?\s*(signed|unsigned)?\s*((?:\[[^\]]+\]\s*)*)\s*(\\\S+|\w+)\s*((?:\[[^\]]+\]\s*)*)$', it, re.S)
                if not pm:
                    port_errors.append(it)
                    continue
                d, _, _, pr, pn, ur = pm.groups()
                if d:
                    cur = (d, _parse_ranges(pr) + _parse_ranges(ur))
                elif pr:
                    cur = (cur[0], _parse_ranges(pr) + _parse_ranges(ur))
                ports[pn] = cur if d or pr or cur[0] else (None, [])
                order.append(pn)
        else:
            body = seg[i:]
        # Declaration keywords inside strings must not resolve non-ANSI ports.
        body_masked = _lexical_mask(body, strings=True)
        # localparams / body parameters (non-ANSI parameter declarations)
        for pm in re.finditer(r'\b(?:parameter|localparam)\s+(?:integer\s+|int\s+|\[[^\]]*\]\s*)?([^;]+);', body_masked):
            for item in _split_commas(body[pm.start(1):pm.end(1)]):          # a declaration list: localparam A = .., B = .., C = ..;
                im = re.match(r'\s*(\w+)\s*=\s*(.+)$', item, re.S)
                if im:
                    params.setdefault(im.group(1), im.group(2).strip())
        # non-ANSI port declarations in the body
        for pm in re.finditer(r'\b(input|output|inout)\s+(?:wire\s+|reg\s+|logic\s+)?(?:signed\s+)?((?:\[[^\]]+\]\s*)*)([^;]+);', body_masked):
            for pn in _split_commas(pm.group(3)):
                pn = pn.strip().split('=')[0].strip()
                if pn in ports and ports[pn][0] is None:
                    ports[pn] = (pm.group(1), _parse_ranges(pm.group(2)))
        parsed = Module(name, path, params, ports, body, order)
        parsed.port_parse_errors = port_errors
        mods.append(parsed)
    return mods


def _split_commas(s):
    out, depth, cur = [], 0, []
    masked = _lexical_mask(s, strings=True)
    for i, c in enumerate(s):
        token = masked[i]
        if token in '([{':
            depth += 1
        elif token in ')]}':
            depth -= 1
        if token == ',' and depth == 0:
            out.append(''.join(cur)); cur = []
        else:
            cur.append(c)
    out.append(''.join(cur))
    return out


def rtl_index(roots, files, defines, prefer):
    idx = defaultdict(list)
    paths = []
    for r in roots:
        rp = (ROOT / r) if not Path(r).is_absolute() else Path(r)
        for p in sorted(list(rp.rglob('*.sv')) + list(rp.rglob('*.v'))):
            s = str(p)
            if ('/test/' in s or '/tests/' in s or p.name.startswith('tb_') or p.name.endswith('_bb.v')
                    or (p.name.startswith('tb') and p.name[2:3] in '_.')):
                continue
            paths.append(p)
    paths += [Path(f) if Path(f).is_absolute() else ROOT / f for f in files]
    for p in paths:
        try:
            t = p.read_text(errors='replace')
        except Exception:
            continue
        if 'module' not in t:
            continue
        t = preprocess(strip_comments(t), dict(defines))
        for mod in parse_modules(t, str(p)):
            idx[mod.name].append(mod)
    pref = {str(Path(f).resolve()) for f in prefer}
    out, amb = {}, {}
    for name, defs in idx.items():
        pd = [d for d in defs if str(Path(d.path).resolve()) in pref]
        if pd:
            out[name] = pd[-1]; continue
        sigs = {tuple(sorted((k, v[0]) for k, v in d.ports.items())) for d in defs}
        out[name] = defs[0]
        if len(sigs) > 1:
            amb[name] = sorted({d.path for d in defs})
    return out, amb


# ------------------------------------------------------------------------------------------------ die netlist
class Conn:
    __slots__ = ('bits',)

    def __init__(self, bits):
        self.bits = bits           # list of (net, bit) MSB-first, or ('CONST', v) / ('Z', None)


def parse_die(path, top=None):
    t = strip_comments(Path(path).read_text(errors='replace'))
    mods = list(re.finditer(r'\bmodule\s+(\w+)', t))
    if top:
        mm = [m for m in mods if m.group(1) == top]
        if not mm:
            raise SystemExit(f'die_port_bind: top {top} not in {path}')
        m0 = mm[0]
    else:
        m0 = mods[-1] if len(mods) > 1 else mods[0]
    end = t.find('endmodule', m0.end())
    body = t[m0.end():end]
    hdr_end = body.find(';')
    hdr, rest = body[:hdr_end], body[hdr_end + 1:]
    nets, tin, tout = {}, set(), set()
    insts = []
    for st in rest.split(';'):
        s = st.strip()
        if not s:
            continue
        m = re.match(r'(input|output|inout|wire|reg|logic|tri)\s+(?:wire\s+|logic\s+)?((?:\[[^\]]+\]\s*)?)(.*)$', s, re.S)
        if m:
            rng = re.match(r'\[\s*(\d+)\s*:\s*(\d+)\s*\]', m.group(2) or '')
            w = abs(int(rng.group(1)) - int(rng.group(2))) + 1 if rng else 1
            lo = min(int(rng.group(1)), int(rng.group(2))) if rng else 0
            for n in _split_commas(m.group(3)):
                n = n.strip()
                if n:
                    nets[n] = (w, lo)
                    if m.group(1) == 'input':
                        tin.add(n)
                    elif m.group(1) == 'output':
                        tout.add(n)
            continue
        if s.startswith('assign'):
            insts.append(('__assign__', s, {}, {}))
            continue
        m = re.match(r'(\\\S+|\w+)\s*(#\s*\((.*?)\)\s*)?(\\\S+\s|\w+)\s*\((.*)\)\s*$', s, re.S)
        if not m:
            continue
        mst, _, prm, inst, conns = m.groups()
        params = {}
        if prm:
            for pm in re.finditer(r'\.(\w+)\s*\(([^()]*(?:\([^()]*\))?[^()]*)\)', prm):
                params[pm.group(1)] = pm.group(2).strip()
        cm = {}
        for c in _named_conns(conns):
            cm[c[0]] = c[1]
        insts.append((mst, inst.strip(), params, cm))
    for n in re.findall(r'(\\\S+|\w+)', hdr):
        pass
    return nets, tin, tout, insts


def _named_conns(s):
    i, n = 0, len(s)
    while i < n:
        j = s.find('.', i)
        if j < 0:
            return
        k = j + 1
        if k < n and s[k] == '\\':
            e = k
            while e < n and not s[e].isspace():
                e += 1
            name = s[k:e]
            k = e
        else:
            mm = re.match(r'\w+', s[k:])
            if not mm:
                i = k; continue
            name = mm.group(0); k += len(name)
        while k < n and s[k].isspace():
            k += 1
        if k >= n or s[k] != '(':
            i = k; continue
        depth, e = 0, k
        while e < n:
            if s[e] == '(':
                depth += 1
            elif s[e] == ')':
                depth -= 1
                if depth == 0:
                    break
            e += 1
        yield name, s[k + 1:e].strip()
        i = e + 1


def expr_bits(expr, nets):
    """die connection expression -> list of bits MSB-first: (net, i) | ('CONST', b) | ('Z', None); None = unparsable."""
    e = expr.strip()
    if not e:
        return []
    if e.startswith('{') and e.endswith('}'):
        inner = e[1:-1].strip()
        rep = re.match(r'(\d+)\s*\{(.*)\}$', inner, re.S)
        if rep:
            b = expr_bits('{' + rep.group(2) + '}', nets)
            return None if b is None else b * int(rep.group(1))
        out = []
        for part in _split_commas(inner):
            b = expr_bits(part, nets)
            if b is None:
                return None
            out += b
        return out
    m = re.fullmatch(r"(\d+)'[sS]?([bBhHdDoO])([0-9a-fA-F_xXzZ?]+)", e)
    if m:
        w = int(m.group(1)); base = m.group(2).lower(); v = m.group(3).replace('_', '')
        if set(v.lower()) <= {'z', '?'}:
            return [('Z', None)] * w
        val = int(re.sub('[xXzZ?]', '0', v), {'b': 2, 'h': 16, 'd': 10, 'o': 8}[base])
        return [('CONST', (val >> (w - 1 - i)) & 1) for i in range(w)]
    if re.fullmatch(r"'[01zZxX]|\d+", e):
        return [('CONST', 0)]
    m = re.fullmatch(r'(\\\S+|\w+)\s*(?:\[\s*(\d+)\s*(?::\s*(\d+)\s*)?\])?', e)
    if m:
        n = m.group(1)
        if n not in nets:
            return [('UNDECL', n)]
        w, lo = nets[n]
        if m.group(2) is None:
            return [(n, i) for i in range(lo + w - 1, lo - 1, -1)]
        a = int(m.group(2)); b = int(m.group(3)) if m.group(3) is not None else a
        step = -1 if a >= b else 1
        return [(n, i) for i in range(a, b + step, step)]
    return None


# ------------------------------------------------------------------------------------------------ check
def pad_bits(spec, width):
    """port-relative bit indexes (LSB = 0) a PAD declaration covers: [[lo, hi], ...] or {"logical_width": L} (bits
    L .. width-1)"""
    if isinstance(spec, dict):
        L = int(spec["logical_width"])
        return set(range(L, width if width is not None else L))
    out = set()
    for lo, hi in spec:
        out |= set(range(min(int(lo), int(hi)), max(int(lo), int(hi)) + 1))
    return out


def load_pads(obj):
    """{"pads": {master: {"reason": str, "ports": {port: [[lo, hi], ...] | {"logical_width": L}}}}} ->
    {(master, port): spec}.  DEDUPE padding (main f041848a1, owner rule 19:50 'fewer distinct tiles'): a standard master
    replicated at a smaller logical width ties its spare INPUT bits low and leaves its spare OUTPUT bits open; only the
    declared bits may be tied (to 0), everything else stays INPUT_TIED.  A master entry without a reason is refused."""
    pads = {}
    for mst, ent in (obj.get("pads", obj) if isinstance(obj, dict) else {}).items():
        if not isinstance(ent, dict) or not str(ent.get("reason", "")).strip() or not isinstance(ent.get("ports"), dict):
            raise SystemExit(f"die_port_bind: pad declaration for {mst} needs a reason and a ports map")
        for pn, spec in ent["ports"].items():
            pads[(mst, pn)] = spec
    return pads


def check(die_v, top, idx, amb, allow_model, mparams=None, max_list=40, straps=frozenset(), pads=None):
    """straps: {(master, port)} declared STRAP inputs (die constants by contract: tile ids, station indexes, group
    numbers); a constant on one of them is recorded as a strap, not as INPUT_TIED.  pads: {(master, port): bit spec}
    declared PAD bits (load_pads): a constant 0 on a declared input bit is a pad bit, not INPUT_TIED; a tie to 1 / 'z, or
    on any undeclared bit, still fails.  Every other tied input fails."""
    pads = pads or {}
    nets, tin, tout, insts = parse_die(die_v, top)
    mparams = mparams or {}
    drv = defaultdict(int)       # (net) -> bitmask of driven bits (by count via lists below)
    drv_cnt = defaultdict(lambda: defaultdict(int))
    io_cnt = defaultdict(lambda: defaultdict(int))
    rd = defaultdict(set)
    for n in tin:
        w, lo = nets[n]
        for i in range(lo, lo + w):
            drv_cnt[n][i] += 1
    masters = {}
    findings = defaultdict(list)
    for mst, inst, params, cm in insts:
        if mst == '__assign__':
            findings['TOP_ASSIGN'].append(inst[:200])
            continue
        rec = masters.setdefault(mst, dict(instances=0, rtl=None, kind=None, param_sets={}, examples=[],
                                           die_port_not_in_rtl=set(), input_unconnected=set(), input_tied=set(),
                                           output_open=set(), width_mismatch={}, unparsed_conn=set(), straps=set(),
                                           pad_bits=defaultdict(int)))
        rec['instances'] += 1
        if len(rec['examples']) < 3:
            rec['examples'].append(inst)
        mod = idx.get(mst)
        if mod is None:
            rec['rtl'] = None
            continue
        rec['rtl'] = mod.path.replace(str(ROOT) + '/', '')
        rec['kind'] = 'model' if mst in allow_model else mod.kind(idx)
        if not params and mst in mparams:     # sidecar: the master's hardened elaboration parameters
            params = {k: v for k, v in mparams[mst].items() if not k.startswith('_')}
            unk = sorted(k for k in params if k not in mod.params)
            if unk:
                findings['PARAM_NOT_IN_RTL'].append(f'{mst}: {unk}')
        pkey = json.dumps(params, sort_keys=True)
        if pkey not in rec['param_sets']:
            rec['param_sets'][pkey] = 0
        rec['param_sets'][pkey] += 1
        env = mod.env(params)
        for pn, ex in cm.items():
            if pn not in mod.ports:
                rec['die_port_not_in_rtl'].add(pn)
                continue
            d = mod.ports[pn][0]
            bits = expr_bits(ex, nets) if ex else []
            if bits is None:
                rec['unparsed_conn'].add(pn)
                continue
            if not bits:
                if d == 'input':
                    rec['input_unconnected'].add(pn)
                elif d == 'output':
                    rec['output_open'].add(pn)
                continue
            w = mod.width(pn, env)
            if w is not None and w != len(bits):
                rec['width_mismatch'].setdefault(pn, set()).add((len(bits), w))
            pset = pad_bits(pads[(mst, pn)], w if w is not None else len(bits)) if (mst, pn) in pads else set()
            for k_msb, b in enumerate(bits):
                if b[0] in ('CONST', 'Z'):
                    if d != 'output':
                        if b[0] == 'CONST' and (mst, pn) in straps:
                            rec['straps'].add(pn)
                        elif b[0] == 'CONST' and b[1] == 0 and (len(bits) - 1 - k_msb) in pset:
                            rec['pad_bits'][pn] += 1
                        else:
                            rec['input_tied'].add(pn)
                elif b[0] == 'UNDECL':
                    rec['unparsed_conn'].add(pn)
                elif d == 'output':
                    drv_cnt[b[0]][b[1]] += 1
                elif d == 'input':
                    rd[b[0]].add(b[1])
                else:                                   # inout (a bundled pass-through face, e.g. a PHY DFI bundle):
                    io_cnt[b[0]][b[1]] += 1             # drives a bit only where no output port drives it
                    rd[b[0]].add(b[1])
        for pn, (d, _) in mod.ports.items():
            if pn not in cm:
                if d == 'input':
                    rec['input_unconnected'].add(pn)
                elif d == 'output':
                    rec['output_open'].add(pn)
    for n in tout:
        w, lo = nets[n]
        rd[n].update(range(lo, lo + w))
    for n, dc in io_cnt.items():
        for i, c in dc.items():
            if drv_cnt[n].get(i, 0) == 0:
                drv_cnt[n][i] += c
    undriven, multi = defaultdict(int), defaultdict(int)
    for n, bs in rd.items():
        dc = drv_cnt.get(n, {})
        for i in bs:
            c = dc.get(i, 0)
            if c == 0:
                undriven[n] += 1
            elif c > 1:
                multi[n] += 1
    for n, dc in drv_cnt.items():
        for i, c in dc.items():
            if c > 1 and i not in rd.get(n, ()):
                multi[n] += 1
    # ---------------- summary
    S = dict(masters=len(masters), instances=sum(r['instances'] for r in masters.values()),
             unbound_masters=0, stub_masters=0, ambiguous_masters=0, port_not_in_rtl=0, width_mismatch=0,
             input_unconnected=0, input_tied=0, unparsed_connections=0, undriven_net_bits=sum(undriven.values()),
             multi_driven_net_bits=sum(multi.values()), top_assigns=len(findings['TOP_ASSIGN']),
             params_not_in_rtl=len(findings['PARAM_NOT_IN_RTL']),
             strap_ports=sum(len(r['straps']) for r in masters.values()),
             pad_bits=sum(sum(r['pad_bits'].values()) for r in masters.values()))
    out_m = {}
    for mst, r in sorted(masters.items()):
        bad = []
        if r['rtl'] is None:
            S['unbound_masters'] += 1; bad.append('UNBOUND')
        else:
            if r['kind'] == 'stub':
                S['stub_masters'] += 1; bad.append('STUB')
            if mst in amb:
                S['ambiguous_masters'] += 1; bad.append('AMBIGUOUS')
        for key, tag in (('die_port_not_in_rtl', 'PORT_NOT_IN_RTL'), ('width_mismatch', 'WIDTH_MISMATCH'),
                         ('input_unconnected', 'INPUT_UNCONNECTED'), ('input_tied', 'INPUT_TIED'),
                         ('unparsed_conn', 'UNPARSED')):
            if r[key]:
                bad.append(tag)
                S[{'die_port_not_in_rtl': 'port_not_in_rtl', 'unparsed_conn': 'unparsed_connections'}.get(key, key)] += len(r[key])
        out_m[mst] = dict(verdict='PASS' if not bad else 'FAIL', fails=bad, instances=r['instances'], rtl=r['rtl'],
                          kind=r['kind'], ambiguous_defs=amb.get(mst), examples=r['examples'],
                          param_sets=dict(list(r['param_sets'].items())[:8]),
                          die_port_not_in_rtl=sorted(r['die_port_not_in_rtl'])[:max_list],
                          input_unconnected=sorted(r['input_unconnected'])[:max_list],
                          input_tied=sorted(r['input_tied'])[:max_list],
                          straps=sorted(r['straps'])[:max_list],
                          pad_bits=dict(sorted(r['pad_bits'].items())[:max_list]),
                          output_open=sorted(r['output_open'])[:max_list],
                          width_mismatch={p: sorted(v) for p, v in sorted(r['width_mismatch'].items())[:max_list]},
                          unparsed_conn=sorted(r['unparsed_conn'])[:max_list])
    fail_keys = [k for k in S if k not in ('masters', 'instances', 'strap_ports', 'pad_bits') and S[k]]
    return dict(schema=SCHEMA, die_v=str(die_v), top=top, verdict='PASS' if not fail_keys else 'FAIL',
                failing=fail_keys, summary=S, masters=out_m,
                undriven_nets=dict(sorted(undriven.items(), key=lambda kv: -kv[1])[:200]),
                undriven_classes=_classes(undriven), multi_driven_classes=_classes(multi),
                multi_driven_nets=dict(sorted(multi.items(), key=lambda kv: -kv[1])[:200]),
                top_assigns=findings['TOP_ASSIGN'][:20], params_not_in_rtl=findings['PARAM_NOT_IN_RTL'][:40])


def _classes(d):
    """net-name classes (digits collapsed) -> bits, all nets (the per-net lists above are capped)"""
    c = defaultdict(lambda: [0, 0, None])
    for n, v in d.items():
        k = re.sub(r'\d+', 'N', n)
        c[k][0] += v; c[k][1] += 1; c[k][2] = c[k][2] or n
    return {k: dict(bits=v[0], nets=v[1], example=v[2]) for k, v in sorted(c.items(), key=lambda kv: -kv[1][0])}


def elab_kit(die_v, top, idx, mparams, out_dir, defines):
    """die top with every master's sidecar parameters inline + the RTL file closure (Verilator file list): a FULL-RTL
    elaboration of the die (no stubs: a master without RTL stays unresolved and fails the elaboration)."""
    out_dir = Path(out_dir).resolve(); out_dir.mkdir(parents=True, exist_ok=True)
    text = Path(die_v).read_text(errors='replace')
    used = set()

    def sub(m):
        mst, rest = m.group(2), m.group(3)
        used.add(mst)
        prm = {k: v for k, v in mparams.get(mst, {}).items() if not k.startswith('_')}
        if not prm or rest.lstrip().startswith('#'):
            return m.group(0)
        ps = ', '.join(f'.{k}({v})' for k, v in prm.items())
        return f'{m.group(1)}{mst} #({ps}){rest}'
    text = re.sub(r'^(\s+)(\w+)(\s+(?:#\s*\(.*?\)\s*)?[\w\\]\S*\s*\()', sub, text, flags=re.M)
    # Verilator's preprocessor stops at 40,000 tokens a line: break the long bit-concatenation lines at their commas
    text = '\n'.join(ln if len(ln) < 4000 else ln.replace(', ', ',\n      ') for ln in text.split('\n'))
    (out_dir / 'die_top.sv').write_text(text)
    files, seen, todo, missing = [], set(), sorted(used), []
    while todo:
        n = todo.pop()
        if n in seen:
            continue
        seen.add(n)
        mod = idx.get(n)
        if mod is None:
            missing.append(n); continue
        if mod.path not in files:
            files.append(mod.path)
        todo += sorted(mod.children(idx) - seen)
    incs = sorted({str(Path(f).parent) for f in files})
    fl = [f'+incdir+{d}' for d in incs] + [f'+define+{d}' for d in defines] + files + [str(out_dir / 'die_top.sv')]
    (out_dir / 'die_top.f').write_text('\n'.join(fl) + '\n')
    return dict(files=len(files), unresolved_modules=sorted(missing), top_file=str(out_dir / 'die_top.sv'),
                file_list=str(out_dir / 'die_top.f'))


def load_manifest(fl):
    """a file list / die RTL manifest -> (files, defines, libdirs): '+define+A+B' build defines, '+libdir+DIR' hard-macro
    model libraries (indexed, not preferred), other non-comment lines = RTL files (preferred over other definitions)"""
    base = Path(fl).parent
    files, defines, libdirs = [], [], []
    for ln in Path(fl).read_text().split('\n'):
        ln = ln.strip()
        if ln.startswith('+define+'):
            defines += [d for d in ln[len('+define+'):].split('+') if d]
        elif ln.startswith('+libdir+'):
            libdirs.append(ln[len('+libdir+'):])
        elif ln and not ln.startswith(('#', '//', '+', '-')):
            p = Path(ln)
            files.append(str(p if p.is_absolute() or (ROOT / p).exists() else base / p))
    return files, defines, libdirs


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('die_v')
    ap.add_argument('--top')
    ap.add_argument('--rtl-root', action='append', default=None, help='RTL tree(s) to index (default rtl/)')
    ap.add_argument('--rtl-file', action='append', default=[], help='extra RTL file (generated glue, PHY models ...)')
    ap.add_argument('-f', dest='filelists', action='append', default=[], help='file list (one path a line)')
    ap.add_argument('--define', action='append', default=[])
    ap.add_argument('--allow-model', action='append', default=[],
                    help='module allowed to be a behavioural model (hard analog / bit-array core); only meaningful as a '
                         'child: a die-level master named here is still reported as kind=model')
    ap.add_argument('--prefer', action='append', default=[], help='file whose definition wins over duplicates')
    ap.add_argument('--params', help='master parameter sidecar {"masters": {master: {param: value}}} '
                                      '(default: DIE_V.params.json when present; inline #(...) on an instance wins)')
    ap.add_argument('--elab-out', help='write DIR/die_top.sv (sidecar parameters inline) + DIR/die_top.f (RTL closure) '
                                       'for a full-RTL Verilator elaboration of the die')
    ap.add_argument('--closure', action='append', default=[], help='print the RTL file closure of MODULE (no die check)')
    ap.add_argument('--strap', action='append', default=[], help='MASTER:PORT declared strap input (a die constant by '
                    'contract, e.g. a tile id); a constant on it is recorded, not INPUT_TIED')
    ap.add_argument('--strap-file', help='JSON [[master, port], ...] or {"straps": [[master, port], ...]}')
    ap.add_argument('--pad-file', help='JSON {"pads": {master: {"reason": ..., "ports": {port: [[lo, hi], ...] | '
                    '{"logical_width": L}}}}}: declared DEDUPE padding bits (spare inputs tied low, spare outputs open); '
                    'default DIE_V.pads.json beside the die netlist (like DIE_V.params.json)')
    ap.add_argument('--out')
    a = ap.parse_args(argv)
    a.pad_file = a.pad_file or (a.die_v + '.pads.json' if Path(a.die_v + '.pads.json').exists() else None)
    pads = load_pads(json.loads(Path(a.pad_file).read_text())) if a.pad_file else {}
    straps = {tuple(s.split(':', 1)) for s in a.strap}
    if a.strap_file:
        sj = json.loads(Path(a.strap_file).read_text())
        straps |= {tuple(x) for x in (sj.get('straps', []) if isinstance(sj, dict) else sj)}
    files = list(a.rtl_file)
    libdirs = []
    for fl in a.filelists:
        f_, d_, l_ = load_manifest(fl)
        files += f_; a.define += d_; libdirs += l_
    defines = {}
    for d in a.define:
        k, _, v = d.partition('=')
        defines[k] = v
    roots = a.rtl_root if a.rtl_root is not None else (['rtl'] + sorted(str(p.relative_to(ROOT)) for p in (ROOT / 'physical').glob('**/rtl')
                                                                  if p.is_dir()))
    roots = roots + libdirs
    idx, amb = rtl_index(roots, files, defines, a.prefer + files)
    if a.closure:
        seen, todo, files_ = set(), list(a.closure), []
        while todo:
            n = todo.pop()
            if n in seen or n not in idx:
                continue
            seen.add(n)
            if idx[n].path not in files_:
                files_.append(idx[n].path)
            todo += sorted(idx[n].children(idx) - seen)
        print('\n'.join(files_))
        return 0
    pj = a.params or (a.die_v + '.params.json' if Path(a.die_v + '.params.json').exists() else None)
    mparams = json.loads(Path(pj).read_text()).get('masters', {}) if pj else {}
    rec = check(a.die_v, a.top, idx, amb, set(a.allow_model), mparams, straps=frozenset(straps), pads=pads)
    rec['pads_declared'] = sorted(':'.join(k) for k in pads)
    rec['die_sha256'] = hashlib.sha256(Path(a.die_v).read_bytes()).hexdigest()
    rec['straps_declared'] = sorted(':'.join(s) for s in straps)
    rec['params_file'] = pj
    if a.elab_out:
        rec['elab'] = elab_kit(a.die_v, a.top, idx, mparams, a.elab_out, a.define)
        if rec['elab']['unresolved_modules']:
            rec['verdict'] = 'FAIL'
            rec['failing'].append('elab_unresolved_modules')
    rec['rtl_roots'] = roots; rec['rtl_files'] = files; rec['defines'] = a.define
    if a.out:
        Path(a.out).write_text(json.dumps(rec, indent=1) + '\n')
    S = rec['summary']
    for mst, r in rec['masters'].items():
        if r['verdict'] != 'PASS':
            det = []
            if r['die_port_not_in_rtl']:
                det.append('not_in_rtl=' + ','.join(r['die_port_not_in_rtl'][:8]))
            if r['width_mismatch']:
                det.append('width=' + ','.join(f'{p}:{v[0][0]}vs{v[0][1]}' for p, v in list(r['width_mismatch'].items())[:6]))
            if r['input_unconnected']:
                det.append('in_unconn=' + ','.join(r['input_unconnected'][:8]))
            if r['input_tied']:
                det.append('tied=' + ','.join(r['input_tied'][:8]))
            print(f"FAIL {mst:34s} x{r['instances']:<6d} {'/'.join(r['fails'])} {' '.join(det)}")
    print('DIE_PORT_BIND ' + rec['verdict'] + ' ' + ' '.join(f'{k}={v}' for k, v in S.items()))
    return 0 if rec['verdict'] == 'PASS' else 1


if __name__ == '__main__':
    sys.exit(main())
