#!/usr/bin/env python3
"""Per-pair die hop check (owner 2026-10-13, el1013-pinreg-audit.log "pairs"): the die statement evaluated for ONE
connected pair of placed instances with each side's own numbers, instead of a flat 500 um for every hop.

A view is reduced to a small TIMING TABLE (view_timing.json, written by pinreg_pairs.py from the view's Liberty ETMs and
its insertion.json; nothing here is estimated):
    clocks[pin]   R_tt / R_ff = mean clock arrival at the boundary registers (insertion.json), spread, n
    buses[bus]    arcs: per related clock pin and active edge   O (latest clock pin -> output, TT)   l (earliest, FF)
                                                                 S (setup at the input pin, TT)        h (hold, FF)
    clock_out[bus] a forwarded clock: delay clock pin edge -> output transition (TT and FF, min / max)

Three link models, chosen from the DIE NETLIST (who drives the capturing clock pin), never from a name:
  TREE   both clock pins hang on the same die clock net.  The die delivers that clock insertion-compensated
         (arrival at X's pin = phi - R_X), so with o = O - R_A and s = S + R_B:
             setup   o_A + w L + s_B              <=  W - U - SKEW      W = T (same active edge) or T/2
             hold    (l_A - R_A) + w_h L - (h_B - R_B) + (T - W)  >=  U_h + SKEW_h      (FF)
         SKEW 90 ps when both R <= 300 ps (one clock level), 150 ps when either is deeper (own trunk tap).
  FWD    the capturing clock pin of B is driven by a clock OUTPUT of A that derives from A's launching clock (a
         forwarded / source-synchronous link: the clock travels beside its bus; no insertion compensation, no tree skew):
             setup   O_A + w Ld (1 + ocv) + S_B   <=  W + F_A + w Lc (1 - ocv) - U
             hold    l_A + w_f Ld (1 - ocv) - h_B + (T - W)  >=  F_A + w_f Lc (1 + ocv) + U_hf       (FF)
         F = clock pin edge -> forwarded edge that B captures on; W from the two ideal edge times (an inverted forward
         with same-edge capture gives W = T/2: rtl/common/ot_fwd_link_stage.sv).
  REV    the launching clock pin of A is driven by a clock output of B (the clock runs against the data): the round
         trip G_B + w Lc + O_A + w Ld + S_B must fit W.
  CROSS  the two clock pins have unrelated sources (a CDC FIFO boundary): no synchronous check, reported.
A side without a table entry (placeholder / generated master) takes the SHARE of the flat rule: 151.7 ps a side, which
makes two placeholders pass at exactly 500 um (the default stays 500 um for them); its hold side is not judged.

Constants are the sign-off ones (tools/budgets/common.py): T 833.333, U 60, wire 0.76 ps/um (TT, buffered die wire),
FF wire credit 0.112 ps/um, hold 50 + 50 (rule H1), OCV 5 %, FF hold uncertainty 25.
"""
import json
import math
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TABLE = 'results/arch/pinreg_audit_1013/pairs/view_timing.json'     # default table (env OT_PAIR_TIMING overrides)
T_PS = 833.333
U_SETUP = 60.0
SKEW_SAME = 90.0            # both insertions <= LEVEL_PS: one clock level
SKEW_DEEP = 150.0           # a tile on its own trunk tap (tools/budgets/common.py SKEW_INTER_PS)
LEVEL_PS = 300.0
W_TT = 0.76                 # ps/um, buffered die wire at TT
W_FF_CREDIT = 0.112         # ps/um, FF wire credit for hold (common.py WIRE_FF_CREDIT_PS_PER_UM)
W_FF = 0.76 * 0.82          # ps/um, the same buffered wire at FF (FF / TT insertion ratio 0.81-0.85, Qwen views)
HOLD_TREE = 100.0           # rule H1: 50 hold margin + 50 die skew
HOLD_FWD = 25.0             # FF hold uncertainty (no tree between the two ends)
OCV = 0.05
DEFAULT_UM = 500.0
AVAIL = T_PS - U_SETUP - SKEW_SAME                 # 683.3 ps
SHARE = (AVAIL - W_TT * DEFAULT_UM) / 2            # 151.7 ps a side at the full 500 um
CLOCK_CLS = ('clock', 'col_clock', 'fclk', 'clock_trunk')


