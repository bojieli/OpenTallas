#!/usr/bin/env python3
"""Bit-level real-pin global-route case of ONE component namespace of the native HBM die candidate (v13).

There is no cross-component netlist yet, so the signal graph of the native die is the union of the components'
INTERNAL connections.  This tool takes one namespace instance of results/arch/hbm_native_1013/die_v13/candidate.json
(e.g. hb_attn_SW_0_lo, hb_attn_SW_0_hi, hb_vms_SW) and emits a k = 1 GRT case:

  gen      window = bbox of the namespace's children + margin (origin snapped to 8.64 um = a multiple of every ASAP7
           track pitch, the 0.27 row and the 0.432 / 2.16 placement grid, so track legality of the v13 origins is kept);
           children at their v13 xy / orientation, FIXED, with their REAL LEFs copied verbatim (no placeholder, no pin
           bundling, no generated pin); nets = the component `connections` expanded per bit, only nets with >= 2 child
           endpoints; every endpoint is checked against the LEF pin names (`port[i]`, or `port` for a scalar) and the
           case is REFUSED when one is absent.  Clock / reset / constant nets are listed and left out of the GRT.
  collect  log + gcell usage + wirelength -> receipt.json, grt_summary.txt, hotspots.txt (worst gcell bins per layer
           in window and die coordinates, nearest children, and the buses whose endpoint box covers the bin).

Conventions taken from the die GRT case generator (tools/hbm_accel_die_fp.py case_grt / case_real, tools/hbm_die_views.py
cmd_die / parse_case_log): place -> layer adjustments -> set_routing_layers -> `global_route -verbose -allow_congestion
-congestion_iterations N -congestion_report_file` -> `report_wire_length -net * -global_route` -> the S81 gcell dump
tail; layer adjustments M2 / M3 1.0, M4 / M5 = the die variant's grt_m45 (0.5) in channels, M6 / M7 = VIA_OBS (0.05);
overflow parsed from the last `^Total` line.
Differences (stated, not hidden):
  * an unconnected bit inside a partly connected bus gets a private one-pin wire u[i] (GRT skips degree-1 nets), not
    the 1'bz of hbm_accel_die_fp.write_netlist: OpenROAD 26Q3 ties every 1'bz to ONE net `zero_` (measured here: 1,472
    / 2,448 terminals on the attention lo / VM slice), which would join unrelated open pins into a fabricated net;
  * k = 1 with the platform tech LEF / make_tracks.tcl (as case_real), not the bundled tech LEF of case_grt (k >= 8);
  * signal layers M2-M7, not M2-M9: the hierarchy contract keeps M8 / M9 for die power / global;
  * blocks are NOT blocked by region adjustments over their outlines: every child's own LEF OBS decides;
  * place_macro -exact (as die_v13/placement.tcl) instead of place_inst, and a moved-origin check after placement.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CAND = 'results/arch/hbm_native_1013/die_v13/candidate.json'
PLAT = '/OpenROAD-flow-scripts/flow/platforms/asap7'      # tools/dsrom_s81_fulldie.py PLAT
VIA_OBS = 0.05                                             # tools/dsrom_s81_fulldie.py VIA_OBS
GRT_M45 = 0.5                                              # tools/hbm_accel_die_fp.py R25GQ_V8 grt_m45
SNAP = 8.64
CLOCK_RESET_PORTS = {'clk', 'ck', 'rst_n', 'rst', 'rstn'}
OUT = 'results/physical/hbm_native_v13_grt'


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def esc(n):
    return n if re.match(r'^[A-Za-z_][A-Za-z0-9_]*$', n) else '\\' + n + ' '


def lef_pins(text):
    """{pin: (direction, use, layers)} of the single MACRO of a view LEF, and its size."""
    pins = {}
    for m in re.finditer(r'^\s*PIN (\S+)\n(.*?)^\s*END \1\s*$', text, re.S | re.M):
        b = m.group(2)
        d = re.search(r'DIRECTION (\w+)', b)
        u = re.search(r'USE (\w+)', b)
        pins[m.group(1)] = (d.group(1) if d else 'INOUT', u.group(1) if u else 'SIGNAL',
                            sorted(set(re.findall(r'LAYER (\S+)', b))))
    w, h = re.search(r'SIZE (\S+) BY (\S+)', text).groups()
    macros = re.findall(r'^MACRO (\S+)', text, re.M)
    return pins, float(w), float(h), macros


def git(*a):
    return subprocess.run(['git', '-C', str(ROOT), *a], capture_output=True, text=True, check=True).stdout.strip()


def cmd_gen(a):
    cand_p = ROOT / CAND
    cand = json.loads(cand_p.read_text())
    ns = a.namespace
    nmap = next((x for x in cand['functional_namespace_maps'] if x['namespace'] == ns), None)
    if nmap is None:
        sys.exit(f'REFUSE: namespace {ns} is not in the candidate')
    comp_p = ROOT / nmap['component_path']
    if sha(comp_p) != nmap['component_sha256']:
        sys.exit(f'REFUSE: {nmap["component_path"]} sha256 differs from the candidate binding')
    comp = json.loads(comp_p.read_text())
    rows = [c for c in cand['children'] if c.get('component_namespace') == ns]
    nolef = [c['instance'] for c in rows if not c.get('view_lef')]
    if nolef:
        sys.exit(f'REFUSE: {len(nolef)} children of {ns} have no real LEF (e.g. {nolef[0]}); no placeholder is generated')
    by_child = {c['component_child']: c for c in rows}
    comp_children = {c['instance'] for c in comp['children']}
    if set(by_child) != comp_children:
        sys.exit(f'REFUSE: candidate children and component children differ: {sorted(set(by_child) ^ comp_children)[:5]}')

    work = Path(a.work).resolve()
    (work / 'lef').mkdir(parents=True, exist_ok=True)
    lefs, masters = {}, {}
    for c in rows:
        rel = c['view_lef']
        if rel in lefs:
            continue
        t = (ROOT / rel).read_text()
        pins, w, h, macros = lef_pins(t)
        if macros != [c['logical_module']]:
            sys.exit(f'REFUSE: {rel} defines {macros}, child master is {c["logical_module"]}')
        (work / 'lef' / Path(rel).name).write_text(t)
        lefs[rel] = dict(file=Path(rel).name, sha256=sha(ROOT / rel), macro=macros[0], w_um=w, h_um=h,
                         pins=len(pins), obs_layers=sorted(set(re.findall(r'LAYER (\S+)', t[t.find('\n  OBS'):])))
                         if '\n  OBS' in t else [])
        masters[macros[0]] = (pins, w, h)

    # ---- window
    def dims(c):
        _, w, h = masters[c['logical_module']]
        return (w, h) if c['orientation'] in ('R0', 'R180', 'MX', 'MY') else (h, w)
    for c in rows:
        if c['orientation'] not in ('R0', 'MX', 'MY', 'R180'):
            sys.exit(f'REFUSE: orientation {c["orientation"]} of {c["instance"]}')
    x0 = min(c['xy_um'][0] for c in rows)
    y0 = min(c['xy_um'][1] for c in rows)
    x1 = max(c['xy_um'][0] + dims(c)[0] for c in rows)
    y1 = max(c['xy_um'][1] + dims(c)[1] for c in rows)
    import math
    ox = math.floor((x0 - a.margin) / SNAP + 1e-9) * SNAP
    oy = math.floor((y0 - a.margin) / SNAP + 1e-9) * SNAP
    W = math.ceil((x1 + a.margin - ox) / SNAP - 1e-9) * SNAP
    H = math.ceil((y1 + a.margin - oy) / SNAP - 1e-9) * SNAP

    # ---- pins
    def pin_of(child, port, idx, scalar_ok):
        pins = masters[by_child[child]['logical_module']][0]
        n = f'{port}[{idx}]'
        if n in pins:
            return n
        if scalar_ok and idx == 0 and port in pins:
            return port
        return None

    missing, routed, clockreset, const_pins = [], [], [], set()
    pin_net = {}
    buses = []
    for cn in comp['connections']:
        eps = [e for e in cn['endpoints'] if e['instance'] != '$boundary']
        has_b = len(eps) != len(cn['endpoints'])
        width = cn['endpoints'][0]['width']
        if any(e['width'] != width for e in cn['endpoints']):
            sys.exit(f'REFUSE: connection {cn["net"]} has endpoints of different widths')
        kind = cn.get('kind')
        is_cr = kind in ('clock', 'reset') or all(e['port'] in CLOCK_RESET_PORTS for e in eps)
        if kind == 'constant':
            for e in eps:
                for j in range(width):
                    p = pin_of(e['instance'], e['port'], e['lsb'] + j, width == 1)
                    if p is None:
                        missing.append((cn['net'], e['instance'], e['port'], e['lsb'] + j))
                    else:
                        const_pins.add((e['instance'], p))
            continue
        bus_bits = 0
        for j in range(width):
            bit = []
            for e in eps:
                p = pin_of(e['instance'], e['port'], e['lsb'] + j, width == 1)
                if p is None:
                    missing.append((cn['net'], e['instance'], e['port'], e['lsb'] + j))
                else:
                    bit.append((e['instance'], p))
            if is_cr:
                clockreset.append((cn['net'], j, bit, has_b))
            elif len(bit) >= 2:
                name = f'{cn["net"]}[{j}]'
                routed.append((name, bit, has_b))
                bus_bits += 1
                for k_ in bit:
                    if k_ in pin_net:
                        sys.exit(f'REFUSE: pin {k_} is on {pin_net[k_]} and {name}')
                    pin_net[k_] = len(routed) - 1
        if bus_bits:
            buses.append(dict(net=cn['net'], bits=bus_bits, also_boundary=has_b,
                              endpoints=[dict(child=e['instance'], port=e['port'], lsb=e['lsb']) for e in eps]))
    for k_ in comp.get('constants', []):
        for j in range(k_['width']):
            p = pin_of(k_['instance'], k_['port'], j, k_['width'] == 1)
            if p is None:
                missing.append(('$constant', k_['instance'], k_['port'], j))
            else:
                const_pins.add((k_['instance'], p))
    bound_pins = set()
    for b in comp.get('boundary_binding', []):
        for j in range(b['width']):
            p = pin_of(b['child_instance'], b['child_port'], b['child_lsb'] + j, b['width'] == 1)
            if p is None:
                missing.append(('$boundary:' + b['parent_port'], b['child_instance'], b['child_port'], b['child_lsb'] + j))
            else:
                bound_pins.add((b['child_instance'], p))
    for cn in comp['connections']:
        if cn.get('kind') == 'constant':
            continue
        eps = [e for e in cn['endpoints'] if e['instance'] != '$boundary']
        if len(eps) == 1:
            e = eps[0]
            for j in range(e['width']):
                p = pin_of(e['instance'], e['port'], e['lsb'] + j, e['width'] == 1)
                if p is not None:
                    bound_pins.add((e['instance'], p))
    unused = set()
    for u in comp.get('unused_outputs', []):
        for j in range(u['width']):
            p = pin_of(u['instance'], u['port'], j, u['width'] == 1)
            if p is not None:
                unused.add((u['instance'], p))
    cr_pins = {k_ for _, _, bit, _ in clockreset for k_ in bit}
    miss_rec = dict(count=len(missing), by_master_port=dict(Counter(
        f'{by_child[i]["logical_module"]}.{p}' for _, i, p, _ in missing).most_common(40)),
        first=[dict(net=n, child=i, port=p, bit=b) for n, i, p, b in missing[:20]])
    if missing and not a.allow_missing:
        (work / 'REFUSED.json').write_text(json.dumps(miss_rec, indent=1))
        sys.exit(f'REFUSE: {len(missing)} endpoint bits have no pin in the child LEF: {json.dumps(miss_rec["by_master_port"])}')

    cls = Counter()
    for ch, c in by_child.items():
        for p, (d, u, _) in masters[c['logical_module']][0].items():
            k_ = (ch, p)
            if u in ('POWER', 'GROUND'):
                cls['power_ground'] += 1
            elif k_ in pin_net:
                cls['routed'] += 1
            elif k_ in cr_pins or (u == 'CLOCK'):
                cls['clock_reset_excluded'] += 1
            elif k_ in const_pins:
                cls['constant_tied_excluded'] += 1
            elif k_ in bound_pins:
                cls['boundary_only_unconnected'] += 1
            elif k_ in unused:
                cls['declared_unused_output'] += 1
            else:
                cls['unlisted_unconnected'] += 1

    # ---- netlist (bus concatenation as hbm_accel_die_fp.write_netlist; open bits on private wires)
    V = [f'// tools/hbm_native_component_grt_1013.py: {ns} internal bit nets (k = 1, real pins)', 'module nat_win ();']
    V.append(f'  wire [{max(len(routed) - 1, 0)}:0] n;')
    n_open = 0
    uidx = len(V)
    V.append('')
    for ch in sorted(by_child):
        c = by_child[ch]
        pins = masters[c['logical_module']][0]
        bus, parts = defaultdict(dict), []
        for p in pins:
            if (ch, p) not in pin_net:
                continue
            net = f'n[{pin_net[(ch, p)]}]'
            m = re.match(r'^(.*)\[(\d+)\]$', p)
            if m:
                bus[m.group(1)][int(m.group(2))] = net
            else:
                parts.append(f'.{esc(p)}({net})')
        for base, bits in sorted(bus.items()):
            idx = sorted(int(re.match(r'^.*\[(\d+)\]$', p).group(1)) for p in pins if p.startswith(base + '[')
                         and re.fullmatch(re.escape(base) + r'\[\d+\]', p))
            if idx != list(range(len(idx))):
                sys.exit(f'REFUSE: LEF bus {c["logical_module"]}.{base} is not contiguous from 0')
            cat = []
            for j in range(len(idx) - 1, -1, -1):
                if j in bits:
                    cat.append(bits[j])
                else:           # a private one-pin wire per unconnected bit (see the docstring: not 1'bz)
                    cat.append(f'u[{n_open}]')
                    n_open += 1
            cat = ', '.join(cat)
            parts.append(f'.{esc(base)}({{{cat}}})')
        V.append(f'  {c["logical_module"]} {c["instance"]} (' + ', '.join(parts) + ');')
    V[uidx] = f'  wire [{max(n_open - 1, 0)}:0] u;'
    V.append('endmodule\n')
    (work / 'die.v').write_text('\n'.join(V))

    place = [f'fplace {c["instance"]} {c["xy_um"][0] - ox:.3f} {c["xy_um"][1] - oy:.3f} {c["orientation"]}'
             for c in rows]
    adj = [f'set_global_routing_layer_adjustment {ln} {v:.4f}' for ln, v in
           (('M2', 1.0), ('M3', 1.0), ('M4', GRT_M45), ('M5', GRT_M45), ('M6', VIA_OBS), ('M7', VIA_OBS))]
    src = (ROOT / 'tools/dsrom_s81_fulldie.py').read_text()
    gtail = re.search(r'tcl \+= r"""\n(set blk \[ord::get_db_block\].*?mem done\n)"""', src, re.S).group(1)
    gtail = gtail.replace('foreach ln {M2 M3 M4 M5 M6 M7 M8 M9}', 'foreach ln {M2 M3 M4 M5 M6 M7}')
    assert 'foreach ln {M2 M3 M4 M5 M6 M7}' in gtail
    lef_read = '\n'.join(f'read_lef /work/lef/{v["file"]}' for v in lefs.values())
    tcl = f"""# native v13 component GRT: {ns}, bit-level real pins (k = 1), window origin ({ox:.3f}, {oy:.3f}) um of the die
