#!/usr/bin/env python3
"""KVG3-WI 10-24: top-down pins for the 22 PLANNED host-root cores of kv3_hub_Wi (G0C 'no pins listed').

core_pins_v37p.py skips the qkd_hr_* cores: they are children INSIDE one leaf of hub_Wi, `host` = the bound instance
u_host (qkd_host_root_admission_obsx) of the bound partition netlist <RTL>/kv3_hub_Wi_part.sv.  This script follows the
v37p logic one level deeper:

 1. elaborate the host leaf hierarchically (yosys read_verilog -defer -sv -DSYNTHESIS of the kit filelist, hierarchy
    -top qkd_host_root_admission_obsx with the parameters the bound partition passes to u_host, proc, write_json; no
    flatten).  Reading aid only: the obsx g_mu generate blocks use nets before declaring them (yosys rejects that,
    Verilator / the binder accept it), so a scratch copy hoists the pure net declarations to the block top (no
    semantic change, the source tree is untouched).
 2. map the cluster-plan members (results/arch/qwen_split_1014/host_root_cluster/partition_plan.json, paths in
    qkd_host_root_admission: top/u_rank/...) onto the obsx hierarchy (a plan segment matches an instance name equal to it
    or ending in '.<segment>': the obsx wraps every block in a g_mu generate scope).  qkd_hr_phy_adp (8 instances, plan
    member g_slice[0].u_slice) maps instance i to g_slice[i].u_slice.
 3. GLUE RULE (KVG3-WI): `glue:*` members (qm_core / qm_host / qm_ingest / fence_core / fence_host / fence_sync) are the
    RTL re-cut pieces of plan actions A1/A2 (native_qm and visibility_fence own logic split by clock family); they do
    not exist as instances in the bound RTL.  A core = ONLY its real instance members; the native_qm own logic
    (u_qm minus u_eng / u_hx / u_cx / u_ox / u_rx) and the whole u_fence stay in the hub_Wi partition glue (a few k
    cells), so every core stays derivable from the bound RTL and hardenable without an RTL re-cut.  Likewise instances
    no child lists (obsx-only u_obs, u_hc, the wrapper own logic) stay glue.  They are reported, not invented.
 4. boundary bits: per member port bit, the host-level net (bit-exact union-find over the non-member hierarchy) reaches
    something outside the core (another member, a glue cell, a host-leaf port).  Partners: other core -> its centre;
    host-leaf port -> its partition-net partners (the v37p rule on u_host: partition bus -> its face window, glue leaf /
    ot_dp_st / ot_dp_dly chain one hop); glue cells -> BFS through <= DEPTH glue cells (nets over FANOUT ends not
    expanded), reached targets kept when <= HOP_MAX distinct.  Clock / reset pins get no data partner.
 5. faces: core_pins_v37p.choose() / balance() (one pins_file per module, one orient per instance), even spread on the
    plan tracks (E/W M4 spill M6 y-tracks, N/S M5 spill M7 x-tracks, symmetric pitch/2 offsets, 2.16-um corner
    keep-out, pins 0.096 um inside the face).
Writes OUT/cores/qkd_hr_*_pins.json, OUT/cores/core_patch_v38u.json (orient / pins_file / note per hub_Wi core; applied
by post_v38u.py), OUT/core_conns.json (kv3_hub_Wi entries replaced, other types kept), OUT/core_pins_hr_report.json.
usage: core_pins_hr.py die_plan.json RTL_DIR KIT_RTL_F OUT_PLAN_DIR [--work DIR]"""
import argparse
import json
import math
import os
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO / 'tools/die_plan'))
from rtlnet import Net                      # noqa: E402
import core_pins_v37p as V                  # noqa: E402

TN, LEAF, LEAF_INST = 'kv3_hub_Wi', 'host', 'u_host'
HR_PLAN = REPO / 'results/arch/qwen_split_1014/host_root_cluster/partition_plan.json'
TOP = 'qkd_host_root_admission_obsx'
DEPTH, FANOUT, HOP_MAX = 3, 64, 8
CLKRST = re.compile(r'^(clk|ck|ck_\w+|clk_\w+|\w*clk|wck|rck|\w+_wck|\w+_rck|rst_n|arst_n|\w*_rst_n|por_n)$')
HOSTCLK = re.compile(r'^(ck_\w+|por_n)$')


