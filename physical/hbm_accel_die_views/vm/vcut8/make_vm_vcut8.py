#!/usr/bin/env python3
"""VM 8-way, VERTICAL CUT (vm8-seam, 2026-10-09): each r22 VM quadrant hfd_vm_<q> (699.816 x 1,000.056 um) is cut at
x = 349.056 into a west and an east half hfd_vm_<q>_w / hfd_vm_<q>_e (349.056 / 350.760 x 1,000.056 um, both origins on
the 1.728 um centre-ck lattice), joined by one registered seam pair w2e / e2w on the cut (sender pin oreg1 + receiver pin
register = +2 cycles per crossing, as every VM cross bus).  Replaces the y = 500 cut of ../split8 (make_vm_split8.py).

WHY (hbm_vm8 closure history, drive-0849 / hbm-forks 10-09): the y = 500 cut halves both LONG faces of a quadrant.
Every quadrant has one long face to the die (f_su / t_su / x / q / i: 7,258-7,770 b) and one long face to its E-W
neighbour quadrant (wr / row / ctl both ways: 9,552 b); the y cut put each of them into 376-470 um of ONE half
(15.5-21 pins/um on M4/M6) and made the other half carry them across the seam.  Measured: hbm_vm8_ses GRT-0116
congestion 6.2k markers ALL at x 675-700 um (the E die face, t_su_SE / xSE / qSE face stages); nen 85 markers at
x 0-25 (W cross face) after its 52k-buffer hold repair; sws 20k markers from the N seam funnel to the W die face; the
only closed half (ne_s, TT +14.06 / FF +1.14) and the near-miss (nw_s) are exactly the two halves with NO dense E/W
face.  Settings (LVT, HM 0/10/25, PD 0.45-0.55, bow, stagger) cannot change pins per um.
The vertical cut gives every long face its full 1,000 um (die faces 7.3-7.8 b/um, E-W cross faces 9.6 b/um), splits
the 700 um N-S cross face by run between the two halves (4,776 b on each 349-351 um part = 13.7 b/um, the density of
the closed ne_s S face), and lays the seam on a 1,000 um cut (4,096-8,435 b, <= 8.5 b/um).

Partition (O = outer half, die face side: sw_w, nw_w, se_e, ne_e; I = inner half, E-W cross side: sw_e, nw_e, se_w, ne_w):
  O: the die face chains (3 stages) + q face; SW also its 6-macro slice (balance: root + 2 cross faces stay in I).
  I: the E-W cross face, the root (SW) / the slice (NW, SE, NE), t_quant (NW, on its N edge as in the r22 tile).
  N-S cross runs: per edge, the runs whose far end is a slice / the root stay on I; the tap row to the x face and the
  write request from the die face go on O (and one dead ctl run each to balance: 4,776 b each side).
Cycles: every FUNCTIONAL VM path keeps its depth (bench mode 2 prints the per-path table vs the 4-tile; mode 3 keeps
the root write / read ports ONE depth): write port 7 / read port 7 / cfg 9 / tap rows xSW 5, xNW 7, xSE 7, xNE 9 /
slice command + return of every slice.  Placeholder pass-throughs of the monolithic wrapper (no VM function, kept
bit-exact) move: t_su_NE <- f_su_NW and t_su_NW <- f_su_NE +4 (die face -> I -> neighbour I -> die face),
t_quant <- f_su_NE +2, t_su_SE <- f_su_SW[2047:1230] -4, t_su_SE <- NW f_e_wr -2 (see the bench table).
Root: ot_hfd_vm_root_x SEATP=1 (safe-hbm S-D3) + FREG=1 (registered SECDED verdicts; make_root_x.py) -- the swn
seat -> fault -> sampled-enable path (-1,331..-1,536 ps TT) is not a seam problem but sits in the root half.
    python3 make_vm_vcut8.py   (writes hfd_vm_<q>_{w,e}.sv, hfd_vm_<q>_jv.sv, tb_vm_vcut8.sv, ports/<master>/*,
                                <master>_face_stages.tcl; prints the per-face pin density table)"""
import json, math, re, sys
from pathlib import Path
D = Path(__file__).resolve().parent
TD = D.parent / 'tiles'
sys.path.insert(0, str(TD))
import make_vm_tiles as mt          # noqa: E402
from make_vm_tiles import NF, W, R, C, TAPW, cat, slice_inst   # noqa: E402

QH = 1000.056                       # r22 quadrant tile height (both halves)
WW, WE = 349.056, 350.760           # west / east half widths: 202 x 1.728 and the rest of 699.816
WID = {'w': WW, 'e': WE}
OUTER = {'sw': 'w', 'nw': 'w', 'se': 'e', 'ne': 'e'}
INNER = {q: ('e' if o == 'w' else 'w') for q, o in OUTER.items()}

def qports(q):
    out = []
    for l in (D.parent / f'split_r19/hfd_vm_{q}/ports.svh').read_text().splitlines():
        m = re.match(r'\s*(input|output) wire \[(\d+):0\] (\w+),?', l)
        if m:
            out.append((m.group(1), int(m.group(2)) + 1, m.group(3)))
    return out

# ---------------------------------------------------------------- port -> half
DIE = {'sw': ['f_su_SW', 't_su_SW', 't_router', 'qSW', 'xSW', 'iSW'],          # die face runs, r22 order (bottom -> top)
       'nw': ['qNW', 'iNW', 'xNW', 'f_su_NW', 't_su_NW'],
       'se': ['f_su_SE', 't_su_SE', 'qSE', 'xSE', 'iSE'],
       'ne': ['iNE', 'qNE', 'xNE', 'f_su_NE', 't_su_NE']}
