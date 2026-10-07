"""Shared model for the top-down timing budgets (CLAUDE BUDGETS, 2026-10-06).

Die models come from tools/budgets/extract_die.py (one gz JSON per die, generator-exact geometry and nets).  Every
constant below is labelled MEASURED (with its record) or POLICY (owner rule); nothing is fitted to this tool's own
output.
"""
from __future__ import annotations

import gzip
import json
import math
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'results/rtl/budgets_20261006'

# ---------------------------------------------------------------------------------------------- POLICY (owner rules)
T_PS = 833.333                 # sign-off period, streaming domain (1.2 GHz)
PERIODS = dict(stream_1p2=833.333, serial_0p9=1111.111, hbm=1024.0, link=833.333, fwd=833.333)
UNC_SETUP_PS = 60.0            # SS setup uncertainty (sign-off)
UNC_HOLD_PS = 25.0             # FF hold uncertainty (sign-off)
ROUTE_T_PS = 770.0             # route over-constraint target (MARGIN-FIRST: +63 ps setup uncertainty)
ACCEPT_PS = 15.0               # acceptance: SS >= +15, FF >= +15 at 833.333 (OWNER 18:15)
SKEW_INTER_PS = 150.0          # die clock-arrival difference across a die wire to a DIFFERENT clock region
SKEW_INTRA_PS = 90.0           # same region: measured pair skew + margin (Qwen 65 + 25); tightened per region from
#                                the clock plan when its measured bound (+25 margin) is lower
SKEW_FWD_PS = 0.0             # forwarded-clock hop (clock with the data): no arrival-difference term on setup
HOLD_IO_SKEW_PS = 50.0         # hold IO uncertainty (FF model; make_io_vclk_ff.sh convention)
INTRA_MARGIN_PS = 25.0
OCV = 0.05                     # clock-path OCV derate on the non-shared insertion (rom_die_clocking_decision 5 %)
MAX_FANOUT_CTRL = 32           # DESIGN SIMPLIFICATION rule 5: fanout > 32 gets kept replicas

# ---------------------------------------------------------------------------------------------- MEASURED
# W15 routed 547-bit express link, M2-M9, SS/FF 60/25: min period = 261 ps + 1.135 ps/um x L (memory ss-wire-reach-504um;
# tools/uarch_model.py SS_REACH_UM basis).  261 = 60 uncertainty + 201 fixed (clk->Q, setup, driver/receiver).
WIRE_SS_PS_PER_UM = 1.135
FIXED_SS_PS = 201.0
# ASAP7 DFFHQNx1_ASAP7_75t_R RVT NLDM (asap7sc7p5t_SEQ_RVT_{SS,FF}_nldm_220123), slew 10-20 ps, small load
CLKQ_SS_PS = 90.0              # SS cell_rise/fall 78-92 ps
SETUP_SS_PS = 30.0             # SS setup 15.6-20.2 ps (+ margin for the 20-40 ps slews at a pin flop)
CLKQ_FF_MIN_PS = 32.2          # FF minimum (stations method, stn_io_min.py)
HOLD_FF_PS = 15.0              # FF hold constraint 9.5-13.2 ps
# fixed 201 split: launch = clk->Q 90 + pin driver 40; capture = receiver 41 + setup 30
DRV_OUT_PS = FIXED_SS_PS - CLKQ_SS_PS - SETUP_SS_PS - 41.0     # 40
RCV_IN_PS = 41.0
# FF wire credit for hold: 50 % of the measured FF wire delay per um (routed SPEF, stations M1_hfd_meso_r1 /
# M1_hfd_gath_r10: 0.2249 / 0.2223 ps/um -> 0.112 ps/um; stn_io_min.py)
WIRE_FF_CREDIT_PS_PER_UM = 0.112
# block-internal clock insertion model (SS, ps) = A + B * sqrt(w*h): least squares over the closure-loop calibrations
# (hfd_index_q_b0/b1/b2/b3/b5 930 x 830: 1132-1324, hfd_svc_SE_s3: 950) and the Z20c q element (510.84 x 126.9, 650 ps
# internal insertion, S81-RERUN 2fcb276fc).  FF = 0.66 x SS (same calibrations: 0.646-0.674).  A measured calibration
# of the master overrides the model in its sheet.
LINT_A_PS, LINT_B_PS_PER_UM, LINT_FF_RATIO = 430.0, 0.865, 0.66

# per-block internal insertion TARGET (what the block's own CTS must meet): the size model, capped where a block's own
# clock-path OCV alone would use the intra-region skew budget: 2 x OCV x L_int <= SKEW_INTRA -> L_int <= 900 ps
LINT_CAP_PS = SKEW_INTRA_PS / (2 * OCV)
LINT_TOL_PS = 100.0            # measured above target + tolerance -> FLAG (smaller block / pin-near clock entry)

