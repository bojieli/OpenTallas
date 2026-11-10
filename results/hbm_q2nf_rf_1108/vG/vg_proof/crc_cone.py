#!/usr/bin/env python3
"""HBM-Q2NF-RF vG: analyse (and optionally retime) the rx CRC check cone of each link codec in the flattened
ot_q2nf_rest.sv.  The cone root is u_codec.crc_bad; the leaves that are bits of u_codec.rf (the 612-bit rx flit register,
D = rx_pin_flit_pin) get their rf-only sub-cones recomputed from rf's D side and registered on rf's clock (retiming
across rf: q(t) = f(rf(t)) for every t after the first rf load, rf has no reset)."""
import re, sys, collections

ID = r'(?:\\\S+ |[A-Za-z_][A-Za-z0-9_$]*)'          # escaped identifier keeps its trailing space
TOK = re.compile(r'(\\\S+ |[A-Za-z_][A-Za-z0-9_$]*)(\s*\[\s*\d+\s*(?::\s*\d+\s*)?\])?')

def norm(name):
    return name.strip()

def parse(path):
    lines = open(path).read().split('\n')
    assigns = {}          # lhs (normalised, incl. [i] if bit) -> (line index, rhs)
    for i, l in enumerate(lines):
        s = l.strip()
        if not s.startswith('assign ') or not s.endswith(';'):
            continue
        m = re.match(r'assign\s+(' + ID + r'(?:\s*\[\s*\d+\s*\])?)\s*=\s*(.*);$', s)
        if not m:
            continue
        assigns[re.sub(r'\s+', '', m.group(1))] = (i, m.group(2))
    return lines, assigns

def refs(rhs):
    out = []
    for m in TOK.finditer(rhs):
        base = norm(m.group(1))
        if re.fullmatch(r"\d+'?[hbdo]?", base) or base in ('h', 'b', 'd'):
            continue
        idx = re.sub(r'\s+', '', m.group(2) or '')
        out.append(base + idx)
    return out

def key_lookup(assigns, r):
    """a reference r may be a whole-vector name or a bit; return the assign keys that define it"""
    if r in assigns:
        return [r]
    return []

def cone(assigns, root, rf_base):
    """backward cone through assigns; returns (nodes, leaves)"""
    nodes, leaves = set(), collections.Counter()
    todo = [root]
    while todo:
        n = todo.pop()
        if n in nodes:
            continue
        ks = key_lookup(assigns, n)
        if not ks:
            base = re.sub(r'\[\d+\]$', '', n)
            leaves['rf' if base == rf_base else base] += 1
            nodes.add(n)
            continue
        nodes.add(n)
        for r in refs(assigns[n][1]):
            todo.append(r)
    return nodes, leaves

def main():
    path = sys.argv[1]
    lines, assigns = parse(path)
    print('assigns', len(assigns))
    for k in (0, 1):
        pre = r'\u_body.g_link[%d].u_link.u_ctl.u.u_core.u_codec.' % k
        root = re.sub(r'\s+', '', pre + 'crc_bad')
        if root not in assigns:
            print('link', k, 'no crc_bad assign', root); continue
        nodes, leaves = cone(assigns, root, re.sub(r'\s+', '', pre + 'rf'))
        print('link', k, 'crc_bad cone nodes', len(nodes))
        for b, c in leaves.most_common(25):
            print('   leaf', c, b)

if __name__ == '__main__' and len(sys.argv) == 2:
    main()

# ---------------- retime transform ----------------
def split_concat(s):
    s = s.strip()
    assert s.startswith('{') and s.endswith('}'), s[:80]
    return [x.strip() for x in s[1:-1].split(',')]

def rename(n):
    n = n.strip()
    return (n + '__vg ') if n.startswith('\\') else (n + '__vg')

