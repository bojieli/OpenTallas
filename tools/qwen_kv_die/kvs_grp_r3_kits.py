#!/usr/bin/env python3
"""KVPC-R 10-23: structural floorplan redesign of the KV die landing-group tiles qkd_kvs_grp / qkd_kvs_grp_h (28 + 4
instances) -> kits physical/ref_tile/qkd_kvs_grp{,_h}_r3a (MAIN) / _r3b (ALT) on the r2d RTL (claude/kdie5-r2d-1022:
pin-registered r2 successor, per-port exit copies, 0 extra edges; RTL byte-identical here).

COORD review 10-23 (tile-review-1023 COORD_VERDICTS: BAD): r2c/r2d frame 222.6 x 1188 um (AR 5.3, tall-thin), 4 SRAMs
in one sparse column, logic in one blob, fill 6.9 % (grp) / 4.3 % (grp_h), 78-84 % empty.

What changes (RTL, ports, clocks, SDC, reset / pin-reg contracts unchanged):
  1. OUTLINE from the pin demand + content: the E face carries the K / V response words (rsp 1056 + krsp 1062 + kreq 38
     + vreq 15 = 2,171 pins), W the four PC word pairs (1,8xx), N / S the fan chain (271 + 144 each).  Height = E pins at
     ~4.6 /um = 475.2 (MAIN) / 518.4 (ALT, 4.2 /um); width from content (std ~17k + 4 x 3.9k macro um2) with the macro
     column + two logic bands: 237.6 (MAIN, AR 2.0) / 259.2 (ALT, AR 2.0).  Fill ~29 % / 24 %: pin-bound (60-70 % would
     need >= 9 pins/um on E).  The frame no longer spans the 4-PC pitch (1,512 um): the die (kv_static_die place, group
     slot) must re-slot it -- the 1,188-um tile carried the fan-chain hop in-tile; at 475 um the r2 in-tile relays stay
     (still 4 edges a hop) and the remaining ~1.0 mm group-to-group gap is ONE die hop at the M8/M9 reach (REACH-M89
     1.2 mm on KV), so 0 schedule edges if the die keeps the chain hop single-stage (STEWARD die call).
  2. MACROS: the 4 ot_sram_1r1w_128x256_m1_r2c2 (94.8 x 41.1, 821 pins on the LEF W edge) form ONE abutted N-S stack
     (pitch 41.088), vertically centred, 43.2 um from the W face (W PHY-side band = the PC words' pin registers):
       MAIN: MY -> pins face the E band (K / V response words, rsp / krsp exit flops)
       ALT : R0 -> pins face the W band (PC landing words)
  3. PINS: explicit per-face ranges in face order (W: pc0 / pc1 words bottom, clocks / straps / pass words mid, pc2 / pc3
     top; E: kreq krsp rsp vreq; N / S: the fan chain), replacing the release-frame io_tcl (frame-exact pins of the
     1,188-um slot).  M4 (W/E) / M5 (N/S), layer cap M5 (OBS contract).  No FT ports: no foreign die lane crosses a group
     longer than the 1.2-mm reach (FT-KV ft_kv_block_cross: kvs_grp max 1,188 um = this tile's own height).
Usage: kvs_grp_r3_kits.py  (writes the four spec.json files; then ref_tile.py gen each)
"""
import copy
import json
import os
import re

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
MW, MH = 94.824, 41.064
PITCH = MH + 0.024


def widths(rtl, top):
    t = open(os.path.join(ROOT, rtl)).read()
    m = re.search(r'module %s\s*\((.*?)\nendmodule' % re.escape(top), t, re.S)
    out = {}
    for msb, lsb, n in re.findall(r'^\s*(?:input|output)\s+wire\s+(?:\[(\d+):(\d+)\]\s+)?(\w+)\s*[;,]', m.group(1), re.M):
        out[n] = int(msb or 0) - int(lsb or 0) + 1
    return out


def spread(order, bits, lo, hi, gap=0.36):
    n = sum(bits[p] for p in order)
    pitch = (hi - lo - gap * (len(order) - 1)) / n
    out, x = {}, lo
    for p in order:
        w = max(bits[p] * pitch, 0.29)
        out[p] = [round(x, 4), round(x + w, 4)]
        x += w + gap
    return out, pitch


