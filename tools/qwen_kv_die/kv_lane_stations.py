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
            # AFTER src: a plain replica on the receiving root; one per load instance when one frame cannot reach them
            # all; every slice of the bus, atomically
            group = [P for P in siblings(src, std) if ('after', P) not in done]
            if not group:
                continue
            pend_e, pend_r, names, ok = [], [], [], True
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
                nmst = f'qkd_rlys_{S}'
                r = reach_of(S, classes)
                m = geo.macros[nmst]

                def cons_for(group_):
                    cs = []
                    used = sorted({i for li_ in group_ for i, _ in loads[li_]})
                    for i in used:
                        cs.append((geo.pin(nmst, f'a[{i}]') or geo.pin(nmst, 'a'), pts(P, 'b', i), r))
                    for li_ in group_:
                        for i, e in loads[li_]:
                            cs.append((geo.pin(nmst, f'b[{i}]') or geo.pin(nmst, 'b'), pts(*e), r))
                    return cs
                if not loads:
                    continue
                clusters = [sorted(loads)]
                progress = set()
                xy = geo.find(nmst, cons_for(clusters[0]))
                placed = [(clusters[0], xy)] if xy is not None else []
                if xy is None:
                    for li_ in sorted(loads):
                        xy_ = geo.find(nmst, cons_for([li_]))
                        if xy_ is None and os.environ.get('OT_KV_STATIONS_AFTER_PROGRESS', '1') == '1':
                            # KVR-PLACE 10-19 (kvs14r-131a7af2c-base: rly_pinfix_af_ES_r74_1__s0 -> seq__g_fan_2__u_fan.af,
                            # 954 um > 2 x 400: no ONE frame reaches both ends, refused 3 iterations running): a PROGRESS
                            # stage as BEFORE has -- within reach of P, as close to the load as the free space allows; the
                            # remaining N -> load span is repaired by a further AFTER stage in the next iteration
                            lp_ = [q for i, e in loads[li_] for q in pts(*e)]
                            used_ = sorted({i for i, _ in loads[li_]})
                            cin_ = [(geo.pin(nmst, f'a[{i}]') or geo.pin(nmst, 'a'), pts(P, 'b', i), r) for i in used_]
                            xy_ = geo.find(nmst, cin_, toward=(sum(q[0] for q in lp_) / len(lp_), sum(q[1] for q in lp_) / len(lp_)))
                            if xy_ is not None:
                                progress.add(li_)
                        if xy_ is None:
                            ok = False
                            refused.append(dict(op='after', station=P, master=nmst, load=li_, group=group,
                                                reason='no legal free frame within reach (bus slice group refused whole)'))
                            break
                        nm_ = f'{P}_y{tag}_{len(placed)}'
                        geo.put(xy_[0], xy_[1], m['W'], m['H'], nm_)
                        names.append(nm_)
                        placed.append(([li_], xy_))
                else:
                    geo.put(xy[0], xy[1], m['W'], m['H'], f'{P}_y{tag}')
                    names.append(f'{P}_y{tag}')
                if not ok:
                    break
                for k, (grp, xy_) in enumerate(placed):
                    N = f'{P}_y{tag}' if len(placed) == 1 else f'{P}_y{tag}_{k}'
                    pend_e.append(dict(op='after', at=P, inst=N, ck=ck, S=S, xy=xy_, loads=grp))
                    pend_r.append(dict(op='after', inst=N, of=P, pair=[src, dst], S=S, lane_kind='plain_receiving',
                                       predicted_master=nmst, master_before=pmst, loads=grp,
                                       within_reach='driver' if any(l_ in progress for l_ in grp) else 'both',
                                       x_um=xy_[0] / 1000, y_um=xy_[1] / 1000, w_um=m['W'] / 1000, h_um=m['H'] / 1000))
            if not ok:
                for nm_ in names:
                    geo.remove(nm_)
                continue
            for e in pend_e:
                geo.place[e['inst']] = (e['xy'][0], e['xy'][1], 'R0')
            edits += pend_e
            records += pend_r
        else:
            refused.append(dict(op='none', pair=[src, dst], reason='neither end is a relay replica'))
    return edits, records, refused


def apply_edits(pre_lines, place_text, edits, expr_bits):
    """netlist + placement edits on the pre-lane replica netlist"""
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
