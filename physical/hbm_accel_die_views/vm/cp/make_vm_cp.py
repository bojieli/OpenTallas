#!/usr/bin/env python3
"""[vm8cp] VM8 TOP-DOWN RE-PLAN (2026-10-12, spec results/arch/hier_contract_1011/vm8_replan.md): logic tiles + channel
relay tiles in place of the 8 halves x 6 grid sub-tiles.

WHY: r3-r11 failed on a different tile almost every round (corner-pin DRT-0255, GPL-0305 divergence at 3.5% util, face
pins 9.4-12 b/um/layer, a 25k-sink core tile, GRT-0183 on crossing nets f_w_wr__t[*], DRT stuck at 577 / 6,686).  The
cause is the partition: a VM half is ~85% feed-through flops (sw_e: 86k sinks, root_x 10.7k), carried on fixed-width
2,264 / 2,256 / 256-bit ring buses whose live content is a few hundred to 2,063 bits, plus placeholder pass-throughs
(f_su -> t_su / t_quant / t_router, no VM function) that cross the whole 1.4 mm VM through every tile.

PLAN (function first, then wires): the VM function is ONE multicast root (ot_hfd_vm_root_x) + 22 SRAMs in 4 slices; its
live traffic is wr data 2,048 + wr req 217 (in), rd req 201, cfg 1, the 2,063-bit published row to the 4 x faces and
202 status bits.  The root and its slices form a compact cluster at the VM centre-left; every bus leaves the tiles and
travels in die-level channels through registered relay tiles (one flop per bit, pins on two opposite faces, <= ~400 um
per hop); the four placeholder streams run in a bottom and a top lane (3 relays each) and never enter a logic tile.
Die pins stay on their faces (W: SW/NW, E: SE/NE); t_quant (NW N face) and t_router (SW W face) move to the NW W face.

    python3 make_vm_cp.py            (writes rtl/*.sv, hfd_vm_cp.sv, specs/<kit>.json, budget.json; prints the budget)
"""
import json, math, sys
from pathlib import Path

D = Path(__file__).resolve().parent
RTL = D / 'rtl'
VMH, VMW = 2000.112, 1399.632           # VM region (the 4 r22 quadrant slots, origin = hb_vm_sw origin)
FH = 498.96                             # face tile height (231 x 2.16 lattice; 4 per face)
BPU = 0.62                              # placed um2 per relay flop bit (DFF + clock / hold share, ASAP7 RVT)
UTIL = 0.45
HV = {'W': 'M4 M6', 'E': 'M4 M6', 'N': 'M3 M5', 'S': 'M3 M5'}   # pin layers per face (signals M2-M6, PG M7)

def snap(v, g): return round(math.ceil(v / g - 1e-9) * g, 3)

# ------------------------------------------------------------------------------------------------- relay kits
# kit: ports {name: (dir, width, face)}, outs {port: [segments, msb first]}; segment ('p', port, hi, lo) | ('fclk', n)
# | ('cat', [...]) ; every non-fclk output bit is one flop whose D is an input pin bit (no logic in a relay tile).
def P(port, hi, lo): return ('p', port, hi, lo)
def P2(port, hi, lo): return ('p2', port, hi, lo)   # two flops: keeps the monolith's in-bus alignment

KITS = {}
def kit(name, h, ports, outs, note):
    KITS[name] = dict(h=h, ports=ports, outs=outs, note=note)

kit('vm_cp_fw0', FH, {'f_su_SW': ('in', 2048, 'W'), 'iSW': ('in', 512, 'W'), 'qSW': ('out', 582, 'W'),
                      'ph': ('out', 2048, 'E', (2, 300)), 'wd': ('out', 2048, 'E', (300, 498))},
    {'qSW': [('fclk', 2), P2('f_su_SW', 2047, 1980), P('iSW', 511, 0)], 'ph': [P('f_su_SW', 2047, 0)],
     'wd': [P('f_su_SW', 2047, 0)]}, 'SW die face lo: f_su_SW -> placeholder lane (ph) + root wr data (wd); q face')
kit('vm_cp_fw1', FH, {'t_su_SW': ('out', 2048, 'W'), 'xSW': ('out', 2068, 'W'),
                      'ph': ('in', 1078, 'E', (2, 200)), 'tap': ('in', 2063, 'E', (200, 498)), 'st': ('in', 970, 'E', (200, 498))},
    {'t_su_SW': [P('ph', 1077, 0), P('st', 969, 0)], 'xSW': [('fclk', 5), P('tap', 2062, 0)]},
    'SW die face hi: t_su_SW = {f_su_SE[1077:0], root status}; xSW tap row')
kit('vm_cp_fw2', FH, {'t_su_NW': ('out', 2048, 'W'), 't_router': ('out', 512, 'W'), 't_quant': ('out', 1024, 'W'),
                      'xNW': ('out', 2068, 'W'), 'ph': ('in', 2048, 'E', (250, 498)), 'tap': ('in', 2063, 'E', (2, 250))},
    {'t_su_NW': [P('ph', 2047, 0)], 't_router': [P('ph', 1535, 1024)], 't_quant': [P('ph', 1023, 0)],
     'xNW': [('fclk', 5), P('tap', 2062, 0)]},
    'NW die face lo: f_su_NE placeholders (t_su_NW, t_router, t_quant moved here) + xNW tap row')
kit('vm_cp_fw3', FH, {'f_su_NW': ('in', 2048, 'W'), 'iNW': ('in', 512, 'W'), 'qNW': ('out', 582, 'W'),
                      'ph': ('out', 2048, 'E', (60, 400)), 'wr': ('out', 217, 'E', (2, 60))},
    {'qNW': [('fclk', 2), P('f_su_NW', 2047, 1980), P('iNW', 511, 0)], 'ph': [P('f_su_NW', 2047, 0)],
     'wr': [P('f_su_NW', 216, 0)]}, 'NW die face hi: f_su_NW -> placeholder lane + root wr request; q face')
kit('vm_cp_fe0', FH, {'f_su_SE': ('in', 2048, 'E'), 'iSE': ('in', 512, 'E'), 'qSE': ('out', 582, 'E'),
                      'ph': ('out', 1078, 'W', (100, 498))},
    {'qSE': [('fclk', 2), P2('f_su_SE', 2047, 1980), P('iSE', 511, 0)], 'ph': [P('f_su_SE', 1077, 0)]},
    'SE die face lo: f_su_SE[1077:0] -> bottom lane (rd request forks at RB2); q face')
