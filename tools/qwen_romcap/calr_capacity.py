#!/usr/bin/env python3
"""QW-CALR 10-20: exact capacity of the CALR (CALENDAR_ROM=1 / TABLE_ROM=1) CTLM successor, from the real image + kit.

Checks (exit 1 on any failure):
  * logical: the CALR10 image (DW0..7 + the two ot_rom_4096x266_m8 via maps, rtl/test/qwen_dv/calr_port) decoded exactly as
    qfd_dv_calendar_rom reads it (row = first[9:2], 4 x 128-b entries / row over m0 ++ m1, 20 spare bits = 0); nent <= NENT 1023
    (10-bit first/nent: the RTL limit), every descriptor 4-aligned and inside nent, one LOCAL4 table-load entry per stage 1..36,
    every segment / range first entry T_0 >= 5 + (NU - 1) (the +1 CALR fetch edge, else a late FAULT);
  * versus the legacy CALD in-PW store: base >= 16 x programme words, base + 2 nent <= 976 (what fails without CALR);
  * physical: the two ROM266 macros + the closed wtn child placed in a CTLM kit floorplan (43.2-um lattice, inside the core,
    no overlap with existing blocks incl. halo) and the resulting hard+std fill.
usage: calr_capacity.py --image DIR --floorplan KIT/floorplan.json [--std-um2 N] [--prog-words 25] --out JSON
"""
import argparse, json, sys
from pathlib import Path

ROM_W, ROM_H = 121.824, 62.910           # ot_rom_4096x266_m8 LEF SIZE
WTN_W, WTN_H = 86.4, 77.76               # closed qfd_tt_ctlm_dv_wtn LEF SIZE
LAT, HALO, NENT_MAX, NU, ROWS = 43.2, 5.4, 1023, 4, 4096


