#!/usr/bin/env python3
"""ELEM-HBM/SPLIT2 (2026-10-24): plan-pin wrappers for the HBM B2l split-piece hard cores + their exactness miters.

    python3 sw2.py --family tkm [--views M1,M2] [--mutant M1,..|all] [--no-miter] [--work DIR]

The B2l core pins of a split piece are the HBM-P5 netcut boundary of the as-built master (physical/die_plan/hbm/cores/
ports/ports_cut.json = the d4g pins_plan names): one bus per (label, dir); label = the master top port the net reaches,
else the first member hierarchical pin on the net, else '~' + the first outside hierarchical pin, else 'glue'.
netcut kept bit COUNTS only, so the bit order inside a plan bus is fixed here (and recorded per module in
results/split_wrappers_b2l/<module>.map.json for the integrator):

    plan bus L, bit i = the i-th boundary net of L in ascending bit index ON THE LABELLING PIN
                        (master port bit for a port label, member / outside pin bit for a pin label)

Per family (one master; the as-built netlists are gone, so the bound master twin is re-elaborated from RTL):
  1. yosys: master twin (bind/asbuilt.json alias, die-netlist parameters) -> hier.json; A0 = flatten only the module
     types on the include / exclude path prefixes (netcut expands exactly those), every other instance kept;
  2. per plan module: cutmap.analyse(A0) re-derives the netcut boundary; every bus width must equal the B2l pins file
     of EVERY pins table of the module (port sets of the tables are compared: PORTSET_MISMATCH is reported);
  3. canonical port bit -> master net: member-set tops through the member instance pins (roles = split_conn.roles_of,
     member module types + parameter values compared); remainder tops (rest_extract + rest_wrap) through the extracted
     port names (= flattened master net names of A1 = the master flattened as rest_extract flattens it);
  4. wrapper wrappers/<module>.sv: exactly the plan pins, canonical top u_core, every canonical input bit = the plan
     pin bit on its master net or the master constant on it, canonical outputs the plan does not pin stay open;
  5. miter (yosys): gold = the master's piece (A0 member cells, or A1 minus the excluded cells) with the plan pins on
     their master nets; gate = wrapper + canonical top + recipe RTL; instances left (members, macros, kept modules) are
     everted to ports under common names; equiv_make / equiv_simple -seq / equiv_induct -seq / equiv_status -assert.
     Mutant control (--mutant): swap two plan bits feeding the canonical core (or two plan output bits); the miter must
     then FAIL.
"""
import argparse
import collections
import copy
import hashlib
import json
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import cutmap                                                       # noqa: E402

REPO = cutmap.REPO
HAC = os.path.dirname(HERE)
HARDEN = os.path.join(REPO, 'physical', 'die_plan', 'hbm', 'cores', 'harden')
PLAN_DIR = os.path.join(REPO, 'physical', 'die_plan', 'hbm_arch', 'B2l')
VIEWS = os.path.join(HAC, 'views_b2l.json')
YOSYS = os.path.expanduser('~/.local/opentallas-tools/bin/yosys')
WORK0 = '/srv/opentallas-scratch/claude/elem-hbm/split2/work'
CONST = cutmap.CONST


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
# include / exclude paths are TWIN hdl paths ('/'-joined instance names, generate scopes inside a name with '.');
# ren maps a twin path label to the as-built label text (the scoped d4g masters wrap the RTL module once more).
PG_PARAMS = dict(READ_RETURN=22, WRITE_RETURN=19, FETCH_EXTRA_EDGES=2, MLAT=4, ALAT=3, LEAF=1, MUT=0, MULTIRATE=1,
                 COLLPORT=1, RF_LOCAL=1, PRETREE=1)


# the plan variant PIN_REG 1 instantiates the lanes in g_pr (as-built r18h5 PIN_REG 0: g_plain, same lane ports)
PG_REN = [(r'^u_slice/', 'u/u_slice/'), (r'\.g_pr\.u_lane', '.g_plain.u_lane')]


def tkm_views():
    tiles = [f'u/g_tiles[{k}].e86.u_tile' for k in range(32)]
    v = {f'ot_hgi_coll_tkm_m_tp192__tile{k}': dict(include=[tiles[k]], exclude=[], kind='members') for k in range(32)}
    v['ot_hgi_coll_tkm_m_tp192__root'] = dict(include=[''], exclude=tiles, kind='rest')
    return v


def pg_lanes(ks):
    return [f'u_slice/g_lane[{k}].g_pr.u_lane' for k in ks] + [f'u_slice/g_bank[{k}].u_bank' for k in ks]


def pg0_views():
    m = 'ot_hbm_su_static_pgslice_lg__'
    v = {f'{m}lane_exp{k}': dict(include=pg_lanes([k]), exclude=[], kind='members') for k in range(15)}
    v[f'{m}lane_exp_l'] = dict(include=pg_lanes([15]), exclude=[], kind='members')
    for j in range(4):
        v[f'{m}lanes_plain{4 * j}_{4 * j + 3}'] = dict(include=pg_lanes(range(16 + 4 * j, 20 + 4 * j)), exclude=[],
                                                       kind='members')
    v[f'{m}pretree@pv0'] = dict(include=['u_slice/g_pretree.u_pt'], exclude=[], kind='members')
    return v


def pg8_views():
    m = 'ot_hbm_su_static_pgslice_lg__'
    v = {f'{m}lanes{4 * j}_{4 * j + 3}': dict(include=pg_lanes(range(4 * j, 4 * j + 4)), exclude=[], kind='members')
         for j in range(8)}
    v[f'{m}pretree'] = dict(include=['u_slice/g_pretree.u_pt'], exclude=[], kind='members')
    return v


def bankq_views():
    m = 'ot_hbm_hc_bankq_ft_static__'
    lg = lambda ks: [f'u_c/u_b/u_st/g_lg.g_grp[{k}].u_lg' for k in ks]
    return {f'{m}lanes0_2': dict(include=lg([0, 1, 2]), exclude=[], kind='members'),
            f'{m}lanes3_5': dict(include=lg([3, 4, 5]), exclude=[], kind='members')}


def coll_views():
    m = 'ot_hfd_coll_q2_hard_v8g__'
    return {f'{m}reduce': dict(include=['u_body/u_reduce'], exclude=[], kind='members'),
            f'{m}ring_ag': dict(include=['u_body/u_ring'], exclude=[], kind='members'),
            f'{m}body': dict(include=[''], exclude=['u_body/u_reduce', 'u_body/u_ring'], kind='rest')}


def sfu_views():
    m = 'ot_hgi_sfu_core_split3__'
    g = 'u_core/u_engine/u_arithmetic/u_grid'
    lanes = [f'{g}/g_lane[{k}].u_sfu' for k in range(16)] + [f'{g}/g_lane[{k}].g_mono.u_map' for k in range(16)]
    mem = 'u_core/u_engine/u_memory'
    return {f'{m}ctl': dict(include=[''], exclude=lanes + [mem], kind='rest'),
            f'{m}opstore_a': dict(include=[mem], exclude=[f'{mem}/g_operand[2].u_group', f'{mem}/g_operand[3].u_group',
                                                          f'{mem}/u_output'], kind='rest')}


def hcroot_views():
    m = 'ot_hbm_hc_root_static__'
    sk = dict(sk_clk='clk', sk_in_valid='in_valid', sk_in_e='in_e', sk_in_ready='in_ready', sk_out_valid='out_valid',
              sk_fault='fault', sk_y='y')
    return {f'{m}tail{k}_rest': dict(include=[f'g_tail[{k}].u_t'], exclude=[f'g_tail[{k}].u_t/u_tail/sink'],
                                     kind='manual', inst=f'g_tail[{k}].u_t', sink=f'g_tail[{k}].u_t.u_tail.sink',
                                     sink_pins=sk) for k in range(2)}


