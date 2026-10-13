#!/usr/bin/env python3
"""[vm8-face-1013] Locked per-bit pin plans for the ten VM8 face / fork tiles (fe0-3, fw0-3, re, rwt), M5 cap.

WHY (measured, vm_cp_*-cp1-2370c0876 on ot-epyc1tb): the cp1 kits packed every port into its own y range per face, so
a bit's input pin and output pin sat up to ~400 um apart in y inside a 12.96-21.6 um wide tile.  GRT final congestion:
fe0 M3 170% / M5 97% (M2 65%, M4 35%), re/rwt M3 191% / M5 110% (M2 34%, M4 21%): ONLY the vertical layers overflow.

PLAN: a tile is a list of SLOTS (one source bit, its flop(s) and every pin it drives); a slot owns a run of M4 tracks
and all its pins sit on those tracks, so in -> flop -> out is a straight horizontal wire.  Pins on one face are >= 2
M4 tracks apart (0.5 pin / track = 10.42 b/um = 0.556 of the 18.75 usable M4 tracks/um), single layer M4, no M6 pin.
Slot runs are ordered and anchored so the die hop to the neighbour stays <= 500 um PER BIT (checked here against the
submitted relay kits' balanced pin positions).  The y shift a fork needs is done by the die in the >= 100 um channels,
except RE, where the 335 um die hop leaves no room for it: RE is a 90.72 um wide switchbox (cut 2,063 / 3,780 = 0.55).
FW2 needs 7,168 + 4,136 tracks = 543 um at 0.5 pin / track: the NW face is re-split FW2 598.32 / FW3 399.6 um (the
fw2|fw3 seam is internal to the NW die face); no M6 grant is needed for fw2 or rwt.

    python3 face_pin_plan.py            writes codex_specs/vm_cp_<t>_cx.json, codex_specs/pins/vm_cp_<t>_cx_pins.tcl
                                        and results/physical/vm8_codex_1013/face_pin_plan.json (cut + per-bit hops)
"""
import importlib.util
import json
import sys
from pathlib import Path

CP = Path(__file__).resolve().parent
ROOT = CP.parents[3]
_l = importlib.util.spec_from_file_location("vm_cp", CP / "make_vm_cp.py")
plan = importlib.util.module_from_spec(_l)
_l.loader.exec_module(plan)

T4, T4O = 0.048, 0.012          # M4 horizontal track pitch / offset (asap7 make_tracks)
T3, T3O = 0.036, 0.009          # M3 vertical track pitch / offset
LO = 50                         # first usable track (2.412 um off the corner)
M4_USABLE = 18.75               # tracks/um after 10% PG / access (stream convention)
REL = "physical/hbm_accel_die_views/vm/cp"

# tile -> (w, h, m5_pg_pitch)
GEOM = {
    'vm_cp_fw0': (28.08, 498.96, 2.7), 'vm_cp_fw1': (23.76, 498.96, 2.7), 'vm_cp_fw2': (28.08, 598.32, 2.7),
    'vm_cp_fw3': (21.6, 399.6, 2.7), 'vm_cp_fe0': (21.6, 498.96, 2.7), 'vm_cp_fe1': (23.76, 498.96, 2.7),
    'vm_cp_fe2': (23.76, 498.96, 2.7), 'vm_cp_fe3': (25.92, 498.96, 2.7), 'vm_cp_rwt': (28.08, 518.4, 2.7),
    'vm_cp_re': (259.2, 401.76, 5.4),
}
# instance origin changes (die level, planning): fw3 follows the fw2 | fw3 seam; relays as candidate_geometry.py
INST_Y = {"u_rt0": 1373.76, "u_rb3": 224.64, "u_fw3": 2 * 498.96 + 598.32}
# section anchors: tile -> [(section key, anchor)], anchor = ('lo', track) first track | ('hi', track) last track + 1
def ntr(t):
    return round(GEOM[t][1] / T4)


