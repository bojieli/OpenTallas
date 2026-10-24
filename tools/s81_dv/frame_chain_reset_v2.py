#!/usr/bin/env python3
"""Close chained-frame reset epochs in an executed bind, preserving lane gates.

Calendar-v2 correction: only the receiving frame's rst_n gets extra stations on ck_r0. Existing return-lane resets
and every ICG remain byte-identical. Run after dv_diecase and before dv_rvcase; rerun strict port bind.
S81-P9-FC 10-23: the delay comes from the edge-exact landing calendar below (chained lanes start at the upstream
frame's LANDED xk, i.e. after the upstream lane flight; per-lane window at tt and ff), replacing "R0 >= G_up", which
left every retimed frame 4-5 periods short (fc30 u_f_3L03 status fault).  Needs the GEN land plan (--land-plan).
"""
import argparse
import math
import hashlib
import json
import re
from pathlib import Path


def digest(text):
    return hashlib.sha256(text.encode()).hexdigest()


# ----------------------------------------------------------------------------------------------------------------
# Edge-exact chained-frame landing calendar (S81-P9-FC 10-23, replaces the calendar-v2 "R0 >= G_up" epoch rule).
#
# Times are in die clock periods T on the common-phase regional roots: a reset station of depth d (or an ICG enable)
# changes at edge d; a hop-0 ICG on the root opened by an enable of depth g gives its first GCLK rise at g + 1.
#   * a forwarded lane clock through N relays starts at  g + 1 + 0.5 * (#inverting dsfd_dvrlyh stations mod 2);
#   * its last hop flight F (whole periods, the routed flight the frame lk strap was chosen for: land-plan S1 at the
#     corner, F = clamp(ceil(-S1 / T), K - D + 1, K - 1); a lane without an S1 row is modelled at K - 1, exactly as
#     dv_slice_cut's dv_flight_sim) delays the clock edge the landing sees: A = start + F;
#   * a CHAINED frame lane is clocked by the upstream frame's xok[k] = its landed xk[k] (u_xo<k> ck_o, no inversion),
#     i.e. by the UPSTREAM lane AFTER the upstream lane's flight, then its own ICG, relays and flight.  calendar-v2
#     took the upstream hop-0 gate G_up as the chained lane start and so dropped F_up (K_up - 1 = 4 periods on every
#     xx02 -> xx03 / xx12 -> xx13 pair) and the own F (1): the retimed frames read 4-5 periods early (fc30 u_f_3L03
#     ret[69] at cyc 141, S81-P9-FC repro).
#   * the frame landing ring (ot_s81_land, crs4 rsync) releases at  Rrel = rst_n depth + sync (FRH10 pad 2 + rsync 2).
# Landing window per lane, both corners (ot_s81_land epochs; edge-exact probe frame_chain_reset_probe.py):
#     late : dt = A - Rrel < K + 1        (the slot read at rc - K is written; dt >= K + 1 sets the lane fault)
#     early: dt > 0 at tt                 (an edge before the release is silently dropped by wc)
# A chained frame failing the window gets the smallest whole reset delay d meeting late; the tool refuses when that d
# would release the ring after the lane epoch G (G - Rrel - d < 0, LANDING-CONTRACT L3) or leave dt <= 0.
LAND_D = 4


def lane_flight(K, s1_ps, T_ps, D=LAND_D):
    """dv_slice_cut flight rule: whole periods of last-hop flight for a lane landing at strap K."""
    if s1_ps is None:
        if K <= 1:
            return 0
        s1_ps = -(K - 1) * T_ps
    return max(min(max(math.ceil(-float(s1_ps) / T_ps), K - D + 1), K - 1), 0)


