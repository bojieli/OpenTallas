#!/usr/bin/env python3
"""Measured qualification of mirrored placements (MY / MX / R180) of closed bound hard views.

S-DIE 2026-10-16.  Closed views are exported by write_abstract_lef without SYMMETRY, so the literal LEF permits R0
only and tools/dsrom_s81_fulldie.py bound_view_orientation_contract refuses the W-going (MY) and S-going (MX)
placements the die generator makes.  This tool is the second, evidence-backed source of permitted orientations: for
every (master, LEF sha256, orientation) it measures what the mirror changes physically and writes a table the
generator accepts only through an explicit --orientation-qualification PATH, only for the exact LEF sha256, and only
when every check is PASS.

Checks per (master, orientation), each against the same master in R0:
  a  signal_track_lattice  every signal pin access shape has a legal on-track origin that also lies on the die site
                           grid: the exact rule of physical/common/ot_macro_track_snap.tcl (ot_mts::rule +
                           snap_axis_cands, wrong-way stubs exempt as main 401c0303c) on the ASAP7 make_tracks lattice.
  b  pg_die_grid           the die PDN (case_irm: horizontal M8 / vertical M9 straps, pitch from the bump pitch and the
                           field coverage) reaches a macro PG strap through the strap's extent ACROSS the die-strap
                           direction (vertical macro strap -> its y-span against horizontal M8; horizontal macro strap ->
                           its x-span against vertical M9).  PASS needs (1) over EVERY legal origin of the orientation,
                           the fewest same-net die straps met per net >= R0's fewest over R0's legal origins (and >= 1
                           where R0 guarantees >= 1)
                           (placement-independent; span_multiset_equal_r0 records the stronger exact equivalence),
                           (2) every placed instance of the die in this orientation meets >= 1 same-net die strap per
                           net, and (3) PG strap centre track alignment over the legal origins no worse than R0
                           (fraction of legal origin classes with every PG strap on track).
  c  row_parity            MX / R180 only: SIZE height an even integer number of 0.27-um rows, so the mirrored internal
                           row stack keeps its boundary rail polarity.  The die-top facts that decide whether parity
                           can matter (std-cell instances on the die top, row-index parity of the R0 placements) are
                           recorded beside it.
  d  timing_clock          the TT/FF/SS ETM liberty files are the hash-verified ones of the binding entry (a liberty
                           timing model carries no orientation: arcs, caps and constraints are orientation-invariant);
                           every liberty clock pin exists in the LEF; the clock pin's mirrored location and face are
                           recorded (the die clock plan reads the pin from the placed LEF, nothing else changes).

usage:
  orientation_qualify.py --binding results/arch/s81_native_20261013/view_binding_closed_1016a.json [--binding ...]
      --placed placed.tsv --placed-source die.v=<sha> --placed-source place.tcl=<sha> --tag 1016 --out OUT.json
  placed.tsv[.gz]: 'inst master x y orient' per fplace line of the die (die.v instance master joined to place.tcl):
    python3 -c 'import re,sys; P={t[1]:t[2:5] for t in map(str.split,open("place.tcl")) if len(t)>=5 and t[0]=="fplace"}
    [print(m.group(2),m.group(1),*P[m.group(2)]) for l in open("die.v") if (m:=re.match(r"\s*(\S+)\s+(\S+)\s*\(",l))
     and m.group(2) in P]'
"""
import argparse
import collections
import hashlib
import json
import math
import re
import subprocess
import sys
from functools import reduce
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))

SCHEMA = 's81-orientation-qualification-v1'
DBU = 4000                      # 0.25 nm: every ASAP7 LEF coordinate and half-coordinate is an integer
ROW_H, SITE_W = 0.27, 0.054     # asap7sc7p5t site; the die rows start at the die origin (initialize_floorplan 0 0)
MIRRORS = ('MY', 'MX', 'R180')
# ASAP7 make_tracks (ORFS platforms/asap7/openRoad/make_tracks.tcl): layer -> [(xoff, xpitch, yoff, ypitch)] um
TRACKS = {
    'M1': [(0.009, .036, .009, .036)], 'M3': [(0.009, .036, .009, .036)], 'M4': [(0.009, .036, .012, .048)],
    'M5': [(0.012, .048, .012, .048)], 'M6': [(0.012, .048, .016, .064)], 'M7': [(0.016, .064, .016, .064)],
    'M8': [(0.116, .08, .116, .08)], 'M9': [(0.116, .08, .116, .08)],
    'M2': [(0.009, .036, o, .27) for o in (.045, .081, .117, .153, .189, .225, .270)]}