def viamap(path, bits=266, mux=8):
    rows = [int(l, 16) for l in Path(path).read_text().split()]
    words = []
    for a in range(len(rows) * mux):
        r, s, v = rows[a // mux], a % mux, 0
        for b in range(bits):
            if (r >> (b * mux + s)) & 1:
                v |= 1 << b
        words.append(v)
    return words


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--image', required=True); ap.add_argument('--floorplan', required=True)
    ap.add_argument('--std-um2', type=float, default=None); ap.add_argument('--prog-words', type=int, default=25)
    ap.add_argument('--slots', default='rom:475.2,388.8;rom:475.2,475.2;wtn:648.0,388.8')
    ap.add_argument('--out', required=True)
    a = ap.parse_args(); img = Path(a.image); fails = []
    m0, m1 = viamap(img / 'calendar_m0.viamap.hex'), viamap(img / 'calendar_m1.viamap.hex')
    dw = [int(l, 16) for l in (img / 'dw.hex').read_text().split()]
    if dw[0] >> 32 != 0x43414C52 or (dw[0] >> 10) & ((1 << 22) - 1):
        fails.append('DW0 is not a CALR10 descriptor')
    nent = dw[0] & 0x3FF
    ents, spare = [], 0
    for r in range((nent + 3) // 4):
        w = m0[r] | (m1[r] << 266)
        spare |= w >> 512
        ents += [(w >> (128 * k)) & ((1 << 128) - 1) for k in range(4)]
    ents = ents[:nent]
    desc = [((d >> 16) & 0x3FF, d & 0x3FF) for d in dw[1:5]]
    if spare: fails.append('ROM spare bits [531:512] non-zero (qfd_dv_calendar_rom faults)')
    if nent > NENT_MAX: fails.append(f'nent {nent} > {NENT_MAX}')
    for i, (f, n) in enumerate(desc):
        if n and (f % 4 or f + n > nent): fails.append(f'descriptor {i} ({f},{n}) misaligned / outside nent')
    t0min = 5 + (NU - 1)
    t0 = {i: ents[f] >> 116 for i, (f, n) in enumerate(desc) if n}
    loc4 = [(k, (e >> 4) & 63) for k, e in enumerate(ents) if ((e & ((1 << 116) - 1)) >> 112) == 14 and (e >> 1) & 7 == 4]
    stages = sorted(s for _, s in loc4)
    if stages != list(range(1, 37)): fails.append(f'LOCAL4 table loads cover stages {stages[:3]}..{stages[-3:]} (need 1..36 once)')
    late = [k for k, _ in loc4 if ents[k] >> 116 < t0min] + [i for i, v in t0.items() if v < t0min]
    if late: fails.append(f'first entries with T_0 < {t0min}: {late[:6]}')
    base = 16 * a.prog_words
    cald_cap = max(0, (976 - base) // 2)
    fp = json.loads(Path(a.floorplan).read_text())
    cx0, cy0, cx1, cy1 = fp['core']; W, H = fp['die'][2], fp['die'][3]
    blocks = [(b['inst'], b['x'], b['y'], b['w'], b['h']) for b in fp['blocks']]
    placed = []
    for n, s in enumerate(a.slots.split(';')):
        kind, xy = s.split(':'); x, y = map(float, xy.split(','))
        w, h = (ROM_W, ROM_H) if kind == 'rom' else (WTN_W, WTN_H)
        name = {0: 'u_gi.u_cal.g_calrom.u_rom.m0', 1: 'u_gi.u_cal.g_calrom.u_rom.m1'}.get(n, 'u_gi.g_wtn.u_wtn')
        if abs(x / LAT - round(x / LAT)) > 1e-6 or abs(y / LAT - round(y / LAT)) > 1e-6: fails.append(f'{name} off the 43.2 lattice')
        if x < cx0 or y < cy0 or x + w > cx1 or y + h > cy1: fails.append(f'{name} outside the core')
        for bn, bx, by, bw, bh in blocks + placed:
            if x < bx + bw + HALO and bx < x + w + HALO and y < by + bh + HALO and by < y + h + HALO:
                fails.append(f'{name} overlaps {bn} (halo {HALO})')
        placed.append((name, x, y, w, h))
    hard0 = sum(w * h for _, _, _, w, h in blocks)
    add = sum(w * h for _, _, _, w, h in placed)
    std = a.std_um2 if a.std_um2 is not None else fp.get('std_area_um2', 0.0)
    out = dict(
        verdict='PASS' if not fails else 'FAIL', fails=fails,
        logical=dict(nent=nent, nent_max=NENT_MAX, fill_pct=round(100 * nent / NENT_MAX, 2), rom_rows_used=(nent + 3) // 4,
                     rom_rows=ROWS, descriptors=desc, first_entry_T0=t0, t0_min=t0min, table_loads=len(loc4)),
        cald_without_calr=dict(programme_words=a.prog_words, base_pw=base, max_entries=cald_cap, nine_bit_nent_max=511,
                               fits=nent <= min(cald_cap, 511), decode_entries=desc[1][1],
                               decode_fits=desc[1][1] <= cald_cap),
        physical=dict(kit=fp['name'], outline=[W, H], placed=[dict(inst=n, x=x, y=y, w=w, h=h) for n, x, y, w, h in placed],
                      hard_um2_before=round(hard0, 1), hard_um2_added=round(add, 1), std_um2=std,
                      fill_before_pct=round(100 * (hard0 + std) / (W * H), 1),
                      fill_after_pct=round(100 * (hard0 + add + std) / (W * H), 1)))
    Path(a.out).write_text(json.dumps(out, indent=1) + '\n')
    print(json.dumps(dict(verdict=out['verdict'], fails=fails, logical=out['logical'], cald=out['cald_without_calr'],
                          fill=[out['physical']['fill_before_pct'], out['physical']['fill_after_pct']])))
    return 0 if not fails else 1


if __name__ == '__main__':
    sys.exit(main())
