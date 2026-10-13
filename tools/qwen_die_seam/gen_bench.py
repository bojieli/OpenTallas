#!/usr/bin/env python3
"""el1011-qseam 2026-10-12: Qwen ROM r22ko4 die SEAM bench generator (transaction level, Verilator 5.050).

Every non-clock die bus of the die-chain netlist (extract.py seam table) is built as the registered link the die places:
source out flop -> K relays (ot_qwen_die_station TAP 0, K = the bus's relay count in die.v, the census that
hier_contract_1011/qwen_rom.json v5 die_top_logic.relays states) -> sink pin.  Every seam carries a monitor
(qseam_mon): each transaction (non-zero word) entering the seam must leave it identical, in order, exactly LAT
cycles later (LAT = K, + deskew pads), and nothing may be left in flight at the end.  Element latencies the
contract posts are checked as COMPOSED seams (src element out flop -> relays -> element -> element out flop):
  vm_grp x path   seq_su.ib -> n_seq_ib (K) -> sp_vector_memory -> xw / xe   LAT = K + XVM (25; was 20)
  SU master       su64.va -> n_su_vm_a -> VM SU master -> n_su_vm_q -> su64   LAT = Ka + VL + Kq (VL 15; was 11)
  ctlm p_am       port_tiles.tf -> n_tt_f* (K) -> tt_ctlm p_am pin register  LAT = K + PAM (1)
Station words are 509 bits (contract v5 D5: 508 data a_d/b_d/t_d + the ready a_r/b_r/t_r, wired backwards
through every corridor relay and station).

Stimulus = transactions recorded from the Qwen L0-L2 chain (split-partition vehicle tools/qwen_missing/
partition_token.py stage L3, exact; host_seamrec.cpp SEAMREC on die 0): B = tile instruction issue (cycle, ib
fingerprint, the 379 ib bits), T = tile tree outputs (cycle, tile, fingerprint; 1536 tiles x 2184 lockstep),
C = collective words, R = collective returns.
  array   corridor + tree: seq_su ib driver (B) -> n_seq_ib -> VM model (XVM) -> 64 column heads (chead TAP 1
          SPLIT 1) -> 1,536 corridor stations (cst TAP 1) -> taps -> 1,536 tile models (tap pin flop; emit the
          recorded T words at their recorded offsets from their instruction's tap arrival) -> 1,440 tree node
          models (a / b pin flops, ONE valid as the tile_nk RTL: legs must be cycle-aligned, pairs checked by tag)
          -> 96 bwords -> port-tile root checkers (in-order golden tree reduction of the recorded fingerprints).
  p2p     every other relayed / abutted data seam, driven by the merged recorded stream (B + C + R, one word per
          cycle, back-to-back bursts as recorded), plus the SU-master and p_am composed seams.
  credit  credit loops (collective seq_coll -> io_xfifo -> seq_coll_x with coll_seq -> coll_seq_x credit returns;
          8 x SU constant buffer o4_cb_ctl / o4_cb_rdy; 6 x res_ser rs / rc): sender CR = round-trip credits,
          receiver buffer CR words, stalled 256 of every 512 cycles; overflow, loss, reorder or a leaked credit FAIL.
Mutants (each must FAIL): drop:<bus>:<k> (relay k becomes a wire), flip:<bus>:<k>:<bit> (relay k corrupts a bit),
xvm:<n> / vl:<n> / pam:<n> (element model latency), cr:+<n> (sender starts with extra credits).
--deskew pads the earlier tree leg at every node with relays (structural fix for unbalanced legs).

    gen_bench.py --seams seams.json --rec seamrec.txt.gz --contract qwen_rom.json --bench array|p2p|credit --out DIR
"""
from __future__ import annotations
import argparse, bisect, collections, functools, gzip, json, re
from pathlib import Path

CW_ST = 508                   # station data bits (509-bit word = 508 data + ready), contract v5 D5
XVM, VL, PAM = 25, 15, 1      # contract element latencies: vm_grp x consumer 20 -> 25, SU master 11 -> 15 (q-sp 10-11
                              # 23:50, VM tile r5), ctlm p_am pin register +1 (q-seq / qwendie 10-11 22:33)
XFIFO = 4                     # io_xfifo CDC edges each way (rom_r22ko4 collective_credit)
TILE_SUBSET = False          # --tile-subset (qwen-tp8)
NL = 3                        # tile_nk node pin -> n_y (TREE_LAT; uniform, so it cancels in leg alignment)
M32 = 0xffffffff
ONE = "1'b1"


def mix(a, b):
    x = (a * 0x9E3779B1 + b * 0x85EBCA77 + 0x165667B1) & M32
    x ^= x >> 15
    return (x * 0x2C1B3C6D) & M32


def rotl(a):
    return ((a << 1) | (a >> 31)) & M32


SV_FN = """function automatic [31:0] mix(input [31:0] a, input [31:0] b);
  reg [31:0] x; x = a * 32'h9E3779B1 + b * 32'h85EBCA77 + 32'h165667B1; x = x ^ (x >> 15); mix = x * 32'h2C1B3C6D;
endfunction
function automatic [6143:0] enc(input [31:0] tag, input [31:0] fp);   // transaction word: bit 0 = valid
  enc = {192{tag ^ fp}}; enc[64:0] = {fp, tag, 1'b1};
endfunction"""

