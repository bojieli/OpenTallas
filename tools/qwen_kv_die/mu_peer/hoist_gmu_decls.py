#!/usr/bin/env python3
"""Find / fix use-before-declaration inside the MU g_mu generate block (Yosys: 'Failed to detect width of signal
access g_mu.x').  --fix hoists every g_mu-scope declaration to the top of g_mu; a wire with an initialiser becomes
'wire ... x;' (hoisted) + 'assign x = expr;' (in place).  Same netlist; only declaration order changes."""
import re, sys
from pathlib import Path
GEN = re.compile(r'\bbegin\s*:\s*g_mu\b')
KW_OPEN = {'begin', 'case', 'casez', 'casex', 'fork', 'function', 'task', 'generate'}
KW_CLOSE = {'end', 'endcase', 'join', 'endfunction', 'endtask', 'endgenerate'}
DECLKW = ('wire', 'reg', 'logic', 'integer')

def mask(t):  # comments/strings -> spaces (same length)
    out = list(t); i = 0; n = len(t)
    while i < n:
        if t.startswith('//', i):
            j = t.find('\n', i); j = n if j < 0 else j
            for k in range(i, j): out[k] = ' '
            i = j
        elif t.startswith('/*', i):
            j = t.find('*/', i) + 2
            for k in range(i, j):
                if t[k] != '\n': out[k] = ' '
            i = j
        elif t[i] == '"':
            j = i + 1
            while t[j] != '"': j += 1 + (t[j] == '\\')
            for k in range(i + 1, j): out[k] = ' '
            i = j + 1
        else: i += 1
    return ''.join(out)

def gmu_spans(m):
    return [gmu_span(m, g) for g in GEN.finditer(m)]

def gmu_span(m, g):
    """(start, end) of the g_mu body in masked text m: after 'begin:g_mu' up to its matching 'end'."""
    depth = 1
    for tok in re.finditer(r'\b\w+\b', m[g.end():]):
        w = tok.group()
        if w in KW_OPEN: depth += 1
        elif w in KW_CLOSE:
            depth -= 1
            if depth == 0: return g.end(), g.end() + tok.start()
    raise AssertionError('unbalanced g_mu')

def stmts(m, a, b):
    """top-level (depth 0) declaration statements in m[a:b] -> list of (start, end_incl_semicolon)."""
    out = []; depth = 0; i = a; stmt_start = True
    while i < b:
        c = m[i]
        if c.isalpha() or c == '_':
            j = i
            while j < b and (m[j].isalnum() or m[j] in '_$'): j += 1
            w = m[i:j]
            if depth == 0 and stmt_start and w in DECLKW:
                k = j; par = 0
                while not (m[k] == ';' and par == 0):
                    par += m[k] in '([{'; par -= m[k] in ')]}'; k += 1
                out.append((i, k + 1)); i = k + 1; stmt_start = True; continue
            if w in KW_OPEN: depth += 1
            elif w in KW_CLOSE: depth -= 1
            stmt_start = w in ('begin', 'end', 'else') or w in KW_CLOSE or w == 'endgenerate'
            i = j; continue
        if c == ';': stmt_start = True
        elif not c.isspace(): stmt_start = False
        i += 1
    return out

def split_top(s, ch):
    parts = []; par = 0; cur = ''
    for c in s:
        par += c in '([{'; par -= c in ')]}'
        if c == ch and par == 0: parts.append(cur); cur = ''
        else: cur += c
    parts.append(cur); return parts

def parse_decl(s):
    """'wire[3:0] a=x, b;' -> (prefix 'wire[3:0] ', [(name, unpacked, init or None)])"""
    s = s.rstrip().rstrip(';')
    mm = re.match(r'(wire|reg|logic|integer)\b(\s*signed\b)?\s*(\[[^\]]*\])?\s*', s)
    prefix = mm.group(0); rest = s[mm.end():]
    items = []
    for p in split_top(rest, ','):
        eq = split_top(p, '=')
        lhs = eq[0].strip(); init = '='.join(eq[1:]).strip() if len(eq) > 1 else None
        nm = re.match(r'(\w+)\s*((?:\[[^\]]*\]\s*)*)$', lhs); assert nm, (s, lhs)
        items.append((nm.group(1), nm.group(2), init))
    return mm.group(1), prefix, items

def analyse_block(m, a, b):
    st = stmts(m, a, b); bad = []
    for (s, e) in st:
        kw, prefix, items = parse_decl(m[s:e])
        for n, _, _ in items:
            u = re.search(r'(?<![\w.$])' + n + r'\b', m[a:s])
            if u: bad.append(n)
    return st, bad

def analyse(text):
    m = mask(text); bad = []
    for a, b in gmu_spans(m): bad += analyse_block(m, a, b)[1]
    return bad

def fix(text):
    m = mask(text); allbad = []
    for a, b in reversed(gmu_spans(m)):
        st, bad = analyse_block(m, a, b)
        if bad: text = fix_block(text, a, st); allbad += bad
    return text, allbad

def fix_block(text, a, st):
    hoisted = []; edits = []
    for (s, e) in st:
        kw, prefix, items = parse_decl(text[s:e])
        decls = []; assigns = []
        for n, unp, init in items:
            if init is not None and kw == 'wire':
                assert not unp, (n, 'unpacked wire with init')
                decls.append(n); assigns.append(f'assign {n}={init};')
            elif init is not None:
                raise SystemExit(f'{kw} {n} has an initialiser ({init}); not hoisted automatically')
            else: decls.append(n + unp)
        hoisted.append(prefix.rstrip() + ' ' + ','.join(decls) + ';')
        edits.append((s, e, ''.join(assigns)))
    out = text
    for s, e, rep in reversed(edits): out = out[:s] + rep + out[e:]
    hdr = '\n // KV-PEER13: g_mu declarations hoisted before first use (Yosys declare-before-use; tools/qwen_kv_die/mu_peer/hoist_gmu_decls.py)\n ' + '\n '.join(hoisted) + '\n'
    return out[:a] + hdr + out[a:]

if __name__ == '__main__':
    do_fix = '--fix' in sys.argv; files = [f for f in sys.argv[1:] if f != '--fix']; rc = 0
    for f in files:
        t = Path(f).read_text()
        if not GEN.search(mask(t)): print(f'{Path(f).name}: no g_mu'); continue
        if do_fix:
            nt, bad = fix(t)
            if bad: Path(f).write_text(nt); after = analyse(nt); print(f'{Path(f).name}: fixed {len(set(bad))} names, after {len(after)}'); rc |= bool(after)
            else: print(f'{Path(f).name}: clean')
        else:
            bad = analyse(t); print(f'{Path(f).name}: {len(set(bad))} forward refs {sorted(set(bad))[:15]}'); rc |= bool(bad)
    sys.exit(rc)
