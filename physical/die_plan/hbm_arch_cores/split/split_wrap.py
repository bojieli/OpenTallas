#!/usr/bin/env python3
"""ELEM-HBM/SPLIT (2026-10-24): hand-checked plan-pin wrappers for B2r2 split pieces + their exactness miters.

    python3 split_wrap.py --family tkm [--views V1,V2] [--work DIR] [--no-miter] [--mutant]

Per family (one master):
  1. elaborate the bound master twin (bind/asbuilt.json alias) hierarchically -> design A0 (cutmap.py docstring);
  2. per plan view: cutmap.analyse = the HBM-P5 netcut boundary re-derived; bus widths must equal the B2r2 pins file
     (a derived bus wider than the plan only where the canonical top records the as-built read set of a master port,
     the extra bits are dead logic of the RTL elaboration: the miter gives them to the gold as free inputs);
  3. canonical port bit -> master net: member-set tops (build_split_tops emit_wrapper) through the member instance
     pins (roles = split_conn.roles_of); remainder tops (rest_extract + rest_wrap) through the extracted port names
     (flattened master wire bits);
  4. wrapper physical/die_plan/hbm_arch_cores/wrappers/<module>.sv: plan pins exactly, canonical top u_core, every
     canonical input bit = the plan pin bit of its master net or the master constant, outputs open when unpinned;
  5. miter (yosys): gold = the member cells of A0 with the plan pins on their master nets (cutmap classes), gate =
     wrapper + canonical top; non-glue instances (member / kept modules, macros) are everted to ports under common
     names (expose -evert), then equiv_make / equiv_simple / equiv_induct / equiv_status -assert (glue state matched by
     the flattened master names), or SAT on the pure-wiring miter.  --mutant swaps two plan bits of one wrapper and
     requires the miter to FAIL.
"""
import argparse
import collections
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import cutmap                                                       # noqa: E402

REPO = cutmap.REPO
HAC = os.path.dirname(HERE)
HARDEN = os.path.join(REPO, 'physical', 'die_plan', 'hbm', 'cores', 'harden')
sys.path.insert(0, HARDEN)
YOSYS = os.path.expanduser('~/.local/opentallas-tools/bin/yosys')
PINS_DIR = '/srv/opentallas-scratch/claude/elem-hbm/inputs/physical/die_plan/hbm_arch/B2r2'
WORK0 = '/srv/opentallas-scratch/claude/elem-hbm/split/work'


def nat(p):
    return [int(x) if x.isdigit() else x for x in re.split(r'(\d+)', p)]


def roles_of(paths):
    """split_conn.roles_of: instance base name (last '/'- or '.'-level), ordinal-suffixed in natural path order."""
    base = [re.split(r'[/.]', p)[-1] for p in paths]
    cnt = collections.Counter(base)
    out, seen = [None] * len(paths), collections.Counter()
    for i in sorted(range(len(paths)), key=lambda i: nat(paths[i])):
        b = base[i]
        if cnt[b] > 1:
            out[i] = f'{b}{seen[b]}'; seen[b] += 1
        else:
            out[i] = b
    return out


# ---------------------------------------------------------------------------------------------------- families
def tkm_views():
    tiles = [f'u/g_tiles[{k}].e86.u_tile' for k in range(32)]
    v = {f'ot_hgi_coll_tkm_m_tp192__tile{k}': dict(include=[tiles[k]], exclude=[], strip=tiles[k] + '/', kind='members')
         for k in range(32)}
    v['ot_hgi_coll_tkm_m_tp192__root'] = dict(include=[''], exclude=tiles, strip='', kind='rest')
    return v


FAMILIES = {
    'tkm': dict(
        master='ot_hgi_coll_tkm_m_tp192', twin='ot_hgi_coll_tkm_m_tp192_p', params={}, defines=[],
        flatten_types=[r'\\ot_hgi_coll_tkm_static_p$'],
        ren=[(r'^u/', 'u/u/')],     # twin hdl path -> as-built path (as-built ot_hgi_coll_tkm_m -> u -> u)
        views=tkm_views),
}


# ---------------------------------------------------------------------------------------------------- helpers
def sh(cmd, log=None, cwd=None):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=cwd)
    if log:
        open(log, 'w').write(r.stdout + r.stderr)
    return r