kit('vm_cp_fe1', FH, {'t_su_SE': ('out', 2048, 'E'), 'xSE': ('out', 2068, 'E'),
                      'ph': ('in', 2048, 'W', (2, 250)), 'tap': ('in', 2063, 'W', (250, 498))},
    {'t_su_SE': [P('ph', 2047, 0)], 'xSE': [('fclk', 5), P('tap', 2062, 0)]}, 'SE die face hi: t_su_SE <- f_su_SW; xSE')
kit('vm_cp_fe2', FH, {'t_su_NE': ('out', 2048, 'E'), 'xNE': ('out', 2068, 'E'),
                      'ph': ('in', 2048, 'W', (250, 498)), 'tap': ('in', 2063, 'W', (2, 250))},
    {'t_su_NE': [P('ph', 2047, 0)], 'xNE': [('fclk', 5), P('tap', 2062, 0)]}, 'NE die face lo: t_su_NE <- f_su_NW; xNE')
kit('vm_cp_fe3', FH, {'f_su_NE': ('in', 2048, 'E'), 'iNE': ('in', 512, 'E'), 'qNE': ('out', 582, 'E'),
                      'ph': ('out', 2048, 'W', (12, 400))},
    {'qNE': [('fclk', 2), P('f_su_NE', 2047, 1980), P('iNE', 511, 0)], 'ph': [P('f_su_NE', 2047, 0)]},
    'NE die face hi: f_su_NE -> top lane (cfg forks at RT2); q face')
# lane relays: W->E and E->W in one tile (both faces carry in + out)
kit('vm_cp_rb', 302.4, {'wi': ('in', 2048, 'W'), 'eo': ('out', 2048, 'E'), 'ei': ('in', 1078, 'E'), 'wo': ('out', 1078, 'W')},
    {'eo': [P('wi', 2047, 0)], 'wo': [P('ei', 1077, 0)]}, 'bottom lane relay: f_su_SW W->E, f_su_SE[1077:0] E->W')
kit('vm_cp_rb2', 302.4, {'wi': ('in', 2048, 'W'), 'eo': ('out', 2048, 'E'), 'ei': ('in', 1078, 'E'), 'wo': ('out', 1078, 'W'),
                         'rd': ('out', 201, 'N')},
    {'eo': [P('wi', 2047, 0)], 'wo': [P('ei', 1077, 0)], 'rd': [P('ei', 200, 0)]},
    'bottom lane relay E end + rd request fork north (to RE)')
kit('vm_cp_rt', 388.8, {'wi': ('in', 2048, 'W'), 'eo': ('out', 2048, 'E'), 'ei': ('in', 2048, 'E'), 'wo': ('out', 2048, 'W')},
    {'eo': [P('wi', 2047, 0)], 'wo': [P('ei', 2047, 0)]}, 'top lane relay: f_su_NW W->E, f_su_NE E->W')
kit('vm_cp_rt2', 388.8, {'wi': ('in', 2048, 'W'), 'eo': ('out', 2048, 'E'), 'ei': ('in', 2048, 'E'), 'wo': ('out', 2048, 'W'),
                         'cfg': ('out', 1, 'S')},
    {'eo': [P('wi', 2047, 0)], 'wo': [P('ei', 2047, 0)], 'cfg': [P('ei', 0, 0)]}, 'top lane relay E end + cfg fork south')
kit('vm_cp_rwa', 259.2, {'i': ('in', 2048, 'W'), 'o': ('out', 2048, 'E')}, {'o': [P('i', 2047, 0)]},
    'W channel: root write data relay')
kit('vm_cp_rwb', 108.0, {'i': ('in', 217, 'W'), 'o': ('out', 217, 'E')}, {'o': [P('i', 216, 0)]},
    'W channel: root write request relay')
kit('vm_cp_rwt', 518.4, {'tap': ('in', 2063, 'E', (244, 444)), 'st': ('in', 202, 'E', (244, 444)), 'sw': ('out', 2063, 'W', (2, 264)),
                         'nw': ('out', 2063, 'W', (268, 516)), 'sto': ('out', 970, 'W', (2, 264))},
    {'sw': [P('tap', 2062, 0)], 'nw': [P('tap', 2062, 0)],
     'sto': [P('st', 201, 10)] * 4 + [P('st', 201, 0)]},
    'W channel: tap row fork to xSW / xNW + status fan-out (tap_owner = 4 copies of the ACK owner)')
# FACE3 10-13 (cx4): se leaves on the S face and ne on the N face, bit k of both on ONE vertical track column (its flop on
# that column at the tap pin's y): the 1 -> 2 fork has no y shuffle left inside the tile (cx3: GRT-0116, vertical overflow
# at the se|ne seam y 175-225).  Width 259.2 (3 M3 tracks per column); the die routes S -> FE1 and N -> FE2.
kit('vm_cp_re', 388.8, {'tap': ('in', 2063, 'W', (70, 300)), 'se': ('out', 2063, 'S', (32, 257)), 'ne': ('out', 2063, 'N', (32, 257)),
                        'rdi': ('in', 201, 'S', (2, 31)), 'rdo': ('out', 201, 'W', (2, 60)), 'cfgi': ('in', 1, 'N', (2, 4)), 'cfgo': ('out', 1, 'W', (2, 60))},
    {'se': [P('tap', 2062, 0)], 'ne': [P('tap', 2062, 0)], 'rdo': [P('rdi', 200, 0)], 'cfgo': [P('cfgi', 0, 0)]},
    'E channel: tap row fork to xSE / xNE; rd request + cfg relays into the root E face')

def seg_w(s):
    return s[1] if s[0] == 'fclk' else s[2] - s[3] + 1