# N-S cross runs on the O part of the edge (the rest of the edge's runs are on I), named from the SOUTH quadrant
NS_O_SOUTH = ['t_n_row', 'f_n_wr', 't_n_ctl']
NS_PARTNER = {'t_n_row': 'f_s_row', 'f_n_wr': 't_s_wr', 't_n_ctl': 'f_s_ctl', 't_n_wr': 'f_s_wr', 'f_n_row': 't_s_row',
              'f_n_ctl': 't_s_ctl'}
NS_O = {'sw': set(NS_O_SOUTH), 'se': set(NS_O_SOUTH), 'nw': {NS_PARTNER[p] for p in NS_O_SOUTH},
        'ne': {NS_PARTNER[p] for p in NS_O_SOUTH}}

def half_of(q, p):
    if p in DIE[q]:
        return OUTER[q]
    if p == 't_quant':
        return INNER[q]
    if re.fullmatch(r'[ft]_[ns]_(wr|row|ctl)', p):
        return OUTER[q] if p in NS_O[q] else INNER[q]
    if re.fullmatch(r'[ft]_[ew]_(wr|row|ctl)', p):
        return INNER[q]
    raise KeyError((q, p))

SEAM = {'sw': (3034, 5401), 'nw': (2048, 2048), 'se': (3293, 1591), 'ne': (2866, 2048)}   # (w2e, e2w) widths

# ---------------------------------------------------------------- face clocks (coordinator 2026-10-09 ~20:10)
# redesign-hbm classified the VM8 hold endpoints: ~90% at the block edges; ONE in-block tree reaches the edge flops at
# ~380 ps and the deep flops at ~690 ps while the edge timing assumes 589 ps -> the clock plan, not the seam geometry (the
# 71b59c2c2 vcut routes confirmed it: all EARLY_FAIL_HOLD, -108..-278 ps at CTS).  Adopted the hbm-forks svc face-clock
# pattern (gen_svc_seg.py --fc, afaaf0d7f): every face of a half gets its own die clock leaf ck<f> (M7 area pin 4 um
# inside that face, mid-face), balanced by the DIE tree; the pin-stage register of every port (input pin register / the
# output pin register) runs on its face leaf; everything else on the centre ck.  Every crossing between a face root and
# the core root is launched from a NEGEDGE LOCKUP copy on the SOURCE root (redesign-hbm --xroot lockup, 470d0d3ba):
#   input :  p -> x<f> (posedge ck<f>) -> lockup (negedge ck<f>) -> core (posedge ck)
#   output:  core -> [stages on ck] -> lockup (negedge ck) -> pin register (posedge ck<f>)   (ot_hfd_oreg<n>x)
# Source -> lockup is root-local (T/2), lockup -> destination gets T/2 of hold margin.  Cycle-exact: 0 added cycles.
FC = True
FACES = 'wens'

def port_face(q, h, p):
    if p in ('w2e', 'e2w'):
        return 'e' if h == 'w' else 'w'
    if p in DIE[q]:
        return OUTER[q]
    if p == 't_quant':
        return 'n'
    if re.fullmatch(r'[ft]_[ns]_(wr|row|ctl)', p):
        return 'n' if q in ('sw', 'se') else 's'
    if re.fullmatch(r'[ft]_[ew]_(wr|row|ctl)', p):
        return INNER[q]
    raise KeyError((q, h, p))

def faces_of(q, h):
    fs = {port_face(q, h, n) for _, _, n in base_ports(q, h) if n not in ('ck', 'rst')}
    return [f for f in FACES if f in fs]

def base_ports(q, h):
    w2e, e2w = SEAM[q]
    ps = [('input', 1, 'ck'), ('input', 1, 'rst')]
    ps += [p for p in qports(q) if p[2] not in ('ck', 'rst') and half_of(q, p[2]) == h]
    ps += [('output', w2e, 'w2e'), ('input', e2w, 'e2w')] if h == 'w' else [('input', w2e, 'w2e'), ('output', e2w, 'e2w')]
    return ps

def half_ports(q, h):
    ps = base_ports(q, h)
    return ps[:1] + ([('input', 1, f'ck{f}') for f in faces_of(q, h)] if FC else []) + ps[1:]