def bus_of(pin):
    return re.sub(r'\[[\d:]+\]$', '', pin)


def load_table(path=None):
    """master -> timing record; {} when there is no table (every pair then takes the flat default)"""
    p = Path(path or os.environ.get('OT_PAIR_TIMING') or ROOT / TABLE)
    if not p.exists():
        return {}
    return json.loads(p.read_text())['masters']


def _edge_time(e):
    return 0.0 if e == 'r' else T_PS / 2


def _window(launch_t, cap_edge_t):
    """ideal time from the launch edge to the first capture edge strictly after it"""
    w = (cap_edge_t - launch_t) % T_PS
    return w if w > 1e-6 else T_PS


def _fwd_arc(co, cap_edge, corner):
    """the forwarded transition `cap_edge` at the clock output: (input edge, min, max), on the hardware sense the table
    records (inv: rtl/common/ot_fwd_link_stage.sv ot_fwd_clk_inv; buf: a clock pass-through)."""
    arcs = co.get(corner) or {}
    sense = co.get('sense')
    if sense is None:
        return None
    k = (('f' if cap_edge == 'r' else 'r') if sense == 'inv' else cap_edge) + cap_edge
    return (k[0], arcs[k][0], arcs[k][1]) if k in arcs else None


class Die:
    """the clock relation of two instance pins, from the die's clock nets: drivers[(inst, pin bus)] = (drv inst, drv pin
    bus, um, net).  A clock pin without a recorded driver hangs on the die's own tree (net = its name or None)."""

    def __init__(self, table, master_of, clock_drivers=None, clock_net=None):
        self.t = table
        self.master_of = master_of
        self.drv = clock_drivers or {}
        self.net = clock_net or {}
        self.fwd_pairs = {(d[0], k[0]) for k, d in self.drv.items()}      # (clock driver instance, clocked instance)

    def source(self, inst, pin):
        d = self.drv.get((inst, bus_of(pin)))
        if d:
            return ('pin', d[0], d[1]), d
        return ('tree', self.net.get((inst, bus_of(pin)))), None

    def relation(self, a, ca, b, cb):
        """-> (model, info): TREE / FWD / REV / CROSS for launch clock pin ca of instance a, capture pin cb of b"""
        sa, da = self.source(a, ca)
        sb, db = self.source(b, cb)
        if sa == sb:                 # one net (a tile that takes its own forwarded column clock back is on that tree)
            return 'TREE', None
        if db and db[0] == a:
            return 'FWD', db
        if da and da[0] == b:
            return 'REV', da
        if a == b and bus_of(ca) == bus_of(cb):
            return 'TREE', None
        return 'CROSS', (sa, sb)


RESET_PIN = re.compile(r'(^|_)a?rst(_n)?$|^rs+$')


def side(table, master, bus, want, how=None):
    """arcs of a die port that launch (want='O') or capture (want='S'); None when the master has no table entry.
    The die port is bound to the view's pins as the die binds it (tools/hier_contract/die_views.py): the view bus of
    that name (exact); else the view buses <port>_* of the port's direction (prefix); else EVERY data bus of that
    direction (direction: the die master's port names are not the element's, representative_by_role) - the last two
    take the worst arc per clock and edge, an upper bound from real arcs.  `how` (a list) receives the binding used."""
    m = table.get(master)
    if not m:
        return None
    name = bus_of(bus)
    d = 'output' if want == 'O' else 'input'
    b = m['buses'].get(name)
    kind = 'exact'
    if b:
        cand = [b]
    else:
        cand = [v for k, v in m['buses'].items() if k.startswith(name + '_') and v['dir'] == d]
        kind = 'prefix'
        if not cand:
            cand = [v for k, v in m['buses'].items() if v['dir'] == d and not RESET_PIN.search(k)]
            kind = 'direction'
    worst = {}
    for v in cand:
        for a in v['arcs']:
            if a.get(want) is None:
                continue
            w = worst.setdefault((a['clk'], a['edge']), dict(clk=a['clk'], edge=a['edge'], O=None, l=None, S=None, h=None))
            for k, f in (('O', max), ('S', max), ('h', max), ('l', min)):
                if a.get(k) is not None:
                    w[k] = a[k] if w[k] is None else f(w[k], a[k])
    if how is not None:
        how.append(kind if len(cand) > 1 or kind == 'exact' else kind + ' (1 bus)')
    return list(worst.values())


