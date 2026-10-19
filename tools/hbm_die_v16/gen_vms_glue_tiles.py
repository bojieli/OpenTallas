#!/usr/bin/env python3
"""OWNERS-HBM/VM-GLUE 2026-10-18, physical rework HBM-KITS-C/VMGLUE 10-18 (g2): hardened-tile tops of the VM hub glue.
Writes
  rtl/hbm_accel/generic/vm/static/hfd_hgi_vms_glue_tiles.sv      the three tile masters
  rtl/hbm_accel/generic/vm/static/hfd_hgi_vms_glue_tiles_ref.sv  BENCH-ONLY contract references <tile>_ref (flat glue
                                                                 ports): the UNCHANGED historical glue
                                                                 ot_vms_slice_static_glue (BANK_PIN_IN 3) behind the
                                                                 tile's latency contract
Tile top = hfd_vms_glue_core_lt (hfd_hgi_vms_glue_lt.sv: the glue wiring with reset-light ring stops / replay and the
parallel hub response demultiplex) plus
  (1) ONE tile clock clk (clk_hub / clk_ring[1:0] / clk_replay are the same stream clock on the same edge);
  (2) ONE reset port rst_n -> ot_rst_relay, 7 regional copies (hub | CW stop | CCW stop | replay + status | hub bank
      face groups E / N / S, g3): release +3 edges after the port (SYNC 2 + TREE 1), assertion asynchronous;
  (3) per-bank ports b<k>_* (a port sits on ONE face, next to its bank) and per-LANE ring ports
      <cw_in|cw_out|ccw_in|ccw_out>_l<k> (flit bits [k*276 +: 276], the bank-k lane) + _h (header bits [2223:2208]), so
      the ring face is laid out in lane bands beside the bank faces (vms_glue_kit_specs.py);
  (4) ONE register stage at every bank-side port (inputs eg / pr / xq_done / xq2_done / status [/ flt] land on a
      plain flop at the pin; outputs xq / xq2 / pq leave from a relay flop at the pin): the tile spans 648 x 1555 um,
      so a bank face to the ring face or to the hub is two reach stages, never one.  The ring commit check moves with
      it: COMMIT_DELAY 5 + 1 (bank pin) + 2 (tile xq relay + xq_done landing) = 8 (the historical BANK_PIN_IN knob).
  (5) E quadrants: the slice id is a strap pin, ONE master serves SE (1, R0) and NE (3, MX); E = NC 0 glue
      (hfd_hgi_vms_static_{SE,NE}_glue, the d4g binding since l4_idx_quad).
COMPILER CONTRACT (vs the historical glue at the same ports), g2 part: every bank-side input is consumed 1 edge later
and every bank-side output appears 1 edge later (eject xq -> xq_done check = COMMIT_DELAY 8, bank_status -> vmstat +1);
reset release +3 edges.  g3 part (HOURLY-HBM/HH-3 10-19, hfd_hgi_vms_glue_lt.sv header): each ring stop consumes every
input except xq_done 1 edge later (ring transit +1 per hub, eject xq / cco +1, tx_enable / tx_source issued 1 edge
earlier relative to the flit, hub -> ring injection +1, replay return ri +1, WACK / ack +1, mirror egress +1 more) and its
rce leaves 1 edge later again (lane-OR tree: rce -> replay -> hq +2); the hub drives pq 1 edge later and consumes pr,
response_enable and response_seq 1 edge later (bank round trip pq -> pr -> cr +4 in all with the g2 pin stages; slot
reuse after a response +1).  <tile>_ref states exactly that with the UNCHANGED historical children and explicit
1-edge delays (hfd_vms_glue_core_g3_ref); tools/hbm_die_v16/vms_glue_tile_equiv.py runs tile vs ref in lockstep.
g4 part (HBM-SAFE-VMGLUE 10-19, SAFE-DESIGN checklist; g3 gates sat >6 h in GRT repair at WNS -21..-44 ps and a placed
reach census (3_place.odb, lanes/HBM-SAFE-VMGLUE_logs) found ~21-33k reg->reg paths > 405 um): REACH stages so that no
single-cycle wire exceeds ~405 um -- bank-side ports pin flop + 2 relays (xq_done / xq2_done + 3: COMMIT_DELAY 13), hub
client ports (cq / cr / schedule controls / status outputs / sid strap) pin flop + 2 relays, hub island <-> ring-stop
header band one relay each (pi, ri, cco, rce, faults -> status), ring stop: second landing with per-half relay copies of
the header decode / tx select / payloads (stop inputs +2 vs historical, ring transit +1 per hub vs g3) and a 3-level rce
tree (rce +1 vs g3).  Schedule selects are REGISTERED ONE-HOT, decoded a stage ahead from the static schedule: hub bank
select (bank_enable / bank_client, qualified), ring-stop tx select (tx_enable / tx_source), replay select (replay_source);
a schedule collision stays a fault (status), never an arbitration.  hfd_vms_glue_core_g4_ref states every edge.
Tile parameter MUT (bench only, default 0): 1 ring-stop flit mutant, 3 eg not landed (contract break), 4 hub pq
without the g3 face-group edge (contract break), 5 hub -> ring pi and ring -> replay rce without the g4 relays (contract break).
    gen_vms_glue_tiles.py [--check]
"""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
D = ROOT / 'rtl/hbm_accel/generic/vm/static'
OUT, REF = D / 'hfd_hgi_vms_glue_tiles.sv', D / 'hfd_hgi_vms_glue_tiles_ref.sv'
LANE = 276
# per-bank slices of the glue's flat bank buses (gen_vms_hoist.py: bank b at [b*W+:W]); name, dir, width, flat bus
BANK = [('xq', 'output', 276, 'bk_xq'), ('xq2', 'output', 276, 'bk_xq2'), ('xq_done', 'input', 1, 'bk_xq_done'),
        ('xq2_done', 'input', 1, 'bk_xq2_done'), ('eg', 'input', 276, 'bk_eg'), ('pq', 'output', 285, 'bk_pq'),
        ('pr', 'input', 266, 'bk_pr'), ('status', 'input', 18, 'bank_status')]
