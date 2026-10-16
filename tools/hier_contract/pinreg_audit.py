#!/usr/bin/env python3
"""Die timing by construction audit (owner 2026-10-13): every inter-tile signal is

    register at the pin  ->  wire <= 500 um  ->  register at the pin,   one fixed budget (IO 0.2 T of 833.333 ps).

Two checks per die contract (results/arch/hier_contract_*/<die>.json):

TILES  every closed view (Liberty ETM, OpenSTA write_timing_model) a contract cell resolves to is read per pin:
         O / S    raw ETM arcs from the tile's CLOCK PIN: clock -> output pin (lightest-load entry), setup at an input pin
         R        the tile's clock-insertion reference = mean clock arrival at its boundary registers (insertion.json
                  <corner>.boundary.mean: the same register set and rule as the sign-off reference io_ref_routed.sdc /
                  the kit's QDM PINFLOP median); else the midrange of the clock pin's min/max_clock_tree_path arcs
                  (ESTIMATE, note ref_estimated), else 0 (ideal clock)
         out_ps   o = O - R   launch residual after the reference        in_ps  s = S + R   capture residual (with setup)
         L / H    FF corner: earliest clock -> output and latest hold requirement at an input, both against R

       THE DIE STATEMENT (el1013-pinreg-audit.log 10-13, same equation as physical/common_flow/link_budget_consistent.sdc).
       The die delivers the clock to tile X's clock pin at  phi - R_X + e_X  (insertion-compensated entry, |e_A - e_B| <=
       SKEW), so the boundary registers of every tile tick at the common phase phi.  A hop A -> B of L um then needs
              o_A + w L + s_B  <=  T - U - SKEW            (setup; U 60, SKEW 90 same region / 150 across, w 0.76 ps/um TT)
              l_A + w_min L - h_B  >=  U_h + SKEW_h        (hold;  the L - H test below, 50 + 50)
       The sign-off SDC (IO "0.2 T") gives the OUTSIDE 0.2 T: it proves o, s <= 0.8 T - 90 - 60 = 516.7 ps a side, which
       does not compose by itself (two closed tiles may spend 1,033 ps).  What composes is the pair sum, so per tile:
         C        = worst o + worst s = O + S: the tile's reference-free cost of one hop against its own kind
         reach    = (T - U - SKEW - C) / w   the die wire a hop tile -> same tile can carry (>= --reach 500 um = OK;
                    negative = fails abutted); against another tile use o_A + s_B
         B        = (T - U - SKEW - w * reach) / 2 = 151.7 ps: the per-side share at the full 500 um (bits over it counted)
         clock    entry_offset_ps = -R (the REQUIRED die clock arrival at the tile's clock pin relative to phi, per
                  corner), boundary spread (max - min arrival at the boundary registers: NOT compensatable, it is
                  inside o and s), q_lb = O - I_max and p_lb = S + I_min (launch / capture path beyond the latest /
                  earliest boundary register: a register AT the pin leaves ~180 / ~150 ps, the closed station class)
       flags (a tile is VIOLATING on comb / out_unreg / in_unreg / spread / abut / min_delay):
               comb        a combinational pin-to-pin arc (the pin is not registered)
               out_unreg   q_lb > --q-pin: logic or a long wire between the launch flop and the pin
               in_unreg    p_lb > --p-pin: the first flop is not at the pin (or a control input fans out first)
               spread      boundary spread > --max-spread (80 ps, the owner clock rule's leaf-arrival spread)
               abut        C > T - U - SKEW: a hop to its own kind fails with no wire at all
               min_delay   L(min over outputs) - H(max over inputs) < 50 ps + skew  (the tile against its own kind)
       notes (not tile defects):
               reach_limited  reach < --reach: the die places a relay within `reach` of this tile
               ref_estimated  no insertion.json: R is the lib midrange over ALL clock sinks (spread_unmeasured: that
                              all-sink spread is over --max-spread; measure the boundary with ck_insertion.py)
               no_clock_arc   an output without any clock arc (constant / unconstrained; reported, not ranked)
       View resolution, in order: --view CELL=DIR, --bind (die_views bind map), --census (S81 real-view census
       timing_libs), the slot's `kit` (physical/ref_tile/<kit>/views/<cell>), a repo view whose Liberty cell has the
       contract cell's name, and (--alias) a same-family Qwen master (qfd_cst_n -> qfd_cst, qfd_crom_g -> qfd_crom_g_a):
       alias bindings are marked and are candidates only.  A cell with no view is listed as NOT AUDITABLE.
       Every view exported before the export-SDC fix (main abc334b14, 2026-10-13 02:42 PDT) is marked PROVISIONAL: its
       ETM boundary numbers may be off by tens of ps; re-run after the view is re-exported.  A view is CORRECTED only by
       its own record: abstract.json / export.json carries `reexport_1013` (re-export at the routed verdict's sequence)
       or a `verdict` with `check` / `expect_ps` (exported by the fixed tool).  A view without that record stays
       PROVISIONAL whatever its commit time (a later commit touching the directory is not a re-export).

HOPS   the die case realised from the contract (netlist + placement) gives every die-level data net = one hop (relays
       and stations are instances, so a net never contains a register).  Qwen: --case DIR (elements.lef, place.tcl,
       die.v; pin-to-pin half-perimeter of the bus-pin centroids).  S81: --s81-opts FILE (the generator model's buses;
       nearest-point distance of the two instance outlines, pin-to-pin where a real LEF pin model exists: a LOWER bound
       for generated slab masters).  A hop over --reach (500 um) is a hop without a relay.

    pinreg_audit.py --contract C.json [--bind B.json] [--census C5.json] [--alias] [--case DIR | --s81-opts F]
                    --out OUT.json [--md OUT.md]
"""
import argparse
import collections
import gzip
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EXPORT_FIX = 'abc334b14'          # view_export verdict replay (el1013-export-sdc.log)
T_PS = 833.333
WIRE = dict(tt=0.76, ss=1.135)   # ps/um buffered die wire (tools/budgets/common.py, dsrom_s81_fulldie TT fit)
NUM = re.compile(r'-?\d+\.?\d*(?:[eE][-+]?\d+)?')
TBL = ('cell_rise', 'cell_fall', 'rise_constraint', 'fall_constraint')


# ---------------------------------------------------------------------------------------------------------- Liberty
def parse_lib(path):
    """-> dict(cell, pins={name: dict(dir, clock, arcs=[(type, related, {tbl: [values]})])}); times in ps."""
    op = gzip.open if str(path).endswith('.gz') else open
    scale, cell, pins = 1.0, None, {}
    pin = arc = tbl = None
    depth = pin_d = arc_d = tbl_d = 0
    in_vals = False
    with op(path, 'rt', errors='replace') as fh:
        for ln in fh:
            s = ln.strip()
            if not s:
                continue
            if in_vals:
                arc[2].setdefault(tbl, []).extend(float(v) * scale for v in NUM.findall(s.split(')')[0]))
                in_vals = ')' not in s
            elif arc is not None:
                if s.startswith('related_pin'):
                    arc[1] = s.split(':', 1)[1].strip(' ;"')
                elif s.startswith('timing_type'):
                    arc[0] = s.split(':', 1)[1].strip(' ;"')
                elif s.startswith('values') and tbl:
                    body = s[s.index('(') + 1:]
                    arc[2].setdefault(tbl, []).extend(float(v) * scale for v in NUM.findall(body.split(')')[0]))
                    in_vals = ')' not in body
                elif s.endswith('{'):
                    nm = s.split('(')[0].strip()
                    if nm in TBL:
                        tbl, tbl_d = nm, depth
            elif pin is not None:
                if s.startswith('direction'):
                    pin['dir'] = s.split(':', 1)[1].strip(' ;"')
                elif s.startswith('clock ') or s.startswith('clock:'):
                    pin['clock'] = 'true' in s
                elif s.startswith('timing') and s.endswith('{'):
                    arc, arc_d = [None, None, {}], depth
                    pin['arcs'].append(arc)
            else:
                if s.startswith('pin') and s.endswith('{'):
                    m = re.match(r'pin\s*\(\s*"?([^")]+?)"?\s*\)', s)
                    if m:
                        pin, pin_d = dict(dir=None, clock=False, arcs=[]), depth
                        pins[m.group(1).strip()] = pin
                elif s.startswith('cell') and s.endswith('{') and cell is None:
                    m = re.match(r'cell\s*\(\s*"?([^")]+?)"?\s*\)', s)
                    cell = m.group(1) if m else None
                elif s.startswith('time_unit'):
                    scale = 1000.0 if '1ns' in s else 1.0
            depth += s.count('{') - s.count('}')
            if tbl is not None and depth <= tbl_d and not in_vals:
                tbl = None
            if arc is not None and depth <= arc_d:
                if arc[0] is None:
                    arc[0] = 'combinational' if arc[1] else 'unknown'
                arc = tbl = None
            if pin is not None and depth <= pin_d:
                pin = None
    return dict(cell=cell, pins=pins)