def fan(kit):
    """source (port, bit) -> [out pins]; p2 keeps the same slot (two flops in series, same wire)."""
    k = plan.KITS[kit]
    out, fclk = {}, []
    for o, segs in k['outs'].items():
        pos = k['ports'][o][1]
        for s in segs:
            n = plan.seg_w(s)
            lo = pos - n
            for b in range(n):
                if s[0] == 'fclk':
                    fclk.append((o, lo + b))
                else:
                    out.setdefault((s[1], s[3] + b), []).append((o, lo + b))
            pos = lo
    return out, fclk


def layout(kit):
    """-> {(port, bit): (face, track or x_um)}, stats"""
    k = plan.KITS[kit]
    ports = k['ports']
    f, fclk = fan(kit)
    face = {p: v[2] for p, v in ports.items()}
    N = ntr(kit)
    HI = N - LO
    pins = {}

    def slot(src, t):
        """place one slot at track t; returns the tracks it uses"""
        grp = {'W': [], 'E': []}
        if face[src[0]] in grp:
            grp[face[src[0]]].append(src)
        for o in f.get(src, []):
            grp[face[o[0]]].append(o)
        n = max(len(grp['W']), len(grp['E']), 1)
        for fc, lst in grp.items():
            off = (n - len(lst))          # centre the shorter face in the slot (2 tracks per pin)
            for j, p in enumerate(lst):
                pins[p] = (fc, t + off + 2 * j)
        return 2 * n

    def size(srcs):
        tot = 0
        for src in srcs:
            nw = sum(1 for o in f.get(src, []) if face[o[0]] == 'W') + (face[src[0]] == 'W')
            ne = sum(1 for o in f.get(src, []) if face[o[0]] == 'E') + (face[src[0]] == 'E')
            tot += 2 * max(nw, ne, 1)
        return tot

    def run(srcs, anchor):
        kind, t = anchor
        if kind == 'hi':
            t -= size(srcs)
        t0 = t
        for src in srcs:
            t += slot(src, t)
        return t0, t

    def lone(lst, fc, t):
        for j, p in enumerate(lst):
            pins[p] = (fc, t + 2 * j)
        return t + 2 * len(lst)

    B = lambda p, a, b: [(p, i) for i in range(a, b)]
    sec = {}
    if kit == 'vm_cp_fw0':
        sec['i'] = run(B('iSW', 0, 512), ('lo', LO))
        sec['f'] = run(B('f_su_SW', 0, 2048), ('lo', sec['i'][1] + 6))
        lone(fclk, 'W', sec['f'][1] + 2)
        ck = sec['i'][1] + 2
    elif kit == 'vm_cp_fw1':
        sec['ph'] = run(B('ph', 0, 1078), ('lo', LO))
        # st slots follow the y order of RWT's sto pins (computed in RWT's layout: st[j] then its 4 copies)
        sec['st'] = run(rwt_sto_order(), ('hi', HI))
        t = sec['st'][0] - 2 - 2 * len(fclk)
        lone(fclk, 'W', t)
        sec['tap'] = run(B('tap', 0, 2063), ('hi', t - 2))
        ck = sec['st'][0] - 2      # beside the fclk pins (g2)
    elif kit == 'vm_cp_fw2':
        sec['tap'] = run(B('tap', 0, 2063), ('lo', LO))
        lone(fclk, 'W', sec['tap'][1] + 2)
        sec['ph'] = run(B('ph', 0, 2048), ('hi', HI))
        ck = sec['tap'][1] + 12    # beside the fclk pins (g2)
    elif kit == 'vm_cp_fw3':
        sec['f'] = run(B('f_su_NW', 0, 2048), ('lo', LO))
        sec['i'] = run(B('iNW', 0, 512), ('lo', sec['f'][1] + 6))
        lone(fclk, 'W', sec['i'][1] + 2)
        ck = sec['f'][1] + 2
    elif kit == 'vm_cp_fe0':
        sec['f'] = run(B('f_su_SE', 0, 1078), ('hi', HI))
        sec['fu'] = run(B('f_su_SE', 1078, 2048), ('hi', sec['f'][0] - 4))
        t = sec['fu'][0] - 2 - 2 * len(fclk)
        lone(fclk, 'E', t)
        sec['i'] = run(B('iSE', 0, 512), ('hi', t - 2))
        ck = t                     # W, straight across from the E fclk pins (g2)
    elif kit == 'vm_cp_fe1':
        sec['ph'] = run(B('ph', 0, 2048), ('lo', LO))
        t = HI - 2 * len(fclk)
        lone(fclk, 'E', t)
        sec['tap'] = run(B('tap', 0, 2063), ('hi', t - 2))
        ck = t                     # W, straight across from the E fclk pins (g2)
    elif kit == 'vm_cp_fe2':
        sec['tap'] = run(B('tap', 0, 2063), ('lo', LO))
        lone(fclk, 'E', sec['tap'][1] + 2)
        sec['ph'] = run(B('ph', 0, 2048), ('hi', HI))
        ck = sec['tap'][1] + 2     # W, straight across from the E fclk pins (g2)
    elif kit == 'vm_cp_fe3':
        # f_su_NE / ph straight across from RT3.ei (die y 1663.7 ..)
        sec['f'] = run(B('f_su_NE', 0, 2048), ('lo', 3476))
        sec['i'] = run(B('iNE', 0, 512), ('lo', sec['f'][1] + 6))
        lone(fclk, 'E', sec['i'][1] + 2)
        ck = sec['i'][1] + 2       # W, straight across from the E fclk pins (g2)
    elif kit == 'vm_cp_rwt':
        sec['tap'] = run(B('tap', 0, 2063), ('lo', LO))
        sec['st'] = run(B('st', 0, 202), ('hi', HI))
        ck = (sec['tap'][1] + sec['st'][0]) // 2
    elif kit == 'vm_cp_re':
        # FACE3 10-13 (cx4, after cx3 GRT-0116 at the se|ne seam): the fork is done on ONE vertical M3 track column per
        # bit: tap[k] enters on W (straight across from the root's tap_e pins), turns once into column c(k); se[k]
        # leaves on the S face and ne[k] on the N face on that same track (3 M3 tracks per column, 0.108 um; M5 free).
        # No bit is shifted in y inside the tile; the die takes S -> FE1.tap and N -> FE2.tap.  Column order: the bits
        # with the longest die y run (max of |FE1 pin y - S face|, |FE2 pin y - N face|) get the columns nearest the
        # E side, so every die hop stays <= 500 um.
        h = GEOM[kit][1]
        y_re = dict((n, y) for n, _m, _x, y, *_r in plan.INST)['u_re']
        need = []
        for i in range(2063):
            d = []
            for fe, yi, edge in (('vm_cp_fe1', plan.FH, y_re), ('vm_cp_fe2', 2 * plan.FH, y_re + h)):
                yy = yi + _fe_tap(fe)[i] * T4 + T4O
                d.append(abs(yy - edge))
            need.append((max(d), i))
        need.sort()                                   # smallest need -> westmost column
        C0, CS = 900, 3
        for c, (_d, i) in enumerate(need):
            pins[('se', i)] = ('S', C0 + CS * c)
            pins[('ne', i)] = ('N', C0 + CS * c)
            pins[('tap', i)] = ('W', 2000 + 2 * i)
        for i in range(201):
            pins[('rdo', i)] = ('W', 64 + 2 * i)
            pins[('rdi', i)] = ('S', 60 + 4 * i)          # M3 track index (x), 0.144 um pitch
        pins[('cfgo', 0)] = ('W', 64 + 2 * 201)
        pins[('cfgi', 0)] = ('N', 80)
        sec = {'col': (C0, C0 + CS * 2063), 'tap': (2000, 6126), 'rdo': (64, 468)}
        ck = 1000
    pins[('ck', 0)] = ('W', ck)
    # checks: every port bit placed once, inside the face, >= 2 tracks apart per face
    for p, v in ports.items():
        for b in range(v[1]):
            assert (p, b) in pins, (kit, p, b)
            assert pins[(p, b)][0] == v[2], (kit, p, b)
    byf = {}
    for p, (fc, t) in pins.items():
        byf.setdefault(fc, []).append(t)
    stats = {}
    for fc, ts in byf.items():
        ts.sort()
        if fc in 'WE':
            assert ts[0] >= 42 and ts[-1] <= N - 42, (kit, fc, ts[0], ts[-1], N)
            assert all(b - a >= 2 for a, b in zip(ts, ts[1:])), (kit, fc)
            win = round(10 / T4)       # peak pins in any 10 um window
            j = 0
            pk = 0
            for i, t in enumerate(ts):
                while ts[j] <= t - win:
                    j += 1
                pk = max(pk, i - j + 1)
            stats[fc] = dict(pins=len(ts), layer='M4', peak_b_per_um=round(pk / 10, 2),
                             cut_fraction=round(pk / 10 / M4_USABLE, 3),
                             span_um=[round(ts[0] * T4 + T4O, 3), round(ts[-1] * T4 + T4O, 3)])
        else:
            stats[fc] = dict(pins=len(ts), layer='M3', span_um=[round(ts[0] * T3 + T3O, 3), round(ts[-1] * T3 + T3O, 3)])
    # worst internal horizontal cut: nets whose pins straddle a y (aligned slots: ~0; RE: the fork)
    ev = []
    srcs = dict(f)
    for src, outs in srcs.items():
        if pins[src][0] not in 'WE':
            continue
        ys = [pins[src][1]] + [pins[o][1] for o in outs if pins[o][0] in 'WE']
        for o in outs:
            if pins[o][0] in 'WE':
                a, b = sorted((pins[src][1], pins[o][1]))
                if b - a > 12:
                    ev += [(a, 1), (b, -1)]
    ev.sort()
    cur = pk = 0
    for _, d in ev:
        cur += d
        pk = max(pk, cur)
    w = GEOM[kit][0]
    vt = w / T3 * 0.9 + w / 0.048 * 0.8        # M3 (10% access) + M5 (20% PG stripes) vertical tracks
    stats['vertical_cut'] = dict(nets_crossing_worst_y=pk, vertical_tracks=round(vt), fraction=round(pk / vt, 3))
    stats['sections_tracks'] = sec
    flops = sum(len(v) for v in f.values()) + sum(
        plan.seg_w(s) for segs in k['outs'].values() for s in segs if s[0] == 'p2')
    stats['sinks'] = flops
    stats['core_um2_per_flop'] = round((w - 4.5) * (GEOM[kit][1] - 2.2) / flops, 2)
    return pins, stats


