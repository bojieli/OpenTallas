#!/usr/bin/env python3
"""VM bank strap masters re-granted at 270 x 270 um (H-DIE 2026-10-15 22:10 stream; H-SM accepted vm_bank_resize_v7_proposal
on condition that N/S also get two pin layers).

Measured reason (H-SM): strap routes at 356.4 x 365.04 fail TT -71.17 (q2/q3, SECDED cone + ~430 ps face wire) and
TT -149.91 / FF -21.13 (q0: dq_v pin flop -> ~400 ps wire -> write mux; insertion 670-720 ps on 5.9k sinks at 33 % fill).
The slot is pin-perimeter bound; 270 x 270 holds the 3 x 1024x256 SRAM stack (36,950 um2) + ~4,400 um2 std at ~57 % fill.

Pins: same faces, same pin order and bit order as vm_strap_grants_2116.json, every face on TWO layers:
  W/E (horizontal): M4 y = 0.012 + 0.048 k  and  M6 y = 0.016 + 0.064 k
  N/S (vertical)  : M5 x = 0.012 + 0.048 k (clear of the tile M5 PG stripes, as the 1015 rule) and M7 x = 0.016 + 0.064 k
  per layer bit pitch >= 0.288 um; the two layers interleave; the bits are SPREAD over the whole usable face (no crowded
  strip).  clk / rst_n / bid / sid keep their M5 tracks and relative spacing, moved to the N-face centre (clock entry N
  centre).  Layer contract: tile signals M2-M5 inside, pins up to M7 (layer_cap M7 grant for the bank tiles): the die
  PDN must leave the M6/M7 pin windows at the W/E/N/S edges free (parent straps stop >= 1 um inside, or skip the pin
  rows) -- recorded as a die-PDN obligation, not assumed met.
"""
import copy, hashlib, json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
DIR = ROOT / 'results/arch/hbm_die_v15'
SRC = DIR / 'vm_strap_grants_2116.json'
OUT = DIR / 'vm_strap_grants_2210.json'
W = H = 270.0
CORE = 2.16
LO, HI = 2.2, 270.0 - 2.2
PITCH = 0.192          # v4 (layer_cap M6, PG on M6): one pin layer per face, 4 tracks
CLOCKISH = ('clk', 'rst_n', 'bid[2:0]', 'sid[1:0]')


def track(off, p, lo, hi, ok=lambda c: True, pitch=None):
    pitch = pitch or PITCH
    out, last = [], -1e9
    k = int((lo - off) / p) + 1
    while off + k * p <= hi + 1e-9:
        c = round(off + k * p, 6); k += 1
        if c - last >= pitch - 1e-9 and ok(c):
            out.append(c); last = c
    return out


PG = []
k = 0
while CORE + .3 + 5.4 * k - .06 < W:
    a = CORE + .3 + 5.4 * k - .06; PG += [(a, a + .12), (a + .192, a + .312)]; k += 1
m5ok = lambda c: True   # v4: tile PG on M6 (layer_cap M6 grant), M5 carries no stripes


def slots(face, lo, hi, need=0):
    # 0.192 um (4 tracks) unless that fills > 90 % of the face, then 0.144 um (3 tracks)
    L = 'M4' if face in 'WE' else 'M5'
    t = track(.012, .048, lo, hi)
    if need > 0.9 * len(t):
        t = track(.012, .048, lo, hi, pitch=.144)
    return [(c, L) for c in t]      # PG is on M6 in the cap-M6 contract: no M5 stripes


