#!/usr/bin/env python3
"""CLAUDE HBM-ABSTRACTS (hub): thin registered die wrappers for the HBM DS die hub quarters (hfd_su, hfd_sfu, hfd_hc,
tools/hbm_accel_die_fp.py r16g) around CLOSED lane elements used as hard macros.

Structure (one generator for the three quarters, parameters in QUARTERS):
  * every die input port is registered once at the boundary (din_q), every die output leaves a register (dout_q);
  * the lanes stand in C2 column PAIRS; the two columns of a pair face one routing channel (left column MY, right
    column R0, lane pins on the channel edge).  Each pair is split into two HALVES (south / north of the die-port band)
    and each half into G GROUPS of L lanes per column (a group spans <= 504 um: one wire stage);
  * BROADCAST: one register chain per (pair, half) carries the lanes' broadcast word (every lane input except the
    per-lane fields) + reset from the boundary outward, one (* keep *) register bank per group (the 2 x L lanes of the
    group read it);  per-lane input fields are a lane-indexed rotation of the group's broadcast bank;
  * RESULTS: one XOR-accumulate chain per (pair, half) carries that chain's share of the die output word inward, one
    (* keep *) register bank per group; each lane output bit is XOR-merged into one slot (the cost of the OR of a
    gather bus, but every lane output bit stays observable at the die output: an OR of ~57 bits per slot saturated
    the SU envelope's outputs to all ones and its negative control could not fail);
  * the chains' heads meet at the die-port band; dout = the heads' accumulators.
  * MARGIN (owner rule 2026-10-06, every macro output staged up front): each lane's outputs are captured in a (* keep *)
    register (lq_<j>) before the result chain's XOR, so no lane clock-to-Q path reaches combinational logic; the lanes'
    inputs are driven straight from the group bank, a register in the channel the lane pins face.

This is a PHYSICAL ENVELOPE of the quarter: real closed lanes, real register boundary, real wire stages and wiring
volume.  It is NOT the SU / SFU / HC function: the SU controller (CTL12) and the die-port protocol of these blocks are
not built, so the die ports' bits map onto lane pins by the fixed rule above.  Views built from it are recorded
interim-not-closed.

    python3 tools/hbm_hub_quarter_gen.py --quarter su --ports DIR/hfd_su/ports.json --out physical/hbm_accel_die_views/su/rtl
"""
from __future__ import annotations

import argparse
import json
import math
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))

SU_PHYS = 'rtl/hdc/v41x/phys/ot_hdc_v41x_su_c12_phys.sv'
HC_RTL = 'rtl/hdc/v41x/ot_dsrom_su_hcpost.sv'
QUARTERS = {
    # master, lane module, lane source, params, per-lane fields, C2 pairs, G groups / half, L lanes / column / group,
    # lane macro (w, h), channel width, spine (east) width
    'su': dict(master='hfd_su', lane='ot_su12_light', src=SU_PHYS, params={}, per_lane=['vi_q', 'rd_q', 'side_y'],
               C2=3, G=8, L=2, PIPE=5),
    'sfu': dict(master='hfd_sfu', lane='ot_su12_sfu', src=SU_PHYS, params={}, per_lane=['vi_q', 'rd_q', 'side_y'],
                C2=1, G=8, L=1, PIPE=1),
    'hc': dict(master='hfd_hc', lane='ot_dsrom_su_hcpost_lane', src=HC_RTL, params={'ML': 5, 'AL': 5},
               per_lane=['r0', 'r1', 'r2', 'r3', 'y'], C2=1, G=11, L=2, PIPE=1),
}


def lane_ports(q):
    import die_top_lint as L
    p = L.parse_module(str(ROOT / q['src']), q['lane'], q['params'] or None)['ports']
    ins = [(n, w) for n, (d, w) in p.items() if d == 'input' and n not in ('clk', 'rst_n')]
    outs = [(n, w) for n, (d, w) in p.items() if d == 'output']
    return ins, outs