def yosys(script, path, log):
    open(path, 'w').write(script)
    r = subprocess.run([YOSYS, '-q', '-l', log, '-s', path], capture_output=True, text=True, cwd=os.path.dirname(path))
    return r.returncode, r.stdout + r.stderr


def master_files(top):
    r = subprocess.run([sys.executable, os.path.join(REPO, 'tools', 'hbm_die_v15', 'master_filelist.py'), top,
                        '--root', REPO, '--json'], capture_output=True, text=True,
                       env=dict(os.environ, HDIE_ALLOW_AMBIGUOUS='1'), cwd=REPO)
    if r.returncode:
        raise SystemExit(f'master_filelist {top}: {r.stderr[-2000:]}')
    return json.loads(r.stdout)


def read_cmds(files, macros, defines):
    d = ''.join(f' -D{x}' for x in ['SYNTHESIS'] + list(defines))
    L = [f"read_verilog -lib {os.path.join(REPO, m['file'])}" for m in macros]
    L += [f"read_verilog -sv{d} {os.path.join(REPO, f)}" for f in files]
    return L


def elab_master(F, work):
    """hier.json (hierarchy kept) and A0.json (flatten the include-prefix module types only, opt_clean)."""
    os.makedirs(work, exist_ok=True)
    a0 = os.path.join(work, 'A0.json')
    if os.path.exists(a0):
        return json.load(open(a0))
    fl = master_files(F['twin'])
    json.dump(fl, open(os.path.join(work, 'master_files.json'), 'w'), indent=1)
    L = read_cmds(fl['files'], fl.get('macros', []), F['defines'])
    for k, v in F['params'].items():
        L.append(f'chparam -set {k} {v} {F["twin"]}')
    L += [f'hierarchy -check -top {F["twin"]}', 'proc', 'opt_clean', 'write_json hier.json']
    rc, out = yosys('\n'.join(L) + '\n', os.path.join(work, 'hier.ys'), os.path.join(work, 'hier.log'))
    if rc:
        raise SystemExit(f'master elaboration failed: {out[-3000:]}')
    hj = json.load(open(os.path.join(work, 'hier.json')))
    flat = [m for m in hj['modules'] if any(re.search(rx, m) for rx in F['flatten_types'])]
    L = ['read_json hier.json', f'hierarchy -top {F["twin"]}', 'setattr -mod -set keep_hierarchy 1 *']
    L += [f'setattr -mod -unset keep_hierarchy {m}' for m in flat]
    L += ['flatten', 'opt_clean', 'write_json A0.json']
    rc, out = yosys('\n'.join(L) + '\n', os.path.join(work, 'a0.ys'), os.path.join(work, 'a0.log'))
    if rc:
        raise SystemExit(f'A0 failed: {out[-3000:]}')
    return json.load(open(a0))


def ren_fn(F):
    def ren(s):
        for a, b in F['ren']:
            s = re.sub(a, b, s)
        return s
    return ren


def plan_view(module):
    V = json.load(open(os.path.join(HAC, 'views_b2r2.json')))
    vs = [v for v in V['view_list'] if v['module'] == module]
    if len(vs) != 1:
        raise SystemExit(f'{module}: {len(vs)} views')
    v = vs[0]
    pins = json.load(open(os.path.join(PINS_DIR, v['pins_file'])))
    if hashlib.sha256(open(os.path.join(PINS_DIR, v['pins_file']), 'rb').read()).hexdigest() != v['pins_sha256']:
        raise SystemExit('pins file changed')
    return v, pins


def canon_info(module, v):
    C = json.load(open(os.path.join(HARDEN, 'canonical_ports_split.json')))['types'][v['canonical_type']]
    tid = next(t for t in C['type_ids'] if re.sub(r'__[\d.]+x[\d.]+$', '', t) == module)
    R = json.load(open(os.path.join(HARDEN, 'recipes_split.json')))[tid]
    return C, C['type_ids'][tid], R


