#!/usr/bin/env python3
"""frame_hier_kit.py -- S81 frame MAIN (b2): hard row bands under a level-3 (M8-passthrough) frame top.

  frame_hier_kit.py --master col_h9 --tag vgch --base-kit s81frame_col_h9_vgc --cuts 552.96,1166.4,1632.96,2246.4,2756.16

1. RTL: frame_hier_part.py splits the bound vector-landed kit RTL (and its bench twin) into band modules <top>_b<k> + the
   wiring top (same module name / params / ports; flattened netlist = the input).
2. One ref_tile kit per band (cluster_level 2: the q element / bf_col children keep PG M7, the band PG = M8 on the die
   grid).  Band k spans frame y [cut_k, cut_k+1); b0 is full width (it owns every frame data port on the E face), b1..b5
   leave a CHANNEL_UM E channel to the frame top (clock ports, the lpr_root reset run).  Abutting faces carry the band
   crossing nets at identical x (io_tcl, exact tracks); b0's E pins are the frame's own pins at their frame coordinates.
3. The frame top kit (cluster_level 3, PG = the bands' M8 stripes passed through) is written by --frame-top once the
   band views exist.
"""
import argparse, collections, hashlib, json, re, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'tools/s81_dv'), str(ROOT / 'tools/landed_parent')]
import lp  # noqa: E402
import frame_vg_kit as V  # noqa: E402

CHANNEL_UM = 0.0      # 3 full-width bands: rows abut, clocks enter each band's E face at the frame pin, lpr_root is fed through
PITCH = {"M3": 0.036, "M4": 0.048, "M5": 0.048, "M6": 0.064}
OFF = {"M3": 0.009, "M5": 0.012, "M4": 0.012, "M6": 0.016}
SIZE = {"M3": (0.018, 0.144), "M5": (0.024, 0.192), "M4": (0.192, 0.024), "M6": (0.192, 0.032)}
FRAME_PORTS = ('lk', 'rst_n', 'xo', 'xok', 'xk', 'x', 'ret')
CLOCKS = ('ck_r0', 'ck_r1', 'ck_r2')


def snap(v, layer):
    p, o = PITCH[layer], OFF[layer]
    return round(o + round((v - o) / p) * p, 4)


def module_ports(text, name):
    m = lp.parse_module(text, name)
    out = []
    for p in m['ports']:
        w = 1
        if p['range']:
            hi, lo = p['range'].strip('[]').split(':')
            w = abs(int(hi) - int(lo)) + 1
        out.append((p['name'], p['dir'], w, bool(p['range'])))
    return out


def bits(name, w, vec):
    return [f'{name}[{i}]' for i in range(w)] if vec else [name]


def positions(kit_spec, kit_rtl, top, iters=80):
    """(x, y) per instance of the flat kit RTL: hard children / macros at their centre; others relaxed to neighbours."""
    pos = {}
    for c in kit_spec['children'] + kit_spec['macros']:
        w, h = V.lef_size(c['view'])
        pos[c['inst'].split('.')[0]] = (c['at'][0] + w / 2, c['at'][1] + h / 2)
    text = lp.preprocess((ROOT / kit_rtl).read_text(), kit_spec.get('defines'))
    mod = lp.parse_module(text, top)
    _, _, insts = lp.parse_body(mod['body'])
    nets = collections.defaultdict(set)
    conns = {}
    for i in insts:
        conns[i['inst']] = i['conns']
        for pin, e in i['conns'].items():
            if pin in ('ck', 'clk', 'cr', 'cr_s'):
                continue
            for n in lp.idents(e):
                nets[n].add(i['inst'])
    nb = collections.defaultdict(list)
    for ks in nets.values():
        if len(ks) <= 40:
            for a in ks:
                nb[a] += [b for b in ks if b != a]
    W, H = kit_spec['outline']['w'], kit_spec['outline']['h']
    soft = [i['inst'] for i in insts if i['inst'] not in pos]
    for s in soft:
        pos[s] = (W / 2, H / 2)
    for _ in range(iters):
        for s in soft:
            ps = [pos[b] for b in nb[s]]
            if ps:
                pos[s] = (sum(p[0] for p in ps) / len(ps), sum(p[1] for p in ps) / len(ps))
    return pos, nets