MON_SV = """module qseam_mon #(parameter integer WS = 1, parameter integer WD = 1, parameter integer CW = 1,
    parameter integer LAT = 0, parameter integer ID = 0) (input clk, input [31:0] cyc, input [WS-1:0] src, input [WD-1:0] snk);
  // transaction-level seam check: every non-zero word entering leaves identical (low CW bits), in order, LAT cycles later
  reg [CW-1:0] vq [$]; int cq [$]; int nin = 0, ntx = 0, nerr = 0;
  always @(posedge clk) begin
    if (|src) begin vq.push_back(src[CW-1:0]); cq.push_back(cyc); nin = nin + 1; end
    if (|snk) begin
      ntx = ntx + 1;
      if (vq.size() == 0) begin nerr = nerr + 1; if (nerr <= 1) $display("SEAM_ERR id=%0d cyc=%0d unexpected", ID, cyc); end
      else begin
        if (vq[0] != snk[CW-1:0] || cyc - cq[0] != LAT) begin
          nerr = nerr + 1;
          if (nerr <= 1) $display("SEAM_ERR id=%0d cyc=%0d lat=%0d exp=%0d data_eq=%0d", ID, cyc, cyc - cq[0], LAT, vq[0] == snk[CW-1:0]);
        end
        void'(vq.pop_front()); void'(cq.pop_front());
      end
    end
  end
  final $display("MON %0d %0d %0d %0d %0d", ID, nin, ntx, nerr, vq.size());
endmodule
"""


class Gen:
    def __init__(self, S, mut):
        self.S, self.bus, self.slots, self.mut = S, S['buses'], S['slots'], mut
        self.L, self.mons = [], []

    def mon(self, src, snk, ws, wd, cw, lat, **meta):
        i = len(self.mons)
        self.mons.append(dict(id=i, lat=lat, **meta))
        self.L.append(f"  qseam_mon #(.WS({ws}), .WD({wd}), .CW({cw}), .LAT({lat}), .ID({i})) m_{i} (.clk(clk), .cyc(cyc), .src({src}), .snk({snk}));")

    def chain(self, b, W=None, pad=0, ready=False, kind=None):
        """wires + relays of bus b (+ pad relays at the sink end) + its seam monitor; returns the sink-side net"""
        d = self.bus[b]
        W = W or d['w']
        K, L = d['K'], self.L
        nm = lambda k: b + (f"__r{k}" if k else '')
        drop = {int(m.split(':')[2]) for m in self.mut if m.startswith('drop:') and m.split(':')[1] == b}
        flip = {int(m.split(':')[2]): int(m.split(':')[3]) for m in self.mut if m.startswith('flip:') and m.split(':')[1] == b}
        nets = [nm(k) for k in range(K + 1)] + [f"{b}__p{p+1}" for p in range(pad)]
        for n in nets:
            L.append(f"  wire [{W-1}:0] {n};" + (f" wire rd_{n};" if ready else ''))
        for k in range(len(nets) - 1):
            a, o = nets[k], nets[k + 1]
            if k in drop:
                L.append(f"  assign {o} = {a};   // MUTANT: relay {k} dropped" + (f" assign rd_{a} = rd_{o};" if ready else ''))
                continue
            oo = o
            if k in flip:
                oo = f"{o}_fl"
                L.append(f"  wire [{W-1}:0] {oo}; assign {o} = {oo} ^ ((|{oo}) ? {W}'d{1 << flip[k]} : {W}'d0);   // MUTANT: relay {k} flips bit {flip[k]}")
            L.append(f"  ot_qwen_die_station #(.DW({W}), .TAP(0)) r_{b}_{k} (.clk(clk), .rst_n(rst_n), .a_d({a}), .a_r({'rd_' + a if ready else ''}), "
                     f".b_d({oo}), .b_r({'rd_' + o if ready else ONE}), .t_d(), .t_r(1'b1), .c_d(), .c_r(1'b1));")
        self.mon(b, nets[-1], W, W, W, K + pad, bus=b, cls=kind or d['cls'], K=K, pad=pad, w=W)
        return nets[-1]


def load_rec(path, need_t=True):
    op = gzip.open if str(path).endswith('.gz') else open
    B, C, R = [], [], []
    Tc, Tf = {}, collections.defaultdict(dict)
    with op(path, 'rt') as f:
        for ln in f:
            p = ln.split()
            if p[0] == 'T':
                if need_t:
                    c = int(p[1])
                    Tc[c] = 1
                    Tf[int(p[2])][c] = int(p[3], 16)
            elif p[0] == 'B':
                ib = 0
                for k, w in enumerate(p[3:15]):
                    ib |= int(w, 16) << (32 * k)
                B.append((int(p[1]), int(p[2], 16), ib & ((1 << 379) - 1)))
            elif p[0] == 'C':
                C.append((int(p[1]), int(p[5], 16)))
            elif p[0] == 'R':
                R.append((int(p[1]), int(p[3], 16)))
    return dict(B=B, C=C, R=R, Tcyc=sorted(Tc), Tf=Tf)


