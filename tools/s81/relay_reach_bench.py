#!/usr/bin/env python3
"""Same-phase relay-pair component timing sensitivity bench (S-DIE H-REACH 2026-10-16, coordinator mandatory item 1: every die hop within MEASURED reach).

CLOCK SCOPE: Both instances receive ideal SAME-PHASE boundary clocks. This is
component sensitivity only. Native ot_fwd_link_stage captures negedge fi0 and
inverts fo0, so an actual fo0->fi0 chain has a HALF-cycle timing window. This
vehicle does not time that real chain; it cannot select a die-safe reach.

For every S81 relay / station class bound at die level (masters dsfd_(rly|stnh|stnv|hstnh|hstnv|sstn|rstg|xstg)* in the
closed-view binding table) a driver instance and a receiver instance OF THE SAME CLASS are placed at separation d along the
class's flow direction, real LEF pin faces, ASAP7, and every data bit between them is routed by OpenROAD global route with
the die's layer rules; estimate_parasitics -global_routing gives the RC; OpenSTA times every bit:

    TT setup  at 833.33 ps (stream) and 1111.1 ps (serial)     FF hold                SS 833.33 setup = sensitivity only
    clock: ideal, defined on each instance's clock pin (ck / fi0 / cw); neighbour skew 80 ps applied ADVERSELY as
           set_clock_uncertainty -setup 140 / -hold 105 = base60/25 plus neighbour80; no planning margin.  Same-class pair: the view's own clock insertion cancels (equal on both sides).
    wire:  UNBUFFERED.  The bench never inserts a buffer / repeater (no repair_design, no repair_timing): the routed
           wire between the two relays is the whole hop (owner rule: generator max wire length = reach, no buffering of
           long wires).

Sampled same-phase setup sensitivity lower bound of a class = min over its bits of the largest pin-to-pin Manhattan length L_i at which that bit passed
TT setup (slack >= 0) at that sweep point and every shorter sweep point.  FF hold is judged per point too: a class whose
hold fails at short d gets hold_min_um (the shortest L with every bit passing hold) -- a hop shorter than that fails.
Reported with no margin; planning number = 0.9 x reach.

Batching: many classes per OpenROAD run (shelf-packed pairs, one die), split by a net budget; each batch is one
directory with run.sh (docker openroad/orfs:asap7lock: GRT + parasitics, then one sta session per corner/period).

    relay_reach_bench.py stage   --binding J --census J --git WT [--rev REV] --out STAGE
    relay_reach_bench.py plan    --stage STAGE --out RUN [--layers m45|die] [--d0 25 --d1 1000 --step 25] [--net-budget N]
    relay_reach_bench.py collect --run RUN [--run RUN2 ...] --stage STAGE --out reach_measured.json
    (each RUN/bNN/run.sh is submitted with ot-run; see tools/s81/relay_reach_run.sh)
"""
import argparse
import collections
import hashlib
import json
import math
import re
import subprocess
import sys
from pathlib import Path

CLASS_RE = re.compile(r'^dsfd_(rly|stnh|stnv|hstnh|hstnv|sstn|rstg|xstg)(_|$)')
IMAGE = 'openroad/orfs:asap7lock'
PLAT = '/OpenROAD-flow-scripts/flow/platforms/asap7'
T_STREAM, T_SERIAL = 833.333, 1111.111
SKEW = 80.0
SETUP_UNCERTAINTY = 60.0
HOLD_UNCERTAINTY = 25.0
GRID = 0.192                     # instance origin snap (LCM of the M4/M5 0.048 and M6/M7 0.064 pitches)
# out bus -> in bus of the next instance of the same class
BUS_MAP = {'o': 'i', 'dq': 'di', 'do0': 'di0', 'xa': 'xai', 'xb': 'xbi', 'cc': 'cci', 'so': 'si'}
NORMAL = {'E': (1, 0), 'W': (-1, 0), 'N': (0, 1), 'S': (0, -1)}
LAYERS = {
    # die GRT (physical/s81_die_views/dietop/dietop_grt_sta.sh): signals M4-M9, M4-M5 30 %, M6-M9 14.6 % adjustment
    'die': ('M4-M9', ['set_global_routing_layer_adjustment M4-M5 0.30', 'set_global_routing_layer_adjustment M6-M9 0.146']),
    # die-top relay signals <= M5 (coordinator rule for die-top relays), same 30 % adjustment
    'm45': ('M4-M5', ['set_global_routing_layer_adjustment M4-M5 0.30']),
    # structural sensitivity (2026-10-16): long die relay hops pushed to M8/M9 (M4-M7 capacity cut 85 %: pin access only)
    # repeated die wire on M7 (M4-M6 capacity cut 85 %: pin access only)
    'm7': ('M4-M7', ['set_global_routing_layer_adjustment M4-M6 0.85']),
    'm89': ('M4-M9', ['set_global_routing_layer_adjustment M4-M7 0.85', 'set_global_routing_layer_adjustment M8-M9 0.146']),
}


def sha(b):
    return hashlib.sha256(b).hexdigest()


# ------------------------------------------------------------------------------------------------ view parsing
def lef_pins(text):
    """-> (macro, (w, h), {pin: (layer, cx, cy)}) from the first RECT of each pin"""
    out, size, macro, pin, lay = {}, None, None, None, None
    for line in text.splitlines():
        s = line.split()
        if not s:
            continue
        if s[0] == 'MACRO':
            macro = s[1]
        elif s[0] == 'SIZE':
            size = (float(s[1]), float(s[3]))
        elif s[0] == 'PIN':
            pin = s[1]
            out[pin] = None
        elif s[0] == 'LAYER' and pin:
            lay = s[1]
        elif s[0] == 'RECT' and pin and out.get(pin) is None:
            x0, y0, x1, y1 = map(float, s[1:5])
            out[pin] = (lay, (x0 + x1) / 2, (y0 + y1) / 2)
        elif s[0] == 'END' and len(s) > 1 and s[1] == pin:
            pin = None
    return macro, size, {k: v for k, v in out.items() if v}


def _lib_number(text, key):
    m = re.search(r'\b' + key + r'\s*:\s*([-+0-9.eE]+)', text)
    return finite_float(m.group(1)) if m else None