# ---------------------------------------------------------------------------------------------------- gate side
def canon_json(C, R, work):
    """member-set canonical top elaborated (yosys JSON): port bits -> member cell pins."""
    out = os.path.join(work, f'canon_{C["top"]}.json')
    if os.path.exists(out):
        return json.load(open(out))
    files = list(dict.fromkeys(R['files'] + [C['file']]))
    L = read_cmds(files, [{'file': f'physical/asap7_memory_macros_v2/{m}/{m}_bb.v'} for m in R.get('macros', [])], [])
    L += [f'hierarchy -check -top {C["top"]}', 'proc', 'opt_clean', f'write_json {out}']
    rc, o = yosys('\n'.join(L) + '\n', out + '.ys', out + '.log')
    if rc:
        raise SystemExit(f'canonical elaboration failed: {o[-3000:]}')
    return json.load(open(out))


def gate_members(cj, top, members_A0):
    """canonical port bit -> [(A0 member path, port, idx)] ; also checks member types equal the master's."""
    mod = cj['modules'][top]
    paths = [p for p, _, _ in members_A0]
    roles = dict(zip(roles_of(paths), members_A0))
    bitpins = collections.defaultdict(list)
    for c, x in mod['cells'].items():
        if c not in roles:
            raise SystemExit(f'canonical cell {c} has no master member (roles {sorted(roles)})')
        path, ty, _ = roles[c]
        if x['type'] != ty:
            raise SystemExit(f'member type differs: canonical {c} = {x["type"]}, master {path} = {ty}')
        for pn, bl in x['connections'].items():
            for i, b in enumerate(bl):
                bitpins[b].append((path, pn, i, x['port_directions'][pn]))
    if len(roles) != len(mod['cells']):
        raise SystemExit(f'canonical has {len(mod["cells"])} members, master {len(roles)}')
    out = {}
    for pn, p in mod['ports'].items():
        out[pn] = (p['direction'], [bitpins.get(b, []) if b not in cutmap.CONST else b for b in p['bits']])
    return out


def member_pin_net(A0top, scopes):
    """(path, port, idx) -> A0 bit (net id or const) for every hierarchical cell of A0."""
    m = {}
    for c, x in A0top['cells'].items():
        if x['type'] == '$scopeinfo':
            continue
        p = cutmap.cell_path(c, x, scopes)
        for pn, bl in x['connections'].items():
            for i, b in enumerate(bl):
                m[(p, pn, i)] = b
    return m


def rest_wrapper_ports(C):
    """remainder canonical top (rest_wrap.py format): canonical port bit -> extracted (_x) port bit name or const."""
    txt = open(os.path.join(REPO, C['file'])).read()
    top = C['top']
    m = re.search(r'(?ms)^module\s+' + re.escape(top) + r'\s*\(.*?^endmodule', txt)
    body = m.group(0)
    import rest_wrap
    _, xports = rest_wrap.ports_of(txt, top + '_x')
    xw = {n.lstrip('\\'): (d, w) for n, d, w in xports}
    decl = {}
    for mm in re.finditer(r'^\s+(input|output) wire (?:\[(\d+):0\] )?(\S+?),?$', body, re.M):
        decl[mm.group(3)] = (mm.group(1), int(mm.group(2)) + 1 if mm.group(2) else 1)
    full = collections.defaultdict(dict)
    for mm in re.finditer(r'^\s+assign (\S+)__full\[(\d+)\] = (\S+?);', body, re.M):
        full[mm.group(1)][int(mm.group(2))] = mm.group(3)
    canon = {n: (d, [None] * w) for n, (d, w) in decl.items()}

    def setbit(expr, xname, xi):
        e = expr.strip()
        mm = re.fullmatch(r'(\w+)\[(\d+)\]', e)
        if mm and mm.group(1) in canon:
            canon[mm.group(1)][1][int(mm.group(2))] = (xname, xi); return
        if e in canon and canon[e][1].__len__() == 1:
            canon[e][1][0] = (xname, xi); return
        raise ValueError(f'cannot place {e}')
    for mm in re.finditer(r'\.(\\\S+\s|[A-Za-z_][\w$]*)\s*\(([^()]*)\)', body):
        xn = mm.group(1).strip().lstrip('\\')
        e = mm.group(2).strip()
        d, w = xw[xn]
        if e == '':
            continue                                                   # open output
        if re.fullmatch(r"\d+'b[01]+", e):
            continue                                                   # never-read master bits, tied inside
        if e.endswith('__full'):
            base = e[:-6]
            for i in range(w):
                src = full[base][i]
                if src.startswith("1'b"):
                    continue
                mi = re.fullmatch(r'(\w+)\[(\d+)\]', src)
                if mi:
                    canon[mi.group(1)][1][int(mi.group(2))] = (xn, i)
                else:
                    canon[src][1][0] = (xn, i)
            continue
        if w == 1:
            setbit(e, xn, 0)
        else:
            if e in canon and len(canon[e][1]) == w:
                for i in range(w):
                    canon[e][1][i] = (xn, i)
            else:
                raise ValueError(f'{xn}: {e}')
    miss = [(n, i) for n, (d, bl) in canon.items() for i, b in enumerate(bl) if b is None]
    # rest_wrap --add ports (constant nets carried by the cut) are not connected to _x
    return canon, miss, xw