RE_SV = r"""// GENERATED by make_vm_cp.py ([vm8cp] E channel tile, cx5 FACE4 2026-10-13): tap row fork to xSE / xNE; rd request + cfg
// relays into the root E face.  EVERY pin has its own register AT the pin and no wire inside the tile is longer than
// ~305 um.  cx4 (one merged flop per fork bit at the corner x of its S/N pin, y of its tap pin) closed, but the die clock
// rule audit of its view (tools/hier_contract/pinreg_audit.py) reads o = 435.7 ps (ne), s = 315.8 ps (tap), o + s =
// 751.5 > 683.3: the tap pin drove up to 255 um of wire before the flop and the flop up to 305 um to the pin; the hops
// RE.se -> FE1.tap and RE.ne -> FE2.tap miss the die budget by 192 / 162 ps.  Three ranks per fork bit now:
//   t_w (at the W pin) -> t_c (the corner: the bit's S/N column, the tap pin's row) -> r_se (at the S pin), r_ne (at the N pin)
// = +2 cycles on the tap row towards the E faces; rdi -> rdo and cfgi -> cfgo take an input pin register = +1 cycle.
module vm_cp_re (input wire ck,
    input wire [2062:0] tap,
    output wire [2062:0] se,
    output wire [2062:0] ne,
    input wire [200:0] rdi,
    output wire [200:0] rdo,
    input wire [0:0] cfgi,
    output wire [0:0] cfgo);
    reg [2062:0] t_w; always @(posedge ck) t_w <= tap;
    reg [2062:0] t_c; always @(posedge ck) t_c <= t_w;
    (* keep = "true", dont_touch = "true" *) reg [2062:0] r_se_0; always @(posedge ck) r_se_0 <= t_c;
    (* keep = "true", dont_touch = "true" *) reg [2062:0] r_ne_0; always @(posedge ck) r_ne_0 <= t_c;
    assign se = r_se_0; assign ne = r_ne_0;
    reg [200:0] r_rdi; always @(posedge ck) r_rdi <= rdi;
    reg [200:0] r_rdo_0; always @(posedge ck) r_rdo_0 <= r_rdi;
    assign rdo = r_rdo_0;
    reg [0:0] r_cfgi; always @(posedge ck) r_cfgi <= cfgi;
    reg [0:0] r_cfgo_0; always @(posedge ck) r_cfgo_0 <= r_cfgi;
    assign cfgo = r_cfgo_0;
endmodule
"""

def relay_sv(name, k):
    if name == 'vm_cp_re':
        return RE_SV
    ps = k['ports']
    L = [f'// GENERATED by make_vm_cp.py ([vm8cp] relay tile; {k["note"]}): one flop per output bit, D = an input pin',
         '// bit, Q = the output pin (registered boundary both sides, no logic); fclk bits = forwarded clock (kept inverter).',
         f'module {name} (input wire ck,']
    decl = []
    for p, (d, w, f, *_r) in ps.items():
        decl.append(f'    {"input" if d == "in" else "output"} wire [{w-1}:0] {p}')
    L.append(',\n'.join(decl) + ');')
    for o, segs in k['outs'].items():
        w = ps[o][1]
        assert sum(seg_w(s) for s in segs) == w, (name, o)
        pos = w
        for s in segs:
            n = seg_w(s); lo = pos - n
            if s[0] == 'fclk':
                for b in range(n):
                    L.append(f'    ot_fwd_clk_inv u_fclk_{o}_{lo+b} (.a(ck), .y({o}[{lo+b}]));')
            else:
                src = f'{s[1]}[{s[2]}:{s[3]}]'
                if s[0] == 'p2':   # SW/SE q: f_su[2047:1980] is one cycle behind i[511:0] in hfd_vm (extra input stage)
                    L.append(f'    reg [{n-1}:0] r2_{o}_{lo}; always @(posedge ck) r2_{o}_{lo} <= {src};')
                    src = f'r2_{o}_{lo}'
                L.append(f'    reg [{n-1}:0] r_{o}_{lo}; always @(posedge ck) r_{o}_{lo} <= {src};')
                L.append(f'    assign {o}[{pos-1}:{lo}] = r_{o}_{lo};')
            pos = lo
    L.append('endmodule')
    return '\n'.join(L) + '\n'

# ------------------------------------------------------------------------------------------------- root plan (FACE3)
# Root pins are locked per bit (io_tcl) and every pin has its register next to it.  W / E pins on M4 at 2 tracks,
# S / N pins on M3 at 2 tracks.  Seat word k (72 code bits, 64 data bits 64k..64k+63) is written to a slice pin block
# and read back beside it (wd pin, rd pin alternate), so the read-back compare and the seat syndrome are local; the
# request registers (W: wd_i, wr_i; E: rd_i) and the tap ranks (W, E) reach it over wire-only paths.  Which word sits
# where is a bottleneck assignment over those three path lengths.  The slice bit order is free (a fixed permutation
# of the SRAM row): S = slice 0 then slice 2 (21 words + 24 unused bits), N = slice 1 then slice 3 (11 data words,
# 200 unused bits, the 4 owner words at the E end).
T3, T3O, T4, T4O = 0.036, 0.009, 0.048, 0.012
RW, RH = 302.4, 432.0
R_WD0, R_CK, R_TW0, R_WR0 = 50, 4150, 4158, 8290            # W face M4 tracks: wd_i[i] = R_WD0 + 2i, tap_w[j], wr_i[i]
R_RST, R_RD0, R_CFG, R_TE0 = 2160, 2170, 2574, 2600         # E face: rd_i straight below tap_e; tap_e straight across RE.tap
R_S0 = 334                                                  # S face first M3 track (pins centred on the face)
R_N0 = 70
# S / N pin pitch: alternately 2 and 3 M3 tracks (2.5 on average = 11.1 pins/um).  cx1 placed every S / N pin on 2
# tracks = 13.9 pins/um on one layer and was refused at the floorplan lint (FLOORPLAN_MARGIN pin_density > 12 b/um/layer
# over 100 um: S/M3 13.9 @40, N/M3 13.9 @3) before any placement; the S face now uses 278 of its 302.4 um.
SN = lambda i: (5 * i) // 2

def _bottleneck(cost):
    """rows -> distinct columns minimising the largest cost (threshold + Kuhn matching)"""
    n, m = len(cost), len(cost[0])
    vals = sorted({c for r in cost for c in r})
    def match(th):
        mc = [-1] * m
        def aug(i, seen):
            for j in range(m):
                if cost[i][j] <= th and j not in seen:
                    seen.add(j)
                    if mc[j] < 0 or aug(mc[j], seen):
                        mc[j] = i; return True
            return False
        for i in range(n):
            if not aug(i, set()): return None
        return mc
    lo, hi = 0, len(vals) - 1
    while lo < hi:
        mid = (lo + hi) // 2
        if match(vals[mid]) is None: lo = mid + 1
        else: hi = mid
    mc = match(vals[lo]); res = [None] * n
    for j, i in enumerate(mc):
        if i >= 0: res[i] = j
    return res, vals[lo]

