#!/usr/bin/env python3
"""TOK-HBM-SUV 2026-10-26: SU Q0 slice vehicle = the B2n plan hard cores of q_su00 + q_su01 (one ot_hbm_su_static_pgslice_lg
#(QID 0, G 0) split into lane / lanes4 / pretree / side cores) composed into the slice glue, with the strap pins tied to the
die_plan.json values.  Bench-only (no stations: the plan's internal stations are cycle-budgeted elsewhere; this checks
function + strap ties).

    su_slice_vehicle.py PARENT.v OUTDIR [--plan physical/die_plan/hbm_arch/B2n/die_plan.json] [--repo R]

PARENT.v = rest_extract.sh output (<name>.parent.v): ot_hbm_su_static_pgslice_lg_s flattened, the 66 member instances
(32 u_lane, 32 u_bank, u_pt, u_sp) kept as cells.  Every hard core of q_su00/q_su01 (except side_rest, whose logic is the
remainder of u_side and stays in the glue) replaces its member cells, wired bit-exactly through the canonical core's role
assigns (build_split_tops.py output; same rule as harden/split_asm.py).  Writes four assemblies (module = suv_asm_<k>,
ports = the master's):
  canon : canonical cores (ot_hbm_su_pg_*_core), lane ids from the master's own constants      -> step 0 vs master
  strap : plan modules: strap masters (*_core_strap) with strap_* pins tied to die_plan values,  -> step 0/1
          other plan modules = their pure-wiring wrappers (physical/die_plan/hbm_arch_cores/wrappers)
  old   : the old constant variants (TR3 variants.json old_module) for every strap master        -> step 1
  mut   : strap with the plan strap values of lane_exp3 and lane_exp5 swapped                    -> must FAIL
and report.json (per core: module, roles, plan straps vs master constants, unmapped/fan-out/const findings)."""
import argparse, importlib.util, json, os, re, sys

ap = argparse.ArgumentParser()
ap.add_argument('parent'); ap.add_argument('out')
ap.add_argument('--plan', default='physical/die_plan/hbm_arch/B2n/die_plan.json')
ap.add_argument('--variants', default='results/type_reduce3_1025/hbm/variants.json')
ap.add_argument('--repo', default='.')
ap.add_argument('--parts', default='q_su00,q_su01')
a = ap.parse_args()
R = a.repo
spec = importlib.util.spec_from_file_location('split_asm', os.path.join(R, 'physical/die_plan/hbm/cores/harden/split_asm.py'))
sa = importlib.util.module_from_spec(spec); spec.loader.exec_module(sa)
CS = 'rtl/hbm_accel/cores_split/ot_hbm_su_static_pgslice_lg/'
WR = 'physical/die_plan/hbm_arch_cores/wrappers/'
CANON = {'full': CS + 'ot_hbm_su_pg_lane_full_core.sv', 'exp': CS + 'ot_hbm_su_pg_lane_exp_core.sv',
         'lanes4': CS + 'ot_hbm_su_pg_lanes4_core.sv', 'pretree': CS + 'ot_hbm_su_pg_pretree_core.sv',
         'softplus': CS + 'ot_hbm_su_side_softplus_core.sv'}
STRAP = {'ot_hbm_su_pg_lane_exp_core_strap': CS + 'ot_hbm_su_pg_lane_exp_core_strap.sv',
         'ot_hbm_su_pg_lanes4_core_strap': CS + 'ot_hbm_su_pg_lanes4_core_strap.sv'}

ptxt = open(a.parent).read()
W = sa.decls(ptxt)
blocks = {b[3]: b for b in sa.inst_blocks(ptxt)}
plan = json.load(open(os.path.join(R, a.plan)))
variants = json.load(open(os.path.join(R, a.variants)))
src_used = {a.plan, a.variants, 'physical/die_plan/hbm/cores/harden/split_asm.py'}


def rd(p):
    src_used.add(p); return open(os.path.join(R, p)).read()


def top_of(txt):
    return re.findall(r'^module\s+(\w+)\s*\(', txt, re.M)[-1]


def wdecls(txt):
    d = {}
    for m in re.finditer(r'\b(?:input|output)\s+wire\s+(?:\[(\d+):(\d+)\]\s*)?(\w+)', txt):
        d[m.group(3)] = (int(m.group(1)), int(m.group(2))) if m.group(1) else None
    for m in re.finditer(r'^\s*wire\s+(?:\[(\d+):(\d+)\]\s*)?(\w+)\s*;', txt, re.M):
        d[m.group(3)] = (int(m.group(1)), int(m.group(2))) if m.group(1) else None
    return d