FAMILIES = {
    'tkm': dict(twin='ot_hgi_coll_tkm_m_tp192_p', params={}, defines=[], ren=[(r'^u/', 'u/u/')], views=tkm_views),
    'pg0': dict(twin='ot_hbm_su_static_pgslice_lg_s', params=dict(QID=0, G=0, **PG_PARAMS), defines=[],
                ren=PG_REN, views=pg0_views, merge_ff_bits=True),
    # pv8 = 'plain slice: 32 plain lanes' (over_cap_split pv8.split.json; canonical lanes4 = KIND 0 lanes): lid >= 32 for
    # every lane needs G >= 2.  B2l instantiates these pieces in q_su20/21 (master pv10) and q_su30/31 (pv14).
    # QID / G reach the lane / bank members only through KIND, so QID 2 G 2 stands for all of them.
    'pg8': dict(twin='ot_hbm_su_static_pgslice_lg_s', params=dict(QID=2, G=2, **PG_PARAMS), defines=[],
                ren=PG_REN, views=pg8_views, merge_ff_bits=True),
    'bankq': dict(twin='ot_hbm_hc_bankq_ft_static', params={}, defines=[], ren=[], views=bankq_views, merge_ff_bits=True),
    'coll': dict(twin='ot_hfd_coll_q2_hard_v8g_s', params=dict(NLINK=1, TP=192, AR_ITER=1, ROWS=256, VM_RT=81),
                 defines=['OT_COLL_ISSUER256_NATIVE32'], ren=[], views=coll_views,
                 extra_files=['rtl/hbm_accel/generic/collective/p2p/ot_hgi_coll_issuer_m256v8.sv'],
                 extra_macros=['ot_sram_1r1w_256x256_m2_r2c2', 'ot_sram_1r1w_64x512_m1_r2c2', 'ot_sram_1rw_256x64_m4_r2c2']),
    # coll body: the canonical body core (rest_extract header) AND the B2l plan pins (u_body_..._a_u_control_...) were
    # both cut from the VM_RT=0 master (generate branch a_u_control); the die netlist binds VM_RT=81 (a_u_control_r).
    'coll0': dict(twin='ot_hfd_coll_q2_hard_v8g_s', params=dict(NLINK=1, TP=192, AR_ITER=1, ROWS=256, VM_RT=0),
                  defines=['OT_COLL_ISSUER256_NATIVE32'], ren=[],
                  views=lambda: {k: v for k, v in coll_views().items() if k.endswith('__body')},
                  extra_files=['rtl/hbm_accel/generic/collective/p2p/ot_hgi_coll_issuer_m256v8.sv'],
                  extra_macros=['ot_sram_1r1w_256x256_m2_r2c2', 'ot_sram_1r1w_64x512_m1_r2c2',
                                'ot_sram_1rw_256x64_m4_r2c2']),
    # canonical ctl / opstore_a cores (rest_extract headers): master ot_hgi_sfu_core_split3 LWB 15 LG_PATH 31 (TAP defaults)
    # master_filelist resolves the ambiguous v41x lane/sfu modules to the non-c12 files; the sfu lanes are the c12 ones
    # (split_files/sfu_lane.files).  The lanes are excluded members of both pieces: only their port lists matter here.
    'sfu': dict(twin='ot_hgi_sfu_core_split3', params=dict(LWB=15, LG_PATH=31), defines=[],
                file_prefer='physical/die_plan/hbm/cores/harden/split_files/sfu_lane.files', a0_per_view=True,
                ren=[], views=sfu_views),
    'hcroot': dict(twin='ot_hbm_hc_root_static_s', params=dict(QDRLY=2, QCHX=11), defines=[], ren=[],
                   views=hcroot_views, a0_per_view=True, merge_ff_bits=True),
}


# ---------------------------------------------------------------------------------------------------- helpers
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


def path_types(hj, top, paths):
    """module types of every proper path prefix instance (the levels netcut expands)."""
    out = set()
    for p in paths:
        if not p:
            continue
        mod = top
        lv = p.split('/')
        for k in range(len(lv) - 1):
            cells = hj['modules'][mod]['cells']
            if lv[k] not in cells:
                raise SystemExit(f'path {p}: no instance {lv[k]} in {mod}')
            mod = cells[lv[k]]['type']
            out.add(mod)
    return out


def retype_off_path(hj, top, flat, paths):
    """netcut expands INSTANCES; type-based flatten would also open same-type instances off the include/exclude
    paths (e.g. hc g_tail[1].u_t when cutting g_tail[0].u_t).  Re-type those to a kept clone."""
    pref = set()
    for p in paths:
        lv = p.split('/') if p else []
        for k in range(1, len(lv)):
            pref.add('/'.join(lv[:k]))
    n = [0]

    def walk(mod, path):
        for cn, c in hj['modules'][mod]['cells'].items():
            if c['type'] not in flat:
                continue
            cp = f'{path}/{cn}' if path else cn
            if cp in pref:
                walk(c['type'], cp)
            else:
                cl = c['type'] + '$offpath'
                if cl not in hj['modules']:
                    hj['modules'][cl] = json.loads(json.dumps(hj['modules'][c['type']]))
                    hj['modules'][cl].setdefault('attributes', {}).pop('top', None)
                c['type'] = cl
                n[0] += 1
    walk(top, '')
    return n[0]


def elab_master(F, fam, specs, work, tag=''):
    """hier.json (hierarchy kept) and A0.json (flatten the path-prefix module types only)."""
    os.makedirs(work, exist_ok=True)
    hjp = os.path.join(work, 'hier.json')
    if not os.path.exists(hjp):
        fl = master_files(F['twin'])
        for x, y in F.get('file_subst', []):
            fl['files'] = [y if f == x else f for f in fl['files']]
        if F.get('file_prefer'):
            # files whose modules override same-named modules of master_filelist's (ambiguous) picks
            pref = [l.strip() for l in open(os.path.join(REPO, F['file_prefer'])) if l.strip() and
                    not l.startswith('macro:') and '/hdc/' in l]   # the ambiguous hdc library only
            modsof = lambda f: set(re.findall(r'^\s*module\s+(\w+)', open(os.path.join(REPO, f)).read(), re.M))
            pm = set().union(*(modsof(f) for f in pref))
            fl['files'] = [f for f in fl['files'] if not (modsof(f) & pm)] + pref
        fl['files'] += [f for f in F.get('extra_files', []) if f not in fl['files']]
        have = {m['module'] for m in fl.get('macros', [])}
        fl.setdefault('macros', []).extend({'module': m, 'file': f'physical/asap7_memory_macros_v2/{m}/{m}_bb.v'}
                                           for m in F.get('extra_macros', []) if m not in have)
        json.dump(fl, open(os.path.join(work, 'master_files.json'), 'w'), indent=1)
        L = read_cmds(fl['files'], fl.get('macros', []), F['defines'])
        for k, v in F['params'].items():
            L.append(f'chparam -set {k} {v} {F["twin"]}')
        L += [f'hierarchy -check -top {F["twin"]}', 'proc', 'opt_clean', 'write_json hier.json']
        rc, out = yosys('\n'.join(L) + '\n', os.path.join(work, 'hier.ys'), os.path.join(work, 'hier.log'))
        if rc:
            raise SystemExit(f'master elaboration failed: {out[-3000:]}')
    a0p = os.path.join(work, f'A0{tag}.json')
    hj = None
    if not os.path.exists(a0p):
        hj = json.load(open(hjp))
        top = F['twin'] if F['twin'] in hj['modules'] else next(m for m in hj['modules']
                                                                 if hj['modules'][m]['attributes'].get('top'))
        flat = set()
        for s in specs.values():
            flat |= path_types(hj, top, s['include'] + s['exclude'])
        src = 'hier.json'
        if tag:
            allp = [p for sp in specs.values() for p in sp['include'] + sp['exclude']]
            retype_off_path(hj, top, flat, allp)
            src = f'hier{tag}.json'
            json.dump(hj, open(os.path.join(work, src), 'w'))
        L = [f'read_json {src}', f'hierarchy -top {top}', 'setattr -mod -set keep_hierarchy 1 *']
        L += [f'setattr -mod -unset keep_hierarchy {yname(m)}' for m in sorted(flat)]
        L += ['flatten', 'opt_clean', f'write_json A0{tag}.json']
        rc, out = yosys('\n'.join(L) + '\n', os.path.join(work, f'a0{tag}.ys'), os.path.join(work, f'a0{tag}.log'))
        if rc:
            raise SystemExit(f'A0 failed: {out[-3000:]}')
    return json.load(open(a0p))


