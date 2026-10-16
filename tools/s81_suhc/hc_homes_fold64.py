#!/usr/bin/env python3
"""S81 HC leaf homes for the 64-CTH fold of the S-DIE hub re-floorplan (S-ENGRAM+NORM helper HC-HOMES, 2026-10-16).

PLANNING SCREEN (no GEN / GRT / timing).  Inputs (source-pinned, sha256 recorded in the summary):
  * the S-DIE child-hub candidate c74342891 (results/arch/s81_child_hub_preview_1016/candidate.json): hub homes, the
    HC_folded64 envelope 6 x 11 at (17800, 9500), and the 37-leaf literal NT CTH reservation (cth0 leaf offsets);
  * the exact HC group map (codex/s81-suhc-homes-0811 results/arch/s81_suhc_homes_1016/hc_group_parent_map.json):
    three chains of 22 / 20 / 22 CTH groups (NG 256, GS 8, NCOL 3 -> NP 11, L1 10, half-octets);
  * the c26b die model (tools/budgets/extract_die.py output) for every die bus width and the baseline homes.
Bus widths are the RTL parameter formulas of dsfd_sp_hc.sv / ot_s81_hc_chain_segment (NG 256, S_RD 2, S_RT 4):
  forward hop  fv 7 + fd 2920 + cy 128 + rst 1                     = 3056 b (N -> S along the chain)
  return hop   flat rv 8 + rd 2156 = 2164 b, or RETCOL rb 4 x 1140 = 4560 b (S -> N)
  NORM lanes   dl 275 (N -> S) + ul 33 (S -> N)                     =  308 b (NTREE only)
Die-level flows (collective Y 8193, VM 5400, sseq 96) are routed with tools/s81/hub_compact_screen.py's own router and
negotiated gcell congestion (500-um hop, 86.4-um gcells, M4+M6 / M3+M5 track densities, -10 % PG).  HC-internal flows
(chain hops, chain U-turns, root/band distribution, tail -> NT bottom) are pin-centroid Manhattan with relay stages
ceil(L / 500) - 1, and cut ratio = bits crossing a cut line / tracks along it (channel: tool densities; over M5-capped
macros: die layers M6 (H) / M7 (V) only, 0.064-um pitch, -10 %).

Variants (same 64 groups, same leaf reservation):
  C0  the candidate's column-major fill (chains jump bottom -> top between columns), band north;
  FN  serpentine fold: chain c down column 2c (R0), U-turn at the bottom, up column 2c+1 (MX); heads and tails on the
      north row; root / NT-bottom band north of the array;
  FS  FN mirrored (heads and tails on the south row, band south);
  FM  split serpentine around a mid band: head below the band, down 2c, U-turn, up 2c+1, cross the band, up, U-turn,
      down 2c, tail above the band; band at the collective / VM height.
  python3 tools/s81_suhc/hc_homes_fold64.py --model model.json.gz --candidate candidate.json --group-map map.json --out DIR
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 's81'))
import hub_compact_screen as S  # noqa: E402

HOP = 500.0
import os
CH_SENS = float(os.environ.get('HC_CTH_H', '835.92'))
PX, PY = 619.92, CH_SENS + 43.2  #              # CTH pitch in the 6 x 11 fold (576.72 + 43.2, 835.92 + 43.2)
CW, CH = 576.72, CH_SENS
STREET = 43.2
BAND_H = 1036.8                        # root / NT-bottom band (24 x 43.2): residual ~1.45 mm2 real views + channels
BAND_CH = 259.2                        # E-W routing channel inside the band (M4 + M6); the rest is over-macro M6
FEED = 345.6                           # FM: macro-free feed-through per odd column for the band-crossing chain hop (M3 + M5)
TURN_CH = 432.0                        # U-turn channel depth (5 gcells): 7924 b / (432 um x 32.8 t/um) = 0.56
FWD, RET_FLAT, RET_COL, NT_DL, NT_UL = 3056, 2164, 4560, 275, 33
HOP_BITS = FWD + RET_COL + NT_DL + NT_UL          # literal NT + RETCOL CTH (the fold's leaf reservation)
HOP_BITS_BASE = FWD + RET_FLAT                    # c26b TAIL_SPLIT 1, NTREE 0
Y_SLICE = [2816, 2560, 2816]                      # NP*GS*32 per chain (chain 1 has 10 groups)
NT_X0 = 168 + 15                                  # chain 0 tail fc0 104 + eps0 64; per-chain fv 7 + nv 8
T_CH_H = (1 / 0.048 + 1 / 0.064) * 0.9           # channel H tracks / um (M4 + M6)
T_CH_V = (1 / 0.036 + 1 / 0.048) * 0.9           # channel V tracks / um (M3 + M5)
T_OM = (1 / 0.064) * 0.9                          # over an M5-capped macro: M6 (H) or M7 (V) only


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def stages(L):
    return max(0, math.ceil(L / HOP - 1e-9) - 1)


def man(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


# ------------------------------------------------------------------ fold geometry
def chain_slots(variant):
    """{group_id: (col, row_from_top, orient, in_face, out_face)} and the turn list per chain"""
    chains = [list(range(0, 22)), list(range(22, 42)), list(range(42, 64))]
    slots, turns, cross = {}, [], []
    if variant == 'C0':
        for g in range(64):
            col, row = divmod(g, 11)
            slots[g] = (col, row, 'R0', 'N', 'S')
        return slots, turns, cross
    for c, ch in enumerate(chains):
        n = len(ch)
        if variant in ('FN', 'FS'):
            half = n // 2
            seq = [(2 * c, r, 'down') for r in range(half)] + [(2 * c + 1, r, 'up') for r in reversed(range(half))]
            turns.append((c, ch[half - 1], ch[half], 'S' if variant == 'FN' else 'N'))
        else:  # FM: lower block rows 5..10 (6) and upper block rows 0..4 (5) from the top; band between rows 4 / 5
            lo = 6 if n == 22 else 5
            up = 5
            lower = list(range(5, 5 + lo))
            upper = list(range(0, up))
            seq = [(2 * c, r, 'down') for r in lower] + [(2 * c + 1, r, 'up') for r in reversed(lower)] + \
                  [(2 * c + 1, r, 'up') for r in reversed(upper)] + [(2 * c, r, 'down') for r in upper]
            k = len(lower)
            turns.append((c, ch[k - 1], ch[k], 'S'))
            cross.append((c, ch[2 * k - 1], ch[2 * k]))
            turns.append((c, ch[2 * k + up - 1], ch[2 * k + up], 'N'))
        for g, (col, row, d) in zip(ch, seq):
            if variant == 'FS':
                row = 10 - row
                d = 'up' if d == 'down' else 'down'
            slots[g] = (col, row, 'R0' if d == 'down' else 'MX', 'N' if d == 'down' else 'S', 'S' if d == 'down' else 'N')
    return slots, turns, cross


def geometry(variant, x0, y0):
    """rects of every CTH group and band; array origin (x0, y0) is the candidate's HC_folded64 corner"""
    slots, turns, cross = chain_slots(variant)
    band_y = None
    def gy(row):
        # row 0 = top.  FM inserts the band (BAND_H + street) between rows 4 and 5
        base = y0 + (10 - row) * PY
        if variant == 'FM' and row <= 4:
            base += BAND_H + STREET
        return base
    rects = {g: (x0 + col * PX, gy(row), CW, CH) for g, (col, row, *_r) in slots.items()}
    top = max(r[1] + r[3] for r in rects.values())
    bot = min(r[1] for r in rects.values())
    if variant in ('C0', 'FN'):
        band_y = top + STREET
    elif variant == 'FS':
        band_y = bot - STREET - BAND_H
    else:
        band_y = y0 + 6 * PY
    band = (x0, band_y, 6 * PX - STREET, BAND_H)
    return slots, turns, cross, rects, band


