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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--partition', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--yosys', default=str(Path.home() / '.local/opentallas-tools/yosys-0.68/bin/yosys'))
    ap.add_argument('--work', default=None)
    ap.add_argument('--reuse', action='store_true', help='reuse the work dir yosys passes 1-2')
    a = ap.parse_args()
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
        dow = collections.Counter(owner[x] for b in ins(n) for x in [drv.get(b)] if x in owner)
        if dow:
            owner[n] = dow.most_common(1)[0][0]
            settle()
    # a cone of die inputs only (e.g. por_n && pll_locked) read by several children: it joins its main consumer
    for n in glue:
        if n not in owner:
            cow = collections.Counter(owner[x] for b in outs(n) for x in cons[b] if x in owner)
            if cow:
                owner[n] = cow.most_common(1)[0][0]
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
    for n, c in owner.items():
        if c not in REPL:
            cells[n].setdefault('attributes', {})['submod'] = c
    json.dump(D, open(work / 'p3in.json', 'w'))
    yosys(a.yosys, '\n'.join([f'read_json {work}/p3in.json', 'hierarchy -top qkd_hr_cluster_src', 'submod', 'opt_clean', 'rename qkd_hr_cluster_src qkd_hr_cluster'] +
                             [f'rename qkd_hr_cluster_src_{c} {c}' for c in sorted(set(part['children']) - REPL)] + [
                              f'write_json {work}/p3.json',
                              'select qkd_hr_cluster ' + ' '.join(sorted(set(part['children']) - REPL)),
                              f'write_verilog -noattr -selected {work}/cluster_raw.v']), 'p3', work)

    # ---- rewrite member instances to their source modules ---------------------------------------------------------------
    pm = paramods(work / 'p2a.log')
    txt = (work / 'cluster_raw.v').read_text()

    def fix(m):
        name = m.group(1)
        base, plist = pm[name]
        pp = ', '.join(f'.{k}({v})' for k, v in plist)
        return f'{base} #({pp}) ' if plist else f'{base} '
    txt = re.sub(r'\\(\$paramod\S+) ', fix, txt)
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
    # yosys rename does not retarget the submod cells: child type -> qkd_hr_<child>, instance -> u_<child>
    txt = re.sub(r'\bqkd_hr_cluster_src_(qkd_hr_\w+) qkd_hr_cluster_src_qkd_hr_(\w+) \(', r'\1 u_\2 (', txt)
    if 'qkd_hr_cluster_src' in txt:
        raise SystemExit('unrenamed qkd_hr_cluster_src reference')
    if '$paramod' in txt:
        raise SystemExit('unresolved $paramod reference left in the generated cluster')
    hdr = ('// GENERATED by tools/qwen_kv_die/host_cluster/gen_cluster.py from the unchanged flat HOST root sources and\n'
           f'// {Path(a.partition).name}; do not edit. Exact by construction; lock-step bench: host_cluster/bench.\n')
    (out / 'qkd_hr_cluster.v').write_text(hdr + txt)
    summary = dict(glue_per_child=dict(collections.Counter(o for n, o in owner.items() if n in glue)),
                   glue_cells=len(glue), glue_assigned=sum(1 for n in glue if n in owner),
                   glue_left_in_parent=sorted(left)[:200], glue_left_count=len(left))
    json.dump(summary, open(out / 'gen_summary.json', 'w'), indent=1)
    print(json.dumps({k: v for k, v in summary.items() if k != 'children'}, indent=1)[:3000])


if __name__ == '__main__':
    main()
