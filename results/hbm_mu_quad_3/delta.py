#!/usr/bin/env python3
"""HBM-MU-QUAD-3 planU3 delta (COORD RULING HBM-CORE-LAT-R3 (5) + G0C lattice errors), applied in place to PLAN_DIR:
 (L) hard-core origins onto the die lattice (grid_um): each off-lattice origin snaps to the nearest lattice point whose
     placed box does not overlap a neighbour (the quad packer used 4.32-um steps; track_offset_um may only carry a
     < BASE_LATTICE sub-lattice shift); internal-station endpoints on that core move with it.
 (P) every hard-core pin table snapped to the plan routing tracks in the core frame (layer offset + k*pitch along the
     layer's cross direction): with origins on the lattice the pins are then on the type/die tracks (R0 and MY).
 (a) root tail engines: x_g_tail_N_..._tail_sink_clk (div-7 output of ot_hbm_hc_tail_rest_core.sk_clk) is an OUTPUT
     generated clock: it drives tailN_sk_step0.clk / tailN_sk_steady.clk (core_conns), the 4 sk die clock taps are
     removed and recorded in generated_clocks.json (create_generated_clock -divide_by 7 -source tailN_rest/clk).
 (b) sk_step0 / sk_steady outlines grown top-down in their root slot (height only, row pitch kept) to <= 0.60 fill
     from the HBM-CORE-LAT-R3 synthesis fills (82 % / 68 % at 155.52 x 172.8); N-face pins follow the N edge.
Usage: delta.py TOOLS_DIE_PLAN PLAN_DIR"""
import json, math, sys, pathlib, hashlib, collections
tools, pd = sys.argv[1], pathlib.Path(sys.argv[2])
sys.path.insert(0, tools)
import schema as S
P = json.load(open(pd / 'die_plan.json')); T = P['partition_types']
L = S.Plan(P).layers; G = float(P['die']['grid_um'])
rep = collections.defaultdict(list)
r3 = lambda v: round(v + 0.0, 4)  # noqa: E731
def box(h, o=None):
    x, y = o or h['origin_um']; dx, dy = h.get('track_offset_um', [0, 0])
    return (x + dx, y + dy, x + dx + h['outline_um'][0], y + dy + h['outline_um'][1])
ov = lambda a, b: a[0] < b[2] - 1e-6 and b[0] < a[2] - 1e-6 and a[1] < b[3] - 1e-6 and b[1] < a[3] - 1e-6  # noqa: E731
# (b) sk resize first (changes outlines)
FILL = {'sk_step0': 0.82, 'sk_steady': 0.68}
rt = T['root']; hcs = {h['inst']: h for h in rt['hard_cores']}
for inst, h in hcs.items():
    k = next((k for k in FILL if inst.endswith(k)), None)
    if not k:
        continue
    w, hh = h['outline_um']; need = w * hh * FILL[k] / 0.60
    nh = math.ceil(need / w / G - 1e-9) * G
    nb = (h['origin_um'][0], h['origin_um'][1], h['origin_um'][0] + w, h['origin_um'][1] + nh)
    hit = [o for o, g in hcs.items() if o != inst and ov(nb, box(g))]
    if hit or nb[3] > rt['outline_um'][1]:
        rep['b_fail'].append(dict(inst=inst, new_h=nh, hits=hit)); continue
    f = pd / h['pins_file']; pins = json.load(open(f))
    for q in pins:
        if abs(q['y'] - hh) < 0.1:
            q['y'] = r3(q['y'] + nh - hh)
    nf = h['pins_file'].replace(f'{w:g}x{hh:g}', f'{w:g}x{nh:g}')
    (pd / nf).write_text(json.dumps(pins))
    h['pins_file'] = nf; h['outline_um'] = [w, round(nh, 3)]
    fill = FILL[k] * hh / nh
    rep['b_resized'].append(dict(inst=inst, outline_um=[w, round(nh, 3)], was=[w, hh], fill_est=round(fill, 3)))
    for tp in rt['clock']['taps']:
        if tp['name'].startswith(inst):
            tp['xy'] = [tp['xy'][0], r3(h['origin_um'][1] + nh / 2)]
