#!/usr/bin/env python3
"""HBM-ARCH B2 r2: hard cores with pins (G0C) -- the step after gen_arch.py / finalize.py.

B2 r1 listed every as-built block as one hard core with no pins (G0C hard_cores 208 = 'no pins listed'), including
over-cap masters (idx score quarter 3.1M per slice, SU pgslice 2.4M, SFU split3 1.4M, hc bankq 0.84M, tkm 6.6M, hc root
1.5M) and tiny glue (1-cell or-gates).  r2 rebuilds hard_cores[] of every type from measured evidence:

  * over-cap masters -> the measured CORE-HBM / HBM-P4 split pieces (hbm/over_cap_split/<master>.split.json, every
    piece <= 350k cells).  A master that B2 slices over k partitions (contents note '(1/k slice)') gets its pieces dealt
    to the k partitions in piece order (SFU 19 -> 5/5/5/4, IDX score 66 -> 17/17/16/16, pgslice 23 -> 12/11 ...).
    SU pgslice __pv2/__pv6 (exp quadrant) use the pv0 split, __pv10/__pv14 (plain) the pv8 split (same RTL, quad strap).
  * blocks that are d4g hard cores keep that module (outline + pin names from the d4g plan pins_file).
  * the SM slot = 8 x 2 hnx_rp3lp3x lane tiles, each hardened as two halves (HNX-SM4P: hnx_rp3lp3h_n 630.72 x 1209.6
    over hnx_rp3lp3h_s 630.72 x 1036.8) -> 32 cores with their kit pins (physical/hbm_next/sm4/*_pins.tcl, exact).
  * anything else (as-built glue / small leaves with no hardened view, all < 50k cells) is a SOFT placed leaf:
    contents[].origin_um / outline_um (a G2 blockage), not a hard core -- as on the d4g plan.
Every hard core and soft leaf is packed in its type outline (shelf packer on the 8.64 lattice, 8.64 halo).  contents[]
get origin/outline (a split master's content = the bounding box of its pieces), so the G2 partition probe sees the
leaf blockages (r1 had none).

Pins (written to B2/cores/<module>__<W>x<H>.json, core R0 frame): every core pin is re-placed on the plan tracks
(E/W faces M4 y = 0.024 + 0.048k, N/S faces M5 x = 0.024 + 0.048k minus the core M5 PG-stripe band x mod 4.32 in
(1.992, 2.328) [CORE-HBM-REPIN], 2.16-um corner keep-out, <= 4.35 pins/um spread evenly).  Face per port:
  1. census connectivity (r18h5 rows src.bus -> dst.bus, quadrants folded SW->NW / SE->NE as gen_arch does): the port
     faces its partner -- a content in the same partition (its centre), or the partition bus whose lane reaches the
     partner partition (its face window, check._bus_targets).  These ports go to core_conns.json, so check.py
     core_faces scores them.
  2. otherwise the port keeps its d4g face (connectivity unknown: piece-internal netcut names; WARN 'unchecked').
  A full face spills its weakest-pull ports to the adjacent face with room.  SM halves keep the kit pin tables.

    python3 cores_b2.py B2/die_plan.json --out B2r2      (writes B2r2/die_plan.json, cores/, core_conns.json, cores_b2.json)
"""
import argparse, collections, copy, glob, gzip, json, math, os, re, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools', 'die_plan'))
import schema as S        # noqa: E402
import check as CK        # noqa: E402

D4G = os.path.join(HERE, '..', 'hbm')
G = 8.64
HALO = 8.64
PITCH, OFF, INSET, KEEP = 0.048, 0.024, 0.019, 2.16
PG_PITCH, PG_BLK = 4.32, (1.992, 2.328)
CAP = 4.35
OPP = dict(N='S', S='N', E='W', W='E')
NORM = dict(N=(0, 1), S=(0, -1), E=(1, 0), W=(-1, 0))
ADJ = dict(N='EW', S='EW', E='NS', W='NS')
PV_SPLIT = {'ot_hbm_su_static_pgslice_lg__pv2': 'ot_hbm_su_static_pgslice_lg__pv0',
            'ot_hbm_su_static_pgslice_lg__pv6': 'ot_hbm_su_static_pgslice_lg__pv0',
            'ot_hbm_su_static_pgslice_lg__pv10': 'ot_hbm_su_static_pgslice_lg__pv8',
            'ot_hbm_su_static_pgslice_lg__pv14': 'ot_hbm_su_static_pgslice_lg__pv8'}