def xname_net(A0top, xn, xi, xw):
    """extracted port name (flattened master wire, splitnets form 'w[i]') -> A0 bit."""
    nn = A0top['netnames']
    pt = A0top['ports']
    if xn in pt and xw[xn][1] == len(pt[xn]['bits']):
        return pt[xn]['bits'][xi]
    if xn in nn and len(nn[xn]['bits']) == xw[xn][1]:
        return nn[xn]['bits'][xi]
    mm = re.fullmatch(r'(.*)\[(-?\d+)\]', xn)
    if mm and xw[xn][1] == 1:
        base, k = mm.group(1), int(mm.group(2))
        w = nn.get(base) or pt.get(base)
        if w is not None:
            off = w.get('offset', 0)
            upto = w.get('upto', 0)
            idx = (k - off) if not upto else (len(w['bits']) - 1 - (k - off))
            return w['bits'][idx]
    raise KeyError(xn)


# ---------------------------------------------------------------------------------------------------- main build
def build_view(F, A0, module, spec, work, report, mutant=False):
    v, pins = plan_view(module)
    C, TI, R = canon_info(module, v)
    top = F['twin']
    A0top = A0['modules'][top]
    scopes = cutmap.scopes_of(A0top)
    P = cutmap.analyse(A0, top, spec['include'], spec['exclude'], ren_fn(F), spec['strip'])
    bad = cutmap.check_plan(P, pins)
    planw = collections.Counter(re.sub(r'\[\d+\]$', '', p['name']) for p in pins)
    order = list(dict.fromkeys(re.sub(r'\[\d+\]$', '', p['name']) for p in pins))
    scal = {b: not any(p['name'].startswith(b + '[') for p in pins) for b in order}
    pm = member_pin_net(A0top, scopes)
    # gate: canonical port bit -> A0 net
    cbit = {}                       # canonical port -> (dir, [A0 bit or const or None])
    if spec['kind'] == 'members':
        cj = canon_json(C, R, work)
        gm = gate_members(cj, C['top'], P.members)
        for pn, (d, bl) in gm.items():
            nets = []
            for pinl in bl:
                if isinstance(pinl, str):
                    nets.append(pinl); continue
                s = {pm[(p, n, i)] for p, n, i, _ in pinl}
                if d == 'output':
                    s = {pm[(p, n, i)] for p, n, i, dd in pinl if dd == 'output'}
                if len(s) != 1:
                    raise SystemExit(f'{module}: canonical {pn} bit -> {len(s)} master nets {pinl[:3]}')
                nets.append(s.pop())
            cbit[pn] = (d, nets)
    else:
        canon, miss, xw = rest_wrapper_ports(C)
        if miss:
            report.setdefault('notes', []).append(f'canonical bits not wired to the extracted core: {miss[:6]}')
        for pn, (d, bl) in canon.items():
            cbit[pn] = (d, [xname_net(A0top, xn, xi, xw) if xb is not None else None
                            for xb in bl for xn, xi in [xb if xb else (None, None)]])
    net2canon_in = collections.defaultdict(list)
    net2canon_out = collections.defaultdict(list)
    for pn, (d, nets) in cbit.items():
        for j, b in enumerate(nets):
            if b is None or b in cutmap.CONST:
                continue
            (net2canon_in if d == 'input' else net2canon_out)[b].append((pn, j))
    # plan bus -> nets; widths: exact, or the canonical read set of a master port (dead RTL bits)
    pbits, dead = {}, {}
    for bus in order:
        nets = P.bus.get(bus)
        if nets is None:
            raise SystemExit(f'{module}: plan bus {bus} not derived from the master (PLAN ITEM)')
        if len(nets) != planw[bus]:
            if P.dirs[bus] == 'input':
                rd = [b for b in nets if b in net2canon_in]
                if len(rd) == planw[bus]:
                    dead[bus] = [b for b in nets if b not in net2canon_in]
                    nets = rd
            if len(nets) != planw[bus]:
                raise SystemExit(f'{module}: bus {bus} plan {planw[bus]} derived {len(nets)} (PLAN ITEM)')
        pbits[bus] = nets
    extra = [b for b in P.bus if b not in planw]
    if extra:
        raise SystemExit(f'{module}: derived buses not in the plan {extra} (PLAN ITEM)')
    # wrapper connections
    srcs = {}                                  # A0 net -> plan bit expr (inputs)
    conns = {}
    outs_assign = []
    for bus in order:
        d = P.dirs[bus]
        for i, b in enumerate(pbits[bus]):
            e = bus if scal[bus] else f'{bus}[{i}]'
            if d == 'input':
                if not net2canon_in.get(b):
                    report.setdefault('unread_plan_inputs', []).append(e)
                srcs[b] = e
            else:
                cs = net2canon_out.get(b)
                if not cs:
                    raise SystemExit(f'{module}: plan output {e} has no canonical driver')
                pn, j = cs[0]
                outs_assign.append((e, pn, j))
    if mutant:                                 # mutant control: swap bits 0 and 1 of the first wide read input bus
        for bus in order:
            nb = pbits[bus]
            if P.dirs[bus] == 'input' and len(nb) >= 2 and nb[0] in net2canon_in and nb[1] in net2canon_in:
                srcs[nb[0]], srcs[nb[1]] = srcs[nb[1]], srcs[nb[0]]
                report['mutant'] = f'{bus}[0] <-> {bus}[1]'
                break
    ties, opens = [], []
    for pn, (d, nets) in cbit.items():
        if d == 'input':
            row = []
            for j, b in enumerate(nets):
                if b in cutmap.CONST:
                    row.append(f"1'b{b if b in '01' else '0'}"); ties.append(f'{pn}[{j}]={b}')
                elif b in srcs:
                    row.append(srcs[b])
                elif b is None:
                    raise SystemExit(f'{module}: canonical input {pn}[{j}] unwired')
                else:
                    raise SystemExit(f'{module}: canonical input {pn}[{j}] on master net {b} with no plan pin')
            conns[pn] = row
        else:
            used = {j for (_, p2, j) in outs_assign if p2 == pn}
            opens += [f'{pn}[{j}]' for j in range(len(nets)) if j not in used]
    txt = emit(module, order, P.dirs, planw, scal, C['top'], cbit, conns, outs_assign, v)
    report.update(dict(module=module, view=v['view'], canonical_type=v['canonical_type'], canonical_top=C['top'],
                       plan_buses=len(order), plan_bits=sum(planw.values()), width_check='PASS' if not bad else
                       f'DEAD_BITS {sorted((k, len(x)) for k, x in dead.items())}',
                       tied_canonical_bits=len(ties), open_canonical_bits=len(opens)))
    return txt, dict(P=P, pbits=pbits, dead=dead, order=order, scal=scal, C=C, R=R, v=v, cbit=cbit)