FLT = ('flt', 'input', 1, 'bk_flt')
# g4 (HBM-SAFE-VMGLUE 10-19): upper = lane bands in the upper half of the ring face (vms_glue_kit_specs.py plan A: bottom
# -> top 6 7 0 1 | hdr | 2 3 4 5; plan B (NW): 5 4 3 2 | hdr | 1 0 7 6); band pairs (0,1) (2,3) (4,5) (6,7) never straddle
M = dict(sw=dict(nc=2, rg=5, wg=2, sid="2'd0", flt=False, q='SW', upper="8'b00111100"),
         e=dict(nc=0, rg=4, wg=2, sid='strap', flt=False, q='SE/NE', upper="8'b00111100"),
         nw=dict(nc=0, rg=5, wg=3, sid="2'd2", flt=True, q='NW', upper="8'b11000011"))
RINGB = [('cw_in', 'input'), ('cw_out', 'output'), ('ccw_in', 'input'), ('ccw_out', 'output')]
RINGC = [('ring_tx_enable', 'input', 2), ('ring_tx_source', 'input', 6), ('replay_enable', 'input', 1),
         ('replay_source', 'input', 1)]
OUTS = [('hub_status', 3), ('mirror_busy', 2), ('vmstat', 19), ('ring_fault', 3)]
# g4 reach stages at the tile ports (HBM-SAFE-VMGLUE 10-19, SAFE-DESIGN item 2: no single-cycle wire > 405 um on the
# 648 x 1555 um tile): every bank-side port is a pin flop + 2 relays (bank face <-> hub island / lane band <= ~1,100 um =
# 3 hops), xq_done / xq2_done a pin flop + 3 relays (bank face -> ring header band <= ~1,430 um = 4 hops), every hub-side
# client port (cq / cr / schedule controls / status outputs / sid strap) a pin flop + 2 relays (corner -> hub island
# <= ~1,000 um).  Ring ports and ring_tx_* (ring face, consumed beside the pins) keep none.
DB, DD, DC = 3, 4, 3
COMMIT_DELAY = 5 + 1 + DB + DD   # historical 5 + bank pin 1 + xq relay DB + xq_done landing DD (g2: 5 + 1 + 1 + 1 = 8)
CLIENT_CTL = ('replay_enable', 'replay_source')   # RINGC entries that are hub-island (client-side) controls


def w(n):
    return f'[{n - 1}:0] ' if n > 1 else ''