def root_plan():
    """-> dict(pins={name: (face, track)}, s_words=[word at S position p], n_words=[...], n_own_off, paths)"""
    pins = {}
    for i in range(2048): pins[f'wd_i[{i}]'] = ('W', R_WD0 + 2 * i)
    pins['ck'] = ('W', R_CK)
    for j in range(2063): pins[f'tap_w[{j}]'] = ('W', R_TW0 + 2 * j); pins[f'tap_e[{j}]'] = ('E', R_TE0 + 2 * j)
    for i in range(217): pins[f'wr_i[{i}]'] = ('W', R_WR0 + 2 * i)
    pins['rst'] = ('E', R_RST); pins['cfg_i'] = ('E', R_CFG)
    for i in range(201): pins[f'rd_i[{i}]'] = ('E', R_RD0 + 2 * i)
    # S face sequence
    seq = [f'cmd0[{i}]' for i in range(10)] + ['rv0']
    for n in range(768): seq += [f'wd0[{n}]', f'rd0[{n}]']
    seq += [f'cmd2[{i}]' for i in range(10)] + ['rv2']
    for n in range(768): seq += [f'wd2[{n}]', f'rd2[{n}]']
    for i, nm in enumerate(seq): pins[nm] = ('S', R_S0 + SN(i))
    # N face: status at the W end, slice 1, slice 3 data tail, unused, owner words at the E end
    seq = [f'st_o[{i}]' for i in range(202)] + [f'cmd1[{i}]' for i in range(10)] + ['rv1']
    for n in range(768): seq += [f'wd1[{n}]', f'rd1[{n}]']
    seq += [f'cmd3[{i}]' for i in range(10)] + ['rv3']
    for n in range(224): seq += [f'wd3[{n}]', f'rd3[{n}]']
    for i, nm in enumerate(seq): pins[nm] = ('N', R_N0 + SN(i))
    n_end = R_N0 + SN(len(seq) - 1)
    own = []
    for n in range(224, 512): own += [f'wd3[{n}]', f'rd3[{n}]']
    e0 = round(RW / T3) - 70 - SN(len(own) - 1)
    assert e0 > n_end + 2, (e0, n_end)
    for i, nm in enumerate(own): pins[nm] = ('N', e0 + SN(i))
    xy = lambda nm: ((0.0 if pins[nm][0] == 'W' else RW, pins[nm][1] * T4 + T4O) if pins[nm][0] in 'WE'
                     else (pins[nm][1] * T3 + T3O, 0.0 if pins[nm][0] == 'S' else RH))
    mh = lambda a, b: abs(a[0] - b[0]) + abs(a[1] - b[1])
    def slot_xy(face, n):                           # centre of the 72-bit block starting at face bit n
        nm = (lambda q: (f'wd0[{q}]' if q < 768 else f'wd2[{q - 768}]')) if face == 'S' else \
             (lambda q: (f'wd1[{q}]' if q < 768 else f'wd3[{q - 768}]'))
        a, b = xy(nm(n)), xy(nm(n + 71))
        return ((a[0] + b[0]) / 2, a[1])
    def cost(k, s):
        d = 64 * k + 32
        return max(mh(xy(f'wd_i[{d}]'), s), mh(xy(f'tap_w[{d}]'), s), mh(xy(f'tap_e[{d}]'), s))
    s_slots = [slot_xy('S', 72 * p) for p in range(21)]
    s_words, s_max = _bottleneck([[round(cost(k, s), 1) for s in s_slots] for k in range(21)])
    n_slots = [slot_xy('N', 72 * q) for q in range(11)]
    n_words, n_max = _bottleneck([[round(cost(k, s), 1) for s in n_slots] for k in range(21, 32)])
    s_at = [None] * 21
    for k, pp in enumerate(s_words): s_at[pp] = k
    n_at = [None] * 11
    for i, q in enumerate(n_words): n_at[q] = 21 + i
    own_off = 768 + 224                              # N face bit offset of word 32 (wd3[224])
    o_xy = slot_xy('N', own_off + 144)
    paths = dict(s_words_max_um=s_max, n_words_max_um=n_max,
                 owner_from_wr_um=round(mh(xy('wr_i[120]'), o_xy), 1), owner_from_rd_um=round(mh(xy('rd_i[100]'), o_xy), 1),
                 owner_to_status_um=round(mh(xy('st_o[100]'), o_xy), 1),
                 tap_hi_from_w32_um=round(max(mh(xy('tap_w[2055]'), slot_xy('N', own_off)), mh(xy('tap_e[2055]'), slot_xy('N', own_off))), 1))
    return dict(pins=pins, s_at=s_at, n_at=n_at, own_off=own_off, paths=paths, xy=xy)

def root_sv():
    pl = root_plan()
    L = []
    for pp, k in enumerate(pl['s_at']):
        L.append(f'    assign s_wd[{72*pp+71}:{72*pp}] = m_wd[{72*k+71}:{72*k}]; assign m_rd[{72*k+71}:{72*k}] = s_rd[{72*pp+71}:{72*pp}];')
    for q, k in enumerate(pl['n_at']):
        L.append(f'    assign n_wd[{72*q+71}:{72*q}] = m_wd[{72*k+71}:{72*k}]; assign m_rd[{72*k+71}:{72*k}] = n_rd[{72*q+71}:{72*q}];')
    o = pl['own_off']
    L.append(f'    assign n_wd[{o+287}:{o}] = m_wd[2591:2304]; assign m_rd[2591:2304] = n_rd[{o+287}:{o}];')
    L.append(f"    assign s_wd[1535:1512] = 24'd0; assign n_wd[{o-1}:792] = {o-792}'d0; assign m_rd[2815:2592] = 224'd0;")
    return ROOT.replace('@MAP@', '\n'.join(L))

