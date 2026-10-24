#!/usr/bin/env python3
"""HBM v2 plan post-pass: planned hard cores, per-type cell budgets, declared clock taps, C0 tree fan-out.

HBM-P3-TAPS 2026-10-23.  G3 prerequisites named in the G1 record (results/geom_review/hbm_plan__hbm__d0b73c621f78.json)
and in GEOM-REVIEW3 07:50 items 2-4.  This pass only ADDS fields to partition types (clock.taps[], hard_cores[], the
type note) and writes plan_notes_v2.json; it never changes partitions, buses, ports, lanes, routing or latency.
It is called at the end of gen_plan_v2.py (one hook line), and can be re-run on a written plan:
    python3 taps_cores_v2.py <plan_dir>        (reads die_plan.json + v2_assign.json, rewrites both outputs)

Rules applied (TOPDOWN-PLAN.md):
  * L1 cap (COORD 06:12): <= 400k std cells per OpenROAD run; partition = glue + stations flattened (<= 400k), each
    planned hard core <= 400k.  Cores here are budgeted at <= 350k Yosys cells (P&R adds buffers/hold cells).
  * Hard cores (COORD 06:01, 08:36; PLAN-TOOL 08:42 schema): origin on the 8.64 lattice, sub-lattice track_offset_um
    so the as-built (platform-track) pins land on the plan tracks in the type frame and under every instance orient.
  * Clock taps (COORD 07:24 (2)): one spine tap per planned core or landed region, taps <= 1.2 mm apart.  Metric:
    Manhattan (L1) distance, because partition clock and data wires are routed H/V.  Every point of the outline is
    within 1200 um L1 of a tap (sampled on the 8.64 lattice), and every tap has a neighbour tap within 1200 um L1.
  * Hard IP (the HBM3E PHY) keeps its own clocking: taps per channel group, no std-cell count.
  * SM quarters (q_sm<k><a..d>, ot_hbm_accel_smh_attn): cores and cells from the HBM-P3-SM four-way split
    (inputs/sm_split_cores.json = snapshot of sm_split/sm_split.json, measured Yosys); outlines EST, no pins.
"""
import collections, json, math, os, re, shutil, sys

G = 8.64                       # die lattice
REACH = 600.0                  # tap grid pitch / coverage, L1 um (COORD R4 10-23: tap grid pitch <= 600 um)
PHY_REACH = 1200.0             # hard IP (HBM3E PHY): per channel-group DFI clock taps
CAP = 400_000
CORE_BUDGET = 350_000          # split target for a core (Yosys cells)
HARDEN_MIN = 20_000            # leaves below this (and without macros) are flattened into the partition glue
GLUE_CELLS_PER_BIT = 2         # boundary / station / fork register bit: 1 flop + ~1 buffer/hold cell (EST)
INS_PS, INS_TOL = 250.0, 40.0
SM_MOD = 'ot_hbm_accel_smh_attn'
# HBM-P5-PINS: the SM synthetic cores lx / tp are real modules now (rtl/hbm_accel/sm/attn/qsplit, lock-step == tile)
SM_WRAP = {'lx': 'ot_hbm_sm_attn_leafh_lx', 'tp': 'ot_hbm_sm_attn_tile_tp'}
HARD_IP = {'ot_hbm3e_phy_rc_e8p5'}
LAYER = {'M2': ('H', 0.036, 0.045), 'M3': ('V', 0.036, 0.009), 'M4': ('H', 0.048, 0.024), 'M5': ('V', 0.048, 0.024),
         'M6': ('H', 0.064, 0.032), 'M7': ('V', 0.064, 0.032), 'M8': ('H', 0.080, 0.040), 'M9': ('V', 0.080, 0.040)}

HERE = os.path.dirname(os.path.abspath(__file__))


def r3(v):
    return round(v + 0.0, 3)


def lat_floor(v):
    return math.floor(v / G + 1e-9) * G


def lat_ceil(v):
    return math.ceil(v / G - 1e-9) * G


# ------------------------------------------------------------------------------------------------ track offset
def _mod(v, p):
    return round(v - p * math.floor(v / p + 1e-9), 4)


