#!/usr/bin/env python3
"""S81 HEAD ctl glue R6 (STW-S81c-DIE2-C25 10-22): SECOND-FACE pin plan, parallel fallback to R5 (M4+M6 E face).

Head-die h11m3/h11f3 GRT probes: the one hot class is the glue E face ((10,10-13) H 17k MAIN / 26k FB): 54 ctl<->lane
links (36 ln_mesh + 18 ln_draft, 276 b) leave the 3,888-um E face in 64.8-um bands at ~3.5 pins/um local.

R6 = R3/R4 glue (same RTL file, same ports/widths, same relay stages = same latency) with a new pin plan:
  * the E lane whose die position is southernmost (ln_draft2) leaves on the S face, the northernmost (ln_draft4) on the
    N face, each in the free E-end window of that face (the seq peer windows + sn/ss bands own x ~0.28W..0.71W, so the
    N/S faces are NOT free over their whole length: only one 6-link lane fits per face end at <= ~3 pins/um);
  * the remaining 42 E links are re-spread uniformly over the whole E face (64.8-um -> 90.7/101-um pitch);
  * MAIN r6m: single layer (M4 E/W, M5 N/S).  FB r6f: + R5's two-layer E face (every 2nd E pin M6, m6_pin_grant).
Gate: the relay stage count of every net must equal R3's (the generated RTL must equal the committed R3 top except the
'// relay ... anchor distance' comments), else FAIL; the committed R3 RTL file is used unchanged.
Writes results/arch/s81_head_1021/glue_r6/h11{m,f}_ctl_links_r6.json (die-side landing positions, relative to ctl
origin), physical/ref_tile/s81hd_glue_r6{m,f}/{io_pins.tcl,spec.json} and runs ref_tile gen.

  python3 tools/s81_head/glue_r6_kits.py [--no-gen]
"""
import copy, json, os, subprocess, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/s81_head'))
sys.path.insert(0, str(ROOT / 'tools/hier_contract'))
import glue_rg_gen as G   # noqa: E402
import m6_pin_grant as M6   # noqa: E402

MOVE = {'ln_draft2': 'S', 'ln_mesh4': 'N'}      # lane -> new face (die y: draft2 2808 = south end, mesh4 21589 = north end;
#   the only S-/N-end lanes whose move keeps every relay stage count: draft4/mesh0/mesh1/mesh5/draft3/mesh3 would
#   lengthen their fault/CSR relays to WH1)
EDGE = 20.0                                     # um kept free at each face end / beside the existing N/S windows
OUT = ROOT / 'results/arch/s81_head_1021/glue_r6'
NAMES = {'m': 's81hd_glue_r6m', 'f': 's81hd_glue_r6f'}
BASE_SPEC = {'m': 's81hd_glue_r4m', 'f': 's81hd_glue_r5f'}
ORIG_LOAD, ORIG_ANCH = G.load_links, G.anchors


def ns_used(v):
    """x-extent of the existing N / S pins (seq peer windows + sn/ss bands), from the R3 generator's own placement"""
    W = G.VAR[v]['W']; c = W / 2
    pp = json.loads((G.ARCH / f'peer_pin_plan_{v}.json').read_text())
    hi = max([c + 457.6] + [c + r['hi_um'] for r in pp['rows']]); lo = min([c - 489.6] + [c + r['lo_um'] for r in pp['rows']])
    return lo, hi


def r6_links(v, ST3):
    g = G.VAR[v]; W, H = g['W'], g['H']
    d = copy.deepcopy(ORIG_LOAD(v))
    L = d['links']
    lo, hi = ns_used(v)
    for lane, face in MOVE.items():
        rs = sorted([r for r in L if r['port'].startswith(lane + '_')], key=lambda r: r['pos_um'])
        assert len(rs) == 6 and all(r['face'] == 'E' for r in rs), lane
        a, b = hi + EDGE, W - EDGE                     # E-end window of the N / S face
        P = (b - a) / len(rs)
        for i, r in enumerate(rs):
            r.update(face=face, pos_um=round(a + P * (i + 0.5), 3), r3_face='E')
    E = sorted([r for r in L if r['face'] == 'E'], key=lambda r: r['pos_um'])
    lanes = []
    for r in E:
        if r['port'][:-2] not in lanes:
            lanes.append(r['port'][:-2])
    P, pos = place_e(v, lanes, ST3)
    for ln in lanes:
        rs = [r for r in E if r['port'][:-2] == ln]
        s0, p = pos[ln]
        for i, r in enumerate(rs):
            r['r3_pos_um'] = r['pos_um']; r['pos_um'] = round(s0 + p * i, 3)
    d['schema'] = 'opentallas.s81hd.glue_r6.ctl_links.v1'
    d['r6'] = dict(move=MOVE, e_pitch_um=round(P, 3), e_lane_start_pitch={k: [round(a, 3), round(b, 3)] for k, (a, b) in pos.items()}, ns_window_um=[round(hi + EDGE, 3), W - EDGE],
                   rule='moved lanes in the E-end window of N/S beyond the seq/sn/ss windows; E links re-spread at the largest common '
                        'pitch that keeps every lane centroid inside its R3 relay-stage window, the last lane spread over the spare top')
    return d