ROOT = r"""// GENERATED by make_vm_cp.py ([vm8cp] ROOT tile, FACE3 2026-10-13 pipelined): ot_hfd_vm_root_p (tiles/make_root_p.py) + the
// 772-bit cfg chain.  EVERY pin is a register: the request inputs (wd_i / wr_i / rd_i) and the slice rv pins are
// registered here, the slice read data is captured by the root's `sampled` register, the slice write data is the root's
// seat register, the slice commands, both tap rows and the status are registers inside the root.  ~14.5k sinks, one root.
// The four slices sit one hop from the root with IDENTICAL command and return depth (3 cycles pin to pin): the root
// captures in a fixed cycle (S_CAP) and faults if the rv pins were not all 1 in it; the simulation check below also
// fails on any rv outside that cycle.
// Slice bit order (root_plan() in make_vm_cp.py): seat word k sits in the pin block nearest its request pins and tap
// pins; S face = slice 0 then slice 2, N face = slice 1 then slice 3 (owner words at its E end, 200 + 24 unused bits).
module vm_cp_root (input wire ck, input wire rst,
    input wire [2047:0] wd_i, input wire [216:0] wr_i, input wire [200:0] rd_i, input wire cfg_i,
    output wire [2062:0] tap_w, output wire [2062:0] tap_e, output wire [201:0] st_o,
    output wire [9:0] cmd0, output wire [9:0] cmd1, output wire [9:0] cmd2, output wire [9:0] cmd3,
    output wire [767:0] wd0, output wire [767:0] wd1, output wire [767:0] wd2, output wire [511:0] wd3,
    input wire rv0, input wire rv1, input wire rv2, input wire rv3,
    input wire [767:0] rd0, input wire [767:0] rd1, input wire [767:0] rd2, input wire [511:0] rd3);
    reg [1:0] rst_s; always @(posedge ck) rst_s <= {rst_s[0], rst};
    (* keep = "true", dont_touch = "true" *) reg [10:0] rst_r; always @(posedge ck) rst_r <= {11{rst_s[1]}};
    reg [771:0] cfg; always @(posedge ck) cfg <= {cfg[770:0], cfg_i};
    reg [2047:0] wd_q; reg [216:0] wr_q; reg [200:0] rd_q; reg [3:0] rv_q;      // pin registers
    always @(posedge ck) begin wd_q <= wd_i; wr_q <= wr_i; rd_q <= rd_i; rv_q <= {rv3, rv2, rv1, rv0}; end
    wire [39:0] cmd; wire [2815:0] m_wd, m_rd; wire fault;
    wire [1535:0] s_wd, s_rd = {rd2, rd0}; wire [1279:0] n_wd, n_rd = {rd3, rd1};
@MAP@
    ot_hfd_vm_root_p u_mr (.clk(ck), .rst_r(rst_r), .mem_cmd_o(cmd), .mem_wd(m_wd), .mem_rv_q(rv_q), .mem_rd(m_rd),
        .wr_v(wr_q[15]), .wr_bank(wr_q[16]), .wr_addr(wr_q[23:17]), .wr_data({wr_q[14:0], wd_q}), .wr_owner(wr_q[215:24]),
        .wr_ACK_ready(wr_q[216]), .rd_v(rd_q[0]), .rd_bank(rd_q[1]), .rd_addr(rd_q[8:2]), .rd_owner(rd_q[200:9]),
        .tap_w(tap_w), .tap_e(tap_e), .tap_ACK_v(cfg[3:0]), .tap_ACK_owner(cfg[771:4]), .st_o(st_o), .fault(fault));
    assign cmd0 = cmd[9:0]; assign cmd1 = cmd[19:10]; assign cmd2 = cmd[29:20]; assign cmd3 = cmd[39:30];
    assign wd0 = s_wd[767:0]; assign wd2 = s_wd[1535:768]; assign wd1 = n_wd[767:0]; assign wd3 = n_wd[1279:768];
`ifndef SYNTHESIS
    wire [3:0] rv = {rv3, rv2, rv1, rv0};
    always @(posedge ck) if (!rst_r[0] && !fault && ((|rv) != (&rv) || (&rv) != (u_mr.on.state == 5'd8)))
        $fatal(1, "VM_CP slice returns not aligned / not in the capture cycle %b state %0d", rv, u_mr.on.state);
`endif
endmodule
"""

def slice_sv(nm):
    w = nm * 256
    return f'''// GENERATED by make_vm_cp.py ([vm8cp] SLICE tile, {2*nm} macros): ot_hfd_vm_slice NM={nm} (command registered at the
// macros, read data registered at the macro outputs) + its own reset sync.  cmd = {{addr[6:0], bank, we, v}}.
module vm_cp_slice{nm} (input wire ck, input wire rst, input wire [9:0] cmd, input wire [{w-1}:0] wd,
    output wire rv, output wire [{w-1}:0] rd);
    reg [1:0] rst_s; always @(posedge ck) rst_s <= {{rst_s[0], rst}};
    ot_hfd_vm_slice #(.NM({nm})) u_slice (.clk(ck), .rst_n(~rst_s[1]), .cmd_v(cmd[0]), .we(cmd[1]), .bank(cmd[2]),
        .addr(cmd[9:3]), .wd(wd), .rv(rv), .rd(rd));
endmodule
'''

LOGIC = {
    'vm_cp_root': dict(h=432.0, w=302.4, ports={
        'wd_i': ('in', 2048, 'W', (2, 200)), 'wr_i': ('in', 217, 'W', (400, 430)), 'tap_w': ('out', 2063, 'W', (200, 400)),
        'st_o': ('out', 202, 'W', (200, 400)), 'rd_i': ('in', 201, 'E', (2, 100)), 'cfg_i': ('in', 1, 'E', (2, 100)),
        'tap_e': ('out', 2063, 'E', (100, 330)), 'rst': ('in', 1, 'E', (2, 100)),
        'cmd0': ('out', 10, 'S'), 'wd0': ('out', 768, 'S'), 'rv0': ('in', 1, 'S'), 'rd0': ('in', 768, 'S'),
        'cmd2': ('out', 10, 'S'), 'wd2': ('out', 768, 'S'), 'rv2': ('in', 1, 'S'), 'rd2': ('in', 768, 'S'),
        'cmd1': ('out', 10, 'N'), 'wd1': ('out', 768, 'N'), 'rv1': ('in', 1, 'N'), 'rd1': ('in', 768, 'N'),
        'cmd3': ('out', 10, 'N'), 'wd3': ('out', 512, 'N'), 'rv3': ('in', 1, 'N'), 'rd3': ('in', 512, 'N')},
        note='multicast root + cfg chain, registered outputs; sized by the gate std area'),
    'vm_cp_slice3': dict(h=216.0, w=280.8, macros=6, ports={'cmd': ('in', 10, 'N'), 'wd': ('in', 768, 'N'),
        'rv': ('out', 1, 'N'), 'rd': ('out', 768, 'N'), 'rst': ('in', 1, 'N')}, note='6-macro slice (SW, NW, SE; NW mirrored MX); FACE3 10-13: 280.8 wide, pairs share a channel (slice3_pin_plan.py)'),
    'vm_cp_slice2': dict(h=216.0, w=259.2, macros=4, ports={'cmd': ('in', 10, 'N'), 'wd': ('in', 512, 'N'),
        'rv': ('out', 1, 'N'), 'rd': ('out', 512, 'N'), 'rst': ('in', 1, 'N')}, note='4-macro slice (NE, mirrored MX)'),
}

