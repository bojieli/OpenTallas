#!/usr/bin/env python3
"""QK-FWD 10-18 (owner: few tile variants; coordinator: one hardened master per width / direction / frame class):
the Qwen compute die's forwarded half-cycle lane frames (OT_SPLIT_FWD_LANES=1: qfd_rlyh0_ / qfd_rlyh_ / qfd_landh0_ /
qfd_landh_<W>_<FiFo>_<w>x<h>, one master per GEN frame: 147 on dv2f14bn, 164 on dv2f14bg) deduplicated into CLASS masters.

  width class   Wc = 1 (W = 1), 128 (2 <= W <= 128), 600 (129 <= W <= 600); W is quantised UP, the spare a[W..Wc-1]
                inputs are tied low by the die (tie_lo of the frame) and the spare b[W..Wc-1] outputs left open
  direction     4 classes under the row-legal orientations (frames are SHAVE-mirror-legal on M4/M5):
                  H  straight E<->W   (rep EW;  WE = MY)
                  V  straight N<->S   (rep NS;  SN = MX)
                  HV in E/W, out N/S  (rep EN;  ES = MX, WN = MY, WS = R180)
                  VH in N/S, out E/W  (rep NE;  SE = MX, NW = MY, SW = R180)
                a class may take another member of its group as the rep (the closed 1-bit views keep their faces:
                rlyh_1 V = SN, rlyh0_1 VH = SW); the orientation maps the rep onto the GEN frame's faces
  frame         Wc 1 / 128: 64.776 x 30.216 (the GEN corridor relay frame) for every direction (128 + epoch pin on a
                30.2-um E/W face = 4.4 pins/um);  Wc 600: every data face >= 600 / 6 + 4 um (<= 6 pins/um, tile review
                checklist), the area >= the D 4 landing's 2.8 um2/bit / 0.55:  V 104.088 x 60.456 (the GEN's own
                landing-size formula at 600 b), H 64.776 x 105.816, HV / VH 104.088 x 105.816

    fwd_lane_classes.py table --pins GEN/out/pins [...] --out class_table.json   map GEN masters -> class + orientation
    fwd_lane_classes.py pins  --out DIR [--classes ...]                          class pin files for gen_fwd_lane_kits.py
"""
import argparse, json, math, re, sys
from pathlib import Path

FAMS = ('rlyh0', 'rlyh', 'landh0', 'landh')
# Q-H16C 10-18: the forwarded RESET lanes (ot_qfd_rlane_st / ot_qfd_rlane_land, 1 b) -- width class 1 only
RST_FAMS = ('rlyr0', 'rlyr', 'rlyrl')
WCLS = (1, 128, 600)
GROUP = {'EW': 'H', 'WE': 'H', 'NS': 'V', 'SN': 'V', 'EN': 'HV', 'ES': 'HV', 'WN': 'HV', 'WS': 'HV',
         'NE': 'VH', 'SE': 'VH', 'NW': 'VH', 'SW': 'VH'}
REP = {'H': 'EW', 'V': 'NS', 'HV': 'EN', 'VH': 'NE'}
# closed 1-bit views (qfwd_*-f2-9ddc1acf2 / -f1-93960f2c9, native BINDABLE / BINDABLE with the k* case) keep their faces
REP_OVERRIDE = {('rlyh', 1, 'V'): 'SN', ('rlyh0', 1, 'VH'): 'SW'}
GX, GY, SHAVE = 0.432, 2.16, 0.024
MIRROR = {'R0': {}, 'MX': {'N': 'S', 'S': 'N'}, 'MY': {'E': 'W', 'W': 'E'}, 'R180': {'N': 'S', 'S': 'N', 'E': 'W', 'W': 'E'}}
IN_PORTS = {'rlyh0': ('a',), 'rlyh': ('a', 'ea'), 'landh0': ('a',), 'landh': ('a', 'ea'), 'rlyr0': ('a',), 'rlyr': ('a',),
            'rlyrl': ('a',)}