def nb(e):
    m = re.match(r'^(\S+?)\s*(?:\[(\d+)\])?$', e.strip())
    return (m.group(1), int(m.group(2)) if m.group(2) else 0)


def roles_of(inst):
    m = re.fullmatch(r'u_su_Q0_lane_exp(\d+|_l)', inst)
    if m:
        n = 15 if m.group(1) == '_l' else int(m.group(1))
        return ('full' if n == 0 else 'exp'), {f'\\u_slice.g_lane[{n}].g_pr.u_lane': 'u_lane', f'\\u_slice.g_bank[{n}].u_bank': 'u_bank'}
    m = re.fullmatch(r'u_su_Q0_lanes_plain(\d+)_(\d+)', inst)
    if m:
        b = 16 + int(m.group(1)); r = {}
        for k in range(4):
            r[f'\\u_slice.g_lane[{b + k}].g_pr.u_lane'] = f'u_lane{k}'; r[f'\\u_slice.g_bank[{b + k}].u_bank'] = f'u_bank{k}'
        return 'lanes4', r
    if inst == 'u_su_Q0_pretree':
        return 'pretree', {'\\u_slice.g_pretree.u_pt': 'u_pt'}
    if inst == 'u_su_Q0_side_softplus':
        return 'softplus', {'\\u_slice.g_side_pipe.u_side.u_sp': 'u_sp'}
    return None, None


def canon_map(kind, roles):
    """(canonical port, bit) -> parent bit expression; ports of the canonical core."""
    txt = rd(CANON[kind]); top = top_of(txt); ports = sa.wrapper_ports(txt, top)
    pw = {p[0]: p[2] for p in ports}
    pin = {}
    for path, role in roles.items():
        for pn, ex in blocks[path][4].items():
            pin[(role, pn)] = list(reversed(sa.bits(ex, W)))
    sm = {}
    if kind == 'softplus':                       # hand core: port p = u_sp.p (sp, vo open)
        for nm, d, w in ports:
            for j in range(w):
                sm[(nm, j)] = pin[('u_sp', nm)][j]
        return top, ports, sm
    for m in re.finditer(r'^\s*assign\s+(\S+)\s*=\s*(\S+?);', txt, re.M):
        l, r = m.group(1), m.group(2)
        if '__' in l.split('[')[0] and l.split('__')[0] in roles.values():
            if r.startswith("1'b") or r.startswith('n_int'):
                continue
            role, port = l.split('[')[0].split('__', 1)
            _, li = sa.rng(l, len(pin[(role, port)])); rn, ri = sa.rng(r, pw.get(r))   # unranged role pin = full width
            assert len(li) == len(ri), m.group(0)
            for x, y in zip(li, ri):
                sm[(rn, y)] = pin[(role, port)][x]
        elif '__' in r.split('[')[0] and r.split('__')[0] in roles.values():
            if l.startswith('n_int'):
                continue
            role, port = r.split('[')[0].split('__', 1)
            _, ri = sa.rng(r, len(pin[(role, port)])); ln, li = sa.rng(l, pw.get(l))
            assert len(li) == len(ri), m.group(0)
            for x, y in zip(ri, li):
                sm[(ln, y)] = pin[(role, port)][x]
    return top, ports, sm


def wrap_map(path):
    """pure-wiring wrapper around a canonical core -> ports, {(wport,bit): [(cport,bit)..]} inputs, {(wport,bit): (cport,bit)}
    outputs, {(cport,bit): const} canonical inputs tied inside the wrapper, set of canonical output bits that reach a port."""
    txt = rd(path); top = top_of(txt); ports = sa.wrapper_ports(txt, top); D = wdecls(txt)
    m = re.search(r'^\s*(ot_hbm_su_pg_\w+)\s+u_core\s*\((.*?)\);', txt, re.M | re.S)
    ctop = m.group(1)
    cports = {p[0]: (p[1], p[2]) for p in sa.wrapper_ports(rd(CS + ctop + '.sv'), ctop)}
    w2c_in, c_const, cw2c, w2c_out = {}, {}, {}, {}
    for pm in re.finditer(r'\.(\w+)\s*\(([^()]*)\)', m.group(2)):
        cp, ex = pm.group(1), pm.group(2).strip()
        d, w = cports[cp]
        if not ex:
            continue
        bl = sa.bits(ex, D); assert len(bl) == w, (path, cp, len(bl), w)
        for k, e in enumerate(bl):
            cb = (cp, w - 1 - k)
            if d == 'input':
                if e.startswith("1'b"):
                    c_const[cb] = e
                else:
                    w2c_in.setdefault(nb(e), []).append(cb)
            else:
                cw2c[nb(e)] = cb
    for am in re.finditer(r'^\s*assign\s+(.+?)\s*=\s*(.+?);', txt, re.M):
        lb, rb = sa.bits(am.group(1), D), sa.bits(am.group(2), D)
        assert len(lb) == len(rb), am.group(0)
        for le, re_ in zip(lb, rb):
            if re_.startswith("1'b"):
                w2c_out[nb(le)] = re_
            else:
                w2c_out[nb(le)] = cw2c.get(nb(re_), ('?', re_))
    for nm, d, w in ports:                        # outputs wired straight to the core output port
        if d == 'output':
            for j in range(w):
                if (nm, j) not in w2c_out and (nm, j) in cw2c:
                    w2c_out[(nm, j)] = cw2c[(nm, j)]
    return top, ctop, ports, w2c_in, w2c_out, c_const