def electrical_screen(lib_text, measured_slew):
    """Reject a die-safe inference unless actual electrical constraints and receiver evidence exist.

    This ETM-only vehicle has no mapped receiver-D proof or driver pin load measurement.
    Even explicit pin limits cannot make this vehicle a native electrical qualification.
    """
    pins = lib_pins(lib_text)
    transitions = {p: v['max_transition'] for p, v in pins.items() if v['max_transition'] is not None}
    caps = {p: v['max_capacitance'] for p, v in pins.items() if v['max_capacitance'] is not None}
    violations = []
    for pin, slew in measured_slew:
        if pin in transitions and slew is not None and slew > transitions[pin]:
            violations.append(dict(pin=pin, slew_ps=slew, limit_ps=transitions[pin]))
    dependent = bool(re.search(r'variable_[123]\s*:\s*(?:related_pin_transition|constrained_pin_transition|input_net_transition)', lib_text))
    return dict(status='FAIL' if violations else 'UNPROVEN', usable_as_die_reach_bound=False,
                explicit_max_transition_pins=len(transitions), explicit_max_capacitance_pins=len(caps),
                slew_dependent_tables_present=dependent,
                transition_violations=violations,
                max_capacitance_gate='UNPROVEN: driver pin load not measured by this ETM-only vehicle' if caps else 'UNPROVEN: ETM has no explicit max_capacitance',
                reason='Mapped receiver cell/final-D load and slew proof is required; scalar ETM setup cannot qualify electrical reach')


def lib_pins(text):
    """{pin: dict(dir, clock, rel{}, types{})} from a Liberty ETM"""
    pins = {}
    for m in re.finditer(r'pin\("?([^")]+)"?\)\s*\{(.*?)\n    \}', text, re.S):
        body = m.group(2)
        d = re.search(r'direction\s*:\s*(\w+)', body)
        pins[m.group(1)] = dict(dir=d.group(1) if d else '?', clock='clock : true' in body,
                                rel=set(re.findall(r'related_pin\s*:\s*"([^"]+)"', body)),
                                types=set(re.findall(r'timing_type\s*:\s*(\w+)', body)),
                                max_transition=_lib_number(body, 'max_transition'),
                                max_capacitance=_lib_number(body, 'max_capacitance'))
    return pins


def face(size, x, y):
    w, h = size
    d = {'W': x, 'E': w - x, 'S': y, 'N': h - y}
    return min(d, key=d.get)


def bit_index(p):
    m = re.match(r'^(.*)\[(\d+)\]$', p)
    return (m.group(1), int(m.group(2))) if m else (p, None)


def class_model(lef_text, lib_text):
    """the pair model of one class: clock pins, out->in bus pairs (with faces), flow direction.  None + reason when the
    view has no usable pins"""
    macro, size, lp = lef_pins(lef_text)
    pins = lib_pins(lib_text)
    if not size or not lp:
        return None, 'LEF has no SIZE / no pins'
    clocks = sorted(p for p, v in pins.items() if v['clock'] and v['dir'] == 'input')
    if not clocks:
        return None, 'no clock pin in the TT lib'
    buses = collections.defaultdict(dict)
    for p, v in pins.items():
        b, i = bit_index(p)
        if p not in lp:
            continue
        edge = v['types'] & {'rising_edge', 'falling_edge'}
        if v['dir'] == 'output' and edge and (v['rel'] & set(clocks)):
            buses[('out', b)][i] = p
        elif v['dir'] == 'input' and v['types'] & {'setup_rising', 'setup_falling'}:
            buses[('in', b)][i] = p
    pairs, unmatched = [], []
    for (kind, b), bits in sorted(buses.items()):
        if kind != 'out':
            continue
        ib = BUS_MAP.get(b)
        if not ib or ('in', ib) not in buses or len(buses[('in', ib)]) != len(bits):
            unmatched.append(b)
            continue
        fo = collections.Counter(face(size, *lp[p][1:]) for p in bits.values()).most_common(1)[0][0]
        fi = collections.Counter(face(size, *lp[p][1:]) for p in buses[('in', ib)].values()).most_common(1)[0][0]
        pairs.append(dict(out=b, inp=ib, width=len(bits), out_face=fo, in_face=fi,
                          out_pins={str(k): v for k, v in sorted(bits.items(), key=lambda kv: (kv[0] is None, kv[0]))},
                          in_pins={str(k): v for k, v in buses[('in', ib)].items()}))
    if not pairs:
        return None, f'no out->in data bus pair (outputs {unmatched})'
    main = max(pairs, key=lambda p: p['width'])
    for p in pairs:      # forward = launched by the driver toward the receiver; reverse = receiver -> driver
        p['dir'] = 'fwd' if p['out_face'] == main['out_face'] else (
            'rev' if NORMAL[p['out_face']] == tuple(-c for c in NORMAL[main['out_face']]) else 'skip')
    return dict(macro=macro, size=size, clocks=clocks, pairs=pairs, unmatched_out=unmatched,
                flow=main['out_face'] + '>' + main['in_face'], pin_xy={p: v[1:] for p, v in lp.items()},
                pin_layer={p: v[0] for p, v in lp.items()}), None


# ------------------------------------------------------------------------------------------------ 1-bit buses
def one_bit_buses(lib_text):
    return set(re.findall(r'type \("?(\w+)"?\) \{\s*base_type : array;\s*data_type : bit;\s*bit_width : 1;', lib_text))


def scalarize_lib(text, names):
    """bench adapter: a 1-bit Liberty bus X (pin X[0]) becomes the scalar pin X.  OpenROAD's Verilog reader segfaults
    (orfs:asap7lock, VerilogReader::makeModuleInst) on any connection to a 1-bit bus port of an ETM (dsfd_hstnh_1,
    measured 2026-10-16), and drops an escaped bit-port connection silently; the arcs / values are unchanged."""
    lines = text.split('\n')
    out, i = [], 0
    while i < len(lines):
        m = re.match(r'^(\s*)bus\("?(\w+)"?\) \{\s*$', lines[i])
        if m and m.group(2) in names:
            ind, x = m.group(1), m.group(2)
            j = i + 1
            while not re.match(r'^\s*pin\("?' + re.escape(x) + r'\[0\]"?\) \{', lines[j]):
                j += 1
            k = j + 1
            pind = re.match(r'^(\s*)', lines[j]).group(1)
            while lines[k] != pind + '}':
                k += 1
            out.append(lines[j].replace(f'{x}[0]', x))
            out.extend(lines[j + 1:k + 1])
            e = k + 1
            while lines[e] != ind + '}':
                e += 1
            i = e + 1
            continue
        out.append(lines[i])
        i += 1
    t = '\n'.join(out)
    for x in names:
        t = t.replace(f'"{x}[0]"', f'"{x}"')
    return t


