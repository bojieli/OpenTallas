#!/usr/bin/env python3
"""CORE-HBM-SPLIT (2026-10-23): final RTL top of a remainder piece from the rest_extract.sh output.

The yosys submodule keeps whole port wires; bits of a MASTER port that the as-built core never touches (netlist cut,
split_conn.top_port_use) are dropped from the core pins and tied 0 inside.  Hierarchical wire names become plain
identifiers.  Output file = the extracted module renamed <top>_x + the wrapper <top>.

    rest_wrap.py --ext X.v --name EXTNAME --top TOP --use use.json --out FILE.sv --hdr "comment"
"""
import argparse, json, re


def ports_of(txt, name):
    m = re.search(r'(?ms)^module\s+\\?' + re.escape(name) + r'\b.*?^endmodule', txt)
    out = []
    for l in m.group(0).splitlines():
        mm = re.match(r'  (input|output|inout)\s+(?:signed\s+)?(?:\[(\d+):(\d+)\]\s*)?(\S+)\s*;', l)
        if mm:
            w = abs(int(mm.group(2)) - int(mm.group(3))) + 1 if mm.group(2) else 1
            out.append((mm.group(4), mm.group(1), w))
    return m, out


def clean(nm):
    s = nm.lstrip('\\')
    s = re.sub(r'[^A-Za-z0-9_]+', '_', s).strip('_')
    return re.sub(r'_+', '_', s)


