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
TILE_LANE_Y = 0.960            # fe-push-hphys-1010: the lane macro's y = 0 mod 0.048 (M4) and 0 mod 0.064 (M6), so its W-face
                                # pins (on grid in the lane frame) stay on the tile's tracks; 1.080 put all 2,251 off-track
TILE_SW = 100.224              # tiled su: the tile's register strip width (232 x 0.432), the lane beside it; every
                               # tile pin sits over the strip (fp lint macro_edge: no pins behind the lane)
TILE_W = 184.896              # tile width (428 x 0.432): strip + lane 83.16 + 1.512 um (lane 79.92 -> 83.16 2026-10-10: the PINKO lane at 79.92 is 65.9 % utilised with its hold-buffer allowance)
EDGE_BAND = 160.0              # um: the end port bands sit at the far-end lane group (south / north)
CG_ENREG = False              # --cg-enreg ([cg-hc] 2026-10-10): ot_cg_tile ENREG = 1 (registered ICG enable)
FOLD = 1                     # --fold N ([cg-hc] 2026-10-10): a chain half's groups over N physical column pairs
HOP = 480.0                    # um a face-chain stage (owner rule 2026-10-07: stages <= 480 um apart)
QUARTERS = {
    # master, lane module, lane source, params, per-lane fields, C2 pairs, G groups / half, L lanes / column / group,
    # lane macro (w, h), channel width, spine (east) width
    'su': dict(master='hfd_su', lane='ot_su12_light', src=SU_PHYS, params={}, per_lane=['vi_q', 'rd_q', 'side_y'],
               C2=3, G=8, L=2, PIPE=5,
               # r23 coordinator decision 2026-10-07: end port bands for the S-face / N-face buses (2.8 mm from the
               # centre band): their face chains end at the far-end group of the south / north chains
               end={'r': 'S', 'f_su_ns': 'N', 't_su_ns': 'N'}, lane_wh=(83.16, 162.0),
               # coll inject ownership (hgi-takeover 2026-10-09, coll/rtl/spec.json ep.inj_data): f_coll carries the
               # endpoint's {inj_rd[1:0], inj_idx[2 x 16], ...} at bits 579:546; inject flit i (lane h: inj_idx[16h+15:16h])
               # is owned by quarter i mod 4 (SW 0, NW 1, SE 2, NE 3, the 2-bit strap qid tied by the die top); t_coll
               # half h (512 bits) is the AND of the envelope's result with own_h = inj_rd[h] & (inj_idx_h[1:0] == qid),
               # so a non-owner drives ZERO and hfd_coll's OR of the four quarters is the owner's data
               inj_gate=dict(out='t_coll', ctl='f_coll', rd=578, idx=546, lanes=2, strap='qid',
                             strap_pins=[('qid[0]', 1406.04, 4450.716), ('qid[1]', 1406.04, 4450.812)])),
    'sfu': dict(master='hfd_sfu', lane='ot_su12_sfu', src=SU_PHYS, params={}, per_lane=['vi_q', 'rd_q', 'side_y'],
                C2=1, G=8, L=1, PIPE=1, lane_wh=(159.84, 330.48),
                # fill-8 2026-10-10 (--tiled, opt-in): FACED tile hfd_sfu_tile (see emit_tile_faced): pin flops at both
                # faces + negedge face lockups, a lane-input pin bank; lane origin y on the M4 track lattice (0 mod 0.048)
                tile=dict(name='hfd_sfu_tile', style='faced', lane_y=1.056)),
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

    def __init__(self, q, ports, half=False):
        self.q = q
        self.S = 1 if half else 2           # columns per pair (fill-8 --half-width: ONE tile column per pair)
        self.din = [(p, v['bits']) for p, v in sorted(ports['ports'].items())
                    if v['direction'] == 'input' and p not in ('ck', 'rst', 'cg_en', q.get('inj_gate', {}).get('strap')) and not re.fullmatch(r'ck\d+[ew]?', p)]
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
        self.N = self.K * self.G * self.S * self.L
        self.WC = -(-self.WOm // self.K)     # accumulator width of one chain
        # tiled (su, hbm-forks 2026-10-10): one chain per COLUMN (pair, half, side): KC chains of NT tiles; accumulate
        # width WCT a chain; broadcast rotation RB / accumulate rotation RA per tile hop
        self.tiled = False
        self.KC, self.NT = self.S * self.K, self.G * self.L
        self.WCT = -(-self.WOm // self.KC)
        self.RB = 37
        self.RA = (self.LO % self.WCT) or 1
        self.PIPE = q.get('PIPE', 0)         # extra (* keep *) wire stages on every die input and output (port band
        #                                      -> chain heads up to ~2.7 mm: a stage per <= 504 um)
        # r23 (2x hub, ports clustered per face): PER-PORT face chains sized from the geometry: the first input stage /
        # the last output stage AT the pin, a stage every <= HOP um from the pin-window centroid to the quarter centre
        # (the port band / chain heads), placed by common/face_chain_place.tcl (OT_FC_FILE = face_stages.tcl)
        self.dp, self.pin_y, self.tgt_y = {}, {}, {}
        self.H = ports.get('h_um', 0.0)
        self.cks = sorted([p for p in ports['ports'] if re.fullmatch(r'ck\d+[ew]?', p)], key=lambda x: (int(re.sub(r'\D', '', x)), x))
        # [cg-hc] 2026-10-10 (A): ck<c>e / ck<c>w = the E / W half of row root c (balanced face taps, 2 pins a row)
        self.ck_split = any(p[-1] in 'ew' for p in self.cks)
        self.W = ports.get('w_um', 0.0)
        self.lane_y = {}                     # set from the placement (multi-ck segment choice)
        if ports.get('w_um') and HOP:
            cx, cy = ports.get('band_xy') or (ports['w_um'] / 2, ports['h_um'] / 2)   # [sfu] --fold: band at the S rows
            for p, v in ports['ports'].items():
                if p in ('ck', 'rst') or re.fullmatch(r'ck\d+[ew]?', p) or not v.get('pins'):
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
        self.fold = 0                        # [sfu] --fold F: chains folded into F-tile column segments (set by main)

    def turns(self):
        """[sfu] --fold: the tile hops r -> r + 1 of a chain that turn from one column segment to the next"""
        return [r for r in range(self.NT - 1) if self.fold and (r + 1) % self.fold == 0]

    def lanes(self):
        """(lane index j, chain k, group g, side s (0 left col / 1 right col), slot i)."""
        j = 0
        for k in range(self.K):
            for g in range(self.G):
                for s in range(self.S):
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

    def rotl(self, v, n):
        W = len(v)
        return [v[(i - n) % W] for i in range(W)]

    def tile_inputs(self, bcq):
        """a tile's lane input vector from its broadcast register (bc fields in order, per-lane fields at fixed taps)"""
        vec, bi, pi = {}, 0, 0
        for n, w in self.ins:
            if n in self.q['per_lane']:
                vec[n] = [bcq[((pi + t) * 7 + 3) % self.LB] for t in range(w)]
                pi += w
            else:
                vec[n] = bcq[bi:bi + w]
                bi += w
        flat = []
        for n, w in self.ins:
            flat += vec[n]
        return flat

    def model_tiled(self, din_bits):
        bcw = self.bcw(din_bits)
        d = self.split(din_bits, self.din)
        einj = {}
        for side in ('S', 'N'):
            ks = self.end_chains(side)
            eb = [b for p, _ in self.end_bits(side, self.din) for b in d[p]]
            for u, b in enumerate(eb):
                key = (ks[u % len(ks)] * self.S, (u // len(ks)) % self.WCT)
                einj[key] = einj.get(key, 0) ^ b
        heads, fars = [], {}
        for c in range(self.KC):
            bcs = [self.rotl(bcw, (11 * c) % self.LB)]
            for r in range(self.NT):
                bcs.append(self.rotl(bcs[-1], self.RB))
            fars[c] = bcs[self.NT]
            lqs = [self.stub_out(self.tile_inputs(bcs[r])) for r in range(self.NT)]
            a = [einj.get((c, x), 0) for x in range(self.WCT)]
            for r in reversed(range(self.NT)):
                a = self.rotl(a, self.RA)
                for t in range(self.LO):
                    a[t] ^= lqs[r][t]
            heads.append(a)
        flat = [b for h in heads for b in h]
        main = flat[:self.WOm]
        outd, mo = {}, 0
        for p, w in self.dout_m:
            outd[p] = main[mo:mo + w]
            mo += w
        for side in ('S', 'N'):
            ks = self.end_chains(side)
            t = 0
            for p, w in self.end_bits(side, self.dout):
                outd[p] = [fars[ks[tt % len(ks)] * self.S][(tt // len(ks)) % self.LB] for tt in range(t, t + w)]
                t += w
        return [b for p, _ in self.dout for b in outd[p]]

    def model_raw(self, din_bits):
        if self.tiled:
            return self.model_tiled(din_bits)
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
    nck = len({re.sub(r'\D', '', c) for c in P.cks})
    seg_h = (P.H / nck) if nck else 0.0
    faced = P.tiled and q.get('tile', {}).get('style') == 'faced'
    tname = q.get('tile', {}).get('name', 'hfd_su_tile')

    def ck(y, x=None):
        """the clock net of a register at height y: one die clock pin per segment (r24 multi-ck) or the single ck.
        [cg-hc] split roots (A): the W half (x < W / 2) of row c is clk<c>w, the E half and every register without a
        position (face chains, band: the IO is on the E face) clk<c>e."""
        if not nck:
            return 'clk'
        c = min(nck - 1, max(0, int(y // seg_h)))
        if getattr(P, 'ck_split', False):
            return f'clk{c}' + ('w' if (x is not None and x < P.W / 2) else 'e')
        return f'clk{c}'

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
    gx = {}
    for j, k, g, s_, i in P.lanes():
        if j in getattr(P, 'lane_x', {}):
            gx.setdefault((k, g), []).append(P.lane_x[j])
    gx = {kg: sum(v) / len(v) for kg, v in gx.items()}
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
        L_ += [f'    wire clk{c[2:]} = {c}[0];' for c in P.cks]
    else:
        L_.append('    wire clk = ck[0];')
    L_ += ['    // reset request: two-flop synchroniser at the boundary, carried down every broadcast chain',
           '    (* keep *) reg [1:0] rst_q;',
           f'    always @(posedge {ck(band_y)}) rst_q <= {{rst_q[0], rst[0]}};',
           '    // face chains: input stage 0 at the pin, a stage per <= 480 um to its band (per-port depth dp)']
    R('rst_q', 2, ck(band_y))
    gk = {}
    gkt = {}
    if cg and not P.tiled:                       # per-group gated clocks gk_<k>_<g> and the wake chain (see docstring)
        bc_ = ck(band_y)
        L_ += ['    // cg: wake pin flop at the band, one wake register per group outward along each chain',
               f'    (* keep *) reg cg_q;  always @(posedge {bc_}) cg_q <= cg_en[0];']
        for k in range(P.K):
            pn, pc = 'cg_q', bc_
            rn = 'rst_q[1]'
            for g in range(P.G):
                c_ = ck(gy[(k, g)], gx.get((k, g)))
                src, rsrc = pn, rn
                if pc != c_:
                    L_.append(f'    (* keep *) reg cgx_{k}_{g};  always @(negedge {pc}) cgx_{k}_{g} <= {pn};   // cg wake lockup ({pc} -> {c_})')
                    L_.append(f'    (* keep *) reg crx_{k}_{g};  always @(negedge {pc}) crx_{k}_{g} <= {rn};   // cg reset relay lockup')
                    src, rsrc = f'cgx_{k}_{g}', f'crx_{k}_{g}'
                # root-local reset relay (one register a group, beside the gate): the gate's async reset never crosses the quarter
                L_ += [f'    (* keep *) reg crr_{k}_{g};  always @(posedge {c_}) crr_{k}_{g} <= {rsrc};',
                       f'    wire cgw_{k}_{g}, gk_{k}_{g};',
                       f'    ot_cg_tile #(.HOLD(64), .RSTEN(0){", .ENREG(1)" if CG_ENREG else ""}, .MUT_LATE(`ifdef OT_HUB_CG_MUT_LATE 4 `else 0 `endif)) u_cg_{k}_{g} (.clk({c_}), '
                       f'.rst_n(~crr_{k}_{g}), .cgi({src}), .cgo(cgw_{k}_{g}), .gclk(gk_{k}_{g}));']
                gk[(k, g)] = f'gk_{k}_{g}'
                pn, pc, rn = f'cgw_{k}_{g}', c_, f'crr_{k}_{g}'
    if cg and P.tiled:
        bc_ = ck(band_y)
        L_.append(f'    (* keep *) reg cg_q; always @(posedge {bc_}) cg_q <= cg_en[0];')
        for chain in range(P.KC):
            k, side = divmod(chain, P.S)
            pn, rn, pc = 'cg_q', 'rst_q[1]', bc_
            for r in range(P.NT):
                g, i = divmod(r, P.L)
                j = ((k * P.G + g) * P.S + side) * P.L + i
                c_ = ck(P.lane_y.get(j, band_y), getattr(P, 'lane_x', {}).get(j))
                src, rsrc = pn, rn
                if pc != c_:
                    L_.append(f'    (* keep *) reg cgxt_{j}; always @(negedge {pc}) cgxt_{j} <= {pn};')
                    L_.append(f'    (* keep *) reg crxt_{j}; always @(negedge {pc}) crxt_{j} <= {rn};')
                    src, rsrc = f'cgxt_{j}', f'crxt_{j}'
                L_.append(f'    (* keep *) reg crrt_{j}; always @(posedge {c_}) crrt_{j} <= {rsrc};')
                L_.append(f'    wire cgwt_{j}, gkt_{j};')
                L_.append(f'    ot_cg_tile #(.HOLD(64), .RSTEN(0){", .ENREG(1)" if CG_ENREG else ""}, .MUT_LATE(`ifdef OT_HUB_CG_MUT_LATE 4 `else 0 `endif)) u_cgt_{j} (.clk({c_}), .rst_n(~crrt_{j}), .cgi({src}), .cgo(cgwt_{j}), .gclk(gkt_{j}));')
                gkt[j] = f'gkt_{j}'
                pn, rn, pc = f'cgwt_{j}', f'crrt_{j}', c_
    for p_, w in P.din:
        D = P.dp[p_]
        py, ty = P.pin_y.get(p_, band_y), P.tgt_y.get(p_, band_y)
        for s_ in range(D):
            c_ = ck(py + s_ / D * (ty - py))
            src = p_ if s_ == 0 else X(f'{p_}_i{s_ - 1}', c_)
            L_.append(f'    (* keep *) reg [{w - 1}:0] {p_}_i{s_};  always @(posedge {c_}) {p_}_i{s_} <= {src};')
            R(f'{p_}_i{s_}', w, c_)
    # xroot: one broadcast source per destination root (each operand through its lockup copy when the roots differ)
    bdst = (sorted({ck(P.lane_y.get((k * P.G * P.S + side) * P.L, band_y), getattr(P, 'lane_x', {}).get((k * P.G * P.S + side) * P.L)) for k in range(P.K) for side in range(P.S)}) if P.tiled else sorted({ck(gy[(k, 0)], gx.get((k, 0))) for k in range(P.K)}) ) if xroot and nck else [None]
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
    if P.tiled:
        # ---- TILED (hbm-forks 2026-10-10, Tensix / systolic): one hfd_su_tile hard macro per lane (lane + its broadcast
        # register forwarded tile to tile with a per-hop rotation + lane-output capture + accumulate register); the
        # quarter top keeps the face chains, the broadcast fold and tile-to-tile wiring
        einj = {}
        for side in ('S', 'N'):
            ks = P.end_chains(side)
            u = 0
            for p_, w in P.end_bits(side, P.din):
                for b in range(w):
                    einj.setdefault((ks[u % len(ks)] * P.S, (u // len(ks)) % P.WCT), []).append((f'{p_}_i{P.dp[p_] - 1}', b))
                    u += 1
        for c in range(P.KC):
            k, s_ = divmod(c, P.S)
            L_.append(' '.join(f'wire [{P.LB}:0] tb_{c}_{r};' for r in range(P.NT + 1)))
            L_.append(' '.join(f'wire [{P.WCT - 1}:0] ta_{c}_{r};' for r in range(P.NT + 1)))
            hj = (k * P.G * P.S + s_) * P.L
            hc = ck(P.lane_y.get(hj, band_y), getattr(P, 'lane_x', {}).get(hj))
            bs = 'bsrc' + (f'_{hc}' if bdst != [None] else '')
            rc_ = (11 * c) % P.LB          # per-chain head rotation of the broadcast word (distinct chains)
            HR = getattr(P, 'head_relay', 0)
            hin = f'hsrc_{c}' if HR else f'tb_{c}_0'
            if HR:
                L_.append(f'    wire [{P.LB}:0] hsrc_{c};')
            if neg and c == 0:
                e0, cm_ = f'{{{bs}[{P.LB}], {bs}[{P.LB - 1}:1], ~{bs}[0]}}', '   // NEGATIVE CONTROL: chain 0 bit 0 inverted'
            elif rc_:
                e0, cm_ = f'{{{bs}[{P.LB}], {bs}[{P.LB - 1 - rc_}:0], {bs}[{P.LB - 1}:{P.LB - rc_}]}}', ''
            else:
                e0, cm_ = bs, ''
            assert not (faced and HR), 'faced tiles carry their own head-in / head-out registers: no --head-relay'
            if faced:      # head-in register on the head tile's root, beside the head tile's band-side face
                L_.append(f'    (* keep *) reg [{P.LB}:0] bh_{c};  always @(posedge {hc}) bh_{c} <= {e0};{cm_}')
                L_.append(f'    assign tb_{c}_0 = bh_{c};')
                R(f'bh_{c}', P.LB + 1, hc)
            elif HR:
                L_.append(f'    assign {hin} = {e0};{cm_}')
                # cons1011 head relay (textbook class 4): the broadcast word is registered at the band on the chain's
                # own root (the only root crossing: lockup -> hb_0, local) and relayed HR-1 more stages (<= ~420 um each)
                # to the chain head, whose bc_in is driven straight from the last stage (no logic, ~20-50 um)
                for s2 in range(HR):
                    src2 = hin if s2 == 0 else f'hb_{c}_{s2 - 1}'
                    L_.append(f'    (* keep *) reg [{P.LB}:0] hb_{c}_{s2};  always @(posedge {hc}) hb_{c}_{s2} <= {src2};')
                L_.append(f'    assign tb_{c}_0 = hb_{c}_{HR - 1};')
            else:
                L_.append(f'    assign tb_{c}_0 = {e0};{cm_}')
            ein = ['1\'b0'] * P.WCT
            for x in range(P.WCT):
                if (c, x) in einj:
                    fj = ((k * P.G + P.G - 1) * P.S + s_) * P.L + P.L - 1
                    fc = ck(P.lane_y.get(fj, band_y), getattr(P, 'lane_x', {}).get(fj))
                    ein[x] = ' ^ '.join(f'{X(n_, fc)}[{b_}]' for n_, b_ in einj[(c, x)])
            sep_ = ',\n        ' if einj else ', '    # far-end injection: one term a line (Verilator: < 40,000 tokens a line)
            L_.append(f'    assign ta_{c}_{P.NT} = {{' + sep_.join(reversed(ein)) + '};')
            for r in range(P.NT):
                g, i = divmod(r, P.L)
                j = ((k * P.G + g) * P.S + s_) * P.L + i
                tc = gkt.get(j, ck(P.lane_y.get(j, band_y), getattr(P, 'lane_x', {}).get(j)))
                tm = tname if faced else (getattr(P, 'tile_master', None) or ('hfd_su_tile_xl' if xroot else 'hfd_su_tile'))
                if r in P.turns():
                    # [sfu] --fold: a column-segment turn (the two tiles' far faces, one tile pitch apart): one posedge
                    # relay register each way on the quarter clock between the source tile's negedge face lockup and
                    # the destination tile's pin flop (+1 cycle each way; every register hop <= HOP)
                    L_.append(f'    wire [{P.LB}:0] tbt_{c}_{r};  wire [{P.WCT - 1}:0] tat_{c}_{r};')
                    L_.append(f'    (* keep *) reg [{P.LB}:0] tbr_{c}_{r};  always @(posedge {tc}) tbr_{c}_{r} <= tbt_{c}_{r};')
                    L_.append(f'    (* keep *) reg [{P.WCT - 1}:0] tar_{c}_{r};  always @(posedge {tc}) tar_{c}_{r} <= ta_{c}_{r + 1};')
                    L_.append(f'    assign tb_{c}_{r + 1} = tbr_{c}_{r};  assign tat_{c}_{r} = tar_{c}_{r};')
                    L_.append(f'    {tm} u_tile_{j} (.clk({tc}), .bc_in(tb_{c}_{r}), .bc_out(tbt_{c}_{r}), '
                              f'.acc_in(tat_{c}_{r}), .acc_out(ta_{c}_{r}));')
                    continue
                L_.append(f'    {tm} u_tile_{j} (.clk({tc}), .bc_in(tb_{c}_{r}), .bc_out(tb_{c}_{r + 1}), '
                          f'.acc_in(ta_{c}_{r + 1}), .acc_out(ta_{c}_{r}));')
            if faced:      # head-out register on the head tile's root: captures the head tile's negedge face lockup
                L_.append(f'    (* keep *) reg [{P.WCT - 1}:0] hq_{c};  always @(posedge {hc}) hq_{c} <= ta_{c}_0;')
                R(f'hq_{c}', P.WCT, hc)
        HR = getattr(P, 'head_relay', 0)
        if HR:
            # cons1011 head relay (output): each chain head's accumulator captured on the chain root next to the head
            # tile (half cycle from the tile's negedge acc_out, ~20-50 um), relayed HR-1 stages to the band; the band
            # output stage reads it through its lockup copy (heads(d))
            for c in range(P.KC):
                k, s_ = divmod(c, P.S)
                hj = (k * P.G * P.S + s_) * P.L
                hc = ck(P.lane_y.get(hj, band_y), getattr(P, 'lane_x', {}).get(hj))
                for s2 in range(HR):
                    src2 = f'ta_{c}_0' if s2 == 0 else f'hq_{c}_{s2 - 1}'
                    L_.append(f'    (* keep *) reg [{P.WCT - 1}:0] hq_{c}_{s2};  always @(posedge {hc}) hq_{c}_{s2} <= {src2};')
                R(f'hq_{c}_{HR - 1}', P.WCT, hc)
        elif faced:
            L_.append(f'    wire [{P.KC * P.WCT - 1}:0] heads = {{' + ', '.join(f'hq_{c}' for c in reversed(range(P.KC))) + '};')
        else:
            L_.append(f'    wire [{P.KC * P.WCT - 1}:0] heads = {{' + ', '.join(f'ta_{c}_0' for c in reversed(range(P.KC))) + '};')
    else:
        for k in range(P.K):
            for g in range(P.G):
                c_ = ck(gy[(k, g)], gx.get((k, g)))
                src = ('bsrc' + (f'_{c_}' if bdst != [None] else '')) if g == 0 else X(f'bc_{k}_{g - 1}', c_)
                e_ = gk.get((k, g), c_)
                L_.append(f'    (* keep *) reg [{P.LB}:0] bc_{k}_{g};  always @(posedge {e_}) bc_{k}_{g} <= {src};')
                R(f'bc_{k}_{g}', P.LB + 1, c_, e_)
        for j, k, g, s_, i in P.lanes():
            b = f'bc_{k}_{g}'
            lc = ck(gy[(k, g)], gx.get((k, g))) if (q.get('lane_ck_bank') or cg) else ck(P.lane_y.get(j, band_y), getattr(P, 'lane_x', {}).get(j))
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
                c_ = ck(gy[(k, g)], gx.get((k, g)))
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
        if P.tiled and getattr(P, 'head_relay', 0):
            if d not in hd:
                hd[d] = f'heads_{d}'
                L_.append(f'    wire [{P.KC * P.WCT - 1}:0] heads_{d} = {{' + ', '.join(X(f'hq_{c}_{P.head_relay - 1}', d) for c in reversed(range(P.KC))) + '};')
            return hd[d]
        if P.tiled and not faced:
            return 'heads'
        hn = [f'hq_{c}' for c in range(P.KC)] if P.tiled else [f'acc_{k}_0' for k in range(P.K)]
        if not xroot or not nck or all(cw[n_][0] == d for n_ in hn):
            return 'heads'
        if d not in hd:
            hd[d] = f'heads_{d}'
            L_.append(f'    wire [{len(hn) * cw[hn[0]][1] - 1}:0] heads_{d} = {{' + ', '.join(X(n_, d) for n_ in reversed(hn)) + '};')
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
            if P.tiled:
                srcs[p_] = (lambda d, ks=ks, t=t, w=w: '{' + (',\n        ' if w > 512 else ', ').join(f'tb_{ks[tt % len(ks)] * P.S}_{P.NT}[{(tt // len(ks)) % P.LB}]' for tt in reversed(range(t, t + w))) + '}')
            else:
                srcs[p_] = (lambda d, ks=ks, t=t, w=w: '{' + ', '.join(f'{X(f"bc_{ks[tt % len(ks)]}_{P.G - 1}", d)}[{(tt // len(ks)) % P.LB}]'
                                                                    for tt in reversed(range(t, t + w))) + '}')
            t += w
    if ig:
        cq = X(f"{ig['ctl']}_i{P.dp[ig['ctl']] - 1}", ck(band_y))   # the control port at the band (its last input stage)
        hw = dict(P.dout)[ig['out']] // ig['lanes']
        NR = hw // 32                                         # owner-flag replicas: fanout 32 each (no 512-wide net)
        L_ += ['    // coll inject ownership gate: static die strap captured at the real face, relayed to the band']
        sp = ig['strap']
        if sp in P.pin_y:
            D = P.dp[sp]
            py = P.pin_y[sp]
            for si in range(D):
                sc = ck(py + si / D * (band_y - py))
                src = sp if si == 0 else X(f'{sp}_i{si - 1}', sc)
                nm = f'{sp}_i{si}'
                L_.append(f'    (* keep *) reg [1:0] {nm}; always @(posedge {sc}) {nm} <= {src};')
                R(nm, 2, sc)
            L_.append(f'    wire [1:0] qid_q = {X(f"{sp}_i{D - 1}", ck(band_y))};')
        else:
            L_.append(f"    (* keep *) reg [1:0] qid_q; always @(posedge {ck(band_y)}) qid_q <= {sp};")
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


def emit_tile(P):
    """hfd_su_tile: one lane + its boundary registers (tiled su quarter, hbm-forks 2026-10-10).  Broadcast in -> bcq
    (forwarded rotated by RB to the next tile), lane inputs from bcq (bc fields in order, per-lane fields at fixed taps),
    lane outputs captured (lq), accumulate: acc_out <= rotl(acc_in, RA) ^ lq (low LO bits)."""
    q = P.q
    LB, W, LO = P.LB, P.WCT, P.LO
    L_ = ['`timescale 1ns/1ps',
          f'// tools/hbm_hub_quarter_gen.py --tiled: hfd_su_tile = one {q["lane"]} + its broadcast / capture / accumulate registers',
          'module hfd_su_tile (',
          '    input  wire clk,',
          f'    input  wire [{LB}:0] bc_in,',
          f'    output wire [{LB}:0] bc_out,',
          f'    input  wire [{W - 1}:0] acc_in,',
          f'    output reg  [{W - 1}:0] acc_out',
          ');',
          f'    (* keep *) reg [{LB}:0] bcq;',
          '    always @(posedge clk) bcq <= bc_in;',
          f'    assign bc_out = {{bcq[{LB}], bcq[{LB - 1 - P.RB}:0], bcq[{LB - 1}:{LB - P.RB}]}};',
          f'    wire [{LO - 1}:0] lo;']
    conns = ['.clk(clk)', f'.rst_n(~bcq[{LB}])']
    bi = pi = 0
    for n, w in P.ins:
        if n in q['per_lane']:
            bits = [((pi + t) * 7 + 3) % LB for t in range(w)]
            conns.append(f'.{n}({{' + ', '.join(f'bcq[{x}]' for x in reversed(bits)) + '})')
            pi += w
        else:
            conns.append(f'.{n}(bcq[{bi + w - 1}:{bi}])')
            bi += w
    ob = 0
    for n, w in P.outs:
        conns.append(f'.{n}(lo[{ob + w - 1}:{ob}])')
        ob += w
    prm = ('#(' + ', '.join(f'.{a}({v})' for a, v in q['params'].items()) + ') ') if q['params'] else ''
    L_.append(f'    {q["lane"]} {prm}u_lane (' + ', '.join(conns) + ');')
    L_ += [f'    (* keep *) reg [{LO - 1}:0] lq;',
           '    always @(posedge clk) lq <= lo;',
           f'    wire [{W - 1}:0] acc_r = {{acc_in[{W - 1 - P.RA}:0], acc_in[{W - 1}:{W - P.RA}]}};',
           f'    always @(posedge clk) acc_out <= acc_r ^ {{{W - LO}\'d0, lq}};',
           'endmodule', '']
    return '\n'.join(L_)


def _m4_track(y):
    """nearest asap7 M4 track centre (y = 0.012 + 0.048 k) at or above y"""
    k = -(-round((y - 0.012) * 1000) // 48)
    return round(0.012 + 0.048 * k, 4)


def emit_tile_io(P, tw, th):
    """the tile's pins: bc_in on the S edge, bc_out on the N edge (M5 and M7 over the register strip; nothing behind the
    lane), acc_out / acc_in on the W (strip) edge on M4 (lower / upper half), clk on the W edge mid"""
    L_ = ['# tools/hbm_hub_quarter_gen.py --tiled: hfd_su_tile pins']
    nb = P.LB + 1
    # [su] R25GQ agent 2026-10-10: three vertical layers over the strip, M3 every 4th track (0.144), M5 every 3rd (0.144),
    # M7 every 2nd (0.128), the slots taken evenly in x (the [sfu] faced-tile precedent 18d5bc494).  Was M5 0.096 + M7
    # 0.128 filled M5-first: S / N M5 10.3 b/um (fp lint target 6) and the routability-driven global placement of the
    # 212e3da48 tile (4,398 FIRM pin flops, 645 um2 movable) inflated +314 % and diverged (GPL-0305) / stalled at 0.76.
    # bb7e34c70 DRT-0255: the M3 edge pins (bc_in) had no access path in the bottom row (maze route fails at y < 4 um);
    # M5 every other track (0.096) + M7 every other (0.128), taken evenly in x: 10.4 / 7.8 b/um at full, < 12
    # fe-push-hphys-1010: every pin ON its routing track (asap7 make_tracks: M5 x 0.012 + 0.048k, M7 x 0.016 + 0.064k,
    # M4 y 0.012 + 0.048k).  The old origins 0.528 / 0.64 / y 2.0 sat a quarter pitch off: DRT-0422 / DRT-0421 on every
    # bc_in / acc pin and DRT-0255 maze failures at the S edge (2f07deaae, bb7e34c70, fe sw147).
    full = sorted(((ly, round(x0 + pt * k, 4)) for ly, x0, pt in (('M5', 0.540, 0.096), ('M7', 0.656, 0.128))
                   for k in range(int((TILE_SW - x0 - 0.5) / pt) + 1)), key=lambda t: (t[1], t[0]))
    assert len(full) >= nb, (len(full), nb)
    slots = [full[(i * len(full)) // nb] for i in range(nb)]
    for port, y, w_, h_ in (('bc_in', 0.0, None, None), ('bc_out', th, None, None)):
        for b in range(nb):
            ly, x = slots[b]
            sz = '0.0240 0.1920' if ly == 'M5' else '0.0320 0.1920'
            yy = 0.096 if port == 'bc_in' else round(th - 0.096, 4)
            L_.append(f'place_pin -pin_name {{{port}[{b}]}} -layer {ly} -location {{{x:.4f} {yy:.4f}}} -pin_size {{{sz}}}')
    half = th / 2
    for port, y0 in (('acc_out', 2.028), ('acc_in', _m4_track(half + 2.0))):
        for b in range(P.WCT):
            L_.append(f'place_pin -pin_name {{{port}[{b}]}} -layer M4 -location {{0.0960 {y0 + 0.096 * b:.4f}}} -pin_size {{0.1920 0.0240}}')
            assert y0 + 0.096 * b < (half if port == 'acc_out' else th) - 1.0
    L_.append(f'place_pin -pin_name {{clk}} -layer M4 -location {{0.0960 {_m4_track(half):.4f}}} -pin_size {{0.1920 0.0240}}')
    return '\n'.join(L_) + '\n'


FACED_PIN_PITCH = (('M3', 0.513, 0.144), ('M5', 0.540, 0.144), ('M7', 0.656, 0.128))   # layer, first x, pitch
# R25GQ 10-10 (the SU tile_xl DRT-0255 lesson): every origin on the ASAP7 track grid (M3 0.009 + 0.036 k, M5 0.012 + 0.048 k,
# M7 0.016 + 0.064 k); the old 0.516 / 0.528 / 0.64 were a quarter track off
FACED_E_PAD = 8.208      # um east of the lane (19 x 0.432): [sfu] 2026-10-10 the 271.944-um tile measured std 3,566 +
#                          lane 52,824 um2 = 62.5 % (fp lint gate 60 %); with the widest strip the 480-um rule allows
#                          and this pad the tile is 314.928 um wide: 54.0 %


def tile_strip_w(P):
    """faced tile: the register strip, as wide as the in-tile crossing rule allows (tile height + strip width <= HOP),
    on the 0.432 grid.  It carries one face's pins (bc + acc) over the strip alone on three vertical layers at <= 7.8
    pins / um each (fp lint pin density: fail > 12, target 6; [sfu] 2026-10-10: M5 0.096 + M7 0.064 was 15.6 b/um on
    M7): M3 every 4th track (0.144), M5 every 3rd (0.144), M7 every 2nd (0.128); each face pin meets its partner on the
    abutting tile straight across the 0.54 um gap."""
    th = P.q['lane_wh'][1] + 2.16
    sw = round(math.floor((HOP - th) / 0.432 + 1e-9) * 0.432, 3)
    nb = P.LB + 1 + P.WCT
    assert sum(int((sw - x0 - 0.5) / pt) + 1 for _, x0, pt in FACED_PIN_PITCH) >= nb, ('faced strip too narrow', sw, nb)
    return sw


def emit_tile_faced(P):
    """hfd_sfu_tile (fill-8 2026-10-10, Tensix-style tile that owns its registers): one closed lane + its register strip.
    Every tile pin is a register pin (no logic between a pin and its flop):
      band-side face (S in R0): bc_in -> bcq (pin flops);  acc_out <- negedge face lockup of acco
      outer face     (N in R0): acc_in -> accq (pin flops); bc_out  <- negedge face lockup of bco
    bcq -> bco (rotation by RB, posedge, the S -> N tile crossing, <= tile height + strip width) -> negedge lockup;
    bcq -> lin (lane-input pin bank beside the lane's W-edge pins: broadcast fields in order, per-lane fields at the
    fixed taps of tile_inputs, the reset bit -> the lane's rst_n: a per-tile registered reset copy) -> lane -> lq
    (capture beside the lane's output pins);  accq -> acco = rotl(accq, RA) ^ lq (posedge, the N -> S crossing) ->
    negedge lockup.  A neighbour's lockup -> this tile's pin flop is an abutted hop (half a cycle plus inter-root skew;
    T/2 of hold margin), so tiles on different clock roots chain without hold buffers.  Steady-state function = the
    hfd_su_tile function (Plan.model_tiled): bc 2 edges a tile, acc 2 edges a tile, lane path +2 (lin, lq)."""
    q = P.q
    LB, W, LO = P.LB, P.WCT, P.LO
    tn = q['tile']['name']
    LI = sum(w for _, w in P.ins)
    L_ = ['`timescale 1ns/1ps',
          f'// tools/hbm_hub_quarter_gen.py --quarter {[k for k, v in QUARTERS.items() if v is q][0]} --tiled: {tn} = one '
          f'{q["lane"]} + its face pin flops, face lockups, lane-input bank, output capture and accumulate registers',
          f'// LB {LB} broadcast bits + reset, LI {LI} lane input bits, LO {LO} lane output bits, WCT {W} accumulate bits, RB {P.RB}, RA {P.RA}',
          '// mutants (bench only): OT_SFU_TILE_MUT_ROT (bc forward rotation RB+1), OT_SFU_TILE_MUT_TAP (one per-lane',
          '// field bit from the next tap), OT_SFU_TILE_MUT_ACC (lane output bit 0 dropped from the accumulate)',
          f'module {tn} (',
          '    input  wire clk,',
          f'    input  wire [{LB}:0] bc_in,',
          f'    output reg  [{LB}:0] bc_out,',
          f'    input  wire [{W - 1}:0] acc_in,',
          f'    output reg  [{W - 1}:0] acc_out',
          ');',
          '`ifdef OT_SFU_TILE_MUT_ROT',
          f'    localparam integer P_RB = {P.RB + 1};',
          '`else',
          f'    localparam integer P_RB = {P.RB};',
          '`endif',
          f'    (* keep *) reg [{LB}:0] bcq;  always @(posedge clk) bcq <= bc_in;            // band-side face pin flops',
          f'    (* keep *) reg [{W - 1}:0] accq;  always @(posedge clk) accq <= acc_in;         // outer face pin flops',
          f'    wire [{LB - 1}:0] bcd = bcq[{LB - 1}:0];',
          f'    wire [{2 * LB - 1}:0] bcdd = {{bcd, bcd}};',
          f'    wire [{LB - 1}:0] bcr = bcdd[{2 * LB - 1} - P_RB -: {LB}];                 // rotl(bcd, P_RB)',
          f'    (* keep *) reg [{LB}:0] bco;  always @(posedge clk) bco <= {{bcq[{LB}], bcr}};   // S -> N crossing',
          '    always @(negedge clk) bc_out <= bco;                                      // outer face lockup']
    # lane-input bank: broadcast fields in order, per-lane fields at the fixed taps, reset bit last
    taps = []
    bi = pi = 0
    for n, w in P.ins:
        if n in q['per_lane']:
            taps.append((n, [((pi + t) * 7 + 3) % LB for t in range(w)]))
            pi += w
        else:
            taps.append((n, list(range(bi, bi + w))))
            bi += w
    L_.append(f'    (* keep *) reg [{LI}:0] lin;                                        // lane-input pin bank (+ reset copy)')
    L_.append('    always @(posedge clk) begin')
    # the TAP mutant moves the first per-lane field bit the bench's lane stand-in observes (stub_out reads lane input
    # bits (13t + 5) % LI and (7t + 1) % LI only)
    seen = {(t * 13 + 5) % LI for t in range(LO)} | {(t * 7 + 1) % LI for t in range(LO)}
    o, mut_at = 0, None
    for n, bits in taps:
        if n in q['per_lane'] and mut_at is None:
            mut_at = next((o + t for t in range(len(bits)) if o + t in seen), None)
        o += len(bits)
    assert mut_at is not None
    o = 0
    offs = {}
    for n, bits in taps:
        offs[n] = o
        for t, x in enumerate(bits):
            if o + t == mut_at:
                L_.append('`ifdef OT_SFU_TILE_MUT_TAP')
                L_.append(f'        lin[{o + t}] <= bcq[{(x + 1) % LB}];')
                L_.append('`else')
                L_.append(f'        lin[{o + t}] <= bcq[{x}];')
                L_.append('`endif')
            else:
                L_.append(f'        lin[{o + t}] <= bcq[{x}];')
        o += len(bits)
    L_.append(f'        lin[{LI}] <= bcq[{LB}];')
    L_.append('    end')
    L_.append(f'    wire [{LO - 1}:0] lo;')
    conns = ['.clk(clk)', f'.rst_n(~lin[{LI}])']
    for n, w in P.ins:
        conns.append(f'.{n}(lin[{offs[n] + w - 1}:{offs[n]}])')
    ob = 0
    for n, w in P.outs:
        conns.append(f'.{n}(lo[{ob + w - 1}:{ob}])')
        ob += w
    prm = ('#(' + ', '.join(f'.{a}({v})' for a, v in q['params'].items()) + ') ') if q['params'] else ''
    L_.append(f'    {q["lane"]} {prm}u_lane (' + ', '.join(conns) + ');')
    L_ += [f'    (* keep *) reg [{LO - 1}:0] lq;  always @(posedge clk) lq <= lo;            // lane output capture',
           '`ifdef OT_SFU_TILE_MUT_ACC',
           f'    wire [{LO - 1}:0] lqa = {{lq[{LO - 1}:1], 1\'b0}};',
           '`else',
           f'    wire [{LO - 1}:0] lqa = lq;',
           '`endif',
           f'    wire [{W - 1}:0] acc_r = {{accq[{W - 1 - P.RA}:0], accq[{W - 1}:{W - P.RA}]}};',
           f'    (* keep *) reg [{W - 1}:0] acco;  always @(posedge clk) acco <= acc_r ^ {{{W - LO}\'d0, lqa}};   // N -> S crossing',
           '    always @(negedge clk) acc_out <= acco;                                    // band-side face lockup',
           'endmodule', '']
    return '\n'.join(L_)


def emit_tile_io_faced(P, tw, th, sw):
    """faced tile pins, all over the register strip (x < sw; nothing behind the lane): band-side edge (y = 0): bc_in
    then acc_out; outer edge (y = th): bc_out then acc_in, each bit at the SAME x as its partner pin on the abutting
    tile (bc_out[b] over the next tile's bc_in[b], acc_out[b] under the previous tile's acc_in[b]); clk on the strip's
    outer (W) edge at mid height (M4)"""
    L_ = [f'# tools/hbm_hub_quarter_gen.py --tiled: {P.q["tile"]["name"]} pins (faced tile, strip {sw} um)']
    slots = sorted(((ly, round(x0 + pt * k, 4)) for ly, x0, pt in FACED_PIN_PITCH
                    for k in range(int((sw - x0 - 0.5) / pt) + 1)), key=lambda t: (t[1], t[0]))   # x order: even spread
    nb = P.LB + 1
    assert len(slots) >= nb + P.WCT, (len(slots), nb + P.WCT)
    for edge, ports in ((0, (('bc_in', nb), ('acc_out', P.WCT))), (1, (('bc_out', nb), ('acc_in', P.WCT)))):
        k = 0
        yy = 0.096 if edge == 0 else round(th - 0.096, 4)
        for port, n in ports:
            for b in range(n):
                ly, x = slots[k]
                k += 1
                sz = {'M3': '0.0180 0.1920', 'M5': '0.0240 0.1920'}.get(ly, '0.0320 0.1920')
                L_.append(f'place_pin -pin_name {{{port}[{b}]}} -layer {ly} -location {{{x:.4f} {yy:.4f}}} -pin_size {{{sz}}}')
    cy = round(round(th / 2 / 0.048) * 0.048 + 0.012, 4)
    L_.append(f'place_pin -pin_name {{clk}} -layer M4 -location {{0.0960 {cy:.4f}}} -pin_size {{0.1920 0.0240}}')
    return '\n'.join(L_) + '\n'


def emit_tile_xl(p):
    s=emit_tile(p).replace('module hfd_su_tile (','module hfd_su_tile_xl (')
    s=s.replace(f'output wire [{p.LB}:0] bc_out',f'output reg  [{p.LB}:0] bc_out')
    s=s.replace('    assign bc_out =',f'    wire [{p.LB}:0] bc_pos;\n    assign bc_pos =')
    s=s.replace('    always @(posedge clk) acc_out <=',f'    reg [{p.WCT-1}:0] acc_pos;\n    always @(posedge clk) acc_pos <=')
    s=s.replace('endmodule','''`ifdef OT_SU_TILE_MUT_NOLOCKUP
    always @(*) begin bc_out = bc_pos; acc_out = acc_pos; end
`else
    always @(negedge clk) begin bc_out <= bc_pos; acc_out <= acc_pos; end
`endif
endmodule''')
    return s


def emit_hub(P):
    """conservative-1011 TWO-LEVEL (owner 10-11 21:00): hfd_hc_hub = the quarter's band glue as its own hard element.
    One clock, every boundary registered: die-face pin flops fi <= f_sfu, the per-chain 7-way XOR broadcast fold with the
    chain's head rotation into out-flops hb<c> (bit LB = synchronised reset), head accumulators hq<c> -> pin flops ->
    t_sfu out-flops.  The die places it at the port band; band <-> chain-head relays are die-level seams."""
    LB, KC, WCT = P.LB, P.KC, P.WCT
    (pn, W), = P.din_m
    (po, WO_), = P.dout_m
    L_ = ['// tools/hbm_hub_quarter_gen.py --hub: hfd_hc_hub (band glue of the tiled hfd_hc quarter, conservative-1011)',
          '`timescale 1ns/1ps', 'module hfd_hc_hub (', '    input  wire clk,', '    input  wire rst,',
          f'    input  wire [{W - 1}:0] {pn},', f'    output wire [{WO_ - 1}:0] {po},']
    L_ += [f'    output wire [{LB}:0] hb{c},' for c in range(KC)]
    L_ += [f'    input  wire [{WCT - 1}:0] hq{c}' + (',' if c < KC - 1 else '') for c in range(KC)]
    L_ += [');', '    (* keep *) reg [1:0] rst_q;  always @(posedge clk) rst_q <= {rst_q[0], rst};',
           f'    (* keep *) reg [{W - 1}:0] fi;  always @(posedge clk) fi <= {pn};',
           f'    wire [{LB}:0] bsrc;', '    assign bsrc[%d] = rst_q[1];' % LB]
    fold = {}
    for u in range(W):
        fold.setdefault(u % LB, []).append(f'fi[{u}]')
    for t in range(LB):
        L_.append(f'    assign bsrc[{t}] = ' + (' ^ '.join(fold.get(t, [])) or "1'b0") + ';')
    for c in range(KC):
        rc_ = (11 * c) % LB
        e = (f'{{bsrc[{LB}], bsrc[{LB - 1 - rc_}:0], bsrc[{LB - 1}:{LB - rc_}]}}' if rc_ else 'bsrc')
        L_.append(f'    wire [{LB}:0] hs{c} = {e};')
        mut = (f'\n`ifdef OT_HC_HUB_MUT\n    always @(posedge clk) hbr{c} <= {{hs{c}[{LB}:1], ~hs{c}[0]}};   // MUTANT: chain {c} fold bit 0 inverted\n`else\n'
               if c == 1 else '\n')
        L_.append(f'    (* keep *) reg [{LB}:0] hbr{c};{mut}    always @(posedge clk) hbr{c} <= hs{c};' + ('\n`endif' if c == 1 else ''))
        L_.append(f'    assign hb{c} = hbr{c};')
    for c in range(KC):
        L_.append(f'    (* keep *) reg [{WCT - 1}:0] hqi{c};  always @(posedge clk) hqi{c} <= hq{c};')
    L_.append(f'    (* keep *) reg [{WO_ - 1}:0] to;  always @(posedge clk) to <= {{' + ', '.join(f'hqi{c}' for c in reversed(range(KC))) + '};')
    L_ += [f'    assign {po} = to;', 'endmodule', '']
    return '\n'.join(L_)


def emit_hub_comp(P, quarter_rtl, neg=False):
    """the hardened composition hfd_hc = hfd_hc_hub + die-level head relays (HR stages each way on the chain-head clock)
    + the 88 tiles exactly as the die places them (tile lines taken from the quarter emission)."""
    HR = max(1, getattr(P, 'head_relay', 0) or 3)
    keep = [l for l in quarter_rtl.split('\n')
            if re.match(r'^\s*(wire clk|wire \[\d+:0\] t[ab]_|assign ta_\d+_%d |hfd_hc_tile_xl |[a-z_]+ u_tile_)' % P.NT, l)]
    head = quarter_rtl.split('\n')
    i0 = next(i for i, l in enumerate(head) if l.startswith('module '))
    i1 = next(i for i, l in enumerate(head) if l.startswith(');'))
    hck = {}
    for l in keep:
        m = re.search(r'\.clk\((\w+)\), \.bc_in\(tb_(\d+)_0\)', l)
        if m:
            hck[int(m.group(2))] = m.group(1)
    (pn, W), = P.din_m
    (po, WO_), = P.dout_m
    L_ = ['// tools/hbm_hub_quarter_gen.py --hub: hardened composition of hfd_hc (hub + die head relays + 88 tiles)',
          '`timescale 1ns/1ps'] + head[i0:i1 + 1]
    L_ += [l for l in keep if 'wire clk' in l]
    L_ += [f'    wire [{P.LB}:0] hbo_{c}; wire [{P.WCT - 1}:0] hqo_{c};' for c in range(P.KC)]
    band = 'clk4e' if 'wire clk4e' in quarter_rtl else hck[0]
    L_.append(f'    hfd_hc_hub u_hub (.clk({band}), .rst(rst[0]), .{pn}({pn}), .{po}({po}), '
              + ', '.join(f'.hb{c}(hbo_{c})' for c in range(P.KC)) + ', ' + ', '.join(f'.hq{c}(hqo_{c})' for c in range(P.KC)) + ');')
    L_ += [l for l in keep if 'wire clk' not in l and 'u_tile_' not in l]
    for c in range(P.KC):
        hc = hck[c]
        for s2 in range(HR):
            src = f'hbo_{c}' if s2 == 0 else f'hb_{c}_{s2 - 1}'
            L_.append(f'    (* keep *) reg [{P.LB}:0] hb_{c}_{s2};  always @(posedge {hc}) hb_{c}_{s2} <= {src};   // die seam relay')
        last = f'hb_{c}_{HR - 1}'
        if neg and c == 0:
            L_.append(f'    assign tb_{c}_0 = {{{last}[{P.LB}:1], ~{last}[0]}};   // NEGATIVE CONTROL')
        else:
            L_.append(f'    assign tb_{c}_0 = {last};')
        for s2 in range(HR):
            src = f'ta_{c}_0' if s2 == 0 else f'hq_{c}_{s2 - 1}'
            L_.append(f'    (* keep *) reg [{P.WCT - 1}:0] hq_{c}_{s2};  always @(posedge {hc}) hq_{c}_{s2} <= {src};   // die seam relay')
        L_.append(f'    assign hqo_{c} = hq_{c}_{HR - 1};')
    L_ += [l for l in keep if 'u_tile_' in l]
    L_ += ['endmodule', '']
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
    hold = (2 * P.NT + 2 * P.DMAX + 2 * getattr(P, 'head_relay', 0) + 20) if P.tiled else (2 * P.G + 2 * P.DMAX + 14)   # tiled: 16 broadcast + 16 accumulate tile hops
    if P.tiled and q.get('tile', {}).get('style') == 'faced':
        hold = 4 * P.NT + 2 * P.DMAX + 24     # faced tiles: 2 edges a tile each way, + head in / out, lin / lq
        hold += 2 * len(P.turns())            # [sfu] --fold: one relay each way per turn
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


def emit_place(P, w, h, Wq, Hq, edge=10.0, gap=10.0, two_sided=False, mname='u_lane'):
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
    C2 = P.C2 * FOLD                                # physical column pairs (FOLD > 1: a chain half folded over FOLD pairs)
    e = up_(edge, GX)
    gp = up_(gap, GX)
    c = dn((Wq - 2 * e - 2 * C2 * w - (C2 - 1) * gp) / C2, GX)
    if FOLD > 1:
        # [cg-hc] 2026-10-10 r2: the inter-pair gap holds standard-cell rows between two lane macros; below 12 um it is an
        # unusable sliver (floorplan lint, hcq r25gq: 32 gaps of 10.37 um) -> >= 12 um, taken from the channel (pitch kept)
        gp = max(gp, up_(12.0, GX))
        # [cg-hc] 2026-10-10: the pair pitch carries the chain hop between folded columns (serpentine: outer -> outer),
        # so it stays <= HOP - 10; the spare width goes to the two edge strips (face chains / die pins)
        c = min(c, dn(HOP - 10.0 - 2 * w - gp, GX))
        e = dn((Wq - C2 * (2 * w + c) - (C2 - 1) * gp) / 2, GX)
    assert P.S == 1 or c >= 30.0 - 1e-6, ('channel narrower than 30 um', c)
    py = h + GY
    gpc = -(-P.G // FOLD)                           # groups per folded half column
    n = gpc * P.L                                   # lanes per half column
    band = Hq - 2 * edge - 2 * n * py
    assert P.fold or band >= 50.0, ('port band thinner than 50 um', band)
    blo = up_(edge + n * py, GY)
    bhi = dn(blo + band, GY)
    xs = []
    if P.S == 1:      # fill-8 --half-width: one tile column per pair, pairs side by side, centred
        c = 0.0
        x0 = dn((Wq - C2 * w - (C2 - 1) * gp) / 2, GX)
        assert x0 >= e - 1e-6, ('half-width quarter narrower than its tile column', x0)
        xs = [(x0 + pr * (w + gp),) for pr in range(C2)]
    elif two_sided:
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
    if P.fold:
        # [sfu] --fold F (R25GQ: a wide, short slot): chain c = KC chains of NT tiles, folded into ceil(NT / F) column
        # segments side by side; segment 0 starts at the S band (bc in on the tile's band-side face = S: R0, flowing
        # N), odd segments flow S (MX: band-side face on top); the turn tiles' far faces meet across one column gap
        assert P.KC == 2, ('--fold places two chains about the centre', P.KC)
        nseg = -(-P.NT // P.fold)
        ncol = P.KC * nseg
        gx = dn((Wq - ncol * w) / (ncol + 1), GX)
        assert gx >= 10.0 - 1e-6, ('fold: column gap narrower than 10 um (the tile clk pin access on its W edge)', gx)
        y0 = up_(max(edge, Hq - edge - P.fold * py - 30.0), GY)   # rows packed to the top, the band below them
        assert y0 >= 30.0 and y0 + P.fold * py <= Hq + 1e-6, ('fold: column taller than the quarter', y0)
        xs = [(gx + cc * (w + gx),) for cc in range(ncol)]
        for c in range(P.KC):
            for r in range(P.NT):
                g, i = divmod(r, P.L)
                k, s_ = divmod(c, P.S)
                j = ((k * P.G + g) * P.S + s_) * P.L + i
                sg, rr = divmod(r, P.fold)
                # both chain heads beside the slot centre (band -> head hop short): chain 0 turns W, chain 1 E
                x = xs[(nseg - 1 - sg) if c == 0 else (nseg + sg)][0]
                y = round(y0 + (rr if sg % 2 == 0 else P.fold - 1 - rr) * py, 3)
                o = 'R0' if sg % 2 == 0 else 'MX'
                L_.append(f'place_macro -macro_name {{{mname}_{j}}} -location {{{x:.3f} {y:.3f}}} -orientation {o}')
                rec.append([j, round(x, 3), y, o])
        fp = dict(lane_w=w, lane_h=h, two_sided=False, quarter=[Wq, Hq], edge=round(y0, 3), gap=gx, channel=0.0,
                  band=[0.0, round(y0, 3)], column_x=[[round(a[0], 3) for a in xs]], fold=P.fold, lanes=rec)
        return '\n'.join(L_) + '\n', fp
    for j, k, g, s, i in P.lanes():
        pr, half = divmod(k, 2)
        sub, gl = divmod(g, gpc)
        if sub % 2:                                 # serpentine: odd folded columns fill from the outer end
            gl = gpc - 1 - gl
        r = gl * P.L + i
        x = xs[pr * FOLD + (FOLD - 1 - sub)][s]    # group 0 in the EAST pair (FOLD > 1): beside the f_sfu / t_sfu face
        y = blo - (r + 1) * py if half == 0 else bhi + GY + r * py
        y = round(dn(y, GY) if half == 0 else up_(y, GY), 3)
        o = 'MY' if s == 0 and not two_sided else 'R0'
        assert 0 <= x and x + w <= Wq + 1e-6 and 0 <= y and y + h <= Hq + 1e-6, (j, x, y)
        if P.tiled:      # a tile's broadcast enters on its band-side edge: north tiles R0 / MY, south tiles MX / R180
            o = ('MY' if s == 0 else 'R0') if half == 1 else ('R180' if s == 0 else 'MX')
            if P.S == 1:   # one column: the strip (and its clk pin) on the W side, toward the die clock pins
                o = 'R0' if half == 1 else 'MX'
        L_.append(f'place_macro -macro_name {{{mname}_{j}}} -location {{{x:.3f} {y:.3f}}} -orientation {o}')
        rec.append([j, round(x, 3), y, o])
        P.lane_x = getattr(P, 'lane_x', {}); P.lane_x[j] = x + w / 2
    fp = dict(lane_w=w, lane_h=h, two_sided=two_sided, quarter=[Wq, Hq], edge=e, gap=gp, channel=round(c, 3), band=[round(blo, 3), round(bhi, 3)],
              column_x=[[round(a, 3) for a in x_] for x_ in xs], lanes=rec, fold=FOLD)
    return '\n'.join(L_) + '\n', fp


def grid_place(P, tw, th, W, H, rows, cols, mname='u_tile', pitch_x=None):
    """conservative-1011 2026-10-11 (OWNER textbook audit, hfd_hc): tiled quarter as a ROWS x COLS grid of closed tiles,
    one row per die clock-row segment (H / rows), serpentine chains: chain c = rows 2c (E -> W, head at the E port
    band) and 2c + 1 (W -> E).  Tile x / y on 0.192 (the tile's M4 / M5 / M7 pins stay on track); >= 20 um channels."""
    g = lambda v: round(round(v / 0.192) * 0.192, 3)
    pitch_x = g(pitch_x) if pitch_x else g(tw + 20.4); x0 = g(20.16); pitch_y = H / rows
    assert P.KC * P.NT == rows * cols and 2 * P.KC == rows, (P.KC, P.NT, rows, cols)
    assert x0 + (cols - 1) * pitch_x + tw < W - 150, 'no E port band'
    assert pitch_y - th >= 20, 'row channel < 20 um'
    lanes, tcl = [], []
    P.lane_x = {}
    for c in range(P.KC):
        k, s_ = divmod(c, 2)
        for r in range(P.NT):
            gg, i_ = divmod(r, P.L)
            j = ((k * P.G + gg) * 2 + s_) * P.L + i_
            row = 2 * c + r // cols; ie = r % cols
            fe = ie if row % 2 == 0 else cols - 1 - ie          # column counted from the E end
            col = cols - 1 - fe
            x = round(x0 + col * pitch_x, 3); y = g(row * pitch_y + (pitch_y - th) / 2)
            lanes.append([j, x, y]); P.lane_x[j] = x + tw / 2
            tcl.append(f'place_macro -macro_name {{{mname}_{j}}} -location {{{x:.3f} {y:.3f}}} -orientation R0 -exact')
    fp = dict(lanes=lanes, grid=[rows, cols], pitch=[pitch_x, round(pitch_y, 3)], x0=x0, tile=[tw, th],
              e_band_um=round(W - (x0 + (cols - 1) * pitch_x + tw), 3))
    return '\n'.join(tcl) + '\n', fp


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
    ap.add_argument('--tiled', action='store_true', help='su: one hfd_su_tile hard macro per lane (lane + its boundary '
                    'registers), no standard-cell sea in the channels (hbm-forks 2026-10-10)')
    ap.add_argument('--tile-master', help='--tiled: the hardened tile master (default hfd_su_tile[_xl]); conservative-1011: hfd_hc_tile_xl')
    ap.add_argument('--tile-grid', nargs=2, type=int, metavar=('ROWS', 'COLS'), help='--tiled: grid_place (one row per clock segment, serpentine chains)')
    ap.add_argument('--hub', help='--tiled: conservative-1011 TWO-LEVEL: also write hfd_hc_hub + its hardened composition (hub + die head relays + tiles) into this dir')
    ap.add_argument('--head-relay', type=int, default=0, help='--tiled: conservative-1011 per-chain head relay: N registered stages on the '
                    'chain root between the band and each chain head, both directions (textbook class 4: band -> head up to ~0.8 mm)')
    ap.add_argument('--tile-pitch-x', type=float, help='--tile-grid: column pitch um (default tile + 20.4)')
    ap.add_argument('--tile-size', nargs=2, type=float, metavar=('W', 'H'), help='--tiled: the closed tile footprint (default: strip + lane)')
    ap.add_argument('--half-width', action='store_true', help='fill-8 2026-10-10 (Option A, SFU half width): ONE tile column '
                    'per pair (half the lanes) in a quarter of half the width (E-face pins moved onto the new E edge); '
                    'needs --tiled')
    ap.add_argument('--cg', action='store_true', help='per-group clock gating, or per-tile gating with --tiled, with pin cg_en')
    ap.add_argument('--xroot', choices=['none', 'lockup'], default='none',
                    help='lockup: launch every inter-root register hop from a negedge copy on the source root (0 cycles)')
    ap.add_argument('--seg-fold', type=int, default=0, help='[sfu] (was --fold; renamed at the merge with main\'s cg-hc --fold) 2026-10-10 (R25GQ slot 2016 x 1095): fold each tile chain '
                    'into column segments of F tiles (serpentine, a registered relay each way at every turn); faced tiles')
    ap.add_argument('--band-y', type=float, default=None, help='[sfu] R25GQ: the port band / chain-head y (the die '
                    'view ports record has no band_xy; the folded quarter keeps its band at the S rows, 40 um)')
    ap.add_argument('--end', action='append', default=[], metavar='PORT=S|N',
                    help='[sfu] R25GQ (fp decision (a)): a port served by the far end of the S (even) / N (odd) chains '
                    'instead of the centre band (outputs read the far-end broadcast, inputs inject into the far-end '
                    'accumulator), so it does not widen the tile accumulator.  With --fold chain 0 ends at the W edge, '
                    'chain 1 at the E edge: the W-face lgW tap = S, the E-face HGI client ports = N')
    ap.add_argument('--sfut', type=int, default=0, help='hbmdie-1011 (el1011-hbm-sfu SFUT contract): sfu quarter lanes take '
                    'SFUT = N (chain sub-tile: exp / sigmoid / SiLU +2 N cycles); the lane module must declare SFUT and the '
                    'die vec controller must be built with the same SFUT')
    ap.add_argument('--cg-enreg', action='store_true', help='--cg: ot_cg_tile ENREG = 1 (registered ICG enable, 0 cycles)')
    ap.add_argument('--fold', type=int, default=1, help='fold each chain half over N physical column pairs (serpentine; '
                    'square outlines such as R25GQ hfd_hc 2,033 x 1,499 um)')
    a = ap.parse_args()
    global CG_ENREG, FOLD
    CG_ENREG, FOLD = a.cg_enreg, a.fold
    q = QUARTERS[a.quarter]
    if a.sfut:
        assert a.quarter == 'sfu', '--sfut applies to the sfu quarter only'
        src_ = (ROOT / q['src']).read_text()
        assert re.search(r'module\s+' + q['lane'] + r'\s*#\([^;]*\bSFUT\b', src_), (q['lane'], 'declares no SFUT parameter (el1011-hbm-sfu lane top pending)')
        q['params'] = dict(q['params'] or {}, SFUT=a.sfut)     # in place: emit_rtl finds the quarter by identity
    ap_band = a.band_y
    if a.end:
        q['end'] = dict(kv.split('=') for kv in a.end)         # in place: emit_rtl names the quarter by identity
        assert all(v in ('S', 'N') for v in q['end'].values()), q['end']
    pj = json.loads(Path(a.ports).read_text())
    if ap_band is not None:
        pj['band_xy'] = [pj['w_um'] / 2, ap_band]
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    if a.half_width:
        assert a.tiled, '--half-width needs --tiled'
    if a.half_width and not a.seg_fold:      # [sfu] --fold: the ports record is already the slot's (R25GQ proposal)
        W0 = pj['w_um']
        Wh = round(math.ceil(W0 / 2 / GX - 1e-9) * GX, 3)
        for v in pj['ports'].values():           # E-face pins onto the half-width quarter's E edge
            for pp in v.get('pins') or []:
                if pp[2] > W0 / 2:
                    pp[2], pp[4] = round(pp[2] - (W0 - Wh), 4), round(pp[4] - (W0 - Wh), 4)
        pj['w_um'] = Wh
        pj['half_width_of'] = W0
        (out / 'ports_half.json').write_text(json.dumps(pj, indent=1) + '\n')
    P = Plan(q, pj, half=a.half_width)
    P.tiled = a.tiled
    P.fold = a.seg_fold
    P.head_relay = a.head_relay if a.tiled else 0
    assert not a.seg_fold or (a.tiled and q.get('tile', {}).get('style') == 'faced'), '--fold needs a faced tiled quarter'
    m = q['master']
    faced = a.tiled and q.get('tile', {}).get('style') == 'faced'
    if not a.lane_size and q.get('lane_wh'):
        a.lane_size = list(q['lane_wh'])   # the closed lane footprint (registers' clock segments need the placement)
    P.tile_master = a.tile_master
    if faced:       # the faced tile footprint: [register strip SW | lane], lane at (SW, lane_y on the M4 lattice)
        SW = tile_strip_w(P)
        a.lane_size = [round(SW + a.lane_size[0] + FACED_E_PAD, 3), round(a.lane_size[1] + 2.16, 3)]
    elif a.tiled and a.tile_size:
        a.lane_size = list(a.tile_size)
    elif a.tiled:     # the tile footprint: [register strip TSW | lane], lane at (TSW, 0.54), one row pair above it
        a.lane_size = [round(TILE_SW + a.lane_size[0] + 1.512, 3), round(a.lane_size[1] + 2.16, 3)]   # lane at y 1.08: two rows below and above it
    if a.lane_size:                      # placement first: the multi-ck wrapper clocks each register by its segment
        if a.tiled and a.tile_grid:
            tcl, fp = grid_place(P, a.lane_size[0], a.lane_size[1], pj['w_um'], pj['h_um'], *a.tile_grid, pitch_x=a.tile_pitch_x)
        else:
            tcl, fp = emit_place(P, a.lane_size[0], a.lane_size[1], pj['w_um'], pj['h_um'], two_sided=a.two_sided,
                                 mname='u_tile' if a.tiled else 'u_lane')
        P.lane_y = {r[0]: r[2] + a.lane_size[1] / 2 for r in fp['lanes']}
    if q.get('bc_hop_check') and a.lane_size and not a.tile_grid:
        # broadcast relay hops (Manhattan, um): band -> first group bank, bank -> next bank, bank -> farthest lane pin
        # edge of its group (banks sit in the channel between the two columns, at the group's mean lane y)
        cols = fp.get('column_x', [[0, 0]])[0]
        chx = (cols[0] + a.lane_size[0] + cols[1]) / 2 if len(cols) > 1 else cols[0]
        gyy, gxx = {}, {}
        for j, k, g, s_, i in P.lanes():
            gyy.setdefault((k, g), []).append(P.lane_y.get(j, P.H / 2))
            gxx.setdefault((k, g), []).append(P.lane_x.get(j, chx))
        hops = []
        for k in range(P.K):
            prev = P.H / 2
            prevx = None
            for g in range(P.G):
                y = sum(gyy[(k, g)]) / len(gyy[(k, g)])
                x = sum(gxx[(k, g)]) / len(gxx[(k, g)])      # the bank: the channel centre of its column pair
                hops.append(abs(y - prev) + (abs(x - prevx) if prevx is not None else 0.0))
                prev, prevx = y, x
                hops.append(max(abs(yy - y) for yy in gyy[(k, g)]) + abs(chx - (cols[0] + a.lane_size[0])))
        info_hop = max(hops)
        print(f'bc relay max hop {info_hop:.1f} um (limit {HOP})', file=sys.stderr)
        assert info_hop <= HOP, f'broadcast relay hop {info_hop:.1f} um > {HOP} um'
    xr = a.xroot == 'lockup'
    (out / f'{m}.sv').write_text(emit_rtl(P, xroot=xr, cg=a.cg))
    (out / f'{m}_neg.sv').write_text(emit_rtl(P, neg=True, xroot=xr, cg=a.cg))
    (out / f'{q["lane"]}_simstub.sv').write_text(emit_stub(P))
    if faced:
        tn, ly = q['tile']['name'], q['tile']['lane_y']
        tw, th = a.lane_size
        assert abs(ly / 0.048 - round(ly / 0.048)) < 1e-6 and ly >= 1.04 and ly + q['lane_wh'][1] + 0.5 <= th - 0.54, ly
        (out / f'{tn}.sv').write_text(emit_tile_faced(P))
        td = out / 'tile'
        td.mkdir(exist_ok=True)
        (td / 'io_place.tcl').write_text(emit_tile_io_faced(P, tw, th, SW))
        (td / 'macro_place.tcl').write_text(f'place_macro -macro_name {{u_lane}} -location {{{SW:.3f} {ly:.3f}}} -orientation R0 -exact\n')
        # register-to-register hops of the tiled quarter (Manhattan um, owner rule <= HOP):
        #   in-tile crossings (bcq -> bco, accq -> acco, bcq -> lin, lq -> acco): <= tile height + strip width;
        #   tile -> tile: the abutment gap; band centre (din_q / head registers) -> the head tile's band-side face
        cx, cy = pj.get('band_xy') or (pj['w_um'] / 2, pj['h_um'] / 2)
        band_hop = max(abs(cy - (r[2] + (th if r[3] in ('MX', 'R180') else 0.0))) + abs(cx - (r[1] + SW / 2))
                       for r in fp['lanes'] if any(r[0] == ((k * P.G) * P.S + s_) * P.L for k in range(P.K) for s_ in range(P.S)))
        hops = dict(in_tile=round(th + SW, 3), tile_to_tile=round(GY, 3), band_to_head_tile=round(band_hop, 3), limit=HOP)
        if P.fold:      # a turn: source far face -> relay (mid gap) -> destination far face, one tile pitch apart
            hops['turn_relay'] = round((tw + fp['gap']) / 2 + GY, 3)
        print(f'faced tile hops {hops}', file=sys.stderr)
        assert max(hops['in_tile'], hops['band_to_head_tile']) <= HOP, hops
        (td / 'tile.json').write_text(json.dumps(dict(master=tn, w_um=tw, h_um=th, strip_w=SW, lane=q['lane'],
                                                      lane_xy=[SW, ly], LB=P.LB, WCT=P.WCT, RB=P.RB, RA=P.RA, LO=P.LO,
                                                      LI=sum(w for _, w in P.ins), style='faced', hops_um=hops), indent=1) + '\n')
    elif a.tiled:
        (out / 'hfd_su_tile.sv').write_text(emit_tile(P))
        if xr:
            (out / 'hfd_su_tile_xl.sv').write_text(emit_tile_xl(P))
        tw, th = a.lane_size
        td = out / 'tile'
        td.mkdir(exist_ok=True)
        (td / 'io_place.tcl').write_text(emit_tile_io(P, tw, th))
        (td / 'macro_place.tcl').write_text(
            f'place_macro -macro_name {{u_lane}} -location {{{TILE_SW:.3f} {TILE_LANE_Y:.3f}}} -orientation R0 -exact\n')
        (td / 'tile.json').write_text(json.dumps(dict(master='hfd_su_tile_xl' if xr else 'hfd_su_tile', w_um=tw, h_um=th, strip_w=TILE_SW,
                                                      lane=q['lane'], lane_xy=[TILE_SW, TILE_LANE_Y], LB=P.LB, WCT=P.WCT,
                                                      RB=P.RB, RA=P.RA, LO=P.LO), indent=1) + '\n')
    (out / f'tb_{m}.sv').write_text(emit_tb(P, a.nvec, a.seed, out, cg=a.cg))
    if a.tiled and a.hub:
        hd_ = Path(a.hub)
        hd_.mkdir(parents=True, exist_ok=True)
        (hd_ / 'hfd_hc_hub.sv').write_text(emit_hub(P))
        qr = emit_rtl(P, xroot=xr, cg=a.cg)
        (hd_ / f'{m}.sv').write_text(emit_hub_comp(P, qr))
        (hd_ / f'{m}_neg.sv').write_text(emit_hub_comp(P, qr, neg=True))
        for f_ in ('tb_in.mem', 'tb_out.mem', f'tb_{m}.sv', f'{q["lane"]}_simstub.sv'):
            (hd_ / f_).write_text((out / f_).read_text())
    if a.tiled:
        tiled_info = dict(head_relay=P.head_relay, tiles=P.N, chains=P.KC, tiles_per_chain=P.NT, acc_bits_per_chain=P.WCT,
                          **({} if faced else dict(flops_in_tiles=P.N * (P.LB + 1 + P.LO + P.WCT + ((P.LB + 1 + P.WCT) if xr else 0)))),
                          lockup_bits=P.N * (P.LB + 1 + P.WCT) if xr else 0,
                          **({} if not faced else dict(flops_in_tiles=P.N * (3 * (P.LB + 1) + sum(w for _, w in P.ins) + 1 + P.LO + 3 * P.WCT),
                                  face_lockup_bits=P.N * (P.LB + 1 + P.WCT), head_regs=P.KC * (P.LB + 1 + P.WCT),
                                  tile=json.loads((out / 'tile' / 'tile.json').read_text()))),
                          clock_gates=P.N if a.cg else 0, wake_lead_cycles=3 if a.cg else 0,
                          flops_in_top=dict(boundary=sum(w * P.dp[p] for p, w in P.din + P.dout) + 2))
    info = dict(master=m, lane=q['lane'], lane_source=q['src'], lane_params=q['params'], lanes=P.N, chains=P.K,
                groups_per_chain=P.G, lanes_per_column_group=P.L, WI=P.WI, WO=P.WO, lane_broadcast_bits=P.LB,
                lane_per_lane_bits=P.LP, lane_out_bits=P.LO, acc_bits_per_chain=P.WC,
                face_stages=P.dp, flops=dict(boundary=sum(w * P.dp[p] for p, w in P.din + P.dout) + 2, broadcast=P.K * P.G * (P.LB + 1), accumulate=P.K * P.G * P.WC,
                                                                     lane_output_stage=P.N * P.LO))
    if q.get('inj_gate'):
        strap_depth = P.dp[q['inj_gate']['strap']] if q['inj_gate']['strap'] in P.pin_y else 1
        info['flops']['ownership_strap'] = 2 * strap_depth
        info['ownership_capture_init_cycles'] = strap_depth
    if q.get('inj_gate'):            # the strap pins (not die-view ports yet): appended to the route's io_place.tcl
        (out / 'strap_pins.tcl').write_text('# tools/hbm_hub_quarter_gen.py: inject-ownership strap pins (qid, tied per quarter by the die top)\n' +
            ''.join(f'place_pin -pin_name {{{n}}} -layer M4 -location {{{x:.4f} {y:.4f}}} -pin_size {{0.1920 0.0240}}\n'
                    for n, x, y in q['inj_gate']['strap_pins']))
    if a.tiled:
        info['tiled'] = tiled_info
    (out / 'plan.json').write_text(json.dumps(info, indent=1) + '\n')
    (out / 'face_stages.tcl').write_text('# tools/hbm_hub_quarter_gen.py: die port -> face chain depth (common/face_chain_place.tcl)\n' +
        ''.join(f'set fc_ps({p}) {P.dp[p]}\n' for p, _ in P.dout) + ''.join(f'set fc_psi({p}) {P.dp[p]}\n' for p, _ in P.din))
    if q.get('inj_gate') and q['inj_gate']['strap'] in P.pin_y:
        with (out / 'face_stages.tcl').open('a') as sf:
            sf.write(f"set fc_psi({q['inj_gate']['strap']}) {P.dp[q['inj_gate']['strap']]}\n")
    if a.lane_size:
        (out / 'macro_place.tcl').write_text(tcl)
        (out / 'floorplan.json').write_text(json.dumps({k: v for k, v in fp.items() if k != 'lanes'}, indent=1) + '\n')
    print(json.dumps(info))


if __name__ == '__main__':
    main()