def solve_offset(pins, orients):
    """Smallest sub-lattice (dx, dy) on a 0.004-um grid that puts every pin on its plan track, in the type frame and
    in every instance orient (x mirror for MY/R180, y mirror for MX/R180: the plan grid is then needed to be
    mirror-symmetric, offset = pitch/2, which M2/M3 are not).  Returns (dx, dy, bad_layers)."""
    flip_x = any(o in ('MY', 'R180') for o in orients)
    flip_y = any(o in ('MX', 'R180') for o in orients)
    need = {'H': {}, 'V': {}}
    bad = collections.Counter()
    for p in pins:
        L = LAYER.get(p['layer'])
        if L is None:
            continue                                   # M1 / unknown: not checked by G0
        d, pitch, off = L
        if (d == 'V' and flip_x or d == 'H' and flip_y) and abs(2 * off - pitch) > 1e-6:
            bad[p['layer']] += 1
            continue
        c = p['x'] if d == 'V' else p['y']
        need[d].setdefault((pitch, off), set()).add(_mod(c, pitch))
    res = []
    for d in ('V', 'H'):
        best = None
        for k in range(0, 540):                        # 0 .. 2.16 um step 0.004 (all pitches are multiples)
            t = k * 0.004
            if all(all(abs(_mod(ph + t - off, pitch)) < 1e-4 or abs(_mod(ph + t - off, pitch) - pitch) < 1e-4
                       for ph in phs) for (pitch, off), phs in need[d].items()):
                best = round(t, 3)
                break
        if best is None:
            for (pitch, off), phs in need[d].items():
                bad[f'{d}-layer pitch {pitch}'] += 1
            best = 0.0
        res.append(best)
    return res[0], res[1], dict(bad)


# ------------------------------------------------------------------------------------------------ geometry
def grid_split(box, n, min_side=G):
    """Split a lattice box (x0,y0,x1,y1) into n lattice sub-boxes (cols x rows near-square, 8.64 gaps)."""
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    best = None
    for c in range(1, n + 1):
        r = math.ceil(n / c)
        cw, rh = w / c, h / r
        score = abs(math.log(max(cw, 1) / max(rh, 1)))
        if best is None or score < best[0]:
            best = (score, c, r)
    _, c, r = best
    cw = lat_floor((w - (c - 1) * G) / c)
    rh = lat_floor((h - (r - 1) * G) / r)
    out = []
    for i in range(n):
        ci, ri = i % c, i // c
        out.append((x0 + ci * (cw + G), y0 + ri * (rh + G), cw, rh))
    return out


def inside(b, x, y):
    return b[0] <= x <= b[0] + b[2] and b[1] <= y <= b[1] + b[3]


