#!/usr/bin/env python3
"""PATH-HBM/Q3 (2026-10-25): bench-only ASSEMBLY of a split master from its rest_extract parent view.

rest_extract.sh writes <name>.parent.v = the flattened master top (elab_top) with the remainder submodule instance and
the excluded member instances.  This script swaps every one of them for the generated split-piece tops:
  --rest  WRAPPER.sv:EXTNAME        remainder core wrapper (rest_wrap.py output): its u_x port map maps extracted port
                                    names -> wrapper port bits; the parent's connection of the EXTNAME instance is reused
  --piece WRAPPER.sv:PATH=ROLE,...  member-set top (build_split_tops.py / split_conn.emit_wrapper output); member
                                    instance PATH of the parent takes role ROLE; 'assign ROLE__port[..] = NAME[..]' and
                                    'assign NAME[..] = ROLE__port[..]' give every wrapper port bit its parent net
  --mut   K:WRAPPERTOP:PORT:BIT     bench mutant K: wrapper input bit XOR (lockstep_mut == K)  (extra input port)
Writes module --top (ports = master ports [+ lockstep_mut]).  Unmapped wrapper outputs -> dangling wires;
unmapped wrapper inputs -> listed (FAIL unless the wrapper ties them itself).
"""
import argparse, re, sys, collections

RX_ID = r'(?:\\\S+\s|[A-Za-z_][\w$]*)'


def decls(txt):
    w = {}
    for m in re.finditer(r'^\s*(?:input|output|inout|wire|reg)\s+(?:signed\s+)?(?:\[(-?\d+):(-?\d+)\]\s*)?(\\\S+|[A-Za-z_][\w$]*)\s*;', txt, re.M):
        w[m.group(3).strip()] = (int(m.group(1)), int(m.group(2))) if m.group(1) else None
    return w


def items(expr):
    e = expr.strip()
    if e.startswith('{') and e.endswith('}'):
        e = e[1:-1]
    out, depth, cur = [], 0, ''
    i = 0
    while i < len(e):
        ch = e[i]
        if ch == '\\':                       # escaped identifier: up to whitespace
            j = i
            while j < len(e) and not e[j].isspace():
                j += 1
            cur += e[i:j] + ' '; i = j; continue
        if ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
        if ch == ',' and depth == 0:
            out.append(cur.strip()); cur = ''
        else:
            cur += ch
        i += 1
    if cur.strip():
        out.append(cur.strip())
    return out


def bits(expr, W):
    """msb-first list of single-bit expressions."""
    res = []
    for it in items(expr):
        m = re.match(r"^(\d+)'([bhdo])([0-9a-fA-FxXzZ_]+)$", it)
        if m:
            w, b, v = int(m.group(1)), m.group(2), m.group(3).replace('_', '').lower()
            s = v if b == 'b' else (''.join('xxxx' if c in 'xz' else format(int(c, 16), '04b') for c in v) if b == 'h'
                                   else format(int(v), 'b'))
            s = s[-w:].rjust(w, '0')
            res += [f"1'b{c}" for c in s]
            continue
        if it.startswith('{'):
            res += bits(it, W); continue
        m = re.match(r'^(\\\S+|[A-Za-z_][\w$]*)\s*(?:\[(\d+)(?::(\d+))?\])?$', it)
        assert m, it
        nm = m.group(1)
        sp = nm + ' ' if nm.startswith('\\') else nm
        if m.group(2) is not None:
            hi = int(m.group(2)); lo = int(m.group(3)) if m.group(3) is not None else hi
            rng = range(hi, lo - 1, -1) if hi >= lo else range(hi, lo + 1)
            res += [f'{sp}[{i}]' for i in rng]
        else:
            d = W.get(nm)
            if d is None:
                res.append(sp)
            else:
                rng = range(d[0], d[1] - 1, -1) if d[0] >= d[1] else range(d[0], d[1] + 1)
                res += [f'{sp}[{i}]' for i in rng]
    return res