def inspect(text, sync_edges, land=None, corners=('tt', 'ff')):
    relays = {}
    for m in re.finditer(r'(dsfd_rly_1_\w+) (\w+) \(\.ck\(([\w\[\]]+)\), \.rs\((\w+)\), \.i\((\w+)\), \.o\((\w+)\)\);', text):
        master, inst, ck, rs, inp, out = m.groups()
        relays[out] = dict(master=master, inst=inst, ck=ck, rs=rs, inp=inp, line=m[0])
    aliases = dict(re.findall(r'assign (\w+) = (\w+);', text))
    def depth(net, seen=()):
        assert net not in seen, ('reset cycle', net)
        if net in relays:
            return depth(relays[net]['inp'], seen + (net,)) + 1
        if net in aliases:
            return depth(aliases[net], seen + (net,))
        return 0
    gates = {m[4]: dict(inst=m[1], ck=m[2], ena=m[3], line=m[0]) for m in re.finditer(
        r'ICGx4_ASAP7_75t_R (\w+) \(\.CLK\(([\w\[\]]+)\), \.ENA\((\w+)\), \.SE\(\S+\), \.GCLK\((\w+)\[0\]\)\);', text)}
    # forwarded lane stations: master per (clock bus, output index); dsfd_dvrlyh_* = half-cycle (inverting) ck_o
    station = {}
    for m in re.finditer(r'(dsfd_dvrlyh?_\w+) \w+ \([^;]*?\.ck\((\w+)\[(\d+)\]\), \.ck_o\((\w+)\[(\d+)\]\)', text):
        assert m[2] == m[4] and int(m[5]) == int(m[3]) + 1, ('lane clock station not chained', m[0][:120])
        station[(m[2], int(m[5]))] = m[1].startswith('dsfd_dvrlyh_')
    # bench flight wires (cut slice tops): the flight F is explicit
    flights = {m[4]: dict(F=int(m[1]), base=m[2], stages=int(m[3])) for m in re.finditer(
        r'dv_flight_sim #\(\.W\(\d+\), \.F\((\d+)\)\) \w+ \(\.ck_in\((\w+)\[(\d+)\]\), \.rs\(\w+\), \.i_in\([^)]*\), \.ck_out\((\w+)\)', text)}
    T_ps = float(land['T_ps']) if land else None
    lp = {r['link']: r for r in land['links']} if land else {}
    frames = {}
    for m in re.finditer(r'(col_\w+) #\(\.INSTANCE\("(\w+)"\)\) (\w+) \((.*?)\);', text):
        master, identity, inst, body = m.groups()
        assert inst == identity
        rst = re.search(r'\.rst_n\((\w+)\)', body)[1]
        root = re.search(r'\.ck_r0\((\w+)\)', body)[1]
        lkm = re.search(r"\.lk\((\d+)'h(\w+)\)", body)
        exprs = [e.strip() for e in re.search(r'\.xk\(\{([^}]*)\}\)', body)[1].split(',')]
        nl = len(exprs); kw = int(lkm[1]) // nl; lkv = int(lkm[2], 16)
        lanes = []
        for pos, expr in enumerate(exprs):
            k = nl - 1 - pos                                   # concatenation is high lane first
            K = (lkv >> (kw * k)) & ((1 << kw) - 1)
            if expr in flights:
                fl = flights[expr]; base, n = fl['base'], fl['stages']; F = {c: fl['F'] for c in corners}
            else:
                lane = re.fullmatch(r'(\w+)\[(\d+)\]', expr)
                assert lane, ('unresolved frame lane', inst, expr)
                base, n = lane[1], int(lane[2])
                assert land, ('die netlist needs the GEN land plan for the lane flights', inst)
                row = lp.get('x_%s_l%d' % (inst.removeprefix('u_'), k)) or {}
                F = {c: lane_flight(K, (row.get('s1') or {}).get(c), T_ps) for c in corners}
            assert base in gates, ('unresolved frame lane gate', inst, expr)
            g = gates[base]
            inv = sum(station[(base, i)] for i in range(1, n + 1))
            lanes.append(dict(lane=k, net=base, stages=n, gate=g, K=K, F=F, inv=inv,
                              first_epoch=depth(g['ena']) + n % 2))   # calendar-v2 value, kept for the record
        lanes.sort(key=lambda l: l['lane'])
        frames[inst] = dict(master=master, rst=rst, root=root, reset_depth=depth(rst),
                            read_epoch=depth(rst) + sync_edges, lanes=lanes, line=m[0])
    assert frames, 'no frame instances found'
    def gate(inst, l, c):
        """time of the first rise of the lane's hop-0 / chained ICG (the lane epoch G of LANDING-CONTRACT L3)"""
        g = l['gate']; ena = depth(g['ena'])
        up = re.fullmatch(r'(u_f_\w+?)_xok\[(\d+)\]', g['ck'])
        if not up:
            assert '_xok' not in g['ck'], ('unparsed chained gate clock', inst, g['ck'])
            return ena + 1                                     # hop-0 gate on the (common-phase) root
        assert up[1] in frames, ('missing upstream frame', inst, up[1])
        ul = frames[up[1]]['lanes'][int(up[2])]
        assert not re.match(r'u_f_\w+_xok', ul['gate']['ck']), ('deeper frame chain not modelled', inst, up[1])
        t1 = arrive(up[1], ul, c)                              # upstream LANDED xk = xok (u_xo: 2 inverters)
        # the chained ICG latch is transparent in the low phase before each xok rise (also before the first rise of
        # an idle-high lane); an enable that rises before rise j (ck edge + clk-q) passes rise j
        return t1 + next(j for j in range(64) if ena < t1 + j)
    def arrive(inst, l, c):
        """time of the first forwarded edge at the frame landing: gate + half-cycle parity + routed flight"""
        return gate(inst, l, c) + 0.5 * (l['inv'] % 2) + l['F'][c]
    for inst, f in frames.items():
        f['upstream'] = sorted({re.match(r'(u_f_\w+?)_xok', l['gate']['ck'])[1] for l in f['lanes'] if '_xok' in l['gate']['ck']})
        f['release'] = f['reset_depth'] + sync_edges
        f['dt'] = {c: [arrive(inst, l, c) - f['release'] for l in f['lanes']] for c in corners}
        f['gate_slack'] = {c: [gate(inst, l, c) - f['release'] for l in f['lanes']] for c in corners}
        # late (both corners, the fault class here): the read slot rc - K is written, dt < K + 1 (dt >= K + 1 sets
        # the lane fault; bench F is the ceiling of the routed flight, so dt <= K + 0.5 also holds with real flight);
        # early: no forwarded edge before the release at the sim corner (dt > 0 at tt: wc counts ck_f edge 0).
        # early_warn (recorded, not a verdict): LANDING-CONTRACT L3 release after the lane epoch G (G - Rrel < 0) or a
        # coincident first edge at ff (dt <= 0) -- every GEN direct frame has G - Rrel in {0, 1}.
        f['late'] = max(dt - l['K'] for c in corners for dt, l in zip(f['dt'][c], f['lanes']))
        f['early'] = min(f['gate_slack'][c][j] for c in corners for j in range(len(f['lanes'])))
        f['window_ok'] = f['late'] < 1 and min(f['dt'][corners[0]]) > 0
        f['early_warn'] = f['early'] < 0 or min(f['dt'][corners[-1]]) <= 0
    changes = {}
    for inst, f in frames.items():
        if not f['upstream'] or f['window_ok']:
            continue
        lo = max(0, math.floor(f['late'] - 1) + 1)             # smallest d with late - d < 1
        hi = math.floor(f['early'])                            # largest d keeping the ring released by G (L3)
        f['delay_range'] = (lo, hi)
        if lo > hi or min(f['dt'][corners[0]]) - lo <= 0:      # recorded; correct() refuses
            changes[inst] = dict(upstream=f['upstream'], infeasible=True, lane_dt=f['dt'], gate_slack=f['gate_slack'],
                                 lane_K=[l['K'] for l in f['lanes']])
            continue
        delay = lo
        changes[inst] = dict(upstream=f['upstream'], reset=f['rst'], root=f['root'],
            old_reset_depth=f['reset_depth'], old_read_epoch=f['read_epoch'],
            upstream_first_epoch=max(l['first_epoch'] for u in f['upstream'] for l in frames[u]['lanes']),
            lane_K=[l['K'] for l in f['lanes']], lane_F={c: [l['F'][c] for l in f['lanes']] for c in corners},
            lane_dt=f['dt'], gate_slack=f['gate_slack'], delay_range=[lo, hi],
            delay=delay, new_read_epoch=f['read_epoch'] + delay,
            new_lane_dt={c: [dt - delay for dt in f['dt'][c]] for c in corners})
    return frames, changes, relays, aliases