# (L) lattice
for tn, t in T.items():
    cores = t.get('hard_cores', [])
    for h in cores:
        ox, oy = h['origin_um']
        if abs(ox / G - round(ox / G)) < 1e-6 and abs(oy / G - round(oy / G)) < 1e-6:
            continue
        others = [box(g) for g in cores if g is not h] + [box(c) for c in t.get('contents', []) if c.get('origin_um') and c.get('outline_um') and c.get('inst') not in {g['inst'] for g in cores}]
        cand = sorted({(math.floor(ox / G + 1e-9) * G, math.floor(oy / G + 1e-9) * G), (math.ceil(ox / G - 1e-9) * G, math.floor(oy / G + 1e-9) * G),
                       (math.floor(ox / G + 1e-9) * G, math.ceil(oy / G - 1e-9) * G), (math.ceil(ox / G - 1e-9) * G, math.ceil(oy / G - 1e-9) * G)},
                      key=lambda c: abs(c[0] - ox) + abs(c[1] - oy))
        W_, H_ = t['outline_um']
        ok = next((c for c in cand if not any(ov(box(h, c), b) for b in others)
                   and box(h, c)[0] >= -1e-6 and box(h, c)[1] >= -1e-6 and box(h, c)[2] <= W_ + 1e-6 and box(h, c)[3] <= H_ + 1e-6), None)
        if ok is None:
            rep['L_fail'].append(dict(type=tn, inst=h['inst'], origin=[ox, oy])); continue
        nx, ny = round(ok[0], 3), round(ok[1], 3); dx, dy = nx - ox, ny - oy
        b0 = box(h)
        h['origin_um'] = [nx, ny]
        n = 0
        for s in t.get('internal_stations', []):
            for key in ('from_um', 'to_um'):
                p = s[key]
                if b0[0] - 1e-3 <= p[0] <= b0[2] + 1e-3 and b0[1] - 1e-3 <= p[1] <= b0[3] + 1e-3:
                    s[key] = [r3(p[0] + dx), r3(p[1] + dy)]; n += 1
        for tp in t.get('clock', {}).get('taps', []):
            if tp['name'] == h['inst'] or tp['name'].startswith(h['inst'] + '.'):
                tp['xy'] = [r3(tp['xy'][0] + dx), r3(tp['xy'][1] + dy)]
        rep['L_moved'].append(dict(type=tn, inst=h['inst'], d=[round(dx, 3), round(dy, 3)], station_ends=n))
# (P) pin snap
seen = set(); snapmax = 0.0; nsn = 0; coll = 0
for tn, t in T.items():
    for h in t.get('hard_cores', []):
        f = h.get('pins_file')
        if not f or f in seen:
            continue
        seen.add(f); fp = pd / f
        js = json.load(open(fp)); lst = js.get('pins', js) if isinstance(js, dict) else js
        cw, ch = h['outline_um']; ch_ = 0; used = set()
        for q in lst:
            Ly = L.get(q['layer'])
            if Ly is None or q['layer'] == 'M1':
                continue
            ax = 'x' if Ly['dir'] == 'V' else 'y'; lim = cw if ax == 'x' else ch
            v = q[ax]; k = round((v - Ly['offset_um']) / Ly['pitch_um']); nv = Ly['offset_um'] + k * Ly['pitch_um']
            if nv > lim: nv -= Ly['pitch_um']
            if nv < 0: nv += Ly['pitch_um']
            nv = round(nv, 4)
            if abs(nv - v) > 1e-6:
                snapmax = max(snapmax, abs(nv - v)); q[ax] = nv; ch_ += 1
            key = (q['layer'], q['x'], q['y'])
            if key in used: coll += 1
            used.add(key)
        if ch_:
            nsn += ch_; fp.write_text(json.dumps(js))
            rep['P_tables'].append(dict(file=f, snapped=ch_))
rep['P_summary'] = dict(tables=len(rep['P_tables']), pins=nsn, max_move_um=round(snapmax, 4), same_site_pairs=coll)
# (a) generated clock
cc = json.load(open(pd / 'core_conns.json')); r = cc['root']; gen = []
for N in (0, 1):
    rest = f'u_hc_eng_tail{N}_rest'; pin = f'x_g_tail_{N}_u_t_u_tail_sink_clk'
    sks = [f'u_hc_eng_tail{N}_sk_step0', f'u_hc_eng_tail{N}_sk_steady']
    if pin in r.get(rest, {}):
        r[rest][pin] = [f'core:{s}' for s in sks]
        for s in sks:
            r[s]['clk'] = [f'core:{rest}']
        gen.append(dict(name=f'tail{N}_sk_clk', source=f'{rest}/clk', pin=f'{rest}/{pin}', divide_by=7,
                        sinks=[f'{s}/clk' for s in sks],
                        sdc=f'create_generated_clock -name tail{N}_sk_clk -source [get_pins {rest}/clk] -divide_by 7 [get_pins {rest}/{pin}]'))
before = len(rt['clock']['taps'])
rt['clock']['taps'] = [tp for tp in rt['clock']['taps'] if not any(tp['name'] == f'{s}.clk' for g in gen for s in [x.split('/')[0] for x in g['sinks']])]
rep['a_generated'] = gen; rep['a_taps_removed'] = before - len(rt['clock']['taps'])
(pd / 'core_conns.json').write_text(json.dumps(cc, indent=1))
(pd / 'generated_clocks.json').write_text(json.dumps(gen, indent=1) + '\n')
s = json.dumps(P, indent=1) + '\n'
(pd / 'die_plan.json').write_text(s); (pd / 'die_plan.sha256').write_text(hashlib.sha256(s.encode()).hexdigest() + '  die_plan.json\n')
(pd / 'delta_report.json').write_text(json.dumps(rep, indent=1) + '\n')
print(json.dumps(dict(sha=hashlib.sha256(s.encode()).hexdigest()[:12], b=rep['b_resized'], b_fail=rep['b_fail'], L_moved=len(rep['L_moved']),
                      L_fail=rep['L_fail'][:5], nL_fail=len(rep['L_fail']), P=rep['P_summary'], a_taps_removed=rep['a_taps_removed'], gen=len(gen))))