_fe = {}


def _fe_tap(fe):
    """FE tile tap pin tracks by bit"""
    if fe not in _fe:
        p, _ = layout(fe)
        _fe[fe] = [p[('tap', i)][1] for i in range(2063)]
    return _fe[fe]


def rwt_sto_order():
    """fw1.st bits in the y order of rwt.sto pins"""
    p, _ = layout('vm_cp_rwt')
    return [('st', b) for (name, b), (fc, t) in sorted(p.items(), key=lambda kv: kv[1][1]) if name == 'sto']


def local_xy(kit, face, t):
    w, h, _ = GEOM[kit]
    if face in 'WE':
        return (0.0 if face == 'W' else w, round(t * T4 + T4O, 4))
    return (round(t * T3 + T3O, 4), 0.0 if face == 'S' else h)


_cache = {}


def master_pins(master):
    """{port: [(x, y) local per bit]} for any VM8 master: planned tiles exactly, others = the balanced placer formula
    over their spec pin_ranges (run_abi3_physical OT_PIN_BALANCE: lo + (hi - lo) * (k + 0.5) / n, bit order)."""
    if master in _cache:
        return _cache[master]
    out = {}
    if master in GEOM:
        pins, _ = layout(master)
        for (p, b), (fc, t) in pins.items():
            out.setdefault(p, {})[b] = local_xy(master, fc, t)
        out = {p: [v[b] for b in range(len(v))] for p, v in out.items()}
        dims = GEOM[master][:2]
    else:
        spec = None
        for cand in (CP / "codex_specs" / f"{master}_cx2.json", CP / "codex_specs" / f"{master}_cx.json",
                     ROOT / "physical/ref_tile" / master / "spec.json"):
            if cand.exists():
                spec = json.loads(cand.read_text())
                break
        w, h = spec["outline"]["w"], spec["outline"]["h"]
        dims = (w, h)
        for fc, ps in spec["pins"].items():
            for p in ps:
                n = 1 if p == spec["clock_port"] else plan.ports_of(master).get(p, (0, 1))[1]
                L = h if fc in 'WE' else w
                lo, hi = spec.get("pin_ranges", {}).get(p, (0, L))
                pos = [lo + (hi - lo) * (i + 0.5) / n for i in range(n)]
                out[p] = [((0.0 if fc == 'W' else w, y) if fc in 'WE' else (y, 0.0 if fc == 'S' else h)) for y in pos]
    _cache[master] = (out, dims)
    return _cache[master]