def legal_spread(want, lo, hi, layers, step):
    """want: [(key, x)] -> {key: (x, layer)}: sorted by wanted x, min spacing `step`, inside [lo, hi], alternating layers"""
    want = sorted(want, key=lambda t: t[1])
    n = len(want)
    if n == 0:
        return {}
    if n * step > hi - lo:
        raise SystemExit(f'{n} pins do not fit in [{lo}, {hi}] at step {step}')
    xs = [min(max(x, lo), hi) for _, x in want]
    # forward pass (min spacing), backward pass (upper bound), forward again
    for i in range(1, n):
        xs[i] = max(xs[i], xs[i - 1] + step)
    xs[-1] = min(xs[-1], hi)
    for i in range(n - 2, -1, -1):
        xs[i] = min(xs[i], xs[i + 1] - step)
    xs[0] = max(xs[0], lo)
    for i in range(1, n):
        xs[i] = max(xs[i], xs[i - 1] + step)
    out = {}
    for i, (k, _) in enumerate(want):
        L = layers[i % len(layers)]
        out[k] = (snap(xs[i], L), L)
    return out


def place_line(pin, layer, x, y):
    w, h = SIZE[layer]
    return f'place_pin -pin_name {{{pin}}} -layer {layer} -location {{{x:.4f} {y:.4f}}} -pin_size {{{w} {h}}} -force_to_die_boundary'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--master', required=True)
    ap.add_argument('--tag', required=True)
    ap.add_argument('--base-kit', required=True)
    ap.add_argument('--cuts', required=True, help='band assignment cuts (base-kit y, by instance centre)')
    ap.add_argument('--edges', required=True, help='physical band edges after --shift (frame y), one per cut')
    ap.add_argument('--why', default='')
    ap.add_argument('--shift', default='', help='y0:dy,...: hard children with frame y >= y0 move up by dy (cumulative '
                    'thresholds; opens >= 44.3-um band seams: 2 x (core margin 2.16 + 20-um pin edge))')
    a = ap.parse_args()
    m, tag = a.master, a.tag
    cuts = [float(c) for c in a.cuts.split(',')]
    shifts = sorted((float(t), float(d)) for t, d in (x.split(':') for x in a.shift.split(',') if x))
    base = json.loads((ROOT / 'physical/ref_tile' / a.base_kit / 'spec.json').read_text())
    W, H = base['outline']['w'], base['outline']['h']
    bounds = [0.0] + [float(e) for e in a.edges.split(',')] + [H]
    nb = len(bounds) - 1
    top = base['top']
    kit_old = next(f for f in base['sources'] if '/kit/' in f and '_l4_lp_kit' in f)
    src_tag = re.search(r'_l4_lp_kit_(\w+)\.sv$', kit_old).group(1)
    twin_old = base['frame']['lp_rtl'].replace('_l4_lp.sv', '_l4_lp_rf3r.sv')
    # ---- band of every original child (by kit centre y; soft relays relaxed)
    lps = json.loads((ROOT / V.REC / src_tag / f'{m}_spec.json').read_text())
    lps['_spec_path'] = 'x'
    iy, _ = V.inst_y(base, lps)          # the same y the vgc region re-cut used
    band_of = lambda y: sum(y >= c for c in cuts)
    regions = lps['regions']
    reg = {i: r['name'] for r in regions for i in r['insts']}
    inst_band = {i: band_of(iy[i]) for i in reg}
    # every band must sit in one lp region (the band shares that region's clock port)
    b_reg = collections.defaultdict(set)
    for i, b in inst_band.items():
        b_reg[b].add(reg[i])
    if any(len(v) != 1 for v in b_reg.values()):
        raise SystemExit(f'a band spans two lp regions: { {b: sorted(v) for b, v in b_reg.items()} }')
    core = inst_band['u_cf']
    force = {k: core for k in ('u_frl_rst', 'u_xrl0', 'u_xrl1', 'u_xrl2', 'u_xrl3', 'u_lpr_root')}
    hd = ROOT / V.REC / tag
    hd.mkdir(parents=True, exist_ok=True)
    (hd / f'{m}_bands.json').write_text(json.dumps(dict(inst=inst_band, force=force, cuts=cuts), indent=0))
    srcs = [f for f in json.loads((ROOT / V.REC / src_tag / f'{m}_spec.json').read_text())['child_sources'] + base['sources']
            if f.endswith(('.sv', '.v')) and (ROOT / f).exists()]
    kit_new = f'{V.LPDIR}/kit/{m}_l4_lp_kit_{tag}.sv'
    twin_new = f'{V.LPDIR}/{tag}/{m}_l4_lp_rf3r.sv'
    (ROOT / V.LPDIR / tag).mkdir(parents=True, exist_ok=True)
    rep = {}
    for src, dst, key in ((kit_old, kit_new, 'kit'), (twin_old, twin_new, 'twin')):
        r = subprocess.run([sys.executable, str(ROOT / 'tools/s81_dv/frame_hier_part.py'), '--rtl', src, '--top', top,
                            '--bands', str(hd / f'{m}_bands.json'), '--out', str(ROOT / dst), '--sources', *srcs,
                            '--defines', *base.get('defines', []), '--report', str(hd / f'{m}_part_{key}.json'), '--feedthrough']
                           + (['--mut0-assigns'] if key == 'kit' else []),
                           cwd=ROOT, capture_output=True, text=True)
        if r.returncode:
            raise SystemExit(r.stderr[-3000:] + r.stdout[-2000:])
        rep[key] = json.loads((hd / f'{m}_part_{key}.json').read_text())
    if rep['kit']['inst_band'] != rep['twin']['inst_band']:
        raise SystemExit('kit and twin partitions differ')
    far = rep['kit']['far_nets']
    if set(far) - {'lpr_root'}:
        raise SystemExit(f'non-adjacent band nets other than lpr_root (fed through): {far}')
    full_band = {i: b for i, b in rep['kit']['inst_band'].items()}
    hier_text = lp.preprocess((ROOT / kit_new).read_text(), base.get('defines'))
    bports = {b: module_ports(hier_text, f'{top}_b{b}') for b in range(nb)}
    # ---- net x for abutted faces: mean x of the flat instances on the net
    kpos, knets = positions(base, kit_old, top)
    def net_x(n):
        xs = [kpos[i][0] for i in knets.get(re.sub(r"__ft\d+$", "", n), ()) if i in kpos]
        return sum(xs) / len(xs) if xs else W / 2
    owner = collections.defaultdict(set)
    for b in range(nb):
        for n, d, w, vec in bports[b]:
            owner[n].add(b)
    face = {b: {} for b in range(nb)}       # port -> face
    lines = {b: [] for b in range(nb)}
    top_lines = []
    wband = lambda b: W if b == 0 else W - CHANNEL_UM
    margin = 3.0
    # frame data ports: b0 E face at the frame pin ranges (M4 / M6 alternate, exact tracks), shared with the frame top
    width = {n: (w, vec) for b in range(nb) for n, d, w, vec in bports[b]}
    fr = base['pin_ranges']
    for p in FRAME_PORTS:
        if p not in owner:
            continue
        if owner[p] != {core}:
            raise SystemExit(f'frame port {p} reaches bands {owner[p]} (only the core band b{core} may own frame data ports)')
        lo, hi = fr[p]
        w, vec = width[p]
        bl = bits(p, w, vec)
        step = (hi - lo) / len(bl)
        for k, pin in enumerate(bl):
            L = 'M4' if k % 2 == 0 else 'M6'
            y = snap(lo + step * (k + 0.5), L)
            if not lo <= y <= hi:
                raise SystemExit(f'{pin} off its range')
            lines[core].append(place_line(pin, L, W, y - bounds[core]))
            top_lines.append(place_line(pin, L, W, y))
        face[core][p] = 'E'
    # abutted boundaries
    for k in range(nb - 1):
        # fed-through nets: band k drives <n>__ft<k>, band k+1 reads it on its port <n>
        ft = {f'{n[:-len(f"__ft{k}")]}': n for n in owner if n.endswith(f'__ft{k}') and k in owner[n]}
        shared = sorted(n for n, bs in owner.items() if k in bs and k + 1 in bs and n not in CLOCKS and n not in ft)
        pairs = [(n, n) for n in shared] + [(lo_n, up_n) for up_n, lo_n in ft.items()]
        want = []
        for lo_n, up_n in pairs:
            w, vec = width[lo_n]
            for lo_pin, up_pin in zip(bits(lo_n, w, vec), bits(up_n, w, vec)):
                want.append(((lo_pin, up_pin), net_x(lo_n)))
        lim = min(wband(k), wband(k + 1)) - margin
        pl = legal_spread(want, margin, lim, ('M3', 'M5'), 0.144)
        for (lo_pin, up_pin), (x, L) in pl.items():
            lines[k].append(place_line(lo_pin, L, x, bounds[k + 1] - bounds[k]))
            lines[k + 1].append(place_line(up_pin, L, x, 0.0))
        for lo_n, up_n in pairs:
            face[k][lo_n] = 'N'
            face[k + 1][up_n] = 'S'
    # clocks + lpr_root: the frame-top channel.  b0 takes them on its N face inside the channel x range; b1.. on E.
    # clocks: each band's root enters its E face at the frame's own ck pin (the frame top is pure abutment)
    for n in sorted(x for x in owner if x in CLOCKS):
        for b in sorted(owner[n]):
            lo, hi = fr[n]
            if not bounds[b] <= lo and hi <= bounds[b + 1]:
                raise SystemExit(f'clock {n} pin [{lo}, {hi}] is outside band b{b} [{bounds[b]}, {bounds[b + 1]})')
            y = snap((lo + hi) / 2, 'M4')
            lines[b].append(place_line(n, 'M4', W, y - bounds[b]))
            top_lines.append(place_line(n, 'M4', W, y))
            face[b][n] = 'E'
    for b in range(nb):
        miss = [n for n, d, w, vec in bports[b] if n not in face[b]]
        if miss:
            raise SystemExit(f'band b{b}: ports without a face: {miss[:10]} ({len(miss)})')
    # ---- band kits
    prec = json.loads((ROOT / base['landed_record']).read_text())
    out = {}
    for b in range(nb):
        name = f's81frame_{m}_{tag}_b{b}'
        s = json.loads(json.dumps(base))
        s['name'] = name
        s['top'] = f'{top}_b{b}'
        s['sources'] = [kit_new if f == kit_old else f for f in base['sources']]
        y0 = bounds[b]
        sh = lambda y: y + sum(dy for t, dy in shifts if y >= t - 1e-6)
        s['outline'] = dict(w=round(wband(b), 4), h=round(bounds[b + 1] - y0, 4), exact=True)
        s['children'] = [dict(c, at=[c['at'][0], round(sh(c['at'][1]) - y0, 4)]) for c in base['children']
                         if full_band[c['inst'].split('.')[0]] == b]
        s['macros'] = [dict(c, at=[c['at'][0], round(sh(c['at'][1]) - y0, 4)]) for c in base['macros']
                       if full_band[c['inst'].split('.')[0]] == b]
        cks = sorted({n for n in owner if n in CLOCKS and b in owner[n]})
        if len(cks) != 1:
            raise SystemExit(f'band b{b} clocks {cks}')
        for k in ('clock_entry_domains', 'reset_landing', 'pin_ranges', 'reroute_reason'):
            s.pop(k, None)
        # one root, landed band of the parent (raw ROM clocks on the region root: a landed multiple_cts_roots cluster)
        s['clock'] = 'multiple_cts_roots'
        s['clock_port'] = cks[0]
        s['clock_ports'] = [cks[0]]
        pnames = [n for n, d, w, vec in bports[b]]
        rname = next(r for r, rr in prec['regions'].items() if rr['clock_port'] == cks[0])
        insts_b = sorted(i for i, v in full_band.items() if v == b)
        halves = []
        for L in prec['landings']:
            for side in ('w', 'r'):
                if full_band.get(f"u_lpl_{L['name']}_{side}") == b:
                    other = full_band.get(f"u_lpl_{L['name']}_{'r' if side == 'w' else 'w'}")
                    if other == b:
                        raise SystemExit(f"landing {L['name']} has ring and read in band b{b}")
                    halves.append(dict(name=L['name'], side=side, peer_band=other,
                                       ports=[f"lpl_{L['name']}_{k}" for k in ('bank', 'epo', 'vld')]))
        brec = dict(generator='tools/s81_dv/frame_hier_kit.py', kind='landed_band', top=s['top'],
                    parent_record=base['landed_record'], parent_top=top, band=b, bounds=[bounds[b], bounds[b + 1]],
                    regions={rname: dict(clock_port=cks[0], children=insts_b)}, D=prec['D'], E=prec['E'], K=prec.get('K'),
                    landings=[], landing_halves=halves, landing_implementation=prec.get('landing_implementation'))
        rp = f'{V.REC}/{tag}/{s["top"]}_record.json'
        (ROOT / rp).write_text(json.dumps(brec, indent=1) + '\n')
        s['landed_record'] = rp
        s['landed_band'] = True
        s['reset_ports'] = [p for p in ('rst_n',) if p in pnames]
        s['static_ports'] = [p for p in ('lk',) if p in pnames]
        if 'xk' in pnames:
            s['forwarded_clock_ports'] = ['xk']
            s['reset_landing'] = base['reset_landing']

        else:
            s.pop('forwarded_clock_ports', None)
            s.pop('forwarded_soft_clocks', None)
            s['reset_landing'] = dict(enable=False, reason=(
                'band of a landed frame: its resets are the frame lp reset-forest leaves / lpr_root run (registered '
                'kept leaves on this band clock), not a port reset'))
        dirs = {n: d for n, d, w, vec in bports[b]}
        s['clock_entry_domains'] = {'core': dict(ratio=[1, 1], ports=[cks[0]],
                                                 inputs=sorted(n for n in pnames if dirs[n] == 'in' and n != cks[0]),
                                                 outputs=sorted(n for n in pnames if dirs[n] == 'out'))}
        s['soft_root_macro_bindings'] = {i: v for i, v in base['soft_root_macro_bindings'].items() if full_band.get(i) == b}
        if not s['soft_root_macro_bindings']:
            s.pop('soft_root_macro_bindings', None)
            s.pop('soft_root_macro_masters', None)
        fp = collections.defaultdict(list)
        for n in pnames:
            fp[face[b][n]].append(n)
        s['pins'] = dict(fp)
        s['io_tcl'] = f'physical/ref_tile/{name}/pins.tcl'
        s['structural_change'] = (
            f'S81 frame MAIN-hier (b2, STW-S81c-DIE-FRAME 10-22): band b{b} of {m} {tag} = rows y [{bounds[b]}, '
            f'{bounds[b + 1]}) of the bound {src_tag} landed frame (same instances / nets; frame_hier_part.py); hard band '
            f'(level-2 cluster) under a level-3 M8-passthrough frame top. ' + a.why)
        s['frame'] = dict(base['frame'], hier=dict(tag=tag, band=b, bounds=bounds, channel_um=CHANNEL_UM, kit_rtl=kit_new,
                                                   twin_rtl=twin_new))
        j = s['job']
        j['tag'] = f'{tag}_b{b}'
        j['purpose'] = f'S81 {m} frame band b{b} ({tag}: hard row band of the {src_tag} landed frame)'
        j['views_to'] = f'physical/ref_tile/{name}/views'
        j['record_to'] = f'results/rtl/ref_tile/{name}'
        j['extra_paths'] = sorted(set(j.get('extra_paths', []) + [f'{V.REC}/{tag}', f'{V.LPDIR}/{tag}']))
        # the frame benches run on the frame top (flattened = bound netlist); the band carries the partition proof
        j['benches'] = [dict(name='hier_partition_equiv', expect='pass', threads=1, peak_ram_gb=8,
                             cmd=f'python3 tools/s81_dv/frame_hier_kit.py --check {m} {tag} {b}')]
        kd = ROOT / 'physical/ref_tile' / name
        kd.mkdir(parents=True, exist_ok=True)
        (kd / 'pins.tcl').write_text(f'# generated by tools/s81_dv/frame_hier_kit.py ({m} {tag} band b{b}); abutted faces '
                                     f'carry identical x on both bands\n' + '\n'.join(lines[b]) + '\n')
        sp = ROOT / 'tools/ref_tile/specs_s81frame' / f'{name}.json'
        sp.write_text(json.dumps(s, indent=1) + '\n')
        out[name] = dict(outline=s['outline'], children=len(s['children']), macros=len(s['macros']), ports=len(pnames),
                         pins=len(lines[b]), clock=cks[0], faces={f: len(v) for f, v in fp.items()})
    (hd / f'{m}_top_pins.tcl').write_text('\n'.join(top_lines) + '\n')
    (hd / f'{m}_hier.json').write_text(json.dumps(dict(bounds=bounds, channel_um=CHANNEL_UM, bands=out,
                                                       kit=kit_new, twin=twin_new, far_nets=far), indent=1))
    print(json.dumps(out, indent=1))


