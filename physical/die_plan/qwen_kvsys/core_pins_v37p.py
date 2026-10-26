#!/usr/bin/env python3
"""KV-P6-PINS 10-23: top-down pin assignment for the PLANNED hard cores of plan v3.7 (G0C 'no pins listed').

For every partition type with hard_cores[], read the bound partition netlist (binder RTL, tools/die_plan/bind.py output:
<RTL>/<type>_part.sv), find each core's boundary bits (member-leaf port bits whose net reaches anything outside the
core: a partition port, another core, a glue leaf), and their partners (partition bus -> its face window, other core ->
its centre, glue leaf -> the buses / cores that leaf touches, one hop).  Per core MODULE (one pins_file shared by all
its instances), each pin group (core port = '<member>__<leaf port>' for multi-leaf cores, the leaf port for single-leaf
cores) goes on the core face that best faces its partners summed over all instances (check.py core_faces score), ports
with no positioned partner on the face toward the type centre.  Pins per face are spread evenly over the whole face
(>= 2.16 um corner keep-out) on the plan tracks (E/W faces M4 y-tracks, N/S faces M5 x-tracks; symmetric offset pitch/2
so every orient stays on track); a face over 1 pin / 2 tracks spills onto M6/M7.
Writes cores/<module>_pins.json and core_conns.json (planned cores only; reuse-closed LEF cores keep their pins).
usage: core_pins_v37p.py die_plan.json RTL_DIR OUT_PLAN_DIR"""
import json, math, re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from rtlnet import Net

# kvs_pc chain kvpc0 -> 1 -> 2 -> 3: serpentine in the 2 x 2 core block (kvpc2 above kvpc1, kvpc3 above kvpc0), so
# every chain hop is a neighbour hop (as placed by post_v37c, 1 -> 2 was a diagonal back across the block)
SWAP = {tn: [('kvpc2', 'kvpc3')] for tn in ('kv3_pc', 'kv3_pc_v1', 'kv3_pc_v2', 'kv3_pc_v3')}
PITCH = dict(M4=0.048, M5=0.048, M6=0.064, M7=0.064)
OFFS = dict(M4=0.024, M5=0.024, M6=0.032, M7=0.032)
KEEP = 2.16
CLKRST = re.compile(r'^(clk|ck|ck_\w+|clk_\w+|rst_n|arst_n|\w*_rst_n)$')
HOP_MAX = 8      # a glue leaf touching more buses / cores than this is a hub: no direction, not a partner
NORM = dict(N=(0, 1), S=(0, -1), E=(1, 0), W=(-1, 0))


def members(t, hc):
    note = hc.get('note', '')
    m = re.match(r'(head_eighth|pv_pair): ([^;(]+)', note)
    insts = [c['inst'] for c in t['contents']]
    if m:
        pre = [x.strip() for x in m.group(2).split('+')]
        return [i for i in insts if any(i == p or i.startswith(p + '__') for p in pre)], pre
    return [i for i in insts if i == hc['inst']], None


def rel(inst, pre, hc):
    if pre is None:
        return None
    if hc['module'] == 'kv3_pv_pair':
        k = pre.index(next(p for p in pre if inst == p or inst.startswith(p + '__')))
        return f's{k}'
    return re.sub(r'^head\d__', '', inst).replace('__', '_')


def rtl_file(rtl, tn):
    f = Path(rtl) / f'{tn}_part.sv'
    if not f.exists():
        m = re.match(r'(.*)_(r\d+)$', tn)
        f = Path(rtl) / f'{m.group(1)}_part_{m.group(2)}.sv'
    return f


OR = dict(R0=(1, 1), MX=(1, -1), MY=(-1, 1), R180=(-1, -1))


def fscore(f, o, dirs):
    sx, sy = OR[o]
    return max(NORM[f][0] * ux * sx + NORM[f][1] * uy * sy for ux, uy in dirs)