def merged(rec):
    return sorted([(c, f) for c, f, _ in rec['B']] + rec['C'] + rec['R'])


def hexfile(out, name, rows, nhex):
    (out / f"{name}.hex").write_text(''.join(f"{r:0{nhex}x}\n" for r in rows) or '0\n')


def tb_head(name):
    return ['`timescale 1ns/1ps', f'module {name};', SV_FN, '  reg clk = 0, rst_n = 0; reg [31:0] cyc = 0;',
            '  always #1 clk = ~clk;', '  always @(posedge clk) begin cyc <= cyc + 1; if (cyc == 4) rst_n <= 1; end']


def resolve_corridor(S):
    """direction of the unrelayed head-chain words (chead <-> chead) by a walk from the VM x heads"""
    bus, slots = S['buses'], S['slots']
    ports = collections.defaultdict(list)
    for b, d in bus.items():
        if d['cls'] == 'corridor':
            for e in d['src'] + d['dst']:
                ports[e.split('.')[0]].append(b)
    seen, todo = set(), []
    for b in ('n_head_31', 'n_head_32'):
        seen.add(b)
        todo += [e.split('.')[0] for e in bus[b]['dst']]
    while todo:
        n = todo.pop()
        for b in ports[n]:
            if b in seen:
                continue
            seen.add(b)
            d = bus[b]
            eps = d['src'] + d['dst']
            if d['K'] == 0:
                d['src'] = [e for e in eps if e.split('.')[0] == n]
                d['dst'] = [e for e in eps if e.split('.')[0] != n]
            todo += [e.split('.')[0] for e in d['dst'] if slots[e.split('.')[0]]['master'] != 'qfd_tile_nk']


def tree_pads(S, xvm=None):
    """qwen-tp8: the relay pads that align every tree node's two legs, by the array bench's own static arrival model
    (identical to gen_array --deskew).  Returns ({bus: pad relays}, legs misaligned before padding).  The die generator
    (recipe tp8a, tree_pads) places these pads as real relays, so the netlist's tree is balanced and the bench passes
    WITHOUT --deskew."""
    resolve_corridor(S)
    bus, slots = S['buses'], S['slots']
    xvm = XVM if xvm is None else xvm
    pb = {e: b for b, d in bus.items() for e in d['src'] + d['dst']}
    inp = collections.defaultdict(list)
    for b, d in bus.items():
        if d['cls'] == 'clock':
            continue
        for e in d['dst']:
            inp[e.split('.')[0]].append((b, e.split('.')[1]))
    tiles = sorted([n for n, s in slots.items() if s['master'] == 'qfd_tile_nk'], key=lambda n: tuple(map(int, n.split('_')[1:])))
    nodes = [t for t in tiles if 'n_a' in slots[t]['pins']]
    Kib = bus['n_seq_ib']['K']

    @functools.lru_cache(None)
    def a_out(slot):
        if slot == 'sp_vector_memory':
            return Kib + xvm
        b = inp[slot][0][0]
        return a_out(bus[b]['src'][0].split('.')[0]) + bus[b]['K'] + 1
    tbase = lambda t: a_out(bus[pb[f'{t}.tap']]['src'][0].split('.')[0]) + bus[pb[f'{t}.tap']]['K'] + 1
    pads = {}

    def leg(t, port, yf):
        b = pb[f'{t}.{port}']
        st, sp = bus[b]['src'][0].split('.')
        return (tbase(st) if sp == 't_out' else yf(st)) + bus[b]['K'] + pads.get(b, 0)

    @functools.lru_cache(None)
    def y0(t):
        return max(leg(t, 'n_a', y0), leg(t, 'n_b', y0)) + NL
    mis = sum(1 for t in nodes if leg(t, 'n_a', y0) != leg(t, 'n_b', y0))

    @functools.lru_cache(None)
    def yp(t):
        a, b = leg(t, 'n_a', yp), leg(t, 'n_b', yp)
        if a != b:
            pads[pb[f'{t}.n_a' if a < b else f'{t}.n_b']] = abs(a - b)
        return max(a, b) + NL
    for t in nodes:
        yp(t)
    return pads, mis, len(nodes)


