#!/usr/bin/env python3
"""S81 die lead r6 (2026-10-14 PM): top-down subslots + ASSIGNED pin files for the masters five streams wait on
(owner 10-13 18:22: the die tools assign the pins of new / unclosed masters; closed views stand and their routed pins are
ADOPTED as the assignment, never re-pinned without a die window).

  v19_pins_1014.py engram OUT_DIR   Engram own-state leaves of dsfd_engram_c_hl (request el1011-s81die.log 08:04, B2)
  v19_pins_1014.py markov OUT_DIR   Markov K256 cluster (39 closed leaves, request 06:49, romB)
  v19_pins_1014.py gather OUT_DIR   gather v4 'direct' (request 11:36, gather r2)
  v19_pins_1014.py rwb    OUT_DIR   PQ RWB x12 (request 12:13 / 12:55, B3)

Every file: schema opentallas.s81.assigned_pins.v1 (as tools/s81/hc_ntree_pins.py): ports -> per_bit [face, layer,
centre along the face from its W / S end (um, master frame), depth]; plus OUT_DIR/layout.json (subslots in the parent
frame, hop table pin-to-pin, decisions).  Positions come from the neighbour each face meets (the closed child views'
LEF pins), N/S pins M5, W/E pins M4 (layer cap M5), >= 0.096 um between pins of one face and layer.
"""
from __future__ import annotations
import json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
P = 0.096
REACH = 500.0


def lef_bits(path):
    """{port: {bit: (face, layer, x, y)}} in the master frame + size."""
    t = (ROOT / path).read_text()
    w, h = map(float, re.search(r'SIZE ([\d.]+) BY ([\d.]+)', t).groups())
    d = {}
    for mm in re.finditer(r'PIN (\S+)\n(.*?)END \1', t, re.S):
        if 'USE POWER' in mm[2] or 'USE GROUND' in mm[2]:
            continue
        r = re.search(r'LAYER (\S+) ;\s+RECT\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)', mm[2])
        if not r:
            continue
        x0, y0, x1, y1 = map(float, r.groups()[1:])
        face = 'S' if y0 < 0.3 else 'N' if y1 > h - 0.3 else 'W' if x0 < 0.3 else 'E' if x1 > w - 0.3 else 'I'
        nm = re.match(r'(.*?)(?:\[(\d+)\])?$', mm[1].replace('\\', ''))
        d.setdefault(nm[1], {})[int(nm[2] or 0)] = (face, r[1], round((x0 + x1) / 2, 4), round((y0 + y1) / 2, 4))
    return (w, h), d


def run(face, start, bits, layer=None, pitch=P):
    ly = layer or ('M5' if face in 'NS' else 'M4')
    return [[face, ly, round(start + i * pitch, 3), 0.192] for i in range(bits)]


def at(face, coords, layer=None):
    ly = layer or ('M5' if face in 'NS' else 'M4')
    return [[face, ly, round(c, 3), 0.192] for c in coords]


def resolve(ports, outline):
    """nudge pins of one face+layer apart to >= P (keeps order), stays inside the face."""
    occ = {}
    for p, v in ports.items():
        for i, b in enumerate(v):
            occ.setdefault((b[0], b[1]), []).append([b[2], p, i])
    moved = 0
    for (face, ly), lst in occ.items():
        lst.sort()
        L = outline[0] if face in 'NS' else outline[1]
        for k in range(1, len(lst)):
            if lst[k][0] - lst[k - 1][0] < P - 1e-6:
                lst[k][0] = round(lst[k - 1][0] + P, 3)
                moved += 1
        assert lst[-1][0] < L - 0.2, (face, ly, lst[-1], L)
        for c, p, i in lst:
            ports[p][i][2] = round(c, 3)
    return moved