def clock_refs(lib, ins_json, corner):
    """clock pin -> dict(rise, fall, src, min, max): the boundary insertion reference per launching edge."""
    out = {}
    for name, p in lib['pins'].items():
        tree = [a for a in p['arcs'] if a[0] and a[0].endswith('_clock_tree_path')]
        if not tree:
            continue
        r = [v for a in tree for v in a[2].get('cell_rise', [])]
        f = [v for a in tree for v in a[2].get('cell_fall', [])] or r
        if not r:
            continue
        out[name] = dict(rise=(min(r) + max(r)) / 2, fall=(min(f) + max(f)) / 2, min=min(r), max=max(r), src='lib midrange',
                         bmin=min(r), bmax=max(r), n=None)
    records = [ins_json or {}]
    # A dual-clock view needs the independently measured reference of each
    # clock. The pin mapping comes from the routed SDC's create_clock port.
    records += list((ins_json or {}).get('clock_measurements', {}).values())
    for record in records:
        j = record.get(corner) or {}
        b = j.get('boundary') if isinstance(j, dict) else None
        if not (out and isinstance(b, dict) and b.get('mean') is not None):
            continue
        ck = record.get('lib_clock_pin') or record.get('clock')
        # insertion.json names the SDC clock port ("ck"); the Liberty clock pin may be a bus bit ("ck[0]") or the RTL
        # name ("clk"): exact name, else the bus, else the view's only clock pin (the measurement has one clock).
        # A view with several clock pins under other names (raw "cck" beside the spine "sk"): the measured clock is the
        # pin whose latest tree arc IS the measurement's latest boundary / sink arrival (same route, within 1 ps).
        hit = ([n for n in out if n == ck] or [n for n in out if bus_of(n) == ck] or (list(out) if len(out) == 1 else [])
               or [n for n in out if any(isinstance(x, dict) and x.get('max') is not None and abs(float(x['max']) - out[n]['max']) <= 1.0
                                         for x in (b, j.get('all')))])
        for name in hit[:1]:
            ref = out[name]
            d = float(b['mean']) - ref['rise']
            ref.update(rise=ref['rise'] + d, fall=ref['fall'] + d, src='insertion.json boundary mean',
                       bmin=float(b.get('min', ref['min'])), bmax=float(b.get('max', ref['max'])), n=b.get('n'))
    return out


def pin_metrics(lib, refs):
    """per pin: dict(dir, out, in, lmin, hold, comb=[related], clk) - None where the pin has no such arc."""
    res = {}
    for name, p in lib['pins'].items():
        if name in refs or p['clock'] or p['dir'] not in ('input', 'output', 'inout'):
            continue
        outs, lmins, ins, holds, comb, clk = [], [], [], [], [], set()
        edges = collections.Counter((a[1], a[0]) for a in p['arcs'] if a[0] in ('rising_edge', 'falling_edge'))
        if p['dir'] == 'output' and any((r_, 'rising_edge') in edges and (r_, 'falling_edge') in edges for r_, _ in edges):
            res[name] = dict(dir='clock_out', out=None, lmin=None, inp=None, hold=None, comb=[], clk=sorted({r_ for r_, _ in edges}))
            continue          # both edges of one clock reach the pin: a forwarded / through clock, not a data launch
        for typ, rel, v in p['arcs']:
            typ = typ or ''
            r = refs.get(rel, {})
            if typ in ('rising_edge', 'falling_edge'):
                ref = r.get('rise' if typ == 'rising_edge' else 'fall', 0.0)
                first = [v[k][0] for k in ('cell_rise', 'cell_fall') if v.get(k)]
                if first:
                    outs.append(max(first) - ref)
                    lmins.append(min(first) - ref)
                    clk.add(rel)
            elif typ.startswith('setup_') or typ.startswith('hold_'):
                ref = r.get('rise' if typ.endswith('rising') else 'fall', 0.0)
                vals = [x for k in ('rise_constraint', 'fall_constraint') for x in v.get(k, [])]
                if vals:
                    (ins if typ.startswith('setup') else holds).append(max(vals) + ref if typ.startswith('setup') else max(vals) - ref)
                    clk.add(rel)
            elif typ.startswith('combinational') or typ in ('unknown', 'three_state_enable', 'three_state_disable'):
                if rel:
                    comb.append(rel)
            elif 'clock_tree' not in typ and rel and rel not in refs and typ not in ('recovery_rising', 'removal_rising',
                                                                                    'recovery_falling', 'removal_falling',
                                                                                    'min_pulse_width'):
                comb.append(rel)
        res[name] = dict(dir=p['dir'], out=max(outs) if outs else None, lmin=min(lmins) if lmins else None,
                         inp=max(ins) if ins else None, hold=max(holds) if holds else None, comb=sorted(set(comb)),
                         clk=sorted(clk))
    return res


# ------------------------------------------------------------------------------------------------- view resolution
def git(*a):
    return subprocess.run(['git', '-C', str(ROOT)] + list(a), capture_output=True, text=True).stdout


def lib_index():
    """Liberty cell name, view directory name and ref_tile kit name -> [view dir] over every tracked *_tt/_ff/_ss
    .lib outside the memory-macro stores (a Qwen die-master view is stored under the master's name while its Liberty
    cell carries the RTL module name)."""
    head = git('rev-parse', 'HEAD').strip()
    cache = Path(os.environ.get('TMPDIR', '/tmp')) / f'pinreg_libindex2_{head[:12]}.json'
    if cache.exists():
        return json.loads(cache.read_text())
    files = [f for f in git('ls-files', 'physical', 'results').split('\n')
             if re.search(r'_(tt|ff|ss)\.lib(\.gz)?$', f) and not re.search(r'asap7_memory|pdie_macros|physical_abi3', f)]
    idx = collections.defaultdict(set)
    for f in files:
        op = gzip.open if f.endswith('.gz') else open
        try:
            with op(ROOT / f, 'rt', errors='replace') as fh:
                for ln in fh:
                    m = re.match(r'\s*cell\s*\(\s*"?([\w$]+)"?\s*\)', ln)
                    if m:
                        d = str(Path(f).parent)
                        idx[m.group(1)].add(d)
                        idx[Path(d).name].add(d)
                        k = re.search(r'/ref_tile/([^/]+)/views/', d + '/')
                        if k:
                            idx[k.group(1)].add(d)
                        break
        except OSError:
            pass
    idx = {k: sorted(v) for k, v in idx.items()}
    cache.write_text(json.dumps(idx))
    return idx


def view_rank(d):
    if '/ref_tile/' in d and '/views/' in d:
        return 0
    if '/closed/' in d or 's81_die_views/views' in d or '/assembled/' in d:
        return 1
    if 'qwen_die_masters/views' in d or 'hbm_accel_die_views' in d:
        return 2
    return 3 if d.startswith('physical/') and '/routes/' not in d else 4


def corner_libs(d):
    out = {}
    p = ROOT / d
    if not p.is_dir():
        return out
    for f in sorted(p.iterdir()):
        m = re.search(r'_(tt|ff|ss)\.lib(\.gz)?$', f.name)
        if m:
            out.setdefault(m.group(1), f)
    return out