def face_pt(r, f, frac=0.5):
    x, y, w, h = r
    return {'N': (x + w * frac, y + h), 'S': (x + w * frac, y), 'E': (x + w, y + h * frac), 'W': (x, y + h * frac)}[f]


def band_items(band, variant):
    """residual real-view homes inside the band (one root per chain at its head column, comb / cpin / cseq at the
    west end toward VM + collective, the NT bottom (cnbot) at the centre between the three tails)"""
    bx, by, bw, bh = band
    items = {}
    for c in range(3):
        items[f'croot{c}'] = (bx + 2 * c * PX, by, CW, bh)            # crooty_w 194.4 + crootr_* 276.48 per chain
    items['comb'] = (bx + 1 * PX, by, CW, bh)                           # ccf 410.4 x 542.16 + pads + cseq + cpin
    items['cnbot'] = (bx + 3 * PX, by, CW, bh)                          # cncla/b x 3, cnrsq, cntree x 2
    items['ctrl'] = (bx + 5 * PX, by, CW, bh)                           # caq / ccr / crx / controller residual
    return items


# ------------------------------------------------------------------ internal flows
def internal_flows(variant, x0, y0):
    slots, turns, cross, rects, band = geometry(variant, x0, y0)
    items = band_items(band, variant)
    flows = []
    chains = [list(range(0, 22)), list(range(22, 42)), list(range(42, 64))]
    turn_pairs = {(a, b) for _, a, b, _f in turns}
    cross_pairs = {(a, b) for _, a, b in cross}
    for c, ch in enumerate(chains):
        for a, b in zip(ch, ch[1:]):
            sa, sb = slots[a], slots[b]
            pa = face_pt(rects[a], sa[4])
            pb = face_pt(rects[b], sb[3])
            if (a, b) in turn_pairs:
                f = sa[4]
                d = -TURN_CH / 2 if f == 'S' else TURN_CH / 2
                L = man(pa, pb) + 2 * abs(d)
                kind = 'chain_turn'
            else:
                L = man(pa, pb)
                kind = 'chain_cross_band' if (a, b) in cross_pairs else 'chain_hop'
            flows.append(dict(kind=kind, chain=c, a=f'cth{a}', b=f'cth{b}', bits=HOP_BITS, len_um=round(L, 2),
                              bit_mm=round(HOP_BITS * L / 1000, 2), stages=stages(L), pa=pa, pb=pb))
        head, tail = ch[0], ch[-1]
        root = items[f'croot{c}']
        hp = face_pt(rects[head], slots[head][3])
        rp = face_pt(root, 'S' if root[1] > hp[1] else 'N')
        L = man(hp, rp)
        flows.append(dict(kind='root_head', chain=c, a=f'croot{c}', b=f'cth{head}', bits=FWD + RET_FLAT + NT_DL,
                          len_um=round(L, 2), bit_mm=round((FWD + RET_FLAT + NT_DL) * L / 1000, 2), stages=stages(L),
                          pa=rp, pb=hp))
        tp = face_pt(rects[tail], slots[tail][4])
        nb = items['cnbot']
        npnt = face_pt(nb, 'S' if nb[1] > tp[1] else 'N')
        L = man(tp, npnt)
        nbits = NT_DL + NT_UL + 15 + (168 if c == 0 else 0)
        flows.append(dict(kind='tail_ntbot', chain=c, a=f'cth{tail}', b='cnbot', bits=nbits, len_um=round(L, 2),
                          bit_mm=round(nbits * L / 1000, 2), stages=stages(L), pa=tp, pb=npnt))
        # root <-> comb (returned rd 2164 per chain) and Y slice band entry -> root
        cp = (items['comb'][0] + CW / 2, items['comb'][1] + BAND_H / 2)
        rc = (root[0] + CW / 2, root[1] + BAND_H / 2)
        L = man(cp, rc)
        flows.append(dict(kind='root_comb', chain=c, a=f'croot{c}', b='comb', bits=RET_FLAT, len_um=round(L, 2),
                          bit_mm=round(RET_FLAT * L / 1000, 2), stages=stages(L), pa=rc, pb=cp))
        ye = (band[0], band[1] + BAND_H / 2)
        L = man(ye, rc)
        flows.append(dict(kind='y_slice', chain=c, a='band_W', b=f'croot{c}', bits=Y_SLICE[c] + 1, len_um=round(L, 2),
                          bit_mm=round((Y_SLICE[c] + 1) * L / 1000, 2), stages=stages(L), pa=ye, pb=rc))
    return dict(slots=slots, turns=turns, cross=cross, rects=rects, band=band, items=items, flows=flows)


