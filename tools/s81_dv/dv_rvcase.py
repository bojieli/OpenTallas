#!/usr/bin/env python3
"""S81-DIE7 (10-18) REAL-VIEW die case: the physical GRT + die STA case built FROM THE STRICT BIND NETLIST.

dv_diecase (standin mode) builds its own die netlist (plan lanes as o_<link>/i_<link> pins, DFF / closed relay
stations, one clk, no reset tree, no landing tiles) and lets the landing.sdc model stand in for the landings.  This
tool instead takes the bound die top of `dv_diecase --bind real` (tools/s81_dv/dv_bind.py: every instance real RTL,
DIE_PORT_BIND STRICT PASS) and makes it physical as it is:
  * every master with a CLOSED view (physical/ref_tile/<spec>/views/<master>/ on --view-refs, first ref wins) binds that
    LEF + TT/FF liberty: today the 14 half-cycle relay masters dsfd_dvrlyh_* and the reset station dsfd_rly_1_WN;
    landings / frames / crs4 / ctrl / clusters pick their views up the day they close (re-run, nothing else changes);
  * every other instance is a LABELLED per-instance STAND-IN abstract (rv_<inst>) whose pins are the RTL ports of its
    bound module, bit for bit as the bind netlist connects them: lane bits at the plan's link end points (2-track pitch,
    as dv_diecase), forwarded clocks beside their lane, region clocks at the S-face centre, the reset pin at the reset
    tree's pin point, other nets toward the instance they reach, tied / open bits (declared pads, straps) on one
    internal point (1-pin nets, never routed); stand-in timing = dv_diecase.stand_in_lib (flop-first, launch 25 ps,
    setup 25 / hold 0 against the master's clock pin; forwarded clock outputs a 25-ps positive-unate arc from it --
    the bound RTL forwards clk uninverted, e.g. ot_s81sl_slice ck_line);
  * landing tiles dsfd_dvland_* are REAL INSTANCES (placed outside the receiving face at the lane's end point, routed
    from the last station; ck_f = the lane's forwarded clock, ck = the receiver region root); without a closed view their
    stand-in times i against ck with the land plan's window (set_multicycle_path -setup E / -hold D-1 on ld_<link>/i,
    exactly the pilot model, now at the real pin); frame x lanes (crs4 inside the frame) keep the model on the frame pins;
  * regional reset tree = the bound dsfd_rly_1_WN stations at their street / lane-companion points (timed: release paths);
  * regional clock roots ck_<region> are top ports (DIE-CLOCK roots, ideal: no die tree built here, labelled); every
    lane clock is physical (hop-0 forward cell or source output -> relay ck -> ck_o -> ... -> landing ck_f).
Top-port nets (clock roots, rst_n, PMA, land_fault) are special (not die-top routing).

  dv_rvcase.py --plan P --bind-dir BIND/bind --bind-table T --land-plan LP --out CASE [--pin-window 3] [--die-repair]
      -> CASE/{views/, die.v, place.tcl, run.tcl, run.sh, sta_<c>.tcl, sta.sh, landing.sdc, classify.py, case.json}
Labels: NOT_A_DIE_RESULT while case.json census lists stand-ins.
"""
import argparse, collections, json, math, re, shutil, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / 'tools')); sys.path.insert(0, str(HERE))
import die_port_bind as DPB          # noqa: E402
import dv_diecase as DC              # noqa: E402
import dv_sta_pilot as SP            # noqa: E402
from die_cluster import boundary as CB   # noqa: E402
import abstract_pin_windows as APW   # noqa: E402

GITDIR = DC.GITDIR
PITCH = DC.PIN_PITCH
PLAT = DC.PLAT
T_PS = 833.333
STD_CORNERS = dict(SP.STD, ss=('SEQ_RVT_SS_nldm_220123.lib', 'INVBUF_RVT_SS_nldm_220122.lib.gz',
                              'SIMPLE_RVT_SS_nldm_211120.lib.gz'))
C_PS, U_PS = 25.0, 25.0
CONST_RE = re.compile(r"\b(\d+)'[sS]?[bBhHdDoO][0-9a-fA-F_xXzZ?]+")
LINK_RE = re.compile(r'^w_(.+)_(src|dst|lnd)$')
_FULL_CONST = re.compile(r"\s*(\d+)'[sS]?([bBhHdDoO])([0-9a-fA-F_]+)\s*")


def clock_sdc(table, top_ports):
    """Declare core and off-die PHY domains from the same binding contract."""
    domains = table.get('clock_domains', {})
    absent = set(domains) - set(top_ports)
    if absent:
        raise ValueError(f'domain clock ports missing from bound die: {sorted(absent)}')
    core = sorted(p for p in top_ports if p.startswith('ck_') and p not in domains)
    if not core:
        raise ValueError('bound die has no core clock ports')
    lines = [f'create_clock -name clk -period {T_PS} [get_ports {{{" ".join(core)}}}]']
    for port, domain in sorted(domains.items()):
        period = domain['period_ps']
        if period <= 0:
            raise ValueError(f'invalid period for {port}: {period}')
        lines.append(f'create_clock -name {port} -period {period} [get_ports {{{port}}}]')
        if domain.get('asynchronous_to_core'):
            lines.append(f'set_clock_groups -asynchronous -group [get_clocks clk] -group [get_clocks {port}]')
    return '\n'.join(lines)


def const_bits(e):
    """a full Verilog constant 3'd4 / 12'hb6d -> [bit0, bit1, ...]; anything else (x/z, concatenation, net) -> None"""
    m = _FULL_CONST.fullmatch(e or '')
    if not m:
        return None
    w, v = int(m.group(1)), int(m.group(3).replace('_', ''), {'b': 2, 'h': 16, 'd': 10, 'o': 8}[m.group(2).lower()])
    return [(v >> i) & 1 for i in range(w)]


def case_strap_sdc(insts, kind, port_bind_json):
    """NS-CASE: set_case_analysis lines for every declared strap port (strict bind masters[].straps) of every non-stand-in
    instance whose connection is a full constant.  Guarded with get_pins -quiet (a view lacking the pin is reported in
    the STA log, never an abort).  Returns the SDC lines (header + one line per bit)."""
    try:
        pb = json.load(open(port_bind_json))
    except (OSError, ValueError):
        return ['# NS-CASE strap case analysis: no port_bind.json -> none']
    sp = {m: set(r.get('straps') or []) for m, r in (pb.get('masters') or {}).items()}
    out, n = [], 0
    for mst, nm, _, cm in insts:
        if kind.get(nm) == 'standin' or not sp.get(mst):
            continue
        for p in sorted(sp[mst]):
            bits = const_bits(cm.get(p))
            if bits is None:
                continue
            for i, b in enumerate(bits):
                pin = f'{nm}/{p}' if len(bits) == 1 else f'{nm}/{p}[{i}]'
                out.append(f'ot_case {b} {{{pin}}}')
                n += 1
    hdr = ['# NS-CASE 10-18: die-constant strap pins (strict-bind straps) case-analysed with the netlist value',
           'set ::ot_case_n 0; set ::ot_case_miss 0',
           'proc ot_case {v p} { set q [get_pins -quiet $p]; if {[llength $q]} { set_case_analysis $v $q; incr ::ot_case_n } '
           'else { incr ::ot_case_miss } }']
    return hdr + out + ['puts "OT_CASE_STRAPS set $::ot_case_n missing $::ot_case_miss of %d"' % n]
FCK_RE = re.compile(r'^n(.+)_fck$')
RST_RE = re.compile(r'^(rs_|rsl_|rst_sync)')


def git(ref, path, binary=False):
    r = subprocess.run(['git', '-C', GITDIR, 'show', f'{ref}:{path}'], capture_output=True)
    if r.returncode:
        return None
    return r.stdout if binary else r.stdout.decode()


def closed_views(refs):
    """master -> (ref, view dir) for every physical/ref_tile/<spec>/views/<master>/<master>.lef (first ref wins)"""
    out = {}
    for ref in refs:
        r = subprocess.run(['git', '-C', GITDIR, 'ls-tree', '-r', '--name-only', ref, 'physical/ref_tile/'],
                           capture_output=True, text=True)
        for p in r.stdout.split():
            m = re.match(r'(physical/ref_tile/[^/]+/views/([^/]+))/\2\.lef$', p)
            if m and m.group(2) not in out:
                out[m.group(2)] = (ref, m.group(1))
    return out


MACRO_DIR = 'physical/asap7_memory_macros_v2'


def macro_views(refs, masters):
    """master -> (ref, dir) for every die-level master that is a memory / PHY macro with a real view under
    physical/asap7_memory_macros_v2/<m>/<m>.lef (+ <m>_<corner>.lib), e.g. the K-only HBM PHY _k (S81-MU5 10-19);
    first ref wins. Without this the macro becomes a pin-only stand-in."""
    out = {}
    for ref in refs:
        for m in sorted(masters):
            if m not in out and git(ref, f'{MACRO_DIR}/{m}/{m}.lef') is not None:
                out[m] = (ref, f'{MACRO_DIR}/{m}')
    return out