SM_MOD = 'hnx_sm_p3_rp3lp3x_8x2'
HALVES = {'hnx_rp3lp3h_n': (630.72, 1209.6), 'hnx_rp3lp3h_s': (630.72, 1036.8)}
HNX_REF = 'origin/claude/hnx-sm4p-1020'
SOFT_MAX = 100000
ALT_PV8 = (760.32, 725.76)    # same area as the d4g q_su2 outline 587.52 x 933.12 (0.548 mm2), aspect 1.05      # a non-d4g-core block above this many cells would need a hardened view (none in B2)


def snap(v):
    return math.ceil(v / G - 1e-9) * G


# ------------------------------------------------------------------------------------------------- evidence
def d4g_cores():
    """module -> (outline, pins_file abs) from the d4g plan (prefer pins_plan_v3 > pins_plan > pins)."""
    p = json.load(open(os.path.join(D4G, 'die_plan.json')))
    rank = lambda f: 0 if 'pins_plan_v3' in f else 1 if 'pins_plan/' in f else 2
    out = {}
    for t in p['partition_types'].values():
        for c in t.get('hard_cores', []):
            f = c.get('pins_file')
            if not f:
                continue
            cur = out.get(c['module'])
            if cur is None or rank(f) < rank(cur[1]):
                out[c['module']] = (tuple(c['outline_um']), f)
    return {m: (o, os.path.join(D4G, f)) for m, (o, f) in out.items()}


def splits():
    out = {}
    for f in glob.glob(os.path.join(D4G, 'over_cap_split', '*.split.json')):
        d = json.load(open(f))
        out[d['master']] = d
    return out


def read_pins(f):
    js = json.load(open(f))
    js = js.get('pins', js) if isinstance(js, dict) else js
    return [(q.get('name') or f"{q['bus']}[{q.get('bit', 0)}]", q['layer'], q['x'], q['y']) for q in js]


def halves_pins():
    out = {}
    for h, (w, hh) in HALVES.items():
        txt = subprocess.run(['git', '-C', ROOT, 'show', f'{HNX_REF}:physical/hbm_next/sm4/{h}_pins.tcl'],
                             capture_output=True, text=True, check=True).stdout
        pins = []
        for m in re.finditer(r'-pin_name \{([^}]+)\} -layer (M\d) -location \{([\d.]+) ([\d.]+)\}', txt):
            pins.append((m.group(1), m.group(2), float(m.group(3)), float(m.group(4))))
        # kit pins sit on the platform M4/M5 tracks (offset 0.012); move each to the nearest plan symmetric track
        # (offset 0.024, pitch 0.048) along its edge, as pins_plan_v2 'repin' (the hnx kits are not closed yet)
        used, snapped = set(), []
        for nm, ln, x, y in pins:
            v = y if ln in ('M4', 'M6') else x
            k = round((v - OFF) / PITCH)
            for d in (0, 1, -1, 2, -2, 3, -3):
                key = (ln, x if ln in ('M4', 'M6') else y, k + d)
                if key not in used:
                    used.add(key); k += d; break
            a = round(OFF + k * PITCH, 4)
            snapped.append((nm, ln, x, a) if ln in ('M4', 'M6') else (nm, ln, a, y))
        out[h] = snapped
    return out


def base(n):
    return re.sub(r'\[\d+\]$', '', n)


def bitk(n):
    m = re.match(r'^(.*)\[(\d+)\]$', n)
    return (m.group(1), int(m.group(2))) if m else (n, -1)


def face_of(x, y, w, h):
    return min([(x, 'W'), (w - x, 'E'), (y, 'S'), (h - y, 'N')])[1]