FF_TYPES = {'$dff', '$adff', '$sdff', '$dffe', '$adffe', '$sdffe', '$sdffce', '$dffsr', '$dffsre', '$aldff', '$aldffe'}
PERBIT = {'ARST_VALUE', 'SRST_VALUE', 'AD'}


def merge_ff_bits(js, top, region=None):
    """as-built synthesis merges identical flop BITS and identical combinational cells (opt_merge) (same type, clock / reset / enable nets, same D net, same reset
    value): RTL `reg [W-1:0] r; always r[l] <= x;` is one as-built flop.  Merge them the same way (sound: equal next
    state and reset value; the duplicate's readers move to the representative).  Iterated to a fixed point.
    Returns the number of merged bits."""
    mod = js['modules'][top]
    total = 0
    nxt = [1 + max([b for c in mod['cells'].values() for bl in c['connections'].values() for b in bl
                    if isinstance(b, int)] + [b for n in mod['netnames'].values() for b in n['bits'] if isinstance(b, int)])]
    dangling = set()
    while True:
        rep, seen = {}, {}
        for cn in sorted(mod['cells']):
            c = mod['cells'][cn]
            if c['type'] not in FF_TYPES:
                continue
            q = c['connections'].get('Q', [])
            d = c['connections'].get('D', [])
            ctl = tuple((pn, tuple(bl)) for pn, bl in sorted(c['connections'].items()) if pn not in ('Q', 'D', 'AD'))
            prm = tuple((k, v) for k, v in sorted(c.get('parameters', {}).items()) if k not in PERBIT and k != 'WIDTH')
            for i, qb in enumerate(q):
                if not isinstance(qb, int) or i >= len(d) or qb in dangling:
                    continue
                pb = tuple((k, str(c['parameters'][k])[::-1][i] if k in c.get('parameters', {}) and
                            len(str(c['parameters'][k])) == len(q) else '') for k in sorted(PERBIT))
                key = (c['type'], prm, ctl, d[i], pb, region(cn, c) if region else None)
                if key in seen:
                    rep[qb] = seen[key]
                else:
                    seen[key] = qb
        # identical combinational internal cells (same type, parameters, input nets): as-built opt_merge
        cseen, dupcells = {}, set()
        for cn in sorted(mod['cells']):
            c = mod['cells'][cn]
            if not c['type'].startswith('$') or c['type'] in FF_TYPES or 'mem' in c['type'] or \
                    not c.get('port_directions'):
                continue
            pd = c['port_directions']
            outs = [pn for pn in sorted(c['connections']) if pd.get(pn) == 'output']
            if not outs or any(b in dangling for pn in outs for b in c['connections'][pn]):
                continue
            ins = tuple((pn, tuple(c['connections'][pn])) for pn in sorted(c['connections']) if pd.get(pn) != 'output')
            key = (c['type'], tuple(sorted((k, str(v)) for k, v in c.get('parameters', {}).items())), ins,
                   region(cn, c) if region else None)
            if key in cseen:
                r = mod['cells'][cseen[key]]
                for pn in outs:
                    for b, rb in zip(c['connections'][pn], r['connections'][pn]):
                        if isinstance(b, int) and b != rb and b not in rep:
                            rep[b] = rb
                dupcells.add(cn)
            else:
                cseen[key] = cn
        if not rep:
            return total
        total += len(rep)
        for cn, c in mod['cells'].items():
            for pn, bl in c['connections'].items():
                if (c['type'] in FF_TYPES and pn == 'Q') or \
                        (cn in dupcells and c.get('port_directions', {}).get(pn) == 'output'):
                    nb = []
                    for b in bl:
                        if b in rep:
                            nb.append(nxt[0]); dangling.add(nxt[0]); nxt[0] += 1
                        else:
                            nb.append(b)
                    c['connections'][pn] = nb
                else:
                    c['connections'][pn] = [rep.get(b, b) for b in bl]
        for p in mod['ports'].values():
            p['bits'] = [rep.get(b, b) for b in p['bits']]
        for n in mod['netnames'].values():
            n['bits'] = [rep.get(b, b) for b in n['bits']]


def yname(m):
    """module name as a yosys selection argument."""
    return m.replace('\\', '\\\\').replace('$', '\\$') if ('$' in m or '\\' in m) else m


def ren_fn(F):
    def ren(s):
        for a, b in F['ren']:
            s = re.sub(a, b, s)
        return s
    return ren


def plan_tables(module):
    """all B2l pins tables of the plan module -> (views, buses {name: width} of the first, mismatch list)."""
    V = json.load(open(VIEWS))
    vs = [v for v in V['view_list'] if v['module'] == module]
    if not vs:
        raise SystemExit(f'{module}: no B2l view')
    tabs = []
    for v in vs:
        pf = os.path.join(PLAN_DIR, v['pins_file'])
        if hashlib.sha256(open(pf, 'rb').read()).hexdigest() != v['pins_sha256']:
            raise SystemExit(f'{v["view"]}: pins file changed since the inventory')
        pins = json.load(open(pf))
        tabs.append((v, pins, collections.Counter(re.sub(r'\[\d+\]$', '', p['name']) for p in pins)))
    mism = []
    for v, _, c in tabs[1:]:
        if c != tabs[0][2]:
            mism.append(dict(view=v['view'], vs=tabs[0][0]['view'],
                             diff=sorted(set(c.items()) ^ set(tabs[0][2].items()))[:20]))
    return tabs, mism


def canon_info(module, v):
    C = json.load(open(os.path.join(HARDEN, 'canonical_ports_split.json')))['types'][v['canonical_type']]
    tid = next(t for t in C['type_ids'] if re.sub(r'__[\d.]+x[\d.]+$', '', t) == module)
    R = json.load(open(os.path.join(HARDEN, 'recipes_split.json')))[tid]
    return C, C['type_ids'][tid], R


def macro_bbs(R):
    return [{'file': f'physical/asap7_memory_macros_v2/{m}/{m}_bb.v'} for m in R.get('macros', [])]


def canon_json(C, R, work):
    """canonical top elaborated hierarchically (yosys JSON)."""
    out = os.path.join(work, f'canon_{C["top"]}.json')
    if os.path.exists(out):
        return json.load(open(out))
    files = list(dict.fromkeys(R['files'] + ([C['file']] if C.get('file') else [])))
    L = read_cmds(files, macro_bbs(R), R.get('defines', []))
    L += [f'hierarchy -check -top {C["top"]}', 'proc', 'opt_clean', f'write_json {out}']
    rc, o = yosys('\n'.join(L) + '\n', out + '.ys', out + '.log')
    if rc:
        raise SystemExit(f'canonical elaboration failed: {o[-3000:]}')
    return json.load(open(out))