class H(mt.T):
    def __init__(s, q, h):
        s.t, s.L, s.n = f'{q}_{h}', [], 0
        s.ports = half_ports(q, h)
        decl = ',\n'.join(f'    {d} wire [{w-1}:0] {n}' for d, w, n in s.ports)
        s.L.append(f'// GENERATED by vm/vcut8/make_vm_vcut8.py (see there): 8-way VM half (vertical cut) hfd_vm_{q}_{h}')
        s.L.append(f'module hfd_vm_{q}_{h} (\n{decl}\n);')
        s.L += ['    wire clk = ck[0];', '    reg [1:0] rst_s; always @(posedge clk) rst_s <= {rst_s[0], rst[0]};',
                '    wire rst_n = ~rst_s[1];']
        s.q, s.h = q, h
        if FC:
            for f in faces_of(q, h):
                s.L.append(f'    wire cf_{f} = ck{f}[0];   // face die clock leaf ({f.upper()} face)')
    def cf(s, p):
        return f'cf_{port_face(s.q, s.h, p)}' if FC else 'clk'
    def inp(s, p, w, n):           # die face input chain of n stages -> i_<p>; stage 0 on the face leaf + lockup
        if not FC:
            return mt.T.inp(s, p, w, n)
        c = s.cf(p)
        s.a(f'reg [{w-1}:0] i0_{p}; always @(posedge {c}) i0_{p} <= {p};')
        s.a(f'reg [{w-1}:0] il_{p}; always @(negedge {c}) il_{p} <= i0_{p};   // lockup (face root)')
        prev = f'il_{p}'
        for k in range(1, n - 1):
            s.a(f'reg [{w-1}:0] i{k}_{p}; always @(posedge clk) i{k}_{p} <= {prev};'); prev = f'i{k}_{p}'
        s.a(f'reg [{w-1}:0] i_{p}; always @(posedge clk) i_{p} <= {prev};')
    def out(s, p, w, n, expr, fclk=()):   # output through per-bit ot_hfd_oreg<n>x: lockup on ck, pin register on the face leaf
        if not FC:
            return mt.T.out(s, p, w, n, expr, fclk)
        c = s.cf(p)
        s.a(f'wire [{w-1}:0] od_{p} = {expr};'); s.a(f'wire [{w-1}:0] o_{p};')
        s.a(f'for (genvar k = 0; k < {w}; k = k + 1) begin : g_o_{p}')
        s.a(f'    ot_hfd_oreg{n}x u (.clk(clk), .clkf({c}), .d(od_{p}[k]), .q(o_{p}[k]));'); s.a('end')
        for k in range(w):
            if k in fclk:      # forwarded clocks leave on the same face leaf as their data
                s.n += 1; s.a(f'wire fclk_{s.n}; ot_fwd_clk_inv u_fclk_{s.n} (.a({c}), .y(fclk_{s.n})); assign {p}[{k}] = fclk_{s.n};')
        if fclk:
            s.a(f'for (genvar k = 0; k < {min(fclk)}; k = k + 1) begin : g_a_{p} assign {p}[k] = o_{p}[k]; end')
        else:
            s.a(f'assign {p} = o_{p};')
    def zero(s, *ps):
        for p in ps:
            w = dict((n, w) for _, w, n in s.ports)[p]
            s.a(f"assign {p} = {w}'d0;")
    def check(s):
        """every declared port is driven (outputs) / named (inputs, unused ones allowed)"""
        txt = '\n'.join(s.L)
        for d, w, n in s.ports:
            if d == 'output':
                assert re.search(rf'assign {n}( =|\[)|assign {n}\[k\] =', txt), (s.t, n)

def cross_in(s, p, w):     # cross / seam input: pin register on the face leaf + lockup -> x_<p> (read by the core on ck)
    if not FC:
        return mt.cross_in(s, p, w)
    c = s.cf(p)
    s.a(f'reg [{w-1}:0] xf_{p}; always @(posedge {c}) xf_{p} <= {p};')
    s.a(f'reg [{w-1}:0] x_{p}; always @(negedge {c}) x_{p} <= xf_{p};   // lockup (face root)')

def cross_out(s, p, w, expr): s.out(p, w, 1, expr)

# ---------------------------------------------------------------- SW (O = w: die face + slice; I = e: root + cross)
def sw_w():
    s = H('sw', 'w')
    s.inp('f_su_SW', 2048, NF); s.inp('iSW', 512, NF)
    for p, w in (('f_n_wr', W), ('e2w', 5401)): cross_in(s, p, w)
    s.a('// e2w: [2062:0] tap row, [4110:2063] t_su_SW payload, [4622:4111] t_router payload, [5400:4623] slice command')
    slice_inst(s, 'sw', 'x_e2w[4623]', 'x_e2w[4624]', 'x_e2w[4625]', 'x_e2w[4632:4626]', 'x_e2w[5400:4633]', 's0_v', 's0_d')
    s.a('// w2e: [2047:0] f_su_SW (write data + placeholders), [2264:2048] NW write request x_f_n_wr[216:0], [2265] slice v, [3033:2266] slice data')
    cross_out(s, 'w2e', 3034, '{s0_d, s0_v, x_f_n_wr[216:0], i_f_su_SW}')
    mt.x_face(s, 'SW', 'x_e2w[2062:0]'); mt.q_face(s, 'SW')
    s.out('t_su_SW', 2048, NF, 'x_e2w[4110:2063]')
    s.out('t_router', 512, NF, 'x_e2w[4622:4111]')
    cross_out(s, 't_n_row', R, cat([(0, TAPW, 'x_e2w[2062:0]')], R))   # tap -> NW x face (same seam bits as xSW)
    s.zero('t_n_ctl')
    return s