def check(die, hop):
    """hop: dict(a=(inst, master, pin), b=(inst, master, pin), um=L or None) -> verdict record.
    setup_ps / hold_ps are MARGINS (>= 0 passes); reach_um is the longest wire this pair closes at."""
    (ia, ma, pa), (ib, mb, pb) = hop['a'], hop['b']
    L = hop.get('um')
    t = die.t
    how = []
    A, B = side(t, ma, pa, 'O', how), side(t, mb, pb, 'S', how)
    rec = dict(real=(A is not None) + (B is not None))
    if any(not h_.startswith('exact') for h_ in how):
        rec['bind'] = 'direction' if any(h_.startswith('direction') for h_ in how) else 'prefix'
    if L is None:
        return dict(rec, model='NOPIN', status='n/e', note='no pin geometry on one end (abutted / generated master)')
    if (A is None or B is None) and A != [] and B != [] and ((ia, ib) in die.fwd_pairs or (ib, ia) in die.fwd_pairs):
        A = B = None            # a forwarded link with a placeholder end: no tree share applies, the flat rule judges it
        rec['note'] = 'forwarded link with a placeholder end: flat rule'
    if A is None and B is None:
        ok = L <= DEFAULT_UM
        return dict(rec, model='DEFAULT', status='pass' if ok else 'fail', setup_ps=round(W_TT * (DEFAULT_UM - L), 1),
                    reach_um=DEFAULT_UM, o=None, s=None)
    if A == [] or B == []:
        return dict(rec, model='NOARC', status='n/e', note='the view has no clocked arc on this pin (constant / async / clock)')
    for m_, arcs in ((ma, A), (mb, B)):
        for arc in arcs or []:
            c = t[m_]['clocks'].get(arc['clk'])
            if c is not None and c.get('R_tt') is None:        # a clock tree whose boundary insertion is not measured
                return dict(rec, model='UNMEASURED', status='n/e', unmeasured=m_,
                            note=f"{m_}.{arc['clk']}: clock insertion not measured (no insertion.json): not judged, never estimated")
    best = None
    cross = None
    for a in (A or [None]):
        for b in (B or [None]):
            r = _pair(die, t, ia, ma, a, ib, mb, b, L)
            if r['model'] == 'CROSS':
                cross = r
                continue
            if best is None or min(r['setup_ps'], r.get('hold_ps') if r.get('hold_ps') is not None else 1e9) < \
                    min(best['setup_ps'], best.get('hold_ps') if best.get('hold_ps') is not None else 1e9):
                best = r
    if best is None:
        return dict(rec, **cross, status='cross')
    st = 'pass'
    if best['setup_ps'] < 0:
        st = 'fail'
    if best.get('hold_ps') is not None and best['hold_ps'] < 0:
        st = 'fail' if st == 'fail' else 'hold'
    return dict(rec, **best, status=st)


