#!/usr/bin/env python3
"""ELEM-HBM/SPLIT (2026-10-24): exactness miter of a plan-pin wrapper (+ canonical top) against the master members.

gold = the member cells of design A0 (the re-elaborated bound master) with the plan pins on their master nets (the
       cutmap classes; extra dead bits of the RTL elaboration as free inputs xdead_*), kept member modules flattened;
gate = wrapper + canonical top + recipe RTL, flattened down to the member instances (member-set pieces) or the
       macros (remainder pieces).
Common names: member instances -> m_<role> on both sides; the gate's u_core. / u_core.u_x. prefixes are stripped so the
glue registers carry the flattened master names on both sides.  Remaining instances are everted to ports (expose
-evert), then yosys equiv_make / equiv_simple -seq / equiv_induct -seq / equiv_status -assert.
"""
import collections
import copy
import json
import os
import re
import subprocess

YOSYS = os.path.expanduser('~/.local/opentallas-tools/bin/yosys')


def ys(script, work, name):
    p = os.path.join(work, name + '.ys')
    open(p, 'w').write(script)
    r = subprocess.run([YOSYS, '-q', '-l', os.path.join(work, name + '.log'), '-s', p], capture_output=True,
                       text=True, cwd=work)
    return r.returncode, (r.stdout + r.stderr)[-4000:]


def rename_json(js, top, cellmap, strip):
    mod = js['modules'][top]

    def rn(n):
        if n in cellmap:
            return cellmap[n]
        for s in strip:
            if n.startswith(s):
                return n[len(s):]
        return n
    mod['cells'] = {rn(c): x for c, x in mod['cells'].items()}
    nn = {}
    for n, x in mod['netnames'].items():
        k = rn(n)
        if k in nn:            # keep the first
            continue
        nn[k] = x
    mod['netnames'] = nn


