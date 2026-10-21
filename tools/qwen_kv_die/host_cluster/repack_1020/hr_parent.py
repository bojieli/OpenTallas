#!/usr/bin/env python3
"""KV-HROOT10 10-20: qkd_hr_cluster (KV host root parent, CRITICAL qkd_host_root) repack planner + stand-in generator.

    hr_parent.py eval  VARIANT            lane lengths (pin-to-pin manhattan per net) + face pin density for a placement
    hr_parent.py emit  VARIANT OUTDIR     stand-in views (peer / prompt / ingest_qm, STANDIN_NOT_A_VIEW) + spec.json

Inputs (scratch, from tools/conn.py on rtl/qwen_sys/host_cluster_20261017/qkd_hr_cluster.v): netbits.json (instance port
bit -> net), conn.json (top port widths / directions).  Closed child pins come from the CLOSED view LEFs on origin/main;
the peer stand-in takes the pin faces / ranges of the live 518.4-sq gate kit qkd_hr_core_peer_p32e (KV-HOST9A); prompt
and ingest_qm stand-ins get PARENT-ASSIGNED faces (top-down rule: unclosed tiles are pinned by the parent): every port on
the face toward the centroid of its peers in this placement.
"""
import collections
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
S = HERE
NB = json.load(open(S / 'netbits.json'))
CJ = json.load(open(S / 'conn.json'))
LAT = 43.2

R = 'physical/ref_tile'
CLOSED = {   # inst -> (view dir, cell)
    **{f'u_rank__u_adapter__g_slice_{i}___u_slice': (f'{R}/qfd_link_adp128/views/qfd_link_adp128', 'qfd_link_adp128')
       for i in range(8)},
    'u_rank__u_control__u_packet__u_rx': (f'{R}/qkd_hr_core_rx/views/qkd_host_rx_class_admission_rr', 'qkd_host_rx_class_admission_rr'),
    'u_rank__u_phy__u_pad': (f'{R}/qkd_hr_phy_pad/views/qkd_host_rx_pad5', 'qkd_host_rx_pad5'),
    'u_cdc_pc': (f'{R}/qkd_hr_cdc_pc/views/qkd_hr_cdc_pc', 'qkd_hr_cdc_pc'),
    'u_core_tx': (f'{R}/qkd_hr_core_tx/views/qkd_hr_core_tx', 'qkd_hr_core_tx'),
    'u_core_guard': (f'{R}/qkd_hr_core_guard/views/qkd_hr_core_guard', 'qkd_hr_core_guard'),
    'u_core_order': (f'{R}/qkd_hr_core_order/views/qkd_hr_core_order', 'qkd_hr_core_order'),
    'u_core_queue': (f'{R}/qkd_hr_core_queue/views/qkd_hr_core_queue', 'qkd_hr_core_queue'),
    'u_cdc_host': (f'{R}/qkd_hr_cdc_host/views/qkd_hr_cdc_host', 'qkd_hr_cdc_host'),
}
STANDIN = {  # inst -> (cell, w, h, clocks, rtl file for directions)
    'u_core_peer': ('qkd_hr_core_peer', 518.4, 518.4, ['ck_core'], 'rtl/qwen_sys/host_cluster_20261017/qkd_hr_core_peer.v'),
    'u_core_prompt': ('qkd_hr_core_prompt', 475.2, 432.0, ['ck_core'], 'rtl/qwen_sys/host_cluster_20261017/qkd_hr_core_prompt.v'),
    'u_ingest_qm': ('qkd_hr_ingest_qm', 345.6, 345.6, ['ck_core', 'ck_host', 'ck_ingest'], 'rtl/qwen_sys/host_cluster_20261017/qkd_hr_ingest_qm.v'),
}
CLOCKS = ('ck_core', 'ck_host', 'ck_ingest', 'ck_phy_fam', 'ck_phy')


def gshow(p):
    return subprocess.run(['git', '-C', '/home/ubuntu/OpenTallas', 'show', 'origin/main:' + p], capture_output=True,
                          text=True, check=True).stdout