def _pair(die, t, ia, ma, a, ib, mb, b, L):
    if a is None or b is None:                       # one placeholder end: tree model with the flat share on its side
        ca = t[ma]['clocks'].get(a['clk'], {}) if a else {}
        cb = t[mb]['clocks'].get(b['clk'], {}) if b else {}
        deep = max(ca.get('R_tt') or 0.0, cb.get('R_tt') or 0.0) > LEVEL_PS
        avail = T_PS - U_SETUP - (SKEW_DEEP if deep else SKEW_SAME)
        o = a['O'] - (ca.get('R_tt') or 0.0) if a else SHARE
        s = b['S'] + (cb.get('R_tt') or 0.0) if b else SHARE
        return dict(model='TREE', half=True, o=round(o, 1), s=round(s, 1), avail=round(avail, 1),
                    setup_ps=round(avail - o - s - W_TT * L, 1), hold_ps=None, reach_um=round((avail - o - s) / W_TT, 1))
    model, info = die.relation(ia, a['clk'], ib, b['clk'])
    ca, cb = t[ma]['clocks'].get(a['clk'], {}), t[mb]['clocks'].get(b['clk'], {})
    if model == 'CROSS':
        return dict(model='CROSS', clocks=[f"{ma}.{a['clk']}", f"{mb}.{b['clk']}"], sources=[str(x) for x in info])
    if model == 'TREE':
        ra, rb = ca.get('R_tt') or 0.0, cb.get('R_tt') or 0.0
        W = _window(_edge_time(a['edge']), _edge_time(b['edge']))
        skew = SKEW_DEEP if max(ra, rb) > LEVEL_PS else SKEW_SAME
        avail = W - U_SETUP - skew
        o, s = a['O'] - ra, b['S'] + rb
        r = dict(model='TREE', o=round(o, 1), s=round(s, 1), avail=round(avail, 1), skew=skew,
                 setup_ps=round(avail - o - s - W_TT * L, 1), reach_um=round((avail - o - s) / W_TT, 1), hold_ps=None)
        if a.get('l') is not None and b.get('h') is not None:
            lo = a['l'] - (ca.get('R_ff') or 0.0)
            hi = b['h'] - (cb.get('R_ff') or 0.0)
            r.update(l=round(lo, 1), h=round(hi, 1), hold_ps=round(lo + W_FF_CREDIT * L - hi + (T_PS - W) - HOLD_TREE, 1))
        return r
    drv_inst, drv_pin, Lc, _net = info
    Lc = L if Lc is None else Lc
    if model == 'FWD':
        co = t[ma].get('clock_out', {}).get(bus_of(drv_pin))
        if not co or bus_of(co['clk']) != bus_of(a['clk']):
            return dict(model='CROSS', clocks=[f"{ma}.{a['clk']}", f"{mb}.{b['clk']}"],
                        sources=[f'{ma}.{drv_pin} is not a forward of the launching clock'])
        f = _fwd_arc(co, b['edge'], 'tt')
        ff = _fwd_arc(co, b['edge'], 'ff')
        if not f:
            return dict(model='CROSS', clocks=[f"{ma}.{a['clk']}", f"{mb}.{b['clk']}"], sources=['no forwarded arc for the capture edge'])
        W = _window(_edge_time(a['edge']), _edge_time(f[0]))
        fixed = W + f[1] - U_SETUP - a['O'] - b['S']
        setup = fixed + W_TT * (Lc * (1 - OCV) - L * (1 + OCV))
        # reach: the bundle is one route (Lc = Ld = L): wire mismatch is 2 ocv w L
        r = dict(model='FWD', window=round(W, 1), o=round(a['O'] - f[1], 1), s=round(b['S'], 1), avail=round(W - U_SETUP, 1),
                 sense='inverted' if f[0] != b['edge'] else 'same', clock_um=Lc, setup_ps=round(setup, 1),
                 reach_um=round(fixed / (2 * OCV * W_TT), 1) if fixed > 0 else round(fixed / W_TT, 1), hold_ps=None)
        if a.get('l') is not None and b.get('h') is not None and ff:
            r['hold_ps'] = round(a['l'] + W_FF * L * (1 - OCV) - b['h'] + (T_PS - W) - ff[2] - W_FF * Lc * (1 + OCV) - HOLD_FWD, 1)
        return r
    # REV: B forwards the clock that launches at A
    co = t[mb].get('clock_out', {}).get(bus_of(drv_pin))
    if not co or bus_of(co['clk']) != bus_of(b['clk']):
        return dict(model='CROSS', clocks=[f"{ma}.{a['clk']}", f"{mb}.{b['clk']}"],
                    sources=[f'{mb}.{drv_pin} is not a forward of the capturing clock'])
    g = _fwd_arc(co, a['edge'], 'tt')
    gf = _fwd_arc(co, a['edge'], 'ff')
    if not g:
        return dict(model='CROSS', clocks=[f"{ma}.{a['clk']}", f"{mb}.{b['clk']}"], sources=['no forwarded arc for the launch edge'])
    W = _window(_edge_time(g[0]), _edge_time(b['edge']))
    fixed = W - U_SETUP - g[2] - a['O'] - b['S']
    r = dict(model='REV', window=round(W, 1), o=round(a['O'] + g[2], 1), s=round(b['S'], 1), avail=round(W - U_SETUP, 1),
             clock_um=Lc, setup_ps=round(fixed - W_TT * (1 + OCV) * (L + Lc), 1),
             reach_um=round(fixed / (2 * W_TT * (1 + OCV)), 1), hold_ps=None)
    if a.get('l') is not None and b.get('h') is not None and gf:
        r['hold_ps'] = round(gf[1] + a['l'] + W_FF * (1 - OCV) * (L + Lc) - b['h'] + (T_PS - W) - HOLD_FWD, 1)
    return r