def rtl_ports(cmd):
    """module -> {port: (dir, ranges)} from the RTL set the STRICT port bind used (bind_case port_bind_cmd)"""
    roots, files, prefer, defines = [], [], [], {}
    i = 0
    while i < len(cmd):
        k = cmd[i]
        if k in ('--rtl-root', '--rtl-file', '--prefer', '--define') and i + 1 < len(cmd):
            v = cmd[i + 1]
            if k == '--define':
                n, _, val = v.partition('=')
                defines[n] = val or '1'
            else:
                {'--rtl-root': roots, '--rtl-file': files, '--prefer': prefer}[k].append(v)
            i += 2
            continue
        i += 1
    # the bind ran in another worktree / scratch: map its paths onto this worktree where they no longer exist
    def fix(p):
        if Path(p).exists():
            return p
        m = re.search(r'/(rtl|physical)/(.*)$', p)
        q = ROOT / m.group(1) / m.group(2) if m else None
        return str(q) if q is not None and q.exists() else p
    idx, _ = DPB.rtl_index([fix(r) for r in roots] or [str(ROOT / 'rtl')], [fix(f) for f in files], defines, [fix(f) for f in prefer])
    return idx


def face_of(b, x, y):
    d = {'W': abs(x - b['x']), 'E': abs(x - b['x'] - b['w']), 'S': abs(y - b['y']), 'N': abs(y - b['y'] - b['h'])}
    return min(d, key=d.get)


def project(rect, x, y):
    """nearest boundary point of rect (x0, y0, w, h) toward (x, y): -> (face, local coordinate along it)"""
    x0, y0, w, h = rect
    cx, cy = x0 + w / 2, y0 + h / 2
    dx, dy = x - cx, y - cy
    if abs(dx) * h >= abs(dy) * w:
        f = 'E' if dx > 0 else 'W'
        t = min(max(cy + (dy * (w / 2) / abs(dx) if dx else 0) - y0, 0.3), h - 0.3)
    else:
        f = 'N' if dy > 0 else 'S'
        t = min(max(cx + (dx * (h / 2) / abs(dy) if dy else 0) - x0, 0.3), w - 0.3)
    return f, t


def pin_rect(f, t, w, h):
    if f in 'WE':
        t = min(max(t, 0.2), h - 0.2); xx = 0.0 if f == 'W' else w - 0.1
        return 'M4', (xx, t - 0.012, xx + 0.1, t + 0.012)
    t = min(max(t, 0.2), w - 0.2); yy = 0.0 if f == 'S' else h - 0.1
    return 'M5', (t - 0.012, yy, t + 0.012, yy + 0.1)


def lib_text(cell, ports, clk, label):
    """ports: [(name, dir, width, is_bus, kind)] kind in data | clock | fclk_out"""
    L = [f'library ({cell}_standin) {{', f'  /* STAND-IN ({label}): S81-DIE7 real-view die case, not a closed view */',
         '  delay_model : table_lookup ; time_unit : "1ps" ; capacitive_load_unit (1, ff) ; voltage_unit : "1V" ;',
         '  current_unit : "1mA" ; pulling_resistance_unit : "1kohm" ; leakage_power_unit : "1nW" ;',
         '  nom_voltage : 0.7 ; nom_temperature : 25 ; nom_process : 1 ;',
         '  input_threshold_pct_rise : 50 ; input_threshold_pct_fall : 50 ; output_threshold_pct_rise : 50 ;',
         '  output_threshold_pct_fall : 50 ; slew_lower_threshold_pct_rise : 10 ; slew_lower_threshold_pct_fall : 10 ;',
         '  slew_upper_threshold_pct_rise : 90 ; slew_upper_threshold_pct_fall : 90 ;']
    for b in sorted({w for _, _, w, bus, _ in ports if bus}):
        L.append(f'  type (b{b}) {{ base_type : array ; data_type : bit ; bit_width : {b} ; bit_from : {b - 1} ; bit_to : 0 ; downto : true ; }}')
    L += [f'  cell ({cell}) {{', '    area : 1 ;']
    for name, d, w, bus, kind in ports:
        head = f'    bus ({name}) {{ bus_type : b{w} ;' if bus else f'    pin ({name}) {{'
        if d == 'input':
            if kind == 'clock' or name == clk:
                L.append(head + ' direction : input ; clock : true ; capacitance : 1.0 ; }')
                continue
            if clk is None:
                L.append(head + ' direction : input ; capacitance : 0.6 ; }')
                continue
            L += [head + ' direction : input ; capacitance : 0.6 ;',
                  f'      timing () {{ related_pin : "{clk}" ; timing_type : setup_rising ; rise_constraint (scalar) {{ values ("{U_PS}") ; }} fall_constraint (scalar) {{ values ("{U_PS}") ; }} }}',
                  f'      timing () {{ related_pin : "{clk}" ; timing_type : hold_rising ; rise_constraint (scalar) {{ values ("0") ; }} fall_constraint (scalar) {{ values ("0") ; }} }}',
                  '    }']
        else:
            if clk is None:
                L.append(head + ' direction : output ; max_capacitance : 40 ; }')
                continue
            if kind == 'fclk_out':
                arc = (f'timing () {{ related_pin : "{clk}" ; timing_sense : positive_unate ; cell_rise (scalar) {{ values ("{C_PS}") ; }} '
                       f'cell_fall (scalar) {{ values ("{C_PS}") ; }} rise_transition (scalar) {{ values ("20") ; }} fall_transition (scalar) {{ values ("20") ; }} }}')
            else:
                arc = (f'timing () {{ related_pin : "{clk}" ; timing_type : rising_edge ; cell_rise (scalar) {{ values ("{C_PS}") ; }} '
                       f'cell_fall (scalar) {{ values ("{C_PS}") ; }} rise_transition (scalar) {{ values ("20") ; }} fall_transition (scalar) {{ values ("20") ; }} }}')
            L += [head + ' direction : output ; max_capacitance : 40 ;', '      ' + arc, '    }']
    L += ['  }', '}']
    return '\n'.join(L) + '\n'