def cw_of(nc):
    return max(1, (nc).bit_length()) if nc else 1   # CW = clog2(NC+1)


def bankp(c):
    return BANK + ([FLT] if c['flt'] else [])


def common(c):
    nc = c['nc']; cw = cw_of(nc)
    p = []
    if nc:
        p += [('cq', 'input', nc * 338), ('cr', 'output', nc * 274)]
    p += [('client_seq', 'input', (nc + 1) * 2), ('response_enable', 'input', nc + 1), ('response_seq', 'input', (nc + 1) * 2),
          ('bank_enable', 'input', 8), ('bank_client', 'input', 8 * cw), ('hub_ring_enable', 'input', 2),
          ('hub_ring_client', 'input', 2 * cw)]
    return p


def ports(k, c):
    p = [('clk', 'input', 1), ('rst_n', 'input', 1)]
    if c['sid'] == 'strap':
        p.append(('sid', 'input', 2))
    p += common(c)
    for n, d in RINGB:
        p += [(f'{n}_l{b}', d, LANE) for b in range(8)] + [(f'{n}_h', d, 16)]
    p += RINGC
    for b in range(8):
        p += [(f'b{b}_{n}', d, wd) for n, d, wd, _ in bankp(c)]
    p += [(n, 'output', wd) for n, wd in OUTS]
    return p


def ref_ports(k, c):
    """the historical glue's flat port list (one clk)"""
    p = [('clk', 'input', 1), ('rst_n', 'input', 1)]
    if c['sid'] == 'strap':
        p.append(('sid', 'input', 2))
    p += common(c)
    p += [(n, d, 2224) for n, d in RINGB] + RINGC
    p += [(f, d, 8 * wd) for _, d, wd, f in bankp(c)]
    p += [(n, 'output', wd) for n, wd in OUTS]
    return p


def decl(p):
    return ',\n'.join(f'    {d} wire {w(n)}{nm}' for nm, d, n in p)


def cat(names):
    return '{' + ', '.join(names) + '}'


def chain(L, src, width, depth, name):
    """plain register chain src -> name_s0 -> ... -> name_s<depth-1>; returns the last stage (src when depth 0)"""
    prev = src
    for i in range(depth):
        L.append(f'    reg {w(width)}{name}_s{i}; always @(posedge clk) {name}_s{i} <= {prev};')
        prev = f'{name}_s{i}'
    return prev


def bank_depth(n):
    return DD if n in ('xq_done', 'xq2_done') else DB


def client_ins(c):
    """hub-side client inputs (tile port name, width) that get the DC reach stages"""
    p = [(nm, wd) for nm, d, wd in common(c) if d == 'input']
    p += [(nm, wd) for nm, d, wd in RINGC if nm in CLIENT_CTL]
    if c['sid'] == 'strap':
        p.append(('sid', 2))
    return p


def client_outs(c):
    p = [(nm, wd) for nm, d, wd in common(c) if d == 'output']
    return p + list(OUTS)