# ------------------------------------------------------------------------------------------------- instances
# (inst, kit, x, y, orient, {port: net})   x/y = lower-left in the VM region (um); widths of relay kits from area
XW = 12.96                              # gate: 10.8 um outlines leave 6.48 um core = PDN-0185 (no M7 strap pair)
XWK = {'vm_cp_rb2': 21.6, 'vm_cp_re': 259.2}   # 201-bit N / S faces; re = one track column per fork bit
INST = [
    ('u_fw0', 'vm_cp_fw0', 0, 0, 'R0', {'f_su_SW': 'f_su_SW', 'iSW': 'iSW', 'qSW': 'qSW', 'ph': 'n_fw0_ph', 'wd': 'n_fw0_wd'}),
    ('u_fw1', 'vm_cp_fw1', 0, FH, 'R0', {'t_su_SW': 't_su_SW', 'xSW': 'xSW', 'ph': 'n_rb0_wo', 'tap': 'n_rwt_sw', 'st': 'n_rwt_st'}),
    ('u_fw2', 'vm_cp_fw2', 0, 2 * FH, 'R0', {'t_su_NW': 't_su_NW', 't_router': 't_router', 't_quant': 't_quant', 'xNW': 'xNW',
                                             'ph': 'n_rt0_wo', 'tap': 'n_rwt_nw'}),
    ('u_fw3', 'vm_cp_fw3', 0, 3 * FH, 'R0', {'f_su_NW': 'f_su_NW', 'iNW': 'iNW', 'qNW': 'qNW', 'ph': 'n_fw3_ph', 'wr': 'n_fw3_wr'}),
    ('u_fe0', 'vm_cp_fe0', None, 0, 'R0', {'f_su_SE': 'f_su_SE', 'iSE': 'iSE', 'qSE': 'qSE', 'ph': 'n_fe0_ph'}),
    ('u_fe1', 'vm_cp_fe1', None, FH, 'R0', {'t_su_SE': 't_su_SE', 'xSE': 'xSE', 'ph': 'n_rb3_eo', 'tap': 'n_re_se'}),
    ('u_fe2', 'vm_cp_fe2', None, 2 * FH, 'R0', {'t_su_NE': 't_su_NE', 'xNE': 'xNE', 'ph': 'n_rt3_eo', 'tap': 'n_re_ne'}),
    ('u_fe3', 'vm_cp_fe3', None, 3 * FH, 'R0', {'f_su_NE': 'f_su_NE', 'iNE': 'iNE', 'qNE': 'qNE', 'ph': 'n_fe3_ph'}),
    ('u_rb0', 'vm_cp_rb', 172.8, 172.8, 'R0', {'wi': 'n_fw0_ph', 'eo': 'n_rb0_eo', 'ei': 'n_rb1_wo', 'wo': 'n_rb0_wo'}),
    ('u_rb1', 'vm_cp_rb', 518.4, 172.8, 'R0', {'wi': 'n_rb0_eo', 'eo': 'n_rb1_eo', 'ei': 'n_rb2_wo', 'wo': 'n_rb1_wo'}),
    ('u_rb2', 'vm_cp_rb2', 864.0, 172.8, 'R0', {'wi': 'n_rb1_eo', 'eo': 'n_rb2_eo', 'ei': 'n_rb3_wo', 'wo': 'n_rb2_wo',
                                                'rd': 'n_rb2_rd'}),
    ('u_rb3', 'vm_cp_rb', 1209.6, 172.8, 'R0', {'wi': 'n_rb2_eo', 'eo': 'n_rb3_eo', 'ei': 'n_fe0_ph', 'wo': 'n_rb3_wo'}),
    ('u_rt0', 'vm_cp_rt', 172.8, 1468.8, 'R0', {'wi': 'n_fw3_ph', 'eo': 'n_rt0_eo', 'ei': 'n_rt1_wo', 'wo': 'n_rt0_wo'}),
    ('u_rt1', 'vm_cp_rt', 518.4, 1468.8, 'R0', {'wi': 'n_rt0_eo', 'eo': 'n_rt1_eo', 'ei': 'n_rt2_wo', 'wo': 'n_rt1_wo'}),
    ('u_rt2', 'vm_cp_rt2', 864.0, 1468.8, 'R0', {'wi': 'n_rt1_eo', 'eo': 'n_rt2_eo', 'ei': 'n_rt3_wo', 'wo': 'n_rt2_wo',
                                                 'cfg': 'n_rt2_cfg'}),
    ('u_rt3', 'vm_cp_rt', 1209.6, 1468.8, 'R0', {'wi': 'n_rt2_eo', 'eo': 'n_rt3_eo', 'ei': 'n_fe3_ph', 'wo': 'n_rt3_wo'}),
    ('u_rwa', 'vm_cp_rwa', 129.6, 475.2, 'R0', {'i': 'n_fw0_wd', 'o': 'n_rwa_o'}),
    ('u_rwb', 'vm_cp_rwb', 129.6, 1274.4, 'R0', {'i': 'n_fw3_wr', 'o': 'n_rwb_o'}),
    ('u_rwt', 'vm_cp_rwt', 129.6, 734.4, 'R0', {'tap': 'n_root_tw', 'st': 'n_root_st', 'sw': 'n_rwt_sw', 'nw': 'n_rwt_nw',
                                                'sto': 'n_rwt_st'}),
    ('u_re', 'vm_cp_re', 950.4, 806.4, 'R0', {'tap': 'n_root_te', 'se': 'n_re_se', 'ne': 'n_re_ne', 'rdi': 'n_rb2_rd',
                                               'rdo': 'n_re_rd', 'cfgi': 'n_rt2_cfg', 'cfgo': 'n_re_cfg'}),
    ('u_root', 'vm_cp_root', 345.6, 777.6, 'R0', {'wd_i': 'n_rwa_o', 'wr_i': 'n_rwb_o', 'rd_i': 'n_re_rd', 'cfg_i': 'n_re_cfg',
        'tap_w': 'n_root_tw', 'tap_e': 'n_root_te', 'st_o': 'n_root_st', 'rst': 'rst',
        **{f'{p}{k}': f'n_s{k}_{p}' for k in range(4) for p in ('cmd', 'wd', 'rv', 'rd')}}),
    ('u_s0', 'vm_cp_slice3', 345.6, 540.0, 'R0', {'cmd': 'n_s0_cmd', 'wd': 'n_s0_wd', 'rv': 'n_s0_rv', 'rd': 'n_s0_rd', 'rst': 'rst'}),
    ('u_s2', 'vm_cp_slice3', 626.4, 540.0, 'R0', {'cmd': 'n_s2_cmd', 'wd': 'n_s2_wd', 'rv': 'n_s2_rv', 'rd': 'n_s2_rd', 'rst': 'rst'}),
    ('u_s1', 'vm_cp_slice3', 345.6, 1231.2, 'MX', {'cmd': 'n_s1_cmd', 'wd': 'n_s1_wd', 'rv': 'n_s1_rv', 'rd': 'n_s1_rd', 'rst': 'rst'}),
    ('u_s3', 'vm_cp_slice2', 626.4, 1231.2, 'MX', {'cmd': 'n_s3_cmd', 'wd': 'n_s3_wd', 'rv': 'n_s3_rv', 'rd': 'n_s3_rd', 'rst': 'rst'}),
]