def scalarize_lef(text, names):
    for x in names:
        t = re.sub(r'(\b(?:PIN|END)\s+)' + re.escape(x) + r'\[0\](\s)', r'\g<1>' + x + r'\g<2>', text)
        text = t
    return text


def scalar_pin(pin, names):
    b, i = bit_index(pin)
    return b if (i == 0 and b in names) else pin


# ------------------------------------------------------------------------------------------------ stage
def classes_from_binding(binding):
    b = json.loads(Path(binding).read_text())['bound']
    return {k: v for k, v in sorted(b.items()) if CLASS_RE.match(k)}


def census_counts(census):
    out = collections.Counter()
    if not census:
        return out
    for rows in json.loads(Path(census).read_text()).values():
        if isinstance(rows, list):
            for n, m in rows:
                out[m] += n
    return out


def cmd_stage(a):
    out = Path(a.out)
    (out / 'views').mkdir(parents=True, exist_ok=True)
    cls = classes_from_binding(a.binding)
    cnt = census_counts(a.census)
    rec = dict(schema='opentallas.s81.relay_reach_stage.v1', binding=a.binding, binding_rev=a.rev, census=a.census,
               classes={})
    for m, row in cls.items():
        r = dict(verdict=row.get('verdict'), job=row.get('job'), instances_c26l=cnt.get(m, 0), files={}, problems=[])
        for c, f in row.get('files', {}).items():
            if c not in ('lef', 'tt', 'ff', 'ss'):
                continue
            try:
                if a.git:
                    data = subprocess.run(['git', '-C', a.git, 'show', f'{a.rev}:{f["path"]}'], capture_output=True,
                                          check=True).stdout
                else:
                    data = (Path(a.root) / f['path']).read_bytes()
            except Exception as e:  # noqa: BLE001
                r['problems'].append(f'{c} missing: {f["path"]} ({type(e).__name__})')
                continue
            if sha(data) != f['sha256']:
                r['problems'].append(f'{c} sha256 mismatch {f["path"]}')
                continue
            dst = out / 'views' / m / f'{m}_{c}.{"lef" if c == "lef" else "lib"}'
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(data)
            r['files'][c] = dict(path=f['path'], sha256=f['sha256'])
        if not r['problems'] and {'lef', 'tt', 'ff'} <= set(r['files']):
            mod, why = class_model((out / 'views' / m / f'{m}_lef.lef').read_text(),
                                   (out / 'views' / m / f'{m}_tt.lib').read_text())
            if mod is None:
                r['problems'].append(why)
            else:
                (out / 'views' / m / 'model.json').write_text(json.dumps(mod))
                r['flow'] = mod['flow']
                r['buses'] = [f"{p['out']}->{p['inp']}x{p['width']} {p['out_face']}>{p['in_face']} {p['dir']}"
                              for p in mod['pairs']]
                r['unmatched_out'] = mod['unmatched_out']
        elif not r['problems']:
            r['problems'].append('LEF / TT / FF view incomplete')
        rec['classes'][m] = r
    (out / 'stage.json').write_text(json.dumps(rec, indent=1))
    bad = {m: r['problems'] for m, r in rec['classes'].items() if r['problems']}
    print(f'staged {len(cls)} classes, {len(cls) - len(bad)} usable; not measurable: {bad}')


# ------------------------------------------------------------------------------------------------ plan
def snap(v):
    return round(round(v / GRID) * GRID, 3)


def pair_geometry(mod, d):
    """driver at the origin (R0); receiver R0 with its main-input-bus centroid at the driver's main-output-bus centroid
    + d along the output face normal.  -> (rx, ry, bbox) or None when the bodies overlap"""
    w, h = mod['size']
    main = max(mod['pairs'], key=lambda p: p['width'])
    xy = mod['pin_xy']
    co = [sum(xy[p][i] for p in main['out_pins'].values()) / main['width'] for i in (0, 1)]
    ci = [sum(xy[p][i] for p in main['in_pins'].values()) / main['width'] for i in (0, 1)]
    n = NORMAL[main['out_face']]
    rx, ry = snap(co[0] + d * n[0] - ci[0]), snap(co[1] + d * n[1] - ci[1])
    if rx < w - 1e-6 and rx + w > 1e-6 and ry < h - 1e-6 and ry + h > 1e-6:
        return None
    return rx, ry, (min(0, rx), min(0, ry), max(w, rx + w), max(h, ry + h))