def last_commit_time(d):
    t = git('log', '-1', '--format=%ct', '--', d).strip()
    return int(t) if t else 0


def export_corrected(view):
    """-> 'reexport_1013' | 'verdict' | None: the view's own record of an export at the routed verdict's sequence."""
    for n in ('abstract.json', 'export.json'):
        f = ROOT / view / n
        if not f.exists():
            continue
        try:
            d = json.loads(f.read_text())
        except (OSError, ValueError):
            continue
        if not isinstance(d, dict):
            continue
        if d.get('reexport_1013'):
            return 'reexport_1013'
        v = d.get('verdict')
        if isinstance(v, dict) and (v.get('check') or v.get('expect_ps')):
            return 'verdict'
    return None


def resolve_views(contract, a):
    """cell -> dict(view, binding, instances, slots) for every non-die contract cell (plus census closed masters)."""
    cells = collections.OrderedDict()
    for s in contract['slots']:
        if s.get('kind') == 'die':
            continue
        c = cells.setdefault(s['cell'], dict(instances=0, slots=[], kit=None, kinds=set()))
        c['instances'] += 1
        c['kinds'].add(s.get('kind'))
        if len(c['slots']) < 3:
            c['slots'].append(s['name'])
        if isinstance(s.get('kit'), str):
            c['kit'] = s['kit']
    explicit = dict(v.split('=', 1) for v in a.view or [])
    bind = {}
    for b in a.bind or []:
        bind.update({k: v['view'] for k, v in json.loads(Path(b).read_text()).items() if isinstance(v, dict) and v.get('view')})
    census = {}
    if a.census:
        for m in json.loads(Path(a.census).read_text())['masters']:
            libs = [t['path'] for t in m.get('timing_libs', []) if t.get('exists')]
            if libs and m.get('timing_index_tag') in ('closed', 'assembled', 'partitioned'):
                census[m['master']] = dict(view=str(Path(libs[0]).parent), instances=m.get('instances', 0),
                                           tag=m['timing_index_tag'], physical=m.get('physical_binding'))
    for k, v in census.items():
        if k not in cells:
            cells[k] = dict(instances=v['instances'], slots=[], kit=None, kinds={'die-placed master (census)'})
    idx = lib_index()
    out = collections.OrderedDict()
    for cell, c in cells.items():
        view, how = None, None
        if cell in explicit:
            view, how = explicit[cell], 'explicit'
        elif cell in bind:
            view, how = bind[cell], 'bind map'
        elif cell in census:
            view, how = census[cell]['view'], f"census ({census[cell]['tag']} timing, {census[cell]['physical']})"
        if view is None and c['kit']:
            k = re.sub(r'-v\d+-[0-9a-f]{6,}$', '', c['kit'])
            cand = f'physical/ref_tile/{k}/views/{cell}'
            if corner_libs(cand):
                view, how = cand, f'contract kit {c["kit"]}'
        if view is None and idx.get(cell):
            cand = sorted(idx[cell], key=lambda d: (view_rank(d), -last_commit_time(d)))
            view, how = cand[0], 'cell / view name' + (f' (1 of {len(cand)} views)' if len(cand) > 1 else '')
        if view is None and a.alias:
            base = re.sub(r'_(n|s|e|w|g)$', '', cell)
            al = [k for k in idx if k != cell and (k == base or re.fullmatch(re.escape(cell) + r'_[a-z]', k)
                                                    or re.fullmatch(re.escape(base) + r'(_[a-z]|_m5|_ref|_tp8|_rt)', k)
                                                    or re.fullmatch(re.escape(cell) + r'(_m5|_ref|_tp8|_rt)', k))]
            cand = sorted((d for k in al for d in idx[k]), key=lambda d: (view_rank(d), -last_commit_time(d)))
            if cand:
                view, how = cand[0], 'ALIAS (same-family master, candidate only)'
        out[cell] = dict(view=view, binding=how, instances=c['instances'], slots=c['slots'], kinds=sorted(k for k in c['kinds'] if k))
    return out


# ------------------------------------------------------------------------------------------------------ tile audit
def bus_of(pin):
    return re.sub(r'\[\d+\]$', '', pin)


def side_budget(a, corner):
    """-> (per-side share B at the full reach, pair sum available with no wire, wire ps/um) for the corner."""
    w = WIRE.get(corner, WIRE['tt']) if a.wire is None else a.wire
    avail = T_PS - a.setup_unc - a.die_skew
    return (avail - w * a.reach) / 2, avail, w


def fixes(s, dc, flags, a, w, thr):
    out = []
    if 'comb' in flags:
        out.append(f"{s['comb_bits']} combinational pin-to-pin bits: register them at the pin")
    if 'out_unreg' in flags:
        x = s['q_lb_ps'] - a.q_class
        out.append(f"output pin register missing or far: {s['out_unreg_bits']} bits ({', '.join(s['out_unreg_buses'][:4])}), worst "
                   f"{s['q_lb_bus']} leaves {s['q_lb_ps']:.0f} ps after the latest boundary clock = {x:.0f} ps over a pin flop "
                   f"(logic, or ~{x / w:.0f} um of wire, after the flop): add / move the output register to the pin")
    if 'in_unreg' in flags:
        x = s['p_lb_ps'] - a.p_class
        ctl = bool(re.search(r'rst|reset|clr|_en$|_v$|^en|stall|flush', s['p_lb_bus'] or ''))
        out.append(f"input pin register missing or far: {s['in_unreg_bits']} bits ({', '.join(s['in_unreg_buses'][:4])}), worst "
                   f"{s['p_lb_bus']} needs {s['p_lb_ps']:.0f} ps before the earliest boundary clock = {x:.0f} ps over a pin flop: "
                   + ('control / reset input fans out before its first flop: one pin register, fan-out tree behind it'
                      if ctl else f'first flop ~{x / w:.0f} um (or logic) behind the pin: register at the pin'))
    if 'spread' in flags:
        out.append(f"boundary clock spread {dc['boundary_spread_ps']:.0f} ps > {a.max_spread:.0f}: put the boundary registers on one "
                   f"balanced sub-root (or split the root); every ps is inside o + s ({1 / w:.1f} um of reach per ps)")
    if 'abut' in flags and not ({'out_unreg', 'in_unreg'} & set(flags)):
        out.append(f"o + s = {s['pair_cost_ps']:.0f} ps > {s['pair_available_ps']:.0f}: fails against its own kind with no wire")
    if 'min_delay' in flags:
        out.append(f"L - H = {s['min_delay_margin_ps']:.0f} ps < {thr:.0f}: pin hold cells at the input pin flops (finishing recipe 2)")
    return out