class Plan:
    """The mapping, shared by the RTL emitter and the reference model."""

    def __init__(self, q, ports):
        self.q = q
        self.din = [(p, v['bits']) for p, v in sorted(ports['ports'].items())
                    if v['direction'] == 'input' and p not in ('ck', 'rst')]
        self.dout = [(p, v['bits']) for p, v in sorted(ports['ports'].items()) if v['direction'] == 'output']
        assert all(v['direction'] in ('input', 'output') for v in ports['ports'].values())
        self.WI = sum(w for _, w in self.din)
        self.WO = sum(w for _, w in self.dout)
        self.ins, self.outs = lane_ports(q)
        self.bc = [(n, w) for n, w in self.ins if n not in q['per_lane']]
        self.pl = [(n, w) for n, w in self.ins if n in q['per_lane']]
        self.LB = sum(w for _, w in self.bc)
        self.LP = sum(w for _, w in self.pl)
        self.LO = sum(w for _, w in self.outs)
        self.C2, self.G, self.L = q['C2'], q['G'], q['L']
        self.K = self.C2 * 2                 # chains: (pair, half)
        self.N = self.K * self.G * 2 * self.L
        self.WC = -(-self.WO // self.K)      # accumulator width of one chain
        self.PIPE = q.get('PIPE', 0)         # extra (* keep *) wire stages on every die input and output (port band
        #                                      -> chain heads up to ~2.7 mm: a stage per <= 504 um)

    def lanes(self):
        """(lane index j, chain k, group g, side s (0 left col / 1 right col), slot i)."""
        j = 0
        for k in range(self.K):
            for g in range(self.G):
                for s in range(2):
                    for i in range(self.L):
                        yield j, k, g, s, i
                        j += 1

    # ---- reference model (steady state, constant die inputs)
    def lane_inputs(self, din_bits, j):
        bcw = [0] * self.LB
        for u in range(self.WI):                 # bsrc[t] = XOR of din_q[t + m * LB]: every die input bit is used
            bcw[u % self.LB] ^= din_bits[u]
        plw = [bcw[(j * self.LP + t) % self.LB] for t in range(self.LP)]
        vec, bi, pi = {}, 0, 0
        for n, w in self.ins:
            if n in self.q['per_lane']:
                vec[n] = plw[pi:pi + w]
                pi += w
            else:
                vec[n] = bcw[bi:bi + w]
                bi += w
        flat = []
        for n, w in self.ins:
            flat += vec[n]
        return flat

    def stub_out(self, lin):
        LI = len(lin)
        return [lin[(t * 13 + 5) % LI] ^ lin[(t * 7 + 1) % LI] for t in range(self.LO)]

    def slot(self, j, t):
        return (j * self.LO + t) % self.WC

    def model(self, din_bits):
        acc = [[0] * self.WC for _ in range(self.K)]
        for j, k, g, s, i in self.lanes():
            lo = self.stub_out(self.lane_inputs(din_bits, j))
            for t, b in enumerate(lo):
                acc[k][self.slot(j, t)] ^= b
        flat = []
        for k in range(self.K):
            flat += acc[k]
        return flat[:self.WO]


def vec(bits):
    return ''.join(str(b) for b in reversed(bits))


def emit_rtl(P, neg=False):
    q = P.q
    m = q['master']
    L_ = [f'// tools/hbm_hub_quarter_gen.py --quarter {[k for k, v in QUARTERS.items() if v is q][0]}: PHYSICAL ENVELOPE die '
          f'wrapper of {m} (r16g ports) around {P.N} closed {q["lane"]} lanes; see the generator docstring.',
          f'// WI {P.WI} die input bits, WO {P.WO} die output bits, lane: broadcast {P.LB} + per-lane {P.LP} in, '
          f'{P.LO} out; {P.K} chains x {P.G} groups x 2 columns x {P.L} lanes.',
          '`timescale 1ns/1ps', f'module {m} (']
    decl = []
    for p, w in sorted([(p, w) for p, w in P.din] + [('ck', 1), ('rst', 1)]):
        decl.append(f'    input  wire [{w - 1}:0] {p}')
    for p, w in P.dout:
        decl.append(f'    output wire [{w - 1}:0] {p}')
    L_.append(',\n'.join(sorted(decl, key=lambda s: s.split()[-1])) + '\n);')
    L_ += ['    wire clk = ck[0];',
           '    // reset request: two-flop synchroniser at the boundary, carried down every broadcast chain',
           '    (* keep *) reg [1:0] rst_q;',
           '    always @(posedge clk) rst_q <= {rst_q[0], rst[0]};',
           f'    (* keep *) reg [{P.WI - 1}:0] din_p0;',
           '    always @(posedge clk) din_p0 <= {' + ', '.join(p for p, _ in reversed(P.din)) + '};']
    for s_ in range(1, P.PIPE + 1):
        L_.append(f'    (* keep *) reg [{P.WI - 1}:0] din_p{s_};  always @(posedge clk) din_p{s_} <= din_p{s_ - 1};')
    L_ += [f'    wire [{P.WI - 1}:0] din_q = din_p{P.PIPE};', f'    wire [{P.LB}:0] bsrc;']
    # bsrc[t] = XOR of din_q[t + m LB]; bsrc[LB] = reset
    fold = {}
    for u in range(P.WI):
        fold.setdefault(u % P.LB, []).append(f'din_q[{u}]')
    L_.append(f'    assign bsrc[{P.LB}] = rst_q[1];')
    for t in range(P.LB):
        L_.append(f'    assign bsrc[{t}] = ' + (' ^ '.join(fold.get(t, [])) or "1'b0") + ';')
    for k in range(P.K):
        for g in range(P.G):
            src = 'bsrc' if g == 0 else f'bc_{k}_{g - 1}'
            L_.append(f'    (* keep *) reg [{P.LB}:0] bc_{k}_{g};  always @(posedge clk) bc_{k}_{g} <= {src};')
    outs_by_lane = {}
    for j, k, g, s, i in P.lanes():
        b = f'bc_{k}_{g}'
        conns = ['.clk(clk)', f'.rst_n(~{b}[{P.LB}])']
        bi = 0
        pi = 0
        for n, w in P.ins:
            if n in q['per_lane']:
                bits = [(j * P.LP + pi + t) % P.LB for t in range(w)]
                conns.append(f'.{n}({{' + ', '.join(f'{b}[{x}]' for x in reversed(bits)) + '})')
                pi += w
            else:
                conns.append(f'.{n}({b}[{bi + w - 1}:{bi}])')
                bi += w
        lo = f'lo_{j}'
        L_.append(f'    wire [{P.LO - 1}:0] {lo};')
        ob = 0
        for n, w in P.outs:
            conns.append(f'.{n}({lo}[{ob + w - 1}:{ob}])')
            ob += w
        prm = ''.join(f'#(.{a}({v})) ' for a, v in [])
        if q['params']:
            prm = '#(' + ', '.join(f'.{a}({v})' for a, v in q['params'].items()) + ') '
        L_.append(f'    {q["lane"]} {prm}u_lane_{j} (' + ', '.join(conns) + ');')
        L_.append(f'    (* keep *) reg [{P.LO - 1}:0] lq_{j};  always @(posedge clk) lq_{j} <= {lo};')
        outs_by_lane[j] = (k, g)
    # accumulators: group G-1 is the far end; head g = 0 at the boundary
    for k in range(P.K):
        for g in reversed(range(P.G)):
            terms = {}
            for j, kk, gg, s, i in P.lanes():
                if kk != k or gg != g:
                    continue
                for t in range(P.LO):
                    x = P.slot(j, t)
                    if neg and j == 1 and t < 8:
                        x = (x + 1) % P.WC          # negative control: lane 1's first 8 result bits one slot off
                    terms.setdefault(x, []).append(f'lq_{j}[{t}]')
            prev = f'acc_{k}_{g + 1}' if g + 1 < P.G else None
            L_.append(f'    wire [{P.WC - 1}:0] nx_{k}_{g};')
            for x in range(P.WC):
                parts = ([f'{prev}[{x}]'] if prev else []) + terms.get(x, [])
                L_.append(f'    assign nx_{k}_{g}[{x}] = ' + (' ^ '.join(parts) if parts else "1'b0") + ';')
            L_.append(f'    (* keep *) reg [{P.WC - 1}:0] acc_{k}_{g};  always @(posedge clk) acc_{k}_{g} <= nx_{k}_{g};')
    L_.append(f'    wire [{P.K * P.WC - 1}:0] heads = {{' + ', '.join(f'acc_{k}_0' for k in reversed(range(P.K))) + '};')
    L_.append(f'    (* keep *) reg [{P.WO - 1}:0] dout_p0;  always @(posedge clk) dout_p0 <= heads[{P.WO - 1}:0];')
    for s_ in range(1, P.PIPE + 1):
        L_.append(f'    (* keep *) reg [{P.WO - 1}:0] dout_p{s_};  always @(posedge clk) dout_p{s_} <= dout_p{s_ - 1};')
    L_.append(f'    wire [{P.WO - 1}:0] dout_q = dout_p{P.PIPE};')
    ob = 0
    for p, w in P.dout:
        L_.append(f'    assign {p} = dout_q[{ob + w - 1}:{ob}];')
        ob += w
    L_.append('endmodule\n')
    return '\n'.join(L_)


def emit_stub(P):
    """simulation stand-in of the lane (same module name / ports): registered fixed bit function of its inputs."""
    q = P.q
    ins = ', '.join(f'input wire [{w - 1}:0] {n}' for n, w in P.ins)
    outs = ', '.join(f'output wire [{w - 1}:0] {n}' for n, w in P.outs)
    prm = ('#(' + ', '.join(f'parameter integer {a} = 0' for a in q['params']) + ') ') if q['params'] else ''
    LI = sum(w for _, w in P.ins)
    lin = '{' + ', '.join(n for n, _ in reversed(P.ins)) + '}'
    L_ = [f'// SIM STUB of {q["lane"]} (connectivity bench only): out[t] = in[(13t+5) % LI] ^ in[(7t+1) % LI], registered',
          f'module {q["lane"]} {prm}(input wire clk, input wire rst_n, {ins}, {outs});',
          f'    wire [{LI - 1}:0] lin = {lin};',
          f'    reg [{P.LO - 1}:0] r;',
          '    always @(posedge clk) begin']
    for t in range(P.LO):
        L_.append(f'        r[{t}] <= lin[{(t * 13 + 5) % LI}] ^ lin[{(t * 7 + 1) % LI}];')
    L_.append('    end')
    ob = 0
    for n, w in P.outs:
        L_.append(f'    assign {n} = r[{ob + w - 1}:{ob}];')
        ob += w
    L_.append('endmodule\n')
    return '\n'.join(L_)


def emit_tb(P, nvec, seed, out):
    rnd = random.Random(seed)
    vin, vout = [], []
    for _ in range(nvec):
        d = [rnd.getrandbits(1) for _ in range(P.WI)]
        vin.append(d)
        vout.append(P.model(d))
    (out / 'tb_in.mem').write_text('\n'.join(f'{int(vec(d), 2):0{(P.WI + 3) // 4}x}' for d in vin) + '\n')
    (out / 'tb_out.mem').write_text('\n'.join(f'{int(vec(d), 2):0{(P.WO + 3) // 4}x}' for d in vout) + '\n')
    q = P.q
    m = q['master']
    hold = 2 * P.G + 2 * P.PIPE + 14
    ports = ', '.join(f'.{p}(din[{o + w - 1}:{o}])' for (p, w), o in zip(P.din, _offs(P.din))) + ', ' + \
        ', '.join(f'.{p}(dout[{o + w - 1}:{o}])' for (p, w), o in zip(P.dout, _offs(P.dout)))
    return f"""`timescale 1ns/1ps
// connectivity bench of {m}: {nvec} random die input words (seed {seed}), each held {hold} cycles; the die output must
// settle to the generator's reference (tools/hbm_hub_quarter_gen.py Plan.model) and match exactly; exit 1 on mismatch.
module tb;
    reg clk = 0; always #0.4165 clk = ~clk;
    reg rst = 1;
    reg [{P.WI - 1}:0] din;
    wire [{P.WO - 1}:0] dout;
    reg [{P.WI - 1}:0] vin [0:{nvec - 1}];
    reg [{P.WO - 1}:0] vout [0:{nvec - 1}];
    integer v, c, bad, lat, first;
    {m} dut(.ck(clk), .rst(rst), {ports});
    initial begin
        $readmemh("tb_in.mem", vin); $readmemh("tb_out.mem", vout);
        bad = 0; lat = 0;
        din = 0; repeat (6) @(posedge clk); rst = 0;
        for (v = 0; v < {nvec}; v = v + 1) begin
            din = vin[v]; first = -1;
            for (c = 0; c < {hold}; c = c + 1) begin
                @(posedge clk); #0.1;
                if (first < 0 && dout === vout[v]) first = c;
            end
            if (dout !== vout[v]) begin bad = bad + 1; $display("MISMATCH vec %0d", v); end
            if (first > lat) lat = first;
        end
        $display("OT_RESULT vectors={nvec} mismatches=%0d settle_cycles=%0d", bad, lat + 1);
        if (bad != 0) $fatal(1, "FAIL");
        $finish;
    end
endmodule
"""


def _offs(lst):
    o, out = 0, []
    for _, w in lst:
        out.append(o)
        o += w
    return out


GX, GY = 0.432, 0.54          # macro origin grid: lcm(site 0.054, M4/M5 0.048) in x, two rows in y (rail parity)


def emit_place(P, w, h, Wq, Hq, edge=10.0, gap=10.0, two_sided=False):
    """ORFS MACRO_PLACEMENT_TCL of the quarter's lanes (w x h each) and the floorplan record.

    x: edge strip | pair 0: column s=0 (MY, pins on its right edge) | channel | column s=1 (R0, pins on its left edge) |
       gap | pair 1 ... | edge strip.  y: each column is south half (chain k = 2 pair) + port band + north half
       (chain k = 2 pair + 1); group g = 0 is the one at the band, lane slot i stacks outward; lanes of a column sit on
       a pitch of h + 0.54 (one free row pair between abutting lanes).  The edge strips keep every die pin's M4 / M5
       access free of lane obstructions; r2 lanes leave M6 / M7 open, so pins outside the band reach it over the lanes.
    two_sided (lanes with pins on both edges, su/io_lr.tcl): every column R0 between two channels, 2 C2 + 1 channels
       of equal width (the two edge channels replace the edge strips)."""
    dn = lambda v, g: math.floor(v / g + 1e-9) * g
    up_ = lambda v, g: math.ceil(v / g - 1e-9) * g
    C2 = P.C2
    e = up_(edge, GX)
    gp = up_(gap, GX)
    c = dn((Wq - 2 * e - 2 * C2 * w - (C2 - 1) * gp) / C2, GX)
    assert c >= 30.0 - 1e-6, ('channel narrower than 30 um', c)
    py = h + GY
    n = P.G * P.L                                   # lanes per half column
    band = Hq - 2 * edge - 2 * n * py
    assert band >= 50.0, ('port band thinner than 50 um', band)
    blo = up_(edge + n * py, GY)
    bhi = dn(blo + band, GY)
    xs = []
    if two_sided:
        c = dn((Wq - 2 * C2 * w) / (2 * C2 + 1), GX)
        assert c >= 30.0 - 1e-6, ('channel narrower than 30 um', c)
        e = gp = c
        for pr in range(C2):
            x0 = c + pr * 2 * (w + c)
            xs.append((x0, x0 + w + c))
    else:
        for pr in range(C2):
            x0 = e + pr * (2 * w + c + gp)
            xs.append((x0, x0 + w + c))
    L_ = [f'# tools/hbm_hub_quarter_gen.py --quarter: {P.q["master"]} lane placement ({P.N} x {P.q["lane"]} {w} x {h})']
    rec = []
    for j, k, g, s, i in P.lanes():
        pr, half = divmod(k, 2)
        r = g * P.L + i
        x = xs[pr][s]
        y = blo - (r + 1) * py if half == 0 else bhi + GY + r * py
        y = round(dn(y, GY) if half == 0 else up_(y, GY), 3)
        o = 'MY' if s == 0 and not two_sided else 'R0'
        assert 0 <= x and x + w <= Wq + 1e-6 and 0 <= y and y + h <= Hq + 1e-6, (j, x, y)
        L_.append(f'place_macro -macro_name {{u_lane_{j}}} -location {{{x:.3f} {y:.3f}}} -orientation {o}')
        rec.append([j, round(x, 3), y, o])
    fp = dict(lane_w=w, lane_h=h, two_sided=two_sided, quarter=[Wq, Hq], edge=e, gap=gp, channel=round(c, 3), band=[round(blo, 3), round(bhi, 3)],
              column_x=[[round(a, 3), round(b, 3)] for a, b in xs], lanes=rec)
    return '\n'.join(L_) + '\n', fp


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--quarter', choices=sorted(QUARTERS), required=True)
    ap.add_argument('--ports', required=True, help='tools/hbm_die_views.py ports output: <dir>/<master>/ports.json')
    ap.add_argument('--out', required=True)
    ap.add_argument('--nvec', type=int, default=6)
    ap.add_argument('--seed', type=int, default=20261006)
    ap.add_argument('--lane-size', nargs=2, type=float, metavar=('W', 'H'),
                    help='also write macro_place.tcl / floorplan.json for lanes of this footprint')
    ap.add_argument('--two-sided', action='store_true', help='lanes with pins on both edges (su/io_lr.tcl)')
    a = ap.parse_args()
    q = QUARTERS[a.quarter]
    P = Plan(q, json.loads(Path(a.ports).read_text()))
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    m = q['master']
    (out / f'{m}.sv').write_text(emit_rtl(P))
    (out / f'{m}_neg.sv').write_text(emit_rtl(P, neg=True))
    (out / f'{q["lane"]}_simstub.sv').write_text(emit_stub(P))
    (out / f'tb_{m}.sv').write_text(emit_tb(P, a.nvec, a.seed, out))
    info = dict(master=m, lane=q['lane'], lane_source=q['src'], lane_params=q['params'], lanes=P.N, chains=P.K,
                groups_per_chain=P.G, lanes_per_column_group=P.L, WI=P.WI, WO=P.WO, lane_broadcast_bits=P.LB,
                lane_per_lane_bits=P.LP, lane_out_bits=P.LO, acc_bits_per_chain=P.WC,
                flops=dict(boundary=(P.WI + P.WO) * (1 + P.PIPE) + 2, broadcast=P.K * P.G * (P.LB + 1), accumulate=P.K * P.G * P.WC,
                                                                     lane_output_stage=P.N * P.LO))
    (out / 'plan.json').write_text(json.dumps(info, indent=1) + '\n')
    if a.lane_size:
        pj = json.loads(Path(a.ports).read_text())
        tcl, fp = emit_place(P, a.lane_size[0], a.lane_size[1], pj['w_um'], pj['h_um'], two_sided=a.two_sided)
        (out / 'macro_place.tcl').write_text(tcl)
        (out / 'floorplan.json').write_text(json.dumps({k: v for k, v in fp.items() if k != 'lanes'}, indent=1) + '\n')
    print(json.dumps(info))


if __name__ == '__main__':
    main()