def cmd_plan(a):
    stage = Path(a.stage)
    srec = json.loads((stage / 'stage.json').read_text())
    run = Path(a.out)
    run.mkdir(parents=True, exist_ok=True)
    ds = [round(a.d0 + i * a.step, 3) for i in range(int(round((a.d1 - a.d0) / a.step)) + 1)]
    sel = [m for m, r in srec['classes'].items() if not r['problems'] and (not a.classes or m in a.classes)]
    items = []          # (class, d, nets, geometry)
    for m in sel:
        mod = json.loads((stage / 'views' / m / 'model.json').read_text())
        bits = sum(p['width'] for p in mod['pairs'] if p['dir'] != 'skip')
        for d in ds:
            g = pair_geometry(mod, d)
            items.append((m, d, bits, g, mod))
    # batches: whole classes, bounded by net count AND by die area (GRT memory follows the die area:
    # measured 2026-10-16, 20-128 GB peak RSS at 5.6-36 mm2, ~3.5 GB/mm2 -- declared 8-16 GB was wrong and made
    # earlyoom kill closure routes on AGIdock; see mem_gb_for_area)
    def cls_area(its):
        a_ = 0.0
        for m, d, bits, g, mod in its:
            if g is None:
                continue
            x0, y0, x1, y1 = g[2]
            mg = 30.0 + 0.05 * max(x1 - x0, y1 - y0)
            a_ += (x1 - x0 + 2 * mg) * (y1 - y0 + 2 * mg)
        return a_ * 1.7 / 1e6          # shelf-packing overhead (measured die / box area ~1.5-1.8)
    batches, cur, curn, cura = [], [], 0, 0.0
    by_cls = collections.OrderedDict()
    for it in items:
        by_cls.setdefault(it[0], []).append(it)
    for m, its in by_cls.items():
        n = sum(i[2] for i in its)
        ar = cls_area(its)
        if cur and (curn + n > a.net_budget or cura + ar > a.max_area_mm2):
            batches.append(cur)
            cur, curn, cura = [], 0, 0.0
        cur += its
        curn += n
        cura += ar
    if cur:
        batches.append(cur)
    lay, adj = LAYERS[a.layers]
    index = []
    for bi, its in enumerate(batches):
        bd = run / f'b{bi:02d}'
        bd.mkdir(parents=True, exist_ok=True)
        index.append(write_batch(bd, its, stage, lay, adj, a))
    (run / 'plan.json').write_text(json.dumps(dict(
        schema='opentallas.s81.relay_reach_plan.v1', clock_scenario='ideal_common_phase_component_sensitivity', real_forwarded_chain_timed=False, layers=a.layers, signal_layers=lay, adjustments=adj, sweep_um=ds,
        skew_ps=SKEW, base_setup_uncertainty_ps=SETUP_UNCERTAINTY, base_hold_uncertainty_ps=HOLD_UNCERTAINTY, periods_ps=dict(stream=T_STREAM, serial=T_SERIAL), image=IMAGE, stage=str(stage),
        batches=index), indent=1))
    print(f'{len(batches)} batches, {len(sel)} classes, {len(ds)} sweep points: ' +
          ', '.join(f"{b['dir']} {b['classes']} cls {b['nets']} nets" for b in index))


NLDM = PLAT + '/lib/NLDM'
STD_LIBS = ('asap7sc7p5t_AO_RVT_{C}_nldm_211120.lib.gz', 'asap7sc7p5t_INVBUF_RVT_{C}_nldm_220122.lib.gz',
            'asap7sc7p5t_OA_RVT_{C}_nldm_211120.lib.gz', 'asap7sc7p5t_SEQ_RVT_{C}_nldm_220123.lib',
            'asap7sc7p5t_SIMPLE_RVT_{C}_nldm_211120.lib.gz')
REPEATERS = ('BUFx4_ASAP7_75t_R', 'BUFx4f_ASAP7_75t_R', 'BUFx5_ASAP7_75t_R', 'BUFx6f_ASAP7_75t_R', 'BUFx8_ASAP7_75t_R')
MAX_TRANSITION = 260.0


def std_libs(corner):
    return '\n'.join(f'read_liberty {NLDM}/{f.format(C=corner.upper())}' for f in STD_LIBS)


def repeater_tcl(layer):
    """--repeaters: OpenROAD repair_design on every die wire (slew / cap driven at the closed views' 260 ps
    max_transition, BUFx4..BUFx8 only), placement RC of LAYER, then legalise the repeaters"""
    return f'''set_wire_rc -signal -layer {layer}
set_max_transition {MAX_TRANSITION} [current_design]
set_dont_use [get_lib_cells -quiet *_ASAP7_75t_R]
unset_dont_use [get_lib_cells {{{' '.join(REPEATERS)}}}]
estimate_parasitics -placement
repair_design -slew_margin 0 -cap_margin 0
puts "OT_REPAIR repeaters [llength [get_cells -quiet -filter {{ref_name =~ BUFx*}} *]]"
detailed_placement
check_placement -verbose
mem repair'''


def mem_gb_for_area(mm2):
    """honest ot-heavy declaration and docker --memory cap for one GRT batch: measured peak RSS 20-128 GB over
    5.6-36.2 mm2 dies (fwd_die b01-b07, fwd_die2, fwd_die3 2026-10-16) = 3.3-3.6 GB/mm2; 4 GB/mm2 + 8 GB"""
    return int(math.ceil(4.0 * mm2 + 8))


