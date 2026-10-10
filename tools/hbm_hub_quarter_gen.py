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
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))

SU_PHYS = 'rtl/hdc/v41x/phys/ot_hdc_v41x_su_c12_phys.sv'
HC_RTL = 'rtl/hdc/v41x/ot_dsrom_su_hcpost.sv'
EDGE_BAND = 160.0              # um: the end port bands sit at the far-end lane group (south / north)
HOP = 480.0                    # um a face-chain stage (owner rule 2026-10-07: stages <= 480 um apart)
QUARTERS = {
    # master, lane module, lane source, params, per-lane fields, C2 pairs, G groups / half, L lanes / column / group,
    # lane macro (w, h), channel width, spine (east) width
    'su': dict(master='hfd_su', lane='ot_su12_light', src=SU_PHYS, params={}, per_lane=['vi_q', 'rd_q', 'side_y'],
               C2=3, G=8, L=2, PIPE=5,
               # r23 coordinator decision 2026-10-07: end port bands for the S-face / N-face buses (2.8 mm from the
               # centre band): their face chains end at the far-end group of the south / north chains
               end={'r': 'S', 'f_su_ns': 'N', 't_su_ns': 'N'}, lane_wh=(79.92, 162.0),
               # coll inject ownership (hgi-takeover 2026-10-09, coll/rtl/spec.json ep.inj_data): f_coll carries the
               # endpoint's {inj_rd[1:0], inj_idx[2 x 16], ...} at bits 579:546; inject flit i (lane h: inj_idx[16h+15:16h])
               # is owned by quarter i mod 4 (SW 0, NW 1, SE 2, NE 3, the 2-bit strap qid tied by the die top); t_coll
               # half h (512 bits) is the AND of the envelope's result with own_h = inj_rd[h] & (inj_idx_h[1:0] == qid),
               # so a non-owner drives ZERO and hfd_coll's OR of the four quarters is the owner's data
               inj_gate=dict(out='t_coll', ctl='f_coll', rd=578, idx=546, lanes=2, strap='qid',
                             strap_pins=[('qid[0]', 1406.04, 4450.716), ('qid[1]', 1406.04, 4450.812)])),
    'sfu': dict(master='hfd_sfu', lane='ot_su12_sfu', src=SU_PHYS, params={}, per_lane=['vi_q', 'rd_q', 'side_y'],
                C2=1, G=8, L=1, PIPE=1, lane_wh=(159.84, 330.48)),
    'hc': dict(master='hfd_hc', lane='ot_dsrom_su_hcpost_lane', src=HC_RTL, params={'ML': 7, 'AL': 6},
               per_lane=['r0', 'r1', 'r2', 'r3', 'y'], C2=1, G=11, L=2, PIPE=1, lane_wh=(85.32, 115.02)),
    # safe-hbm 2026-10-08 (REVIEW_20261008 C1, S-C1): the HC quarter around the PIN-REGISTERED lane
    # (ot_dsrom_su_hcpost_lane_pr: a flop at every lane input pin, +1 cycle) with each lane (and its output capture lq)
    # clocked by the clock of the broadcast bank that launches into it (lane clock entry matched to the bc launch), and
    # every broadcast relay hop (band -> first bank, bank -> bank, bank -> its lanes) checked <= HOP (480 um).
    'hcp': dict(master='hfd_hc', lane='ot_dsrom_su_hcpost_lane_pr', src='rtl/hdc/v41x/ot_dsrom_su_hcpost_lane_pr.sv',
                params={'ML': 7, 'AL': 6}, per_lane=['r0', 'r1', 'r2', 'r3', 'y'], C2=1, G=11, L=2, PIPE=1,
                lane_wh=(85.32, 115.02), lane_ck_bank=True, bc_hop_check=True),
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
                    if v['direction'] == 'input' and p not in ('ck', 'rst') and not re.fullmatch(r'ck\d+', p)]
        self.dout = [(p, v['bits']) for p, v in sorted(ports['ports'].items()) if v['direction'] == 'output']
        assert all(v['direction'] in ('input', 'output') for v in ports['ports'].values())
        self.WI = sum(w for _, w in self.din)                 # every die input bit (the bench vector)
        self.WO = sum(w for _, w in self.dout)
        self.end = q.get('end', {}) if q.get('end') and all(p in ports['ports'] for p in q.get('end', {})) else {}
        self.din_m = [(p, w) for p, w in self.din if p not in self.end]
        self.dout_m = [(p, w) for p, w in self.dout if p not in self.end]
        self.WIm = sum(w for _, w in self.din_m)              # the centre band's inputs (folded into the broadcast)
        self.WOm = sum(w for _, w in self.dout_m)
        self.ins, self.outs = lane_ports(q)
        self.bc = [(n, w) for n, w in self.ins if n not in q['per_lane']]
        self.pl = [(n, w) for n, w in self.ins if n in q['per_lane']]
        self.LB = sum(w for _, w in self.bc)
        self.LP = sum(w for _, w in self.pl)
        self.LO = sum(w for _, w in self.outs)
        self.C2, self.G, self.L = q['C2'], q['G'], q['L']
        self.K = self.C2 * 2                 # chains: (pair, half)
        self.N = self.K * self.G * 2 * self.L
        self.WC = -(-self.WOm // self.K)     # accumulator width of one chain
        self.PIPE = q.get('PIPE', 0)         # extra (* keep *) wire stages on every die input and output (port band
        #                                      -> chain heads up to ~2.7 mm: a stage per <= 504 um)
        # r23 (2x hub, ports clustered per face): PER-PORT face chains sized from the geometry: the first input stage /
        # the last output stage AT the pin, a stage every <= HOP um from the pin-window centroid to the quarter centre
        # (the port band / chain heads), placed by common/face_chain_place.tcl (OT_FC_FILE = face_stages.tcl)
        self.dp, self.pin_y, self.tgt_y = {}, {}, {}
        self.H = ports.get('h_um', 0.0)
        self.cks = sorted([p for p in ports['ports'] if re.fullmatch(r'ck\d+', p)], key=lambda x: int(x[2:]))
        self.lane_y = {}                     # set from the placement (multi-ck segment choice)
        if ports.get('w_um') and HOP:
            cx, cy = ports['w_um'] / 2, ports['h_um'] / 2
            for p, v in ports['ports'].items():
                if p in ('ck', 'rst') or re.fullmatch(r'ck\d+', p) or not v.get('pins'):
                    continue
                xs = [(pp[2] + pp[4]) / 2 for pp in v['pins']]
                ys = [(pp[3] + pp[5]) / 2 for pp in v['pins']]
                ty = cy if p not in self.end else (EDGE_BAND if self.end[p] == 'S' else ports['h_um'] - EDGE_BAND)
                d = abs(sum(xs) / len(xs) - cx) + abs(sum(ys) / len(ys) - ty)
                self.dp[p] = max(1, math.ceil(d / HOP))
                self.pin_y[p] = sum(ys) / len(ys)
                self.tgt_y[p] = ty
        for p, _ in self.din + self.dout:
            self.dp.setdefault(p, self.PIPE + 1)
        self.DMAX = max(self.dp.values())

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
    def split(self, bits, lst):
        out, o = {}, 0
        for p, w in lst:
            out[p] = bits[o:o + w]
            o += w
        return out

    def main_bits(self, din_bits):
        d = self.split(din_bits, self.din)
        return [b for p, _ in self.din_m for b in d[p]]

    def bcw(self, din_bits):
        m = self.main_bits(din_bits)
        bcw = [0] * self.LB
        for u in range(self.WIm):                # bsrc[t] = XOR of din_q[t + m * LB]: every centre input bit is used
            bcw[u % self.LB] ^= m[u]
        return bcw

    def end_chains(self, side):
        return [k for k in range(self.K) if (k % 2 == 0) == (side == 'S')]

    def end_bits(self, side, ports_list):
        return [(p, w) for p, w in ports_list if self.end.get(p) == side]

    def lane_inputs(self, din_bits, j):
        bcw = self.bcw(din_bits)
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

    def model(self, din_bits, qid=None):
        o = self.model_raw(din_bits)
        ig = self.q.get('inj_gate')
        if not ig or qid is None:
            return o
        d = self.split(din_bits, self.din)
        c = d[ig['ctl']]
        off = dict(zip([p for p, _ in self.dout], _offs(self.dout)))[ig['out']]
        hw = dict(self.dout)[ig['out']] // ig['lanes']
        for h in range(ig['lanes']):
            idx = c[ig['idx'] + 16 * h] | c[ig['idx'] + 16 * h + 1] << 1
            if not (c[ig['rd'] + h] and idx == qid):
                for b in range(off + h * hw, off + (h + 1) * hw):
                    o[b] = 0
        return o

    def model_raw(self, din_bits):
        acc = [[0] * self.WC for _ in range(self.K)]
        d = self.split(din_bits, self.din)
        for side in ('S', 'N'):                  # end-band inputs enter the far-end accumulator of their side's chains
            ks = self.end_chains(side)
            eb = [b for p, _ in self.end_bits(side, self.din) for b in d[p]]
            for u, b in enumerate(eb):
                acc[ks[u % len(ks)]][(u // len(ks)) % self.WC] ^= b
        for j, k, g, s, i in self.lanes():
            lo = self.stub_out(self.lane_inputs(din_bits, j))
            for t, b in enumerate(lo):
                acc[k][self.slot(j, t)] ^= b
        flat = []
        for k in range(self.K):
            flat += acc[k]
        main = flat[:self.WOm]
        bcw = self.bcw(din_bits)
        outd, mo = {}, 0
        for p, w in self.dout_m:
            outd[p] = main[mo:mo + w]
            mo += w
        for side in ('S', 'N'):                  # end-band outputs read the far-end broadcast bank of their side
            ks = self.end_chains(side)
            t = 0
            for p, w in self.end_bits(side, self.dout):
                outd[p] = [bcw[(tt // len(ks)) % self.LB] for tt in range(t, t + w)]
                t += w
        return [b for p, _ in self.dout for b in outd[p]]


def vec(bits):
    return ''.join(str(b) for b in reversed(bits))


def emit_rtl(P, neg=False, xroot=False, cg=False):
    """xroot (redesign-hbm 2026-10-09, opt-in): every register-to-register hop between two segment clock roots
    (multi-ck wrappers) is launched from a LOCKUP register: a negedge copy of the source register on the SOURCE root.
    The source -> lockup hop is root-local (half a cycle), the lockup -> destination hop gets half a cycle plus the
    inter-root skew on the setup side and T/2 of hold margin, so an inter-root skew of up to ~T/2 - clk-to-Q is
    absorbed without hold buffers.  Cycle-exact (the destination still samples the source's value of the previous
    edge): 0 added cycles; cost = one flop per crossing bit (scan-chain lockup-latch practice).
    cg (redesign-hbm 2026-10-09, opt-in; coordinator: die 613.5 W vs 474.56 W, coarse per-unit gating REQUIRED): one ICG per
    lane GROUP (ot_cg_tile on the group's segment root): the group's broadcast bank, its lanes' clock pins, their output
    captures and the group's accumulator run on the gated clock; the face stages, the reset synchroniser and the output
    stages stay on the raw roots.  New pin cg_en (the unit's busy, from its record adapter): a band pin flop, then a wake
    register per group stepping outward along each chain one group an edge (as fast as the broadcast), across roots
    through a negedge lockup; HOLD 64 edges after the wake drops.  Contract: cg_en rises >= 2 edges before new input."""
    q = P.q
    m = q['master']
    nck = len(P.cks)
    seg_h = (P.H / nck) if nck else 0.0

    def ck(y):
        """the clock net of a register at height y: one die clock pin per segment (r24 multi-ck) or the single ck"""
        if not nck:
            return 'clk'
        return f'clk{min(nck - 1, max(0, int(y // seg_h)))}'

    cw, xk = {}, []                  # xroot: register -> (clock, width); emitted lockup registers

    def R(name, w, c, e=None):
        cw[name] = (c, w, e or c)

    def X(name, d):
        """the operand a register on clock d reads for register `name` (its lockup copy when the roots differ)"""
        if not xroot or not nck or name not in cw or cw[name][0] == d:
            return name
        s, w, e = cw[name]
        nm = f'{name}_xk'
        if nm not in cw:
            cw[nm] = (f'~{s}', w, e)
            xk.append(f'    (* keep *) reg [{w - 1}:0] {nm};  always @(negedge {e}) {nm} <= {name};   // xroot lockup ({s} root)')
        return nm

    band_y = P.H / 2
    gy = {}
    for j, k, g, s_, i in P.lanes():
        gy.setdefault((k, g), []).append(P.lane_y.get(j, band_y))
    gy = {kg: sum(v) / len(v) for kg, v in gy.items()}
    L_ = [f'// tools/hbm_hub_quarter_gen.py --quarter {[k for k, v in QUARTERS.items() if v is q][0]}: PHYSICAL ENVELOPE die '
          f'wrapper of {m} around {P.N} closed {q["lane"]} lanes; see the generator docstring.',
          f'// WI {P.WI} die input bits (centre band {P.WIm}), WO {P.WO} die output bits (centre band {P.WOm}), lane: broadcast '
          f'{P.LB} + per-lane {P.LP} in, {P.LO} out; {P.K} chains x {P.G} groups x 2 columns x {P.L} lanes.'
          + (f' {nck} die clock pins (one sub-tree per {seg_h:.1f} um segment).' if nck else ''),
          '`timescale 1ns/1ps', f'module {m} (']
    decl = []
    cports = [(c, 1) for c in P.cks] if nck else [('ck', 1)]
    ig = q.get('inj_gate')
    for p_, w in sorted([(p_, w) for p_, w in P.din] + cports + [('rst', 1)] + ([(ig['strap'], 2)] if ig else [])
                        + ([('cg_en', 1)] if cg else [])):
        decl.append(f'    input  wire [{w - 1}:0] {p_}')
    for p_, w in P.dout:
        decl.append(f'    output wire [{w - 1}:0] {p_}')
    L_.append(',\n'.join(sorted(decl, key=lambda x: x.split()[-1])) + '\n);')
    if nck:
        L_ += [f'    wire clk{c} = ck{c}[0];' for c in range(nck)]
    else:
        L_.append('    wire clk = ck[0];')
    L_ += ['    // reset request: two-flop synchroniser at the boundary, carried down every broadcast chain',
           '    (* keep *) reg [1:0] rst_q;',
           f'    always @(posedge {ck(band_y)}) rst_q <= {{rst_q[0], rst[0]}};',
           '    // face chains: input stage 0 at the pin, a stage per <= 480 um to its band (per-port depth dp)']
    R('rst_q', 2, ck(band_y))
    gk = {}
    if cg:                                       # per-group gated clocks gk_<k>_<g> and the wake chain (see docstring)
        bc_ = ck(band_y)
        L_ += ['    // cg: wake pin flop at the band, one wake register per group outward along each chain',
               f'    (* keep *) reg cg_q;  always @(posedge {bc_}) cg_q <= cg_en[0];']
        for k in range(P.K):
            pn, pc = 'cg_q', bc_
            rn = 'rst_q[1]'
            for g in range(P.G):
                c_ = ck(gy[(k, g)])
                src, rsrc = pn, rn
                if pc != c_:
                    L_.append(f'    (* keep *) reg cgx_{k}_{g};  always @(negedge {pc}) cgx_{k}_{g} <= {pn};   // cg wake lockup ({pc} -> {c_})')
                    L_.append(f'    (* keep *) reg crx_{k}_{g};  always @(negedge {pc}) crx_{k}_{g} <= {rn};   // cg reset relay lockup')
                    src, rsrc = f'cgx_{k}_{g}', f'crx_{k}_{g}'
                # root-local reset relay (one register a group, beside the gate): the gate's async reset never crosses the quarter
                L_ += [f'    (* keep *) reg crr_{k}_{g};  always @(posedge {c_}) crr_{k}_{g} <= {rsrc};',
                       f'    wire cgw_{k}_{g}, gk_{k}_{g};',
                       f'    ot_cg_tile #(.HOLD(64), .RSTEN(0), .MUT_LATE(`ifdef OT_HUB_CG_MUT_LATE 4 `else 0 `endif)) u_cg_{k}_{g} (.clk({c_}), '
                       f'.rst_n(~crr_{k}_{g}), .cgi({src}), .cgo(cgw_{k}_{g}), .gclk(gk_{k}_{g}));']
                gk[(k, g)] = f'gk_{k}_{g}'
                pn, pc, rn = f'cgw_{k}_{g}', c_, f'crr_{k}_{g}'
    for p_, w in P.din:
        D = P.dp[p_]
        py, ty = P.pin_y.get(p_, band_y), P.tgt_y.get(p_, band_y)
        for s_ in range(D):
            c_ = ck(py + s_ / D * (ty - py))
            src = p_ if s_ == 0 else X(f'{p_}_i{s_ - 1}', c_)
            L_.append(f'    (* keep *) reg [{w - 1}:0] {p_}_i{s_};  always @(posedge {c_}) {p_}_i{s_} <= {src};')
            R(f'{p_}_i{s_}', w, c_)
    # xroot: one broadcast source per destination root (each operand through its lockup copy when the roots differ)
    bdst = sorted({ck(gy[(k, 0)]) for k in range(P.K)}) if xroot and nck else [None]
    for d in bdst:
        sfx = f'_{d}' if d else ''
        L_.append(f'    wire [{P.WIm - 1}:0] din_q{sfx} = {{' + ', '.join(X(f'{p_}_i{P.dp[p_] - 1}', d) for p_, _ in reversed(P.din_m)) + '};')
        L_ += [f'    wire [{P.LB}:0] bsrc{sfx};']
        fold = {}
        for u in range(P.WIm):
            fold.setdefault(u % P.LB, []).append(f'din_q{sfx}[{u}]')
        L_.append(f'    assign bsrc{sfx}[{P.LB}] = {X("rst_q", d)}[1];')
        for t in range(P.LB):
            L_.append(f'    assign bsrc{sfx}[{t}] = ' + (' ^ '.join(fold.get(t, [])) or "1'b0") + ';')
    for k in range(P.K):
        for g in range(P.G):
            c_ = ck(gy[(k, g)])
            src = ('bsrc' + (f'_{c_}' if bdst != [None] else '')) if g == 0 else X(f'bc_{k}_{g - 1}', c_)
            e_ = gk.get((k, g), c_)
            L_.append(f'    (* keep *) reg [{P.LB}:0] bc_{k}_{g};  always @(posedge {e_}) bc_{k}_{g} <= {src};')
            R(f'bc_{k}_{g}', P.LB + 1, c_, e_)
    for j, k, g, s_, i in P.lanes():
        b = f'bc_{k}_{g}'
        lc = ck(gy[(k, g)]) if (q.get('lane_ck_bank') or cg) else ck(P.lane_y.get(j, band_y))
        b = X(b, lc)
        lroot, lc = lc, gk.get((k, g), lc)          # cg: the lane and its capture on the group's gated clock
        conns = [f'.clk({lc})', f'.rst_n(~{b}[{P.LB}])']
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
        prm = ''
        if q['params']:
            prm = '#(' + ', '.join(f'.{a}({v})' for a, v in q['params'].items()) + ') '
        L_.append(f'    {q["lane"]} {prm}u_lane_{j} (' + ', '.join(conns) + ');')
        L_.append(f'    (* keep *) reg [{P.LO - 1}:0] lq_{j};  always @(posedge {lc}) lq_{j} <= {lo};')
        R(f'lq_{j}', P.LO, lroot, lc)
    # end-band inputs: XORed into the far-end accumulator of their side's chains
    einj = {}
    for side in ('S', 'N'):
        ks = P.end_chains(side)
        u = 0
        for p_, w in P.end_bits(side, P.din):
            for b in range(w):
                einj.setdefault((ks[u % len(ks)], (u // len(ks)) % P.WC), []).append((f'{p_}_i{P.dp[p_] - 1}', b))
                u += 1
    # accumulators: group G-1 is the far end; head g = 0 at the boundary
    for k in range(P.K):
        for g in reversed(range(P.G)):
            c_ = ck(gy[(k, g)])
            terms = {}
            for j, kk, gg, s_, i in P.lanes():
                if kk != k or gg != g:
                    continue
                for t in range(P.LO):
                    x = P.slot(j, t)
                    if neg and j == 1 and t < 8:
                        x = (x + 1) % P.WC          # negative control: lane 1's first 8 result bits one slot off
                    terms.setdefault(x, []).append(f'{X(f"lq_{j}", c_)}[{t}]')
            if g == P.G - 1:
                for x in range(P.WC):
                    terms.setdefault(x, []).extend(f'{X(n_, c_)}[{b_}]' for n_, b_ in einj.get((k, x), []))
            prev = X(f'acc_{k}_{g + 1}', c_) if g + 1 < P.G else None
            L_.append(f'    wire [{P.WC - 1}:0] nx_{k}_{g};')
            for x in range(P.WC):
                parts = ([f'{prev}[{x}]'] if prev else []) + terms.get(x, [])
                L_.append(f'    assign nx_{k}_{g}[{x}] = ' + (' ^ '.join(parts) if parts else "1'b0") + ';')
            e_ = gk.get((k, g), c_)
            L_.append(f'    (* keep *) reg [{P.WC - 1}:0] acc_{k}_{g};  always @(posedge {e_}) acc_{k}_{g} <= nx_{k}_{g};')
            R(f'acc_{k}_{g}', P.WC, c_, e_)
    L_.append(f'    wire [{P.K * P.WC - 1}:0] heads = {{' + ', '.join(f'acc_{k}_0' for k in reversed(range(P.K))) + '};')
    hd = {}

    def heads(d):
        """the chain heads as read by a register on clock d (xroot: through the heads' lockup copies)"""
        if not xroot or not nck or all(cw[f'acc_{k}_0'][0] == d for k in range(P.K)):
            return 'heads'
        if d not in hd:
            hd[d] = f'heads_{d}'
            L_.append(f'    wire [{P.K * P.WC - 1}:0] heads_{d} = {{' + ', '.join(X(f'acc_{k}_0', d) for k in reversed(range(P.K))) + '};')
        return hd[d]
    # face chains: the last output stage at the pin (per-port depth dp)
    ob = 0
    srcs = {}
    for p_, w in P.dout_m:
        srcs[p_] = (lambda d, hi=ob + w - 1, lo=ob: f'{heads(d)}[{hi}:{lo}]')
        ob += w
    for side in ('S', 'N'):                      # end-band outputs: the far-end broadcast bank of their side
        ks = P.end_chains(side)
        t = 0
        for p_, w in P.end_bits(side, P.dout):
            srcs[p_] = (lambda d, ks=ks, t=t, w=w: '{' + ', '.join(f'{X(f"bc_{ks[tt % len(ks)]}_{P.G - 1}", d)}[{(tt // len(ks)) % P.LB}]'
                                                                for tt in reversed(range(t, t + w))) + '}')
            t += w
    if ig:
        cq = X(f"{ig['ctl']}_i{P.dp[ig['ctl']] - 1}", ck(band_y))   # the control port at the band (its last input stage)
        hw = dict(P.dout)[ig['out']] // ig['lanes']
        NR = hw // 32                                         # owner-flag replicas: fanout 32 each (no 512-wide net)
        L_ += ['    // coll inject ownership gate (see the generator\'s QUARTERS su inj_gate): quarter qid drives t_coll half h',
               '    // only when it owns inject flit inj_idx_h (inj_idx_h mod 4 == qid and inj_rd[h]); every other quarter drives 0',
               f"    (* keep *) reg [1:0] qid_q;  always @(posedge {ck(band_y)}) qid_q <= {ig['strap']};"]
        for h in range(ig['lanes']):
            own = f"{cq}[{ig['rd'] + h}] & ({cq}[{ig['idx'] + 16 * h + 1}:{ig['idx'] + 16 * h}] == qid_q)"
            L_.append('`ifdef OT_HFD_SU_MUT_NOGATE')
            L_.append(f"    wire own_{h} = 1'b1;                       // NEGATIVE CONTROL: every quarter drives")
            L_.append('`else')
            L_.append(f'    wire own_{h} = {own};')
            L_.append('`endif')
            L_.append(f'    (* keep *) reg [{NR - 1}:0] own_r{h};  always @(posedge {ck(band_y)}) own_r{h} <= {{{NR}{{own_{h}}}}};')
            R(f'own_r{h}', NR, ck(band_y))
        ownw = {}

        def own(d, NR=NR):
            nm = f"{ig['out']}_own" + (f'_{d}' if xroot and nck and cw[f'own_r0'][0] != d else '')
            if nm not in ownw:
                ownw[nm] = 1
                msk = ', '.join(f'{{32{{{X(f"own_r{h}", d)}[{r}]}}}}' for h in reversed(range(ig['lanes'])) for r in reversed(range(NR)))
                L_.append(f"    wire [{dict(P.dout)[ig['out']] - 1}:0] {nm} = {{{msk}}};")
            return nm
        if not xroot:
            own(None)
        srcs[ig['out']] = (lambda d, f=srcs[ig['out']]: f"({f(d)} & {own(d)})")
    for p_, w in P.dout:
        D = P.dp[p_]
        py, ty = P.pin_y.get(p_, band_y), P.tgt_y.get(p_, band_y)
        for s_ in range(D):
            c_ = ck(ty + (s_ + 1) / D * (py - ty))
            src = srcs[p_](c_) if s_ == 0 else X(f'{p_}_o{s_ - 1}', c_)
            L_.append(f'    (* keep *) reg [{w - 1}:0] {p_}_o{s_};  always @(posedge {c_}) {p_}_o{s_} <= {src};')
            R(f'{p_}_o{s_}', w, c_)
        L_.append(f'    assign {p_} = {p_}_o{D - 1};')
    if xk:
        L_.append(f'    // xroot: {len(xk)} lockup registers, {sum(cw[n][1] for n in cw if n.endswith("_xk"))} bits')
        L_ += xk
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


def emit_tb(P, nvec, seed, out, cg=False):
    rnd = random.Random(seed)
    vin, vout = [], []
    ig = P.q.get('inj_gate')
    if ig:
        nvec = max(nvec, 8)
        coff = dict(zip([p for p, _ in P.din], _offs(P.din)))[ig['ctl']]
    for v in range(nvec):
        d = [rnd.getrandbits(1) for _ in range(P.WI)]
        if ig:          # inject beats: rd pattern and flit indices cycling through every owner on both lanes
            rd = [3, 1, 2, 3, 0, 3, 3, 3][v % 8]
            for h in range(ig['lanes']):
                d[coff + ig['rd'] + h] = (rd >> h) & 1
                i_ = (v + 3 * h) % 4
                d[coff + ig['idx'] + 16 * h], d[coff + ig['idx'] + 16 * h + 1] = i_ & 1, i_ >> 1
        vin.append(d)
        vout.append(P.model(d))
    (out / 'tb_in.mem').write_text('\n'.join(f'{int(vec(d), 2):0{(P.WI + 3) // 4}x}' for d in vin) + '\n')
    (out / 'tb_out.mem').write_text('\n'.join(f'{int(vec(d), 2):0{(P.WO + 3) // 4}x}' for d in vout) + '\n')
    if ig:
        for qd in range(4):
            (out / f'tb_out_q{qd}.mem').write_text('\n'.join(f'{int(vec(P.model(d, qd)), 2):0{(P.WO + 3) // 4}x}'
                                                            for d in vin) + '\n')
    q = P.q
    m = q['master']
    hold = 2 * P.G + 2 * P.DMAX + 14
    cks = ', '.join(f'.{c}(clk)' for c in P.cks) if P.cks else '.ck(clk)'
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
    parameter integer QID = 0;
    reg cg_en = 1;
    {m} dut({cks}, .rst(rst), {ports}{(", ." + ig['strap'] + "(QID[1:0])") if ig else ''}{", .cg_en(cg_en)" if cg else ''});
    initial begin
        $readmemh("tb_in.mem", vin); {'$readmemh($sformatf("tb_out_q%0d.mem", QID), vout);' if ig else '$readmemh("tb_out.mem", vout);'}
        bad = 0; lat = 0;
        din = 0; repeat (6) @(posedge clk); rst = 0;
        for (v = 0; v < {nvec}; v = v + 1) begin
{'''            // cg: a fully gated gap (inputs held, wake low) before every vector, wake raised 3 edges before the data
            cg_en = 0; repeat (200) @(posedge clk); #0.1 cg_en = 1; repeat (3) @(posedge clk); #0.1;
''' if cg else ''}            din = vin[v]; first = -1;
            for (c = 0; c < {hold}; c = c + 1) begin
                @(posedge clk); #0.1;
                if (first < 0 && dout === vout[v]) first = c;
            end
            if (dout !== vout[v]) begin bad = bad + 1; $display("MISMATCH vec %0d", v); end
            if (first > lat) lat = first;
        end
        $display("OT_RESULT vectors={nvec} qid=%0d mismatches=%0d settle_cycles=%0d", QID, bad, lat + 1);
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
    ap.add_argument('--cg', action='store_true', help='coarse per-group clock gating (ot_cg_tile) with pin cg_en (redesign-hbm)')
    ap.add_argument('--xroot', choices=['none', 'lockup'], default='none',
                    help='lockup: launch every inter-root register hop from a negedge copy on the source root (0 cycles)')
    a = ap.parse_args()
    q = QUARTERS[a.quarter]
    P = Plan(q, json.loads(Path(a.ports).read_text()))
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    m = q['master']
    pj = json.loads(Path(a.ports).read_text())
    if not a.lane_size and q.get('lane_wh'):
        a.lane_size = list(q['lane_wh'])   # the closed lane footprint (registers' clock segments need the placement)
    if a.lane_size:                      # placement first: the multi-ck wrapper clocks each register by its segment
        tcl, fp = emit_place(P, a.lane_size[0], a.lane_size[1], pj['w_um'], pj['h_um'], two_sided=a.two_sided)
        P.lane_y = {r[0]: r[2] + a.lane_size[1] / 2 for r in fp['lanes']}
    if q.get('bc_hop_check') and a.lane_size:
        # broadcast relay hops (Manhattan, um): band -> first group bank, bank -> next bank, bank -> farthest lane pin
        # edge of its group (banks sit in the channel between the two columns, at the group's mean lane y)
        cols = fp.get('column_x', [[0, 0]])[0]
        chx = (cols[0] + a.lane_size[0] + cols[1]) / 2 if len(cols) > 1 else cols[0]
        gyy = {}
        for j, k, g, s_, i in P.lanes():
            gyy.setdefault((k, g), []).append(P.lane_y.get(j, P.H / 2))
        hops = []
        for k in range(P.K):
            prev = P.H / 2
            for g in range(P.G):
                y = sum(gyy[(k, g)]) / len(gyy[(k, g)])
                hops.append(abs(y - prev))
                prev = y
                hops.append(max(abs(yy - y) for yy in gyy[(k, g)]) + abs(chx - (cols[0] + a.lane_size[0])))
        info_hop = max(hops)
        print(f'bc relay max hop {info_hop:.1f} um (limit {HOP})', file=sys.stderr)
        assert info_hop <= HOP, f'broadcast relay hop {info_hop:.1f} um > {HOP} um'
    xr = a.xroot == 'lockup'
    (out / f'{m}.sv').write_text(emit_rtl(P, xroot=xr, cg=a.cg))
    (out / f'{m}_neg.sv').write_text(emit_rtl(P, neg=True, xroot=xr, cg=a.cg))
    (out / f'{q["lane"]}_simstub.sv').write_text(emit_stub(P))
    (out / f'tb_{m}.sv').write_text(emit_tb(P, a.nvec, a.seed, out, cg=a.cg))
    info = dict(master=m, lane=q['lane'], lane_source=q['src'], lane_params=q['params'], lanes=P.N, chains=P.K,
                groups_per_chain=P.G, lanes_per_column_group=P.L, WI=P.WI, WO=P.WO, lane_broadcast_bits=P.LB,
                lane_per_lane_bits=P.LP, lane_out_bits=P.LO, acc_bits_per_chain=P.WC,
                face_stages=P.dp, flops=dict(boundary=sum(w * P.dp[p] for p, w in P.din + P.dout) + 2, broadcast=P.K * P.G * (P.LB + 1), accumulate=P.K * P.G * P.WC,
                                                                     lane_output_stage=P.N * P.LO))
    if q.get('inj_gate'):            # the strap pins (not die-view ports yet): appended to the route's io_place.tcl
        (out / 'strap_pins.tcl').write_text('# tools/hbm_hub_quarter_gen.py: inject-ownership strap pins (qid, tied per quarter by the die top)\n' +
            ''.join(f'place_pin -pin_name {{{n}}} -layer M4 -location {{{x:.4f} {y:.4f}}} -pin_size {{0.1920 0.0240}}\n'
                    for n, x, y in q['inj_gate']['strap_pins']))
    (out / 'plan.json').write_text(json.dumps(info, indent=1) + '\n')
    (out / 'face_stages.tcl').write_text('# tools/hbm_hub_quarter_gen.py: die port -> face chain depth (common/face_chain_place.tcl)\n' +
        ''.join(f'set fc_ps({p}) {P.dp[p]}\n' for p, _ in P.dout) + ''.join(f'set fc_psi({p}) {P.dp[p]}\n' for p, _ in P.din))
    if a.lane_size:
        (out / 'macro_place.tcl').write_text(tcl)
        (out / 'floorplan.json').write_text(json.dumps({k: v for k, v in fp.items() if k != 'lanes'}, indent=1) + '\n')
    print(json.dumps(info))


if __name__ == '__main__':
    main()