def kit_geom(name):
    if name in LOGIC:
        g = LOGIC[name]; return g['w'], g['h']
    k = KITS[name]
    bits = sum(v[1] for v in k['ports'].values() if v[0] == 'out')
    return max(XWK.get(name, XW), snap(bits * BPU / (k["h"] * UTIL), 2.16)), k["h"]

def ports_of(name):
    return LOGIC[name]['ports'] if name in LOGIC else KITS[name]['ports']

def top_sv():
    nets = {}
    for inst, kn, *_r, conn in INST:
        for p, n in conn.items():
            if not n.startswith('n_'):
                continue
            nets.setdefault(n, ports_of(kn)[p][1])
    L = ['// GENERATED by make_vm_cp.py: [vm8cp] VM composition (logic tiles + channel relay tiles), monolithic hfd_vm ports.',
         '// Bench only: the die places these tiles (two-level hierarchy), no parent route.',
         'module hfd_vm_cp (input wire [0:0] ck, input wire [0:0] rst,',
         '    input wire [2047:0] f_su_SW, f_su_NW, f_su_SE, f_su_NE, input wire [511:0] iSW, iNW, iSE, iNE,',
         '    output wire [2047:0] t_su_SW, t_su_NW, t_su_SE, t_su_NE, output wire [581:0] qSW, qNW, qSE, qNE,',
         '    output wire [2067:0] xSW, xNW, xSE, xNE, output wire [1023:0] t_quant, output wire [511:0] t_router);']
    for n, w in sorted(nets.items()):
        L.append(f'    wire [{w-1}:0] {n};')
    L += ['`ifdef MUT_XBUS', "    wire [767:0] n_s2_wd_x = {n_s2_wd[767:12], n_s2_wd[10], n_s2_wd[11], n_s2_wd[9:0]};",
          '`else', '    wire [767:0] n_s2_wd_x = n_s2_wd;', '`endif',
          '`ifdef MUT_RELAY', "    wire [2062:0] n_re_se_x = {n_re_se[2062:12], n_re_se[10], n_re_se[11], n_re_se[9:0]};",
          '`else', '    wire [2062:0] n_re_se_x = n_re_se;', '`endif']
    for inst, kn, x, y, o, conn in INST:
        c = []
        for p, n in conn.items():
            if inst == 'u_s2' and p == 'wd': n = 'n_s2_wd_x'
            if inst == 'u_fe1' and p == 'tap': n = 'n_re_se_x'
            c.append(f'.{p}({n}{"[0]" if n in ("rst",) else ""})')
        L.append(f'    {kn} {inst} (.ck(ck[0]), ' + ', '.join(c) + ');')
    L.append('endmodule')
    return '\n'.join(L) + '\n'

# ------------------------------------------------------------------------------------------------- budget
CORNER = 2.0                            # face pins >= 2 um off every corner (r9 swet5 DRT-0255 corner-pin class)

def prange(kn, p, w, h):
    d, bw, f, *r = ports_of(kn)[p]
    L = h if f in 'WE' else w
    lo, hi = r[0] if r else (CORNER, L - CORNER)
    return f, max(lo, CORNER), min(hi, L - CORNER)

def oface(f, o):
    return ('S' if f == 'N' else 'N' if f == 'S' else f) if o == 'MX' else f

def budget():
    rows, hops, worst = [], [], 0.0
    pos = {}
    for inst, kn, x, y, o, conn in INST:
        w, h = kit_geom(kn)
        if x is None: x = round(VMW - w, 3)
        pos[inst] = (x, y, w, h, o)
    seen = set()
    for inst, kn, x, y, o, conn in INST:
        if kn in seen: continue
        seen.add(kn)
        X, Y, w, h, o = pos[inst]
        for f in 'NSEW':
            L = h if f in 'WE' else w
            nl = len(HV[f].split())
            bins = [0.0] * (int(L) + 1)
            tot = 0
            for p, v in ports_of(kn).items():
                ff, lo, hi = prange(kn, p, w, h)
                if ff != f: continue
                tot += v[1]
                for i in range(int(lo), max(int(lo) + 1, int(hi))):
                    bins[i] += v[1] / max(hi - lo, 1.0)
            if not tot: continue
            pk = max(sum(bins[i:i + 10]) / 10 for i in range(max(1, len(bins) - 9)))
            rows.append(dict(kit=kn, face=f, bits=tot, len_um=round(L, 1), peak_b_per_um_layer=round(pk / nl, 2),
                             layers=HV[f]))
            worst = max(worst, pk / nl)
    drv, rcv = {}, {}
    for inst, kn, x, y, o, conn in INST:
        X, Y, w, h, _ = pos[inst]
        for p, n in conn.items():
            d, bw = ports_of(kn)[p][:2]
            f, lo, hi = prange(kn, p, w, h)
            if o == 'MX' and f in 'NS':
                f = oface(f, o)
            m = (lo + hi) / 2
            c = {'W': (X, Y + m), 'E': (X + w, Y + m), 'S': (X + m, Y), 'N': (X + m, Y + h)}[f]
            (drv if d == 'out' else rcv).setdefault(n, []).append((inst, c, bw))
    for n in sorted(drv):
        for di, dc, bw in drv[n]:
            for ri, rc, _ in rcv.get(n, []):
                hops.append(dict(net=n, bits=bw, frm=di, to=ri, mid_um=round(abs(dc[0] - rc[0]) + abs(dc[1] - rc[1]), 1)))
    return pos, rows, hops, worst