# ------------------------------------------------------------------------------------------------- pin placement
LAY2 = dict(M6=(0.064, 0.032), M7=(0.064, 0.032))
CAP2 = 6.0 - CAP          # second pin layer (M6 E/W, M7 N/S) up to the CORE-HBM hard cap 6.0 pins/um
SLACK = 1.3              # grown cores: perimeter capacity >= 1.3 x pins, so connected ports can take their face


def tracks(L, vert, layer=None):
    p, o = LAY2[layer] if layer else (PITCH, OFF)
    k0 = math.ceil((KEEP - o) / p - 1e-9)
    k1 = math.floor((L - KEEP - o) / p + 1e-9)
    out = []
    for k in range(k0, k1 + 1):
        a = round(o + k * p, 4)
        if vert and not layer and PG_BLK[0] < (a % PG_PITCH) < PG_BLK[1]:
            continue
        out.append(a)
    return out


def face_caps(f, w, h):
    L = w if f in 'NS' else h
    c1 = min(len(tracks(L, f in 'NS')), int(CAP * max(0.0, L - 2 * KEEP)))
    c2 = min(len(tracks(L, f in 'NS', 'M7' if f in 'NS' else 'M6')), int(CAP2 * max(0.0, L - 2 * KEEP)))
    return c1, c2


def face_cap(f, w, h):
    return sum(face_caps(f, w, h))