def audit_view(view, a, fix_time):
    libs = corner_libs(view)
    if not libs:
        return dict(error='no *_tt/_ff/_ss .lib in the view')
    sc = 'tt' if 'tt' in libs else ('ss' if 'ss' in libs else None)
    hc = 'ff' if 'ff' in libs else None
    ij = ROOT / view / 'insertion.json'
    ins = json.loads(ij.read_text()) if ij.exists() else None
    rec = dict(view=view, setup_corner=sc, hold_corner=hc, libs={k: v.name for k, v in libs.items()})
    ct = last_commit_time(view)
    rec['export_sdc_corrected'] = export_corrected(view)
    rec['committed_before_export_sdc_fix'] = bool(ct and ct < fix_time)
    rec['exported_before_export_sdc_fix'] = not rec['export_sdc_corrected']
    thr = a.hold_margin + a.skew
    budget, avail, _w = side_budget(a, sc or 'tt')
    refs_sc = {}
    buses = collections.OrderedDict()

    def b(name, d):
        return buses.setdefault(bus_of(name), dict(dir=d, bits=0, out_ps=None, in_ps=None, L_ps=None, H_ps=None,
                                                    comb_bits=0, out_over_bits=0, in_over_bits=0, no_clock_arc_bits=0,
                                                    no_setup_arc_bits=0, comb_from=[], worst_out_pin=None, worst_in_pin=None))
    mx = lambda x, y: y if x is None else (x if y is None else max(x, y))
    mn = lambda x, y: y if x is None else (x if y is None else min(x, y))
    if sc:
        lib = parse_lib(libs[sc])
        refs = clock_refs(lib, ins, sc)
        rec['lib_cell'] = lib['cell']
        rec['clocks'] = {k: dict(ref_ps=round(v['rise'], 1), min_ps=round(v['min'], 1), max_ps=round(v['max'], 1), src=v['src'],
                                 boundary_min_ps=round(v['bmin'], 1), boundary_max_ps=round(v['bmax'], 1),
                                 boundary_spread_ps=round(v['bmax'] - v['bmin'], 1), boundary_n=v['n'])
                         for k, v in refs.items()}
        refs_sc = refs
        if not refs:
            rec['note'] = 'no *_clock_tree_path arc: ideal-clock view, reference 0'
        for name, m in pin_metrics(lib, refs).items():
            r = b(name, m['dir'])
            r['bits'] += 1
            r['clocks'] = sorted(set(r.get('clocks', [])) | set(m['clk']))
            ck = refs.get(m['clk'][0]) if m['clk'] else None
            hi, lo = (ck['bmax'] - ck['rise'], ck['rise'] - ck['bmin']) if ck else (0.0, 0.0)
            if m['comb']:
                r['comb_bits'] += 1
                r['comb_from'] = sorted(set(r['comb_from']) | {bus_of(x) for x in m['comb']})[:8]
            if m['dir'] == 'output':
                if m['out'] is None and not m['comb']:
                    r['no_clock_arc_bits'] += 1
                elif m['out'] is not None:
                    if r['out_ps'] is None or m['out'] > r['out_ps']:
                        r['worst_out_pin'] = name
                    r['out_ps'] = mx(r['out_ps'], m['out'])
                    r['out_over_bits'] += m['out'] > budget
                    r['q_lb_ps'] = mx(r.get('q_lb_ps'), m['out'] - hi)
                    r['out_unreg_bits'] = r.get('out_unreg_bits', 0) + (m['out'] - hi > a.q_pin)
            elif m['dir'] == 'input':
                if m['inp'] is None and not m['comb']:
                    r['no_setup_arc_bits'] += 1
                elif m['inp'] is not None:
                    if r['in_ps'] is None or m['inp'] > r['in_ps']:
                        r['worst_in_pin'] = name
                    r['in_ps'] = mx(r['in_ps'], m['inp'])
                    r['in_over_bits'] += m['inp'] > budget
                    r['p_lb_ps'] = mx(r.get('p_lb_ps'), m['inp'] - lo)
                    r['in_unreg_bits'] = r.get('in_unreg_bits', 0) + (m['inp'] - lo > a.p_pin)
    if hc:
        lib = parse_lib(libs[hc])
        refs = clock_refs(lib, ins, hc)
        rec['clocks_ff'] = {k: dict(ref_ps=round(v['rise'], 1), boundary_min_ps=round(v['bmin'], 1),
                                    boundary_max_ps=round(v['bmax'], 1), src=v['src']) for k, v in refs.items()}
        for name, m in pin_metrics(lib, refs).items():
            r = b(name, m['dir'])
            if m['dir'] == 'output':
                r['L_ps'] = mn(r['L_ps'], m['lmin'])
            elif m['dir'] == 'input':
                r['H_ps'] = mx(r['H_ps'], m['hold'])
    for r in buses.values():
        for k in ('out_ps', 'in_ps', 'L_ps', 'H_ps', 'q_lb_ps', 'p_lb_ps'):
            if r.get(k) is not None:
                r[k] = round(r[k], 1)
    Ls = [(r['L_ps'], k) for k, r in buses.items() if r['L_ps'] is not None]
    Hs = [(r['H_ps'], k) for k, r in buses.items() if r['H_ps'] is not None]
    outs = [(r['out_ps'], k) for k, r in buses.items() if r['out_ps'] is not None]
    inps = [(r['in_ps'], k) for k, r in buses.items() if r['in_ps'] is not None]
    summ = dict(pins=sum(r['bits'] for r in buses.values()), buses=len(buses),
                comb_bits=sum(r['comb_bits'] for r in buses.values()),
                out_over_bits=sum(r['out_over_bits'] for r in buses.values()),
                in_over_bits=sum(r['in_over_bits'] for r in buses.values()),
                no_clock_arc_out_bits=sum(r['no_clock_arc_bits'] for r in buses.values()),
                no_setup_arc_in_bits=sum(r['no_setup_arc_bits'] for r in buses.values()),
                worst_out_ps=max(outs)[0] if outs else None, worst_out_bus=max(outs)[1] if outs else None,
                worst_in_ps=max(inps)[0] if inps else None, worst_in_bus=max(inps)[1] if inps else None,
                L_min_ps=min(Ls)[0] if Ls else None, L_min_bus=min(Ls)[1] if Ls else None,
                H_max_ps=max(Hs)[0] if Hs else None, H_max_bus=max(Hs)[1] if Hs else None)
    summ['min_delay_margin_ps'] = round(summ['L_min_ps'] - summ['H_max_ps'], 1) if Ls and Hs else None
    summ['min_delay_bits_out'] = sum(r['bits'] for r in buses.values()
                                     if Hs and r['L_ps'] is not None and r['L_ps'] - summ['H_max_ps'] < thr)
    summ['min_delay_bits_in'] = sum(r['bits'] for r in buses.values()
                                    if Ls and r['H_ps'] is not None and summ['L_min_ps'] - r['H_ps'] < thr)
    # ---- die clock delivery: the data clock (the one most data pins are timed to), its reference and spread
    use = collections.Counter()
    for r in buses.values():
        for c in r.get('clocks', []):
            use[c] += r['bits']
    dck = use.most_common(1)[0][0] if use else (next(iter(refs_sc)) if refs_sc else None)
    ck = refs_sc.get(dck)
    qs = [(r['q_lb_ps'], k) for k, r in buses.items() if r.get('q_lb_ps') is not None]
    ps_ = [(r['p_lb_ps'], k) for k, r in buses.items() if r.get('p_lb_ps') is not None]
    o, s_ = summ['worst_out_ps'], summ['worst_in_ps']
    C = round((o or 0.0) + (s_ or 0.0), 1) if (o is not None or s_ is not None) else None
    summ.update(pair_cost_ps=C, reach_self_um=round((avail - C) / _w, 1) if C is not None else None,
                side_budget_ps=round(budget, 1), pair_available_ps=round(avail, 1),
                q_lb_ps=max(qs)[0] if qs else None, q_lb_bus=max(qs)[1] if qs else None,
                p_lb_ps=max(ps_)[0] if ps_ else None, p_lb_bus=max(ps_)[1] if ps_ else None,
                out_unreg_bits=sum(r.get('out_unreg_bits', 0) for r in buses.values()),
                in_unreg_bits=sum(r.get('in_unreg_bits', 0) for r in buses.values()),
                out_unreg_buses=sorted((k for k, r in buses.items() if r.get('out_unreg_bits')), key=lambda k: -buses[k]['q_lb_ps'])[:8],
                in_unreg_buses=sorted((k for k, r in buses.items() if r.get('in_unreg_bits')), key=lambda k: -buses[k]['p_lb_ps'])[:8])
    if ck:
        ffr = (rec.get('clocks_ff') or {}).get(dck) or {}
        rec['die_clock'] = dict(
            clock_pin=dck, corner=sc, reference_ps=round(ck['rise'], 1), reference_src=ck['src'],
            entry_offset_ps=round(-ck['rise'], 1), entry_offset_ff_ps=round(-ffr['ref_ps'], 1) if ffr else None,
            boundary_min_ps=round(ck['bmin'], 1), boundary_max_ps=round(ck['bmax'], 1),
            boundary_spread_ps=round(ck['bmax'] - ck['bmin'], 1), boundary_n=ck['n'],
            all_sinks_min_ps=round(ck['min'], 1), all_sinks_max_ps=round(ck['max'], 1),
            # the residual after compensation IS (out_ps, in_ps); moving the entry by d ps trades them 1:1 (o - d, s + d)
            residual_out_ps=o, residual_in_ps=s_,
            balanced_entry_offset_ps=round(-(ck['rise'] + ((o or 0.0) - (s_ or 0.0)) / 2), 1) if o is not None and s_ is not None else None,
            signoff_allow_ps=round(0.8 * T_PS - 90.0 - a.setup_unc, 1),
            note='entry_offset = required die clock arrival at this clock pin relative to the common boundary phase; '
                 'balanced_entry_offset equalises o and s (hold must then be re-checked: l and h move with it)')
    flags = []
    if summ['comb_bits']:
        flags.append('comb')
    if summ['out_unreg_bits']:
        flags.append('out_unreg')
    if summ['in_unreg_bits']:
        flags.append('in_unreg')
    measured = bool(ck) and ck['src'] == 'insertion.json boundary mean'
    if measured and ck['bmax'] - ck['bmin'] > a.max_spread:
        flags.append('spread')
    if C is not None and C > avail:
        flags.append('abut')
    if summ['min_delay_margin_ps'] is not None and summ['min_delay_margin_ps'] < thr:
        flags.append('min_delay')
    notes = []
    if C is not None and C <= avail and summ['reach_self_um'] < a.reach:
        notes.append('reach_limited')
    if ck and not measured:
        notes.append('ref_estimated')
        if ck['bmax'] - ck['bmin'] > a.max_spread:
            notes.append('spread_unmeasured')     # all-sink lib spread over the limit; the boundary spread needs insertion.json
    rec['notes'] = notes
    rec['fix'] = fixes(summ, rec.get('die_clock'), flags, a, _w, thr)
    summ['clock_out_bits'] = sum(r['bits'] for r in buses.values() if r['dir'] == 'clock_out')
    if sc == 'ss':
        rec['note'] = (rec.get('note', '') + ' SS-only view (no TT lib): out/in are SS numbers against the TT budget').strip()
    rec.update(summary=summ, flags=flags, buses=buses)
    return rec