def emit(mod, iname, ports, srcmap, notes):
    conns, dang = [], 0
    for nm, d, w in ports:
        bl = []
        for j in range(w - 1, -1, -1):
            e = srcmap.get((nm, j))
            if e is None:
                if d == 'input':
                    notes['unmapped_in'].append(f'{nm}[{j}]'); e = "1'b0"
                else:
                    e = f'asm_nc_{iname}[{dang}]'; dang += 1
            bl.append(e)
        conns.append(f'    .{nm}({{ {", ".join(bl)} }})' if w > 1 else f'    .{nm}({bl[0]})')
    return f'  wire [{max(dang, 1) - 1}:0] asm_nc_{iname};\n  {mod} {iname} (\n' + ',\n'.join(conns) + '\n  );'


def vbits(v):
    m = re.fullmatch(r"(\d+)'b([01]+)", v); return m.group(2)


cores = []
for p in a.parts.split(','):
    for hc in plan['partition_types'][p]['hard_cores']:
        cores.append(dict(part=p, **hc))
rep = dict(parent=os.path.basename(a.parent), cores=[], skipped=[], vehicles={})
cm = {}
for hc in cores:
    kind, roles = roles_of(hc['inst'])
    if kind is None:
        rep['skipped'].append(dict(inst=hc['inst'], module=hc['module'], why='remainder of u_side (stays in the glue; text-verbatim core)'))
        continue
    ctop, cports, csm = canon_map(kind, roles)
    cm[hc['inst']] = (kind, roles, ctop, cports, csm, hc)
used_cells = set(p for v in cm.values() for p in v[1])
member_cells = set(b for b in blocks if re.match(r'\\u_slice\.(g_lane|g_bank|g_pretree|g_side_pipe)', b))
rep['member_cells'] = len(member_cells); rep['replaced_cells'] = len(used_cells)
rep['cells_not_replaced'] = sorted(member_cells - used_cells)