def spread(avail, n):
    assert n <= len(avail), (n, len(avail))
    if n == 0:
        return []
    if n == 1:
        return [avail[len(avail) // 2]]
    return [avail[round(i * (len(avail) - 1) / (n - 1))] for i in range(n)]


def regrant(s):
    s = copy.deepcopy(s)
    pins = s['pins']
    old_clk = next(p for p in pins if p['name'] == 'clk')['bit_centres_um'][0]
    ck = [p for p in pins if p['name'] in CLOCKISH]
    # clock group: shift by a multiple of 0.048 so every centre stays a legal PG-clear M5 track, nearest the N centre
    best = None
    for j in range(-200, 201):
        d = round(W / 2 - old_clk + j * .048, 6)
        d = round(round(d / .048) * .048, 6)
        cs = [round(c + d, 6) for p in ck for c in p['bit_centres_um']]
        if all(m5ok(c) and LO <= c <= HI for c in cs):
            if best is None or abs(cs[0] - W / 2) < abs(best[1] - W / 2):
                best = (d, cs[0])
    d = best[0]
    ck_lo = min(c + d for p in ck for c in p['bit_centres_um']) - .3
    ck_hi = max(c + d for p in ck for c in p['bit_centres_um']) + .3
    for p in ck:
        p['bit_centres_um'] = [round(c + d, 6) for c in p['bit_centres_um']]
        p['offset'] = round((p['bit_centres_um'][0] + p['bit_centres_um'][-1]) / 2, 6)
        p['span_um'] = [round(p['bit_centres_um'][0] - .048, 6), round(p['bit_centres_um'][-1] + .048, 6)]
    out_pins = list(ck)
    for face in 'NSWE':
        fp = sorted([p for p in pins if p['face'] == face and p['name'] not in CLOCKISH], key=lambda p: p['bit_centres_um'][0])
        if not fp:
            continue
        if face == 'N':
            before = [p for p in fp if p['bit_centres_um'][0] < old_clk]; after = [p for p in fp if p['bit_centres_um'][0] > old_clk]
            nb = lambda g: sum(len(p['bit_centres_um']) for p in g)
            groups = [(before, slots('N', LO, ck_lo, nb(before))), (after, slots('N', ck_hi, HI, nb(after)))]
        else:
            groups = [(fp, slots(face, LO, HI, sum(len(p['bit_centres_um']) for p in fp)))]
        for grp, avail in groups:
            n = sum(len(p['bit_centres_um']) for p in grp)
            pick = spread(avail, n); i = 0
            for p in grp:
                m = len(p['bit_centres_um']); sel = pick[i:i + m]; i += m
                q = dict(name=p['name'], face=face, layer=None, layers=sorted({l for _, l in sel}),
                         bit_centres_um=[c for c, _ in sel], bit_layers=[l for _, l in sel],
                         offset=round((sel[0][0] + sel[-1][0]) / 2, 6), span_um=[round(sel[0][0] - .048, 6), round(sel[-1][0] + .048, 6)],
                         bit_pitch_um=PITCH, bit_centres_rule='explicit bit_centres_um[i] on bit_layers[i] (actual track; >= 0.192)')
                q['layer'] = q['layers'][0] if len(q['layers']) == 1 else '+'.join(q['layers'])
                out_pins.append(q)
    # legality: unique (face, layer, centre), per-layer pitch
    seen = {}
    for p in out_pins:
        for c, l in zip(p['bit_centres_um'], p.get('bit_layers') or [p['layer']] * len(p['bit_centres_um'])):
            key = (p['face'], l)
            seen.setdefault(key, []).append(c)
    for key, cs in seen.items():
        cs.sort()
        assert all(b - a >= .096 - 1e-9 for a, b in zip(cs, cs[1:])), key
        assert len(set(cs)) == len(cs), key
    s['pins'] = out_pins
    s['outline'] = dict(w=W, h=H)
    s['pin_ranges'] = {p['name']: p['span_um'] for p in out_pins}
    s['face_density'] = {f: round(sum(len(p['bit_centres_um']) for p in out_pins if p['face'] == f) * PITCH / (W - 2 * LO), 4) for f in 'NSWE'}
    s['clock_entry'] = dict(pin='clk', face='N', layer='M5', offset=next(p for p in out_pins if p['name'] == 'clk')['bit_centres_um'][0])
    s.update(signal_max_layer='M6', layer_cap='M6', pg_layer='M6', strap_layer='M7', layer_rule='tile',
             layer_cap_grant=dict(layer_cap='M6', reason='VM bank strap masters are pin-perimeter bound (270 x 270, ~1,260 b per face): PG moves to M6 so M5 pins need no stripe clearance; parent strap M7 (H-DIE 2210, H-SM proposal)'),
             pin_layer_grant=dict(W='M4', E='M4', N='M5', S='M5', internal_signals='M2-M6'),
             grant='die_owned_strap_pins_270_cap6_2210', version=4, instance_homes=[],
             scope='270 x 270 strap master grant (H-SM accepted 22:5x). Physical qualification, parent adoption and homes OPEN.')
    for kk in ('source_sha256', 'source_dependencies_sha256'):
        s.pop(kk, None)
    return s


g = json.loads(SRC.read_text())
new = dict(g, version=4, owner='Claude H-DIE 2210', derived_from=str(SRC.relative_to(ROOT)), slots=[regrant(s) for s in g['slots']],
           adoption_scope='Exact 270 x 270 child pins (two layers per face) for hfd_vms_bank_strap_q0..3; homes/parent packing follow.',
           production_binding_adopted=False)
OUT.write_text(json.dumps(new, indent=1) + '\n')
gf = ROOT / 'results/arch/hier_contract_1015/hbm_v15.json'
d = json.loads(gf.read_text())
d['vm_strap_child_grants_2210'] = dict(file=str(OUT.relative_to(ROOT)), sha256=hashlib.sha256(OUT.read_bytes()).hexdigest(),
    outline_um=[W, H], supersedes='vm_strap_child_grants_2116 (356.4 x 365.04) for NEW strap kits; running 356x365 routes = diagnostics',
    pin_layers=dict(W='M4', E='M4', N='M5', S='M5'), layer_cap='M6 (PG M6, parent strap M7)', bit_pitch_um=0.192, accepted_by='H-SM 2026-10-15 ~23:0x (cap-M6 single-layer variant; 2-layer v3 withdrawn: ref_tile has no pins-above-cap leaf contract)', production_binding_adopted=False)
if 'vm_bank_resize_v7_proposal' in d:
    d['vm_bank_resize_v7_proposal']['status'] = 'ADOPTED 2210 (H-SM accepted with N/S two layers) -> vm_strap_child_grants_2210'
gf.write_text(json.dumps(d, indent=1) + '\n')
for s in new['slots']:
    print(s['cell'], s['outline'], s['face_density'], s['clock_entry'])