def severity(t):
    """combinational first, then the shortest reach against its own kind (the largest o + s)."""
    s = t.get('summary') or {}
    return (-(s.get('comb_bits', 0) > 0), -(s.get('pair_cost_ps') or 0.0), -(s.get('comb_bits', 0)),
            (s.get('min_delay_margin_ps') if s.get('min_delay_margin_ps') is not None else 1e9))


def die_clock_summary(audited, a):
    """The die clock tree's side of the rule: per-tile entry offsets, and what a COMMON-phase entry would cost."""
    ts = [t for t in audited if t.get('die_clock') and t['summary'].get('worst_out_ps') is not None
          and t['summary'].get('worst_in_ps') is not None and t.get('setup_corner') == 'tt']
    if not ts:
        return None
    R = {t['cell']: t['die_clock']['reference_ps'] for t in ts}
    rmax, rmin = max(R.values()), min(R.values())
    avail = T_PS - a.setup_unc - a.die_skew
    comp = max(((x['summary']['worst_out_ps'] + y['summary']['worst_in_ps'], x['cell'], y['cell']) for x in ts for y in ts))
    comm = max(((x['summary']['worst_out_ps'] + y['summary']['worst_in_ps'] + R[x['cell']] - R[y['cell']], x['cell'], y['cell'])
                for x in ts for y in ts))
    hs = [t for t in ts if t['summary'].get('L_min_ps') is not None and t['summary'].get('H_max_ps') is not None and t.get('clocks_ff')]
    Rf = {t['cell']: (t['clocks_ff'].get(t['die_clock']['clock_pin']) or {}).get('ref_ps', 0.0) for t in hs}
    hold = None
    if hs:
        hc = min(((x['summary']['L_min_ps'] - y['summary']['H_max_ps'], x['cell'], y['cell']) for x in hs for y in hs))
        hm = min(((x['summary']['L_min_ps'] - y['summary']['H_max_ps'] + Rf[x['cell']] - Rf[y['cell']], x['cell'], y['cell'])
                  for x in hs for y in hs))
        hold = dict(need_ps=a.hold_margin + a.skew,
                    compensated=dict(margin_ps=round(hc[0], 1), src=hc[1], dst=hc[2]),
                    common_phase=dict(margin_ps=round(hm[0], 1), src=hm[1], dst=hm[2]))
    trk = sorted(Rf[c] / R[c] for c in Rf if R[c] > 50 and Rf[c] > 0)
    return dict(
        corner='tt', tiles=len(ts), reference_min_ps=rmin, reference_max_ps=rmax, reference_span_ps=round(rmax - rmin, 1),
        deepest=max(R, key=R.get), shallowest=min(R, key=R.get),
        rule='clock at tile X clock pin = phi - R_X (+ common trunk); the branch to X carries R_max - R_X of added delay',
        added_delay_ps={c: round(rmax - v, 1) for c, v in sorted(R.items(), key=lambda kv: kv[1])},
        ocv_skew_ps=dict(frac=a.ocv, non_shared_per_side_ps=rmax, pair_ps=round(2 * a.ocv * rmax, 1), of_die_skew_ps=a.die_skew,
                         note='every clock pin is matched to the deepest tile, so each side of every hop carries >= R_max of '
                              'non-shared insertion: 2 x OCV x R_max of the die skew budget is spent before the die tree itself'),
        ff_tt_tracking=dict(min=round(trk[0], 3), max=round(trk[-1], 3),
                            mistrack_ps=round((trk[-1] - trk[0]) * (rmax - rmin), 1),
                            note='R_ff / R_tt per tile; a fixed-ratio delay line misses the span by this much at the other corner') if trk else None,
        setup_pair_available_ps=round(avail, 1),
        setup_worst_pair=dict(compensated=dict(o_plus_s_ps=round(comp[0], 1), src=comp[1], dst=comp[2],
                                               wire_left_ps=round(avail - comp[0], 1)),
                              common_phase=dict(o_plus_s_ps=round(comm[0], 1), src=comm[1], dst=comm[2],
                                                wire_left_ps=round(avail - comm[0], 1)),
                              note='potential pairs among the audited cells (connectivity not resolved); common phase adds '
                                   'R_src - R_dst to the pair'),
        hold_worst_pair=hold)


# ------------------------------------------------------------------------------------------------------- hop audit
def cls(n):
    return re.sub(r'\d+', '#', n)