def sw_e():
    s = H('sw', 'e')
    for p, w in (('f_n_row', R), ('f_e_wr', W), ('f_e_row', R), ('w2e', 3034)): cross_in(s, p, w)
    s.a('wire [2047:0] fs = x_w2e[2047:0];   // f_su_SW after its face chain (west) + the seam (+2)')
    s.a('wire [216:0] wq = x_w2e[2264:2048];   // NW write request (f_n_wr[216:0]) after its pin register (west) + the seam (+2)')
    s.a('wire s0_v = x_w2e[2265]; wire [767:0] s0_d = x_w2e[3033:2266];   // SW slice return (west, over the seam)')
    s.a('reg [771:0] cfg; always @(posedge clk) cfg <= {cfg[770:0], x_f_e_wr[1791]};')
    s.a('// write port ONE depth (7): wr_v & co cross the SW seam (+2) after their NW face, wr_data[2047:0] the same seam (+2)')
    s.a('// after the SW face chain + the two r20 balance regs')
    s.a('reg [2047:0] wd0_f_su_SW, wd_f_su_SW; always @(posedge clk) begin wd0_f_su_SW <= fs; wd_f_su_SW <= wd0_f_su_SW; end')
    s.a('wire m_v, m_we, m_bank; wire [6:0] m_addr; wire [2815:0] m_wd; wire m_rd_v; wire [2815:0] m_rd;')
    s.a('wire wr_ready, wr_ACK_v, rd_ready, native_release, drained, fault; wire [3:0] tap_v; wire [191:0] wr_ACK_owner;')
    s.a('wire [767:0] tap_owner; wire [4*2063-1:0] tap_data;')
    s.a('ot_hfd_vm_root_x #(.ENABLE(1), .SEATP(1), .FREG(1)) u_mr (.clk(clk), .por_n(rst_n), .mem_cmd_v(m_v), .mem_cmd_we(m_we), '
        '.mem_cmd_bank(m_bank), .mem_cmd_addr(m_addr), .mem_wd(m_wd), .mem_rd_v(m_rd_v), .mem_rd(m_rd), '
        '.wr_v(wq[15]), .wr_ready(wr_ready), .wr_bank(wq[16]), .wr_addr(wq[23:17]), '
        '.wr_data({wq[14:0], wd_f_su_SW[2047:0]}), .wr_owner(wq[215:24]), .wr_ACK_v(wr_ACK_v), '
        '.wr_ACK_ready(wq[216]), .wr_ACK_owner(wr_ACK_owner), .rd_v(x_f_e_wr[0]), .rd_ready(rd_ready), '
        '.rd_bank(x_f_e_wr[1]), .rd_addr(x_f_e_wr[8:2]), .rd_owner(x_f_e_wr[200:9]), .tap_v(tap_v), .tap_ready(4\'d15), '
        '.tap_data(tap_data), .tap_owner(tap_owner), .tap_ACK_v(cfg[3:0]), .tap_ACK_owner(cfg[771:4]), '
        '.native_release(native_release), .drained(drained), .fault(fault));')
    s.a('reg c_v, c_we, c_bank; reg [6:0] c_addr; reg [767:0] c_wd;')
    s.a('always @(posedge clk) begin c_v <= m_v && rst_n; c_we <= m_we; c_bank <= m_bank; c_addr <= m_addr; c_wd <= m_wd[767:0]; end')
    s.a('reg [3:0] got; reg [2815:0] hold;')
    s.a('wire [3:0] arr = {x_f_e_row[769], x_f_e_row[0], x_f_n_row[0], s0_v};')
    s.a('wire [3:0] got_nx = got | arr;')
    s.a('assign m_rd_v = &got_nx;')
    s.a('assign m_rd = {arr[3] ? x_f_e_row[1281:770] : hold[2815:2304], arr[2] ? x_f_e_row[768:1] : hold[2303:1536], '
        'arr[1] ? x_f_n_row[768:1] : hold[1535:768], arr[0] ? s0_d : hold[767:0]};')
    s.a('always @(posedge clk or negedge rst_n) if (!rst_n) got <= 0; else got <= m_rd_v ? 4\'d0 : got_nx;')
    s.a('always @(posedge clk) hold <= m_rd;')
    cmd = mt.CMD('m')
    cross_out(s, 't_n_wr', W, cat(cmd + [(10, 768, 'm_wd[1535:768]'), (778, 818, 'fs[2047:1230]')], W))
    cross_out(s, 't_e_wr', W, cat(cmd + [(10, 768, 'm_wd[2303:1536]'), (778, 512, 'm_wd[2815:2304]'), (1290, 974, 'fs[973:0]')], W))
    cross_out(s, 't_e_ctl', C, 'fs[1229:974]')
    cross_out(s, 't_e_row', R, cat([(0, TAPW, 'tap_data[2062:0]')], R))
    tsu = ('{x_f_e_wr[1278:201], tap_owner[767:0], wr_ACK_owner[191:0], tap_v[3:0], fault, drained, native_release, rd_ready, '
           'wr_ACK_v, wr_ready}')
    cross_out(s, 'e2w', 5401, f'{{c_wd, c_addr, c_bank, c_we, c_v, x_f_e_wr[1790:1279], {tsu}, tap_data[2062:0]}}')
    return s

# ---------------------------------------------------------------- NW (O = w: die face; I = e: slice + cross + t_quant)
def nw_w():
    s = H('nw', 'w')
    s.inp('f_su_NW', 2048, NF); s.inp('iNW', 512, NF)
    for p, w in (('f_s_row', R), ('e2w', 2048)): cross_in(s, p, w)
    s.a('// e2w: [2047:0] x_f_e_row[2047:0] (NE -> NW row placeholder: t_su_NW)')
    cross_out(s, 't_s_wr', W, cat([(0, 217, 'i_f_su_NW[216:0]')], W))    # root write request (O run: local)
    mt.x_face(s, 'NW', 'x_f_s_row[2062:0]'); mt.q_face(s, 'NW')
    s.out('t_su_NW', 2048, NF, 'x_e2w[2047:0]')
    cross_out(s, 'w2e', 2048, 'i_f_su_NW')
    return s

def nw_e():
    s = H('nw', 'e')
    for p, w in (('f_s_wr', W), ('f_e_row', R), ('w2e', 2048)): cross_in(s, p, w)
    s.a('// w2e: [2047:0] f_su_NW after its face chain (west) + the seam: the t_e_row placeholder to NE')
    slice_inst(s, 'nw', 'x_f_s_wr[0]', 'x_f_s_wr[1]', 'x_f_s_wr[2]', 'x_f_s_wr[9:3]', 'x_f_s_wr[777:10]', 'sv', 'sd')
    cross_out(s, 't_s_row', R, cat([(0, 1, 'sv'), (1, 768, 'sd')], R))
    cross_out(s, 't_e_wr', W, cat([(0, 818, 'x_f_s_wr[1595:778]')], W))
    cross_out(s, 't_e_row', R, cat([(0, 2048, 'x_w2e[2047:0]')], R))
    s.zero('t_s_ctl', 't_e_ctl')
    s.out('t_quant', 1024, NF, 'x_f_e_row[1023:0]')
    cross_out(s, 'e2w', 2048, 'x_f_e_row[2047:0]')
    return s

