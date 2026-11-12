"""VISLAYOUT2-HBM form G1 for q_su31 / q_su31__physical_v1 (NE_su31 / NW_su31): open a macro-free N-S transit
channel through BOTH macro rows.

INTENT.  q_su31 (1831.68 x 1555.2) holds 4 lane groups of 4 pieces (190.08 x 311.04).
  - Top row y 1011-1322: lanes28_31 at x 60-821, lanes20_23 at x 916-1676.
  - Bottom row y 242-553: lanes12_15 at x 60-821, lanes4_7 at x 916-1676.
  - The two rows leave a 95-um central gap and a 155-um E strip.
Die transit through the type: two 1615-b N->S lanes (su31 L8303mx1 / L8304mx1, pv1 L8303x1 / L8304x1).
  - N windows x 662-1169, S windows x 295-835. Total 3230 b.
  - They must cross both macro rows. Today they go over the macros or squeeze into the 95-um gap.
  - Real GRT q_su31 0609563b63c5: 44,729 overflow (H 19.2k / V 25.5k), hot at (740,780).
G1 re-sites both rows (cores move rigidly by group, orientations kept):
  - W groups at x LEFT, E groups after a central channel of CHW um.
  - The E strip keeps >= ~90 um for the E-face buses L5004/L5005 (L1202/L1203 on pv1), which sit beside the top row.
  - Each transit lane runs N window -> top band -> down the channel (own column) -> bottom band -> S window.
  - Registers sit evenly by arc length from the input pin; a station is a register column (H leg) or row (V leg).
  - A lane needing a hop > 390 um gets +1 station, declared in latency.lanes.
Outputs: OUT plan (ft re-routed) and SEED json for core_place --seed --no-search, which moves the cores and the
stations / taps riding them and legalises."""
import json, sys
src, dst, seed_out = sys.argv[1], sys.argv[2], sys.argv[3]
CHW = float(sys.argv[4]) if len(sys.argv) > 4 else 212.0
LEFT = float(sys.argv[5]) if len(sys.argv) > 5 else 8.64
TYPES = ['q_su31', 'q_su31__physical_v1']
HOP_MAX = 390.0
NOADD = (sys.argv[6] if len(sys.argv) > 6 else '0') == '1'   # 1: no extra internal registers (core_place --reach decides)
PW = 190.08
CW, RH, XS = 1.404, 0.27, 0.216
p = json.load(open(src))
seed = {}
def mid(w): return round(sum(w) / 2, 2)
def seglen(a, b): return abs(b[0] - a[0]) + abs(b[1] - a[1])
FIRST = 170.0   # first register this far (arc) from the N window centre: the S0->S1 reach counts the window spread
def walk(pts, k):
    L = sum(seglen(pts[i], pts[i + 1]) for i in range(len(pts) - 1))
    out = []
    d1 = min(L / k, FIRST)
    for j in range(1, k):
        d = d1 + (L - d1) * (j - 1) / (k - 1) if k > 1 else d1; i = 0
        while i < len(pts) - 2 and d > seglen(pts[i], pts[i + 1]):
            d -= seglen(pts[i], pts[i + 1]); i += 1
        a, b = pts[i], pts[i + 1]; sl = seglen(a, b); f = d / sl if sl else 0
        out.append(([round(a[0] + (b[0] - a[0]) * f, 2), round(a[1] + (b[1] - a[1]) * f, 2)], 'V' if a[0] == b[0] else 'H'))
    return out, L