def cut_lines(G, variant):
    """bits / tracks on every cut line that internal flows cross (vertical cuts between columns inside the band and the
    turn channels, horizontal cuts at the band faces)"""
    out = []
    band = G['band']
    bx, by, bw, bh = band
    # vertical cuts at each column street, over the band height (H tracks: band macros -> M6 over-macro + street M4)
    for k in range(1, 6):
        xc = bx + k * PX - STREET / 2
        bits = sum(f['bits'] for f in G['flows'] if f['kind'] in ('root_comb', 'y_slice', 'tail_ntbot')
                   and min(f['pa'][0], f['pb'][0]) < xc < max(f['pa'][0], f['pb'][0]))
        tracks = BAND_CH * T_CH_H + (bh - BAND_CH) * T_OM
        out.append(dict(cut=f'band_x{k}', where='band vertical cut at column street %d' % k, bits=bits,
                        tracks=round(tracks), ratio=round(bits / tracks, 3)))
    # U-turn channel vertical cut (each turn alone in its own column pair)
    for c, a, b, f in G['turns']:
        tracks = TURN_CH * T_CH_H
        out.append(dict(cut=f'turn_c{c}_{f}', where=f'chain {c} U-turn channel ({f}) between its two columns',
                        bits=HOP_BITS, tracks=round(tracks), ratio=round(HOP_BITS / tracks, 3)))
    # chain hop across a 43.2 street / band: the hop bits over the CTH N/S face width (V tracks M3+M5 in the street)
    tr = CW * T_CH_V
    out.append(dict(cut='cth_face', where='any chain hop across a CTH N/S face (576.72 um, M3+M5 face pins)',
                    bits=HOP_BITS, tracks=round(tr), ratio=round(HOP_BITS / tr, 3)))
    if G['cross']:
        out.append(dict(cut='band_cross', where='FM chain hop crossing the band at its column (over band macros, M7)',
                        bits=HOP_BITS, tracks=round(FEED * T_CH_V), ratio=round(HOP_BITS / (FEED * T_CH_V), 3),
                        note='macro-free %.1f-um feed-through in the band at columns 1/3/5 (M3+M5); over band macros on M7 '
                             'only it would be %.3f' % (FEED, HOP_BITS / (CW * T_OM))))
    return out


