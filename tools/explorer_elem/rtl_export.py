#!/usr/bin/env python3
"""RTL side of the Chip Explorer element page.  Runs on the fleet host that holds the closure job (host python3 +
yosys in the ORFS container, through ot-heavy):

    rtl_export.py --config <job orfs work dir>/config.mk --src <job src = checkout at the source commit> --out <dir>

Elaborates EXACTLY the synthesis inputs of the route (config.mk: DESIGN_NAME, VERILOG_FILES, VERILOG_DEFINES,
VERILOG_TOP_PARAMS) with yosys `hierarchy -chparam ...; proc` (no flatten, no optimisation) and writes <out>/rtl.json:
  files      every synthesised source file's text (path relative to the source tree)
  modules    per elaborated module: base name, src file:line, ports (dir, width), instances (name, module, src line),
             named signals (name -> file, line, width)  -- lets the page map a placed flop to its RTL declaration
  tree       the elaborated instance tree from the top
  diagrams   per module near the top: its sub-blocks (outermost generate blocks / instances) and the signals between
             them, with bit widths, from the elaborated netlist connectivity (driver -> sinks per bit)
"""
import argparse, collections, json, os, pathlib, re, subprocess, sys

IMAGE = 'openroad/orfs:asap7lock'
YOSYS = '/OpenROAD-flow-scripts/tools/install/yosys/bin/yosys'


def cfg(path):
    out = {}
    for ln in pathlib.Path(path).read_text().splitlines():
        m = re.match(r'^export\s+(\w+)\s*\??=\s*(.*)$', ln)
        if m: out[m.group(1)] = m.group(2).strip()
    return out


def base_name(k):
    if not k.startswith('$'): return k
    m = re.search(r'\\([A-Za-z_][A-Za-z0-9_]*)', k)
    return m.group(1) if m else k


def src_of(attrs):
    s = (attrs or {}).get('src', '')
    s = s.split('|')[0]
    m = re.match(r'^(.*?):(\d+)', s)
    if not m: return None
    f = m.group(1)
    if f.startswith('/src/'): f = f[5:]
    return [f, int(m.group(2))]


def strip_comments(t):
    t = re.sub(r'/\*.*?\*/', lambda m: re.sub(r'[^\n]', ' ', m.group(0)), t, flags=re.S)
    t = re.sub(r'//[^\n]*', '', t)
    return re.sub(r'"(?:\\.|[^"\\])*"', '""', t)


