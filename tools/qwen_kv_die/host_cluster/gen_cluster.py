#!/usr/bin/env python3
"""KVJ-A3 (10-17): generate the HOST root cluster RTL (A3/A4/A5) from the UNCHANGED flat sources, exactly.

Input: the r2 partition (results/arch/qwen_split_1014/host_root_cluster/partition_r2.json): child -> member instance
paths of qkd_host_root_admission (ENABLE_SERVICE/NATIVE/TOKEN=1, NL=2 = the kv_die binding).

Method (yosys >= 0.40, no hand-written glue):
 1. p2: a source wrapper qkd_hr_cluster_src with the D3 clock face (ck_core, ck_host, ck_ingest, ck_phy_fam,
    ck_phy[7:0]; each flat clock port is tied to its family net, kv_die.HOST_CLK_FAMILY + HOST_CLK_INFERRED) around the
    flat root; member module types get keep_hierarchy; flatten (A3: the wires-only levels dissolve).
 2. every glue cell (the flattened rank/root/control/bundle/bridge/phy_cdc5/adp512 logic, A4) is moved into the child
    that consumes it (fixpoint over consumers; a cone read only by top ports goes to its drivers' child);
 3. yosys submod cuts one module per child (A5: one port per family clock net, i.e. one clock entry per family);
 4. write_verilog of the cluster top + child wrappers; member instances are rewritten from yosys $paramod names to
    `<module> #(.P(v))` from the derive log, so the members compile from their original RTL.

The result is exact by construction; bench/tb_cluster_lockstep.cpp checks it cycle-by-cycle against the flat root.
usage: gen_cluster.py --partition P.json --out DIR [--yosys Y] [--mutant N]
"""
import argparse
import collections
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tools' / 'qwen_kv_die'))
TOP = 'qkd_host_root_admission'
PARAMS = dict(ENABLE_SERVICE=1, ENABLE_NATIVE=1, ENABLE_TOKEN=1, NL=2)
CENSUS_YS = ROOT / 'results/arch/qwen_split_1014/host_root_cluster/census/elab.ys'
FAM_PORT = dict(core='ck_core', host='ck_host', ingest='ck_ingest', phy='ck_phy_fam')
# KV-CDC2 (10-18): leaf-local CDC forks (same ports/parameters) that the CDC leaves instantiate instead of the shared
# originals; the originals stay unchanged for the closed core children and the flat root
FORKS = json.loads((ROOT / 'rtl/qwen_sys/host_cluster_cdc_20261018/forks.json').read_text())
FORKS.pop('_doc', None)


def src_clocks(D, mod, bit, memo, depth=0):
    """the clock bits (as bits of module `mod`) of the registers whose outputs reach `bit` of `mod` through combinational
    cells; a clock that is not a port bit of `mod` comes back as ('int', bit).  Submodule instances are followed through
    their port maps."""
    key = (mod, bit)
    if key in memo:
        return memo[key]
    memo[key] = set()
    M = D['modules'][mod]
    X = memo.setdefault(('index', mod), {})
    if 'drv' not in X:
        dv = {}
        for n, c in M['cells'].items():
            dirs = c.get('port_directions', {})
            for pn, bb in c['connections'].items():
                if dirs.get(pn) == 'output':
                    for k, b in enumerate(bb):
                        if isinstance(b, int):
                            dv[b] = (n, pn, k)
        X['drv'] = dv
        X['pbit'] = {b: (pn, k) for pn, pd in M['ports'].items() for k, b in enumerate(pd['bits']) if isinstance(b, int)}
    out = set()
    if bit in X['drv'] and depth < 64:
        n, pn, k = X['drv'][bit]
        c = M['cells'][n]
        if 'CLK' in c['connections']:
            cb = c['connections']['CLK'][0]
            out.add(cb if cb in X['pbit'] else ('int', cb))
        elif c['type'] in D['modules']:
            sub = D['modules'][c['type']]
            for cb in src_clocks(D, c['type'], sub['ports'][pn]['bits'][k], memo, depth + 1):
                if isinstance(cb, tuple):
                    out.add(cb)
                else:
                    sp, sk = memo[('index', c['type'])]['pbit'][cb]
                    pb = c['connections'][sp][sk]
                    out.add(pb if pb in X['pbit'] else ('int', pb))
        else:
            for ip, bb in c['connections'].items():
                if c.get('port_directions', {}).get(ip) != 'output':
                    for b in bb:
                        if isinstance(b, int):
                            out |= src_clocks(D, mod, b, memo, depth + 1)
    memo[key] = out
    return out