# ----------------------------------------------------------------------------------------------- elaboration
def hoist(src, dst):
    """scratch copy of the obsx file with the pure net declarations of every g_mu block hoisted to the block top."""
    lines, out, i = Path(src).read_text().split('\n'), [], 0
    decl = re.compile(r'^\s*(wire|logic|reg)(\s|\[)[^=()]*$')
    while i < len(lines):
        out.append(lines[i])
        if 'begin:g_mu' in lines[i]:
            blk, up, j, infn = [], [], i + 1, False
            while not lines[j].startswith('end endgenerate'):
                ln = lines[j]
                infn = infn or bool(re.search(r'\bfunction\b', ln))
                if infn or ln.lstrip().startswith('//'):
                    blk.append(ln)
                else:
                    code, _, com = ln.partition('//')
                    parts, keep = code.split(';'), []
                    for p in parts[:-1]:
                        (up if decl.match(p) else keep).append(p + ';')
                    blk.append(''.join(keep) + parts[-1] + (('//' + com) if com else ''))
                if re.search(r'\bendfunction\b', ln):
                    infn = False
                j += 1
            out += up + blk
            i = j
            continue
        i += 1
    Path(dst).write_text('\n'.join(out))


def leaf_params(part_sv):
    m = re.search(r'^\s*' + TOP + r'\s*#\((.*?)\)\s*' + LEAF_INST + r'\s*\(', Path(part_sv).read_text(), re.M)
    return re.findall(r'\.(\w+)\(([^()]*)\)', m.group(1)) if m else []


def elaborate(kit_f, part_sv, work):
    work.mkdir(parents=True, exist_ok=True)
    js = work / 'host_elab.json'
    if js.exists():
        return js
    fs = [l.strip() for l in open(kit_f) if l.strip() and not l.startswith(('+', '-', '//'))]
    fs = [f for f in fs if not re.search(r'/kv3_hub_Wi_part(_bound)?\.sv$', f)]
    fs2 = []
    for f in fs:
        if f.endswith('/' + TOP + '.sv'):
            hoist(f, work / (TOP + '.sv'))
            f = str(work / (TOP + '.sv'))
        fs2.append(f)
    ch = ' '.join(f'-chparam {k} {v}' for k, v in leaf_params(part_sv))
    ys = work / 'host_elab.ys'
    ys.write_text(f"read_verilog -defer -sv -DSYNTHESIS {' '.join(fs2)}\nhierarchy -top {TOP} {ch}\nproc\n"
                  f"write_json {js}\n")
    env = dict(os.environ, PATH=str(Path.home() / '.local/opentallas-tools/bin') + ':' + os.environ.get('PATH', ''))
    subprocess.run(['yosys', '-q', '-l', str(work / 'host_elab.log'), str(ys)], check=True, env=env,
                   stdout=subprocess.DEVNULL)
    return js