def hops_qwen_case(case, contract, reach):
    """die_audit.py's class-4 walk at the 500 um rule, with the endpoint masters kept per hop."""
    D = Path(case)
    size, pins, cur, pin = {}, collections.defaultdict(dict), None, None
    bitpin = collections.defaultdict(dict)        # cell -> full pin name -> (x, y): for concatenated connections
    for lef in sorted(D.glob('*.lef')):
        for ln in open(lef):
            s = ln.strip()
            if s.startswith('MACRO '):
                cur, pin = s.split()[1], None
            elif s.startswith('SIZE') and cur not in size:
                t = s.split()
                size[cur] = (float(t[1]), float(t[3]))
            elif s.startswith('PIN '):
                pin = s.split()[1]
            elif pin and s.startswith('RECT'):
                t = s.split()
                d = pins[cur].setdefault(bus_of(pin), [0.0, 0.0, 0])
                d[0] += (float(t[1]) + float(t[3])) / 2
                d[1] += (float(t[2]) + float(t[4])) / 2
                d[2] += 1
                bitpin[cur][pin] = ((float(t[1]) + float(t[3])) / 2, (float(t[2]) + float(t[4])) / 2)
                pin = None
    pos = {}
    if (D / 'place.tcl').exists():
        for ln in open(D / 'place.tcl'):
            m = re.search(r'findInst (\S+)\]\s+([\d.]+)\s+([\d.]+)\s+(\w+)', ln)
            if m:
                pos[m.group(1)] = (float(m.group(2)), float(m.group(3)), m.group(4))
    else:       # HBM die case (tools/hbm_accel_die_fp.py grt): the placement is the place_inst block of run.tcl
        for ln in open(D / 'run.tcl'):
            m = re.match(r'place_inst -name (\S+) -location \{([\d.]+) ([\d.]+)\} -orientation (\S+)', ln)
            if m:
                pos[m.group(1)] = (float(m.group(2)), float(m.group(3)), m.group(4))
    txt = (D / 'die.v').read_text()
    # a bundled case (manifest bundle_k = 16) carries one wire per k bits: report bits, not bundles
    kb = json.loads((D / 'manifest.json').read_text()).get('bundle_k', 1) if (D / 'manifest.json').exists() else 1
    width = {m.group(2): (int(m.group(1)) + 1) * kb for m in re.finditer(r'wire \[(\d+):0\] (\S+);', txt)}
    inst, netpins = {}, collections.defaultdict(list)
    netbits = collections.defaultdict(list)        # net -> [(inst, full pin name)] of concatenated connections
    for m in re.finditer(r'^\s+(\w+) (\S+) \((.*?)\);', txt, re.M):
        mst, nm, body = m.groups()
        inst[nm] = mst
        for p in re.finditer(r'\.(\w+)\(([^()]*)\)', body):
            port, ex = p.group(1), p.group(2).strip()
            if re.fullmatch(r"\d+'[bdh][0-9a-fA-F_]+", ex):
                continue                              # a constant (strap, chain end, tied ready): not a net
            if ex.startswith('{'):
                # contract v5 die.v: a concatenation, MSB first (a hard-macro bus pin fed bit by bit from several nets,
                # or one net wired field to field): every element is measured at its own pin bit
                el = []
                for e in ex.strip('{}').split(','):
                    e = e.strip()
                    q = re.fullmatch(r'(\w+)\[(\d+)(?::(\d+))?\]', e)
                    if q:
                        hi, lo = int(q.group(2)), int(q.group(3) if q.group(3) is not None else q.group(2))
                        el += [q.group(1)] * (hi - lo + 1)
                    else:
                        el.append(e if re.fullmatch(r'\w+', e) else None)
                seen_ = set()
                for j, net in enumerate(el):
                    if net is None:
                        continue
                    pn = f'{port}[{len(el) - 1 - j}]'
                    if pn in bitpin.get(mst, {}):
                        netbits[net].append((nm, pn))
                    elif net not in seen_:
                        netpins[net].append((nm, port))
                    seen_.add(net)
                continue
            # a slice of a net (one die bundle = several view ports) is that net
            netpins[re.sub(r'\[\d+(?::\d+)?\]$', '', ex)].append((nm, port))
    for net, l in netbits.items():
        by_i = collections.defaultdict(list)
        for i, pn in l:
            by_i[i].append(pn)
        for i, pns in by_i.items():
            xs_ = [bitpin[inst[i]][q][0] for q in pns]
            ys_ = [bitpin[inst[i]][q][1] for q in pns]
            key = '@bits:' + net
            pins[inst[i]][key + ':' + i] = [sum(xs_), sum(ys_), len(pns)]
            netpins[net].append((i, key + ':' + i))

    def pinxy(i, p):
        if i not in pos or inst[i] not in size:
            return None
        x0, y0, o = pos[i]
        w, h = size[inst[i]]
        d = pins[inst[i]].get(p)
        if not d or not d[2]:
            return None
        px, py = d[0] / d[2], d[1] / d[2]
        return {'R0': (x0 + px, y0 + py), 'MX': (x0 + px, y0 + h - py), 'MY': (x0 + w - px, y0 + py),
                'R180': (x0 + w - px, y0 + h - py)}.get(o)
    is_clk = lambda n: n.startswith(('n_clk', 'n_fck', 'n_pll')) or '_clk_' in n
    hops, nopin, nets = [], 0, 0
    for n, ps in netpins.items():
        if is_clk(n) or len(ps) < 2:
            continue
        nets += 1
        pts = [pinxy(i, p) for i, p in ps]
        if any(q is None for q in pts):
            nopin += 1
            continue
        xs, ys = [q[0] for q in pts], [q[1] for q in pts]
        L = max(xs) - min(xs) + max(ys) - min(ys)
        if L > reach:
            hops.append(dict(um=round(L, 1), net=n, bits=width.get(n, 1), ends=[f'{i}.{p}' for i, p in ps[:4]], pins=len(ps),
                             masters=sorted({inst[i] for i, _ in ps}), measure='pin-to-pin',
                             kind='reset' if re.match(r'n_rst|n_arst|.*_rst_', n) else 'data'))
    slots = {s['name']: s for s in contract['slots'] if s.get('kind') != 'die' and s.get('origin')}
    same = sum(1 for k, s in slots.items() if k in pos and abs(pos[k][0] - s['origin']['x']) < 0.01 and abs(pos[k][1] - s['origin']['y']) < 0.01)
    src = ' '.join((D / f).read_text().strip() for f in ('SOURCE_COMMIT', 'SOURCE_NOTE') if (D / f).exists())
    return dict(source=f'case {case} {src}'.strip(), instances=len(inst), data_nets=nets, nets_without_pin_model=nopin,
                contract_slots=len(slots), contract_slots_placed_as_contract=same,
                contract_slots_missing_or_moved=len(slots) - same), hops


def hops_s81(opts_file, extra, contract, reach):
    sys.path.insert(0, str(ROOT / 'tools'))
    os.environ.setdefault('OT_S81_CTRL_GATE_WARN', 'phys')
    os.environ.setdefault('OT_S81_Q_LEF', 'physical/s81_die_views/q_elem_qs5f_efs/q_elem.lef.gz')
    os.chdir(ROOT)
    import dsrom_s81_fulldie as F
    ap = argparse.ArgumentParser()
    F.die_options(ap)
    F.apply_options(ap.parse_args(Path(opts_file).read_text().split() + extra.split()))
    m = F.build()
    F.finalize_r8(m)
    by = {it.name: it for it in m['insts']}
    pp = F._lint_pin_pt(m)
    near = lambda it, q: (min(max(q[0], it.x), it.x + it.w), min(max(q[1], it.y), it.y + it.h))
    cen = lambda it: (it.x + it.w / 2, it.y + it.h / 2)
    hops, nets = [], 0
    for bid, kind, bits, eps in m['buses']:
        if kind in F.HOP_SKIP or len(eps) < 2 or eps[0][0] not in by:
            continue
        d = by[eps[0][0]]
        for li, lp in eps[1:]:
            if li not in by or li == eps[0][0]:
                continue
            nets += 1
            l = by[li]
            pa, pb = pp(eps[0][0], eps[0][1]), pp(li, lp)
            if pa and pb:
                L, how = abs(pa[0] - pb[0]) + abs(pa[1] - pb[1]), 'pin-to-pin'
            else:
                qa = pa or near(d, pb or cen(l))
                qb = pb or near(l, qa)
                qa = pa or near(d, qb)
                L, how = abs(qa[0] - qb[0]) + abs(qa[1] - qb[1]), 'outline nearest point (lower bound)'
            if L > reach:
                hops.append(dict(um=round(L, 1), net=str(bid), bits=bits, cls=kind, ends=[f'{eps[0][0]}.{eps[0][1]}', f'{li}.{lp}'],
                                 masters=sorted({str(d.master), str(l.master)}), kinds=[d.kind, l.kind], measure=how))
    slots = {s['name']: s for s in contract['slots'] if s.get('kind') != 'die' and s.get('origin')}
    same = sum(1 for k, s in slots.items() if k in by and abs(by[k].x - s['origin']['x']) < 0.01 and abs(by[k].y - s['origin']['y']) < 0.01)
    return dict(source=f'generator model {opts_file} {extra}'.strip(), instances=len(by), data_nets=nets,
                contract_slots=len(slots), contract_slots_placed_as_contract=same,
                contract_slots_missing_or_moved=len(slots) - same,
                note='contract slot names that are hierarchical (parent/child) are not die-model instance names; '
                     'only top-level slots can match'), hops