def lef_pins(text):
    W, H = map(float, re.search(r'SIZE (\S+) BY (\S+)', text).groups())
    out = {}
    for pm in re.finditer(r'^  PIN (\S+)(.*?)^  END \1', text, re.S | re.M):
        n = pm.group(1)
        if n in ('VDD', 'VSS'):
            continue
        r = re.search(r'RECT\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)', pm.group(2))
        if not r:
            continue
        x0, y0, x1, y1 = map(float, r.groups())
        out[n] = ((x0 + x1) / 2, (y0 + y1) / 2)
    return W, H, out


def rtl_dirs(path):
    t = gshow(path)
    d = {}
    for kind in ('input', 'output'):
        for w, n in re.findall(rf'^\s*{kind}\s+(?:wire\s+)?(\[[^\]]*\])?\s*(\w+)', t, re.M):
            d[n] = kind
    return d


def face_of(x, y, w, h):
    return min((('W', x), ('E', w - x), ('S', y), ('N', h - y)), key=lambda t: t[1])[0]


def orient_xy(x, y, w, h, o):
    if o in ('MX', 'R180'):
        y = h - y
    if o in ('MY', 'R180'):
        x = w - x
    return x, y


def peer_kit_pins(w, h):
    """bit -> local xy for the peer stand-in from the p32e kit pins/pin_ranges (evenly spread)."""
    s = json.load(open(S / 'p32e_spec.json'))
    pr = s.get('pin_ranges', {})
    widths = {p: len(b) for p, b in NB['inst']['u_core_peer'].items()}
    out = {}
    for face, names in s['pins'].items():
        # names sharing a range are interleaved along it in order
        groups = collections.defaultdict(list)
        for n in names:
            lo, hi = pr.get(n, (0.1 * (h if face in 'EW' else w), 0.9 * (h if face in 'EW' else w)))
            groups[(round(lo, 3), round(hi, 3))].append(n)
        for (lo, hi), ns in groups.items():
            bits = [(n, i) for n in ns for i in range(widths.get(n, 1))]
            for k, (n, i) in enumerate(bits):
                pos = lo + (hi - lo) * (k + 0.5) / len(bits)
                xy = {'W': (0.0, pos), 'E': (w, pos), 'S': (pos, 0.0), 'N': (pos, h)}[face]
                out[f'{n}[{i}]' if widths.get(n, 1) > 1 else n] = (face, xy)
    return out


def load(variant):
    V = json.load(open(variant))
    blocks = {}
    for inst, (vd, cell) in CLOSED.items():
        W, H, pins = lef_pins(gshow(f'{vd}/{cell}.lef'))
        blocks[inst] = dict(cell=cell, w=W, h=H, pins=pins, view=vd, standin=False)
    for inst, (cell, w, h, cks, rtl) in STANDIN.items():
        blocks[inst] = dict(cell=cell, w=w, h=h, pins={}, standin=True, clocks=cks, rtl=rtl)
    for inst, p in V['place'].items():
        blocks[inst].update(x=p[0], y=p[1], o=p[2] if len(p) > 2 else 'R0')
    return V, blocks


def net_members(blocks):
    nets = collections.defaultdict(list)     # net -> [(inst, pin bit name)]
    for inst, ports in NB['inst'].items():
        for p, bits in ports.items():
            for i, n in enumerate(bits):
                nm = f'{p}[{i}]' if len(bits) > 1 else p
                nets[n].append((inst, nm, p))
    for p, bits in NB['ports'].items():
        for i, n in enumerate(bits):
            nets[n].append(('PORT', f'{p}[{i}]' if len(bits) > 1 else p, p))
    return nets