def build(base, name, tag, W, H, orient, why, x0=None):
    s = copy.deepcopy(json.load(open(os.path.join(ROOT, 'physical/ref_tile', base, 'spec.json'))))
    bits = widths(s['sources'][0], s['top'])
    s['name'] = name
    s['outline'] = {'w': W, 'h': H, 'exact': True}
    for k in ('io_tcl', 'pin_hook_before_flops', 'pre_dpl_extra'):
        s.pop(k, None)
    pr = {}
    dens = {}
    for f, ports in s['pins'].items():
        ports = [p for p in ports if p in bits]
        L = (W if f in 'NS' else H)
        r, _p = spread(ports, bits, 1.0, L - 1.0)
        pr.update(r)
        dens[f] = round(sum(bits[p] for p in ports) / (L - 2), 2)
    s['pin_ranges'] = pr
    s['route'] = dict(s['route'], pin_balance={'group_max': 1, 'h': 'M4', 'v': 'M5'})   # bit order judged + kept
    x0 = x0 if x0 is not None else (43.2 if orient == 'MY' else 86.4)
    y0 = round(((H - 4 * PITCH) / 2) // 2.16 * 2.16, 4)
    mac = s['macros']
    s['macros'] = [dict(m, at=[x0, round(y0 + k * PITCH, 4)], orient=orient, at_exact=True) for k, m in enumerate(mac)]
    if tag.startswith('r4'):
        eb = sum(bits[p] for p in s['pins']['E'] if p in bits)
        s['fill_reason'] = {'pin_bound': (
            f"KVPC-R grp {tag} PIN-BOUND by the {eb}-bit E bus (kreq/krsp/rsp/vreq, die partner E: STEWARD-QK 10-23 ruling, "
            f"no N/S move): {eb} pins / ({H} - 2) um = {dens.get('E')} /um on M4 (pin pitch {(H - 2) / eb:.3f} um = "
            f"{(H - 2) / eb / 0.048:.1f} M4 tracks; M6 is above the M5 cap), so H = {H}; W = 23.76 W pin-reg band + 94.8 "
            f"macro + E band = {W}.  W {dens.get('W')} /um, N {dens.get('N')}, S {dens.get('S')}.  No padding.")}
    else:
      s['fill_reason'] = {'pin_bound': (
        f"KVPC-R grp r3 pin-bound outline {W} x {H}: E {dens.get('E')} /um (K/V response words), W {dens.get('W')} /um "
        f"(4 PC word pairs), N {dens.get('N')} S {dens.get('S')}; content std ~17k + macros 15.6k um2 would fit ~230 x 230 "
        "at 60-70 %, which needs >= 9 pins/um on E; height = E pins at ~4.2-4.6 /um, width = macro column + two bands.")}
    s['kits_b'] = dict(s.get('kits_b') or {}, frame=[round(W + 2.16, 2), round(H + 2.16, 2)], kit_outline=[W, H])
    pur = (f"KVPC-R 10-23 {tag}: COORD-review redesign of {s['top'][:-4]} on the r2d RTL (byte-identical, 0 edges): "
           f"outline {W} x {H} (was 222.6 x 1188, AR 5.3, fill 4-7 %), 4 SRAMs as one abutted N-S stack {orient} at x {x0}, "
           f"explicit face ranges (W pc0/1 low, pc2/3 high; E kreq/krsp/rsp/vreq; N/S fan chain). {why}")
    s['purpose'] = pur
    s['structural_change'] = pur
    s['job'] = dict(s['job'], owner='Claude:KVPC-R', branch='claude/kvgrp-r3-1023', tag=tag, purpose=pur)
    d = os.path.join(ROOT, 'physical/ref_tile', name)
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, 'spec.json'), 'w') as fh:
        json.dump(s, fh, indent=1)
        fh.write('\n')
    print(name, W, H, orient, 'pins/um', dens)


if __name__ == '__main__':
    for b, t in (('qkd_kvs_grp_r2da', 'qkd_kvs_grp'), ('qkd_kvs_grp_h_r2da', 'qkd_kvs_grp_h')):
        build(b, t + '_r3a', 'r3a', 237.6, 475.2, 'MY', 'MAIN: macros face the E response band.')
        build(b, t + '_r3b', 'r3b', 259.2, 518.4, 'R0', 'ALT: macros face the W PC landing band, E 4.2 /um.')
    # r4 (GEOM-REVIEW 02:05 FAIL of r3: empty N/S bands, W face strip + E islands).  STEWARD-QK ruling 02:10: the K/V
    # words stay on E (their die partner is E); pin-bound height from the E bus at a legal pitch; the logic packed
    # against E with the macros facing it (MY); the W band is only the PC-word pin registers (macro 21.6 um inside the core, the pin
    # edge); width = W band + macro + E band, no padding.
    for b, t in (('qkd_kvs_grp_r2da', 'qkd_kvs_grp'), ('qkd_kvs_grp_h_r2da', 'qkd_kvs_grp_h')):
        build(b, t + '_r4a', 'r4a', 151.2, 397.44, 'MY', 'r4 MAIN: E 2,175 pins at 5.5 /um (M4), macros MY at x 23.76 face the E band.', 23.76)
        build(b, t + '_r4b', 'r4b', 164.16, 438.48, 'MY', 'r4 ALT: E at 5.0 /um, macros MY at x 23.76 face the E band.', 23.76)