def module_params(js, mname):
    m = js['modules'].get(mname, {})
    return {k: v for k, v in (m.get('parameter_default_values') or {}).items()}


def base_type(t):
    return re.sub(r'^\$paramod\$[0-9a-f]+\\', '', re.sub(r'^\$paramod\\([^\\]+)\\.*$', r'\1', t))


# ---------------------------------------------------------------------------------------------------- gate side
def gate_members(cj, top, P, A0):
    """member-set canonical: canonical port bit -> [(A0 member path, port, idx, dir)]; member types + params checked."""
    mod = cj['modules'][top]
    paths = [p for p, _, _ in P.members]
    roles = dict(zip(roles_of(paths), P.members))
    bitpins = collections.defaultdict(list)
    checks = []
    cells = {c: x for c, x in mod['cells'].items() if x['type'] != '$scopeinfo'}
    for c, x in cells.items():
        if c not in roles:
            raise SystemExit(f'canonical cell {c} has no master member (roles {sorted(roles)})')
        path, ty, _ = roles[c]
        if base_type(x['type']) != base_type(ty):
            raise SystemExit(f'member type differs: canonical {c} = {x["type"]}, master {path} = {ty}')
        pc, pm = module_params(cj, x['type']), module_params(A0, ty)
        diff = sorted(k for k in set(pc) | set(pm) if str(pc.get(k)) != str(pm.get(k)))
        if diff:
            raise SystemExit(f'member parameters differ {c}: {[(k, pc.get(k), pm.get(k)) for k in diff][:6]}')
        checks.append(f'{c}={base_type(ty)} params {len(pc)} equal')
        for pn, bl in x['connections'].items():
            for i, b in enumerate(bl):
                bitpins[b].append((path, pn, i, x['port_directions'][pn]))
    if len(roles) != len(cells):
        raise SystemExit(f'canonical has {len(cells)} members, master {len(roles)}')
    out = {}
    for pn, p in mod['ports'].items():
        out[pn] = (p['direction'], [bitpins.get(b, []) if b not in CONST else b for b in p['bits']])
    return out, checks


def member_pin_net(Atop, scopes):
    m = {}
    for c, x in Atop['cells'].items():
        if x['type'] == '$scopeinfo':
            continue
        p = cutmap.cell_path(c, x, scopes)
        for pn, bl in x['connections'].items():
            for i, b in enumerate(bl):
                m[(p, pn, i)] = b
    return m



# ---------------------------------------------------------------------------------------------------- rest kind
sys.path.insert(0, HARDEN)


def kept_types_of(C):
    """module types the remainder core (rest_extract _x module) keeps as instances (macros, kept leaves)."""
    txt = open(os.path.join(REPO, C['file'])).read()
    m = re.search(r'(?ms)^module\s+\\?' + re.escape(C['top'] + '_x') + r'\b.*?^endmodule', txt)
    kw = {'input', 'output', 'inout', 'wire', 'reg', 'assign', 'always', 'if', 'else', 'end', 'begin', 'case',
          'endcase', 'module', 'endmodule', 'initial', 'integer', 'genvar', 'generate', 'endgenerate', 'for',
          'localparam', 'parameter', 'signed', 'default'}
    out = set()
    for mm in re.finditer(r'^\s+([A-Za-z_][\w$]*)\s+(?:#\(.*?\)\s*)?(\\\S+|[A-Za-z_][\w$]*)\s*\(', m.group(0), re.M | re.S):
        if mm.group(1) not in kw:
            out.add(mm.group(1))
    return out


def a1_design(F, A0, spec, keep_types, work):
    """A1 = the master flattened as rest_extract flattens it: every instance flattened except the excluded members'
    module types and the kept types (macros / kept leaves of the remainder core)."""
    top = F['twin']
    Atop = A0['modules'][top]
    scopes = cutmap.scopes_of(Atop)
    ex_types = set()
    for c, x in Atop['cells'].items():
        if x['type'] == '$scopeinfo':
            continue
        if cutmap.under(cutmap.cell_path(c, x, scopes), spec['exclude']):
            ex_types.add(x['type'])
    hj = json.load(open(os.path.join(work, 'hier.json')))
    keep = set(ex_types)
    for m in hj['modules']:
        if base_type(m) in keep_types or m in keep_types:
            keep.add(m)
    tag = hashlib.sha1(json.dumps(sorted(keep)).encode()).hexdigest()[:10]
    tag = 'm' + tag[1:]                          # A1 format rev (memory -nomap)
    p = os.path.join(work, f'A1_{tag}.json')
    if not os.path.exists(p):
        L = ['read_json hier.json', f'hierarchy -top {top}', 'setattr -mod -unset keep_hierarchy *']
        L += [f'setattr -mod -set keep_hierarchy 1 {yname(m)}' for m in sorted(keep)]
        # memory -nomap: $memrd/$memwr -> self-contained $mem_v2 (gold is a cell subset; MEMID memories would dangle)
        L += ['flatten', 'memory -nomap', 'opt_clean', f'write_json A1_{tag}.json']
        rc, out = yosys('\n'.join(L) + '\n', os.path.join(work, f'a1_{tag}.ys'), os.path.join(work, f'a1_{tag}.log'))
        if rc:
            raise SystemExit(f'A1 failed: {out[-3000:]}')
    js = json.load(open(p))
    if F.get('merge_ff_bits'):
        # never merge a piece cell with an outside one (the gold is the piece's own cells)
        sc1 = cutmap.scopes_of(js['modules'][top])
        inc = spec['include']
        def region(cn, c):
            pth = cutmap.cell_path(cn, c, sc1)
            return (('' in inc) or cutmap.under(pth, inc)) and not cutmap.under(pth, spec['exclude'])
        merge_ff_bits(js, top, region)
    return js, sorted(keep), tag


def resolve_name(Atop, nm):
    """'name' / 'name[i]' (public netname, i in declared index space) -> bit of Atop, or KeyError."""
    nn, pt = Atop['netnames'], Atop['ports']
    if nm in nn and len(nn[nm]['bits']) == 1:
        return nn[nm]['bits'][0]
    mm = re.fullmatch(r'(.*)\[(-?\d+)\]', nm)
    if mm:
        base, k = mm.group(1), int(mm.group(2))
        w = nn.get(base)
        if w is not None:
            off = w.get('offset', 0)
            idx = (k - off) if not w.get('upto', 0) else (len(w['bits']) - 1 - (k - off))
            if 0 <= idx < len(w['bits']):
                return w['bits'][idx]
    raise KeyError(nm)


def anchor_names(A0top, b):
    """every public netname bit of A0 net b ('name' or 'name[i]'), shortest first."""
    out = []
    for n, x in A0top['netnames'].items():
        if x.get('hide_name', 0):
            continue
        for i, bb in enumerate(x['bits']):
            if bb == b:
                k = i + x.get('offset', 0) if not x.get('upto', 0) else (len(x['bits']) - 1 - i + x.get('offset', 0))
                out.append(n if len(x['bits']) == 1 else f'{n}[{k}]')
    return sorted(out, key=len)


def rest_canon_bits(C, A1top, report):
    """canonical port -> (dir, [A1 net | const | None]) through the rest_wrap wrapper and the _x port names."""
    import split_wrap
    canon, miss, xw = split_wrap.rest_wrapper_ports(C)
    if miss:
        report['canonical_bits_not_to_core'] = [f'{n}[{i}]' for n, i in miss][:20]
    out = {}
    for pn, (d, bl) in canon.items():
        nets = []
        for xb in bl:
            if xb is None:
                nets.append(None)
                continue
            xn, xi = xb
            try:
                nets.append(split_wrap.xname_net(A1top, xn, xi, xw))
            except KeyError:
                try:
                    nets.append(resolve_name(A1top, xn if xw[xn][1] == 1 else f'{xn}[{xi}]'))
                except KeyError:
                    raise SystemExit(f'canonical {pn}: extracted port {xn} not a net of the master (A1)')
        out[pn] = (d, nets)
    return out