def write_batch(bd, its, stage, lay, adj, a):
    gap = 30.0
    boxes = []
    for m, d, bits, g, mod in its:
        if g is None:
            continue
        x0, y0, x1, y1 = g[2]
        mg = gap + 0.05 * max(x1 - x0, y1 - y0)
        boxes.append((m, d, g, mod, x1 - x0 + 2 * mg, y1 - y0 + 2 * mg, mg))
    total = sum(b[4] * b[5] for b in boxes)
    rowmax = max(max(b[4] for b in boxes), math.sqrt(total) * 1.3)
    x = y = rowh = 0.0
    W = 0.0
    placed = []
    for b in sorted(boxes, key=lambda b: -b[5]):
        if x + b[4] > rowmax:
            x, y, rowh = 0.0, y + rowh, 0.0
        placed.append((b, x, y))
        x += b[4]
        rowh = max(rowh, b[5])
        W = max(W, x)
    H = y + rowh
    insts, nets, sinks, place, masters = [], [], {}, [], set()
    scal = {}
    for m_ in {b[0] for b in boxes}:
        vd_ = stage / 'views' / m_
        names = one_bit_buses((vd_ / f'{m_}_tt.lib').read_text())
        scal[m_] = names
        if names:
            (vd_ / f'{m_}_lef_s.lef').write_text(scalarize_lef((vd_ / f'{m_}_lef.lef').read_text(), names))
            for c_ in ('tt', 'ff', 'ss'):
                if (vd_ / f'{m_}_{c_}.lib').exists():
                    (vd_ / f'{m_}_{c_}_s.lib').write_text(scalarize_lib((vd_ / f'{m_}_{c_}.lib').read_text(), names))
    clock_paths = []
    fclk = {}
    v = ['module reach_top ();']
    for k, (b, ox, oy) in enumerate(placed):
        m, d, g, mod, bw, bh, mg = b
        masters.add(m)
        rx, ry, (bx0, by0, _, _) = g
        ax, ay = snap(ox + mg - bx0), snap(oy + mg - by0)
        A, B = f'P{k}_A', f'P{k}_B'
        pos = {A: (ax, ay), B: (snap(ax + rx), snap(ay + ry))}
        place += [f'place_inst -name {A} -location {{{pos[A][0]:.3f} {pos[A][1]:.3f}}} -orientation R0 -status FIRM',
                  f'place_inst -name {B} -location {{{pos[B][0]:.3f} {pos[B][1]:.3f}}} -orientation R0 -status FIRM']
        conn = {A: [], B: []}
        for p in mod['pairs']:
            if p['dir'] == 'skip':
                continue
            src, dst = (A, B) if p['dir'] == 'fwd' else (B, A)
            wn = f'n{k}_{p["out"]}'
            if p['width'] == 1:     # scalar pin, or a 1-bit bus scalarized by the bench adapter
                # 1-bit Liberty bus: connect the scalarized pin (bench adapter, see scalarize_lib)
                v.append(f'  wire {wn};')
                conn[src].append(f'.{p["out"]}({wn})')
                conn[dst].append(f'.{p["inp"]}({wn})')
            else:
                v.append(f'  wire [{p["width"] - 1}:0] {wn};')
                conn[src].append(f'.{p["out"]}({wn})')
                conn[dst].append(f'.{p["inp"]}({wn})')
            for bit, op in p['out_pins'].items():
                ip = p['in_pins'][bit]
                sx = pos[src][0] + mod['pin_xy'][op][0]
                sy = pos[src][1] + mod['pin_xy'][op][1]
                tx = pos[dst][0] + mod['pin_xy'][ip][0]
                ty = pos[dst][1] + mod['pin_xy'][ip][1]
                sinks[f'{dst}/{scalar_pin(ip, scal[m])}'] = dict(cls=m, d=d, bus=f'{p["out"]}->{p["inp"]}', dir=p['dir'],
                                            drv=f'{src}/{op}', L=round(abs(sx - tx) + abs(sy - ty), 3),
                                            faces=f'{p["out_face"]}>{p["in_face"]}')
        if getattr(a, 'fwd_clock', False) and 'fo0[0]' in mod['pin_xy'] and 'fi0[0]' in mod['pin_xy']:
            # --fwd-clock: route the die's forwarded clock A.fo0 -> B.fi0 (chain_nets fclk) for the native composed pair
            # bench (relay_native_pair.py); the ETM STA here still defines its clock on each fi0 pin
            v.append(f'  wire n{k}_fck;' if 'fo0' in scal[m] else f'  wire [0:0] n{k}_fck;')
            conn[A].append(f'.fo0(n{k}_fck)')
            conn[B].append(f'.fi0(n{k}_fck)')
            fx = [pos[A][i] + mod['pin_xy']['fo0[0]'][i] - pos[B][i] - mod['pin_xy']['fi0[0]'][i] for i in (0, 1)]
            fclk[f'n{k}_fck'] = dict(cls=m, d=d, drv=f'{A}/fo0[0]', sink=f'{B}/fi0[0]', L=round(abs(fx[0]) + abs(fx[1]), 3))
        for I in (A, B):
            clock_paths.extend(f'{I}/{scalar_pin(c, scal[m])}' for c in mod['clocks'])
            v.append(f'  {m} {I} ({", ".join(conn[I])});')
        insts.append(dict(k=k, cls=m, d=d, A=pos[A], B=pos[B]))
    v.append('endmodule')
    (bd / 'reach.v').write_text('\n'.join(v) + '\n')
    (bd / 'map.json').write_text(json.dumps(dict(sinks=sinks, insts=insts, die_um=[W, H], fclk=fclk)))
    vdir = '/stage/views'
    sx = lambda m: '_s' if scal.get(m) else ''  # noqa: E731
    lefs = '\n'.join(f'read_lef {vdir}/{m}/{m}_lef{sx(m)}.lef' for m in sorted(masters))
    libs = lambda c: '\n'.join(f'read_liberty {vdir}/{m}/{m}_{c}{sx(m)}.lib' for m in sorted(masters))  # noqa: E731
    clk_queries = ' '.join('[get_pins -regexp {' + re.escape(c) + '}]' for c in clock_paths)
    tcl = f"""# relay_reach_bench batch {bd.name}: {len(placed)} pairs, {len(sinks)} sink bits, die {W:.1f} x {H:.1f} um
proc mem {{tag}} {{ set f [open /proc/self/status]; set s [read $f]; close $f
  regexp {{VmHWM:\\s+(\\d+)}} $s -> h; puts "OTMEM $tag hwm_mb=[expr {{$h/1024}}] t=[clock seconds]"; flush stdout }}
read_lef {PLAT}/lef/asap7_tech_1x_201209.lef
read_lef {PLAT}/lef/asap7sc7p5t_28_R_1x_220121a.lef
{lefs}
{std_libs('tt') if getattr(a, 'repeaters', None) else ''}
{libs('tt')}
read_verilog /work/reach.v
link_design reach_top
initialize_floorplan -die_area {{0 0 {snap(W + 20):.3f} {snap(H + 20):.3f}}} -core_area {{0 0 {snap(W + 20):.3f} {snap(H + 20):.3f}}} -site asap7sc7p5t
source {PLAT}/openRoad/make_tracks.tcl
{chr(10).join(place)}
mem placed
source {PLAT}/setRC.tcl
{repeater_tcl(a.repeaters) if getattr(a, 'repeaters', None) else ''}
set_routing_layers -signal {lay}
{chr(10).join(adj)}
global_route -congestion_iterations 30 -allow_congestion -verbose -congestion_report_file /work/grt_congestion.rpt
mem grt
report_wire_length -net * -global_route -detailed_route -file /work/wirelength.csv
estimate_parasitics -global_routing -spef_file /work/reach.spef
write_verilog /work/reach_grt.v
mem done
puts OT_REACH_GRT_DONE
"""
    (bd / 'grt.tcl').write_text(tcl)
    sink_list = sorted(sinks)
    (bd / 'sinks.txt').write_text('\n'.join(sink_list) + '\n')
    for name, corner, per, chk in (('tt833', 'tt', T_STREAM, 'max'), ('tt1111', 'tt', T_SERIAL, 'max'),
                                   ('ff_hold', 'ff', T_STREAM, 'min'), ('ss833', 'ss', T_STREAM, 'max')):
        sta = f"""# {name}: {corner} {'setup' if chk == 'max' else 'hold'} at {per} ps, neighbour skew {SKEW} ps adverse
{std_libs(corner) if getattr(a, 'repeaters', None) else ''}
{libs(corner)}
read_verilog /work/reach_grt.v
link_design reach_top
read_spef /work/reach_sta.spef
set cp [concat {clk_queries}]
if {{[llength $cp] != {len(clock_paths)}}} {{ error "clock pin coverage mismatch" }}
create_clock -name clk -period {per} $cp
set_clock_uncertainty -setup {SKEW + SETUP_UNCERTAINTY} [all_clocks]
set_clock_uncertainty -hold {SKEW + HOLD_UNCERTAINTY} [all_clocks]
set f [open /work/{name}.slk w]
set fp [open /work/sinks.txt r]
set n 0
while {{[gets $fp pn] >= 0}} {{
  if {{$pn eq ""}} continue
  set p [get_pins $pn]
  puts $f "$pn [get_property $p slack_{chk}] [get_property $p slew_max]"
  incr n
}}
close $fp; close $f
report_checks -path_delay {chk} -group_path_count 3 -fields {{slew cap}} -digits 2
puts "OT_REACH_STA_DONE {name} $n"
"""
        (bd / f'sta_{name}.tcl').write_text(sta)
    mem = mem_gb_for_area(W * H / 1e6)
    (bd / 'run.sh').write_text(f"""#!/bin/bash
# relay_reach_bench batch: GRT + parasitics (openroad), then 4 sta sessions; inputs /stage (views) + /work (this dir)
# DECLARE {max(mem, 24)} GB to ot-heavy (ot-run --mem): GRT docker --memory={mem}g (die {W * H / 1e6:.2f} mm2, 4 GB/mm2 + 8),
# then 4 x sta at --memory=6g each; peak RSS is logged (/usr/bin/time -v)
set -u
B=$(cd "$(dirname "$0")" && pwd); S=${{1:?stage dir}}; T=${{2:-8}}
cd $B
docker run --rm --name reach_$(basename $(dirname $B))_$(basename $B) --cpus=$T --memory={mem}g -v $B:/work -v $S:/stage:ro -w /work {IMAGE} \\
  bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; /usr/bin/time -v openroad -threads $T -no_init -exit /work/grt.tcl > /work/grt.log 2>&1; rc=\\$?; chmod -R a+rwX /work; exit \\$rc"
echo $? > grt.exit
grep -q OT_REACH_GRT_DONE grt.log || {{ echo GRT_FAIL; exit 1; }}
# This bench has no top ports. OpenROAD emits an empty *PORTS section;
# OpenSTA rejects it. Remove only that empty header; all extracted RC stays byte-identical.
sed '/^[*]PORTS$/d' reach.spef > reach_sta.spef
for c in tt833 tt1111 ff_hold ss833; do
  docker run --rm --name reach_$(basename $(dirname $B))_$(basename $B)_$c --cpus=2 --memory=6g -v $B:/work -v $S:/stage:ro -w /work {IMAGE} \\
    bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; /usr/bin/time -v sta -no_init -exit /work/sta_$c.tcl > /work/sta_$c.log 2>&1; chmod -R a+rwX /work" &
done
wait
for c in tt833 tt1111 ff_hold ss833; do grep -q OT_REACH_STA_DONE sta_$c.log || {{ echo STA_FAIL $c; exit 1; }}; done
rm -f reach.spef.gz; gzip -f reach.spef
echo BATCH_DONE
""")
    (bd / 'run.sh').chmod(0o755)
    return dict(dir=bd.name, mem_gb=max(mem, 24), classes=len({p[0][0] for p in placed}), pairs=len(placed), nets=len(sinks),
                die_um=[round(W, 1), round(H, 1)], skipped_overlap=[(m, d) for m, d, _, g, _ in its if g is None])