def gen_array(S, rec, out, deskew, mut):
    resolve_corridor(S)
    g = Gen(S, mut)
    bus, slots, L = g.bus, g.slots, g.L
    xvm = next((int(m.split(':')[1]) for m in mut if m.startswith('xvm:')), XVM)
    B, Tcyc, Tf = rec['B'], rec['Tcyc'], rec['Tf']
    t0, NI, NG = B[0][0], len(B), len(Tcyc)
    bcs = [c for c, _, _ in B]
    tins = [bisect.bisect_right(bcs, c) - 1 for c in Tcyc]
    assert min(tins) >= 0
    toff = [c - bcs[i] for c, i in zip(Tcyc, tins)]
    pb = {e: b for b, d in bus.items() for e in d['src'] + d['dst']}
    inp = collections.defaultdict(list)
    for b, d in bus.items():
        if d['cls'] == 'clock':
            continue
        for e in d['dst']:
            inp[e.split('.')[0]].append((b, e.split('.')[1]))
    tiles = sorted([n for n, s in slots.items() if s['master'] == 'qfd_tile_nk'], key=lambda n: tuple(map(int, n.split('_')[1:])))
    rtiles = sorted(Tf)
    if len(rtiles) != len(tiles):
        # qwen-tp8: a die with fewer tiles than the recording (768 TP8 tiles vs the 1,536-tile TP4 record) takes the
        # first len(tiles) recorded tile streams as its stimulus (the golden root sums are recomputed from them)
        assert len(rtiles) > len(tiles) and TILE_SUBSET, (len(rtiles), len(tiles))
        rtiles = rtiles[:len(tiles)]
    ri = {t: rtiles[i] for i, t in enumerate(tiles)}             # die slot (sorted c, r) -> recorded tile index
    nodes = [t for t in tiles if 'n_a' in slots[t]['pins']]
    Kib = bus['n_seq_ib']['K']

    # ---- static arrival model (cycles after the seq_su ib out flop) for leg alignment / deskew pads
    @functools.lru_cache(None)
    def a_out(slot):
        if slot == 'sp_vector_memory':
            return Kib + xvm
        b = inp[slot][0][0]
        return a_out(bus[b]['src'][0].split('.')[0]) + bus[b]['K'] + 1     # station: +1
    tbase = lambda t: a_out(bus[pb[f'{t}.tap']]['src'][0].split('.')[0]) + bus[pb[f'{t}.tap']]['K'] + 1
    pads = {}

    def leg(t, port, yf):
        b = pb[f'{t}.{port}']
        st, sp = bus[b]['src'][0].split('.')
        return (tbase(st) if sp == 't_out' else yf(st)) + bus[b]['K'] + pads.get(b, 0)

    @functools.lru_cache(None)
    def y0(t):
        return max(leg(t, 'n_a', y0), leg(t, 'n_b', y0)) + NL
    mis = [(t, leg(t, 'n_a', y0) - leg(t, 'n_b', y0)) for t in nodes if leg(t, 'n_a', y0) != leg(t, 'n_b', y0)]
    if deskew:
        @functools.lru_cache(None)
        def yp(t):
            a, b = leg(t, 'n_a', yp), leg(t, 'n_b', yp)
            if a != b:
                pads[pb[f'{t}.n_a' if a < b else f'{t}.n_b']] = abs(a - b)
            return max(a, b) + NL
        for t in nodes:
            yp(t)

    L += tb_head('qseam_array_tb')
    hexfile(out, 'b_cyc', [c - t0 for c in bcs], 8)
    hexfile(out, 'b_ib', [ib for _, _, ib in B], 96)
    hexfile(out, 't_ins', tins, 8)
    hexfile(out, 't_off', toff, 8)
    hexfile(out, 't_fp', [Tf[ri[t]][c] for t in tiles for c in Tcyc], 8)
    L += [f'  reg [31:0] bcyc [0:{NI-1}]; reg [383:0] bib [0:{NI-1}]; integer bi = 0;',
          f'  reg [31:0] tins [0:{NG-1}]; reg [31:0] toff [0:{NG-1}]; reg [31:0] tfp [0:{len(tiles) * NG - 1}];',
          '  initial begin $readmemh("b_cyc.hex", bcyc); $readmemh("b_ib.hex", bib); $readmemh("t_ins.hex", tins); '
          '$readmemh("t_off.hex", toff); $readmemh("t_fp.hex", tfp); end']
    W = bus['n_seq_ib']['w']
    L += [f"  reg [{W-1}:0] ib_q;   // seq_su.ib out flop: {{tag[1:0], ib[378:0], go}} at the recorded issue cycles",
          f"  always @(posedge clk) begin ib_q <= '0; if (rst_n && bi < {NI} && cyc >= bcyc[bi] + 8) begin "
          f"ib_q <= {{bi[1:0], bib[bi][378:0], 1'b1}}; bi <= bi + 1; end end"]
    sib = g.chain('n_seq_ib', kind='p2p')
    L.append("  assign n_seq_ib = ib_q;")
    # VM model: ib pin flop + (xvm - 2) stages + x out flop = xvm cycles from the VM ib pin to xw / xe
    L += [f"  reg [{W-1}:0] vm_p [0:{xvm-2}]; reg [{CW_ST-1}:0] vm_x; reg [31:0] vm_n = 0;",
          f"  always @(posedge clk) begin vm_p[0] <= {sib}; for (int k = 1; k <= {xvm-2}; k++) vm_p[k] <= vm_p[k-1];",
          f"    vm_x <= '0; if (vm_p[{xvm-2}][0]) begin vm_x <= {{mix(vm_n, 1), mix(vm_n, 2), mix(vm_n, 3), mix(vm_n, 4), vm_p[{xvm-2}][379:0]}}; vm_n <= vm_n + 1; end end",
]
    g.mon('ib_q', 'vm_x', W, CW_ST, 380, Kib + XVM, bus='vm_grp:n_seq_ib->x', cls='vm_grp', K=Kib, pad=0, w=380)
    ARR = [b for b, d in bus.items() if d['cls'] in ('corridor', 'tree') or b.startswith('n_bword')]
    sink = {}
    for b in ARR:
        cor = bus[b]['cls'] == 'corridor'
        sink[b] = g.chain(b, W=CW_ST if cor else None, pad=pads.get(b, 0), ready=cor,
                          kind='tree' if b.startswith('n_bword') else None)
    L.append("  assign n_head_31 = vm_x; assign n_head_32 = vm_x; wire vm_xw_r = rd_n_head_31, vm_xe_r = rd_n_head_32;")
    for n, s in slots.items():
        m = s['master']
        if not m.startswith(('qfd_chead', 'qfd_cst')):
            continue
        (ib_, ip), = inp[n]
        outs = {p: re.sub(r'__r\d+$', '', v) for p, v in s['pins'].items() if p not in ('ck', ip)}
        if m.startswith('qfd_cst'):
            td, cd = outs.pop('tap'), None
        else:
            td, cd = outs.pop('s'), outs.pop('n')
        bd = next(iter(outs.values())) if outs else None
        for nm_, v in (('bd', bd), ('cd', cd)):
            if v is None:
                L.append(f"  wire [{CW_ST-1 if nm_ == 'bd' else 0}:0] {n}_{nm_};")
        rr = lambda v: f"rd_{v}" if v else "1'b1"
        L.append(f"  ot_qwen_die_station #(.DW({CW_ST}), .TAP(1), .SPLIT({1 if cd else 0})) st_{n} (.clk(clk), .rst_n(rst_n), "
                 f".a_d({sink[ib_]}), .a_r(rd_{sink[ib_]}), .b_d({bd or n + '_bd'}), .b_r({rr(bd)}), .t_d({td}), .t_r({rr(td)}), "
                 f".c_d({cd or n + '_cd'}), .c_r({rr(cd)}));")
    for i, t in enumerate(tiles):
        p = slots[t]['pins']
        tp = sink[pb[t + '.tap']]
        L.append(f"  assign rd_{tp} = 1'b1;")
        L.append(f"  qseam_tile #(.TI({i})) {t} (.clk(clk), .cyc(cyc), .tap({tp}), .t_out({p['t_out']}));")
        if 'n_a' in p:
            L.append(f"  qseam_node #(.TID({i})) {t}_nd (.clk(clk), .cyc(cyc), .a({sink[pb[t + '.n_a']]}), .b({sink[pb[t + '.n_b']]}), .y({p['n_y']}));")
    roots = sorted((b for b in bus if b.startswith('n_bword')), key=lambda x: int(x.split('_')[-1]))
    for j, b in enumerate(roots):
        L.append(f"  qseam_root #(.RID({j})) rt_{j} (.clk(clk), .cyc(cyc), .w({sink[b]}));")
    end = (Tcyc[-1] - t0) + 2500
    L += [f'  reg [31:0] rgold [0:{len(roots) * NG - 1}]; initial $readmemh("root_gold.hex", rgold);',
          f'  always @(posedge clk) if (cyc == {end}) begin $display("READY xw=%0d xe=%0d", vm_xw_r, vm_xe_r); '
          f'$display("QSEAM_ARRAY END cyc=%0d", cyc); $finish; end',
          'endmodule',
          f"""module qseam_tile #(parameter integer TI = 0) (input clk, input [31:0] cyc, input [{CW_ST-1}:0] tap, output reg [511:0] t_out);
{SV_FN}
  // tap pin flop; instruction k = the k-th go; recorded T word g leaves toff[g] cycles after its instruction's pin flop
  reg [{CW_ST-1}:0] tq; integer nk = 0, gi = 0, late = 0; reg [31:0] ak [0:{NI-1}];
  wire [31:0] gk = (gi < {NG}) ? qseam_array_tb.tins[gi] : 32'hffffffff;
  always @(posedge clk) begin
    tq <= tap; t_out <= '0;
    if (tq[0]) begin ak[nk] = cyc; nk = nk + 1; end
    if (gi < {NG} && gk < nk && cyc >= ak[gk] + qseam_array_tb.toff[gi]) begin
      if (cyc != ak[gk] + qseam_array_tb.toff[gi]) late = late + 1;
      t_out <= enc(gi, qseam_array_tb.tfp[TI * {NG} + gi])[511:0]; gi = gi + 1;
    end
  end
  final if (gi != {NG} || nk != {NI} || late) $display("TILE_ERR ti=%0d instr=%0d out=%0d late=%0d", TI, nk, gi, late);
endmodule
module qseam_node #(parameter integer TID = 0) (input clk, input [31:0] cyc, input [511:0] a, input [511:0] b, output [511:0] y);
{SV_FN}
  // a / b pin flops under ONE valid (ot_qwen_rom_tile_nk n_va): the legs must arrive in the same cycle with the same tag
  reg [511:0] aq, bq, yq [0:{NL-2}]; integer nerr = 0, npair = 0;
  always @(posedge clk) begin aq <= a; bq <= b; end
  wire pair = aq[0] && bq[0] && aq[32:1] == bq[32:1];
  always @(posedge clk) begin
    yq[0] <= pair ? enc(aq[32:1], {{aq[63:33], aq[64]}} ^ bq[64:33])[511:0] : '0;
    for (int k = 1; k <= {NL-2}; k++) yq[k] <= yq[k-1];
    if (pair) npair = npair + 1;
    if ((aq[0] | bq[0]) && !pair) begin nerr = nerr + 1;
      if (nerr <= 1) $display("PAIR_MISMATCH node=%0d cyc=%0d a(v=%0d tag=%0d) b(v=%0d tag=%0d)", TID, cyc, aq[0], aq[32:1], bq[0], bq[32:1]); end
  end
  assign y = yq[{NL-2}];
  final $display("NODE %0d %0d %0d", TID, npair, nerr);
endmodule
module qseam_root #(parameter integer RID = 0) (input clk, input [31:0] cyc, input [511:0] w);
  // port-tile bword pin flop; in-order compare with the golden tree reduction of the recorded tile fingerprints
  reg [511:0] wq; integer n = 0, nerr = 0;
  always @(posedge clk) begin wq <= w;
    if (wq[0]) begin
      if (n >= {NG} || wq[32:1] != n || wq[64:33] != qseam_array_tb.rgold[RID * {NG} + n]) begin nerr = nerr + 1;
        if (nerr <= 1) $display("ROOT_ERR rid=%0d cyc=%0d n=%0d tag=%0d", RID, cyc, n, wq[32:1]); end
      n = n + 1;
    end
  end
  final $display("ROOT %0d %0d %0d", RID, n, nerr);
endmodule""", MON_SV]
    (out / 'qseam_array_tb.sv').write_text('\n'.join(L) + '\n')

    @functools.lru_cache(None)
    def gold(src):
        st, sp = src.split('.')
        if sp == 't_out':
            return tuple(Tf[ri[st]][c] for c in Tcyc)
        A = gold(bus[pb[f'{st}.n_a']]['src'][0])
        Bv = gold(bus[pb[f'{st}.n_b']]['src'][0])
        return tuple(rotl(x) ^ y for x, y in zip(A, Bv))
    hexfile(out, 'root_gold', [v for r in roots for v in gold(bus[r]['src'][0])], 8)
    meta = dict(bench='array', deskew=deskew, mut=mut, xvm_model=xvm, xvm_contract=XVM, instructions=NI, tree_words_per_tile=NG,
                tiles=len(tiles), nodes=len(nodes), roots=len(roots), station_bits=CW_ST + 1,
                misaligned_nodes_as_placed=len(mis), skew_histogram=dict(sorted(collections.Counter(d for _, d in mis).items())),
                pad_relays=sum(pads.values()), pad_buses=len([v for v in pads.values() if v]),
                pad_bits=sum(v * bus[k]['w'] for k, v in pads.items()),
                worst=sorted(mis, key=lambda x: -abs(x[1]))[:6],
                tap_arrival=dict(min=min(tbase(t) for t in tiles), max=max(tbase(t) for t in tiles)),
                relays=sum(bus[b]['K'] for b in ARR) + Kib, end_cycle=end)
    return meta, g.mons