# ---------------------------------------------------------------- SE (I = w: slice + cross; O = e: die face)
def se_w():
    s = H('se', 'w')
    for p, w in (('f_w_wr', W), ('f_w_row', R), ('f_w_ctl', C), ('f_n_row', R), ('e2w', 1591)): cross_in(s, p, w)
    s.a('// e2w: [1077:0] f_su_SE[1077:0] (read request [200:0] + placeholders), [1590:1078] NE write bus x_f_n_wr[512:0]')
    slice_inst(s, 'se', 'x_f_w_wr[0]', 'x_f_w_wr[1]', 'x_f_w_wr[2]', 'x_f_w_wr[9:3]', 'x_f_w_wr[777:10]', 'sv', 'sd')
    cross_out(s, 't_n_wr', W, cat([(0, 10, 'x_f_w_wr[9:0]'), (10, 512, 'x_f_w_wr[1289:778]')], W))
    cross_out(s, 't_w_wr', W, cat([(0, 201, 'x_e2w[200:0]'), (201, 1078, 'x_e2w[1077:0]'),
                                    (1279, 512, 'x_e2w[1589:1078]'), (1791, 1, 'x_e2w[1590]')], W))
    cross_out(s, 't_w_row', R, cat([(0, 1, 'sv'), (1, 768, 'sd'), (769, 1, 'x_f_n_row[0]'), (770, 512, 'x_f_n_row[512:1]')], R))
    s.zero('t_w_ctl')
    s.a('// w2e: [2062:0] tap row (SW -> SE x face and -> NE), [3036:2063] x_f_w_wr[2263:1290], [3292:3037] x_f_w_ctl')
    cross_out(s, 'w2e', 3293, '{x_f_w_ctl[255:0], x_f_w_wr[2263:1290], x_f_w_row[2062:0]}')
    return s

def se_e():
    s = H('se', 'e')
    s.inp('f_su_SE', 2048, NF); s.inp('iSE', 512, NF)
    for p, w in (('f_n_wr', W), ('w2e', 3293)): cross_in(s, p, w)
    mt.x_face(s, 'SE', 'x_w2e[2062:0]'); mt.q_face(s, 'SE')
    s.out('t_su_SE', 2048, NF, '{x_f_n_wr[1330:513], x_w2e[3292:3037], x_w2e[3036:2063]}')
    cross_out(s, 't_n_row', R, cat([(0, TAPW, 'x_w2e[2062:0]')], R))    # tap -> NE x face (same seam bits as xSE)
    s.zero('t_n_ctl')
    cross_out(s, 'e2w', 1591, '{x_f_n_wr[512:0], i_f_su_SE[1077:0]}')
    return s

# ---------------------------------------------------------------- NE (I = w: slice + cross; O = e: die face)
def ne_w():
    s = H('ne', 'w')
    for p, w in (('f_s_wr', W), ('f_w_wr', W), ('f_w_row', R), ('e2w', 2048)): cross_in(s, p, w)
    s.a('// e2w: [2047:0] f_su_NE after its face chain (east) + the seam: the t_w_row placeholder to NW')
    slice_inst(s, 'ne', 'x_f_s_wr[0]', 'x_f_s_wr[1]', 'x_f_s_wr[2]', 'x_f_s_wr[9:3]', 'x_f_s_wr[521:10]', 'sv', 'sd')
    cross_out(s, 't_s_row', R, cat([(0, 1, 'sv'), (1, 512, 'sd')], R))
    cross_out(s, 't_w_row', R, cat([(0, 2048, 'x_e2w[2047:0]')], R))
    s.zero('t_s_ctl', 't_w_ctl', 't_w_wr')
    s.a('// w2e: [817:0] x_f_w_wr[817:0] (NW wr placeholder -> t_s_wr), [2865:818] x_f_w_row[2047:0] (-> t_su_NE)')
    cross_out(s, 'w2e', 2866, '{x_f_w_row[2047:0], x_f_w_wr[817:0]}')
    return s

def ne_e():
    s = H('ne', 'e')
    s.inp('f_su_NE', 2048, NF); s.inp('iNE', 512, NF)
    for p, w in (('f_s_row', R), ('w2e', 2866)): cross_in(s, p, w)
    mt.x_face(s, 'NE', 'x_f_s_row[2062:0]'); mt.q_face(s, 'NE')
    s.out('t_su_NE', 2048, NF, 'x_w2e[2865:818]')
    cross_out(s, 't_s_wr', W, cat([(0, 512, 'i_f_su_NE[1535:1024]'), (512, 1, 'i_f_su_NE[0]'), (513, 818, 'x_w2e[817:0]')], W))
    cross_out(s, 'e2w', 2048, 'i_f_su_NE')
    return s

HALVES = (sw_w, sw_e, nw_w, nw_e, se_w, se_e, ne_w, ne_e)