def instances():
    inst = {}
    for name, master, x, y, orient, conn in plan.INST:
        pins, (w, h) = master_pins(master)
        x = round(plan.VMW - w, 3) if x is None else x
        y = INST_Y.get(name, y)
        inst[name] = dict(master=master, x=x, y=round(y, 3), w=w, h=h, orient=orient, conn=conn)
    return inst


def hops():
    inst = instances()
    drv, rcv = {}, {}
    for name, d in inst.items():
        pins, _ = master_pins(d['master'])
        for port, net in d['conn'].items():
            direction = plan.ports_of(d['master'])[port][0]
            xy = []
            for (px, py) in pins[port]:
                if d['orient'] == 'MX':
                    py = d['h'] - py
                xy.append((d['x'] + px, d['y'] + py))
            (drv if direction == 'out' else rcv).setdefault(net, []).append((name, port, xy))
    rows = []
    for net, ds in drv.items():
        for (a, ap, axy) in ds:
            for (b, bp, bxy) in rcv.get(net, []):
                dist = [abs(p[0] - q[0]) + abs(p[1] - q[1]) for p, q in zip(axy, bxy)]
                rows.append(dict(net=net, frm=f"{a}.{ap}", to=f"{b}.{bp}", bits=len(dist),
                                 max_bit_um=round(max(dist), 1), mean_bit_um=round(sum(dist) / len(dist), 1),
                                 worst_bit=dist.index(max(dist))))
    over = []
    names = list(inst)
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            A, Bx = inst[a], inst[b]
            if (min(A['x'] + A['w'], Bx['x'] + Bx['w']) > max(A['x'], Bx['x']) + 1e-6
                    and min(A['y'] + A['h'], Bx['y'] + Bx['h']) > max(A['y'], Bx['y']) + 1e-6):
                over.append([a, b])
    return inst, rows, over