def assign_standins(V, blocks, nets):
    """parent-assigned faces for prompt / ingest stand-ins; p32e faces for the peer."""
    def centre(b):
        return b['x'] + b['w'] / 2, b['y'] + b['h'] / 2
    PW, PH = V['outline']
    for inst, b in blocks.items():
        if not b['standin']:
            continue
        w, h = b['w'], b['h']
        if inst == 'u_core_peer' and V.get('peer_pins', 'p32e') == 'p32e':
            pk = peer_kit_pins(w, h)
            for nm, (face, xy) in pk.items():
                b['pins'][nm] = xy
            continue
        # per port: face toward peers' centroid; bits packed at DENS/um around the partner's projection on that face
        ports = NB['inst'][inst]
        perface = collections.defaultdict(list)
        prefs = []
        cx, cy = centre(b)
        for p, bits in ports.items():
            if p in CLOCKS:
                continue
            sx = sy = k = 0
            for n in bits:
                for (oi, onm, op) in nets[n]:
                    if oi == inst:
                        continue
                    if oi == 'PORT':
                        f = V.get('port_face', {}).get(op) or face_of(cx, cy, PW, PH)
                        tx, ty = {'W': (0, cy), 'E': (PW, cy), 'S': (cx, 0), 'N': (cx, PH)}[f]
                    else:
                        ob = blocks[oi]
                        q = gxy(ob, onm) if not ob['standin'] else None
                        tx, ty = q if q else centre(ob)
                    sx += tx; sy += ty; k += 1
            tx, ty = (sx / k, sy / k) if k else (cx, b['y'])
            # local frame: undo the orientation flips
            lx, ly = tx - b['x'], ty - b['y']
            if b['o'] in ('MY', 'R180'):
                lx = w - lx
            if b['o'] in ('MX', 'R180'):
                ly = h - ly
            # faces by distance from the target to each face segment
            def segd(f):
                if f in 'EW':
                    fx = w if f == 'E' else 0.0
                    return abs(lx - fx) + max(0.0, abs(ly - h / 2) - h / 2)
                fy = h if f == 'N' else 0.0
                return abs(ly - fy) + max(0.0, abs(lx - w / 2) - w / 2)
            order = sorted('NSEW', key=segd)
            fixed = V.get('standin_face', {}).get(f'{inst}.{p}')
            prefs.append((len(ports[p]), p, [fixed] if fixed else order, lx, ly))
        DENS = float(V.get('standin_pins_per_um', 4.0))
        cap = {f: 0.9 * (h if f in 'EW' else w) * DENS for f in 'NSEW'}
        used = collections.Counter()
        for n, p, order, lx, ly in sorted(prefs, reverse=True):
            f = next((f for f in order if used[f] + n <= cap[f]), order[0])
            used[f] += n
            perface[f].append(((ly if f in 'EW' else lx), p))
        for f, ps in perface.items():
            L = h if f in 'EW' else w
            lo_l, hi_l = 0.04 * L, 0.96 * L
            spans = []
            for along, p in sorted(ps):
                n = len(ports[p]); s = n / DENS
                a = min(max(along - s / 2, lo_l), hi_l - s)
                spans.append([a, s, p])
            # sweep right then left to remove overlaps
            for i in range(1, len(spans)):
                spans[i][0] = max(spans[i][0], spans[i - 1][0] + spans[i - 1][1])
            if spans and spans[-1][0] + spans[-1][1] > hi_l:
                spans[-1][0] = hi_l - spans[-1][1]
                for i in range(len(spans) - 2, -1, -1):
                    spans[i][0] = min(spans[i][0], spans[i + 1][0] - spans[i][1])
            if spans and spans[0][0] < lo_l - 1e-6:
                raise SystemExit(f'stand-in {inst} face {f}: {sum(s[1] for s in spans):.0f} um of pins > face {L}')
            for a, s, p in spans:
                n = len(ports[p])
                for i in range(n):
                    pos = a + s * (i + 0.5) / n
                    b['pins'][f'{p}[{i}]' if n > 1 else p] = {'W': (0.0, pos), 'E': (w, pos), 'S': (pos, 0.0), 'N': (pos, h)}[f]
        for k, c in enumerate(b['clocks']):
            b['pins'][c] = (w / 2 + 4.32 * k, 0.0)


def gxy(b, nm):
    if nm not in b['pins']:
        return None
    x, y = b['pins'][nm]
    x, y = orient_xy(x, y, b['w'], b['h'], b['o'])
    return b['x'] + x, b['y'] + y