def hop_summary(meta, hops, reach):
    hops.sort(key=lambda h: -h['um'])
    by_cls = collections.OrderedDict()
    for h in hops:
        c = by_cls.setdefault(cls(h['net']), dict(hops=0, bits=0, max_um=0.0, masters=set(), example=h['net']))
        c['hops'] += 1
        c['bits'] += h['bits']
        c['max_um'] = max(c['max_um'], h['um'])
        c['masters'] |= set(h['masters'])
    for c in by_cls.values():
        c['masters'] = sorted(c['masters'])[:6]
    by_master = collections.Counter(mst for h in hops for mst in h['masters'])
    rst = [h for h in hops if h.get('kind') == 'reset']
    return dict(meta, reach_um=reach, hops_over=len(hops), bits_over=sum(h['bits'] for h in hops),
                data_hops_over=len(hops) - len(rst), reset_nets_over=len(rst),
                max_um=hops[0]['um'] if hops else 0.0,
                by_class=sorted(([k, v] for k, v in by_cls.items()), key=lambda kv: -kv[1]['max_um']),
                by_master=by_master.most_common(40), worst=hops[:60])


# ------------------------------------------------------------------------------------------------------------ main
def fmt(v, w=7):
    return f'{v:{w}.1f}' if isinstance(v, (int, float)) else ' ' * (w - 1) + '-'


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--contract', required=True)
    ap.add_argument('--contract-label', help='recorded instead of the --contract path (a contract read from another branch)')
    ap.add_argument('--bind', action='append', help='die_views bind map (repeatable)')
    ap.add_argument('--census', help='S81 real-view census JSON (masters[].timing_libs)')
    ap.add_argument('--view', action='append', help='CELL=view dir (repeatable)')
    ap.add_argument('--alias', action='store_true', help='bind a same-family master view when no exact view exists')
    ap.add_argument('--case', help='Qwen die case dir (elements.lef, place.tcl, die.v)')
    ap.add_argument('--s81-opts', help='S81 generator options file')
    ap.add_argument('--s81-extra', default='--cfifo-colck')
    ap.add_argument('--setup-unc', type=float, default=60.0, help='setup clock uncertainty at sign-off, ps')
    ap.add_argument('--die-skew', type=float, default=90.0, help='die clock arrival error between two insertion-compensated '
                    'tile clock pins, ps (kit OT_IO_SKEW: 90 same region; 150 across regions)')
    ap.add_argument('--wire', type=float, default=None, help='die wire ps/um (default 0.76 TT, 1.135 for SS-only views)')
    ap.add_argument('--max-spread', type=float, default=80.0, help='boundary clock arrival spread allowed in a tile, ps')
    ap.add_argument('--q-class', type=float, default=180.0, help='clock -> pin of a register AT the pin, ps (closed stations)')
    ap.add_argument('--p-class', type=float, default=150.0, help='pin -> flop + setup of a register AT the pin, ps')
    ap.add_argument('--q-pin', type=float, default=220.0, help='out_unreg above this launch path, ps')
    ap.add_argument('--p-pin', type=float, default=190.0, help='in_unreg above this capture path, ps')
    ap.add_argument('--ocv', type=float, default=0.05, help='clock-path OCV on non-shared insertion (tools/budgets/common.py)')
    ap.add_argument('--reach', type=float, default=500.0)
    ap.add_argument('--hold-margin', type=float, default=50.0)
    ap.add_argument('--skew', type=float, default=50.0, help='die clock skew between two tiles for the minimum-delay test, ps '
                    '(the sign-off kits\' OT_IO_HOLD_SKEW)')
    ap.add_argument('--out', required=True)
    ap.add_argument('--md')
    a = ap.parse_args(argv)
    contract = json.loads(Path(a.contract).read_text())
    fix_time = int(git('log', '-1', '--format=%ct', EXPORT_FIX).strip() or 0)
    views = resolve_views(contract, a)
    cache, tiles = {}, []
    for cell, v in views.items():
        t = dict(cell=cell, instances=v['instances'], slots=v['slots'], kinds=v['kinds'], binding=v['binding'])
        if v['view']:
            if v['view'] not in cache:
                cache[v['view']] = audit_view(v['view'], a, fix_time)
            t.update(cache[v['view']])
            t['view'] = v['view']
        else:
            t['error'] = 'NOT AUDITABLE: no closed view (.lib ETM) found for the contract cell'
        tiles.append(t)
    audited = [t for t in tiles if 'summary' in t]
    viol = sorted((t for t in audited if t['flags']), key=severity)
    B, avail, w_tt = side_budget(a, 'tt')
    dcs = die_clock_summary(audited, a)
    thr = a.hold_margin + a.skew
    cross = []
    for s in audited:
        for d in audited:
            L, H = s['summary']['L_min_ps'], d['summary']['H_max_ps']
            if L is not None and H is not None and L - H < thr and s is not d:
                cross.append(dict(src=s['cell'], dst=d['cell'], margin_ps=round(L - H, 1)))
    cross.sort(key=lambda c: c['margin_ps'])
    hops = None
    if a.case:
        hops = hop_summary(*hops_qwen_case(a.case, contract, a.reach), a.reach)
    elif a.s81_opts:
        hops = hop_summary(*hops_s81(a.s81_opts, a.s81_extra, contract, a.reach), a.reach)
    prov = sum(1 for t in audited if t.get('exported_before_export_sdc_fix'))
    out = dict(schema='opentallas.pinreg_audit.v1', die=contract.get('die'), contract=a.contract_label or a.contract,
               contract_version=contract.get('version'), source_commit=git('rev-parse', '--short=9', 'HEAD').strip(),
               schema_note='v2 (10-13): judged on the pair equation with insertion-compensated clock entry; v1 judged '
                           'each side against 0.2 T',
               rule=dict(period_ps=T_PS, setup_unc_ps=a.setup_unc, die_skew_ps=a.die_skew, wire_ps_per_um=w_tt, reach_um=a.reach,
                         pair_available_ps=round(avail, 1), side_budget_ps=round(B, 1),
                         signoff_allow_ps=round(0.8 * T_PS - 90.0 - a.setup_unc, 1),
                         max_spread_ps=a.max_spread, q_pin_ps=a.q_pin, p_pin_ps=a.p_pin, q_class_ps=a.q_class, p_class_ps=a.p_class,
                         min_delay_ps=thr, hold_margin_ps=a.hold_margin, skew_ps=a.skew,
                         reading='die clock at tile X clock pin = phi - R_X (R = mean boundary-register insertion, the sign-off '
                                 'reference); hop A -> B: o_A + w L + s_B <= T - U - SKEW with o = clk->pin - R, s = setup@pin + R; '
                                 'per tile C = o + s, reach = (T - U - SKEW - C) / w; the sign-off SDC (0.2 T outside) only '
                                 'proves o, s <= signoff_allow each'),
               die_clock=dcs,
               status=('PROVISIONAL: %d of %d audited views carry no corrected-export record (reexport_1013 / verdict check) '
                       'after the export-SDC fix (%s); their boundary numbers may be off by tens of ps'
                       % (prov, len(audited), EXPORT_FIX)) if prov else 'views post export-SDC fix',
               export_sdc=dict(corrected=len(audited) - prov, pre_fix=prov,
                               pre_fix_views=sorted({t['view'] for t in audited if t.get('exported_before_export_sdc_fix')})),
               counts=dict(contract_cells=len(tiles), audited=len(audited), not_auditable=len(tiles) - len(audited),
                           violating=len(viol), reach_limited=sum(1 for t in audited if 'reach_limited' in t.get('notes', [])),
                           clean=sum(1 for t in audited if not t['flags'] and 'reach_limited' not in t.get('notes', [])),
                           ref_estimated=sum(1 for t in audited if 'ref_estimated' in t.get('notes', [])),
                           alias_bound=sum(1 for t in audited if (t['binding'] or '').startswith('ALIAS')),
                           by_flag=dict(collections.Counter(f for t in viol for f in t['flags'])),
                           instances_audited=sum(t['instances'] for t in audited),
                           instances_not_auditable=sum(t['instances'] for t in tiles if 'summary' not in t),
                           hops_over=hops['hops_over'] if hops else None),
               ranked_violations=[dict(rank=i + 1, cell=t['cell'], instances=t['instances'], flags=t['flags'], view=t['view'],
                                       binding=t['binding'], provisional=t.get('exported_before_export_sdc_fix'),
                                       setup_corner=t.get('setup_corner'), notes=t.get('notes'), fix=t.get('fix'),
                                       reference_ps=(t.get('die_clock') or {}).get('reference_ps'),
                                       reference_src=(t.get('die_clock') or {}).get('reference_src'),
                                       boundary_spread_ps=(t.get('die_clock') or {}).get('boundary_spread_ps'),
                                       **{k: t['summary'][k] for k in ('comb_bits', 'out_over_bits', 'in_over_bits', 'worst_out_ps',
                                                                      'worst_out_bus', 'worst_in_ps', 'worst_in_bus', 'L_min_ps',
                                                                      'H_max_ps', 'min_delay_margin_ps', 'pins', 'pair_cost_ps',
                                                                      'reach_self_um', 'q_lb_ps', 'q_lb_bus', 'p_lb_ps', 'p_lb_bus',
                                                                      'out_unreg_bits', 'in_unreg_bits')})
                                  for i, t in enumerate(viol)],
               not_auditable=[dict(cell=t['cell'], instances=t['instances'], kinds=t['kinds']) for t in tiles if 'summary' not in t],
               cross_tile_min_delay=dict(note='potential pairs (connectivity between view cells is not resolved): '
                                              'L_min(src) - H_max(dst) < %.0f ps' % thr, pairs=len(cross), worst=cross[:40]),
               hops=hops, tiles=tiles)
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(out, indent=1) + '\n')
    f1 = lambda v: '-' if v is None else f'{v:.1f}'
    L = [f"# Pin-register audit: {out['die']} (contract v{out['contract_version']}, {out['source_commit']})", '',
         f"Rule (die statement): the die delivers the clock to each tile's clock pin at `phi - R` (R = mean insertion of the "
         f"tile's boundary registers, the sign-off reference); a hop A -> B of L um needs `o_A + {w_tt} L + s_B <= "
         f"{T_PS:.1f} - {a.setup_unc:.0f} - {a.die_skew:.0f} = {avail:.1f} ps` (o = clk->pin - R, s = setup@pin + R). "
         f"Per tile C = o + s and reach = ({avail:.1f} - C) / {w_tt} against its own kind; the per-side share at "
         f"{a.reach:.0f} um is {B:.1f} ps. The sign-off SDC (IO 0.2 T outside) proves only o, s <= "
         f"{out['rule']['signoff_allow_ps']} ps each. Hold: L - H >= {thr:.0f} ps ({a.hold_margin:.0f} + skew {a.skew:.0f}).", '',
         f"**{out['status']}**", '',
         f"Cells {len(tiles)}: audited {len(audited)} ({out['counts']['instances_audited']} instances); VIOLATING {len(viol)} "
         f"{out['counts']['by_flag']}; reach-limited only {out['counts']['reach_limited']}; clean {out['counts']['clean']}; "
         f"reference estimated (no insertion.json) {out['counts']['ref_estimated']}; not auditable {len(tiles) - len(audited)} "
         f"({out['counts']['instances_not_auditable']} instances); alias-bound {out['counts']['alias_bound']}.", '']
    if dcs:
        sp, hp_ = dcs['setup_worst_pair'], dcs['hold_worst_pair']
        L += ['## Die clock delivery', '',
              f"R spans {dcs['reference_min_ps']} ({dcs['shallowest']}) .. {dcs['reference_max_ps']} ({dcs['deepest']}) ps at TT "
              f"= {dcs['reference_span_ps']} ps. Compensated entry: each branch carries R_max - R of added delay; OCV "
              f"{a.ocv:.0%} on the non-shared {dcs['reference_max_ps']} ps a side = {dcs['ocv_skew_ps']['pair_ps']} ps of the "
              f"{a.die_skew:.0f} ps die skew on EVERY hop; FF/TT tracking of R "
              + (f"{dcs['ff_tt_tracking']['min']}..{dcs['ff_tt_tracking']['max']} = {dcs['ff_tt_tracking']['mistrack_ps']} ps over the span."
                 if dcs['ff_tt_tracking'] else 'n/a.'), '',
              f"Worst potential pair, setup (available {avail:.1f} ps before wire): compensated {sp['compensated']['o_plus_s_ps']} ps "
              f"({sp['compensated']['src']} -> {sp['compensated']['dst']}, wire left {sp['compensated']['wire_left_ps']}); COMMON-phase "
              f"entry {sp['common_phase']['o_plus_s_ps']} ps ({sp['common_phase']['src']} -> {sp['common_phase']['dst']}, wire left "
              f"{sp['common_phase']['wire_left_ps']})."
              + (f" Hold (need {hp_['need_ps']:.0f}): compensated {hp_['compensated']['margin_ps']} ps ({hp_['compensated']['src']} -> "
                 f"{hp_['compensated']['dst']}); common phase {hp_['common_phase']['margin_ps']} ps ({hp_['common_phase']['src']} -> "
                 f"{hp_['common_phase']['dst']})." if hp_ else ''), '']
    L += ['## Tiles (all audited, worst reach first)', '',
          '| cell | inst | corner | R ps (src) | clock entry vs phi | + branch delay | boundary spread | o ps (bus) | s ps (bus) | C = o+s | reach um | q_lb | p_lb | L-H | flags | notes |',
          '|---|---:|---|---|---:|---:|---:|---|---|---:|---:|---:|---:|---:|---|---|']
    for t in sorted(audited, key=lambda t: -(t['summary'].get('pair_cost_ps') or 0)):
        s_, dc = t['summary'], t.get('die_clock') or {}
        add = (dcs or {}).get('added_delay_ps', {}).get(t['cell'])
        L.append(f"| {t['cell']} | {t['instances']} | {t.get('setup_corner')} | {f1(dc.get('reference_ps'))} "
                 f"({'ins.json' if dc.get('reference_src', '').startswith('insertion') else 'lib mid'}) | {f1(dc.get('entry_offset_ps'))} | "
                 f"{f1(add)} | {f1(dc.get('boundary_spread_ps'))} | {f1(s_['worst_out_ps'])} ({s_['worst_out_bus']}) | "
                 f"{f1(s_['worst_in_ps'])} ({s_['worst_in_bus']}) | {f1(s_['pair_cost_ps'])} | {f1(s_['reach_self_um'])} | "
                 f"{f1(s_['q_lb_ps'])} | {f1(s_['p_lb_ps'])} | {f1(s_['min_delay_margin_ps'])} | {' '.join(t['flags']) or '-'} | "
                 f"{' '.join(t.get('notes', [])) or '-'} |")
    L += ['', '## Violating tiles and the fix each needs', '']
    for r in out['ranked_violations']:
        L.append(f"{r['rank']}. **{r['cell']}** x{r['instances']} [{' '.join(r['flags'])}] ({r['binding']}): " + '; '.join(r['fix'] or ['-']))
    L += ['', f"Export-SDC: {out['export_sdc']['corrected']} audited cells on corrected views, {prov} still pre-fix"
              + (': ' + ', '.join(out['export_sdc']['pre_fix_views']) if prov else '') + '.']
    L += ['', 'Not auditable (no closed view): ' + (', '.join(f"{t['cell']} x{t['instances']}" for t in out['not_auditable']) or 'none'), '']
    if hops:
        L += [f"## Hops over {a.reach:.0f} um: {hops['hops_over']} ({hops['bits_over']} bits; {hops['data_hops_over']} data, "
              f"{hops['reset_nets_over']} unrelayed reset nets), max {hops['max_um']} um", '',
              f"Source: {hops['source']}; {hops['instances']} instances, {hops['data_nets']} data hops; contract slots placed as the "
              f"contract {hops['contract_slots_placed_as_contract']} / {hops['contract_slots']}.", '',
              '| class | hops | bits | max um | masters |', '|---|---:|---:|---:|---|']
        L += [f"| {k} | {v['hops']} | {v['bits']} | {v['max_um']} | {', '.join(v['masters'])} |" for k, v in hops['by_class'][:40]]
    else:
        L += ['## Hops: no die case given (contract carries placement but no nets)']
    if a.md:
        Path(a.md).write_text('\n'.join(L) + '\n')
    print('\n'.join(L[:12]))
    print(f"hops over {a.reach:.0f} um: {hops['hops_over'] if hops else 'n/a'}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