def l1(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def place_taps(w, h, cores, root):
    """Core taps (one per core, at the core centre) + glue taps on a <= 1.2 mm grid where cores do not cover."""
    taps = []
    for c in cores:
        x, y = c['_box'][0] + c['_box'][2] / 2, c['_box'][1] + c['_box'][3] / 2
        taps.append(dict(name=f"{c['inst']}.ck", xy=[r3(x), r3(y)], kind='core', orient=c.get('orient', 'R0'),
                         insertion_ps=INS_PS, insertion_tol_ps=INS_TOL,
                         budget_owner=f"core CTS {c['module']} (insertion below the core ck pin)",
                         from_root_um=r3(l1((x, y), root))))
    nx, ny = max(1, math.ceil(w / REACH)), max(1, math.ceil(h / REACH))
    sx, sy = w / nx, h / ny
    for j in range(ny):
        for i in range(nx):
            cx, cy = (i + 0.5) * sx, (j + 0.5) * sy
            pts = [(i * sx + a * sx, j * sy + b * sy) for a in (0, 0.5, 1) for b in (0, 0.5, 1)]
            if all(any(inside(c['_box'], *p) for c in cores) for p in pts):
                continue                                # region fully inside hard cores: their taps clock it
            cx, cy = off_core(cx, cy, w, h, cores)
            if l1((cx, cy), root) < 1.0:
                continue                                # the type's root tap (clock.tap_um) is already here
            taps.append(glue_tap(f'g{i}_{j}.ck', cx, cy, root))
    k = 0
    while True:                                         # refine: no lattice point farther than REACH from a tap
        worst, wp = tap_worst(w, h, taps, step=1, cores=cores)   # P4: step 1 (the metric's grid): 8.64-um channels
        if worst <= REACH or k > 400:
            break
        cx, cy = off_core(*wp, w, h, cores)
        taps.append(glue_tap(f'gr{k}.ck', cx, cy, root))
        k += 1
    for b in range(64):                                 # P4: bridge taps until the <= REACH tap graph is connected
        pts = [t['xy'] for t in taps]
        seen, todo = {0}, [0]
        while todo:
            a_ = todo.pop()
            for j in range(len(pts)):
                if j not in seen and l1(pts[a_], pts[j]) <= REACH:
                    seen.add(j); todo.append(j)
        if len(seen) == len(pts):
            break
        i, j = min(((i, j) for i in seen for j in range(len(pts)) if j not in seen),
                   key=lambda ij: l1(pts[ij[0]], pts[ij[1]]))
        mx, my = (pts[i][0] + pts[j][0]) / 2, (pts[i][1] + pts[j][1]) / 2
        cx, cy = off_core(mx, my, w, h, cores)
        if l1((cx, cy), pts[i]) > REACH or l1((cx, cy), pts[j]) > REACH:
            cx, cy = mx, my                             # bridge inside a core's halo: keep the midpoint
        taps.append(glue_tap(f'gb{b}.ck', cx, cy, root))
    return taps


def glue_tap(name, x, y, root):
    return dict(name=name, xy=[r3(x), r3(y)], kind='glue', orient='R0', insertion_ps=INS_PS, insertion_tol_ps=INS_TOL,
                budget_owner='partition glue CTS (landed region: boundary flops, stations, glue)',
                from_root_um=r3(l1((x, y), root)))


def off_core(cx, cy, w, h, cores):
    """move a glue tap that falls on a hard core just outside it (nearest core edge + 8.64)"""
    boxes = [c['_box'] for c in cores if inside(c['_box'], cx, cy)]
    if not boxes:
        return cx, cy
    b = boxes[0]
    cand = [(b[0] - G, cy), (b[0] + b[2] + G, cy), (cx, b[1] - G), (cx, b[1] + b[3] + G)]
    cand = [p for p in cand if 0 <= p[0] <= w and 0 <= p[1] <= h and not any(inside(c['_box'], *p) for c in cores)]
    return min(cand, key=lambda p: l1(p, (cx, cy))) if cand else (cx, cy)


def tap_worst(w, h, taps, step=3, cores=()):
    """worst L1 distance from a glue lattice point to its nearest tap.  Points inside a hard core are skipped: the
    core's own CTS clocks them from its core tap (R4 covers the partition glue / landed region)."""
    pts = [t['xy'] for t in taps]
    boxes = [c['_box'] for c in cores]
    worst, wp = -1.0, None
    xs = [min(i * G, w) for i in range(0, int(w // G) + 1, step)] + [w]
    ys = [min(j * G, h) for j in range(0, int(h // G) + 1, step)] + [h]
    for x in xs:
        for y in ys:
            if boxes and any(inside(b, x, y) for b in boxes):
                continue
            d = min(abs(x - q[0]) + abs(y - q[1]) for q in pts) if pts else 1e9
            if d > worst:
                worst, wp = d, (x, y)
    return worst, wp


def tap_metrics(w, h, taps, cores=()):
    if not taps:
        return None
    pts = [t['xy'] for t in taps]
    cov, _ = tap_worst(w, h, taps, step=1, cores=cores)
    nn = 0.0
    if len(pts) > 1:
        nn = max(min(l1(p, q) for q in pts if q is not p) for p in pts)
    # connectivity of the <= REACH tap graph
    seen, todo = {0}, [0]
    while todo:
        a = todo.pop()
        for b in range(len(pts)):
            if b not in seen and l1(pts[a], pts[b]) <= REACH:
                seen.add(b); todo.append(b)
    return dict(n=len(pts), max_point_to_tap_um=round(cov, 1), max_nn_tap_um=round(nn, 1),
                connected=len(seen) == len(pts))


# ------------------------------------------------------------------------------------------------ main pass
def load_blocks(ft):
    m = {}
    for line in open(os.path.join(ft, 'dumps', 'dump-hbm', 'blocks.tsv')):
        f = line.rstrip('\n').split('\t')
        m[f[0]] = f[1]
    return m


def apply(plan, out_dir, where, ft=None):
    ft = ft or os.path.join(HERE, 'inputs')
    ev_all = json.load(open(os.path.join(HERE, 'inputs', 'cells_evidence.json')))
    EV, SPL = ev_all['masters'], ev_all['splits']
    SM = json.load(open(os.path.join(HERE, 'inputs', 'sm_split_cores.json')))
    blocks = load_blocks(ft)
    types = plan['partition_types']
    parts_of = collections.defaultdict(list)
    for p in plan['partitions']:
        parts_of[p['type']].append(p)
    ptype = {p['name']: p['type'] for p in plan['partitions']}
    # as-built masters per (type, base module); representative = canonical (NW / C0) partition instance
    masters = collections.defaultdict(list)
    for n, pn in sorted(where.items()):
        mst = blocks.get(n)
        if mst is None or pn not in ptype:
            continue
        masters[(ptype[pn], re.sub(r'__pv\d+$', '', mst))].append((not pn.startswith(('NW_', 'C0')), pn, mst))
    notes = dict(scope='HBM-P3-TAPS post-pass (taps_cores_v2.py); plan stage only, no P&R claim',
                 cap_cells=CAP, core_budget_cells=CORE_BUDGET, harden_min_cells=HARDEN_MIN,
                 glue_cells_per_bit=GLUE_CELLS_PER_BIT, tap_metric='L1 (Manhattan) um', tap_reach_um=REACH,
                 a_cell_um2=ev_all['a_cell_um2'], types={}, over_cap=[], pins_files=[])
    pins_used = set()
    pp_used = set()
    OCS = {}                                            # (type, module) -> measured split (over_cap_split/)
    oci = os.path.join(HERE, 'over_cap_split', 'index.json')
    if os.path.exists(oci):
        for mst, e in json.load(open(oci))['masters'].items():
            sp = json.load(open(os.path.join(HERE, 'over_cap_split', e['file'])))
            sp['_file'] = e['file']
            for tn_ in e.get('plan_types', []):
                OCS[(tn_, re.sub(r'__pv\d+$', '', mst))] = sp
    ppi = os.path.join(HERE, 'cores', 'pins_plan', 'index.json')
    PP = ({k: v['file'] for k, v in json.load(open(ppi))['done'].items()} if os.path.exists(ppi) else {})
    for tn in sorted(types):
        t = types[tn]
        w, h = t['outline_um']
        orients = sorted({p['orient'] for p in parts_of[tn]})
        root = t['clock']['tap_um']
        is_sm = tn.startswith('q_sm')
        busw = {b['name']: b['width'] for b in t['buses']}
        glue = dict(boundary_bits=sum(busw.values()),
                    station_bits=sum(s['width'] * s.get('stations', 1) for s in t.get('ft_slots', [])))
        glue['fork_bits'] = 0
        flat, cores, rows = [], [], []
        if is_sm:                                       # SM quarter: cores from the HBM-P3-SM split (measured Yosys)
            q = re.match(r'q_sm\d([abcd])', tn).group(1)
            sq = SM['quarters'][q]
            m_ = 4 * G
            box = (m_, m_, lat_floor(w - m_), lat_floor(h - m_))
            for i, ((sx, sy, sw, sh), sc) in enumerate(zip(grid_split(box, len(sq['cores'])), sq['cores'])):
                cores.append(dict(inst=f"sm_{sc['role']}{i}", module=SM_WRAP.get(sc['role'], sc['module'].split(' ')[0]),
                                  origin_um=[r3(sx), r3(sy)], outline_um=[r3(sw), r3(sh)], orient='R0',
                                  track_offset_um=[0.0, 0.0],
                                  note=f"SM quarter {q} core {sc['name']} ({sc['module']}): {sc['cells']} cells "
                                       f"{sc['label']} (sm_split); outline EST (grid of the quarter)"
                                       + (f"; wrapper RTL {SM_WRAP[sc['role']]} (rtl/hbm_accel/sm/attn/qsplit)"
                                          if sc['role'] in SM_WRAP else ''),
                                  _cells=sc['cells'], _box=(sx, sy, sw, sh)))
            flat.append(dict(inst='sm_glue', module=f"SM quarter {q} glue ({sq['glue_note']})",
                             cells=sq['glue_cells'], basis='sm_split glue_cells_with_relays_est', macros=0))
        for c in t['contents']:
            if c['status'] == 'new':
                if c['module'] == 'hbm_ft_fork_reg':
                    stem = c['inst'][3:]
                    glue['fork_bits'] += max([wd for nm, wd in busw.items() if nm.startswith(stem)] or [0])
                continue
            if c['module'] == SM_MOD:
                continue
            cand = sorted(masters.get((tn, c['module']), []))
            mst = cand[0][2] if cand else c['module']
            evs = [EV[m_] for _, _, m_ in cand if m_ in EV] or ([EV[c['module']]] if c['module'] in EV else [])
            ev = max(evs, key=lambda e: e['cells'] or 0) if evs else None
            cells = ev['cells'] if ev else None
            basis = ev['basis'] if ev else 'NONE'
            macros = sum((ev or {}).get('macros', {}).values()) if ev else 0
            rec = dict(inst=c['inst'], module=c['module'], status=c['status'], master=mst, cells=cells,
                       basis=basis, macros=macros)
            if c['module'] in HARD_IP:
                rec['hard_ip'] = True
                rows.append(rec)
                continue
            if cells is not None and cells < HARDEN_MIN and not macros:
                flat.append(rec)
                continue
            ox, oy = c['origin_um']
            cw, ch = c['outline_um']
            if cells is not None and cells > CAP:
                # ---------------- split proposal: sub-cores tile the leaf's lattice box
                box = (lat_ceil(ox), lat_ceil(oy), lat_floor(ox + cw), lat_floor(oy + ch))
                if c['module'] == 'ot_hbm_su_static_pgslice_lg':
                    key = ('ot_hbm_su_static_pgslice_lg__exp' if any(re.search(r'__pv[0-7]$', m_) for _, _, m_ in cand)
                           else 'ot_hbm_su_static_pgslice_lg__plain')
                else:
                    key = c['module'] if c['module'] in SPL else None
                groups = []
                osp = OCS.get((tn, c['module'])) or OCS.get((re.sub(r'_v\d+$', '', tn), c['module']))   # P6: new _vN variants of a split type
                if osp:                                     # P4: measured connectivity split (HBM-P4-SPLIT)
                    groups = [(cr['core_label'], cr['cells'],
                               f"{cr['module']} ({cr['cells']} Yosys; {osp['status']})") for cr in osp['cores']]
                    sub_glue = osp.get('glue_cells') or 0
                    sbasis = f"YOSYS {osp['basis']}"
                    snote = (f"over_cap_split/{osp['_file']} {osp['status']}: {len(groups)} cores by connectivity, "
                             f"max {max(g[1] for g in groups)}")
                elif key:
                    sp = SPL[key]
                    for nm, n, each in sp['parts']:
                        per = max(1, CORE_BUDGET // each) if each <= CORE_BUDGET else 0
                        if per:
                            for g0 in range(0, n, per):
                                k = min(per, n - g0)
                                groups.append((f'{nm}{g0}' + (f'_{g0 + k - 1}' if k > 1 else ''), k * each,
                                               f'{k} x {nm} {each} (Yosys hierarchy)'))
                        else:                                       # one child itself over budget: halve it again
                            m2 = math.ceil(each / CORE_BUDGET)
                            for g0 in range(n):
                                for s in range(m2):
                                    groups.append((f'{nm}{g0}_s{s}', math.ceil(each / m2),
                                                   f'{nm} {each} / {m2} (child over the 350k budget: RTL split of '
                                                   f'its stages needed)'))
                    sub_glue = sp['glue']
                    sbasis = f"YOSYS hierarchy {sp['stat']}"
                    snote = sp['note']
                else:
                    n = math.ceil(cells / CORE_BUDGET)
                    groups = [(f'part{i}', math.ceil(cells / n), f'1/{n} of {c["module"]} (EST equal split)')
                              for i in range(n)]
                    sub_glue = 0
                    sbasis = basis
                    snote = (f'no module hierarchy available (synthesis .stat not kept): equal {n}-way split by '
                             f'area is a PROPOSAL; the RTL owner partitions it into {n} cores of <= 350k'
                             + (f'; its {macros} SRAM macros go with the sub-cores' if macros else ''))
                subs = grid_split(box, len(groups))
                for (nm, cc, why), (sx, sy, sw, sh) in zip(groups, subs):
                    cores.append(dict(inst=f"{c['inst']}_{nm}", module=f"{c['module']}__{nm}", origin_um=[r3(sx), r3(sy)],
                                      outline_um=[r3(sw), r3(sh)], orient='R0', track_offset_um=[0.0, 0.0],
                                      note=f'SPLIT PROPOSAL of {c["module"]} ({cells} cells > cap): {why}; '
                                           f'pins derived from the partition plan at G3', _cells=cc, _box=(sx, sy, sw, sh)))
                if sub_glue:
                    flat.append(dict(inst=c['inst'] + '_glue', module=c['module'] + ' (top + pinned banks)',
                                     cells=sub_glue, basis=sbasis, macros=macros))
                notes['over_cap'].append(dict(type=tn, inst=c['inst'], module=c['module'], master=mst, cells=cells,
                                              basis=basis, split_into=len(groups),
                                              max_sub_core=max(g[1] for g in groups), proposal=snote))
                rec.update(split=len(groups))
                rows.append(rec)
                continue
            # ---------------- one hard core = the as-built leaf
            X = min(max(0.0, round(ox / G) * G), lat_floor(w - cw - 0.2))
            Y = min(max(0.0, round(oy / G) * G), lat_floor(h - ch - 0.2))
            pins_path = os.path.join(HERE, 'cores', 'pins', f'{mst}.json')
            core = dict(inst=c['inst'], module=c['module'], origin_um=[r3(X), r3(Y)], outline_um=[cw, ch],
                        orient='R0', _cells=cells, _box=(X, Y, cw, ch))
            if os.path.exists(pins_path):
                pins = json.load(open(pins_path))
                dx, dy, bad = solve_offset(pins, orients)
                core['track_offset_um'] = [dx, dy]
                if bad:
                    core['note'] = (f'as-built {mst}: {sum(bad.values())} pins on {sorted(bad)} cannot land on the '
                                    'plan tracks under the mirrored instances (plan M2/M3 grids are not '
                                    'mirror-symmetric): re-pin to M4/M5 at G3; pins_file omitted')
                else:
                    core['pins_file'] = f'cores/pins/{mst}.json'
                    pins_used.add(mst)
                    core['note'] = f'as-built pins of {mst} (r18h5 view LEF), platform tracks + offset'
            else:
                core['track_offset_um'] = [0.012, 0.012]
                core['note'] = f'no as-built LEF kept for {mst}; pins from the partition plan at G3'
            core['note'] += f'; cells {cells} ({basis.split(" ")[0]})'
            cores.append(core)
            rows.append(rec)
        # ---------------- budgets
        glue_cells = GLUE_CELLS_PER_BIT * (glue['boundary_bits'] + glue['station_bits'] + glue['fork_bits'])
        flat_cells = sum(f['cells'] or 0 for f in flat)
        core_cells = [c['_cells'] for c in cores if c.get('_cells') is not None]
        tinfo = dict(outline_um=[w, h], instances=len(parts_of[tn]), orients=orients,
                     glue_cells=glue_cells + flat_cells, glue_regs_cells=glue_cells, glue_flat_leaf_cells=flat_cells,
                     glue_basis=(f'EST {GLUE_CELLS_PER_BIT} cells/bit x (boundary {glue["boundary_bits"]} + station '
                                 f'{glue["station_bits"]} + fork {glue["fork_bits"]} bits) + flattened leaves'),
                     n_cores=len(cores), core_cells_max=max(core_cells) if core_cells else 0,
                     core_cells_total=sum(core_cells), cores=[dict(inst=c['inst'], module=c['module'],
                                                                   cells=c.get('_cells')) for c in cores],
                     flattened=[dict(inst=f['inst'], module=f['module'], cells=f['cells']) for f in flat],
                     leaves=rows)
        if is_sm:
            tinfo.update(sm_split=SM['source_sha256'], note='SM quarter of ot_hbm_accel_smh_attn: cores and cells '
                                                             'from physical/die_plan/hbm/sm_split (HBM-P3-SM)')
        # ---------------- taps
        need = (w + h) / 2 > REACH or len(cores) > 1 or t.get('hard')
        taps = []
        if t.get('hard'):                               # hard IP: per channel-group taps along the PHY
            n = max(1, math.ceil(w / (2 * PHY_REACH - h)))
            n = max(n, math.ceil(w / PHY_REACH))
            for i in range(n):
                x = (i + 0.5) * w / n
                taps.append(dict(name=f'ch{i}.ck', xy=[r3(x), r3(h / 2)], kind='leaf', orient='R0',
                                 insertion_ps=INS_PS, insertion_tol_ps=INS_TOL,
                                 budget_owner='HBM3E PHY hard IP (DFI clock per channel group)',
                                 from_root_um=r3(l1((x, h / 2), root))))
        elif need:
            taps = place_taps(w, h, cores, root)
        if taps:
            t['clock']['taps'] = taps
        tinfo['taps'] = tap_metrics(w, h, taps, cores=[] if t.get('hard') else cores)
        tinfo['taps_kinds'] = dict(collections.Counter(tp['kind'] for tp in taps))
        # ---------------- overlap audit of the cores
        ov = 0
        bx = [c['_box'] for c in cores]
        for i in range(len(bx)):
            for j in range(i + 1, len(bx)):
                a, b = bx[i], bx[j]
                if a[0] < b[0] + b[2] - 1e-6 and b[0] < a[0] + a[2] - 1e-6 and a[1] < b[1] + b[3] - 1e-6 \
                        and b[1] < a[1] + a[3] - 1e-6:
                    ov += 1
        tinfo['core_overlaps'] = ov
        for c in cores:                                 # P4: plan-derived pins (pins_plan_v2.py) where none exist
            if 'pins_file' in c:
                continue
            fn = PP.get(f"{c['module']}@{c['outline_um'][0]}x{c['outline_um'][1]}") or \
                PP.get(f"{c['module']}@{c['outline_um'][0]:g}x{c['outline_um'][1]:g}")
            if fn:
                c['pins_file'] = f'cores/pins_plan/{fn}'
                c['track_offset_um'] = [0.0, 0.0]
                c['note'] = (c.get('note', '') + '; P4 plan-derived pins on plan M4/M5 tracks (pins_plan_v2.py)')
                pp_used.add(fn)
        if cores:
            t['hard_cores'] = [{k: v for k, v in c.items() if not k.startswith('_')} for c in cores]
        # ---------------- type note
        if True:
            cn = (f"cells: glue {tinfo['glue_cells'] / 1e3:.0f}k (regs EST + flattened leaves) + {len(cores)} hard "
                  f"cores (max {tinfo['core_cells_max'] / 1e3:.0f}k)")
            if any(r.get('hard_ip') for r in rows):
                cn += ' + hard IP'
        t['note'] = (t.get('note', '') + ' | ' + cn + f"; clock taps {len(taps)}").strip(' |')
        notes['types'][tn] = tinfo
    notes['pins_files'] = sorted(pins_used)
    if os.path.realpath(os.path.join(out_dir, 'cores')) != os.path.realpath(os.path.join(HERE, 'cores')):
        # pins_file paths are relative to the plan file
        os.makedirs(os.path.join(out_dir, 'cores', 'pins'), exist_ok=True)
        for m in sorted(pins_used):
            shutil.copyfile(os.path.join(HERE, 'cores', 'pins', f'{m}.json'),
                            os.path.join(out_dir, 'cores', 'pins', f'{m}.json'))
    notes['pins_plan_files'] = sorted(pp_used)
    if pp_used and os.path.realpath(os.path.join(out_dir, 'cores')) != os.path.realpath(os.path.join(HERE, 'cores')):
        os.makedirs(os.path.join(out_dir, 'cores', 'pins_plan'), exist_ok=True)
        for m in sorted(pp_used):
            shutil.copyfile(os.path.join(HERE, 'cores', 'pins_plan', m), os.path.join(out_dir, 'cores', 'pins_plan', m))
    notes['c0_tree'] = c0_tree(plan)
    notes['summary'] = summarise(notes)
    json.dump(notes, open(os.path.join(out_dir, 'plan_notes_v2.json'), 'w'), indent=1, sort_keys=True)
    return notes


def c0_tree(plan):
    """GEOM 07:50 item 4: C0 holds the die-level roots; each root drives each quadrant through its own registered
    output <bus>_q<Q>.  Per root: buses, bits and lanes per quadrant, lane endpoints, hops and cycles."""
    types = plan['partition_types']
    lat = plan['latency']['lanes']
    port = {p['id']: p for p in plan['ports']}
    lane_of_port = {}
    for l in plan['lanes']:
        for pid in l['ports']:
            lane_of_port[pid] = l
    out = {}
    for tn, pname in (('c0', 'C0'), ('q_vm', 'NW_vm')):
        t = types[tn]
        mod = {c['inst']: c['module'] for c in t['contents']}
        roots = collections.defaultdict(lambda: dict(module=None, out_buses=0, in_buses=0, out_bits=0, in_bits=0,
                                                     per_quadrant={}, lanes=0, dst_parts=set(), max_cycles=0,
                                                     max_hops=0))
        ep = 0
        for b in t['buses']:
            inst, leafport = (b.get('leaf') or '?.?').split('.', 1)
            r = roots[inst]
            r['module'] = mod.get(inst, inst)
            ep += 1
            if b['dir'] == 'out':
                r['out_buses'] += 1; r['out_bits'] += b['width']
                q = re.search(r'_q(NW|NE|SW|SE)$', leafport)
                if q:
                    pq = r['per_quadrant'].setdefault(q.group(1), dict(buses=0, bits=0))
                    pq['buses'] += 1; pq['bits'] += b['width']
                for p in plan['ports']:
                    if p['src']['part'] == pname and p['src']['bus'] == b['name']:
                        l = lane_of_port.get(p['id'])
                        if l:
                            r['lanes'] += 1
                            r['dst_parts'].add(port[l['ports'][-1]]['dst']['part'])
                            r['max_hops'] = max(r['max_hops'], len(l['ports']))
                            r['max_cycles'] = max(r['max_cycles'], lat.get(l['id'], {}).get('cycles', 0))
            else:
                r['in_buses'] += 1; r['in_bits'] += b['width']
        for r in roots.values():
            r['dst_parts'] = sorted(r['dst_parts'])
            r['fanout_per_hop'] = ('root register -> ' + (f"{len(r['per_quadrant'])} registered quadrant outputs "
                                                          f"_q<Q> inside {pname} (fan-out {len(r['per_quadrant'])})"
                                                          if r['per_quadrant'] else 'its own output register')
                                   + ' -> each output 1:1 on its own lane (seam invariant: one 2-pin net per port '
                                     'bit, no fan-out at a seam; G0 check_seams) -> stations 1:1 -> one '
                                     'destination boundary register (a broadcast re-forks only in a generated '
                                     'hbm_ft_fork_reg of the destination region)')
        out[tn] = dict(partition=pname, lane_endpoints=ep, roots=dict(sorted(roots.items())))
    return out


def summarise(notes):
    T = notes['types']
    real = T
    taps = {k: v['taps'] for k, v in T.items() if v.get('taps')}
    return dict(types=len(T), types_with_taps=len(taps), taps=sum(v['n'] for v in taps.values()),
                hard_cores=sum(v['n_cores'] for v in T.values()),
                max_core_cells=max(v['core_cells_max'] for v in real.values()),
                max_core_type=max(real, key=lambda k: real[k]['core_cells_max']),
                max_glue_cells=max(v['glue_cells'] for v in real.values()),
                max_glue_type=max(real, key=lambda k: real[k]['glue_cells']),
                glue_over_cap=[k for k, v in real.items() if v['glue_cells'] > CAP],
                cores_over_cap=[(k, c['inst'], c['cells']) for k, v in real.items() for c in v['cores']
                                if (c['cells'] or 0) > CAP],
                leaves_split=len(notes['over_cap']),
                max_point_to_tap_um=max((v['max_point_to_tap_um'] for v in taps.values()), default=0),
                max_nn_tap_um=max((v['max_nn_tap_um'] for v in taps.values()), default=0),
                all_tap_graphs_connected=all(v['connected'] for v in taps.values()),
                core_overlaps=sum(v['core_overlaps'] for v in T.values()),
                sm_types=sorted(k for k, v in T.items() if v.get('sm_split')))


if __name__ == '__main__':
    d = sys.argv[1] if len(sys.argv) > 1 else HERE
    plan = json.load(open(os.path.join(d, 'die_plan.json')))
    where = json.load(open(os.path.join(d, 'v2_assign.json')))['where']
    n = apply(plan, d, where)
    json.dump(plan, open(os.path.join(d, 'die_plan.json'), 'w'), indent=None, separators=(',', ':'))
    print(json.dumps(n['summary'], indent=1))