# ----------------------------------------------------------------------------------------------- host connectivity
class Host:
    def __init__(self, js):
        self.J = json.load(open(js))['modules']
        self.top = next(m for m, v in self.J.items() if v.get('attributes', {}).get('top'))

    def resolve(self, member, slice_idx=None):
        """plan path top/a/b/c -> obsx instance path (real names joined by '/') or None"""
        segs = member.split('/')[1:]
        m, path = self.top, []
        for s in segs:
            if slice_idx is not None:
                s = re.sub(r'g_slice\[\d+\]', f'g_slice[{slice_idx}]', s)
            hit = [cn for cn, c in self.J[m]['cells'].items() if c['type'] in self.J and (cn == s or cn.endswith('.' + s))]
            if len(hit) != 1:
                return None
            path.append(hit[0])
            m = self.J[m]['cells'][hit[0]]['type']
        return '/'.join(path)

    def walk(self, members):
        """union-find over (inst path, bit) of the non-member hierarchy; returns nets {root: [ends]}, glue cells."""
        par = {}

        def f(x):
            r = x
            while par.get(r, r) != r:
                r = par[r]
            while par.get(x, x) != r:
                par[x], x = r, par[x]
            return r

        def u(a, b):
            a, b = f(a), f(b)
            if a != b:
                par[a] = b
        raw, glue, subtree = [], [], {}
        mods = {}

        def rec(m, path):
            has = False
            for cn, c in self.J[m]['cells'].items():
                cp = (path + '/' + cn) if path else cn
                if c['type'] in self.J:
                    if cp in members:
                        mods[cp] = c['type']
                        for p, bits in c['connections'].items():
                            for i, b in enumerate(bits):
                                if isinstance(b, int):
                                    raw.append(((path, b), ('M', cp, p, i)))
                        has = True
                        continue
                    ch = self.J[c['type']]
                    for p, bits in c['connections'].items():
                        cb = ch['ports'][p]['bits']
                        for i, b in enumerate(bits):
                            if isinstance(b, int) and isinstance(cb[i], int):
                                u((path, b), (cp, cb[i]))
                    sub = rec(c['type'], cp)
                    subtree[cp] = (c['type'], sub)
                    has |= sub
                else:
                    gid = len(glue)
                    glue.append((path, cn, c['type']))
                    for p, bits in c['connections'].items():
                        for b in bits:
                            if isinstance(b, int):
                                raw.append(((path, b), ('G', gid)))
            return has
        rec(self.top, '')
        for p, d in self.J[self.top]['ports'].items():
            for i, b in enumerate(d['bits']):
                if isinstance(b, int):
                    raw.append((('', b), ('P', p, i)))
        nets = {}
        for k, e in raw:
            nets.setdefault(f(k), []).append(e)
        gnets = {}
        for r, es in nets.items():
            for e in es:
                if e[0] == 'G':
                    gnets.setdefault(e[1], set()).add(r)
        self.mods = mods
        return nets, glue, gnets, subtree

    def port_info(self, mpath):
        """{port: (direction, [bits], offset)} of the module of a member instance"""
        m = self.J[self.mods[mpath]]
        off = {n: v.get('offset', 0) for n, v in m.get('netnames', {}).items()}
        return {p: (d['direction'], d['bits'], off.get(p, 0)) for p, d in m['ports'].items()}


# ----------------------------------------------------------------------------------------------- partition level
def leaf_partners(part_sv, bus_names):
    """{(host port, bit): set('bus:B')} -- core_pins_v37p rule on the u_host leaf: partition bus direct, glue leaf /
    station chain one hop."""
    net = Net(part_sv)
    g = net.graph()
    hop, nbr = {}, {}
    for nb, ends in g.items():
        for e in ends:
            hop.setdefault(e[0], set())
    for nb, ends in g.items():
        tg = {'bus:' + e[1] for e in ends if e[0] == '<port>' and e[1] in bus_names}
        gl = [e[0] for e in ends if e[0] not in ('<port>', LEAF_INST)]
        for e in gl:
            hop[e] |= tg
            nbr.setdefault(e, set()).update(x for x in gl if x != e)
    chain = {i for i, (m_, _) in net.insts.items() if m_.startswith('ot_dp_st') or m_.startswith('ot_dp_dly')}
    for _ in range(64):
        ch_ = False
        for i in chain:
            for j in nbr.get(i, ()):
                if not hop[i] >= hop[j] and j in chain:
                    hop[i] |= hop[j]; ch_ = True
                if not hop[j] >= hop[i]:
                    hop[j] |= hop[i]; ch_ = True
        if not ch_:
            break
    out = {}
    for p, e in net.insts[LEAF_INST][1].items():
        bs = net.bits(e)
        n = len(bs)
        for k, nb in enumerate(bs):
            if nb is None:
                continue
            tg = set()
            for x in g.get(net.find(nb), []):
                if x[0] == LEAF_INST:
                    continue
                if x[0] == '<port>':
                    if x[1] in bus_names:
                        tg.add('bus:' + x[1])
                elif x[0] in chain or len(hop.get(x[0], ())) <= HOP_MAX:
                    tg |= hop.get(x[0], set())
            out[(p, n - 1 - k)] = tg
    return out