class Gate:
    """the generators' per-pair hop gate: limit(drv inst, drv master, drv pin, load inst, load master, load pin) -> um,
    = min(default_um, the reach of that pair's real views under its link model); default_um (the flat 500 um rule) when
    neither end has a view, the pair is a clock crossing, or a view has no clocked arc / no measured insertion there.
    A pair whose die port is bound to the view only by direction (pair_check.side) keeps default_um and is listed in
    .candidates (judge_direction=True judges it on that upper bound).
    `buses`: the generator's bus list [(bus, cls, bits, [(inst, pin), ...driver first])]: its clock-class buses give
    the clock drivers (forwarded links); `clock_net`: {(inst, pin): tree net} for tree leaf nets without a driver."""

    def __init__(self, table=None, default_um=DEFAULT_UM, buses=None, clock_net=None, judge_direction=False):
        self.t = load_table() if table is None else table
        self.default = default_um
        drv = {}
        for bid, cls, bits, eps in buses or []:
            if cls in CLOCK_CLS and len(eps) > 1 and cls != 'clock_trunk':
                for li, lp in eps[1:]:
                    drv[(li, bus_of(lp))] = (eps[0][0], bus_of(eps[0][1]), None, bid)
        self.die = Die(self.t, {}, drv, clock_net or {})
        self.used = dict(real=0, half=0, default=0, not_judged=0)
        self.pairs = {}
        self.judge_direction = judge_direction
        self.candidates = {}    # pairs whose port binding is by direction (an upper bound): reported, flat limit kept
        self.hold = {}          # pair -> worst FF hold margin (< 0) at zero wire: the hop fails whatever its length

    def limit(self, ia, ma, pa, ib, mb, pb):
        if not self.t or (ma not in self.t and mb not in self.t):
            self.used['default'] += 1
            return self.default
        r = check(self.die, dict(a=(ia, ma, pa), b=(ib, mb, pb), um=0.0))
        if r.get('reach_um') is None or r['model'] == 'DEFAULT':
            self.used['not_judged'] += 1
            return self.default
        lim = round(min(self.default, r['reach_um']), 1)
        k = (ma, bus_of(pa), mb, bus_of(pb), r['model'])
        if r.get('bind') == 'direction' and not self.judge_direction:
            # the die master's port names are not the view's: the worst bus of that direction is an UPPER BOUND, not
            # this port's arc.  It does not fail a build; it is listed until a bind map names the pins.
            self.used['not_judged'] += 1
            if lim < self.default:
                self.candidates[k] = min(lim, self.candidates.get(k, lim))
            return self.default
        self.used['real' if r['real'] == 2 else 'half'] += 1
        if r.get('hold_ps') is not None and r['hold_ps'] < 0:      # FF hold with no wire at all: no length repairs it
            self.hold[k] = min(r['hold_ps'], self.hold.get(k, 0.0))
        self.pairs[k] = min(lim, self.pairs.get(k, lim))
        return lim