def retime(path, out):
    lines, assigns = parse(path)
    decl = {}
    for l in lines:
        m = re.match(r'\s*(?:wire|reg)\s*(\[\s*(\d+)\s*:\s*(\d+)\s*\])?\s*(' + ID + r')\s*;', l)
        if m:
            decl[norm(m.group(4))] = (int(m.group(2)) - int(m.group(3)) + 1) if m.group(1) else 1
    add_decl, add_logic, notes = [], [], []
    for k in (0, 1):
        pre = r'\u_body.g_link[%d].u_link.u_ctl.u.u_core.u_codec.' % k
        rfb = pre + 'rf'
        # rf bits <- register name, and that register's D concat + always header
        ai = [i for i, l in enumerate(lines) if l.strip().startswith('assign { ' + rfb + '[611]')]
        assert len(ai) == 1, ('rf assign', k, len(ai))
        a = lines[ai[0]].strip()
        lhs, rhs = a[len('assign '):-1].split('=', 1)
        rf_bits = [norm(x) for x in split_concat(lhs)]
        reg = norm(rhs)
        assert len(rf_bits) == 612 and re.fullmatch(r'_\d+_', reg), (len(rf_bits), reg)
        di = [i for i, l in enumerate(lines) if l.strip().startswith(reg + ' <= {')]
        assert len(di) == 1, ('rf D', k, len(di))
        dlist = split_concat(lines[di[0]].strip()[len(reg + ' <= '):-1])
        assert len(dlist) == 612
        hdr = lines[di[0] - 1].strip()
        assert hdr.startswith('always @(posedge') and 'rst' not in hdr, hdr
        dmap = dict(zip(rf_bits, dlist))
        root = re.sub(r'\s+', '', pre + 'crc_bad')
        nodes, _ = cone(assigns, root, re.sub(r'\s+', '', rfb))
        memo = {}
        def rfonly(n):
            if n in memo: return memo[n]
            memo[n] = True
            if n not in assigns:
                ok = re.sub(r'\s+', '', n) in {re.sub(r'\s+', '', b) for b in dmap} or re.fullmatch(r"h[0-9a-f]*|\d+", n) is not None
            else:
                ok = all(rfonly(r) for r in refs(assigns[n][1]))
            memo[n] = ok
            return ok
        rfset = {re.sub(r'\s+', '', b): b for b in dmap}
        front = set()
        for n in nodes:
            if n in assigns and not rfonly(n):
                for r in refs(assigns[n][1]):
                    if r in assigns and rfonly(r):
                        front.add(r)
        assert front, 'no frontier'
        dup = set()
        def walk(n):
            if n in dup or n not in assigns: return
            dup.add(n)
            for r in refs(assigns[n][1]): walk(r)
        for f in front: walk(f)
        def sub_rhs(rhs):
            def rep(m):
                base = norm(m.group(1)); idx = m.group(2) or ''
                key = base + re.sub(r'\s+', '', idx)
                if key in rfset and not idx:
                    return dmap[rfset[key]] + ' '
                if key in dup:
                    return rename(base) + idx if not idx else rename(base) + idx
                return m.group(0)
            return TOK.sub(rep, rhs)
        for n in sorted(dup):
            w = decl.get(n, 1)
            add_decl.append('  wire %s%s;' % ('[%d:0] ' % (w - 1) if w > 1 else '', rename(n)))
            add_logic.append('  assign %s = %s;' % (rename(n), sub_rhs(assigns[n][1])))
        for f in sorted(front):
            w = decl.get(f, 1)
            q = rename(f).rstrip() + '_q' + (' ' if f.startswith('\\') else '')
            add_decl.append('  reg %s%s;' % ('[%d:0] ' % (w - 1) if w > 1 else '', q))
            add_logic.append('  %s' % hdr)
            add_logic.append('    %s <= %s;' % (q, rename(f)))
            li, _ = assigns[f]
            lines[li] = '  assign %s = %s; // HBM-Q2NF-RF vG: retimed across %s (rf)' % (f, q, reg)
        notes.append('link %d: rf reg %s, frontier %d nodes, duplicated %d assigns, clock "%s"' % (k, reg, len(front), len(dup), hdr))
    # insert before the last endmodule of the top-level flattened module (the one declaring the codec signals)
    end = max(i for i, l in enumerate(lines) if l.strip() == 'endmodule' and i > ai[0])
    end = min(i for i, l in enumerate(lines) if l.strip() == 'endmodule' and i > ai[0])
    lines[end:end] = ['  // HBM-Q2NF-RF vG retime begin'] + add_decl + add_logic + ['  // HBM-Q2NF-RF vG retime end']
    open(out, 'w').write('\n'.join(lines))
    for n in notes: print(n)

if __name__ == '__main__' and len(sys.argv) > 3 and sys.argv[2] == 'retime':
    retime(sys.argv[1], sys.argv[3])