HORIZONTAL = {'M2', 'M4', 'M6', 'M8'}


def d(v):
    return int(round(float(v) * DBU))


def sha256(b):
    return hashlib.sha256(b).hexdigest()


def read_pinned(rel, want, rev):
    """(bytes, git commit or None) of the version of rel whose sha256 is want: the work tree / rev copy, else the
    newest commit on rev's history whose blob has that sha256 (an older binding table pins a since-replaced view)."""
    b = read_repo(rel, rev)
    if sha256(b) == want:
        return b, None
    log = subprocess.run(['git', '-C', str(ROOT), 'log', '--format=%H', rev, '--', rel], capture_output=True, text=True)
    for c in log.stdout.split():
        r = subprocess.run(['git', '-C', str(ROOT), 'show', f'{c}:{rel}'], capture_output=True)
        if r.returncode == 0 and sha256(r.stdout) == want:
            return r.stdout, c
    raise SystemExit(f'orientation_qualify: no version of {rel} on {rev} has sha256 {want}')


def read_repo(rel, rev):
    """bytes of a repo file: the work tree copy if present, else the git object at rev (sparse worktrees)."""
    p = ROOT / rel
    if p.is_file():
        return p.read_bytes()
    r = subprocess.run(['git', '-C', str(ROOT), 'show', f'{rev}:{rel}'], capture_output=True)
    if r.returncode:
        raise SystemExit(f'orientation_qualify: {rel} neither in the work tree nor at {rev}')
    return r.stdout


# ---------------------------------------------------------------------------------------------------- LEF
def parse_lef(text, master):
    """dict(W, H, pins {name: dict(use, shapes [(layer, x1, y1, x2, y2)] DBU)}, symmetry, errors) of MACRO master."""
    lines = text.splitlines()
    out = dict(W=None, H=None, pins={}, symmetry=None, errors=[])
    start = [j for j, l in enumerate(lines) if re.fullmatch(r'\s*MACRO\s+' + re.escape(master) + r'\s*', l)]
    if len(start) != 1:
        out['errors'].append(f'{len(start)} MACRO {master} headers')
        return out
    pin = layer = None
    in_obs = False
    for l in lines[start[0] + 1:]:
        t = l.split()
        if not t:
            continue
        if t[0] == 'END' and len(t) > 1 and t[1] == master:
            break
        if t[0] == 'SIZE' and pin is None and not in_obs:
            out['W'], out['H'] = d(t[1]), d(t[3])
        elif t[0] == 'SYMMETRY' and pin is None and not in_obs:
            out['symmetry'] = ' '.join(t[1:]).rstrip(';').split()
        elif t[0] == 'PIN':
            pin = t[1]
            out['pins'][pin] = dict(use='SIGNAL', shapes=[])
        elif t[0] == 'OBS':
            pin, in_obs = None, True
        elif t[0] == 'USE' and pin:
            out['pins'][pin]['use'] = t[1].rstrip(';')
        elif t[0] == 'LAYER':
            layer = t[1].rstrip(';')
        elif t[0] == 'RECT' and pin:
            v = [x for x in t[1:] if x != ';']
            if v and v[0] == 'MASK':
                v = v[2:]
            out['pins'][pin]['shapes'].append((layer, *[d(x) for x in v[:4]]))
        elif t[0] == 'POLYGON' and pin:
            out['errors'].append(f'pin {pin} has a POLYGON shape (not modelled: fail closed)')
        elif t[0] == 'END' and len(t) > 1 and pin and t[1] == pin:
            pin = None
    if out['W'] is None:
        out['errors'].append('no SIZE')
    return out


