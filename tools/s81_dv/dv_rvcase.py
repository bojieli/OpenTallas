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
from clock_roles import contract_clock_nets, whole_spare_frame_clock_outputs, validate_spare_frame_source_guard
from frame_bind import orientation, orient_point, orient_face
from forward_clock_guard import validate_native_forwarding  # noqa: E402
from die_cluster import boundary as CB   # noqa: E402
import abstract_pin_windows as APW   # noqa: E402
import geo_clock as GC   # noqa: E402  (S81.CLK geometric regional roots)
from die_safety import corners as DSC, gen_check as DSG, kit_pins as DSK, m8 as DSM   # noqa: E402  (ROOT14 10-20)

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


def forwarded_payload_width(master):
    """Exact source families whose forwarded payload is the complete i bus.

    Landing reset, selector and receiver clock inputs belong to separate trees;
    tracing them as payload can falsely demand dozens of clock buffers.
    """
    for pattern in (r'dsfd_dvrlyh?_(\d+)_[A-Z]+', r'dsfd_dvland_(\d+)l?',
                    r'dsdv_svc_busland_(\d+)', r'dsdv_pv_local_land_(\d+)'):
        match = re.fullmatch(pattern, master)
        if match:
            return int(match[1])
    if master in ('dsdv_pv_local_land_n32_276', 'dsdv_pv_local_land_n32_source4_276'):
        return 276
    if master == 'dsfd_dvland_pvrd':
        return 562
    return None


def forwarded_payload_contracts(insts, kind, standin_cells):
    result = {}
    for master, name, _, _ in insts:
        width = forwarded_payload_width(master)
        if width:
            cell = standin_cells[name] if kind[name] == 'standin' else master
            if cell in result and result[cell] != width:
                raise ValueError(f'inconsistent forwarded payload width for {cell}')
            result[cell] = width
    return result


def install_controller_corner_repair(out):
    """Patch the generated step artifact, before its clock/data balancing."""
    shutil.copy(HERE / 'ctrl_corner.tcl', out / 'ctrl_corner.tcl')
    hook = ('source /work/ctrl_corner.tcl\n'
            'if {[s81_ctrl_corner_repair /work/ctrl_corner] != 0} { write_db /work/out/ctrl_corner.fail.odb; exit 5 }\n'
            'global_connect\n')
    path = out / 'die_repeaters_step.tcl'
    text = path.read_text()
    marker = 'ot_die_rep_fclk_equalize '
    if marker not in text:
        raise ValueError('controller corner repair requires generated forwarded-clock equalization')
    path.write_text(text.replace(marker, hook + marker, 1))


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
            # Explicit frame clocks are members of the existing core PLL
            # family. Preserve the table's existing PHY/core relationship.
            family = ['clk'] + ([p for p, d in sorted(domains.items())
                if d.get('relationship') == 'same_pll_fixed_phase' and not d.get('asynchronous_to_core')]
                if table.get('instance_clock_ports') else [])
            core_group = 'clk' if len(family) == 1 else '{' + ' '.join(family) + '}'
            lines.append(f'set_clock_groups -asynchronous -group [get_clocks {core_group}] -group [get_clocks {port}]')
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


def _natkey(s):
    return [int(t) if t.isdigit() else t for t in re.split(r'(\d+)', s)]


def kit_dirs(refs, masters, explicit=None, table=None):
    """ROOT14 stand-in fidelity: master -> (ref, kit dir) of the OPEN tile's kit, for its real pin plan.
    Order: --kit-pins MASTER=[REF:]KITDIR > bind table "kits" {master: {ref, kit}} > physical/ref_tile/<master>/ >
    the kit whose spec.json top == master (natural-sort last name = newest revision; alternatives recorded)."""
    out, alts = {}, {}
    for m, v in (explicit or {}).items():
        out[m] = v
    for m, v in ((table or {}).get('kits') or {}).items():
        if m in masters and m not in out:
            out[m] = (v.get('commit') or v.get('ref') or refs[0], v['kit'])
    left = set(masters) - set(out)
    for ref in refs:
        if not left:
            break
        r = subprocess.run(['git', '-C', GITDIR, 'ls-tree', '-r', '--name-only', ref, 'physical/ref_tile/'],
                           capture_output=True, text=True)
        specs = [p for p in r.stdout.split() if re.fullmatch(r'physical/ref_tile/[^/]+/spec\.json', p)]
        for m in sorted(left):
            if f'physical/ref_tile/{m}/spec.json' in specs:
                out[m] = (ref, f'physical/ref_tile/{m}')
        left = set(masters) - set(out)
        if not left or not specs:
            continue
        q = subprocess.run(['git', '-C', GITDIR, 'cat-file', '--batch'], input=''.join(f'{ref}:{p}\n' for p in specs),
                           capture_output=True, text=True)
        tops = collections.defaultdict(list)
        for p, body in zip(specs, re.split(r'^[0-9a-f]{40} blob \d+\n', q.stdout, flags=re.M)[1:]):
            mt = re.search(r'"top"\s*:\s*"([^"]+)"', body)
            if mt and mt.group(1) in left:
                tops[mt.group(1)].append(p.rsplit('/', 1)[0])
        for m, ks in tops.items():
            ks.sort(key=_natkey)
            out[m] = (ref, ks[-1]); alts[m] = ks[:-1]
        left = set(masters) - set(out)
    return out, alts


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


def fwd_relocate(out, insts, ibits, touch, loc, placer, kind, scell, gap=4.0, orientations=None):
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
                        qx, qy = orient_point(q[0], q[1], loc[o][2], loc[o][3], (orientations or {}).get(o, 'R0'))
                        drv[b] = (o, x0 + qx, y0 + qy)
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


def _free_cands(placer, x, y, w, h, near=10, step=4.0, rmax=400.0, ray_um=200.0, per_ray=3):
    """free lower-left positions for a w x h macro around lower-left (x, y): the `near` nearest (square spiral), plus the
    first `per_ray` free points on each of the 4 axis rays (a station can slide along its street); [(x, y, disp)]"""
    out, seen = [], set()

    def ok(dx, dy):
        k = (round(dx, 3), round(dy, 3))
        if k in seen:
            return False
        seen.add(k)
        return not placer.hits((x + dx, y + dy, x + dx + w, y + dy + h))
    if ok(0.0, 0.0):
        out.append((x, y, 0.0))
    k = 1
    while len(out) < near and k * step <= rmax:
        d = k * step
        ring = []
        for t in range(-k, k + 1):
            ring += [(t * step, d), (t * step, -d), (d, t * step), (-d, t * step)]
        ring.sort(key=lambda p: abs(p[0]) + abs(p[1]))
        for dx, dy in ring:
            if ok(dx, dy):
                out.append((x + dx, y + dy, abs(dx) + abs(dy)))
                if len(out) >= near:
                    break
        k += 1
    for ux, uy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        n, d = 0, step
        while n < per_ray and d <= ray_um:
            if ok(ux * d, uy * d):
                out.append((x + ux * d, y + uy * d, d)); n += 1; d += 4 * step
            else:
                d += step
    return out