def main():
    ap = argparse.ArgumentParser()
    for k in ('ext', 'name', 'top', 'use', 'out'):
        ap.add_argument('--' + k, required=True)
    ap.add_argument('--hdr', default='')
    ap.add_argument('--parent', default='')
    # constant nets the as-built hierarchical netlist carries across the cut (no cross-boundary constant propagation),
    # which the flattened extraction folds away: 'input:NAME:W' = pin kept, unread; 'output:NAME:W:VALUE' = driven const
    ap.add_argument('--add', action='append', default=[])
    # kept member-type cells yosys named '$paramod$<hash>\\MOD': 'MOD=#(...)' rewrites them to the RTL module + params
    ap.add_argument('--paramod', action='append', default=[])
    a = ap.parse_args()
    txt = open(a.ext).read()
    m, ports = ports_of(txt, a.name)
    unused, topname = set(), {}
    if a.parent:
        ptxt0 = open(a.parent).read()
        tops = set(re.findall(r'^  (?:input|output)\s+(?:\[\d+:\d+\]\s*)?(\S+)\s*;', ptxt0, re.M))
        mi0 = re.search(r'(?ms)^\s*\\?' + re.escape(a.name) + r'\s+\S+\s*\((.*?)\);', ptxt0)
        for pm in re.finditer(r'\.(\\\S+\s|[A-Za-z_][\w$]*)\s*\(\s*(\\\S+\s|[A-Za-z_][\w$]*)\s*(\[\d+\])?\s*\)', mi0.group(1)):
            if pm.group(2).strip() in tops:          # the core port IS a master port net: keep the master name
                topname[pm.group(1).strip()] = pm.group(2).strip()
    if a.parent:     # outputs the master never reads outside the core (yosys keeps (* keep *) wires as ports)
        ptxt = open(a.parent).read()
        mi = re.search(r'(?ms)^\s*\\?' + re.escape(a.name) + r'\s+\S+\s*\((.*?)\);', ptxt)
        blk = mi.group(0)
        rest = ptxt[:mi.start()] + ptxt[mi.end():]
        rx_id = re.compile(r'(\\\S+|[A-Za-z_][\w$]*)')
        used = set(rx_id.findall(rest))
        for pm in re.finditer(r'\.(\\\S+\s|[A-Za-z_][\w$]*)\s*\((.*?)\)\s*(?:,|$)', mi.group(1), re.S):
            pn = pm.group(1).strip()
            ids = [x for x in rx_id.findall(pm.group(2)) if not re.match(r"^\d", x)]
            if not any(x in used for x in ids):
                unused.add(pn)
    use = json.load(open(a.use))
    body = m.group(0)
    body = re.sub(r'^module\s+\\?' + re.escape(a.name) + r'\b', f'module {a.top}_x', body, count=1)
    for s in a.paramod:
        mod, prm = s.split('=', 1)
        body = re.sub(r'\\\$paramod\$[0-9a-f]+\\' + re.escape(mod) + r'\s', f'{mod} {prm} ', body)
    assert '$paramod' not in body, 'unresolved $paramod cell type'
    L = [a.hdr.rstrip(), '`timescale 1ns/1ps', body, '', f'module {a.top} (']
    decl, conns, asg, final = [], [], [], []
    # splitnets made single-bit ports '\\base[i]': regroup them into one bus per (base, dir), bits in index order
    groups, single = {}, []
    for nm, d, w in ports:
        mm = re.match(r'^\\(.+)\[(\d+)\]$', nm)
        if mm and w == 1 and nm not in unused:
            groups.setdefault((mm.group(1), d), []).append((int(mm.group(2)), nm))
        else:
            single.append((nm, d, w))
    used_names = set()
    for (base, d), bl in groups.items():
        bl.sort()
        tb = {topname.get(nm) for _, nm in bl}
        c = clean(tb.pop() if len(tb) == 1 and None not in tb else base)
        while c in used_names:
            c += '_'
        used_names.add(c)
        decl.append(f'    {d} wire {"[%d:0] " % (len(bl) - 1) if len(bl) > 1 else ""}{c}')
        for k, (i, nm) in enumerate(bl):
            conns.append(f'.{nm} ({c}[{k}])' if len(bl) > 1 else f'.{nm} ({c})')
        final.append([c, d, len(bl), 0])
    ports = single
    for nm, d, w in ports:
        c = clean(topname.get(nm, nm))
        ref = nm if not nm.startswith('\\') else nm + ' '
        if d == 'output' and nm in unused:
            conns.append(f'.{ref}()')
            continue
        if d == 'input' and nm in use and len(use[nm]) < w:
            u = use[nm]
            if not u:                               # master port the core never reads: no pin, tied 0 inside
                conns.append(f".{ref}({w}'b0)")
                continue
            decl.append(f'    input wire [{len(u) - 1}:0] {c}' if len(u) > 1 else f'    input wire {c}')
            asg.append(f'    wire [{w - 1}:0] {c}__full;')
            for k, i in enumerate(u):
                asg.append(f'    assign {c}__full[{i}] = {c}[{k}];' if len(u) > 1 else f'    assign {c}__full[{i}] = {c};')
            for i in range(w):
                if i not in set(u):
                    asg.append(f"    assign {c}__full[{i}] = 1'b0;   // master bit the core never reads")
            conns.append(f'.{ref}({c}__full)')
            final.append([c, d, len(u), 0])
        else:
            decl.append(f'    {d} wire {"[%d:0] " % (w - 1) if w > 1 else ""}{c}')
            conns.append(f'.{ref}({c})')
            final.append([c, d, w, 0])
    for s in a.add:
        f = s.split(':')
        w = int(f[2])
        decl.append(f'    {f[0]} wire {"[%d:0] " % (w - 1) if w > 1 else ""}{f[1]}')
        if f[0] == 'output':
            asg.append(f'    assign {f[1]} = {f[3]};   // constant net of the master carried by the cut')
        else:
            asg.append(f'    // {f[1]}: cut pin of a net the master ties constant ({w} b); the core folds the constant')
        final.append([f[1], f[0], w, 0])
    L.append(',\n'.join(decl))
    L.append(');')
    L += asg
    L.append(f'    {a.top}_x u_x (\n        ' + ',\n        '.join(conns) + ');')
    L += ['endmodule', '']
    open(a.out, 'w').write('\n'.join(L))
    print('dropped unused outputs:', len([p for p in ports if p[1] == 'output' and p[0] in unused]))
    print(json.dumps(dict(inp=sum(p[2] for p in final if p[1] == 'input'), out=sum(p[2] for p in final if p[1] == 'output'))))


if __name__ == '__main__':
    main()