def join(q):
    w2e, e2w = SEAM[q]
    decl = ',\n'.join(f'    {d} wire [{w-1}:0] {n}' for d, w, n in qports(q))
    if q == 'se':   # MUT_SEAM: two seam tap bits swapped (xSE and the NE tap row go wrong)
        mut = ('`ifdef MUT_SEAM\n    wire [%d:0] w2e_x = {w2e[%d:12], w2e[10], w2e[11], w2e[9:0]};   // seam tap bits 10/11 swapped\n'
               '`else\n    wire [%d:0] w2e_x = w2e;\n`endif\n') % (w2e - 1, w2e - 1, w2e - 1)
    else:
        mut = f'    wire [{w2e-1}:0] w2e_x = w2e;\n'
    return (f'// GENERATED by vm/vcut8/make_vm_vcut8.py: hfd_vm_{q} as its two vertical-cut halves (bench join; quadrant ports)\n'
            f'module hfd_vm_{q}_jv (\n{decl}\n);\n    wire [{w2e-1}:0] w2e; wire [{e2w-1}:0] e2w;\n{mut}'
            f'    hfd_vm_{q}_w u_w (.*{fcc(q, "w")});\n    hfd_vm_{q}_e u_e (.*, .w2e(w2e_x){fcc(q, "e")});\nendmodule\n')

def fcc(q, h):     # bench join: the face leaves are the same die clock
    return ''.join(f', .ck{f}(ck)' for f in faces_of(q, h)) if FC else ''

def tb():
    t = (TD / 'tb_vm_tiles.sv').read_text()
    t = t.replace('// r19 VM quadrant tiles joined vs the monolithic hfd_vm',
                  '// GENERATED by vm/vcut8/make_vm_vcut8.py from tiles/tb_vm_tiles.sv: `VCUT8 = the 8 vertical-cut halves (via\n'
                  '// hfd_vm_<q>_jv) joined; MUT_SEAM (vcut8 only) swaps two SE seam tap bits.  Original header:\n'
                  '// r19 VM quadrant tiles joined vs the monolithic hfd_vm')
    for q in ('sw', 'nw', 'se', 'ne'):
        t = t.replace(f'    hfd_vm_{q} u_{q} (', f'    `VMQ({q}) u_{q} (')
    t = t.replace('module vm_joined', '`ifdef VCUT8\n`define VMQ(q) hfd_vm_``q``_jv\n`define SWH .u_e\n`else\n`define VMQ(q) hfd_vm_``q\n'
                  '`define SWH\n`endif\nmodule vm_joined', 1)
    t = t.replace('`define VM_CFG u.u_sw.cfg', '`define VM_CFG u.u_sw`SWH.cfg')
    t = t.replace('`define VM_ROOT u.u_sw.u_mr.on', '`define VM_ROOT u.u_sw`SWH.u_mr.on')
    t = t.replace('`define VM_RT u.u_sw.u_mr', '`define VM_RT u.u_sw`SWH.u_mr')
    assert t.count('`VMQ(') == 4 and 'u.u_sw`SWH.u_mr' in t
    return t

# ---------------------------------------------------------------- pins
# Layers: E/W faces even bits M4 / odd bits M6 (horizontal), N/S faces M5 / M7 (vertical), widths on the WIDTHTABLE.
# PDN (vm/pdn_vm.tcl): M5 straps 0.12 @ 0.300 / 0.492 (+5.4 k), M6 straps 0.288 @ 0.600 / 1.176 (+5.4 k), M7 stripes 0.288 @
# 1.0 / 6.4 (+10.8 k), all relative to the half's own origin: a pin track within 0.1 um of a strap is skipped.  Faces
# that abut (E-W cross, N-S cross, seam) are laid by ONE function call per edge, so both partners get identical
# coordinates (the halves of an edge share the edge's origin: same y for E-W edges and the seam, same x for N-S edges).
TRK = {'M4': (0.012, 0.048), 'M5': (0.012, 0.048), 'M6': (0.016, 0.064), 'M7': (0.016, 0.064)}
SZ = {'M4': '0.1920 0.0240', 'M6': '0.1920 0.0320', 'M5': '0.0240 0.1920', 'M7': '0.0320 0.1920'}
STRAP = {'M5': (5.4, [(0.300, 0.420), (0.492, 0.612)]), 'M6': (5.4, [(0.600, 0.888), (1.176, 1.464)]),
         'M7': (10.8, [(1.000, 1.288), (6.400, 6.688)])}
PAIR_PITCHES = (0.512, 0.448, 0.384, 0.320, 0.288, 0.256, 0.224, 0.192, 0.160, 0.144, 0.128, 0.112, 0.096)

def free(ly, a):
    if ly not in STRAP:
        return True
    per, bands = STRAP[ly]
    hw = (0.016 if ly in ('M6', 'M7') else 0.012) + 0.10
    r = a % per
    return all(not (lo - hw <= r <= hi + hw) and not (lo - hw <= r + per <= hi + hw) and not (lo - hw <= r - per <= hi + hw)
               for lo, hi in bands)