def run(sw, A0, top, module, spec, info, wrapper_txt, work, tag, roles_of):
    wd = os.path.join(work, 'miter', f'{module}{tag}')
    os.makedirs(wd, exist_ok=True)
    P, pbits, dead, order = info['P'], info['pbits'], info['dead'], info['order']
    C, R = info['C'], info['R']
    A0top = A0['modules'][top]
    member_kind = spec['kind'] == 'members'
    # ---------------- gold
    gm = {'attributes': {}, 'ports': {}, 'cells': {}, 'netnames': copy.deepcopy(A0top['netnames'])}
    paths = [p for p, _, _ in P.members]
    cellmap = {}
    if member_kind:
        for (path, ty, c), role in zip(P.members, roles_of(paths)):
            cellmap[c] = f'm_{role}'
    for path, ty, c in P.members:
        gm['cells'][c] = copy.deepcopy(A0top['cells'][c])
    for bus in order:
        gm['ports'][bus] = {'direction': P.dirs[bus], 'bits': list(pbits[bus])}
    for bus, nets in dead.items():
        gm['ports'][f'xdead_{bus}'] = {'direction': 'input', 'bits': list(nets)}
    for pn in gm['ports']:                 # plan bus names may shadow master wires of another width (tile_clk)
        gm['netnames'].pop(pn, None)
    for pn in A0top['ports']:
        if pn in gm['netnames'] and pn not in gm['ports']:
            gm['netnames']['xmaster_' + pn] = gm['netnames'].pop(pn)
    gj = {'creator': 'split/miter.py', 'modules': {k: v for k, v in A0['modules'].items() if k != top}}
    gj['modules']['gold'] = gm
    rename_json(gj, 'gold', cellmap, [])
    json.dump(gj, open(os.path.join(wd, 'gold_in.json'), 'w'))
    mtypes = sorted({ty for _, ty, _ in P.members}) if member_kind else []
    keep = ''.join(f'setattr -mod -set keep_hierarchy 1 {t}\n' for t in mtypes)
    rc, out = ys('read_json gold_in.json\nhierarchy -top gold\nsetattr -mod -unset keep_hierarchy *\n' + keep +
                 'flatten\nopt_clean\nwrite_json gold_flat.json\n', wd, 'gold1')
    if rc:
        return dict(verdict='ERROR', stage='gold', log=out)
    # ---------------- gate
    open(os.path.join(wd, f'{module}__wrap.sv'), 'w').write(wrapper_txt)
    files = list(dict.fromkeys(R['files'] + [C['file']]))
    from split_wrap import read_cmds, REPO
    L = read_cmds(files, [{'file': f'physical/asap7_memory_macros_v2/{m}/{m}_bb.v'} for m in R.get('macros', [])],
                  R.get('defines', []))
    L.append(f'read_verilog -sv -DSYNTHESIS {module}__wrap.sv')
    L += [f'hierarchy -check -top {module}', 'proc']
    if member_kind:
        L += [f'setattr -mod -set keep_hierarchy 1 {t}' for t in mtypes]
    L += ['flatten', 'opt_clean', f'rename -top gate', 'write_json gate_flat.json']
    rc, out = ys('\n'.join(L) + '\n', wd, 'gate1')
    if rc:
        return dict(verdict='ERROR', stage='gate', log=out)
    gt = json.load(open(os.path.join(wd, 'gate_flat.json')))
    if member_kind:
        cm = {f'u_core.{role}': f'm_{role}' for role in roles_of(paths)}
        rename_json(gt, 'gate', cm, ['u_core.'])
    else:
        rename_json(gt, 'gate', {}, ['u_core.u_x.', 'u_core.'])
    json.dump(gt, open(os.path.join(wd, 'gate_in.json'), 'w'))
    # ---------------- evert both, reconcile ports, equivalence
    for side in ('gold', 'gate'):
        src = 'gold_flat.json' if side == 'gold' else 'gate_in.json'
        rc, out = ys(f'read_json {src}\nhierarchy -top {side}\nexpose -evert {side}/c:* {side}/t:$* %d\nhierarchy -top {side}\n'
                     f'opt_clean\nwrite_json {side}_ev.json\n', wd, f'{side}2')
        if rc:
            return dict(verdict='ERROR', stage=f'{side} evert', log=out)
    g = json.load(open(os.path.join(wd, 'gold_ev.json')))
    t = json.load(open(os.path.join(wd, 'gate_ev.json')))
    gp, tp = g['modules']['gold']['ports'], t['modules']['gate']['ports']
    only_g = sorted(set(gp) - set(tp))
    only_t = sorted(set(tp) - set(gp))
    notes = []
    for name in only_g:                    # dead plan bits (xdead_*) and member pins the gate leaves unconnected
        if gp[name]['direction'] != 'input':
            notes.append(f'gold-only output port {name}')
        _addport(t['modules']['gate'], name, gp[name])
    for name in only_t:
        if tp[name]['direction'] != 'input':
            notes.append(f'gate-only output port {name}')
        _addport(g['modules']['gold'], name, tp[name])
    wid = [n for n in set(gp) & set(tp) if len(gp[n]['bits']) != len(tp[n]['bits'])]
    if wid:
        return dict(verdict='FAIL', stage='ports', detail=f'width differs: {wid[:6]}')
    g['modules'] = {'gold': g['modules']['gold']}
    t['modules'] = {'gate': t['modules']['gate']}
    left = [c for m in (g, t) for mm in m['modules'].values() for c, x in mm['cells'].items()
            if not x['type'].startswith('$')]
    if left:
        return dict(verdict='ERROR', stage='evert', detail=f'instances left {left[:5]}')
    json.dump(g, open(os.path.join(wd, 'gold_m.json'), 'w'))
    json.dump(t, open(os.path.join(wd, 'gate_m.json'), 'w'))
    rc, out = ys('read_json gold_m.json\nread_json gate_m.json\n'
                 'async2sync\nequiv_make gold gate eq\nhierarchy -top eq\nequiv_simple -seq 4\nequiv_induct -seq 4\n'
                 'tee -o equiv_status.txt equiv_status\nequiv_status -assert\n', wd, 'equiv')
    st = open(os.path.join(wd, 'equiv_status.txt')).read() if os.path.exists(os.path.join(wd, 'equiv_status.txt')) else ''
    m = re.search(r'Found (\d+) \$equiv cells', st)
    un = re.search(r'Of those cells (\d+) are proven and (\d+) are unproven', st)
    verdict = 'PASS' if rc == 0 and not notes else ('FAIL' if (un and int(un.group(2)) > 0) or notes else 'ERROR')
    res = dict(verdict=verdict, equiv_cells=int(m.group(1)) if m else None,
               unproven=int(un.group(2)) if un else (0 if 'Equivalence successfully proven' in st else None),
               ports=len(gp), gold_only_ports=only_g[:20], gate_only_ports=only_t[:20], notes=notes, dir=wd)
    if rc and not st:
        res['log'] = out
    return res


def _addport(mod, name, like):
    mx = 1 + max([b for p in mod['ports'].values() for b in p['bits'] if isinstance(b, int)] +
                 [b for n in mod['netnames'].values() for b in n['bits'] if isinstance(b, int)] + [1])
    bits = list(range(mx, mx + len(like['bits'])))
    if like['direction'] == 'output':
        bits = ['x'] * len(like['bits'])
    mod['ports'][name] = {'direction': like['direction'], 'bits': bits}
    mod['netnames'][name] = {'hide_name': 0, 'bits': bits, 'attributes': {}}