# ------------------------------------------------------------------------------------------------ collect
def finite_float(value):
    x = float(value)
    if not math.isfinite(x):
        raise ValueError('unconstrained/non-finite timing value')
    return x


def read_slk(p):
    out = {}
    if not p.exists():
        return out
    for line in p.read_text().splitlines():
        s = line.split()
        if len(s) >= 2:
            try:
                out[s[0]] = (finite_float(s[1]), finite_float(s[2]) if len(s) > 2 else None)
            except ValueError:
                out[s[0]] = (None, None)
    return out


def class_reach(rows, key):
    """rows: [(d, L, slack, sinkpin)] for one class; per bit (pin name of the receiver input, same at every d) the
    largest L at which the bit passed at this and every shorter sweep point -> (reach, worst bit, slack at reach, d_pass,
    first_fail_d)"""
    by_bit = collections.defaultdict(list)
    for d, L, s, pin, bus in rows:
        by_bit[(bus, pin.split('/', 1)[1])].append((d, L, s))
    best = None
    for bit, pts in by_bit.items():
        pts.sort()
        r, rs = 0.0, None
        for d, L, s in pts:
            if s is None or s < 0:
                break
            r, rs = L, s
        if best is None or r < best[0]:
            best = (r, bit, rs)
    by_d = collections.defaultdict(list)
    for d, L, s, pin, bus in rows:
        by_d[d].append(s)
    d_pass, first_fail = 0.0, None
    for d in sorted(by_d):
        if all(s is not None and s >= 0 for s in by_d[d]):
            if first_fail is None:
                d_pass = d
        elif first_fail is None:
            first_fail = d
    return dict(reach_um=round(best[0], 1), worst_bit=f'{best[1][0]} {best[1][1]}',
                slack_at_reach_ps=None if best[2] is None else round(best[2], 2), d_pass_um=d_pass,
                first_fail_d_um=first_fail,
                worst_slack_by_d={str(d): round(min(s for s in by_d[d] if s is not None), 2)
                                  if any(s is not None for s in by_d[d]) else None for d in sorted(by_d)})