def place_e(v, lanes, ST3):
    """largest common pitch p such that each remaining E lane (6 links at p, in R3 order) keeps its centroid inside the
    window where no relay net of that lane needs more stages than R3 (anchors of the fixed zones are R3's); the last lane
    then takes the spare top of the face at its own pitch (centroid still inside its window)."""
    H = G.VAR[v]['H']; A = ORIG_ANCH(v); I = {}
    for ln in lanes:
        z, _ = G.lane_of(ln + '_t'); lo, hi = -1e9, 1e9
        for nm, s, d, vf, df, grp in G.nets():
            if z in (s, d):
                o = d if s == z else s
                r = G.HOP * ST3[nm][0] - 100.0 - abs(A[z][0] - A[o][0]) - 1.0
                lo = max(lo, A[o][1] - r); hi = min(hi, A[o][1] + r)
        I[ln] = (lo, hi)

    def feas(p):
        y = EDGE + 0.5 * p; pos = {}
        for ln in lanes:
            lo, hi = I[ln]; s0 = max(y, lo - 2.5 * p)
            if s0 + 2.5 * p > hi:
                return None
            pos[ln] = (s0, p); y = s0 + 6 * p
        return pos if y - 0.5 * p <= H - EDGE else None
    a, b = 10.0, 400.0
    for _ in range(60):
        m = (a + b) / 2
        a, b = (m, b) if feas(m) else (a, m)
    p = int(a * 10) / 10.0; pos = feas(p)
    ln = lanes[-1]; s0, _ = pos[ln]
    q = max(p, min((H - EDGE - 0.5 * p - s0) / 5, (I[ln][1] - s0) / 2.5))
    pos[ln] = (s0, int(q * 10) / 10.0)
    return p, pos


def anchors_r6(v):
    A = ORIG_ANCH(v)
    g = G.VAR[v]; H = g['H']
    L = G.load_links(v)['links']
    for lane, face in MOVE.items():
        z, _ = G.lane_of(lane + '_t')
        xs = [r['pos_um'] for r in L if r['port'].startswith(lane + '_')]
        A[z] = (sum(xs) / len(xs), H - 150.0 if face == 'N' else 150.0, face)
    return A


def gen_pins(v):
    g = G.VAR[v]; W, H = g['W'], g['H']
    L = G.load_links(v)['links']
    pins = []
    for face in 'WENS':
        rs = sorted([r for r in L if r['face'] == face and r['port'].startswith(('ln_', 'lep_'))], key=lambda r: r['pos_um'])
        ps = [r['pos_um'] for r in rs]
        for i, r in enumerate(rs):
            gaps = [abs(ps[j] - r['pos_um']) for j in (i - 1, i + 1) if 0 <= j < len(ps) and ps[j] != r['pos_um']]
            half = 0.42 * min(gaps)
            k = int(r['link'].rsplit('_l', 1)[1])
            mine = G.pack_bits(r['port'])[276 * k: 276 * (k + 1)]
            pins += [(nm, face, c) for nm, c in G.place_band(mine, r['pos_um'] - half, r['pos_um'] + half)]
    c = W / 2
    pp = json.loads((G.ARCH / f'peer_pin_plan_{v}.json').read_text())
    for row in pp['rows']:
        pins += [(nm, 'N', x) for nm, x in G.place_band(G.bus_names('seq_' + row['port'], row['bits']), c + row['lo_um'], c + row['hi_um'])]
    for face, o, i in (('N', 'sn_o', 'sn_i'), ('S', 'ss_o', 'ss_i')):
        pins += [(nm, face, x) for nm, x in G.place_band(G.bus_names(o, 565), c - 489.6, c - 149.6)]
        pins += [(nm, face, x) for nm, x in G.place_band(G.bus_names(i, 565), c + 117.6, c + 457.6)]
    used = sorted(x for nm, f, x in pins if f == 'W')
    best = None
    for a, b in zip(used, used[1:]):
        if b - a > 4.0:
            m = (a + b) / 2
            if best is None or abs(m - H / 2) < abs(best - H / 2):
                best = m
    pins += [('ck', 'W', G.snap(best - 0.48)), ('rst_n', 'W', G.snap(best + 0.48))]
    names = [p[0] for p in pins]
    assert len(names) == len(set(names)), 'duplicate pin'
    for f in 'NSWE':               # no two pins of one face closer than one grid step
        xs = sorted(x for nm, ff, x in pins if ff == f)
        assert all(b - a >= G.GRID - 1e-6 for a, b in zip(xs, xs[1:])), f
        assert xs[0] > 0 and xs[-1] < (W if f in 'NS' else H), f
    return pins