# ------------------------------------------------------------------ die-level flows
DIE_FLOWS = {('sp_collective', 'sp_hc_s'): 8193, ('sp_hc_s', 'sp_vm'): 5400, ('sp_hc_s', 'sp_sseq'): 96}


BAND_FACES = {'FM': {('sp_hc_s', 'sp_collective'): 'W', ('sp_collective', 'sp_hc_s'): 'E', ('sp_hc_s', 'sp_vm'): 'W'},
              'FN': {('sp_hc_s', 'sp_vm'): 'W'}, 'C0': {('sp_hc_s', 'sp_vm'): 'W'}, 'FS': {('sp_hc_s', 'sp_collective'): 'W'}}


def die_rows(R, var=None):
    saved = dict(S.FIXED_FACE)
    for k in [('sp_hc_s', 'sp_hc_t'), ('sp_hc_t', 'sp_hc_s')]:
        S.FIXED_FACE.pop(k, None)
    S.FIXED_FACE.update(BAND_FACES.get(var, {}))
    try:
        return S.p2p_rows(R, DIE_FLOWS)
    finally:
        S.FIXED_FACE.clear()
        S.FIXED_FACE.update(saved)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--model', required=True)
    ap.add_argument('--candidate', required=True)
    ap.add_argument('--group-map', required=True)
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    model = S.load(a.model)
    cand = json.loads(Path(a.candidate).read_text())
    gmap = json.loads(Path(a.group_map).read_text())
    assert [g['group_id'] for g in gmap['groups']] == list(range(64))
    assert [sum(1 for g in gmap['groups'] if g['chain_column'] == c) for c in range(3)] == [22, 20, 22]
    p2p, trees, ports, mrects = S.flows_of(model)
    for k in DIE_FLOWS:
        assert p2p[k] == DIE_FLOWS[k], (k, p2p[k])
    assert p2p[('sp_hc_s', 'sp_hc_t')] == 3 * (FWD + RET_FLAT)
    hc = cand['homes']['HC_folded64']
    x0, y0 = hc['xy_um']
    assert hc['outline_um'] == [3676.32, 9627.12]
    y0 = y0 + 9627.12 - (11 * PY - STREET) if CH != 835.92 else y0   # keep the top fixed when the CTH grows
    leaf0 = [c for c in cand['children'] if c['group'] == 'HC' and c['name'].startswith('cth0/')]
    assert len(leaf0) == 37
    ytop0 = y0 + 10 * PY
    leaf_off = [(c['name'][5:], c['xy_um'][0] - x0, c['xy_um'][1] - ytop0, c['outline_um']) for c in leaf0]

    # baseline (c26b die model homes, TAIL_SPLIT 1 seam routed through the die)
    base_flows = dict(DIE_FLOWS)
    base_flows[('sp_hc_s', 'sp_hc_t')] = p2p[('sp_hc_s', 'sp_hc_t')]
    base = S.p2p_rows(mrects, base_flows)
    res = dict(baseline=dict(die_rows=[{k: v for k, v in r.items() if k != 'path'} for r in base]))
    seam = next(r for r in base if r['b'] == 'sp_hc_t')
    base_int = 61 * HOP_BITS_BASE * 0.0 / 1000      # abutted N/S chains (0 gap) inside each slab
    res['baseline']['totals'] = dict(
        die_bit_mm=round(sum(r['bit_mm'] for r in base), 1), internal_hops_bit_mm=base_int,
        chain_extra_stages=seam['stages'], seam_bits=seam['bits'],
        y_stages=next(r['stages'] for r in base if r['a'] == 'sp_collective'),
        vm_stages=next(r['stages'] for r in base if r['b'] == 'sp_vm'),
        nt_seam='TAIL_SPLIT 1 seam (t_tf 3056 + f_tr 2164 per chain) has NO NORM lanes: dsfd_sp_hc rejects NTREE with '
                'TAIL_SPLIT 1; a NORM tree at the seam needs +3 x (275 dl + 33 ul) + srs = 925 b new seam ports')
    # candidate R: hub homes moved, HC fold = 'sp_hc_s' (die-facing band + array) for the die router
    Rc = dict(mrects)
    for k, v in cand['homes'].items():
        if k in Rc:
            Rc[k] = (v['xy_um'][0], v['xy_um'][1], v['outline_um'][0], v['outline_um'][1])
    Rc.pop('sp_hc_t', None)
    overlaps = []
    homes = {}
    for var in ('C0', 'FN', 'FS', 'FM'):
        G = internal_flows(var, x0, y0)
        R = dict(Rc)
        R['sp_hc_s'] = G['band']                       # die-facing ports live on the root band
        arr = G['rects']
        ax0 = min(r[0] for r in arr.values()); ay0 = min(r[1] for r in arr.values())
        ax1 = max(r[0] + r[2] for r in arr.values()); ay1 = max(r[1] + r[3] for r in arr.values())
        R['hc_array'] = (ax0, ay0, ax1 - ax0, ay1 - ay0) if var != 'FM' else (ax0, ay0, ax1 - ax0, G['band'][1] - ay0 - STREET)
        if var == 'FM':
            R['hc_array_up'] = (ax0, G['band'][1] + BAND_H + STREET, ax1 - ax0, ay1 - G['band'][1] - BAND_H - STREET)
        S.FIXED_FACE.update(BAND_FACES.get(var, {}))
        rows = die_rows(R, var)
        hub_x = (9000.0, 23000.0)
        chans = {'COLL|HC': (Rc['sp_collective'][0] + Rc['sp_collective'][2], 9000, x0, 21000),
                 'VM|HC': (Rc['sp_vm'][0] + Rc['sp_vm'][2], Rc['sp_vm'][1], x0, Rc['sp_vm'][1] + Rc['sp_vm'][3])}
        cong, util, gr = S.congestion(R, rows, [], hub_x, chans)
        for k in BAND_FACES.get(var, {}):
            S.FIXED_FACE.pop(k, None)
        cuts = cut_lines(G, var)
        fl = G['flows']
        by = {}
        for f in fl:
            d = by.setdefault(f['kind'], dict(n=0, bits=0, bit_mm=0.0, max_len_um=0.0, max_stages=0, stage_bits=0))
            d['n'] += 1; d['bits'] += f['bits']; d['bit_mm'] += f['bit_mm']
            d['max_len_um'] = max(d['max_len_um'], f['len_um']); d['max_stages'] = max(d['max_stages'], f['stages'])
            d['stage_bits'] += f['stages'] * f['bits']
        for d in by.values():
            d['bit_mm'] = round(d['bit_mm'], 1)
        chain_st = [sum(f['stages'] for f in fl if f['chain'] == c and f['kind'].startswith('chain')) for c in range(3)]
        die_tot = round(sum(r['bit_mm'] for r in rows), 1)
        int_tot = round(sum(f['bit_mm'] for f in fl), 1)
        envelope = (ax0, min(ay0, G['band'][1]), ax1 - ax0, max(ay1, G['band'][1] + BAND_H) - min(ay0, G['band'][1]))
        ov = [k for k, r in Rc.items() if k not in ('sp_hc_s',) and r[0] < envelope[0] + envelope[2] and
              r[0] + r[2] > envelope[0] and r[1] < envelope[1] + envelope[3] and r[1] + r[3] > envelope[1]]
        res[var] = dict(
            envelope_um=[round(v, 3) for v in envelope], band_um=[round(v, 3) for v in G['band']],
            die_rows=[{k: v for k, v in r.items() if k != 'path'} for r in rows],
            die_congestion=dict({k: cong[k] for k in ('max_util', 'edges_over_060', 'edges_over_100', 'channels', 'routing_complete')},
                                hot_edges=cong['hot_edges'][:4]),
            internal=by, cuts=cuts, max_cut_ratio=max(c['ratio'] for c in cuts),
            chain_relay_stages_per_chain=chain_st,
            totals=dict(die_bit_mm=die_tot, internal_bit_mm=int_tot, total_bit_mm=round(die_tot + int_tot, 1),
                        y_stages=next(r['stages'] for r in rows if r['a'] == 'sp_collective'),
                        vm_stages=next(r['stages'] for r in rows if r['b'] == 'sp_vm'),
                        worst_chain_extra_stages=max(chain_st),
                        nt_join_max_stages=max(f['stages'] for f in fl if f['kind'] == 'tail_ntbot')),
            overlaps_with_unmoved_model_blocks=ov)
        homes[var] = G
        res[var]['_R'] = R
        res[var]['_rows'] = rows
        res[var]['_util'] = (util, gr)
    # pick: least total bit-mm among variants whose cut <= 0.60 and die routing completes
    ok = [v for v in ('FN', 'FS', 'FM') if res[v]['max_cut_ratio'] <= 0.60 and res[v]['die_congestion']['routing_complete']
          and res[v]['die_congestion']['max_util'] <= 0.60]
    pick_ok = bool(ok)
    ok = ok or ['FN', 'FS', 'FM']
    pick = min(ok, key=lambda v: (res[v]['totals']['total_bit_mm'], res[v]['totals']['worst_chain_extra_stages']))
    G = homes[pick]
    gmap_by = {g['group_id']: g for g in gmap['groups']}
    hj = dict(schema='opentallas.s81.hc_homes_fold64.v1', variant=pick, scope='CANDIDATE PLANNING HOMES, not adopted; '
              'owner Explorer review + source-current real views + full native trial required',
              array_origin_um=[x0, y0], pitch_um=[PX, PY], cth_outline_um=[CW, CH], band=G['band'], groups=[], band_items={}, leaves=[])
    for g in range(64):
        col, row, orient, fin, fout = G['slots'][g]
        r = G['rects'][g]
        m = gmap_by[g]
        hj['groups'].append(dict(group_id=g, logical_instance=m['logical_instance'], chain=m['chain_column'],
                                 chain_position=m['chain_position'], col=col, row_from_top=row,
                                 origin_um=[round(r[0], 3), round(r[1], 3)], orient=orient,
                                 faces=dict(fwd_in=fin, fwd_out=fout, ret_in=fout, ret_out=fin, nt_dl_in=fin,
                                            nt_dl_out=fout, nt_ul_in=fout, nt_ul_out=fin)))
        for name, dx, dy, ol in leaf_off:
            # dy is measured from the CTH origin (bottom); MX mirrors about the CTH horizontal centre line
            ly = r[1] + dy if orient == 'R0' else r[1] + CH - dy - ol[1]
            hj['leaves'].append(dict(group_id=g, leaf=name, origin_um=[round(r[0] + dx, 3), round(ly, 3)],
                                     outline_um=ol, orient=orient,
                                     chain_faces='N in / S out' if orient == 'R0' else 'S in / N out'))
    for k, v in G['items'].items():
        hj['band_items'][k] = dict(origin_um=[round(v[0], 3), round(v[1], 3)], outline_um=[v[2], v[3]])
    assert len(hj['leaves']) == 2368
    # leaf overlap check
    boxes = sorted((l['origin_um'][0], l['origin_um'][1], l['outline_um'][0], l['outline_um'][1]) for l in hj['leaves'])
    over = 0
    for i, b in enumerate(boxes):
        for c in boxes[i + 1:i + 60]:
            if c[0] >= b[0] + b[2] - 1e-6:
                break
            if c[1] < b[1] + b[3] - 1e-6 and b[1] < c[1] + c[3] - 1e-6 and c[0] < b[0] + b[2] - 1e-6:
                over += 1
    hj['leaf_overlap_pairs'] = over
    (out / 'homes.json').write_text(json.dumps(hj, indent=0) + '\n')
    render(res, homes, pick, out / 'flow.png', Rc, mrects)
    for v in ('C0', 'FN', 'FS', 'FM'):
        for k in ('_R', '_rows', '_util'):
            res[v].pop(k)
    summary = dict(
        schema='opentallas.s81.hc_homes_fold64_summary.v1', scope='PLANNING SCREEN (no GEN / GRT / timing / native)',
        inputs=dict(model=dict(path=a.model, sha256=sha(a.model)), candidate=dict(path=a.candidate, sha256=sha(a.candidate),
                    commit='c74342891'), group_map=dict(path=a.group_map, sha256=sha(a.group_map), branch='codex/s81-suhc-homes-0811')),
        widths=dict(fwd=FWD, ret_flat=RET_FLAT, ret_col=RET_COL, nt_dl=NT_DL, nt_ul=NT_UL, hop_fold=HOP_BITS,
                    hop_c26b=HOP_BITS_BASE),
        hop_um=HOP, picked=pick, picked_meets_all_gates=pick_ok, picked_rule='least total bit-mm with every HC-internal cut <= 0.60, die gcell max util <= 0.60 and die routing complete',
        results=res, leaf_overlap_pairs=over,
        norm_join=norm_join(res, pick))
    (out / 'summary.json').write_text(json.dumps(summary, indent=1) + '\n')
    print(json.dumps({v: dict(res[v]['totals'], max_cut=res[v]['max_cut_ratio'], chain_stages=res[v].get('chain_relay_stages_per_chain'),
                              die_util=res[v]['die_congestion']['max_util']) for v in ('C0', 'FN', 'FS', 'FM')}, indent=1))
    print('picked', pick, 'leaf overlaps', over)