def evaluate(V, blocks, nets, quiet=False):
    PW, PH = V['outline']
    lanes = collections.defaultdict(list)     # (a, b) -> distances
    portface = collections.defaultdict(lambda: collections.Counter())
    portpos = {}
    for n, mem in nets.items():
        pts = []
        tops = []
        for inst, nm, p in mem:
            if inst == 'PORT':
                tops.append((nm, p))
                continue
            if p in CLOCKS:
                continue
            xy = gxy(blocks[inst], nm)
            if xy is None:
                continue
            pts.append((inst, xy))
        # broadcast nets (resets / straps / shared status, >= 4 child pins) are reported apart
        if len(pts) >= 4:
            xs = [q[1][0] for q in pts]; ys = [q[1][1] for q in pts]
            lanes[('BROADCAST', n.split('[')[0])].append((max(xs) - min(xs)) + (max(ys) - min(ys)))
            pts = pts[:1] if tops else []
        for i in range(len(pts)):
            for j in range(i + 1, len(pts)):
                (a, pa), (bb, pb) = pts[i], pts[j]
                d = abs(pa[0] - pb[0]) + abs(pa[1] - pb[1])
                lanes[tuple(sorted((a, bb)))].append(d)
        for nm, p in tops:
            if p in CLOCKS or not pts:
                continue
            # parent pin at the projection of the (first) child pin onto the chosen face
            inst, (x, y) = pts[0]
            f = V.get('port_face', {}).get(p) or face_of(x, y, PW, PH)
            d = {'W': x, 'E': PW - x, 'S': y, 'N': PH - y}[f]
            pos = y if f in 'EW' else x
            portface[f][p] += 1
            portpos[nm] = (f, pos)
            lanes[(inst, 'PORT:' + f)].append(d)
    rows = []
    for k, ds in lanes.items():
        rows.append((max(ds), sum(ds) / len(ds), len(ds), k))
    rows.sort(reverse=True)
    over = sum(1 for k, ds in lanes.items() if k[0] != 'BROADCAST' for d in ds if d > 405)
    if not quiet:
        print(f'outline {PW} x {PH} = {PW * PH / 1e6:.3f} mm2; child area {sum(b["w"] * b["h"] for b in blocks.values()) / 1e6:.3f}')
        print(f'bits > 405 um: {over}')
        for mx, mean, n, k in [r for r in rows if r[2] >= 8 or r[3][0] == 'BROADCAST'][:30]:
            print(f'  max {mx:7.1f} mean {mean:7.1f} bits {n:5d}  {k[0].replace("u_rank__u_", "")} - {k[1].replace("u_rank__u_", "")}')
        for f in 'NSEW':
            tot = sum(portface[f].values())
            L = PH if f in 'EW' else PW
            print(f'  face {f}: {tot} bits over {L} um = {tot / L:.2f}/um  top {portface[f].most_common(6)}')
    # overlaps / outline
    bl = list(blocks.items())
    for i in range(len(bl)):
        a = bl[i][1]
        if a['x'] < 21.6 - 1e-6 or a['y'] < 21.6 - 1e-6 or a['x'] + a['w'] > PW - 21.6 + 1e-6 or a['y'] + a['h'] > PH - 21.6 + 1e-6:
            print('  OUTSIDE', bl[i][0])
        if abs(a['x'] / LAT - round(a['x'] / LAT)) > 1e-6 or abs(a['y'] / LAT - round(a['y'] / LAT)) > 1e-6:
            print('  OFF-LATTICE', bl[i][0], a['x'], a['y'])
        for j in range(i + 1, len(bl)):
            b = bl[j][1]
            gx = max(b['x'] - (a['x'] + a['w']), a['x'] - (b['x'] + b['w']))
            gy = max(b['y'] - (a['y'] + a['h']), a['y'] - (b['y'] + b['h']))
            if gx < 21.6 - 1e-6 and gy < 21.6 - 1e-6:
                print('  OVERLAP/GAP<21.6', bl[i][0], bl[j][0], round(gx, 1), round(gy, 1))
    return rows, over, portface, portpos


def main():
    cmd, variant = sys.argv[1], sys.argv[2]
    V, blocks = load(variant)
    nets = net_members(blocks)
    assign_standins(V, blocks, nets)
    rows, over, portface, portpos = evaluate(V, blocks, nets)
    if cmd == 'emit':
        import hr_emit
        hr_emit.emit(V, blocks, nets, rows, over, portface, portpos, Path(sys.argv[3]))


if __name__ == '__main__':
    main()