def write(out, master, outline, ports, clock, rule, case, extra=None):
    nudged = resolve(ports, outline)
    for p, v in ports.items():
        for b in v:
            L = outline[0] if b[0] in 'NS' else outline[1]
            assert 0.2 <= b[2] <= L - 0.2, (master, p, b, L)
    occ = sorted((b[0], b[1], b[2], p) for p, v in ports.items() for b in v)
    for a, b in zip(occ, occ[1:]):
        assert not (a[0] == b[0] and a[1] == b[1] and b[2] - a[2] < 0.0955), (master, a, b)
    rec = dict(schema='opentallas.s81.assigned_pins.v1', master=master, case=case, outline_um=outline,
               clock_entries={'stream': [clock]}, source=f'tools/s81/v19_pins_1014.py (die lead r6, top-down)', rule=rule,
               nudged_to_pitch=nudged, ports={p: dict(bits=len(v), uniform=False, per_bit=v) for p, v in ports.items()})
    if extra:
        rec.update(extra)
    fn = out / f'{master}.json'
    fn.write_text(json.dumps(rec, indent=1) + '\n')
    W, H = outline
    lines = [f'# {master}: die-assigned pins ({case}, tools/s81/v19_pins_1014.py); 1-bit ports written as scalars']
    for p, v in ports.items():
        for i, (f, ly, c, _) in enumerate(v):
            x, y = {'N': (c, H - 0.042), 'S': (c, 0.042), 'W': (0.042, c), 'E': (W - 0.042, c)}[f]
            nm = p if len(v) == 1 else f'{p}[{i}]'
            lines.append(f'place_pin -pin_name {{{nm}}} -layer {ly} -location {{{x:.3f} {y:.3f}}} -force_to_die_boundary')
    fn.with_suffix('.tcl').write_text('\n'.join(lines) + '\n')
    return fn


def manh(a, b):
    return round(abs(a[0] - b[0]) + abs(a[1] - b[1]), 1)


