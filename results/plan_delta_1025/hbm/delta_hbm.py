#!/usr/bin/env python3
"""PLAN-DELTA/HBM 2026-10-25: one hardened core per RTL master + interface with ONE pin template (TYPE-REDUCE HBM,
approved), whole-instance orient instead of per-instance pin tables, owner option B ID straps (parent_id_straps).

Deterministic + idempotent: reads the BASE plan (BASE_SHA:physical/die_plan/hbm/die_plan.json via git show), writes physical/die_plan/hbm/die_plan.json, new pin tables under
physical/die_plan/hbm/cores/pins_plan_c1/ and displacement / summary JSON next to this script.

Groups (PATH-HBM items excluded: tkm root/tiles, q_hub/NW_hub, root partition type, L74/L12/L13):
  sfu_lane      16 piece modules -> master ot_hgi_sfu_split3_lane_core, strap map_lane_j (ID, option B)
  pg_lane_exp   15 piece modules -> master ot_hbm_su_pg_lane_exp_core, strap lane_lane_id (ID, option B)
  hc_tail_rest   2 piece modules -> master ot_hbm_hc_tail_rest_core
  score_tail     2 piece modules -> master ot_hbm_idx_tail_native
  single-module multi-table cores (same module, several pin tables) -> one table each (names identical)
Pin names: canonical master port names where the cut pin maps 1:1 (canonical_ports_split.json); cut pins that feed
several canonical ports (concatenations, bit order not in the census) keep a lane-neutral cut name (lane index
stripped) -- HBM-CORES owns the bit map of those.

Template choice: per group, the member table (in its own frame) that minimises the total Manhattan pin displacement
over all members, each member taking its best whole-instance orient of R0/MX/MY/R180.  Displacement of a pin =
|placed position before - placed position after| in the parent type frame.  Every pin moved > 405 um is listed.
"""
import json, os, re, sys, hashlib, collections, copy

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
PDIR = os.path.join(ROOT, 'physical/die_plan/hbm')
BASE_SHA = '39476539437879ffec85905e1e68b2d63c0dec68'   # origin/main 2026-10-25 (60 types / 187 partitions)
REACH = 405.0
ORIENTS = ('R0', 'MX', 'MY', 'R180')
PATH_EXCLUDE = re.compile(r'tkm')            # PATH-HBM P4/P5 cores (root + tiles) stay untouched
NEWDIR = 'cores/pins_plan_c1'
# PATH-HBM types: c0 = the root partition type (u18_root tkm root + 32 tkm tiles) and any type holding the NW_hub TKM
# ingress source cores (ot_hfd_coll_q2_hard_v8g pieces, PATH P1) -- no core entry of these types is changed
PATH_TYPE_CORE = re.compile(r'tkm|ot_hfd_coll_q2_hard')

MASTER_GROUPS = {   # canonical type -> (plan module to write, approved ID straps)
    'sfu_lane': ('ot_hgi_sfu_split3_lane_core', {'map_lane_j'}),
    'pg_lane_exp': ('ot_hbm_su_pg_lane_exp_core', {'lane_lane_id'}),
    'hc_tail_rest': ('ot_hbm_hc_tail_rest_core', set()),
    'score_tail': ('ot_hbm_idx_tail_native', set()),
}
# main 39476539: modules with >1 pin table at ONE outline (sm_attn leafh_lx / native_col / tile_tp, vm_calendar_role
# and pretree have one table per outline = genuinely different designs; not touched)
SINGLES = ['ot_hbm_svc_pc_ctrl_leaf_cfg_h9b']


def opt(o, w, h, x, y):
    if o in ('MY', 'R180'):
        x = w - x
    if o in ('MX', 'R180'):
        y = h - y
    return x, y


def split_bit(n):
    m = re.fullmatch(r'(.*)\[(\d+)\]', n)
    return (m.group(1), int(m.group(2))) if m else (n, None)


def neutral(base):
    return re.sub(r'(?<=_)\d+(?=_)', 'N', base)


def load_pins(f):
    P = json.load(open(os.path.join(PDIR, f)))
    P = P['pins'] if isinstance(P, dict) else P
    return [(p['name'], p['layer'], float(p['x']), float(p['y'])) for p in P]


def renamer(cut_pins, ports):
    pw = {p[0]: p[2] for p in ports}
    users = collections.Counter(cn for m in cut_pins.values() for cn in m)
    # canonical name only for a cut pin that IS a whole canonical port (same width, sole user): bit i == bit i
    whole = {b for b, m in cut_pins.items() if len(m) == 1 and all(users[cn] == 1 and pw.get(cn) == w
                                                                    for cn, w in m.items())}

    def rn(name):
        b, i = split_bit(name)
        m = cut_pins.get(b)
        if b in whole:
            (cn, w), = m.items()
            if pw.get(cn) == 1 and w == 1:
                return cn
            return f'{cn}[{i if i is not None else 0}]'
        # concatenated or census-unmapped cut pin: lane-neutral cut name (HBM-CORES owns the bit map)
        return neutral(b) + (f'[{i}]' if i is not None else '')
    return rn


