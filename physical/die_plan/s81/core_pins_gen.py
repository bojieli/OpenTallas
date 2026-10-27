"""S81-P9-HC 10-23: CORE-KS pin tables (inputs/core_pins/<module>.json) for the non-frame hard cores of gen_plan_v4.py
(NONFRAME_HC).  Same format and pick rule as the CORE-KS tables: per signal pin, the centre of its largest non-M1 rect
(USE POWER / GROUND skipped); then the core_pins_fix.py rule: a pin whose pick is off the kit track after the
[0.108, 0.012] core offset is re-pointed to another rect of the same pin on the same layer that is on track.
pinhash = sha256 of the sorted (dir, rects) per pin, 12 hex: same function as CORE-KS lefcmp.h, but over this
line parser's pins (lefcmp's regex truncates bus names at '[', so the hashes are not comparable across the two tools).
A LEF path is read from the worktree, else from git HEAD (sparse checkouts), else as a file (.zst decompressed).
usage (repo root): python3 physical/die_plan/s81/core_pins_gen.py [--force]"""
import hashlib, json, os, re, subprocess, sys
sys.path.insert(0, 'tools/die_plan'); sys.path.insert(0, 'physical/die_plan/s81')
import schema as S
import gen_plan_v4 as G

L = {x['name']: x for x in S.ASAP7_LAYERS}
OFF = tuple(G.CORE_TRACK_OFFSET)
OUT = 'physical/die_plan/s81/inputs/core_pins'


def read_lef(path):
    if os.path.exists(path):
        raw = open(path, 'rb').read()
    else:
        raw = subprocess.run(['git', 'show', 'HEAD:' + path], check=True, capture_output=True).stdout
    if path.endswith('.zst'):
        raw = subprocess.run(['zstd', '-dc'], input=raw, check=True, capture_output=True).stdout
    return raw.decode()


def parse(txt, mod):
    """like CORE-KS lefcmp.parse, line-based (fast on large LEFs; full bus pin names): size, {pin: (dir, sorted rects (layer, x0, y0,
    x1, y1))}, + {pin: use}"""
    inm, size, pins, use, cur = False, None, {}, {}, None
    for ln in txt.splitlines():
        t = ln.split()
        if not t:
            continue
        if not inm:
            inm = t[0] == 'MACRO' and len(t) > 1 and t[1] == mod
            continue
        if t[0] == 'END' and len(t) > 1 and t[1] == mod and cur is None:
            break
        if cur is None:
            if t[0] == 'SIZE' and size is None:
                size = (float(t[1]), float(t[3]))
            elif t[0] == 'PIN':
                cur, d, u, geo, layer = t[1], None, 'SIGNAL', [], None
            continue
        if t[0] == 'END' and len(t) > 1 and t[1] == cur:
            pins[cur] = (d, tuple(sorted(geo)))
            use[cur] = u
            cur = None
        elif t[0] == 'DIRECTION' and d is None:
            d = t[1]
        elif t[0] == 'USE' and u == 'SIGNAL':
            u = t[1].rstrip(';')
        elif t[0] == 'LAYER':
            layer = t[1]
        elif t[0] == 'RECT':
            geo.append((layer,) + tuple(round(float(x), 3) for x in t[1:5]))
    if not inm or size is None:
        raise SystemExit('%s: no MACRO/SIZE in LEF' % mod)
    return size, pins, use


def pinhash(p):
    return hashlib.sha256(json.dumps(sorted(p.items())).encode()).hexdigest()[:12]


def ontrack(ln, x, y):
    l_ = L[ln]
    c = (x + OFF[0]) if l_['dir'] == 'V' else (y + OFF[1])
    k = (c - l_['offset_um']) / l_['pitch_um']
    return abs(k - round(k)) < 1e-4


def table(mod, lef):
    size, pins, use = parse(read_lef(lef), mod)
    out, fixed = [], 0
    for name in sorted(pins):
        if use[name] in ('POWER', 'GROUND'):
            continue
        rs = [r for r in pins[name][1] if r[0] != 'M1' and r[0] in L]
        if not rs:
            continue
        big = max(rs, key=lambda r: (r[3] - r[1]) * (r[4] - r[2]))   # first largest (sorted order)
        x, y = round((big[1] + big[3]) / 2, 4), round((big[2] + big[4]) / 2, 4)
        if not ontrack(big[0], x, y):
            alt = [r for r in rs if r[0] == big[0] and ontrack(r[0], (r[1] + r[3]) / 2, (r[2] + r[4]) / 2)]
            if alt:
                x, y = round((alt[0][1] + alt[0][3]) / 2, 4), round((alt[0][2] + alt[0][4]) / 2, 4)
                fixed += 1
        out.append(dict(name=name, layer=big[0], x=x, y=y))
    src = 'S81-P9-HC 10-23 from LEF %s (largest non-M1 rect centre, CORE-KS rule)' % lef
    if fixed:
        src += '; %d multi-port pins re-pointed to their on-track access rect (core_pins_fix rule)' % fixed
    return dict(module=mod, lef=lef, source=src, pinhash=pinhash(pins), pins=out), size


def main():
    force = '--force' in sys.argv
    mods = {}
    for spec in G.NONFRAME_HC.values():
        for c in spec['cores']:
            mods[c['module']] = c['lef']
    for mod, lef in sorted(mods.items()):
        f = os.path.join(OUT, mod + '.json')
        if os.path.exists(f) and not force:
            print('keep', f)
            continue
        j, size = table(mod, lef)
        json.dump(j, open(f, 'w'), indent=0)
        print('wrote %s: %d pins, size %s' % (f, len(j['pins']), size))


if __name__ == '__main__':
    main()