def density(pins, v, win=100.0):
    W, H = G.VAR[v]['W'], G.VAR[v]['H']
    out = {}
    for f in 'NSWE':
        xs = sorted(x for nm, ff, x in pins if ff == f); Lf = W if f in 'NS' else H
        j = 0; mx = 0
        for i in range(len(xs)):
            while xs[i] - xs[j] > win:
                j += 1
            mx = max(mx, i - j + 1)
        out[f] = dict(pins=len(xs), per_um_face=round(len(xs) / Lf, 2), max_per_um_100um=round(mx / win, 2))
    return out


def io_tcl(pins, v, m6):
    W, H = G.VAR[v]['W'], G.VAR[v]['H']
    lines = [f'# GENERATED by tools/s81_head/glue_r6_kits.py ({NAMES[v]}, {W:g} x {H:g} um): R6 second-face pin plan '
             f'(lanes {MOVE} moved off the E face; 42 E links re-spread uniformly); same bit order per die link (hd_bind pack).']
    grant = []
    e_sorted = sorted([p for p in pins if p[1] == 'E'], key=lambda p: p[2])
    on_m6 = {p[0] for i, p in enumerate(e_sorted) if m6 and i % 2 == 1}
    if m6:
        lines.append('# r6f: E-face pins alternate M4 / M6 by y (every 2nd E pin on M6 at the same centre), m6_pin_grant (R5 recipe)')
    for nm, f, x in pins:
        if f == 'W':
            lines.append(f'place_pin -pin_name {{{nm}}} -layer M4 -location {{0.000000 {x:.6f}}} -pin_size {{0.192 0.024}} -force_to_die_boundary')
        elif f == 'E' and nm in on_m6:
            lines.append(f'place_pin -pin_name {{{nm}}} -layer M6 -location {{{W:.6f} {x:.6f}}} -pin_size {{0.384 0.032}} -force_to_die_boundary')
            grant.append(dict(name=nm, face='E', span_um=[round(x - 0.096, 3), round(x + 0.096, 3)], max_depth_um=0.384,
                              max_area_um2=0.024576))
        elif f == 'E':
            lines.append(f'place_pin -pin_name {{{nm}}} -layer M4 -location {{{W:.6f} {x:.6f}}} -pin_size {{0.192 0.024}} -force_to_die_boundary')
        elif f == 'N':
            lines.append(f'place_pin -pin_name {{{nm}}} -layer M5 -location {{{x:.6f} {H:.6f}}} -pin_size {{0.024 0.192}} -force_to_die_boundary')
        else:
            lines.append(f'place_pin -pin_name {{{nm}}} -layer M5 -location {{{x:.6f} 0.000000}} -pin_size {{0.024 0.192}} -force_to_die_boundary')
    return '\n'.join(lines) + '\n', grant