def best_orient(cand, mem, w, h):
    """cand: {name: (layer,x,y)} template in own frame; mem: {name: (layer,X,Y)} placed (pre-delta) in core box frame"""
    best = None
    for o in ORIENTS:
        d = []
        for n, (_l, X, Y) in mem.items():
            _cl, cx, cy = cand[n]
            tx, ty = opt(o, w, h, cx, cy)
            d.append((abs(X - tx) + abs(Y - ty), n))
        s = sum(x for x, _ in d)
        if best is None or s < best[0]:
            best = (s, o, d)
    return best


def main():
    import subprocess
    plan = json.loads(subprocess.check_output(['git', '-C', ROOT, 'show', f'{BASE_SHA}:physical/die_plan/hbm/die_plan.json']))
    T = plan['partition_types']
    ninst = collections.Counter(p['type'] for p in plan['partitions'])
    canon = json.load(open(os.path.join(PDIR, 'cores/harden/canonical_ports_split.json')))['types']
    piece_of = {}
    for cn, c in canon.items():
        for tid, v in c['type_ids'].items():
            mod, wh = re.match(r'(.*)__([\d.]+x[\d.]+)$', tid).groups()
            piece_of[(mod, wh)] = (cn, v)
    groups = collections.defaultdict(list)       # gname -> [(type, idx, hc, renamed placed pins, straps)]
    path_types = sorted(tn for tn, t in T.items() if any(PATH_TYPE_CORE.search(h['module'])
                                                         for h in t.get('hard_cores') or []))
    print('PATH types left untouched:', path_types)
    for tn in sorted(T):
        if tn in path_types:
            continue
        for i, hc in enumerate(T[tn].get('hard_cores') or []):
            m = hc['module']
            if PATH_EXCLUDE.search(m):
                continue
            wh = 'x'.join(f'{v:g}' for v in hc['outline_um'])
            key = piece_of.get((m, wh))
            if key and key[0] in MASTER_GROUPS:
                cn, v = key
                rn = renamer(v['cut_pins'], canon[cn]['ports'])
                g = cn
                straps = v.get('straps', {})
            elif m in SINGLES:
                g, rn, straps = f'single:{m}:{wh}', (lambda n: n), {}
            else:
                continue
            groups[g].append((tn, i, hc, rn, straps))
    out_groups, disp_rows = {}, []
    os.makedirs(os.path.join(PDIR, NEWDIR), exist_ok=True)
    for g in sorted(groups):
        mem = groups[g]
        hc0 = mem[0][2]
        w, h = hc0['outline_um']
        placed, tabs = [], []
        for tn, i, hc, rn, st in mem:
            pins = load_pins(hc['pins_file'])
            o0 = hc.get('orient', 'R0')
            own = {}
            for n, l, x, y in pins:
                own[rn(n)] = (l, x, y)
            assert len(own) == len(pins), (g, hc['inst'], 'rename collision')
            tabs.append(own)
            placed.append({n: (l, *opt(o0, w, h, x, y)) for n, (l, x, y) in own.items()})
        names = {frozenset(t) for t in tabs}
        if len(names) != 1:
            print(f'SKIP {g}: members have different pin name sets ({len(names)})')
            continue
        uniq = {}
        for k, t in enumerate(tabs):
            uniq.setdefault(hashlib.sha1(json.dumps(sorted(t.items())).encode()).hexdigest(), k)
        best = None
        for sha, k in sorted(uniq.items()):
            tot, choice = 0.0, []
            for pm in placed:
                s, o, d = best_orient(tabs[k], pm, w, h)
                tot += s
                choice.append((o, d))
            if best is None or tot < best[0]:
                best = (tot, k, choice)
        # an as-built published view (cores/pins/, a closed core's LEF pins) wins over plan-derived tables: the
        # closed core is not re-pinned; every member takes the as-built member's track_offset_um (same lattice)
        asb = [k2 for sha, k2 in sorted(uniq.items()) if mem[k2][2]['pins_file'].startswith('cores/pins/')]
        if len(asb) == 1:
            k2 = asb[0]
            choice = [best_orient(tabs[k2], pm, w, h)[1:] for pm in placed]
            best = (sum(sum(x for x, _ in d) for _o, d in choice), k2, choice)
        tot, k, choice = best
        tmpl_off = mem[k][2].get('track_offset_um', [0.0, 0.0]) if len(asb) == 1 else None
        tmpl = dict(tabs[k])
        cn = g.split(':')[0]
        strap_ports = {}
        if cn in MASTER_GROUPS:
            module, ok_ids = MASTER_GROUPS[cn]
            for s in sorted({s for *_r, st in mem for s in st}):
                assert s in ok_ids, (g, s, 'strap is not an owner-approved ID')
                wdt = [p[2] for p in canon[cn]['ports'] if p[0] == s][0]
                strap_ports[s] = wdt
            # strap input pins: on the clock pin's layer/face row, next free positions at the row pitch
            if strap_ports:
                clk = sorted((v for n, v in tmpl.items() if 'clk' in n), key=lambda v: (v[2], v[1]))[0]
                row = sorted(x for l, x, y in tmpl.values() if l == clk[0] and abs(y - clk[2]) < 1e-6)
                pitch = min(b - a for a, b in zip(row, row[1:]) if b - a > 1e-6)
                x = row[-1]
                for s, wdt in strap_ports.items():
                    for b in range(wdt):
                        x = round(x + pitch, 4)
                        assert x < w, (g, 'strap row overflow')
                        tmpl[f'{s}[{b}]' if wdt > 1 else s] = (clk[0], x, clk[2])
        else:
            module = hc0['module']
        rows = [dict(name=n, layer=l, x=round(x, 4), y=round(y, 4)) for n, (l, x, y) in sorted(tmpl.items())]
        stem = (module if cn in MASTER_GROUPS else hc0['module']) + '__' + 'x'.join(f'{v:g}' for v in (w, h))
        rel = f'{NEWDIR}/{stem}.json'
        txt = json.dumps(rows, indent=0) + '\n'
        open(os.path.join(PDIR, rel), 'w').write(txt)
        gd = dict(module=module, template_from=f'{mem[k][0]}/{mem[k][2]["inst"]}', pins_file=rel,
                  members=[], total_disp_um=round(tot, 1), straps=strap_ports)
        for (tn, i, hc, rn, st), (o, d) in zip(mem, choice):
            far = sorted([x for x in d if x[0] > REACH], reverse=True)
            ent = T[tn]['hard_cores'][i]
            gd['members'].append(dict(type=tn, inst=hc['inst'], old_module=hc['module'], old_pins=hc['pins_file'],
                                      orient=o, replicas=ninst[tn], p50=round(sorted(x for x, _ in d)[len(d) // 2], 1),
                                      max=round(max(x for x, _ in d), 1), n_over_405=len(far)))
            for x, n in far:
                disp_rows.append(dict(group=g, type=tn, inst=hc['inst'], pin=n, disp_um=round(x, 1)))
            if tmpl_off is not None and ent.get('track_offset_um') != tmpl_off:
                d0 = ent.get('track_offset_um', [0.0, 0.0])
                gd['members'][-1].update(track_offset_from=d0, track_offset_to=tmpl_off,
                                         max=round(max(abs(X - (opt(o, w, h, *tmpl[n][1:])[0] + tmpl_off[0] - d0[0]))
                                                       + abs(Y - (opt(o, w, h, *tmpl[n][1:])[1] + tmpl_off[1] - d0[1]))
                                                       for n, (_l, X, Y) in placed[mem.index((tn, i, hc, rn, st))].items()), 3))
                ent['track_offset_um'] = list(tmpl_off)
            # a member whose old table is the template shifted by one constant sub-track (dx, dy) keeps its pins
            # exactly: the shift moves into track_offset_um (the plan's sub-lattice placement field)
            pm = placed[mem.index((tn, i, hc, rn, st))]
            sh = {(round(X - opt(o, w, h, *tmpl[n][1:])[0], 4), round(Y - opt(o, w, h, *tmpl[n][1:])[1], 4))
                  for n, (_l, X, Y) in pm.items()}
            if tmpl_off is None and len(sh) == 1 and sh != {(0.0, 0.0)}:
                (sx, sy), = sh
                ox, oy = ent.get('track_offset_um', [0.0, 0.0])
                ent['track_offset_um'] = [round(ox + sx, 4), round(oy + sy, 4)]
                gd['members'][-1].update(track_shift_um=[sx, sy], max=0.0, p50=0.0, n_over_405=0)
                disp_rows[:] = [r for r in disp_rows if not (r['type'] == tn and r['inst'] == hc['inst'])]
            ent['module'] = module
            ent['pins_file'] = rel
            ent['orient'] = o
            if st:
                ent['parent_id_straps'] = {s: dict(width=strap_ports[s], value=int(v, 2)) for s, v in sorted(st.items())}
            ent['note'] = (f"PLAN-DELTA/HBM 10-25: one master + one pin template ({rel}), whole-instance orient {o}"
                           + (f"; ID straps {sorted(st)} tied at the parent (owner option B)" if st else '')
                           + f"; was {hc['module']} {hc['pins_file']}")
        gd['total_disp_um'] = round(sum(m['max'] and sum(x for x, _ in c[1]) or 0 for m, c in zip(gd['members'], choice)), 1)
        out_groups[g] = gd
        print(f"{g}: {len(mem)} entries, {len(uniq)} tables -> 1 ({module}), total disp {tot:.0f} um, "
              f"pins >405: {sum(m['n_over_405'] for m in gd['members'])}")
    plan['note'] = plan['note'] + ' | PLAN-DELTA/HBM 2026-10-25: one master + one pin template per core group (results/plan_delta_1025/hbm).'
    json.dump(plan, open(os.path.join(PDIR, 'die_plan.json'), 'w'), separators=(',', ':'))
    json.dump(dict(groups=out_groups), open(os.path.join(HERE, 'delta_groups.json'), 'w'), indent=1)
    json.dump(disp_rows, open(os.path.join(HERE, 'displacements_over_405.json'), 'w'), indent=0)
    print('pins >405 um:', len(disp_rows))


if __name__ == '__main__':
    main()