# ------------------------------------------------------------------------------------------------------------ Engram
def engram(out):
    V = 'physical/s81_engc_tiles/rso_views/'
    _, io = lef_bits(V + 'ot_engc_t_io_rso_r1/ot_engc_t_io_rso_r1.lef')
    _, pbc = lef_bits(V + 'ot_engc_t_pbc_rso/ot_engc_t_pbc_rso.lef')
    _, pbb = lef_bits(V + 'ot_engc_t_pbb_rso_xt/ot_engc_t_pbb_rso_xt.lef')
    _, win = lef_bits(V + 'ot_engc_t_win_rso/ot_engc_t_win_rso.lef')
    _, ws = lef_bits(V + 'ot_engc_t_ws_rso/ot_engc_t_ws_rso.lef')
    _, sink = lef_bits('physical/s81_ph_views/closed/dsfd_engram_sink/dsfd_engram_sink.lef')
    _, lkp = lef_bits('physical/s81_ph_views/closed/dsfd_engram_lkp/dsfd_engram_lkp.lef')
    # child origins: physical/s81_engc_tiles/compose/macro_place.tcl (parent 1188 x 432, all R0)
    ORG = dict(sink=(38.016, 274.32), lkp=(410.4, 142.56), win=(404.784, 371.52), io=(735.264, 384.48),
               ws=(2.592, 138.24), pb1=(2.592, 2.16), pb0=(750.384, 2.16), pb2=(974.16, 2.16))
    VIEWS = dict(io=io, pb0=pbc, pb2=pbc, pb1=pbb, win=win, ws=ws, sink=sink, lkp=lkp)

    def pin(child, port, bit=0):
        f, ly, x, y = VIEWS[child][port][bit]
        return (ORG[child][0] + x, ORG[child][1] + y)

    case = 'v19_engram_hl'
    files, sub, hops = [], {}, []
    # rr0: rd0 return relay in the pb0 | io seam (y 371.52 .. 384.48): abuts io (q straight into io.rd0), a 4.32-um
    # routing channel above pb0 carries the <= 3.9-um jogs pb0.r_d -> rr0.d (the bank SRAM output is captured 4.3 um
    # from its pin); x >= 777.6 keeps io.r0_a / r0_oh -> pb0 (x 759 .. 776.7) straight beside it.
    X0, Y0, W_, H_ = 777.6, 375.84, 165.888, 8.64
    rr0 = dict(d=at('S', [max(0.3, pin('pb0', 'r_d', i)[0] - X0) for i in range(256)]),
               q=at('N', [pin('io', 'rd0', i)[0] - X0 for i in range(256)]),
               ck=at('W', [4.032]), rst_n=at('W', [4.608]))
    resolve(rr0, [W_, H_])
    files.append(write(out, 'ot_engc_rr256', [W_, H_], rr0, 'ck', 'die lead r6: u_rr0 in the pb0|io seam, abutting io; '
                       'd at the pb0.r_d x (S, 4.32-um jog channel below), q at the io.rd0 x (N, abutted)', case))
    sub['u_rr0 ot_engc_rr256'] = [X0, Y0, W_, H_]
    hops += [('pb0.r_d -> rr0.d (SRAM out, capture at pin)', round(Y0 - 371.52 + 3.9, 1)), ('rr0.q -> io.rd0 (abutted)', 0.0)]
    # rr2: rd2 64-bit relay, same form, 43.2 wide (the requested width) under io.rd2
    X2 = 997.92
    rr2 = dict(d=at('S', [pin('pb2', 'r_d', i)[0] - X2 for i in range(64)]),
               q=at('N', [pin('io', 'rd2', i)[0] - X2 for i in range(64)]),
               ck=at('W', [4.032]), rst=at('W', [4.608]))
    files.append(write(out, 'ot_engc_rr64', [43.2, 8.64], rr2, 'ck', 'die lead r6: u_rr2 in the pb2|io seam abutting io; '
                       'port rst = the async die reset, conditioned INSIDE the leaf (2-flop sync on ck): the ctl -> rr2 '
                       'reset hop would be 533-607 um > 500', case))
    sub['u_rr2 ot_engc_rr64'] = [X2, Y0, 43.2, 8.64]
    hops += [('pb2.r_d -> rr2.d', round(Y0 - 371.52 + 1.2, 1)), ('rr2.q -> io.rd2 (abutted)', 0.0)]
    # column between pb1 (E face x 693.792) and pb0 (W face x 750.384): W channel 17.712 um (pb1.x_d 320 + w_a/w_oh 14 +
    # r_a/r_oh 14 from ws / to io run vertically there: 348 b / 646 M5+M7 tracks = 0.54), ctl_x y 2.16..90.72, rr1 above.
    CX, CW = 711.504, 36.288
    # rr1 (NEW master ot_engc_rr256w: same RTL body as ot_engc_rr256, W-face d): d at the pb1.r_d y (W, straight across
    # the W channel), q on N toward the x 734.4..750.4 column to io.rd1 (~290 um); ck/rst_n on E.
    RX, RY, RW, RH = CX, 90.72, 30.24, 32.4
    rr1 = dict(d=at('W', [pin('pb1', 'r_d', i)[1] - RY for i in range(256)]),
               q=run('N', 2.016, 256), ck=at('E', [16.032]), rst_n=at('E', [16.608]))
    files.append(write(out, 'ot_engc_rr256w', [RW, RH], rr1, 'ck', 'die lead r6: NEW master name for u_rr1 (same body as '
                       'ot_engc_rr256; one master cannot hold both faces): d W at pb1.r_d y, q N (E end) toward the '
                       'lkp|pb0 column', case))
    sub['u_rr1 ot_engc_rr256w'] = [RX, RY, RW, RH]
    hops += [('pb1.r_d -> rr1.d (straight, W channel)', round(RX - 693.792, 1)),
             ('rr1.q -> io.rd1 (N, jog E, column x 734.4..750.4 north, over pb0 corner)', round((384.48 - RY - RH) + 20 + 15, 1))]
    # ctl split: ONE ctl leaf cannot reach its endpoints (x pipe pb1 -> pb0 at x ~700 / status pipe sink -> win at x ~400 /
    # 8 reset pins over the whole 1188 x 432 cluster: sink 980 um from the x-pipe site). Split into two leaves:
    #   ot_engc_ctl_x (column): x transit pipe 334 b, conditioners io / pb1 / pb0 / pb2, partial ACK ack_x
    #   ot_engc_ctl_s (top band W of win): status pipe 16 b, release pipe 4 b, conditioners win / ws / lkp / sink, final rso
    #   ack_x reaches ctl_s through ONE closed dsfd_rly_1_EW (rs = die reset) between ws and lkp (+1 cycle on the ACK).
    XH = 88.56
    xd_in = [pbb['x_do'][i][3] for i in range(320)]
    ctlx = dict(x_d=at('W', xd_in), x_oh=at('W', [pbb['x_oh'][i][3] for i in range(6)]),
                x_a=at('W', [pbb['x_a'][i][3] for i in range(8)]),
                x_d_q=at('E', [pbc['w_d'][i][3] for i in range(256)] + [pbc['x_d'][i][3] for i in range(64)]),
                x_oh_q=at('E', [pbc['w_oh'][i][3] for i in range(6)]), x_a_q=at('E', [pbc['w_a'][i][3] for i in range(8)]),
                ck=at('S', [12.0]), rst=at('S', [12.096]), ack_x=at('S', [2.016]), rst_pb1_n=at('S', [2.112]),
                child_rso_x=at('S', [2.208, 2.304, 33.024, 33.12]),          # {pb2, pb0, pb1, io}: pb1 W end, pb0/pb2/io E end
                states_x=run('S', 16.032, 4),
                rst_io_n=at('S', [33.216]), rst_pb0_n=at('S', [33.312]), rst_pb2_n=at('S', [33.408]))
    # child_rso_x bit order {io, pb1, pb0, pb2} = [0..3]
    ctlx['child_rso_x'] = at('S', [33.024, 2.208, 33.12, 33.504])
    moved = resolve(ctlx, [CW, XH])
    files.append(write(out, 'ot_engc_ctl_x', [CW, XH], ctlx, 'ck', f'die lead r6: ctl split (x part); W x_* at the pb1.x_do / '
                       f'x_oh / x_a y, E x_*_q at the pb0.w_d|x_d / w_oh / w_a y (2.592-um via gap to pb0), control on S '
                       f'({moved} pins nudged to the 0.096 pitch)', case,
                       dict(proposed_rtl='module ot_engc_ctl_x (input ck, rst, input [5:0] x_oh, input [7:0] x_a, input [319:0] x_d, '
                                         'output [5:0] x_oh_q, output [7:0] x_a_q, output [319:0] x_d_q, output rst_io_n, rst_pb1_n, '
                                         'rst_pb0_n, rst_pb2_n, input [3:0] child_rso_x /*{pb2,pb0,pb1,io}*/, output [3:0] states_x, '
                                         'output ack_x /*registered &{child_rso_x, states_x}*/)')))
    sub['u_ctl_x ot_engc_ctl_x'] = [CX, 2.16, CW, XH]
    SX, SY, SW, SH = 354.24, 410.4, 43.2, 17.28
    wy = lambda p, i: pin('win', p, i)[1] - SY
    ctls = dict(s_rdy_q=at('E', [wy('s_rdy', i) for i in range(8)]), s_perr_q=at('E', [wy('s_perr', i) for i in range(8)]),
                vrel=at('E', [wy('vrel_o', i) for i in range(4)]), rst_win_n=at('E', [15.84]), child_rso_s=at('E', [15.936, 2.016]),
                s_rdy=run('W', 2.016, 8), s_perr=run('W', 2.016 + 8 * P, 8), rst_sink_n=at('W', [14.016]),
                rst_ws_n=at('S', [36.0]), rst_lkp_n=at('S', [41.04]), vrel_q=run('S', 41.136, 4), ack_x_i=at('S', [35.904]),
                ck=at('N', [20.016]), rst=at('N', [20.112]), rso=at('N', [24.0]), states_s=run('N', 26.016, 4))
    ctls['child_rso_s'] = [['E', 'M4', 15.936, 0.192], ['S', 'M5', 35.808, 0.192]]   # {ws, win}: [0]=win E, [1]=ws S
    ctls['child_rso_s'] = [['E', 'M4', 15.936, 0.192], ['S', 'M5', 35.808, 0.192]]
    moved = resolve(ctls, [SW, SH])
    files.append(write(out, 'ot_engc_ctl_s', [SW, SH], ctls, 'ck', 'die lead r6: ctl split (status part) in the top band '
                       'above sink, W of win: E pins at the win W-face y (7.3-um straight hops), W toward sink, S down the '
                       'ws|lkp column', case,
                       dict(proposed_rtl='module ot_engc_ctl_s (input ck, rst, output rst_win_n, rst_ws_n, rst_lkp_n, rst_sink_n, '
                                         'input [1:0] child_rso_s /*{ws,win}*/, output [3:0] states_s /*{sink,lkp,ws,win}*/, '
                                         'input ack_x_i, output rso /*registered &{child_rso_s, states_s, ack_x_i}*/, '
                                         'input [7:0] s_rdy, s_perr, output [7:0] s_rdy_q, s_perr_q, input [3:0] vrel, output [3:0] vrel_q)')))
    sub['u_ctl_s ot_engc_ctl_s'] = [SX, SY, SW, SH]
    sub['u_rly_ack dsfd_rly_1_EW (CLOSED s81_rly_1_ew view, rs = parent rst)'] = [393.984, 144.72, 15.12, 15.12]
    cx_s = lambda port, k=0: (CX + ctlx[port][k][2], 2.16) if ctlx[port][k][0] == 'S' else None
    cs_ = lambda port, k=0: {'E': (SX + SW, SY + ctls[port][k][2]), 'W': (SX, SY + ctls[port][k][2]),
                             'S': (SX + ctls[port][k][2], SY), 'N': (SX + ctls[port][k][2], SY + SH)}[ctls[port][k][0]]
    # pin-to-pin hop estimates (Manhattan along the open channels named; parent wiring, no tile crossing)
    hops += [
        ('pb1.x_do -> ctl_x.x_d (W channel, straight)', round(CX - 693.792, 1)),
        ('ctl_x.x_d_q -> pb0.w_d/x_d (2.592 gap)', round(750.384 - CX - CW, 1)),
        ('ctl_x.rst_pb1_n -> pb1.rst (W channel N, band W)', round(manh(cx_s('rst_pb1_n'), pin('pb1', 'rst')) + 2 * 17.7, 1)),
        ('ctl_x.rst_pb0_n -> pb0.rst (E gap N)', manh(cx_s('rst_pb0_n'), pin('pb0', 'rst'))),
        ('ctl_x.rst_pb2_n -> pb2.rst (under pb0, pb0|pb2 seam N)', round((974.16 - CX - 33.408) + 182.65, 1)),
        ('ctl_x.rst_io_n -> io.rst (E gap, column N)', round(manh(cx_s('rst_io_n'), pin('io', 'rst')) + 10, 1)),
        ('ctl_x.rst_io_n -> rr0.rst_n / rr1.rst_n', round(manh(cx_s('rst_io_n'), (X0, Y0 + 4.6)) + 10, 1)),
        ('io.rso -> ctl_x.child_rso_x[0] (column S)', round(manh(pin('io', 'rso'), cx_s('child_rso_x', 0)) + 10, 1)),
        ('pb2.rso -> ctl_x.child_rso_x[3] (seam, under pb0)', round((974.16 - CX - 33.5) + 187.2, 1)),
        ('pb1.rso -> ctl_x.child_rso_x[1]', round(manh(pin('pb1', 'rso'), cx_s('child_rso_x', 1)) + 2 * 17.7, 1)),
        ('ctl_x.ack_x -> rly_ack.i (W channel N, band W, ws|lkp column N)', round((CX + 2.0 - 409.1) + (152.28 - 2.16) + 20, 1)),
        ('rly_ack.o -> ctl_s.ack_x_i (column N, sink|lkp column)', round((SY - 152.28) + abs(393.98 - (SX + 35.9)) + 12, 1)),
        ('sink.rdy/perr -> ctl_s.s_rdy/s_perr (N along sink W, band E)', round(manh(pin('sink', 'perr', 7), cs_('s_perr', 7)) + 4, 1)),
        ('ctl_s.s_rdy_q -> win.s_rdy (straight)', round(404.784 - SX - SW, 1)),
        ('win.vrel_o -> ctl_s.vrel (straight)', round(404.784 - SX - SW, 1)),
        ('ctl_s.vrel_q -> lkp.rel (sink|lkp column, lkp|win seam)', round(manh(cs_('vrel_q', 0), pin('lkp', 'rel', 0)) + 20, 1)),
        ('ctl_s.rst_win_n -> win.rst (band above win)', round(manh(cs_('rst_win_n'), pin('win', 'rst')) + 13, 1)),
        ('win.rso -> ctl_s.child_rso_s[0]', round(manh(pin('win', 'rso'), cs_('child_rso_s', 0)) + 13, 1)),
        ('ctl_s.rst_ws_n -> ws.rst (ws|lkp column S)', round(manh(cs_('rst_ws_n'), pin('ws', 'rst')) + 10, 1)),
        ('ws.rso -> ctl_s.child_rso_s[1]', round(manh(pin('ws', 'rso'), cs_('child_rso_s', 1)) + 10, 1)),
        ('ctl_s.rst_lkp_n -> lkp.rst_n', round(manh(cs_('rst_lkp_n'), pin('lkp', 'rst_n')) + 10, 1)),
        ('ctl_s.rst_sink_n -> sink.rst_n (band W, sink W face S)', round(manh(cs_('rst_sink_n'), pin('sink', 'rst_n')) + 8, 1)),
    ]
    worst = max(h for _, h in hops)
    assert worst <= REACH, hops
    layout = dict(schema='opentallas.s81.subslots.v1', parent='dsfd_engram_c_hl (slot eng_SE 1188 x 432, unchanged)', case=case,
                  owner='S81 die lead r6', request='el1011-s81die.log 2026-10-14 08:04 (B2 s81-romB2, claude/s81-romB2-enghl)',
                  children_from='physical/s81_engc_tiles/compose/macro_place.tcl (unchanged)', subslots=sub,
                  decisions=['rr0 / rr2 sit in the bank|io seams abutting io (the bank SRAM output is captured 4.3 um from its '
                             'pin); the requested 43.2 x 17.28 does not fit the 12.96 seam: rr256 = 165.888 x 8.64, rr64 = 43.2 x 8.64',
                             'u_rr1 needs its own master ot_engc_rr256w (W-face d at pb1.r_d): one master cannot carry both forms',
                             'rr64 conditions the die reset itself (port rst): ctl -> rr2 reset >= 533 um',
                             'ot_engc_ctl_leaf SPLIT into ot_engc_ctl_x + ot_engc_ctl_s (+1 closed dsfd_rly_1_EW on the ACK, +1 '
                             'cycle of startup ACK latency, no data-path cycle): a single leaf has endpoints up to 980 um apart',
                             'the old provisional faces of the s81engc_* kits are void; re-gate on these files'],
                  hops_um=dict(hops), worst_hop_um=worst, reach_um=REACH,
                  pin_files=[str(f.relative_to(ROOT)) for f in files])
    (out / 'layout.json').write_text(json.dumps(layout, indent=1) + '\n')
    print('engram', len(files), 'files; worst hop', worst)