def relay_class(table, pattern):
    """(o, s) of the die's relay / station class: the worst TREE residuals over the table masters matching `pattern`"""
    o = s = None
    rx = re.compile(pattern)
    for m, v in table.items():
        if not rx.search(m):
            continue
        for b in v['buses'].values():
            for a in b['arcs']:
                r = v['clocks'].get(a['clk'], {}).get('R_tt') or 0.0
                if a.get('O') is not None:
                    o = max(o or -1e9, a['O'] - r)
                if a.get('S') is not None and b.get('kind') != 'reset':
                    s = max(s or -1e9, a['S'] + r)
    return (round(o, 1) if o is not None else None), (round(s, 1) if s is not None else None)


def fix(rec, L, cls_o, cls_s, replan_um=50.0):
    """cheapest fix of a setup-failing TREE hop -> dict(fix, cycles, relays, pinreg=[sides], excess_um, alt).
       (iii) replan    the pair closes within `replan_um` less wire: move a pin / relay site, no cycle
       (i)   relay     n more die relays of the die's class (n cycles on this bundle, no tile re-route)
       (ii)  pinreg    a register at the pin of the named side(s) (tile re-route, +1 cycle a side) + the relays still needed
    cls_o / cls_s: the relay class residuals (a register at the pin is one relay stage built into the tile)."""
    avail = rec['avail']
    o, s = rec['o'], rec['s']
    need = -rec['setup_ps']
    excess = need / W_TT
    cls_o = SHARE if cls_o is None else cls_o
    cls_s = SHARE if cls_s is None else cls_s
    r_ar = (avail - o - cls_s) / W_TT
    r_rb = (avail - cls_o - s) / W_TT
    r_rr = (avail - cls_o - cls_s) / W_TT
    out = dict(excess_um=round(excess, 1), reach_src_to_relay_um=round(r_ar, 1), reach_relay_to_dst_um=round(r_rb, 1),
               reach_relay_um=round(r_rr, 1))

    def relays(first, last, span):
        if first < 0 or last < 0 or r_rr <= 0 and span > first + last:
            return None
        return 1 + max(0, math.ceil((span - first - last) / r_rr - 1e-9)) if span > first + last else 1

    opts = []
    n = relays(r_ar, r_rb, L)
    if n is not None:
        opts.append((n, 0, dict(fix='relay', relays=n, pinreg=[], cycles=n)))
    for sides in (['src'], ['dst'], ['src', 'dst']):
        oo = cls_o if 'src' in sides else o
        ss = cls_s if 'dst' in sides else s
        direct = (avail - oo - ss) / W_TT
        if direct >= L:
            m = 0
        else:
            m = relays((avail - oo - cls_s) / W_TT, (avail - cls_o - ss) / W_TT, L)
            if m is None:
                continue
        opts.append((len(sides) + m, len(sides), dict(fix='pinreg', relays=m, pinreg=sides, cycles=len(sides) + m)))
    if not opts:
        return dict(out, fix='none', cycles=None, relays=None, pinreg=[], note='the relay class does not close against itself')
    opts.sort(key=lambda x: (x[0], x[1]))
    best = dict(opts[0][2])
    if excess <= replan_um and (avail - o - s) > 0:
        best = dict(fix='replan', relays=0, pinreg=[], cycles=0, else_=opts[0][2])
    return dict(out, **best)