def calendar_rows(frames, corners=('tt', 'ff')):
    """one row per frame: release, lane dt per corner, K, window verdict (the calendar check)"""
    return {i: dict(upstream=f['upstream'], release=f['release'], K=[l['K'] for l in f['lanes']],
                    F={c: [l['F'][c] for l in f['lanes']] for c in corners}, dt=f['dt'], gate_slack=f['gate_slack'],
                    late=f['late'], early=f['early'], ok=f['window_ok'], early_warn=f['early_warn'])
            for i, f in frames.items()}


def correct(bind, output=None, plan_path=None, views_dir=None, land_path=None):
    bind = Path(bind)
    text = (bind / 'die.v').read_text()
    case = json.loads((bind / 'bind_case.json').read_text())
    hints = json.loads((bind / 'place_hints.json').read_text())
    rule = case['frame_hop0_gates']['rule']
    sync = int(re.search(r'depth \+ (\d+)', rule)[1])
    land_path = Path(land_path) if land_path else bind.parents[1] / 'land.json'
    land = json.loads(land_path.read_text())
    frames, changes, relays, aliases = inspect(text, sync, land)
    plan_path = Path(plan_path) if plan_path else bind.parents[1] / 'plan.json'
    plan = json.loads(plan_path.read_text())
    bodies = {b['name']: b for b in plan['blocks']}
    reset_positions = {r['inst']: r['xy'] for r in hints['reset_place']}
    views_dir = Path(views_dir) if views_dir else bind.parents[1] / 'case/views'
    lef_shapes = {}
    def shape(master):
        if master not in lef_shapes:
            p = views_dir / (master + '.lef')
            lef = p.read_text()
            match = re.search(r'\bSIZE\s+([\d.]+)\s+BY\s+([\d.]+)\s*;', lef)
            assert match, ('actual relay LEF SIZE missing', p)
            lef_shapes[master] = dict(width_um=float(match[1]), height_um=float(match[2]),
                sha256=hashlib.sha256(p.read_bytes()).hexdigest(), path=str(p))
        return lef_shapes[master]
    def overlaps(a, b):
        return a[0] < b[2]-1e-6 and b[0] < a[2]-1e-6 and a[1] < b[3]-1e-6 and b[1] < a[3]-1e-6
    new_boxes = []
    original = text
    additions, placement = [], []
    for inst, row in changes.items():
        f = frames[inst]
        old = f['rst']; master = relays[old]['master']
        size = shape(master); mw, mh = size['width_um'], size['height_um']
        pin = hints['block_rst_pin'][inst.removeprefix('u_')]
        body = bodies[inst.removeprefix('u_')]
        x, y, w, h = (body[k] for k in ('x', 'y', 'w', 'h'))
        face = min(('W', 'E', 'S', 'N'), key=lambda side:
            dict(W=abs(pin[0]-x), E=abs(pin[0]-x-w), S=abs(pin[1]-y), N=abs(pin[1]-y-h))[side])
        previous = reset_positions[relays[old]['inst']]
        row['placement_face'] = face
        row['placement_source_xy'] = previous
        row['placement_hops_um'] = []
        for k in range(row['delay']):
            net = f'rsfc2_{inst}_{k}'
            assert not re.search(r'\b' + net + r'\b', original), ('already patched', net)
            additions += [f'  wire {net};', f'  {master} st_{net} (.ck({f["root"]}), .rs({old}), .i({old}), .o({net}));   // chained-frame calendar v2']
            # Leave 0.01 um beyond the placer's 0.5 um clearance: exact 0.5
            # gaps can round below the threshold in double/0.001-um DBU math.
            clearance = 0.51
            xy = dict(W=[x-mw/2-clearance, pin[1]+k*(mh+clearance)], E=[x+w+mw/2+clearance, pin[1]+k*(mh+clearance)],
                      S=[pin[0]+k*(mw+clearance), y-mh/2-clearance], N=[pin[0]+k*(mw+clearance), y+h+mh/2+clearance])[face]
            xy = [round(v, 3) for v in xy]
            box = [xy[0]-mw/2, xy[1]-mh/2, xy[0]+mw/2, xy[1]+mh/2]
            assert not any(overlaps(box, [b['x']-0.5,b['y']-0.5,b['x']+b['w']+0.5,b['y']+b['h']+0.5])
                           for b in plan['blocks']), ('reset macro footprint collides with hard body', inst, xy)
            assert not any(overlaps(box, [b[0]-0.5,b[1]-0.5,b[2]+0.5,b[3]+0.5]) for b in new_boxes), ('new reset macro footprints collide', inst, xy)
            new_boxes.append(box)
            hop = abs(xy[0]-previous[0]) + abs(xy[1]-previous[1])
            assert hop <= 405, ('new reset source hop exceeds reach', inst, hop)
            row['placement_hops_um'].append(round(hop, 3)); previous = xy
            placement.append(dict(inst='st_' + net, master=master, orient='R0', xy=xy,
                kind='frame_chain_reset_v2'))
            old = net
        load_hop = abs(previous[0]-pin[0]) + abs(previous[1]-pin[1])
        assert load_hop <= 405
        row['placement_load_hop_um'] = round(load_hop, 3)
        line = f['line'].replace(f'.rst_n({f["rst"]})', f'.rst_n({old})')
        assert line != f['line'] and text.count(f['line']) == 1
        text = text.replace(f['line'], line)
        row['new_reset'] = old
    assert text.count('\nendmodule') == 1, 'expected one die module'
    text = text.replace('\nendmodule', '\n' + '\n'.join(additions) + '\nendmodule') if additions else text
    report = dict(schema='opentallas.s81.frame_chain_reset_v2.v2', source_die_sha256=digest(original),
        corrected_die_sha256=digest(text), receiver_reset_edges=sync, frames=len(frames), changes=changes,
        added_stations=len(placement), plan_sha256=hashlib.sha256(plan_path.read_bytes()).hexdigest(),
        reset_master_lefs=lef_shapes,
        placement_rule='actual LEF-sized rectangles: target 0.51 um clearance (>=0.5) from hard bodies and other new reset macros; every new source/load Manhattan hop <=405 um',
        ret_lane_rule='all preexisting reset stations, ICGs and lane relay connections unchanged')
    # Prove the mutation envelope by removing only the recorded new stations and
    # restoring only each receiving frame reset pin. All other bytes must match.
    restore = text
    for inst, row in changes.items():
        restore = restore.replace(f'.rst_n({row["new_reset"]})', f'.rst_n({row["reset"]})')
    if additions:
        restore = restore.replace('\n' + '\n'.join(additions) + '\nendmodule', '\nendmodule')
    assert restore == original, 'mutation escaped frame reset connections'
    bad = {i: c for i, c in changes.items() if c.get('infeasible')}
    assert not bad, ('chained frame without a legal reset delay', bad)
    after = inspect(text, sync, land)
    assert not after[1], 'chained reset deficit remains after correction'
    report['land_plan'] = dict(path=str(land_path), sha256=hashlib.sha256(land_path.read_bytes()).hexdigest())
    report['calendar_rule'] = ('edge-exact chained landing: lane start = upstream landed xk (upstream hop-0 gate + parity + '
        'upstream flight) -> own ICG + parity + own flight; per lane 0 < A - Rrel <= K at tt and ff; smallest reset delay')
    report['calendar_after'] = calendar_rows(after[0])
    report['calendar_window_fail_after'] = sorted(i for i, f in after[0].items() if not f['window_ok'])
    if output:
        output = Path(output); output.mkdir(parents=True, exist_ok=False)
        (output / 'die.v').write_text(text)
        hints['reset_place'] += placement
        case['reset']['stations'] += len(placement)
        case['reset']['frame_chain_reset_v2'] = report
        fg = case['frame_hop0_gates']; fg['frame_epoch_stations'] += len(placement)
        fg['rule'] += '; calendar-v2 clock-limited chains retain original ICG enables and delay only receiving frame rst_n; rows record corrected read epoch'
        for inst, row in changes.items():
            name = inst.removeprefix('u_')
            fg['frame_epoch_delay'][name] = fg['frame_epoch_delay'].get(name, 0) + row['delay']
            case['reset'].setdefault('frame_actual_release_depth', {})[name] = row['old_reset_depth'] + row['delay']
        for row in fg['rows']:
            key = row['inst'] if row['inst'].startswith('u_') else 'u_' + row['inst']
            if key in changes:
                c = changes[key]
                row['frame_rst'] = c['new_reset']; row['read_epoch'] = c['new_read_epoch']
                row['calendar_G_minus_R0'] -= c['delay']
                row['frame_chain_clock_limited'] = True
        case['frame_chain_reset_v2'] = report
        (output / 'bind_case.json').write_text(json.dumps(case, indent=1) + '\n')
        (output / 'place_hints.json').write_text(json.dumps(hints, indent=1) + '\n')
        (output / 'frame_chain_reset_v2.json').write_text(json.dumps(report, indent=1) + '\n')
    return report


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--bind-dir', required=True)
    ap.add_argument('--out-dir', help='new output directory: corrected die and changed metadata; original remains immutable')
    ap.add_argument('--plan', help='actual GEN plan; defaults to ../../plan.json from the bind directory')
    ap.add_argument('--views-dir', help='actual consumed relay LEF directory; defaults to ../../case/views')
    ap.add_argument('--land-plan', help='GEN land plan (lane S1 -> flight); defaults to ../../land.json (bind_case landings.land_plan)')
    a = ap.parse_args()
    r = correct(a.bind_dir, a.out_dir, a.plan, a.views_dir, a.land_plan)
    print(json.dumps({k: v for k, v in r.items() if k != 'calendar_after'}, indent=1))
