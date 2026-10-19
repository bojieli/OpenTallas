#!/usr/bin/env python3
"""HKV-STATIONS 10-19: REAL relay stations for the KV forwarded lanes (no reservation-only records, no waivers).

kv_fwd_lanes.py builds the forwarded half-cycle lanes on the replica netlist, adapts illegal X mirrors (MY -> R0,
R180 -> MX) and refuses physical prep when kv_lane_reach.audit finds an incident transport bit over its width-class reach
(36:400 / 296:370 / 528:340 um, pin centre to pin centre, Manhattan).  This module turns every such failure into netlist
+ placement edits on the PRE-LANE replica netlist (closed relay standards qkd_rlys_<S>), after which kv_fwd_lanes re-forms
the lanes, so every inserted stage takes its lane role (hop-0 qkd_rlysh0_<S>, half-cycle qkd_rlysh_<S>, landing
qkd_landsh0?_<S>) and its planned E / K from the unchanged lane rules:

  BEFORE  load station Q (lane or plain replica) overreached from its driver: a new replica N on Q's clock root takes
          Q's input bus, Q takes N's output.  The SAME stage is inserted in every slice of the bus (rly_<bus>_<k>__s<j>)
          so no bus or record bundle is torn (netlist_relay_stages / die_relay_check count it; layer_compile recompiles
          the seam ages from the die table).
  AFTER   a landing / last station P overreaching block loads: a plain replica on the RECEIVING root after the landing
          (one more registered edge in the receiving region), forked per load instance when one frame cannot reach them
          all; every slice of the bus gets the same stage.
  SLOT    a wide landing with no planner frame (rly_aq_WS_73, rly_pvin_WN_3_40 in fa7fe4ff9): the landing is moved to a
          legal free frame of its own outline within reach of its driver and loads.

Every new / moved frame: R0 on the closed abstract's joint M3/M5 track lattice (kv_lane_orientation.origin_rules), no
overlap with any placed macro or earlier frame, inside the die, every data / forwarded-clock / epoch pin pair within its
class reach (the gate's own metric).  The audit then re-runs on the actual adapted placement with the inserted / moved
instances added to its scope; anything still failing is iterated (more stages) or refused.
"""
import math
import os
import re
from collections import defaultdict

import kv_lane_orientation as LO

C = LO.C
INST = re.compile(r'^(\s+)(\S+) (\S+) \((.*)\);\s*$')
CONN = re.compile(r'\.(\w+)\(([^()]*)\)')
PLACE = re.compile(r'^ot_mts::place \[\$_blk findInst (\S+)\] (\S+) (\S+) (\S+)\s*$')
STD = re.compile(r'^qkd_rlys_(\d+)$')
STEP_NM = 2160
MARGIN_UM = 4.0
SPINE_MAX = int(os.environ.get('OT_KV_AFTER_SPINE_MAX', '64'))   # stages on one AFTER spine (refuse beyond)
PROGRESS_MIN_NM = 50000                                             # a progress stage gains >= 50 um on its target


def reach_of(width, classes):
    return next((um for lim, um in classes if width <= lim), classes[-1][1])


def die_area(case):
    for f in ('run.tcl', 'run_pa.tcl'):
        p = case / f
        if p.exists():
            m = re.search(r'-die_area\s*\{\s*0\s+0\s+([\d.]+)\s+([\d.]+)\s*\}', p.read_text())
            if m:
                return round(float(m.group(1)) * 1000), round(float(m.group(2)) * 1000)
    return 13260672, 28475280         # kvs14p die (run.tcl initialize_floorplan)


def parse_place(text):
    out = {}
    for ln in text.split('\n'):
        m = PLACE.match(ln)
        if m:
            out[m.group(1)] = (round(float(m.group(2)) * 1000), round(float(m.group(3)) * 1000), m.group(4))
    return out


def pack(bits):
    """bit refs LSB first ('0' / '1' constants) -> Verilog expression, MSB first"""
    runs = []
    for b in bits:
        m = re.fullmatch(r'(\S+)\[(\d+)\]', b)
        if b in ('0', '1'):
            if runs and runs[-1][0] == "'" + b:
                runs[-1][1] += 1
            else:
                runs.append(["'" + b, 1, None])
        elif m and runs and runs[-1][0] == m.group(1) and runs[-1][2] == int(m.group(2)) - 1:
            runs[-1][2] += 1
        elif m:
            runs.append([m.group(1), int(m.group(2)), int(m.group(2))])
        else:
            raise ValueError(b)
    parts = []
    for n, lo, hi in reversed(runs):
        if n in ("'0", "'1"):
            parts.append(f"{lo}'b{n[1] * lo}")
        else:
            parts.append(f'{n}[{lo}]' if lo == hi else f'{n}[{hi}:{lo}]')
    return parts[0] if len(parts) == 1 else '{' + ', '.join(parts) + '}'