# ----------------------------------------------------------------------------------------------- pin placement
def place(mod, pb, face_of, cw, ch):
    """v37p even spread of each face's bits over the plan tracks"""
    pins, rep = [], {}
    for f in 'NSEW':
        grp = [(b, bit) for b in sorted(pb) if face_of[b] == f for bit in sorted(pb[b])]
        if not grp:
            continue
        L = cw if f in 'NS' else ch
        lay = ['M5', 'M7'] if f in 'NS' else ['M4', 'M6']
        ntr = {l: int((L - 2 * V.KEEP) / V.PITCH[l]) for l in lay}
        use = [lay[0]] if len(grp) <= ntr[lay[0]] // 2 else lay
        cap = sum(ntr[l] // 2 for l in use)
        assert len(grp) <= cap, (mod, f, len(grp), cap)
        share = [len(grp)] if len(use) == 1 else [round(len(grp) * ntr[use[0]] / (ntr[use[0]] + ntr[use[1]]))]
        if len(use) == 2:
            share.append(len(grp) - share[0])
        k0 = 0
        for l, nl in zip(use, share):
            p_, o_ = V.PITCH[l], V.OFFS[l]
            lo = math.ceil((V.KEEP - o_) / p_)
            hi = math.floor((L - V.KEEP - o_) / p_)
            for j in range(nl):
                tr = lo + int((j + 0.5) * (hi - lo + 1) / nl)
                c = round(o_ + tr * p_, 6)
                b, bit = grp[k0 + j]
                x, y = {'N': (c, round(ch - 0.096, 6)), 'S': (c, 0.096), 'E': (round(cw - 0.096, 6), c),
                        'W': (0.096, c)}[f]
                pins.append(dict(name=f'{b}[{bit}]', layer=l, x=x, y=y))
            k0 += nl
        rep[f] = dict(pins=len(grp), layers=use)
    return pins, rep


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('plan'); ap.add_argument('rtl'); ap.add_argument('kit_f'); ap.add_argument('out')
    ap.add_argument('--work', default=str(Path.home() / 'scratch/kv-g3/wi/elab'))
    a = ap.parse_args()
    import check as C
    import schema as S
    plan = json.load(open(a.plan))
    SP = S.Plan(plan)
    t = plan['partition_types'][TN]
    W, H = t['outline_um']
    part_sv = Path(a.rtl) / f'{TN}_part.sv'
    hr = json.load(open(HR_PLAN))
    host = Host(elaborate(a.kit_f, part_sv, Path(a.work)))
    hcs = [h for h in t['hard_cores'] if h['module'].startswith('qkd_hr_')]
    # ---- members
    core_mem, missing, glue_members, report = {}, [], {}, {}
    for h in hcs:
        ch = hr['children'][h['module']]
        m = re.match(r'.*_(\d+)$', h['inst']) if ch.get('instances', 1) > 1 else None
        idx = int(m.group(1)) if m else None
        real, rels = [], []
        for mem in ch['members']:
            if mem.startswith('glue:'):
                glue_members.setdefault(h['module'], []).append(mem)
                continue
            rp = host.resolve(mem, idx)
            if rp is None:
                missing.append((h['inst'], mem))
                continue
            real.append(rp)
            rels.append(mem.split('/')[-1])
        assert len(set(rels)) == len(rels), (h['inst'], rels)
        core_mem[h['inst']] = dict(zip(real, rels))
        report[h['inst']] = dict(module=h['module'], members={r: p for p, r in zip(ch['members'], real)},
                                 glue_members_left_in_partition_glue=glue_members.get(h['module'], []))
    member_core = {p: ci for ci, ms in core_mem.items() for p in ms}
    nets, glue, gnets, subtree = host.walk(set(member_core))
    # instances outside every core (maximal subtrees without a member) = partition glue
    unassigned = sorted(p for p, (_, has) in subtree.items()
                        if not has and ('/' not in p or subtree[p.rsplit('/', 1)[0]][1]))
    hb = leaf_partners(part_sv, {b['name'] for b in t.get('buses', [])})
    bt = C._bus_targets(SP, TN)
    cent = {h['inst']: (h['origin_um'][0] + h['outline_um'][0] / 2, h['origin_um'][1] + h['outline_um'][1] / 2)
            for h in t['hard_cores']}

    def port_tags(p, i):
        return set(hb.get((p, i), ()))

    pins_by_mod = {h['module']: {} for h in hcs}
    conns = {h['inst']: {} for h in hcs}
    insts_by_mod = {}
    memo = {}

    def reach(gid, d):
        """targets ('m:<member path>' | 'bus:<B>') on the nets of glue cell gid, plus d more glue cells deep"""
        k = (gid, d)
        if k in memo:
            return memo[k]
        memo[k] = res = set()
        for n_ in gnets.get(gid, ()):
            es_ = nets[n_]
            if len(es_) > FANOUT:
                continue
            for e in es_:
                if e[0] == 'M':
                    res.add('m:' + e[1])
                elif e[0] == 'P':
                    if not HOSTCLK.match(e[1]):
                        res |= port_tags(e[1], e[2])
                elif d > 0 and e[1] != gid:
                    res |= reach(e[1], d - 1)
        return res

    # index member ends -> net root
    mend = {}
    for r, es in nets.items():
        for e in es:
            if e[0] == 'M':
                mend[(e[1], e[2], e[3])] = r
    for h in hcs:
        ci = h['inst']
        ms = core_mem[ci]
        pb = pins_by_mod[h['module']]
        cc = conns[ci]
        for mp, rel in ms.items():
            pinf = host.port_info(mp)
            for p, (d, bits, off) in pinf.items():
                base = f'{rel}__{p}' if len(ms) > 1 else p
                for i in range(len(bits)):
                    r = mend.get((mp, p, i))
                    if r is None:
                        continue            # constant / unconnected at the instance
                    es = nets[r]
                    others = [e for e in es if not (e[0] == 'M' and member_core[e[1]] == ci)]
                    if not others:
                        continue            # intra-core net
                    pb.setdefault(base, set()).add(i + off)
                    direct, viag = set(), set()
                    clk = bool(CLKRST.match(p))
                    # direct ends
                    for e in others:
                        if e[0] == 'M':
                            direct.add('core:' + member_core[e[1]])
                        elif e[0] == 'P':
                            clk |= bool(HOSTCLK.match(e[1]))
                            direct |= port_tags(e[1], e[2])
                    # through glue cells (bounded, memoised per glue cell)
                    if len(es) <= FANOUT:
                        for e in es:
                            if e[0] == 'G':
                                for v in reach(e[1], DEPTH - 1):
                                    if v.startswith('m:'):
                                        if member_core[v[2:]] != ci:
                                            viag.add('core:' + member_core[v[2:]])
                                    else:
                                        viag.add(v)
                    viag -= direct
                    tg = direct | (viag if len(viag) <= HOP_MAX else set())
                    tg.discard('core:' + ci)
                    if clk:
                        tg = set()
                    if tg:
                        cc.setdefault(base, set()).update(tg)
        cx, cy = cent[ci]
        rec = {}
        for base in pb:
            dirs = []
            for v in cc.get(base, ()):
                k_, _, nm = v.partition(':')
                q = bt.get(nm, (None, None))[1] if k_ == 'bus' else cent.get(nm)
                if q is None:
                    continue
                dd = math.hypot(q[0] - cx, q[1] - cy)
                if dd > 1e-6:
                    dirs.append(((q[0] - cx) / dd, (q[1] - cy) / dd))
            if not dirs:
                dd = math.hypot(W / 2 - cx, H / 2 - cy) or 1
                dirs = [((W / 2 - cx) / dd * 1e-3, (H / 2 - cy) / dd * 1e-3)]
            rec[base] = dirs
        insts_by_mod.setdefault(h['module'], []).append((TN, ci, rec))
    # ---- faces + pins per module
    out = Path(a.out)
    (out / 'cores').mkdir(parents=True, exist_ok=True)
    outl = {h['module']: h['outline_um'] for h in hcs}
    patch, mods_rep = {}, {}
    for mod, pb in sorted(pins_by_mod.items()):
        if not pb:
            mods_rep[mod] = dict(pins=0, note='EMPTY: no boundary bits')
            continue
        cw, chh = outl[mod]
        face_of, orients = V.choose(pb, insts_by_mod[mod])
        face_of = V.balance(pb, insts_by_mod[mod], orients, face_of, cw, chh)
        pins, rep = place(mod, pb, face_of, cw, chh)
        fn = f'cores/{mod}_pins.json'
        json.dump(dict(schema='opentallas.die_plan.core_pins.v1', core=mod,
                       frame=f'core R0, origin (0,0), outline {cw} x {chh}',
                       source='KVG3-WI 10-24 top-down pin assignment (core_pins_hr.py): boundary bits of the real '
                              'instance members of the host-root cluster child inside the bound hub_Wi leaf u_host '
                              '(qkd_host_root_admission_obsx, binder kv41, RTL e33504a6f); glue:* members stay '
                              'partition glue; face = best facing to partners (other cores, host-leaf port -> '
                              'partition bus windows) over all instances; even spread on the plan tracks',
                       faces=rep, pins=pins), open(out / fn, 'w'), indent=0)
        for (_, ci, _), o in zip(insts_by_mod[mod], orients):
            gl = glue_members.get(mod, [])
            note = (f'qkd_host_rt cluster child {mod}; PLANNED core: pins top-down (core_pins_hr.py, KVG3-WI v3.8u) '
                    f'from the real instance members {sorted(core_mem[ci].values())} in u_host (obsx); '
                    + (f'glue members {", ".join(gl)} NOT in the core (stay hub_Wi partition glue, no RTL re-cut); '
                       if gl else '') + 'lef/lib pending (CORE-KS harden)')
            patch.setdefault(TN, {})[ci] = dict(orient=o, pins_file=fn, note=note)
        mods_rep[mod] = dict(pins=len(pins), faces=rep, groups=len(pb),
                             orients={ci: o for (_, ci, _), o in zip(insts_by_mod[mod], orients)})
        print(mod, len(pins), rep, file=sys.stderr)
    json.dump(patch, open(out / 'cores' / 'core_patch_v38u.json', 'w'), indent=1, sort_keys=True)
    cfile = out / 'core_conns.json'
    cj = json.load(open(cfile)) if cfile.exists() else {}
    cj[TN] = {ci: {b: sorted(v) for b, v in ps.items()} for ci, ps in sorted(conns.items()) if ps}
    json.dump(cj, open(cfile, 'w'), separators=(',', ':'), sort_keys=True)
    for ci in report:
        ps = conns.get(ci, {})
        report[ci]['pin_groups_with_partner'] = len(ps)
        report[ci]['partner_kinds'] = sorted({v.split(':')[0] for vs in ps.values() for v in vs})
    json.dump(dict(schema='opentallas.die_plan.core_pins_hr_report.v1', type=TN, leaf=f'{LEAF} = {LEAF_INST} ({TOP})',
                   params=dict(leaf_params(part_sv)), depth=DEPTH, fanout=FANOUT, hop_max=HOP_MAX,
                   glue_rule='cores = real instance members only; glue:* (A1/A2 re-cut pieces of native_qm / '
                             'visibility_fence) and instances no child lists stay hub_Wi partition glue',
                   missing_members=missing, glue_members=glue_members,
                   instances_outside_cores=unassigned, cores=report, modules=mods_rep),
              open(out / 'core_pins_hr_report.json', 'w'), indent=1, sort_keys=True)
    print('missing members:', missing, file=sys.stderr)


if __name__ == '__main__':
    main()