def runs(items):
    """[expr per bit lsb first] -> verilog concat (msb first) with bus[a:b] runs."""
    parts = []
    for e in reversed(items):
        mm = re.fullmatch(r'(\w+)\[(\d+)\]', e)
        if parts and mm:
            pm_ = re.fullmatch(r'(\w+)\[(\d+)(?::(\d+))?\]', parts[-1])
            if pm_ and pm_.group(1) == mm.group(1):
                lo = int(pm_.group(3) if pm_.group(3) is not None else pm_.group(2))
                hi = int(pm_.group(2))
                if int(mm.group(2)) == lo - 1:
                    parts[-1] = f'{mm.group(1)}[{hi}:{lo - 1}]'
                    continue
        parts.append(e)
    return parts[0] if len(parts) == 1 else '{' + ', '.join(parts) + '}'


def emit(module, order, dirs, planw, scal, ctop, cbit, conns, outs_assign, v):
    L = [f'// GENERATED by physical/die_plan/hbm_arch_cores/split/split_wrap.py (ELEM-HBM/SPLIT 2026-10-24). Do not edit.',
         f'// Plan module {module} (B2r2 view {v["view"]}, pins {v["pins_file"]}): exactly the plan pins, wired per bit',
         f'// to the canonical top {ctop} as the bound master wires them (bit i of a plan bus = i-th boundary net in',
         f'// ascending index on its labelling pin; split/cutmap.py).  Exactness: wrappers/{v["family"].lower()}_exactness.json.',
         '`default_nettype none', f'module {module} (']
    decl = []
    for b in order:
        w = planw[b]
        decl.append(f'    {dirs[b]} wire {"" if scal[b] else f"[{w - 1}:0] "}{b}')
    L.append(',\n'.join(decl))
    L.append(');')
    for pn, (d, nets) in cbit.items():
        if d == 'output':
            L.append(f'    wire {"[%d:0] " % (len(nets) - 1) if len(nets) > 1 else ""}c_{pn};')
    cl = []
    for pn, (d, nets) in cbit.items():
        if d == 'input':
            cl.append(f'        .{pn}({runs(conns[pn])})')
        else:
            cl.append(f'        .{pn}(c_{pn})')
    L.append(f'    {ctop} u_core (\n' + ',\n'.join(cl) + ');')
    per = collections.OrderedDict()
    for e, pn, j in outs_assign:
        w = len(cbit[pn][1])
        bus = re.sub(r'\[\d+\]$', '', e)
        per.setdefault(bus, []).append(f'c_{pn}[{j}]' if w > 1 else f'c_{pn}')
    for bus, src in per.items():
        L.append(f'    assign {bus} = {runs(src)};')
    L += ['endmodule', '`default_nettype wire', '']
    return '\n'.join(L)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--family', required=True)
    ap.add_argument('--views', default='')
    ap.add_argument('--work', default=WORK0)
    ap.add_argument('--out', default=os.path.join(HAC, 'wrappers'))
    ap.add_argument('--no-miter', action='store_true')
    ap.add_argument('--mutant', default='', help='views (comma) that also get the mutant control')
    a = ap.parse_args()
    F = FAMILIES[a.family]
    work = os.path.join(a.work, a.family)
    A0 = elab_master(F, work)
    specs = F['views']()
    sel = [x for x in a.views.split(',') if x] or list(specs)
    res = {}
    for module in sel:
        rep = {}
        try:
            txt, info = build_view(F, A0, module, specs[module], work, rep)
        except SystemExit as e:
            rep['error'] = str(e)
            print(module, 'ERROR', e)
            res[module] = rep
            continue
        open(os.path.join(a.out, f'{module}.sv'), 'w').write(txt)
        json.dump({k: v for k, v in info.items() if k in ('pbits', 'dead', 'order')},
                  open(os.path.join(work, f'{module}.map.json'), 'w'))
        if not a.no_miter:
            import miter
            rep['miter'] = miter.run(None, A0, F['twin'], module, specs[module], info, txt, work, '', roles_of)
            if module in a.mutant.split(','):
                mrep = {}
                mtxt, minfo = build_view(F, A0, module, specs[module], work, mrep, mutant=True)
                rep['mutant'] = dict(swap=mrep.get('mutant'),
                                     **miter.run(None, A0, F['twin'], module, specs[module], minfo, mtxt, work,
                                                 '__mutant', roles_of))
                rep['mutant']['caught'] = rep['mutant']['verdict'] == 'FAIL'
        res[module] = rep
        print(module, json.dumps({k: (v if k not in ('miter', 'mutant') else {kk: vv for kk, vv in v.items()
                                                                             if kk in ('verdict', 'unproven', 'equiv_cells', 'caught', 'swap', 'stage', 'notes')})
                                  for k, v in rep.items()})[:900])
    json.dump(res, open(os.path.join(work, 'build_report.json'), 'w'), indent=1)


if __name__ == '__main__':
    main()