def tile(k, c):
    p = ports(k, c); nc = c['nc']
    L = [f'module hfd_hgi_vms_glue_{k}_t #(parameter integer MUT=0) (', decl(p), ');']
    L.append('    // reset landing (SAFE-DESIGN item 1): the port lands in 2 plain registered stages at its face (rst_l0 -> rst_l1),')
    L.append('    // then the regional relay (2 sync + 11 region copies): assertion +2 edges, release +5 edges after the port')
    L.append('    reg rst_l0, rst_l1;')
    L.append('    always @(posedge clk) begin rst_l0 <= rst_n; rst_l1 <= rst_l0; end')
    L.append('    wire [10:0] rr;')
    L.append('    ot_rst_relay #(.REGIONS(11),.SYNC_STAGES(2),.TREE_STAGES(1)) u_rst(.clk(clk),.rst_n_in(rst_l1),.rst_n(rr));')
    L.append('    // ring buses: lane k = flit bits [k*276 +: 276], header = [2223:2208]')
    for n, d in RINGB:
        L.append(f'    wire [2223:0] {n};')
        if d == 'input':
            L.append(f'    assign {n} = ' + cat([f'{n}_h'] + [f'{n}_l{b}' for b in reversed(range(8))]) + ';')
        else:
            L += [f'    assign {n}_l{b} = {n}[{b * LANE + LANE - 1}:{b * LANE}];' for b in range(8)]
            L.append(f'    assign {n}_h = {n}[2223:2208];')
    L.append(f'    // g4 reach stages: bank-side ports pin flop + {DB - 1} relays (xq_done / xq2_done + {DD - 1}), hub-side client ports'
             f' pin flop + {DC - 1} relays (plain registers, no reset: flushed while the regional resets are held)')
    for n, d, wd, f in bankp(c):
        dep = bank_depth(n)
        L.append(f'    wire [{8 * wd - 1}:0] {f}_p, {f}_c;')
        if d == 'input':
            L.append(f'    assign {f}_p = ' + cat([f'b{b}_{n}' for b in reversed(range(8))]) + ';')
            last = chain(L, f'{f}_p', 8 * wd, dep, f)
            byp = " (MUT == 3) ? bk_eg_p :" if f == 'bk_eg' else ''
            L.append(f'    assign {f}_c ={byp} {last};')
        else:
            last = chain(L, f'{f}_c', 8 * wd, dep, f)
            L.append(f'    assign {f}_p = {last};')
            L += [f'    assign b{b}_{n} = {f}_p[{b * wd + wd - 1}:{b * wd}];' if wd > 1 else f'    assign b{b}_{n} = {f}_p[{b}];'
                  for b in range(8)]
    for nm, wd in client_ins(c):
        last = chain(L, nm, wd, DC, f'{nm}_g')
        L.append(f'    wire {w(wd)}{nm}_c = {last};')
    for nm, wd in client_outs(c):
        L.append(f'    wire {w(wd)}{nm}_c;')
        last = chain(L, f'{nm}_c', wd, DC, f'{nm}_g')
        L.append(f'    assign {nm} = {last};')
    st = 'bank_status_c'
    if c['flt']:
        L.append('    // NW: the wq2-merge leaves (vmm_NWb) sticky flt -> bank status bit 17 (as hfd_hgi_vms_static_NW_glue)')
        L.append('    wire [143:0] bank_status_m;')
        L += [f'    assign bank_status_m[{b * 18 + 17}:{b * 18}] = {{bank_status_c[{b * 18 + 17}] | bk_flt_c[{b}], '
              f'bank_status_c[{b * 18 + 16}:{b * 18}]}};' for b in range(8)]
        st = 'bank_status_m'
    sid = 'sid_c' if c['sid'] == 'strap' else c['sid']
    conn = ['.clk(clk)', '.rst_n(rr)', f'.sid({sid})']
    conn += [f'.{nm}({nm}_c)' for nm, _, _ in common(c)]
    if not nc:
        conn += ['.cq(338\'d0)', '.cr()']
    conn += [f'.{n}({n})' for n, _ in RINGB] + [f'.{n}({n}_c)' if n in CLIENT_CTL else f'.{n}({n})' for n, _, _ in RINGC]
    conn += [f'.bank_status({st})', '.bk_xq(bk_xq_c)', '.bk_xq2(bk_xq2_c)', '.bk_xq_done(bk_xq_done_c)',
             '.bk_xq2_done(bk_xq2_done_c)', '.bk_eg(bk_eg_c)', '.bk_pq(bk_pq_c)', '.bk_pr(bk_pr_c)']
    conn += [f'.{n}({n}_c)' for n, _ in OUTS]
    L.append(f'    hfd_vms_glue_core_lt #(.NC({nc}),.COMMIT_DELAY({COMMIT_DELAY}),.UPPER({c["upper"]}),'
             f'.RMUT((MUT == 1) ? 1 : (MUT == 4) ? 4 : (MUT == 5) ? 5 : 0)) u_core (\n        '
             + ',\n        '.join(conn) + ');')
    L.append('endmodule')
    return '\n'.join(L) + '\n'