def spec_of(kit, pins):
    w, h, pg = GEOM[kit]
    old = json.loads((CP / "specs" / f"{kit}.json").read_text())
    name = f"{kit}_cx"
    faces = {}
    for p, v in plan.KITS[kit]['ports'].items():
        faces.setdefault(v[2], []).append(p)
    faces.setdefault('W', []).insert(0, 'ck')
    rng = {}
    for (p, b), (fc, t) in pins.items():
        c = local_xy(kit, fc, t)
        v = c[1] if fc in 'WE' else c[0]
        lo, hi = rng.get(p, (v, v))
        rng[p] = (min(lo, v), max(hi, v))
    job = dict(old["job"])
    job.update(owner="Claude:vm8-face-1013", branch="claude/vm8-face-1013", tag="cx1",
               views_to=f"physical/ref_tile/{name}/views", record_to=f"results/rtl/ref_tile/{name}")
    route = dict(pd=0.5, threads=8, peak_ram_gb=48, hold_margin_ns=0.01, pin_v="M3 M5", pin_h="M4", pin_min_tracks=1)
    if pg != 5.4:
        route["m5_pg_pitch"] = pg
    s = dict(name=name, top=kit, kind="tile", sources=old["sources"], clock_port="ck", reset_ports=[],
             outline=dict(w=w, h=h), pins=faces,
             pin_ranges={p: [round(a, 3), round(b, 3)] for p, (a, b) in sorted(rng.items())},
             io_tcl=f"{REL}/codex_specs/pins/{name}_pins.tcl", route=route, job=job, params={}, macros=[],
             children=[], inter=[], layer_cap="M5", outhold=True)
    if old.get("forwarded_clock"):
        s["forwarded_clock"] = True
    return s