def family():
    from kv_die import HOST_CLK_FAMILY, HOST_CLK_INFERRED
    return dict(HOST_CLK_FAMILY, **HOST_CLK_INFERRED)


def read_cmds():
    lines = CENSUS_YS.read_text().splitlines()[:2]
    return [l.replace(' src/', ' ' + str(ROOT) + '/') for l in lines]


def yosys(y, script, log, cwd):
    (cwd / (log + '.ys')).write_text(script)
    r = subprocess.run([y, '-q', '-l', str(cwd / (log + '.log')), '-s', str(cwd / (log + '.ys'))],
                       capture_output=True, text=True)
    if r.returncode:
        raise SystemExit(f'yosys {log} failed: ' + (r.stdout + r.stderr)[-3000:])


def lit(v):
    v = v.strip()
    m = re.fullmatch(r"(s?)(\d+)'([01xz]+)", v)
    if m:
        n = int(m.group(3), 2)
        if m.group(1) and m.group(3)[0] == '1':
            n -= 1 << len(m.group(3))
        return str(n)
    if re.fullmatch(r'-?\d+', v) or v.startswith('"'):
        return v
    raise SystemExit(f'unparsed parameter literal {v!r}')


def paramods(log):
    """$paramod name -> (base module, [(param, value)]) from the hierarchy derive messages"""
    out, base, ps = {}, None, []
    for line in log.read_text().splitlines():
        m = re.search(r"derive mode using pre-parsed AST for module `\\(\S+)'", line)
        if m:
            base, ps = m.group(1), []
            continue
        m = re.match(r'\s*Parameter \\(\w+) = (.+)$', line)
        if m and base:
            ps.append((m.group(1), lit(m.group(2))))
            continue
        m = re.search(r"Generating RTLIL representation for module `(\$paramod\S+)'", line)
        if m and base:
            out[m.group(1)] = (base, ps)
            base = None
    return out