class Placer:
    """overlap-free placement of small movable macros (landings, reset stations, forward cells) among fixed bodies"""
    B = 200.0

    def __init__(self, W, H):
        self.W, self.H = W, H
        self.buck = collections.defaultdict(list)

    def add(self, r):
        x0, y0, x1, y1 = r
        for i in range(int(x0 // self.B), int(x1 // self.B) + 1):
            for j in range(int(y0 // self.B), int(y1 // self.B) + 1):
                self.buck[(i, j)].append(r)

    def hits(self, r, gap=0.5):
        x0, y0, x1, y1 = r
        if x0 < 1.2 or y0 < 1.2 or x1 > self.W - 1.2 or y1 > self.H - 1.2:
            return True
        for i in range(int((x0 - gap) // self.B), int((x1 + gap) // self.B) + 1):
            for j in range(int((y0 - gap) // self.B), int((y1 + gap) // self.B) + 1):
                for a in self.buck.get((i, j), ()):
                    if a[0] < x1 + gap and x0 < a[2] + gap and a[1] < y1 + gap and y0 < a[3] + gap:
                        return True
        return False

    def put(self, x, y, w, h, prefer=None, step=None, rmax=400.0):
        """lower-left nearest (x, y) with no overlap: first along `prefer` (unit vector list), then a square spiral"""
        step = step or max(2.0, min(w, h) / 2)
        cands = [(0.0, 0.0)]
        for k in range(1, int(rmax / step) + 1):
            d = k * step
            for ux, uy in (prefer or []):
                cands.append((ux * d, uy * d))
            for t in range(-k, k + 1):
                cands += [(t * step, d), (t * step, -d), (d, t * step), (-d, t * step)]
        for dx, dy in cands:
            r = (x + dx, y + dy, x + dx + w, y + dy + h)
            if not self.hits(r):
                self.add(r)
                return r[0], r[1], abs(dx) + abs(dy)
        r = (x, y, x + w, y + h)
        self.add(r)
        return x, y, None


def lef_pins(path):
    """{pin: (cx, cy, direction)} from a single-macro LEF (first RECT of each pin; line scan, LEFs are ~20 MB), plus (w, h)"""
    pins, size, cur, d = {}, None, None, ''
    with open(path) as fh:
        for ln in fh:
            t = ln.split()
            if not t:
                continue
            if t[0] == 'SIZE' and size is None:
                size = (float(t[1]), float(t[3]))
            elif t[0] == 'PIN':
                cur, d = t[1], ''
            elif cur and t[0] == 'DIRECTION':
                d = t[1].upper()
            elif cur and t[0] == 'RECT' and cur not in pins:
                q = [float(v) for v in t[1:5]]
                pins[cur] = ((q[0] + q[2]) / 2, (q[1] + q[3]) / 2, d)
            elif cur and t[0] == 'END' and len(t) > 1 and t[1] == cur:
                cur = None
    return size, pins


def fwd_relocate(out, insts, ibits, touch, loc, placer, kind, scell, gap=4.0):
    """move every fwd_<lane> (hop-0 forward cell) to the centroid of the pins that actually drive st_<lane>_0.i.
    Returns {lane: (moved_um, n_source_pins, pin_span_um)}; lanes whose source pins cannot be found keep the plan point."""
    mst_of = {nm: m for m, nm, _, _ in insts}
    want = {}
    for nm in mst_of:
        if nm.startswith('fwd_') and f'st_{nm[4:]}_0' in ibits and 'i' in ibits[f'st_{nm[4:]}_0']:
            want[nm] = [b for b in ibits[f'st_{nm[4:]}_0']['i'] if b[0] not in ('CONST', 'Z', 'UNDECL')]
    need = {}
    for f, bits in want.items():
        for b in bits:
            need.setdefault(b[0], set()).add(b)
    cache, drv = {}, {}
    for n_ in need:
        for o in touch.get(n_, ()):
            if o.startswith('st_') or o not in loc or o.startswith('fwd_'):
                continue
            cell = scell.get(o) if kind.get(o) == 'standin' else mst_of[o]
            lp = out / 'views' / f'{cell}.lef'
            if not lp.exists():
                continue
            if cell not in cache:
                cache[cell] = lef_pins(lp)
            _, pins = cache[cell]
            for p, bl in ibits[o].items():
                w = len(bl)
                for k, b in enumerate(bl):
                    if b[0] != n_ or b not in need[n_]:
                        continue
                    pn = f'{p}[{w - 1 - k}]' if f'{p}[{w - 1 - k}]' in pins else p
                    q = pins.get(pn)
                    if q and q[2] == 'OUTPUT':
                        x0, y0 = loc[o][0], loc[o][1]
                        drv[b] = (o, x0 + q[0], y0 + q[1])
    moves = {}
    for f, bits in sorted(want.items()):
        pts = [drv[b] for b in bits if b in drv]
        if not pts:
            continue
        srcs = collections.Counter(p[0] for p in pts)
        o = srcs.most_common(1)[0][0]
        pts = [p for p in pts if p[0] == o]
        cx = sum(p[1] for p in pts) / len(pts); cy = sum(p[2] for p in pts) / len(pts)
        span = max(p[1] for p in pts) - min(p[1] for p in pts) + max(p[2] for p in pts) - min(p[2] for p in pts)
        bx, by, bw, bh, _ = loc[o]
        fc = face_of(dict(x=bx, y=by, w=bw, h=bh), cx, cy)
        dx, dy = {'W': (-gap, 0), 'E': (gap, 0), 'S': (0, -gap), 'N': (0, gap)}[fc]
        ox, oy = loc[f][0] + 0.6, loc[f][1] + 0.3
        px_, py_, _ = placer.put(cx + dx - 0.6, cy + dy - 0.3, 1.2, 0.6, step=1.0)
        loc[f] = (px_, py_, 1.2, 0.6, 'PLACED')
        moves[f[4:]] = (round(abs(px_ + 0.6 - ox) + abs(py_ + 0.3 - oy), 1), len(pts), round(span, 1))
    return moves


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--plan', required=True, type=Path)
    ap.add_argument('--bind-dir', required=True, type=Path, help='dv_diecase --bind real output <out>/bind (die.v, bind_case.json, place_hints.json)')
    ap.add_argument('--bind-table', required=True, type=Path)
    ap.add_argument('--land-plan', required=True, type=Path)
    ap.add_argument('--out', required=True, type=Path)
    ap.add_argument('--view-refs', nargs='+', default=['origin/main'])
    ap.add_argument('--pin-window', type=float, default=3.0)
    ap.add_argument('--die-repair', action='store_true')
    ap.add_argument('--dieflow-ref', default='origin/main')
    ap.add_argument('--dcc-ref', default='origin/main', help='ref of tools/die_clock_check.{py,tcl} (+ hbm_die_v15/die_clock_tree.py)')
    ap.add_argument('--corners', nargs='+', choices=('tt', 'ff', 'ss'), default=['tt', 'ff'])
    ap.add_argument('--congestion-iterations', type=int, default=30)
    ap.add_argument('--macro-views', action='store_true',
                    help=f'bind die-level macros with a real view under {MACRO_DIR}/<m>/ (HBM PHY _k, SRAMs) instead of a stand-in')
    a = ap.parse_args()
    out = a.out
    for d in ('views/sta', 'out', 'sta', 'dcc/tools/hbm_die_v15'):
        (out / d).mkdir(parents=True, exist_ok=True)
    plan = DC.load(a.plan)
    T = json.load(open(a.bind_table))
    LP = json.load(open(a.land_plan))
    bc = json.load(open(a.bind_dir / 'bind_case.json'))
    hints = json.load(open(a.bind_dir / 'place_hints.json'))
    W, H = plan['facts']['die_um']
    blocks = {b['name']: b for b in plan['blocks']}
    mod2master = {m.get('module'): k for k, m in T['masters'].items() if m.get('module')}
    links = {}
    for l in plan['links']:
        (bi0, _, x0, y0, _), (bi1, _, x1, y1, _) = l['e']
        n0, n1 = plan['blocks'][bi0]['name'], plan['blocks'][bi1]['name']
        pts = [tuple(p) for p in l['sp']] if 'sp' in l else [(h[2], h[3]) for h in l['h'][:-1]]
        links[l['i'].replace('-', '_')] = dict(src=n0, dst=n1, sxy=(x0, y0), dxy=(x1, y1), bits=l['b'], pts=pts, cls=l['c'], hops=l['h'])

    # ------------------------------------------------------------------ netlist
    nets, tin, tout, insts = DPB.parse_die(a.bind_dir / 'die.v', 'dv_die')
    assigns = [x for x in insts if x[0] == '__assign__']
    insts = [x for x in insts if x[0] != '__assign__']
    views = closed_views(a.view_refs)
    if a.macro_views:
        for m_, v_ in macro_views(a.view_refs, {x[0] for x in insts if not x[0].endswith('_ASAP7_75t_R')} - set(views)).items():
            views[m_] = v_
    # MU-DIE-S81/PO2 (10-19): the bind table pins each landing master's view (land_views: record commit + kit) -- the
    # SAME view dv_bind's landing reset check derived landing_reset_stages from; it overrides the first-ref-wins pick
    for m_, v_ in T.get('land_views', {}).items():
        views[m_] = (v_.get('commit') or v_['ref'], f"{v_['kit']}/views/{m_}")
    idx = rtl_ports(bc['port_bind_cmd'])
    kind = {}
    for mst, nm, _, _ in insts:
        kind[nm] = ('std' if mst.endswith('_ASAP7_75t_R') else 'closed' if mst in views else 'standin')
    # instances touching each net (net-name level) for the generic pin direction
    touch = collections.defaultdict(set)
    ibits = {}
    for mst, nm, _, cm in insts:
        pb = {}
        for p, e in cm.items():
            bits = DPB.expr_bits(e, nets)
            if bits is None:
                raise SystemExit(f'dv_rvcase: unparsable connection {nm}.{p} = {e[:80]}')
            pb[p] = bits
            for n_, _ in bits:
                if n_ not in ('CONST', 'Z', 'UNDECL'):
                    touch[n_].add(nm)
        ibits[nm] = pb
    top = set(tin) | set(tout)
    clocks_sdc = clock_sdc(T, top)
    # clock nets: region roots, lane forwarded clocks (relay ck / ck_o, landing ck_f, forward cells), peer clocks (bind clk_peer)
    clocknets = {n for n in top if n.startswith('ck_')}
    for mst, nm, _, cm in insts:
        cps = []
        if mst.startswith('dsfd_dvrlyh_') or mst.startswith('dsfd_dvrly_'):
            cps = ['ck', 'ck_o']
        elif mst.startswith('dsfd_dvland_'):
            cps = ['ck_f', 'ck']
        elif mst.endswith('_ASAP7_75t_R') and nm.startswith('fwd_'):
            cps = ['A', 'Y', 'CLK', 'GCLK']     # BUFx8 forward / ICGx4 hop-0 lane clock gate (S81-LBGAP/G1)
        else:
            tm = T['masters'].get(mod2master.get(mst, ''), {})
            cps = [tm.get('clk')] + [cp['port'] for cp in tm.get('clk_peer', [])]
        for p in cps:
            if p and p in ibits[nm]:
                clocknets |= {n_ for n_, _ in ibits[nm][p] if n_ not in ('CONST', 'Z', 'UNDECL')}

    # ------------------------------------------------------------------ positions of every instance (centre) + sizes
    vsize = {}
    for m, (ref, d) in views.items():
        if m in {x[0] for x in insts}:
            lef = git(ref, f'{d}/{m}.lef')
            sz = next(l.split() for l in lef.splitlines() if l.strip().startswith('SIZE'))
            vsize[m] = (float(sz[1]), float(sz[3]))
            (out / 'views' / f'{m}.lef').write_text(lef)
            for c in a.corners:
                lib = git(ref, f'{d}/{m}_{c}.lib')
                if lib is None:
                    raise SystemExit(f'dv_rvcase: closed view {m} has no {c} lib at {ref}:{d}')
                if 'pin("ck_o")' in lib and m.startswith('dsfd_dvrlyh_'):
                    # dv_sta_pilot: ETM self-related ck_o edges -> one ck -> ck_o arc, negative unate (half-cycle view)
                    lib = SP.patch_ck_o(lib)
                    i_ = lib.index('S81-DIE4 STA pilot: ETM self-related'); j_ = lib.rindex('timing_sense : positive_unate', 0, i_)
                    lib = lib[:j_] + 'timing_sense : negative_unate' + lib[j_ + len('timing_sense : positive_unate'):]
                elif 'pin("ck_o")' in lib:
                    lib = SP.patch_ck_o(lib)
                (out / 'views' / 'sta' / f'{m}_{c}.lib').write_text(lib)    # STA corner libs (the GRT reads views/*.lib: TT copy below)
            (out / 'views' / f'{m}.lib').write_text(git(ref, f'{d}/{m}_tt.lib'))
    placer = Placer(W, H)
    loc = {}            # inst -> (x, y lower-left, w, h, status)
    for b in blocks.values():
        loc[f'u_{b["name"]}'] = (b['x'], b['y'], b['w'], b['h'], 'FIRM')
        placer.add((b['x'], b['y'], b['x'] + b['w'], b['y'] + b['h']))
    mst_of = {nm: mst for mst, nm, _, _ in insts}
    for nm, L in links.items():
        for k, (px, py) in enumerate(L['pts']):
            i = f'st_{nm}_{k}'
            if i in mst_of:
                w_, h_ = vsize[mst_of[i]]
                loc[i] = (px - w_ / 2, py - h_ / 2, w_, h_, 'FIRM')
                placer.add((px - w_ / 2, py - h_ / 2, px + w_ / 2, py + h_ / 2))
    moved = collections.Counter(); far = []
    rw, rh = vsize.get(T.get('reset_master'), (17.28, 17.28))
    # landings: outside the receiving face at the lane end point, long side along the face
    land = {r['inst']: r for r in hints['landings']}
    for i, r in sorted(land.items()):
        L = links[r['link']]; b = blocks[r['dst']]
        nb = r['bits']; flops = (r['D'] + 1) * nb
        area = flops * 0.29 / 0.45
        long_ = max(nb * PITCH + 6.0, math.sqrt(area)); short = max(area / long_, 12.0)
        x, y = L['dxy']; f = face_of(b, x, y)
        if f in 'SN':
            w_, h_ = long_, short; xx = x - w_ / 2; yy = b['y'] - h_ - 2.0 if f == 'S' else b['y'] + b['h'] + 2.0
            pref = [(1, 0), (-1, 0), (0, -1 if f == 'S' else 1)]
        else:
            w_, h_ = short, long_; yy = y - h_ / 2; xx = b['x'] - w_ - 2.0 if f == 'W' else b['x'] + b['w'] + 2.0
            pref = [(0, 1), (0, -1), (-1 if f == 'W' else 1, 0)]
        px_, py_, dd = placer.put(xx, yy, w_, h_, prefer=pref)
        loc[i] = (px_, py_, w_, h_, 'FIRM'); moved['landing'] += dd is not None and dd > 0
        if dd is None or dd > 200:
            far.append((i, dd))
    for p in hints['reset_place']:
        i = p['inst']; x, y = p['xy']
        px_, py_, dd = placer.put(x - rw / 2, y - rh / 2, rw, rh, step=4.0)
        loc[i] = (px_, py_, rw, rh, 'FIRM'); moved['reset'] += dd is not None and dd > 0
        if dd is None or dd > 100:
            far.append((i, dd))
    rx, ry = hints['reset_root_xy']
    for k, i in enumerate(('rst_root0', 'rst_root1')):
        px_, py_, dd = placer.put(rx - rw / 2 + k * (rw + 1), max(ry, 2.0), rw, rh, step=4.0)
        loc[i] = (px_, py_, rw, rh, 'FIRM')
    for mst, i, _, _ in insts:
        if i.startswith('fwd_'):
            L = links[i[4:]]; b = blocks[L['src']]; x, y = L['sxy']; f = face_of(b, x, y)
            dx, dy = {'W': (-4, 0), 'E': (4, 0), 'S': (0, -4), 'N': (0, 4)}[f]
            px_, py_, dd = placer.put(x + dx - 0.6, y + dy - 0.3, 1.2, 0.6, step=1.0)
            loc[i] = (px_, py_, 1.2, 0.6, 'PLACED')
        elif i.startswith('rinv_') and i[5:] in blocks:      # active-high block reset: inverter beside the reset pin
            b = blocks[i[5:]]; x, y = hints['block_rst_pin'].get(i[5:], (b['x'] + b['w'] / 2, b['y']))
            f = face_of(b, x, y)
            dx, dy = {'W': (-4, 0), 'E': (4, 0), 'S': (0, -4), 'N': (0, 4)}[f]
            px_, py_, dd = placer.put(x + dx - 0.6, y + dy - 0.3, 1.2, 0.6, step=1.0)
            loc[i] = (px_, py_, 1.2, 0.6, 'PLACED')
    missing = [i for _, i, _, _ in insts if i not in loc]
    if missing:
        raise SystemExit(f'dv_rvcase: no position for {len(missing)} instances, e.g. {missing[:5]}')
    centre = {i: (v[0] + v[2] / 2, v[1] + v[3] / 2) for i, v in loc.items()}

    # ------------------------------------------------------------------ stand-in abstracts + libs
    census = collections.Counter(); scell = {}
    lane_bits_mcp = collections.defaultdict(list)     # link -> [pin names] (frame lanes: model on the frame pins)
    for mst, nm, _, cm in insts:
        if kind[nm] != 'standin':
            census[f'{kind[nm]}:{mst}'] += 1
            continue
        census[f'standin:{mst}'] += 1
        mod = idx.get(mst)
        if mod is None:
            raise SystemExit(f'dv_rvcase: no RTL module {mst} for stand-in {nm}')
        cell = f'rv_{nm[2:] if nm.startswith("u_") else nm}'
        scell[nm] = cell
        x0, y0, w, h, _ = loc[nm]
        bname = nm[2:] if nm.startswith('u_') else None
        is_land = nm in land
        clk = 'ck' if is_land else T['masters'].get(mod2master.get(mst, ''), {}).get('clk')
        ports, sig, inner = [], [], []
        lefp = []
        slot = collections.Counter()
        for p, bits in ibits[nm].items():
            if p not in mod.ports:
                raise SystemExit(f'dv_rvcase: {nm}.{p} not a port of {mst}')
            d = {'input': 'input', 'output': 'output'}.get(mod.ports[p][0], 'input')
            wdt = len(bits); bus = bool(mod.ports[p][1])
            kinds = set()
            for k, (n_, bi) in enumerate(bits):
                pn = f'{p}[{wdt - 1 - k}]' if bus else p
                # ---- role of the bit -> pin location
                f = t = None
                if n_ in ('CONST', 'Z', 'UNDECL') or (n_ not in top and touch.get(n_, set()) <= {nm}):
                    inner.append(pn); continue
                if n_ in top:
                    kinds.add('clock' if n_.startswith('ck_') else 'data')
                    if bname:
                        f, t = 'S', w / 2 + PITCH * (3 + slot['top']); slot['top'] += 1
                    else:
                        inner.append(pn); continue
                elif n_ in clocknets and not n_.startswith('ck_'):
                    kinds.add('fclk_out' if d == 'output' else 'clock')
                    ln = FCK_RE.match(n_).group(1) if FCK_RE.match(n_) else None
                    L = links.get(ln)
                    if L and bname in (L['src'], L['dst']):
                        x, y = L['sxy'] if bname == L['src'] else L['dxy']
                        f = face_of(blocks[bname], x, y)
                        t = (y - y0 if f in 'WE' else x - x0) + L['bits'] * PITCH / 2 + PITCH * (1 + slot[('f', ln)]); slot[('f', ln)] += 1
                elif LINK_RE.match(n_) and bname:
                    ln, role = LINK_RE.match(n_).groups(); kinds.add('data')
                    L = links.get(ln)
                    if L and bname in (L['src'], L['dst']):
                        x, y = L['sxy'] if (bname == L['src'] and role == 'src') else L['dxy']
                        f = face_of(blocks[bname], x, y)
                        t = (y - y0 if f in 'WE' else x - x0) - L['bits'] * PITCH / 2 + (bi + 0.5) * PITCH
                        if role == 'dst' and d == 'input' and L['dst'] == bname:     # lane into the block with no landing tile
                            lane_bits_mcp[ln].append(f'{nm}/{pn}')
                elif n_.startswith('ck_'):
                    kinds.add('clock'); f, t = 'S', w / 2 + PITCH * slot['ck']; slot['ck'] += 1
                elif RST_RE.match(n_) and bname and bname in hints['block_rst_pin']:
                    kinds.add('data'); x, y = hints['block_rst_pin'][bname]; f = face_of(blocks[bname], x, y)
                    t = (y - y0 if f in 'WE' else x - x0) + PITCH * slot['rs']; slot['rs'] += 1
                if f is None:
                    kinds.add('data')
                    oth = [centre[o] for o in touch.get(n_, ()) if o != nm and o in centre]
                    if not oth:
                        inner.append(pn); continue
                    ox = sum(q[0] for q in oth) / len(oth); oy = sum(q[1] for q in oth) / len(oth)
                    f, t = project((x0, y0, w, h), ox, oy)
                    key = (p, f)
                    t = t + PITCH * (slot[key] - (wdt / 2 if wdt > 1 else 0)); slot[key] += 1
                lay, rect = pin_rect(f, t, w, h)
                lefp.append((pn, d, lay, rect)); sig.append((pn, lay, rect))
            if p == clk:
                pk = 'clock'
            elif d == 'output':
                pk = 'fclk_out' if 'fclk_out' in kinds and kinds <= {'fclk_out'} else 'data'
            else:
                pk = 'clock' if kinds and kinds <= {'clock'} else 'data'
            ports.append((p, d, wdt, bus, pk))
        dirs = {p: d for p, d, *_ in ports}
        for pn in inner:      # tied / open / pad bits: one internal point (1-pin nets, never routed)
            lefp.append((pn, dirs[pn.split('[')[0]], 'M4', (w / 2, h / 2 - 0.012, w / 2 + 0.1, h / 2 + 0.012)))
        lines = [f'MACRO {cell}', '  CLASS BLOCK ;', '  ORIGIN 0 0 ;', f'  SIZE {w:.3f} BY {h:.3f} ;', '  SYMMETRY X Y ;']
        for pn, d, lay, (q0, q1, q2, q3) in lefp:
            lines += [f'  PIN {pn}', f'    DIRECTION {d.upper()} ;', '    USE SIGNAL ;', '    PORT', f'      LAYER {lay} ;',
                      f'        RECT {q0:.3f} {q1:.3f} {q2:.3f} {q3:.3f} ;', '    END', f'  END {pn}']
        lines += ['  OBS', '    LAYER M1 ;', f'      RECT 0.2 0.2 {w - 0.2:.3f} {h - 0.2:.3f} ;']
        win = APW.windows(w, h, sig, a.pin_window, 4, 6) if a.pin_window > 0 and sig else {}
        for li, Ly in enumerate(('M2', 'M3', 'M4', 'M5', 'M6'), 2):
            if not win.get(li):
                lines += [f'    LAYER {Ly} ;', f'      RECT 0.2 0.2 {w - 0.2:.3f} {h - 0.2:.3f} ;']
                continue
            lines += [f'    LAYER {Ly} ;'] + [f'      RECT {q[0]:.3f} {q[1]:.3f} {q[2]:.3f} {q[3]:.3f} ;'
                                              for q in APW.minus_rect((0.2, 0.2, w - 0.2, h - 0.2), win[li])]
        lines += ['  END', f'END {cell}', '']
        (out / 'views' / f'{cell}.lef').write_text('VERSION 5.8 ;\nBUSBITCHARS "[]" ;\nDIVIDERCHAR "/" ;\n' + '\n'.join(lines) + 'END LIBRARY\n')
        (out / 'views' / f'{cell}.lib').write_text(lib_text(cell, ports, clk if clk in dirs else None,
                                                            f'{mst} bound RTL ports; ' + ('landing tile, window = land plan MCP' if is_land else 'block')))

    # ------------------------------------------------------------------ hop-0 forward cell at the REAL data launch point
    # DIE-S81-LEAD 10-19 (case_p4l3_rv fclk FAIL): the hop-0 forward cell sat at the PLAN link end point, but a closed
    # view smaller than its plan slot (dsdv_bk_col 674x648 in a 680x4179 slot) or with its own pin plan launches the
    # data elsewhere -> fclk 2 repeaters vs data up to 27.  The forwarded clock must launch where its data launches:
    # move fwd_<lane> to the centroid of the actual source pins of st_<lane>_0.i (closed LEF / stand-in LEF), outside
    # that face, so fclk and data run the same wire (DIE-CLOCK +-1).
    fwd_moves = fwd_relocate(out, insts, ibits, touch, loc, placer, kind, scell)
    # ------------------------------------------------------------------ case netlist (bind netlist, stand-in cells, PHYSICAL ties)
    # DIE-S81-LEAD 10-19: every constant bit is driven by its own TIEHI/TIELO cell (was a floating 1-pin wire tz_*: not
    # physical, and the exact fclk payload audit (c5f578d5a/57459e378) counts an undriven payload bit as missing).  The
    # ties carry no position here: run.tcl places each at its load pin and spreads them with the die repeater step's
    # legaliser (tie_place.tcl) -- a Python nearest-free-site search stalled at abutted frames (Codex 10-18 23:39).
    tz = [0]
    decl, ties = [], []

    def detie(e, host, physical):
        def rep(m):
            if not physical:      # stand-in: the strap is internal to the modelled block (its LEF has the bit as an
                w_ = int(m.group(1)); n = f'tz_{tz[0]}'; tz[0] += 1      # inner point under OBS) -> 1-pin wire, as before
                decl.append(f'  wire [{w_ - 1}:0] {n};')
                return n
            bits = const_bits(m.group(0))
            if bits is None:
                raise SystemExit(f'dv_rvcase: unresolved constant {m.group(0)} on {host}; never float a physical input')
            n = f'tz_{tz[0]}'; tz[0] += 1
            decl.append(f'  wire [{len(bits) - 1}:0] {n};')
            for k, bit in enumerate(bits):
                mst_, pin_ = ('TIEHIx1_ASAP7_75t_R', 'H') if bit else ('TIELOx1_ASAP7_75t_R', 'L')
                ties.append(f'  {mst_} tie_{n}_{k} (.{pin_}({n}[{k}]));')
            return n
        return CONST_RE.sub(rep, e)
    body = []
    for mst, nm, prm, cm in insts:
        cs = ', '.join(f'.{p}({detie(e, nm, kind[nm] != "standin")})' for p, e in cm.items())
        if kind[nm] == 'standin':
            body.append(f'  {scell[nm]} {nm} ({cs});')
        else:
            body.append(f'  {mst} {nm} ({cs});')
    for _, s_, _, _ in assigns:
        if CONST_RE.search(s_):
            raise SystemExit('dv_rvcase: constant assign has no physical load to place its tie at -- bind it to a port')
        body.append('  ' + s_ + ';')
    body += ties
    hdr = [f'// S81-DIE7 REAL-VIEW die case netlist from {a.bind_dir / "die.v"} (tools/s81_dv/dv_rvcase.py): bound instances, '
           'stand-in cells rv_* where no closed view, constant bits driven by TIEHI/TIELO cells tie_tz_*',
           f'module dv_die ({", ".join(sorted(top))});']
    for n in sorted(nets):
        wv, lo = nets[n]
        rng = f'[{lo + wv - 1}:{lo}] ' if wv > 1 or lo else ''
        hdr.append(f'  {"input" if n in tin else "output" if n in tout else "wire"} {rng}{n};')
    (out / 'die.v').write_text('\n'.join(hdr + decl + body + ['endmodule']) + '\n')

    # ------------------------------------------------------------------ placement
    pl = []
    for i, (x, y, w_, h_, st) in sorted(loc.items()):
        pl.append(f'place_inst -name {i} -location {{{x:.3f} {y:.3f}}} -orientation R0 -status {st}')
    (out / 'place.tcl').write_text('\n'.join(pl) + '\n')

    # ------------------------------------------------------------------ landing / frame-lane window model (land plan)
    sdc = [f'# S81-DIE7 real-view landing windows from {a.land_plan}: landing stand-in i (or frame lane pins) vs the receiver root, '
           'set_multicycle_path -setup E / -hold D-1 (dv_land_pilot rule); a CLOSED landing view replaces this by its own arcs']
    link_pins = {}
    for r in LP['links']:
        nm = r['link']; i = f'ld_{nm}'
        if i in loc and kind.get(i) == 'standin':
            pins = f'[get_pins {i}/i[*]]'
        elif i in loc:
            continue
        elif lane_bits_mcp.get(nm):
            pins = '[get_pins {' + ' '.join(lane_bits_mcp[nm]) + '}]'
        else:
            continue
        link_pins[nm] = pins
        sdc.append(f'set_multicycle_path -setup {r.get("K") or r["E"]} -to {pins}')   # S81-LBGAP/G8: the landing reads at K
        sdc.append(f'set_multicycle_path -hold {r["D"] - 1} -to {pins}')
    # NS-CASE 10-18 (ROOT-2115): the strict bind's declared STRAP ports (port_bind.json masters[].straps: landing k,
    # pvrd k/nw/rb, col_h* lk) carry die constants; the die STA case-analyses them bit by bit with the netlist's own
    # value (the tile native audit --case excludes exactly these pins, so die STA must not time them either)
    case_lines = case_strap_sdc(insts, kind, a.bind_dir / 'port_bind.json')
    sdc += case_lines
    (out / 'landing.sdc').write_text('\n'.join(sdc) + '\n')
    no_model = [r['link'] for r in LP['links'] if r['link'] not in link_pins and f'ld_{r["link"]}' not in loc]

    # ------------------------------------------------------------------ GRT run
    repair = DC.die_repair_tcl(out, a.dieflow_ref, skip=()) if a.die_repair else '# no die repair\n'
    # Relay RTL's complete forwarded payload is i[W-1:0]; rs is a separate
    # synchronous reset tree, not payload. Declare the width as well as the port
    # so a missing/disconnected payload bit fails the structural audit.
    if a.die_repair:
        contracts = []
        for master in sorted({m for m, _, _, _ in insts}):
            match = re.fullmatch(r'dsfd_dvrlyh?_(\d+)_[A-Z]+', master)
            if match:
                contracts.append(f'{{{master}}} {{{{i\\[*\\]}} {int(match[1])}}}')
        repair = ('set ::ot_die_rep_fclk_data_ports [dict create ' + ' '.join(contracts) + ']\n' + repair)
    post = ('estimate_parasitics -global_routing\n'
            'if {[llength [info procs ot_die_rep_post_grt_audit]]} { ot_die_rep_post_grt_audit /work/die_repeaters.post_grt.json }\n'
            if a.die_repair else 'estimate_parasitics -global_routing\n')
    # DIE-S81-LEAD 10-19: physical tie placement (each tie at its single load pin, then the die repeater step's spread
    # legaliser moves it to the nearest free slot; the legaliser's per-run caches are cleared so the repeater pass
    # rebuilds its obstacles with the ties in place and its own slot width)
    (out / 'tie_place.tcl').write_text('''# DIE-S81-LEAD tie placement (tools/s81_dv/dv_rvcase.py)
proc ot_rv_place_ties {report} {
  set blk [ord::get_db_block]; set ties {}; set bad 0
  foreach inst [$blk getInsts] {
    set m [[$inst getMaster] getName]
    if {$m ne "TIEHIx1_ASAP7_75t_R" && $m ne "TIELOx1_ASAP7_75t_R"} { continue }
    set xy {}
    foreach o [$inst getITerms] {
      if {[$o getIoType] ne "OUTPUT" || [$o getNet] eq "NULL"} { continue }
      foreach it [[$o getNet] getITerms] {
        if {[$it getIoType] ne "INPUT"} { continue }
        set b [$it getBBox]
        set xy [list [expr {([$b xMin] + [$b xMax]) / 2}] [expr {([$b yMin] + [$b yMax]) / 2}]]; break
      }
    }
    if {![llength $xy]} { incr bad; puts "OT_TIE_NOLOAD [$inst getName]"; continue }
    $inst setLocation {*}$xy; $inst setPlacementStatus PLACED; lappend ties $inst
  }
  set left [ot_die_rep_spread $ties $report 0.30 8.64 0.60 3]
  foreach v {::ot_die_rep_slw ::ot_die_rep_obs ::ot_die_rep_occ ::ot_die_rep_onobs ::ot_die_rep_maxdisp} { unset -nocomplain $v }
  array unset ::ot_die_rep_ob
  puts "OT_TIES placed=[llength $ties] noload=$bad unplaced=$left"; flush stdout
  return [expr {$bad + $left}]
}
''')
    tie_step = ('source /work/die_repeaters.tcl\nsource /work/tie_place.tcl\n'
                'if {[ot_rv_place_ties /work/out/tie_spread.json] != 0} { puts "OT_TIE_PLACE_FAIL"; exit 4 }\n') if ties else '# no tie cells\n'
    if ties and not a.die_repair:
        raise SystemExit('dv_rvcase: tie cells need --die-repair (the tie spread uses the die repeater legaliser)')
    tcl = f'''# S81-DIE7 REAL-VIEW die case (tools/s81_dv/dv_rvcase.py) -- census in case.json (stand-ins labelled)
read_lef {PLAT}/lef/asap7_tech_1x_201209.lef
read_lef {PLAT}/lef/asap7sc7p5t_28_R_1x_220121a.lef
foreach f [glob /work/views/*.lef] {{ read_lef $f }}
read_liberty {PLAT}/lib/NLDM/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib
read_liberty {PLAT}/lib/NLDM/asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib.gz
read_liberty {PLAT}/lib/NLDM/asap7sc7p5t_SIMPLE_RVT_TT_nldm_211120.lib.gz
foreach f [glob /work/views/*.lib] {{ read_liberty $f }}
read_verilog /work/die.v
link_design dv_die
{CB.floorplan_tcl(W, H)}
make_tracks M9 -x_offset 0.116 -x_pitch 0.080 -y_offset 0.116 -y_pitch 0.080
make_tracks M8 -x_offset 0.116 -x_pitch 0.080 -y_offset 0.116 -y_pitch 0.080
make_tracks M7 -x_offset 0.016 -x_pitch 0.064 -y_offset 0.016 -y_pitch 0.064
make_tracks M6 -x_offset 0.012 -x_pitch 0.048 -y_offset 0.016 -y_pitch 0.064
make_tracks M5 -x_offset 0.012 -x_pitch 0.048 -y_offset 0.012 -y_pitch 0.048
make_tracks M4 -x_offset 0.009 -x_pitch 0.036 -y_offset 0.012 -y_pitch 0.048
make_tracks M3 -x_offset 0.009 -x_pitch 0.640 -y_offset 0.009 -y_pitch 0.640
make_tracks M2 -x_offset 0.009 -x_pitch 0.640 -y_offset 0.045 -y_pitch 0.640
make_tracks M1 -x_offset 0.009 -x_pitch 0.036 -y_offset 0.009 -y_pitch 0.036
set p0 [clock seconds]
source /work/place.tcl
puts "OT_PLACE_S [expr {{[clock seconds]-$p0}}] insts [llength [get_cells *]]"
{CB.legalize_tcl('place', max_dpl_gsites=2.0)}
{tie_step}write_db /work/out/place.odb
source {PLAT}/setRC.tcl
set_wire_rc -signal -layer M6
# top-port nets (regional clock roots, rst_n, PMA, land_fault): special = not die-top routing (DIE-CLOCK roots ideal here)
set nsp 0
foreach bt [[ord::get_db_block] getBTerms] {{ set n [$bt getNet]; if {{$n ne "NULL"}} {{ $n setSpecial; incr nsp }} }}
puts "OT_SPECIAL_TOP_NETS $nsp"
# S81-DIE8 10-18: the die repeater step runs BEFORE create_clock.  With the region roots declared as clocks, STA
# propagates them through the hop-0 forward cell (BUFx8 / G1 ICGx4) and repair_design silently skips every hop-0
# forwarded-clock net even though repeat_nets un-skips it (case_p4l_rv: all 140 hop-0 fclk nets 0 repeaters,
# 108 > data-1 -> fclk_mismatch FAIL).  Clock / reset distribution stays untouched by the step's own skip list
# (clock-pin + sigtype + glob dont_touch); no step check reads the SDC clock.
{repair}{clocks_sdc}
set_routing_layers -signal M2-M7 -clock M5-M9
set_global_routing_layer_adjustment M2-M3 0.50
set_global_routing_layer_adjustment M4-M5 0.30
set_global_routing_layer_adjustment M6-M7 0.20
set t0 [clock seconds]
global_route -congestion_iterations {a.congestion_iterations} -allow_congestion -verbose -congestion_report_file /work/out/grt_congestion.rpt
puts "OT_GRT_S [expr {{[clock seconds]-$t0}}]"
write_db /work/out/grt.odb
{post}
puts OT_DONE
'''
    (out / 'run.tcl').write_text(tcl)
    shutil.copy(ROOT / 'tools/die_cluster/cluster_bounds.tcl', out / 'cluster_bounds.tcl')
    (out / 'run.sh').write_text('''#!/bin/bash
D=$(cd $(dirname $0) && pwd); N=dvrv-$$
docker run --rm --name $N --cpus=${CPUS:-8} --memory=${MEMG:-96}g -v $D:/work -w /work openroad/orfs:asap7lock \\
  bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; /usr/bin/time -v openroad -threads ${CPUS:-8} -no_init -exit /work/run.tcl > /work/out/run.log 2>&1; rc=\\$?; chmod -R a+rwX /work/out; exit \\$rc"
rc=$?; echo $rc > $D/out/run.exit; exit $rc
''')

    # ------------------------------------------------------------------ die STA (TT setup / FF hold + setup) + clock dumps
    for f, dst in (('tools/die_clock_check.py', 'dcc/tools/die_clock_check.py'), ('tools/die_clock_check.tcl', 'dcc/tools/die_clock_check.tcl'),
                   ('tools/hbm_die_v15/die_clock_tree.py', 'dcc/tools/hbm_die_v15/die_clock_tree.py')):
        txt = git(a.dcc_ref, f)
        if txt is None:
            raise SystemExit(f'dv_rvcase: {f} not at {a.dcc_ref}')
        (out / dst).write_text(txt)
    lnd_pins = ' '.join(sorted(i for i in loc if i in land))
    blk_clk = []
    for mst, nm, _, _ in insts:
        if nm.startswith('u_'):
            c_ = T['masters'].get(mod2master.get(mst, ''), {}).get('clk')
            if c_:
                blk_clk.append(f'{nm}/{c_}')
    link_list = ' '.join(f'{k} {{ld_{k}/i[*]}}' for k, v in sorted(link_pins.items()) if not v.startswith('[get_pins {'))
    lane_list = ' '.join(f'{k} {{{" ".join(lane_bits_mcp[k])}}}' for k in sorted(link_pins) if link_pins[k].startswith('[get_pins {'))
    for c in a.corners:
        std = ' '.join(STD_CORNERS[c])
        (out / f'sta_{c}.tcl').write_text(f'''# S81-DIE7 REAL-VIEW die STA {c} (tools/s81_dv/dv_rvcase.py): closed views + labelled stand-ins (case.json census)
foreach f {{{std}}} {{ read_liberty {PLAT}/lib/NLDM/asap7sc7p5t_$f }}
foreach f [glob /work/views/sta/*_{c}.lib] {{ read_liberty $f }}
foreach f [glob /work/views/rv_*.lib] {{ read_liberty $f }}
read_db /work/out/grt.odb
source {PLAT}/setRC.tcl
set_wire_rc -signal -layer M6
{clocks_sdc}
set_propagated_clock [all_clocks]
set_clock_uncertainty -setup 60 [all_clocks]
set_clock_uncertainty -hold 25 [all_clocks]
set_false_path -from [get_ports rst_n]
source /work/landing.sdc
if {{[catch {{estimate_parasitics -global_routing}} e]}} {{ puts "OT_STA_PARA placement ($e)"; estimate_parasitics -placement }} else {{ puts "OT_STA_PARA global_routing" }}
puts "OT_STA_WNS_SETUP"; report_worst_slack -max -digits 1
puts "OT_STA_WNS_HOLD"; report_worst_slack -min -digits 1
puts "OT_STA_TNS_SETUP"; report_tns -digits 1
foreach {{d tag}} {{max setup min hold}} {{
  if {{[catch {{report_checks -path_delay $d -group_path_count 200000 -endpoint_path_count 1 -unique_paths_to_endpoint -format end > /work/sta/{c}_$tag.end.rpt}}]}} {{
    report_checks -path_delay $d -group_count 200000 -endpoint_count 1 -unique_paths_to_endpoint -format end > /work/sta/{c}_$tag.end.rpt
  }}
  report_checks -path_delay $d -group_path_count 12 -fields {{slew cap fanout}} -digits 1 > /work/sta/{c}_$tag.paths.rpt
}}
report_check_types -max_slew -max_capacitance -violators > /work/sta/{c}_drv.rpt
proc rv_worst {{fo l ps}} {{
  foreach d {{max min}} {{
    set pe [lindex [find_timing_paths -path_delay $d -to $ps -group_path_count 1] 0]
    if {{$pe eq ""}} {{ puts $fo "$l $d none"; continue }}
    set pn "?"; catch {{ set pn [get_full_name [[$pe path] pin]] }}
    set sl "?"; catch {{ set sl [sta::format_time [$pe slack] 1] }}
    puts $fo "$l $d $sl $pn"
  }}
}}
set fo [open /work/sta/link_{c}.rpt w]
foreach {{l pins}} {{{link_list}}} {{ rv_worst $fo $l [get_pins $pins] }}
foreach {{l pins}} {{{lane_list}}} {{ rv_worst $fo $l [get_pins $pins] }}
close $fo
# clock arrivals: landing ck_f (forwarded lane clock at the ring) / ck (receiver root) and every block clock entry
set fo [open /work/sta/clk_{c}.tsv w]
proc rv_arr {{fo p}} {{
  set q [get_pins -quiet $p]
  if {{$q eq ""}} {{ puts $fo "$p\\t-\\t-"; return }}
  set mx -; set mn -
  catch {{ set mx [get_property $q arrival_max_rise] }}; catch {{ set mn [get_property $q arrival_min_rise] }}
  puts $fo "$p\\t$mx\\t$mn"
}}
foreach i {{{lnd_pins}}} {{ rv_arr $fo $i/ck_f; rv_arr $fo $i/ck }}
foreach p {{{' '.join(blk_clk)}}} {{ rv_arr $fo $p }}
close $fo
set ::env(OT_DCC_OUT) /work/sta/die_clock_dump_{c}.tsv
source /work/dcc/tools/die_clock_check.tcl
puts OT_STA_DONE
''')
    runs = ' && '.join(f'/usr/bin/time -v openroad -threads ${{CPUS:-8}} -no_init -exit /work/sta_{c}.tcl > /work/sta/sta_{c}.log 2>&1' for c in a.corners)
    dccs = '\n'.join(f'python3 $D/dcc/tools/die_clock_check.py report $D/sta/die_clock_dump_{c}.tsv --out $D/sta/die_clock_check_{c}.json '
                     f'--pairs $D/pairs.json > $D/sta/die_clock_check_{c}.log 2>&1' for c in a.corners)
    (out / 'sta.sh').write_text(f'''#!/bin/bash
# S81-DIE7 real-view die STA {' / '.join(a.corners)} + die_clock_check + classify (needs out/grt.odb)
D=$(cd $(dirname $0) && pwd); N=dvrvsta-$$; mkdir -p $D/sta
docker run --rm --name $N --cpus=${{CPUS:-8}} --memory=${{MEMG:-64}}g -v $D:/work -w /work openroad/orfs:asap7lock \\
  bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; {runs}; chmod -R a+rwX /work/sta"
rc=$?
{dccs}
python3 $D/classify.py $D {' '.join(a.corners)} > $D/sta/classes.txt 2>&1
echo $rc > $D/sta/run.exit; exit $rc
''')
    (out / 'run_all.sh').write_text('''#!/bin/bash
# S81-DIE7 real-view die chain: GRT (+ die repeaters) -> die STA TT/FF -> die_clock_check -> classes / pair judge
set -u; D=$(cd $(dirname $0) && pwd); date > $D/run_all.start
CPUS=${CPUS:-16} MEMG=${MEMG_GRT:-96} bash $D/run.sh; grt_rc=$?; echo "grt rc $grt_rc" >> $D/run_all.log
[ $grt_rc -eq 0 ] || { date > $D/run_all.done; exit $grt_rc; }
[ -f $D/out/grt.odb ] || { echo "NO grt.odb" >> $D/run_all.log; date > $D/run_all.done; exit 3; }
CPUS=${CPUS:-16} MEMG=${MEMG_STA:-64} bash $D/sta.sh; sta_rc=$?; echo "sta rc $sta_rc" >> $D/run_all.log
date > $D/run_all.done; exit $sta_rc
''')
    for f in ('run.sh', 'sta.sh', 'run_all.sh'):
        (out / f).chmod(0o755)
    # pairs for die_clock_check: every linked block pair + every landing with its receiver
    pairs = sorted({tuple(sorted((f'u_{L["src"]}', f'u_{L["dst"]}'))) for L in links.values() if L['src'] != L['dst']})
    pairs += [(i, f'u_{r["dst"]}') for i, r in sorted(land.items())]
    (out / 'pairs.json').write_text(json.dumps(dict(pairs=[list(p) for p in pairs]), indent=1))
    (out / 'classify.py').write_text(CLASSIFY)
    # ------------------------------------------------------------------ census
    chains = [dict(link=nm, cls=L['cls'], bits=L['bits'], stages=len(L['pts']), src=L['src'], dst=L['dst']) for nm, L in links.items()]
    lrows = {r['link']: dict(E=r['E'], D=r['D'], inst=f'ld_{r["link"]}' if f'ld_{r["link"]}' in loc else None,
                             model='landing_standin_mcp' if f'ld_{r["link"]}' in loc and kind.get(f'ld_{r["link"]}') == 'standin'
                             else 'landing_closed_view' if f'ld_{r["link"]}' in loc else
                             ('frame_lane_pins_mcp' if blocks[r['dst']]['kind'] == 'frame' else 'receiver_pins_mcp_NO_LANDING_TILE')
                             if r['link'] in link_pins else 'none') for r in LP['links']}
    info = dict(schema='opentallas.s81_dv.rv_case.v1', plan=str(a.plan), bind_dir=str(a.bind_dir), bind_table=str(a.bind_table),
                land_plan=str(a.land_plan), die_um=[W, H], area_mm2=round(W * H / 1e6, 2), view_refs=a.view_refs,
                die_v_sha256=__import__('hashlib').sha256((a.bind_dir / 'die.v').read_bytes()).hexdigest(),
                port_bind_rc=bc.get('port_bind_rc'), instances=len(insts),
                census=dict(sorted(census.items())),
                closed_views={m: f'{r}:{d}' for m, (r, d) in views.items() if m in {x[0] for x in insts}},
                standin_instances=sum(1 for v in kind.values() if v == 'standin'),
                closed_instances=sum(1 for v in kind.values() if v == 'closed'), std_instances=sum(1 for v in kind.values() if v == 'std'),
                tie_wires=tz[0], tie_cells=len(ties), fwd_moves_over_20um={k: v for k, v in fwd_moves.items() if v[0] > 20}, placement_moves=dict(moved), placement_far=far[:50], landing_windows=dict(collections.Counter(v['model'] for v in lrows.values())),
                land_plan_links_without_model=no_model, regional_roots='IDEAL top ports ck_<region> (DIE-CLOCK trees not built in this case)',
                label=('NOT_A_DIE_RESULT: real-view case; stand-ins = ' + ', '.join(sorted({m.split(':', 1)[1] for m in census if m.startswith('standin:')}))
                       + ' (no closed view yet); closed = ' + ', '.join(sorted({m.split(':', 1)[1] for m in census if m.startswith('closed:')}))),
                memory_note='case_p4l_r (stand-in die netlist) GRT 38.6 GB / 24 min, STA 24 GB / 3.3 min per corner (s81die6, ot-epyc5)',
                chains=chains, landings=lrows)
    (out / 'case.json').write_text(json.dumps(info, indent=1))
    print(json.dumps({k: v for k, v in info.items() if k not in ('chains', 'landings')}, indent=1))


CLASSIFY = r'''#!/usr/bin/env python3
# S81-DIE7 real-view die STA classes + per-neighbour-pair clock judge (TT and FF): python3 classify.py CASE tt ff
import json, re, sys, collections
D = sys.argv[1]; corners = sys.argv[2:]
case = json.load(open(f'{D}/case.json'))
cls = {c['link']: c['cls'] for c in case['chains']}
def klass(ep):
    inst = ep.split('/')[0]
    if inst.startswith('ld_'):
        return ('landing', cls.get(inst[3:], '?'))
    if re.match(r'st_rs(l|g)?_|rst_root', inst):     # rsg_: hop-0 gate calendar stations (S81-LBGAP/G1)
        return ('reset', 'station')
    m = re.match(r'st_(.+)_(\d+)$', inst)
    if m:
        return (cls.get(m.group(1), m.group(1).split('_')[0]), 'relay')
    if inst.startswith('u_'):
        return ('block_in', inst[2:].split('_')[0])
    return ('other', inst.split('_')[0])
res = {}
for corner in corners:
    for tag in ('setup', 'hold'):
        try: txt = open(f'{D}/sta/{corner}_{tag}.end.rpt').read()
        except OSError: continue
        agg = collections.defaultdict(lambda: dict(n=0, neg=0, wns=1e9, tns=0.0, worst=None))
        for line in txt.splitlines():
            f = line.split()
            if len(f) < 4 or '/' not in f[0]: continue
            try: sl = float(f[-2] if f[-1] in ('(VIOLATED)', '(MET)') else f[-1])
            except ValueError: continue
            k = '|'.join(klass(f[0])); a = agg[k]; a['n'] += 1
            if sl < a['wns']: a['wns'] = sl; a['worst'] = f[0]
            if sl < 0: a['neg'] += 1; a['tns'] += sl
        res[f'{corner}_{tag}'] = dict(sorted(agg.items(), key=lambda kv: kv[1]['wns']))
# ---- per-link landed windows (link_<c>.rpt) and per-neighbour-pair clock judge
win = {}
for c in corners:
    try:
        for line in open(f'{D}/sta/link_{c}.rpt'):
            f = line.split()
            if len(f) >= 3 and f[2] not in ('none', '?'):
                win.setdefault(f[0], {})[f'{c}_{"setup" if f[1] == "max" else "hold"}'] = float(f[2])
    except OSError: pass
arr = {c: {} for c in corners}
for c in corners:
    try:
        for line in open(f'{D}/sta/clk_{c}.tsv'):
            p, mx, mn = line.rstrip('\n').split('\t')
            arr[c][p] = (float(mx) if mx not in ('-', '') else None, float(mn) if mn not in ('-', '') else None)
    except OSError: pass
# SS is sensitivity evidence only (owner option B); pair/window verdicts remain TT/FF.
reported_corners = corners
corners = [c for c in corners if c in ('tt', 'ff')]
sensitivity_windows = {nm: {k: v for k, v in w.items() if not k.startswith(('tt_', 'ff_'))} for nm, w in win.items()}
win = {nm: {k: v for k, v in w.items() if k.startswith(('tt_', 'ff_'))} for nm, w in win.items()}
landed = {}
for nm, r in case['landings'].items():
    if not r['inst']: continue
    row = dict(E=r['E'], D=r['D'], window=win.get(nm, {}))
    for c in corners:
        f_ = arr[c].get(f"{r['inst']}/ck_f", (None, None))[0]; k_ = arr[c].get(f"{r['inst']}/ck", (None, None))[0]
        row[f'{c}_ckf_minus_ck_ps'] = None if f_ is None or k_ is None else round(f_ - k_, 1)
    vals = [row.get(f'{c}_ckf_minus_ck_ps') for c in corners]
    row['tt_ff_drift_ps'] = round(max(vals) - min(vals), 1) if all(v is not None for v in vals) else None
    w = row['window']
    row['verdict'] = ('PASS' if w and all(v >= 0 for v in w.values()) and len(w) == 2 * len(corners) else
                      'FAIL' if w and any(v < 0 for v in w.values()) else 'UNMEASURED')
    landed[nm] = row
frame_lanes = {nm: dict(E=r['E'], window=win.get(nm, {}),
                        verdict=('PASS' if win.get(nm) and all(v >= 0 for v in win[nm].values()) else 'FAIL' if win.get(nm) else 'UNMEASURED'))
               for nm, r in case['landings'].items() if r['model'] in ('frame_lane_pins_mcp', 'receiver_pins_mcp_NO_LANDING_TILE')}
# unlanded neighbour pairs (0-stage lanes: root -> root): receiver vs source clock entry skew <= 80 at TT and FF
ent = {}
for c in corners:
    for p, v in arr[c].items():
        if p.startswith('u_'): ent.setdefault(p.split('/')[0], {})[c] = v
pairs = {}
for ch in case['chains']:
    if ch['stages'] or ch['src'] == ch['dst']: continue
    a_, b_ = f"u_{ch['src']}", f"u_{ch['dst']}"
    row = {}
    for c in corners:
        x = ent.get(a_, {}).get(c, (None, None)); y = ent.get(b_, {}).get(c, (None, None))
        row[c] = None if x[0] is None or y[0] is None else round(abs(x[0] - y[0]), 1)
    pairs[ch['link']] = dict(src=a_, dst=b_, skew_ps=row, verdict=('PASS' if all(v is not None and v <= 80 for v in row.values()) else
                                                                     'FAIL' if any(v is not None and v > 80 for v in row.values()) else 'UNMEASURED'))
judge = dict(rule='landed crossing: ring window (setup_E / hold_E >= 0) at TT and FF; unlanded neighbour pair: |clock entry skew| <= 80 ps at TT and FF',
             regional_roots=case.get('regional_roots'),
             landed=dict(n=len(landed), verdicts=dict(collections.Counter(v['verdict'] for v in landed.values())),
                         max_tt_ff_drift_ps=max((v['tt_ff_drift_ps'] for v in landed.values() if v['tt_ff_drift_ps'] is not None), default=None),
                         worst=sorted(((min(v['window'].values()), k) for k, v in landed.items() if v['window']))[:10]),
             frame_lanes=dict(n=len(frame_lanes), verdicts=dict(collections.Counter(v['verdict'] for v in frame_lanes.values())),
                              worst=sorted(((min(v['window'].values()), k) for k, v in frame_lanes.items() if v['window']))[:10]),
             unlanded_pairs=dict(n=len(pairs), verdicts=dict(collections.Counter(v['verdict'] for v in pairs.values())),
                                 worst=sorted(((max(x for x in v['skew_ps'].values() if x is not None), k) for k, v in pairs.items()
                                               if any(x is not None for x in v['skew_ps'].values())), reverse=True)[:10]))
for c in corners:
    try:
        j = json.load(open(f'{D}/sta/die_clock_check_{c}.json'))
        judge[f'die_clock_check_{c}'] = {k: j[k] for k in list(j)[:6] if k != 'tiles'}
    except Exception as e:
        judge[f'die_clock_check_{c}'] = f'unavailable ({e})'
json.dump(dict(classes=res, judge=judge, sensitivity=dict(corners=[c for c in reported_corners if c not in corners], windows=sensitivity_windows), landed=landed, frame_lanes=frame_lanes, pairs=pairs), open(f'{D}/sta/classes.json', 'w'), indent=1)
for k, v in res.items():
    print(k); [print(f'  {c:40s} n={a["n"]:7d} neg={a["neg"]:7d} wns={a["wns"]:9.1f} tns={a["tns"]:12.1f} {a["worst"]}') for c, a in list(v.items())[:18]]
print(json.dumps(judge, indent=1, default=str)[:6000])
'''


if __name__ == '__main__':
    main()