def hold_min(rows):
    """shortest sweep d from which every bit passes FF hold at that and every longer point; the worst-bit L there"""
    by_d = collections.defaultdict(list)
    for d, L, s, pin, bus in rows:
        by_d[d].append((s, L))
    ds = sorted(by_d)
    ok = [all(s is not None and s >= 0 for s, _ in by_d[d]) for d in ds]
    if all(ok):
        return dict(hold_ok_all=True, tested_min_d_um=ds[0], hold_min_um=round(max(L for _, L in by_d[ds[0]]), 1), worst_hold_ps=round(min(s for d in ds for s, _ in by_d[d]), 2))
    lo = None
    for i in range(len(ds) - 1, -1, -1):
        if not ok[i]:
            break
        lo = ds[i]
    return dict(hold_ok_all=False, hold_min_d_um=lo,
                hold_min_um=None if lo is None else round(max(L for _, L in by_d[lo]), 1),
                worst_hold_ps=round(min(s for d in ds for s, _ in by_d[d] if s is not None), 2),
                hold_fail_d_um=[d for d, o in zip(ds, ok) if not o])


def cmd_collect(a):
    stage = Path(a.stage)
    srec = json.loads((stage / 'stage.json').read_text())
    res = {}
    runs = {}
    for rd in a.run:
        rd = Path(rd)
        plan = json.loads((rd / 'plan.json').read_text())
        runs[plan['layers']] = dict(dir=str(rd), signal_layers=plan['signal_layers'], adjustments=plan['adjustments'],
                                    sweep_um=plan['sweep_um'], batches=[])
        if plan.get('base_setup_uncertainty_ps') != SETUP_UNCERTAINTY or plan.get('base_hold_uncertainty_ps') != HOLD_UNCERTAINTY or plan.get('skew_ps') != SKEW:
            raise ValueError('plan uncertainty metadata missing or inconsistent; cannot mix timing scenarios')
        for b in plan['batches']:
            bd = rd / b['dir']
            corners = ('tt833', 'tt1111', 'ff_hold', 'ss833')
            ok = all((bd / f'{c}.slk').exists() and
                     (bd / f'sta_{c}.log').exists() and
                     f'OT_REACH_STA_DONE {c} ' in (bd / f'sta_{c}.log').read_text(errors='ignore')
                     for c in corners)
            ok = ok and (bd / 'grt.log').exists() and 'OT_REACH_GRT_DONE' in (bd / 'grt.log').read_text(errors='ignore')
            runs[plan['layers']]['batches'].append(dict(dir=str(bd), complete=bool(ok), job=_job(bd)))
            if not ok:
                continue
            mp = json.loads((bd / 'map.json').read_text())['sinks']
            slk = {c: read_slk(bd / f'{c}.slk') for c in ('tt833', 'tt1111', 'ff_hold', 'ss833')}
            ovf = _overflow(bd / 'grt.log')
            if any(set(v) != set(mp) or any(s is None for s, _ in v.values()) for v in slk.values()):
                runs[plan['layers']]['batches'][-1].update(complete=False, reason='incomplete/non-finite STA coverage')
                continue
            rows = collections.defaultdict(lambda: collections.defaultdict(list))
            slews = collections.defaultdict(list)
            for pin, s in mp.items():
                for c in slk:
                    v = slk[c].get(pin, (None, None))
                    rows[s['cls']][c].append((s['d'], s['L'], v[0], pin, s['bus']))
                    if c == 'tt833':
                        slews[s['cls']].append((s['d'], s['L'], v[1], pin.split('/', 1)[1]))
            for m, cr in rows.items():
                r = res.setdefault(m, {}).setdefault(plan['layers'], {})
                r['stream'] = class_reach(cr['tt833'], 'tt833')
                r['serial'] = class_reach(cr['tt1111'], 'tt1111')
                r['ss_sensitivity_833'] = {k: v for k, v in class_reach(cr['ss833'], 'ss833').items()
                                           if k in ('reach_um', 'd_pass_um')}
                r['hold_ff'] = hold_min(cr['ff_hold'])
                rr = r['stream']['reach_um']
                sl = [x for d, L, x, pin in slews[m] if x is not None and d <= r['stream']['d_pass_um']]
                r['max_sink_slew_tt_ps_within_reach'] = round(max(sl), 1) if sl else None
                r['electrical_validity'] = electrical_screen((stage / 'views' / m / f'{m}_tt.lib').read_text(),
                    [(pin, x) for d, L, x, pin in slews[m] if d <= r['stream']['d_pass_um']])
                r['batch'] = str(bd)
                r['grt_overflow'] = ovf
    out = dict(schema='opentallas.s81.relay_reach_measured.v1', date=a.date, collector_sha256=sha(Path(__file__).read_bytes()),
               clock_scenario='ideal_common_phase_component_sensitivity',
               actual_forwarded_half_cycle_chain_status='OPEN: not timed by this bench',
               qualification='SENSITIVITY_ONLY; no die reach selection',
               method=('MEASURED COMPONENT SENSITIVITY ONLY (not forwarded-chain reach): same-class driver->receiver pair at separation d along the flow '
                       'direction, real LEF pin faces, R0, ASAP7; every data bit routed by OpenROAD global_route '
                       '(die layer rules) and extracted by estimate_parasitics -global_routing (setRC.tcl); OpenSTA per '
                       'bit: TT setup 833.33 ps (stream) / 1111.1 ps (serial), FF hold, SS 833 setup sensitivity; ideal '
                       'clock on each instance clock pin with 80 ps neighbour skew applied adversely (uncertainty -setup '
                       '140 / -hold 105 = base60/25 plus neighbour80), no planning margin.  UNBUFFERED: no repair_design / repair_timing / repeaters; '
                       'the wire between the relays is the whole hop.  reach_um = min over bits of the largest '
                       'pin-to-pin Manhattan L at which the bit passed TT setup at that and every shorter sweep point.'),
               caveats=['Both fi0 pins use ideal same-phase clocks; actual inverted fo0->fi0 opposite-half-cycle chain remains OPEN',
                        'GRT + estimate_parasitics RC, not detail-route + RCX (no DRT calibration in this record unless '
                        'listed under calibration)',
                        'Reach measurements are component screens; overflow and unmeasured real clock distribution cannot qualify a die',
                        'driver ETM output tables are characterised to 92.16 fF; longer wires extrapolate the table',
                        'ETM setup / hold are scalar (input slew independent): a slow edge at the receiver is not '
                        'penalised by the view; sink slew is reported (max_sink_slew_tt_ps_within_reach) for the DRV '
                        'reader',
                        'same-class pair: common clock insertion reference cancels; mixed-class hops need direct timing '
                        'and are not proven by min(self-pair reach of endpoints)',
                        'Forwarded-clock stations are same-phase sensitivities only: the ETM fo0 arc is self-related and cannot '
                        'propagate actual fi0->fo0 inversion. Real native generated-clock waveform and wire load are mandatory for chain timing'],
               runs=runs, gate_layers=a.gate_layers, classes={})
    for m, r in srec['classes'].items():
        row = dict(instances_c26l=r.get('instances_c26l', 0), flow=r.get('flow'), buses=r.get('buses'),
                   view=dict(job=r.get('job'), verdict=r.get('verdict'), **{c: f for c, f in r['files'].items()}))
        if r['problems']:
            row.update(status='NOT_MEASURED', reason='; '.join(r['problems']))
        elif m not in res or a.gate_layers not in res[m]:
            row.update(status='NOT_MEASURED', reason='batch not complete')
            row['measured'] = res.get(m, {})
        else:
            g = res[m][a.gate_layers]
            row.update(status='MEASURED' if g['grt_overflow'] == [0, 0, 0] else 'TIMING_MEASURED_ROUTE_UNQUALIFIED', measured=res[m],
                       electrical_validity=g['electrical_validity'], usable_as_die_reach_bound=False,
                       clock_scenario='ideal_common_phase_component_sensitivity', actual_forwarded_half_cycle_chain_status='OPEN')
            row['reach_um'] = g['stream']['reach_um']
            row['reach_serial_um'] = g['serial']['reach_um']
            row['planning_um'] = round(0.9 * g['stream']['reach_um'], 1)
            row['planning_serial_um'] = round(0.9 * g['serial']['reach_um'], 1)
            hm = g['hold_ff'].get('hold_min_um')
            row['hold_min_um'] = hm
            if row['reach_um'] < a.flag_um:
                row['flag'] = 'REBUILD' if row['reach_um'] < a.rebuild_um or row['instances_c26l'] >= a.rebuild_inst \
                    else 'SHORT-HOP-ONLY'
        out['classes'][m] = row
    meas = {m: r for m, r in out['classes'].items() if r['status'] == 'MEASURED'}
    out['summary'] = dict(
        classes=len(out['classes']), measured=len(meas),
        not_measured={m: r.get('reason', r['status']) for m, r in out['classes'].items() if r['status'] != 'MEASURED'},
        below_flag_um=a.flag_um,
        flagged=sorted(([m, r['reach_um'], r['instances_c26l'], r['flag']] for m, r in meas.items() if r.get('flag')),
                       key=lambda x: x[1]),
        worst15_instance_weighted=[[m, r['reach_um'], r['instances_c26l']] for m, r in sorted(
            meas.items(), key=lambda kv: (kv[1]['reach_um'], -kv[1]['instances_c26l']))
            if r['instances_c26l'] > 0][:15],
        hold_floor=sorted([[m, r['hold_min_um']] for m, r in meas.items() if r['hold_min_um'] is not None and r['hold_min_um'] > 0], key=lambda x: -x[1]),
        min_reach_um=min((r['reach_um'] for r in meas.values()), default=None),
        min_reach_used_um=min((r['reach_um'] for r in meas.values() if r['instances_c26l']), default=None))
    Path(a.out).write_text(json.dumps(out, indent=1))
    print(json.dumps(out['summary'], indent=1)[:4000])