# ---------------------------------------------------------------------------------------------------- build
def build_view(F, A0, module, spec, work, report, mutant=False):
    tabs, mism = plan_tables(module)
    if mism:
        report['portset_mismatch'] = mism
        raise SystemExit(f'{module}: PORTSET_MISMATCH between pins tables {[m["view"] for m in mism]}')
    v, pins, planw = tabs[0]
    report['views'] = [t[0]['view'] for t in tabs]
    C, TI, R = canon_info(module, v)
    top = F['twin']
    Atop = A0['modules'][top]
    scopes = cutmap.scopes_of(Atop)
    order = list(dict.fromkeys(re.sub(r'\[\d+\]$', '', p['name']) for p in pins))
    scal = {b: not any(p['name'].startswith(b + '[') for p in pins) for b in order}
    P = None
    tried = []
    groot = glue_root_fn(Atop, spec)
    strips = [''] + sorted({spec['include'][0].rsplit('/', 1)[0] + '/' if '/' in spec['include'][0] else ''} |
                           {'/'.join(F_ren(F, spec['include'][0]).split('/')[:k]) + '/'
                            for k in range(1, len(F_ren(F, spec['include'][0]).split('/')))} |
                           ({F_ren(F, spec['include'][0]) + '/'} if spec['include'][0] else set()))
    for st in dict.fromkeys(strips):
        P_ = cutmap.analyse(A0, top, spec['include'], spec['exclude'], ren_fn(F), st, glue_root=groot)
        bad = cutmap.check_plan(P_, pins)
        tried.append((st, len(bad), bad[:4]))
        if not bad:
            P = P_; report['strip'] = st
            break
    if P is None:
        best = min(tried, key=lambda t: t[1])
        report['derive'] = [dict(strip=t[0], mismatches=t[1], e_g=[list(map(str, x)) for x in t[2]]) for t in tried]
        P = cutmap.analyse(A0, top, spec['include'], spec['exclude'], ren_fn(F), best[0], glue_root=groot)
        report['strip'] = best[0]
    pm = member_pin_net(Atop, scopes)
    cbit = {}                                  # canonical port -> (dir, [A0 net or const or None])
    info_extra = {}
    if spec['kind'] == 'members':
        cj = canon_json(C, R, work)
        gm, checks = gate_members(cj, C['top'], P, A0)
        report['member_checks'] = checks
        for pn, (d, bl) in gm.items():
            nets = []
            for pinl in bl:
                if isinstance(pinl, str):
                    nets.append(pinl); continue
                if not pinl:
                    nets.append(None); continue
                if d == 'output':
                    s = {pm[(p, n, i)] for p, n, i, dd in pinl if dd == 'output'} or {pm[(p, n, i)] for p, n, i, _ in pinl}
                else:
                    s = {pm[(p, n, i)] for p, n, i, _ in pinl}
                if len(s) != 1:
                    raise SystemExit(f'{module}: canonical {pn} bit -> {len(s)} master nets {pinl[:3]}')
                nets.append(s.pop())
            cbit[pn] = (d, nets)
    elif spec['kind'] == 'rest':
        keep_types = kept_types_of(C)
        A1, keep, tag = a1_design(F, A0, spec, keep_types, work)
        A1top = A1['modules'][top]
        report['a1'] = dict(tag=tag, kept_types=keep)
        cbit = rest_canon_bits(C, A1top, report)
        # plan bits: A0 nets -> A1 nets through their public names (flatten keeps every A0 name in A1)
        tr = {}
        for bus, nets in P.bus.items():
            for b in nets:
                for nm in anchor_names(Atop, b):
                    try:
                        tr[b] = resolve_name(A1top, nm)
                        break
                    except KeyError:
                        continue
                else:
                    raise SystemExit(f'{module}: plan net {b} ({bus}) has no public name in A1')
        P.bus = {bus: [tr[b] for b in nets] for bus, nets in P.bus.items()}
        info_extra = dict(A1=A1, A1tag=tag, keep=keep)
    elif spec['kind'] == 'manual':
        # hand-written canonical (gen_split_rtl.py: the twin text minus the excluded child): canonical port = the
        # same-named port of the instance spec['inst'], or (sk_*) the pin of the excluded child it replaces
        A1, keep, tag = a1_design(F, A0, spec, set(), work)
        A1top = A1['modules'][top]
        report['a1'] = dict(tag=tag, kept_types=keep)
        cj = canon_json(C, R, work)
        sink = A1top['cells'][spec['sink']]
        for pn, pp in cj['modules'][C['top']]['ports'].items():
            w = len(pp['bits'])
            if pn in spec['sink_pins']:
                bl = sink['connections'][spec['sink_pins'][pn]]
                if len(bl) != w:
                    raise SystemExit(f'{module}: {pn} width {w} != sink pin {len(bl)}')
                cbit[pn] = (pp['direction'], list(bl))
            else:
                nets = []
                for i in range(w):
                    nm = f"{spec['inst']}.{pn}" if w == 1 else f"{spec['inst']}.{pn}[{i}]"
                    try:
                        nets.append(resolve_name(A1top, nm))
                    except KeyError:
                        raise SystemExit(f'{module}: canonical {pn}: no master net {nm}')
                cbit[pn] = (pp['direction'], nets)
        tr = {}
        for bus, nets in P.bus.items():
            for b in nets:
                for nm in anchor_names(Atop, b):
                    try:
                        tr[b] = resolve_name(A1top, nm)
                        break
                    except KeyError:
                        continue
                else:
                    raise SystemExit(f'{module}: plan net {b} ({bus}) has no public name in A1')
        P.bus = {bus: [tr[b] for b in nets] for bus, nets in P.bus.items()}
        info_extra = dict(A1=A1, A1tag=tag, keep=keep, gate_prefix=spec['inst'] + '.')
    else:
        raise SystemExit(f'{module}: kind {spec["kind"]} not implemented in this pass')
    net2in = collections.defaultdict(list)
    net2out = collections.defaultdict(list)
    for pn, (d, nets) in cbit.items():
        for j, b in enumerate(nets):
            if b is None or b in CONST:
                continue
            (net2in if d == 'input' else net2out)[b].append((pn, j))
    pbits, dead, problems = {}, {}, []
    for bus in order:
        nets = P.bus.get(bus)
        if nets is None:
            problems.append(f'plan bus {bus} not derived from the master')
            continue
        if len(nets) != planw[bus]:
            # RTL boundary bits the as-built netlist does not carry (folded / unread there): the canonical top (cut
            # from the as-built netlist) has no port bit on them.  Inputs: free inputs of the gold (xdead_*) - the
            # miter then proves they do not matter; outputs: not exposed (nothing outside reads them as built).
            ref = net2in if P.dirs[bus] == 'input' else net2out
            rd = [b for b in nets if b in ref]
            if len(rd) == planw[bus]:
                dead[bus] = [b for b in nets if b not in ref]
                nets = rd
            if len(nets) != planw[bus]:
                problems.append(f'bus {bus} plan {planw[bus]} derived {len(nets)}')
                continue
        pbits[bus] = nets
    extra = [b for b in P.bus if b not in planw]
    if extra:
        problems.append(f'derived buses not in the plan {extra[:8]}')
    if problems:
        report['problems'] = problems
        raise SystemExit(f'{module}: derived boundary != plan pins (PLAN ITEM): {problems[:4]}')
    srcs, conns, outs_assign, unread = {}, {}, [], []
    for bus in order:
        d = P.dirs[bus]
        for i, b in enumerate(pbits[bus]):
            e = bus if scal[bus] else f'{bus}[{i}]'
            if d == 'input':
                if not net2in.get(b):
                    unread.append(e)
                srcs[b] = e
            else:
                cs = net2out.get(b)
                if not cs and b in CONST:
                    # master constant on a plan output (e.g. sfu u_vm.stage_mask = all ones): the canonical carries
                    # it as a constant-driven output port of the same name (unconnected to its core) - use that
                    # port bit; else drive the master constant.  The miter checks the value either way.
                    cand = [pn for pn, (dd, nn) in cbit.items() if dd == 'output' and len(nn) == planw[bus]
                            and (bus == pn or bus.endswith('_' + pn)) and nn[i] is None]
                    cs = [(cand[0], i)] if len(cand) == 1 else [(None, b)]
                    report.setdefault('const_outputs', []).append(f'{e}={b} via {cs[0][0] or "constant"}')
                if not cs:
                    raise SystemExit(f'{module}: plan output {e} has no canonical driver')
                outs_assign.append((e, cs[0][0], cs[0][1]))
    if mutant:
        done = False
        for bus in sorted(order, key=lambda b: -len(pbits[b])):
            nb = pbits[bus]
            if P.dirs[bus] == 'input' and len(nb) >= 2 and nb[0] in net2in and nb[1] in net2in and \
                    not re.search(r'(clk|rst)', bus):
                srcs[nb[0]], srcs[nb[1]] = srcs[nb[1]], srcs[nb[0]]
                report['mutant'] = f'{bus}[0] <-> {bus}[1]'
                done = True
                break
        if not done:
            raise SystemExit(f'{module}: no mutant candidate')
    ties, opens = [], []
    for pn, (d, nets) in cbit.items():
        if d == 'input':
            row = []
            for j, b in enumerate(nets):
                if b in CONST:
                    row.append(f"1'b{b if b in '01' else '0'}"); ties.append(f'{pn}[{j}]={b}')
                elif b in srcs:
                    row.append(srcs[b])
                elif b is None:
                    # canonical input bit the canonical core never reads (rest_wrap: not to the core): wire the
                    # same-named plan input (parent connection kept) or tie 0; unread either way (miter checks)
                    cand = [bb for bb in order if P.dirs[bb] == 'input' and planw[bb] == len(nets)
                            and (bb == pn or bb.endswith('_' + pn))]
                    if len(cand) == 1:
                        row.append(cand[0] if scal[cand[0]] else f'{cand[0]}[{j}]')
                    else:
                        row.append("1'b0")
                    ties.append(f'{pn}[{j}]=unread->{cand[0] if len(cand) == 1 else "0"}')
                else:
                    raise SystemExit(f'{module}: canonical input {pn}[{j}] on master net {b} with no plan pin')
            conns[pn] = row
        else:
            used = {j for (_, p2, j) in outs_assign if p2 == pn}
            opens += [f'{pn}[{j}]' for j in range(len(nets)) if j not in used]
    txt = emit(module, order, P.dirs, planw, scal, C['top'], cbit, conns, outs_assign, report['views'], v)
    report.update(dict(canonical_type=v['canonical_type'], canonical_top=C['top'], plan_buses=len(order),
                       plan_bits=sum(planw.values()), pins_tables=len(tabs),
                       dead_bits={k: len(x) for k, x in dead.items()}, unread_plan_inputs=unread[:20],
                       n_unread_plan_inputs=len(unread), tied_canonical_bits=ties[:40], n_tied=len(ties),
                       open_canonical_bits=len(opens)))
    names = {}
    ntop = info_extra['A1']['modules'][top] if info_extra else Atop
    for bus in order:
        names[bus] = [netname(ntop, b) for b in pbits[bus]]
    return txt, dict(P=P, pbits=pbits, dead=dead, order=order, scal=scal, C=C, R=R, v=v, cbit=cbit, names=names,
                     kind=spec['kind'], **info_extra)