def choose(pb, insts, rounds=6):
    """pin face per group (shared by every instance) + one orient per instance: alternate (faces | orients) to
    maximise the summed best cosine, with ports facing away (< -0.1) penalised hard."""
    ors = ['R0'] * len(insts)
    faces = {}
    for _ in range(rounds):
        faces = {b: max('NSEW', key=lambda f: (sum(fscore(f, o, rec[b]) for o, (_, _, rec) in zip(ors, insts)), f))
                 for b in pb}
        new = []
        for _, _, rec in insts:
            def val(o):
                v = 0.0
                for b, dirs in rec.items():
                    c = fscore(faces[b], o, dirs)
                    v += (c - 100 * (c < -0.1)) * len(pb[b])
                return v
            new.append(max(OR, key=val))
        if new == ors:
            break
        ors = new
    return faces, ors


def balance(pb, insts, ors, faces, cw, ch, dens=4):
    """spread: a face over 1 pin / `dens` tracks sheds its least-committed pin groups to the next-best face that
    still faces every instance's partners (cos >= 0 for all instances)."""
    cap = {f: int((cw if f in 'NS' else ch) / 0.048 / dens) for f in 'NSEW'}
    faces = dict(faces)
    for _ in range(4 * len(pb)):
        load = {f: sum(len(pb[b]) for b in pb if faces[b] == f) for f in 'NSEW'}
        over = [f for f in 'NSEW' if load[f] > cap[f]]
        if not over:
            break
        f0 = max(over, key=lambda f: load[f] - cap[f])
        best = None
        for b in pb:
            if faces[b] != f0:
                continue
            tot0 = sum(fscore(f0, o, rec[b]) for o, (_, _, rec) in zip(ors, insts))
            for f1 in 'NSEW':
                if f1 == f0 or load[f1] + len(pb[b]) > cap[f1]:
                    continue
                cs = [fscore(f1, o, rec[b]) for o, (_, _, rec) in zip(ors, insts)]
                if min(cs) < 0:
                    continue
                loss = (tot0 - sum(cs)) / len(insts)
                if best is None or loss < best[0]:
                    best = (loss, b, f1)
        if best is None:
            break
        faces[best[1]] = best[2]
    return faces


def apply_layout(types):
    """core moves (type frame, 8.64-um lattice) -> {type: {inst: origin}}: kvs_pc serpentine; pv join to the middle
    of its column (p0, p1, join, p2, p3 bottom-up) so the closed join's ts0 (S) / ts2 (N) face their pairs directly
    and ts1 (W) / ts3 (E) sit beside p1 / p3 (column top unchanged: 1071.36)."""
    moves = {}
    for tn, t in types.items():
        hs = {h['inst']: h for h in t.get('hard_cores', [])}
        if tn in SWAP:
            for a_, b_ in SWAP[tn]:
                moves.setdefault(tn, {})[a_] = hs[b_]['origin_um']
                moves[tn][b_] = hs[a_]['origin_um']
        if re.match(r'kv3_pv(_|$)', tn):
            for g in range(4):
                j = hs.get(f'pv__u_g{g}_j')
                ps = [hs[f'pvg{g}_p{k}'] for k in range(4)]
                y0, ph = ps[0]['origin_um'][1], ps[0]['outline_um'][1]
                gy = round(ps[1]['origin_um'][1] - y0 - ph, 6)
                if not j:
                    continue
                jy = round(y0 + 2 * (ph + gy), 6)
                moves.setdefault(tn, {})[j['inst']] = [j['origin_um'][0], jy]
                moves[tn][ps[2]['inst']] = [ps[2]['origin_um'][0], round(jy + j['outline_um'][1] + gy, 6)]
                moves[tn][ps[3]['inst']] = [ps[3]['origin_um'][0], round(jy + j['outline_um'][1] + 2 * gy + ph, 6)]
    for tn, mv in moves.items():
        hs = {h['inst']: h for h in types[tn]['hard_cores']}
        for ci, o in mv.items():
            hs[ci]['origin_um'] = list(o)
    return moves