class Geo:
    """macro abstracts (nm), placement, occupancy bins and die box"""
    def __init__(self, macros, place, die, dirs):
        self.macros, self.place, self.die, self.dirs = macros, place, die, dirs
        self.step = 100000
        self.bins = defaultdict(list)
        self.rules = {}

    def build_bins(self, masters):
        self.bins.clear()
        for n, (x, y, o) in self.place.items():
            m = self.macros.get(masters.get(n))
            if m:
                self.put(x, y, m['W'], m['H'], n)

    def put(self, x, y, w, h, name):
        for a in range(int(x // self.step), int((x + w) // self.step) + 1):
            for b in range(int(y // self.step), int((y + h) // self.step) + 1):
                self.bins[a, b].append((x, y, w, h, name))

    def collides(self, x, y, w, h, ignore=()):
        for a in range(int(x // self.step), int((x + w) // self.step) + 1):
            for b in range(int(y // self.step), int((y + h) // self.step) + 1):
                for ox, oy, ow, oh, nm in self.bins.get((a, b), ()):
                    if nm in ignore:
                        continue
                    if x < ox + ow and ox < x + w and y < oy + oh and oy < y + h:
                        return True
        return False

    def rule(self, master):
        if master not in self.rules:
            self.rules[master] = LO.origin_rules(self.macros[master], 'R0')
        return self.rules[master]

    def pin(self, master, name, orient='R0'):
        """pin centre offsets (nm) of a master pin in an orientation"""
        m = self.macros[master]
        p = m['pd'].get(name)
        if p is None:
            return []
        return [((q[0] + q[2]) / 2, (q[1] + q[3]) / 2) for _, r in p['rects']
                for q in [C.transform_rect(r, orient, m['W'], m['H'])]]

    def ep_points(self, inst, master, port, bit):
        pl = self.place.get(inst)
        m = self.macros.get(master)
        if pl is None or m is None:
            return []
        x, y, o = pl
        pts = self.pin(master, f'{port}[{bit}]', o) or (self.pin(master, port, o) if bit == 0 else [])
        return [(x + a, y + b) for a, b in pts]

    def remove(self, name):
        for k in list(self.bins):
            self.bins[k] = [b for b in self.bins[k] if b[4] != name]

    def find(self, master, cons, ignore=(), toward=None):
        """legal free R0 origin of `master` meeting every (pin offsets, external points, reach_um) constraint, or None.
        Manhattan |dx| + |dy| = max over the four sign forms, so the worst constraint is O(1) per candidate."""
        m = self.macros[master]
        W, H = m['W'], m['H']
        forms = []
        for offs, pts, r in cons:
            for (dx, dy) in offs:
                for (X, Y) in pts:
                    forms.append((X - dx, Y - dy, (r - MARGIN_UM) * 1000))
        if not forms:
            return None
        k = [max(s1 * fx + s2 * fy - fr for fx, fy, fr in forms) for s1 in (1, -1) for s2 in (1, -1)]
        # feasible box (necessary): |fx - ox| + |fy - oy| <= fr for every form
        lox = max(fx - fr for fx, fy, fr in forms)
        hix = min(fx + fr for fx, fy, fr in forms)
        loy = max(fy - fr for fx, fy, fr in forms)
        hiy = min(fy + fr for fx, fy, fr in forms)
        lox, loy = max(lox, 0), max(loy, 0)
        hix, hiy = min(hix, self.die[0] - W), min(hiy, self.die[1] - H)
        if lox > hix or loy > hiy:
            return None
        rule = self.rule(master)

        def snaps(v, axis):
            P = rule[axis]['joint_period_nm']
            base = math.floor(v / P) * P
            return sorted((base + r_ + d for r_ in rule[axis]['legal_origins_mod_joint_nm'] for d in (-P, 0, P)),
                          key=lambda z: abs(z - v))[:2]
        cx, cy = (lox + hix) / 2, (loy + hiy) / 2
        xs = [cx + i * STEP_NM * s for i in range(int((hix - lox) / 2 / STEP_NM) + 2) for s in ((1, -1) if i else (1,))]
        ys = [cy + i * STEP_NM * s for i in range(int((hiy - loy) / 2 / STEP_NM) + 2) for s in ((1, -1) if i else (1,))]
        tx, ty = (toward[0] - W / 2, toward[1] - H / 2) if toward else (cx, cy)
        cands = sorted(((x, y) for x in xs for y in ys), key=lambda p: abs(p[0] - tx) + abs(p[1] - ty))
        seen = set()
        for x0, y0 in cands:
            for x in snaps(x0, 'x'):
                for y in snaps(y0, 'y'):
                    if (x, y) in seen:
                        continue
                    seen.add((x, y))
                    if x < 0 or y < 0 or x + W > self.die[0] or y + H > self.die[1]:
                        continue
                    if max(k[0] - (x + y), k[1] - (x - y), k[2] - (-x + y), k[3] - (-x - y)) > 0:
                        continue
                    if self.collides(x, y, W, H, ignore):
                        continue
                    return x, y
        return None


def lane_roles(new):
    return {c: mst for c, (mst, _) in new.items()}


class Net:
    """bit-level connectivity of the rendered (laned) netlist: driver / load endpoints with masters"""
    def __init__(self, lines, dirs, expr_bits):
        self.wires = {}
        for ln in lines:
            m = re.match(r'\s*wire\s+\[(\d+):0\]\s+(\S+);', ln)
            if m:
                self.wires[m.group(2)] = int(m.group(1)) + 1
        self.insts = {}
        for ln in lines:
            m = INST.match(ln)
            if m and m.group(2) not in ('module', 'wire', 'input', 'output', 'inout'):
                self.insts[m.group(3)] = (m.group(2), dict(CONN.findall(m.group(4))))
        self.drv, self.lds = {}, defaultdict(list)
        for nm, (mst, cs) in self.insts.items():
            for p, v in cs.items():
                d = self.direction(mst, p, dirs)
                for i, b in enumerate(expr_bits(v, self.wires)):
                    if b in ('0', '1'):
                        continue
                    if d in ('OUTPUT', 'INOUT'):
                        self.drv.setdefault(b, (nm, p, i))
                    if d in ('INPUT', 'INOUT'):
                        self.lds[b].append((nm, p, i))
        self.expr_bits = expr_bits

    @staticmethod
    def direction(mst, p, dirs):
        if STD.match(mst):
            return 'OUTPUT' if p == 'b' else 'INPUT'
        if mst.startswith(('qkd_rlysh', 'qkd_landsh')):
            return 'OUTPUT' if p in ('b', 'eb', 'ck_o', 'fault', 'tie_hi', 'tie_lo') else 'INPUT'
        return dirs.get(mst, {}).get(p, 'INOUT')

    def bits(self, inst, port):
        return self.expr_bits(self.insts[inst][1].get(port, ''), self.wires)


def siblings(name, std_names):
    base = re.sub(r'__s\d+$', '', name)
    if base == name:
        return [name]
    pat = re.compile(re.escape(base) + r'__s\d+$')
    return sorted(n for n in std_names if pat.match(n))


def plan_repairs(viol_pairs, pre_lines, lane_lines, new, lanes, geo, dirs, expr_bits, classes, tag, cache):
    """viol_pairs: {(src_inst, dst_inst)} transport pairs over reach on the adapted placement.
    Returns (edits, records, refused): edits = list of ('before', Q, N, ck, S, xy) / ('after', P, N, ck, S, xy, loads)."""
    net = Net(lane_lines, dirs, expr_bits)
    pre = {}
    for li, ln in enumerate(pre_lines):
        m = INST.match(ln)
        if m and m.group(2) not in ('module', 'wire', 'input', 'output', 'inout'):
            pre[m.group(3)] = (m.group(2), dict(CONN.findall(m.group(4))), li)
    std = {n for n, (mst, _, _) in pre.items() if STD.match(mst)}
    lane_of, pos_of = {}, {}
    for L in lanes:
        for j, c in enumerate(L['stations']):
            lane_of[c], pos_of[c] = L, j
    roles = lane_roles(new)
    edits, records, refused, done = [], [], [], set()
    masters = {n: v[0] for n, v in net.insts.items()}

    def pts(inst, port, bit):
        return geo.ep_points(inst, masters[inst], port, bit)

    def ck_of(inst):
        v = pre[inst][1].get('ck', '').strip()
        return v.split('[')[0]

    # ---- AFTER planning (KVR-PLACE2 10-19): one frame / forks / tapped spine, then equal-depth pads ----
    def _cen(ps):
        return (sum(x for x, _ in ps) / len(ps), sum(y for _, y in ps) / len(ps))

    def _dist(a, b):
        return abs(a[0] - b[0]) + abs(a[1] - b[1])

    def _lcons(nmst, r, loads, grp):
        return [(geo.pin(nmst, f'b[{i}]') or geo.pin(nmst, 'b'), pts(*e), r) for l_ in grp for i, e in loads[l_]]

    def _scons(nmst, r, src, smst, bits):
        # every NET bit of the source output reaches the stage input (spare bits are nets too: the audit measures them)
        return [(geo.pin(nmst, f'a[{i}]') or geo.pin(nmst, 'a'), geo.ep_points(src, smst, 'b', i), r) for i in bits]

    def _take(nmst, name, xy, names):
        m_ = geo.macros[nmst]
        geo.put(xy[0], xy[1], m_['W'], m_['H'], name)
        geo.place[name] = (xy[0], xy[1], 'R0')
        names.append(name)

    def _drop(name, names):
        geo.remove(name)
        geo.place.pop(name, None)
        names.remove(name)

    def after_stages(P, pmst, S, nmst, r, loads, tag, names):
        """stage dicts (inst, at, loads = the loads rewired to it, taps, xy, depth, side, role) or None"""
        sb = [i for i, b in enumerate(net.bits(P, 'b')) if b not in ('0', '1')]
        lds = sorted(loads)
        xy = geo.find(nmst, _scons(nmst, r, P, pmst, sb) + _lcons(nmst, r, loads, lds))
        if xy is not None:
            _take(nmst, f'{P}_y{tag}', xy, names)
            return [dict(inst=f'{P}_y{tag}', at=P, loads=lds, taps=list(lds), xy=xy, depth=1, side='both', role='single')]
        forks = []
        for k, l_ in enumerate(lds):
            xy = geo.find(nmst, _scons(nmst, r, P, pmst, sb) + _lcons(nmst, r, loads, [l_]))
            if xy is None:
                break
            _take(nmst, f'{P}_y{tag}_{k}', xy, names)
            forks.append(dict(inst=f'{P}_y{tag}_{k}', at=P, loads=[l_], taps=[l_], xy=xy, depth=1, side='both', role='fork'))
        else:
            return forks
        for st in forks:
            _drop(st['inst'], names)
        if os.environ.get('OT_KV_STATIONS_AFTER_PROGRESS', '1') != '1':
            return None
        lpts = {l_: [q for i, e in loads[l_] for q in pts(*e)] for l_ in lds}
        if any(not v for v in lpts.values()):
            return None
        stages, src, smst, bits, remaining = [], P, pmst, sb, lds
        bofs = geo.pin(nmst, 'b[0]') or geo.pin(nmst, 'b')
        while remaining:
            if len(stages) >= SPINE_MAX:
                return None
            sp = [q for i in bits for q in geo.ep_points(src, smst, 'b', i)]
            if not sp:
                return None
            sc = _cen(sp)
            order = sorted(remaining, key=lambda l_: (_dist(_cen(lpts[l_]), sc), l_))
            cin = _scons(nmst, r, src, smst, bits)
            best = None
            for k in range(1, len(order) + 1):
                tw = _cen(lpts[order[k]]) if k < len(order) else None
                xy = geo.find(nmst, cin + _lcons(nmst, r, loads, order[:k]), toward=tw)
                if xy is None:
                    break
                best = (k, xy)
            if best is None:
                tgt = _cen(lpts[order[0]])
                xy = geo.find(nmst, cin, toward=tgt)
                if xy is None or not bofs:
                    return None
                if _dist(_cen([(xy[0] + a, xy[1] + b) for a, b in bofs]), tgt) > _dist(sc, tgt) - PROGRESS_MIN_NM:
                    return None                      # no progress toward the nearest load: refuse, never loop
                best = (0, xy)
            k, xy = best
            nm = f'{P}_y{tag}_c{len(stages)}'
            _take(nmst, nm, xy, names)
            stages.append(dict(inst=nm, at=src, loads=list(order), taps=order[:k], xy=xy, depth=len(stages) + 1,
                               side='both' if k else 'driver', role='spine'))
            remaining, src, smst, bits = order[k:], nm, nmst, list(range(S))
        return stages

    def pad_to(pl, D, tag, names):
        """equal depth D on every load of the slice: PAD stages from each load's tap (each within reach of the
        previous stage and of the load, so they sit beside the load)"""
        nmst, S, loads, P = pl['nmst'], pl['S'], pl['loads'], pl['P']
        r = reach_of(S, classes)
        tapped = [(l_, st) for st in list(pl['stages']) for l_ in st['taps']]
        for li_, (l_, st) in enumerate(sorted(tapped, key=lambda x: x[0])):
            if st['depth'] >= D:
                continue
            st['taps'].remove(l_)
            prev, tw = st['inst'], _cen([q for i, e in loads[l_] for q in pts(*e)])
            for k in range(D - st['depth']):
                xy = geo.find(nmst, _scons(nmst, r, prev, nmst, range(S)) + _lcons(nmst, r, loads, [l_]), toward=tw)
                if xy is None:
                    return False
                nm = f'{P}_y{tag}_p{li_}_{k}'
                _take(nmst, nm, xy, names)
                pl['stages'].append(dict(inst=nm, at=prev, loads=[l_], taps=[l_] if k == D - st['depth'] - 1 else [],
                                         xy=xy, depth=st['depth'] + k + 1, side='both', role='pad'))
                prev = nm
        return True
    for (src, dst) in sorted(viol_pairs):
        if dst in std:
            # BEFORE dst: every slice of dst's bus position, atomically (a torn bus is never emitted)
            group = [Q for Q in siblings(dst, std) if ('before', Q) not in done]
            if not group:
                continue
            plan = []
            for Q in group:
                done.add(('before', Q))
                S = int(STD.match(pre[Q][0]).group(1))
                L, j = lane_of.get(Q), pos_of.get(Q)
                qrole = roles.get(Q, pre[Q][0])
                if L is None:
                    kind, nmst, qmst = 'plain', f'qkd_rlys_{S}', qrole
                elif j == 0 and L['src_kind'] != 'station':
                    kind, nmst = 'first', f'qkd_rlysh0_{S}'
                    qmst = qrole.replace('qkd_rlysh0_', 'qkd_rlysh_').replace('qkd_landsh0_', 'qkd_landsh_')
                else:
                    kind, nmst, qmst = 'mid', f'qkd_rlysh_{S}', qrole
                r = reach_of(S, classes)
                cin, cout, qa = [], [], []
                for i, b in enumerate(net.bits(Q, 'a')):
                    if b in ('0', '1'):
                        continue
                    d = net.drv.get(b)
                    if d is not None:
                        cin.append((geo.pin(nmst, f'a[{i}]') or geo.pin(nmst, 'a'), pts(*d), r))
                    qp = geo.ep_points(Q, qmst, 'a', i)
                    qa += qp
                    cout.append((geo.pin(nmst, f'b[{i}]') or geo.pin(nmst, 'b'), qp, r))
                if kind in ('mid', 'first') and qmst.startswith(('qkd_rlysh_', 'qkd_landsh_')):
                    cout.append((geo.pin(nmst, 'ck_o'), geo.ep_points(Q, qmst, 'ckf', 0), r))
                    cout.append((geo.pin(nmst, 'eb'), geo.ep_points(Q, qmst, 'ea', 0), r))
                if kind == 'mid' and j:
                    P = L['stations'][j - 1]
                    cin.append((geo.pin(nmst, 'ckf'), pts(P, 'ck_o', 0), r))
                    cin.append((geo.pin(nmst, 'ea'), pts(P, 'eb', 0), r))
                N = f'{Q}_x{tag}'
                xy, reach_side = geo.find(nmst, cin + cout), 'both'
                if xy is None and qa:
                    # progress stage: driver side within reach, as close to Q as the free space allows; the remaining
                    # N -> Q span is repaired by a further real stage in the next iteration
                    toward = (sum(p[0] for p in qa) / len(qa), sum(p[1] for p in qa) / len(qa))
                    xy, reach_side = geo.find(nmst, cin, toward=toward), 'driver'
                if xy is None:
                    plan = None
                    refused.append(dict(op='before', station=Q, master=nmst, group=group,
                                        reason='no legal free frame within driver reach (bus slice group refused whole)'))
                    break
                m = geo.macros[nmst]
                geo.put(xy[0], xy[1], m['W'], m['H'], N)
                plan.append((Q, N, S, kind, nmst, xy, m, reach_side))
            if plan is None:
                for Q in group:
                    geo.remove(f'{Q}_x{tag}')
                continue
            for Q, N, S, kind, nmst, xy, m, reach_side in plan:
                geo.place[N] = (xy[0], xy[1], 'R0')
                edits.append(dict(op='before', at=Q, inst=N, ck=ck_of(Q), S=S, xy=xy))
                records.append(dict(op='before', inst=N, of=Q, pair=[src, dst], S=S, lane_kind=kind,
                                    predicted_master=nmst, within_reach=reach_side, x_um=xy[0] / 1000,
                                    y_um=xy[1] / 1000, w_um=m['W'] / 1000, h_um=m['H'] / 1000))
        elif src in std:
            # AFTER src: a plain replica on the receiving root -- one frame for all loads, else one per load (forks),
            # else (KVR-PLACE2 10-19) a TAPPED SPINE planned whole in this iteration: P -> c0 -> c1 -> ... toward the
            # loads, each load tapped from the first stage that reaches it.  Every load of every slice of the bus then
            # gets PAD stages up to the group's deepest tap, so the bus keeps ONE age (kv_static_die words carry one age;
            # a held calendar word seen at two ages would be read outside its hold window).  kvs14r-f9ef813ab-kvrplace:
            # ks_acal -> the 8 expanded ASTK eps span ~10 mm of strip; one progress stage per iteration and per load
            # (596ce7008) left 420 bits over reach after 6 iterations.
            group = [P for P in siblings(src, std) if ('after', P) not in done]
            if not group:
                continue
            plans, names, ok = [], [], True
            for P in group:
                done.add(('after', P))
                S = int(STD.match(pre[P][0]).group(1))
                L = lane_of.get(P)
                ck = f'n_clk_core_{L["dst_tree"]}' if L is not None else ck_of(P)
                pmst = roles.get(P, pre[P][0])
                loads = defaultdict(list)                     # load inst -> [(bit i, ep)]
                for i, b in enumerate(net.bits(P, 'b')):
                    if b in ('0', '1'):
                        continue
                    for e in net.lds.get(b, ()):
                        if e[0] != P:
                            loads[e[0]].append((i, e))
                if not loads:
                    continue
                nmst = f'qkd_rlys_{S}'
                stages = after_stages(P, pmst, S, nmst, reach_of(S, classes), loads, tag, names)
                if stages is None:
                    ok = False
                    refused.append(dict(op='after', station=P, master=nmst, loads=sorted(loads), group=group,
                                        reason='no legal free frame within reach / spine made no progress '
                                               '(bus slice group refused whole)'))
                    break
                plans.append(dict(P=P, S=S, ck=ck, pmst=pmst, nmst=nmst, loads=loads, stages=stages))
            if ok and plans:
                D = max(st['depth'] for pl in plans for st in pl['stages'] if st['taps'])
                for pl in plans:
                    if not pad_to(pl, D, tag, names):
                        ok = False
                        refused.append(dict(op='after', station=pl['P'], master=pl['nmst'], group=group,
                                            reason=f'no legal free pad frame (equal depth {D})'))
                        break
            if not ok:
                for nm_ in names:
                    geo.remove(nm_)
                    geo.place.pop(nm_, None)
                continue
            for pl in plans:
                m = geo.macros[pl['nmst']]
                for st in pl['stages']:
                    edits.append(dict(op='after', at=st['at'], inst=st['inst'], ck=pl['ck'], S=pl['S'], xy=st['xy'],
                                      loads=st['loads'], level=st['depth'] - 1))
                    records.append(dict(op='after', inst=st['inst'], of=st['at'], pair=[src, dst], S=pl['S'],
                                        lane_kind='plain_receiving', predicted_master=pl['nmst'],
                                        master_before=pl['pmst'] if st['at'] == pl['P'] else pl['nmst'],
                                        loads=st['loads'], taps=st['taps'], depth=st['depth'], role=st['role'],
                                        within_reach=st['side'], x_um=st['xy'][0] / 1000, y_um=st['xy'][1] / 1000,
                                        w_um=m['W'] / 1000, h_um=m['H'] / 1000))
        else:
            refused.append(dict(op='none', pair=[src, dst], reason='neither end is a relay replica'))
    return edits, records, refused


def apply_edits(pre_lines, place_text, edits, expr_bits):
    """netlist + placement edits on the pre-lane replica netlist.  Chained AFTER stages (spine / pads: 'level' = depth - 1)
    are applied level by level, so a stage planned AFTER another inserted stage finds its driver's line."""
    levels = sorted({e.get('level', 0) for e in edits})
    if len(levels) > 1:
        lines_, pt_ = list(pre_lines), place_text
        for lv in levels:
            lines_, pt_ = apply_edits(lines_, pt_, [e for e in edits if e.get('level', 0) == lv], expr_bits)
        return lines_, pt_
    wires = {}
    for ln in pre_lines:
        m = re.match(r'\s*wire\s+\[(\d+):0\]\s+(\S+);', ln)
        if m:
            wires[m.group(2)] = int(m.group(1)) + 1
    where = {}
    for li, ln in enumerate(pre_lines):
        m = INST.match(ln)
        if m and m.group(2) not in ('module', 'wire', 'input', 'output', 'inout'):
            where[m.group(3)] = li
    lines = list(pre_lines)
    add_inst, add_wire, add_place = defaultdict(list), [], []

    def conns(li):
        m = INST.match(lines[li])
        return m.group(1), m.group(2), m.group(3), CONN.findall(m.group(4))

    def emit(li, ind, mst, nm, cs):
        lines[li] = f'{ind}{mst} {nm} (' + ', '.join(f'.{p}({v})' for p, v in cs) + ');'
    after_groups = defaultdict(list)
    for e in edits:
        if e['op'] == 'before':
            li = where[e['at']]
            ind, mst, nm, cs = conns(li)
            a = dict(cs)['a']
            o = f'n_{e["inst"]}__o'
            add_wire.append(f'  wire [{e["S"] - 1}:0] {o};')
            emit(li, ind, mst, nm, [(p, (f'{o}[{e["S"] - 1}:0]' if p == 'a' else v)) for p, v in cs])
            add_inst[li].append(f'{ind}qkd_rlys_{e["S"]} {e["inst"]} (.ck({e["ck"]}), .a({a}), .b({o}[{e["S"] - 1}:0]));')
        else:
            after_groups[e['at']].append(e)
    for P, es in after_groups.items():
        li = where[P]
        ind, mst, nm, cs = conns(li)
        bb = expr_bits(dict(cs)['b'], wires)
        for e in es:
            o = f'n_{e["inst"]}__o'
            add_wire.append(f'  wire [{e["S"] - 1}:0] {o};')
            add_inst[li].append(f'{ind}qkd_rlys_{e["S"]} {e["inst"]} (.ck({e["ck"]}), .a({dict(cs)["b"]}), '
                                f'.b({o}[{e["S"] - 1}:0]));')
            sub = {b: f'{o}[{i}]' for i, b in enumerate(bb) if b not in ('0', '1')}
            for L in e['loads']:
                lj = where[L]
                ind2, mst2, nm2, cs2 = conns(lj)
                out = []
                for p, v in cs2:
                    bits = expr_bits(v, wires) if v.strip() else []
                    if any(b in sub for b in bits):
                        v = pack([sub.get(b, b) for b in bits])
                    out.append((p, v))
                emit(lj, ind2, mst2, nm2, out)
    for e in edits:
        x, y = e['xy']
        add_place.append(f'ot_mts::place [$_blk findInst {e["inst"]}] {x / 1000:.3f} {y / 1000:.3f} R0')
    res = []
    for li, ln in enumerate(lines):
        res.append(ln)
        res.extend(add_inst.get(li, ()))
    k = max(i for i, ln in enumerate(res) if re.match(r'\s*wire\b', ln))
    res[k + 1:k + 1] = add_wire
    pt = place_text.rstrip('\n') + '\n' + '\n'.join(add_place) + '\n'
    return res, pt


def move(place_text, inst, xy):
    pat = re.compile(r'^(ot_mts::place \[\$_blk findInst ' + re.escape(inst) + r'\] )\S+ \S+ \S+(\s*)$', re.M)
    out, n = pat.subn(lambda m: f'{m.group(1)}{xy[0] / 1000:.3f} {xy[1] / 1000:.3f} R0{m.group(2)}', place_text)
    if n != 1:
        raise ValueError(f'{inst}: {n} placement lines')
    return out