def norm_join(res, pick):
    p = res[pick]
    return dict(
        tail_split1='The current die TAIL_SPLIT 1 seam (sp_hc_s t_tf* / f_tr*, dsfd_sp_hc_t) has no NORM-tree lane ports: '
                    'dsfd_sp_hc_t $fatal on NTREE; f_dl / srs were INPUT_UNCONNECTED. It cannot carry NT lanes.',
        fold_requirement='The fold puts every chain head AND tail on the band: NT lanes run inside each CTH hop (dl 275 '
                         'N->S, ul 33 S->N, included in the 7,924-b hop) and only the 3 tail -> cnbot joins are new wires. '
                         'This needs ONE combined HC parent (HC_s + HC_t, no die seam; a hardenable TAIL_SPLIT 0 NTREE 1 '
                         'RETCOL 1 composition with cnbot in the band), not dsfd_sp_hc_c + dsfd_sp_hc_t.',
        tail_to_cnbot=dict(bits_per_chain='dl 275 + ul 33 + fv 7 + nv 8 = 323 (chain 0 +168: fc0 104 + eps0 64)',
                           total_bits=3 * 323 + 168, faces='tail CTH chain-out face (band side) -> cnbot face toward the array',
                           max_stages=p['totals']['nt_join_max_stages'],
                           rows={k: v for k, v in p['internal'].get('tail_ntbot', {}).items()}),
        if_two_parents_kept='If S-DIE keeps two die parents, the seam needs +925 b (3 x 275 dl + 3 x 33 ul + srs) of '
                            'registered seam ports on dsfd_sp_hc_c and dsfd_sp_hc_t_nt, equal-age with t_tf/f_tr, and the '
                            'seam must sit where the fold returns to the band (otherwise the lanes ride the full chain).',
        norm_to_su='No die bus carries NT results to SU/NORM today; the NT bottom output stays inside HC (ul scale lanes '
                   'back up the chains, flt to chain 0). A NORM result export to SU, if the S-NORM swap needs one, is an '
                   'extra source-defined bus (not in the model) and would leave from the band W face.')