def adopt(out, master, lef, case, why, extra=None):
    """closed view: its routed pins ARE the assignment (no re-pin)."""
    (w, h), d = lef_bits(lef)
    ports = {p: [[b[0], b[1], b[2] if b[0] in 'NS' else b[3], 0.192] for _, b in sorted(v.items())] for p, v in d.items()}
    rec = dict(schema='opentallas.s81.assigned_pins.v1', master=master, case=case, outline_um=[w, h], adopted_closed_view=lef,
               source='tools/s81/v19_pins_1014.py (die lead r6): CLOSED view pins adopted as the assignment (closed tiles stand)',
               rule=why, ports={p: dict(bits=len(v), uniform=False, per_bit=v) for p, v in ports.items()})
    if extra:
        rec.update(extra)
    fn = out / f'{master}.json'
    fn.write_text(json.dumps(rec, indent=1) + '\n')
    return fn, (w, h), d


# ------------------------------------------------------------------------------------------------------------ Markov
def markov(out):
    case = 'v19_markov_k256'
    M = {}
    files = []
    names = ['mul', 'ctl', 'pair', 'fold', 'join'] + [f'chunk{k}' for k in range(8)]
    for n in names:
        top = f'ot_s81_markov_{n}_native'
        lef = f'physical/ref_tile/s81_markov_{n}_native/views/{top}/{top}.lef'
        ins = json.loads((ROOT / f'physical/ref_tile/s81_markov_{n}_native/views/{top}/insertion.json').read_text())
        fn, wh, d = adopt(out, top, lef, case, 'Markov K256 leaf, CLOSED: pins stand; placed by the cluster layout.json',
                          dict(phi_R_ps=dict(tt=ins['tt']['boundary']['mean'], ff=ins.get('ff', {}).get('boundary', {}).get('mean'))))
        files.append(fn)
        M[n] = dict(wh=wh, pins=d, R=ins['tt']['boundary']['mean'])
    # ring layout around a CENTRAL ctl (every leaf within ~400 um Manhattan of the ctl pins): rows bottom -> top
    #   R0 chain 0 (c0s0..c0s7 left -> right) | R1 mul 0..7 | R2 ctl (centre) | R3 mul 8..15 | R4 tree pair, fold0..3, join
    #   | R5 chain 1; a CH-um channel column above ctl (x = ctl span) brings the 544 external input bits from the N face
    #   down the ctl W side to its S face (rows R3..R5 leave that column free).
    PITCH, G, CH = 51.84, 4.32, 30.24
    place = {}
    xs = [G + k * PITCH for k in range(8)]
    Wc = 8 * PITCH - 8.64 + 2 * G + CH + 8.64
    xctl = round(((Wc - 73.44) / 2) // 0.432 * 0.432, 3)
    # columns of R3..R5 skip the channel [xctl - 8.64, xctl + 73.44 + 8.64]: 4 leaves W of it, 4 E of it
    xs_split = [G + k * PITCH for k in range(4)] + [Wc - G - 43.2 - (3 - k) * PITCH for k in range(4)]
    y0 = G
    place.update({f'u_c0s{k}': (f'chunk{k}', xs_split[k], y0) for k in range(8)})
    y1 = y0 + 116.64 + 10.8
    for lane in range(8):
        place[f'g_mul[{lane}].u_mul'] = ('mul', xs_split[lane], y1)
    y2 = y1 + 34.56 + 10.8
    place['u_ctl'] = ('ctl', xctl, y2)
    y3 = y2 + 34.56 + 10.8
    for lane in range(8, 16):
        place[f'g_mul[{lane}].u_mul'] = ('mul', xs_split[lane - 8], y3)
    y4 = y3 + 34.56 + 10.8
    tx = [xs_split[k] for k in (7, 6, 5, 4, 3, 2)]   # pair under the chain ends (E), join toward the ctl
    place['u_pair'] = ('pair', tx[0], y4)
    for k in range(4):
        place[f'g_tree[{k}].u_fold'] = ('fold', tx[1 + k], y4)
    place['u_join'] = ('join', tx[5], y4)
    y5 = y4 + 34.56 + 10.8
    place.update({f'u_c1s{k}': (f'chunk{k}', xs_split[k], y5) for k in range(8)})
    Hc = round(-(-(y5 + 116.64 + G) // 2.16) * 2.16, 2)

    def PP(inst, port, bit=0):
        m, x, y = place[inst]
        f, ly, px, py = M[m]['pins'][port][bit]
        return (x + px, y + py)
    hops = []
    for lane in range(16):
        hops.append((f'ctl.mul_weight -> mul{lane}.a', manh(PP('u_ctl', 'mul_weight', 16 * lane), PP(f'g_mul[{lane}].u_mul', 'a'))))
        hops.append((f'ctl.mul_embed -> mul{lane}.b', manh(PP('u_ctl', 'mul_embed', 16 * lane + 15), PP(f'g_mul[{lane}].u_mul', 'b', 15))))
        c, k = divmod(lane, 8)
        hops.append((f'mul{lane}.y -> c{c}s{k}.p', manh(PP(f'g_mul[{lane}].u_mul', 'y', 31), PP(f'u_c{c}s{k}', 'p', 31))))
        hops.append((f'mul{lane}.fault -> ctl.pf', manh(PP(f'g_mul[{lane}].u_mul', 'fault'), PP('u_ctl', 'pf', lane))))
    for c in range(2):
        hops.append((f'ctl.pv_last -> c{c}s0.vin', manh(PP('u_ctl', 'pv_last'), PP(f'u_c{c}s0', 'vin'))))
        for k in range(7):
            hops.append((f'c{c}s{k}.y -> c{c}s{k+1}.sum', manh(PP(f'u_c{c}s{k}', 'y', 0), PP(f'u_c{c}s{k+1}', 'sum', 0))))
        for k in range(8):
            hops.append((f'c{c}s{k}.bad -> ctl.bad_chunk', manh(PP(f'u_c{c}s{k}', 'bad'), PP('u_ctl', 'bad_chunk', 8 * c + k))))
    hops.append(('c0s7.y -> pair.a', manh(PP('u_c0s7', 'y', 0), PP('u_pair', 'a', 0))))
    hops.append(('c1s7.y -> pair.b', manh(PP('u_c1s7', 'y', 0), PP('u_pair', 'b', 0))))
    hops.append(('pair.y -> fold0.x', manh(PP('u_pair', 'y', 0), PP('g_tree[0].u_fold', 'x', 0))))
    for k in range(3):
        hops.append((f'fold{k}.y -> fold{k+1}.x', manh(PP(f'g_tree[{k}].u_fold', 'y', 0), PP(f'g_tree[{k+1}].u_fold', 'x', 0))))
    hops.append(('fold3.y -> join.x', manh(PP('g_tree[3].u_fold', 'y', 0), PP('u_join', 'x', 0))))
    hops.append(('ctl.head -> join.head', manh(PP('u_ctl', 'head', 0), PP('u_join', 'head', 0))))
    hops.append(('join.y -> ctl.jd (S face, wraps the ctl E side)', round(manh(PP('u_join', 'y', 31), PP('u_ctl', 'jd', 31)) + 2 * 34.56, 1)))
    hops.append(('pair/fold/join.bad -> ctl.bad_tree', manh(PP('u_join', 'vout'), PP('u_ctl', 'bad_tree', 4))))
    worst = max(h for _, h in hops)
    assert worst <= REACH, sorted(hops, key=lambda x: -x[1])[:5]
    # cluster (die master ot_s81_markov_k256_native) pins: external data straight below the ctl S pins (MTP head side = S),
    # outputs (ctl N face) brought down the ctl W side to the S face, 39 clock entries + rst_n on W at their leaf rows.
    cx, cy = place['u_ctl'][1], place['u_ctl'][2]
    cp = M['ctl']['pins']
    ports = {}
    # all external ports on N inside the free channel column between the 4+4 leaf columns of R3..R5 (x 203.04 .. 250.56),
    # M5 / M7 alternating (0.096 a layer): inputs first (down the channel, around the ctl W side to its S face), then
    # outputs (ctl N face straight up)
    chx0 = xs_split[3] + 43.2 + 2.0
    seq = [(prt, i) for prt in ('head_logit', 'weight_bf16', 'embed_bf16', 'in_valid', 'start', 'out_ready')
           for i in range(len(cp[prt]))] + \
          [(prt, i) for prt in ('out_bits', 'out_valid', 'start_ready', 'in_ready', 'fault') for i in range(len(cp[prt]))]
    for k, (prt, i) in enumerate(seq):
        ports.setdefault(prt, []).append(['N', 'M5' if k % 2 == 0 else 'M7', round(chx0 + k * 0.048, 3), 0.192])
    assert ports['fault'][-1][2] < xs_split[4] - 2.0, (ports['fault'][-1], xs_split[4])
    ports['clk'] = at('W', [cy + 14.9]); ports['rst_n'] = at('W', [cy + 15.0])
    ck = []
    order = [f'g_mul[{l}].u_mul' for l in range(16)] + [f'u_c0s{k}' for k in range(8)] + [f'u_c1s{k}' for k in range(8)] + \
            ['u_pair'] + [f'g_tree[{k}].u_fold' for k in range(4)] + ['u_join']
    for i, inst in enumerate(order):
        ck.append(place[inst][2] + 14.892 + (i % 8) * 0.096 + (0.0 if inst.startswith('g_mul') else 0.0))
    ck.sort()
    ports['clk_leaf'] = at('W', ck)
    outline = [round(Wc, 3), Hc]
    files.append(write(out, 'ot_s81_markov_k256_native', outline, ports, 'clk',
                       'die lead r6: Markov cluster die pins: external data/control on N (toward the MTP sequencer) over the '
                       'channel column above the central ctl; 38 clk_leaf entries (phi - R_leaf at each pin) + clk / rst_n on W', case,
                       dict(clock_entries={'clk': 'u_ctl', 'clk_leaf[i]': 'RTL order: mul0..15, c0s0..7, c1s0..7, pair, fold0..3, join'})))
    layout = dict(schema='opentallas.s81.subslots.v1', parent='ot_s81_markov_k256_native (wires only)', case=case,
                  owner='S81 die lead r6', request='el1011-s81die.log 2026-10-14 06:49 (s81-romB, Markov K256)',
                  outline_um=outline, area_mm2=round(outline[0] * outline[1] / 1e6, 4), orientation='all leaves R0',
                  subslots={k: [v[0], round(v[1], 3), round(v[2], 3)] + list(M[v[0]]['wh']) for k, v in place.items()},
                  die_slot=dict(die='head die (DIE_KIND head; MTP_SEQ centre column)', where='centre column directly S of the '
                                'mtp sequencer slab, cluster N face toward it; on stage dies no slot (no Markov)',
                                generator='--markov-slot (v19 GEN: inserted after mtp in centre[], area = outline)'),
                  phi_R_tt_ps={k: M[v[0]]['R'] for k, v in place.items()},
                  hops_um=dict(hops), worst_hop_um=worst, reach_um=REACH, pin_files=[str(f.relative_to(ROOT)) for f in files])
    (out / 'layout.json').write_text(json.dumps(layout, indent=1) + '\n')
    print('markov', len(files), 'files; outline', outline, 'worst hop', worst)


if __name__ == '__main__':
    what, out = sys.argv[1], Path(sys.argv[2])
    out = out if out.is_absolute() else ROOT / out
    out.mkdir(parents=True, exist_ok=True)
    globals()[what](out)