def apply_wraps(txt, wraps, strict=True):
    """member instance type <m> -> <wrapper> (instance lines only: `<m> #(...) u_x (` or `<m> u_x (`)"""
    for wv in wraps:
        m = re.fullmatch(r'(\w+)=(\w+)', wv)
        if not m:
            raise SystemExit(f'bad --wrap {wv}')
        pat = re.compile(r'^(\s*)' + m.group(1) + r'(?=\s+(?:#\(|\\?[A-Za-z_]))', re.M)
        txt, n = pat.subn(lambda x: x.group(1) + m.group(2), txt)
        if strict and not n:
            raise SystemExit(f'--wrap {wv}: no instance of {m.group(1)}')
    return txt


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--partition', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--yosys', default=str(Path.home() / '.local/opentallas-tools/yosys-0.68/bin/yosys'))
    ap.add_argument('--work', default=None)
    ap.add_argument('--reuse', action='store_true', help='reuse the work dir yosys passes 1-2')
    ap.add_argument('--mutant', action='append', default=[],
                    help='bench mutant: invert child INPUT bit u_<child>.<port>[i] at the parent (the output must FAIL)')
    ap.add_argument('--wrap', action='append', default=[],
                    help='member wrapper <member module>=<wrapper module> (same ports and parameters; e.g. '
                         'qkd_host_tx_class=qkd_host_tx_class_rr, the NATIVE-FIX3 reset-relay wrappers)')
    ap.add_argument('--wrap-only', default=None,
                    help='apply --wrap to the already generated qkd_hr_*.v files in this dir and exit (no yosys)')
    ap.add_argument('--param', action='append', default=[],
                    help='member parameter override <member module>.<PARAM>=<int> (e.g. qkd_host_rx_class_admission.IR_REPL=1)')
    a = ap.parse_args()
    if a.wrap_only:
        for f in sorted(Path(a.wrap_only).glob('qkd_hr_*.v')):
            t = f.read_text()
            w = apply_wraps(t, a.wrap, strict=False)
            if w != t:
                f.write_text(w)
                print(f'wrapped {f}')
        return
    part = json.load(open(a.partition))
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    work = Path(a.work or out / 'work')
    work.mkdir(parents=True, exist_ok=True)
    fam = family()

    # ---- pass 1: port list + member types (hierarchy only) ---------------------------------------------------------
    chp = ' '.join(f'-chparam {k} {v}' for k, v in PARAMS.items())
    reuse = (work / 'p2.json').exists() and '--reuse' in sys.argv
    if not reuse: yosys(a.yosys, '\n'.join(read_cmds() + [f'hierarchy -check -top {TOP} {chp}', f'select {TOP}',
                                             f'write_json -selected {work}/p1.json']), 'p1', work)
    J = json.load(open(work / 'p1.json'))['modules']
    ports = J[TOP]['ports']

    # ---- source wrapper with the D3 clock face -----------------------------------------------------------------------
    conns, decl = [], ['input wire ck_core', 'input wire ck_host', 'input wire ck_ingest', 'input wire ck_phy_fam',
                       'input wire [7:0] ck_phy']
    for p, d in ports.items():
        w = len(d['bits'])
        if p == 'ck_phy':
            conns.append('.ck_phy(ck_phy)')
        elif p == 'ck_qm_bank':
            conns.append('.ck_qm_bank({2{ck_ingest}})')
        elif p in fam:
            conns.append(f'.{p}({FAM_PORT[fam[p]]})')
        else:
            decl.append(f"{d['direction']} wire {'[%d:0] ' % (w - 1) if w > 1 else ''}{p}")
            conns.append(f'.{p}({p})')
    ps = ','.join(f'.{k}({v})' for k, v in PARAMS.items())
    src = (f'// generated by tools/qwen_kv_die/host_cluster/gen_cluster.py (D3 clock face around the flat root)\n'
           f'module qkd_hr_cluster_src(\n ' + ',\n '.join(decl) + f'\n);\n {TOP} #({ps}) u_root(\n  ' +
           ',\n  '.join(conns) + ');\nendmodule\n')
    (work / 'qkd_hr_cluster_src.v').write_text(src)

    # ---- pass 2: flatten everything but the members ------------------------------------------------------------------
    if not reuse: yosys(a.yosys, '\n'.join(read_cmds() + [f'read_verilog -sv {work}/qkd_hr_cluster_src.v',
                                             'hierarchy -check -top qkd_hr_cluster_src', 'proc', 'opt_clean',
                                             f'write_json {work}/p2a.json']), 'p2a', work)
    D = json.load(open(work / 'p2a.json'))
    J = D['modules']
    member_of, mtypes = {}, set()
    for child, c in part['children'].items():
        for path in c['members']:
            mod = J['qkd_hr_cluster_src']['cells']['u_root']['type']
            for seg in path.split('/')[1:]:
                mod = J[mod]['cells'][seg]['type']
            member_of[path] = child
            mtypes.add(mod)
    for t in mtypes:
        if t not in D['modules']:
            raise SystemExit(f'member type {t} missing after pass 2a')
        D['modules'][t].setdefault('attributes', {})['keep_hierarchy'] = '00000000000000000000000000000001'
    if not reuse: json.dump(D, open(work / 'p2b.json', 'w'))
    if not reuse: yosys(a.yosys, '\n'.join([f'read_json {work}/p2b.json', 'hierarchy -top qkd_hr_cluster_src',
                              'flatten', 'opt_clean', f'write_json {work}/p2.json']), 'p2', work)
    D = json.load(open(work / 'p2.json'))
    T = D['modules']['qkd_hr_cluster_src']
    cells = T['cells']

    # ---- glue ownership ------------------------------------------------------------------------------------------------
    owner = {}
    for path, child in member_of.items():
        name = 'u_root.' + '.'.join(path.split('/')[1:])
        if name not in cells:
            raise SystemExit(f'member cell {name} not found after flatten')
        owner[name] = child
    drv, cons = {}, collections.defaultdict(set)
    for n, c in cells.items():
        if c['type'] == '$scopeinfo':
            continue
        dirs = c.get('port_directions', {})
        for p, bits in c['connections'].items():
            for b in bits:
                if not isinstance(b, int):
                    continue
                if dirs.get(p) == 'output':
                    drv[b] = n
                else:
                    cons[b].add(n)
    for p, d in T['ports'].items():
        for b in d['bits']:
            if isinstance(b, int):
                (cons[b].add('TOP:' + p) if d['direction'] == 'output' else drv.__setitem__(b, 'TOP:' + p))
    glue = [n for n, c in cells.items() if n not in owner and c['type'] != '$scopeinfo']

    def outs(n):
        c = cells[n]
        return [b for p, bits in c['connections'].items() if c.get('port_directions', {}).get(p) == 'output'
                for b in bits if isinstance(b, int)]

    def ins(n):
        c = cells[n]
        return [b for p, bits in c['connections'].items() if c.get('port_directions', {}).get(p) != 'output'
                for b in bits if isinstance(b, int)]
    def settle():
      changed = True
      while changed:
        changed = False
        for n in glue:
              if n in owner:
                  continue
              cs = {x for b in outs(n) for x in cons[b]}
              ow = {owner.get(x, '?') if not x.startswith('TOP:') else 'TOP' for x in cs}
              if '?' in ow:
                  continue
              ow.discard('TOP')
              if len(ow) == 1:
                  owner[n] = ow.pop()
                  changed = True
              elif not ow:
                  ds = {drv.get(b) for b in ins(n)}
                  dow = {owner.get(x, '?') for x in ds if x and not x.startswith('TOP:')}
                  if '?' not in dow and len(dow) == 1:
                      owner[n] = dow.pop()
                      changed = True
    settle()
    # a register / cone whose consumers span several children: it joins the child that drives most of its inputs
    # (the register mass it is computed from); then the consumer fixpoint runs again
    for n in glue:
        if n in owner:
            continue
        dow = collections.Counter(sorted(owner[x] for b in ins(n) for x in [drv.get(b)] if x in owner))
        if dow:
            owner[n] = sorted(dow.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]
            settle()
    # a cone of die inputs only (e.g. por_n && pll_locked) read by several children: it joins its main consumer
    for n in glue:
        if n not in owner:
            cow = collections.Counter(sorted(owner[x] for b in outs(n) for x in cons[b] if x in owner))
            if cow:
                owner[n] = sorted(cow.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]
                settle()
    left = [n for n in glue if n not in owner]
    seq = [n for n in left if re.search(r'dff|dlatch|mem', cells[n]['type'])]
    if seq:
        raise SystemExit(f'sequential glue without a single consumer child: {seq[:10]}')
    # a child replicated as several instances of ONE hardened module (phy_adp x8) is not wrapped: its members stay
    # instances in the parent, and the glue they own stays with them in the parent
    REPL = {c for c, d in part['children'].items() if len(d['members']) > 1 and
            len({cells['u_root.' + '.'.join(p.split('/')[1:])]['type'] for p in d['members']}) == 1 and
            all('g_slice' in p for p in d['members'])}
    # a child marked "direct" in the partition (one member, no glue, one clock) is hardened as that module itself (its
    # kit top is the member, e.g. qkd_host_rx_class_admission): it stays a direct instance in the parent
    DIRECT = {c for c, d in part['children'].items() if d.get('direct')}
    for c in DIRECT:
        if len(part['children'][c]['members']) != 1 or any(o == c for n, o in owner.items() if n in glue):
            raise SystemExit(f'{c}: a direct child must be one member without glue')
    REPL = REPL | DIRECT
    # ---- explicit submod (yosys submod dropped ports of aliased flatten nets): one module per child; a port is every
    # bit a child's cells share with cells outside it or with a die port, grouped by its best net name and direction,
    # so a die vector assembled from several children (service_faults, hc) is a plain output of each driving child
    best = {}
    for nm, n_ in sorted(T['netnames'].items(), key=lambda kv: (kv[1].get('hide_name', 0), kv[0] not in T['ports'],
                                                               kv[0].count('.'), len(kv[0]), kv[0])):
        for i, b in enumerate(n_['bits']):
            if isinstance(b, int) and b not in best:
                best[b] = (nm, i)
    used = collections.defaultdict(set)              # bit -> owning children / 'P' (parent cell or die port)
    for n, c in cells.items():
        if c['type'] == '$scopeinfo':
            continue
        o = owner.get(n) if owner.get(n) not in REPL else None
        for bits in c['connections'].values():
            for b in bits:
                if isinstance(b, int):
                    used[b].add(o or 'P')
    for d in T['ports'].values():
        for b in d['bits']:
            if isinstance(b, int):
                used[b].add('P')
    def sname(nm):
        nm = nm[len('u_root.'):] if nm.startswith('u_root.') else nm
        return re.sub(r'[^A-Za-z0-9_]', '_', nm.replace('.', '__'))
    mods, inst = {}, {}
    children = sorted(set(part['children']) - REPL)
    # KV-CDC2 (coordinator decision A, 10-18): a multi-family child gets one output port per clock family; every bit of
    # it comes from registers of that family, and the receiving domain synchronises it (e.g. the core guard's two-flop
    # fm/fs per raw fault bit) and combines the bits only after that synchronisation
    fam_bit = {T['ports'][FAM_PORT[f]]['bits'][0]: f for f in FAM_PORT}
    fam_bit.update({b: 'phy' for b in T['ports']['ck_phy']['bits']})
    # flat clock nets are aliases of the D3 face bits (an internal clock assign keeps its own bit): resolve each bit
    # through the wrapper's buffers
    memo, split_log = {}, {}       # src_clocks memo (also its per-module driver index under ('index', module))

    def bit_family(b):
        cl = src_clocks(D, 'qkd_hr_cluster_src', b, memo)
        fams = {fam_bit.get(x) for x in cl}
        return fams.pop() if len(fams) == 1 and None not in fams else None
    for ch in children:
        mine = [n for n, o in owner.items() if o == ch]
        bits = sorted({b for n in mine for bb in cells[n]['connections'].values() for b in bb if isinstance(b, int)})
        groups = collections.OrderedDict()
        multi = len({fam_bit[b] for b in bits if b in fam_bit}) > 1
        for b in bits:
            if used[b] - {ch}:
                dname = drv.get(b)
                d = 'output' if dname in mine else 'input'
                nm, i = best[b]
                groups.setdefault((sname(nm), d), []).append((i, b))
        if multi:
            for (nm, d), lst in list(groups.items()):
                if d != 'output':
                    continue
                fl = {b: bit_family(b) for _, b in lst}
                fams = set(fl.values())
                if len(fams) < 2:
                    continue
                if None in fams:
                    raise SystemExit(f'{ch}: output {nm} mixes families {sorted(map(str, fams))} and some bit has no '
                                     'single register family')
                del groups[(nm, d)]
                for f in sorted(fams):
                    groups[(f'{nm}_{f}', d)] = [(i, b) for i, b in lst if fl[b] == f]
                split_log.setdefault(ch, {})[nm] = {f: sum(1 for b in fl.values() if b == f) for f in sorted(fams)}
        ports, conn, pdir, taken = {}, {}, {}, set()
        for (nm, d), lst in groups.items():
            name = nm if nm not in taken else f'{nm}_{d[0]}'
            if name in taken:
                raise SystemExit(f'{ch}: port name collision {name}')
            taken.add(name)
            lst.sort()
            ports[name] = dict(direction=d, bits=[b for _, b in lst])
            conn[name] = [b for _, b in lst]
            pdir[name] = d
        mcells = {n: cells[n] for n in mine}
        nets = {}
        for nm, n_ in T['netnames'].items():
            bb = [b for b in n_['bits'] if isinstance(b, int)]
            if bb and all(b in set(bits) for b in bb) and not nm.startswith('$'):
                nets[nm] = dict(hide_name=n_.get('hide_name', 0), bits=n_['bits'], attributes={})
        for nm, pp in ports.items():
            nets[nm] = dict(hide_name=0, bits=pp['bits'], attributes={})
        mods[ch] = dict(attributes={}, ports=ports, cells=mcells, netnames=nets)
        inst['u_' + ch[len('qkd_hr_'):]] = dict(hide_name=0, type=ch, parameters={}, attributes={},
                                                port_directions=pdir, connections=conn)
    nb = [max(b for c in cells.values() for bb in c['connections'].values() for b in bb if isinstance(b, int)) + 10]
    for mi, mspec in enumerate(a.mutant):
        m = re.fullmatch(r'(u_\w+)\.(\w+)\[(\d+)\]', mspec)
        if not m or m.group(1) not in inst or m.group(2) not in inst[m.group(1)]['connections']:
            raise SystemExit(f'bad --mutant {mspec}')
        c_ = inst[m.group(1)]
        if c_['port_directions'][m.group(2)] != 'input':
            raise SystemExit(f'--mutant {mspec}: not a child input')
        bl = c_['connections'][m.group(2)]
        cells[f'$ot_mutant${mi}'] = dict(hide_name=1, type='$not', parameters=dict(A_SIGNED='0', A_WIDTH='1', Y_WIDTH='1'),
                                         attributes={}, port_directions=dict(A='input', Y='output'),
                                         connections=dict(A=[bl[int(m.group(3))]], Y=[nb[0]]))
        bl[int(m.group(3))] = nb[0]
        nb[0] += 1
    for n in [n for n, o in owner.items() if o in children]:
        del cells[n]
    cells.update(inst)
    for k in [k for k in D['modules'] if k not in ('qkd_hr_cluster_src',)]:
        pass
    D['modules'].update(mods)
    D['modules']['qkd_hr_cluster'] = D['modules'].pop('qkd_hr_cluster_src')
    D['modules']['qkd_hr_cluster']['attributes'] = {}
    # plain identifiers for every generated module's nets (flatten names u_root.u_rank.x -> u_rank__x); a name that a
    # port already uses (the port's own best net) is dropped
    for mn in children + ['qkd_hr_cluster']:
        m = D['modules'][mn]
        out_n = {}
        for nm in list(m['ports']):
            out_n[nm] = m['netnames'].get(nm, dict(hide_name=0, bits=m['ports'][nm]['bits'], attributes={}))
        for nm, n_ in m['netnames'].items():
            if nm in m['ports'] or nm.startswith('$'):
                continue
            sn = sname(nm) if nm.startswith('u_root.') else nm
            if sn not in out_n:
                out_n[sn] = n_
        m['netnames'] = out_n
    json.dump(D, open(work / 'p3in.json', 'w'))
    yosys(a.yosys, '\n'.join([f'read_json {work}/p3in.json', 'hierarchy -top qkd_hr_cluster', 'opt_clean',
                              f'tee -o {work}/check.txt check', f'write_json {work}/p3.json',
                              'select qkd_hr_cluster ' + ' '.join(children),
                              f'write_verilog -noattr -selected {work}/cluster_raw.v']), 'p3', work)
    chk = (work / 'check.txt').read_text()
    if re.search(r'used but has no driver|multiple conflicting drivers|undriven', chk):
        raise SystemExit('generated cluster has undriven/conflicting nets: ' + chk[-2000:])
    # ---- rewrite member instances to their source modules ---------------------------------------------------------------
    pm = paramods(work / 'p2a.log')
    txt = (work / 'cluster_raw.v').read_text()

    def fix(m):
        name = m.group(1)
        base, plist = pm[name]
        pp = ', '.join(f'.{k}({v})' for k, v in plist)
        return f'{base} #({pp}) ' if plist else f'{base} '
    txt = re.sub(r'\\(\$paramod\S+) ', fix, txt)
    # KV-CDC2 (coordinator decision B, 10-18): member instances of a forked module bind the leaf-local CDC fork
    forked = collections.Counter()

    def fork(m):
        forked[m.group(2)] += 1
        return m.group(1) + FORKS[m.group(2)]['fork'] + m.group(3)
    # the instance name may be escaped (`\\u_root.u_rank.u_fence`) when the member has no parameters (KV-CDC3 10-18:
    # the visibility fence stayed unforked because `\w` missed the backslash)
    txt = re.sub(r'(?m)^(\s+)(' + '|'.join(FORKS) + r')(\s+(?:#|\w|\\))', fork, txt)
    if set(forked) != set(FORKS):
        raise SystemExit(f'CDC forks not applied: {sorted(set(FORKS) - set(forked))} (forked {dict(forked)})')
    for pv in a.param:                 # member parameter overrides (opt-in RTL levers whose lock-step gate passed)
        m = re.fullmatch(r'(\w+)\.(\w+)=(-?\d+)', pv)
        n0 = len(re.findall(r'\b' + m.group(1) + r' #\(', txt))
        if not n0:
            raise SystemExit(f'--param {pv}: no instance of {m.group(1)}')
        txt = re.sub(r'\b(' + m.group(1) + r') #\(', lambda x: f'{x.group(1)} #(.{m.group(2)}({m.group(3)}), ', txt)
    txt = apply_wraps(txt, a.wrap)
    # escaped flattened names (\u_root.u_rank.u_phy.tx_d ) -> plain identifiers (u_rank__u_phy__tx_d); collisions refused
    plain = set(re.findall(r'(?<![\\\w$])[A-Za-z_][A-Za-z0-9_$]*', re.sub(r'\\\S+ ', ' ', txt)))
    esc = sorted(set(re.findall(r'\\(u_root\.\S+) ', txt)))
    ren = {}
    for e in esc:
        r = e[len('u_root.'):]
        n = re.sub(r'[^A-Za-z0-9_]', '_', r.replace('.', '__') if '.' in r else 'root__' + r)
        if n in plain or n in ren.values():
            raise SystemExit(f'port/net rename collision {e} -> {n}')
        ren[e] = n
    txt = re.sub(r'\\(u_root\.\S+) ', lambda m: ren[m.group(1)] + ' ', txt)
    if 'qkd_hr_cluster_src' in txt:
        raise SystemExit('unrenamed qkd_hr_cluster_src reference')
    if re.search(r'^\s*inout\b', txt, re.M):
        raise SystemExit('inout port in the generated cluster (multi-driver net across children)')
    if '$paramod' in txt:
        raise SystemExit('unresolved $paramod reference left in the generated cluster')
    hdr = ('// GENERATED by tools/qwen_kv_die/host_cluster/gen_cluster.py from the unchanged flat HOST root sources and\n'
           f'// {Path(a.partition).name}; do not edit. Exact by construction; lock-step bench: host_cluster/bench.\n')
    # one file per generated module: a child's kit binds only its own wrapper (an edit in one child leaves the other
    # kits' source bindings intact); the parent file is the wires-only cluster top
    mods = re.findall(r'(?:/\*.*?\*/\s*)?(module\s+(\w+)\b.*?\nendmodule\n)', txt, re.S)
    for body, name in mods:
        (out / f'{name}.v').write_text(hdr + '`timescale 1ns/1ps\n' + body)
    for f in out.glob('qkd_hr_*.v'):
        if f.stem not in {n for _, n in mods}:
            f.unlink()
    summary = dict(direct_children=sorted(DIRECT), wrapped_children=children, glue_per_child=dict(collections.Counter(o for n, o in owner.items() if n in glue)),
                   glue_cells=len(glue), glue_assigned=sum(1 for n in glue if n in owner),
                   glue_left_in_parent=sorted(left)[:200], glue_left_count=len(left),
                   family_split_outputs=split_log, forked_members=dict(forked))
    json.dump(summary, open(out / 'gen_summary.json', 'w'), indent=1)
    print(json.dumps({k: v for k, v in summary.items() if k != 'children'}, indent=1)[:3000])


if __name__ == '__main__':
    main()