def check(m, tag, b):
    """partition proof for one band: the band module's instances are exactly the bound kit's instances assigned to it, with
    identical module / parameter text and identical (port-resolved) connection expressions"""
    h = json.loads((ROOT / V.REC / tag / f'{m}_hier.json').read_text())
    part = json.loads((ROOT / V.REC / tag / f'{m}_part_kit.json').read_text())
    ib = part['inst_band']
    src = (ROOT / h['kit']).read_text()
    flat_src = re.search(r'from (\S+) -- hard row bands', src).group(1)
    ft = lp.preprocess((ROOT / flat_src).read_text(), [])
    fm = lp.parse_module(ft, re.search(r'module\s+(\w+)_b0\b', src).group(1))
    _, _, fi = lp.parse_body(fm['body'])
    flat = {i['inst']: (i['module'], i['params'], i['conns']) for i in fi}
    ht = lp.preprocess(src, [])
    top = re.search(r'module\s+(\w+)_b0\b', src).group(1)
    bm = lp.parse_module(ht, f'{top}_b{b}')
    _, _, bi = lp.parse_body(bm['body'])
    want = {k for k, v in ib.items() if v == int(b)}
    got = {i['inst'] for i in bi}
    bad = [i['inst'] for i in bi if (i['module'], i['params'], i['conns']) != flat.get(i['inst'])]
    ok = want == got and not bad
    print(f"HIER_EQUIV {'PASS' if ok else 'FAIL'} {m} {tag} b{b}: {len(got)} instances (missing {len(want - got)}, "
          f"extra {len(got - want)}, changed {len(bad)})")
    return 0 if ok else 1