def place_pins(groups, w, h):
    """groups: [(port, [pin names], face, pull{face: score})] -> pins, {port: majority face}.  Greedy per pin: groups
    with the strongest pull first; a full face spills the rest of a bus to the next face by pull (adjacent first)."""
    cap = {f: face_cap(f, w, h) for f in 'NSEW'}
    if sum(len(g[1]) for g in groups) > sum(cap.values()):
        raise ValueError(f'perimeter full: {sum(len(g[1]) for g in groups)} pins > {sum(cap.values())} on {w}x{h}')
    load = collections.Counter()
    on = collections.defaultdict(list)
    gf = {}
    blind = lambda g: len(g[3]) == 1 and abs(list(g[3].values())[0] - 0.01) < 1e-9
    # connected ports first (smallest first, so a bus that must spill is a big one with most pins still facing);
    # spill faces by pull (mean cos to the partners); blind ports (d4g face kept) fill what is left
    for port, names, f, pull in sorted(groups, key=lambda g: (blind(g), len(g[1]))):
        if blind((port, names, f, pull)):
            order = [f] + sorted((x for x in 'NSEW' if x != f), key=lambda x: (x not in ADJ[f], load[x] - cap[x]))
        else:
            order = sorted('NSEW', key=lambda x: -pull.get(x, -1))
        cnt = collections.Counter()
        for nm in sorted(names, key=bitk):
            for x in order:
                if load[x] < cap[x]:
                    load[x] += 1; on[x].append(nm); cnt[x] += 1
                    break
        gf[port] = cnt.most_common(1)[0][0]
    out = []
    for f in 'NSEW':
        names = on[f]
        if not names:
            continue
        L = w if f in 'NS' else h
        c1, _ = face_caps(f, w, h)
        for names_, lay in ((names[:c1], None), (names[c1:], 'M7' if f in 'NS' else 'M6')):
            n = len(names_)
            if not n:
                continue
            tr = tracks(L, f in 'NS', lay)
            idx = [int(round(i * (len(tr) - 1) / max(1, n - 1))) if n > 1 else len(tr) // 2 for i in range(n)]
            for nm, k in zip(names_, idx):
                a = tr[k]
                lv = lay or 'M5'
                lh = lay or 'M4'
                if f == 'N':
                    out.append((nm, lv, a, round(h - INSET, 4)))
                elif f == 'S':
                    out.append((nm, lv, a, INSET))
                elif f == 'E':
                    out.append((nm, lh, round(w - INSET, 4), a))
                else:
                    out.append((nm, lh, INSET, a))
    return out, gf


def min_outline(npins, w, h):
    """grow (aspect kept, 4.32 steps) until the perimeter holds npins at CAP."""
    while sum(face_cap(f, w, h) for f in "NSEW") < npins * SLACK:
        w, h = w + 4.32, h + 4.32 * h / w
        h = math.ceil(h / 4.32) * 4.32
    return round(w, 4), round(h, 4)


# ------------------------------------------------------------------------------------------------- packing
def pack(items, W, H, fixed=()):
    """items [(key, w, h)] -> {key: (x, y)} shelf-packed (tallest first) in W x H with HALO; None if no fit."""
    for order in ('h', 'a', 'w'):
        key = dict(h=lambda it: (-it[2], -it[1]), a=lambda it: (-it[1] * it[2],), w=lambda it: (-it[1], -it[2]))[order]
        pos = {}
        x, y, rowh = HALO, HALO, 0.0
        ok = True
        for k, w, h in sorted(items, key=key):
            ws, hs = snap(w), snap(h)
            if x + ws > W - HALO + 1e-6:
                x, y, rowh = HALO, y + rowh + HALO, 0.0
            if x + ws > W - HALO + 1e-6 or y + hs > H - HALO + 1e-6:
                ok = False
                break
            pos[k] = (round(x, 4), round(y, 4))
            x += ws + HALO
            rowh = max(rowh, hs)
        if ok:
            return pos
    return None


def pack_columns(items, W, H):
    """fallback: column packing (fill y first)."""
    pos = {}
    x, y, colw = HALO, HALO, 0.0
    for k, w, h in sorted(items, key=lambda it: (-it[1], -it[2])):
        ws, hs = snap(w), snap(h)
        if y + hs > H - HALO + 1e-6:
            x, y, colw = x + colw + HALO, HALO, 0.0
        if y + hs > H - HALO + 1e-6 or x + ws > W - HALO + 1e-6:
            return None
        pos[k] = (round(x, 4), round(y, 4))
        y += hs + HALO
        colw = max(colw, ws)
    return pos


# ------------------------------------------------------------------------------------------------- census
def census_conn(plan_dir):
    rows = [l.rstrip('\n').split('\t') for l in gzip.open(os.path.join(D4G, 'census', 'hbm_r18h5_rows.tsv.gz'), 'rt')][1:]
    cmap = json.load(open(os.path.join(plan_dir, 'census_map.json')))
    fold = lambda n: re.sub(r'_SW(?=\d|_|$)', '_NW', re.sub(r'_SE(?=\d|_|$)', '_NE', n))
    def parts_of(n):
        n = fold(n)
        if n in cmap['parts']:
            return [cmap['parts'][n]]
        for rx, g in cmap['rules']:
            if re.match(rx, n):
                return cmap['groups'][g]
        return []
    conn = collections.defaultdict(lambda: collections.defaultdict(set))   # asbuilt -> port -> {partner asbuilt}
    for src, sb, dst, db, kind, bits in rows:
        if kind in ('clock', 'reset'):
            continue
        conn[fold(src)][sb].add(fold(dst))
        conn[fold(dst)][db].add(fold(src))
    return conn, parts_of


# ------------------------------------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('plan')
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    src_dir = os.path.dirname(os.path.abspath(a.plan))
    out = os.path.abspath(a.out)
    os.makedirs(os.path.join(out, 'cores'), exist_ok=True)
    plan = json.load(open(a.plan))
    D4 = d4g_cores()
    SP = splits()
    HP = halves_pins()
    conn, parts_of = census_conn(src_dir)
    P0 = S.Plan(plan)
    rep = dict(types={}, pins_files={}, soft=[], unfit=[], spill={}, conn_ports=0, blind_ports=0, cores=0, grown={})

    # share groups: (content inst, module) -> sorted types holding a slice
    share = collections.defaultdict(list)
    for tn, t in plan['partition_types'].items():
        for c in t['contents']:
            m = re.search(r'\(1/(\d+) slice\)', c.get('note', ''))
            if m:
                share[(c['inst'], c['module'])].append(tn)
    asb = {}
    for tn, t in plan['partition_types'].items():
        for c in t['contents']:
            m = re.match(r'as-built (\S+)', c.get('note', ''))
            if m:
                asb[(tn, c['inst'])] = m.group(1)

    pin_tables = {}       # (module, w, h) -> pins

    def pins_for(mod, w, h, groups):
        pins, gf = place_pins(groups, w, h)
        return pins

    core_conns = {}
    for tn, t in plan['partition_types'].items():
        w, h = t['outline_um']
        inst_nw = next(n for n, p in P0.parts.items() if p['type'] == tn and p.get('orient', 'R0') == 'R0') \
            if any(p['type'] == tn and p.get('orient', 'R0') == 'R0' for p in P0.parts.values()) else None
        old = {c['inst']: c for c in t.get('hard_cores', [])}
        cont = {c['inst']: c for c in t['contents']}
        items = []        # (key, w, h, kind, payload)
        if t.get('hard') and any(c['module'] == SM_MOD for c in old.values()):
            new = []
            for col in range(8):
                for row in range(2):
                    for hn, y0 in (('hnx_rp3lp3h_s', 0.0), ('hnx_rp3lp3h_n', 1036.8)):
                        hw, hh = HALVES[hn]
                        new.append(dict(inst=f'u_sm_t{row}{col}_{hn[-1]}', module=hn,
                                        origin_um=[round(col * 630.72, 4), round(row * 2246.4 + y0, 4)],
                                        outline_um=[hw, hh], track_offset_um=[0.0, 0.0],
                                        pins_file=f'cores/{hn}.json',
                                        note='HNX-SM4P hardened half (kit pins exact, physical/hbm_next/sm4)'))
            for hn in HALVES:
                json.dump([dict(name=n, layer=l, x=x, y=y) for n, l, x, y in HP[hn]],
                          open(os.path.join(out, 'cores', f'{hn}.json'), 'w'))
            t['hard_cores'] = new
            cont['u_sm']['origin_um'] = [0.0, 0.0]
            cont['u_sm']['outline_um'] = [w, h]
            cont['u_sm']['note'] += '; hard cores = 16 tiles x (N + S half) = 32 hnx_rp3lp3h kits'
            rep['types'][tn] = dict(cores=32, soft=0)
            rep['cores'] += 32
            continue
        cells_ev = {}
        for ci, hc in old.items():
            c = cont.get(ci, {})
            mod = hc['module']
            master = PV_SPLIT.get(mod, mod)
            if master in SP:
                pieces = SP[master]['cores']
                grp = sorted(share.get((ci, mod), [tn]))
                k, j = len(grp), grp.index(tn)
                n = len(pieces)
                mine = pieces[j * n // k:(j + 1) * n // k] if k > 1 else pieces
                if ci.startswith('u_su_') and k == 2:     # pgslice: deal pieces to the two halves
                    mine = pieces[j::2]
                for pc in mine:
                    pm = f"{SP[master]['master'] if not master.startswith('ot_hbm_su_static_pgslice') else 'ot_hbm_su_static_pgslice_lg'}__{pc['core_label']}"
                    if pm not in D4:
                        raise SystemExit(f'{tn} {ci}: piece {pm} has no d4g pins')
                    (pw, ph), pf = D4[pm]
                    if master.endswith('pgslice_lg__pv8') and (pw, ph) == (587.52, 933.12):
                        pw, ph = ALT_PV8
                    items.append((f'{ci}_{pc["core_label"]}', pw, ph, 'core', dict(module=pm, src=pf, cells=pc['cells'],
                                   parent=ci, note=f'split piece {pc["core_label"]} of {mod} ({master}.split.json)')))
                c['note'] = c.get('note', '') + f'; hard cores = {len(mine)} split pieces of {master}'
                c['cells'] = sum(pc['cells'] for pc in mine)
            elif mod in D4:
                (pw, ph), pf = D4[mod]
                items.append((ci, pw, ph, 'core', dict(module=mod, src=pf, cells=c.get('cells'), parent=ci, note='d4g hard core')))
            else:
                if (c.get('cells') or 0) > SOFT_MAX:
                    raise SystemExit(f'{tn} {ci} {mod}: {c.get("cells")} cells and no hardened view')
                items.append((ci, hc['outline_um'][0], hc['outline_um'][1], 'soft', dict(module=mod)))
        # soft contents without a hard core entry keep no outline (glue)
        if not items:
            t.pop('hard_cores', None)
            continue
        sized = []
        for k, iw, ih, kind, pl in items:
            if kind == 'core':
                npin = len(read_pins(pl['src']))
                if sum(face_cap(f, iw, ih) for f in 'NSEW') < npin:
                    nw, nh = min_outline(npin, iw, ih)
                    rep['grown'][f'{tn}.{k}'] = [iw, ih, nw, nh, npin]
                    iw, ih = nw, nh
            sized.append((k, iw, ih, kind, pl))
        items = sized
        pos = pack([(k, iw, ih) for k, iw, ih, _, _ in items], w, h) or pack_columns([(k, iw, ih) for k, iw, ih, _, _ in items], w, h)
        if pos is None:
            rep['unfit'].append(tn)
            print('UNFIT', tn, w, h, sum(snap(iw) * snap(ih) for _, iw, ih, _, _ in items) / (w * h))
            continue
        geo = {k: (pos[k][0], pos[k][1], snap(iw) if kind == 'soft' else iw, snap(ih) if kind == 'soft' else ih)
               for k, iw, ih, kind, _ in items}
        # contents: origin / outline (split master = bbox of its pieces)
        for ci, c in cont.items():
            mem = [g for k, g in geo.items() if k == ci or k.startswith(ci + '_') and any(it[0] == k and it[4].get('parent') == ci for it in items)]
            if mem:
                x0 = min(g[0] for g in mem); y0 = min(g[1] for g in mem)
                x1 = max(g[0] + g[2] for g in mem); y1 = max(g[1] + g[3] for g in mem)
                c['origin_um'] = [round(x0, 4), round(y0, 4)]
                c['outline_um'] = [round(x1 - x0, 4), round(y1 - y0, 4)]
        # targets for connectivity
        bt = CK._bus_targets(S.Plan(plan), tn)
        bus_lanes = collections.defaultdict(set)     # bus -> partner partitions
        if inst_nw:
            for L in plan['lanes']:
                p0 = P0.ports[L['ports'][0]]; p1 = P0.ports[L['ports'][-1]]
                if p0['src']['part'] == inst_nw:
                    bus_lanes[p0['src']['bus']].add(p1['dst']['part'])
                if p1['dst']['part'] == inst_nw:
                    bus_lanes[p1['dst']['bus']].add(p0['src']['part'])
        by_asb = {asb[(tn, ci)]: ci for ci in cont if (tn, ci) in asb}
        new_hc = []
        tconn = {}
        for k, iw, ih, kind, pl in items:
            if kind == 'soft':
                rep['soft'].append(f'{tn}.{k}')
                continue
            x0, y0 = geo[k][0], geo[k][1]
            cx, cy = x0 + iw / 2, y0 + ih / 2
            src_pins = read_pins(pl['src'])
            ow, oh = D4[pl['module']][0]
            ports = collections.OrderedDict()
            for nm, ln, px, py in src_pins:
                ports.setdefault(base(nm), []).append((nm, face_of(px, py, ow, oh)))
            ab = asb.get((tn, pl['parent'])) if k == pl['parent'] else None
            groups = []
            pconn = {}
            for port, lst in ports.items():
                names = [x[0] for x in lst]
                f0 = collections.Counter(x[1] for x in lst).most_common(1)[0][0]
                tg = []
                if ab and port in conn.get(ab, {}) and inst_nw:
                    for partner in conn[ab][port]:
                        pps = parts_of(partner)
                        if inst_nw in pps and partner in by_asb and by_asb[partner] != k:
                            tg.append(('leaf', by_asb[partner]))
                        else:
                            for b, others in bus_lanes.items():
                                if set(pps) & others and b in bt:
                                    tg.append(('bus', b))
                pts = []
                for kd, nm in sorted(set(tg)):
                    if kd == 'bus':
                        pts.append(bt[nm][1])
                    else:
                        c2 = cont[nm]
                        if 'origin_um' in c2:
                            pts.append((c2['origin_um'][0] + c2['outline_um'][0] / 2, c2['origin_um'][1] + c2['outline_um'][1] / 2))
                dirs = []
                for tx, ty in pts:
                    d = math.hypot(tx - cx, ty - cy)
                    if d > 1e-6:
                        dirs.append(((tx - cx) / d, (ty - cy) / d))
                if dirs:
                    pull = {f: sum(NORM[f][0] * ux + NORM[f][1] * uy for ux, uy in dirs) / len(dirs) for f in 'NSEW'}
                    f = max(pull, key=pull.get)
                    pconn[port] = [f'{kd}:{nm}' for kd, nm in sorted(set(tg))]
                    rep['conn_ports'] += 1
                else:
                    pull = {f0: 0.01}
                    f = f0
                    rep['blind_ports'] += 1
                groups.append((port, names, f, pull))
            cw, ch = iw, ih
            while True:
                try:
                    pins, gf = place_pins(groups, cw, ch)
                    break
                except ValueError:
                    cw, ch = min_outline(sum(len(g[1]) for g in groups), cw + 4.32, ch)
                    rep['grown'][f'{tn}.{k}'] = [iw, ih, cw, ch]
            spills = [p for p, f, *_ in [(g[0], g[2]) for g in groups] if gf[p] != f]
            if spills:
                rep['spill'][f'{tn}.{k}'] = len(spills)
            key = f"{pl['module']}__{cw:g}x{ch:g}__{tn}_{k}" if pconn else f"{pl['module']}__{cw:g}x{ch:g}"
            pf = f'cores/{key}.json'
            if pf not in pin_tables:
                pin_tables[pf] = pins
                json.dump([dict(name=n, layer=l, x=x, y=y) for n, l, x, y in pins], open(os.path.join(out, pf), 'w'))
            new_hc.append(dict(inst=k, module=pl['module'], origin_um=[x0, y0], outline_um=[cw, ch],
                               track_offset_um=[0.0, 0.0], pins_file=pf,
                               note=pl['note'] + (f"; {pl['cells']} cells" if pl.get('cells') else '')))
            if pconn:
                tconn[k] = pconn
            rep['cores'] += 1
        t['hard_cores'] = new_hc
        if not new_hc:
            t.pop('hard_cores')
        if tconn:
            core_conns[tn] = tconn
        rep['types'][tn] = dict(cores=len(new_hc), soft=sum(1 for it in items if it[3] == 'soft'),
                                fill=round(sum(g[2] * g[3] for g in geo.values()) / (w * h), 3))
    # the SM type cell estimate (r1: 1203 placeholder)
    for tn, t in plan['partition_types'].items():
        if any(c['module'] == SM_MOD for c in t['contents']):
            # lower bound: the halves' own std cells only (HNX-SM4P README: 25-30k um2 per half) at the d4g SM ratio
            # 0.116 um2 / cell (native_col 253.5k cells / 29.5k um2); the 18 hard children per half come on top
            t['cells'] = int(32 * 30000 / 0.116)
            t['note'] = ('LOWER BOUND: 32 hnx_rp3lp3h halves x 30k um2 std cells / 0.116 um2 per cell (hard '
                               'children excluded); type over 400k -> built from the 32 half kits as hard cores')
    plan['note'] = plan.get('note', '') + '; r2 cores_b2.py: hard cores = measured split pieces / d4g cores / SM halves, plan-track pins'
    json.dump(plan, open(os.path.join(out, 'die_plan.json'), 'w'), indent=0)
    json.dump(core_conns, open(os.path.join(out, 'core_conns.json'), 'w'), indent=0)
    rep['pins_files'] = len(pin_tables) + len(HALVES)
    json.dump(rep, open(os.path.join(out, 'cores_b2.json'), 'w'), indent=1)
    print(json.dumps({k: v for k, v in rep.items() if k not in ('types', 'soft')}, indent=0)[:3000])
    print('soft leaves', len(rep['soft']))


if __name__ == '__main__':
    main()