def gen_p2p(S, rec, out, mut):
    g = Gen(S, mut)
    bus, L = g.bus, g.L
    vl = next((int(m.split(':')[1]) for m in mut if m.startswith('vl:')), VL)
    pam = next((int(m.split(':')[1]) for m in mut if m.startswith('pam:')), PAM)
    E = merged(rec)
    t0, nE = E[0][0], len(E)
    L += tb_head('qseam_p2p_tb')
    hexfile(out, 'e_cyc', [c - t0 for c, _ in E], 8)
    hexfile(out, 'e_fp', [f for _, f in E], 8)
    L += [f'  reg [31:0] ecyc [0:{nE-1}]; reg [31:0] efp [0:{nE-1}];',
          '  initial begin $readmemh("e_cyc.hex", ecyc); $readmemh("e_fp.hex", efp); end']
    sel = sorted(b for b, d in bus.items() if (d['cls'] == 'p2p' or b.startswith('n_rk_'))
                 and not b.startswith(('n_bword', 'n_seq_ib', 'n_su_vm_q')))

    def driver(b, j, W):
        L.append(f"  reg [{W-1}:0] s_{b}; integer bi_{j} = 0;   // {bus[b]['src']} -> {bus[b]['dst']}  K={bus[b]['K']}")
        L.append(f"  always @(posedge clk) begin s_{b} <= '0; if (rst_n && bi_{j} < {nE} && cyc >= ecyc[bi_{j}] + 8) begin "
                 f"s_{b} <= enc(bi_{j}, mix(efp[bi_{j}], {j}))[{W-1}:0]; bi_{j} <= bi_{j} + 1; end end")
    for j, b in enumerate(sel):
        W = bus[b]['w']
        driver(b, j, W)
        end = g.chain(b)
        L.append(f"  assign {b} = s_{b};")
        if b.startswith('n_tt_f'):          # ctlm p_am pin register (composed seam)
            L.append(f"  reg [{W-1}:0] pam_{b} [0:{max(pam, 1)-1}];")
            if pam:
                L.append(f"  always @(posedge clk) begin pam_{b}[0] <= {end}; for (int k = 1; k < {pam}; k++) pam_{b}[k] <= pam_{b}[k-1]; end")
                po = f"pam_{b}[{pam-1}]"
            else:
                po = end
                L.append(f"  // MUTANT: no p_am pin register")
            g.mon(f"s_{b}", po, W, W, W, bus[b]['K'] + PAM, bus=f'p_am:{b}', cls='ctlm_pam', K=bus[b]['K'], pad=0, w=W)
        if b == 'n_su_vm_a':               # VM SU master: answer word = the request echoed, VL cycles from the VM pin
            Wq = bus['n_su_vm_q']['w']
            L.append(f"  reg [{W-1}:0] vl_p [0:{vl-1}]; always @(posedge clk) begin vl_p[0] <= {end}; for (int k = 1; k < {vl}; k++) vl_p[k] <= vl_p[k-1]; end")
            qend = g.chain('n_su_vm_q')
            L.append(f"  assign n_su_vm_q = {{{Wq - W}'d0, vl_p[{vl-1}]}};")
            g.mon(f"s_{b}", qend, W, Wq, W, bus[b]['K'] + VL + bus['n_su_vm_q']['K'], bus='su_master:n_su_vm_a->n_su_vm_q',
                  cls='su_master', K=bus[b]['K'] + bus['n_su_vm_q']['K'], pad=0, w=W)
    L += [f'  always @(posedge clk) if (cyc == {E[-1][0] - t0 + 600}) begin $display("QSEAM_P2P END seams={len(sel)}"); $finish; end',
          'endmodule', MON_SV]
    (out / 'qseam_p2p_tb.sv').write_text('\n'.join(L) + '\n')
    meta = dict(bench='p2p', mut=mut, seams=len(sel) + 1, relays=sum(bus[b]['K'] for b in sel) + bus['n_su_vm_q']['K'],
                transactions_per_seam=nE, vl_model=vl, vl_contract=VL, pam_model=pam, pam_contract=PAM)
    return meta, g.mons