def io_tcl(kit, pins):
    L = [f"# generated by {REL}/face_pin_plan.py ({kit}_cx) -- do not edit",
         "# locked per-bit pin plan: every slot's input pin, flop and output pins share its M4 tracks (W/E M4 only)"]
    for (p, b), (fc, t) in sorted(pins.items(), key=lambda kv: (kv[1][0], kv[1][1])):
        n = plan.KITS[kit]['ports'][p][1] if p != 'ck' else 1
        nm = p if n == 1 else f"{p}[{b}]"
        x, y = local_xy(kit, fc, t)
        layer = 'M4' if fc in 'WE' else 'M3'
        L.append(f"place_pin -pin_name {{{nm}}} -layer {layer} -location {{{x:.4f} {y:.4f}}} -force_to_die_boundary")
    return "\n".join(L) + "\n"


def main():
    (CP / "codex_specs" / "pins").mkdir(exist_ok=True)
    if len(sys.argv) > 2 and sys.argv[1] == "--pins-only":
        # one tile: its pin file + its hops only (the spec stays as edited by hand: later tags carry structural changes)
        kit = sys.argv[2]
        pins, st = layout(kit)
        (CP / "codex_specs" / "pins" / f"{kit}_cx_pins.tcl").write_text(io_tcl(kit, pins))
        inst, rows, over = hops()
        mine = [r for r in rows if kit[6:] in r['frm'].split('.')[0] or kit[6:] in r['to'].split('.')[0]]
        print(kit, GEOM[kit], {f: st[f] for f in 'WENS' if f in st}, 'overlap', over)
        for r in mine:
            print('  ', r)
        s = spec_of(kit, pins)
        print('pin_ranges', json.dumps(s['pin_ranges']), 'pins', json.dumps(s['pins']))
        return 1 if (over or any(r['max_bit_um'] > 500 for r in mine)) else 0
    res = dict(planning_only=True, tiles={})
    for kit in GEOM:
        pins, st = layout(kit)
        s = spec_of(kit, pins)
        (CP / "codex_specs" / f"{kit}_cx.json").write_text(json.dumps(s, indent=2) + "\n")
        (CP / "codex_specs" / "pins" / f"{kit}_cx_pins.tcl").write_text(io_tcl(kit, pins))
        res['tiles'][kit] = dict(outline=GEOM[kit][:2], m5_pg_pitch=GEOM[kit][2], **st)
    inst, rows, over = hops()
    res['instances'] = {k: {a: v[a] for a in ('master', 'x', 'y', 'w', 'h', 'orient')} for k, v in inst.items()}
    res['overlap'] = over
    res['hops'] = rows
    res['hops_above_500'] = [r for r in rows if r['max_bit_um'] > 500]
    res['note'] = ("per-bit Manhattan pin-to-pin distance; relay / root / slice pins from the balanced placer formula "
                   "over their spec pin_ranges (root + slices legacy plan, under redesign by their owners)")
    out = ROOT / "results/physical/vm8_codex_1013/face_pin_plan.json"
    out.write_text(json.dumps(res, indent=1) + "\n")
    for k, v in res['tiles'].items():
        print(k, v['outline'], 'sinks', v['sinks'], 'core/flop', v['core_um2_per_flop'],
              {f: (v[f]['pins'], v[f].get('cut_fraction')) for f in 'WENS' if f in v}, 'vcut', v['vertical_cut'])
    print('instances', len(inst), 'overlap', over, 'hops', len(rows), 'max', max(r['max_bit_um'] for r in rows))
    for r in sorted(rows, key=lambda r: -r['max_bit_um'])[:14]:
        print('  ', r)
    return 1 if (over or res['hops_above_500']) else 0


if __name__ == "__main__":
    sys.exit(main())