def main():
    gen = '--no-gen' not in sys.argv
    ST3 = G.plan_stages()
    r6 = {v: r6_links(v, ST3) for v in G.VAR}
    G.load_links = lambda v: r6[v]
    G.anchors = anchors_r6
    ST6 = G.plan_stages()
    diff = {k: (ST3[k][0], ST6[k][0]) for k in ST3 if ST3[k][0] != ST6[k][0]}
    assert not diff, f'R6 changes relay stages (latency): {diff}'
    rtl = G.OUT_RTL.read_text()
    with tempfile.TemporaryDirectory() as td:
        G.OUT_RTL = Path(td) / 'top.sv'; G.gen_rtl(ST6)
        code = lambda t: [ln for ln in t.splitlines() if not ln.strip().startswith('//')]
        assert code(G.OUT_RTL.read_text()) == code(rtl), 'R6 RTL differs from the committed R3 top'   # only the
        # '// relay ... max anchor distance' comments move with the anchors; the committed R3 file stays the RTL
    OUT.mkdir(parents=True, exist_ok=True)
    rep = dict(schema='opentallas.s81hd.glue_r6.report.v1', stages_equal_r3=True, rtl_identical_r3=True, kits={})
    for v in G.VAR:
        (OUT / f'h11{v}_ctl_links_r6.json').write_text(json.dumps(r6[v], indent=1) + '\n')
        pins = gen_pins(v)
        tcl, grant = io_tcl(pins, v, m6=(v == 'f'))
        name = NAMES[v]; kd = ROOT / f'physical/ref_tile/{name}'; kd.mkdir(parents=True, exist_ok=True)
        (kd / 'io_pins.tcl').write_text(tcl)
        dens = density(pins, v)
        if v == 'f':
            dens['E']['per_layer_max_per_um_100um'] = round(dens['E']['max_per_um_100um'] / 2, 2)
        rep['kits'][name] = dict(pins=len(pins), faces=dens, m6_pins=len(grant))
        s = json.loads((ROOT / f'physical/ref_tile/{BASE_SPEC[v]}/spec.json').read_text())
        faces = {'N': [], 'S': [], 'W': [], 'E': [], 'ANY': []}
        base = {}
        for nm, f, x in pins:
            base.setdefault(nm.split('[')[0], set()).add(f)
        for b, fs in sorted(base.items()):
            faces['ANY' if len(fs) > 1 else next(iter(fs))].append(b)
        s['pins'] = {f: n for f, n in faces.items() if n}
        s['name'] = name
        s['io_tcl'] = f'physical/ref_tile/{name}/io_pins.tcl'
        if grant:
            g0 = s['m6_pin_grant']
            # R6_IO_COMMIT = the commit that holds this io_pins.tcl (ref_tile gen checks the grant against it)
            s['m6_pin_grant'] = dict(g0, ports=grant, source_commit=os.environ.get('R6_IO_COMMIT', '0' * 40),
                                     source_spec_sha256='0' * 64,
                                     granted_by=g0['granted_by'] + '; carried to R6 FB by STEWARD-S81c 12:00 (second face + M4+M6 E face)')
        else:
            assert 'm6_pin_grant' not in s
        prev = s['structural_change']
        s['structural_change'] = (
            f'R6 ({name}) second-face pin plan (STW-S81c-DIE2-C25, STEWARD-S81c 12:00 parallel fallback to R5): head-die '
            'h11m3/h11f3 GRT hot class = glue E face (54 ctl<->lane links in 64.8-um bands). ln_draft2 (southernmost lane) -> S '
            'face, ln_draft4 (northernmost) -> N face, in the E-end window beyond the seq/sn/ss windows; the 42 remaining E '
            f'links re-spread uniformly over the E face. Faces (pins, max per um over 100 um): {json.dumps(dens)}. '
            + ('Plus R5 two-layer E face (every 2nd E pin M6, m6_pin_grant). ' if grant else 'Single layer (no M6 grant). ')
            + 'Same RTL file (generator-verified: identical code, every relay stage count equal), ports, widths and relay stages (latency). Prev: ' + prev)
        s['job'].update(owner='Claude:STW-S81c-DIE2-C25', branch='claude/s81hd-glue-r6-1022', tag=name,
                        views_to=f'physical/ref_tile/{name}/views', record_to=f'results/rtl/ref_tile/{name}')
        s['job']['extra_paths'] = sorted(set(s['job'].get('extra_paths', [])) | {'results/arch/s81_head_1021/glue_r6'})
        if grant:
            s['m6_pin_grant']['source_spec_sha256'] = M6.spec_digest(s)
        p = kd / 'spec.json'
        p.write_text(json.dumps(s, indent=1) + '\n')
        if gen:
            r = subprocess.run([sys.executable, str(ROOT / 'tools/ref_tile/ref_tile.py'), 'gen', str(p)], cwd=ROOT,
                               capture_output=True, text=True)
            print(name, 'gen rc', r.returncode, (r.stdout + r.stderr).strip()[-600:])
            assert r.returncode == 0
    (OUT / 'r6_report.json').write_text(json.dumps(rep, indent=1) + '\n')
    print(json.dumps(rep['kits'], indent=1))


if __name__ == '__main__':
    main()
