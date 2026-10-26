#!/usr/bin/env python3
"""Q-DIEPLAN (Q-COMPUTE-DIE helper, 2026-10-16): parametric compute-die homes for a grown NK/NL tile outline.

usage: mk_dieplan.py TEMPLATE_HOMES OUT_HOMES [--tw 522.72] [--th 907.2] [--die-w 32996.16]

Same masters, same instances, same orientations as TEMPLATE (fpq_r2hs4); only positions move.
Field: 48 x 16 tiles, corridor 64.8 (station 52.68 + xcol 64.776 live in it), row gap 129.6, head gap y8-y7 = 1641.6
(xcol 1434.2 between s_c_7 and s_c_8); stations / heads keep their offsets to their tile (tap pins keep y).
Reticle: die width <= 33 mm, so the spine column is die_w - 2 x (24 x (tw + 64.8)) wide (4,752 um at 522.72).
The 4,872-um VM cannot sit in that column, so the plan is 'column + south band':
  south band (below the field): PHY row on the S edge (serdes x3, UCIe, KV UCIe), collective, the VM, and the KV
    stack native59 / d2d_rom / ucie_kv directly under the VM write face (x3 link ~0 instead of 10 mm)
  spine column: SU on the VM (seam = band top), seq_su on the SU W face, cbuf column on the SU E face;
    W strip = the three W slab stacks (res_ser | port | lanes abutted, centroids aligned: no gap jog);
    E strip = the three _f1 slabs (coordinator 07:40: each array half ends its bwords on its own side);
    middle strip = tt_ctlm, up4 leaves, xs_tap at the head row, clocks/resets.
"""
import argparse, json, math
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument('template'); ap.add_argument('out')
ap.add_argument('--tw', type=float, default=522.72); ap.add_argument('--th', type=float, default=907.2)
ap.add_argument('--die-w', type=float, default=32996.16)
ap.add_argument('--b0', type=float, default=None, help='band-0 port centre y (default: lowest legal)')
ap.add_argument('--mode', choices=('band', 'centre', 'owner'), default='band',
                help='band: VM/collective/PHY in a south band (wide tile); centre: 5-column W array|W ports|core|E ports|E array')
ap.add_argument('--pairs', choices=('split', 'together'), default='split',
                help='split: port_k on the W strip, _f1 on the E strip (each array half beside its words); together: [port|f1] centred')
a = ap.parse_args()
T = json.load(open(a.template)); H = T['homes']
TW, TH = a.tw, a.th
CORR, RGAP, HG, X0, STY = 64.8, 129.6, 1641.6, 21.6, 410.4
PC, PR = TW + CORR, TH + RGAP
g = lambda v, q=2.16: round(round(v / q) * q, 3)          # placement grid
G = 21.6                                                    # block gap (one row gap unit)

FIELD_W = 24 * PC                                           # one half incl. its last corridor
XS = X0 + FIELD_W - X0                                      # W field: x0 21.6 .. 21.6 + 24 PC (corridor end)
XS = X0 + 24 * PC
RIGHT_MARGIN = 33.72
S = a.die_w - 2 * XS - (TW + 52.68 + RIGHT_MARGIN - PC) + 0.0
# die_w = XS + S + 23 PC + TW + 52.68 + 33.72  ->  S
S = a.die_w - XS - 23 * PC - TW - 52.68 - RIGHT_MARGIN
XE = XS + S
assert S > 3000, S
out = {}
def put(n, x, y, o=None):
    h = dict(H[n]); h.update(x=round(x, 3), y=round(y, 3))
    if o: h['o'] = o
    if n.startswith('t_'): h.update(w=TW, h=TH)
    out[n] = h
def W(n): return H[n]['w']
def Hh(n): return H[n]['h']