def label_ranges(text):
    """labelled begin ... end blocks: [(label, start_line, end_line, depth)]"""
    t = strip_comments(text)
    out, stack = [], []
    lines = [0]
    for i, c in enumerate(t):
        if c == '\n': lines.append(i + 1)
    import bisect
    for m in re.finditer(r'\bbegin\b(\s*:\s*([A-Za-z_][A-Za-z0-9_]*))?|\bend\b', t):
        ln = bisect.bisect_right(lines, m.start())
        if m.group(0).startswith('begin'):
            stack.append((m.group(2), ln))
        elif stack:
            lab, s0 = stack.pop()
            if lab: out.append((lab, s0, ln, len(stack)))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--config', required=True); ap.add_argument('--src', required=True); ap.add_argument('--out', required=True)
    ap.add_argument('--mem', type=int, default=24); ap.add_argument('--image', default=IMAGE); ap.add_argument('--depth', type=int, default=3)
    a = ap.parse_args()
    out = pathlib.Path(a.out).resolve(); out.mkdir(parents=True, exist_ok=True)
    c = cfg(a.config)
    top = c['DESIGN_NAME']; files = c['VERILOG_FILES'].split(); defs = c.get('VERILOG_DEFINES', '').split()
    tp = c.get('VERILOG_TOP_PARAMS', '').split(); params = list(zip(tp[0::2], tp[1::2]))
    ys = ['read_verilog -defer -sv %s %s' % (' '.join(defs), ' '.join(files)),
          'hierarchy -top %s %s' % (top, ' '.join('-chparam %s %s' % kv for kv in params)),
          'proc', 'write_json /out/rtl_yosys.json']
    (out / 'rtl.ys').write_text('\n'.join(ys) + '\n')
    if not (out / 'rtl_yosys.json').exists() or os.environ.get('OT_RTL_REDO'):
        cmd = ['ot-heavy', '--mem', str(a.mem), '--', 'docker', 'run', '--rm', '--memory', '%dg' % a.mem, '--user', '%d:%d' % (os.getuid(), os.getgid()),
               '-v', '%s:/src:ro' % a.src, '-v', '%s:/out' % out, a.image, YOSYS, '-q', '-l', '/out/yosys.log', '-s', '/out/rtl.ys']
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode and '-defer' in ys[0]:      # ORFS reads with -defer; a few designs elaborate only without it
            ys[0] = ys[0].replace('read_verilog -defer -sv', 'read_verilog -sv')
            (out / 'rtl.ys').write_text('\n'.join(ys) + '\n')
            r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode: sys.exit('yosys failed: %s\n%s' % (r.stderr[-2000:], (out / 'yosys.log').read_text()[-2000:] if (out / 'yosys.log').exists() else ''))
    Y = json.loads((out / 'rtl_yosys.json').read_text())['modules']
    srcroot = pathlib.Path(a.src)
    texts = {}
    for f in files:
        rel = f[5:] if f.startswith('/src/') else f
        try: texts[rel] = (srcroot / rel).read_text(errors='replace')
        except OSError: pass
    ranges = {f: label_ranges(t) for f, t in texts.items()}

    mods = {}
    for k, m in Y.items():
        if m.get('attributes', {}).get('blackbox') or m.get('attributes', {}).get('whitebox'):
            mods[k] = dict(name=base_name(k), blackbox=True, src=src_of(m.get('attributes')), ports=[], inst=[], nets={})
            continue
        ports = [[p, d['direction'][0], len(d['bits'])] for p, d in m.get('ports', {}).items()]
        inst = [[cn, cd['type'], src_of(cd.get('attributes'))] for cn, cd in m.get('cells', {}).items() if cd['type'] in Y or not cd['type'].startswith('$')]
        nets = {}
        for nn, nd in m.get('netnames', {}).items():
            if nd.get('hide_name'): continue
            s = src_of(nd.get('attributes'))
            if s: nets[nn] = [s[0], s[1], len(nd['bits'])]
        mods[k] = dict(name=base_name(k), src=src_of(m.get('attributes')), ports=ports, inst=inst, nets=nets)

    def tree(k, path, depth):
        m = mods.get(k, {})
        node = dict(p=path, m=m.get('name', base_name(k)), k=k, src=m.get('src'), bb=bool(m.get('blackbox')))
        if depth < 40 and not m.get('blackbox'):
            node['c'] = [tree(t, (path + '.' if path else '') + n, depth + 1) for n, t, _ in sorted(m.get('inst', []))]
        return node
    T = tree(top, '', 0)

    def module_range(k):
        s = mods[k].get('src')
        if not s or s[0] not in texts: return None
        t = strip_comments(texts[s[0]]).splitlines()
        for i in range(s[1] - 1, len(t)):
            if re.search(r'\bendmodule\b', t[i]): return (s[0], s[1], i + 1)
        return (s[0], s[1], len(t))

    def diagram(k, prefix=None):
        """sub-blocks of module k (outermost generate blocks / instances); with prefix, the sub-blocks one level inside
        that generate scope, everything else of the module lumped as '(rest of <module>)'"""
        m = Y[k]; mr = module_range(k); P = (prefix + '.') if prefix else ''
        rest = '(rest of %s)' % mods[k]['name']
        outer = []
        if mr:
            f, a0, a1 = mr
            inside = [r for r in ranges.get(f, []) if r[1] > a0 and r[2] <= a1]
            dmin = min([r[3] for r in inside], default=0)
            outer = [r for r in inside if r[3] == dmin]

        nb = {}
        # bits that carry a name at this scope level are interface signals: a scoped alias of them (wire x = cap inside
        # a generate block) says who READS them, not who drives them, so they never decide a cell's block
        scope_bits = set()
        for nn, nd in m.get('netnames', {}).items():
            if not nd.get('hide_name') and '$' not in nn and nn.startswith(P) and '.' not in nn[len(P):]:
                scope_bits.update(b for b in nd['bits'] if isinstance(b, int))
        for nn, nd in m.get('netnames', {}).items():
            if nd.get('hide_name') or '$' in nn or not nn.startswith(P) or '.' not in nn[len(P):]: continue
            for b in nd['bits']:
                if isinstance(b, int) and b not in scope_bits: nb.setdefault(b, nn[len(P):].split('.')[0])

        def group_of_cell(cn, cd):
            if not cn.startswith('$') or cd['type'] in Y:
                if P and not cn.startswith(P): return rest
                return cn[len(P):].split('.')[0]
            pd = cd.get('port_directions') or {}
            outs = [nb.get(b) for p_, bits in cd.get('connections', {}).items() if pd.get(p_) == 'output' for b in bits if isinstance(b, int)]
            outs = [o for o in outs if o]
            if outs: return collections.Counter(outs).most_common(1)[0][0]
            if P: return rest
            s = src_of(cd.get('attributes'))
            if s and mr and s[0] == mr[0]:
                for lab, s0, s1, _ in outer:
                    if s0 <= s[1] <= s1: return lab
            return '(module logic)'
        sub = {}
        for cn, cd in m.get('cells', {}).items():
            sub[cn] = (group_of_cell(cn, cd), cd)
        drv = {}; snk = collections.defaultdict(set)
        dirs_of = lambda cd: cd.get('port_directions') or {p: d['direction'] for p, d in Y.get(cd['type'], {}).get('ports', {}).items()}
        for cn, (g, cd) in sub.items():
            pd = dirs_of(cd)
            for p, bits in cd.get('connections', {}).items():
                d = pd.get(p, 'input')
                for b in bits:
                    if not isinstance(b, int): continue
                    if d == 'output': drv[b] = g
                    else: snk[b].add(g)
        for p, d in m.get('ports', {}).items():
            for b in d['bits']:
                if not isinstance(b, int): continue
                if d['direction'] == 'input': drv[b] = rest if P else '(inputs)'
                else: snk[b].add(rest if P else '(outputs)')
        rep = {}
        for nn, nd in sorted(m.get('netnames', {}).items(), key=lambda x: (x[1].get('hide_name', 0), x[0].count('.'), len(x[0]))):
            for b in nd['bits']:
                if isinstance(b, int) and b not in rep: rep[b] = nn
        edges = collections.defaultdict(lambda: collections.Counter())
        for b, g in drv.items():
            for h in snk.get(b, ()):
                if h != g:
                    nm = rep.get(b, '?')
                    edges[(g, h)]['(unnamed)' if nm.startswith('$') or '$' in nm.split('.')[-1] else nm] += 1
        groups = collections.Counter(g for g, _ in sub.values())
        lines = {lab: [mr[0], s0, s1] for lab, s0, s1, _ in outer} if mr else {}
        for cn, (g, cd) in sub.items():
            if (not cn.startswith('$') or cd['type'] in Y) and g == cn: lines[g] = [None] + (src_of(cd.get('attributes')) or [None, None])[1:] + [None]
        if P: lines = {}
        return dict(module=mods[k]['name'], prefix=prefix, src=mods[k]['src'], groups=[[g, n, lines.get(g)] for g, n in groups.most_common()],
                    edges=[[g, h, sorted(([n, w] for n, w in c.items()), key=lambda x: -x[1])[:12], sum(c.values())] for (g, h), c in edges.items()])

    diags = {}
    def walk(node, depth):
        if node.get('bb') or depth > a.depth: return
        if node['k'] in Y and node['k'] not in diags:
            try:
                diags[node['k']] = d = diagram(node['k'])
                # drill-down: generate scopes holding several instances (e.g. a for-generate MAC g_mac[0])
                for g, n, _ in d.get('groups', []):
                    if g.startswith('(') or depth > 1: continue
                    ninst = sum(1 for cn, cd in Y[node['k']].get('cells', {}).items() if cn.startswith(g + '.') and (cd['type'] in Y))
                    if ninst >= 3: diags[node['k'] + '|' + g] = diagram(node['k'], g)
            except Exception as e: diags[node['k']] = dict(error=str(e))
        for ch in node.get('c', []): walk(ch, depth + 1)
    walk(T, 0)
    res = dict(schema='opentallas.explorer_elem.rtl.v1', top=top, top_params=params, defines=defs,
               source_commit=(srcroot / 'SOURCE_COMMIT').read_text().strip() if (srcroot / 'SOURCE_COMMIT').exists() else None,
               files=texts, modules=mods, tree=T, diagrams=diags, yosys_script=ys)
    (out / 'rtl.json').write_text(json.dumps(res, separators=(',', ':')))
    print('rtl.json', (out / 'rtl.json').stat().st_size, 'modules', len(mods), 'diagrams', len(diags))


if __name__ == '__main__':
    main()