proc mem {{tag}} {{ set f [open /proc/self/status]; set s [read $f]; close $f
  regexp {{VmRSS:\\s+(\\d+)}} $s -> r; puts "OTMEM $tag [expr {{$r/1024}}] MB [clock seconds]" }}
read_lef {PLAT}/lef/asap7_tech_1x_201209.lef
read_lef {PLAT}/lef/asap7sc7p5t_28_R_1x_220121a.lef
{lef_read}
read_verilog /work/die.v
link_design nat_win
initialize_floorplan -die_area {{0 0 {W:.3f} {H:.3f}}} -core_area {{0 0 {W:.3f} {H:.3f}}} -site asap7sc7p5t
source {PLAT}/openRoad/make_tracks.tcl
set ::env(MAKE_TRACKS) {PLAT}/openRoad/make_tracks.tcl
set ot_moved 0
proc fplace {{nm x y o}} {{
  place_macro -macro_name $nm -location [list $x $y] -orientation $o -exact
  set i [[ord::get_db_block] findInst $nm]
  set bb [$i getBBox]
  set px [expr {{[$bb xMin] / 1000.0}}]; set py [expr {{[$bb yMin] / 1000.0}}]
  if {{abs($px - $x) > 0.0005 || abs($py - $y) > 0.0005 || [$i getOrient] ne $o}} {{
    incr ::ot_moved; if {{$::ot_moved < 20}} {{ puts "OT_MOVED $nm want $x $y $o got $px $py [$i getOrient]" }} }}
  $i setPlacementStatus FIRM
}}
set t0 [clock seconds]
source /work/place.tcl
puts "OT_TIME place_s=[expr {{[clock seconds]-$t0}}]"
set blk [ord::get_db_block]
set boxes {{}}
foreach inst [$blk getInsts] {{
  set bb [$inst getBBox]
  lappend boxes [list [$bb xMin] [$bb yMin] [$bb xMax] [$bb yMax] [$inst getName]]
}}
set boxes [lsort -integer -index 0 $boxes]
set n [llength $boxes]; set ov 0; set out 0
set dw [[$blk getDieArea] xMax]; set dh [[$blk getDieArea] yMax]
set active {{}}
foreach b $boxes {{
  lassign $b x0 y0 x1 y1 nm
  if {{$x0 < 0 || $y0 < 0 || $x1 > $dw || $y1 > $dh}} {{ incr out; if {{$out < 20}} {{ puts "OT_OUTSIDE $nm" }} }}
  set keep {{}}
  foreach a $active {{
    lassign $a ax0 ay0 ax1 ay1 an
    if {{$ax1 > $x0}} {{
      lappend keep $a
      if {{$ay0 < $y1 && $y0 < $ay1}} {{ incr ov; if {{$ov < 50}} {{ puts "OT_OVERLAP $an $nm" }} }}
    }}
  }}
  lappend keep $b
  set active $keep
}}
puts "OT_LEGAL instances=$n overlaps=$ov outside=$out moved=$ot_moved"
{chr(10).join(adj)}
set_routing_layers -signal M2-M7
set t0 [clock seconds]
mem pre_grt
global_route -verbose -allow_congestion -congestion_iterations {a.iters} -congestion_report_file /work/grt_congestion.rpt
puts "OT_TIME grt_s=[expr {{[clock seconds]-$t0}}]"
mem grt
report_wire_length -net * -global_route -file /work/wirelength.csv
""" + gtail
    (work / 'place.tcl').write_text('\n'.join(place) + '\n')
    (work / 'run.tcl').write_text(tcl)
    (work / 'nets.json').write_text(json.dumps(dict(
        buses=buses, children={c['component_child']: dict(
            instance=c['instance'], master=c['logical_module'], orient=c['orientation'],
            rect=[round(c['xy_um'][0] - ox, 3), round(c['xy_um'][1] - oy, 3),
                  round(c['xy_um'][0] - ox + dims(c)[0], 3), round(c['xy_um'][1] - oy + dims(c)[1], 3)]) for c in rows})))
    tool = Path(__file__).resolve()
    dirty = git('status', '--porcelain', '--', str(tool.relative_to(ROOT)), CAND, nmap['component_path'])
    man = dict(
        schema='opentallas.hbm.native_component_grt.v1', case=a.case or ns, namespace=ns,
        source_commit=git('rev-parse', 'HEAD'), source_dirty=bool(dirty),
        tool=dict(path=str(tool.relative_to(ROOT)), sha256=sha(tool)),
        candidate=dict(path=CAND, sha256=sha(cand_p), variant=cand['variant']),
        component=dict(path=nmap['component_path'], sha256=nmap['component_sha256']),
        window=dict(die_origin_um=[round(ox, 3), round(oy, 3)], size_um=[round(W, 3), round(H, 3)],
                    children_bbox_die_um=[round(v, 3) for v in (x0, y0, x1, y1)], margin_um=a.margin, snap_um=SNAP),
        counts=dict(instances=len(rows), masters=len(masters), bit_nets=len(routed),
                    bit_net_pins=sum(len(b) for _, b, _ in routed), buses=len(buses),
                    bit_nets_also_on_boundary=sum(1 for _, _, hb in routed if hb),
                    clock_reset_nets=len(clockreset), clock_reset_pins=len(cr_pins),
                    missing_lef_pins=len(missing), signal_pin_classes=dict(cls)),
        missing_lef_pins=miss_rec,
        clock_reset_nets=[dict(net=n, bit=j, pins=len(b), boundary=hb) for n, j, b, hb in clockreset][:64],
        pin_name_convention='LEF BUSBITCHARS "[]": bus bit = port[i]; scalar port = port (no index)',
        grt=dict(signal_layers='M2-M7', layer_adjustment=dict(M2=1.0, M3=1.0, M4=GRT_M45, M5=GRT_M45, M6=VIA_OBS,
                                                               M7=VIA_OBS),
                 congestion_iterations=a.iters, tech='platform asap7_tech_1x_201209.lef + make_tracks.tcl (k = 1)',
                 block_blockage="each child's own LEF OBS (no region adjustment)", m8_m9='not used for signals'),
        lefs=lefs)
    (work / 'manifest.json').write_text(json.dumps(man, indent=1))
    print(json.dumps(dict(case=man['case'], work=str(work), window=man['window'], counts=man['counts'])))


LAYER_RE = r'^(M\d|Total)\s+(\d+)\s+(\d+)\s+([\d.]+)%\s+(\d+) /\s+(\d+) /\s+(\d+)'


def cmd_collect(a):
    work = Path(a.work)
    man = json.loads((work / 'manifest.json').read_text())
    nets = json.loads((work / 'nets.json').read_text())
    out = ROOT / OUT / man['case']
    out.mkdir(parents=True, exist_ok=True)
    log = (work / 'run.log').read_text(errors='replace')
    res = {}
    exitf = work / 'run.log.exit'
    res['exit_code'] = int(exitf.read_text().strip()) if exitf.exists() else None
    m = re.search(r'OT_LEGAL instances=(\d+) overlaps=(\d+) outside=(\d+) moved=(\d+)', log)
    if m:
        res.update(placed_instances=int(m.group(1)), overlaps=int(m.group(2)), outside=int(m.group(3)),
                   moved_by_place_macro=int(m.group(4)))
    rows = re.findall(LAYER_RE, log, re.M)
    # the last table of the log (final congestion report)
    last = {}
    for r in rows:
        last[r[0]] = dict(capacity=int(r[1]), demand=int(r[2]), usage_pct=float(r[3]), overflow_h=int(r[4]),
                          overflow_v=int(r[5]), overflow=int(r[6]))
    if 'Total' in last:
        res['overflow_total'] = last['Total']['overflow']
        res['per_layer'] = last
    for k in ('place_s', 'grt_s'):
        mm = re.search(r'OT_TIME ' + k + r'=(\d+)', log)
        if mm:
            res[k] = int(mm.group(1))
    mm = re.search(r'Maximum resident set size \(kbytes\): (\d+)', log)
    if mm:
        res['peak_rss_gb'] = round(int(mm.group(1)) / 1048576, 2)
    mm = re.search(r'Elapsed \(wall clock\) time \(h:mm:ss or m:ss\): (\S+)', log)
    if mm:
        p = [float(v) for v in mm.group(1).split(':')]
        res['wall_s'] = round(sum(v * 60 ** i for i, v in enumerate(reversed(p))), 1)
    res['log_errors'] = re.findall(r'^\[ERROR[^\n]*', log, re.M)[:10] + re.findall(r'^Error: [^\n]*', log, re.M)[:5]
    wc = Counter(re.findall(r'^\[WARNING (\S+)\]', log, re.M))
    res['log_warnings'] = dict(wc.most_common(12))
    mm = re.search(r'Total wirelength: (\d+) um', log)
    if mm:
        res['grt_total_wirelength_um'] = int(mm.group(1))
    wl = work / 'wirelength.csv'
    if wl.exists():
        tot, mx, mxn, n = 0.0, 0.0, None, 0
        hdr = None
        for ln in wl.read_text().splitlines():
            f = ln.split(',')
            if hdr is None:
                hdr = f
                continue
            try:
                v = float(f[1])
            except (ValueError, IndexError):
                continue
            n += 1
            tot += v
            if v > mx:
                mx, mxn = v, f[0]
        res.update(wirelength_csv=dict(header=hdr, nets=n, total_um=round(tot, 1), max_net_um=round(mx, 2), max_net=mxn))
    summ = [ln for ln in log.splitlines() if re.match(r'^(Layer|M\d|Total|-{20,}|\[INFO GRT-00(96|97|98|18|12)\]|OT_|OTMEM)', ln)]
    (out / 'grt_summary.txt').write_text('\n'.join(summ[-80:]) + '\n')

    # ---- hot spots: 4x4 gcell bins of the S81 gcell dump (cap/use per layer)
    gu = work / 'gcell_usage.txt'
    hot_txt = []
    if gu.exists():
        gx = gy = None
        bins = []
        with gu.open() as f:
            for ln in f:
                if ln.startswith('GRIDX'):
                    gx = [int(v) for v in ln.split()[1].split(',')]
                elif ln.startswith('GRIDY'):
                    gy = [int(v) for v in ln.split()[1].split(',')]
                elif ln.startswith('L '):
                    p = ln.split()
                    ly, j = p[1], int(p[2])
                    for bi, cu in enumerate(p[3:]):
                        c_, u_ = cu.split('/')
                        c_, u_ = int(c_), int(u_)
                        if u_ > c_:
                            bins.append((u_ - c_, ly, bi * 4, j, c_, u_))
        ox, oy = man['window']['die_origin_um']
        ch = nets['children']
        per_layer = Counter()
        for b in bins:
            per_layer[b[1]] += b[0]
        res['overflow_bins'] = dict(bins_over=len(bins), excess_tracks_by_layer=dict(per_layer),
                                    note='4x4-gcell bins with usage > capacity (sum over the bin; sub-bin overflow '
                                         'can hide inside a bin whose sum fits)')
        bins.sort(reverse=True)
        hot = []

        def rect_of(i, j):
            x0 = gx[i] / 1000.0
            y0 = gy[j] / 1000.0
            x1 = gx[min(i + 4, len(gx) - 1)] / 1000.0 if i + 4 < len(gx) else man['window']['size_um'][0]
            y1 = gy[min(j + 4, len(gy) - 1)] / 1000.0 if j + 4 < len(gy) else man['window']['size_um'][1]
            return x0, y0, x1, y1

        def dist(r, q):
            dx = max(q[0] - r[2], r[0] - q[2], 0)
            dy = max(q[1] - r[3], r[1] - q[3], 0)
            return (dx * dx + dy * dy) ** 0.5
        for ex, ly, i, j, c_, u_ in bins[:a.top]:
            r = rect_of(i, j)
            near = sorted((round(dist(r, v['rect']), 2), k) for k, v in ch.items())[:3]
            cover = []
            for bu in nets['buses']:
                rs = [ch[e['child']]['rect'] for e in bu['endpoints']]
                bx = (min(q[0] for q in rs), min(q[1] for q in rs), max(q[2] for q in rs), max(q[3] for q in rs))
                if bx[0] <= r[2] and bx[2] >= r[0] and bx[1] <= r[3] and bx[3] >= r[1]:
                    cover.append((bu['bits'], bu['net'], ' <-> '.join(f'{e["child"]}.{e["port"]}' for e in bu['endpoints'])))
            cover.sort(reverse=True)
            hot.append(dict(layer=ly, excess=ex, capacity=c_, usage=u_, window_rect_um=[round(v, 3) for v in r],
                            die_rect_um=[round(r[0] + ox, 3), round(r[1] + oy, 3), round(r[2] + ox, 3), round(r[3] + oy, 3)],
                            nearest_children=[dict(child=k, dist_um=d) for d, k in near],
                            covering_buses=[dict(bits=b_, net=n_, endpoints=e_) for b_, n_, e_ in cover[:4]]))
        res['hotspots'] = hot[:10]
        for h in hot:
            hot_txt.append(f'{h["layer"]} excess {h["excess"]} (use {h["usage"]} / cap {h["capacity"]}) window '
                           f'{h["window_rect_um"]} die {h["die_rect_um"]}\n   nearest: '
                           + '; '.join(f'{n_["child"]} ({n_["dist_um"]} um)' for n_ in h['nearest_children'])
                           + '\n   buses: ' + ' | '.join(f'{b_["net"]} x{b_["bits"]} {b_["endpoints"]}' for b_ in h['covering_buses']))
        # coarse map: excess per layer on a 16 x 12 grid of the window
        Wd, Hd = man['window']['size_um']
        for ly in sorted(per_layer):
            g = [[0] * 16 for _ in range(12)]
            for ex, l2, i, j, _, _ in bins:
                if l2 == ly:
                    g[min(11, int(gy[j] / 1000.0 / Hd * 12))][min(15, int(gx[i] / 1000.0 / Wd * 16))] += ex
            hot_txt.append(f'MAP {ly} excess tracks, 16 x 12 cells of the {Wd} x {Hd} um window (top row = max y)')
            hot_txt += ['   ' + ' '.join(f'{v:7d}' for v in row) for row in reversed(g)]
    cg = work / 'grt_congestion.rpt'
    if cg.exists():
        res['congestion_rpt_violations'] = len(re.findall(r'^violation type', cg.read_text(errors='replace'), re.M))
    (out / 'hotspots.txt').write_text('\n'.join(hot_txt) + '\n')
    rec = dict(man)
    rec.pop('lefs_text', None)
    rec['remote'] = a.remote
    rec['result'] = res
    (out / 'receipt.json').write_text(json.dumps(rec, indent=1) + '\n')
    print(json.dumps(dict(case=man['case'], **{k: v for k, v in res.items() if k not in ('per_layer', 'hotspots')})))


def main():
    ap = argparse.ArgumentParser()
    sp = ap.add_subparsers(dest='cmd', required=True)
    g = sp.add_parser('gen')
    g.add_argument('--namespace', required=True)
    g.add_argument('--case')
    g.add_argument('--work', required=True)
    g.add_argument('--margin', type=float, default=21.6)
    g.add_argument('--iters', type=int, default=50)
    g.add_argument('--allow-missing', action='store_true', help='diagnostic only: do not refuse on absent LEF pins')
    g.set_defaults(fn=cmd_gen)
    c = sp.add_parser('collect')
    c.add_argument('--work', required=True)
    c.add_argument('--remote', default=None)
    c.add_argument('--top', type=int, default=24)
    c.set_defaults(fn=cmd_collect)
    a = ap.parse_args()
    a.fn(a)


if __name__ == '__main__':
    main()