def main():
    plan, rtl, out = json.load(open(sys.argv[1])), sys.argv[2], Path(sys.argv[3])
    types = plan['partition_types']
    moves = apply_layout(types)
    pins_by_mod = {}     # module -> {pin base: set(bits)}
    score = {}           # module -> {pin base: {face: score}}
    conns = {}
    stats = {}
    insts_by_mod = {}
    for tn, t in types.items():
        hcs = [h for h in t.get('hard_cores', []) if not h['module'].startswith('qkd_hr_')]
        if not hcs:
            continue
        net = Net(rtl_file(rtl, tn))
        g = net.graph()
        W, H = t['outline_um']
        bus_pt = {}
        for b in t.get('buses', []):
            bus_pt[b['name']] = None
        cent = {h['inst']: (h['origin_um'][0] + h['outline_um'][0] / 2, h['origin_um'][1] + h['outline_um'][1] / 2)
                for h in t['hard_cores']}
        r2c = {}
        mem = {}
        for h in t['hard_cores']:
            ms, pre = members(t, h)
            mem[h['inst']] = (ms, pre)
            for i in ms:
                r2c['u_' + i.replace('__', '_')] = h['inst']
        missing = [i for h in hcs for i in mem[h['inst']][0] if 'u_' + i.replace('__', '_') not in net.insts]
        assert not missing, (tn, missing[:5])
        # glue leaf -> partners (one hop)
        hop, nbr = {}, {}
        for nb, ends in g.items():
            for e in ends:
                hop.setdefault(e[0], set())
        for nb, ends in g.items():
            tg = set()
            for e in ends:
                if e[0] == '<port>':
                    if e[1] in bus_pt:
                        tg.add('bus:' + e[1])
                elif e[0] in r2c:
                    tg.add('core:' + r2c[e[0]])
            gl = [e[0] for e in ends if e[0] != '<port>' and e[0] not in r2c]
            for e in gl:
                hop[e] |= tg
                nbr.setdefault(e, set()).update(x for x in gl if x != e)
        # registered stations / delay chains (ot_dp_*) pass their partners through (fixed point)
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
        bt = C._bus_targets(SP, tn)
        for h in hcs:
            ci = h['inst']
            ms, pre = mem[ci]
            mine = set('u_' + i.replace('__', '_') for i in ms)
            cx, cy = cent[ci]
            pb = {} if h.get('pins_file') else pins_by_mod.setdefault(h['module'], {})   # reuse-closed: conns only
            sc = score.setdefault(h['module'], {})
            cc = conns.setdefault(tn, {}).setdefault(ci, {})
            for ri in sorted(mine):
                mod, pm = net.insts[ri]
                pi = next(i for i in ms if 'u_' + i.replace('__', '_') == ri)
                rn = rel(pi, pre, h)
                for p, e in pm.items():
                    bs = net.bits(e)
                    n = len(bs)
                    for k, nb in enumerate(bs):
                        if nb is None:
                            continue
                        ends = g.get(net.find(nb), [])
                        others = [x for x in ends if x[0] not in mine]
                        if not others:
                            continue
                        base = f'{rn}__{p}' if rn else p
                        pb.setdefault(base, set()).add(n - 1 - k)
                        tg = set()
                        for x in others:
                            if x[0] == '<port>':
                                if x[1] in bus_pt:
                                    tg.add('bus:' + x[1])
                            elif x[0] in r2c:
                                tg.add('core:' + r2c[x[0]])
                            elif x[0] in chain or len(hop.get(x[0], ())) <= HOP_MAX:
                                tg |= hop.get(x[0], set())   # through a station chain / a small glue leaf
                        tg.discard('core:' + ci)
                        if CLKRST.match(p):   # clock taps / reset spine: no data partner
                            tg = set()
                        if tg:
                            cc.setdefault(base, set()).update(tg)
            # partner directions (type frame) per pin group, for the face / orient choice below
            if h.get('pins_file'):
                continue
            rec = {}
            for base in pb:
                dirs = []
                for v in cc.get(base, ()):
                    k_, _, nm = v.partition(':')
                    q = bt.get(nm, (None, None))[1] if k_ == 'bus' else cent.get(nm)
                    if q is None:
                        continue
                    d = math.hypot(q[0] - cx, q[1] - cy)
                    if d > 1e-6:
                        dirs.append(((q[0] - cx) / d, (q[1] - cy) / d))
                if not dirs:            # no positioned partner: toward the type centre, tiny weight
                    d = math.hypot(W / 2 - cx, H / 2 - cy) or 1
                    dirs = [((W / 2 - cx) / d * 1e-3, (H / 2 - cy) / d * 1e-3)]
                rec[base] = dirs
            insts_by_mod.setdefault(h['module'], []).append((tn, ci, rec))
        stats[tn] = len(hcs)
    # place pins per module
    outl = {}
    for t in types.values():
        for h in t.get('hard_cores', []):
            outl[h['module']] = h['outline_um']
    (out / 'cores').mkdir(parents=True, exist_ok=True)
    files = {}
    patch = {}
    for mod, pb in pins_by_mod.items():
        cw, ch = outl[mod]
        face_of, orients = choose(pb, insts_by_mod[mod])
        face_of = balance(pb, insts_by_mod[mod], orients, face_of, cw, ch)
        for (tn, ci, _), o in zip(insts_by_mod[mod], orients):
            patch.setdefault(tn, {})[ci] = dict(orient=o, pins_file=f'cores/{mod}_pins.json')
        pins = []
        rep = {}
        for f in 'NSEW':
            grp = [(b, bit) for b in sorted(pb) if face_of[b] == f for bit in sorted(pb[b])]
            if not grp:
                continue
            L = cw if f in 'NS' else ch
            lay = ['M5', 'M7'] if f in 'NS' else ['M4', 'M6']
            ntr = {l: int((L - 2 * KEEP) / PITCH[l]) for l in lay}
            use = [lay[0]] if len(grp) <= ntr[lay[0]] // 2 else lay
            cap = sum(ntr[l] // 2 for l in use)
            assert len(grp) <= cap, (mod, f, len(grp), cap)
            share = [len(grp)] if len(use) == 1 else [round(len(grp) * ntr[use[0]] / (ntr[use[0]] + ntr[use[1]]))]
            if len(use) == 2:
                share.append(len(grp) - share[0])
            k0 = 0
            for l, nl in zip(use, share):
                p_, o_ = PITCH[l], OFFS[l]
                lo = math.ceil((KEEP - o_) / p_)
                hi = math.floor((L - KEEP - o_) / p_)
                for j in range(nl):
                    tr = lo + int((j + 0.5) * (hi - lo + 1) / nl)
                    c = round(o_ + tr * p_, 6)
                    b, bit = grp[k0 + j]
                    if f == 'N':
                        x, y = c, round(ch - 0.096, 6)
                    elif f == 'S':
                        x, y = c, 0.096
                    elif f == 'E':
                        x, y = round(cw - 0.096, 6), c
                    else:
                        x, y = 0.096, c
                    pins.append(dict(name=f'{b}[{bit}]', layer=l, x=x, y=y))
                k0 += nl
            rep[f] = dict(pins=len(grp), layers=use)
        fn = f'cores/{mod}_pins.json'
        json.dump(dict(schema='opentallas.die_plan.core_pins.v1', core=mod, frame=f'core R0, origin (0,0), outline {cw} x {ch}',
                       source='KV-P6-PINS 10-23 top-down pin assignment (core_pins_v37p.py): boundary bits of the bound '
                              'partition netlist (binder3 kv39), face = best facing to partners over all instances, '
                              'even spread on the plan tracks', faces=rep, pins=pins),
                  open(out / fn, 'w'), indent=0)
        files[mod] = fn
        print(mod, len(pins), rep, file=sys.stderr)
    cj = {tn: {ci: {b: sorted(v) for b, v in ps.items()} for ci, ps in cs.items()} for tn, cs in conns.items()}
    json.dump(cj, open(out / 'core_conns.json', 'w'), separators=(',', ':'), sort_keys=True)
    for tn, mv in moves.items():
        for ci, o in mv.items():
            patch.setdefault(tn, {}).setdefault(ci, {})['origin_um'] = list(o)
    json.dump(patch, open(out / 'cores' / 'core_patch_v37p.json', 'w'), indent=1, sort_keys=True)


if __name__ == '__main__':
    sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'tools/die_plan'))
    import check as C
    import schema as S
    SP = S.Plan(json.load(open(sys.argv[1])))
    main()
