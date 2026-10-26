#!/usr/bin/env python3
"""frame_hier_part.py -- split a flat landed-frame top (lp kit / twin RTL) into hard row-band modules + a wiring top.

The partition is purely structural: the same instances, the same nets, the same parameters.  The flattened netlist is
identical to the input (so the per-net latency, the lp schedule and every bench result are unchanged); the top keeps
its module name, parameters and ports byte-identical.  Instances move into band modules <top>_b<k>; assigns move with
them when every net they touch lives in one band; every other net is a band port (in / out by its driver).

  frame_hier_part.py --rtl IN.sv --top col_h9_l4_lp --bands bands.json --out OUT.sv [--sources-spec kit/spec.json]

bands.json: {"inst": {"u_x": 0, ...}} for the ORIGINAL children; lp-generated instances (pads, rings, reads, forests)
follow their neighbours (u_lprc_<c> -> c; rings -> source children, reads -> readers, forests -> leaf majority), with
"force": {"u_frl_rst": 0, ...} overrides.
"""
import argparse, collections, json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'tools/landed_parent')]
import lp  # noqa: E402

DIR_PRIMS = dict(lp.LIB_PORTS)
DIR_PRIMS['ot_reset_sync'] = {'clk': 'in', 'async_rst_n': 'in', 'sync_rst_n': 'out'}


def strip_comments(t):
    t = re.sub(r'/\*.*?\*/', ' ', t, flags=re.S)
    return re.sub(r'//[^\n]*', '', t)


def statements(rest):
    """split non-instance body text into ';'-terminated statements (paren-aware)"""
    out, d, cur = [], 0, ''
    for ch in rest:
        cur += ch
        if ch in '({[':
            d += 1
        elif ch in ')}]':
            d -= 1
        elif ch == ';' and d == 0:
            if cur.strip() != ';':
                out.append(cur.strip())
            cur = ''
    if cur.strip():
        raise SystemExit(f'trailing body text: {cur.strip()[:80]}')
    return out