def glue_root_fn(Atop, spec):
    """bit order of a 'glue' plan bus (boundary nets with no labelling pin): (port name, bit index) of the include-root
    instance port the net crosses (alphabetical port order, ascending index).  Only single-include pieces have glue."""
    if len(spec['include']) != 1 or not spec['include'][0]:
        return None
    pre = spec['include'][0].replace('/', '.') + '.'
    idx = {}
    for n, x in Atop['netnames'].items():
        if not n.startswith(pre) or '.' in n[len(pre):]:
            continue
        port = n[len(pre):]
        for i, b in enumerate(x['bits']):
            if isinstance(b, int):
                k = i + x.get('offset', 0) if not x.get('upto', 0) else len(x['bits']) - 1 - i + x.get('offset', 0)
                idx.setdefault(b, (port, k))
    return lambda b, pins: idx.get(b)


def F_ren(F, s):
    return ren_fn(F)(s)


_NN = {}


def netname(Atop, b):
    """a readable master name of net b (shortest public netname bit)."""
    key = id(Atop)
    if key not in _NN:
        d = {}
        for n, x in Atop['netnames'].items():
            hid = x.get('hide_name', 0)
            for i, bb in enumerate(x['bits']):
                if bb in CONST:
                    continue
                nm = n if len(x['bits']) == 1 else f'{n}[{i + x.get("offset", 0)}]'
                cur = d.get(bb)
                if cur is None or (cur[0], len(cur[1])) > (hid, len(nm)):
                    d[bb] = (hid, nm)
        _NN[key] = d
    return _NN[key].get(b, (1, str(b)))[1]


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