def render(res, homes, pick, png, Rc, mrects):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, axs = plt.subplots(1, 4, figsize=(22, 11))
    cols = {'chain_hop': '#2c7fb8', 'chain_turn': '#d95f0e', 'chain_cross_band': '#d95f0e', 'root_head': '#31a354',
            'tail_ntbot': '#c51b8a', 'root_comb': '#756bb1', 'y_slice': '#e6550d'}
    for ax, var in zip(axs, ('C0', 'FN', 'FS', 'FM')):
        G = homes[var]
        r = res[var]
        for k in ('sp_collective', 'sp_vm', 'sp_su_s', 'sp_host', 'sp_wfc', 'sp_sseq'):
            x, y, w, h = Rc[k]
            ax.add_patch(plt.Rectangle((x / 1e3, y / 1e3), w / 1e3, h / 1e3, fc='#eeeeee', ec='#555', lw=0.8))
            ax.text((x + w / 2) / 1e3, (y + h / 2) / 1e3, k.replace('sp_', ''), ha='center', va='center', fontsize=8)
        for g, (x, y, w, h) in G['rects'].items():
            c = G['slots'][g]
            chain = 0 if g < 22 else 1 if g < 42 else 2
            ax.add_patch(plt.Rectangle((x / 1e3, y / 1e3), w / 1e3, h / 1e3, fc=['#deebf7', '#e5f5e0', '#fee6ce'][chain],
                                       ec='#666', lw=0.4))
            ax.text((x + w / 2) / 1e3, (y + h / 2) / 1e3, f'{g}\n{c[2]}', ha='center', va='center', fontsize=5)
        x, y, w, h = G['band']
        ax.add_patch(plt.Rectangle((x / 1e3, y / 1e3), w / 1e3, h / 1e3, fc='#fff7bc', ec='k', lw=0.8))
        for k, (ix, iy, iw, ih) in G['items'].items():
            ax.text((ix + iw / 2) / 1e3, (iy + ih / 2) / 1e3, k, ha='center', va='center', fontsize=5.5)
        for f in G['flows']:
            pa, pb = f['pa'], f['pb']
            if f['kind'] == 'chain_hop':
                continue
            lw = 0.6 + 2.2 * min(1.0, f['bits'] / 8000)
            ax.plot([pa[0] / 1e3, pb[0] / 1e3, pb[0] / 1e3], [pa[1] / 1e3, pa[1] / 1e3, pb[1] / 1e3], color=cols[f['kind']],
                    lw=lw, alpha=0.85)
        for row in r['_rows']:
            import numpy as np
            p = np.array(row['path']) / 1e3
            ax.plot(p[:, 0], p[:, 1], color='#b30000', lw=0.8 + 2.5 * min(1.0, row['bits'] / 8193), alpha=0.8)
            mid = p[len(p) // 2]
            ax.text(mid[0], mid[1], f"{row['bits']}b {row['stages']}st", fontsize=6, color='#b30000')
        t = r['totals']
        ax.set_title(f"{var}{' (picked)' if var == pick else ''}: total {t['total_bit_mm'] / 1e3:.1f} kbit-mm\n"
                     f"die {t['die_bit_mm'] / 1e3:.1f}k + HC-internal {t['internal_bit_mm'] / 1e3:.1f}k; "
                     f"Y {t['y_stages']} st, VM {t['vm_stages']} st\nchain extra stages {r['chain_relay_stages_per_chain']}, "
                     f"NT join {t['nt_join_max_stages']} st, max cut {r['max_cut_ratio']:.2f}", fontsize=9)
        ax.set_xlim(9.5, 22.5)
        ax.set_ylim(7.8, 20.6)
        ax.set_aspect('equal')
        ax.set_xlabel('x (mm)')
    axs[0].set_ylabel('y (mm)')
    from matplotlib.lines import Line2D
    fig.legend([Line2D([0], [0], color=c, lw=2) for c in ('#b30000', '#d95f0e', '#31a354', '#c51b8a', '#756bb1', '#e6550d')],
                  ['die flow (router path)', 'chain U-turn / band cross', 'root -> head', 'tail -> NT bottom (NORM lanes)',
                   'root -> comb return', 'Y slice band -> root'], loc='lower center', ncol=6, fontsize=9)
    fig.suptitle('S81 HC 64-CTH fold homes (6 x 11 at 17.8, 9.5 mm) -- chain order, band and HC flows; '
                 'labels: group id / orient', fontsize=11)
    fig.tight_layout()
    fig.savefig(png, dpi=95)
    plt.close(fig)


if __name__ == '__main__':
    main()