def lay(runs, L1, L2, lo, hi):
    """runs: [(port, bits)] in order along the face; returns ({port: [coord of bit b]}, {port: layer list}, pitch, span)"""
    n = sum(b for _, b in runs)
    gap = 4 * TRK[L2][1]                                   # between runs
    for P in PAIR_PITCHES:
        need = sum(-(-b // 2) * P for _, b in runs) + gap * (len(runs) - 1)
        if need <= hi - lo:
            break
    else:
        raise AssertionError(('face runs do not fit on two layers', runs, hi - lo))
    a0 = lo + (hi - lo - need) / 2
    last = {L1: -1.0, L2: -1.0}
    pos, lys = {}, {}
    for p, b in runs:
        pos[p], lys[p] = [], []
        for i in range(b):
            ly = L1 if i % 2 == 0 else L2
            off, pt = TRK[ly]
            want = max(a0 + (i // 2) * P, last[ly] + pt)
            x = off + math.ceil((want - off) / pt - 1e-9) * pt
            while not free(ly, x):
                x += pt
            assert x <= hi + 1e-6, (p, i, x, hi)
            x = round(x, 4)
            last[ly] = x
            pos[p].append(x); lys[p].append(ly)
        a0 += -(-b // 2) * P + gap
    return pos, lys, P, round(need, 2), n

def plan():
    """{master: [(port, bit, layer, x, y, size)]} for all 8 halves + the density table"""
    pins = {f'hfd_vm_{q}_{h}': [] for q in OUTER for h in 'we'}
    dens = []
    def put(master, face, pos, lys, ren=lambda p: p):
        w = WID[master[-1]]
        for p, xs in pos.items():
            for b, a in enumerate(xs):
                ly = lys[p][b]
                if face in 'EW':
                    x, y = (w - 0.096 if face == 'E' else 0.096), a
                else:
                    x, y = a, (QH - 0.096 if face == 'N' else 0.096)
                pins[master].append((ren(p), b, ly, round(x, 4), round(y, 4), SZ[ly]))
    def note(master, face, runs, P, need, n, span):
        dens.append((master, face, n, round(span, 1), round(n / span, 2), P, need))
    widths = {q: {n: w for _, w, n in qports(q)} for q in OUTER}
    # die faces (outer long face)
    for q in OUTER:
        m = f'hfd_vm_{q}_{OUTER[q]}'
        runs = [(p, widths[q][p]) for p in DIE[q]]
        lo, hi = 3.0, QH - 3.0
        pos, lys, P, need, n = lay(runs, 'M4', 'M6', lo, hi)
        put(m, 'W' if OUTER[q] == 'w' else 'E', pos, lys); note(m, 'W' if OUTER[q] == 'w' else 'E', runs, P, need, n, hi - lo)
    # E-W cross edges: (west quadrant, east quadrant); runs named from the west quadrant (t_e_* / f_e_*)
    for qa, qb in (('sw', 'se'), ('nw', 'ne')):
        runs = [(p, widths[qa][p]) for p in ('t_e_wr', 't_e_row', 't_e_ctl', 'f_e_wr', 'f_e_row', 'f_e_ctl')]
        lo, hi = 3.0, QH - 3.0
        pos, lys, P, need, n = lay(runs, 'M4', 'M6', lo, hi)
        ma, mb = f'hfd_vm_{qa}_e', f'hfd_vm_{qb}_w'
        put(ma, 'E', pos, lys); put(mb, 'W', pos, lys, lambda p: p.replace('_e_', '_w_').replace('t_w', 'X').replace('f_w', 't_w').replace('X', 'f_w'))
        note(ma, 'E', runs, P, need, n, hi - lo); note(mb, 'W', runs, P, need, n, hi - lo)
    # N-S cross edges: (south quadrant, north quadrant), split into the west-half part and the east-half part
    for qs, qn in (('sw', 'nw'), ('se', 'ne')):
        for h in 'we':
            ro = (h == OUTER[qs])
            names = [p for p in ('t_n_row', 'f_n_wr', 't_n_ctl', 't_n_wr', 'f_n_row', 'f_n_ctl') if (p in NS_O_SOUTH) == ro]
            runs = [(p, widths[qs][p]) for p in names]
            lo, hi = 3.0, WID[h] - 3.0
            pos, lys, P, need, n = lay(runs, 'M5', 'M7', lo, hi)
            ms, mn = f'hfd_vm_{qs}_{h}', f'hfd_vm_{qn}_{h}'
            put(ms, 'N', pos, lys); put(mn, 'S', pos, lys, lambda p: NS_PARTNER[p])
            note(ms, 'N', runs, P, need, n, hi - lo); note(mn, 'S', runs, P, need, n, hi - lo)
    # seam (west half E face / east half W face)
    for q in OUTER:
        w2e, e2w = SEAM[q]
        runs = [('w2e', w2e), ('e2w', e2w)]
        lo, hi = 3.0, QH - 3.0
        pos, lys, P, need, n = lay(runs, 'M4', 'M6', lo, hi)
        put(f'hfd_vm_{q}_w', 'E', pos, lys); put(f'hfd_vm_{q}_e', 'W', pos, lys)
        note(f'hfd_vm_{q}_w/e', 'seam', runs, P, need, n, hi - lo)
    # t_quant (nw_e, N edge: north quadrant's outer edge)
    pos, lys, P, need, n = lay([('t_quant', 1024)], 'M5', 'M7', 20.0, WE - 20.0)
    put('hfd_vm_nw_e', 'N', pos, lys); note('hfd_vm_nw_e', 'N', [('t_quant', 1024)], P, need, n, WE - 40.0)
    # ck (centre, M7 track, one wire wide) and rst (outer short edge, near the corner away from the runs)
    for q in OUTER:
        for h in 'we':
            m = f'hfd_vm_{q}_{h}'
            w = WID[h]
            xc = 0.016 + round((w / 2 - 0.016) / 0.064) * 0.064
            pins[m].append(('ck', 0, 'M7', round(xc, 4), round(QH / 2, 4), '0.0320 0.2880'))
            ys = 0.096 if q in ('sw', 'se') else QH - 0.096          # outer short edge (VM slot edge)
            xr = 0.012 + round(((10.0 if h == 'e' else w - 10.0) - 0.012) / 0.048) * 0.048
            while not free('M5', xr):
                xr += 0.048
            pins[m].append(('rst', 0, 'M5', round(xr, 4), ys, SZ['M5']))
    # face clock leaves (FC): M7 area pin 4 um inside its face, mid-face (off the centre ck column), on a free M7 track
    if FC:
        for q in OUTER:
            for h in 'we':
                m = f'hfd_vm_{q}_{h}'
                w = WID[h]
                for f in faces_of(q, h):
                    if f in 'we':
                        xt, y = (4.0 if f == 'w' else w - 4.0), round(QH / 2 + 30.0, 4)
                    else:
                        xt, y = w / 2 + 30.0, (4.0 if f == 's' else round(QH - 4.0, 4))
                    x = 0.016 + round((xt - 0.016) / 0.064) * 0.064
                    while not free('M7', x):
                        x += 0.064 if f != 'e' else -0.064
                    pins[m].append((f'ck{f}', 0, 'M7', round(x, 4), y, '0.0320 0.2880'))
    # sanity: every half port has all its bits, no two pins of one layer on one spot, all inside the outline
    for m, ps in pins.items():
        q, h = m.split('_')[2], m.split('_')[3]
        seen, got = set(), {}
        for p, b, ly, x, y, _ in ps:
            assert 0.0 <= x <= WID[h] and 0.0 <= y <= QH, (m, p, b, x, y)
            k = (ly, round(x, 3), round(y, 3))
            assert k not in seen, ('pin clash', m, p, b, k)
            seen.add(k); got[p] = got.get(p, 0) + 1
        want = {n: w for _, w, n in half_ports(q, h)}
        assert got == want, (m, {k: (got.get(k), want.get(k)) for k in set(got) | set(want) if got.get(k) != want.get(k)})
    return pins, dens

def write_ports(m, pins):
    q, h = m.split('_')[2], m.split('_')[3]
    od = D / 'ports' / m; od.mkdir(parents=True, exist_ok=True)
    ps = sorted(pins, key=lambda t: (t[0], t[1]))
    (od / 'io_place.tcl').write_text(f'# {m}: 8-way VM half pins, vertical cut (vm/vcut8/make_vm_vcut8.py)\n' +
        ''.join(f'place_pin -pin_name {{{p}[{b}]}} -layer {ly} -location {{{x:.4f} {y:.4f}}} -pin_size {{{sz}}}\n'
                for p, b, ly, x, y, sz in ps))
    ports = {}
    for d, w, n in half_ports(q, h):
        pp = [t for t in ps if t[0] == n]
        xs, ys = [t[3] for t in pp], [t[4] for t in pp]
        ports[n] = {'bits': w, 'direction': d, 'layer': pp[0][2], 'layers': sorted({t[2] for t in pp}),
                    'x': [min(xs), max(xs)], 'y': [min(ys), max(ys)]}
    (od / 'ports.json').write_text(json.dumps({'master': m, 'kind': 'vm8v', 'w_um': WID[h], 'h_um': QH, 'obs_top': 7,
        'parent': f'hfd_vm_{q}', 'half': h, 'side': 'outer' if OUTER[q] == h else 'inner',
        'generator': 'physical/hbm_accel_die_views/vm/vcut8/make_vm_vcut8.py', 'ports': ports}, indent=1) + '\n')

if __name__ == '__main__':
    for f in HALVES:
        s = f(); s.check(); (D / f'hfd_vm_{s.t}.sv').write_text(s.text())
        (D / f'hfd_vm_{s.t}_face_stages.tcl').write_text('# generated by make_vm_vcut8.py: die port -> face chain depth\n' +
            ''.join(f'set fc_ps({n}) {(NF if n.startswith(("f_su", "t_su", "i", "q", "x", "t_router", "t_quant")) else 1) + (1 if FC else 0)}\n'
                    for _, _, n in s.ports if n not in ('ck', 'rst') and not re.fullmatch(r'ck[wens]', n)))
    for q in OUTER:
        (D / f'hfd_vm_{q}_jv.sv').write_text(join(q))
    (D / 'tb_vm_vcut8.sv').write_text(tb())
    pins, dens = plan()
    for m, ps in pins.items():
        write_ports(m, ps)
    # macro placement (hbm_vm8v_sww 71b59c2c2 FLOORPLAN_MARGIN: auto placement left a 7.49 um macro gap holding rows): the
    # slice's 2 banks x NM macros (94.824 x 41.04) as two columns 14.04 um apart, rows 14.04 um apart, R0, on the site
    # (0.054) / row (0.27, core y0 0.54) grid; centred in x, low in y (clear of the centre ck pin and the face lockups).
    for m, nm in (('hfd_vm_sw_w', 3), ('hfd_vm_nw_e', 3), ('hfd_vm_se_w', 3), ('hfd_vm_ne_w', 2)):
        w = WID[m[-1]]
        x0 = round(round((w / 2 - (2 * 94.824 + 14.04) / 2) / 0.054) * 0.054, 3)
        L = [f'# {m}: slice macros (make_vm_vcut8.py)']
        for b in range(2):
            for k in range(nm):
                y = round(0.54 + round((200.0 + k * 55.08) / 0.27) * 0.27, 3)
                L.append(f'place_macro -macro_name {{u_slice.banks\\[{b}\\].macros\\[{k}\\].u_sram}} -location {{{round(x0 + b * 108.864, 3)} {y}}} -orientation R0')
        (D / f'{m}_macro_place.tcl').write_text('\n'.join(L) + '\n')
    rows = [dict(master=a, face=f, bits=n, span_um=sp, bits_per_um=d, pair_pitch_um=P, used_um=nd) for a, f, n, sp, d, P, nd in dens]
    (D / 'pin_density.json').write_text(json.dumps(rows, indent=1) + '\n')
    for r in rows:
        print(f"{r['master']:16s} {r['face']:5s} {r['bits']:6d} b / {r['span_um']:7.1f} um = {r['bits_per_um']:5.2f} b/um  pair {r['pair_pitch_um']}")
    print('ok')