lane_swap = {'u_su_Q0_lane_exp3': 'u_su_Q0_lane_exp5', 'u_su_Q0_lane_exp5': 'u_su_Q0_lane_exp3'}
for veh in ('canon', 'strap', 'old', 'mut'):
    repl, vrep = [], []
    for inst, (kind, roles, ctop, cports, csm, hc) in cm.items():
        notes = dict(inst=inst, plan_module=hc['module'], unmapped_in=[], fanout_diff=[], const_vs_parent=[], open_canon_out=0)
        iname = 'suv_' + inst
        straps = {s['port']: vbits(s['value']) for s in hc.get('straps', [])}
        if veh == 'mut' and inst in lane_swap:
            other = next(h for h in cores if h['inst'] == lane_swap[inst])
            straps = {s['port']: vbits(s['value']) for s in other['straps']}
        if veh == 'canon' or (veh != 'canon' and kind == 'softplus'):
            mod, ports, sm = ctop, cports, csm
            notes['module'] = mod
        else:
            if hc['module'] in STRAP and veh in ('strap', 'mut'):
                wpath = STRAP[hc['module']]
            elif hc['module'] in STRAP:
                vs = [v for v in variants[hc['module']] if {k: vbits(x) for k, x in v['straps'].items()} == straps]
                assert len(vs) == 1, (inst, straps)
                wpath = WR + vs[0]['old_module'] + '.sv'
            else:
                wpath = WR + hc['module'] + '.sv'
            mod, wctop, ports, w2c_in, w2c_out, c_const = wrap_map(wpath)
            assert wctop == ctop, (inst, wctop, ctop)
            notes['module'] = mod; notes['wrapper'] = wpath
            sm = {}
            for (wp, i), tg in w2c_in.items():
                if wp.startswith('strap_'):
                    continue
                sm[(wp, i)] = csm[tg[0]]
                for t in tg[1:]:
                    if csm[t] != csm[tg[0]]:
                        notes['fanout_diff'].append(f'{wp}[{i}]->{t}')
            for sp, val in (straps.items() if wpath in STRAP.values() else ()):   # plan tie at the parent
                w = len(val)
                tg = [w2c_in.get((sp, i), [None])[0] for i in range(w)]
                master = ''.join(csm[t][-1] if t and csm[t].startswith("1'b") else '?' for t in reversed(tg))
                for i in range(w):
                    sm[(sp, i)] = "1'b" + val[w - 1 - i]
                notes.setdefault('straps', {})[sp] = dict(plan=val, master_const=master, equal=(master == val))
            for cb, cval in c_const.items():
                if csm.get(cb) != cval:
                    notes['const_vs_parent'].append(f'{cb[0]}[{cb[1]}] wrapper {cval} parent {csm.get(cb)}')
            reached = set()
            for (wp, i), tg in w2c_out.items():
                if isinstance(tg, tuple) and tg[0] != '?':
                    sm[(wp, i)] = csm[tg]; reached.add(tg)
            notes['open_canon_out'] = sum(1 for nm, d, w in cports if d == 'output' for j in range(w) if (nm, j) not in reached)
        if veh == 'canon' and kind in ('exp', 'full', 'lanes4'):
            for nm, d, w in cports:
                if nm.endswith('lane_id'):
                    mv = ''.join(csm[(nm, j)][-1] for j in range(w - 1, -1, -1))
                    sp = 'strap_' + nm
                    pv = {s['port']: vbits(s['value']) for s in hc.get('straps', [])}.get(sp)
                    notes.setdefault('lane_id', {})[nm] = dict(master_const=mv, plan=pv, equal=(pv is None or pv == mv))
        first = None
        for path in roles:
            b = blocks[path]
            if first is None:
                first = b
            else:
                repl.append((b[0], b[1], f'  // {path}: inside {iname}'))
        repl.append((first[0], first[1], emit(mod, iname, ports, sm, notes)))
        vrep.append(notes)
    out = ptxt
    for s, e, t in sorted(repl, reverse=True):
        out = out[:s] + t + out[e:]
    out = re.sub(r'^module elab_top\(', f'module suv_asm_{veh}(', out, count=1, flags=re.M)
    open(os.path.join(a.out, f'asm_{veh}.v'), 'w').write(f'// GENERATED by tools/hbm_b2/strap_tok/su_slice_vehicle.py ({veh}). Bench only.\n' + out)
    rep['vehicles'][veh] = vrep
bad = []
for veh, vr in rep['vehicles'].items():
    for n in vr:
        if n['unmapped_in'] or n['fanout_diff']:
            bad.append(f"{veh}/{n['inst']}: unmapped_in {len(n['unmapped_in'])} fanout_diff {len(n['fanout_diff'])}")
        if veh in ('strap', 'old') and n['const_vs_parent']:
            bad.append(f"{veh}/{n['inst']}: {len(n['const_vs_parent'])} wrapper constants differ from the master net: {n['const_vs_parent'][:3]}")
        for sp, s in n.get('straps', {}).items():
            if veh != 'mut' and not s['equal']:
                bad.append(f"{veh}/{n['inst']}.{sp}: plan {s['plan']} != master {s['master_const']}")
        for nm, s in n.get('lane_id', {}).items():
            if not s['equal']:
                bad.append(f"{veh}/{n['inst']}.{nm}: plan {s['plan']} != master {s['master_const']}")
rep['compose_errors'] = bad
rep['sources'] = sorted(src_used)
rep['verdict'] = 'PASS' if not bad and not rep['cells_not_replaced'] else 'FAIL'
json.dump(rep, open(os.path.join(a.out, 'report.json'), 'w'), indent=1)
print(json.dumps(dict(verdict=rep['verdict'], cores=len(cm), skipped=[s['inst'] for s in rep['skipped']],
                      replaced=rep['replaced_cells'], members=rep['member_cells'], not_replaced=rep['cells_not_replaced'][:6],
                      errors=bad[:10])))
sys.exit(0 if rep['verdict'] == 'PASS' else 1)
