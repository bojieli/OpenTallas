#!/usr/bin/env python3
"""Parse a hierarchical yosys netlist (write_verilog -noattr), and for the SM top module derive
child-to-child bit connections plus whether each child port bit is register-launched / register-captured.
Usage: net_analyze.py netlist.v top_module_substring out.json
"""
import re, sys, json, collections

src = open(sys.argv[1]).read()
TOPSUB = sys.argv[2]
def norm(n):
    n = n.strip()
    return n[1:] if n.startswith('\\') else n
mods = {}
for m in re.finditer(r'^module (\S+)\s*\((.*?)\);\n(.*?)^endmodule', src, re.S | re.M):
    mods[norm(m.group(1))] = m.group(3)
print('modules', len(mods), file=sys.stderr)

ident = r'(?:\\\S+|[A-Za-z_][A-Za-z0-9_$]*)'
decl_re = re.compile(r'^\s*(input|output|inout|wire|reg)\s+(?:signed\s+)?(?:\[(-?\d+):(-?\d+)\]\s+)?(' + ident + r')\s*;', re.M)
inst_re = re.compile(r'^\s*(' + ident + r')\s+(' + ident + r')\s*\((.*?)\);', re.M | re.S)
pin_re = re.compile(r'\.(' + ident + r')\s*\((.*?)\)\s*(?:,|$)', re.S)
assign_re = re.compile(r'^\s*assign\s+(.*?)\s*=\s*(.*?);', re.M | re.S)


class Mod:
    pass

def split_top(s):
    out, depth, cur = [], 0, ''
    for ch in s:
        if ch == '{': depth += 1
        if ch == '}': depth -= 1
        if ch == ',' and depth == 0:
            out.append(cur); cur = ''
        else:
            cur += ch
    if cur.strip(): out.append(cur)
    return out

parsed = {}
def parse(name):
    if name in parsed: return parsed[name]
    body = mods[name]
    M = Mod(); M.name = name; M.w = {}; M.dir = {}; M.lo = {}
    for d in decl_re.finditer(body):
        kind, hi, lo, n = d.group(1), d.group(2), d.group(3), norm(d.group(4))
        hi = int(hi) if hi is not None else 0; lo = int(lo) if lo is not None else 0
        M.w[n] = abs(hi - lo) + 1; M.lo[n] = min(hi, lo)
        if kind in ('input', 'output', 'inout'): M.dir[n] = kind
    def bits(expr):
        expr = expr.strip()
        if not expr: return []
        if expr.startswith('{'):
            r = []
            for p in split_top(expr[1:-1]): r += bits(p)
            return r
        mc = re.match(r"^(\d+)'([hbdo])([0-9a-fA-FxzXZ_]+)$", expr)
        if mc:
            w = int(mc.group(1)); return [('CONST', i) for i in range(w)][::-1]
        ms = re.match(r'^(' + ident + r')\s*(?:\[(\d+)(?::(\d+))?\])?$', expr)
        if not ms: raise ValueError(expr)
        n = norm(ms.group(1))
        if ms.group(2) is None:
            w = M.w.get(n, 1); lo = M.lo.get(n, 0)
            return [(n, lo + i) for i in range(w)][::-1]
        hi = int(ms.group(2)); lo = int(ms.group(3)) if ms.group(3) else hi
        step = -1 if hi >= lo else 1
        return [(n, i) for i in range(hi, lo + step, step)]
    M.bits = bits
    M.insts = []
    for im in inst_re.finditer(body):
        typ, iname, conns = norm(im.group(1)), norm(im.group(2)), im.group(3)
        if typ in ('module', 'assign', 'input', 'output', 'wire', 'reg'): continue
        pins = {}
        for pm in pin_re.finditer(conns):
            pins[norm(pm.group(1))] = bits(pm.group(2))
        M.insts.append((typ, iname, pins))
    M.assigns = []
    for am in assign_re.finditer(body):
        l, r = bits(am.group(1)), bits(am.group(2))
        if len(r) < len(l): r = [('CONST', 0)] * (len(l) - len(r)) + r
        r = r[-len(l):] if len(l) else r
        M.assigns += list(zip(l, r))
    # net graph: driver per bit, sinks per bit
    M.drv = {}; M.snk = collections.defaultdict(list)
    for n, d in M.dir.items():
        lo = M.lo[n]
        for i in range(M.w[n]):
            if d == 'input': M.drv[(n, lo + i)] = ('PORT', n, lo + i)
            else: M.snk[(n, lo + i)].append(('PORT', n, lo + i))
    for l, r in M.assigns:
        M.drv[l] = ('ASSIGN', r)
        M.snk[r].append(('ASSIGN', l))
    for k, (typ, iname, pins) in enumerate(M.insts):
        for p, bl in pins.items():
            od = pdir(typ, p)
            if typ in mods:
                cm = parse(typ); w = cm.w.get(p, len(bl)); lo = cm.lo.get(p, 0)
                for j, b in enumerate(bl):
                    pb = lo + (len(bl) - 1 - j)
                    if od == 'output': M.drv[b] = ('INST', k, p, pb)
                    else: M.snk[b].append(('INST', k, p, pb))
            else:
                for b in bl:
                    if od == 'output': M.drv[b] = ('INST', k, p, 0)
                    else: M.snk[b].append(('INST', k, p, 0))
    parsed[name] = M
    return M

OUTPINS = {'Y', 'QN', 'Q', 'CON', 'SN', 'YN', 'QD'}
def pdir(typ, p):
    if typ in mods:
        return parse(typ).dir.get(p, 'input')
    return 'output' if p in OUTPINS else 'input'