def inst_blocks(txt):
    """[(start, end, type, name, {port: expr})] for every instance in the module text."""
    out = []
    for m in re.finditer(r'^  (\\\S+|[A-Za-z_][\w$]*)\s+(\\\S+|[A-Za-z_][\w$]*)\s*\($', txt, re.M):
        end = txt.index('\n  );', m.end())
        body = txt[m.end():end]
        conns = {}
        for pm in re.finditer(r'^\s*\.(\\\S+\s|[A-Za-z_][\w$]*)\s*\((.*)\),?\s*$', body, re.M):
            conns[pm.group(1).strip()] = pm.group(2).strip()
        out.append((m.start(), end + len('\n  );'), m.group(1), m.group(2).strip(), conns))
    return out


def wrapper_ports(txt, top):
    m = re.search(r'(?ms)^module\s+' + re.escape(top) + r'\s*\((.*?)\);', txt)
    ps = []
    for l in m.group(1).split(','):
        mm = re.match(r'\s*(input|output)\s+wire\s+(?:\[(\d+):(\d+)\]\s*)?(\S+)', l)
        if mm:
            ps.append((mm.group(4), mm.group(1), int(mm.group(2)) - int(mm.group(3)) + 1 if mm.group(2) else 1))
    return ps


def rng(s, w=None):
    m = re.match(r'^(\S+?)(?:\[(\d+)(?::(\d+))?\])?$', s.strip())
    nm = m.group(1)
    if m.group(2) is None:
        return nm, (list(range(w)) if w else [0])
    hi = int(m.group(2)); lo = int(m.group(3)) if m.group(3) is not None else hi
    return nm, list(range(lo, hi + 1))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--parent', required=True)
    ap.add_argument('--top', required=True)
    ap.add_argument('--rest', action='append', default=[])
    ap.add_argument('--piece', action='append', default=[])
    ap.add_argument('--mut', action='append', default=[])
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    ptxt = open(a.parent).read()
    W = decls(ptxt)
    blocks = {b[3]: b for b in inst_blocks(ptxt)}
    repl = []          # (start, end, new text)
    muts = collections.defaultdict(list)
    for s in a.mut:
        k, wt, port, bit = s.split(':')
        muts[(wt, port)].append((int(bit), int(k)))
    unmapped_in = []

    def emit(wtop, ports, srcmap, iname):
        conns = []
        dang = 0
        for nm, d, w in ports:
            bl = []
            for j in range(w - 1, -1, -1):
                e = srcmap.get((nm, j))
                if e is None:
                    if d == 'input':
                        unmapped_in.append(f'{wtop}.{nm}[{j}]'); e = "1'b0"
                    else:
                        e = f'asm_nc_{iname}[{dang}]'; dang += 1
                if d == 'input':
                    for bit, k in muts.get((wtop, nm), []):
                        if bit == j:
                            e = f"({e} ^ (lockstep_mut == 4'd{k}))"
                bl.append(e)
            conns.append(f'    .{nm}({{ {", ".join(bl)} }})' if w > 1 else f'    .{nm}({bl[0]})')
        pre = f'  wire [{max(dang, 1) - 1}:0] asm_nc_{iname};\n'
        return pre + f'  {wtop} {iname} (\n' + ',\n'.join(conns) + '\n  );'

    for spec in a.rest:
        wf, ext = spec.split(':')
        wtxt = open(wf).read()
        wtop = re.search(r'^module\s+(\S+)\s*\(', wtxt[wtxt.index('_x u_x') - 200000 if False else 0:], re.M)
        tops = re.findall(r'^module\s+(\S+)\s*\(', wtxt, re.M)
        wtop = [t for t in tops if not t.endswith('_x')][-1]
        ports = wrapper_ports(wtxt, wtop)
        rpw = {p[0]: p[2] for p in ports}
        ux = wtxt[wtxt.index(f'{wtop}_x u_x ('):]
        b = blocks[ext]
        srcmap = {}
        for pm in re.finditer(r'\.(\\\S+\s|[A-Za-z_][\w$]*)\s*\(([^()]*)\)', ux):
            xp, wexp = pm.group(1).strip(), pm.group(2).strip()
            if not wexp or "'b" in wexp:
                continue
            pe = b[4].get(xp)
            if pe is None:
                continue
            pb = bits(pe, W)
            if wexp.endswith('__full'):          # rest_wrap 'use' subset: assign X__full[i] = X[k] / X
                base = wexp[:-6]
                lsb = list(reversed(pb))
                for am in re.finditer(r'assign ' + re.escape(wexp) + r'\[(\d+)\] = ' + re.escape(base) + r'(?:\[(\d+)\])?;', wtxt):
                    srcmap[(base, int(am.group(2) or 0))] = lsb[int(am.group(1))]
                continue
            nm, idx = rng(wexp, rpw.get(wexp))
            assert len(pb) == len(idx), (xp, wexp)
            for k, i in enumerate(sorted(idx, reverse=True)):
                srcmap[(nm, i)] = pb[k]
        repl.append((b[0], b[1], emit(wtop, ports, srcmap, 'u_' + wtop)))
    for spec in a.piece:
        wf, rest = spec.split(':', 1)
        roles = dict(x.split('=') for x in rest.split(','))
        wtxt = open(wf).read()
        wtop = re.findall(r'^module\s+(\S+)\s*\(', wtxt, re.M)[-1]
        ports = wrapper_ports(wtxt, wtop)
        pw = {p[0]: p[2] for p in ports}
        pin = {}           # (role, port) -> lsb-first bit exprs of the parent connection
        first = None
        for path, role in roles.items():
            b = blocks[path]
            first = first or b
            for pn, ex in b[4].items():
                pin[(role, pn)] = list(reversed(bits(ex, W)))
        srcmap = {}
        for m in re.finditer(r'^\s*assign\s+(\S+)\s*=\s*(\S+?);', wtxt, re.M):
            l, r = m.group(1), m.group(2)
            if '__' in l.split('[')[0] and l.split('__')[0] in roles.values():   # role pin <- wrapper port
                if r.startswith("1'b") or r.startswith('n_int'):
                    continue
                role, port = l.split('[')[0].split('__', 1)
                _, li = rng(l); rn, ri = rng(r, pw.get(r))
                for x, y in zip(li, ri):
                    srcmap[(rn, y)] = pin[(role, port)][x]
            elif '__' in r.split('[')[0] and r.split('__')[0] in roles.values():  # wrapper port <- role pin
                if l.startswith('n_int'):
                    continue
                role, port = r.split('[')[0].split('__', 1)
                _, ri = rng(r); ln, li = rng(l, pw.get(l))
                for x, y in zip(ri, li):
                    srcmap[(ln, y)] = pin[(role, port)][x]
        for path in roles:
            b = blocks[path]
            if b is not first:
                repl.append((b[0], b[1], f'  // {path}: inside {wtop}'))
        repl.append((first[0], first[1], emit(wtop, ports, srcmap, 'u_' + wtop)))
    out = ptxt
    for s, e, t in sorted(repl, reverse=True):
        out = out[:s] + t + out[e:]
    out = re.sub(r'^module elab_top\(', f'module {a.top}(lockstep_mut, ' if a.mut else f'module {a.top}(', out, count=1, flags=re.M)
    if a.mut:
        out = out.replace(';\n', ';\n  input [3:0] lockstep_mut;\n', 1)
    open(a.out, 'w').write('// GENERATED bench-only split assembly (split_asm.py, PATH-HBM/Q3 2026-10-25)\n' + out)
    print('unmapped wrapper inputs:', len(unmapped_in), unmapped_in[:20])


if __name__ == '__main__':
    main()