def eval_range(rng, env):
    if not rng:
        return None
    hi, lo = lp.split_range(rng)
    e = lambda x: int(eval(lp.c_to_py(x), {}, env))
    return f'[{e(hi)}:{e(lo)}]'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--rtl', required=True)
    ap.add_argument('--top', required=True)
    ap.add_argument('--bands', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--sources', nargs='*', default=[], help='module sources for child port directions')
    ap.add_argument('--defines', nargs='*', default=[])
    ap.add_argument('--report')
    ap.add_argument('--feedthrough', action='store_true', help='chain non-adjacent band nets through the bands between')
    ap.add_argument('--mut0-assigns', action='store_true',
                    help='synthesis kit: resolve (MUT == k) ? A : B in assigns to B (the kit elaborates MUT = 0), so a landing '
                         'read feeds its band readers directly instead of through a top-level mutant mux')
    a = ap.parse_args()
    raw = (ROOT / a.rtl).read_text()
    text = strip_comments(raw)
    mod = lp.parse_module(text, a.top)
    body = mod['body']
    _, _, insts = lp.parse_body(body)
    # non-instance statements
    rest, last = [], 0
    for ins in insts:
        rest.append(body[last:ins['span'][0]])
        last = ins['span'][1]
    rest.append(body[last:])
    stm = statements(' '.join(rest))
    env = {}
    for k, v in mod['params'].items():
        try:
            env[k] = int(eval(lp.c_to_py(v), {}, env))
        except Exception:
            pass
    decls, assigns, lparams = {}, [], []
    for s in stm:
        m = re.match(r'(localparam|parameter)\b', s)
        if m:
            lparams.append(s)
            mm = re.match(r'localparam\s+(?:integer\s+|int\s+)?(\w+)\s*=\s*(.+);', s, re.S)
            if mm:
                env[mm.group(1)] = int(eval(lp.c_to_py(mm.group(2)), {}, env))
            continue
        m = re.match(r'wire\s*(?:signed\s*)?(\[[^\]]*\])?\s*(.+);$', s, re.S)
        if m:
            rng = m.group(1)
            items = lp.split_top(m.group(2))
            for it in items:
                m2 = re.match(r'\s*(\w+)\s*(=\s*(.+))?$', it, re.S)
                decls[m2.group(1)] = rng
                if m2.group(2):
                    assigns.append(dict(lhs=m2.group(1), rhs=m2.group(3).strip(), text=f'assign {m2.group(1)} = {m2.group(3).strip()};'))
            continue
        if a.mut0_assigns:
            s = re.sub(r'\(MUT == \d+\)\s*\?\s*([^:;]+?)\s*:\s*([^;]+?);', r'\2;', s)
        m = re.match(r'assign\s+(.+?)\s*=\s*(.+);$', s, re.S)
        if m:
            assigns.append(dict(lhs=m.group(1).strip(), rhs=m.group(2).strip(), text=s))
            continue
        raise SystemExit(f'unhandled statement: {s[:120]}')
    ports = {p['name']: p for p in mod['ports']}
    nets = set(decls) | set(ports)
    # child port directions
    src = '\n'.join(lp.preprocess((ROOT / f).read_text(errors='replace'), a.defines) for f in a.sources)
    pdir = {}
    def dirs(m):
        if m not in pdir:
            if m in DIR_PRIMS:
                pdir[m] = DIR_PRIMS[m]
            else:
                pm = lp.parse_module(src, m)
                pdir[m] = {p['name']: p['dir'] for p in pm['ports']}
        return pdir[m]
    nid = lambda e: {n for n in lp.idents(e) if n in nets}
    # ---- band of every instance
    B = json.loads((ROOT / a.bands).read_text() if not Path(a.bands).is_absolute() else Path(a.bands).read_text())
    band = dict(B['inst'])
    band.update(B.get('force', {}))
    byname = {i['inst']: i for i in insts}
    for i in insts:
        m = re.match(r'u_lprc_(u_\w+)$', i['inst'])
        if m and m.group(1) in band and i['inst'] not in band:
            band[i['inst']] = band[m.group(1)]
    users = collections.defaultdict(set)          # net -> instance names
    for i in insts:
        for pin, e in i['conns'].items():
            for n in nid(e):
                users[n].add(i['inst'])
    alias = collections.defaultdict(set)          # net <-> net through assigns
    for s in assigns:
        ns = nid(s['lhs']) | nid(s['rhs'])
        for x in ns:
            alias[x] |= ns
    def reach(n, depth=4):
        seen, fr = {n}, {n}
        for _ in range(depth):
            fr = {y for x in fr for y in alias[x]} - seen
            seen |= fr
        return seen
    # an lp-generated instance may only join a band whose original children share its clock net
    ckb = collections.defaultdict(set)
    CKP = ('ck', 'clk')
    for i in insts:
        if i['inst'] in band:
            for pin in CKP:
                if pin in i['conns']:
                    ckb[i['conns'][pin].strip()].add(band[i['inst']])
    for _ in range(6):
        changed = False
        for i in insts:
            if i['inst'] in band:
                continue
            votes = collections.Counter()
            for pin, e in i['conns'].items():
                if pin in ('ck', 'clk', 'rsi'):
                    continue
                for n in nid(e):
                    if n in ports:
                        continue
                    for x in reach(n):
                        for u in users[x]:
                            if u != i['inst'] and u in band and not u.startswith('u_lpl_'):
                                votes[band[u]] += 1
            ck = next((i['conns'][p].strip() for p in CKP if p in i['conns']), None)
            if ck in ckb:
                votes = collections.Counter({b: v for b, v in votes.items() if b in ckb[ck]})
            if votes:
                band[i['inst']] = votes.most_common(1)[0][0]
                changed = True
        if not changed:
            break
    miss = [i['inst'] for i in insts if i['inst'] not in band]
    if miss:
        raise SystemExit(f'unbanded instances: {miss[:20]} ({len(miss)})')
    # ---- assign clusters
    loc_ref = collections.defaultdict(set)        # net -> locations of instance references
    for i in insts:
        for pin, e in i['conns'].items():
            for n in nid(e):
                loc_ref[n].add(band[i['inst']])
    for p in ports:
        loc_ref[p].add('top')
    par = list(range(len(assigns)))
    def f(x):
        while par[x] != x:
            par[x] = par[par[x]]; x = par[x]
        return x
    by_net = collections.defaultdict(list)
    for k, s in enumerate(assigns):
        s['nets'] = nid(s['lhs']) | nid(s['rhs'])
        for n in s['nets']:
            by_net[n].append(k)
    for n, ks in by_net.items():
        for k in ks[1:]:
            par[f(k)] = f(ks[0])
    clus = collections.defaultdict(list)
    for k in range(len(assigns)):
        clus[f(k)].append(k)
    aloc = {}
    for c, ks in clus.items():
        locs = set()
        for k in ks:
            for n in assigns[k]['nets']:
                locs |= loc_ref[n]
        L = next(iter(locs)) if len(locs) == 1 else 'top'
        for k in ks:
            aloc[k] = L
    # ---- net locations, drivers
    nloc = collections.defaultdict(set)
    drv = collections.defaultdict(set)
    for i in insts:
        d = dirs(i['module'])
        for pin, e in i['conns'].items():
            if pin not in d:
                raise SystemExit(f"{i['inst']}: {i['module']} has no port {pin}")
            for n in nid(e):
                nloc[n].add(band[i['inst']])
                if d[pin] == 'out':
                    drv[n].add(band[i['inst']])
    for k, s in enumerate(assigns):
        for n in s['nets']:
            nloc[n].add(aloc[k])
        for n in nid(s['lhs']):
            drv[n].add(aloc[k])
    for p, pp in ports.items():
        nloc[p].add('top')
        if pp['dir'] == 'in':
            drv[p].add('top')
    multi = {n: sorted(map(str, v)) for n, v in drv.items() if len(v) > 1}
    if multi:
        raise SystemExit(f'nets driven from more than one location (bit-split needed): {list(multi.items())[:10]}')
    bands = sorted({b for b in band.values()})
    width = lambda n: eval_range(decls.get(n) if n in decls else ports[n]['range'], env)
    bp = {b: [] for b in bands}
    internal = {b: [] for b in bands}
    for n in sorted(nloc):
        L = nloc[n]
        if len(L) == 1 and 'top' not in L:
            internal[next(iter(L))].append(n)
            continue
        for b in L:
            if b == 'top':
                continue
            bp[b].append((n, 'output' if b in drv[n] else 'input'))
    # ---- feedthroughs (--feedthrough): a net from band d to bands beyond d+1 is chained band to band (rows abut, the
    # frame top has no channel): band k < the farthest reader takes it in and re-drives it as <n>__ft<k> (a plain assign,
    # no cell), and band k+1 reads that copy.  The flattened netlist is the same net.
    topconn = {b: {} for b in bands}
    ft_assigns = {b: [] for b in bands}
    ft_wires = []
    for n in sorted(nloc):
        L = sorted(x for x in nloc[n] if x != 'top')
        if not a.feedthrough or len(L) < 2 or L[-1] - L[0] <= 1:
            continue
        d = drv[n] - {'top'}
        if 'top' in nloc[n] or d != {L[0]}:
            raise SystemExit(f'feedthrough {n}: needs a single driver band below its readers and no top use ({L}, drv {d})')
        for k in range(L[0] + 1, L[-1]):
            if k not in L:
                bp[k].append((n, 'input'))
            bp[k].append((f'{n}__ft{k}', 'output'))
            ft_assigns[k].append(f'assign {n}__ft{k} = {n};')
            ft_wires.append(f'{n}__ft{k}')
            topconn[k + 1][n] = f'{n}__ft{k}'
            if n in decls:
                decls[f'{n}__ft{k}'] = decls[n]
    # ---- emit
    params_txt = mod['params_txt'] or ''
    # every header parameter (incl. typed ones: 'parameter string INSTANCE' names the ROM images -- S81-P6 10-23: the
    # bands defaulted INSTANCE, so ROM instance names diverged from the flat frame)
    pnames = re.findall(r'\bparameter\s+(?:(?:string|integer|int|bit|logic|real)\s+)?(?:\[[^\]]*\]\s*)?(\w+)\s*=', params_txt)
    out = [f'// GENERATED by tools/s81_dv/frame_hier_part.py from {a.rtl} -- hard row bands {bands}; the flattened netlist '
           f'is the input netlist (same instances, nets, parameters).', '`default_nettype none']
    lp_txt = '\n'.join('    ' + s for s in lparams if s.startswith('localparam'))
    for b in bands:
        out.append(f'module {a.top}_b{b} #({params_txt}) (')
        pl = []
        for n, d in bp[b]:
            r = width(n)
            pl.append(f'    {d} wire {r + " " if r else ""}{n}')
        out.append(',\n'.join(pl))
        out.append(');')
        out.append(lp_txt)
        for n in internal[b]:
            r = width(n)
            out.append(f'    wire {r + " " if r else ""}{n};')
        for k, s in enumerate(assigns):
            if aloc[k] == b:
                out.append('    ' + s['text'])
        out += ['    ' + t for t in ft_assigns[b]]
        for i in insts:
            if band[i['inst']] == b:
                out.append('    ' + body[i['span'][0]:i['span'][1]].strip())
        out.append('endmodule\n')
    # top: original header verbatim
    hdr = re.search(rf'\bmodule\s+{re.escape(a.top)}\b.*?\);', text, re.S).group(0)
    out.append(hdr)
    out.append(lp_txt)
    top_nets = sorted(n for n in nloc if n not in ports and not (len(nloc[n]) == 1 and 'top' not in nloc[n]))
    for n in top_nets + ft_wires:
        r = width(n)
        out.append(f'    wire {r + " " if r else ""}{n};')
    for k, s in enumerate(assigns):
        if aloc[k] == 'top':
            out.append('    ' + s['text'])
    pass_params = ', '.join(f'.{k}({k})' for k in pnames)
    for b in bands:
        conns = ',\n'.join(f'        .{n}({topconn[b].get(n, n)})' for n, _ in bp[b])
        out.append(f'    {a.top}_b{b} #({pass_params}) u_b{b} (\n{conns}\n    );')
    out.append('endmodule\n`default_nettype wire\n')
    Path(a.out).write_text('\n'.join(out))
    rep = dict(bands={str(b): dict(insts=sum(1 for v in band.values() if v == b), ports=len(bp[b]),
                                    port_bits=None, internal_nets=len(internal[b]),
                                    assigns=sum(1 for v in aloc.values() if v == b)) for b in bands},
               top_assigns=sum(1 for v in aloc.values() if v == 'top'), top_nets=len(top_nets),
               inst_band={k: v for k, v in band.items()})
    nb = {}
    for b in bands:
        tot = 0
        for n, _ in bp[b]:
            r = width(n)
            tot += 1 if not r else abs(int(r[1:-1].split(':')[0]) - int(r[1:-1].split(':')[1])) + 1
        rep['bands'][str(b)]['port_bits'] = tot
    # crossing nets between band pairs (non-adjacent flagged)
    pairs = collections.Counter()
    for n, L in nloc.items():
        bl = sorted(x for x in L if x != 'top')
        for x in range(len(bl)):
            for y in range(x + 1, len(bl)):
                pairs[f'{bl[x]}-{bl[y]}'] += 1
    rep['band_pair_nets'] = dict(pairs)
    rep['far_nets'] = {n: sorted(str(x) for x in L) for n, L in nloc.items()
                       if len([x for x in L if x != 'top']) > 1 and max(x for x in L if x != 'top') - min(x for x in L if x != 'top') > 1}
    rep['top_port_bands'] = {p: sorted(str(x) for x in nloc[p] if x != 'top') for p in ports}
    if a.report:
        Path(a.report).write_text(json.dumps(rep, indent=1))
    print(json.dumps({k: v for k, v in rep.items() if k != 'inst_band'}, indent=None)[:3000])


if __name__ == '__main__':
    main()