def rs_chain_place(stations, insts, ibits, touch, loc, placer, hints, blocks, reach, skip_loads=()):
    """C22 --rs-chain-place: place every reset / gate-calendar station (dsfd_rly_1_WN, planned in hints['reset_place'],
    provisional loc = planned point) by a DP over the reset TREE (every station has one station parent: rst_sync ->
    street -> crossing -> leaf -> gate calendar -> ICG ENA / relay rs / landing rs / block rst_n).  Each station picks one
    of ~20 free candidate points near its planned point; cost = 1e6 per hop (centre to centre, to its station children and
    to its fixed non-station loads) over `reach` + 1e3 x excess + displacement um.  Children are committed top-down
    (a candidate taken meanwhile falls back to the next best).  Stage counts are unchanged.
    skip_loads: instances no longer loading a station net in the case netlist (co-forwarded relay reset stages k >= 2)."""
    import time as _t
    t0 = _t.time()
    st = set(stations)
    cen = lambda i: (loc[i][0] + loc[i][2] / 2, loc[i][1] + loc[i][3] / 2)
    plan_c = {i: cen(i) for i in st}
    parent, kids, terms = {}, collections.defaultdict(list), collections.defaultdict(list)
    for i in st:
        outs = {n_ for n_, _ in ibits[i].get('o', []) if n_ not in ('CONST', 'Z', 'UNDECL')}
        for n_ in outs:
            for o in touch.get(n_, ()):
                if o == i:
                    continue
                if o in st:
                    if any(b_[0] == n_ for p_ in ('i', 'rs') for b_ in ibits[o].get(p_, [])):
                        if o not in parent:
                            parent[o] = i; kids[i].append(o)
                    continue
                if o in skip_loads or o not in loc:
                    continue
                if o.startswith('u_') and o[2:] in hints.get('block_rst_pin', {}):
                    terms[i].append(tuple(hints['block_rst_pin'][o[2:]]))
                elif o.startswith('u_') and o[2:] in blocks:
                    b = blocks[o[2:]]; px, py = plan_c[i]
                    terms[i].append((min(max(px, b['x']), b['x'] + b['w']), min(max(py, b['y']), b['y'] + b['h'])))
                else:
                    terms[i].append(cen(o))
    roots = sorted(i for i in st if i not in parent)
    order, seen = [], set()
    for r in roots:                       # iterative pre-order
        stk = [r]
        while stk:
            v = stk.pop()
            if v in seen:
                continue
            seen.add(v); order.append(v); stk.extend(kids[v])
    hop = lambda a_, b_: abs(a_[0] - b_[0]) + abs(a_[1] - b_[1])
    hc = lambda h: 0.0 if h <= reach else 1e6 + 1e3 * (h - reach)
    cand, f = {}, {}
    for i in st:
        x0, y0, w, h, _ = loc[i]
        cs = _free_cands(placer, x0, y0, w, h)
        cand[i] = [(cx + w / 2, cy + h / 2, dd) for cx, cy, dd in cs] or [(x0 + w / 2, y0 + h / 2, 0.0)]
    best_child = {}
    for v in reversed(order):              # children before parents
        fv = []
        for (cx, cy, dd) in cand[v]:
            c = dd + sum(hc(hop((cx, cy), t)) for t in terms[v])
            for u in kids[v]:
                c += min(hc(hop((cx, cy), cand[u][k][:2])) + f[u][k] for k in range(len(cand[u])))
            fv.append(c)
        f[v] = fv
    placed, fallback = {}, 0
    W_, H_ = placer.W, placer.H
    for v in order:
        w, h = loc[v][2], loc[v][3]
        if v in parent:
            pc = placed[parent[v]]
            ranks = sorted(range(len(cand[v])), key=lambda k: hc(hop(pc, cand[v][k][:2])) + f[v][k])
        else:
            ranks = sorted(range(len(cand[v])), key=lambda k: f[v][k])
        for k in ranks:
            cx, cy, _ = cand[v][k]
            r = (cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2)
            if not placer.hits(r):
                placer.add(r); placed[v] = (cx, cy); break
        else:
            pc_ = plan_c[v]
            px_, py_, _ = placer.put(pc_[0] - w / 2, pc_[1] - h / 2, w, h, step=4.0)
            placed[v] = (px_ + w / 2, py_ + h / 2); fallback += 1
        loc[v] = (placed[v][0] - w / 2, placed[v][1] - h / 2, w, h, 'FIRM')
    over, over_plan, worst = [], 0, []
    for v in st:
        for u in kids[v]:
            hp, hq = hop(placed[v], placed[u]), hop(plan_c[v], plan_c[u])
            over_plan += hq > reach
            if hp > reach:
                over.append(('reset_station', u, v, round(hp, 1), round(hq, 1)))
        for t in terms[v]:
            hp = hop(placed[v], t)
            if hp > reach:
                over.append(('station_load', v, f'{t[0]:.1f},{t[1]:.1f}', round(hp, 1), None))
    disp = sorted(hop(placed[v], plan_c[v]) for v in st)
    rep = dict(stations=len(st), roots=len(roots), station_hops=sum(len(k_) for k_ in kids.values()),
               load_hops=sum(len(t_) for t_ in terms.values()), planned_station_hops_over_reach=over_plan,
               placed_hops_over_reach=len(over), by_kind=dict(collections.Counter(o[0] for o in over)),
               max_hop_um=max((o[3] for o in over), default=None), fallback_spiral=fallback,
               disp_um=dict(median=round(disp[len(disp) // 2], 1), p99=round(disp[int(len(disp) * 0.99)], 1), max=round(disp[-1], 1)) if disp else None,
               reach_um=reach, seconds=round(_t.time() - t0, 1),
               rule='tree DP: candidates near each planned point (nearest free + 4 axis rays), cost 1e6/hop over reach '
                    '+ 1e3 x excess + displacement; same stations, same stage counts')
    return rep, sorted(over, key=lambda o: -o[3])


def gen_safety_facts(insts, ibits, T, mod2master, top, links, LP, loc, kind, blocks, reach):
    """ROOT14 10-20: GEN safety facts (opentallas.die_gen_safety_facts.v1) of a real-view S81 die case"""
    region = {}
    roots = {}
    abut_region = {}
    for mst, nm, _, _ in insts:
        if not nm.startswith('u_'):
            continue
        clk = T['masters'].get(mod2master.get(mst, ''), {}).get('clk')
        nets_ = [n_ for n_, _ in ibits[nm].get(clk, [])] if clk else []
        n_ = next((x for x in nets_ if x not in ('CONST', 'Z', 'UNDECL')), None)
        r_ = n_ or f'?{nm}'
        region[nm[2:]] = r_
        roots[r_] = n_ if (n_ in top and n_.startswith('ck_')) else None
        # S81.CLK2 (10-22): an ABUTTED face (master 'abut': plan_ports realised as named connections to the peer, e.g.
        # dsfd_ctrl_rg3 dfi0/dfi1 -> HBM PHY k_*/kr_*) is IO of the master's clk_peer clock (ctrl ckh = ck_hbm: the
        # core <-> hclk CDC is the closed tile's async FIFO, physical/ref_tile/s81ctrl_rg3 clock.sdc) -> its region is the
        # peer clock net, not the core clk
        tm = T['masters'].get(mod2master.get(mst, ''), {})
        ab = tm.get('abut') or {}
        for cp in tm.get('clk_peer') or []:
            pn = next((x for x, _ in ibits[nm].get(cp.get('port'), []) if x in top and x.startswith('ck_')), None)
            if pn and cp.get('master') == ab.get('peer'):
                for pp in ab.get('plan_ports', []):
                    abut_region[(nm[2:], pp.split('.')[0])] = pn
                    roots[pn] = pn
    lp = {r['link']: r for r in LP['links']}
    crossings, wires = [], []
    for ln, L in sorted(links.items()):
        wires.append(dict(id=ln, kind=L['cls'], pts=[list(L['sxy'])] + [list(p) for p in L['pts']] + [list(L['dxy'])]))
        rs, rd = region.get(L['src'], f"?{L['src']}"), region.get(L['dst'], f"?{L['dst']}")
        rs = abut_region.get((L['src'], L.get('sport')), rs)
        rd = abut_region.get((L['dst'], L.get('dport')), rd)
        roots.setdefault(rs, None); roots.setdefault(rd, None)
        if rs == rd:
            continue
        li = f'ld_{ln}'
        landing = None
        if li in loc:
            landing = li
            ck = [n_ for n_, _ in ibits.get(li, {}).get('ck', [])]
            if not any(x in top and x.startswith('ck_') for x in ck):
                rd = f'{li}.ck'; roots[rd] = None              # landing ring read on no region root
        elif ln in lp and blocks.get(L['dst'], {}).get('kind') == 'frame':
            landing = f"frame:{L['dst']}"                       # crs4 ring inside the receiving frame
        crossings.append(dict(id=ln, src_region=rs, dst_region=rd, landing=landing, bits=L['bits']))
    return dict(schema=DSG.SCHEMA_FACTS, design='s81', reach_um=reach, regions={k: dict(root=v) for k, v in roots.items()},
                crossings=crossings, wires=wires)


def clock_regions_report(insts, ibits, T, mod2master, top, loc, links, LP, plan, bc, reach):
    """S81.CLK (10-21): geometric regional roots of the bound die (tools/s81_dv/geo_clock.py).
    Returns (report, landed): per core root (top ck_* not a declared clock domain) its PLACED sink count / bbox against
    the region extent (+ reach) -> gate; the landed crossings for die_clock_check --landed (reset release crossings =
    parent station -> the receiving region's <child>_xk stage; lanes landed by a ring whose two block roots differ);
    the 0-stage block pairs across roots (unlanded neighbour boundaries, judged at 80 ps, never claimed landed) and the
    reset-leaf -> station / landing reads across roots (counted, not claimed landed)."""
    W, H = plan['facts']['die_um']
    cr = bc.get('clock_regions') or {}
    domains = set(T.get('clock_domains', {}))
    core = sorted(n for n in top if n.startswith('ck_') and n not in domains)
    pin_root = {}                     # inst -> its clock-pin root (first core / domain top net on its clock pin)
    for mst, nm, _, _ in insts:
        if nm.startswith('u_'):
            cps = [T['masters'].get(mod2master.get(mst, ''), {}).get('clk')]
        elif mst.startswith('dsfd_dvland_') or mst.startswith('dsfd_rly_1') or nm.startswith('st_rs') or nm.startswith('rst_root'):
            cps = ['ck']
        else:
            cps = ['CLK', 'A', 'ck']
        for cp in cps:
            got = [n_ for n_, _ in ibits[nm].get(cp, []) if n_ in top and n_.startswith('ck_')] if cp else []
            if got:
                pin_root[nm] = got[0]
                break
    sinks = collections.defaultdict(list)
    for mst, nm, _, cm in insts:
        if nm not in loc:
            continue
        x, y, w_, h_, _ = loc[nm]
        for p_, bits in ibits[nm].items():
            for n_ in {b_[0] for b_ in bits} & set(core):
                sinks[n_[3:]].append((nm, x + w_ / 2, y + h_ / 2))
    if cr.get('mode') == 'geometric':
        grid = GC.Grid.from_spec(cr['grid'])
        reg = {b: (f'b_{b}' if r['kind'] == 'own_root' else r['cell']) for b, r in cr['blocks'].items()}
        ext = GC.extents(grid, plan['blocks'], reg, [b for b, r in cr['blocks'].items() if r['kind'] == 'table_clock'])
        spec = grid.spec()
    else:
        ext, spec = {}, dict(mode=cr.get('mode', 'logical (bind before S81.CLK)'))
    gate = GC.root_gate({r: sorted(set(v)) for r, v in sinks.items()}, ext, reach)
    # ---- landed crossings
    landed_pairs, rx = [], (bc.get('reset') or {}).get('crossings', [])
    for x_ in rx:
        landed_pairs.append([x_['parent'], x_['stage'], 'reset_release_crossing'])
    lp = {r['link'] for r in LP['links']}
    bkind = {b['name']: b.get('kind') for b in plan['blocks']}
    by_pair = collections.defaultdict(list)
    for ln, L in links.items():
        if L['src'] == L['dst']:
            continue
        ra, rb = pin_root.get(f'u_{L["src"]}'), pin_root.get(f'u_{L["dst"]}')
        ring = (f'ld_{ln}' in loc) or (ln in lp and bkind.get(L['dst']) == 'frame' and bool(L['pts']))
        by_pair[tuple(sorted((f'u_{L["src"]}', f'u_{L["dst"]}')))].append((ln, ra != rb, ring, L['cls']))
    unlanded, async_pairs = [], 0
    asyn = {k for k, v in T.get('clock_domains', {}).items() if v.get('asynchronous_to_core')}
    for (a_, b_), rows in sorted(by_pair.items()):
        if not any(c for _, c, _, _ in rows):
            continue
        if pin_root.get(a_) in asyn or pin_root.get(b_) in asyn:
            async_pairs += 1          # declared asynchronous domain (PHY ck_hbm, async FIFO): CDC, not a region crossing
            continue
        if all(r for _, c, r, _ in rows if c):
            landed_pairs.append([a_, b_, 'lane_ring'])
        else:
            unlanded.append(dict(a=a_, b=b_, links=[ln for ln, c, r, _ in rows if c and not r],
                                 classes=sorted({k for _, c, r, k in rows if c and not r})))
    # reset leaf reads across roots (station / landing rs from a station of another root), xk pairs excluded
    drv = {}
    for mst, nm, _, _ in insts:
        if nm.startswith('st_rs') or nm.startswith('rst_root'):
            for n_, _ in ibits[nm].get('o', []):
                drv[n_] = nm
    xk = {(x_['parent'], x_['stage']) for x_ in rx}
    sink_x = collections.Counter()
    for mst, nm, _, _ in insts:
        if 'rs' not in ibits[nm] or nm not in pin_root:
            continue
        for n_, _ in ibits[nm]['rs']:
            d_ = drv.get(n_)
            if d_ and pin_root.get(d_) and pin_root[d_] != pin_root[nm] and (d_, nm) not in xk:
                sink_x['reset_station' if nm.startswith('st_rs') else 'landing' if nm.startswith('ld_') else 'other'] += 1
    rep_ = dict(mode=cr.get('mode', 'logical'), grid=spec, core_roots=len(core),
                own_roots=sorted(b for b, r in (cr.get('blocks') or {}).items() if r['kind'] == 'own_root'),
                gate=dict(verdict=gate['verdict'], fails=gate['fails'], reach_um=reach, max_span_um=gate['max_span_um'],
                          rule='every non-frame root: placed sink bbox inside its extent (cell U member blocks | own block) + reach'),
                regions=gate['roots'],
                crossings=dict(reset_release_landed=len(rx), lane_ring_landed_pairs=sum(1 for p_ in landed_pairs if p_[2] == 'lane_ring'),
                               unlanded_neighbour_pairs=len(unlanded), async_domain_pairs=async_pairs,
                               unlanded_by_class=dict(collections.Counter(k for u in unlanded for k in u['classes'])),
                               unlanded_first=unlanded[:20],
                               reset_reads_across_roots=dict(sink_x),
                               max_reset_crossings_on_path=(bc.get('reset') or {}).get('max_crossings_on_path')),
                landed_rule='reset release crossing = one extra registered stage <child>_xk on the receiving region root '
                            '(release depth +1 per crossing, bind reset calendar); lane crossing = dsfd_dvland ring / frame crs4; '
                            '0-stage neighbour pairs stay judged at the 80 ps neighbour budget (not claimed landed)')
    landed = dict(schema='opentallas.s81_dv.landed.v1', pairs=[p_[:2] for p_ in landed_pairs],
                  kinds=dict(collections.Counter(p_[2] for p_ in landed_pairs)),
                  regions=[],      # never a whole-region exemption: 0-stage neighbour pairs between two roots stay judged
                  region_info={r: dict(sinks=v['sinks'], bbox=v['bbox'], extent=v.get('extent')) for r, v in gate['roots'].items()},
                  grid=spec)
    return rep_, landed


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
    ap.add_argument('--signal-top-layer', choices=('M7', 'M8'), default='M7', help='M8 is die signals only; M9 stays clock/PG')
    ap.add_argument('--dcc-ref', default='origin/main', help='ref of tools/die_clock_check.{py,tcl} (+ hbm_die_v15/die_clock_tree.py)')
    ap.add_argument('--corners', nargs='+', choices=('tt', 'ff', 'ss'), default=['tt', 'ff'])
    ap.add_argument('--congestion-iterations', type=int, default=30)
    ap.add_argument('--macro-views', action='store_true',
                    help=f'bind die-level macros with a real view under {MACRO_DIR}/<m>/ (HBM PHY _k, SRAMs) instead of a stand-in')
    ap.add_argument('--standin-pins', choices=('kit', 'centroid'), default='kit',
                    help='ROOT14 10-20: an OPEN tile stand-in takes its pins from the tile kit pin plan (face/order/layer: '
                         'io_tcl / assigned_pins.json / spec pins faces); bits the kit does not place (or centroid = old '
                         'behaviour, diagnostic) fall back to the plan link end points / neighbour-centroid projection')
    ap.add_argument('--kit-pins', nargs='*', default=[], metavar='MASTER=[REF:]KITDIR',
                    help='explicit kit for an open master (default: bind table kits, physical/ref_tile/<master>, spec top match)')
    ap.add_argument('--gen-safety-diag', metavar='REASON',
                    help='ROOT14: run past a GEN safety FAIL (crossing without landing/root, wire hop > 405 um) as a '
                         'labelled diagnostic (NOT_A_DIE_RESULT); default = the GEN fails')
    ap.add_argument('--clock-region-diag', metavar='REASON',
                    help='S81.CLK: run past a clock-region gate FAIL (a non-frame root whose placed sink bbox leaves its '
                         'geometric extent + reach, e.g. a pre-S81.CLK logical bind) as a labelled diagnostic')
    ap.add_argument('--reach-um', type=float, default=DSG.REACH_UM, help='GEN safety planning reach (owner 405 um)')
    ap.add_argument('--no-ir', metavar='REASON', help='skip the die IR-drop step in run_all.sh (labelled NOT_A_DIE_RESULT)')
    ap.add_argument('--rfw', action='store_true',
                    help='STW-S81c-DIE-C21 cap21: co-forwarded relay reset -- every forwarded relay stage k>=1 takes rs from a '
                         'die-level retimer clocked by its own forwarded clock fck[k], fed from the retimer of stage k-1 '
                         '(the reset travels the lane with its clock; was a regional-root reset grid flop -> per-stage CDC)')
    ap.add_argument('--hold-eco', action='store_true',
                    help='STW-S81c-DIE-C21 cap21: post-GRT die hold ECO session (hold_eco.sh) before the die STA: hold buffers '
                         'on die data nets only (clock / reset-distribution / special / skip nets dont_touch; closed views are '
                         'macros and cannot be edited)')
    ap.add_argument('--dieclk', action='store_true',
                    help='STW-S81c-DIE-C22 cap22: physical regional clock tree per die clock root port (tools/die_clock '
                         'build.py safe DME tree + measured TT/FF trim) between placement and the die repeater step; the '
                         'root port stays a top port and drives its regional entry buffer ckr_<root> at the sink median; '
                         'STA propagates through the real trees (was: ideal special root nets up to 9.9 mm)')
    ap.add_argument('--dieclk-iters', type=int, default=3, help='measured trim iterations of the die clock build')
    ap.add_argument('--fck-out-pin', action='store_true',
                    help='STW-S81c-DIE-C22 cap22: a stand-in forwarded-clock OUTPUT bit (slice ck_xc[k], no kit pin) that '
                         'drives one hop-0 forward cell sits beside its lane data launch (as nX_fck lanes); was the '
                         'centroid of the whole bus loads -> up to 6.8 mm unbuffered clock-pin nets to the fwd ICG')
    ap.add_argument('--rs-chain-place', action='store_true',
                    help='STW-S81c-DIE-C22 cap22: reset / gate-calendar stations placed by a tree DP over the reset tree '
                         '(candidates near each planned point, cost = hops over --reach-um, then displacement) after the '
                         'forward cells are relocated; same stations, same stage counts (no latency change); was a '
                         'per-station spiral that pushed 400-um planned hops to 405-1,228 um')
    a = ap.parse_args()
    # ROOT14 10-20 (COORD 21:29 (a)): TT setup + FF hold on every die build, diagnostic ones included
    a.corners = DSC.required(a.corners)
    M8 = DSM.model(a.signal_top_layer)
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
    # S81.CLK2 (10-22): a chain-end variant module (e.g. u_irg_07 = dsdv_idx_rg3_nq, the qo-less IDX tail) is bound in
    # place of its plan master; without this its stand-in had no clock pin rule (lib with no timing arcs) and gen_safety
    # put it on no root (C2 '?u_irg_07')
    for k, m in T['masters'].items():
        ce = (m.get('chain_end') or {}).get('module')
        if ce:
            mod2master.setdefault(ce, k)
    links = {}
    for l in plan['links']:
        (bi0, sp0, x0, y0, _), (bi1, sp1, x1, y1, _) = l['e']
        n0, n1 = plan['blocks'][bi0]['name'], plan['blocks'][bi1]['name']
        pts = [tuple(p) for p in l['sp']] if 'sp' in l else [(h[2], h[3]) for h in l['h'][:-1]]
        links[l['i'].replace('-', '_')] = dict(src=n0, dst=n1, sxy=(x0, y0), dxy=(x1, y1), bits=l['b'], pts=pts, cls=l['c'], hops=l['h'],
                                               sport=sp0, dport=sp1)

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
    landing_instances = {row['inst'] for row in hints['landings']}
    # clock nets: region roots, lane forwarded clocks (relay ck / ck_o, landing ck_f, forward cells), peer clocks (bind clk_peer)
    clocknets = {n for n in top if n.startswith('ck_')}
    for mst, nm, _, cm in insts:
        cps = []
        if mst.startswith('dsfd_dvrlyh_') or mst.startswith('dsfd_dvrly_'):
            cps = ['ck', 'ck_o']
        elif nm in landing_instances:
            cps = ['ck_f', 'ck']
        elif mst.endswith('_ASAP7_75t_R') and nm.startswith('fwd_'):
            cps = ['A', 'Y', 'CLK', 'GCLK']     # BUFx8 forward / ICGx4 hop-0 lane clock gate (S81-LBGAP/G1)
        else:
            tm = T['masters'].get(mod2master.get(mst, ''), {})
            cps = [tm.get('clk')] + [cp['port'] for cp in tm.get('clk_peer', [])]
        for p in cps:
            if p and p in ibits[nm]:
                clocknets |= {n_ for n_, _ in ibits[nm][p] if n_ not in ('CONST', 'Z', 'UNDECL')}

    # Bind-table clock roles cover direct source->frame lanes too. Such lanes
    # have no fwd_ gate or relay to seed clocknets (e.g. slice ck_xc -> xk).
    # Only the existing source-guarded selected72 X-chain-end declaration can
    # omit an entire forwarded xok port. Strict bind must still be PASS; active
    # clock outputs and every clock input keep the normal contract checks.
    clock_directions = {m: {p: r[0] for p, r in module.ports.items()} for m, module in idx.items()}
    strict_clock_bind = json.load(open(a.bind_dir / 'port_bind.json'))
    unused_clock_outputs = set()
    spare_clock_context = None
    if strict_clock_bind.get('verdict') == 'PASS':
        validate_spare_frame_source_guard(
            T.get('selected72_spare_faces_g8', {}), {m: v.path for m, v in idx.items()},
            insts, a.bind_dir / 'die.v', strict_clock_bind, git)
        spare_clock_context = (T.get('rtl_widths', {}), json.load(open(a.bind_dir / 'pads.json')),
                               T.get('selected72_spare_faces_g8', {}))
        unused_clock_outputs = whole_spare_frame_clock_outputs(
            insts, ibits, T['masters'], mod2master, clock_directions,
            T.get('rtl_widths', {}), json.load(open(a.bind_dir / 'pads.json')),
            T.get('selected72_spare_faces_g8', {}))
    clocknets, contract_clock_inputs = contract_clock_nets(
        insts, ibits, T['masters'], mod2master,
        clock_directions, clocknets, spare_frame_context=spare_clock_context)

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
                # Source-pinned native forwarding only: never reinterpret SELF ETM tables.
                validate_native_forwarding(m, c, lib,
                    lambda artifact: git(ref, f'{d}/{artifact}'))
                (out / 'views' / 'sta' / f'{m}_{c}.lib').write_text(lib)    # STA corner libs (the GRT reads views/*.lib: TT copy below)
            tt_lib = git(ref, f'{d}/{m}_tt.lib')
            validate_native_forwarding(m, 'tt', tt_lib,
                lambda artifact: git(ref, f'{d}/{artifact}'))
            (out / 'views' / f'{m}.lib').write_text(tt_lib)
    placer = Placer(W, H)
    loc = {}            # inst -> (x, y lower-left, w, h, status)
    orientations = {f'u_{b["name"]}': orientation(T, b['name']) for b in blocks.values()}
    _rm = a.bind_dir / 'relay_mirror.json'  # historical IDX4 opposite vertical view placed MX
    if _rm.exists():
        orientations.update({i: v['orient'] for i, v in json.loads(_rm.read_text()).items()})
    for b in blocks.values():
        loc[f'u_{b["name"]}'] = (b['x'], b['y'], b['w'], b['h'], 'FIRM')
        placer.add((b['x'], b['y'], b['x'] + b['w'], b['y'] + b['h']))
    # S81-LINKS gap reserves (plan['blockages']): geometry only -- no instance, no pins; the Python placer, the hard
    # placement blockage and the M1-M6 routing obstruction below keep every cell and lower-layer wire out of them
    # (M7/M8 stay open over them exactly as over the stand-in SerDes columns beside them)
    reserves = plan.get('blockages', [])
    for b in reserves:
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
        body = T.get('landing_assemblies', {}).get(mst_of[i], {}).get('body_um')
        if body:
            # Explicit source/native outline grant, fixed orientation. No inherited view.
            w_, h_ = map(float, body)
            if f in 'SN':
                xx = x - w_ / 2; yy = b['y'] - h_ - 2.0 if f == 'S' else b['y'] + b['h'] + 2.0
            else:
                yy = y - h_ / 2; xx = b['x'] - w_ - 2.0 if f == 'W' else b['x'] + b['w'] + 2.0
        px_, py_, dd = placer.put(xx, yy, w_, h_, prefer=pref)
        loc[i] = (px_, py_, w_, h_, 'FIRM'); moved['landing'] += dd is not None and dd > 0
        if dd is None or dd > 200:
            far.append((i, dd))
    for p in hints['reset_place']:
        i = p['inst']; x, y = p['xy']
        if a.rs_chain_place:
            # C22: provisional = planned point (stand-in heuristic pins read it); placed by rs_chain_place after the
            # forward cells are relocated (the gate-calendar end station must reach its fwd ICG ENA)
            loc[i] = (x - rw / 2, y - rh / 2, rw, rh, 'FIRM')
            continue
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
    # C22 --fck-out-pin: (net, bit) of a block forwarded-clock output -> the ONE hop-0 forward cell it clocks
    fck_bit_icg, fck_out_pins = {}, collections.Counter()
    if a.fck_out_pin:
        _cnt = collections.Counter()
        for mst, nm, _, _ in insts:
            if nm.startswith('fwd_') and mst.endswith('_ASAP7_75t_R') and nm[4:] in links:
                for b_ in ibits[nm].get('CLK', []):
                    if b_[0] not in ('CONST', 'Z', 'UNDECL'):
                        fck_bit_icg[b_] = nm; _cnt[b_] += 1
        fck_bit_icg = {k: v for k, v in fck_bit_icg.items() if _cnt[k] == 1}

    # ------------------------------------------------------------------ stand-in abstracts + libs
    census = collections.Counter(); scell = {}
    lane_bits_mcp = collections.defaultdict(list)     # link -> [pin names] (frame lanes: model on the frame pins)
    # ROOT14 10-20 stand-in fidelity: the OPEN tile's kit pin plan (face / order / layer) places its stand-in pins
    open_masters = sorted({mst for mst, nm, _, _ in insts if kind[nm] == 'standin'})
    kitpin = {}; kit_alts = {}; pin_src = collections.Counter(); kit_rows = {}
    if a.standin_pins == 'kit':
        expl = {}
        for e in a.kit_pins:
            m_, _, v_ = e.partition('=')
            r_, _, k_ = v_.rpartition(':')
            expl[m_] = (r_ or a.view_refs[0], k_)
        kdirs, kit_alts = kit_dirs(a.view_refs, open_masters, expl, T)
        for m_, (r_, k_) in sorted(kdirs.items()):
            md = idx.get(m_)
            pw = {}
            for mst_, nm_, _, _ in insts:
                if mst_ == m_:
                    pw = {pp: (len(bb), bool(md.ports[pp][1]) if md and pp in md.ports else len(bb) > 1) for pp, bb in ibits[nm_].items()}
                    break
            plan_ = DSK.load_plan(lambda rel, r_=r_: git(r_, rel), k_, pw)
            if plan_:
                kitpin[m_] = plan_
            kit_rows[m_] = dict(ref=r_, kit=k_, source=plan_['source'] if plan_ else None, pins=len(plan_['pins']) if plan_ else 0,
                                alternatives=kit_alts.get(m_, [])[-5:])
    # Explicit frame plans are stored in native master coordinates. Placement
    # applies the instance transform once; never pre-mirror these kit pins.
    for master, pp in T.get('standin_pin_plans', {}).items():
        if master in open_masters:
            kitpin[master] = pp
            kit_rows[master] = dict(ref=T.get('frame_lp_binding', {}).get('source_ref'),
                source=pp['source'], pins=len(pp['pins']), coordinates='native_master_unoriented')
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
                kp = DSK.place(kitpin[mst], pn, w, h) if mst in kitpin and not (n_ in top and not bname) else None
                if kp is not None:
                    f, t, klay = kp
                    kinds.add('clock' if (n_ in clocknets or n_.startswith('ck_')) and d != 'output' else
                              'fclk_out' if n_ in clocknets and d == 'output' else 'data')
                    lm = LINK_RE.match(n_)
                    if lm and bname:
                        L = links.get(lm.group(1))
                        if L and lm.group(2) == 'dst' and d == 'input' and L['dst'] == bname:
                            lane_bits_mcp[lm.group(1)].append(f'{nm}/{pn}')
                    lay, rect = DSK.pin_rect(f, t, w, h, klay)
                    lefp.append((pn, d, lay, rect)); sig.append((pn, lay, rect)); pin_src['kit'] += 1
                    continue
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
                    elif L is None and d == 'output' and (n_, bi) in fck_bit_icg:
                        # C22: block forwarded-clock output bit (slice ck_xc[k]) -> its lane's hop-0 forward cell: the
                        # pin sits right after that lane's data launch bits, so clock and data leave together
                        ln = fck_bit_icg[(n_, bi)][4:]; L = links[ln]
                        if L['src'] == bname:
                            x, y = L['sxy']
                            f = face_of(blocks[bname], x, y)
                            t = (y - y0 if f in 'WE' else x - x0) + L['bits'] * PITCH / 2 + PITCH * (1 + slot[('f', ln)]); slot[('f', ln)] += 1
                            fck_out_pins['beside_lane'] += 1
                        else:
                            fck_out_pins['lane_src_mismatch'] += 1
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
                # Heuristics/projected link endpoints above are in placed
                # physical coordinates. Invert the instance reflection before
                # writing the native LEF; place_inst will apply it once.
                f, t = orient_face(f, t, w, h, orientations.get(nm, 'R0'))
                lay, rect = pin_rect(f, t, w, h)
                lefp.append((pn, d, lay, rect)); sig.append((pn, lay, rect))
                pin_src['heuristic_no_kit' if mst not in kitpin else 'heuristic_bit_not_in_kit'] += 1
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
    fwd_moves = fwd_relocate(out, insts, ibits, touch, loc, placer, kind, scell, orientations=orientations)
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
    # ------------------------------------------------------------------ STW-S81c-DIE-C21 co-forwarded relay reset (--rfw)
    # MAIN4 die STA: relay_reset hold -23.2 ns on 7459 of 7953 relay rs pins.  Stage k of a forwarded lane is clocked by
    # n<lane>_fck[k] (stage k-1 ck_o; ~245 ps per hop, 23.4 ns at stage 94) while its rs came from a reset grid flop
    # st_rs_* on an IDEAL regional root ck_g*: an uncontrolled phase per stage = a reset CDC, not a buffering problem.
    # Fix (die glue only, no block interface / topology change): rfw_<lane>_<k> (DFFHQNx1, CLK = fck[k]) +
    # rfwi_<lane>_<k> (INVx1) per stage k>=1; D(k) = rfwq(k-1) (stage 1: its own former grid rs, local), rs(stage k) =
    # rfwq(k).  Reset release reaches stage k k cycles after stage 1, exactly as the data wave does; hop = the relay hop.
    rfw_cells, rfw_rows, rfw_rs, rfw_first = [], [], {}, set()
    if a.rfw:
        fck_re = re.compile(r'^n(\w+)_fck\[(\d+)\]$')
        lanes_ = collections.defaultdict(dict)
        for i_, (mst, nm, prm, cm) in enumerate(insts):
            if not mst.startswith('dsfd_dvrly') or kind.get(nm) == 'standin' or 'rs' not in cm or 'ck' not in cm:
                continue
            m_ = fck_re.match(cm['ck'].strip())
            if m_:
                lanes_[m_.group(1)][int(m_.group(2))] = i_
        for lane_, st_ in sorted(lanes_.items()):
            prevq = None
            for k_ in sorted(st_):
                i_ = st_[k_]
                mst, nm, prm, cm = insts[i_]
                if k_ == 0:
                    prevq = None
                    continue
                d_ = prevq if (prevq is not None and (k_ - 1) in st_) else cm['rs'].strip()
                if CONST_RE.search(d_) or CONST_RE.search(cm['rs']):
                    prevq = None            # constant reset (tied stage): leave it as bound
                    continue
                qn, q = f'rfwn_{lane_}_{k_}', f'rfwq_{lane_}_{k_}'
                decl.append(f'  wire {qn};'); decl.append(f'  wire {q};')
                rfw_cells.append(f'  DFFHQNx1_ASAP7_75t_R rfw_{lane_}_{k_} (.CLK({cm["ck"].strip()}), .D({d_}), .QN({qn}));')
                rfw_cells.append(f'  INVx1_ASAP7_75t_R rfwi_{lane_}_{k_} (.A({qn}), .Y({q}));')
                rfw_rows.append((f'rfw_{lane_}_{k_}', f'rfwi_{lane_}_{k_}', nm))
                if d_ == cm['rs'].strip():
                    rfw_first.add(nm)       # its retimer (at this stage's rs pin) still loads the station net
                rfw_rs[nm] = q          # body-only override: insts / ibits (gen safety, clock regions) stay the bind netlist
                prevq = q
        print(f'RFW co-forwarded relay reset: lanes={len(lanes_)} stages_rewired={len(rfw_rows)} cells={len(rfw_cells)}', flush=True)
    body = []
    for mst, nm, prm, cm in insts:
        # STW-S81c-DIE 10-22 (cap18/CLK2 fclk pairing_errors=2): a stand-in LANDING whose forwarded payload is a
        # declared i-bus contract (forwarded_payload_width) receives its zero padding from the die top
        # (pvso_*_local_l2 = {tz[265:0], 10 real bits}); those padding pins are real boundary pins of the stand-in LEF,
        # so drive them with physical TIELO/TIEHI cells like any bound instance. A floating 1-pin wire left 266 of the
        # 276 contracted bits untraced -> data_port_contract_ERROR. Straps (k, sid ...) of stand-ins stay internal.
        payload_w = forwarded_payload_width(mst)
        if nm in rfw_rs:
            cm = dict(cm, rs=rfw_rs[nm])
        cs = ', '.join(f'.{p}({detie(e, nm, kind[nm] != "standin" or (p == "i" and bool(payload_w)))})'
                       for p, e in cm.items())
        if kind[nm] == 'standin':
            body.append(f'  {scell[nm]} {nm} ({cs});')
        else:
            body.append(f'  {mst} {nm} ({cs});')
    for _, s_, _, _ in assigns:
        if CONST_RE.search(s_):
            raise SystemExit('dv_rvcase: constant assign has no physical load to place its tie at -- bind it to a port')
        body.append('  ' + s_ + ';')
    body += ties
    body += rfw_cells
    # ------------------------------------------------------------------ C22 regional die clock entry (--dieclk)
    # Every die clock root port ck_* keeps its top port; the port drives ONE entry buffer ckr_<root> (placed at the
    # median of its sinks) whose output net carries all former loads.  tools/die_clock/build.py then builds the physical
    # regional tree from ckr_<root>/Y (safe DME tree, repeater <= 220 um, measured TT/FF trim) before the repeater step.
    dieclk_ports = []
    if a.dieclk:
        if not a.die_repair:
            raise SystemExit('dv_rvcase: --dieclk needs --die-repair (two-session die flow)')
        cand_p = sorted(n for n in tin if n.startswith('ck_') and nets[n][0] == 1 and touch.get(n))
        if cand_p:
            rx_ = re.compile(r'(?<![\w$])(' + '|'.join(map(re.escape, sorted(cand_p, key=len, reverse=True))) + r')(?![\w$\[])')
            used = set()

            def _sub(m):
                used.add(m.group(1)); return 'ckrn_' + m.group(1)
            body = [rx_.sub(_sub, ln) for ln in body]
            dieclk_ports = sorted(used)
            for p_ in dieclk_ports:
                decl.append(f'  wire ckrn_{p_};')
                body.append(f'  BUFx24_ASAP7_75t_R ckr_{p_} (.A({p_}), .Y(ckrn_{p_}));')
        print(f'DIECLK entry buffers: roots={len(dieclk_ports)} (ck_* input ports with loads {len(cand_p)})', flush=True)
    hdr = [f'// S81-DIE7 REAL-VIEW die case netlist from {a.bind_dir / "die.v"} (tools/s81_dv/dv_rvcase.py): bound instances, '
           'stand-in cells rv_* where no closed view, constant bits driven by TIEHI/TIELO cells tie_tz_*',
           f'module dv_die ({", ".join(sorted(top))});']
    for n in sorted(nets):
        wv, lo = nets[n]
        rng = f'[{lo + wv - 1}:{lo}] ' if wv > 1 or lo else ''
        hdr.append(f'  {"input" if n in tin else "output" if n in tout else "wire"} {rng}{n};')
    (out / 'die.v').write_text('\n'.join(hdr + decl + body + ['endmodule']) + '\n')

    # ------------------------------------------------------------------ C22 reset-tree DP placement (--rs-chain-place)
    rsdp, rsdp_over = None, []
    if a.rs_chain_place:
        rsdp, rsdp_over = rs_chain_place([p['inst'] for p in hints['reset_place']], insts, ibits, touch, loc, placer,
                                         hints, blocks, a.reach_um, skip_loads=set(rfw_rs) - rfw_first)
        (out / 'rs_chain_place.tsv').write_text('kind\tcapture\tsource\thop_um\tplanned_hop_um\n' +
                                                ''.join('\t'.join(map(str, o)) + '\n' for o in rsdp_over))
        print('RS_CHAIN_PLACE', json.dumps(rsdp), flush=True)
        centre = {i: (v[0] + v[2] / 2, v[1] + v[3] / 2) for i, v in loc.items()}
    dieclk_info = None
    if dieclk_ports:
        domains_ = T.get('clock_domains', {})
        rows_, trees_ = [], []
        for p_ in dieclk_ports:
            pts = sorted(centre[o] for o in touch[p_] if o in centre)
            xs = sorted(q[0] for q in pts); ys = sorted(q[1] for q in pts)
            rows_.append(f'ckr_{p_} {xs[len(xs) // 2]:.3f} {ys[len(ys) // 2]:.3f}\n')
            trees_.append(dict(name=p_, root=f'ckr_{p_}/Y', period=float(domains_.get(p_, {}).get('period_ps', T_PS)), select='all'))
        (out / 'ckr_place.txt').write_text(''.join(rows_))
        (out / 'dieclk_spec.json').write_text(json.dumps(dict(
            trees=trees_, rc_layer=M8['sta_wire_rc_layer'], safe_tree=True, grid_center=True,
            note='C22 regional die clock trees: one tree per die clock root port, rooted at its entry buffer ckr_<root>; '
                 'no balance_group (regions are balanced inside; region crossings are landed / neighbour-judged)'), indent=1))
        dieclk_info = dict(roots=len(dieclk_ports), iters=a.dieclk_iters, spec='dieclk_spec.json',
                           tool=f'{a.dcc_ref}:tools/die_clock/build.py (safe tree, grid_center, two-corner TT/FF trim)')
    # ------------------------------------------------------------------ placement
    pl = []
    for i, (x, y, w_, h_, st) in sorted(loc.items()):
        pl.append(f'place_inst -name {i} -location {{{x:.3f} {y:.3f}}} -orientation {orientations.get(i, "R0")} -status {st}')
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

    # ------------------------------------------------------------------ ROOT14 GEN safety (tools/die_safety/gen_check.py)
    # region of a block = the die clock net on its clock pin (ck_<region> top port = the region root); a link between
    # two regions is a crossing and needs a landing ring (ld_<link> landing tile, or the crs4 ring inside a frame) whose
    # receiver clock is a region root; every link hop (source pin -> stations -> destination pin) <= the 405-um reach
    gs_facts = gen_safety_facts(insts, ibits, T, mod2master, top, links, LP, loc, kind, blocks, a.reach_um)
    gs = DSG.check_facts(gs_facts, a.reach_um)
    if a.gen_safety_diag:
        gs['diagnostic'] = a.gen_safety_diag
    (out / 'gen_safety_facts.json').write_text(json.dumps(gs_facts) + '\n')
    (out / 'gen_safety.json').write_text(json.dumps(gs, indent=1) + '\n')
    print(DSG.status_line(gs), flush=True)
    if gs['verdict'] != 'PASS':
        if not a.gen_safety_diag:
            raise SystemExit(f"dv_rvcase: GEN SAFETY FAIL ({out / 'gen_safety.json'}): " + ' | '.join(gs['fails'])
                             + ' -- fix the plan (landings / roots / relay sites), or --gen-safety-diag REASON for a labelled diagnostic')
        (out / 'NOT_A_DIE_RESULT').write_text(f'GEN_SAFETY_FAIL_DIAGNOSTIC_ONLY: {a.gen_safety_diag}\n')

    # ------------------------------------------------------------------ S81.CLK geometric clock regions + landed crossings
    ckr, landed = clock_regions_report(insts, ibits, T, mod2master, top, loc, links, LP, plan, bc, a.reach_um)
    (out / 'landed.json').write_text(json.dumps(landed, indent=1) + '\n')
    print('CLOCK_REGIONS', json.dumps({k: ckr[k] for k in ('mode', 'core_roots', 'gate', 'crossings')})[:2000], flush=True)
    if ckr['gate']['verdict'] != 'PASS':
        if not a.clock_region_diag:
            raise SystemExit(f"dv_rvcase: CLOCK REGION GATE FAIL ({len(ckr['gate']['fails'])} roots, e.g. "
                             f"{ckr['gate']['fails'][:5]}): rebind with geometric clock regions (dv_bind S81.CLK), or "
                             '--clock-region-diag REASON for a labelled diagnostic')
        ckr['diagnostic'] = a.clock_region_diag
        with open(out / 'NOT_A_DIE_RESULT', 'a') as fh:
            fh.write(f'CLOCK_REGION_GATE_FAIL_DIAGNOSTIC_ONLY: {a.clock_region_diag}\n')

    # ------------------------------------------------------------------ GRT run
    repair = DC.die_repair_tcl(out, a.dieflow_ref, rc_layer=M8['repeater_rc_layer'], skip=()) if a.die_repair else '# no die repair\n'
    if a.die_repair and T.get('controller_corner_repair'):
        install_controller_corner_repair(out)
    # Relay RTL's complete forwarded payload is i[W-1:0]; rs is a separate
    # synchronous reset tree, not payload. Declare the width as well as the port
    # so a missing/disconnected payload bit fails the structural audit.
    if a.die_repair:
        contracts = []
        payload_contracts = forwarded_payload_contracts(insts, kind, scell)
        for master, width in sorted(payload_contracts.items()):
            contracts.append(f'{{{master}}} {{{{i\\[*\\]}} {width}}}')
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
    if rfw_rows:
        if not a.die_repair:
            raise SystemExit('dv_rvcase: --rfw needs --die-repair (the retimer spread uses the die repeater legaliser)')
        # STW-S81c-DIE-C21: each retimer pair starts at its relay stage's rs pin; the die repeater legaliser spreads them
        # to the nearest free slots (the relay macros and channels are obstacles), then its caches are cleared as for ties.
        (out / 'rfw_place.txt').write_text(''.join(f'{d} {i} {s_}\n' for d, i, s_ in rfw_rows))
        (out / 'rfw_place.tcl').write_text('''# STW-S81c-DIE-C21 co-forwarded relay reset retimer placement (tools/s81_dv/dv_rvcase.py --rfw)
proc ot_rv_place_rfw {listfile report} {
  set blk [ord::get_db_block]; set cells {}; set bad 0
  set fh [open $listfile]
  while {[gets $fh line] >= 0} {
    lassign $line dff inv stage
    set si [$blk findInst $stage]
    if {$si eq "NULL" || $si eq ""} { incr bad; continue }
    set it [$si findITerm rs]
    set b [expr {$it eq "NULL" || $it eq "" ? [$si getBBox] : [$it getBBox]}]
    set x [expr {([$b xMin] + [$b xMax]) / 2}]; set y [expr {([$b yMin] + [$b yMax]) / 2}]
    foreach c [list $dff $inv] {
      set ci [$blk findInst $c]
      if {$ci eq "NULL" || $ci eq ""} { incr bad; continue }
      $ci setLocation $x $y; $ci setPlacementStatus PLACED; lappend cells $ci
    }
  }
  close $fh
  set left [ot_die_rep_spread $cells $report 0.30 8.64 0.60 3]
  foreach v {::ot_die_rep_slw ::ot_die_rep_obs ::ot_die_rep_occ ::ot_die_rep_onobs ::ot_die_rep_maxdisp} { unset -nocomplain $v }
  array unset ::ot_die_rep_ob
  puts "OT_RFW placed=[llength $cells] missing=$bad unplaced=$left"; flush stdout
  return [expr {$bad + $left}]
}
''')
        tie_step += ('source /work/die_repeaters.tcl\nsource /work/rfw_place.tcl\n'
                     'if {[ot_rv_place_rfw /work/rfw_place.txt /work/out/rfw_spread.json] != 0} { puts "OT_RFW_PLACE_FAIL"; exit 4 }\n')
        # the forwarded-clock audit lists the retimer captures on fck[k] but does not judge them as payload hops
        repair = 'set ::ot_die_rep_fclk_aux_capture_masters {DFFHQNx1_ASAP7_75t_R}\n' + repair
    if ties and not a.die_repair:
        raise SystemExit('dv_rvcase: tie cells need --die-repair (the tie spread uses the die repeater legaliser)')
    reserve_tcl = ''
    if reserves:
        reserve_tcl = ('# S81-LINKS gap reserves: hard placement blockage + M1-M6 obstruction (no master, no pins)\n'
                       'set ot_rsv_blk [ord::get_db_block]; set ot_rsv_dbu [$ot_rsv_blk getDbUnitsPerMicron]; set ot_rsv_tech [ord::get_db_tech]\n')
        for b in reserves:
            q = ' '.join(f'[expr {{round({v:.4f} * $ot_rsv_dbu)}}]' for v in (b['x'], b['y'], b['x'] + b['w'], b['y'] + b['h']))
            reserve_tcl += (f'set ot_rsv_b [odb::dbBlockage_create $ot_rsv_blk {q}]; puts "OT_RESERVE {b["name"]} placement_blockage"\n'
                            f'foreach L {{M1 M2 M3 M4 M5 M6}} {{ odb::dbObstruction_create $ot_rsv_blk [$ot_rsv_tech findLayer $L] {q} }}\n')
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
{reserve_tcl}set p0 [clock seconds]
source /work/place.tcl
puts "OT_PLACE_S [expr {{[clock seconds]-$p0}}] insts [llength [get_cells *]]"
{CB.legalize_tcl('place', max_dpl_gsites=2.0)}
{tie_step}write_db /work/out/place.odb
source {PLAT}/setRC.tcl
set_wire_rc -signal -layer {M8['sta_wire_rc_layer']}
# top-port nets (regional clock roots, rst_n, PMA, land_fault): special = not die-top routing (DIE-CLOCK roots ideal here)
set nsp 0
foreach bt [[ord::get_db_block] getBTerms] {{ set n [$bt getNet]; if {{$n ne "NULL"}} {{ $n setSpecial; incr nsp }} }}
puts "OT_SPECIAL_TOP_NETS $nsp"
# S81-DIE8 10-18: the die repeater step runs BEFORE create_clock.  With the region roots declared as clocks, STA
# propagates them through the hop-0 forward cell (BUFx8 / G1 ICGx4) and repair_design silently skips every hop-0
# forwarded-clock net even though repeat_nets un-skips it (case_p4l_rv: all 140 hop-0 fclk nets 0 repeaters,
# 108 > data-1 -> fclk_mismatch FAIL).  Clock / reset distribution stays untouched by the step's own skip list
# (clock-pin + sigtype + glob dont_touch); no step check reads the SDC clock.
{repair}
# Preserve actual repaired placement for pin-to-pin reach inspection before routing.
write_db /work/out/post_repair.odb
{clocks_sdc}
set_routing_layers -signal M2-{a.signal_top_layer} -clock M5-M9
set_global_routing_layer_adjustment M2-M3 0.50
set_global_routing_layer_adjustment M4-M5 0.30
set_global_routing_layer_adjustment M6-{a.signal_top_layer} 0.20
set t0 [clock seconds]
global_route -congestion_iterations {a.congestion_iterations} -allow_congestion -verbose -congestion_report_file /work/out/grt_congestion.rpt
puts "OT_GRT_S [expr {{[clock seconds]-$t0}}]"
write_db /work/out/grt.odb
{post}
puts OT_DONE
'''
    if dieclk_ports:
        # C22: session 1 = place + ties + retimers + entry buffers -> out/place.odb; build.py (die clock trees, measured
        # TT/FF trim) -> out/dieclk/clock.odb; session 2 = repeater step + GRT on the clocked ODB (one session, so the
        # post-GRT repeater audit keeps its in-session state)
        head_, sep_, rest_ = tcl.partition('write_db /work/out/place.odb\n')
        if not sep_:
            raise SystemExit('dv_rvcase: --dieclk: run.tcl has no place.odb split point')
        (out / 'ckr_place.tcl').write_text('''# STW-S81c-DIE-C22 die clock entry buffer placement (tools/s81_dv/dv_rvcase.py --dieclk)
proc ot_rv_place_ckr {listfile report} {
  set blk [ord::get_db_block]; set dbu [$blk getDbUnitsPerMicron]; set cells {}; set bad 0
  set fh [open $listfile]
  while {[gets $fh line] >= 0} {
    lassign $line nm x y
    set ci [$blk findInst $nm]
    if {$ci eq "NULL" || $ci eq ""} { incr bad; continue }
    $ci setLocation [expr {round($x * $dbu)}] [expr {round($y * $dbu)}]; $ci setPlacementStatus PLACED; lappend cells $ci
  }
  close $fh
  set left [ot_die_rep_spread $cells $report 0.30 8.64 0.60 3]
  foreach v {::ot_die_rep_slw ::ot_die_rep_obs ::ot_die_rep_occ ::ot_die_rep_onobs ::ot_die_rep_maxdisp} { unset -nocomplain $v }
  array unset ::ot_die_rep_ob
  puts "OT_CKR placed=[llength $cells] missing=$bad unplaced=$left"; flush stdout
  return [expr {$bad + $left}]
}
''')
        ckr_step = ('source /work/die_repeaters.tcl\nsource /work/ckr_place.tcl\n'
                    'if {[ot_rv_place_ckr /work/ckr_place.txt /work/out/ckr_spread.json] != 0} { puts "OT_CKR_PLACE_FAIL"; exit 4 }\n')
        (out / 'run_place.tcl').write_text(head_ + ckr_step + sep_ + 'puts OT_PLACE_DONE\n')
        std_tt_ = ' '.join(STD_CORNERS['tt'])
        tcl = (f'''# S81-DIE7 REAL-VIEW die case, session 2 (C22 --dieclk): clocked ODB from tools/die_clock/build.py -> repeaters -> GRT
foreach f {{{std_tt_}}} {{ read_liberty {PLAT}/lib/NLDM/asap7sc7p5t_$f }}
foreach f [glob /work/views/*.lib] {{ read_liberty $f }}
read_db /work/out/dieclk/clock.odb
set ot_nck 0
foreach n [[ord::get_db_block] getNets] {{ if {{[string match ckrn_* [$n getName]] || [string match n_dc_* [$n getName]]}} {{ $n setSigType CLOCK; incr ot_nck }} }}
puts "OT_DIECLK_ODB insts [llength [[ord::get_db_block] getInsts]] clock_nets_typed $ot_nck"
''' + rest_)
        (out / 'run_inner.sh').write_text(f'''#!/bin/bash
# C22 die flow inside the container: place session -> die clock build -> repeaters + GRT session
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
P={PLAT}/lib/NLDM; N=${{CPUS:-8}}
/usr/bin/time -v openroad -threads $N -no_init -exit /work/run_place.tcl > /work/out/run_place.log 2>&1
rc=$?; grep -q OT_PLACE_DONE /work/out/run_place.log || {{ echo "OT_PLACE_STEP_FAIL rc=$rc (out/run_place.log)" > /work/out/run.log; exit 4; }}
ls {' '.join('$P/asap7sc7p5t_' + f for f in STD_CORNERS['tt'])} /work/views/*.lib > /work/out/libs_tt.txt
ls {' '.join('$P/asap7sc7p5t_' + f for f in STD_CORNERS['ff'])} /work/views/sta/*_ff.lib /work/views/rv_*.lib > /work/out/libs_ff.txt
/usr/bin/time -v openroad -python -no_init -exit /work/dcc/tools/die_clock/build.py --odb /work/out/place.odb --spec /work/dieclk_spec.json \\
  --libs /work/out/libs_tt.txt --libs-ff /work/out/libs_ff.txt --out /work/out/dieclk --iters ${{DIECLK_ITERS:-{a.dieclk_iters}}} --write-odb > /work/out/dieclk.log 2>&1
rc=$?; grep -q DIE_CLOCK_BUILD_DONE /work/out/dieclk.log || {{ echo "OT_DIECLK_FAIL rc=$rc (out/dieclk.log)" > /work/out/run.log; exit 7; }}
/usr/bin/time -v openroad -threads $N -no_init -exit /work/run.tcl > /work/out/run.log 2>&1
''')
        (out / 'run_inner.sh').chmod(0o755)
        for f_ in ('build.py', 'regtree.py', 'qualification.py'):
            txt = git(a.dcc_ref, f'tools/die_clock/{f_}')
            if txt is None:
                raise SystemExit(f'dv_rvcase: tools/die_clock/{f_} not at {a.dcc_ref}')
            (out / 'dcc/tools/die_clock').mkdir(parents=True, exist_ok=True)
            (out / 'dcc/tools/die_clock' / f_).write_text(txt)
        (out / 'root_clock_report.py').write_text(ROOT_CLOCK_REPORT)
    (out / 'run.tcl').write_text(tcl)
    shutil.copy(ROOT / 'tools/die_cluster/cluster_bounds.tcl', out / 'cluster_bounds.tcl')
    run_cmd = ('bash /work/run_inner.sh; rc=\\$?' if dieclk_ports else
             '/usr/bin/time -v openroad -threads ${CPUS:-8} -no_init -exit /work/run.tcl > /work/out/run.log 2>&1; rc=\\$?')
    (out / 'run.sh').write_text('''#!/bin/bash
D=$(cd $(dirname $0) && pwd); N=dvrv-$$
docker run --rm --name $N --cpus=${CPUS:-8} --memory=${MEMG:-96}g -e CPUS=${CPUS:-8} -v $D:/work -w /work openroad/orfs:asap7lock \\
  bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; ''' + run_cmd + '''; chmod -R a+rwX /work/out; exit \\$rc"
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
set_wire_rc -signal -layer {M8['sta_wire_rc_layer']}
{clocks_sdc}
set_propagated_clock [all_clocks]
set_clock_uncertainty -setup 60 [all_clocks]
set_clock_uncertainty -hold 25 [all_clocks]
set_false_path -from [get_ports rst_n]
source /work/landing.sdc
if {{[catch {{estimate_parasitics -global_routing}} e]}} {{ puts "OT_STA_PARA placement ($e){' NOT_A_DIE_RESULT (M8 die: GRT per-layer RC required)' if M8['m8_signals'] else ''}"; estimate_parasitics -placement }} else {{ puts "OT_STA_PARA global_routing" }}
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
# C22 (--dieclk): propagated arrival at every regional clock tree sink (out/dieclk/sink_pins.txt: tree<TAB>pin)
if {{[file exists /work/out/dieclk/sink_pins.txt]}} {{
  set fi [open /work/out/dieclk/sink_pins.txt]; set fo [open /work/sta/root_arr_{c}.tsv w]
  while {{[gets $fi line] >= 0}} {{
    lassign [split $line "\t"] tr pn
    set q [get_pins -quiet [string map {{[ \\[ ] \\]}} $pn]]
    set mx -; set mn -
    if {{[llength $q] == 1}} {{ catch {{ set mx [get_property $q arrival_max_rise] }}; catch {{ set mn [get_property $q arrival_min_rise] }} }}
    puts $fo "$tr\t$pn\t$mx\t$mn"
  }}
  close $fi; close $fo
}}
puts OT_STA_DONE
''')
    runs = ' && '.join(f'/usr/bin/time -v openroad -threads ${{CPUS:-8}} -no_init -exit /work/sta_{c}.tcl > /work/sta/sta_{c}.log 2>&1' for c in a.corners)
    dccs = '\n'.join(f'python3 $D/dcc/tools/die_clock_check.py report $D/sta/die_clock_dump_{c}.tsv --out $D/sta/die_clock_check_{c}.json '
                     f'--pairs $D/pairs.json --landed $D/landed.json > $D/sta/die_clock_check_{c}.log 2>&1' for c in a.corners)
    (out / 'sta.sh').write_text(f'''#!/bin/bash
# S81-DIE7 real-view die STA {' / '.join(a.corners)} + die_clock_check + classify (needs out/grt.odb)
D=$(cd $(dirname $0) && pwd); N=dvrvsta-$$; mkdir -p $D/sta
[ -f $D/root_clock_report.py ] && python3 $D/root_clock_report.py pins $D
docker run --rm --name $N --cpus=${{CPUS:-8}} --memory=${{MEMG:-64}}g -v $D:/work -w /work openroad/orfs:asap7lock \\
  bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; {runs}; chmod -R a+rwX /work/sta"
rc=$?
{dccs}
python3 $D/classify.py $D {' '.join(a.corners)} > $D/sta/classes.txt 2>&1
[ -f $D/root_clock_report.py ] && python3 $D/root_clock_report.py report $D {' '.join(a.corners)} > $D/sta/root_clock.txt 2>&1
echo $rc > $D/sta/run.exit; exit $rc
''')
    # STW-S81c-DIE-C21 10-22 (--hold-eco): post-GRT die hold ECO session before the die STA.  MAIN4 diag STA: hold on
    # every forwarded hop class (relay_data x_frame/hbm/idx/coll/unit/attn/xtier/ret -64..-181 ps), landing data, die
    # nets into closed views (iqf qs, bk_col vi_s, ctrl k_rdy/kr_data/rq from the PHY on ck_hbm) -- the die flow had no
    # hold repair.  Hold buffers go on die data nets only: special top nets and the repeater step's skip list (clock /
    # sigtype nets) are dont_touch, and closed views are macros (nothing inside them is editable).  Corner: TT, the
    # worse hold corner on this die (relay_data TT -180.7 vs FF -142.6 ps), margin 10 ps; FF hold is then judged by the
    # STA.  New cells are legalised by the die repeater spread.  Fail-soft: on any failure the pre-ECO grt.odb is kept.
    if a.hold_eco:
        std_tt = ' '.join(STD_CORNERS['tt'])
        (out / 'hold_eco.tcl').write_text(f'''# STW-S81c-DIE-C21 post-GRT die hold ECO (tools/s81_dv/dv_rvcase.py --hold-eco)
foreach f {{{std_tt}}} {{ read_liberty {PLAT}/lib/NLDM/asap7sc7p5t_$f }}
foreach f [glob /work/views/sta/*_tt.lib] {{ read_liberty $f }}
foreach f [glob /work/views/rv_*.lib] {{ read_liberty $f }}
read_db /work/out/grt_prehold.odb
source {PLAT}/setRC.tcl
set_wire_rc -signal -layer {M8['sta_wire_rc_layer']}
{clocks_sdc}
set_propagated_clock [all_clocks]
set_clock_uncertainty -setup 60 [all_clocks]
set_clock_uncertainty -hold 25 [all_clocks]
set_false_path -from [get_ports rst_n]
source /work/landing.sdc
if {{[catch {{estimate_parasitics -global_routing}} e]}} {{ puts "OT_HOLD_PARA placement ($e)"; estimate_parasitics -placement }} else {{ puts "OT_HOLD_PARA global_routing" }}
set blk [ord::get_db_block]
set ndt 0
foreach n [$blk getNets] {{ if {{[$n isSpecial]}} {{ $n setDoNotTouch 1; incr ndt }} }}
if {{[file exists /work/die_repeaters.skip_nets.txt]}} {{
  set fh [open /work/die_repeaters.skip_nets.txt]
  foreach nm [split [string trim [read $fh]] "\n"] {{ set n [$blk findNet $nm]; if {{$n ne "NULL" && $n ne ""}} {{ $n setDoNotTouch 1; incr ndt }} }}
  close $fh
}}
set maxid 0; foreach i [$blk getInsts] {{ if {{[$i getId] > $maxid}} {{ set maxid [$i getId] }} }}
puts "OT_HOLD_DONT_TOUCH nets=$ndt pre_max_inst_id=$maxid"
puts "OT_HOLD_PRE"; report_worst_slack -min -digits 1; report_tns -min -digits 1
set t0 [clock seconds]
if {{[catch {{repair_timing -hold -hold_margin 10 -allow_setup_violations -max_buffer_percent 20}} e]}} {{ puts "OT_HOLD_FAIL repair_timing: $e"; exit 5 }}
puts "OT_HOLD_REPAIR_S [expr {{[clock seconds]-$t0}}]"
set new {{}}; foreach i [$blk getInsts] {{ if {{[$i getId] > $maxid}} {{ lappend new $i }} }}
source /work/die_repeaters.tcl
set left [ot_die_rep_spread $new /work/out/hold_spread.json 0.30 8.64 0.60 3]
puts "OT_HOLD_CELLS new=[llength $new] unplaced=$left"
if {{$left != 0}} {{ puts "OT_HOLD_FAIL unplaced hold cells $left"; exit 6 }}
estimate_parasitics -placement
puts "OT_HOLD_POST"; report_worst_slack -min -digits 1; report_tns -min -digits 1
write_db /work/out/grt.odb
puts OT_HOLD_DONE
''')
        (out / 'hold_eco.sh').write_text('''#!/bin/bash
# STW-S81c-DIE-C21 post-GRT die hold ECO: out/grt.odb -> out/grt_prehold.odb, ECO writes a new out/grt.odb; any failure restores it
D=$(cd $(dirname $0) && pwd); N=dvrvhold-$$
[ -f $D/out/grt.odb ] || exit 3
mv $D/out/grt.odb $D/out/grt_prehold.odb || exit 3
timeout ${HOLD_TIMEOUT:-5h} docker run --rm --name $N --cpus=${CPUS:-8} --memory=${MEMG:-96}g -v $D:/work -w /work openroad/orfs:asap7lock \
  bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; /usr/bin/time -v openroad -threads ${CPUS:-8} -no_init -exit /work/hold_eco.tcl > /work/out/hold_eco.log 2>&1; rc=\\$?; chmod -R a+rwX /work/out; exit \\$rc"
rc=$?
if [ $rc -ne 0 ] || ! grep -q OT_HOLD_DONE $D/out/hold_eco.log 2>/dev/null; then
  docker rm -f $N >/dev/null 2>&1; rm -f $D/out/grt.odb; mv $D/out/grt_prehold.odb $D/out/grt.odb; echo "HOLD_ECO_FAILED rc=$rc (pre-ECO grt.odb kept)" > $D/out/hold_eco.exit; exit $rc
fi
echo "HOLD_ECO_OK" > $D/out/hold_eco.exit; exit 0
''')
        (out / 'hold_eco.sh').chmod(0o755)
    # ROOT14 10-20: die IR-drop check with the M8 signal routes present (tools/die_safety/ir_step.sh, copied into the case);
    # FAIL / NOT_RUN = chain exit 1 + OWNER_REPORT line in run_all.log (the coordinator tells the owner)
    shutil.copytree(ROOT / 'tools/die_safety', out / 'die_safety', dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns('__pycache__', 'test_*'))
    ir_block = ('echo "ir: SKIPPED (' + a.no_ir.replace('"', "'") + ') NOT_A_DIE_RESULT" >> $D/run_all.log; echo IR_DROP_SKIPPED >> $D/NOT_A_DIE_RESULT\n'
                if a.no_ir else
                'OT_IR_DESIGN=s81 bash $D/die_safety/ir_step.sh $D/out/grt.odb $D/ir_drop $D/out/run.log > $D/ir_drop.log 2>&1; ir_rc=$?\n'
                'grep -E "^(DIE_IR_DROP|OWNER_REPORT) " $D/ir_drop.log >> $D/run_all.log; echo "ir rc $ir_rc" >> $D/run_all.log\n')
    (out / 'run_all.sh').write_text('''#!/bin/bash
# S81-DIE7 real-view die chain: GRT (+ die repeaters) -> die STA TT/FF -> die_clock_check -> classes / pair judge
set -u; D=$(cd $(dirname $0) && pwd); date > $D/run_all.start
CPUS=${CPUS:-16} MEMG=${MEMG_GRT:-96} bash $D/run.sh; grt_rc=$?; echo "grt rc $grt_rc" >> $D/run_all.log
[ $grt_rc -eq 0 ] || { date > $D/run_all.done; exit $grt_rc; }
[ -f $D/out/grt.odb ] || { echo "NO grt.odb" >> $D/run_all.log; date > $D/run_all.done; exit 3; }
''' + ('''CPUS=${CPUS:-16} MEMG=${MEMG_HOLD:-96} bash $D/hold_eco.sh; hold_rc=$?; echo "hold_eco rc $hold_rc $(cat $D/out/hold_eco.exit 2>/dev/null)" >> $D/run_all.log
''' if a.hold_eco else '') + '''CPUS=${CPUS:-16} MEMG=${MEMG_STA:-64} bash $D/sta.sh; sta_rc=$?; echo "sta rc $sta_rc" >> $D/run_all.log
''' + ir_block + '''date > $D/run_all.done; [ $sta_rc -eq 0 ] || exit $sta_rc; exit ${ir_rc:-0}
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
                unused_forward_clock_outputs=sorted(unused_clock_outputs),
                census=dict(sorted(census.items())),
                closed_views={m: f'{r}:{d}' for m, (r, d) in views.items() if m in {x[0] for x in insts}},
                standin_instances=sum(1 for v in kind.values() if v == 'standin'),
                closed_instances=sum(1 for v in kind.values() if v == 'closed'), std_instances=sum(1 for v in kind.values() if v == 'std'),
                tie_wires=tz[0], tie_cells=len(ties), rfw=dict(enabled=bool(a.rfw), stages_rewired=len(rfw_rows), cells=len(rfw_cells)), hold_eco=bool(a.hold_eco), fwd_moves_over_20um={k: v for k, v in fwd_moves.items() if v[0] > 20}, placement_moves=dict(moved), placement_far=far[:50], landing_windows=dict(collections.Counter(v['model'] for v in lrows.values())),
                land_plan_links_without_model=no_model,
                regional_roots=('PHYSICAL regional trees (C22 --dieclk): top port ck_<root> -> entry buffer ckr_<root> at the sink '
                                'median (ideal from the port to the entry) -> tools/die_clock build.py tree; STA propagated'
                                if dieclk_ports else 'IDEAL top ports ck_<region> (DIE-CLOCK trees not built in this case)'),
                dieclk=dieclk_info, rs_chain_place=rsdp, fck_out_pins=dict(fck_out_pins),
                clock_regions=ckr,
                label=('NOT_A_DIE_RESULT: real-view case; stand-ins = ' + ', '.join(sorted({m.split(':', 1)[1] for m in census if m.startswith('standin:')}))
                       + ' (no closed view yet); closed = ' + ', '.join(sorted({m.split(':', 1)[1] for m in census if m.startswith('closed:')}))),
                memory_note='case_p4l_r (stand-in die netlist) GRT 38.6 GB / 24 min, STA 24 GB / 3.3 min per corner (s81die6, ot-epyc5)',
                chains=chains, landings=lrows,
                gen_safety={k: gs[k] for k in ('verdict', 'reach_um', 'counts', 'max_hop_um', 'fails', 'diagnostic') if k in gs},
                standin_pins=dict(mode=a.standin_pins, bits_by_source=dict(pin_src), kits=kit_rows,
                                  open_masters_without_kit_plan=[m_ for m_ in open_masters if m_ not in kitpin]),
                m8_model=M8, sta_corners=a.corners,
                ir_drop='SKIPPED: ' + a.no_ir if a.no_ir else 'run_all.sh -> ir_drop/ir_drop.json (tools/die_safety/ir_step.sh)')
    (out / 'case.json').write_text(json.dumps(info, indent=1))
    print(json.dumps({k: v for k, v in info.items() if k not in ('chains', 'landings')}, indent=1))


ROOT_CLOCK_REPORT = r'''#!/usr/bin/env python3
# C22 per-root regional die clock report (tools/s81_dv/dv_rvcase.py --dieclk)
#   root_clock_report.py pins CASE              -> out/dieclk/sink_pins.txt (tree<TAB>pin) from the build manifest
#   root_clock_report.py report CASE tt ff ...  -> sta/root_clock.json + summary: per root insertion (late max / early min)
#     and pin-arrival spread (late and early) at every corner from the die STA (GRT parasitics, propagated clocks);
#     owner clock rule: spread <= 80 ps at TT and FF inside a region.  The build's own placement-parasitic trim
#     measurement (manifest iterations) is carried for comparison.
import json, sys, collections
mode, D = sys.argv[1], sys.argv[2]
man = json.load(open(f'{D}/out/dieclk/manifest.json'))
if mode == 'pins':
    open(f'{D}/out/dieclk/sink_pins.txt', 'w').write(''.join(f"{v['tree']}\t{k}\n" for k, v in sorted(man['sinks'].items())))
    sys.exit(0)
res = dict(schema='opentallas.s81_dv.root_clock.v1', rule='per root: pin-arrival spread <= 80 ps at TT and FF (owner clock rule)',
           roots=len(man['trees']), cells=len(man['cells']), build_last_iteration=(man.get('iterations') or [{}])[-1].get('trees'),
           safe_tree_violations=len((man.get('safe_tree') or {}).get('violations', [])), corners={})
for c in sys.argv[3:]:
    per = collections.defaultdict(lambda: dict(n=0, late=[], early=[]))
    try:
        for ln in open(f'{D}/sta/root_arr_{c}.tsv'):
            t, p, mx, mn = ln.rstrip('\n').split('\t')
            r = per[t]; r['n'] += 1
            if mx not in ('-', ''): r['late'].append(float(mx))
            if mn not in ('-', ''): r['early'].append(float(mn))
    except OSError as e:
        res['corners'][c] = f'unavailable ({e})'; continue
    rows = {}
    for t, r in per.items():
        L, E = r['late'], r['early']
        rows[t] = dict(sinks=r['n'], measured=len(L), insertion_max_ps=round(max(L), 1) if L else None,
                       insertion_min_ps=round(min(E), 1) if E else None,
                       spread_late_ps=round(max(L) - min(L), 1) if L else None, spread_early_ps=round(max(E) - min(E), 1) if E else None)
    over = sorted((max(v['spread_late_ps'] or 0, v['spread_early_ps'] or 0), t) for t, v in rows.items())
    res['corners'][c] = dict(roots=len(rows), over_80=sum(1 for s_, _ in over if s_ > 80), worst=over[::-1][:15],
                             insertion_max_ps=max((v['insertion_max_ps'] for v in rows.values() if v['insertion_max_ps'] is not None), default=None),
                             unmeasured_sinks=sum(v['sinks'] - v['measured'] for v in rows.values()), per_root=rows)
json.dump(res, open(f'{D}/sta/root_clock.json', 'w'), indent=1)
for c, v in res['corners'].items():
    if isinstance(v, str):
        print(f'ROOT_CLOCK {c} {v}'); continue
    print(f"ROOT_CLOCK {c} roots={v['roots']} spread>80ps={v['over_80']} max_insertion_ps={v['insertion_max_ps']} unmeasured={v['unmeasured_sinks']} worst={v['worst'][:5]}")
'''


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