def selftest_band_record(m, tag):
    """clock_entry_constraints landed_band records + half-landing SDC: every band validates and constrains each half;
    mutants (half on the wrong side, a missing port, a whole landing, a foreign parent landing) are refused"""
    sys.path.insert(0, str(ROOT / 'tools/ref_tile'))
    import clock_entry_constraints as C
    h = json.loads((ROOT / V.REC / tag / f'{m}_hier.json').read_text())
    bad = 0
    for name in h['bands']:
        spec = json.loads((ROOT / 'tools/ref_tile/specs_s81frame' / f'{name}.json').read_text())
        rec = C.landed_record(spec, ROOT)
        sdc = C.landed_sdc(spec, ROOT)
        n = len(rec['landing_halves'])
        ok = (f'OT_LP_HALF_SDC' in sdc) == bool(n) and sdc.count('set_multicycle_path -setup') == n
        print(f'BAND_RECORD {name}: halves {n}, sdc multicycles {sdc.count("set_multicycle_path -setup")} ->', 'OK' if ok else 'BAD')
        bad += not ok
        if not n:
            continue
        rp = ROOT / spec['landed_record']
        orig = rp.read_text()
        for mut in ('side', 'port', 'whole', 'foreign'):
            r = json.loads(orig)
            if mut == 'side':
                r['landing_halves'][0]['side'] = 'w' if r['landing_halves'][0]['side'] == 'r' else 'r'
            elif mut == 'port':
                r['landing_halves'][0]['ports'] = r['landing_halves'][0]['ports'][:2]
            elif mut == 'whole':
                r['landings'] = [dict(name=r['landing_halves'][0]['name'])]
            else:
                r['landing_halves'][0]['name'] = '99999'
            try:
                rp.write_text(json.dumps(r))
                C.landed_record(spec, ROOT)
                print(f'  mutant {mut}: ACCEPTED (BAD)'); bad += 1
            except ValueError:
                pass
            finally:
                rp.write_text(orig)
    print('BAND_RECORD_SELFTEST', 'PASS' if not bad else 'FAIL')
    return 1 if bad else 0


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--selftest-band-record':
        raise SystemExit(selftest_band_record(*sys.argv[2:4]))
    if len(sys.argv) > 1 and sys.argv[1] == '--check':
        raise SystemExit(check(*sys.argv[2:5]))
    main()