def ref(k, c):
    p = ref_ports(k, c); nc = c['nc']
    L = [f'module hfd_hgi_vms_glue_{k}_t_ref (', decl(p), ');']
    L.append('    wire rr;  // the same reset timing: 2-stage landing, then 2 sync + 1 relay stage')
    L.append('    reg rst_l0, rst_l1;')
    L.append('    always @(posedge clk) begin rst_l0 <= rst_n; rst_l1 <= rst_l0; end')
    L.append('    ot_rst_relay #(.REGIONS(1),.SYNC_STAGES(2),.TREE_STAGES(1)) u_rst(.clk(clk),.rst_n_in(rst_l1),.rst_n(rr));')
    L.append(f'    // contract: bank-side inputs consumed {DB} edges later (xq_done / xq2_done {DD}), bank-side outputs {DB} edges later;'
             f' hub-side client inputs / outputs (+ sid strap) {DC} edges each way')
    for n, d, wd, f in bankp(c):
        dep = bank_depth(n)
        L.append(f'    wire [{8 * wd - 1}:0] {f}_g;')
        if d == 'input':
            last = chain(L, f, 8 * wd, dep, f'{f}_d')
            L.append(f'    assign {f}_g = {last};')
        else:
            last = chain(L, f'{f}_g', 8 * wd, dep, f'{f}_d')
            L.append(f'    assign {f} = {last};')
    for nm, wd in client_ins(c):
        last = chain(L, nm, wd, DC, f'{nm}_d')
        L.append(f'    wire {w(wd)}{nm}_c = {last};')
    for nm, wd in client_outs(c):
        L.append(f'    wire {w(wd)}{nm}_c;')
        last = chain(L, f'{nm}_c', wd, DC, f'{nm}_d')
        L.append(f'    assign {nm} = {last};')
    st = 'bank_status_g'
    if c['flt']:
        L.append('    wire [143:0] bank_status_m;')
        L.append('    genvar fb;')
        L.append('    generate for(fb=0;fb<8;fb=fb+1)begin:g_flt')
        L.append('        assign bank_status_m[fb*18+:18]={bank_status_g[fb*18+17]|bk_flt_g[fb],bank_status_g[fb*18+:17]};')
        L.append('    end endgenerate')
        st = 'bank_status_m'
    sid = 'sid_c' if c['sid'] == 'strap' else c['sid']
    conn = ['.clk(clk)', '.rst_n(rr)', f'.sid({sid})']
    conn += [f'.{nm}({nm}_c)' for nm, _, _ in common(c)]
    if not nc:
        conn += [".cq(338'd0)", '.cr()']
    conn += [f'.{n}({n})' for n, _ in RINGB] + [f'.{n}({n}_c)' if n in CLIENT_CTL else f'.{n}({n})' for n, _, _ in RINGC]
    conn += [f'.bank_status({st})'] + [f'.{f}({f}_g)' for _, _, _, f in BANK if f != 'bank_status']
    conn += [f'.{n}({n}_c)' for n, _ in OUTS]
    L.append(f'    hfd_vms_glue_core_g4_ref #(.NC({nc}),.COMMIT_DELAY({COMMIT_DELAY})) u_glue (\n        '
             + ',\n        '.join(conn) + ');')
    L.append('endmodule')
    return '\n'.join(L) + '\n'