def emit(module, order, dirs, planw, scal, ctop, cbit, conns, outs_assign, views, v):
    L = [f'// GENERATED by physical/die_plan/hbm_arch_cores/split/sw2.py (ELEM-HBM/SPLIT2 2026-10-24). Pure wiring.',
         f'// Plan module {module}: exactly the B2l plan pins (pins tables: {", ".join(views)}),',
         f'// wired per bit to the canonical top {ctop} as the bound master wires them: plan bus bit i = the i-th',
         f'// boundary net of the bus in ascending index on its labelling pin (split/cutmap.py).  Unpinned canonical outputs',
         f'// are open; constants are the master constants on those nets.  Exactness record:',
         f'// physical/die_plan/hbm_arch_cores/results/split_wrappers_b2l.json (per-bit map results/split_wrappers_b2l/).',
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
        bus = re.sub(r'\[\d+\]$', '', e)
        if pn is None:
            per.setdefault(bus, []).append(f"1'b{j}")
            continue
        w = len(cbit[pn][1])
        per.setdefault(bus, []).append(f'c_{pn}[{j}]' if w > 1 else f'c_{pn}')
    for bus, src in per.items():
        L.append(f'    assign {bus} = {runs(src)};')
    L += ['endmodule', '`default_nettype wire', '']
    return '\n'.join(L)


# ---------------------------------------------------------------------------------------------------- miter
def ys(script, wd, name):
    p = os.path.join(wd, name + '.ys')
    open(p, 'w').write(script)
    r = subprocess.run([YOSYS, '-q', '-l', os.path.join(wd, name + '.log'), '-s', p], capture_output=True,
                       text=True, cwd=wd)
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
        if k in nn:
            continue
        nn[k] = x
    mod['netnames'] = nn


def _addport(mod, name, like):
    mx = 1 + max([b for p in mod['ports'].values() for b in p['bits'] if isinstance(b, int)] +
                 [b for n in mod['netnames'].values() for b in n['bits'] if isinstance(b, int)] + [1])
    bits = list(range(mx, mx + len(like['bits'])))
    mod['ports'][name] = {'direction': like['direction'], 'bits': bits}
    mod['netnames'][name] = {'hide_name': 0, 'bits': bits, 'attributes': {}}


def miter(F, A0, module, spec, info, wrapper_txt, work, tag):
    wd = os.path.join(work, 'miter', f'{module}{tag}')
    os.makedirs(wd, exist_ok=True)
    P, pbits, dead, order = info['P'], info['pbits'], info['dead'], info['order']
    C, R = info['C'], info['R']
    top = F['twin']
    rest = info['kind'] in ('rest', 'manual')
    D = info['A1'] if rest else A0
    Atop = D['modules'][top]
    gm = {'attributes': {}, 'ports': {}, 'cells': {}, 'netnames': copy.deepcopy(Atop['netnames'])}
    paths = [p for p, _, _ in P.members]
    if rest:
        scopes = cutmap.scopes_of(Atop)
        inc = spec['include']
        cellmap = {}
        for c, x in Atop['cells'].items():
            if x['type'] == '$scopeinfo':
                continue
            pth = cutmap.cell_path(c, x, scopes)
            if (('' in inc) or cutmap.under(pth, inc)) and not cutmap.under(pth, spec['exclude']):
                gm['cells'][c] = copy.deepcopy(x)
        mtypes = []
    else:
        cellmap = {c: f'm_{role}' for (path, ty, c), role in zip(P.members, roles_of(paths))}
        for path, ty, c in P.members:
            gm['cells'][c] = copy.deepcopy(Atop['cells'][c])
        mtypes = sorted({ty for _, ty, _ in P.members})
    for bus in order:
        gm['ports'][bus] = {'direction': P.dirs[bus], 'bits': list(pbits[bus])}
    for bus, nets in dead.items():
        if P.dirs[bus] == 'input':
            gm['ports'][f'xdead_{bus}'] = {'direction': 'input', 'bits': list(nets)}
    for pn in gm['ports']:
        gm['netnames'].pop(pn, None)
    for pn in Atop['ports']:
        if pn in gm['netnames'] and pn not in gm['ports']:
            gm['netnames']['xmaster_' + pn] = gm['netnames'].pop(pn)
    gj = {'creator': 'split/sw2.py', 'modules': {k: v for k, v in D['modules'].items() if k != top}}
    gj['modules']['gold'] = gm
    rename_json(gj, 'gold', cellmap, [])
    json.dump(gj, open(os.path.join(wd, 'gold_in.json'), 'w'))
    kset = set(mtypes or info.get('keep', []))
    for mn, mv in gj['modules'].items():
        if mn == 'gold':
            continue
        at = mv.setdefault('attributes', {})
        at.pop('keep_hierarchy', None)
        if mn in kset:
            at['keep_hierarchy'] = '00000000000000000000000000000001'
    json.dump(gj, open(os.path.join(wd, 'gold_in.json'), 'w'))
    rc, out = ys('read_json gold_in.json\nhierarchy -top gold\nflatten\nmemory -nomap\nopt_clean\nwrite_json gold_flat.json\n',
                 wd, 'gold1')
    if rc:
        return dict(verdict='ERROR', stage='gold', log=out)
    open(os.path.join(wd, f'{module}__wrap.sv'), 'w').write(wrapper_txt)
    files = list(dict.fromkeys(R['files'] + ([C['file']] if C.get('file') else [])))
    L = read_cmds(files, macro_bbs(R), R.get('defines', []))
    L.append(f'read_verilog -sv -DSYNTHESIS {module}__wrap.sv')
    L += [f'hierarchy -check -top {module}', 'proc']
    gate_types = {base_type(t) for t in kset}
    L += ['write_json gate_h.json']
    rc, out = ys('\n'.join(L) + '\n', wd, 'gate0')
    if rc:
        return dict(verdict='ERROR', stage='gate', log=out)
    gh = json.load(open(os.path.join(wd, 'gate_h.json')))
    for mn, mv in gh['modules'].items():
        at = mv.setdefault('attributes', {})
        at.pop('keep_hierarchy', None)
        if base_type(mn) in gate_types and mn != module:
            at['keep_hierarchy'] = '00000000000000000000000000000001'
    json.dump(gh, open(os.path.join(wd, 'gate_h.json'), 'w'))
    rc, out = ys(f'read_json gate_h.json\nhierarchy -top {module}\nflatten\nmemory -nomap\nopt_clean\nrename -top gate\n'
                 'write_json gate_flat.json\n', wd, 'gate1')
    if rc:
        return dict(verdict='ERROR', stage='gate', log=out)
    gt = json.load(open(os.path.join(wd, 'gate_flat.json')))
    cm = {} if rest else {f'u_core.{role}': f'm_{role}' for role in roles_of(paths)}
    if info.get('gate_prefix'):
        mod = gt['modules']['gate']
        pre = info['gate_prefix']
        fix = lambda n: pre + n[len('u_core.'):] if n.startswith('u_core.') else n
        mod['cells'] = {fix(c): x for c, x in mod['cells'].items()}
        mod['netnames'] = {fix(n): x for n, x in mod['netnames'].items()}
    else:
        rename_json(gt, 'gate', cm, ['u_core.u_x.', 'u_core.'])
    json.dump(gt, open(os.path.join(wd, 'gate_in.json'), 'w'))
    for side in ('gold', 'gate'):
        src = 'gold_flat.json' if side == 'gold' else 'gate_in.json'
        rc, out = ys(f'read_json {src}\nhierarchy -top {side}\nexpose -evert {side}/c:* {side}/t:$* %d {side}/t:$paramod* %u\n'
                     f'hierarchy -top {side}\nopt_clean\nwrite_json {side}_ev.json\n', wd, f'{side}2')
        if rc:
            return dict(verdict='ERROR', stage=f'{side} evert', log=out)
    g = json.load(open(os.path.join(wd, 'gold_ev.json')))
    t = json.load(open(os.path.join(wd, 'gate_ev.json')))
    gp, tp = g['modules']['gold']['ports'], t['modules']['gate']['ports']
    only_g = sorted(set(gp) - set(tp))
    only_t = sorted(set(tp) - set(gp))
    notes = []
    for name in only_g:
        if gp[name]['direction'] != 'input':
            notes.append(f'gold-only output port {name}')
        elif not name.startswith('xdead_'):
            notes.append(f'gold-only input port {name}')
        _addport(t['modules']['gate'], name, gp[name])
    for name in only_t:
        notes.append(f'gate-only {tp[name]["direction"]} port {name}')
        _addport(g['modules']['gold'], name, tp[name])
    wid = [n for n in set(gp) & set(tp) if len(gp[n]['bits']) != len(tp[n]['bits'])]
    if wid:
        return dict(verdict='FAIL', stage='ports', detail=f'width differs: {wid[:6]}', notes=notes, dir=wd)
    g['modules'] = {'gold': g['modules']['gold']}
    t['modules'] = {'gate': t['modules']['gate']}
    left = [c for m in (g, t) for mm in m['modules'].values() for c, x in mm['cells'].items()
            if not x['type'].startswith('$') or x['type'].startswith('$paramod')]
    # vacuity guard: every kept instance must have become ports (its pins compared / driven as free inputs)
    if left:
        return dict(verdict='ERROR', stage='evert', detail=f'instances left {left[:5]}', dir=wd)
    alias_n = 0
    if rest:
        # the rest canonical core is a bit-blasted netlist (scalar wires '\\u.beat[5]'): give the gold's public vector
        # nets per-bit aliases of the same names so equiv_make pairs the state bits
        gm_ = g['modules']['gold']['netnames']
        tn_ = t['modules']['gate']['netnames']
        add = {}
        for n, x in gm_.items():
            if n.startswith('$') or len(x['bits']) < 2:
                continue
            off, upto = x.get('offset', 0), x.get('upto', 0)
            for i, b in enumerate(x['bits']):
                k = (len(x['bits']) - 1 - i if upto else i) + off
                nm = f'{n}[{k}]'
                if nm in tn_ and nm not in gm_ and isinstance(b, int):
                    add[nm] = dict(hide_name=0, bits=[b], attributes={})
        gm_.update(add)
        alias_n = len(add)
    json.dump(g, open(os.path.join(wd, 'gold_m.json'), 'w'))
    json.dump(t, open(os.path.join(wd, 'gate_m.json'), 'w'))
    if os.path.exists(os.path.join(wd, 'equiv_status.txt')):
        os.remove(os.path.join(wd, 'equiv_status.txt'))
    hasmem = any(x['type'].startswith('$mem') for m in (g, t) for mm in m['modules'].values()
                 for x in mm['cells'].values())
    rc, out = ys('read_json gold_m.json\nread_json gate_m.json\n' + ('memory_map\nopt_clean\n' if hasmem else '') +
                 'async2sync\nequiv_make gold gate eq\nhierarchy -top eq\n' +
                 # rest / manual (big): cheap combinational pass + induction first; -seq 4 only on what remains
                 ('equiv_simple\nequiv_induct -seq 4\nequiv_simple -seq 4\nequiv_induct -seq 4\n' if rest else
                  'equiv_simple -seq 4\nequiv_induct -seq 4\n') +
                 'tee -o equiv_status.txt equiv_status\nequiv_status -assert\n', wd, 'equiv')
    stp = os.path.join(wd, 'equiv_status.txt')
    st = open(stp).read() if os.path.exists(stp) else ''
    m = re.search(r'Found (\d+) \$equiv cells', st)
    un = re.search(r'Of those cells (\d+) are proven and (\d+) are unproven', st)
    unproven = int(un.group(2)) if un else (0 if 'Equivalence successfully proven' in st else None)
    unobs = []
    if unproven:
        # an unproven $equiv between two same-named nets that NOTHING reads on either side (no cell input, no port) is
        # unobservable: it cannot reach any output, and no other $equiv was proven assuming it.  Such pairs arise
        # from dead RTL bits (e.g. a flop capturing an xdead_* input that as-built removed).  Everything else counts.
        def readers(mod, nm):
            x = mod['netnames'].get(nm)
            if x is None:
                return None
            bs = {b for b in x['bits'] if isinstance(b, int)}
            r = 0
            for c in mod['cells'].values():
                for pn, bl in c['connections'].items():
                    if c.get('port_directions', {}).get(pn) != 'output' and bs & set(bl):
                        r += 1
            for pp in mod['ports'].values():
                if bs & set(pp['bits']):
                    r += 1
            return r
        gmod, tmod = g['modules']['gold'], t['modules']['gate']
        pairs = re.findall(r'Unproven \$equiv \S+ \\(\S+)_gold \\(\S+)_gate', st)
        if len(pairs) == unproven:
            for a_, b_ in pairs:
                if a_ == b_ and readers(gmod, a_) == 0 and readers(tmod, b_) == 0:
                    unobs.append(a_)
    if rc and unproven and len(unobs) == unproven and not notes:
        verdict = 'PASS'
    elif rc == 0 and not notes and unproven == 0:
        verdict = 'PASS'
    elif (unproven or 0) > 0 or notes:
        verdict = 'FAIL'
    else:
        verdict = 'ERROR'
    res = dict(verdict=verdict, equiv_cells=int(m.group(1)) if m else None, unproven=unproven,
               ports=len(gp), gold_only_ports=only_g[:20], gate_only_ports=only_t[:20], notes=notes[:20], dir=wd,
               cmd=f'cd {wd} && yosys -s equiv.ys')
    res['gold_bit_aliases'] = alias_n
    if unobs:
        res['unobservable_unproven'] = unobs[:20]
        res['n_unobservable_unproven'] = len(unobs)
    if verdict != 'PASS':
        res['unproven_e_g'] = [l.strip() for l in st.splitlines() if 'Unproven' in l][:6]
        if rc and not st:
            res['log'] = out
    return res


# ---------------------------------------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--family', required=True)
    ap.add_argument('--views', default='')
    ap.add_argument('--work', default=WORK0)
    ap.add_argument('--out', default=os.path.join(HAC, 'wrappers'))
    ap.add_argument('--maps', default=os.path.join(HAC, 'results', 'split_wrappers_b2l'))
    ap.add_argument('--no-miter', action='store_true')
    ap.add_argument('--mutant', default='', help="modules (comma) that also get the mutant control, or 'all'")
    a = ap.parse_args()
    F = FAMILIES[a.family]
    work = os.path.join(a.work, a.family)
    specs = F['views']()
    A0 = elab_master(F, a.family, specs, work)
    merged = merge_ff_bits(A0, F['twin']) if F.get('merge_ff_bits') else 0
    sel = [x for x in a.views.split(',') if x] or list(specs)
    os.makedirs(a.maps, exist_ok=True)
    res = {}
    for key in sel:
        module = key.split('@')[0]
        rep = dict(family=a.family, module=module, twin=F['twin'], params=F['params'], merged_ff_bits=merged,
                   include=specs[key]['include'],
                   exclude=specs[key]['exclude'], kind=specs[key]['kind'])
        t0 = time.time()
        if F.get('a0_per_view'):
            A0 = elab_master(F, a.family, {key: specs[key]}, work, tag='_' + re.sub(r'\W', '_', module))
            if F.get('merge_ff_bits'):
                rep['merged_ff_bits'] = merge_ff_bits(A0, F['twin'])
        try:
            txt, info = build_view(F, A0, module, specs[key], work, rep)
        except SystemExit as e:
            rep['error'] = str(e)
            rep['verdict'] = 'NOT_BUILT'
            print(module, 'ERROR', e, flush=True)
            res[key] = rep
            os.makedirs(os.path.join(work, 'reports'), exist_ok=True)
            json.dump(rep, open(os.path.join(work, 'reports', f'{module}.json'), 'w'), indent=1, default=str)
            continue
        open(os.path.join(a.out, f'{module}.sv'), 'w').write(txt)
        json.dump(dict(module=module, convention='plan bus bit i = i-th boundary net in ascending index on its '
                                                 'labelling pin; names = master (twin) net names',
                       twin=F['twin'], params=F['params'], buses=info['names'],
                       dead_bits={k: [netname((info.get('A1') or A0)['modules'][F['twin']], b) for b in v]
                                  for k, v in info['dead'].items()}),
                  open(os.path.join(a.maps, f'{module}.map.json'), 'w'), indent=0)
        if not a.no_miter:
            rep['miter'] = miter(F, A0, module, specs[key], info, txt, work, '')
            rep['verdict'] = rep['miter']['verdict']
            if a.mutant == 'all' or module in a.mutant.split(','):
                mrep = {}
                mtxt, minfo = build_view(F, A0, module, specs[key], work, mrep, mutant=True)
                mr = miter(F, A0, module, specs[key], minfo, mtxt, work, '__mutant')
                rep['mutant'] = dict(swap=mrep.get('mutant'), verdict=mr['verdict'], unproven=mr.get('unproven'),
                                     caught=mr['verdict'] == 'FAIL', dir=mr.get('dir'))
        rep['seconds'] = round(time.time() - t0, 1)
        res[key] = rep
        os.makedirs(os.path.join(work, 'reports'), exist_ok=True)
        json.dump(rep, open(os.path.join(work, 'reports', f'{module}.json'), 'w'), indent=1, default=str)
        print(module, rep.get('verdict'), json.dumps({k: rep[k] for k in ('miter', 'mutant') if k in rep},
                                                     default=str)[:600], flush=True)


if __name__ == '__main__':
    main()