def xform(x1, y1, x2, y2, o, W, H):
    if o == 'R0':
        a, b = (x1, y1), (x2, y2)
    elif o == 'MX':
        a, b = (x1, H - y1), (x2, H - y2)
    elif o == 'MY':
        a, b = (W - x1, y1), (W - x2, y2)
    elif o == 'R180':
        a, b = (W - x1, H - y1), (W - x2, H - y2)
    else:
        raise ValueError(o)
    return min(a[0], b[0]), min(a[1], b[1]), max(a[0], b[0]), max(a[1], b[1])


# ---------------------------------------------------------------------------------------------------- (a) lattice
def axis_tracks(layer, axis):
    pats = [(d(t[2]), d(t[3])) if axis == 'y' else (d(t[0]), d(t[1])) for t in TRACKS[layer]]
    P = reduce(math.lcm, [p for _, p in pats], 1)
    return P, sorted({(o + k * p) % P for o, p in pats for k in range(P // p)})


def meet(c1, c2):
    (P1, S1), (P2, S2) = c1, c2
    L = math.lcm(P1, P2)
    a, b = set(S1), set(S2)
    return L, [r for r in range(L) if r % P1 in a and r % P2 in b]


def track_rule(mac, o):
    """ot_mts::rule: {'x': (P, S), 'y': (P, S)} legal origin residues (DBU) of the signal pins, plus offenders."""
    cons = {'x': (1, [0]), 'y': (1, [0])}
    per = collections.defaultdict(dict)
    for pn, p in mac['pins'].items():
        if p['use'] in ('POWER', 'GROUND'):
            continue
        shapes = []
        for lay, *r in p['shapes']:
            if lay not in TRACKS:
                continue
            ax = 'y' if lay in HORIZONTAL else 'x'
            q = xform(*r, o, mac['W'], mac['H'])
            along, across = (q[2] - q[0], q[3] - q[1]) if ax == 'y' else (q[3] - q[1], q[2] - q[0])
            shapes.append((lay, ax, q, along >= across))
        if any(s[3] for s in shapes):            # wrong-way stubs exempt while the pin keeps a preferred shape
            shapes = [s for s in shapes if s[3]]
        for lay, ax, q, _ in shapes:
            per[(lay, ax)].setdefault(q[1] + q[3] if ax == 'y' else q[0] + q[2], pn)
    bad = []
    for (lay, ax), cs in sorted(per.items()):
        P, T = axis_tracks(lay, ax)
        legal = None
        for c2, pn in cs.items():
            ok = set() if c2 % 2 else {(t - c2 // 2) % P for t in T}
            nl = ok if legal is None else legal & ok
            if not nl and legal:
                bad.append(dict(layer=lay, axis=ax, pin=pn, centre_um=c2 / 2 / DBU))
            legal = nl
            if not legal:
                break
        cons[ax] = meet(cons[ax], (P, sorted(legal)))
    return cons, bad


def site_classes(P, S, grid):
    """legal origin classes on the site grid: origin = k * grid with (k * grid) % P in S, as residues mod lcm."""
    L = math.lcm(P, grid)
    ok = set(S)
    return L, [v for v in range(0, L, grid) if v % P in ok]


# ---------------------------------------------------------------------------------------------------- (b) PG
def die_pg_lattice():
    """case_irm's die M8/M9 PG lattice (tools/dsrom_s81_fulldie.py): pitch, offset, stripe width (um)."""
    import dsrom_s81_fulldie as G
    vp = G.BUMP_PITCH / math.sqrt(0.5)
    raw = G.dn(0.48 / G.COV['field'], 0.160)
    n = math.ceil(vp / raw - 1e-9)
    n += (n % 2 == 0)
    pitch = G.pg_pitch_grid(vp / n)
    return dict(source='tools/dsrom_s81_fulldie.py case_irm top grid', layers=dict(M8='HORIZONTAL', M9='VERTICAL'),
                pitch_um=pitch, offset_um=round((vp / 2) % pitch, 3), width_um=0.48, bump_pitch_um=round(vp, 4),
                field_coverage=G.COV['field'], nets_order=['VDD', 'VSS'], net_step_um=pitch / 2)


def pg_shapes(mac, o):
    out = []
    for pn, p in mac['pins'].items():
        if p['use'] not in ('POWER', 'GROUND'):
            continue
        for lay, *r in p['shapes']:
            out.append((pn, lay, xform(*r, o, mac['W'], mac['H'])))
    return out


def pg_spans(mac, o):
    """sorted [(net, layer, span lo, span hi)]: the extent of each PG shape across the die strap it meets."""
    s = []
    for net, lay, q in pg_shapes(mac, o):
        s.append((net, lay, q[1], q[3]) if lay not in HORIZONTAL else (net, lay, q[0], q[2]))
    return sorted(s)


def die_strap_hits(lo, hi, origin, net, lat):
    """number of die straps of net (horizontal M8 if the macro strap is vertical, vertical M9 otherwise) lying fully
    inside [origin + lo, origin + hi] (DBU)."""
    pitch, w = d(lat['pitch_um']), d(lat['width_um'])
    off = d(lat['offset_um']) + (0 if net == 'VDD' else pitch // 2)
    a, b = origin + lo, origin + hi - w
    if b < a:
        return 0
    k0 = math.ceil((a - off) / pitch)
    k1 = math.floor((b - off) / pitch)
    return max(0, k1 - k0 + 1)


def pg_worst_over_origins(spans, xs, ys, lat):
    """{net: fewest same-net die straps met} over EVERY legal origin (xs / ys: site_classes of the orientation's rule):
    placement-independent, so the table entry holds for any die placement; None without a legal origin."""
    if not xs[1] or not ys[1]:
        return None
    pitch = d(lat['pitch_um'])

    def phases(c):
        L, S = c
        n = pitch // math.gcd(L, pitch)
        return sorted({(r + k * L) % pitch for r in S for k in range(n)})
    px, py = phases(xs), phases(ys)
    out = {}
    for net in sorted({s[0] for s in spans}):
        vy = collections.Counter((a, b) for n, l, a, b in spans if n == net and l not in HORIZONTAL)
        vx = collections.Counter((a, b) for n, l, a, b in spans if n == net and l in HORIZONTAL)
        wy = min(sum(k * die_strap_hits(a, b, o_, net, lat) for (a, b), k in vy.items()) for o_ in py) if vy else 0
        wx = min(sum(k * die_strap_hits(a, b, o_, net, lat) for (a, b), k in vx.items()) for o_ in px) if vx else 0
        out[net] = wy + wx
    return out


def pg_track_fraction(mac, o, xs, ys):
    """fraction of legal (x, y) origin classes for which every PG strap centre lies on its layer's track."""
    sh = pg_shapes(mac, o)
    if not sh:
        return None
    Lx, X = xs
    Ly, Y = ys
    need = collections.defaultdict(set)
    for net, lay, q in sh:
        if lay not in TRACKS:
            continue
        ax = 'y' if lay in HORIZONTAL else 'x'
        need[(lay, ax)].add(q[1] + q[3] if ax == 'y' else q[0] + q[2])

    def ok_axis(ax, v):
        for (lay, a), cs in need.items():
            if a != ax:
                continue
            P, T = axis_tracks(lay, ax)
            T = set(T)
            if any(c2 % 2 or (v + c2 // 2) % P not in T for c2 in cs):
                return False
        return True
    fx = sum(ok_axis('x', v) for v in X) / len(X) if X else 0.0
    fy = sum(ok_axis('y', v) for v in Y) / len(Y) if Y else 0.0
    return round(fx * fy, 6)


# ---------------------------------------------------------------------------------------------------- (d) clock
def lib_clock_pins(text, master):
    m = re.search(r'cell\s*\(\s*"?' + re.escape(master) + r'"?\s*\)', text)
    if not m:
        return None
    pins = []
    for pm in re.finditer(r'pin\s*\(\s*"?([^")]+)"?\s*\)\s*\{(.*?)\n\s*\}', text[m.end():], re.S):
        if re.search(r'^\s*clock\s*:\s*true\s*;', pm.group(2).split('timing')[0], re.M):
            pins.append(pm.group(1))
    return sorted(set(pins))


def face(c, W, H):
    x, y = c
    return min((('W', x), ('E', W - x), ('S', y), ('N', H - y)), key=lambda t: t[1])[0]


# ---------------------------------------------------------------------------------------------------- driver
def load_placed(path):
    by = collections.defaultdict(list)
    import gzip
    for line in (gzip.open(path, 'rt') if str(path).endswith('.gz') else open(path)):
        t = line.split()
        if len(t) == 5:
            by[t[1]].append((t[0], d(t[2]), d(t[3]), t[4]))
    return by


def qualify_entry(master, rec, table_rel, table_sha, rev, placed, lat, die_facts, orients):
    lef_f = rec['files']['lef']
    raw, lef_commit = read_pinned(lef_f['path'], lef_f['sha256'], rev)
    mac = parse_lef(raw.decode(), master)
    libs = {}
    for c in ('tt', 'ff', 'ss'):
        f = rec['files'][c]
        b, _ = read_pinned(f['path'], f['sha256'], rev)
        libs[c] = dict(path=f['path'], sha256=sha256(b), table_sha256=f['sha256'], text=b.decode(errors='ignore'))
    insts = placed.get(master, [])
    use = collections.Counter(o for *_, o in insts)
    gx, gy = d(SITE_W), d(ROW_H)
    r0_rule, _ = track_rule(mac, 'R0') if not mac['errors'] else ({'x': (1, []), 'y': (1, [])}, [])
    r0x, r0y = site_classes(*r0_rule['x'], gx), site_classes(*r0_rule['y'], gy)
    r0_pg_frac = pg_track_fraction(mac, 'R0', r0x, r0y)
    r0_spans = pg_spans(mac, 'R0')
    r0_worst = pg_worst_over_origins(r0_spans, r0x, r0y, lat)
    rows = mac['H'] / gy if mac['H'] else 0
    even_rows = bool(mac['H']) and mac['H'] % gy == 0 and (mac['H'] // gy) % 2 == 0
    r0_row_parity = collections.Counter(('even' if (y // gy) % 2 == 0 else 'odd') if y % gy == 0 else 'off_row'
                                        for _, _, y, o in insts if o == 'R0')
    clocks = lib_clock_pins(libs['tt']['text'], master)
    res = {}
    for o in orients:
        chk = {}
        # (a)
        if mac['errors']:
            chk['signal_track_lattice'] = dict(verdict='FAIL', reason='LEF parse: ' + '; '.join(mac['errors']))
        else:
            rule, bad = track_rule(mac, o)
            xs, ys = site_classes(*rule['x'], gx), site_classes(*rule['y'], gy)
            ok = bool(xs[1]) and bool(ys[1])
            chk['signal_track_lattice'] = dict(
                verdict='PASS' if ok else 'FAIL', rule='physical/common/ot_macro_track_snap.tcl ot_mts::rule, wrong-way '
                'stubs exempt (401c0303c), meet site grid 0.054 x 0.27',
                legal_origin_classes=dict(x=[xs[0] / DBU, len(xs[1])], y=[ys[0] / DBU, len(ys[1])]),
                r0_legal_origin_classes=dict(x=[r0x[0] / DBU, len(r0x[1])], y=[r0y[0] / DBU, len(r0y[1])]),
                offenders=bad[:6], **({} if ok else dict(reason='no legal origin on the track lattice and site grid')))
        # (b)
        spans = pg_spans(mac, o)
        nets = sorted({s[0] for s in spans})
        invariant = [(n, l, a, b) for n, l, a, b in spans] == r0_spans
        worst = {}
        for name, x, y, oo in insts:
            if oo != o:
                continue
            for n in nets:
                h = sum(die_strap_hits(a, b, y if l not in HORIZONTAL else x, n, lat)
                        for nn, l, a, b in spans if nn == n)
                worst[n] = min(worst.get(n, h), h)
        frac = pg_track_fraction(mac, o, xs, ys) if not mac['errors'] else None
        wo = pg_worst_over_origins(spans, xs, ys, lat) if not mac['errors'] else None
        reasons = []
        if not spans:
            reasons.append('no PG pin shapes')
        if wo is None or r0_worst is None:
            reasons.append('no legal origin to evaluate the PG landing on')
        elif set(wo) != set(r0_worst) or any(wo[n] < r0_worst[n] for n in r0_worst):
            reasons.append(f'fewest same-net die straps over legal origins {wo} < R0 {r0_worst}')
        elif any(wo.get(n, 0) < 1 <= r0_worst.get(n, 0) for n in ('VDD', 'VSS')):
            reasons.append(f'some legal origin meets no same-net die strap: {wo}')
        if any(v < 1 <= (r0_worst or {}).get(n, 0) for n, v in worst.items()):
            reasons.append(f'a placed instance meets no same-net die strap: {worst}')
        thin = r0_worst is not None and any(r0_worst.get(n, 0) < 1 for n in ('VDD', 'VSS'))
        if frac is not None and r0_pg_frac is not None and frac < r0_pg_frac:
            reasons.append(f'PG on-track origin fraction {frac} < R0 {r0_pg_frac}')
        layers = sorted({s[1] for s in spans})
        chk['pg_die_grid'] = dict(
            verdict='FAIL' if reasons else 'PASS', reason='; '.join(reasons) or None, pg_layers=layers,
            pg_shapes=len(spans), span_multiset_equal_r0=invariant,
            min_same_net_die_straps_over_legal_origins=wo, r0_min_same_net_die_straps_over_legal_origins=r0_worst,
            die_strap_layer={l: ('M8' if l not in HORIZONTAL else 'M9') for l in layers},
            placed_instances=use.get(o, 0), min_same_net_die_straps_per_instance=worst or None,
            pg_on_track_origin_fraction=frac, r0_pg_on_track_origin_fraction=r0_pg_frac,
            note=('R0 itself can miss a same-net die strap at some legal origin (block thinner than the die strap '
                  'pitch): the block needs a local strap set (pdn_thin_pitch) in every orientation; the mirror is '
                  'no worse') if thin else None)
        # (c)
        if o == 'MY':
            chk['row_parity'] = dict(verdict='PASS', reason=None, applies=False, note='MY keeps the row stack')
        else:
            chk['row_parity'] = dict(
                verdict='PASS' if even_rows else 'FAIL', applies=True, height_um=mac['H'] / DBU, rows=round(rows, 4),
                even_integer_rows=even_rows, r0_placed_row_index_parity=dict(r0_row_parity),
                reason=None if even_rows else 'height not an even integer number of 0.27-um rows', **die_facts)
        # (d)
        reasons = []
        for c, l_ in libs.items():
            if l_['sha256'] != l_['table_sha256']:
                reasons.append(f'{c} liberty sha256 differs from the binding entry')
        if clocks is None:
            reasons.append('tt liberty has no cell ' + master)
        cpins = []
        for cp in clocks or []:
            p = mac['pins'].get(cp)
            if not p or not p['shapes']:
                reasons.append(f'liberty clock pin {cp} absent from the LEF')
                continue
            lay, *r = p['shapes'][0]
            c0 = ((r[0] + r[2]) / 2, (r[1] + r[3]) / 2)
            q = xform(*r, o, mac['W'], mac['H'])
            c1 = ((q[0] + q[2]) / 2, (q[1] + q[3]) / 2)
            cpins.append(dict(pin=cp, layer=lay, r0_um=[v / DBU for v in c0], r0_face=face(c0, mac['W'], mac['H']),
                              mirrored_um=[v / DBU for v in c1], mirrored_face=face(c1, mac['W'], mac['H'])))
        chk['timing_clock'] = dict(
            verdict='FAIL' if reasons else 'PASS', reason='; '.join(reasons) or None,
            liberty={c: dict(path=l_['path'], sha256=l_['sha256']) for c, l_ in libs.items()},
            invariance='an ETM liberty carries no placement orientation: arcs, pin caps and constraints apply unchanged; '
                       'the die clock plan and STA read the clock pin from the placed (mirrored) LEF',
            clock_pins=cpins)
        res[o] = dict(verdict='PASS' if all(c['verdict'] == 'PASS' for c in chk.values()) else 'FAIL',
                      used_on_die=use.get(o, 0), checks=chk)
    return dict(master=master, lef_path=lef_f['path'], lef_sha256=lef_f['sha256'], lef_git_commit=lef_commit, size_um=[mac['W'] / DBU, mac['H'] / DBU],
                literal_symmetry=mac['symmetry'], binding_tables=[dict(path=table_rel, sha256=table_sha)],
                placed_orientation_counts=dict(use), orientations=res)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[1])
    ap.add_argument('--binding', action='append', required=True, help='view-binding table (repo-relative)')
    ap.add_argument('--die-binding', help='the binding table the placed die used (summary scope; default: first --binding)')
    ap.add_argument('--placed', required=True, help="'inst master x y orient' rows of the die placement")
    ap.add_argument('--placed-source', action='append', default=[], help='NAME=SHA256 of the placement sources')
    ap.add_argument('--die-std-cells', type=int, required=True, help='std-cell instances on the die top (die.v)')
    ap.add_argument('--rev', default='HEAD', help='git revision for view files absent from a sparse work tree')
    ap.add_argument('--tag', required=True)
    ap.add_argument('--out', required=True)
    a = ap.parse_args(argv)
    placed = load_placed(a.placed)
    lat = die_pg_lattice()
    die_facts = dict(die_top_std_cell_instances=a.die_std_cells,
                     die_rows_note='die top holds hard macros only; no die-level row, tap or filler cells abut a macro '
                                   'edge' if a.die_std_cells == 0 else 'die top has std cells')
    entries = {}
    for t in a.binding:
        raw = read_repo(t, a.rev)
        tab = json.loads(raw)
        if tab.get('schema') != 's81-view-binding-v1':
            raise SystemExit(f'{t}: schema {tab.get("schema")!r}')
        for mst, rec in sorted(tab['bound'].items()):
            key = (mst, rec['files']['lef']['sha256'])
            if key in entries:
                entries[key]['binding_tables'].append(dict(path=t, sha256=sha256(raw)))
                continue
            entries[key] = qualify_entry(mst, rec, t, sha256(raw), a.rev, placed, lat, die_facts, MIRRORS)
            print(f'{mst}: ' + ' '.join(f'{o}={v["verdict"]}' for o, v in entries[key]['orientations'].items()),
                  file=sys.stderr)
    ents = sorted(entries.values(), key=lambda e: (e['master'], e['lef_sha256']))
    die_tab = a.die_binding or a.binding[0]
    used = [(e, o, v) for e in ents if any(t['path'] == die_tab for t in e['binding_tables'])
            for o, v in e['orientations'].items() if v['used_on_die']]
    fails = collections.Counter()
    for e, o, v in used:
        for c, cv in v['checks'].items():
            if cv['verdict'] != 'PASS':
                fails[c] += 1
    summary = dict(
        die_binding_table=die_tab, entries=len(ents), masters=len({e['master'] for e in ents}),
        used_mirrored_families=len({(e['master'], e['lef_sha256']) for e, o, v in used}),
        used_mirrored_pairs=len(used), used_mirrored_instances=sum(v['used_on_die'] for e, o, v in used),
        qualified_pairs=sum(v['verdict'] == 'PASS' for e, o, v in used),
        qualified_instances=sum(v['used_on_die'] for e, o, v in used if v['verdict'] == 'PASS'),
        failed_pairs=sum(v['verdict'] != 'PASS' for e, o, v in used),
        failed_instances=sum(v['used_on_die'] for e, o, v in used if v['verdict'] != 'PASS'),
        failed_pairs_by_check=dict(fails),
        all_entries_pass={o: sum(e['orientations'][o]['verdict'] == 'PASS' for e in ents) for o in MIRRORS})
    out = dict(schema=SCHEMA, tag=a.tag, tool='tools/s81/orientation_qualify.py',
               rule='An orientation of a bound closed view is permitted by this table only for the exact LEF sha256 and '
                    'only when every check of that orientation is PASS (tools/dsrom_s81_fulldie.py '
                    '--orientation-qualification). The literal LEF SYMMETRY contract is unchanged.',
               view_source_rev=subprocess.run(['git', '-C', str(ROOT), 'rev-parse', a.rev], capture_output=True,
                                              text=True).stdout.strip(),
               placement=dict(rows=a.placed, sources=dict(s.split('=', 1) for s in a.placed_source)),
               die_pg_lattice=lat, summary=summary, entries=ents)
    Path(a.out).write_text(json.dumps(out, indent=1) + '\n')
    print(json.dumps(summary, indent=1))


if __name__ == '__main__':
    main()