REFCORE = """// g4 contract core (HBM-SAFE-VMGLUE 10-19): ot_vms_slice_static_glue wiring (one clock) + the g3 / g4 edges, stated as
// plain delays around the UNCHANGED historical children: each ring stop sees every input except xq_done 2 edges late (g3
// landing + g4 band relay) and its rce leaves 2 edges late (3-level lane-OR tree); the hub sees pr / response_enable /
// response_seq 1 edge late and its pq leaves 1 edge late (g3); g4 hub-island <-> ring-stop reach relays: pi and ri +1
// more into the stops, cco +1 into the hub, rce +1 into the replay, ring faults +1 into the status block.
module hfd_vms_glue_core_g4_ref #(
    parameter integer NC=0,
    parameter integer CW=((NC+1)>1)?$clog2(NC+1):1,
    parameter integer COMMIT_DELAY=8
)(
    input wire clk, rst_n,
    input wire [1:0] sid,
    input wire [((NC>0)?NC:1)*338-1:0] cq,
    output wire [((NC>0)?NC:1)*274-1:0] cr,
    input wire [(NC+1)*2-1:0] client_seq,
    input wire [(NC+1)-1:0] response_enable,
    input wire [(NC+1)*2-1:0] response_seq,
    input wire [7:0] bank_enable,
    input wire [8*CW-1:0] bank_client,
    input wire [1:0] hub_ring_enable,
    input wire [2*CW-1:0] hub_ring_client,
    input wire [2223:0] cw_in,ccw_in,
    output wire [2223:0] cw_out,ccw_out,
    input wire [1:0] ring_tx_enable,
    input wire [5:0] ring_tx_source,
    input wire replay_enable,replay_source,
    input wire [143:0] bank_status,
    output wire [2207:0] bk_xq,bk_xq2,
    input wire [7:0] bk_xq_done,bk_xq2_done,
    input wire [2207:0] bk_eg,
    output wire [8*285-1:0] bk_pq,
    input wire [8*266-1:0] bk_pr,
    output wire [2:0] hub_status,
    output wire [1:0] mirror_busy,
    output wire [18:0] vmstat,
    output wire [2:0] ring_fault
);
    wire [(NC+1)*338-1:0] hcq;
    wire [(NC+1)*274-1:0] hcr;
    wire [337:0] hq;
    wire [273:0] hr=hcr[NC*274+:274];
    generate if(NC>0)begin:g_local
        assign hcq={hq,cq};assign cr=hcr[NC*274-1:0];
    end else begin:g_no_local
        assign hcq=hq;assign cr='0;
    end endgenerate
    wire [289:0] pi0,pi1;
    wire [263:0] cco0,cco1;
    wire [287:0] rce0,rce1,rce0_s,rce1_s;
    wire [265:0] ri0,ri1;
    wire [2:0] wk01,wk10;
    wire ack01,ack10;
    wire [8*285-1:0] pq_h;
    // the g3 / g4 edges
    reg [8*266-1:0] pr_d; reg [NC:0] re_d; reg [(NC+1)*2-1:0] rs_d; reg [8*285-1:0] pq_d;
    reg [2223:0] cwi_d, ccwi_d, cwi_e, ccwi_e; reg [289:0] pi0_h, pi1_h, pi0_d, pi1_d, pi0_e, pi1_e;
    reg [2207:0] eg_d, eg_e; reg [265:0] ri0_h, ri1_h, ri0_d, ri1_d, ri0_e, ri1_e;
    reg [2:0] wk01_d, wk10_d, wk01_e, wk10_e; reg ack01_d, ack10_d, ack01_e, ack10_e; reg [1:0] txe_d, txe_e;
    reg [5:0] txs_d, txs_e; reg [1:0] sid_d, sid_e;
    reg [287:0] rce0_d, rce1_d, rce0_e, rce1_e, rce0_h, rce1_h; reg [263:0] cco0_h, cco1_h; reg [2:0] rf_h;
    wire [263:0] cco0_s, cco1_s;
    always @(posedge clk) begin
        pr_d<=bk_pr; re_d<=response_enable; rs_d<=response_seq; pq_d<=pq_h;
        pi0_h<=pi0; pi1_h<=pi1; ri0_h<=ri0; ri1_h<=ri1;
        cwi_d<=cw_in; ccwi_d<=ccw_in; pi0_d<=pi0_h; pi1_d<=pi1_h; eg_d<=bk_eg; ri0_d<=ri0_h; ri1_d<=ri1_h;
        wk01_d<=wk01; wk10_d<=wk10; ack01_d<=ack01; ack10_d<=ack10; txe_d<=ring_tx_enable; txs_d<=ring_tx_source;
        sid_d<=sid;
        cwi_e<=cwi_d; ccwi_e<=ccwi_d; pi0_e<=pi0_d; pi1_e<=pi1_d; eg_e<=eg_d; ri0_e<=ri0_d; ri1_e<=ri1_d;
        wk01_e<=wk01_d; wk10_e<=wk10_d; ack01_e<=ack01_d; ack10_e<=ack10_d; txe_e<=txe_d; txs_e<=txs_d; sid_e<=sid_d;
        rce0_d<=rce0_s; rce1_d<=rce1_s; rce0_e<=rce0_d; rce1_e<=rce1_d; rce0_h<=rce0_e; rce1_h<=rce1_e;
        cco0_h<=cco0_s; cco1_h<=cco1_s; rf_h<=ring_fault;
    end
    assign bk_pq=pq_d; assign rce0=rce0_h; assign rce1=rce1_h; assign cco0=cco0_h; assign cco1=cco1_h;
    ot_vms_hub_static #(.NC(NC),.CW(CW)) u_hub(
        .clk(clk),.rst_n(rst_n),.sid(sid),.cq(hcq),.cr(hcr),
        .client_seq(client_seq),.response_enable(re_d),.response_seq(rs_d),
        .bank_enable(bank_enable),.bank_client(bank_client),
        .cw_enable(hub_ring_enable[0]),.cw_client(hub_ring_client[0+:CW]),
        .ccw_enable(hub_ring_enable[1]),.ccw_client(hub_ring_client[CW+:CW]),
        .pq(pq_h),.pr(pr_d),.cwi(pi0),.cci(pi1),.cco0(cco0),.cco1(cco1),.status(hub_status));
    ot_vms_rstop_static #(.COMMIT_DELAY(COMMIT_DELAY)) u_cw(
        .clk(clk),.rst_n(rst_n),.sid(sid_e),.dir(1'b0),
        .tx_enable(txe_e[0]),.tx_source(txs_e[0+:3]),
        .l_in(cwi_e),.l_out(cw_out),.pi(pi0_e),.eg(eg_e),.xq(bk_xq),.xq_done(bk_xq_done),
        .rce(rce0_s),.ri(ri0_e),.wko(wk01),.wki(wk10_e),.cco(cco0_s),
        .ack_o(ack01),.ack_i(ack10_e),.mirror_busy(mirror_busy[0]),.fault(ring_fault[0]));
    ot_vms_rstop_static #(.COMMIT_DELAY(COMMIT_DELAY)) u_ccw(
        .clk(clk),.rst_n(rst_n),.sid(sid_e),.dir(1'b1),
        .tx_enable(txe_e[1]),.tx_source(txs_e[3+:3]),
        .l_in(ccwi_e),.l_out(ccw_out),.pi(pi1_e),.eg(eg_e),.xq(bk_xq2),.xq_done(bk_xq2_done),
        .rce(rce1_s),.ri(ri1_e),.wko(wk10),.wki(wk01_e),.cco(cco1_s),
        .ack_o(ack10),.ack_i(ack01_e),.mirror_busy(mirror_busy[1]),.fault(ring_fault[1]));
    ot_vms_rcl_static u_replay(.clk(clk),.rst_n(rst_n),.sid(sid),
        .rx_enable(replay_enable),.rx_source(replay_source),.rce0(rce0),.rce1(rce1),
        .hq(hq),.hr(hr),.ri0(ri0),.ri1(ri1),.fault(ring_fault[2]));
    ot_vms_status_static u_status(.clk(clk),.rst_n(rst_n),
        .bank_status(bank_status),.hub_status(hub_status),.ring_fault(|rf_h),.vmstat(vmstat));
endmodule
"""