def is_ff(t): return t.startswith('DFF') or t.startswith('ot_sram') or t.startswith('DHL') or t.startswith('DLL')
def is_buf(t): return t.startswith('INV') or t.startswith('BUF') or t.startswith('HB')

memo_o, memo_i = {}, {}
def out_kind(mname, port, b, depth=0):
    """how output port bit of module mname is driven: set of {'reg','logic','in:<port>'}"""
    key = (mname, port, b)
    if key in memo_o: return memo_o[key]
    memo_o[key] = {'reg'}  # cycle guard
    M = parse(mname)
    res = trace_drv(M, (port, b), depth)
    memo_o[key] = res
    return res

def trace_drv(M, bit, depth, seen=None):
    seen = seen or set()
    if bit in seen: return {'logic'}
    seen.add(bit)
    d = M.drv.get(bit)
    if d is None: return {'undriven'}
    if d[0] == 'PORT': return {'in:' + d[1]}
    if d[0] == 'ASSIGN':
        if d[1][0] == 'CONST': return {'const'}
        return trace_drv(M, d[1], depth, seen)
    typ, iname, pins = M.insts[d[1]]
    if typ in mods:
        r = out_kind(typ, d[2], d[3], depth + 1)
        out = set()
        for x in r:
            if x.startswith('in:'):
                ip = x[3:]
                # follow the child's input back in this module (feedthrough across child)
                cm = parse(typ); bl = pins.get(ip, [])
                # conservative: comb feedthrough across a child = logic
                out.add('logic')
            else: out.add(x)
        return out
    if is_ff(typ): return {'reg'}
    if is_buf(typ):
        inp = [b for p, bl in pins.items() if pdir(typ, p) == 'input' for b in bl]
        out = set()
        for b in inp: out |= trace_drv(M, b, depth, seen)
        return out
    return {'logic'}

def in_kind(mname, port, b):
    key = (mname, port, b)
    if key in memo_i: return memo_i[key]
    memo_i[key] = {'reg'}
    M = parse(mname)
    res = trace_snk(M, (port, b))
    memo_i[key] = res
    return res

def trace_snk(M, bit, seen=None):
    seen = seen or set()
    if bit in seen: return set()
    seen.add(bit)
    out = set()
    for s in M.snk.get(bit, []):
        if s[0] == 'PORT': out.add('out:' + s[1]); continue
        if s[0] == 'ASSIGN': out |= trace_snk(M, s[1], seen); continue
        typ, iname, pins = M.insts[s[1]]
        if typ in mods:
            r = in_kind(typ, s[2], s[3])
            out |= {('logic' if x.startswith('out:') else x) for x in r}
            continue
        if is_ff(typ):
            out.add('reg' if s[2] in ('D',) or typ.startswith('ot_sram') else 'logic(ff-ctl)')
            continue
        if is_buf(typ):
            for p, bl in pins.items():
                if pdir(typ, p) == 'output':
                    for b in bl: out |= trace_snk(M, b, seen)
            continue
        out.add('logic')
    return out

top = [n for n in mods if TOPSUB in n and 'v16w' not in n][0]
T = parse(top)
# group top-level instances: submodules by name, std cells as glue
def grp(k):
    typ, iname, _ = T.insts[k]
    return iname if typ in mods else 'top_glue'
# connection table: for every child input bit, find the driving child (through top glue comb cells / assigns)
def src_of(bit, seen=None):
    seen = seen or set()
    if bit in seen: return set()
    seen.add(bit)
    d = T.drv.get(bit)
    if d is None: return {('undriven', None, False)}
    if d[0] == 'PORT': return {('PORT:' + d[1], None, False)}
    if d[0] == 'ASSIGN':
        if d[1][0] == 'CONST': return {('const', None, False)}
        return src_of(d[1], seen)
    typ, iname, pins = T.insts[d[1]]
    if typ in mods: return {(iname, (d[2], d[3]), False)}
    if is_ff(typ): return {('top_reg', iname, False)}
    r = set()
    for p, bl in pins.items():
        if pdir(typ, p) == 'input':
            for b in bl:
                for x in src_of(b, seen): r.add((x[0], x[1], True))
    return r

rows = collections.Counter()
regs = collections.defaultdict(lambda: collections.Counter())
for k, (typ, iname, pins) in enumerate(T.insts):
    if typ not in mods: continue
    cm = parse(typ)
    for p, bl in pins.items():
        if cm.dir.get(p) != 'input': continue
        lo = cm.lo.get(p, 0)
        for j, b in enumerate(bl):
            pb = lo + (len(bl) - 1 - j)
            for (s, sp, viaglue) in src_of(b):
                sport = sp[0] if isinstance(sp, tuple) else (sp or '')
                key = (s, sport, iname, p, viaglue)
                rows[key] += 1
                sk = ','.join(sorted(in_kind(typ, p, pb)))
                if isinstance(sp, tuple):
                    styp = [t for t, n, _ in T.insts if n == s][0]
                    ok = ','.join(sorted(out_kind(styp, sp[0], sp[1])))
                else:
                    ok = 'top_reg' if s == 'top_reg' else s
                regs[key][(ok, sk)] += 1
out = []
for key, n in sorted(rows.items()):
    out.append(dict(src=key[0], src_port=key[1], dst=key[2], dst_port=key[3], via_top_glue=key[4], bits=n,
                    kinds={f'{a}|{b}': c for (a, b), c in regs[key].items()}))
json.dump(dict(top=top, insts=[(t, n) for t, n, _ in T.insts if t in mods], rows=out), open(sys.argv[3], 'w'), indent=1)
print('rows', len(out), file=sys.stderr)