if a.mode == 'owner':
    # owner 07:50 layout on a tall tile (same width -> 7.86-mm centre): W array | port_k strip | core | _f1 strip | E array.
    # Each pair's 6,704-b port<->f1 link is one centroid line across the core: it is placed in a block-free channel
    # (b0 between the collective and native59, b1 just over the SU, b2 over the core top), never over the VM/SU.
    YF = 21.6
    def rowy(r): return YF + r * PR if r < 8 else YF + (r - 1) * PR + HG
    for n in H:
        p = n.split('_')
        if p[0] == 't':
            c, r = int(p[1]), int(p[2]); put(n, X0 + c * PC if c < 24 else XE + (c - 24) * PC, rowy(r))
    for n, h in H.items():
        p = n.split('_')
        if p[0] == 's' and len(p) == 3 and p[1].isdigit():
            c, r = int(p[1]), int(p[2]); t = out[f't_{c}_{r}']; put(n, t['x'] + TW, t['y'] + (h['y'] - H[f't_{c}_{r}']['y']))
        elif p[0] == 'h' and len(p) == 2 and p[1].isdigit():
            c = int(p[1]); t = out[f't_{c}_7']; put(n, t['x'] + TW, t['y'] + (h['y'] - H[f't_{c}_7']['y']))
    FIELD_TOP = rowy(15) + TH; DIE_H = g(FIELD_TOP + 25.92)
    OH = T['die']['h']; oxs = 21.6 + 24 * 522.72
    PW = W('sp_port_tiles_0'); F1X = XE - PW - 129.6
    PH = Hh('sp_port_tiles_0'); RS = Hh('sp_res_ser_0'); LN = Hh('sp_band_lanes_0'); GL, GR = 43.2, 86.4
    HALF = 130.0 + G                                            # a 260-um cut window around each pair line, kept block-free
    BIN = 260.0                                                 # cuts.py FINE window grid (edges at k x 260 um)
    def onbin(c):                                               # the pair line on a window centre: its window is block-free
        return g(math.floor(c / BIN) * BIN + BIN / 2) if (c % BIN) <= BIN / 2 else g(math.ceil(c / BIN) * BIN + BIN / 2)
    def gapfree(y0):                                            # lanes gap [y0, y0+43.2] between two 50-um scan lines
        k = math.floor(y0 / 50.0); f = y0 - 50.0 * k
        return y0 if 0.5 <= f <= 6.3 else 50.0 * (k + 1) + 2.16
    PHY = ('io_serdes', 'io_serdes_1', 'io_serdes_2', 'io_ucie')
    TOP = ('ucie_kv', 'd2d_rom', 'bump_fwd_lrst', 'bump_fwd_epoch', 'ckb_rom', 'rs_bump')
    SLAB = [f'sp_{k}_{b}' for k in ('port_tiles', 'band_lanes', 'res_ser') for b in range(3)] + [f'sp_port_tiles_{b}_f1' for b in range(3)]
    for n in PHY:
        put(n, H[n]['x'] - oxs + XS, H[n]['y'])
    phy_top = max(out[n]['y'] + out[n]['h'] for n in PHY)
    coll = H['io_collective']
    put('io_collective', g(F1X - G - coll['w']), g(phy_top + G))
    below = lambda: RS + GR + PH / 2                            # MX: res_ser under the port
    above_r0 = lambda: LN + GL + PH / 2                         # R0: lanes under the port
    c0 = onbin(max(phy_top + G + below(), out['io_collective']['y'] + coll['h'] + HALF))
    vm = H['sp_vector_memory']; DX = g(F1X - G - (vm['x'] + vm['w']))
    nat_y = g(c0 + BIN / 2 + G)
    DYC = g(nat_y - H['native59']['y'])
    for n, h in H.items():
        if n in out or n in SLAB or n in TOP or n in ('io_collective',): continue
        put(n, h['x'] + DX, h['y'] + DYC)                       # hub cluster moves rigidly (abutments kept)
    for n in TOP:
        put(n, H[n]['x'] + DX, DIE_H - (OH - H[n]['y']))
    su = out['sp_su64_sfu']; su_top = su['y'] + su['h']
    vmh = out['sp_vector_memory']; vmh['y'] = round(su['y'] - vmh['h'] - 0.024, 3)   # su_vm_abut: 0 <= gap (fp-safe 24 nm)
    core_top = max(out[n]['y'] + out[n]['h'] for n in H if n not in SLAB and n not in TOP and n in out
                   and not n.startswith(('t_', 's_', 'h_')) and out[n]['y'] < su_top + 10)
    c1 = onbin(core_top + HALF)
    # stack orientation per band: b0 MX (res_ser low), b1 R0 (lanes low), b2 MX (res_ser low)
    ori = {0: 'MX', 1: 'R0', 2: 'MX'}
    def stack(b, c):
        # the port moves <= 60 um inside its line's window so the 43.2-um lanes gap lies between two 50-um scan lines
        # (the cut model lumps the 8,192-b ty/tw pair onto one centroid line; the real pins are straight 43-um stubs)
        ok = lambda v: 0.5 <= v % 50.0 <= 6.3
        for k in range(0, 560):
            d = (k // 2) * 0.216 * (1 if k % 2 == 0 else -1)
            p_y = g(c - PH / 2 + d, 0.216)
            if ori[b] == 'MX' and ok(p_y + PH): break
            if ori[b] == 'R0' and ok(p_y - GL): break
        if ori[b] == 'MX': rs_y = p_y - GR - RS; l_y = p_y + PH + GL; lo, hi = rs_y, l_y + LN
        else: l_y = p_y - GL - LN; rs_y = p_y + PH + GR; lo, hi = l_y, rs_y + RS
        return p_y, rs_y, l_y, lo, hi
    _, _, _, lo1, hi1 = stack(1, c1)
    _, _, _, lo0, hi0 = stack(0, c0)
    assert hi0 + G <= lo1, (hi0, lo1)
    c2 = onbin(hi1 + G + RS + GR + PH / 2)
    centres = []
    for b, c in enumerate((c0, c1, c2)):
        p_y, rs_y, l_y, lo, hi = stack(b, c)
        assert hi <= FIELD_TOP + 1e-3, (b, hi, FIELD_TOP)
        put(f'sp_res_ser_{b}', XS + (PW - W(f'sp_res_ser_{b}')) / 2, rs_y, ori[b])
        put(f'sp_port_tiles_{b}', XS, p_y, ori[b])
        put(f'sp_band_lanes_{b}', XS + (PW - W(f'sp_band_lanes_{b}')) / 2, l_y, ori[b])
        put(f'sp_port_tiles_{b}_f1', F1X, p_y)
        centres.append(p_y + PH / 2)
    l0 = out['sp_band_lanes_0']; lx = XS + PW + G
    for k in range(4):
        put(f'tt_up4_leaf{k}', lx + k * 86.4, g(l0['y'] + LN - Hh('tt_up4_leaf0')))
    for k, n in enumerate(('up4_sel_branch0', 'up4_sel_branch1', 'rstseq_rom')):
        put(n, lx + k * 86.4, g(l0['y'] + LN - Hh('tt_up4_leaf0') - 86.4))
    # embed / sys face: above the b1 line window, beside the SU top
    for n in ('embed_prov',):
        put(n, H[n]['x'] + DX, g(c1 + BIN / 2 + G))
    sf = (g(18900.0 + DX), g(c1 + BIN / 2 + G))
    # every pair line window must be block-free across the core
    core = [n for n in out if not n.startswith(('t_', 's_', 'h_')) and n not in SLAB]
    for c in (c0, c1, c2):
        for n in core:
            h = out[n]
            assert not (h['y'] < c + BIN / 2 and h['y'] + h['h'] > c - BIN / 2 and h['x'] < F1X and h['x'] + h['w'] > XS + PW), (n, c)
    DIE_W = a.die_w
    for n, h in out.items():
        assert h['x'] >= -1e-3 and h['y'] >= -1e-3 and h['x'] + h['w'] <= DIE_W + 1e-3 and h['y'] + h['h'] <= DIE_H + 1e-3, (n, h)
    res = dict(schema='opentallas.qwen.globalfp-q-homes.2210.v1', candidate=Path(a.out).stem.replace('-homes', ''),
               reserve={}, die=dict(w=DIE_W, h=DIE_H),
               params=dict(tile=[TW, TH], corridor=CORR, row_gap=RGAP, head_gap=HG, spine=round(S, 3), spine_x=[XS, XE],
                           sysface_xy=list(sf), port_centres=[round(c, 1) for c in centres], core_dx=DX, core_dy=DYC,
                           mode='owner: W array | port_k | core | _f1 | E array (tall tile)', source='mk_dieplan.py'),
               homes=out)
    Path(a.out).write_text(json.dumps(res, indent=1) + '\n')
    print(json.dumps(dict(die=[DIE_W, DIE_H], mm2=round(DIE_W * DIE_H / 1e6, 1), spine=round(S, 1), sysface=sf, ports=res['params']['port_centres'])))
    raise SystemExit(0)

if a.mode == 'centre':
    # field from the die bottom (no band); core = template spine core shifted to clear the E (_f1) strip and stretched
    # with the field rows; PHY row stays on the S edge; top-edge KV PHY / d2d follow the die top
    YF = 21.6
    def rowy(r): return YF + r * PR if r < 8 else YF + (r - 1) * PR + HG
    for n in H:
        p = n.split('_')
        if p[0] == 't':
            c, r = int(p[1]), int(p[2]); put(n, X0 + c * PC if c < 24 else XE + (c - 24) * PC, rowy(r))
    for n, h in H.items():
        p = n.split('_')
        if p[0] == 's' and len(p) == 3 and p[1].isdigit():
            c, r = int(p[1]), int(p[2]); t = out[f't_{c}_{r}']; put(n, t['x'] + TW, t['y'] + (h['y'] - H[f't_{c}_{r}']['y']))
        elif p[0] == 'h' and len(p) == 2 and p[1].isdigit():
            c = int(p[1]); t = out[f't_{c}_7']; put(n, t['x'] + TW, t['y'] + (h['y'] - H[f't_{c}_7']['y']))
    FIELD_TOP = rowy(15) + TH; DIE_H = g(FIELD_TOP + 25.92)
    OH = T['die']['h']; OTOP = OH - 25.92
    oxs = 21.6 + 24 * 522.72                                    # template spine start (457.92 tile)
    def ostretch(y):                                            # template field row -> new field row (same fraction)
        o7, o8 = 21.6 + 7 * 950.4, 21.6 + 7 * 950.4 + 1641.6
        if y <= o7 + 950.4: return YF + (y - 21.6) * PR / 950.4
        if y < o8: return rowy(7) + (y - o7) * (rowy(8) - rowy(7)) / (o8 - o7)
        return rowy(8) + (y - o8) * PR / 950.4
    PW = W('sp_port_tiles_0'); F1X = XE - PW - 129.6
    vm = H['sp_vector_memory']; DX = g(F1X - G - (vm['x'] + vm['w']))
    STRETCH = ('io_collective', 'embed_prov')
    DYC = g(ostretch(vm['y'] + vm['h']) - (vm['y'] + vm['h']))
    PHY = ('io_serdes', 'io_serdes_1', 'io_serdes_2', 'io_ucie')
    TOP = ('ucie_kv', 'd2d_rom', 'bump_fwd_lrst', 'bump_fwd_epoch', 'ckb_rom', 'rs_bump')
    SLAB = [f'sp_{k}_{b}' for k in ('port_tiles', 'band_lanes', 'res_ser') for b in range(3)] + [f'sp_port_tiles_{b}_f1' for b in range(3)]
    for n, h in H.items():
        if n in out or n in SLAB: continue
        if n in PHY: put(n, h['x'] - oxs + XS, h['y'])
        elif n in TOP: put(n, h['x'] + DX, DIE_H - (OH - h['y']))
        elif n in STRETCH: put(n, h['x'] + DX, g(ostretch(h['y'])))
        else: put(n, h['x'] + DX, h['y'] + DYC)            # the hub cluster moves rigidly (abutments kept)
    PH = Hh('sp_port_tiles_0'); RS = Hh('sp_res_ser_0'); LN = Hh('sp_band_lanes_0'); GL, GR = 43.2, 86.4
    centres = []
    lo = max(out[n]['y'] + out[n]['h'] for n in PHY) + G
    for b in range(3):
        o = H[f'sp_port_tiles_{b}']; yc = g(ostretch(o['y'] + PH / 2))
        p_y = yc - PH / 2
        if b < 2: rs_y = p_y - GR - RS; l_y = p_y + PH + GL
        else: l_y = p_y - GL - LN; rs_y = p_y + PH + GR
        bot = min(rs_y, l_y)
        if bot < lo: rs_y, p_y, l_y = rs_y + lo - bot, p_y + lo - bot, l_y + lo - bot
        put(f'sp_res_ser_{b}', XS + (PW - W(f'sp_res_ser_{b}')) / 2, rs_y)
        put(f'sp_port_tiles_{b}', XS, p_y)
        put(f'sp_band_lanes_{b}', XS + (PW - W(f'sp_band_lanes_{b}')) / 2, l_y)
        put(f'sp_port_tiles_{b}_f1', F1X, p_y)
        centres.append(p_y + PH / 2); lo = max(rs_y, l_y) + max(RS, LN) + G
    # band-upper leaves / up4 select relays / reset root: template had them between port and f1 (W of the core);
    # here they sit on the lanes_0 E face (pword_0 2,058 b), clear of the W port strip
    l0 = out['sp_band_lanes_0']; lx = XS + PW + G
    for k in range(4):
        put(f'tt_up4_leaf{k}', lx + k * 86.4, g(l0['y'] + LN - Hh('tt_up4_leaf0')))
    for k, n in enumerate(('up4_sel_branch0', 'up4_sel_branch1', 'rstseq_rom')):
        put(n, lx + k * 86.4, g(l0['y'] + LN - Hh('tt_up4_leaf0') - 86.4))
    sf = (18900.0 + DX, g(ostretch(12420.0)))
    assert out['io_collective']['y'] + out['io_collective']['h'] + G <= out['native59']['y'], 'collective under native59'
    DIE_W = a.die_w
    for n, h in out.items():
        assert h['x'] >= -1e-3 and h['y'] >= -1e-3 and h['x'] + h['w'] <= DIE_W + 1e-3 and h['y'] + h['h'] <= DIE_H + 1e-3, (n, h)
    res = dict(schema='opentallas.qwen.globalfp-q-homes.2210.v1', candidate=Path(a.out).stem.replace('-homes', ''),
               reserve={}, die=dict(w=DIE_W, h=DIE_H),
               params=dict(tile=[TW, TH], corridor=CORR, row_gap=RGAP, head_gap=HG, spine=round(S, 3), spine_x=[XS, XE],
                           sysface_xy=list(sf), port_centres=[round(c, 1) for c in centres], core_dx=DX,
                           mode='centre: W array | port_k | core | _f1 | E array', source='mk_dieplan.py'),
               homes=out)
    Path(a.out).write_text(json.dumps(res, indent=1) + '\n')
    print(json.dumps(dict(die=[DIE_W, DIE_H], mm2=round(DIE_W * DIE_H / 1e6, 1), spine=round(S, 1), sysface=sf, ports=res['params']['port_centres'])))
    raise SystemExit(0)

# ---------------- south band ----------------
Y_PHY = 21.6
kv_stack = Y_PHY + Hh('ucie_kv') + G + Hh('d2d_rom') + G + Hh('native59') + G     # native59 top + gap
VM_Y = g(max(kv_stack, Y_PHY + Hh('io_serdes') + G))
YF = g(VM_Y + Hh('sp_vector_memory'))                       # field bottom = VM top = SU bottom
VM_Y = YF - Hh('sp_vector_memory')

def rowy(r): return YF + r * PR if r < 8 else YF + (r - 1) * PR + HG
for n, h in H.items():
    p = n.split('_')
    if p[0] == 't':
        c, r = int(p[1]), int(p[2])
        x = X0 + c * PC if c < 24 else XE + (c - 24) * PC
        put(n, x, rowy(r))
for n, h in H.items():
    p = n.split('_')
    if p[0] == 's' and len(p) == 3 and p[1].isdigit():
        c, r = int(p[1]), int(p[2]); t = out[f't_{c}_{r}']
        put(n, t['x'] + TW, t['y'] + (h['y'] - H[f't_{c}_{r}']['y']))
    elif p[0] == 'h' and len(p) == 2 and p[1].isdigit():
        c = int(p[1]); t = out[f't_{c}_7']
        put(n, t['x'] + TW, t['y'] + (h['y'] - H[f't_{c}_7']['y']))
FIELD_TOP = rowy(15) + TH
DIE_H = g(FIELD_TOP + 25.92)

# ---------------- spine column: SU cluster on the band ----------------
SU_X = g(XS + W('seq_su') + 0.216)                        # seq_su abuts the SU W face at the column edge
put('sp_su64_sfu', SU_X, YF)
put('seq_su', SU_X - W('seq_su') - 0.216 + 0.216, g(YF + 300.0))
# VM under the SU: VM N-face SU pins (x ~0.92-1.18 mm) under the SU S-face va/vq pins (x 0.06-0.31 mm)
VM_X = g(SU_X - 860.0)
put('sp_vector_memory', VM_X, VM_Y)
# KV stack under the VM write face (VM S-face ar/q/commit at x 4.21-4.41 mm; native59 pins on its N face)
NX = g(VM_X + 4311.0 - 243.0)
put('native59', NX, VM_Y - G - Hh('native59'))
put('d2d_rom', NX + 150.0, out['native59']['y'] - G - Hh('d2d_rom'), 'R0')
put('ucie_kv', NX, Y_PHY, 'R0')
# KV-side bumps beside the d2d / KV PHY
bx = NX + W('native59') + G
for k, n in enumerate(('bump_fwd_lrst', 'bump_fwd_epoch', 'ckb_rom', 'rs_bump')):
    put(n, bx + k * 64.8, Y_PHY + 400.0)
# collective W of the VM (band row 2), its N-face in/out toward seq_su; PHY row under it
CX = g(VM_X - G - W('io_collective'))
put('io_collective', CX, g(Y_PHY + Hh('io_serdes') + G))
ux = g(CX + 2442.0 - W('io_ucie') / 2)
put('io_ucie', ux, Y_PHY)
put('io_serdes', g(ux + W('io_ucie') + G), Y_PHY)
put('io_serdes_1', g(ux - G - W('io_serdes_1')), Y_PHY)
put('io_serdes_2', g(out['io_serdes_1']['x'] - G - W('io_serdes_2')), Y_PHY)
# cbuf column on the SU E face (cq/ca pins at SU y 0.66-1.90 mm), crom pairs in two columns beside it
cx = SU_X + W('sp_su64_sfu') + G
order = [6, 7, 4, 2, 3, 0, 5, 1]                          # template order of the cq pins up the SU E face
for k, i in enumerate(order):
    put(f'cbuf_g_{i}', cx, g(YF + 560.0 + k * (Hh('cbuf_g_0') + 4.32)))
    put(f'crom_g_{i}', cx + (1 + k % 2) * (W('crom_g_0') + G), g(YF + 300.0 + (k // 2) * (Hh('crom_g_0') + 4.32)))
assert cx + 3 * W('crom_g_0') + 2 * G <= XE + 1e-3
# embed provider beside seq_su (code word 512 b), sys_face beside the d2d (rx / prog records 1,096 b)
put('embed_prov', g(VM_X - W('embed_prov') - G), YF - Hh('embed_prov') - G)
SYSFACE = (g(bx + 4 * 64.8 + G), g(out['d2d_rom']['y']))      # 302.4 x 216 (sited by OT_SPLIT_SYSFACE_XY)

# ---------------- spine column: slab strips ----------------
SU_TOP = YF + Hh('sp_su64_sfu')
PW = W('sp_port_tiles_0')
if a.pairs == 'split':
    port_x, F1X = XS, XE - PW - 129.6                       # f1: one row-gap channel off the E array (bword jogs)
else:
    port_x = g((XS + XE) / 2 - PW - 261.36); F1X = port_x + PW + 522.72
PH = Hh('sp_port_tiles_0'); RS = Hh('sp_res_ser_0'); LN = Hh('sp_band_lanes_0')
GL, GR = 43.2, 86.4                                         # lanes gap (pin jog <= 13 um), res_ser gap (rq jog <= 146 um)
yc0 = a.b0 if a.b0 else SU_TOP + 300.0 + RS + GR + PH / 2   # the stack clears the SU / crom column
centres = []
y = yc0 - PH / 2 - RS - GR                                  # b0: MX stack res_ser | port | lanes
for b in range(3):
    if b < 2:   # MX: res_ser bottom, port, lanes top
        rs_y = y; p_y = y + RS + GR; l_y = p_y + PH + GL; top = l_y + LN
    else:       # R0: lanes bottom, port, res_ser top
        l_y = y; p_y = y + LN + GL; rs_y = p_y + PH + GR; top = rs_y + RS
    # centroids aligned: the pin-straight stubs cross no vertical cut line
    put(f'sp_res_ser_{b}', port_x + (PW - W(f'sp_res_ser_{b}')) / 2, rs_y)
    put(f'sp_port_tiles_{b}', port_x, p_y)
    put(f'sp_band_lanes_{b}', port_x + (PW - W(f'sp_band_lanes_{b}')) / 2, l_y)
    put(f'sp_port_tiles_{b}_f1', F1X, p_y)
    centres.append(p_y + PH / 2)
    y = top + G
assert y <= FIELD_TOP, (y, FIELD_TOP)
# ---------------- middle strip ----------------
if a.pairs == 'split':
    MX0 = XS + PW + G; MX1 = F1X - G
else:
    MX0 = XS + G; MX1 = port_x - G
mid = (MX0 + MX1) / 2
l0 = out['sp_band_lanes_0']
put('xs_tap', g(XS + W('seq_su') + 900.0), g(SU_TOP + G))     # on the SU top, W part (xsw/xaw), toward both heads
put('tt_ctlm', g(XS + W('seq_su') + 1200.0) if a.pairs == 'split' else MX0, g(SU_TOP + G))
lx = l0['x'] + W('sp_band_lanes_0') + G
for k in range(4):                                           # up4 leaves on the lanes_0 E side (pword_0 2,058 b)
    put(f'tt_up4_leaf{k}', lx + k * 86.4, g(l0['y'] + LN - Hh('tt_up4_leaf0')))
put('up4_sel_station', lx + 4 * 86.4, g(l0['y'] + LN - 30.0))
for k in range(2):                                           # template-only relay homes (dropped on rebase)
    put(f'up4_sel_branch{k}', lx + 4 * 86.4 + 21.6 * (k + 1), g(l0['y'] + LN - 30.0))
tt = out['tt_ctlm']
put('res_train_issue', tt['x'] + tt['w'] + G, g(SU_TOP + G))
put('rstseq_rom', tt['x'] + tt['w'] + G, g(SU_TOP + G + 200.0))
put('clk_rx', g(tt['x'] + tt['w'] + G), g(tt['y'] + tt['h'] + 400.0))
missing = sorted(set(H) - set(out))
for n in missing:
    if n in ('sys_face',):
        out[n] = dict(H[n]); out[n].update(x=SYSFACE[0], y=SYSFACE[1])
    else:
        raise SystemExit(f'no home for {n}')
DIE_W = a.die_w
for n, h in out.items():
    assert h['x'] >= -1e-3 and h['y'] >= -1e-3 and h['x'] + h['w'] <= DIE_W + 1e-3 and h['y'] + h['h'] <= DIE_H + 1e-3, (n, h)
res = dict(schema='opentallas.qwen.globalfp-q-homes.2210.v1', candidate=Path(a.out).stem.replace('-homes', ''),
           reserve={}, die=dict(w=DIE_W, h=DIE_H),
           params=dict(tile=[TW, TH], corridor=CORR, row_gap=RGAP, head_gap=HG, spine=round(S, 3), spine_x=[XS, XE],
                       band_top=YF, sysface_xy=list(SYSFACE), port_centres=[round(c, 1) for c in centres],
                       mode='column+south-band', source='mk_dieplan.py'),
           homes=out)
Path(a.out).write_text(json.dumps(res, indent=1) + '\n')
print(json.dumps(dict(die=[DIE_W, DIE_H], mm2=round(DIE_W * DIE_H / 1e6, 1), spine=round(S, 1), band_top=YF,
                      sysface=SYSFACE, ports=res['params']['port_centres'])))