rep = []
for tn in TYPES:
    t = p['partition_types'][tn]
    W_, H_ = t['outline_um']
    sd = {}
    for h in t['hard_cores']:
        i, o = h['inst'], h['origin_um']
        grp_w = any(g in i for g in ('lanes28_31', 'lanes12_15'))
        rel = o[0] - (60.48 if grp_w else 915.84)
        k = round(rel / PW)
        x = (LEFT if grp_w else LEFT + 4 * PW + CHW) + k * PW
        sd[i] = {'origin_um': [round(x, 4), o[1]], 'orient': h.get('orient', 'R0')}
    seed[tn] = sd
    G0 = LEFT + 4 * PW; G1 = G0 + CHW
    top_y1 = max(h['origin_um'][1] + h['outline_um'][1] for h in t['hard_cores'])
    bot_y0 = min(h['origin_um'][1] for h in t['hard_cores'])
    YT = round((top_y1 + H_) / 2, 2); YBOT = round(bot_y0 / 2, 2)
    tr = [s for s in t['ft_slots'] if s['width'] >= 1000 and s['in_face'] == 'N' and s['out_face'] == 'S']
    tr.sort(key=lambda s: mid(s['in_window_um']))
    cols = [round(G0 + CHW * 0.28, 2), round(G0 + CHW * 0.72, 2)]
    ys = sorted([YBOT + 40, YBOT - 40], reverse=True)
    sw = sorted(tr, key=lambda s: -mid(s['out_window_um']))      # the S lane farthest E turns highest
    ybot = {s['name']: ys[j] for j, s in enumerate(sw)}
    for c, s in zip(cols, tr):
        xn, xs = mid(s['in_window_um']), mid(s['out_window_um'])
        yt = YT + (25 if c == cols[0] else -25)
        pts = [[xn, H_], [xn, yt], [c, yt], [c, ybot[s['name']]], [xs, ybot[s['name']]], [xs, 0.0]]
        k0 = int(s['stations']); _, L = walk(pts, k0); k = k0
        while (L - min(L / k, FIRST)) / max(1, k - 1) > HOP_MAX:
            k += 1
        regs, _ = walk(pts, k)
        s['stations'] = k
        s['regs_um'] = [pts[0]] + [r for r, _ in regs]
        n = s['width'] + 1
        blk = []
        for (r, leg) in regs:
            cols_n = 4 if leg == 'H' else 56
            rows = -(-n // cols_n)
            x0 = round(round((r[0] - cols_n * 1.512 / 2) / XS) * XS, 3); y0 = round(round((r[1] - rows * RH / 2) / RH) * RH, 3)
            x0 = min(max(x0, 0.5), W_ - cols_n * 1.512 - 0.5); y0 = min(max(y0, 0.5), H_ - rows * RH - 0.5)
            blk.append([[round(x0 + cc * 1.512, 3), round(y0 + rr * RH, 3)] for rr, cc in (divmod(b, cols_n) for b in range(n))])
        s['bit_sites_um'] = blk; s['bit_site_cell_um'] = [CW, RH]
        s['note'] = (s.get('note', '') + f' | VISLAYOUT2-HBM 11-11 G1: through the central macro-free channel x {G0:.0f}-{G1:.0f}, path {L:.0f} um, {k} stations').strip(' |')
        if k != k0:
            lid = s['name'].split('x')[0].rstrip('m')
            lat = p['latency']['lanes'][lid]
            for key in ('cycles', 'stations', 'natural'):
                lat[key] = int(lat[key]) + (k - k0)
            lat['note'] = (lat.get('note', '') + f' | VISLAYOUT2-HBM 11-11 G1: +{k - k0} station in {tn} {s["name"]}').strip(' |')
        rep.append((tn, s['name'], s['width'], round(L), k0, k, round(L / k)))
    # E groups move right by (CHW - 94.96 - (60.48 - LEFT)); internal stations ending on an E-group core then need
    # one more register (core_place re-routes them with the count it finds): +1 station, declared in latency.lanes
    dxE = LEFT + 4 * PW + CHW - 915.84
    if dxE > 0.5 and not NOADD:
        for st in t.get('internal_stations', []):
            if st['to_um'][0] >= 1600 and st['from_um'][0] < 1600:
                fr, te = st['from_um'], st['to_um']
                need = abs(fr[0] - te[0] - dxE) + abs(fr[1] - te[1]) + 70.0      # new length + reroute margin
                add = 0
                while (len(st['regs_um']) + 1) * 360 * 0.8 < need:          # core_place limit (regs+1) x reach x 0.8
                    lr = st['regs_um'][-1]
                    st['regs_um'] = st['regs_um'] + [[round((lr[0] + te[0] + dxE) / 2, 2), round((lr[1] + te[1]) / 2, 2)]]
                    add += 1
                if not add:
                    continue
                lid = st['conn'].split(':')[1].split('_')[0]
                lat = p['latency']['lanes'].get(lid)
                if lat is not None:
                    for key in ('cycles', 'stations', 'natural'):
                        lat[key] = int(lat[key]) + add
                st['note'] = (st.get('note', '') + f' | VISLAYOUT2-HBM 11-11 G1: +{add} register (E group +{dxE:.1f} um)').strip(' |')
                rep.append((tn, f'station+{add}', st['conn'], st['bits'], lid, lat is not None))
    t['note'] = (t.get('note', '') + f' | VISLAYOUT2-HBM 11-11 G1: central N-S transit channel {CHW:g} um through both macro rows').strip(' |')
    rep.append((tn, 'channel', G0, G1, 'E strip', round(W_ - (G1 + 4 * PW), 2)))
json.dump(p, open(dst, 'w'), indent=1)
json.dump(seed, open(seed_out, 'w'), indent=1)
for r in rep: print(*r)
