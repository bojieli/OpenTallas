#!/usr/bin/env python3
"""Die timing by construction audit (owner 2026-10-13): every inter-tile signal is

    register at the pin  ->  wire <= 500 um  ->  register at the pin,   one fixed budget (IO 0.2 T of 833.333 ps).

Two checks per die contract (results/arch/hier_contract_*/<die>.json):

TILES  every closed view (Liberty ETM, OpenSTA write_timing_model) a contract cell resolves to is read per pin:
         out_ps   clock -> output pin, lightest-load table entry, minus the tile's clock insertion reference
         in_ps    input pin -> flop = setup at the pin plus the insertion reference (includes the flop's setup time)
         L / H    FF corner: earliest clock -> output and latest hold requirement at an input, both against the reference
       flags:  comb       a combinational pin-to-pin arc (the pin is not registered)
               out_over   out_ps > budget           in_over  in_ps > budget        (budget = 0.2 T = 166.7 ps a side)
               min_delay  L(min over outputs) - H(max over inputs) < 50 ps + skew  (the tile against its own kind)
               no_clock_arc  an output without any clock arc (constant / unconstrained; reported, not ranked)
       The insertion reference is the view's insertion.json corner mean (the boundary pin-flop reference the sign-off
       SDC uses) when present, else the midrange of the clock pin's min/max_clock_tree_path arcs, else 0 (ideal clock).
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
        ref = dict(rise=(min(r) + max(r)) / 2, fall=(min(f) + max(f)) / 2, min=min(r), max=max(r), src='lib midrange')
        j = (ins_json or {}).get(corner) or {}
        if (ins_json or {}).get('clock') == name and isinstance(j.get('boundary'), dict) and j['boundary'].get('mean') is not None:
            d = float(j['boundary']['mean']) - ref['rise']
            ref.update(rise=ref['rise'] + d, fall=ref['fall'] + d, src='insertion.json boundary mean')
        out[name] = ref
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
    budget, thr = a.budget_frac * T_PS, a.hold_margin + a.skew
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
        rec['clocks'] = {k: dict(ref_ps=round(v['rise'], 1), min_ps=round(v['min'], 1), max_ps=round(v['max'], 1), src=v['src'])
                         for k, v in refs.items()}
        if not refs:
            rec['note'] = 'no *_clock_tree_path arc: ideal-clock view, reference 0'
        for name, m in pin_metrics(lib, refs).items():
            r = b(name, m['dir'])
            r['bits'] += 1
            r['clocks'] = sorted(set(r.get('clocks', [])) | set(m['clk']))
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
            elif m['dir'] == 'input':
                if m['inp'] is None and not m['comb']:
                    r['no_setup_arc_bits'] += 1
                elif m['inp'] is not None:
                    if r['in_ps'] is None or m['inp'] > r['in_ps']:
                        r['worst_in_pin'] = name
                    r['in_ps'] = mx(r['in_ps'], m['inp'])
                    r['in_over_bits'] += m['inp'] > budget
    if hc:
        lib = parse_lib(libs[hc])
        refs = clock_refs(lib, ins, hc)
        for name, m in pin_metrics(lib, refs).items():
            r = b(name, m['dir'])
            if m['dir'] == 'output':
                r['L_ps'] = mn(r['L_ps'], m['lmin'])
            elif m['dir'] == 'input':
                r['H_ps'] = mx(r['H_ps'], m['hold'])
    for r in buses.values():
        for k in ('out_ps', 'in_ps', 'L_ps', 'H_ps'):
            if r[k] is not None:
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
    flags = []
    if summ['comb_bits']:
        flags.append('comb')
    if summ['out_over_bits']:
        flags.append('out_over')
    if summ['in_over_bits']:
        flags.append('in_over')
    if summ['min_delay_margin_ps'] is not None and summ['min_delay_margin_ps'] < thr:
        flags.append('min_delay')
    summ['clock_out_bits'] = sum(r['bits'] for r in buses.values() if r['dir'] == 'clock_out')
    if sc == 'ss':
        rec['note'] = (rec.get('note', '') + ' SS-only view (no TT lib): out/in are SS numbers against the TT budget').strip()
    rec.update(summary=summ, flags=flags, buses=buses)
    return rec


def severity(t):
    s = t.get('summary') or {}
    b = T_PS * 0.2
    over = max((s.get('worst_out_ps') or 0) - b, (s.get('worst_in_ps') or 0) - b, 0)
    return (-(s.get('comb_bits', 0) > 0), -round(over, 1), -(s.get('comb_bits', 0)), (s.get('min_delay_margin_ps') if s.get('min_delay_margin_ps') is not None else 1e9))


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
    for ln in open(D / 'place.tcl'):
        m = re.match(r'ot_mts::place \[\$_blk findInst (\S+)\] ([\d.]+) ([\d.]+) (\S+)', ln)
        if m:
            pos[m.group(1)] = (float(m.group(2)), float(m.group(3)), m.group(4))
    txt = (D / 'die.v').read_text()
    width = {m.group(2): int(m.group(1)) + 1 for m in re.finditer(r'wire \[(\d+):0\] (\S+);', txt)}
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
    ap.add_argument('--bind', action='append', help='die_views bind map (repeatable)')
    ap.add_argument('--census', help='S81 real-view census JSON (masters[].timing_libs)')
    ap.add_argument('--view', action='append', help='CELL=view dir (repeatable)')
    ap.add_argument('--alias', action='store_true', help='bind a same-family master view when no exact view exists')
    ap.add_argument('--case', help='Qwen die case dir (elements.lef, place.tcl, die.v)')
    ap.add_argument('--s81-opts', help='S81 generator options file')
    ap.add_argument('--s81-extra', default='--cfifo-colck')
    ap.add_argument('--budget-frac', type=float, default=0.2, help="the tile's share of T on each side of a seam")
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
    out = dict(schema='opentallas.pinreg_audit.v1', die=contract.get('die'), contract=a.contract,
               contract_version=contract.get('version'), source_commit=git('rev-parse', '--short=9', 'HEAD').strip(),
               rule=dict(budget_ps=round(a.budget_frac * T_PS, 1), budget_frac=a.budget_frac, reach_um=a.reach,
                         min_delay_ps=thr, hold_margin_ps=a.hold_margin, skew_ps=a.skew, period_ps=T_PS,
                         reading='tile share of the cycle: clock->pin <= 0.2 T after the insertion reference, pin->flop '
                                 '(setup at the pin + reference) <= 0.2 T; the die wire owns the remaining 0.6 T'),
               status=('PROVISIONAL: %d of %d audited views carry no corrected-export record (reexport_1013 / verdict check) '
                       'after the export-SDC fix (%s); their boundary numbers may be off by tens of ps'
                       % (prov, len(audited), EXPORT_FIX)) if prov else 'views post export-SDC fix',
               export_sdc=dict(corrected=len(audited) - prov, pre_fix=prov,
                               pre_fix_views=sorted({t['view'] for t in audited if t.get('exported_before_export_sdc_fix')})),
               counts=dict(contract_cells=len(tiles), audited=len(audited), not_auditable=len(tiles) - len(audited),
                           violating=len(viol), alias_bound=sum(1 for t in audited if (t['binding'] or '').startswith('ALIAS')),
                           by_flag=dict(collections.Counter(f for t in viol for f in t['flags'])),
                           instances_audited=sum(t['instances'] for t in audited),
                           instances_not_auditable=sum(t['instances'] for t in tiles if 'summary' not in t),
                           hops_over=hops['hops_over'] if hops else None),
               ranked_violations=[dict(rank=i + 1, cell=t['cell'], instances=t['instances'], flags=t['flags'], view=t['view'],
                                       binding=t['binding'], provisional=t.get('exported_before_export_sdc_fix'),
                                       setup_corner=t.get('setup_corner'),
                                       **{k: t['summary'][k] for k in ('comb_bits', 'out_over_bits', 'in_over_bits', 'worst_out_ps',
                                                                      'worst_out_bus', 'worst_in_ps', 'worst_in_bus', 'L_min_ps',
                                                                      'H_max_ps', 'min_delay_margin_ps', 'pins')})
                                  for i, t in enumerate(viol)],
               not_auditable=[dict(cell=t['cell'], instances=t['instances'], kinds=t['kinds']) for t in tiles if 'summary' not in t],
               cross_tile_min_delay=dict(note='potential pairs (connectivity between view cells is not resolved): '
                                              'L_min(src) - H_max(dst) < %.0f ps' % thr, pairs=len(cross), worst=cross[:40]),
               hops=hops, tiles=tiles)
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(out, indent=1) + '\n')
    L = [f"# Pin-register audit: {out['die']} (contract v{out['contract_version']}, {out['source_commit']})", '',
         f"Rule: clock->pin and pin->flop each <= {out['rule']['budget_ps']} ps (0.2 T), hop <= {a.reach:.0f} um, "
         f"L - H >= {thr:.0f} ps ({a.hold_margin:.0f} + skew {a.skew:.0f}).", '', f"**{out['status']}**", '',
         f"Cells {len(tiles)}: audited {len(audited)} ({out['counts']['instances_audited']} instances), violating {len(viol)} "
         f"{out['counts']['by_flag']}, not auditable {len(tiles) - len(audited)} ({out['counts']['instances_not_auditable']} instances), "
         f"alias-bound {out['counts']['alias_bound']}.", '',
         '| # | cell | inst | corner | flags | comb bits | out > B bits | worst out ps (bus) | in > B bits | worst in ps (bus) | L min | H max | L-H | binding |',
         '|---|---|---:|---|---|---:|---:|---|---:|---|---:|---:|---:|---|']
    for r in out['ranked_violations']:
        L.append(f"| {r['rank']} | {r['cell']} | {r['instances']} | {r['setup_corner']} | {' '.join(r['flags'])} | {r['comb_bits']} | {r['out_over_bits']} | "
                 f"{fmt(r['worst_out_ps']).strip()} ({r['worst_out_bus']}) | {r['in_over_bits']} | {fmt(r['worst_in_ps']).strip()} ({r['worst_in_bus']}) | "
                 f"{fmt(r['L_min_ps']).strip()} | {fmt(r['H_max_ps']).strip()} | {fmt(r['min_delay_margin_ps']).strip()} | {r['binding']} |")
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
    print('\n'.join(L[:8]))
    print(f"hops over {a.reach:.0f} um: {hops['hops_over'] if hops else 'n/a'}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