OUT_PORTS = {'rlyh0': ('b', 'eb'), 'rlyh': ('b', 'eb'), 'landh0': ('b',), 'landh': ('b',), 'rlyr0': ('b',), 'rlyr': ('b',),
             'rlyrl': ('b',)}
AREA = {'rlyh0': ('ck', 'en', 'ck_o'), 'rlyh': ('ckf', 'ck_o'),
        'landh': ('ckf', 'ck', 'rs', 'k0', 'k1', 'k2', 'tie_hi', 'tie_lo', 'fault'),
        'landh0': ('ck_s', 'en', 'ck', 'rs', 'k0', 'k1', 'k2', 'tie_hi', 'tie_lo', 'fault'),
        'rlyr0': ('ck', 'ck_o'), 'rlyr': ('ckf', 'ck_o'), 'rlyrl': ('ck',)}
NAME = re.compile(r'^qfd_(rlyh0|rlyh|landh0|landh|rlyr0|rlyrl|rlyr)_(\d+)_([NSEW]{2})_(\d+)x(\d+)$')


def up(x, g):
    return math.ceil(x / g - 1e-9) * g


def wclass(W):
    for q in WCLS:
        if W <= q:
            return q
    raise SystemExit(f'width {W} > {WCLS[-1]}: add a width class')


def frame(Wc, grp):
    if Wc <= 128:
        return 64.776, 30.216
    face = Wc / 6.0 + 4.0
    wv = round(up(face, GX) - SHAVE, 3)
    hh = round(up(face, GY) - SHAVE, 3)
    hv = round(max(up(2.8 * Wc / 0.55 / wv, GY), 60.48) - SHAVE, 3)
    return {'V': (wv, hv), 'H': (64.776, hh), 'HV': (wv, hh), 'VH': (wv, hh)}[grp]


def rep_faces(fam, Wc, grp):
    return REP_OVERRIDE.get((fam, Wc, grp), REP[grp])


def class_name(fam, Wc, grp):
    w, h = frame(Wc, grp)
    return f'qfd_{fam}_{Wc}_{rep_faces(fam, Wc, grp)}_{round(w)}x{round(h)}'


def orient(rep, faces):
    for o, mp in MIRROR.items():
        if ''.join(mp.get(c, c) for c in rep) == faces:
            return o
    raise ValueError(f'no row-legal orientation maps {rep} onto {faces}')


def classify(m):
    g = NAME.match(m)
    if not g:
        return None
    fam, W, fc = g.group(1), int(g.group(2)), g.group(3)
    Wc, grp = wclass(W), GROUP[fc]
    if fam in RST_FAMS and Wc != 1:
        raise SystemExit(f'{m}: reset lane wider than 1 b: add a reset width class')
    rep = rep_faces(fam, Wc, grp)
    return dict(master=m, family=fam, bits=W, faces=fc, cls=class_name(fam, Wc, grp), class_bits=Wc, group=grp,
                rep_faces=rep, orient=orient(rep, fc), spare_bits=Wc - W, class_frame=list(frame(Wc, grp)),
                gen_frame=[int(g.group(4)), int(g.group(5))])


def all_classes():
    return [class_name(f, w, g) for f in FAMS for w in WCLS for g in ('H', 'V', 'HV', 'VH')] + \
        [class_name(f, 1, g) for f in RST_FAMS for g in ('H', 'V', 'HV', 'VH')]