HDR = ('`timescale 1ns/1ps\n`default_nettype none\n// GENERATED by tools/hbm_die_v16/gen_vms_glue_tiles.py (do not edit): ')


def main():
    doc = '\n'.join('// ' + x for x in __doc__.strip().split('\n')[:-1])
    rtl = HDR + 'VM hub-glue tile masters.\n' + doc + '\n' + ''.join(tile(k, c) for k, c in M.items()) + '`default_nettype wire\n'
    rf = (HDR + 'BENCH-ONLY contract references <tile>_ref: the UNCHANGED historical children (ot_vms_hub_static, '
          'ot_vms_rstop_static, ot_vms_rcl_static, ot_vms_status_static) wired as ot_vms_slice_static_glue with the g3 '
          'and g4 edges as explicit plain delays (hfd_vms_glue_core_g4_ref), behind the g4 reach stages on every bank-side and client-side port '
          'and the tile reset relay timing, at the historical flat ports.\n'
          + REFCORE + ''.join(ref(k, c) for k, c in M.items()) + '`default_nettype wire\n')
    if '--check' in sys.argv:
        ok = OUT.read_text() == rtl and REF.read_text() == rf
        print('VMS_GLUE_TILES_GEN', 'CHECK_PASS' if ok else 'CHECK_FAIL'); sys.exit(0 if ok else 1)
    OUT.write_text(rtl); REF.write_text(rf); print('VMS_GLUE_TILES_GEN WROTE', OUT.relative_to(ROOT), REF.relative_to(ROOT))


if __name__ == '__main__':
    main()
