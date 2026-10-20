#!/usr/bin/env python3
"""HBM-DIE10 10-20 DIE CHECKLIST (COORD 10-20 08:20): dense-face wire report of a GEN case, from the case's OWN pin views.

    die_dense_face_report.py CASE_DIR --contract CONTRACT.json[.gz] --out R.json [--dense-re RE] [--reach 405]

For every dense-face instance (HBM PHY phy_*, d2d / SerDes lk_* / ucie, host / ep endpoints, frame landings hbfd_land*)
every signal pin bit of its LEF view (CASE_DIR/views/*.lef = the views the GEN placed, SYNTH or hard) is paired with
the far-end pin bit of each contract edge on that bit; the wire is the Manhattan distance between the two placed pin
bits.  Per instance face (N/S/E/W = nearest side of the pin): bits, wires, max wire um, wires > reach, and the
per-crossing wire count (far-end instance) top 6.  The view kind (manifest 'views': SYNTH outline or hard/model LEF)
is printed per instance so a stand-in face is visible (S81 mu5k lesson: stand-in pins projected to the neighbour
centroid funnel a PHY face).  Exit 0 always (report, not a gate); the GEN packet carries the JSON.
"""
import argparse, collections, gzip, json, re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'hbm_die_v15'))
import case_reach as CR  # noqa: E402

DENSE = r'^(phy_|lk_|ucie|d2d|serdes|host_ep$|ep_[NS]\d)'   # frame landings: matched by master hbfd_land* below


def ld(p):
    return json.load(gzip.open(p, 'rt') if str(p).endswith('.gz') else open(p))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('case', type=Path); ap.add_argument('--contract', required=True); ap.add_argument('--out', required=True)
    ap.add_argument('--dense-re', default=DENSE); ap.add_argument('--reach', type=float, default=405.0)
    a = ap.parse_args()
    man = json.loads((a.case / 'manifest.json').read_text())
    pl = {n: dict(v, orient=v.get('orient', v.get('o')), master=v.get('master', v.get('m'))) for n, v in man['placement'].items()}
    rx = re.compile(a.dense_re)
    dense = {n for n, v in pl.items() if rx.search(n) or v['master'].startswith(('hbfd_land', 'ot_hbm3e_phy', 'ot_pdie_'))}
    c = ld(a.contract)
    peers = collections.defaultdict(lambda: collections.defaultdict(list))   # inst -> (port, bit) -> [(inst, port, bit)]
    want = set()
    for e in c['edges']:
        si, sp, slo, shi = e['source']; ki, kp, klo, khi = e['sink']
        if si not in dense and ki not in dense:
            continue
        want.update((si, ki))
        for b in range(shi - slo):
            if si in dense:
                peers[si][(sp, slo + b)].append((ki, kp, klo + b))
            if ki in dense:
                peers[ki][(kp, klo + b)].append((si, sp, slo + b))
    masters = {pl[n]['master'] for n in want if n in pl}
    L = {}
    for f in (a.case / 'views').glob('*.lef'):
        head = f.read_text()[:4000]
        if f.stem in masters or any(m in masters for m in re.findall(r'^MACRO (\S+)', head, re.M)):
            L.update(CR.lef(f))
    pos_cache = {}

    def pin(inst, port, bit):
        k = (inst, port, bit)
        if k in pos_cache:
            return pos_cache[k]
        v = pl.get(inst); r = None
        if v and v['master'] in L:
            lv = L[v['master']]
            p = lv['pins'].get(f'{port}[{bit}]') or (lv['pins'].get(port) if bit == 0 else None)
            if p:
                x, y = CR.xf(v, lv['w'], lv['h'], *p)
                ds = dict(W=p[0], E=lv['w'] - p[0], S=p[1], N=lv['h'] - p[1])
                if v['orient'] != 'R0':   # face in die frame: nearest side of the placed box
                    bw, bh = v.get('w', lv['w']), v.get('h', lv['h'])
                    ds = dict(W=x - v['x'], E=v['x'] + bw - x, S=y - v['y'], N=v['y'] + bh - y)
                r = (x, y, min(ds, key=ds.get))
        pos_cache[k] = r
        return r

    views = man.get('views', {})
    out = {}
    for n in sorted(dense):
        if n not in pl:
            continue
        faces = collections.defaultdict(lambda: dict(bits=0, wires=0, max_um=0.0, over_reach=0, nopin=0, cross=collections.Counter()))
        for (p, b), lst in peers.get(n, {}).items():
            me = pin(n, p, b)
            if me is None:
                faces['?']['nopin'] += 1; continue
            f = faces[me[2]]; f['bits'] += 1
            for (j, q, bb) in lst:
                o = pin(j, q, bb)
                if o is None:
                    f['nopin'] += 1; continue
                d = abs(o[0] - me[0]) + abs(o[1] - me[1])
                f['wires'] += 1; f['max_um'] = max(f['max_um'], round(d, 1)); f['over_reach'] += d > a.reach
                f['cross'][j] += 1
        if not faces:
            continue
        m = pl[n]['master']
        out[n] = dict(master=m, view=str(views.get(m, 'LEF'))[:60],
                      faces={k: dict(v, cross=v['cross'].most_common(6), crossings=len(v['cross'])) for k, v in sorted(faces.items())})
    summ = collections.defaultdict(lambda: dict(insts=0, wires=0, max_um=0.0, over_reach=0, max_cross_wires=0, nopin=0))
    for n, r in out.items():
        cls = ('PHY' if r['master'].startswith('ot_hbm3e_phy') else 'D2D_SERDES' if r['master'].startswith('ot_pdie_')
               else 'LANDING' if r['master'].startswith('hbfd_land') else 'HOST_EP')
        s = summ[cls]; s['insts'] += 1
        for f in r['faces'].values():
            s['wires'] += f['wires']; s['max_um'] = max(s['max_um'], f['max_um']); s['over_reach'] += f['over_reach']
            s['nopin'] += f['nopin']; s['max_cross_wires'] = max([s['max_cross_wires']] + [w for _, w in f['cross']])
    rep = dict(schema='opentallas.hbm.die_dense_face.v1', case=str(a.case), reach_um=a.reach, summary=dict(summ), instances=out)
    Path(a.out).write_text(json.dumps(rep, indent=1, default=str) + '\n')
    for k, s in sorted(summ.items()):
        print(f'DENSE_FACE {k} insts {s["insts"]} wires {s["wires"]} max_um {s["max_um"]} over_reach {s["over_reach"]} '
              f'max_wires_per_crossing {s["max_cross_wires"]} nopin {s["nopin"]}')
    for n, r in out.items():
        if r['master'].startswith(('ot_hbm3e_phy', 'ot_pdie_')):
            print('DENSE_FACE_INST', n, r['master'], r['view'][:20], ' '.join(
                f'{k}:w{v["wires"]}/max{v["max_um"]}/>R{v["over_reach"]}/x{v["crossings"]}/top{v["cross"][0][1] if v["cross"] else 0}'
                for k, v in r['faces'].items()))


if __name__ == '__main__':
    main()