def gen_credit(S, rec, out, mut):
    g = Gen(S, mut)
    bus, L = g.bus, g.L
    E = merged(rec)
    t0, nE = E[0][0], len(E)
    xcr = sum(int(m.split(':')[1]) for m in mut if m.startswith('cr:'))
    lanes = [('coll', ['n_seq_coll', 'XF', 'n_seq_coll_x'], ['n_coll_seq', 'XF', 'n_coll_seq_x'])]
    lanes += [(f'cbuf{k}', [f'n_o4_cb_ctl_{k}'], [f'n_o4_cb_rdy_{k}']) for k in range(8)]
    lanes += [(f'rs{k}', [f'n_rs_{k}'], [f'n_rc_{k}']) for k in range(6) if f'n_rs_{k}' in S['buses']]   # TP8: 3 bands
    L += tb_head('qseam_credit_tb')
    hexfile(out, 'e_cyc', [c - t0 for c, _ in E], 8)
    hexfile(out, 'e_fp', [f for _, f in E], 8)
    L += [f'  reg [31:0] ecyc [0:{nE-1}]; reg [31:0] efp [0:{nE-1}];',
          '  initial begin $readmemh("e_cyc.hex", ecyc); $readmemh("e_fp.hex", efp); end']
    meta = dict(bench='credit', mut=mut, extra_credits=xcr, transactions_per_lane=nE, lanes={})

    def path(nm, segs, tag):
        cur, k_tot, src, w = None, 0, None, None
        for s in segs:
            if s == 'XF':
                L.append(f"  reg [{w-1}:0] {nm}_{tag}_xf [0:{XFIFO-1}]; always @(posedge clk) begin {nm}_{tag}_xf[0] <= {cur}; "
                         f"for (int k = 1; k < {XFIFO}; k++) {nm}_{tag}_xf[k] <= {nm}_{tag}_xf[k-1]; end")
                cur, k_tot = f"{nm}_{tag}_xf[{XFIFO-1}]", k_tot + XFIFO
                continue
            d = bus[s]
            L.append(f"  // seam {s}: {d['src']} -> {d['dst']}  K={d['K']}")
            end = g.chain(s, kind='credit')
            if cur is not None:   # element out flop between two die seams (io_xfifo port)
                L.append(f"  reg [{d['w']-1}:0] {s}_po; always @(posedge clk) {s}_po <= {cur}; assign {s} = {s}_po;")
                k_tot += 1
            else:
                src = s
            cur, k_tot, w = end, k_tot + d['K'], d['w']
        return src, cur, k_tot, w
    for j, (nm, fwd, ret) in enumerate(lanes):
        fs, fe, kf, wfe = path(nm, fwd, 'f')
        rs_, re_, kr, wre = path(nm, ret, 'r')
        Wf, Wr = bus[fwd[0]]['w'], bus[ret[0]]['w']
        WC = min(Wf, wfe)
        CR = 1 + kf + 1 + 1 + kr + 1     # out flop, fwd chain, receiver pin flop, pop + return flop, ret chain, sender pin flop
        meta['lanes'][nm] = dict(fwd=fwd, ret=ret, K_fwd=kf, K_ret=kr, credits_round_trip=CR, buffer=CR)
        L += [f"  wire {nm}_cret = {re_}[0];",
              f"  qseam_credit_lane #(.WF({Wf}), .WFE({wfe}), .WR({Wr}), .CR({CR}), .XCR({xcr}), .NEV({nE}), .ID({j}), .WC({WC})) l_{nm} "
              f"(.clk(clk), .rst_n(rst_n), .cyc(cyc), .ret_in({nm}_cret), .fwd_out({fs}), .fwd_in({fe}), .ret_out({rs_}));"]
    L += [f'  always @(posedge clk) if (cyc == {E[-1][0] - t0 + 4 * nE + 400}) begin $display("QSEAM_CREDIT END lanes={len(lanes)}"); $finish; end',
          'endmodule', MON_SV,
          '''module qseam_credit_lane #(parameter integer WF = 66, parameter integer WFE = 66, parameter integer WR = 1, parameter integer CR = 8,
    parameter integer XCR = 0, parameter integer NEV = 1, parameter integer ID = 0, parameter integer WC = 25)
    (input clk, input rst_n, input [31:0] cyc, input ret_in, output [WF-1:0] fwd_out, input [WFE-1:0] fwd_in, output [WR-1:0] ret_out);
''' + SV_FN + '''
  // sender: CR (+XCR mutant) credits, one word per cycle at the recorded event cycles; receiver: pin flop, CR-word
  // buffer, pops only in the second half of every 512-cycle window (a 256-cycle stall
  // > every round trip, so all credits land in the buffer), one credit returned per pop
  integer ei = 0, credits = CR + XCR, rx = 0, nerr = 0, ns = 0; reg [WF-1:0] oq = '0; reg [WR-1:0] rq = '0; reg [WFE-1:0] iq = '0; reg rin = 0;
  reg [WF-1:0] pend [$]; reg [WC-1:0] exp_q [$]; reg [WC-1:0] buf_q [$];
  assign fwd_out = oq; assign ret_out = rq;
  always @(posedge clk) begin
    oq <= '0; rq <= '0; iq <= fwd_in; rin <= ret_in;
    if (rst_n) begin
      if (ei < NEV && cyc >= qseam_credit_tb.ecyc[ei] + 8) begin pend.push_back(enc(ei, mix(qseam_credit_tb.efp[ei], ID))[WF-1:0]); ei = ei + 1; end
      if (rin) credits = credits + 1;
      if (credits > CR + XCR) begin nerr = nerr + 1; if (nerr <= 1) $display("CREDIT_EXCESS lane=%0d cyc=%0d", ID, cyc); end
      if (pend.size() != 0 && credits > 0) begin oq <= pend[0]; exp_q.push_back(pend[0][WC-1:0]); void'(pend.pop_front()); credits = credits - 1; ns = ns + 1; end
      if (iq[0]) begin buf_q.push_back(iq[WC-1:0]);
        if (buf_q.size() > CR) begin nerr = nerr + 1; if (nerr <= 1) $display("BUFFER_OVERFLOW lane=%0d cyc=%0d depth=%0d", ID, cyc, buf_q.size()); end end
      if (buf_q.size() != 0 && (cyc % 512) >= 256) begin
        if (exp_q.size() == 0 || buf_q[0] != exp_q[0]) begin nerr = nerr + 1; if (nerr <= 1) $display("WORD_MISMATCH lane=%0d cyc=%0d", ID, cyc); end
        if (exp_q.size() != 0) void'(exp_q.pop_front());
        void'(buf_q.pop_front()); rq <= 1; rx = rx + 1;
      end
    end
  end
  final $display("LANE %0d %0d %0d %0d %0d %0d %0d %0d", ID, ei, ns, rx, pend.size(), exp_q.size(), credits, nerr);
endmodule''']
    (out / 'qseam_credit_tb.sv').write_text('\n'.join(L) + '\n')
    return meta, g.mons


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--seams', required=True)
    ap.add_argument('--rec', required=True)
    ap.add_argument('--contract', required=True)
    ap.add_argument('--bench', choices=('array', 'p2p', 'credit'), required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--deskew', action='store_true')
    ap.add_argument('--mut', action='append', default=[])
    ap.add_argument('--tile-subset', action='store_true', help='qwen-tp8: map the die tiles onto the first N recorded tiles')
    a = ap.parse_args()
    global TILE_SUBSET
    TILE_SUBSET = a.tile_subset
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    S = json.load(open(a.seams))
    C = json.load(open(a.contract))
    # the bench is built from the contract's relay census: die.v relays per master == die_top_logic.relays
    got = collections.Counter(r['master'] for d in S['buses'].values() for r in d['relays'])
    want = C['die_top_logic']['relays']
    assert dict(got) == want, 'die.v relay census != contract die_top_logic.relays'
    assert any(d['id'] == 'D5' and '509' in d['change'] for d in C['deltas']), 'contract lacks D5 509-bit station words'
    rec = load_rec(a.rec, need_t=a.bench == 'array')
    fn = dict(array=lambda: gen_array(S, rec, out, a.deskew, a.mut), p2p=lambda: gen_p2p(S, rec, out, a.mut),
              credit=lambda: gen_credit(S, rec, out, a.mut))[a.bench]
    meta, mons = fn()
    meta.update(contract_version=C['version'], contract_relays=sum(want.values()))
    json.dump(dict(meta=meta, monitors=mons), open(out / 'expect.json', 'w'))
    print(json.dumps(meta)[:1200])


if __name__ == '__main__':
    main()