def _job(bd):
    p = bd / 'job.txt'
    return p.read_text().strip() if p.exists() else None


def _overflow(log):
    if not log.exists():
        return None
    t = log.read_text(errors='ignore')
    m = re.findall(r'Total\s+\d+\s+\d+\s+[\d.]+%\s+(\d+)\s*/\s*(\d+)\s*/\s*(\d+)', t)
    return [int(x) for x in m[-1]] if m else None


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sp = ap.add_subparsers(dest='cmd', required=True)
    s = sp.add_parser('stage')
    s.add_argument('--binding', default='results/arch/s81_native_20261013/view_binding_closed_sdie_c26l.json')
    s.add_argument('--census', default='results/physical/die_iter_1012/s81/sdie_1815/c26l_census.json')
    s.add_argument('--git', help='read the view files with git show from this worktree')
    s.add_argument('--rev', default='HEAD')
    s.add_argument('--root', default='.', help='else read them from this checkout root')
    s.add_argument('--out', required=True)
    p = sp.add_parser('plan')
    p.add_argument('--stage', required=True)
    p.add_argument('--out', required=True)
    p.add_argument('--layers', choices=sorted(LAYERS), default='m45')
    p.add_argument('--d0', type=float, default=25.0)
    p.add_argument('--d1', type=float, default=1000.0)
    p.add_argument('--step', type=float, default=25.0)
    p.add_argument('--net-budget', type=int, default=150000)
    p.add_argument('--repeaters', choices=['M4', 'M5', 'M7'], help='repair_design repeaters on every die wire (RC of LAYER)')
    p.add_argument('--max-area-mm2', type=float, default=8.0, help='per-batch die area bound (GRT memory ~3.5 GB/mm2)')
    p.add_argument('--classes', nargs='*')
    p.add_argument('--fwd-clock', action='store_true', help='also route A.fo0 -> B.fi0 (forwarded clock) where both exist')
    c = sp.add_parser('collect')
    c.add_argument('--stage', required=True)
    c.add_argument('--run', action='append', required=True)
    c.add_argument('--gate-layers', default='m45')
    c.add_argument('--flag-um', type=float, default=300.0)
    c.add_argument('--rebuild-um', type=float, default=200.0)
    c.add_argument('--rebuild-inst', type=int, default=100)
    c.add_argument('--date', default='2026-10-16')
    c.add_argument('--out', required=True)
    a = ap.parse_args(argv)
    dict(stage=cmd_stage, plan=cmd_plan, collect=cmd_collect)[a.cmd](a)


if __name__ == '__main__':
    sys.exit(main())