STATION_KINDS = {'stn', 'rly', 'sstn', 'hstn', 'waypoint', 'rstg', 'cfifo'}


def lint_model(w, h):
    ss = LINT_A_PS + LINT_B_PS_PER_UM * math.sqrt(max(w, 1.0) * max(h, 1.0))
    return round(ss, 1), round(ss * LINT_FF_RATIO, 1)


def reach_um(skew_ps, period=T_PS, margin=ACCEPT_PS):
    """longest register-to-register die wire that closes at `period` with `margin`, under a clock skew term"""
    return max(0.0, (period - UNC_SETUP_PS - margin - FIXED_SS_PS - skew_ps) / WIRE_SS_PS_PER_UM)


def load_die(path):
    with gzip.open(path, 'rt') as f:
        d = json.load(f)
    d['by'] = {i[0]: i for i in d['insts']}
    return d


def xform(inst, xy):
    """master-coordinate point -> die coordinates for instance row [name, master, kind, region, domain, x, y, w, h, o]"""
    _, _, _, _, _, x, y, w, h, o = inst
    px, py = xy
    if o in ('MY', 'R180', 'FN', 'S'):
        px = w - px
    if o in ('MX', 'R180', 'FS', 'S'):
        py = h - py
    return (x + px, y + py)


def port_xy(d, inst, port):
    """die point of (instance, port): the generator / LEF anchor, else the outline centre (None flag)"""
    if '@' in port and inst[1] not in d.get('real_masters', ()):     # HBM r23: a sliced generated endpoint -> base port
        port = port.split('@', 1)[0]
    a = d['ports'].get(inst[1], {}).get(port)
    if a:
        return xform(inst, a), True
    return (inst[5] + inst[7] / 2, inst[6] + inst[8] / 2), False


def box_gap(a, b):
    dx = max(0.0, max(a[5], b[5]) - min(a[5] + a[7], b[5] + b[7]))
    dy = max(0.0, max(a[6], b[6]) - min(a[6] + a[8], b[6] + b[8]))
    return dx + dy


def pin_dist(d, ia, pa, ib, pb):
    """Manhattan pin-to-pin length; falls back to the outline gap when either anchor is missing"""
    (xa, ya), ka = port_xy(d, ia, pa)
    (xb, yb), kb = port_xy(d, ib, pb)
    if ka and kb:
        return abs(xa - xb) + abs(ya - yb), 'pins'
    if ka or kb:
        q = (xa, ya) if ka else (xb, yb)
        other = ib if ka else ia
        cx = min(max(q[0], other[5]), other[5] + other[7])
        cy = min(max(q[1], other[6]), other[6] + other[8])
        return abs(q[0] - cx) + abs(q[1] - cy), 'pin-outline'
    return box_gap(ia, ib), 'outline'


def in_rect(p, r):
    return r[0] <= p[0] <= r[2] and r[1] <= p[1] <= r[3]


def clock_trees(d):
    """{tree: dict(root=(inst, port), sinks=[(inst, port)], cls)} from the die clock nets (S81: clock / col_clock;
    HBM: clock_trunk).  Forwarded clocks (S81 fclk, HBM segment fclk bits) are not CTS trees."""
    out = {}
    for bid, cls, bits, eps in d['buses']:
        if cls in ('clock', 'col_clock', 'clock_trunk'):
            out[bid] = dict(cls=cls, root=tuple(eps[0][:2]), sinks=[tuple(e[:2]) for e in eps[1:] if e[0] != 'TOP'])
    return out


def sink_regions(d, trees):
    """inst -> (tree, region): region = the tree for column / per-region trees; for die trunks the rect region the
    instance centre falls in (HBM clock_regions; S81 spine / svc_* / band), else '<tree>:die'"""
    rects = [(r['name'], r['rect']) for r in d['regions'] if not r['name'].startswith('frame_')
             and r.get('kind') not in ('channel', 'soft_child_reservation')]
    out = {}
    for t, tr in trees.items():
        for inst, port in tr['sinks']:
            it = d['by'][inst]
            if tr['cls'] == 'col_clock':
                out.setdefault(inst, (t, t, port))
                continue
            c = (it[5] + it[7] / 2, it[6] + it[8] / 2)
            reg = next((n for n, r in rects if in_rect(c, r)), 'die')
            out.setdefault(inst, (t, f'{t}:{reg}', port))
    return out


def domain_of(d, inst):
    it = d['by'].get(inst)
    return it[4] if it else 'top'