def class_pins(cn):
    g = NAME.match(cn)
    fam, Wc, rep = g.group(1), int(g.group(2)), g.group(3)
    w, h = frame(Wc, GROUP[rep])
    ports, faces = {}, {}

    def place(port, face, bits, lo, pitch):
        r0 = round(lo, 3)
        ports[port] = dict(face=face, layer='M5' if face in 'NS' else 'M4', bits=bits,
                           range_um=[r0, round(r0 + pitch * (bits - 1), 3)], bit0_at='lo',
                           direction='output' if port in OUT_PORTS[fam] else 'input', peer=None)
        faces.setdefault(face, []).append(port)
        return r0 + pitch * bits
    for face, plist in ((rep[0], IN_PORTS[fam]), (rep[1], OUT_PORTS[fam])):
        span = w if face in 'NS' else h
        need = (Wc + len(plist) - 1)
        pitch = min(0.192, max(0.048, math.floor((span - 4.0) / need / 0.048) * 0.048))
        x = (span - pitch * need) / 2
        for p in plist:
            x = place(p, face, Wc if p in ('a', 'b') else 1, x, pitch)
    for i, p in enumerate(AREA[fam]):
        ports[p] = dict(face='S', layer='M8', bits=1, range_um=[round(w / 2, 3)] * 2, bit0_at='lo',
                        direction='output' if p in ('ck_o', 'tie_hi', 'tie_lo', 'fault') else 'input', peer=None,
                        interior=True, positions_xy_um=[[round(w / 2 - 0.8 + 1.6 * (i % 2), 3), round(h / 2 - 3 + 1.6 * (i // 2), 3)]])
    return dict(schema='opentallas.qwen-tp8.assigned-pins.v1', master=cn, outline=dict(w=w, h=h), instances=None,
                pins=faces, pin_ranges={p: v['range_um'] for p, v in ports.items() if not v.get('interior')}, ports=ports,
                overlapping_pin_pairs=0,
                note=('QK-FWD class master (tools/qwen_split/fwd_lane_classes.py): data faces of the class rep, '
                      'positions informational (the flow places the face pins; the die adopts the view pins); centre '
                      'area pins go to the free face in the kit'))


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sp = ap.add_subparsers(dest='cmd', required=True)
    t = sp.add_parser('table')
    t.add_argument('--pins', nargs='+', type=Path, required=True)
    t.add_argument('--out', type=Path, required=True)
    p = sp.add_parser('pins')
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--classes', nargs='*')
    a = ap.parse_args()
    if a.cmd == 'table':
        rows, other = {}, set()
        for d in a.pins:
            for f in sorted(d.glob('qfd_*.json')):
                j = json.loads(f.read_text())
                r = classify(j['master'])
                if r is None:
                    if j['master'].startswith(('qfd_rlyr', 'qfd_landh', 'qfd_rlyh')):
                        other.add(j['master'])
                    continue
                r.setdefault('instances', {})[d.parent.parent.name if d.name == 'pins' else str(d)] = j.get('instances')
                rows.setdefault(r['master'], r)['instances'].update(r['instances'])
        cls = {}
        for r in rows.values():
            c = cls.setdefault(r['cls'], dict(cls=r['cls'], family=r['family'], class_bits=r['class_bits'], group=r['group'],
                                              rep_faces=r['rep_faces'], frame=r['class_frame'], members=[]))
            c['members'].append(dict(master=r['master'], orient=r['orient'], bits=r['bits'], spare_bits=r['spare_bits'],
                                     instances=r['instances']))
        out = dict(schema='opentallas.qwen_split.fwd_lane_classes.v1', tool='tools/qwen_split/fwd_lane_classes.py',
                   sources=[str(d) for d in a.pins], masters=len(rows), classes_used=len(cls), classes_all=len(all_classes()),
                   not_classed=sorted(other), rule=__doc__.split('\n\n')[1] if '\n\n' in __doc__ else '',
                   die_obligation=('GEN: emit the class master name + orient per frame (orient maps the class rep faces onto '
                                   'the frame faces), class frame size, a[W..Wc-1] from the frame tie_lo, b[W..Wc-1] open'),
                   classes=dict(sorted(cls.items())), map={m: dict(cls=r['cls'], orient=r['orient'], spare_bits=r['spare_bits'])
                                                          for m, r in sorted(rows.items())})
        a.out.write_text(json.dumps(out, indent=1) + '\n')
        print(f"{len(rows)} masters -> {len(cls)} classes (of {len(all_classes())}); not classed: {sorted(other)}")
    else:
        a.out.mkdir(parents=True, exist_ok=True)
        for cn in a.classes or all_classes():
            (a.out / f'{cn}.json').write_text(json.dumps(class_pins(cn), indent=1) + '\n')
            print(cn)


if __name__ == '__main__':
    main()