def spec(kn, pos_inst):
    w, h = kit_geom(kn)
    ports = ports_of(kn)
    pins, ranges = {}, {}
    for p, (d, bw, f, *r) in ports.items():
        pins.setdefault(f, []).append(p)
        _f, lo, hi = prange(kn, p, w, h)
        ranges[p] = [round(lo, 3), round(hi, 3)]
    ckf = 'N' if kn.startswith('vm_cp_slice') else 'W'     # slices: all pins on the face toward the root (macro rows clear)
    pins.setdefault(ckf, []).insert(0, 'ck')
    L = w if ckf == 'N' else h
    ranges['ck'] = [round(L / 2 - 1, 3), round(L / 2 + 1, 3)]
    # gate (02:30): PPL places an ordered group on ONE layer, so two 1-2k buses sharing a face range (and ck in its middle)
    # failed PPL-0107/0093.  Pins now go through run_abi3_physical's balanced placer (place_pin, alternating M4/M6 or
    # M3/M5 per pin, uniform over the port's range), which needs DISJOINT per-port ranges on a face: overlapping ranges
    # are packed in order of their midpoints, each port getting a share proportional to its bits (ck 2 um), 1 um gaps.
    width = {p: ports[p][1] for p in ports}; width['ck'] = 0
    for f, plist in pins.items():
        Lf = w if f in 'NS' else h
        order = sorted(plist, key=lambda p: ((ranges[p][0] + ranges[p][1]) / 2, plist.index(p)))
        clusters = []
        for p in order:
            lo, hi = ranges[p]
            if clusters and lo < clusters[-1][2]:
                clusters[-1][0].append(p); clusters[-1][2] = max(clusters[-1][2], hi); clusters[-1][1] = min(clusters[-1][1], lo)
            else:
                clusters.append([[p], lo, hi])
        for ps, lo, hi in clusters:
            if len(ps) == 1:
                continue
            gaps = 1.0 * (len(ps) - 1); fixed = sum(2.0 for p in ps if p == 'ck')
            avail = hi - lo - gaps - fixed; tot = sum(width[p] for p in ps)
            x = lo
            for p in ps:
                span = 2.0 if p == 'ck' else avail * width[p] / tot
                ranges[p] = [round(x, 3), round(x + span, 3)]; x += span + 1.0
            for p in ps:
                assert ranges[p][1] <= Lf - CORNER + 1e-6 and ranges[p][0] >= CORNER - 1e-6, (kn, p, ranges[p])
    srcs = [f'physical/hbm_accel_die_views/vm/cp/rtl/{kn}.sv']
    s = {'name': kn, 'top': kn, 'kind': 'tile', 'sources': srcs, 'clock_port': 'ck', 'reset_ports': [],
         'outline': {'w': w, 'h': h}, 'pg_layer': 'M7', 'pins': pins, 'pin_ranges': ranges,
         'route': {'pd': 0.50, 'threads': 8, 'peak_ram_gb': 48, 'hold_margin_ns': 0.010, 'pin_v': 'M3 M5', 'pin_h': 'M4 M6',
                   'pin_balance': {'group_max': 1, 'h': 'M4 M6', 'v': 'M3 M5'}}}
    s['job'] = {'owner': 'Claude:el1011-hbm-vm8cp', 'branch': 'claude/el1011-hbm-vm8cp', 'tag': 'cp1',
                'purpose': f'[vm8cp] VM8 top-down re-plan tile {kn} (results/arch/hier_contract_1011/vm8_replan.md)',
                'extra_paths': ['physical/hbm_accel_die_views/vm', 'physical/hbm_accel_die_views/common', 'rtl/common',
                                'physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2'],
                'benches': [{'name': 'vm_cp_bench', 'cmd': 'bash physical/hbm_accel_die_views/vm/cp/run_vm_cp.sh {RUN}/bench/vmcp',
                             'expect': 'pass', 'threads': 16, 'peak_ram_gb': 32, 'needs': ['verilator'],
                             'min_count_regex': r'events=(\d+)/'},
                            {'name': 'vm_cp_bench_mut_xbus', 'cmd': 'VM_CP_MUT=XBUS bash physical/hbm_accel_die_views/vm/cp/run_vm_cp.sh {RUN}/bench/vmcp_mut',
                             'expect': 'fail', 'threads': 16, 'peak_ram_gb': 32, 'needs': ['verilator']}],
                'views_to': f'physical/ref_tile/{kn}/views', 'record_to': f'results/rtl/ref_tile/{kn}'}
    if kn in KITS:
        s['sources'].insert(0, 'rtl/common/ot_fwd_link_stage.sv')
        if any(sg[0] == 'fclk' for segs in KITS[kn]['outs'].values() for sg in segs):
            s['forwarded_clock'] = True
    if kn == 'vm_cp_root':
        s['sources'].append('physical/hbm_accel_die_views/vm/tiles/ot_hfd_vm_root_p.sv')
        s['reset_ports'] = ['rst']; s['route']['peak_ram_gb'] = 96
    if kn.startswith('vm_cp_slice'):
        nm = LOGIC[kn]['macros']
        s['sources'] += ['physical/hbm_accel_die_views/vm/tiles/ot_hfd_vm_slice.sv',
                         'physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2_bb.v']
        s['macros'] = [{'view': 'physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2', 'count': nm}]
        s['reset_ports'] = ['rst']
    return s

if __name__ == '__main__':
    RTL.mkdir(exist_ok=True); (D / 'specs').mkdir(exist_ok=True)
    for kn, k in KITS.items():
        (RTL / f'{kn}.sv').write_text(relay_sv(kn, k))
    (RTL / 'vm_cp_root.sv').write_text(root_sv())
    (RTL / 'vm_cp_slice3.sv').write_text(slice_sv(3)); (RTL / 'vm_cp_slice2.sv').write_text(slice_sv(2))
    (D / 'hfd_vm_cp.sv').write_text(top_sv())
    pos, rows, hops, worst = budget()
    for kn in list(KITS) + list(LOGIC):
        (D / 'specs' / f'{kn}.json').write_text(json.dumps(spec(kn, pos), indent=1) + '\n')
    ov = [(a, b) for a in pos for b in pos if a < b and pos[a][0] < pos[b][0] + pos[b][2] - 1e-6 and pos[b][0] < pos[a][0] + pos[a][2] - 1e-6 and pos[a][1] < pos[b][1] + pos[b][3] - 1e-6 and pos[b][1] < pos[a][1] + pos[a][3] - 1e-6]
    oob = [a for a in pos if pos[a][0] < 0 or pos[a][1] < 0 or pos[a][0] + pos[a][2] > VMW + 1e-6 or pos[a][1] + pos[a][3] > VMH + 1e-6]
    print('overlaps', ov, 'out of region', oob)
    over = [r for r in rows if r['peak_b_per_um_layer'] > 6.0]
    longh = [h for h in hops if h['mid_um'] > 500]
    json.dump(dict(region=[VMW, VMH], tiles={i: dict(zip(('x', 'y', 'w', 'h', 'orient'), v)) for i, v in pos.items()},
                   faces=rows, hops=hops, worst_b_per_um_layer=round(worst, 2), over_6=over, hops_over_500=longh),
              open(D / 'budget.json', 'w'), indent=1)
    print(f'kits {len(KITS) + len(LOGIC)}  instances {len(INST)}  worst face {worst:.2f} b/um/layer  faces>6: {len(over)}  '
          f'hops>500um (pin-range mid to mid): {len(longh)}')
    for r in sorted(rows, key=lambda r: -r['peak_b_per_um_layer'])[:6]:
        print('  face', r['kit'], r['face'], r['bits'], 'b /', r['len_um'], 'um peak', r['peak_b_per_um_layer'], 'b/um/layer')
    for h in sorted(hops, key=lambda h: -h['mid_um'])[:6]:
        print('  hop', h['net'], h['bits'], h['frm'], '->', h['to'], h['mid_um'], 'um')
